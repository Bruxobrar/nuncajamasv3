import math
import struct
from dataclasses import dataclass


def vec_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vec_cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def vec_length(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def vec_norm(v):
    length = vec_length(v)
    if length <= 1e-9:
        return (0.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def vec_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vec_scale(v, s):
    return (v[0] * s, v[1] * s, v[2] * s)


def tri_normal(v0, v1, v2):
    return vec_norm(vec_cross(vec_sub(v1, v0), vec_sub(v2, v0)))


def write_binary_stl(path, triangles):
    header = b"baggen soft cosmetic bag engine".ljust(80, b"\0")
    with open(path, "wb") as handle:
        handle.write(header)
        handle.write(struct.pack("<I", len(triangles)))
        for v0, v1, v2 in triangles:
            normal = tri_normal(v0, v1, v2)
            handle.write(struct.pack("<3f", *normal))
            handle.write(struct.pack("<3f", *v0))
            handle.write(struct.pack("<3f", *v1))
            handle.write(struct.pack("<3f", *v2))
            handle.write(struct.pack("<H", 0))


@dataclass
class BagParams:
    height: float = 96.0
    width: float = 78.0
    depth: float = 46.0
    thickness: float = 2.2
    top_scale: float = 0.76
    body_roundness: float = 0.72
    side_tuck: float = 0.22
    belly: float = 0.18
    pleat_depth: float = 0.11
    pleat_count: int = 6
    rim_wave_amp: float = 5.2
    rim_wave_count: int = 6
    rim_band_height: float = 11.0
    handle_span: float = 44.0
    handle_drop: float = 58.0
    handle_pair_gap: float = 11.0
    handle_thickness: float = 3.2
    eyelet_radius: float = 3.4
    eyelet_thickness: float = 1.25
    eyelet_count: int = 6
    eyelet_drop: float = 12.0
    drawstring_thickness: float = 1.25
    drawstring_drop: float = 28.0
    n_theta: int = 180
    n_z: int = 120


def clamp(value, low, high):
    return max(low, min(high, value))


def smoothstep01(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def sign_pow(value, exponent):
    return math.copysign(abs(value) ** exponent, value)


def add_quad(tris, v00, v10, v11, v01, flip=False):
    if flip:
        tris.append((v00, v11, v10))
        tris.append((v00, v01, v11))
    else:
        tris.append((v00, v10, v11))
        tris.append((v00, v11, v01))


def add_disk(tris, ring, center, flip=False):
    count = len(ring)
    for index in range(count):
        nxt = (index + 1) % count
        if flip:
            tris.append((center, ring[nxt], ring[index]))
        else:
            tris.append((center, ring[index], ring[nxt]))


def build_local_frame(tangent):
    tangent = vec_norm(tangent)
    up = (0.0, 0.0, 1.0) if abs(tangent[2]) < 0.92 else (0.0, 1.0, 0.0)
    normal = vec_norm(vec_cross(up, tangent))
    if vec_length(normal) <= 1e-9:
        up = (1.0, 0.0, 0.0)
        normal = vec_norm(vec_cross(up, tangent))
    binormal = vec_norm(vec_cross(tangent, normal))
    return tangent, normal, binormal


def tube_ring(center, tangent, radius, segments):
    _tangent, normal, binormal = build_local_frame(tangent)
    ring = []
    for idx in range(segments):
        angle = (2.0 * math.pi * idx) / segments
        offset = vec_add(vec_scale(normal, math.cos(angle) * radius), vec_scale(binormal, math.sin(angle) * radius))
        ring.append(vec_add(center, offset))
    return ring


def add_tube_polyline(tris, points, radius, path_segments=14, cap_start=False, cap_end=False):
    if len(points) < 2 or radius <= 0.0:
        return
    rings = []
    for idx, point in enumerate(points):
        if idx == 0:
            tangent = vec_sub(points[1], point)
        elif idx == len(points) - 1:
            tangent = vec_sub(point, points[idx - 1])
        else:
            tangent = vec_add(vec_sub(points[idx + 1], point), vec_sub(point, points[idx - 1]))
        rings.append(tube_ring(point, tangent, radius, path_segments))

    for idx in range(len(rings) - 1):
        ring0 = rings[idx]
        ring1 = rings[idx + 1]
        for seg in range(path_segments):
            nxt = (seg + 1) % path_segments
            add_quad(tris, ring0[seg], ring1[seg], ring1[nxt], ring0[nxt])

    if cap_start:
        add_disk(tris, list(reversed(rings[0])), points[0], flip=False)
    if cap_end:
        add_disk(tris, rings[-1], points[-1], flip=False)


def add_torus(tris, center, axis_u, axis_v, major_radius, tube_radius, major_segments=36, tube_segments=14):
    rings = []
    centers = []
    for idx in range(major_segments):
        angle = (2.0 * math.pi * idx) / major_segments
        ring_center = vec_add(center, vec_add(vec_scale(axis_u, math.cos(angle) * major_radius), vec_scale(axis_v, math.sin(angle) * major_radius)))
        tangent = vec_add(vec_scale(axis_u, -math.sin(angle)), vec_scale(axis_v, math.cos(angle)))
        centers.append(ring_center)
        rings.append(tube_ring(ring_center, tangent, tube_radius, tube_segments))

    for idx in range(major_segments):
        nxt = (idx + 1) % major_segments
        ring0 = rings[idx]
        ring1 = rings[nxt]
        for seg in range(tube_segments):
            seg_next = (seg + 1) % tube_segments
            add_quad(tris, ring0[seg], ring1[seg], ring1[seg_next], ring0[seg_next])


def add_uv_sphere(tris, center, radius, u_segments=16, v_segments=10):
    rings = []
    for vidx in range(1, v_segments):
        phi = math.pi * vidx / v_segments
        z = center[2] + radius * math.cos(phi)
        rr = radius * math.sin(phi)
        ring = []
        for uidx in range(u_segments):
            theta = (2.0 * math.pi * uidx) / u_segments
            ring.append((center[0] + rr * math.cos(theta), center[1] + rr * math.sin(theta), z))
        rings.append(ring)

    north = (center[0], center[1], center[2] + radius)
    south = (center[0], center[1], center[2] - radius)
    if not rings:
        return

    first = rings[0]
    for idx in range(u_segments):
        nxt = (idx + 1) % u_segments
        tris.append((north, first[idx], first[nxt]))

    for ridx in range(len(rings) - 1):
        ring0 = rings[ridx]
        ring1 = rings[ridx + 1]
        for idx in range(u_segments):
            nxt = (idx + 1) % u_segments
            add_quad(tris, ring0[idx], ring1[idx], ring1[nxt], ring0[nxt])

    last = rings[-1]
    for idx in range(u_segments):
        nxt = (idx + 1) % u_segments
        tris.append((south, last[nxt], last[idx]))


def bag_axes(z, params):
    u = clamp(z / max(params.height, 1e-6), 0.0, 1.0)
    lower = smoothstep01(u / 0.22)
    upper = smoothstep01((1.0 - u) / 0.24)
    fullness = 0.74 + 0.46 * math.sin(math.pi * (u ** 0.9))
    base_width = params.width * 0.5 * fullness
    base_depth = params.depth * 0.5 * (0.82 + 0.34 * math.sin(math.pi * (u ** 0.95)))
    top_mix = smoothstep01((u - 0.58) / 0.42)
    width = base_width * (1.0 - top_mix * (1.0 - params.top_scale))
    depth = base_depth * (1.0 - top_mix * (1.0 - params.top_scale * (1.0 - params.side_tuck * 0.5)))
    width *= 0.94 + 0.06 * lower
    depth *= 0.92 + 0.08 * upper
    return max(params.thickness * 1.8, width), max(params.thickness * 1.6, depth)


def rim_height(theta, params):
    return params.height + params.rim_wave_amp * math.sin(theta * params.rim_wave_count)


def bag_point(theta, z, params, inset=0.0):
    width, depth = bag_axes(z, params)
    width = max(params.thickness * 1.4, width - inset)
    depth = max(params.thickness * 1.2, depth - inset)

    exponent = 2.0 + params.body_roundness * 3.6
    cx = sign_pow(math.cos(theta), 2.0 / exponent)
    sy = sign_pow(math.sin(theta), 2.0 / exponent)

    pleat_bias = smoothstep01((z / max(params.height, 1e-6) - 0.18) / 0.82)
    pleat = 1.0 - params.pleat_depth * pleat_bias * (0.5 + 0.5 * math.cos(params.pleat_count * theta)) ** 2
    belly = 1.0 + params.belly * math.sin(theta) * math.sin(theta) * math.sin(math.pi * clamp(z / max(params.height, 1e-6), 0.0, 1.0))

    x = width * cx * pleat
    y = depth * sy * belly
    top_wave_weight = smoothstep01((z - (params.height - params.rim_band_height)) / max(params.rim_band_height, 1e-6))
    z_out = z + top_wave_weight * params.rim_wave_amp * math.sin(theta * params.rim_wave_count)
    return (x, y, z_out)


def build_shell(tris, params):
    nt = max(36, params.n_theta)
    nz = max(12, params.n_z)
    outer = [[None] * nt for _ in range(nz)]
    inner = [[None] * nt for _ in range(nz)]

    for iz in range(nz):
        z = (params.height * iz) / (nz - 1)
        for it in range(nt):
            theta = (2.0 * math.pi * it) / nt
            outer[iz][it] = bag_point(theta, z, params, inset=0.0)
            inner[iz][it] = bag_point(theta, z, params, inset=params.thickness)

    for iz in range(nz - 1):
        for it in range(nt):
            nxt = (it + 1) % nt
            add_quad(tris, outer[iz][it], outer[iz + 1][it], outer[iz + 1][nxt], outer[iz][nxt])
            add_quad(tris, inner[iz][it], inner[iz][nxt], inner[iz + 1][nxt], inner[iz + 1][it])

    bottom_outer_center = (0.0, 0.0, 0.0)
    bottom_inner_center = (0.0, 0.0, params.thickness * 0.75)
    add_disk(tris, outer[0], bottom_outer_center, flip=False)
    add_disk(tris, list(reversed(inner[0])), bottom_inner_center, flip=False)

    for it in range(nt):
        nxt = (it + 1) % nt
        add_quad(tris, outer[0][it], outer[0][nxt], inner[0][nxt], inner[0][it])
        add_quad(tris, outer[-1][it], inner[-1][it], inner[-1][nxt], outer[-1][nxt])


def handle_anchor(theta, z, params):
    return bag_point(theta, z, params, inset=-params.handle_thickness * 0.2)


def build_handles(tris, params):
    anchor_z = params.height - params.eyelet_drop * 0.35
    left_theta = math.pi
    right_theta = 0.0
    left = handle_anchor(left_theta, anchor_z, params)
    right = handle_anchor(right_theta, anchor_z, params)
    span = min(params.handle_span, abs(right[0] - left[0]) * 0.92)
    x0 = -span * 0.5
    x1 = span * 0.5

    for offset_sign in (-1.0, 1.0):
        y_offset = offset_sign * params.handle_pair_gap * 0.5
        points = []
        for idx in range(17):
            t = idx / 16.0
            x = x0 * (1.0 - t) + x1 * t
            z = anchor_z + params.handle_drop * math.sin(math.pi * t)
            y = y_offset + 2.4 * math.sin(math.pi * t) ** 1.5
            points.append((x, y, z))
        add_tube_polyline(tris, points, params.handle_thickness, path_segments=16, cap_start=False, cap_end=False)


def eyelet_angles(count):
    if count <= 1:
        return [-math.pi * 0.5]
    start = -math.pi * 0.84
    end = -math.pi * 0.16
    return [start + (end - start) * idx / (count - 1) for idx in range(count)]


def build_eyelets_and_drawstring(tris, params):
    z = params.height - params.eyelet_drop
    anchors = []
    for theta in eyelet_angles(params.eyelet_count):
        center = bag_point(theta, z, params, inset=-params.eyelet_thickness * 0.4)
        radial = vec_norm((center[0], center[1], 0.0))
        axis_u = (0.0, 0.0, 1.0)
        axis_v = radial
        add_torus(tris, center, axis_u, axis_v, params.eyelet_radius, params.eyelet_thickness, major_segments=28, tube_segments=12)
        anchors.append(center)

    if len(anchors) < 2:
        return

    string_points = [anchors[0]]
    for center in anchors[1:-1]:
        string_points.append((center[0], center[1], center[2] - params.eyelet_radius * 0.18))
    string_points.append(anchors[-1])
    add_tube_polyline(tris, string_points, params.drawstring_thickness, path_segments=12, cap_start=False, cap_end=False)

    left_end = [
        anchors[1],
        (anchors[1][0] - 3.0, anchors[1][1] - 5.0, anchors[1][2] - params.drawstring_drop * 0.35),
        (anchors[1][0] - 5.0, anchors[1][1] - 8.5, anchors[1][2] - params.drawstring_drop),
    ]
    right_end = [
        anchors[-2],
        (anchors[-2][0] + 3.0, anchors[-2][1] - 4.0, anchors[-2][2] - params.drawstring_drop * 0.32),
        (anchors[-2][0] + 5.5, anchors[-2][1] - 7.0, anchors[-2][2] - params.drawstring_drop * 0.96),
    ]
    add_tube_polyline(tris, left_end, params.drawstring_thickness, path_segments=12, cap_start=False, cap_end=True)
    add_tube_polyline(tris, right_end, params.drawstring_thickness, path_segments=12, cap_start=False, cap_end=True)

    knot_radius = params.drawstring_thickness * 1.7
    add_uv_sphere(tris, left_end[-1], knot_radius)
    add_uv_sphere(tris, right_end[-1], knot_radius)


def make_mesh(params):
    tris = []
    build_shell(tris, params)
    build_handles(tris, params)
    build_eyelets_and_drawstring(tris, params)
    return tris
