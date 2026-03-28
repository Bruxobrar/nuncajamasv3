import math
from dataclasses import asdict, dataclass
from typing import Any

GENERATOR_ID = "lampbase2"
GENERATOR_LABEL = "LampBase2"


Triangle = tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]


def polar(radius: float, theta: float, z: float) -> tuple[float, float, float]:
    return (radius * math.cos(theta), radius * math.sin(theta), z)


def add_quad(tris: list[Triangle], v00, v10, v11, v01, flip: bool = False):
    if not flip:
        tris.append((v00, v10, v11))
        tris.append((v00, v11, v01))
    else:
        tris.append((v00, v11, v10))
        tris.append((v00, v01, v11))


def add_annulus_cap(tris: list[Triangle], r_in: float, r_out: float, z: float, n_theta: int, flip: bool = False):
    for i in range(n_theta):
        t0 = (2.0 * math.pi * i) / n_theta
        t1 = (2.0 * math.pi * (i + 1)) / n_theta
        o0 = polar(r_out, t0, z)
        o1 = polar(r_out, t1, z)
        i0 = polar(r_in, t0, z)
        i1 = polar(r_in, t1, z)
        add_quad(tris, i0, o0, o1, i1, flip=flip)


def add_capped_ring(tris: list[Triangle], r_in: float, r_out: float, z0: float, z1: float, n_theta: int):
    for i in range(n_theta):
        t0 = (2.0 * math.pi * i) / n_theta
        t1 = (2.0 * math.pi * (i + 1)) / n_theta

        o00 = polar(r_out, t0, z0)
        o01 = polar(r_out, t1, z0)
        o10 = polar(r_out, t0, z1)
        o11 = polar(r_out, t1, z1)
        add_quad(tris, o00, o10, o11, o01)

        if r_in > 0.0:
            i00 = polar(r_in, t0, z0)
            i01 = polar(r_in, t1, z0)
            i10 = polar(r_in, t0, z1)
            i11 = polar(r_in, t1, z1)
            add_quad(tris, i00, i01, i11, i10)
        else:
            center0 = (0.0, 0.0, z0)
            center1 = (0.0, 0.0, z1)
            tris.append((center0, o01, o00))
            tris.append((center1, o10, o11))

    if r_in > 0.0:
        add_annulus_cap(tris, r_in, r_out, z0, n_theta, flip=True)
        add_annulus_cap(tris, r_in, r_out, z1, n_theta, flip=False)


def add_lug(
    tris: list[Triangle],
    radius: float,
    lug_radial: float,
    z0: float,
    z1: float,
    theta_center: float,
    theta_width: float,
    n_theta: int = 12,
):
    a0 = theta_center - theta_width / 2.0
    a1 = theta_center + theta_width / 2.0
    r0 = radius
    r1 = radius + lug_radial
    for i in range(n_theta):
        t0 = a0 + (a1 - a0) * i / n_theta
        t1 = a0 + (a1 - a0) * (i + 1) / n_theta
        p000 = polar(r0, t0, z0)
        p001 = polar(r0, t1, z0)
        p010 = polar(r0, t0, z1)
        p011 = polar(r0, t1, z1)
        p100 = polar(r1, t0, z0)
        p101 = polar(r1, t1, z0)
        p110 = polar(r1, t0, z1)
        p111 = polar(r1, t1, z1)

        add_quad(tris, p100, p110, p111, p101)
        add_quad(tris, p000, p001, p011, p010)
        add_quad(tris, p000, p100, p101, p001)
        add_quad(tris, p010, p011, p111, p110)
        if i == 0:
            add_quad(tris, p000, p010, p110, p100)
        if i == n_theta - 1:
            add_quad(tris, p001, p101, p111, p011)


@dataclass
class BaseParams:
    interface_type: str = "ring"
    interface_diameter: float = 42.0
    base_radius: float = 68.0
    base_height: float = 16.0
    stem_outer_diameter: float = 28.0
    stem_height: float = 20.0
    plug_height: float = 16.0
    plug_wall: float = 2.4
    fit_clearance: float = 0.35
    cable_hole_radius: float = 4.0
    n_theta: int = 120
    n_lugs: int = 3
    twist_deg: float = 70.0
    lug_deg: float = 16.0
    mount_height: float = 14.0
    lug_thickness_z: float = 2.2
    lug_radial: float = 2.0


LIMITS: dict[str, dict[str, float]] = {
    "interface_diameter": {"min": 16.0, "max": 120.0, "step": 0.1},
    "base_radius": {"min": 22.0, "max": 160.0, "step": 0.5},
    "base_height": {"min": 6.0, "max": 40.0, "step": 0.5},
    "stem_outer_diameter": {"min": 8.0, "max": 80.0, "step": 0.5},
    "stem_height": {"min": 4.0, "max": 80.0, "step": 0.5},
    "plug_height": {"min": 4.0, "max": 40.0, "step": 0.5},
    "plug_wall": {"min": 1.2, "max": 8.0, "step": 0.1},
    "fit_clearance": {"min": 0.0, "max": 1.2, "step": 0.05},
    "cable_hole_radius": {"min": 1.0, "max": 12.0, "step": 0.1},
    "n_theta": {"min": 48, "max": 240, "step": 1},
    "n_lugs": {"min": 2, "max": 6, "step": 1},
    "twist_deg": {"min": 30.0, "max": 120.0, "step": 1.0},
    "lug_deg": {"min": 8.0, "max": 26.0, "step": 1.0},
    "mount_height": {"min": 6.0, "max": 30.0, "step": 0.5},
    "lug_thickness_z": {"min": 0.8, "max": 6.0, "step": 0.1},
    "lug_radial": {"min": 0.5, "max": 6.0, "step": 0.1},
}


DESCRIPTIONS: dict[str, str] = {
    "interface_diameter": "Diametro interno efectivo de la lampara que la base debe calzar.",
    "base_radius": "Radio general de apoyo de la base.",
    "base_height": "Espesor de la base principal.",
    "stem_outer_diameter": "Diametro del cuello que sostiene el conector.",
    "stem_height": "Altura entre la base y el comienzo del conector.",
    "plug_height": "Altura del plug cilindrico o spigot.",
    "plug_wall": "Espesor del plug macho.",
    "fit_clearance": "Holgura radial para que el calce no quede demasiado duro.",
    "cable_hole_radius": "Canal central para el cable.",
    "n_theta": "Resolucion angular de la base.",
    "n_lugs": "Cantidad de lugs si el conector es bayoneta.",
    "twist_deg": "Grados de giro para trabar bayoneta.",
    "lug_deg": "Ancho angular de cada lug.",
    "mount_height": "Altura util del conector bayoneta.",
    "lug_thickness_z": "Espesor del lug en altura.",
    "lug_radial": "Saliente radial del lug.",
}


def suggest_defaults(
    mount: dict[str, Any],
    lamp_bounds: dict[str, list[float]] | None = None,
    footprint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    footprint = footprint or {}
    female_id = float(
        footprint.get("fit_lower_inner_diameter_safe")
        or footprint.get("fit_lower_inner_diameter")
        or mount.get("female_id_mm")
        or 36.0
    )
    mount_type = str(mount.get("type") or "ring")
    lamp_radius = female_id * 0.9
    lamp_height = 180.0
    if lamp_bounds:
        mins = lamp_bounds.get("min") or [0.0, 0.0, 0.0]
        maxs = lamp_bounds.get("max") or [0.0, 0.0, 0.0]
        lamp_radius = max(abs(float(mins[0])), abs(float(maxs[0])), abs(float(mins[1])), abs(float(maxs[1])))
        lamp_height = max(40.0, float(maxs[2]) - float(mins[2]))

    lower_outer = float(footprint.get("fit_lower_diameter_avg") or footprint.get("diameter_avg") or female_id)
    upper_outer = float(footprint.get("fit_upper_diameter_avg") or lower_outer)
    footprint_diameter = max(
        female_id,
        lower_outer,
        upper_outer,
        float(footprint.get("diameter_avg") or 0.0),
        float(footprint.get("radius_p90") or 0.0) * 2.0,
    )
    footprint_radius = max(
        female_id * 0.5,
        lower_outer * 0.5,
        upper_outer * 0.48,
        float(footprint.get("radius_p90") or 0.0),
    )

    base_radius = max(female_id * 0.9, lamp_radius * 0.58, footprint_radius * 1.08) + 14.0
    stem_outer_diameter = max(18.0, female_id * 0.58, footprint_diameter * 0.6)
    stem_height = max(10.0, min(32.0, lamp_height * 0.12))
    plug_height = 16.0 if mount_type == "bayonet_female" else 14.0

    params = BaseParams(
        interface_type="bayonet_female" if mount_type == "bayonet_female" else "ring",
        interface_diameter=female_id,
        base_radius=round(base_radius, 1),
        base_height=16.0,
        stem_outer_diameter=round(stem_outer_diameter, 1),
        stem_height=round(stem_height, 1),
        plug_height=plug_height,
        plug_wall=2.4,
        fit_clearance=0.35,
        cable_hole_radius=4.0,
        n_theta=120,
    )
    return asdict(params)


def make_mesh(params: BaseParams) -> list[Triangle]:
    tris: list[Triangle] = []

    core_radius = max(0.5, params.cable_hole_radius)
    base_outer = max(params.base_radius, core_radius + 6.0)
    interface_radius = max(6.0, params.interface_diameter / 2.0 - params.fit_clearance)
    plug_outer = max(core_radius + params.plug_wall, interface_radius)
    plug_inner = max(core_radius, plug_outer - params.plug_wall)
    stem_outer = max(params.stem_outer_diameter / 2.0, core_radius + params.plug_wall + 1.0, plug_inner)
    plug_z0 = params.base_height + params.stem_height
    plug_z1 = plug_z0 + params.plug_height

    add_capped_ring(tris, core_radius, base_outer, 0.0, params.base_height, params.n_theta)
    add_capped_ring(tris, core_radius, stem_outer, params.base_height, plug_z0, params.n_theta)

    if params.interface_type == "bayonet_female":
        add_capped_ring(tris, core_radius, max(stem_outer, plug_outer - params.lug_radial * 0.4), params.base_height, plug_z0, params.n_theta)
        add_capped_ring(tris, plug_inner, plug_outer, plug_z0, plug_z1, params.n_theta)

        lug_step = 2.0 * math.pi / max(1, params.n_lugs)
        lug_width = math.radians(params.lug_deg)
        lug_z0 = plug_z0 + max(0.0, params.mount_height - params.lug_thickness_z)
        lug_z1 = plug_z0 + params.mount_height
        for index in range(params.n_lugs):
            add_lug(
                tris,
                plug_outer,
                params.lug_radial,
                lug_z0,
                lug_z1,
                index * lug_step,
                lug_width,
                n_theta=12,
            )
    else:
        add_capped_ring(tris, plug_inner, plug_outer, plug_z0, plug_z1, params.n_theta)

    return tris
