import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_geom import add_capped_ring, add_lofted_superellipse_ring


GENERATOR_ID = "lampbase_fit2"
GENERATOR_LABEL = "FitBase2 Morph"


@dataclass
class BaseParams:
    interface_type: str = "fit20_morph"
    socket_lower_x: float = 42.0
    socket_lower_y: float = 42.0
    socket_upper_x: float = 40.0
    socket_upper_y: float = 40.0
    socket_depth: float = 20.0
    socket_clearance: float = 0.9
    socket_wall: float = 3.4
    shell_lower_x: float = 52.0
    shell_lower_y: float = 52.0
    shell_upper_x: float = 58.0
    shell_upper_y: float = 58.0
    shell_mid_scale: float = 1.06
    shell_lip_height: float = 4.0
    shell_outer_gap: float = 2.6
    base_radius: float = 76.0
    base_height: float = 12.0
    floor_thickness: float = 5.0
    n_theta: int = 144
    shape_power: float = 3.2


LIMITS = {
    "socket_lower_x": {"min": 12.0, "max": 140.0, "step": 0.5},
    "socket_lower_y": {"min": 12.0, "max": 140.0, "step": 0.5},
    "socket_upper_x": {"min": 12.0, "max": 140.0, "step": 0.5},
    "socket_upper_y": {"min": 12.0, "max": 140.0, "step": 0.5},
    "socket_depth": {"min": 8.0, "max": 30.0, "step": 0.5},
    "socket_clearance": {"min": 0.2, "max": 2.0, "step": 0.05},
    "socket_wall": {"min": 2.0, "max": 10.0, "step": 0.1},
    "shell_lower_x": {"min": 18.0, "max": 180.0, "step": 0.5},
    "shell_lower_y": {"min": 18.0, "max": 180.0, "step": 0.5},
    "shell_upper_x": {"min": 18.0, "max": 180.0, "step": 0.5},
    "shell_upper_y": {"min": 18.0, "max": 180.0, "step": 0.5},
    "shell_mid_scale": {"min": 1.0, "max": 1.24, "step": 0.01},
    "shell_lip_height": {"min": 1.0, "max": 10.0, "step": 0.2},
    "shell_outer_gap": {"min": 0.8, "max": 8.0, "step": 0.1},
    "base_radius": {"min": 24.0, "max": 190.0, "step": 0.5},
    "base_height": {"min": 6.0, "max": 28.0, "step": 0.5},
    "floor_thickness": {"min": 2.0, "max": 12.0, "step": 0.1},
    "n_theta": {"min": 72, "max": 220, "step": 1},
    "shape_power": {"min": 2.2, "max": 7.0, "step": 0.1},
}


DESCRIPTIONS = {
    "socket_lower_x": "Ancho interior del encastre en la base del cabezal.",
    "socket_lower_y": "Profundidad interior del encastre en la base del cabezal.",
    "socket_upper_x": "Ancho interior del encastre a 20 mm de altura.",
    "socket_upper_y": "Profundidad interior del encastre a 20 mm de altura.",
    "socket_depth": "Profundidad total del encastre.",
    "socket_clearance": "Holgura para que el cabezal entre sin forzar.",
    "socket_wall": "Espesor minimo del cuerpo que sostiene el encastre.",
    "shell_lower_x": "Ancho exterior de la piel que abraza la base del cabezal.",
    "shell_lower_y": "Profundidad exterior de la piel en la base del cabezal.",
    "shell_upper_x": "Ancho exterior de la piel a 20 mm de altura.",
    "shell_upper_y": "Profundidad exterior de la piel a 20 mm de altura.",
    "shell_mid_scale": "Cuanto se infla la transicion para verse mas amorfa.",
    "shell_lip_height": "Altura extra del labio superior.",
    "shell_outer_gap": "Separacion visual entre cabezal y piel exterior.",
    "base_radius": "Radio del plato inferior de apoyo.",
    "base_height": "Altura del apoyo inferior.",
    "floor_thickness": "Piso macizo debajo del encastre.",
    "n_theta": "Resolucion del perfil.",
    "shape_power": "Redondeo general del perfil: alto = mas cuadrado.",
}


def _shape_power(shape_hint: str) -> float:
    if shape_hint == "angular":
        return 5.4
    if shape_hint == "oval":
        return 3.4
    return 2.7


def _safe_outer_axis(socket_axis: float, fit_axis: float, gap: float, wall: float) -> float:
    socket_radius = socket_axis * 0.5
    fit_radius = fit_axis * 0.5
    return max(socket_radius + wall + 1.2, fit_radius + gap)


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
        or lower_inner * 1.02
    )
    upper_inner = min(upper_inner, lower_inner * 1.24)

    lower_outer_x = float(footprint.get("fit_lower_diameter_x") or lower_inner * 1.18)
    lower_outer_y = float(footprint.get("fit_lower_diameter_y") or lower_inner * 1.18)
    upper_outer_x = float(footprint.get("fit_upper_diameter_x") or upper_inner * 1.18)
    upper_outer_y = float(footprint.get("fit_upper_diameter_y") or upper_inner * 1.18)

    socket_clearance = 0.75 if shape_hint == "angular" else 0.9
    socket_wall = 3.8 if shape_hint == "angular" else 3.4
    shell_outer_gap = 2.2 if shape_hint == "angular" else 2.8

    shell_lower_x = _safe_outer_axis(lower_inner, lower_outer_x, shell_outer_gap, socket_wall) * 2.0
    shell_lower_y = _safe_outer_axis(lower_inner, lower_outer_y, shell_outer_gap, socket_wall) * 2.0
    shell_upper_x = _safe_outer_axis(upper_inner, upper_outer_x, shell_outer_gap, socket_wall) * 2.0
    shell_upper_y = _safe_outer_axis(upper_inner, upper_outer_y, shell_outer_gap, socket_wall) * 2.0

    shell_span = max(shell_lower_x, shell_lower_y, shell_upper_x, shell_upper_y)
    base_radius = max(shell_span * 0.66, lower_inner * 0.72) + 8.0
    base_height = 10.0 if shape_hint == "round" else 12.0

    params = BaseParams(
        interface_type="fit20_morph",
        socket_lower_x=round(lower_inner, 1),
        socket_lower_y=round(lower_inner, 1),
        socket_upper_x=round(upper_inner, 1),
        socket_upper_y=round(upper_inner, 1),
        socket_depth=float(footprint.get("fit_depth_mm") or 20.0),
        socket_clearance=socket_clearance,
        socket_wall=socket_wall,
        shell_lower_x=round(shell_lower_x, 1),
        shell_lower_y=round(shell_lower_y, 1),
        shell_upper_x=round(shell_upper_x, 1),
        shell_upper_y=round(shell_upper_y, 1),
        shell_mid_scale=1.03 if shape_hint == "angular" else 1.08,
        shell_lip_height=3.5 if shape_hint == "angular" else 4.5,
        shell_outer_gap=shell_outer_gap,
        base_radius=round(base_radius, 1),
        base_height=base_height,
        shape_power=_shape_power(shape_hint),
    )
    return asdict(params)


def make_mesh(params: BaseParams):
    tris = []
    core_radius = max(2.0, min(params.socket_lower_x, params.socket_lower_y) * 0.1)
    add_capped_ring(tris, core_radius, params.base_radius, 0.0, params.base_height, params.n_theta)

    z_floor = params.base_height - params.floor_thickness
    z_mid = params.base_height + params.socket_depth * 0.52
    z_top = params.base_height + params.socket_depth
    z_lip = z_top + params.shell_lip_height

    lower_inner = (
        max(core_radius + 0.5, params.socket_lower_x * 0.5 + params.socket_clearance),
        max(core_radius + 0.5, params.socket_lower_y * 0.5 + params.socket_clearance),
    )
    upper_inner = (
        max(core_radius + 0.5, params.socket_upper_x * 0.5 + params.socket_clearance),
        max(core_radius + 0.5, params.socket_upper_y * 0.5 + params.socket_clearance),
    )

    lower_shell = (
        max(lower_inner[0] + params.socket_wall, params.shell_lower_x * 0.5),
        max(lower_inner[1] + params.socket_wall, params.shell_lower_y * 0.5),
    )
    upper_shell = (
        max(upper_inner[0] + params.socket_wall, params.shell_upper_x * 0.5),
        max(upper_inner[1] + params.socket_wall, params.shell_upper_y * 0.5),
    )
    mid_shell = (
        max(lower_shell[0], upper_shell[0]) * params.shell_mid_scale,
        max(lower_shell[1], upper_shell[1]) * params.shell_mid_scale,
    )
    mid_inner = (
        (lower_inner[0] * 0.52) + (upper_inner[0] * 0.48),
        (lower_inner[1] * 0.52) + (upper_inner[1] * 0.48),
    )
    lip_shell = (
        max(upper_shell[0] - params.shell_outer_gap * 0.4, upper_inner[0] + params.socket_wall),
        max(upper_shell[1] - params.shell_outer_gap * 0.4, upper_inner[1] + params.socket_wall),
    )

    add_lofted_superellipse_ring(
        tris,
        lower_inner=lower_inner,
        lower_outer=lower_shell,
        upper_inner=mid_inner,
        upper_outer=mid_shell,
        z0=z_floor,
        z1=z_mid,
        n_theta=params.n_theta,
        exponent=params.shape_power,
    )
    add_lofted_superellipse_ring(
        tris,
        lower_inner=mid_inner,
        lower_outer=mid_shell,
        upper_inner=upper_inner,
        upper_outer=upper_shell,
        z0=z_mid,
        z1=z_top,
        n_theta=params.n_theta,
        exponent=params.shape_power,
    )
    add_lofted_superellipse_ring(
        tris,
        lower_inner=upper_inner,
        lower_outer=upper_shell,
        upper_inner=upper_inner,
        upper_outer=lip_shell,
        z0=z_top,
        z1=z_lip,
        n_theta=params.n_theta,
        exponent=max(2.4, params.shape_power - 0.4),
    )
    return tris
