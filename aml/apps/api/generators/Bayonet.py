import argparse
import math
import os
import random
import struct
from dataclasses import dataclass
from typing import List, Tuple, Optional

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

def write_binary_stl(path: str, triangles: List[Tuple[Tuple[float,float,float], Tuple[float,float,float], Tuple[float,float,float]]], header_text: bytes):
    header = header_text.ljust(80, b"\0")
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
    if not flip:
        tris.append((v00, v10, v11))
        tris.append((v00, v11, v01))
    else:
        tris.append((v00, v11, v10))
        tris.append((v00, v01, v11))

def clamp(x, a, b): return max(a, min(b, x))

# Build a cylindrical wall segment (ring sector) between theta_a..theta_b
def add_ring_sector(
    tris,
    r_in: float,
    r_out: float,
    z0: float,
    z1: float,
    theta_a: float,
    theta_b: float,
    n_theta: int,
    cap_ends: bool = True
):
    # assumes theta_b > theta_a
    for i in range(n_theta):
        t0 = theta_a + (theta_b - theta_a) * (i / n_theta)
        t1 = theta_a + (theta_b - theta_a) * ((i+1) / n_theta)

        # outer wall
        o00 = polar(r_out, t0, z0)
        o01 = polar(r_out, t1, z0)
        o10 = polar(r_out, t0, z1)
        o11 = polar(r_out, t1, z1)
        add_quad(tris, o00, o10, o11, o01, flip=False)

        # inner wall (flip orientation)
        i00 = polar(r_in, t0, z0)
        i01 = polar(r_in, t1, z0)
        i10 = polar(r_in, t0, z1)
        i11 = polar(r_in, t1, z1)
        add_quad(tris, i00, i01, i11, i10, flip=False)

        # top/bottom faces to make it solid (annulus sector)
        # bottom
        add_quad(tris, o00, o01, i01, i00, flip=False)
        # top
        add_quad(tris, o10, i10, i11, o11, flip=False)

    if cap_ends:
        # cap at theta_a and theta_b (vertical faces closing the sector)
        # theta_a face
        a0o = polar(r_out, theta_a, z0)
        a1o = polar(r_out, theta_a, z1)
        a0i = polar(r_in, theta_a, z0)
        a1i = polar(r_in, theta_a, z1)
        add_quad(tris, a0o, a1o, a1i, a0i, flip=False)

        # theta_b face
        b0o = polar(r_out, theta_b, z0)
        b1o = polar(r_out, theta_b, z1)
        b0i = polar(r_in, theta_b, z0)
        b1i = polar(r_in, theta_b, z1)
        add_quad(tris, b0o, b0i, b1i, b1o, flip=False)

def add_full_ring(tris, r_in, r_out, z0, z1, n_theta=180):
    add_ring_sector(tris, r_in, r_out, z0, z1, 0.0, 2.0*math.pi, n_theta, cap_ends=False)

# A small rectangular-ish lug approximated as a ring sector + thickness
def add_lug(tris, r_base, lug_radial, z0, z1, theta_center, theta_width, n_theta=14):
    ra = r_base
    rb = r_base + lug_radial
    ta = theta_center - theta_width/2
    tb = theta_center + theta_width/2
    add_ring_sector(tris, ra, rb, z0, z1, ta, tb, n_theta, cap_ends=True)

# -----------------------------
# Lamp body generators
# (Basket V1 + Wire diamonds V2)
# Simplified integration: both return triangles for the shell body,
# then we union by appending mount triangles.
# -----------------------------

@dataclass
class BasketParams:
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
    return t*t*(3.0 - 2.0*t)

def basket_radius_profile(z: float, p: BasketParams) -> float:
    H = p.height
    u = z / H
    taper_factor = 1.0 - p.taper * u
    bulges = math.sin(2.0 * math.pi * (p.bulb_count * u + p.bulb_phase))
    end_soft = smoothstep(min(u/0.08, 1.0)) * smoothstep(min((1.0-u)/0.08, 1.0))
    r = p.r_base * taper_factor + p.bulb_amp * bulges * end_soft
    return max(p.r_min, r)

def basket_weave_disp(theta: float, z: float, p: BasketParams) -> float:
    H = p.height
    u = z / H
    weave_sharp = 1.7
    a = abs(math.sin(p.weave_theta * theta + (p.weave_pitch * 2.0 * math.pi) * u))
    b = abs(math.sin(-p.weave_theta * theta + (p.weave_pitch * 2.0 * math.pi) * u))
    a = pow(a, weave_sharp)
    b = pow(b, weave_sharp)
    s = (1.0 - p.weave_mix) * a + p.weave_mix * b
    s2 = abs(math.sin(2.0 * p.weave_theta * theta + 2.0 * (p.weave_pitch * 2.0 * math.pi) * u))
    s2 = pow(s2, 1.3)
    s = 0.78 * s + 0.22 * s2
    micro = 0.12 * math.sin((u * 2.0 * math.pi) * 7.0 + 0.6 * math.sin(theta * 3.0))
    s = (s + micro) - 0.55
    return p.weave_amp * s

def make_basket_shell(p: BasketParams) -> List[Tuple[Tuple[float,float,float], Tuple[float,float,float], Tuple[float,float,float]]]:
    H = p.height
    nt, nz = p.n_theta, p.n_z
    outer = [[None]*nt for _ in range(nz)]
    inner = [[None]*nt for _ in range(nz)]

    for iz in range(nz):
        z = (H * iz) / (nz - 1)
        r0 = basket_radius_profile(z, p)
        r_in = max(p.r_min, r0 - p.thickness)
        for it in range(nt):
            theta = (2.0*math.pi * it) / nt
            d = basket_weave_disp(theta, z, p)
            r_out = max(p.r_min, r0 + d)
            outer[iz][it] = (r_out*math.cos(theta), r_out*math.sin(theta), z)
            inner[iz][it] = (r_in*math.cos(theta), r_in*math.sin(theta), z)

    tris = []

    # outer surface
    for iz in range(nz-1):
        for it in range(nt):
            it2 = (it + 1) % nt
            v00 = outer[iz][it]
            v10 = outer[iz][it2]
            v11 = outer[iz+1][it2]
            v01 = outer[iz+1][it]
            add_quad(tris, v00, v10, v11, v01, flip=False)

    # inner surface
    for iz in range(nz-1):
        for it in range(nt):
            it2 = (it + 1) % nt
            v00 = inner[iz][it]
            v10 = inner[iz+1][it]
            v11 = inner[iz+1][it2]
            v01 = inner[iz][it2]
            add_quad(tris, v00, v10, v11, v01, flip=False)

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

@dataclass
class WireParams:
    height: float = 200.0
    radius: float = 45.0
    wires: int = 26
    rotations: float = 6.0
    offset_b: float = 0.5
    wire_width: float = 2.0
    wire_thickness: float = 1.2
    seg_per_rot: int = 110
    r_min: float = 10.0

def add_wire_ribbon(tris, p: WireParams, theta0: float, direction: float):
    H = p.height
    r = p.radius
    total_segs = max(120, int(abs(p.rotations) * p.seg_per_rot))
    nz = total_segs + 1

    for iz in range(nz - 1):
        z0 = (H * iz) / (nz - 1)
        z1 = (H * (iz + 1)) / (nz - 1)
        u0 = z0 / H
        u1 = z1 / H

        th_c0 = theta0 + direction * (p.rotations * 2.0 * math.pi) * u0
        th_c1 = theta0 + direction * (p.rotations * 2.0 * math.pi) * u1

        dth = p.wire_width / max(p.r_min, r)
        th0a, th0b = th_c0 - dth/2.0, th_c0 + dth/2.0
        th1a, th1b = th_c1 - dth/2.0, th_c1 + dth/2.0

        ro = r
        ri = max(p.r_min, r - p.wire_thickness)

        o00 = polar(ro, th0a, z0)
        o01 = polar(ro, th0b, z0)
        o10 = polar(ro, th1a, z1)
        o11 = polar(ro, th1b, z1)

        i00 = polar(ri, th0a, z0)
        i01 = polar(ri, th0b, z0)
        i10 = polar(ri, th1a, z1)
        i11 = polar(ri, th1b, z1)

        add_quad(tris, o00, o10, o11, o01, flip=False)  # outer
        add_quad(tris, i00, i01, i11, i10, flip=False)  # inner
        add_quad(tris, o00, i00, i10, o10, flip=False)  # side A
        add_quad(tris, o01, o11, i11, i01, flip=False)  # side B

        if iz == 0:
            add_quad(tris, o00, o01, i01, i00, flip=False)
        if iz == nz - 2:
            add_quad(tris, o10, i10, i11, o11, flip=False)

def make_wire_diamonds(p: WireParams) -> List[Tuple[Tuple[float,float,float], Tuple[float,float,float], Tuple[float,float,float]]]:
    tris = []
    for k in range(p.wires):
        theta0 = (2.0 * math.pi * k) / p.wires
        add_wire_ribbon(tris, p, theta0, direction=+1.0)
        theta1 = theta0 + (2.0 * math.pi / p.wires) * p.offset_b
        add_wire_ribbon(tris, p, theta1, direction=-1.0)
    return tris

# -----------------------------
# Bayonet mount generator
# - Female mount on head (recommended)
# - Male mount as a separate adapter (recommended)
# Geometry is built as explicit solids (no booleans):
#   - Female = outer collar segmented + entry windows + internal ledge
#   - Male   = inner spigot ring + 3 lugs
# -----------------------------
@dataclass
class BayonetParams:
    # shared
    n_lugs: int = 3
    twist_deg: float = 70.0          # how much you turn to lock (60..90)
    entry_deg: float = 22.0          # angular size of each entry window
    lug_deg: float = 16.0            # angular size of each lug
    mount_height: float = 14.0       # height of the coupling
    wall: float = 2.4                # collar wall thickness

    # sizes
    socket_id: float = 32.0          # female internal diameter (mm) (fits male OD + clearance)
    clearance: float = 0.30          # radial clearance for FDM

    # locking ledge (female) / lug (male)
    lug_thickness_z: float = 2.2     # thickness in Z of the lug/ledge
    lug_radial: float = 2.0          # how far lug protrudes radially

    # detent (simple bump)
    detent: bool = True
    detent_radial: float = 0.55
    detent_deg: float = 10.0

def add_female_bayonet(tris, bp: BayonetParams, z_base: float, outer_radius_hint: float):
    """
    Female part: a collar with entry windows.
    We model it as a ring wall that is missing in 'entry' regions.
    Inside, we add a ledge ring sector that catches the lugs after twisting.
    """
    z0 = z_base
    z1 = z_base + bp.mount_height

    r_in = bp.socket_id/2.0
    r_out = max(outer_radius_hint, r_in + bp.wall)

    # Build outer collar but leave entry windows:
    lug_step = 2.0*math.pi / bp.n_lugs
    entry_w = math.radians(bp.entry_deg)

    # We'll keep wall everywhere except small windows centered at each lug position
    segments_per_sector = 22

    for i in range(bp.n_lugs):
        c = i * lug_step
        a0 = c + entry_w/2.0
        b0 = c + lug_step - entry_w/2.0
        # sector from a0..b0 (solid), and skip (b0..a0+lug_step) window region
        add_ring_sector(tris, r_in, r_out, z0, z1, a0, b0, segments_per_sector, cap_ends=True)

    # Internal ledge: a thin ring sector near the TOP that catches lugs after twist
    ledge_z0 = z0 + (bp.mount_height - bp.lug_thickness_z)
    ledge_z1 = z0 + bp.mount_height

    # Ledge sits slightly INSIDE so lug can slide under it
    ledge_r_in = r_in
    ledge_r_out = r_in + bp.lug_radial + bp.clearance

    twist = math.radians(bp.twist_deg)
    lug_w = math.radians(bp.lug_deg)

    for i in range(bp.n_lugs):
        # entry center
        c = i * lug_step
        # ledge should start after you twist: place it rotated by +twist from the entry window
        ledge_center = c + twist
        ta = ledge_center - lug_w/2.0
        tb = ledge_center + lug_w/2.0
        add_ring_sector(tris, ledge_r_in, ledge_r_out, ledge_z0, ledge_z1, ta, tb, 14, cap_ends=True)

    # Optional detent bump on the inside near the end-of-twist (adds "click")
    if bp.detent:
        bump_z0 = ledge_z0
        bump_z1 = ledge_z1
        bump_w = math.radians(bp.detent_deg)
        # put detent on lug 0 end position
        det_c = twist + (lug_w * 0.45)
        add_ring_sector(tris, r_in, r_in + bp.detent_radial, bump_z0, bump_z1, det_c - bump_w/2, det_c + bump_w/2, 10, cap_ends=True)

def add_male_bayonet_adapter(tris, bp: BayonetParams, z_base: float, adapter_height: float = 18.0):
    """
    Male adapter: a spigot that goes into the female socket, with external lugs.
    """
    z0 = z_base
    z1 = z_base + adapter_height

    # Spigot outer radius must fit inside female r_in with clearance
    female_r_in = bp.socket_id/2.0
    spigot_r_out = female_r_in - bp.clearance
    spigot_r_in = max(0.0, spigot_r_out - 2.2)  # wall thickness of spigot
    add_full_ring(tris, spigot_r_in, spigot_r_out, z0, z1, n_theta=180)

    # Lugs live near the TOP so they slide under female ledge
    lug_z0 = z_base + (bp.mount_height - bp.lug_thickness_z)
    lug_z1 = z_base + bp.mount_height

    lug_step = 2.0*math.pi / bp.n_lugs
    lug_w = math.radians(bp.lug_deg)

    # Place lugs aligned with entries (centers at 0, 120, 240 deg)
    for i in range(bp.n_lugs):
        c = i * lug_step
        add_lug(tris, spigot_r_out, bp.lug_radial, lug_z0, lug_z1, c, lug_w, n_theta=12)

# -----------------------------
# Assembly
# -----------------------------
def build_head(style: str, seed: int, args) -> Tuple[List[Tuple], float, float]:
    """
    Returns (triangles, height, outer_radius_hint_for_mount)
    """
    rng = random.Random(seed)

    if style == "basket":
        p = BasketParams(
            height=args.height,
            r_base=args.r_base,
            thickness=args.thickness,
            bulb_amp=args.bulb_amp,
            bulb_count=args.bulb_count,
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
            p.taper = clamp(p.taper + rng.uniform(-0.04, 0.06), 0.0, 0.25)
            p.weave_amp = clamp(p.weave_amp * rng.uniform(0.7, 1.35), 0.3, 1.6)
            p.weave_theta = clamp(p.weave_theta + rng.uniform(-6.0, 10.0), 14.0, 60.0)
            p.weave_pitch = clamp(p.weave_pitch + rng.uniform(-0.8, 1.0), 1.0, 6.5)
            p.weave_mix = clamp(p.weave_mix + rng.uniform(-0.15, 0.15), 0.2, 0.8)

        tris = make_basket_shell(p)
        outer_r_hint = p.r_base + p.bulb_amp + p.weave_amp + 3.0
        return tris, p.height, outer_r_hint

    if style == "wire":
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
            p.wires = int(clamp(p.wires + rng.randint(-4, 6), 16, 44))
            p.rotations = clamp(p.rotations + rng.uniform(-1.2, 1.4), 3.0, 10.0)
            p.offset_b = clamp(p.offset_b + rng.uniform(-0.12, 0.12), 0.25, 0.75)
            p.wire_width = clamp(p.wire_width * rng.uniform(0.85, 1.25), 1.2, 3.2)
            p.wire_thickness = clamp(p.wire_thickness * rng.uniform(0.9, 1.2), 0.8, 1.8)

        tris = make_wire_diamonds(p)
        outer_r_hint = p.radius + p.wire_thickness + 3.0
        return tris, p.height, outer_r_hint

    raise ValueError("style must be 'basket' or 'wire'")

def main():
    ap = argparse.ArgumentParser(description="Lampgen V3: basket (V1) or wire diamonds (V2) + bayonet 1/4 turn lock mount")

    ap.add_argument("--out", default="out_lamp_v3", help="Output folder")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--style", choices=["basket", "wire"], default="wire")
    ap.add_argument("--vary", action="store_true", help="Randomize params slightly per model")

    # Shared height
    ap.add_argument("--height", type=float, default=200.0)

    # Basket params
    ap.add_argument("--r-base", type=float, default=42.0)
    ap.add_argument("--thickness", type=float, default=1.6)
    ap.add_argument("--bulb-amp", type=float, default=12.0)
    ap.add_argument("--bulb-count", type=float, default=2.5)
    ap.add_argument("--taper", type=float, default=0.08)
    ap.add_argument("--weave-amp", type=float, default=0.9)
    ap.add_argument("--weave-theta", type=float, default=24.0)
    ap.add_argument("--weave-pitch", type=float, default=3.2)
    ap.add_argument("--weave-mix", type=float, default=0.5)
    ap.add_argument("--n-theta", type=int, default=256)
    ap.add_argument("--n-z", type=int, default=220)

    # Wire params
    ap.add_argument("--radius", type=float, default=45.0)
    ap.add_argument("--wires", type=int, default=26)
    ap.add_argument("--rotations", type=float, default=6.0)
    ap.add_argument("--offset-b", type=float, default=0.5)
    ap.add_argument("--wire-width", type=float, default=2.0)
    ap.add_argument("--wire-thickness", type=float, default=1.2)
    ap.add_argument("--seg-per-rot", type=int, default=110)

    # Bayonet params
    ap.add_argument("--socket-id", type=float, default=32.0, help="Female socket inner diameter (mm)")
    ap.add_argument("--mount-height", type=float, default=14.0)
    ap.add_argument("--twist-deg", type=float, default=70.0)
    ap.add_argument("--clearance", type=float, default=0.30)
    ap.add_argument("--n-lugs", type=int, default=3)
    ap.add_argument("--entry-deg", type=float, default=22.0)
    ap.add_argument("--lug-deg", type=float, default=16.0)
    ap.add_argument("--lug-radial", type=float, default=2.0)
    ap.add_argument("--lug-thickness-z", type=float, default=2.2)
    ap.add_argument("--wall", type=float, default=2.4)
    ap.add_argument("--no-detent", action="store_true", help="Disable click-bump detent")

    ap.add_argument("--make-adapter", action="store_true", help="Also export male bayonet adapter STL")

    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    rng = random.Random(args.seed)

    for i in range(args.count):
        model_seed = rng.randint(0, 10**9)

        body_tris, H, outer_r_hint = build_head(args.style, model_seed, args)

        bp = BayonetParams(
            n_lugs=args.n_lugs,
            twist_deg=args.twist_deg,
            entry_deg=args.entry_deg,
            lug_deg=args.lug_deg,
            mount_height=args.mount_height,
            wall=args.wall,
            socket_id=args.socket_id,
            clearance=args.clearance,
            lug_thickness_z=args.lug_thickness_z,
            lug_radial=args.lug_radial,
            detent=(not args.no_detent)
        )

        # Female mount: put at bottom (z=0)
        mount_tris = []
        add_female_bayonet(mount_tris, bp, z_base=0.0, outer_radius_hint=outer_r_hint)

        tris_head = body_tris + mount_tris

        head_name = f"lamp_{args.style}_bayonet_female_h{int(H)}_{i:04d}.stl"
        head_path = os.path.join(args.out, head_name)
        write_binary_stl(head_path, tris_head, header_text=b"lampgen_v3_bayonet_female_head")
        print(f"[{i+1}/{args.count}] HEAD OK -> {head_path}  (tris={len(tris_head)})")

        if args.make_adapter:
            # Male adapter as separate part (base)
            adapter_tris = []
            add_male_bayonet_adapter(adapter_tris, bp, z_base=0.0, adapter_height=max(18.0, bp.mount_height + 4.0))
            adap_name = f"bayonet_male_adapter_id{int(bp.socket_id)}_{i:04d}.stl"
            adap_path = os.path.join(args.out, adap_name)
            write_binary_stl(adap_path, adapter_tris, header_text=b"lampgen_v3_bayonet_male_adapter")
            print(f"           ADAPTER OK -> {adap_path}  (tris={len(adapter_tris)})")

if __name__ == "__main__":
    main()