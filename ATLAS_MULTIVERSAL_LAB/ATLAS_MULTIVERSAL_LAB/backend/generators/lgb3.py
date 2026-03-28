
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
    header = b"lgb_uniform_continuous_woven_lattice".ljust(80, b"\0")
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
    taper: float = 0.05
    bulb_amp: float = 18.0
    bulb_count: float = 2.3
    bulb_phase: float = 0.0

    # textura tejida / enhebrada
    weave_amp: float = 1.10
    weave_theta: float = 38.0
    weave_pitch: float = 56.2
    weave_mix: float = 0.5
    weave_round: float = 0.10
    seam_twist: float = 0.015
    strand_width: float = 0.30   # 0.18 fino / 0.40 ancho
    weave_gap: float = 0.52      # profundidad del hueco visual entre hebras
    gap_round: float = 0.18      # suaviza el hueco para que no se vea seccionado

    thickness: float = 1.10
    r_min: float = 10.0

    n_theta: int = 480
    n_z: int = 620


def clamp(x: float, a: float, b: float) -> float:
    return max(a, min(b, x))


def smoothstep(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def soft_peak_from_cos(c: float, width: float) -> float:
    """
    Convierte cos(phase) en una cresta continua.
    width pequeño = hebra fina.
    width grande = hebra ancha.
    """
    width = clamp(width, 0.02, 0.95)
    threshold = math.cos(math.pi * width)
    if c <= threshold:
        return 0.0
    t = (c - threshold) / (1.0 - threshold)
    return smoothstep(t)


def radius_profile(z: float, p: LampParams) -> float:
    H = p.height
    u = z / H

    taper_factor = 1.0 - p.taper * u
    end_soft = smoothstep(min(u / 0.10, 1.0)) * smoothstep(min((1.0 - u) / 0.10, 1.0))

    bulges = math.sin(2.0 * math.pi * (p.bulb_count * u + p.bulb_phase))
    bulges2 = 0.18 * math.sin(4.0 * math.pi * (p.bulb_count * u + p.bulb_phase) + 0.35)

    r = p.r_base * taper_factor + p.bulb_amp * (0.92 * bulges + bulges2) * end_soft
    return max(p.r_min, r)


def weave_displacement(theta: float, z: float, p: LampParams) -> float:
    """
    Patrón tejido continuo con dos familias de hebras cruzadas.
    En vez de solo inflar "hexágonos", construye crestas para las hebras y
    valles entre ellas, dando el efecto de hueco/enhebrado sin introducir
    bandas horizontales ni etapas visibles.
    """
    H = p.height
    u = z / H

    theta2 = theta + (2.0 * math.pi * p.seam_twist * u)
    phase_z = 2.0 * math.pi * p.weave_pitch * u

    ph1 = p.weave_theta * theta2 + phase_z
    ph2 = -p.weave_theta * theta2 + phase_z

    r1 = soft_peak_from_cos(math.cos(ph1), p.strand_width)
    r2 = soft_peak_from_cos(math.cos(ph2), p.strand_width)

    # mezcla entre ambas familias para que ninguna domine demasiado
    strands = (1.0 - p.weave_mix) * r1 + p.weave_mix * r2
    strands += p.weave_mix * r1 + (1.0 - p.weave_mix) * r2
    strands *= 0.5

    # valle continuo entre hebras: 1 en los huecos, 0 sobre la hebra
    valley = 1.0 - clamp(r1 + r2, 0.0, 1.0)

    # pequeña armónica para evitar una repetición excesivamente "digital"
    micro = 0.5 + 0.5 * math.sin(2.0 * phase_z + 0.35 * math.sin(theta2 * 2.0))
    valley = (1.0 - p.gap_round) * valley + p.gap_round * valley * micro

    # centrado alrededor de 0 para no inflar toda la pieza
    disp = p.weave_amp * strands - p.weave_gap * valley

    # leve redondeo global del cruce
    if p.weave_round > 0.0:
        soft = 0.5 * (math.sin(ph1) + math.sin(ph2))
        disp = (1.0 - p.weave_round) * disp + p.weave_round * (disp + 0.18 * p.weave_amp * soft)

    return disp


def make_mesh(p: LampParams):
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
            d = weave_displacement(theta, z, p)

            # Relieve afuera; adentro casi liso pero acompañando el tejido para
            # que no se vuelva translúcidamente "a rayas".
            r_out = max(p.r_min, r0 + d)
            inner_follow = 0.22 * d
            r_in = max(p.r_min, r0 - p.thickness + inner_follow)

            ct = math.cos(theta)
            st = math.sin(theta)

            outer[iz][it] = (r_out * ct, r_out * st, z)
            inner[iz][it] = (r_in * ct, r_in * st, z)

    tris = []

    def add_quad(v00, v10, v11, v01, flip=False):
        if not flip:
            tris.append((v00, v10, v11))
            tris.append((v00, v11, v01))
        else:
            tris.append((v00, v11, v10))
            tris.append((v00, v01, v11))

    for iz in range(nz - 1):
        for it in range(nt):
            it2 = (it + 1) % nt
            add_quad(
                outer[iz][it],
                outer[iz][it2],
                outer[iz + 1][it2],
                outer[iz + 1][it],
                flip=False,
            )

    for iz in range(nz - 1):
        for it in range(nt):
            it2 = (it + 1) % nt
            add_quad(
                inner[iz][it],
                inner[iz + 1][it],
                inner[iz + 1][it2],
                inner[iz][it2],
                flip=False,
            )

    iz = 0
    for it in range(nt):
        it2 = (it + 1) % nt
        o0 = outer[iz][it]
        o1 = outer[iz][it2]
        i0 = inner[iz][it]
        i1 = inner[iz][it2]
        tris.append((o0, i1, i0))
        tris.append((o0, o1, i1))

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
    ap = argparse.ArgumentParser(description="LGB procedural lamp -> STL (woven threaded look)")
    ap.add_argument("--out", default="out_lamps", help="Output folder")
    ap.add_argument("--count", type=int, default=1, help="How many models")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")

    ap.add_argument("--height", type=float, default=200.0)
    ap.add_argument("--r-base", type=float, default=42.0)
    ap.add_argument("--thickness", type=float, default=1.10)

    ap.add_argument("--bulb-amp", type=float, default=18.0)
    ap.add_argument("--bulb-count", type=float, default=2.3)
    ap.add_argument("--bulb-phase", type=float, default=0.0)
    ap.add_argument("--taper", type=float, default=0.05)

    ap.add_argument("--weave-amp", type=float, default=1.10)
    ap.add_argument("--weave-theta", type=float, default=38.0)
    ap.add_argument("--weave-pitch", type=float, default=56.2)
    ap.add_argument("--weave-mix", type=float, default=0.5)
    ap.add_argument("--weave-round", type=float, default=0.10)
    ap.add_argument("--seam-twist", type=float, default=0.015)
    ap.add_argument("--strand-width", type=float, default=0.30)
    ap.add_argument("--weave-gap", type=float, default=0.52)
    ap.add_argument("--gap-round", type=float, default=0.18)

    ap.add_argument("--n-theta", type=int, default=480)
    ap.add_argument("--n-z", type=int, default=620)

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
            n_theta=args.n_theta,
            n_z=args.n_z,
        )

        if args.vary:
            p.bulb_amp = max(8.0, p.bulb_amp * rng.uniform(0.85, 1.15))
            p.bulb_count = max(1.5, p.bulb_count + rng.uniform(-0.25, 0.25))
            p.taper = clamp(p.taper + rng.uniform(-0.02, 0.03), 0.0, 0.18)

            p.weave_amp = clamp(p.weave_amp * rng.uniform(0.90, 1.10), 0.7, 1.8)
            p.weave_theta = clamp(p.weave_theta + rng.uniform(-3.0, 3.0), 24.0, 48.0)
            p.weave_pitch = clamp(p.weave_pitch + rng.uniform(-6.0, 6.0), 28.0, 72.0)
            p.weave_mix = clamp(p.weave_mix + rng.uniform(-0.08, 0.08), 0.35, 0.65)
            p.weave_round = clamp(p.weave_round + rng.uniform(-0.05, 0.05), 0.0, 0.25)
            p.seam_twist = clamp(p.seam_twist + rng.uniform(-0.008, 0.008), 0.0, 0.05)
            p.strand_width = clamp(p.strand_width + rng.uniform(-0.04, 0.04), 0.18, 0.42)
            p.weave_gap = clamp(p.weave_gap + rng.uniform(-0.08, 0.08), 0.20, 0.85)
            p.gap_round = clamp(p.gap_round + rng.uniform(-0.04, 0.04), 0.0, 0.35)

        tris = make_mesh(p)

        name = (
            f"lgb_h{int(p.height)}_rb{int(p.r_base)}_"
            f"b{p.bulb_count:.2f}_ba{p.bulb_amp:.1f}_"
            f"wa{p.weave_amp:.2f}_wt{int(p.weave_theta)}_wp{p.weave_pitch:.2f}_"
            f"sw{p.strand_width:.2f}_wg{p.weave_gap:.2f}_"
            f"{i:04d}.stl"
        )
        path = os.path.join(args.out, name)
        write_binary_stl(path, tris)
        print(f"[{i+1}/{args.count}] OK -> {path}  (tris={len(tris)})")


if __name__ == "__main__":
    main()
