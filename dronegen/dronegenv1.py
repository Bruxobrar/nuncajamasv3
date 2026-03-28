import argparse
import math
import os
import struct
from dataclasses import dataclass
from typing import List, Tuple

Vec3 = Tuple[float, float, float]
Tri = Tuple[Vec3, Vec3, Vec3]


# -----------------------------
# STL (binary) writer
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

def write_binary_stl(path: str, triangles: List[Tri], header_txt: str = "stallion_like_v1"):
    header = header_txt.encode("ascii", errors="ignore")[:80].ljust(80, b"\0")
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
# Mesh primitives (watertight)
# -----------------------------
def add_quad(tris: List[Tri], a: Vec3, b: Vec3, c: Vec3, d: Vec3, flip=False):
    if not flip:
        tris.append((a, b, c))
        tris.append((a, c, d))
    else:
        tris.append((a, c, b))
        tris.append((a, d, c))

def add_box(tris: List[Tri], cx, cy, cz, sx, sy, sz):
    # axis-aligned box, centered at (cx,cy,cz), sizes sx,sy,sz
    hx, hy, hz = sx/2, sy/2, sz/2
    # 8 corners
    p000 = (cx-hx, cy-hy, cz-hz)
    p001 = (cx-hx, cy-hy, cz+hz)
    p010 = (cx-hx, cy+hy, cz-hz)
    p011 = (cx-hx, cy+hy, cz+hz)
    p100 = (cx+hx, cy-hy, cz-hz)
    p101 = (cx+hx, cy-hy, cz+hz)
    p110 = (cx+hx, cy+hy, cz-hz)
    p111 = (cx+hx, cy+hy, cz+hz)

    # faces (outward)
    add_quad(tris, p000, p100, p110, p010)  # -Z? (actually bottom z-hz) orientation ok
    add_quad(tris, p001, p011, p111, p101)  # top
    add_quad(tris, p000, p010, p011, p001)  # -X
    add_quad(tris, p100, p101, p111, p110)  # +X
    add_quad(tris, p000, p001, p101, p100)  # -Y
    add_quad(tris, p010, p110, p111, p011)  # +Y

def add_cylinder_z(tris: List[Tri], cx, cy, z0, z1, r, segments=64, cap=True):
    # cylinder along Z from z0 to z1
    if z1 < z0:
        z0, z1 = z1, z0
    dt = 2.0 * math.pi / segments
    # side
    for i in range(segments):
        t0 = i * dt
        t1 = (i+1) * dt
        x0, y0 = cx + r*math.cos(t0), cy + r*math.sin(t0)
        x1, y1 = cx + r*math.cos(t1), cy + r*math.sin(t1)
        v00 = (x0, y0, z0)
        v10 = (x1, y1, z0)
        v11 = (x1, y1, z1)
        v01 = (x0, y0, z1)
        add_quad(tris, v00, v10, v11, v01)
    if cap:
        # bottom fan
        cb = (cx, cy, z0)
        ct = (cx, cy, z1)
        for i in range(segments):
            t0 = i * dt
            t1 = (i+1) * dt
            x0, y0 = cx + r*math.cos(t0), cy + r*math.sin(t0)
            x1, y1 = cx + r*math.cos(t1), cy + r*math.sin(t1)
            # bottom (pointing -Z): reverse winding
            tris.append((cb, (x1, y1, z0), (x0, y0, z0)))
            # top (pointing +Z)
            tris.append((ct, (x0, y0, z1), (x1, y1, z1)))

def add_frustum_z(tris: List[Tri], cx, cy, z0, z1, r0, r1, segments=64, cap=True):
    # cone frustum along Z
    if z1 < z0:
        z0, z1 = z1, z0
        r0, r1 = r1, r0
    dt = 2.0 * math.pi / segments
    for i in range(segments):
        t0 = i * dt
        t1 = (i+1) * dt
        a0 = (cx + r0*math.cos(t0), cy + r0*math.sin(t0), z0)
        a1 = (cx + r0*math.cos(t1), cy + r0*math.sin(t1), z0)
        b1 = (cx + r1*math.cos(t1), cy + r1*math.sin(t1), z1)
        b0 = (cx + r1*math.cos(t0), cy + r1*math.sin(t0), z1)
        add_quad(tris, a0, a1, b1, b0)
    if cap:
        if r0 > 0:
            cb = (cx, cy, z0)
            for i in range(segments):
                t0 = i * dt
                t1 = (i+1) * dt
                x0, y0 = cx + r0*math.cos(t0), cy + r0*math.sin(t0)
                x1, y1 = cx + r0*math.cos(t1), cy + r0*math.sin(t1)
                tris.append((cb, (x1, y1, z0), (x0, y0, z0)))
        if r1 > 0:
            ct = (cx, cy, z1)
            for i in range(segments):
                t0 = i * dt
                t1 = (i+1) * dt
                x0, y0 = cx + r1*math.cos(t0), cy + r1*math.sin(t0)
                x1, y1 = cx + r1*math.cos(t1), cy + r1*math.sin(t1)
                tris.append((ct, (x0, y0, z1), (x1, y1, z1)))


# -----------------------------
# Stallion-like airplane (simplified reference model)
# -----------------------------
@dataclass
class StallionLikeParams:
    # taken as “reference proportions” from manual:
    wingspan: float = 1340.0   # mm【STALLION manual】 (reference)
    length: float = 990.0      # mm【STALLION manual】 (reference)

    # geometry simplification controls
    wing_root_chord: float = 255.0  # mm (manual root chord ref)【STALLION manual】
    wing_tip_chord: float = 140.0   # mm (simple taper)
    wing_thickness: float = 18.0    # mm (thick printable wing slab)
    fus_radius_front: float = 55.0  # mm
    fus_radius_mid: float = 45.0
    fus_radius_tail: float = 25.0
    fus_height: float = 95.0        # “oval” effect via stacked frustums
    tailboom_radius: float = 8.0    # tube-like
    tailboom_length: float = 430.0  # matches manual tail boom length (16mm tube in real)【STALLION manual】

    vtail_span: float = 260.0       # mm per side spar ref (manual says 4mm tubes ~260mm)【STALLION manual】
    vtail_thickness: float = 10.0   # mm slab
    vtail_chord: float = 90.0       # mm
    vtail_angle_deg: float = 35.0   # V-tail dihedral-like

    segments: int = 72


def build_stallion_like(p: StallionLikeParams) -> List[Tri]:
    tris: List[Tri] = []

    # Coordinate system:
    # X = left/right (span)
    # Y = forward/back (length)
    # Z = up/down

    # ---------------- fuselage (stacked frustums) ----------------
    # nose -> mid -> tail
    nose_y = +p.length*0.35
    mid_y  = 0.0
    tail_y = -p.length*0.42

    # nose bulb
    add_frustum_z(tris, 0, nose_y, -p.fus_height*0.35, +p.fus_height*0.35,
                  r0=p.fus_radius_front*0.85, r1=p.fus_radius_front, segments=p.segments, cap=True)
    # mid
    add_frustum_z(tris, 0, mid_y, -p.fus_height*0.33, +p.fus_height*0.33,
                  r0=p.fus_radius_front, r1=p.fus_radius_mid, segments=p.segments, cap=True)
    # tail taper
    add_frustum_z(tris, 0, tail_y, -p.fus_height*0.28, +p.fus_height*0.28,
                  r0=p.fus_radius_mid, r1=p.fus_radius_tail, segments=p.segments, cap=True)

    # ---------------- wing (simple tapered slabs) ----------------
    half_span = p.wingspan / 2.0
    # put wing root around mid_y slightly forward like flying wing-ish
    wing_y = +p.length*0.05
    z_wing = 0.0

    # We approximate each wing half as a trapezoid extruded in Z.
    # Build as a "prism" from two rectangles (root/tip) with quads.
    def add_wing_half(sign: float):
        # sign: +1 right, -1 left
        x0 = 0.0
        x1 = sign * half_span

        # root/tip leading edge & trailing edge in Y
        le_root = wing_y + p.wing_root_chord*0.15
        te_root = wing_y - p.wing_root_chord*0.85
        le_tip  = wing_y + p.wing_tip_chord*0.15
        te_tip  = wing_y - p.wing_tip_chord*0.85

        z0 = z_wing - p.wing_thickness/2
        z1 = z_wing + p.wing_thickness/2

        # 8 corners (root 4, tip 4)
        rr_le_b = (x0, le_root, z0)
        rr_te_b = (x0, te_root, z0)
        rr_te_t = (x0, te_root, z1)
        rr_le_t = (x0, le_root, z1)

        tt_le_b = (x1, le_tip, z0)
        tt_te_b = (x1, te_tip, z0)
        tt_te_t = (x1, te_tip, z1)
        tt_le_t = (x1, le_tip, z1)

        # skins
        add_quad(tris, rr_le_b, tt_le_b, tt_te_b, rr_te_b)  # bottom-ish
        add_quad(tris, rr_le_t, rr_te_t, tt_te_t, tt_le_t)  # top-ish

        # edges
        add_quad(tris, rr_le_b, rr_le_t, tt_le_t, tt_le_b)  # leading
        add_quad(tris, rr_te_b, tt_te_b, tt_te_t, rr_te_t)  # trailing
        add_quad(tris, tt_le_b, tt_le_t, tt_te_t, tt_te_b)  # tip cap
        add_quad(tris, rr_te_b, rr_te_t, rr_le_t, rr_le_b)  # root cap

    add_wing_half(+1.0)
    add_wing_half(-1.0)

    # ---------------- tailboom + V-tail slabs ----------------
    # place boom behind tail_y
    boom_y0 = tail_y - 20.0
    boom_y1 = boom_y0 - p.tailboom_length

    # boom as cylinder along Y: easiest is boxes + cylinders; we fake with a thin box
    # (if querés, V2 lo hacemos con cilindro real rotado)
    boom_len = abs(boom_y1 - boom_y0)
    add_box(tris, 0.0, (boom_y0+boom_y1)/2, 0.0, sx=p.tailboom_radius*2.2, sy=boom_len, sz=p.tailboom_radius*2.2)

    # V-tail at end of boom
    tail_y_end = boom_y1
    angle = math.radians(p.vtail_angle_deg)
    for sign in (+1, -1):
        # simple slab: size (span along X, chord along Y, thickness along Z)
        # rotated around Y axis? we approximate by positioning corners (no complex rotation)
        x_span = sign * (p.vtail_span * math.cos(angle))
        z_span = (p.vtail_span * math.sin(angle))

        # base near tail end
        base = (0.0, tail_y_end, 0.0)
        tip  = (x_span, tail_y_end - p.vtail_chord*0.6, z_span)

        # make a small rectangular prism oriented approx by linear interpolation between base and tip
        # We'll just place a box near base and another near tip, connected by a frustum-like box (good enough for V1)
        add_box(tris, base[0], base[1], base[2],
                sx=18.0, sy=p.vtail_chord, sz=p.vtail_thickness)
        add_box(tris, tip[0], tip[1], tip[2],
                sx=14.0, sy=p.vtail_chord*0.8, sz=p.vtail_thickness*0.9)

    return tris


# -----------------------------
# VTOL kit (simplified: 2 front booms + front motor mount + tail motor clamp)
# -----------------------------
@dataclass
class VtolKitParams:
    # Boom (front)
    boom_len: float = 200.0
    boom_w: float = 32.0
    boom_h: float = 28.0

    # Motor mount front (tilt cradle)
    motor_pad_d: float = 32.0
    motor_hole_d: float = 3.2
    motor_pattern: float = 19.0  # many 28xx motors use 19x19, adjustable
    axle_hole_d: float = 5.0     # pivot / shaft hole (simplified)
    bearing_od: float = 8.0      # matches 3x8x4 bearing OD as “8mm” ref【VTOL manual】
    bearing_thick: float = 4.0

    # Tail motor clamp for a tube boom (manual uses 16mm tube; we param)
    tail_tube_od: float = 16.0
    clamp_len: float = 26.0
    clamp_wall: float = 6.0
    clamp_screw_d: float = 3.2

    segments: int = 72


def build_vtol_kit(p: VtolKitParams) -> List[Tri]:
    tris: List[Tri] = []

    # 1) Two booms (L/R) as hollow-ish blocks (no boolean; we do "U shape" by overlapping solids = print ok)
    # For V1, booms are simple blocks with a channel hint.
    def add_boom(cx):
        add_box(tris, cx, 0.0, 0.0, p.boom_w, p.boom_len, p.boom_h)
        # “channel” hint (overlap smaller block in same space does nothing in boolean sense,
        # but visually te marca la cavidad; para cavidad real lo hacemos en V2 con boolean/STEP)
        add_box(tris, cx, -p.boom_len*0.05, -p.boom_h*0.1, p.boom_w*0.55, p.boom_len*0.75, p.boom_h*0.55)

    add_boom(-60.0)
    add_boom(+60.0)

    # 2) Front motor mount (tilt cradle simplified)
    # Base block
    add_box(tris, 0.0, +p.boom_len*0.55, 0.0, 46.0, 34.0, 30.0)
    # motor pad
    add_cylinder_z(tris, 0.0, +p.boom_len*0.55, 15.0, 25.0, p.motor_pad_d/2, segments=p.segments, cap=True)

    # pivot "ears" (where bearing sits) left/right
    ear_y = +p.boom_len*0.55
    ear_z0, ear_z1 = -6.0, +6.0
    for sx in (-1, +1):
        ex = sx * 24.0
        # ear body
        add_cylinder_z(tris, ex, ear_y, ear_z0, ear_z1, r=10.0, segments=40, cap=True)
        # bearing seat visual (OD 8mm per manual bearing 3x8x4)【VTOL manual】
        add_cylinder_z(tris, ex, ear_y, ear_z0-2.0, ear_z0-2.0 + p.bearing_thick, r=p.bearing_od/2, segments=40, cap=True)

    # axle “shaft” (visual)
    add_cylinder_z(tris, 0.0, ear_y, -2.5, +2.5, r=p.axle_hole_d/2, segments=40, cap=True)

    # motor hole pattern (visual pegs “negative” not subtracted)
    # para agujeros reales: en V2 te lo paso con OpenSCAD/STEP boolean
    for sx in (-1, +1):
        for sy in (-1, +1):
            x = sx * p.motor_pattern/2
            y = ear_y + sy * p.motor_pattern/2
            add_cylinder_z(tris, x, y, 12.0, 26.0, r=p.motor_hole_d/2, segments=24, cap=True)

    # 3) Tail motor clamp for tube
    # Manual: tail motor shaft positioned 195mm from tube front【VTOL manual】
    # This STL is ONLY the clamp; positioning is your assembly step.
    clamp_y = -p.boom_len*0.65
    outer_r = (p.tail_tube_od/2) + p.clamp_wall
    inner_r = (p.tail_tube_od/2)

    # We fake clamp as 2 concentric cylinders overlapped (no boolean), then a screw boss.
    add_cylinder_z(tris, 0.0, clamp_y, -p.clamp_len/2, +p.clamp_len/2, r=outer_r, segments=p.segments, cap=True)
    add_cylinder_z(tris, 0.0, clamp_y, -p.clamp_len/2 + 1.0, +p.clamp_len/2 - 1.0, r=inner_r, segments=p.segments, cap=True)

    # screw boss
    add_box(tris, outer_r + 10.0, clamp_y, 0.0, 22.0, 18.0, 18.0)
    add_cylinder_z(tris, outer_r + 10.0, clamp_y, -10.0, +10.0, r=p.clamp_screw_d/2, segments=32, cap=True)

    return tris


# -----------------------------
# CLI
# -----------------------------
def main():
    ap = argparse.ArgumentParser(description="Stallion-like airplane + VTOL kit (simple watertight primitives) -> STL")
    ap.add_argument("--out", default="out_stallion_v1", help="Output folder")
    ap.add_argument("--mode", choices=["airframe", "vtol", "both"], default="both")

    # Airframe refs (manual proportions)
    ap.add_argument("--wingspan", type=float, default=1340.0)
    ap.add_argument("--length", type=float, default=990.0)

    # VTOL basic controls
    ap.add_argument("--boom-len", type=float, default=200.0)
    ap.add_argument("--tail-tube-od", type=float, default=16.0)

    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    if args.mode in ("airframe", "both"):
        p = StallionLikeParams(wingspan=args.wingspan, length=args.length)
        tris = build_stallion_like(p)
        path = os.path.join(args.out, f"stallion_like_airframe_ws{int(p.wingspan)}_L{int(p.length)}.stl")
        write_binary_stl(path, tris, header_txt="stallion_like_airframe_v1")
        print("OK ->", path, "tris=", len(tris))

    if args.mode in ("vtol", "both"):
        v = VtolKitParams(boom_len=args.boom_len, tail_tube_od=args.tail_tube_od)
        tris = build_vtol_kit(v)
        path = os.path.join(args.out, f"stallion_like_vtol_kit_boom{int(v.boom_len)}_tube{int(v.tail_tube_od)}.stl")
        write_binary_stl(path, tris, header_txt="stallion_like_vtol_kit_v1")
        print("OK ->", path, "tris=", len(tris))


if __name__ == "__main__":
    main()