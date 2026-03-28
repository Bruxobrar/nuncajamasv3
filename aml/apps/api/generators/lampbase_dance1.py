import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_geom import add_capped_ring, add_lofted_superellipse_ring, add_wave_ring


GENERATOR_ID = "lampbase_dance1"
GENERATOR_LABEL = "DanceBase1"


@dataclass
class BaseParams:
    interface_type: str = "fit20_dance"
    socket_lower_x: float = 42.0
    socket_lower_y: float = 42.0
    socket_upper_x: float = 46.0
    socket_upper_y: float = 46.0
    socket_depth: float = 20.0
    socket_clearance: float = 0.85
    socket_wall: float = 3.0
    plinth_radius: float = 74.0
    plinth_height: float = 12.0
    orbit_radius: float = 62.0
    orbit_height: float = 10.0
    orbit_wave_amp: float = 5.0
    orbit_wave_lobes: int = 6
    waist_x: float = 24.0
    waist_y: float = 24.0
    waist_height: float = 18.0
    shoulder1_x: float = 38.0
    shoulder1_y: float = 38.0
    shoulder2_x: float = 48.0
    shoulder2_y: float = 48.0
    crown_x: float = 56.0
    crown_y: float = 56.0
    crown_lip_height: float = 4.0
    crown_bloom: float = 1.08
    shape_power: float = 3.2
    n_theta: int = 144


LIMITS = {
    "socket_lower_x": {"min": 12.0, "max": 140.0, "step": 0.5},
    "socket_lower_y": {"min": 12.0, "max": 140.0, "step": 0.5},
    "socket_upper_x": {"min": 12.0, "max": 140.0, "step": 0.5},
    "socket_upper_y": {"min": 12.0, "max": 140.0, "step": 0.5},
    "socket_depth": {"min": 8.0, "max": 30.0, "step": 0.5},
    "socket_clearance": {"min": 0.2, "max": 2.0, "step": 0.05},
    "socket_wall": {"min": 2.0, "max": 10.0, "step": 0.1},
    "plinth_radius": {"min": 24.0, "max": 180.0, "step": 0.5},
    "plinth_height": {"min": 6.0, "max": 24.0, "step": 0.5},
    "orbit_radius": {"min": 18.0, "max": 160.0, "step": 0.5},
    "orbit_height": {"min": 6.0, "max": 24.0, "step": 0.5},
    "orbit_wave_amp": {"min": 0.0, "max": 18.0, "step": 0.5},
    "orbit_wave_lobes": {"min": 3, "max": 12, "step": 1},
    "waist_x": {"min": 10.0, "max": 120.0, "step": 0.5},
    "waist_y": {"min": 10.0, "max": 120.0, "step": 0.5},
    "waist_height": {"min": 8.0, "max": 60.0, "step": 0.5},
    "shoulder1_x": {"min": 12.0, "max": 160.0, "step": 0.5},
    "shoulder1_y": {"min": 12.0, "max": 160.0, "step": 0.5},
    "shoulder2_x": {"min": 12.0, "max": 160.0, "step": 0.5},
    "shoulder2_y": {"min": 12.0, "max": 160.0, "step": 0.5},
    "crown_x": {"min": 18.0, "max": 180.0, "step": 0.5},
    "crown_y": {"min": 18.0, "max": 180.0, "step": 0.5},
    "crown_lip_height": {"min": 1.0, "max": 10.0, "step": 0.2},
    "crown_bloom": {"min": 1.0, "max": 1.24, "step": 0.01},
    "shape_power": {"min": 2.2, "max": 7.0, "step": 0.1},
    "n_theta": {"min": 72, "max": 220, "step": 1},
}


DESCRIPTIONS = {
    "socket_lower_x": "Ancho interior del encastre al pie del cabezal.",
    "socket_lower_y": "Profundidad interior del encastre al pie del cabezal.",
    "socket_upper_x": "Ancho interior del encastre a 20 mm.",
    "socket_upper_y": "Profundidad interior del encastre a 20 mm.",
    "socket_depth": "Profundidad total del encastre.",
    "socket_clearance": "Holgura para que el cabezal entre bien.",
    "socket_wall": "Espesor minimo del cuerpo que sostiene el encastre.",
    "plinth_radius": "Radio del apoyo base, heredado del lado brutalista.",
    "plinth_height": "Altura del apoyo base.",
    "orbit_radius": "Radio del anillo de transicion que le da movimiento.",
    "orbit_height": "Altura del anillo de transicion.",
    "orbit_wave_amp": "Ondulacion del anillo.",
    "orbit_wave_lobes": "Cantidad de pulsos del anillo.",
    "waist_x": "Ancho de la cintura que conecta base y corona.",
    "waist_y": "Profundidad de la cintura que conecta base y corona.",
    "waist_height": "Altura de la cintura.",
    "shoulder1_x": "Primer hombro intermedio siguiendo la base del cabezal.",
    "shoulder1_y": "Primer hombro intermedio siguiendo la base del cabezal.",
    "shoulder2_x": "Segundo hombro intermedio siguiendo la apertura del cabezal.",
    "shoulder2_y": "Segundo hombro intermedio siguiendo la apertura del cabezal.",
    "crown_x": "Ancho de la corona que abraza al cabezal.",
    "crown_y": "Profundidad de la corona que abraza al cabezal.",
    "crown_lip_height": "Altura del labio superior.",
    "crown_bloom": "Cuanto florece la corona antes del acople.",
    "shape_power": "Redondeo general del perfil.",
    "n_theta": "Resolucion del modelo.",
}


def _shape_power(shape_hint: str) -> float:
    if shape_hint == "angular":
        return 5.0
    if shape_hint == "oval":
        return 3.5
    return 2.8


def _build_shell_slices(footprint: dict[str, Any], lower_inner: float, upper_inner: float, gap: float, wall: float) -> list[dict[str, float]]:
    raw_slices = footprint.get("fit_slices") or []
    shell_slices: list[dict[str, float]] = []
    for raw in raw_slices:
        outer_x = float(raw.get("diameter_x") or lower_inner)
        outer_y = float(raw.get("diameter_y") or lower_inner)
        inner_safe = float(raw.get("inner_diameter_safe") or raw.get("inner_diameter") or lower_inner)
        shell_slices.append({
            "z_mid": float(raw.get("z_mid") or 0.0),
            "inner_x": max(lower_inner * 0.5, inner_safe * 0.5),
            "inner_y": max(lower_inner * 0.5, inner_safe * 0.5),
            "outer_x": max(inner_safe * 0.5 + wall, outer_x * 0.5 + gap),
            "outer_y": max(inner_safe * 0.5 + wall, outer_y * 0.5 + gap),
        })
    if not shell_slices:
        shell_slices = [
            {"z_mid": 0.0, "inner_x": lower_inner * 0.5, "inner_y": lower_inner * 0.5, "outer_x": lower_inner * 0.5 + wall + gap, "outer_y": lower_inner * 0.5 + wall + gap},
            {"z_mid": 20.0, "inner_x": upper_inner * 0.5, "inner_y": upper_inner * 0.5, "outer_x": upper_inner * 0.5 + wall + gap, "outer_y": upper_inner * 0.5 + wall + gap},
        ]
    return shell_slices


def suggest_defaults(mount: dict[str, Any], lamp_bounds=None, footprint: dict[str, Any] | None = None) -> dict[str, Any]:
    footprint = footprint or {}
    shape_hint = str(footprint.get("shape_hint") or "round")

    lower_inner = float(
        footprint.get("fit_lower_inner_diameter_safe")
        or footprint.get("fit_lower_inner_diameter")
        or mount.get("female_id_mm")
        or 42.0
    )
    upper_inner = float(
        footprint.get("fit_upper_inner_diameter_safe")
        or footprint.get("fit_upper_inner_diameter")
        or lower_inner * 1.04
    )
    upper_inner = min(upper_inner, lower_inner * 1.22)

    lower_x = float(footprint.get("fit_lower_diameter_x") or footprint.get("diameter_x") or lower_inner)
    lower_y = float(footprint.get("fit_lower_diameter_y") or footprint.get("diameter_y") or lower_inner)
    upper_x = float(footprint.get("fit_upper_diameter_x") or lower_x)
    upper_y = float(footprint.get("fit_upper_diameter_y") or lower_y)
    shell_slices = _build_shell_slices(
        footprint,
        lower_inner=lower_inner,
        upper_inner=upper_inner,
        gap=2.0 if shape_hint == "angular" else 2.4,
        wall=3.4 if shape_hint == "angular" else 3.0,
    )

    crown_slice = shell_slices[min(len(shell_slices) - 1, 1)]
    mid_slice = shell_slices[min(len(shell_slices) - 1, 2)]
    upper_mid_slice = shell_slices[min(len(shell_slices) - 1, 3)]
    crown_x = max(lower_x * 0.98, crown_slice["outer_x"] * 2.0, lower_inner + 8.0)
    crown_y = max(lower_y * 0.98, crown_slice["outer_y"] * 2.0, lower_inner + 8.0)
    orbit_radius = max(crown_x, crown_y) * 0.54 + 10.0
    plinth_radius = max(orbit_radius * 1.12, max(lower_x, lower_y) * 0.58 + 16.0)

    params = BaseParams(
        interface_type="fit20_dance",
        socket_lower_x=round(lower_inner, 1),
        socket_lower_y=round(lower_inner, 1),
        socket_upper_x=round(upper_inner, 1),
        socket_upper_y=round(upper_inner, 1),
        socket_depth=float(footprint.get("fit_depth_mm") or 20.0),
        socket_clearance=0.75 if shape_hint == "angular" else 0.9,
        socket_wall=3.4 if shape_hint == "angular" else 3.0,
        plinth_radius=round(plinth_radius, 1),
        plinth_height=12.0 if shape_hint == "angular" else 10.0,
        orbit_radius=round(orbit_radius, 1),
        orbit_height=10.0,
        orbit_wave_amp=3.0 if shape_hint == "angular" else (4.0 if shape_hint == "oval" else 5.5),
        orbit_wave_lobes=4 if shape_hint == "angular" else (5 if shape_hint == "oval" else 6),
        waist_x=round(max(lower_inner * 0.46, mid_slice["outer_x"] * 0.92), 1),
        waist_y=round(max(lower_inner * 0.46, mid_slice["outer_y"] * 0.92), 1),
        waist_height=18.0 if shape_hint == "angular" else 20.0,
        shoulder1_x=round(max(mid_slice["outer_x"] * 2.0, lower_x * 0.88), 1),
        shoulder1_y=round(max(mid_slice["outer_y"] * 2.0, lower_y * 0.88), 1),
        shoulder2_x=round(max(upper_mid_slice["outer_x"] * 2.0, upper_x * 0.84), 1),
        shoulder2_y=round(max(upper_mid_slice["outer_y"] * 2.0, upper_y * 0.84), 1),
        crown_x=round(crown_x, 1),
        crown_y=round(crown_y, 1),
        crown_lip_height=3.0 if shape_hint == "angular" else 4.5,
        crown_bloom=1.04 if shape_hint == "angular" else 1.1,
        shape_power=_shape_power(shape_hint),
    )
    return asdict(params)


def make_mesh(params: BaseParams):
    tris = []
    core_radius = 4.0
    add_capped_ring(tris, core_radius, params.plinth_radius, 0.0, params.plinth_height, params.n_theta)

    orbit_inner = max(core_radius + 5.0, params.orbit_radius - max(10.0, params.orbit_radius * 0.26))
    add_wave_ring(
        tris,
        orbit_inner,
        params.orbit_radius,
        params.plinth_height * 0.2,
        params.plinth_height + params.orbit_height,
        params.n_theta,
        params.orbit_wave_amp,
        params.orbit_wave_lobes,
    )

    z_socket0 = params.plinth_height + params.orbit_height * 0.72
    z_socket1 = z_socket0 + params.socket_depth
    z_lip = z_socket1 + params.crown_lip_height

    lower_inner = (
        max(core_radius + 0.5, params.socket_lower_x * 0.5 + params.socket_clearance),
        max(core_radius + 0.5, params.socket_lower_y * 0.5 + params.socket_clearance),
    )
    upper_inner = (
        max(core_radius + 0.5, params.socket_upper_x * 0.5 + params.socket_clearance),
        max(core_radius + 0.5, params.socket_upper_y * 0.5 + params.socket_clearance),
    )
    waist_outer = (
        max(lower_inner[0] + params.socket_wall, params.waist_x * 0.5),
        max(lower_inner[1] + params.socket_wall, params.waist_y * 0.5),
    )
    crown_outer = (
        max(upper_inner[0] + params.socket_wall, params.crown_x * 0.5),
        max(upper_inner[1] + params.socket_wall, params.crown_y * 0.5),
    )
    shoulder1_outer = (
        max(lower_inner[0] + params.socket_wall, params.shoulder1_x * 0.5),
        max(lower_inner[1] + params.socket_wall, params.shoulder1_y * 0.5),
    )
    shoulder2_outer = (
        max(upper_inner[0] + params.socket_wall, params.shoulder2_x * 0.5),
        max(upper_inner[1] + params.socket_wall, params.shoulder2_y * 0.5),
    )
    bloom_outer = (
        crown_outer[0] * params.crown_bloom,
        crown_outer[1] * params.crown_bloom,
    )
    profile_points = [
        (z_socket0, lower_inner, waist_outer),
        (z_socket0 + params.socket_depth * 0.25, (lower_inner[0] * 0.9 + upper_inner[0] * 0.1, lower_inner[1] * 0.9 + upper_inner[1] * 0.1), shoulder1_outer),
        (z_socket0 + params.socket_depth * 0.5, (lower_inner[0] * 0.65 + upper_inner[0] * 0.35, lower_inner[1] * 0.65 + upper_inner[1] * 0.35), shoulder2_outer),
        (z_socket0 + params.socket_depth * 0.75, (lower_inner[0] * 0.3 + upper_inner[0] * 0.7, lower_inner[1] * 0.3 + upper_inner[1] * 0.7), (shoulder2_outer[0] * 0.45 + crown_outer[0] * 0.55, shoulder2_outer[1] * 0.45 + crown_outer[1] * 0.55)),
        (z_socket1, upper_inner, crown_outer),
    ]
    for index in range(len(profile_points) - 1):
        z0, inner0, outer0 = profile_points[index]
        z1, inner1, outer1 = profile_points[index + 1]
        add_lofted_superellipse_ring(
            tris,
            lower_inner=inner0,
            lower_outer=outer0,
            upper_inner=inner1,
            upper_outer=outer1,
            z0=z0,
            z1=z1,
            n_theta=params.n_theta,
            exponent=params.shape_power,
        )
    add_lofted_superellipse_ring(
        tris,
        lower_inner=upper_inner,
        lower_outer=crown_outer,
        upper_inner=upper_inner,
        upper_outer=bloom_outer,
        z0=z_socket1,
        z1=z_lip,
        n_theta=params.n_theta,
        exponent=max(2.4, params.shape_power - 0.3),
    )
    return tris
