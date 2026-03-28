import argparse
import math
import os
import random
import struct
from dataclasses import dataclass
from typing import List, Tuple


def vec_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vec_cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def vec_norm(v):
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if length == 0.0:
        return (0.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def tri_normal(v0, v1, v2):
    return vec_norm(vec_cross(vec_sub(v1, v0), vec_sub(v2, v0)))


def write_binary_stl(
    path: str,
    triangles: List[
        Tuple[
            Tuple[float, float, float],
            Tuple[float, float, float],
            Tuple[float, float, float],
        ]
    ],
):
    header = b"lampgen_v4_safe_shell".ljust(80, b"\0")
    with open(path, "wb") as handle:
        handle.write(header)
        handle.write(struct.pack("<I", len(triangles)))
        for (v0, v1, v2) in triangles:
            normal = tri_normal(v0, v1, v2)
            handle.write(struct.pack("<3f", *normal))
            handle.write(struct.pack("<3f", *v0))
            handle.write(struct.pack("<3f", *v1))
            handle.write(struct.pack("<3f", *v2))
            handle.write(struct.pack("<H", 0))


@dataclass
class LampParams:
    height: float = 190.0
    r_base: float = 40.0
    taper: float = 0.05
    bulb_amp: float = 14.0
    bulb_count: float = 2.1
    bulb_phase: float = 0.0

    weave_amp: float = 0.95
    weave_theta: float = 32.0
    weave_pitch: float = 42.0
    weave_mix: float = 0.5
    weave_round: float = 0.12
    seam_twist: float = 0.012
    strand_width: float = 0.28
    weave_gap: float = 0.30
    gap_round: float = 0.12
    membrane: float = 0.10
    perforation: float = 0.0
    inner_follow: float = 0.18
    rib_width_scale: float = 0.72
    rib_thickness: float = 1.25
    rib_seg_per_pitch: int = 96

    thickness: float = 1.45
    r_min: float = 10.0

    n_theta: int = 420
    n_z: int = 520


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def smoothstep(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def soft_peak_from_cos(cosine_value: float, width: float) -> float:
    width = clamp(width, 0.04, 0.92)
    threshold = math.cos(math.pi * width)
    if cosine_value <= threshold:
        return 0.0
    t = (cosine_value - threshold) / max(1e-6, 1.0 - threshold)
    return smoothstep(t)


def sanitize_params(p: LampParams) -> LampParams:
    return LampParams(
        height=max(40.0, p.height),
        r_base=max(8.0, p.r_base),
        taper=clamp(p.taper, -0.08, 0.22),
        bulb_amp=max(0.0, p.bulb_amp),
        bulb_count=max(0.4, p.bulb_count),
        bulb_phase=p.bulb_phase,
        weave_amp=max(0.0, p.weave_amp),
        weave_theta=max(1.0, p.weave_theta),
        weave_pitch=max(0.1, p.weave_pitch),
        weave_mix=clamp(p.weave_mix, 0.0, 1.0),
        weave_round=clamp(p.weave_round, 0.0, 0.6),
        seam_twist=clamp(p.seam_twist, -0.15, 0.15),
        strand_width=clamp(p.strand_width, 0.04, 0.9),
        weave_gap=max(0.0, p.weave_gap),
        gap_round=clamp(p.gap_round, 0.0, 0.8),
        membrane=clamp(p.membrane, 0.0, 1.0),
        perforation=clamp(p.perforation, 0.0, 1.0),
        inner_follow=clamp(p.inner_follow, 0.0, 0.6),
        rib_width_scale=clamp(p.rib_width_scale, 0.18, 1.4),
        rib_thickness=max(0.3, p.rib_thickness),
        rib_seg_per_pitch=max(16, int(p.rib_seg_per_pitch)),
        thickness=max(0.45, p.thickness),
        r_min=max(0.0, p.r_min),
        n_theta=max(24, int(p.n_theta)),
        n_z=max(12, int(p.n_z)),
    )


def radius_profile(z: float, p: LampParams) -> float:
    u = z / p.height
    taper_factor = 1.0 - p.taper * u
    end_soft = smoothstep(min(u / 0.10, 1.0)) * smoothstep(min((1.0 - u) / 0.10, 1.0))

    bulb_a = math.sin(2.0 * math.pi * (p.bulb_count * u + p.bulb_phase))
    bulb_b = 0.18 * math.sin(4.0 * math.pi * (p.bulb_count * u + p.bulb_phase) + 0.35)
    radius = p.r_base * taper_factor + p.bulb_amp * (0.92 * bulb_a + bulb_b) * end_soft
    return max(p.r_min + p.thickness + 0.3, radius)


def texture_fade(u: float) -> float:
    return smoothstep(min(u / 0.08, 1.0)) * smoothstep(min((1.0 - u) / 0.08, 1.0))


def weave_displacement(theta: float, z: float, p: LampParams, base_radius: float) -> float:
    u = z / p.height
    theta2 = theta + (2.0 * math.pi * p.seam_twist * u)
    phase_z = 2.0 * math.pi * p.weave_pitch * u

    phase_a = p.weave_theta * theta2 + phase_z
    phase_b = -p.weave_theta * theta2 + phase_z

    ridge_a = soft_peak_from_cos(math.cos(phase_a), p.strand_width)
    ridge_b = soft_peak_from_cos(math.cos(phase_b), p.strand_width)

    strands = ((1.0 - p.weave_mix) * ridge_a + p.weave_mix * ridge_b)
    strands += (p.weave_mix * ridge_a + (1.0 - p.weave_mix) * ridge_b)
    strands *= 0.5

    valley = 1.0 - clamp(ridge_a + ridge_b, 0.0, 1.0)
    harmonic = 0.5 + 0.5 * math.sin(2.0 * phase_z + 0.35 * math.sin(theta2 * 2.0))
    valley = (1.0 - p.gap_round) * valley + p.gap_round * valley * harmonic

    soft_cross = 0.5 * (math.sin(phase_a) + math.sin(phase_b))
    raw = p.weave_amp * strands - p.weave_gap * valley
    raw = (1.0 - p.weave_round) * raw + p.weave_round * (raw + 0.16 * p.weave_amp * soft_cross)

    # Soft-limit the texture so aggressive values compress instead of exploding.
    radial_room = max(0.6, base_radius - (p.r_min + p.thickness + 0.5))
    amplitude_cap = min(
        p.weave_amp + p.weave_gap + 0.2,
        radial_room * 0.34,
        p.thickness * 0.70 + 0.85,
    )
    limited = amplitude_cap * math.tanh(raw / max(0.25, amplitude_cap))
    return limited * texture_fade(u)


def strand_lane_count(p: LampParams) -> int:
    return max(6, int(round(p.weave_theta)))


def family_center_theta(z: float, p: LampParams, lane_index: int, direction: float) -> float:
    u = z / p.height
    lane_spacing = (2.0 * math.pi) / strand_lane_count(p)
    theta2 = lane_index * lane_spacing - direction * (2.0 * math.pi * p.weave_pitch * u) / max(1.0, p.weave_theta)
    theta = theta2 - (2.0 * math.pi * p.seam_twist * u)
    return theta


def polar(radius: float, theta: float, z: float):
    return (radius * math.cos(theta), radius * math.sin(theta), z)


def add_quad(tris, v00, v10, v11, v01, flip=False):
    if not flip:
        tris.append((v00, v10, v11))
        tris.append((v00, v11, v01))
    else:
        tris.append((v00, v11, v10))
        tris.append((v00, v01, v11))


def make_mesh_solid(params: LampParams):
    p = sanitize_params(params)
    outer = [[None] * p.n_theta for _ in range(p.n_z)]
    inner = [[None] * p.n_theta for _ in range(p.n_z)]

    for iz in range(p.n_z):
        z = (p.height * iz) / (p.n_z - 1)
        r0 = radius_profile(z, p)

        for it in range(p.n_theta):
            theta = (2.0 * math.pi * it) / p.n_theta
            disp = weave_displacement(theta, z, p, r0)

            # Keep the shell thickness almost constant to make it print-friendly.
            outer_radius = max(p.r_min + p.thickness + 0.25, r0 + disp)
            inner_radius = max(p.r_min, r0 - p.thickness + p.inner_follow * disp)
            inner_radius = min(inner_radius, outer_radius - 0.35)
            inner_radius = max(p.r_min, inner_radius)

            outer[iz][it] = polar(outer_radius, theta, z)
            inner[iz][it] = polar(inner_radius, theta, z)

    tris = []

    for iz in range(p.n_z - 1):
        for it in range(p.n_theta):
            it2 = (it + 1) % p.n_theta
            add_quad(
                tris,
                outer[iz][it],
                outer[iz][it2],
                outer[iz + 1][it2],
                outer[iz + 1][it],
                flip=False,
            )

    for iz in range(p.n_z - 1):
        for it in range(p.n_theta):
            it2 = (it + 1) % p.n_theta
            add_quad(
                tris,
                inner[iz][it],
                inner[iz + 1][it],
                inner[iz + 1][it2],
                inner[iz][it2],
                flip=False,
            )

    iz = 0
    for it in range(p.n_theta):
        it2 = (it + 1) % p.n_theta
        o0 = outer[iz][it]
        o1 = outer[iz][it2]
        i0 = inner[iz][it]
        i1 = inner[iz][it2]
        tris.append((o0, i1, i0))
        tris.append((o0, o1, i1))

    iz = p.n_z - 1
    for it in range(p.n_theta):
        it2 = (it + 1) % p.n_theta
        o0 = outer[iz][it]
        o1 = outer[iz][it2]
        i0 = inner[iz][it]
        i1 = inner[iz][it2]
        tris.append((o0, i0, i1))
        tris.append((o0, i1, o1))

    return tris


def add_rib_strip(tris, p: LampParams, lane_index: int, direction: float):
    total_segs = max(p.n_z, int(abs(p.weave_pitch) * p.rib_seg_per_pitch / 8.0))
    nz = total_segs + 1
    lane_spacing = (2.0 * math.pi) / strand_lane_count(p)
    rib_factor = 0.55 + 0.7 * p.strand_width

    for iz in range(nz - 1):
        z0 = (p.height * iz) / (nz - 1)
        z1 = (p.height * (iz + 1)) / (nz - 1)
        r_base0 = radius_profile(z0, p)
        r_base1 = radius_profile(z1, p)
        c0 = family_center_theta(z0, p, lane_index, direction)
        c1 = family_center_theta(z1, p, lane_index, direction)

        d0 = weave_displacement(c0, z0, p, r_base0)
        d1 = weave_displacement(c1, z1, p, r_base1)
        ro0 = max(p.r_min + p.rib_thickness + 0.2, r_base0 + max(0.0, d0))
        ro1 = max(p.r_min + p.rib_thickness + 0.2, r_base1 + max(0.0, d1))
        ri0 = max(p.r_min, ro0 - p.rib_thickness)
        ri1 = max(p.r_min, ro1 - p.rib_thickness)

        half_width0 = lane_spacing * 0.5 * p.rib_width_scale * rib_factor
        half_width1 = lane_spacing * 0.5 * p.rib_width_scale * rib_factor

        o00 = polar(ro0, c0 - half_width0, z0)
        o01 = polar(ro0, c0 + half_width0, z0)
        o10 = polar(ro1, c1 - half_width1, z1)
        o11 = polar(ro1, c1 + half_width1, z1)
        i00 = polar(ri0, c0 - half_width0, z0)
        i01 = polar(ri0, c0 + half_width0, z0)
        i10 = polar(ri1, c1 - half_width1, z1)
        i11 = polar(ri1, c1 + half_width1, z1)

        add_quad(tris, o00, o10, o11, o01, flip=False)
        add_quad(tris, i00, i01, i11, i10, flip=False)
        add_quad(tris, o00, i00, i10, o10, flip=False)
        add_quad(tris, o01, o11, i11, i01, flip=False)

        if iz == 0:
            add_quad(tris, o00, o01, i01, i00, flip=False)
        if iz == nz - 2:
            add_quad(tris, o10, i10, i11, o11, flip=False)


def make_mesh_perforated(params: LampParams):
    p = sanitize_params(params)
    tris = []
    lane_count = strand_lane_count(p)
    family_a = lane_count
    family_b = max(1, int(round(lane_count * (0.45 + 0.55 * p.weave_mix))))

    for lane_index in range(family_a):
        add_rib_strip(tris, p, lane_index, +1.0)

    for lane_index in range(family_b):
        add_rib_strip(tris, p, lane_index, -1.0)

    if p.membrane > 0.001:
        skin = LampParams(**vars(p))
        skin.weave_amp *= 0.28
        skin.weave_gap *= max(0.0, 1.0 - p.perforation)
        skin.thickness = max(0.38, p.thickness * max(0.18, p.membrane * 0.48))
        skin.inner_follow = min(0.12, p.inner_follow * 0.5)
        tris.extend(make_mesh_solid(skin))

    return tris


def make_mesh(params: LampParams):
    return make_mesh_solid(params)


def main():
    ap = argparse.ArgumentParser(description="Lampgen V4 -> STL (safe woven shell)")
    ap.add_argument("--out", default="out_lamps", help="Output folder")
    ap.add_argument("--count", type=int, default=1, help="How many models")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")

    ap.add_argument("--height", type=float, default=190.0)
    ap.add_argument("--r-base", type=float, default=40.0)
    ap.add_argument("--thickness", type=float, default=1.45)

    ap.add_argument("--bulb-amp", type=float, default=14.0)
    ap.add_argument("--bulb-count", type=float, default=2.1)
    ap.add_argument("--bulb-phase", type=float, default=0.0)
    ap.add_argument("--taper", type=float, default=0.05)

    ap.add_argument("--weave-amp", type=float, default=0.95)
    ap.add_argument("--weave-theta", type=float, default=32.0)
    ap.add_argument("--weave-pitch", type=float, default=42.0)
    ap.add_argument("--weave-mix", type=float, default=0.5)
    ap.add_argument("--weave-round", type=float, default=0.12)
    ap.add_argument("--seam-twist", type=float, default=0.012)
    ap.add_argument("--strand-width", type=float, default=0.28)
    ap.add_argument("--weave-gap", type=float, default=0.30)
    ap.add_argument("--gap-round", type=float, default=0.12)
    ap.add_argument("--mode", choices=["solid", "perforated"], default="solid")
    ap.add_argument("--membrane", type=float, default=0.10)
    ap.add_argument("--perforation", type=float, default=0.0)
    ap.add_argument("--inner-follow", type=float, default=0.18)
    ap.add_argument("--rib-width-scale", type=float, default=0.72)
    ap.add_argument("--rib-thickness", type=float, default=1.25)
    ap.add_argument("--rib-seg-per-pitch", type=int, default=96)

    ap.add_argument("--n-theta", type=int, default=420)
    ap.add_argument("--n-z", type=int, default=520)
    ap.add_argument("--vary", action="store_true", help="Randomize parameters slightly per model")

    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rng = random.Random(args.seed)

    for i in range(args.count):
        p = LampParams(
            height=args.height,
            r_base=args.r_base,
            thickness=args.thickness,
            bulb_amp=args.bulb_amp,
            bulb_count=args.bulb_count,
            bulb_phase=args.bulb_phase,
            taper=args.taper,
            weave_amp=args.weave_amp,
            weave_theta=args.weave_theta,
            weave_pitch=args.weave_pitch,
            weave_mix=args.weave_mix,
            weave_round=args.weave_round,
            seam_twist=args.seam_twist,
            strand_width=args.strand_width,
            weave_gap=args.weave_gap,
            gap_round=args.gap_round,
            membrane=args.membrane,
            perforation=args.perforation,
            inner_follow=args.inner_follow,
            rib_width_scale=args.rib_width_scale,
            rib_thickness=args.rib_thickness,
            rib_seg_per_pitch=args.rib_seg_per_pitch,
            n_theta=args.n_theta,
            n_z=args.n_z,
        )

        if args.vary:
            p.bulb_amp = max(6.0, p.bulb_amp * rng.uniform(0.92, 1.08))
            p.bulb_count = max(1.1, p.bulb_count + rng.uniform(-0.18, 0.18))
            p.taper = clamp(p.taper + rng.uniform(-0.015, 0.02), -0.04, 0.14)
            p.weave_amp = max(0.0, p.weave_amp * rng.uniform(0.9, 1.1))
            p.weave_theta = max(8.0, p.weave_theta + rng.uniform(-2.0, 2.0))
            p.weave_pitch = max(4.0, p.weave_pitch + rng.uniform(-5.0, 5.0))
            p.weave_mix = clamp(p.weave_mix + rng.uniform(-0.05, 0.05), 0.3, 0.7)
            p.weave_round = clamp(p.weave_round + rng.uniform(-0.03, 0.03), 0.0, 0.28)
            p.seam_twist = clamp(p.seam_twist + rng.uniform(-0.006, 0.006), -0.04, 0.04)
            p.strand_width = clamp(p.strand_width + rng.uniform(-0.03, 0.03), 0.16, 0.42)
            p.weave_gap = clamp(p.weave_gap + rng.uniform(-0.06, 0.06), 0.05, 0.55)
            p.gap_round = clamp(p.gap_round + rng.uniform(-0.04, 0.04), 0.0, 0.3)
            p.membrane = clamp(p.membrane + rng.uniform(-0.05, 0.05), 0.0, 0.35)
            p.perforation = clamp(p.perforation + rng.uniform(-0.08, 0.08), 0.0, 1.0)
            p.rib_width_scale = clamp(p.rib_width_scale + rng.uniform(-0.05, 0.05), 0.45, 0.95)
            p.rib_thickness = max(0.6, p.rib_thickness * rng.uniform(0.94, 1.08))

        tris = make_mesh_perforated(p) if args.mode == "perforated" else make_mesh_solid(p)
        name = (
            f"lampgenv4_{args.mode}_h{int(p.height)}_rb{int(p.r_base)}_"
            f"b{p.bulb_count:.2f}_ba{p.bulb_amp:.1f}_"
            f"wa{p.weave_amp:.2f}_wt{int(p.weave_theta)}_wp{p.weave_pitch:.2f}_"
            f"{i:04d}.stl"
        )
        path = os.path.join(args.out, name)
        write_binary_stl(path, tris)
        print(f"[{i+1}/{args.count}] OK -> {path} (tris={len(tris)})")


if __name__ == "__main__":
    main()
