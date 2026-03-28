import argparse
import math
import os
import random
import struct
from dataclasses import dataclass
from typing import List, Tuple


# -----------------------------
# STL (binary) writer utilities
# -----------------------------

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
    header = b"lampgen_v1 basket weave".ljust(80, b"\0")
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
# Procedural lamp generator
# -----------------------------

@dataclass
class LampParams:
    height: float = 200.0
    r_base: float = 42.0
    taper: float = 0.08
    bulb_amp: float = 12.0
    bulb_count: float = 2.5
    bulb_phase: float = 0.0

    weave_amp: float = 0.9
    weave_theta: float = 24.0
    weave_pitch: float = 3.2
    weave_mix: float = 0.5

    thickness: float = 1.6
    r_min: float = 10.0

    n_theta: int = 256
    n_z: int = 220


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def radius_profile(z: float, p: LampParams) -> float:
    """Base bulbous radius profile (no weave)."""
    H = p.height
    u = z / H

    taper_factor = 1.0 - p.taper * u
    bulges = math.sin(2.0 * math.pi * (p.bulb_count * u + p.bulb_phase))

    end_soft = smoothstep(min(u / 0.08, 1.0)) * smoothstep(min((1.0 - u) / 0.08, 1.0))

    r = p.r_base * taper_factor + p.bulb_amp * bulges * end_soft
    return max(p.r_min, r)


def weave_displacement(theta: float, z: float, p: LampParams) -> float:
    """
    Basket / wicker weave displacement.
    Incluye:
    - dos familias diagonales
    - shape de fibra tipo paja
    - micro irregularidad
    - seam camouflage suave
    """
    H = p.height
    u = z / H

    # Seam camouflage suave: apenas rota el patrón en la zona media
    layer_twist = 0.05 * math.sin(u * math.pi)
    theta = theta + layer_twist

    # Qué tan "fibra" se ve la paja
    weave_sharp = 1.7

    # Dos direcciones
    a = abs(math.sin(p.weave_theta * theta + (p.weave_pitch * 2.0 * math.pi) * u))
    b = abs(math.sin(-p.weave_theta * theta + (p.weave_pitch * 2.0 * math.pi) * u))

    a = pow(a, weave_sharp)
    b = pow(b, weave_sharp)

    mix = p.weave_mix
    s = (1.0 - mix) * a + mix * b

    # Segunda armónica para redondear las fibras
    s2 = abs(math.sin(2.0 * p.weave_theta * theta + 2.0 * (p.weave_pitch * 2.0 * math.pi) * u))
    s2 = pow(s2, 1.3)

    s = 0.78 * s + 0.22 * s2

    # Micro irregularidad orgánica
    micro = 0.12 * math.sin((u * 2.0 * math.pi) * 7.0 + 0.6 * math.sin(theta * 3.0))
    s = s + micro

    # Centrar para tener crestas y valles
    s = s - 0.55

    return p.weave_amp * s


def make_mesh(p: LampParams):
    """
    Build a hollow shell:
    - Outer surface: profile + weave displacement
    - Inner surface: profile - thickness
    - Caps: connect outer and inner rims at bottom & top
    """
    H = p.height
    nt = p.n_theta
    nz = p.n_z

    outer = [[None] * nt for _ in range(nz)]
    inner = [[None] * nt for _ in range(nz)]

    for iz in range(nz):
        z = (H * iz) / (nz - 1)
        r0 = radius_profile(z, p)
        r_in = max(p.r_min, r0 - p.thickness)

        for it in range(nt):
            theta = (2.0 * math.pi * it) / nt

            d = weave_displacement(theta, z, p)
            r_out = max(p.r_min, r0 + d)

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

    # Outer surface
    for iz in range(nz - 1):
        for it in range(nt):
            it2 = (it + 1) % nt
            v00 = outer[iz][it]
            v10 = outer[iz][it2]
            v11 = outer[iz + 1][it2]
            v01 = outer[iz + 1][it]
            add_quad(v00, v10, v11, v01, flip=False)

    # Inner surface
    for iz in range(nz - 1):
        for it in range(nt):
            it2 = (it + 1) % nt
            v00 = inner[iz][it]
            v10 = inner[iz + 1][it]
            v11 = inner[iz + 1][it2]
            v01 = inner[iz][it2]
            add_quad(v00, v10, v11, v01, flip=False)

    # Bottom cap
    iz = 0
    for it in range(nt):
        it2 = (it + 1) % nt
        o0 = outer[iz][it]
        o1 = outer[iz][it2]
        i0 = inner[iz][it]
        i1 = inner[iz][it2]
        tris.append((o0, i1, i0))
        tris.append((o0, o1, i1))

    # Top cap
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


# -----------------------------
# CLI
# -----------------------------

def main():
    ap = argparse.ArgumentParser(description="Procedural lamp head generator V1 -> STL (basket weave)")
    ap.add_argument("--out", default="out_lamps", help="Output folder")
    ap.add_argument("--count", type=int, default=1, help="How many models")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")

    # Core size
    ap.add_argument("--height", type=float, default=200.0)
    ap.add_argument("--r-base", type=float, default=42.0)
    ap.add_argument("--thickness", type=float, default=1.6)

    # Bulbs
    ap.add_argument("--bulb-amp", type=float, default=12.0)
    ap.add_argument("--bulb-count", type=float, default=2.5)
    ap.add_argument("--bulb-phase", type=float, default=0.0)
    ap.add_argument("--taper", type=float, default=0.08)

    # Weave texture
    ap.add_argument("--weave-amp", type=float, default=0.9)
    ap.add_argument("--weave-theta", type=float, default=24.0)
    ap.add_argument("--weave-pitch", type=float, default=3.2)
    ap.add_argument("--weave-mix", type=float, default=0.5)

    # Resolution
    ap.add_argument("--n-theta", type=int, default=256)
    ap.add_argument("--n-z", type=int, default=220)

    # Variation
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
            n_theta=args.n_theta,
            n_z=args.n_z,
        )

        if args.vary:
            p.bulb_amp = max(6.0, p.bulb_amp * rng.uniform(0.75, 1.25))
            p.bulb_count = max(1.5, p.bulb_count + rng.uniform(-0.6, 0.6))
            p.taper = max(0.0, min(0.25, p.taper + rng.uniform(-0.04, 0.06)))

            p.weave_amp = max(0.3, min(1.6, p.weave_amp * rng.uniform(0.7, 1.35)))
            p.weave_theta = max(14.0, min(60.0, p.weave_theta + rng.uniform(-6.0, 10.0)))
            p.weave_pitch = max(1.0, min(6.5, p.weave_pitch + rng.uniform(-0.8, 1.0)))
            p.weave_mix = max(0.2, min(0.8, p.weave_mix + rng.uniform(-0.15, 0.15)))

        tris = make_mesh(p)

        name = (
            f"basket_h{int(p.height)}_rb{int(p.r_base)}_"
            f"b{p.bulb_count:.2f}_ba{p.bulb_amp:.1f}_"
            f"wa{p.weave_amp:.2f}_wt{int(p.weave_theta)}_wp{p.weave_pitch:.2f}_"
            f"{i:04d}.stl"
        )
        path = os.path.join(args.out, name)
        write_binary_stl(path, tris)

        print(f"[{i+1}/{args.count}] OK -> {path}  (tris={len(tris)})")


if __name__ == "__main__":
    main()