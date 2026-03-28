import io
import json
import math
import struct
import sys
import zipfile
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
REPO_ROOT = ROOT.parent
PB6_PATH = REPO_ROOT / "lampgen" / "pb6.py"
EXPORT_DIR = ROOT / "exports"


def load_pb6():
    spec = spec_from_file_location("pb6_module", PB6_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {PB6_PATH}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pb6 = load_pb6()
DEFAULT_PARAMS = asdict(pb6.LampParams())
PARAM_LIMITS = {
    "height": {"min": 80, "max": 260, "step": 1},
    "r_base": {"min": 18, "max": 80, "step": 1},
    "thickness": {"min": 0.8, "max": 4.0, "step": 0.05},
    "bulb_amp": {"min": 0.0, "max": 24.0, "step": 0.1},
    "bulb_count": {"min": 0.5, "max": 5.0, "step": 0.05},
    "bulb_phase": {"min": 0.0, "max": 1.0, "step": 0.01},
    "taper": {"min": 0.0, "max": 0.2, "step": 0.005},
    "seam_count": {"min": 6, "max": 36, "step": 1},
    "seam_pitch": {"min": 0.5, "max": 6.0, "step": 0.05},
    "seam_width": {"min": 1.0, "max": 10.0, "step": 0.1},
    "seam_height": {"min": 0.0, "max": 4.0, "step": 0.05},
    "seam_softness": {"min": 0.5, "max": 4.0, "step": 0.05},
    "valley_depth": {"min": 0.0, "max": 2.0, "step": 0.05},
    "counter_strength": {"min": 0.0, "max": 1.0, "step": 0.01},
    "counter_phase": {"min": 0.0, "max": 1.0, "step": 0.01},
    "membrane": {"min": 0.0, "max": 1.0, "step": 0.01},
    "perforation": {"min": 0.0, "max": 1.0, "step": 0.01},
    "inner_follow": {"min": 0.0, "max": 0.5, "step": 0.01},
    "rib_width_scale": {"min": 0.2, "max": 1.2, "step": 0.01},
    "rib_thickness": {"min": 0.2, "max": 3.0, "step": 0.05},
    "rib_seg_per_pitch": {"min": 18, "max": 120, "step": 1},
    "dome_height_scale": {"min": 0.1, "max": 0.8, "step": 0.01},
    "n_theta": {"min": 48, "max": 480, "step": 1},
    "n_z": {"min": 32, "max": 360, "step": 1},
}
PARAM_DESCRIPTIONS = {
    "height": "Altura total de la pieza en milimetros.",
    "r_base": "Radio base del volumen principal.",
    "thickness": "Espesor general de la pared o cascaron.",
    "bulb_amp": "Cuanto se infla y se contrae el perfil a lo largo de Z.",
    "bulb_count": "Cantidad de lobulos u ondas verticales en el perfil.",
    "bulb_phase": "Desfase del patron de lobulos sobre la altura.",
    "taper": "Cuanto se estrecha o abre la forma hacia arriba.",
    "seam_count": "Cantidad de costillas o familias de seam alrededor del perimetro.",
    "seam_pitch": "Paso helicoidal del seam a medida que sube en Z.",
    "seam_width": "Ancho de cada seam o relieve.",
    "seam_height": "Cuanto sobresale el seam respecto del cascaron.",
    "seam_softness": "Dureza o suavidad del perfil del seam.",
    "valley_depth": "Profundidad de los valles entre seams.",
    "counter_strength": "Influencia de la segunda familia de seams cruzados.",
    "counter_phase": "Desfase angular de la familia cruzada.",
    "membrane": "Cantidad de piel continua que queda detras del patron.",
    "perforation": "Cuanto se abre la perforacion entre costillas.",
    "inner_follow": "Cuanto acompana la cara interna al relieve exterior.",
    "rib_width_scale": "Escala del ancho de las costillas en modo perforado.",
    "rib_thickness": "Espesor fisico de cada costilla.",
    "rib_seg_per_pitch": "Resolucion de triangulos por paso helicoidal de costilla.",
    "dome_height_scale": "Altura relativa del cierre superior tipo domo.",
    "n_theta": "Resolucion angular de la malla.",
    "n_z": "Resolucion vertical de la malla.",
}
SAFE_FLOORS = {
    "height": 0.001,
    "thickness": 0.0,
    "seam_count": 1,
    "seam_width": 0.001,
    "seam_softness": 0.01,
    "rib_thickness": 0.0,
    "rib_seg_per_pitch": 3,
    "n_theta": 8,
    "n_z": 3,
}
PRESETS = {
    "default": DEFAULT_PARAMS,
    "tall_solid": {
        **DEFAULT_PARAMS,
        "height": 210.0,
        "r_base": 36.0,
        "bulb_amp": 10.5,
        "bulb_count": 2.4,
        "seam_pitch": 3.1,
        "seam_height": 2.0,
    },
    "woven_perforated": {
        **DEFAULT_PARAMS,
        "mode": "perforated",
        "close_top": True,
        "dome_mode": "perforated",
        "height": 180.0,
        "r_base": 34.0,
        "seam_count": 16,
        "seam_pitch": 2.5,
        "membrane": 0.15,
        "perforation": 0.55,
        "rib_width_scale": 0.82,
        "rib_thickness": 1.45,
    },
    "lantern": {
        **DEFAULT_PARAMS,
        "mode": "solid",
        "height": 160.0,
        "r_base": 42.0,
        "bulb_amp": 14.0,
        "bulb_count": 1.7,
        "taper": 0.02,
        "seam_width": 5.0,
        "seam_height": 1.2,
    },
    "compact_vase": {
        **DEFAULT_PARAMS,
        "height": 120.0,
        "r_base": 30.0,
        "bulb_amp": 4.5,
        "bulb_count": 1.55,
        "taper": 0.025,
        "seam_count": 14,
        "seam_pitch": 2.15,
        "seam_width": 3.2,
    },
    "tall_weave": {
        **DEFAULT_PARAMS,
        "height": 235.0,
        "r_base": 33.0,
        "bulb_amp": 9.0,
        "bulb_count": 2.7,
        "taper": 0.055,
        "seam_count": 20,
        "seam_pitch": 3.35,
        "seam_height": 2.05,
        "membrane": 0.22,
    },
    "orbital_lantern": {
        **DEFAULT_PARAMS,
        "height": 170.0,
        "r_base": 44.0,
        "bulb_amp": 16.0,
        "bulb_count": 1.35,
        "taper": 0.01,
        "seam_count": 22,
        "seam_width": 4.8,
        "seam_height": 1.0,
        "valley_depth": 0.35,
    },
    "ribbed_open": {
        **DEFAULT_PARAMS,
        "mode": "perforated",
        "close_top": False,
        "height": 185.0,
        "r_base": 36.0,
        "bulb_amp": 7.8,
        "bulb_count": 2.05,
        "seam_count": 18,
        "seam_pitch": 2.7,
        "rib_width_scale": 0.88,
        "rib_thickness": 1.55,
        "membrane": 0.08,
        "perforation": 0.72,
    },
}


def coerce_params(payload: dict[str, Any]) -> tuple[dict[str, Any], str, bool, str]:
    params = dict(DEFAULT_PARAMS)
    for key, default_value in DEFAULT_PARAMS.items():
        raw = payload.get(key, default_value)
        try:
            numeric = float(raw)
        except (TypeError, ValueError):
            numeric = float(default_value)

        if isinstance(default_value, int) and not isinstance(default_value, bool):
            value = int(round(numeric))
        else:
            value = numeric

        floor = SAFE_FLOORS.get(key)
        if floor is not None:
            value = max(floor, value)
            if isinstance(default_value, int) and not isinstance(default_value, bool):
                value = int(round(value))

        params[key] = value

    mode = payload.get("mode", "solid")
    if mode not in {"solid", "perforated"}:
        mode = "solid"

    dome_mode = payload.get("dome_mode", "solid")
    if dome_mode not in {"solid", "perforated"}:
        dome_mode = "solid"

    close_top = bool(payload.get("close_top", False))
    return params, mode, close_top, dome_mode


def build_triangles(payload: dict[str, Any], interactive: bool) -> tuple[dict[str, Any], list[tuple[Any, Any, Any]]]:
    params, mode, close_top, dome_mode = coerce_params(payload)

    if interactive:
        params["n_theta"] = min(params["n_theta"], 120)
        params["n_z"] = min(params["n_z"], 96)
        params["rib_seg_per_pitch"] = min(params["rib_seg_per_pitch"], 42)

    lamp_params = pb6.LampParams(**params)
    if mode == "solid":
        tris = pb6.make_mesh_solid(lamp_params)
    else:
        tris = pb6.make_mesh_perforated(lamp_params, close_top=close_top, dome_mode=dome_mode)

    return {
        "params": params,
        "mode": mode,
        "close_top": close_top,
        "dome_mode": dome_mode,
        "interactive": interactive,
    }, tris


def triangles_to_indexed_mesh(triangles: list[tuple[Any, Any, Any]]) -> dict[str, Any]:
    vertices: list[list[float]] = []
    vertex_map: dict[tuple[float, float, float], int] = {}
    indices: list[list[int]] = []
    bounds = {
        "min": [float("inf"), float("inf"), float("inf")],
        "max": [float("-inf"), float("-inf"), float("-inf")],
    }

    for tri in triangles:
        tri_indices = []
        for vertex in tri:
            key = (round(vertex[0], 6), round(vertex[1], 6), round(vertex[2], 6))
            idx = vertex_map.get(key)
            if idx is None:
                idx = len(vertices)
                vertex_map[key] = idx
                point = [float(key[0]), float(key[1]), float(key[2])]
                vertices.append(point)
                for axis in range(3):
                    bounds["min"][axis] = min(bounds["min"][axis], point[axis])
                    bounds["max"][axis] = max(bounds["max"][axis], point[axis])
            tri_indices.append(idx)
        indices.append(tri_indices)

    center = [
        (bounds["min"][0] + bounds["max"][0]) * 0.5,
        (bounds["min"][1] + bounds["max"][1]) * 0.5,
        (bounds["min"][2] + bounds["max"][2]) * 0.5,
    ]
    size = [
        bounds["max"][0] - bounds["min"][0],
        bounds["max"][1] - bounds["min"][1],
        bounds["max"][2] - bounds["min"][2],
    ]
    radius = max(size) * 0.5 if vertices else 1.0

    return {
        "vertices": vertices,
        "triangles": indices,
        "bounds": bounds,
        "center": center,
        "radius": radius,
        "triangle_count": len(indices),
        "vertex_count": len(vertices),
    }


def parse_binary_stl(data: bytes) -> list[tuple[Any, Any, Any]]:
    if len(data) < 84:
        raise ValueError("STL binary too small")
    count = struct.unpack_from("<I", data, 80)[0]
    expected = 84 + count * 50
    if len(data) < expected:
        raise ValueError("STL binary truncated")

    triangles = []
    offset = 84
    for _ in range(count):
        offset += 12
        v0 = struct.unpack_from("<3f", data, offset)
        offset += 12
        v1 = struct.unpack_from("<3f", data, offset)
        offset += 12
        v2 = struct.unpack_from("<3f", data, offset)
        offset += 12
        offset += 2
        triangles.append((v0, v1, v2))
    return triangles


def parse_ascii_stl(text: str) -> list[tuple[Any, Any, Any]]:
    triangles = []
    vertices = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("vertex "):
            continue
        parts = line.split()
        if len(parts) != 4:
            raise ValueError("Invalid ASCII STL vertex line")
        vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        if len(vertices) == 3:
            triangles.append((vertices[0], vertices[1], vertices[2]))
            vertices = []
    if not triangles:
        raise ValueError("No triangles found in ASCII STL")
    return triangles


def parse_stl(data: bytes) -> list[tuple[Any, Any, Any]]:
    header = data[:5].lower()
    if header == b"solid":
        try:
            return parse_ascii_stl(data.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            try:
                return parse_ascii_stl(data.decode("latin-1"))
            except ValueError:
                pass
    return parse_binary_stl(data)


def parse_transform_3mf(raw: str | None) -> tuple[float, ...]:
    if not raw:
        return (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
    parts = [float(value) for value in raw.split()]
    if len(parts) != 12:
        raise ValueError("Invalid 3MF transform")
    return tuple(parts)


def apply_transform(point: tuple[float, float, float], transform: tuple[float, ...]) -> tuple[float, float, float]:
    x, y, z = point
    return (
        transform[0] * x + transform[1] * y + transform[2] * z + transform[9],
        transform[3] * x + transform[4] * y + transform[5] * z + transform[10],
        transform[6] * x + transform[7] * y + transform[8] * z + transform[11],
    )


def multiply_transform(left: tuple[float, ...], right: tuple[float, ...]) -> tuple[float, ...]:
    return (
        left[0] * right[0] + left[1] * right[3] + left[2] * right[6],
        left[0] * right[1] + left[1] * right[4] + left[2] * right[7],
        left[0] * right[2] + left[1] * right[5] + left[2] * right[8],
        left[3] * right[0] + left[4] * right[3] + left[5] * right[6],
        left[3] * right[1] + left[4] * right[4] + left[5] * right[7],
        left[3] * right[2] + left[4] * right[5] + left[5] * right[8],
        left[6] * right[0] + left[7] * right[3] + left[8] * right[6],
        left[6] * right[1] + left[7] * right[4] + left[8] * right[7],
        left[6] * right[2] + left[7] * right[5] + left[8] * right[8],
        left[0] * right[9] + left[1] * right[10] + left[2] * right[11] + left[9],
        left[3] * right[9] + left[4] * right[10] + left[5] * right[11] + left[10],
        left[6] * right[9] + left[7] * right[10] + left[8] * right[11] + left[11],
    )


def parse_3mf(data: bytes) -> list[tuple[Any, Any, Any]]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        model_name = None
        for name in archive.namelist():
            lower = name.lower()
            if lower.endswith(".model") and "3d/" in lower:
                model_name = name
                break
        if model_name is None:
            raise ValueError("3MF missing .model payload")

        root = ElementTree.fromstring(archive.read(model_name))
        ns_uri = root.tag.split("}")[0].strip("{") if root.tag.startswith("{") else ""
        ns = {"m": ns_uri} if ns_uri else {}
        object_tag = "m:resources/m:object" if ns else "resources/object"
        mesh_tag = "m:mesh" if ns else "mesh"
        vertices_tag = "m:vertices" if ns else "vertices"
        triangles_tag = "m:triangles" if ns else "triangles"
        vertex_tag = "m:vertex" if ns else "vertex"
        triangle_tag = "m:triangle" if ns else "triangle"
        components_tag = "m:components" if ns else "components"
        component_tag = "m:component" if ns else "component"
        build_tag = "m:build/m:item" if ns else "build/item"

        objects: dict[str, dict[str, Any]] = {}
        for obj in root.findall(object_tag, ns):
            obj_id = obj.attrib.get("id")
            if not obj_id:
                continue
            entry: dict[str, Any] = {}
            mesh = obj.find(mesh_tag, ns)
            if mesh is not None:
                vertices_node = mesh.find(vertices_tag, ns)
                triangles_node = mesh.find(triangles_tag, ns)
                if vertices_node is not None and triangles_node is not None:
                    vertices = []
                    for vertex in vertices_node.findall(vertex_tag, ns):
                        vertices.append(
                            (
                                float(vertex.attrib["x"]),
                                float(vertex.attrib["y"]),
                                float(vertex.attrib["z"]),
                            )
                        )
                    tris = []
                    for tri in triangles_node.findall(triangle_tag, ns):
                        i0 = int(tri.attrib["v1"])
                        i1 = int(tri.attrib["v2"])
                        i2 = int(tri.attrib["v3"])
                        tris.append((vertices[i0], vertices[i1], vertices[i2]))
                    entry["triangles"] = tris

            components = obj.find(components_tag, ns)
            if components is not None:
                refs = []
                for component in components.findall(component_tag, ns):
                    refs.append(
                        (
                            component.attrib.get("objectid", ""),
                            parse_transform_3mf(component.attrib.get("transform")),
                        )
                    )
                entry["components"] = refs
            objects[obj_id] = entry

        if not objects:
            raise ValueError("3MF contains no objects")

        def resolve_object(object_id: str, parent_transform: tuple[float, ...], stack: set[str]) -> list[tuple[Any, Any, Any]]:
            if object_id not in objects:
                return []
            if object_id in stack:
                raise ValueError("3MF circular component reference")
            stack = set(stack)
            stack.add(object_id)
            entry = objects[object_id]
            tris = []
            for tri in entry.get("triangles", []):
                tris.append(tuple(apply_transform(vertex, parent_transform) for vertex in tri))
            for child_id, child_transform in entry.get("components", []):
                tris.extend(resolve_object(child_id, multiply_transform(parent_transform, child_transform), stack))
            return tris

        identity = parse_transform_3mf(None)
        triangles = []
        build_items = root.findall(build_tag, ns)
        if build_items:
            for item in build_items:
                object_id = item.attrib.get("objectid", "")
                transform = parse_transform_3mf(item.attrib.get("transform"))
                triangles.extend(resolve_object(object_id, transform, set()))
        else:
            for object_id in objects:
                triangles.extend(resolve_object(object_id, identity, set()))

        if not triangles:
            raise ValueError("3MF contains no triangles")
        return triangles


def decimate_triangles_for_preview(triangles: list[tuple[Any, Any, Any]], limit: int = 60000) -> list[tuple[Any, Any, Any]]:
    if len(triangles) <= limit:
        return triangles
    step = math.ceil(len(triangles) / limit)
    sampled = triangles[::step]
    return sampled[:limit]


def parse_mesh_file(name: str, data: bytes) -> list[tuple[Any, Any, Any]]:
    suffix = Path(name).suffix.lower()
    if suffix == ".stl":
        return parse_stl(data)
    if suffix == ".3mf":
        return parse_3mf(data)
    raise ValueError("Unsupported file type")


class Handler(BaseHTTPRequestHandler):
    server_version = "JouiVisualizer/0.1"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/config":
            self.send_json(
                {
                    "defaults": DEFAULT_PARAMS,
                    "limits": PARAM_LIMITS,
                    "descriptions": PARAM_DESCRIPTIONS,
                    "presets": PRESETS,
                    "modes": ["solid", "perforated"],
                    "dome_modes": ["solid", "perforated"],
                }
            )
            return

        if parsed.path == "/api/exports":
            files = [
                {"name": file.name, "size": file.stat().st_size}
                for file in sorted(EXPORT_DIR.glob("*.stl"), key=lambda p: p.stat().st_mtime, reverse=True)
            ]
            self.send_json({"files": files[:20]})
            return

        if parsed.path == "/api/download":
            name = parse_qs(parsed.query).get("name", [""])[0]
            path = (EXPORT_DIR / Path(name).name).resolve()
            if not path.exists() or path.parent != EXPORT_DIR.resolve():
                self.send_error(HTTPStatus.NOT_FOUND, "Export not found")
                return
            data = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/sla")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
            self.end_headers()
            self.wfile.write(data)
            return

        if parsed.path == "/" or parsed.path == "":
            return self.serve_static("index.html")

        return self.serve_static(parsed.path.lstrip("/"))

    def do_POST(self):
        if self.path not in {"/api/preview", "/api/export", "/api/import"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length or 0)
        if self.path == "/api/import":
            file_name = self.headers.get("X-Filename", "model.stl")
            try:
                triangles = parse_mesh_file(file_name, body)
            except ValueError as exc:
                self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            mesh = triangles_to_indexed_mesh(decimate_triangles_for_preview(triangles))
            self.send_json(
                {
                    "ok": True,
                    "file": Path(file_name).name,
                    "triangle_count": len(triangles),
                    "preview_triangle_count": mesh["triangle_count"],
                    "mesh": mesh,
                    "source": "import",
                }
            )
            return

        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON")
            return

        if self.path == "/api/preview":
            meta, tris = build_triangles(payload, interactive=True)
            mesh = triangles_to_indexed_mesh(tris)
            self.send_json({"meta": meta, "mesh": mesh})
            return

        meta, tris = build_triangles(payload, interactive=False)
        EXPORT_DIR.mkdir(exist_ok=True)
        params = meta["params"]
        file_name = (
            f"pb6_{meta['mode']}_h{int(params['height'])}_rb{int(params['r_base'])}"
            f"_sc{int(params['seam_count'])}_sp{params['seam_pitch']:.2f}.stl"
        )
        out_path = EXPORT_DIR / file_name
        pb6.write_binary_stl(str(out_path), tris)
        self.send_json(
            {
                "ok": True,
                "file": file_name,
                "path": str(out_path),
                "triangle_count": len(tris),
                "meta": meta,
            }
        )

    def serve_static(self, relative_path: str):
        safe_path = (STATIC_DIR / relative_path).resolve()
        if not safe_path.exists() or STATIC_DIR.resolve() not in safe_path.parents and safe_path != STATIC_DIR.resolve():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        if safe_path.is_dir():
            safe_path = safe_path / "index.html"
            if not safe_path.exists():
                self.send_error(HTTPStatus.NOT_FOUND, "File not found")
                return

        suffix = safe_path.suffix.lower()
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
        }
        data = safe_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_types.get(suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any):
        sys.stdout.write(f"{self.address_string()} - {format % args}\n")


def main():
    EXPORT_DIR.mkdir(exist_ok=True)
    host = "127.0.0.1"
    port = 8765
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"JouiVisualizer running at http://{host}:{port}")
    print(f"Exports folder: {EXPORT_DIR}")
    server.serve_forever()


if __name__ == "__main__":
    main()
