import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_geom import add_capped_ring, add_lofted_superellipse_ring


GENERATOR_ID = "lampbase_fit20"
GENERATOR_LABEL = "FitBase 20mm"


@dataclass
class BaseParams:
    interface_type: str = "ring"
    socket_lower_x: float = 42.0
    socket_lower_y: float = 42.0
    socket_upper_x: float = 40.0
    socket_upper_y: float = 40.0
    socket_depth: float = 20.0
    socket_wall: float = 4.0
    socket_clearance: float = 0.8
    plinth_radius: float = 72.0
    plinth_height: float = 18.0
    floor_thickness: float = 5.0
    n_theta: int = 120
    shape_power: float = 4.0


LIMITS = {
    "socket_lower_x": {"min": 12.0, "max": 140.0, "step": 0.5},
    "socket_lower_y": {"min": 12.0, "max": 140.0, "step": 0.5},
    "socket_upper_x": {"min": 12.0, "max": 140.0, "step": 0.5},
    "socket_upper_y": {"min": 12.0, "max": 140.0, "step": 0.5},
    "socket_depth": {"min": 8.0, "max": 30.0, "step": 0.5},
    "socket_wall": {"min": 2.0, "max": 12.0, "step": 0.1},
    "socket_clearance": {"min": 0.2, "max": 2.0, "step": 0.05},
    "plinth_radius": {"min": 28.0, "max": 180.0, "step": 0.5},
    "plinth_height": {"min": 8.0, "max": 40.0, "step": 0.5},
    "floor_thickness": {"min": 2.0, "max": 12.0, "step": 0.1},
    "n_theta": {"min": 72, "max": 220, "step": 1},
    "shape_power": {"min": 2.2, "max": 7.0, "step": 0.1},
}


DESCRIPTIONS = {
    "socket_lower_x": "Ancho interior del encastre en la base del cabezal.",
    "socket_lower_y": "Profundidad interior del encastre en la base del cabezal.",
    "socket_upper_x": "Ancho interior del encastre a 20 mm de altura.",
    "socket_upper_y": "Profundidad interior del encastre a 20 mm de altura.",
    "socket_depth": "Profundidad del encastre hembra.",
    "socket_wall": "Espesor de pared del socket.",
    "socket_clearance": "Holgura para que el cabezal entre sin trabarse.",
    "plinth_radius": "Radio del apoyo inferior.",
    "plinth_height": "Altura del plato inferior.",
    "floor_thickness": "Piso de apoyo bajo el socket.",
    "n_theta": "Resolucion del perfil.",
    "shape_power": "Redondeo del perfil: mas alto, mas cuadrado.",
}


def suggest_defaults(mount: dict[str, Any], lamp_bounds=None, footprint: dict[str, Any] | None = None) -> dict[str, Any]:
    footprint = footprint or {}
    lower_inner = float(footprint.get("fit_lower_inner_diameter_safe") or footprint.get("fit_lower_inner_diameter") or mount.get("female_id_mm") or 42.0)
    upper_inner = float(footprint.get("fit_upper_inner_diameter_safe") or footprint.get("fit_upper_inner_diameter") or lower_inner * 1.02)
    upper_inner = min(upper_inner, lower_inner * 1.28)
    lower_x = lower_inner
    lower_y = lower_inner
    upper_x = upper_inner
    upper_y = upper_inner
    shape_hint = str(footprint.get("shape_hint") or "round")
    outer_span = max(
        lower_x,
        lower_y,
        upper_x,
        upper_y,
        float(footprint.get("fit_lower_diameter_avg") or lower_x),
    )
    params = BaseParams(
        interface_type="fit20",
        socket_lower_x=round(lower_x, 1),
        socket_lower_y=round(lower_y, 1),
        socket_upper_x=round(upper_x, 1),
        socket_upper_y=round(upper_y, 1),
        socket_depth=float(footprint.get("fit_depth_mm") or 20.0),
        plinth_radius=round(outer_span * 0.72 + 20.0, 1),
        shape_power=5.2 if shape_hint == "angular" else (3.2 if shape_hint == "oval" else 2.6),
    )
    return asdict(params)


def make_mesh(params: BaseParams):
    tris = []
    core_radius = max(2.0, min(params.socket_lower_x, params.socket_lower_y, params.socket_upper_x, params.socket_upper_y) * 0.12)
    add_capped_ring(tris, core_radius, params.plinth_radius, 0.0, params.plinth_height, params.n_theta)

    lower_inner = (
        max(core_radius + 0.5, params.socket_lower_x * 0.5 + params.socket_clearance),
        max(core_radius + 0.5, params.socket_lower_y * 0.5 + params.socket_clearance),
    )
    upper_inner = (
        max(core_radius + 0.5, params.socket_upper_x * 0.5 + params.socket_clearance),
        max(core_radius + 0.5, params.socket_upper_y * 0.5 + params.socket_clearance),
    )
    lower_outer = (lower_inner[0] + params.socket_wall, lower_inner[1] + params.socket_wall)
    upper_outer = (upper_inner[0] + params.socket_wall, upper_inner[1] + params.socket_wall)

    z0 = params.plinth_height - params.floor_thickness
    z1 = params.plinth_height + params.socket_depth
    add_lofted_superellipse_ring(
        tris,
        lower_inner=lower_inner,
        lower_outer=lower_outer,
        upper_inner=upper_inner,
        upper_outer=upper_outer,
        z0=z0,
        z1=z1,
        n_theta=params.n_theta,
        exponent=params.shape_power,
    )
    return tris
