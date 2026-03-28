import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_geom import add_capped_ring, add_superellipse_ring


GENERATOR_ID = "lampbase_abs2"
GENERATOR_LABEL = "OrbitBase"


@dataclass
class BaseParams:
    interface_type: str = "ring"
    interface_diameter: float = 42.0
    orbit_radius: float = 62.0
    orbit_thickness: float = 16.0
    orbit_height: float = 14.0
    waist_radius: float = 16.0
    waist_height: float = 20.0
    crown_radius: float = 28.0
    crown_height: float = 14.0
    plug_height: float = 14.0
    plug_wall: float = 2.4
    fit_clearance: float = 0.35
    cable_hole_radius: float = 4.0
    n_theta: int = 132


LIMITS = {
    "interface_diameter": {"min": 16.0, "max": 120.0, "step": 0.1},
    "orbit_radius": {"min": 24.0, "max": 160.0, "step": 0.5},
    "orbit_thickness": {"min": 8.0, "max": 40.0, "step": 0.5},
    "orbit_height": {"min": 8.0, "max": 28.0, "step": 0.5},
    "waist_radius": {"min": 8.0, "max": 60.0, "step": 0.5},
    "waist_height": {"min": 6.0, "max": 60.0, "step": 0.5},
    "crown_radius": {"min": 10.0, "max": 80.0, "step": 0.5},
    "crown_height": {"min": 6.0, "max": 40.0, "step": 0.5},
    "plug_height": {"min": 6.0, "max": 36.0, "step": 0.5},
    "plug_wall": {"min": 1.2, "max": 8.0, "step": 0.1},
    "fit_clearance": {"min": 0.0, "max": 1.2, "step": 0.05},
    "cable_hole_radius": {"min": 1.0, "max": 12.0, "step": 0.1},
    "n_theta": {"min": 72, "max": 220, "step": 1},
}


DESCRIPTIONS = {
    "interface_diameter": "Diametro de acople.",
    "orbit_radius": "Radio del aro bajo.",
    "orbit_thickness": "Espesor radial del aro.",
    "orbit_height": "Altura del aro.",
    "waist_radius": "Radio del cuello central.",
    "waist_height": "Altura del cuello.",
    "crown_radius": "Radio de la corona superior.",
    "crown_height": "Altura de la corona superior.",
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
    shape_hint = str(footprint.get("shape_hint") or "round")
    orbit = max(footprint_avg * 0.74, diameter) + 14.0
    params = BaseParams(
        interface_type="bayonet_female" if mount.get("type") == "bayonet_female" else "ring",
        interface_diameter=diameter,
        orbit_radius=round(max(orbit, footprint_upper * 0.7 + 10.0), 1),
        orbit_thickness=18.0 if shape_hint == "angular" else 14.0,
        waist_radius=round(max(12.0, diameter * 0.24, footprint_avg * 0.18), 1),
        crown_radius=round(max(20.0, diameter * 0.42, footprint_upper * 0.36), 1),
    )
    return asdict(params)


def make_mesh(params: BaseParams):
    tris = []
    orbit_inner = max(params.cable_hole_radius + 4.0, params.orbit_radius - params.orbit_thickness)
    add_capped_ring(tris, orbit_inner, params.orbit_radius, 0.0, params.orbit_height, params.n_theta)
    add_capped_ring(
        tris,
        params.cable_hole_radius,
        max(params.waist_radius, params.cable_hole_radius + params.plug_wall),
        params.orbit_height,
        params.orbit_height + params.waist_height,
        params.n_theta,
    )
    crown_z0 = params.orbit_height + params.waist_height
    crown_z1 = crown_z0 + params.crown_height
    inner_crown = max(params.cable_hole_radius, params.crown_radius - 8.0)
    add_superellipse_ring(tris, inner_crown, inner_crown, params.crown_radius, params.crown_radius, crown_z0, crown_z1, params.n_theta, 2.6)
    interface_r = max(6.0, params.interface_diameter * 0.5 - params.fit_clearance)
    plug_outer = max(interface_r, params.cable_hole_radius + params.plug_wall)
    plug_inner = max(params.cable_hole_radius, plug_outer - params.plug_wall)
    plug_z0 = crown_z1
    plug_z1 = plug_z0 + params.plug_height
    add_capped_ring(tris, plug_inner, plug_outer, plug_z0, plug_z1, params.n_theta)
    return tris
