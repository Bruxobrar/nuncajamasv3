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
from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
REPO_ROOT = ROOT.parent
EXPORT_DIR = ROOT / "exports"
ENGINE_FILES = {
    "pb": REPO_ROOT / "lampgen" / "pb.py",
    "pb2": REPO_ROOT / "lampgen" / "pb2.py",
    "pb3": REPO_ROOT / "lampgen" / "pb3.py",
    "pb4": REPO_ROOT / "lampgen" / "pb4.py",
    "pb5": REPO_ROOT / "lampgen" / "pb5.py",
    "pb6": REPO_ROOT / "lampgen" / "pb6.py",
    "lampgen": REPO_ROOT / "lampgen" / "lampgen.py",
    "lampgenv2": REPO_ROOT / "lampgen" / "lampgenv2.py",
    "oglgb": REPO_ROOT / "lampgen" / "oglgb.py",
    "lgb2": REPO_ROOT / "lampgen" / "lgb2.py",
    "lgb3": REPO_ROOT / "lampgen" / "lgb3.py",
    "lampgenv3": REPO_ROOT / "lampgen" / "lampgenv3.py",
    "dlampgen": REPO_ROOT / "lampgen" / "dlampgen.py",
    "bayonet": REPO_ROOT / "lampgen" / "Bayonet.py",
}


def load_module(path: Path, module_name: str):
    spec = spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ENGINES = {
    engine_id: load_module(path, f"joui_{engine_id}")
    for engine_id, path in ENGINE_FILES.items()
}
COMMON_LIMITS = {
    "height": {"min": 80, "max": 320, "step": 1},
    "r_base": {"min": 18, "max": 90, "step": 1},
    "radius": {"min": 18, "max": 90, "step": 1},
    "thickness": {"min": 0.4, "max": 4.0, "step": 0.05},
    "r_min": {"min": 0.0, "max": 40.0, "step": 0.1},
    "bulb_amp": {"min": 0.0, "max": 30.0, "step": 0.1},
    "bulb_count": {"min": 0.5, "max": 5.0, "step": 0.05},
    "bulb_phase": {"min": 0.0, "max": 1.0, "step": 0.01},
    "taper": {"min": 0.0, "max": 0.25, "step": 0.005},
    "weave_amp": {"min": 0.0, "max": 3.0, "step": 0.05},
    "weave_theta": {"min": 4.0, "max": 80.0, "step": 0.5},
    "weave_pitch": {"min": 0.2, "max": 120.0, "step": 0.05},
    "weave_mix": {"min": 0.0, "max": 1.0, "step": 0.01},
    "weave_round": {"min": 0.0, "max": 0.5, "step": 0.01},
    "seam_twist": {"min": 0.0, "max": 0.1, "step": 0.001},
    "strand_width": {"min": 0.05, "max": 0.6, "step": 0.01},
    "weave_gap": {"min": 0.0, "max": 1.2, "step": 0.01},
    "gap_round": {"min": 0.0, "max": 0.5, "step": 0.01},
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
    "n_theta": {"min": 48, "max": 720, "step": 1},
    "n_z": {"min": 32, "max": 900, "step": 1},
    "wires": {"min": 8, "max": 64, "step": 1},
    "rotations": {"min": 1.0, "max": 12.0, "step": 0.1},
    "offset_b": {"min": 0.0, "max": 1.0, "step": 0.01},
    "wire_width": {"min": 0.6, "max": 5.0, "step": 0.05},
    "wire_thickness": {"min": 0.4, "max": 3.0, "step": 0.05},
    "inner_radius": {"min": 0.0, "max": 40.0, "step": 0.1},
    "seg_per_rot": {"min": 24, "max": 180, "step": 1},
    "n_lugs": {"min": 2, "max": 6, "step": 1},
    "twist_deg": {"min": 30.0, "max": 120.0, "step": 1},
    "entry_deg": {"min": 8.0, "max": 45.0, "step": 1},
    "lug_deg": {"min": 8.0, "max": 28.0, "step": 1},
    "mount_height": {"min": 6.0, "max": 28.0, "step": 0.5},
    "wall": {"min": 1.0, "max": 6.0, "step": 0.1},
    "socket_id": {"min": 16.0, "max": 60.0, "step": 0.1},
    "clearance": {"min": 0.0, "max": 1.0, "step": 0.01},
    "lug_thickness_z": {"min": 0.8, "max": 6.0, "step": 0.1},
    "lug_radial": {"min": 0.5, "max": 6.0, "step": 0.1},
    "detent_radial": {"min": 0.0, "max": 2.0, "step": 0.05},
    "detent_deg": {"min": 2.0, "max": 24.0, "step": 0.5},
}

COMMON_DESCRIPTIONS = {
    "height": "Altura total de la pieza en milimetros.",
    "r_base": "Radio base del volumen principal.",
    "radius": "Radio base del cilindro o cuerpo de alambre.",
    "thickness": "Espesor general de la pared o cascaron.",
    "r_min": "Radio minimo de seguridad para evitar colapsos.",
    "bulb_amp": "Cuanto se infla y se contrae el perfil a lo largo de Z.",
    "bulb_count": "Cantidad de lobulos u ondas verticales en el perfil.",
    "bulb_phase": "Desfase del patron de lobulos sobre la altura.",
    "taper": "Cuanto se estrecha o abre la forma hacia arriba.",
    "weave_amp": "Intensidad del relieve tejido o de la costura.",
    "weave_theta": "Frecuencia angular del patron alrededor del perimetro.",
    "weave_pitch": "Paso vertical del patron helicoidal o tejido.",
    "weave_mix": "Balance entre las dos familias cruzadas del patron.",
    "weave_round": "Suavizado y redondeo del cruce de hebras.",
    "seam_twist": "Giro suave acumulado del patron con la altura.",
    "strand_width": "Ancho aparente de cada hebra.",
    "weave_gap": "Profundidad visual del hueco entre hebras.",
    "gap_round": "Redondeo de los huecos del tejido.",
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
    "wires": "Cantidad de alambres por familia alrededor del cilindro.",
    "rotations": "Cantidad de vueltas helicoidales a lo largo de la altura.",
    "offset_b": "Desfase angular entre la familia A y la familia B.",
    "wire_width": "Ancho visual de cada cinta o alambre.",
    "wire_thickness": "Espesor radial de cada alambre.",
    "inner_radius": "Radio interior adicional para refuerzo, si existe.",
    "seg_per_rot": "Resolucion por vuelta helicoidal del alambre.",
    "n_lugs": "Cantidad de trabas del encastre bayoneta.",
    "twist_deg": "Grados de giro necesarios para trabar la bayoneta.",
    "entry_deg": "Apertura angular de cada ventana de entrada.",
    "lug_deg": "Ancho angular de cada lug de la bayoneta.",
    "mount_height": "Altura vertical del collar de encastre.",
    "wall": "Espesor de pared del collar bayoneta.",
    "socket_id": "Diametro interior de la hembra bayoneta.",
    "clearance": "Holgura radial para compensar impresion FDM.",
    "lug_thickness_z": "Espesor en Z del lug o repisa de trabado.",
    "lug_radial": "Saliente radial de cada lug.",
    "detent_radial": "Tamano radial del bulto de detent.",
    "detent_deg": "Ancho angular del detent.",
}

COMMON_SAFE_FLOORS = {
    "height": 0.001,
    "r_base": 0.001,
    "radius": 0.001,
    "thickness": 0.0,
    "r_min": 0.0,
    "seam_count": 1,
    "seam_width": 0.001,
    "seam_softness": 0.01,
    "rib_thickness": 0.0,
    "rib_seg_per_pitch": 3,
    "n_theta": 8,
    "n_z": 3,
    "wires": 1,
    "rotations": 0.001,
    "wire_width": 0.001,
    "wire_thickness": 0.001,
    "seg_per_rot": 8,
    "n_lugs": 1,
    "mount_height": 0.001,
    "wall": 0.001,
    "socket_id": 0.001,
    "clearance": 0.0,
    "lug_thickness_z": 0.001,
    "lug_radial": 0.001,
    "detent_radial": 0.0,
    "detent_deg": 0.001,
}


def subset_map(defaults: dict[str, Any], mapping: dict[str, Any]) -> dict[str, Any]:
    return {key: mapping[key] for key in defaults if key in mapping}


def merged(base: dict[str, Any], **updates: Any) -> dict[str, Any]:
    payload = dict(base)
    payload.update(updates)
    return payload


def lamp_defaults(engine_id: str) -> dict[str, Any]:
    return asdict(ENGINES[engine_id].LampParams())


def wire_defaults(engine_id: str) -> dict[str, Any]:
    return asdict(ENGINES[engine_id].WireParams())


def build_family_presets(
    defaults: dict[str, Any],
    family: str,
    supports_modes: bool = False,
    supports_close_top: bool = False,
    supports_dome_mode: bool = False,
) -> dict[str, dict[str, Any]]:
    presets = {"default": dict(defaults)}

    if family == "pb":
        presets["tall_shell"] = merged(
            defaults,
            height=float(defaults.get("height", 160.0)) * 1.25,
            r_base=float(defaults.get("r_base", 35.0)) * 0.92,
            bulb_amp=float(defaults.get("bulb_amp", 8.0)) * 1.15,
            seam_pitch=float(defaults.get("seam_pitch", 2.8)) * 1.1,
            seam_height=float(defaults.get("seam_height", 1.6)) * 1.15,
        )
        open_updates = {
            "height": float(defaults.get("height", 160.0)) * 1.1,
            "membrane": min(1.0, float(defaults.get("membrane", 0.25)) * 0.5),
            "perforation": max(0.35, float(defaults.get("perforation", 0.0)) + 0.45),
            "rib_thickness": float(defaults.get("rib_thickness", 1.2)) * 1.12,
            "seam_count": max(8, int(round(float(defaults.get("seam_count", 18)) * 0.9))),
        }
        if supports_modes:
            open_updates["mode"] = "perforated"
        if supports_close_top:
            open_updates["close_top"] = True
        if supports_dome_mode:
            open_updates["dome_mode"] = "perforated"
        presets["open_lattice"] = merged(defaults, **open_updates)
        return presets

    if family in {"lamp", "lattice"}:
        presets["compact"] = merged(
            defaults,
            height=float(defaults.get("height", 180.0)) * 0.82,
            r_base=float(defaults.get("r_base", 40.0)) * 0.9,
            bulb_amp=float(defaults.get("bulb_amp", 12.0)) * 0.75,
            thickness=float(defaults.get("thickness", 1.4)) * 1.1,
        )
        tall_updates = {
            "height": float(defaults.get("height", 180.0)) * 1.18,
            "r_base": float(defaults.get("r_base", 40.0)) * 0.92,
            "bulb_count": float(defaults.get("bulb_count", 2.0)) + 0.4,
            "weave_amp": float(defaults.get("weave_amp", 1.0)) * 1.15,
        }
        if "weave_pitch" in defaults:
            tall_updates["weave_pitch"] = float(defaults.get("weave_pitch", 4.0)) * (1.08 if family == "lamp" else 1.18)
        if "strand_width" in defaults:
            tall_updates["strand_width"] = max(0.12, float(defaults.get("strand_width", 0.3)) * 0.88)
        presets["tall"] = merged(defaults, **tall_updates)
        return presets

    if family == "wire":
        presets["dense_mesh"] = merged(
            defaults,
            wires=max(12, int(round(float(defaults.get("wires", 24)) * 1.2))),
            rotations=float(defaults.get("rotations", 6.0)) * 1.2,
            wire_width=float(defaults.get("wire_width", 2.0)) * 0.9,
            wire_thickness=float(defaults.get("wire_thickness", 1.2)) * 1.08,
        )
        presets["open_mesh"] = merged(
            defaults,
            wires=max(8, int(round(float(defaults.get("wires", 24)) * 0.82))),
            rotations=float(defaults.get("rotations", 6.0)) * 0.9,
            wire_width=float(defaults.get("wire_width", 2.0)) * 1.1,
        )
        return presets

    return presets


ENGINE_META = {
    "pb": {"label": "PB", "description": "Seam continuo helicoidal v1.", "family": "lamp", "builder": "make_mesh", "params_class": "LampParams", "interactive_caps": {"n_theta": 140, "n_z": 120}},
    "pb2": {"label": "PB2", "description": "Seam lattice con doble familia cruzada.", "family": "pb", "builder": "make_mesh", "params_class": "LampParams", "interactive_caps": {"n_theta": 140, "n_z": 120}},
    "pb3": {"label": "PB3", "description": "Seam shell con modos solid y perforated.", "family": "pb", "builder": "pb_modes", "params_class": "LampParams", "supports_modes": True, "interactive_caps": {"n_theta": 120, "n_z": 96, "rib_seg_per_pitch": 42}},
    "pb4": {"label": "PB4", "description": "PB3 con cierre superior opcional.", "family": "pb", "builder": "pb_modes", "params_class": "LampParams", "supports_modes": True, "supports_close_top": True, "interactive_caps": {"n_theta": 120, "n_z": 96, "rib_seg_per_pitch": 42}},
    "pb5": {"label": "PB5", "description": "PB4 con tapa tipo domo.", "family": "pb", "builder": "pb_modes", "params_class": "LampParams", "supports_modes": True, "supports_close_top": True, "interactive_caps": {"n_theta": 120, "n_z": 96, "rib_seg_per_pitch": 42}},
    "pb6": {"label": "PB6", "description": "Seam shell con solid, perforated y dome modes.", "family": "pb", "builder": "pb_modes", "params_class": "LampParams", "supports_modes": True, "supports_close_top": True, "supports_dome_mode": True, "interactive_caps": {"n_theta": 120, "n_z": 96, "rib_seg_per_pitch": 42}},
    "lampgen": {"label": "Lampgen", "description": "Basket weave organico original.", "family": "lamp", "builder": "make_mesh", "params_class": "LampParams", "interactive_caps": {"n_theta": 160, "n_z": 160}},
    "lampgenv2": {"label": "Lampgen V2", "description": "Costura continua con shell uniforme.", "family": "lamp", "builder": "make_mesh", "params_class": "LampParams", "interactive_caps": {"n_theta": 180, "n_z": 180}},
    "lampgenv3": {"label": "Lampgen V3", "description": "Costura continua helicoidal sobre shell bulboso.", "family": "lamp", "builder": "make_mesh", "params_class": "LampParams", "interactive_caps": {"n_theta": 180, "n_z": 180}},
    "oglgb": {"label": "OGLGB", "description": "Woven lattice continuo con volumen uniforme.", "family": "lattice", "builder": "make_mesh", "params_class": "LampParams", "interactive_caps": {"n_theta": 180, "n_z": 180}},
    "lgb2": {"label": "LGB2", "description": "Lattice woven con cruces redondeados.", "family": "lattice", "builder": "make_mesh", "params_class": "LampParams", "interactive_caps": {"n_theta": 180, "n_z": 180}},
    "lgb3": {"label": "LGB3", "description": "Lattice woven basket con hebras cruzadas.", "family": "lattice", "builder": "make_mesh", "params_class": "LampParams", "interactive_caps": {"n_theta": 180, "n_z": 180}},
    "dlampgen": {"label": "DLampgen", "description": "Wire diamonds con rombos reales.", "family": "wire", "builder": "build_wire_diamonds", "params_class": "WireParams", "interactive_caps": {"seg_per_rot": 60}},
}

BAYONET_DEFAULTS = merged(
    wire_defaults("bayonet"),
    **{key: value for key, value in asdict(ENGINES["bayonet"].BayonetParams()).items() if not isinstance(value, bool)},
)


def build_engine_configs() -> dict[str, dict[str, Any]]:
    configs = {}

    for engine_id, meta in ENGINE_META.items():
        defaults = asdict(getattr(ENGINES[engine_id], meta["params_class"])())
        supports_modes = meta.get("supports_modes", False)
        supports_close_top = meta.get("supports_close_top", False)
        supports_dome_mode = meta.get("supports_dome_mode", False)
        configs[engine_id] = {
            "label": meta["label"],
            "description": meta["description"],
            "defaults": defaults,
            "limits": subset_map(defaults, COMMON_LIMITS),
            "descriptions": subset_map(defaults, COMMON_DESCRIPTIONS),
            "safe_floors": subset_map(defaults, COMMON_SAFE_FLOORS),
            "presets": build_family_presets(defaults, meta["family"], supports_modes, supports_close_top, supports_dome_mode),
            "builder": meta["builder"],
            "params_class": meta["params_class"],
            "supports_modes": supports_modes,
            "supports_close_top": supports_close_top,
            "supports_dome_mode": supports_dome_mode,
            "interactive_caps": meta["interactive_caps"],
        }

    configs["bayonet"] = {
        "label": "Bayonet",
        "description": "Cabezal wire con encastre bayoneta integrado.",
        "defaults": BAYONET_DEFAULTS,
        "limits": subset_map(BAYONET_DEFAULTS, COMMON_LIMITS),
        "descriptions": subset_map(BAYONET_DEFAULTS, COMMON_DESCRIPTIONS),
        "safe_floors": subset_map(BAYONET_DEFAULTS, COMMON_SAFE_FLOORS),
        "presets": {
            "default": dict(BAYONET_DEFAULTS),
            "sturdy_lock": merged(BAYONET_DEFAULTS, wire_thickness=1.45, mount_height=16.0, wall=2.8, lug_radial=2.4),
            "open_wire": merged(BAYONET_DEFAULTS, wires=22, rotations=5.2, wire_width=2.4, clearance=0.34),
        },
        "builder": "bayonet_wire",
        "params_class": "combined",
        "supports_modes": False,
        "supports_close_top": False,
        "supports_dome_mode": False,
        "interactive_caps": {"seg_per_rot": 56},
    }

    return configs


ENGINE_CONFIGS = build_engine_configs()

DEFAULT_ENGINE_ID = "pb6"
ENGINE_LIST = [
    {"id": engine_id, "label": config["label"], "description": config["description"]}
    for engine_id, config in ENGINE_CONFIGS.items()
]


def resolve_engine_id(payload: dict[str, Any]) -> str:
    engine_id = str(payload.get("engine", DEFAULT_ENGINE_ID))
    return engine_id if engine_id in ENGINE_CONFIGS else DEFAULT_ENGINE_ID


def coerce_params(engine_id: str, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    config = ENGINE_CONFIGS[engine_id]
    defaults = config["defaults"]
    params = dict(defaults)
    for key, default_value in defaults.items():
        raw = payload.get(key, default_value)
        try:
            numeric = float(raw)
        except (TypeError, ValueError):
            numeric = float(default_value)

        if isinstance(default_value, int) and not isinstance(default_value, bool):
            value = int(round(numeric))
        else:
            value = numeric

        floor = config["safe_floors"].get(key)
        if floor is not None:
            value = max(floor, value)
            if isinstance(default_value, int) and not isinstance(default_value, bool):
                value = int(round(value))

        params[key] = value

    extra = {}
    if config.get("supports_modes"):
        mode = payload.get("mode", "solid")
        if mode not in {"solid", "perforated"}:
            mode = "solid"
        extra["mode"] = mode
    if config.get("supports_close_top"):
        extra["close_top"] = bool(payload.get("close_top", False))
    if config.get("supports_dome_mode"):
        dome_mode = payload.get("dome_mode", "solid")
        if dome_mode not in {"solid", "perforated"}:
            dome_mode = "solid"
        extra["dome_mode"] = dome_mode

    return params, extra


def build_triangles(engine_id: str, payload: dict[str, Any], interactive: bool) -> tuple[dict[str, Any], list[tuple[Any, Any, Any]]]:
    config = ENGINE_CONFIGS[engine_id]
    params, extra = coerce_params(engine_id, payload)
    if interactive:
        for key, cap in config.get("interactive_caps", {}).items():
            if key in params:
                params[key] = min(params[key], cap)

    module = ENGINES[engine_id]
    builder = config["builder"]

    if builder == "make_mesh":
        param_obj = getattr(module, config["params_class"])(**params)
        tris = module.make_mesh(param_obj)
    elif builder == "build_wire_diamonds":
        param_obj = getattr(module, config["params_class"])(**params)
        tris = module.build_wire_diamonds(param_obj)
    elif builder == "pb_modes":
        lamp_params = getattr(module, config["params_class"])(**params)
        if extra.get("mode") == "perforated":
            kwargs = {}
            if config.get("supports_close_top"):
                kwargs["close_top"] = extra.get("close_top", False)
            if config.get("supports_dome_mode"):
                kwargs["dome_mode"] = extra.get("dome_mode", "solid")
            tris = module.make_mesh_perforated(lamp_params, **kwargs)
        else:
            tris = module.make_mesh_solid(lamp_params)
    elif builder == "bayonet_wire":
        body_args = SimpleNamespace(
            height=params["height"],
            radius=params["radius"],
            wires=params["wires"],
            rotations=params["rotations"],
            offset_b=params["offset_b"],
            wire_width=params["wire_width"],
            wire_thickness=params["wire_thickness"],
            seg_per_rot=params["seg_per_rot"],
            vary=False,
        )
        body_tris, _height, outer_radius_hint = module.build_head("wire", 0, body_args)
        mount_tris: list[tuple[Any, Any, Any]] = []
        module.add_female_bayonet(
            mount_tris,
            module.BayonetParams(
                n_lugs=params["n_lugs"],
                twist_deg=params["twist_deg"],
                entry_deg=params["entry_deg"],
                lug_deg=params["lug_deg"],
                mount_height=params["mount_height"],
                wall=params["wall"],
                socket_id=params["socket_id"],
                clearance=params["clearance"],
                lug_thickness_z=params["lug_thickness_z"],
                lug_radial=params["lug_radial"],
                detent=True,
                detent_radial=params["detent_radial"],
                detent_deg=params["detent_deg"],
            ),
            z_base=0.0,
            outer_radius_hint=outer_radius_hint,
        )
        tris = body_tris + mount_tris
    else:
        raise ValueError(f"Unsupported engine builder: {builder}")

    return {
        "engine": engine_id,
        "params": params,
        "mode": extra.get("mode"),
        "close_top": extra.get("close_top", False),
        "dome_mode": extra.get("dome_mode", "solid"),
        "interactive": interactive,
    }, tris


def export_file_name(engine_id: str, meta: dict[str, Any]) -> str:
    params = meta["params"]
    parts = [engine_id]
    if meta.get("mode"):
        parts.append(str(meta["mode"]))

    aliases = {
        "height": "h",
        "r_base": "rb",
        "radius": "ra",
        "seam_count": "sc",
        "wires": "wi",
        "socket_id": "so",
    }
    for key in ("height", "r_base", "radius", "seam_count", "wires", "socket_id"):
        if key in params:
            value = params[key]
            prefix = aliases[key]
            if isinstance(value, float) and not value.is_integer():
                parts.append(f"{prefix}{value:.2f}")
            else:
                parts.append(f"{prefix}{int(round(value))}")

    return "_".join(parts) + ".stl"


def write_engine_stl(engine_id: str, file_name: str, triangles: list[tuple[Any, Any, Any]]) -> None:
    out_path = EXPORT_DIR / file_name
    if engine_id == "bayonet":
        ENGINES["bayonet"].write_binary_stl(str(out_path), triangles, header_text=b"joui_bayonet_head")
        return
    ENGINES[engine_id].write_binary_stl(str(out_path), triangles)


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
                    "default_engine": DEFAULT_ENGINE_ID,
                    "engines": ENGINE_LIST,
                    "engine_configs": {
                        engine_id: {
                            "defaults": config["defaults"],
                            "limits": config["limits"],
                            "descriptions": config["descriptions"],
                            "presets": config["presets"],
                            "supports_modes": config["supports_modes"],
                            "modes": ["solid", "perforated"] if config["supports_modes"] else [],
                            "dome_modes": ["solid", "perforated"] if config["supports_modes"] else [],
                        }
                        for engine_id, config in ENGINE_CONFIGS.items()
                    },
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
        engine_id = resolve_engine_id(payload)

        if self.path == "/api/preview":
            meta, tris = build_triangles(engine_id, payload, interactive=True)
            mesh = triangles_to_indexed_mesh(tris)
            self.send_json({"meta": meta, "mesh": mesh})
            return

        meta, tris = build_triangles(engine_id, payload, interactive=False)
        EXPORT_DIR.mkdir(exist_ok=True)
        file_name = export_file_name(engine_id, meta)
        write_engine_stl(engine_id, file_name, tris)
        out_path = EXPORT_DIR / file_name
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
