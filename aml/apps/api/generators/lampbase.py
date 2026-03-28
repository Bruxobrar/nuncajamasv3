import argparse
import math
import os
import struct
from dataclasses import dataclass
from typing import List, Tuple


Triangle = Tuple[
    Tuple[float, float, float],
    Tuple[float, float, float],
    Tuple[float, float, float],
]


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


def write_binary_stl(path: str, triangles: List[Triangle]):
    header = b"lamp base with side ears".ljust(80, b"\0")
    with open(path, "wb") as fh:
        fh.write(header)
        fh.write(struct.pack("<I", len(triangles)))
        for v0, v1, v2 in triangles:
            fh.write(struct.pack("<3f", *tri_normal(v0, v1, v2)))
            fh.write(struct.pack("<3f", *v0))
            fh.write(struct.pack("<3f", *v1))
            fh.write(struct.pack("<3f", *v2))
            fh.write(struct.pack("<H", 0))


def polar(r: float, theta: float, z: float):
    return (r * math.cos(theta), r * math.sin(theta), z)


def add_quad(tris: List[Triangle], v00, v10, v11, v01, flip: bool = False):
    if not flip:
        tris.append((v00, v10, v11))
        tris.append((v00, v11, v01))
    else:
        tris.append((v00, v11, v10))
        tris.append((v00, v01, v11))


def add_box(tris: List[Triangle], x0: float, x1: float, y0: float, y1: float, z0: float, z1: float):
    p000 = (x0, y0, z0)
    p001 = (x0, y0, z1)
    p010 = (x0, y1, z0)
    p011 = (x0, y1, z1)
    p100 = (x1, y0, z0)
    p101 = (x1, y0, z1)
    p110 = (x1, y1, z0)
    p111 = (x1, y1, z1)

    add_quad(tris, p000, p100, p110, p010)
    add_quad(tris, p001, p011, p111, p101)
    add_quad(tris, p000, p001, p101, p100)
    add_quad(tris, p010, p110, p111, p011)
    add_quad(tris, p000, p010, p011, p001)
    add_quad(tris, p100, p101, p111, p110)


def add_full_ring(tris: List[Triangle], r_in: float, r_out: float, z0: float, z1: float, n_theta: int):
    for i in range(n_theta):
        t0 = (2.0 * math.pi * i) / n_theta
        t1 = (2.0 * math.pi * (i + 1)) / n_theta

        o00 = polar(r_out, t0, z0)
        o01 = polar(r_out, t1, z0)
        o10 = polar(r_out, t0, z1)
        o11 = polar(r_out, t1, z1)
        add_quad(tris, o00, o10, o11, o01)

        i00 = polar(r_in, t0, z0)
        i01 = polar(r_in, t1, z0)
        i10 = polar(r_in, t0, z1)
        i11 = polar(r_in, t1, z1)
        add_quad(tris, i00, i01, i11, i10)

        add_quad(tris, o00, o01, i01, i00)
        add_quad(tris, o10, i10, i11, o11)


def add_base_band_with_channel(
    tris: List[Triangle],
    base_radius: float,
    z0: float,
    z1: float,
    channel_half: float,
):
    add_box(tris, -base_radius, -channel_half, -base_radius, base_radius, z0, z1)
    add_box(tris, -channel_half, base_radius, channel_half, base_radius, z0, z1)
    add_box(tris, -channel_half, base_radius, -base_radius, -channel_half, z0, z1)


@dataclass
class LampParams:
    base_radius: float = 52.5
    base_height: float = 10.0
    holder_radius: float = 36.0
    holder_height: float = 35.0
    holder_inner_radius: float = 20.0
    cable_hole_radius: float = 3.0
    cable_exit_width: float = 6.0
    cable_exit_height: float = 4.5
    n_theta: int = 180


def make_mesh(p: LampParams) -> List[Triangle]:
    tris: List[Triangle] = []

    cable_z0 = max(1.0, min(p.base_height - 1.5, p.cable_exit_height - p.cable_hole_radius))
    cable_z1 = max(cable_z0 + 1.0, min(p.base_height - 0.4, p.cable_exit_height + p.cable_hole_radius))
    path_half = p.cable_hole_radius
    add_box(tris, -p.base_radius, p.base_radius, -p.base_radius, p.base_radius, 0.0, cable_z0)

    add_base_band_with_channel(tris, p.base_radius, cable_z0, cable_z1, path_half)
    add_box(tris, -p.base_radius, -path_half, -p.base_radius, p.base_radius, cable_z1, p.base_height)
    add_box(tris, -path_half, p.base_radius, path_half, p.base_radius, cable_z1, p.base_height)
    add_box(tris, -path_half, p.base_radius, -p.base_radius, -path_half, cable_z1, p.base_height)
    add_full_ring(tris, p.holder_inner_radius, p.holder_radius, p.base_height, p.base_height + p.holder_height, p.n_theta)

    return tris


def main():
    ap = argparse.ArgumentParser(description="Genera base de lampara con portalamparas y orejitas laterales.")
    ap.add_argument("--out", default="out_lampbase")
    ap.add_argument("--name", default="lamp_base_socket.stl")
    ap.add_argument("--base-radius", type=float, default=52.5)
    ap.add_argument("--base-height", type=float, default=10.0)
    ap.add_argument("--holder-radius", type=float, default=36.0)
    ap.add_argument("--holder-height", type=float, default=35.0)
    ap.add_argument("--holder-inner-radius", type=float, default=20.0)
    ap.add_argument("--cable-hole-radius", type=float, default=3.0)
    ap.add_argument("--cable-exit-width", type=float, default=6.0)
    ap.add_argument("--cable-exit-height", type=float, default=4.5)
    ap.add_argument("--n-theta", type=int, default=180)
    args = ap.parse_args()

    params = LampParams(
        base_radius=args.base_radius,
        base_height=args.base_height,
        holder_radius=args.holder_radius,
        holder_height=args.holder_height,
        holder_inner_radius=args.holder_inner_radius,
        cable_hole_radius=args.cable_hole_radius,
        cable_exit_width=args.cable_exit_width,
        cable_exit_height=args.cable_exit_height,
        n_theta=args.n_theta,
    )

    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, args.name)
    triangles = make_mesh(params)
    write_binary_stl(out_path, triangles)
    print(f"OK -> {out_path} (tris={len(triangles)})")


if __name__ == "__main__":
    main()
