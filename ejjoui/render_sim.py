import math

WORLD_UP = (0.0, 0.0, 1.0)
LIGHT_DIR = (-0.45, -0.7, 0.55)


def normalize(vector):
    length = math.sqrt(sum(part * part for part in vector)) or 1.0
    return tuple(part / length for part in vector)


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def subtract(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def lerp(a, b, t):
    return a + (b - a) * t


def mix_color(a, b, t):
    return tuple(int(round(lerp(a[i], b[i], t))) for i in range(3))


def color_hex(color):
    return '#%02x%02x%02x' % color


LIGHT_DIR = normalize(LIGHT_DIR)


def build_camera(radius, target, camera_state):
    distance = max(radius * camera_state['distance_factor'], 120.0)
    horizontal = math.cos(camera_state['pitch']) * distance
    eye = (
        target[0] + math.cos(camera_state['yaw']) * horizontal,
        target[1] + math.sin(camera_state['yaw']) * horizontal,
        target[2] + math.sin(camera_state['pitch']) * distance,
    )
    forward = normalize((target[0] - eye[0], target[1] - eye[1], target[2] - eye[2]))
    right = cross(forward, WORLD_UP)
    if math.sqrt(dot(right, right)) < 1e-5:
        right = (1.0, 0.0, 0.0)
    else:
        right = normalize(right)
    up = normalize(cross(right, forward))
    return {'eye': eye, 'forward': forward, 'right': right, 'up': up, 'distance': distance}


def project_point(local, camera, focal, width, height, projection='orthographic'):
    relative = subtract(local, camera['eye'])
    vx = dot(relative, camera['right'])
    vy = dot(relative, camera['up'])
    vz = dot(relative, camera['forward'])
    if projection == 'orthographic':
        ortho_scale = min(width, height) / max(120.0, camera['distance'] * 0.9)
        return (vx * ortho_scale + width * 0.5, -vy * ortho_scale + height * 0.52, vz)
    depth = max(1.0, vz)
    scale = focal / depth
    return (vx * scale + width * 0.5, -vy * scale + height * 0.52, vz)


def get_anchored_vertices(mesh, preview_source='generated'):
    vertices = mesh['vertices']
    bounds = mesh['bounds']
    anchor = (
        (bounds['min'][0] + bounds['max'][0]) * 0.5,
        (bounds['min'][1] + bounds['max'][1]) * 0.5,
        bounds['min'][2],
    )
    height = bounds['max'][2] - bounds['min'][2]
    target_height = height * (0.18 if preview_source == 'import' else 0.28)
    local_vertices = [
        (vertex[0] - anchor[0], vertex[1] - anchor[1], vertex[2] - anchor[2])
        for vertex in vertices
    ]
    return local_vertices, (0.0, 0.0, target_height)


def draw_backdrop(canvas, width, height):
    steps = 18
    top = (248, 241, 232)
    mid = (231, 221, 208)
    bottom = (203, 192, 180)
    for index in range(steps):
        y0 = int(height * index / steps)
        y1 = int(height * (index + 1) / steps)
        blend = index / max(1, steps - 1)
        col = mix_color(top, mid if blend < 0.5 else bottom, blend * 2 if blend < 0.5 else (blend - 0.5) * 2)
        canvas.create_rectangle(0, y0, width, y1, fill=color_hex(col), outline=color_hex(col))
    for index in range(1, 6):
        y = height * (0.36 + index * 0.09)
        canvas.create_line(width * 0.08, y, width * 0.92, y, fill='#c8b8a8')


def draw_ground_shadow(canvas, local_vertices, radius, width, height, camera, focal, projection='orthographic'):
    if not local_vertices:
        return
    floor_z = min(vertex[2] for vertex in local_vertices) - max(2.0, radius * 0.05)
    points = []
    for vertex in local_vertices:
        dz = max(0.0, vertex[2] - floor_z)
        shadow_point = (
            vertex[0] - LIGHT_DIR[0] * dz / max(0.2, LIGHT_DIR[2]),
            vertex[1] - LIGHT_DIR[1] * dz / max(0.2, LIGHT_DIR[2]),
            floor_z,
        )
        points.append(project_point(shadow_point, camera, focal, width, height, projection))
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    center_x = (min_x + max_x) * 0.5
    center_y = max_y
    shadow_width = max(90.0, max_x - min_x)
    shadow_height = max(30.0, (max_y - min_y) * 0.22)
    for ring in range(6, 0, -1):
        alpha = ring / 6.0
        rx = shadow_width * alpha
        ry = shadow_height * alpha
        canvas.create_oval(center_x - rx, center_y - ry, center_x + rx, center_y + ry, fill='#6b5645', outline='')


def render_mesh(canvas, mesh, camera_state, preview_source='generated'):
    canvas.delete('all')
    width = max(1, canvas.winfo_width())
    height = max(1, canvas.winfo_height())
    draw_backdrop(canvas, width, height)
    if not mesh:
        return
    local_vertices, target = get_anchored_vertices(mesh, preview_source)
    camera = build_camera(mesh['radius'], target, camera_state)
    focal = min(width, height) * 0.95
    projection = camera_state.get('projection', 'orthographic')
    projected = [project_point(local, camera, focal, width, height, projection) for local in local_vertices]
    draw_ground_shadow(canvas, local_vertices, mesh['radius'], width, height, camera, focal, projection)
    base_color = (220, 162, 102)
    highlight_color = (255, 229, 198)
    shadow_color = (118, 74, 42)
    faces = []
    for triangle in mesh['triangles']:
        a = projected[triangle[0]]
        b = projected[triangle[1]]
        c = projected[triangle[2]]
        ar = local_vertices[triangle[0]]
        br = local_vertices[triangle[1]]
        cr = local_vertices[triangle[2]]
        edge1 = subtract(br, ar)
        edge2 = subtract(cr, ar)
        normal = normalize(cross(edge1, edge2))
        light = max(0.0, dot(normal, LIGHT_DIR))
        rim = pow(1.0 - abs(normal[2]), 1.8)
        facing = dot(normal, camera['forward'])
        depth = (a[2] + b[2] + c[2]) / 3.0
        faces.append((depth, facing, light, rim, triangle))
    faces.sort(key=lambda item: item[0])
    for depth, facing, light, rim, triangle in faces:
        if facing <= 0.0:
            continue
        pa = projected[triangle[0]]
        pb = projected[triangle[1]]
        pc = projected[triangle[2]]
        depth_fog = max(0.0, min(1.0, (depth + mesh['radius'] * 1.2) / (mesh['radius'] * 2.8 or 1.0)))
        lit_color = mix_color(shadow_color, highlight_color, 0.22 + light * 0.78)
        fill_color = mix_color(base_color, lit_color, 0.5 + rim * 0.22)
        fogged = mix_color(fill_color, (233, 225, 214), depth_fog * 0.28)
        canvas.create_polygon([pa[0], pa[1], pb[0], pb[1], pc[0], pc[1]], fill=color_hex(fogged), outline='')
