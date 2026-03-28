import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_geom import add_box, add_capped_ring


GENERATOR_ID = "lampbase_brut2"
GENERATOR_LABEL = "BrutBase B"


@dataclass
class BaseParams:
    interface_type: str = "ring"
    interface_diameter: float = 42.0
    plinth_radius: float = 58.0
    plinth_height: float = 14.0
    tower_radius: float = 18.0
    tower_height: float = 28.0
    buttress_span: float = 64.0
    buttress_thickness: float = 12.0
    buttress_height: float = 24.0
    plug_height: float = 16.0
    plug_wall: float = 2.4
    fit_clearance: float = 0.35
    cable_hole_radius: float = 4.0
    n_theta: int = 96


LIMITS = {
    "interface_diameter": {"min": 16.0, "max": 120.0, "step": 0.1},
    "plinth_radius": {"min": 22.0, "max": 140.0, "step": 0.5},
    "plinth_height": {"min": 8.0, "max": 32.0, "step": 0.5},
    "tower_radius": {"min": 8.0, "max": 60.0, "step": 0.5},
    "tower_height": {"min": 8.0, "max": 80.0, "step": 0.5},
    "buttress_span": {"min": 24.0, "max": 140.0, "step": 0.5},
    "buttress_thickness": {"min": 6.0, "max": 40.0, "step": 0.5},
    "buttress_height": {"min": 8.0, "max": 60.0, "step": 0.5},
    "plug_height": {"min": 6.0, "max": 36.0, "step": 0.5},
    "plug_wall": {"min": 1.2, "max": 8.0, "step": 0.1},
    "fit_clearance": {"min": 0.0, "max": 1.2, "step": 0.05},
    "cable_hole_radius": {"min": 1.0, "max": 12.0, "step": 0.1},
    "n_theta": {"min": 48, "max": 180, "step": 1},
}


DESCRIPTIONS = {
    "interface_diameter": "Diametro de acople.",
    "plinth_radius": "Radio del plato inferior.",
    "plinth_height": "Altura del plato inferior.",
    "tower_radius": "Radio de la torre central.",
    "tower_height": "Altura de la torre central.",
    "buttress_span": "Separacion de los contrafuertes.",
    "buttress_thickness": "Espesor de los contrafuertes.",
    "buttress_height": "Altura de los contrafuertes.",
    "plug_height": "Altura del acople.",
    "plug_wall": "Espesor del acople.",
    "fit_clearance": "Holgura radial.",
    "cable_hole_radius": "Paso de cable central.",
    "n_theta": "Resolucion del cilindro.",
}


def suggest_defaults(mount: dict[str, Any], lamp_bounds=None, footprint: dict[str, Any] | None = None) -> dict[str, Any]:
    footprint = footprint or {}
    diameter = float(footprint.get("fit_lower_inner_diameter_safe") or footprint.get("fit_lower_inner_diameter") or mount.get("female_id_mm") or 36.0)
    footprint_avg = float(footprint.get("fit_lower_diameter_avg") or footprint.get("diameter_avg") or diameter)
    footprint_upper = float(footprint.get("fit_upper_diameter_avg") or footprint_avg)
    params = BaseParams(
        interface_type="bayonet_female" if mount.get("type") == "bayonet_female" else "ring",
        interface_diameter=diameter,
        plinth_radius=round(max(footprint_avg * 0.72, footprint_upper * 0.66, diameter * 0.9) + 18.0, 1),
        tower_radius=round(max(12.0, diameter * 0.26, footprint_avg * 0.22), 1),
        tower_height=round(max(18.0, footprint_upper * 0.26), 1),
        buttress_span=round(max(32.0, footprint_avg * 0.7, footprint_upper * 0.64), 1),
    )
    return asdict(params)


def make_mesh(params: BaseParams):
    tris = []
    add_capped_ring(tris, params.cable_hole_radius, params.plinth_radius, 0.0, params.plinth_height, params.n_theta)

    add_capped_ring(
        tris,
        params.cable_hole_radius,
        max(params.tower_radius, params.cable_hole_radius + params.plug_wall),
        params.plinth_height,
        params.plinth_height + params.tower_height,
        params.n_theta,
    )

    half_span = params.buttress_span * 0.5
    half_thick = params.buttress_thickness * 0.5
    z1 = params.plinth_height + params.buttress_height
    add_box(tris, -half_span, half_span, -half_thick, half_thick, params.plinth_height, z1)
    add_box(tris, -half_thick, half_thick, -half_span, half_span, params.plinth_height, z1)

    interface_r = max(6.0, params.interface_diameter * 0.5 - params.fit_clearance)
    plug_outer = max(interface_r, params.cable_hole_radius + params.plug_wall)
    plug_inner = max(params.cable_hole_radius, plug_outer - params.plug_wall)
    plug_z0 = params.plinth_height + params.tower_height
    plug_z1 = plug_z0 + params.plug_height
    add_capped_ring(tris, plug_inner, plug_outer, plug_z0, plug_z1, params.n_theta)
    return tris
