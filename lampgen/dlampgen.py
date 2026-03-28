import argparse
import math
import os
import random
import struct
from dataclasses import dataclass
from typing import List, Tuple

# -----------------------------
# STL writer (binary)
# -----------------------------

def vec_sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])

def vec_cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

def vec_norm(v):
    l = math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])
    if l == 0:
        return (0.0, 0.0, 0.0)
    return (v[0]/l, v[1]/l, v[2]/l)

def tri_normal(v0, v1, v2):
    e1 = vec_sub(v1, v0)
    e2 = vec_sub(v2, v0)
    return vec_norm(vec_cross(e1, e2))

def write_binary_stl(path: str, triangles: List[Tuple[Tuple[float,float,float], Tuple[float,float,float], Tuple[float,float,float]]]):
    header = b"wire_diamonds_v2 chainlink rombos".ljust(80, b"\0")
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

# -----------------------------
# Geometry helpers
# -----------------------------

def polar(r: float, theta: float, z: float):
    return (r * math.cos(theta), r * math.sin(theta), z)

def add_quad(tris, v00, v10, v11, v01, flip=False):
    # two triangles
    if not flip:
        tris.append((v00, v10, v11))
        tris.append((v00, v11, v01))
    else:
        tris.append((v00, v11, v10))
        tris.append((v00, v01, v11))

# -----------------------------
# Wire diamonds (chain-link) generator
# Idea:
# - Build two families of helical "wires" (ribbons) crossing each other
# - When dense enough, creates diamond holes (rombos) like mesh/chainlink
# - We model each wire as a thin closed ribbon solid (rectangular cross-section)
#   that hugs the cylinder surface, leaving real gaps between wires.
# -----------------------------

@dataclass
class WireParams:
    # Cylinder
    height: float = 200.0
    radius: float = 45.0

    # Diamond / mesh controls
    wires: int = 26               # number of wires per family around circumference
    rotations: float = 6.0        # twists along height (higher => smaller diamonds in Z)
    offset_b: float = 0.5         # offset of family B relative to A (0.5 gives nice diamonds)

    # Wire geometry
    wire_width: float = 2.0       # "flat" width of wire along arc (mm) -> controls hole size
    wire_thickness: float = 1.2   # radial thickness (mm) -> strength
    inner_radius: float = 0.0     # if >0, we also create an inner ring for stiffness (optional)

    # Resolution (smoothness)
    seg_per_rot: int = 110        # segments per helix rotation (bigger = smoother, heavier)
    r_min: float = 10.0

def add_wire_ribbon(tris, p: WireParams, theta0: float, direction: float, phase_u: float):
    """
    Make one helical wire as a closed ribbon solid:
    outer surface at r = radius
    inner surface at r = radius - wire_thickness
    sides close the ribbon.
    """
    H = p.height
    r = p.radius

    total_segs = max(120, int(abs(p.rotations) * p.seg_per_rot))
    nz = total_segs + 1

    for iz in range(nz - 1):
        z0 = (H * iz) / (nz - 1)
        z1 = (H * (iz + 1)) / (nz - 1)
        u0 = z0 / H
        u1 = z1 / H

        # Helix angle centerline
        th_c0 = theta0 + direction * (p.rotations * 2.0 * math.pi) * u0 + (phase_u * 2.0 * math.pi) * u0
        th_c1 = theta0 + direction * (p.rotations * 2.0 * math.pi) * u1 + (phase_u * 2.0 * math.pi) * u1

        # Convert width in mm to delta theta (arc approximation)
        dth = p.wire_width / max(p.r_min, r)

        th0a, th0b = th_c0 - dth/2.0, th_c0 + dth/2.0
        th1a, th1b = th_c1 - dth/2.0, th_c1 + dth/2.0

        ro0 = r
        ro1 = r
        ri0 = max(p.r_min, r - p.wire_thickness)
        ri1 = max(p.r_min, r - p.wire_thickness)

        # outer ring (surface)
        o00 = polar(ro0, th0a, z0)
        o01 = polar(ro0, th0b, z0)
        o10 = polar(ro1, th1a, z1)
        o11 = polar(ro1, th1b, z1)

        # inner ring (thickness)
        i00 = polar(ri0, th0a, z0)
        i01 = polar(ri0, th0b, z0)
        i10 = polar(ri1, th1a, z1)
        i11 = polar(ri1, th1b, z1)

        # Faces
        # outer face
        add_quad(tris, o00, o10, o11, o01, flip=False)
        # inner face
        add_quad(tris, i00, i01, i11, i10, flip=False)
        # side A
        add_quad(tris, o00, i00, i10, o10, flip=False)
        # side B
        add_quad(tris, o01, o11, i11, i01, flip=False)

        # Caps at very bottom and top (so it's watertight)
        if iz == 0:
            add_quad(tris, o00, o01, i01, i00, flip=False)
        if iz == nz - 2:
            add_quad(tris, o10, i10, i11, o11, flip=False)

def build_wire_diamonds(p: WireParams) -> List[Tuple[Tuple[float,float,float], Tuple[float,float,float], Tuple[float,float,float]]]:
    tris = []

    # Two families crossing
    for k in range(p.wires):
        theta0 = (2.0 * math.pi * k) / p.wires

        # Family A
        add_wire_ribbon(tris, p, theta0, direction=+1.0, phase_u=0.0)

        # Family B (offset)
        theta1 = theta0 + (2.0 * math.pi / p.wires) * p.offset_b
        add_wire_ribbon(tris, p, theta1, direction=-1.0, phase_u=0.0)

    return tris

# -----------------------------
# CLI
# -----------------------------

def main():
    ap = argparse.ArgumentParser(description="Wire diamonds cylinder (rombos chain-link) -> STL")

    ap.add_argument("--out", default="out_wire_v2", help="Output folder")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--seed", type=int, default=42)

    # Cylinder
    ap.add_argument("--height", type=float, default=200.0)
    ap.add_argument("--radius", type=float, default=45.0)

    # Diamonds
    ap.add_argument("--wires", type=int, default=26)
    ap.add_argument("--rotations", type=float, default=6.0)
    ap.add_argument("--offset-b", type=float, default=0.5)

    # Wire geometry
    ap.add_argument("--wire-width", type=float, default=2.0)
    ap.add_argument("--wire-thickness", type=float, default=1.2)

    # Resolution
    ap.add_argument("--seg-per-rot", type=int, default=110)

    # Vary
    ap.add_argument("--vary", action="store_true", help="Randomize parameters slightly per model")

    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rng = random.Random(args.seed)

    for i in range(args.count):
        p = WireParams(
            height=args.height,
            radius=args.radius,
            wires=args.wires,
            rotations=args.rotations,
            offset_b=args.offset_b,
            wire_width=args.wire_width,
            wire_thickness=args.wire_thickness,
            seg_per_rot=args.seg_per_rot,
        )

        if args.vary:
            # Controlled variations that keep "rombo mesh" style
            p.wires = int(max(16, min(44, p.wires + rng.randint(-4, 6))))
            p.rotations = max(3.0, min(10.0, p.rotations + rng.uniform(-1.2, 1.4)))
            p.offset_b = max(0.25, min(0.75, p.offset_b + rng.uniform(-0.12, 0.12)))

            p.wire_width = max(1.2, min(3.2, p.wire_width * rng.uniform(0.85, 1.25)))
            p.wire_thickness = max(0.8, min(1.8, p.wire_thickness * rng.uniform(0.9, 1.2)))

        tris = build_wire_diamonds(p)

        name = (
            f"wire_diamonds_h{int(p.height)}_r{int(p.radius)}_"
            f"w{p.wires}_rot{p.rotations:.2f}_"
            f"ww{p.wire_width:.2f}_wt{p.wire_thickness:.2f}_"
            f"{i:04d}.stl"
        )
        path = os.path.join(args.out, name)
        write_binary_stl(path, tris)

        print(f"[{i+1}/{args.count}] OK -> {path}  (tris={len(tris)})")

if __name__ == "__main__":
    main()