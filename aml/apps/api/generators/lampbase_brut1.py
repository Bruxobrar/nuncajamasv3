import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_geom import add_box, add_capped_ring, add_superellipse_ring


GENERATOR_ID = "lampbase_brut1"
GENERATOR_LABEL = "BrutBase A"


@dataclass
class BaseParams:
    interface_type: str = "ring"
    interface_diameter: float = 42.0
    base_width: float = 92.0
    base_depth: float = 92.0
    base_height: float = 18.0
    neck_width: float = 36.0
    neck_depth: float = 36.0
    neck_height: float = 24.0
    plug_height: float = 14.0
    plug_wall: float = 2.4
    fit_clearance: float = 0.35
    cable_hole_radius: float = 4.0
    n_theta: int = 96


LIMITS = {
    "interface_diameter": {"min": 16.0, "max": 120.0, "step": 0.1},
    "base_width": {"min": 30.0, "max": 180.0, "step": 0.5},
    "base_depth": {"min": 30.0, "max": 180.0, "step": 0.5},
    "base_height": {"min": 8.0, "max": 40.0, "step": 0.5},
    "neck_width": {"min": 14.0, "max": 120.0, "step": 0.5},
    "neck_depth": {"min": 14.0, "max": 120.0, "step": 0.5},
    "neck_height": {"min": 6.0, "max": 80.0, "step": 0.5},
    "plug_height": {"min": 6.0, "max": 36.0, "step": 0.5},
    "plug_wall": {"min": 1.2, "max": 8.0, "step": 0.1},
    "fit_clearance": {"min": 0.0, "max": 1.2, "step": 0.05},
    "cable_hole_radius": {"min": 1.0, "max": 12.0, "step": 0.1},
    "n_theta": {"min": 48, "max": 180, "step": 1},
}


DESCRIPTIONS = {
    "interface_diameter": "Diametro de acople efectivo de la lampara.",
    "base_width": "Ancho de la plataforma brutalista.",
    "base_depth": "Profundidad de la plataforma brutalista.",
    "base_height": "Espesor de la plataforma.",
    "neck_width": "Ancho del cuello portante.",
    "neck_depth": "Profundidad del cuello portante.",
    "neck_height": "Altura del cuello.",
    "plug_height": "Altura del acople superior.",
    "plug_wall": "Espesor del acople.",
    "fit_clearance": "Holgura radial.",
    "cable_hole_radius": "Paso de cable central.",
    "n_theta": "Resolucion del acople.",
}


def suggest_defaults(mount: dict[str, Any], lamp_bounds=None, footprint: dict[str, Any] | None = None) -> dict[str, Any]:
    footprint = footprint or {}
    diameter = float(footprint.get("fit_lower_inner_diameter_safe") or footprint.get("fit_lower_inner_diameter") or mount.get("female_id_mm") or 36.0)
    fx = float(footprint.get("fit_lower_diameter_x") or footprint.get("diameter_x") or diameter)
    fy = float(footprint.get("fit_lower_diameter_y") or footprint.get("diameter_y") or diameter)
    ux = float(footprint.get("fit_upper_diameter_x") or fx)
    uy = float(footprint.get("fit_upper_diameter_y") or fy)
    shape_hint = str(footprint.get("shape_hint") or "round")
    width = max(diameter * 1.25, fx * 1.1) + 20.0
    depth = max(diameter * 1.25, fy * 1.1) + 20.0
    if shape_hint == "angular":
        width += 10.0
        depth += 10.0
    params = BaseParams(
        interface_type="bayonet_female" if mount.get("type") == "bayonet_female" else "ring",
        interface_diameter=diameter,
        base_width=round(width, 1),
        base_depth=round(depth, 1),
        neck_width=round(max(24.0, fx * 0.4, ux * 0.54), 1),
        neck_depth=round(max(24.0, fy * 0.4, uy * 0.54), 1),
        neck_height=24.0,
    )
    return asdict(params)


def make_mesh(params: BaseParams):
    tris = []
    half_w = params.base_width * 0.5
    half_d = params.base_depth * 0.5
    add_box(tris, -half_w, half_w, -half_d, half_d, 0.0, params.base_height)

    nw = params.neck_width * 0.5
    nd = params.neck_depth * 0.5
    add_box(tris, -nw, nw, -nd, nd, params.base_height, params.base_height + params.neck_height)

    interface_r = max(6.0, params.interface_diameter * 0.5 - params.fit_clearance)
    plug_outer = max(interface_r, params.cable_hole_radius + params.plug_wall)
    plug_inner = max(params.cable_hole_radius, plug_outer - params.plug_wall)
    z0 = params.base_height + params.neck_height
    z1 = z0 + params.plug_height
    if params.interface_type == "bayonet_female":
        add_superellipse_ring(tris, plug_inner, plug_inner, max(nw, plug_outer), max(nd, plug_outer), params.base_height, z0, params.n_theta, 5.5)
    else:
        add_superellipse_ring(tris, plug_inner, plug_inner, max(nw, plug_outer), max(nd, plug_outer), params.base_height, z0, params.n_theta, 4.5)
    add_capped_ring(tris, plug_inner, plug_outer, z0, z1, params.n_theta)
    return tris
