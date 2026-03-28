import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_geom import add_capped_ring, add_wave_ring


GENERATOR_ID = "lampbase_abs1"
GENERATOR_LABEL = "AuraBase"


@dataclass
class BaseParams:
    interface_type: str = "ring"
    interface_diameter: float = 42.0
    skirt_radius: float = 64.0
    skirt_height: float = 16.0
    wave_amp: float = 8.0
    wave_lobes: int = 6
    neck_radius: float = 20.0
    neck_height: float = 26.0
    plug_height: float = 16.0
    plug_wall: float = 2.4
    fit_clearance: float = 0.35
    cable_hole_radius: float = 4.0
    n_theta: int = 144


LIMITS = {
    "interface_diameter": {"min": 16.0, "max": 120.0, "step": 0.1},
    "skirt_radius": {"min": 24.0, "max": 160.0, "step": 0.5},
    "skirt_height": {"min": 8.0, "max": 40.0, "step": 0.5},
    "wave_amp": {"min": 0.0, "max": 24.0, "step": 0.5},
    "wave_lobes": {"min": 3, "max": 12, "step": 1},
    "neck_radius": {"min": 8.0, "max": 60.0, "step": 0.5},
    "neck_height": {"min": 8.0, "max": 80.0, "step": 0.5},
    "plug_height": {"min": 6.0, "max": 36.0, "step": 0.5},
    "plug_wall": {"min": 1.2, "max": 8.0, "step": 0.1},
    "fit_clearance": {"min": 0.0, "max": 1.2, "step": 0.05},
    "cable_hole_radius": {"min": 1.0, "max": 12.0, "step": 0.1},
    "n_theta": {"min": 72, "max": 220, "step": 1},
}


DESCRIPTIONS = {
    "interface_diameter": "Diametro de acople.",
    "skirt_radius": "Radio de la falda escultorica.",
    "skirt_height": "Altura de la falda.",
    "wave_amp": "Amplitud organica del borde.",
    "wave_lobes": "Cantidad de lobulos.",
    "neck_radius": "Radio del cuello central.",
    "neck_height": "Altura del cuello.",
    "plug_height": "Altura del acople.",
    "plug_wall": "Espesor del acople.",
    "fit_clearance": "Holgura radial.",
    "cable_hole_radius": "Paso de cable.",
    "n_theta": "Resolucion general.",
}


def suggest_defaults(mount: dict[str, Any], lamp_bounds=None, footprint: dict[str, Any] | None = None) -> dict[str, Any]:
    footprint = footprint or {}
    diameter = float(footprint.get("fit_lower_inner_diameter_safe") or footprint.get("fit_lower_inner_diameter") or mount.get("female_id_mm") or 36.0)
    footprint_avg = float(footprint.get("fit_lower_diameter_avg") or footprint.get("diameter_avg") or diameter)
    footprint_upper = float(footprint.get("fit_upper_diameter_avg") or footprint_avg)
    round_hint = str(footprint.get("shape_hint") or "round") == "round"
    params = BaseParams(
        interface_type="bayonet_female" if mount.get("type") == "bayonet_female" else "ring",
        interface_diameter=diameter,
        skirt_radius=round(max(diameter, footprint_avg * 0.72, footprint_upper * 0.68) + 16.0, 1),
        wave_amp=6.0 if round_hint else 10.0,
        wave_lobes=5 if round_hint else 7,
        neck_radius=round(max(14.0, diameter * 0.28, footprint_avg * 0.22), 1),
        neck_height=round(max(20.0, footprint_upper * 0.22), 1),
    )
    return asdict(params)


def make_mesh(params: BaseParams):
    tris = []
    add_wave_ring(
        tris,
        params.cable_hole_radius,
        params.skirt_radius,
        0.0,
        params.skirt_height,
        params.n_theta,
        params.wave_amp,
        params.wave_lobes,
    )
    add_capped_ring(
        tris,
        params.cable_hole_radius,
        max(params.neck_radius, params.cable_hole_radius + params.plug_wall),
        params.skirt_height,
        params.skirt_height + params.neck_height,
        params.n_theta,
    )
    interface_r = max(6.0, params.interface_diameter * 0.5 - params.fit_clearance)
    plug_outer = max(interface_r, params.cable_hole_radius + params.plug_wall)
    plug_inner = max(params.cable_hole_radius, plug_outer - params.plug_wall)
    plug_z0 = params.skirt_height + params.neck_height
    plug_z1 = plug_z0 + params.plug_height
    add_capped_ring(tris, plug_inner, plug_outer, plug_z0, plug_z1, params.n_theta)
    return tris
