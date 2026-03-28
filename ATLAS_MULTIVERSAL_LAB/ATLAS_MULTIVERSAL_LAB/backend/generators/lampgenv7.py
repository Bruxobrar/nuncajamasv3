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
    header = b"lampgen_v7_sphere_flow".ljust(80, b"\0")
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
    height: float = 170.0
    r_base: float = 72.0
    thickness: float = 1.7
    r_min: float = 12.0

    bulb_amp: float = 10.0
    bulb_count: float = 1.3
    bulb_phase: float = 0.0
    taper: float = 0.02

    seam_count: float = 24.0
    seam_pitch: float = 0.9
    seam_width: float = 4.6
    seam_height: float = 2.2
    seam_softness: float = 1.5
    valley_depth: float = 0.9
    counter_strength: float = 0.25
    counter_phase: float = 0.0
    inner_follow: float = 0.14
    outer_smoothing: float = 0.1
    inner_smoothing: float = 0.72

    flow_sway: float = 0.22
    flow_wave_count: float = 3.4
    opening_radius: float = 24.0
    opening_softness: float = 0.18
    lamp_clearance: float = 46.0

    n_theta: int = 360
    n_z: int = 280


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def smoothstep(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def soft_peak_from_cos(cosine_value: float, width: float) -> float:
    width = clamp(width, 0.04, 0.94)
    threshold = math.cos(math.pi * width)
    if cosine_value <= threshold:
        return 0.0
    t = (cosine_value - threshold) / max(1e-6, 1.0 - threshold)
    return smoothstep(t)


def sanitize_params(p: LampParams) -> LampParams:
    return LampParams(
        height=max(80.0, p.height),
        r_base=max(18.0, p.r_base),
        thickness=max(0.5, p.thickness),
        r_min=max(0.0, p.r_min),
        bulb_amp=max(0.0, p.bulb_amp),
        bulb_count=max(0.4, p.bulb_count),
        bulb_phase=p.bulb_phase,
        taper=clamp(p.taper, -0.16, 0.18),
        seam_count=max(4.0, p.seam_count),
        seam_pitch=clamp(p.seam_pitch, -4.0, 4.0),
        seam_width=clamp(p.seam_width, 0.5, 12.0),
        seam_height=max(0.0, p.seam_height),
        seam_softness=clamp(p.seam_softness, 0.3, 4.0),
        valley_depth=max(0.0, p.valley_depth),
        counter_strength=clamp(p.counter_strength, 0.0, 1.0),
        counter_phase=p.counter_phase,
        inner_follow=clamp(p.inner_follow, 0.0, 0.6),
        outer_smoothing=clamp(p.outer_smoothing, 0.0, 1.0),
        inner_smoothing=clamp(p.inner_smoothing, 0.0, 1.0),
        flow_sway=clamp(p.flow_sway, 0.0, 1.4),
        flow_wave_count=max(0.2, p.flow_wave_count),
        opening_radius=max(6.0, p.opening_radius),
        opening_softness=clamp(p.opening_softness, 0.02, 0.8),
        lamp_clearance=max(8.0, p.lamp_clearance),
        n_theta=max(36, int(p.n_theta)),
        n_z=max(24, int(p.n_z)),
    )


def polar(radius: float, theta: float, z: float):
    return (radius * math.cos(theta), radius * math.sin(theta), z)


def add_quad(tris, v00, v10, v11, v01, flip=False):
    if not flip:
        tris.append((v00, v10, v11))
        tris.append((v00, v11, v01))
    else:
        tris.append((v00, v11, v10))
        tris.append((v00, v01, v11))


def sphere_base_radius(z: float, p: LampParams) -> float:
    u = clamp(z / p.height, 0.0, 1.0)
    zn = 2.0 * u - 1.0
    body = math.sqrt(max(0.0, 1.0 - zn * zn))
    taper_scale = 1.0 - p.taper * (u - 0.5)
    bulge_wave = math.sin(2.0 * math.pi * (p.bulb_count * u + p.bulb_phase))
    bulge_shape = smoothstep(math.sin(math.pi * u))
    bulge_scale = 1.0 + 0.24 * (p.bulb_amp / max(10.0, p.r_base)) * bulge_wave * bulge_shape
    return max(p.r_min + p.thickness + 1.0, p.r_base * body * taper_scale * bulge_scale)


def opening_z(p: LampParams) -> float:
    ratio = clamp(p.opening_radius / max(1.0, p.r_base), 0.08, 0.96)
    zn = -math.sqrt(max(0.0, 1.0 - ratio * ratio))
    return p.height * (zn + 1.0) * 0.5


def flow_displacement(theta: float, z: float, p: LampParams, base_radius: float) -> float:
    u = clamp(z / p.height, 0.0, 1.0)
    open_u = opening_z(p) / p.height
    top_fade = smoothstep(min((1.0 - u) / 0.10, 1.0))
    bottom_band = max(0.04, p.opening_softness + 0.02)
    bottom_fade = smoothstep(min(max(0.0, u - open_u) / bottom_band, 1.0))
    pole_fade = top_fade * bottom_fade

    sway = p.flow_sway * math.sin(2.0 * math.pi * p.flow_wave_count * u + 2.0 * math.pi * p.bulb_phase)
    sway += 0.32 * p.counter_strength * math.sin(2.0 * math.pi * (p.bulb_count * u + p.counter_phase))
    swirl = theta + (2.0 * math.pi * p.seam_pitch * (u - 0.5)) + sway
    phase = p.seam_count * swirl

    width = clamp(p.seam_width / 12.0, 0.08, 0.92)
    ridge = soft_peak_from_cos(math.cos(phase), width)
    ridge2 = soft_peak_from_cos(math.cos(phase + 0.65 * math.sin(2.0 * math.pi * u)), clamp(width * 0.82, 0.06, 0.9))
    ridge_mix = (1.0 - p.counter_strength) * ridge + p.counter_strength * ridge2

    valley = 1.0 - ridge_mix
    raw = p.seam_height * ridge_mix - p.valley_depth * valley
    softened = math.tanh(raw * max(0.35, p.seam_softness))

    radial_room = max(0.8, base_radius - (p.r_min + p.thickness + 0.8))
    amplitude_cap = min(p.seam_height + p.valley_depth + 0.8, radial_room * 0.22, p.thickness * 1.15 + 1.2)
    return amplitude_cap * softened * pole_fade


def cavity_radius(z: float, p: LampParams) -> float:
    u = clamp(z / p.height, 0.0, 1.0)
    center = 0.56
    half_span = 0.46
    t = 1.0 - ((u - center) / half_span) ** 2
    if t <= 0.0:
        return p.r_min
    return max(p.r_min, p.lamp_clearance * math.sqrt(t))


def make_mesh(params: LampParams):
    p = sanitize_params(params)
    z0 = opening_z(p)
    z_top_ring = p.height - max(0.65, p.thickness * 0.7)

    outer = [[None] * p.n_theta for _ in range(p.n_z)]
    inner = [[None] * p.n_theta for _ in range(p.n_z)]

    for iz in range(p.n_z):
        t = iz / (p.n_z - 1)
        z = z0 + (z_top_ring - z0) * t
        for it in range(p.n_theta):
            theta = (2.0 * math.pi * it) / p.n_theta
            base_radius = sphere_base_radius(z, p)
            disp = flow_displacement(theta, z, p, base_radius)
            outer_disp = disp * (1.0 - p.outer_smoothing)
            inner_disp = disp * p.inner_follow * (1.0 - p.inner_smoothing)

            outer_radius = max(p.opening_radius, base_radius + outer_disp)
            shell_inner = outer_radius - p.thickness + inner_disp
            void_radius = cavity_radius(z, p)
            inner_radius = max(p.r_min, min(outer_radius - 0.55, max(shell_inner, void_radius)))
            outer[iz][it] = polar(outer_radius, theta, z)
            inner[iz][it] = polar(inner_radius, theta, z)

    tris = []

    for iz in range(p.n_z - 1):
        for it in range(p.n_theta):
            it2 = (it + 1) % p.n_theta
            add_quad(tris, outer[iz][it], outer[iz][it2], outer[iz + 1][it2], outer[iz + 1][it], flip=False)

    for iz in range(p.n_z - 1):
        for it in range(p.n_theta):
            it2 = (it + 1) % p.n_theta
            add_quad(tris, inner[iz][it], inner[iz + 1][it], inner[iz + 1][it2], inner[iz][it2], flip=False)

    for it in range(p.n_theta):
        it2 = (it + 1) % p.n_theta
        add_quad(tris, outer[0][it], inner[0][it], inner[0][it2], outer[0][it2], flip=False)

    outer_tip = (0.0, 0.0, p.height)
    inner_tip = (0.0, 0.0, p.height - max(0.8, p.thickness))
    top_ring = p.n_z - 1
    for it in range(p.n_theta):
        it2 = (it + 1) % p.n_theta
        tris.append((outer[top_ring][it], outer_tip, outer[top_ring][it2]))
        tris.append((inner[top_ring][it], inner[top_ring][it2], inner_tip))

    return tris


def main():
    ap = argparse.ArgumentParser(description="Lampgen V7 sphere flow lamp -> STL")
    ap.add_argument("--out", default="out_lamps", help="Output folder")
    ap.add_argument("--count", type=int, default=1, help="How many models")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    ap.add_argument("--vary", action="store_true", help="Randomize parameters slightly per model")

    ap.add_argument("--height", type=float, default=170.0)
    ap.add_argument("--r-base", type=float, default=72.0)
    ap.add_argument("--thickness", type=float, default=1.7)
    ap.add_argument("--r-min", type=float, default=12.0)
    ap.add_argument("--bulb-amp", type=float, default=10.0)
    ap.add_argument("--bulb-count", type=float, default=1.3)
    ap.add_argument("--bulb-phase", type=float, default=0.0)
    ap.add_argument("--taper", type=float, default=0.02)
    ap.add_argument("--seam-count", type=float, default=24.0)
    ap.add_argument("--seam-pitch", type=float, default=0.9)
    ap.add_argument("--seam-width", type=float, default=4.6)
    ap.add_argument("--seam-height", type=float, default=2.2)
    ap.add_argument("--seam-softness", type=float, default=1.5)
    ap.add_argument("--valley-depth", type=float, default=0.9)
    ap.add_argument("--counter-strength", type=float, default=0.25)
    ap.add_argument("--counter-phase", type=float, default=0.0)
    ap.add_argument("--inner-follow", type=float, default=0.14)
    ap.add_argument("--outer-smoothing", type=float, default=0.1)
    ap.add_argument("--inner-smoothing", type=float, default=0.72)
    ap.add_argument("--flow-sway", type=float, default=0.22)
    ap.add_argument("--flow-wave-count", type=float, default=3.4)
    ap.add_argument("--opening-radius", type=float, default=24.0)
    ap.add_argument("--opening-softness", type=float, default=0.18)
    ap.add_argument("--lamp-clearance", type=float, default=46.0)
    ap.add_argument("--n-theta", type=int, default=360)
    ap.add_argument("--n-z", type=int, default=280)

    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rng = random.Random(args.seed)

    for index in range(args.count):
        params = LampParams(
            height=args.height,
            r_base=args.r_base,
            thickness=args.thickness,
            r_min=args.r_min,
            bulb_amp=args.bulb_amp,
            bulb_count=args.bulb_count,
            bulb_phase=args.bulb_phase,
            taper=args.taper,
            seam_count=args.seam_count,
            seam_pitch=args.seam_pitch,
            seam_width=args.seam_width,
            seam_height=args.seam_height,
            seam_softness=args.seam_softness,
            valley_depth=args.valley_depth,
            counter_strength=args.counter_strength,
            counter_phase=args.counter_phase,
            inner_follow=args.inner_follow,
            outer_smoothing=args.outer_smoothing,
            inner_smoothing=args.inner_smoothing,
            flow_sway=args.flow_sway,
            flow_wave_count=args.flow_wave_count,
            opening_radius=args.opening_radius,
            opening_softness=args.opening_softness,
            lamp_clearance=args.lamp_clearance,
            n_theta=args.n_theta,
            n_z=args.n_z,
        )

        if args.vary:
            params.seam_pitch += rng.uniform(-0.16, 0.16)
            params.flow_sway = clamp(params.flow_sway + rng.uniform(-0.04, 0.05), 0.0, 1.4)
            params.seam_height = max(0.4, params.seam_height * rng.uniform(0.92, 1.08))
            params.valley_depth = max(0.0, params.valley_depth * rng.uniform(0.9, 1.1))
            params.opening_radius = max(8.0, params.opening_radius * rng.uniform(0.94, 1.06))

        tris = make_mesh(params)
        name = (
            f"lampgenv7_h{int(params.height)}_rb{int(params.r_base)}_"
            f"sc{int(params.seam_count)}_sw{params.flow_sway:.2f}_{index:04d}.stl"
        )
        path = os.path.join(args.out, name)
        write_binary_stl(path, tris)
        print(f"[{index+1}/{args.count}] OK -> {path} (tris={len(tris)})")


if __name__ == "__main__":
    main()
