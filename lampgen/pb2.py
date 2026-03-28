import argparse
import math
import os
import random
import struct
from dataclasses import dataclass
from typing import List, Tuple


# -------------------------------------------------
# STL binary writer
# -------------------------------------------------

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
    header = b"pb2 seam lattice lamp".ljust(80, b"\0")
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


# -------------------------------------------------
# Params
# -------------------------------------------------

@dataclass
class LampParams:
    # overall shape
    height: float = 150.0
    r_base: float = 35.0
    taper: float = 0.04
    bulb_amp: float = 7.0
    bulb_count: float = 2.0
    bulb_phase: float = 0.0

    # shell
    thickness: float = 1.6
    r_min: float = 10.0

    # seam system
    seam_count: int = 18          # how many main seam lanes around the body
    seam_pitch: float = 2.8       # turns across the height
    seam_width: float = 4.0       # mm, visual width of one seam
    seam_height: float = 1.6      # mm, how much it rises
    seam_softness: float = 2.2    # bigger = harder ridge
    valley_depth: float = 0.55    # mm, makes "pseudo holes"

    # secondary family
    counter_strength: float = 0.22
    counter_phase: float = 0.5    # offset between families in lane spacing

    # translucency control
    inner_follow: float = 0.18    # 0 = constant inner shell, 1 = same as outer
                                  # 0.15-0.25 is a nice compromise

    # resolution
    n_theta: int = 360
    n_z: int = 260


# -------------------------------------------------
# Shape profile
# -------------------------------------------------

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


# -------------------------------------------------
# New seam logic
# -------------------------------------------------

def wrap_angle(a: float) -> float:
    """Wrap to [-pi, pi]."""
    while a > math.pi:
        a -= 2.0 * math.pi
    while a < -math.pi:
        a += 2.0 * math.pi
    return a

def ridge_profile(dist_mm: float, width_mm: float, softness: float) -> float:
    """
    dist_mm = distance to seam centerline (in mm over the developed surface)
    width_mm = full visual seam width
    returns 0..1
    """
    half_w = max(0.001, width_mm * 0.5)
    if dist_mm >= half_w:
        return 0.0

    # 1 at center, 0 at edge
    x = 1.0 - (dist_mm / half_w)

    # sharpened raised curve
    return pow(x, softness)

def seam_family(theta: float, z: float, r0: float, p: LampParams, direction: float, phase_offset: float) -> float:
    """
    Return the strongest seam ridge from one family at this point.
    Seams are defined as helicoidal centerlines distributed around the circumference.
    """
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
    Main visual engine:
    - dominant seam family
    - weaker counter family
    - valleys between seams to fake "almost holes"
    """
    r0 = radius_profile(z, p)

    # family A
    a = seam_family(theta, z, r0, p, direction=+1.0, phase_offset=0.0)

    # family B, weaker and offset
    b = seam_family(theta, z, r0, p, direction=-1.0, phase_offset=p.counter_phase)

    seam_signal = a + p.counter_strength * b
    seam_signal = max(0.0, min(1.0, seam_signal))

    # Positive ridge + shallow valley between ridges
    # This creates the "looks like holes but isn't" feel
    d = (p.seam_height * seam_signal) - (p.valley_depth * (1.0 - seam_signal))

    return d


# -------------------------------------------------
# Mesh
# -------------------------------------------------

def make_mesh(p: LampParams):
    """
    Outer shell = base profile + seam field
    Inner shell = follows a fraction of seam field to preserve translucency better
    """
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

            x_out = r_out * math.cos(theta)
            y_out = r_out * math.sin(theta)

            x_in = r_in * math.cos(theta)
            y_in = r_in * math.sin(theta)

            outer[iz][it] = (x_out, y_out, z)
            inner[iz][it] = (x_in, y_in, z)

    tris = []

    def add_quad(v00, v10, v11, v01, flip=False):
        if not flip:
            tris.append((v00, v10, v11))
            tris.append((v00, v11, v01))
        else:
            tris.append((v00, v11, v10))
            tris.append((v00, v01, v11))

    # outer
    for iz in range(nz - 1):
        for it in range(nt):
            it2 = (it + 1) % nt
            add_quad(
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


# -------------------------------------------------
# CLI
# -------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="PB2 - seam-driven lamp generator")

    ap.add_argument("--out", default="out_pb2", help="Output folder")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--seed", type=int, default=42)

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
    ap.add_argument("--inner-follow", type=float, default=0.18)

    # res
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
            inner_follow=args.inner_follow,
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
            p.valley_depth = max(0.2, min(1.0, p.valley_depth * rng.uniform(0.9, 1.1)))

        tris = make_mesh(p)

        name = (
            f"pb2_h{int(p.height)}_rb{int(p.r_base)}_"
            f"sc{p.seam_count}_sp{p.seam_pitch:.2f}_"
            f"sw{p.seam_width:.2f}_sh{p.seam_height:.2f}_"
            f"{i:04d}.stl"
        )
        path = os.path.join(args.out, name)
        write_binary_stl(path, tris)

        print(f"[{i+1}/{args.count}] OK -> {path}  (tris={len(tris)})")


if __name__ == "__main__":
    main()