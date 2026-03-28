import argparse
import math
import os
import random
import struct
from dataclasses import dataclass
from typing import List, Tuple


# =========================================================
# STL binary writer
# =========================================================

def vec_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def vec_cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )

def vec_norm(v):
    l = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if l == 0:
        return (0.0, 0.0, 0.0)
    return (v[0] / l, v[1] / l, v[2] / l)

def tri_normal(v0, v1, v2):
    e1 = vec_sub(v1, v0)
    e2 = vec_sub(v2, v0)
    return vec_norm(vec_cross(e1, e2))

def write_binary_stl(path: str, triangles: List[Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]]):
    header = b"pb3 seam engine solid/perforated".ljust(80, b"\0")
    with open(path, "wb") as f:
        f.write(header)
        f.write(struct.pack("<I", len(triangles)))
        for (v0, v1, v2) in triangles:
            n = tri_normal(v0, v1, v2)
            f.write(struct.pack("<3f", *n))
            f.write(struct.pack("<3f", *v0))
            f.write(struct.pack("<3f", *v1))
            f.write(struct.pack("<3f", *v2))
            f.write(struct.pack("<H", 0))


# =========================================================
# Params
# =========================================================

@dataclass
class LampParams:
    # overall shape
    height: float = 150.0
    r_base: float = 35.0
    taper: float = 0.04
    bulb_amp: float = 7.0
    bulb_count: float = 2.0
    bulb_phase: float = 0.0

    # shell / structure thickness
    thickness: float = 1.6
    r_min: float = 10.0

    # seam engine
    seam_count: int = 18
    seam_pitch: float = 2.8
    seam_width: float = 4.0       # mm visual width
    seam_height: float = 1.6      # mm outward height
    seam_softness: float = 2.2    # ridge sharpness
    valley_depth: float = 0.55    # mm inward valley
    counter_strength: float = 0.22
    counter_phase: float = 0.5

    # membrane control for solid mode
    membrane: float = 0.35        # 1.0 = much skin, 0.0 = very little skin
    perforation: float = 0.0      # 0 = no perforation, 1 = max opening tendency
    inner_follow: float = 0.18    # how much inner wall follows the seam field

    # perforated mode
    rib_width_scale: float = 0.72     # 0.5..1.0, width relative to seam_width
    rib_thickness: float = 1.2        # structural thickness for perforated ribs
    rib_seg_per_pitch: int = 90

    # resolution
    n_theta: int = 360
    n_z: int = 260


# =========================================================
# Base profile
# =========================================================

def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

def radius_profile(z: float, p: LampParams) -> float:
    H = p.height
    u = z / H

    taper_factor = 1.0 - p.taper * u
    bulges = math.sin(2.0 * math.pi * (p.bulb_count * u + p.bulb_phase))
    end_soft = smoothstep(min(u / 0.08, 1.0)) * smoothstep(min((1.0 - u) / 0.08, 1.0))

    r = p.r_base * taper_factor + p.bulb_amp * bulges * end_soft
    return max(p.r_min, r)


# =========================================================
# Solid mode seam field
# =========================================================

def wrap_angle(a: float) -> float:
    while a > math.pi:
        a -= 2.0 * math.pi
    while a < -math.pi:
        a += 2.0 * math.pi
    return a

def ridge_profile(dist_mm: float, width_mm: float, softness: float) -> float:
    half_w = max(0.001, width_mm * 0.5)
    if dist_mm >= half_w:
        return 0.0
    x = 1.0 - (dist_mm / half_w)
    return pow(x, softness)

def seam_family(theta: float, z: float, r0: float, p: LampParams, direction: float, phase_offset: float) -> float:
    H = p.height
    u = z / H
    best = 0.0

    lane_spacing = (2.0 * math.pi) / p.seam_count

    for k in range(p.seam_count):
        base_theta = k * lane_spacing + phase_offset * lane_spacing
        center = base_theta + direction * (p.seam_pitch * 2.0 * math.pi) * u

        dtheta = wrap_angle(theta - center)
        dist_mm = abs(dtheta) * r0

        ridge = ridge_profile(dist_mm, p.seam_width, p.seam_softness)
        if ridge > best:
            best = ridge

    return best

def seam_displacement(theta: float, z: float, p: LampParams) -> float:
    """
    Solid mode field:
    - ridges where seam ribs are
    - valleys between them
    - membrane controls how much valley survives
    - perforation can push valleys deeper even in solid mode
    """
    r0 = radius_profile(z, p)

    a = seam_family(theta, z, r0, p, direction=+1.0, phase_offset=0.0)
    b = seam_family(theta, z, r0, p, direction=-1.0, phase_offset=p.counter_phase)

    seam_signal = a + p.counter_strength * b
    seam_signal = max(0.0, min(1.0, seam_signal))

    # membrane floor:
    # seam_signal near 0 means valley
    valley_strength = (1.0 - seam_signal)

    # more membrane = less valley collapse
    membrane_floor = p.membrane

    # perforation tendency increases valley depth even in solid mode
    effective_valley = p.valley_depth * (1.0 + 1.6 * p.perforation)

    d = (p.seam_height * seam_signal) - effective_valley * max(0.0, valley_strength - membrane_floor)
    return d


# =========================================================
# Mesh helpers
# =========================================================

def polar(r: float, theta: float, z: float):
    return (r * math.cos(theta), r * math.sin(theta), z)

def add_quad(tris, v00, v10, v11, v01, flip=False):
    if not flip:
        tris.append((v00, v10, v11))
        tris.append((v00, v11, v01))
    else:
        tris.append((v00, v11, v10))
        tris.append((v00, v01, v11))


# =========================================================
# Solid mode mesh
# =========================================================

def make_mesh_solid(p: LampParams):
    H = p.height
    nt = p.n_theta
    nz = p.n_z

    outer = [[None] * nt for _ in range(nz)]
    inner = [[None] * nt for _ in range(nz)]

    for iz in range(nz):
        z = (H * iz) / (nz - 1)
        r0 = radius_profile(z, p)

        for it in range(nt):
            theta = (2.0 * math.pi * it) / nt

            d = seam_displacement(theta, z, p)

            r_out = max(p.r_min, r0 + d)
            r_in = max(p.r_min, r0 + (p.inner_follow * d) - p.thickness)

            outer[iz][it] = polar(r_out, theta, z)
            inner[iz][it] = polar(r_in, theta, z)

    tris = []

    # outer
    for iz in range(nz - 1):
        for it in range(nt):
            it2 = (it + 1) % nt
            add_quad(
                tris,
                outer[iz][it],
                outer[iz][it2],
                outer[iz + 1][it2],
                outer[iz + 1][it],
                flip=False
            )

    # inner
    for iz in range(nz - 1):
        for it in range(nt):
            it2 = (it + 1) % nt
            add_quad(
                tris,
                inner[iz][it],
                inner[iz + 1][it],
                inner[iz + 1][it2],
                inner[iz][it2],
                flip=False
            )

    # bottom cap
    iz = 0
    for it in range(nt):
        it2 = (it + 1) % nt
        o0 = outer[iz][it]
        o1 = outer[iz][it2]
        i0 = inner[iz][it]
        i1 = inner[iz][it2]
        tris.append((o0, i1, i0))
        tris.append((o0, o1, i1))

    # top cap
    iz = nz - 1
    for it in range(nt):
        it2 = (it + 1) % nt
        o0 = outer[iz][it]
        o1 = outer[iz][it2]
        i0 = inner[iz][it]
        i1 = inner[iz][it2]
        tris.append((o0, i0, i1))
        tris.append((o0, i1, o1))

    return tris


# =========================================================
# Perforated mode: actual ribs only
# =========================================================

def add_rib_strip(tris, p: LampParams, theta0: float, direction: float, phase_offset: float):
    """
    One helicoidal rib as a closed ribbon solid.
    This creates REAL openings between ribs.
    """
    H = p.height
    total_segs = max(p.n_z, int(abs(p.seam_pitch) * p.rib_seg_per_pitch))
    nz = total_segs + 1

    rib_width = max(0.5, p.seam_width * p.rib_width_scale)

    for iz in range(nz - 1):
        z0 = (H * iz) / (nz - 1)
        z1 = (H * (iz + 1)) / (nz - 1)

        u0 = z0 / H
        u1 = z1 / H

        r0 = radius_profile(z0, p) + p.seam_height * 0.35
        r1 = radius_profile(z1, p) + p.seam_height * 0.35

        th_c0 = theta0 + phase_offset + direction * (p.seam_pitch * 2.0 * math.pi) * u0
        th_c1 = theta0 + phase_offset + direction * (p.seam_pitch * 2.0 * math.pi) * u1

        dth0 = rib_width / max(p.r_min, r0)
        dth1 = rib_width / max(p.r_min, r1)

        th0a = th_c0 - dth0 * 0.5
        th0b = th_c0 + dth0 * 0.5
        th1a = th_c1 - dth1 * 0.5
        th1b = th_c1 + dth1 * 0.5

        ro0 = r0
        ro1 = r1
        ri0 = max(p.r_min, r0 - p.rib_thickness)
        ri1 = max(p.r_min, r1 - p.rib_thickness)

        o00 = polar(ro0, th0a, z0)
        o01 = polar(ro0, th0b, z0)
        o10 = polar(ro1, th1a, z1)
        o11 = polar(ro1, th1b, z1)

        i00 = polar(ri0, th0a, z0)
        i01 = polar(ri0, th0b, z0)
        i10 = polar(ri1, th1a, z1)
        i11 = polar(ri1, th1b, z1)

        # outer face
        add_quad(tris, o00, o10, o11, o01, flip=False)
        # inner face
        add_quad(tris, i00, i01, i11, i10, flip=False)
        # sides
        add_quad(tris, o00, i00, i10, o10, flip=False)
        add_quad(tris, o01, o11, i11, i01, flip=False)

        # caps
        if iz == 0:
            add_quad(tris, o00, o01, i01, i00, flip=False)
        if iz == nz - 2:
            add_quad(tris, o10, i10, i11, o11, flip=False)

def make_mesh_perforated(p: LampParams):
    """
    Build only seam ribs. Real openings remain between them.
    membrane can optionally add a very thin backing shell if > 0.
    """
    tris = []

    lane_spacing = (2.0 * math.pi) / p.seam_count
    phase_offset_b = p.counter_phase * lane_spacing

    # family A
    for k in range(p.seam_count):
        theta0 = k * lane_spacing
        add_rib_strip(tris, p, theta0, direction=+1.0, phase_offset=0.0)

    # family B
    family_b_count = max(1, int(round(p.seam_count * max(0.1, p.counter_strength))))
    # keep same count visually by default if counter_strength is notable
    if p.counter_strength >= 0.12:
        family_b_count = p.seam_count

    for k in range(family_b_count):
        theta0 = k * lane_spacing
        add_rib_strip(tris, p, theta0, direction=-1.0, phase_offset=phase_offset_b)

    # Optional ultra-thin membrane backing
    # membrane in perforated mode means "keep some skin"
    if p.membrane > 0.001:
        skin_p = LampParams(**vars(p))
        skin_p.thickness = max(0.35, p.thickness * max(0.15, p.membrane * 0.5))
        skin_p.seam_height = p.seam_height * 0.25
        skin_p.valley_depth = p.valley_depth * (1.0 + p.perforation)
        skin_p.inner_follow = 0.05
        tris.extend(make_mesh_solid(skin_p))

    return tris


# =========================================================
# CLI
# =========================================================

def main():
    ap = argparse.ArgumentParser(description="PB3 seam engine with solid/perforated modes")

    ap.add_argument("--out", default="out_pb3", help="Output folder")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--mode", choices=["solid", "perforated"], default="solid")

    # shape
    ap.add_argument("--height", type=float, default=150.0)
    ap.add_argument("--r-base", type=float, default=35.0)
    ap.add_argument("--thickness", type=float, default=1.6)
    ap.add_argument("--bulb-amp", type=float, default=7.0)
    ap.add_argument("--bulb-count", type=float, default=2.0)
    ap.add_argument("--bulb-phase", type=float, default=0.0)
    ap.add_argument("--taper", type=float, default=0.04)

    # seam engine
    ap.add_argument("--seam-count", type=int, default=18)
    ap.add_argument("--seam-pitch", type=float, default=2.8)
    ap.add_argument("--seam-width", type=float, default=4.0)
    ap.add_argument("--seam-height", type=float, default=1.6)
    ap.add_argument("--seam-softness", type=float, default=2.2)
    ap.add_argument("--valley-depth", type=float, default=0.55)
    ap.add_argument("--counter-strength", type=float, default=0.22)
    ap.add_argument("--counter-phase", type=float, default=0.5)

    # skin/opening controls
    ap.add_argument("--membrane", type=float, default=0.35)
    ap.add_argument("--perforation", type=float, default=0.0)
    ap.add_argument("--inner-follow", type=float, default=0.18)

    # perforated rib controls
    ap.add_argument("--rib-width-scale", type=float, default=0.72)
    ap.add_argument("--rib-thickness", type=float, default=1.2)
    ap.add_argument("--rib-seg-per-pitch", type=int, default=90)

    # resolution
    ap.add_argument("--n-theta", type=int, default=360)
    ap.add_argument("--n-z", type=int, default=260)

    # variation
    ap.add_argument("--vary", action="store_true")

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
            seam_count=args.seam_count,
            seam_pitch=args.seam_pitch,
            seam_width=args.seam_width,
            seam_height=args.seam_height,
            seam_softness=args.seam_softness,
            valley_depth=args.valley_depth,
            counter_strength=args.counter_strength,
            counter_phase=args.counter_phase,
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
            p.bulb_amp = max(5.0, p.bulb_amp * rng.uniform(0.85, 1.15))
            p.bulb_count = max(1.6, p.bulb_count + rng.uniform(-0.25, 0.25))
            p.seam_count = int(max(10, min(28, p.seam_count + rng.randint(-2, 2))))
            p.seam_pitch = max(1.8, min(4.5, p.seam_pitch + rng.uniform(-0.35, 0.35)))
            p.seam_width = max(2.2, min(6.0, p.seam_width * rng.uniform(0.9, 1.1)))
            p.seam_height = max(0.8, min(2.4, p.seam_height * rng.uniform(0.9, 1.1)))
            p.valley_depth = max(0.2, min(1.2, p.valley_depth * rng.uniform(0.9, 1.1)))

        if args.mode == "solid":
            tris = make_mesh_solid(p)
        else:
            tris = make_mesh_perforated(p)

        name = (
            f"pb3_{args.mode}_h{int(p.height)}_rb{int(p.r_base)}_"
            f"sc{p.seam_count}_sp{p.seam_pitch:.2f}_"
            f"sw{p.seam_width:.2f}_sh{p.seam_height:.2f}_"
            f"m{p.membrane:.2f}_pf{p.perforation:.2f}_"
            f"{i:04d}.stl"
        )
        path = os.path.join(args.out, name)
        write_binary_stl(path, tris)

        print(f"[{i+1}/{args.count}] OK -> {path}  (tris={len(tris)})")


if __name__ == "__main__":
    main()