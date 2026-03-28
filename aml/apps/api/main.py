from fastapi import FastAPI, HTTPException, Response, UploadFile, File, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os
import io
import json
import math
import struct
import sys
import zipfile
import inspect
from dataclasses import asdict, is_dataclass, fields
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parent
EXPORT_DIR = ROOT / "exports"

# ConfiguraciÃ³n de autenticaciÃ³n
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(username: str, password: str):
    with open(ROOT / "users.json", "r") as f:
        users = json.load(f)
    if username not in users:
        return False
    stored_pw = users[username]
    # support bcrypt hashes and plain text during desarrollo
    if isinstance(stored_pw, str) and (stored_pw.startswith("$2a$") or stored_pw.startswith("$2b$") or stored_pw.startswith("$2y$")):
        if verify_password(password, stored_pw):
            return username
        return False
    # legacy plain-text login fallback (solo para desarrollo)
    if password == stored_pw:
        return username
    return False

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username

app = FastAPI(title="Atlas Multiversal API")

# Montar estÃ¡ticos (portal/dashboard)
app.mount("/portal/", StaticFiles(directory=ROOT.parent / "portal", html=True), name="portal")
app.mount("/dashboard/", StaticFiles(directory=ROOT.parent / "dashboard", html=True), name="dashboard")
app.mount("/base-studio/", StaticFiles(directory=ROOT.parent / "base-studio", html=True), name="base-studio")

@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/portal/")

@app.get("/portal")
async def portal_redirect():
    return RedirectResponse(url="/portal/")

@app.get("/dashboard")
async def dashboard_redirect():
    return RedirectResponse(url="/dashboard/")

@app.get("/base-studio")
async def base_studio_redirect():
    return RedirectResponse(url="/base-studio/")

# Endpoint de login
class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/token")
async def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# ConfiguraciÃ³n de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restringir dominios en producciÃ³n
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ENGINE_ID_OVERRIDES: dict[str, str] = {
    "Bayonet.py": "bayonet",
}

ENGINE_SKIP_STEMS: set[str] = {
    "base_engine",
    "base_geom",
    "inverse_base",
    "inverse_base_v2",
    "lampbase",
    "lampbase_abs1",
    "lampbase_abs2",
    "lampbase_brut1",
    "lampbase_brut2",
    "lampbase_dance1",
    "lampbase_fit2",
    "lampbase_fit20",
    "lampgenPlanet",
    "lampgenPlanetEngineV1",
}

ENGINE_SKIP_PREFIXES: tuple[str, ...] = (
    "inverse_base",
    "lampbase",
)

def discover_engine_files() -> tuple[dict[str, Path], dict[str, str]]:
    discovered: dict[str, Path] = {}
    skipped: dict[str, str] = {}
    generators_dir = ROOT / "generators"

    for path in sorted(generators_dir.glob("*.py")):
        stem = path.stem
        if stem.startswith("_"):
            skipped[path.name] = "private module"
            continue
        if stem in ENGINE_SKIP_STEMS or any(stem.startswith(prefix) for prefix in ENGINE_SKIP_PREFIXES):
            skipped[path.name] = "base/helper module"
            continue

        engine_id = ENGINE_ID_OVERRIDES.get(path.name, stem.lower())
        if engine_id in discovered:
            skipped[path.name] = f"duplicate engine id ({engine_id})"
            continue
        discovered[engine_id] = path

    return discovered, skipped

def load_module(path: Path, module_name: str):
    root_path = str(ROOT)
    if root_path not in sys.path:
        sys.path.insert(0, root_path)
    spec = spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

BASE_GENERATOR_FILES = {
    "lampbase1": ROOT / "generators" / "inverse_base.py",
    "lampbase2": ROOT / "generators" / "inverse_base_v2.py",
    "lampbase_brut1": ROOT / "generators" / "lampbase_brut1.py",
    "lampbase_brut2": ROOT / "generators" / "lampbase_brut2.py",
    "lampbase_abs1": ROOT / "generators" / "lampbase_abs1.py",
    "lampbase_abs2": ROOT / "generators" / "lampbase_abs2.py",
    "lampbase_fit20": ROOT / "generators" / "lampbase_fit20.py",
    "lampbase_fit2": ROOT / "generators" / "lampbase_fit2.py",
    "lampbase_dance1": ROOT / "generators" / "lampbase_dance1.py",
}

BASE_GENERATORS = {
    generator_id: load_module(path, f"joui_{generator_id}")
    for generator_id, path in BASE_GENERATOR_FILES.items()
    if path.exists()
}

DEFAULT_BASE_GENERATOR_ID = "lampbase1" if "lampbase1" in BASE_GENERATORS else (next(iter(BASE_GENERATORS.keys()), None))

ENGINE_FILES, SKIPPED_ENGINE_FILES = discover_engine_files()

ENGINE_IMPORT_ERRORS: dict[str, str] = {}
ENGINES: dict[str, Any] = {}
for engine_id, path in ENGINE_FILES.items():
    try:
        ENGINES[engine_id] = load_module(path, f"joui_{engine_id}")
    except Exception as exc:
        ENGINE_IMPORT_ERRORS[engine_id] = str(exc)

if ENGINE_IMPORT_ERRORS:
    print(f"Warning: engines with import errors skipped: {sorted(ENGINE_IMPORT_ERRORS.keys())}")

def _defaults_from_params_instance(instance: Any) -> dict[str, Any] | None:
    if is_dataclass(instance):
        defaults = asdict(instance)
    elif hasattr(instance, "__dict__"):
        defaults = dict(vars(instance))
    else:
        return None

    return defaults or None

def _resolve_params_class(engine: Any):
    return getattr(engine, "LampParams", None) or getattr(engine, "LampParameters", None)

def _safe_lamp_defaults_from_engine(engine: Any) -> dict[str, Any] | None:
    params_cls = _resolve_params_class(engine)
    if params_cls is None:
        return None
    try:
        instance = params_cls()
    except Exception:
        return None
    return _defaults_from_params_instance(instance)

def _resolve_scad_builder_class(engine: Any):
    for _, candidate in inspect.getmembers(engine, inspect.isclass):
        if candidate.__module__ != getattr(engine, "__name__", ""):
            continue
        if not callable(getattr(candidate, "build", None)):
            continue
        if not hasattr(candidate, "engine_name"):
            continue
        return candidate
    return None

ENGINE_KINDS: dict[str, str] = {}
SCAD_ENGINE_BUILDERS: dict[str, Any] = {}

INCOMPATIBLE_ENGINES: dict[str, str] = {}
for engine_id, engine in list(ENGINES.items()):
    defaults = _safe_lamp_defaults_from_engine(engine)
    params_cls = _resolve_params_class(engine)
    if defaults is None or params_cls is None:
        INCOMPATIBLE_ENGINES[engine_id] = "missing or invalid LampParams/LampParameters defaults"
        ENGINES.pop(engine_id, None)
        continue
    has_make_mesh = callable(getattr(engine, "make_mesh", None))
    has_mode_mesh = callable(getattr(engine, "make_mesh_solid", None)) and callable(
        getattr(engine, "make_mesh_perforated", None)
    )
    if has_make_mesh or has_mode_mesh:
        ENGINE_KINDS[engine_id] = "mesh"
        continue

    scad_builder_cls = _resolve_scad_builder_class(engine)
    if scad_builder_cls is None:
        INCOMPATIBLE_ENGINES[engine_id] = "missing make_mesh or class-based build() engine"
        ENGINES.pop(engine_id, None)
        continue

    try:
        SCAD_ENGINE_BUILDERS[engine_id] = scad_builder_cls()
        ENGINE_KINDS[engine_id] = "scad"
    except Exception as exc:
        INCOMPATIBLE_ENGINES[engine_id] = f"failed to instantiate SCAD engine: {exc}"
        ENGINES.pop(engine_id, None)
        continue

if INCOMPATIBLE_ENGINES:
    print(f"Warning: incompatible engines skipped: {sorted(INCOMPATIBLE_ENGINES.keys())}")

def engine_workbench_items() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for engine_id, path in ENGINE_FILES.items():
        if engine_id in ENGINES:
            status = "ready"
            reason = "ok"
        elif engine_id in ENGINE_IMPORT_ERRORS:
            status = "import_error"
            reason = ENGINE_IMPORT_ERRORS[engine_id]
        else:
            status = "incompatible"
            reason = INCOMPATIBLE_ENGINES.get(engine_id, "unsupported contract")

        items.append(
            {
                "id": engine_id,
                "file": path.name,
                "status": status,
                "reason": reason,
                "label": engine_label(engine_id),
            }
        )

    for file_name, reason in SKIPPED_ENGINE_FILES.items():
        items.append(
            {
                "id": None,
                "file": file_name,
                "status": "ignored",
                "reason": reason,
                "label": file_name,
            }
        )

    items.sort(key=lambda item: (item["status"], (item.get("id") or ""), item["file"]))
    return items

def pick_default_engine(engine_ids: list[str]) -> str | None:
    if not engine_ids:
        return None
    priority = [
        "lampgenv5",
        "lampgenv6",
        "lampgenv7",
        "pb3",
        "pb2",
        "pb",
    ]
    for candidate in priority:
        if candidate in engine_ids:
            return candidate
    return engine_ids[0]

DEFAULT_ENGINE_ID = pick_default_engine(list(ENGINES.keys()))

def _quantize_vertex(vertex, digits: int = 6):
    return (
        round(float(vertex[0]), digits),
        round(float(vertex[1]), digits),
        round(float(vertex[2]), digits),
    )

def triangles_to_indexed_mesh(triangles):
    vertex_map = {}
    vertices = []
    indexed = []

    for tri in triangles:
        tri_indices = []
        for vertex in tri:
            key = _quantize_vertex(vertex)
            idx = vertex_map.get(key)
            if idx is None:
                idx = len(vertices)
                vertex_map[key] = idx
                vertices.append([key[0], key[1], key[2]])
            tri_indices.append(idx)
        indexed.append(tri_indices)

    if vertices:
        mins = [min(v[i] for v in vertices) for i in range(3)]
        maxs = [max(v[i] for v in vertices) for i in range(3)]
    else:
        mins = [0.0, 0.0, 0.0]
        maxs = [0.0, 0.0, 0.0]

    center = [(mins[i] + maxs[i]) * 0.5 for i in range(3)]
    radius = 0.0
    for v in vertices:
        dx = v[0] - center[0]
        dy = v[1] - center[1]
        dz = v[2] - center[2]
        radius = max(radius, math.sqrt(dx * dx + dy * dy + dz * dz))

    return {
        "vertices": vertices,
        "triangles": indexed,
        "vertex_count": len(vertices),
        "triangle_count": len(indexed),
        "bounds": {"min": mins, "max": maxs},
        "radius": radius,
    }

def decimate_triangles(triangles, max_triangles: int):
    if max_triangles <= 0 or len(triangles) <= max_triangles:
        return triangles
    step = max(1, int(math.ceil(len(triangles) / max_triangles)))
    return triangles[::step]

def _stl_normal(v0, v1, v2):
    ax = v1[0] - v0[0]
    ay = v1[1] - v0[1]
    az = v1[2] - v0[2]
    bx = v2[0] - v0[0]
    by = v2[1] - v0[1]
    bz = v2[2] - v0[2]
    nx = ay * bz - az * by
    ny = az * bx - ax * bz
    nz = ax * by - ay * bx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / length, ny / length, nz / length)

def write_binary_stl(path: Path, triangles):
    header = b"aml_binary_stl".ljust(80, b"\0")
    with open(path, "wb") as handle:
        handle.write(header)
        handle.write(struct.pack("<I", len(triangles)))
        for (v0, v1, v2) in triangles:
            normal = _stl_normal(v0, v1, v2)
            handle.write(struct.pack("<3f", *normal))
            handle.write(struct.pack("<3f", float(v0[0]), float(v0[1]), float(v0[2])))
            handle.write(struct.pack("<3f", float(v1[0]), float(v1[1]), float(v1[2])))
            handle.write(struct.pack("<3f", float(v2[0]), float(v2[1]), float(v2[2])))
            handle.write(struct.pack("<H", 0))

def resolve_engine_id(payload: dict) -> str:
    engine_id = payload.get("engine") or DEFAULT_ENGINE_ID
    if not engine_id or engine_id not in ENGINES:
        raise HTTPException(status_code=404, detail="Engine not found")
    return engine_id

def accepted_lamp_param_keys(engine: Any) -> set[str]:
    params_cls = _resolve_params_class(engine)
    if params_cls is None:
        return set()
    try:
        if is_dataclass(params_cls):
            return {field.name for field in fields(params_cls)}
    except Exception:
        pass

    try:
        signature = inspect.signature(params_cls)
        return {name for name in signature.parameters.keys() if name != "self"}
    except Exception:
        return set()

def build_engine_params(engine_id: str, payload: dict):
    engine = ENGINES[engine_id]
    defaults = lamp_defaults(engine_id)
    accepted = accepted_lamp_param_keys(engine)
    merged = dict(defaults)
    for key, value in payload.items():
        if key in ("engine", "target_triangles"):
            continue
        if accepted and key not in accepted:
            continue
        merged[key] = value

    target_triangles = payload.get("target_triangles")
    has_resolution_params = ("n_theta" in merged and "n_z" in merged)
    if target_triangles:
        try:
            target_triangles = int(target_triangles)
        except (TypeError, ValueError):
            target_triangles = None
    if has_resolution_params and target_triangles and target_triangles > 0:
        current_triangles = int(merged["n_theta"]) * int(merged["n_z"]) * 2
        scale = math.sqrt(target_triangles / max(1, current_triangles))
        merged["n_theta"] = max(48, int(int(merged["n_theta"]) * scale))
        merged["n_z"] = max(32, int(int(merged["n_z"]) * scale))

    if accepted:
        merged = {key: merged[key] for key in accepted if key in merged}
    params_cls = _resolve_params_class(engine)
    if params_cls is None:
        raise HTTPException(status_code=500, detail=f"Engine {engine_id} has no parameter class")
    return params_cls(**merged)

def _build_placeholder_tris(radius_base: float, radius_top: float, height: float, n_theta: int = 56, n_z: int = 42):
    radius_base = max(2.0, float(radius_base))
    radius_top = max(1.0, float(radius_top))
    height = max(20.0, float(height))
    n_theta = max(12, int(n_theta))
    n_z = max(6, int(n_z))

    rings: list[list[tuple[float, float, float]]] = []
    for zi in range(n_z + 1):
        t = zi / n_z
        z = t * height
        bulge = 1.0 + 0.10 * math.sin(t * math.pi)
        radius = (radius_base * (1.0 - t) + radius_top * t) * bulge
        ring: list[tuple[float, float, float]] = []
        for ti in range(n_theta):
            a = (ti / n_theta) * math.tau
            ring.append((radius * math.cos(a), radius * math.sin(a), z))
        rings.append(ring)

    triangles = []
    for zi in range(n_z):
        r0 = rings[zi]
        r1 = rings[zi + 1]
        for ti in range(n_theta):
            tn = (ti + 1) % n_theta
            v00 = r0[ti]
            v01 = r0[tn]
            v10 = r1[ti]
            v11 = r1[tn]
            triangles.append((v00, v10, v11))
            triangles.append((v00, v11, v01))
    return triangles

def build_scad_placeholder_triangles(engine_id: str, params: Any):
    width = _numeric(getattr(params, "width_mm", None)) or 140.0
    height = _numeric(getattr(params, "height_mm", None)) or 180.0
    base_diameter = _numeric(getattr(params, "base_diameter_mm", None)) or (width * 0.55)
    style = str(getattr(params, "style", "modern") or "modern").lower()

    style_factor = {
        "modern": 0.42,
        "industrial": 0.35,
        "minimalist": 0.26,
        "scandinavian": 0.46,
        "vintage": 0.58,
        "art_deco": 0.62,
        "rustic": 0.52,
        "futuristic": 0.24,
    }.get(style, 0.4)

    radius_base = max(width * 0.18, base_diameter * 0.20)
    radius_top = max(6.0, width * style_factor * 0.30)
    tris = _build_placeholder_tris(radius_base, radius_top, height)

    if engine_id == "chandelier":
        n_arms = max(2, int(_numeric(getattr(params, "num_arms", None)) or 4))
        arm_len = max(25.0, width * 0.35)
        arm_r = max(1.8, width * 0.02)
        arm_tris = _build_placeholder_tris(arm_r, arm_r * 0.9, arm_len, n_theta=20, n_z=18)
        hub_z = height * 0.45
        for i in range(n_arms):
            a = (i / n_arms) * math.tau
            ca = math.cos(a)
            sa = math.sin(a)
            for tri in arm_tris:
                rotated = []
                for x, y, z in tri:
                    px = z * ca - y * sa
                    py = z * sa + y * ca
                    pz = hub_z + x
                    rotated.append((px, py, pz))
                tris.append(tuple(rotated))

    return tris

def build_triangles(engine_id: str, payload: dict, interactive: bool):
    engine = ENGINES[engine_id]
    engine_kind = ENGINE_KINDS.get(engine_id, "mesh")
    if engine_kind == "scad":
        params = build_engine_params(engine_id, payload)
        triangles = build_scad_placeholder_triangles(engine_id, params)
        meta = {
            "engine": engine_id,
            "target_triangles": payload.get("target_triangles"),
            "engine_kind": "scad",
            "preview_note": "placeholder mesh generated from SCAD-style engine parameters",
        }
        return meta, triangles

    accepted = accepted_lamp_param_keys(engine)
    mode = payload.get("mode", "solid")
    close_top = bool(payload.get("close_top", False))
    dome_mode = payload.get("dome_mode", "solid")

    def generate_for_params(params_obj):
        if callable(getattr(engine, "make_mesh", None)):
            return engine.make_mesh(params_obj)
        if mode == "perforated":
            fn = getattr(engine, "make_mesh_perforated")
            signature = inspect.signature(fn)
            kwargs = {}
            if "close_top" in signature.parameters:
                kwargs["close_top"] = close_top
            if "dome_mode" in signature.parameters:
                kwargs["dome_mode"] = dome_mode
            return fn(params_obj, **kwargs)
        return engine.make_mesh_solid(params_obj)

    triangles = None
    preview_budget = None
    if interactive and ("n_theta" in accepted and "n_z" in accepted):
        working_payload = dict(payload)
        try:
            requested = int(payload.get("target_triangles") or 0)
        except (TypeError, ValueError):
            requested = 0
        max_preview = requested if requested > 0 else 120000
        max_preview = min(200000, max(2000, max_preview))
        preview_budget = max_preview
        working_payload["target_triangles"] = max_preview

        for attempt in range(5):
            params = build_engine_params(engine_id, working_payload)
            try:
                triangles = generate_for_params(params)
            except Exception as exc:
                raise HTTPException(status_code=500, detail=str(exc))

            if len(triangles) <= max_preview:
                break

            n_theta = getattr(params, "n_theta", None)
            n_z = getattr(params, "n_z", None)
            if not isinstance(n_theta, int) or not isinstance(n_z, int):
                break

            scale = math.sqrt(max_preview / max(1, len(triangles))) * 0.92
            working_payload.pop("target_triangles", None)
            working_payload["n_theta"] = max(48, int(n_theta * scale))
            working_payload["n_z"] = max(32, int(n_z * scale))
    else:
        params = build_engine_params(engine_id, payload)
        try:
            triangles = generate_for_params(params)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    target = payload.get("target_triangles")
    if interactive and not ("n_theta" in accepted and "n_z" in accepted):
        triangles = decimate_triangles(triangles, preview_budget or 80000)

    meta = {"engine": engine_id, "target_triangles": target}
    return meta, triangles

def export_file_name(engine_id: str, payload: dict) -> str:
    height = payload.get("height")
    r_base = payload.get("r_base")
    parts = [engine_id]
    if isinstance(height, (int, float)):
        parts.append(f"h{int(round(height))}")
    if isinstance(r_base, (int, float)):
        parts.append(f"rb{int(round(r_base))}")
    return "_".join(parts) + ".stl"

ENGINE_LABELS: dict[str, str] = {
    "chandelier": "Chandelier",
    "pendant_lamp": "Pendant Lamp",
    "table_lamp": "Table Lamp",
    "floor_lamp": "Floor Lamp",
    "wall_lamp": "Wall Lamp",
    "pb": "PB v1",
    "pb2": "PB v2",
    "pb3": "PB v3 (Seam)",
    "pb4": "PB v4 (Seam)",
    "pb5": "PB v5 (Seam)",
    "pb6": "PB v6 (Seam)",
    "lampgen": "LampGen v1",
    "lampgenv2": "LampGen v2",
    "lampgenv3": "LampGen v3",
    "lampgenv4": "LampGen v4",
    "lampgenv5": "LampGen v5",
    "lampgenv6": "LampGen v6",
    "lampgenv7": "LampGen v7",
    "oglgb": "OG LGB",
    "lgb2": "LGB v2",
    "lgb3": "LGB v3",
}

def engine_family(engine_id: str, engine: Any) -> str:
    explicit = getattr(engine, "FAMILY", None)
    if isinstance(explicit, str) and explicit.strip():
        return explicit
    if engine_id.startswith("pb"):
        return "pb"
    if engine_id.startswith("lampgen"):
        return "lamp"
    if engine_id.startswith("lgb") or engine_id.endswith("lgb") or "lgb" in engine_id:
        return "lgb"
    if engine_id in {"chandelier", "pendant_lamp", "table_lamp", "floor_lamp", "wall_lamp"}:
        return "design"
    return "misc"

def engine_label(engine_id: str) -> str:
    return ENGINE_LABELS.get(engine_id, engine_id)

BASES_CATALOG: list[dict[str, Any]] = [
    {
        "id": "lampbase1_s",
        "family_id": "lampbase1",
        "family_label": "LampBase1",
        "label": "LampBase1 S",
        "connection": "bayonet",
        "preferred_engine_families": ["lamp", "pb"],
        "female_id_range_mm": [24.0, 36.0],
        "notes": "Base de mesa con adaptador macho bayoneta. Ideal para encastres chicos (E14/E26 compactos).",
        "mount_profile": {
            "n_lugs": 3,
            "twist_deg": 60.0,
            "entry_deg": 18.0,
            "lug_deg": 14.0,
            "mount_height": 16.0,
            "wall": 2.2,
            "clearance": 0.25,
            "lug_thickness_z": 2.2,
            "lug_radial": 2.2,
            "detent_radial": 0.6,
            "detent_deg": 8.0,
        },
    },
    {
        "id": "lampbase1_m",
        "family_id": "lampbase1",
        "family_label": "LampBase1",
        "label": "LampBase1 M",
        "connection": "bayonet",
        "preferred_engine_families": ["lamp", "pb"],
        "female_id_range_mm": [32.0, 46.0],
        "notes": "Base de mesa bayoneta para modelos medianos. Buen balance entre rigidez y facilidad de encastre.",
        "mount_profile": {
            "n_lugs": 3,
            "twist_deg": 75.0,
            "entry_deg": 22.0,
            "lug_deg": 18.0,
            "mount_height": 18.0,
            "wall": 2.6,
            "clearance": 0.3,
            "lug_thickness_z": 2.6,
            "lug_radial": 2.6,
            "detent_radial": 0.7,
            "detent_deg": 10.0,
        },
    },
    {
        "id": "lampbase1_l",
        "family_id": "lampbase1",
        "family_label": "LampBase1",
        "label": "LampBase1 L",
        "connection": "bayonet",
        "preferred_engine_families": ["lamp", "pb", "lgb"],
        "female_id_range_mm": [42.0, 60.0],
        "notes": "Base de mesa bayoneta para modelos grandes (diámetros de encastre altos).",
        "mount_profile": {
            "n_lugs": 4,
            "twist_deg": 85.0,
            "entry_deg": 24.0,
            "lug_deg": 18.0,
            "mount_height": 20.0,
            "wall": 3.0,
            "clearance": 0.35,
            "lug_thickness_z": 2.8,
            "lug_radial": 2.8,
            "detent_radial": 0.8,
            "detent_deg": 10.0,
        },
    },
    {
        "id": "lampbase2_m",
        "family_id": "lampbase2",
        "family_label": "LampBase2",
        "label": "LampBase2 M",
        "connection": "ring",
        "preferred_engine_families": ["lamp", "lgb", "pb"],
        "female_id_range_mm": [28.0, 58.0],
        "notes": "Opción genérica tipo aro/prensa (sin bayoneta). Útil cuando el motor expone `opening_radius`.",
        "mount_profile": {},
    },
    {
        "id": "lampbase2_l",
        "family_id": "lampbase2",
        "family_label": "LampBase2",
        "label": "LampBase2 L",
        "connection": "ring",
        "preferred_engine_families": ["lamp", "lgb"],
        "female_id_range_mm": [50.0, 86.0],
        "notes": "Variante mas ancha del sistema aro / plug para bocas grandes u ovaladas.",
        "mount_profile": {},
    },
    {
        "id": "placeholder_threaded",
        "family_id": "threadbase",
        "family_label": "ThreadBase",
        "preferred_engine_families": ["lamp", "pb"],
        "label": "ThreadBase Proto",
        "connection": "thread",
        "female_id_range_mm": [26.0, 44.0],
        "notes": "Placeholder para futuro: base por enrosque. Todavía no genera geometría, solo sirve para testear lógica.",
        "mount_profile": {},
    },
    {
        "id": "placeholder_press_fit",
        "family_id": "pressfitbase",
        "family_label": "PressFitBase",
        "preferred_engine_families": ["lamp", "lgb"],
        "label": "PressFitBase Proto",
        "connection": "press_fit",
        "female_id_range_mm": [22.0, 46.0],
        "notes": "Placeholder para futuro: click / presión. Todavía no genera geometría, solo sirve para testear lógica.",
        "mount_profile": {},
    },
]

def _numeric(value: Any) -> float | None:
    try:
        numeric = float(value)
    except Exception:
        return None
    if not math.isfinite(numeric):
        return None
    return numeric

def detect_mount_interface(params: dict[str, Any]) -> dict[str, Any]:
    socket_id = _numeric(params.get("socket_id"))
    if socket_id is not None and socket_id >= 16.0:
        return {"type": "bayonet_female", "female_id_mm": socket_id, "source": "socket_id"}

    opening_radius = _numeric(params.get("opening_radius"))
    if opening_radius is not None and opening_radius >= 8.0:
        return {"type": "ring", "female_id_mm": opening_radius * 2.0, "source": "opening_radius"}

    return {"type": "unknown", "source": "none"}

def infer_mount_interface(
    params: dict[str, Any],
    footprint: dict[str, Any] | None = None,
    fit_profile: dict[str, Any] | None = None,
    engine_id: str | None = None,
) -> dict[str, Any]:
    mount = detect_mount_interface(params)
    if mount.get("type") != "unknown":
        return mount

    fit_profile = fit_profile or {}
    lower = fit_profile.get("lower") or {}
    inferred_diameter = _numeric(lower.get("inner_diameter_safe")) or _numeric(lower.get("inner_diameter"))
    footprint = footprint or {}
    if inferred_diameter is None:
        inferred_diameter = _numeric(footprint.get("diameter_avg")) or _numeric(footprint.get("radius_p90"))
    if inferred_diameter is not None:
        if inferred_diameter == _numeric(footprint.get("diameter_avg")) and "radius_p90" in footprint:
            inferred_diameter = max(inferred_diameter, float(footprint.get("radius_p90") or 0.0) * 2.0)
        inferred_type = "ring"
        if engine_id and engine_id.startswith("pb") and inferred_diameter <= 60.0:
            inferred_type = "bayonet_female"
        source = "fit_profile" if lower else "footprint"
        return {"type": inferred_type, "female_id_mm": inferred_diameter, "source": source}

    return mount

def _base_connection_for_mount_type(mount_type: str) -> str | None:
    if mount_type == "bayonet_female":
        return "bayonet"
    if mount_type == "ring":
        return "ring"
    return None

def recommend_bases_for_mount(
    mount: dict[str, Any],
    engine_family_id: str | None = None,
    selected_family_id: str | None = None,
) -> list[dict[str, Any]]:
    mount_type = mount.get("type")
    female_id = _numeric(mount.get("female_id_mm"))

    connection = _base_connection_for_mount_type(mount_type) or "ring"
    candidates = [base for base in BASES_CATALOG if base.get("connection") == connection]
    if selected_family_id:
        candidates = [base for base in candidates if base.get("family_id") == selected_family_id]
    if not candidates:
        candidates = [base for base in BASES_CATALOG if base.get("connection") == connection]
    if female_id is None:
        return [
            {"id": base["id"], "label": base["label"], "score": 9.99, "reason": "Falta diámetro de interface."}
            for base in candidates
        ]

    scored: list[dict[str, Any]] = []
    for base in candidates:
        r0, r1 = base.get("female_id_range_mm") or [None, None]
        r0n = _numeric(r0)
        r1n = _numeric(r1)
        if r0n is None or r1n is None or r1n <= r0n:
            continue
        ideal = (r0n + r1n) / 2.0
        width = (r1n - r0n) / 2.0
        inside = r0n <= female_id <= r1n
        dist = abs(female_id - ideal) / max(1e-6, width)
        penalty = 0.0 if inside else 1.0 + (min(abs(female_id - r0n), abs(female_id - r1n)) / max(1e-6, width))
        affinity = 0.0
        preferred = base.get("preferred_engine_families") or []
        if engine_family_id and preferred and engine_family_id not in preferred:
            affinity = 0.45
        score = dist + penalty + affinity
        reason = f"ID {female_id:.1f} mm vs rango {r0n:.1f}-{r1n:.1f} mm."
        scored.append({
            "id": base["id"],
            "label": base["label"],
            "family_id": base.get("family_id"),
            "family_label": base.get("family_label"),
            "score": float(score),
            "reason": reason,
        })

    scored.sort(key=lambda item: item["score"])
    return scored[:6]

def _model_bounds_for_payload(payload: dict) -> dict[str, Any]:
    engine_id = resolve_engine_id(payload)
    _, triangles = build_triangles(engine_id, payload, interactive=True)
    indexed = triangles_to_indexed_mesh(decimate_triangles(triangles, 24000))
    return indexed["bounds"]

def analyze_model_footprint(payload: dict) -> dict[str, Any]:
    engine_id = resolve_engine_id(payload)
    _, triangles = build_triangles(engine_id, payload, interactive=True)
    indexed = triangles_to_indexed_mesh(decimate_triangles(triangles, 36000))
    vertices = indexed["vertices"]
    bounds = indexed["bounds"]
    min_z = float(bounds["min"][2])
    max_z = float(bounds["max"][2])
    height = max(0.001, max_z - min_z)
    band_height = max(4.0, min(18.0, height * 0.08))
    cutoff_z = min_z + band_height

    footprint_vertices = [vertex for vertex in vertices if float(vertex[2]) <= cutoff_z]
    if not footprint_vertices:
        footprint_vertices = vertices

    xs = [float(vertex[0]) for vertex in footprint_vertices]
    ys = [float(vertex[1]) for vertex in footprint_vertices]
    radii = [math.hypot(float(vertex[0]), float(vertex[1])) for vertex in footprint_vertices]

    if not xs or not ys or not radii:
        return {
            "opening_band_z": cutoff_z,
            "sample_count": 0,
            "diameter_x": 0.0,
            "diameter_y": 0.0,
            "diameter_avg": 0.0,
            "radius_max": 0.0,
            "radius_p90": 0.0,
        }

    sorted_radii = sorted(radii)
    p90_index = min(len(sorted_radii) - 1, max(0, int(len(sorted_radii) * 0.9)))
    radius_p90 = float(sorted_radii[p90_index])
    diameter_x = max(xs) - min(xs)
    diameter_y = max(ys) - min(ys)
    diameter_avg = float((diameter_x + diameter_y) * 0.5)
    aspect_ratio = float(max(diameter_x, diameter_y) / max(1e-6, min(diameter_x, diameter_y)))
    corner_ratio = float((max(radii) * 2.0) / max(1e-6, diameter_avg))
    if corner_ratio >= 1.18:
        shape_hint = "angular"
    elif aspect_ratio >= 1.18:
        shape_hint = "oval"
    else:
        shape_hint = "round"
    return {
        "opening_band_z": cutoff_z,
        "sample_count": len(footprint_vertices),
        "diameter_x": float(diameter_x),
        "diameter_y": float(diameter_y),
        "diameter_avg": diameter_avg,
        "radius_max": float(max(radii)),
        "radius_p90": radius_p90,
        "aspect_ratio": aspect_ratio,
        "corner_ratio": corner_ratio,
        "shape_hint": shape_hint,
    }

def analyze_fit_profile(payload: dict, depth_mm: float = 20.0) -> dict[str, Any]:
    engine_id = resolve_engine_id(payload)
    _, triangles = build_triangles(engine_id, payload, interactive=True)
    indexed = triangles_to_indexed_mesh(decimate_triangles(triangles, 40000))
    vertices = indexed["vertices"]
    bounds = indexed["bounds"]
    min_z = float(bounds["min"][2])
    lower_limit = min_z + min(4.0, depth_mm * 0.25)
    upper_start = min_z + max(0.0, depth_mm - 4.0)
    upper_limit = min_z + depth_mm

    lower_vertices = [vertex for vertex in vertices if float(vertex[2]) <= lower_limit]
    upper_vertices = [vertex for vertex in vertices if upper_start <= float(vertex[2]) <= upper_limit]
    if not lower_vertices:
        lower_vertices = vertices
    if not upper_vertices:
        upper_vertices = lower_vertices

    def _measure(points: list[list[float]]) -> dict[str, float]:
        xs = [float(vertex[0]) for vertex in points]
        ys = [float(vertex[1]) for vertex in points]
        radii = [math.hypot(float(vertex[0]), float(vertex[1])) for vertex in points]
        diameter_x = max(xs) - min(xs) if xs else 0.0
        diameter_y = max(ys) - min(ys) if ys else 0.0
        diameter_avg = (diameter_x + diameter_y) * 0.5
        sorted_radii = sorted(radii)
        radius_p12 = sorted_radii[min(len(sorted_radii) - 1, max(0, int(len(sorted_radii) * 0.12)))] if sorted_radii else 0.0
        radius_p20 = sorted_radii[min(len(sorted_radii) - 1, max(0, int(len(sorted_radii) * 0.20)))] if sorted_radii else 0.0
        radius_p90 = sorted_radii[min(len(sorted_radii) - 1, max(0, int(len(sorted_radii) * 0.9)))] if sorted_radii else 0.0
        return {
            "diameter_x": float(diameter_x),
            "diameter_y": float(diameter_y),
            "diameter_avg": float(diameter_avg),
            "inner_diameter": float(radius_p12 * 2.0),
            "inner_diameter_safe": float(radius_p20 * 2.0),
            "radius_p90": float(radius_p90),
        }

    lower = _measure(lower_vertices)
    upper = _measure(upper_vertices)
    slice_count = 5
    slice_height = depth_mm / slice_count if slice_count > 0 else depth_mm
    slices: list[dict[str, Any]] = []
    for index in range(slice_count):
        z0 = min_z + slice_height * index
        z1 = min_z + slice_height * (index + 1)
        slice_vertices = [vertex for vertex in vertices if z0 <= float(vertex[2]) <= z1]
        if not slice_vertices:
            slice_vertices = lower_vertices if index == 0 else upper_vertices
        measurement = _measure(slice_vertices)
        measurement.update({
            "z_start": float(z0 - min_z),
            "z_end": float(z1 - min_z),
            "z_mid": float(((z0 + z1) * 0.5) - min_z),
            "index": index,
        })
        slices.append(measurement)
    return {
        "fit_depth_mm": float(depth_mm),
        "lower": lower,
        "upper": upper,
        "slices": slices,
    }

def available_base_families(
    mount: dict[str, Any],
    engine_family_id: str | None = None,
) -> list[dict[str, Any]]:
    connection = _base_connection_for_mount_type(str(mount.get("type") or "")) or "ring"
    seen: set[str] = set()
    families: list[dict[str, Any]] = []
    for base in BASES_CATALOG:
        family_id = str(base.get("family_id") or base.get("id"))
        if family_id in seen:
            continue
        seen.add(family_id)
        preferred = base.get("preferred_engine_families") or []
        recommended = bool(engine_family_id and preferred and engine_family_id in preferred)
        compatible = base.get("connection") == connection
        families.append({
            "id": family_id,
            "label": base.get("family_label") or family_id,
            "recommended": recommended,
            "compatible": compatible,
            "connection": base.get("connection"),
        })
    families.sort(key=lambda item: (0 if item["compatible"] else 1, 0 if item["recommended"] else 1, item["label"]))
    return families

def get_base_generator(generator_id: str | None = None):
    resolved = generator_id or DEFAULT_BASE_GENERATOR_ID
    generator = BASE_GENERATORS.get(resolved or "")
    if generator is None:
        raise HTTPException(status_code=500, detail="Base generator unavailable")
    return resolved, generator

def build_base_context(payload: dict) -> dict[str, Any]:
    generator_id = payload.get("base_generator") or DEFAULT_BASE_GENERATOR_ID
    resolved_generator_id, generator = get_base_generator(generator_id)

    engine_id = resolve_engine_id(payload)
    engine_info = get_engine_info(engine_id)
    bounds = _model_bounds_for_payload(payload)
    footprint = analyze_model_footprint(payload)
    fit_profile = analyze_fit_profile(payload, 20.0)
    mount = infer_mount_interface(payload, footprint, fit_profile, engine_id)
    footprint_for_defaults = dict(footprint)
    footprint_for_defaults.update({
        "fit_depth_mm": fit_profile["fit_depth_mm"],
        "fit_lower_diameter_x": fit_profile["lower"]["diameter_x"],
        "fit_lower_diameter_y": fit_profile["lower"]["diameter_y"],
        "fit_lower_diameter_avg": fit_profile["lower"]["diameter_avg"],
        "fit_lower_inner_diameter": fit_profile["lower"]["inner_diameter"],
        "fit_lower_inner_diameter_safe": fit_profile["lower"]["inner_diameter_safe"],
        "fit_upper_diameter_x": fit_profile["upper"]["diameter_x"],
        "fit_upper_diameter_y": fit_profile["upper"]["diameter_y"],
        "fit_upper_diameter_avg": fit_profile["upper"]["diameter_avg"],
        "fit_upper_inner_diameter": fit_profile["upper"]["inner_diameter"],
        "fit_upper_inner_diameter_safe": fit_profile["upper"]["inner_diameter_safe"],
        "fit_slices": fit_profile.get("slices") or [],
    })
    defaults = generator.suggest_defaults(mount, bounds, footprint_for_defaults)
    return {
        "engine": engine_id,
        "engine_label": engine_label(engine_id),
        "engine_family": engine_info["family"],
        "base_generator": resolved_generator_id,
        "base_generator_label": getattr(generator, "GENERATOR_LABEL", resolved_generator_id),
        "base_generators": [
            {
                "id": item_id,
                "label": getattr(item_generator, "GENERATOR_LABEL", item_id),
            }
            for item_id, item_generator in BASE_GENERATORS.items()
        ],
        "mount_interface": mount,
        "lamp_bounds": bounds,
        "footprint": footprint,
        "fit_profile": fit_profile,
        "base_families": available_base_families(mount, engine_info["family"]),
        "defaults": defaults,
        "limits": generator.LIMITS,
        "descriptions": generator.DESCRIPTIONS,
    }

def build_inverse_base_params(payload: dict):
    model_payload = payload.get("model") or {}
    context = build_base_context(model_payload)
    _, generator = get_base_generator(context.get("base_generator"))
    defaults = dict(context["defaults"])
    overrides = payload.get("params") or {}
    accepted = set(defaults.keys())

    merged = dict(defaults)
    for key, value in overrides.items():
        if key not in accepted:
            continue
        merged[key] = value

    limits = context["limits"]
    for key, value in list(merged.items()):
        limit = limits.get(key)
        if limit is None:
            continue
        numeric = _numeric(value)
        if numeric is None:
            numeric = _numeric(defaults[key])
        if numeric is None:
            continue
        numeric = max(float(limit["min"]), min(float(limit["max"]), numeric))
        default_numeric = _numeric(defaults[key])
        if default_numeric is not None and float(limit["step"]).is_integer() and float(default_numeric).is_integer():
            numeric = int(round(numeric))
        merged[key] = numeric

    return context, generator.BaseParams(**merged)

def build_inverse_base_triangles(payload: dict):
    context, params = build_inverse_base_params(payload)
    _, generator = get_base_generator(context.get("base_generator"))
    triangles = generator.make_mesh(params)
    return context, params, triangles

def inverse_base_export_file_name(model_payload: dict, params: Any) -> str:
    engine_id = model_payload.get("engine") or "model"
    interface_tag = getattr(params, "interface_type", "base")
    diameter = int(round(getattr(params, "interface_diameter", 0.0)))
    return f"base_{engine_id}_{interface_tag}_id{diameter}.stl"

@app.get("/api/config")
async def api_config():
    engines = []
    engine_configs = {}
    for engine_id in ENGINES:
        info = get_engine_info(engine_id)
        label = engine_label(engine_id)
        engines.append({"id": engine_id, "label": label, "family": info["family"]})
        engine_configs[engine_id] = {
            "label": label,
            "defaults": info["defaults"],
            "limits": info["limits"],
            "descriptions": info["descriptions"],
            "presets": info["presets"],
            "supports_modes": info["supports_modes"],
            "supports_close_top": info["supports_close_top"],
            "supports_dome_mode": info["supports_dome_mode"],
        }

    family_order = {"lamp": 0, "pb": 1, "lgb": 2, "misc": 9}
    engines.sort(key=lambda item: (family_order.get(item["family"], 50), item["label"]))
    default_engine = DEFAULT_ENGINE_ID or (engines[0]["id"] if engines else None)
    if default_engine is None:
        raise HTTPException(status_code=500, detail="No engines available")
    return {"default_engine": default_engine, "engines": engines, "engine_configs": engine_configs}

@app.get("/api/workbench/engines")
async def api_workbench_engines():
    items = engine_workbench_items()
    summary = {
        "ready": sum(1 for item in items if item["status"] == "ready"),
        "incompatible": sum(1 for item in items if item["status"] == "incompatible"),
        "import_error": sum(1 for item in items if item["status"] == "import_error"),
        "ignored": sum(1 for item in items if item["status"] == "ignored"),
    }
    return {
        "summary": summary,
        "default_engine": DEFAULT_ENGINE_ID,
        "items": items,
    }

@app.get("/api/bases/catalog")
async def api_bases_catalog():
    return {"bases": BASES_CATALOG, "version": "2026-03-27"}

@app.post("/api/bases/recommend")
async def api_bases_recommend(payload: dict):
    selected_family_id = payload.get("base_family")
    context = build_base_context(payload)
    mount = context["mount_interface"]
    engine_family_id = context.get("engine_family")
    families = context.get("base_families") or []
    family_id = selected_family_id or (families[0]["id"] if families else None)
    recommendations = recommend_bases_for_mount(mount, engine_family_id, family_id)
    return {
        "mount_interface": mount,
        "footprint": context.get("footprint"),
        "base_families": families,
        "selected_family": family_id,
        "recommendations": recommendations,
    }

@app.post("/api/base/context")
async def api_base_context(payload: dict):
    return build_base_context(payload)

@app.post("/api/base/preview")
async def api_base_preview(payload: dict):
    context, params, triangles = build_inverse_base_triangles(payload)
    return {
        "context": context,
        "params": asdict(params),
        "mesh": triangles_to_indexed_mesh(decimate_triangles(triangles, 120000)),
    }

@app.post("/api/base/export")
async def api_base_export(payload: dict):
    context, params, triangles = build_inverse_base_triangles(payload)
    EXPORT_DIR.mkdir(exist_ok=True)
    model_payload = payload.get("model") or {}
    file_name = inverse_base_export_file_name(model_payload, params)
    path = (EXPORT_DIR / file_name).resolve()
    write_binary_stl(path, triangles)
    return {
        "ok": True,
        "file": file_name,
        "path": str(path),
        "triangle_count": len(triangles),
        "context": context,
        "params": asdict(params),
    }

@app.post("/api/preview")
async def api_preview(payload: dict):
    engine_id = resolve_engine_id(payload)
    meta, triangles = build_triangles(engine_id, payload, interactive=True)
    return {"meta": meta, "mesh": triangles_to_indexed_mesh(triangles)}

@app.post("/api/export")
async def api_export(payload: dict):
    engine_id = resolve_engine_id(payload)
    meta, triangles = build_triangles(engine_id, payload, interactive=False)
    EXPORT_DIR.mkdir(exist_ok=True)
    file_name = export_file_name(engine_id, payload)
    path = (EXPORT_DIR / file_name).resolve()
    write_binary_stl(path, triangles)
    return {"ok": True, "file": file_name, "path": str(path), "triangle_count": len(triangles), "meta": meta}

@app.get("/api/exports")
async def api_exports():
    EXPORT_DIR.mkdir(exist_ok=True)
    files = [
        {"name": file.name, "size": file.stat().st_size}
        for file in sorted(EXPORT_DIR.glob("*.stl"), key=lambda p: p.stat().st_mtime, reverse=True)
    ]
    return {"files": files[:20]}

@app.get("/api/download")
async def api_download(name: str):
    path = (EXPORT_DIR / Path(name).name).resolve()
    if not path.exists() or path.parent != EXPORT_DIR.resolve():
        raise HTTPException(status_code=404, detail="Export not found")
    return FileResponse(path, media_type="application/sla", filename=path.name)

@app.post("/api/import")
async def api_import(request: Request):
    filename = request.headers.get("X-Filename", "import.stl")
    content = await request.body()

    try:
        import trimesh

        suffix = Path(filename).suffix.lower().lstrip(".") or None
        mesh = trimesh.load(io.BytesIO(content), file_type=suffix, force="mesh")
        triangles = mesh.triangles.tolist()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    preview_triangles = decimate_triangles(triangles, 80000)
    indexed = triangles_to_indexed_mesh(preview_triangles)
    return {
        "ok": True,
        "file": filename,
        "triangle_count": len(triangles),
        "preview_triangle_count": indexed["triangle_count"],
        "mesh": indexed,
        "source": "import",
    }

COMMON_LIMITS = {
    "width_mm": {"min": 60.0, "max": 420.0, "step": 1.0},
    "height_mm": {"min": 60.0, "max": 520.0, "step": 1.0},
    "depth_mm": {"min": 40.0, "max": 420.0, "step": 1.0},
    "shade_thickness_mm": {"min": 0.6, "max": 8.0, "step": 0.1},
    "num_arms": {"min": 2, "max": 12, "step": 1},
    "base_diameter_mm": {"min": 30.0, "max": 220.0, "step": 1.0},
    "cord_length_mm": {"min": 20.0, "max": 220.0, "step": 1.0},
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
    "cube_mix": {"min": 0.0, "max": 1.0, "step": 0.01},
    "cube_roundness": {"min": 0.0, "max": 1.0, "step": 0.01},
    "outer_smoothing": {"min": 0.0, "max": 1.0, "step": 0.01},
    "inner_smoothing": {"min": 0.0, "max": 1.0, "step": 0.01},
    "top_style": {"min": 0.0, "max": 3.0, "step": 1},
    "flow_sway": {"min": 0.0, "max": 1.2, "step": 0.01},
    "flow_wave_count": {"min": 0.5, "max": 8.0, "step": 0.05},
    "opening_radius": {"min": 8.0, "max": 60.0, "step": 0.5},
    "opening_softness": {"min": 0.02, "max": 0.6, "step": 0.01},
    "lamp_clearance": {"min": 12.0, "max": 80.0, "step": 0.5},
    "width": {"min": 30.0, "max": 180.0, "step": 1.0},
    "depth": {"min": 18.0, "max": 120.0, "step": 1.0},
    "top_scale": {"min": 0.45, "max": 1.0, "step": 0.01},
    "body_roundness": {"min": 0.1, "max": 1.0, "step": 0.01},
    "side_tuck": {"min": 0.0, "max": 0.6, "step": 0.01},
    "belly": {"min": 0.0, "max": 0.5, "step": 0.01},
    "pleat_depth": {"min": 0.0, "max": 0.3, "step": 0.01},
    "pleat_count": {"min": 3, "max": 12, "step": 1},
    "rim_wave_amp": {"min": 0.0, "max": 14.0, "step": 0.1},
    "rim_wave_count": {"min": 3, "max": 12, "step": 1},
    "rim_band_height": {"min": 4.0, "max": 28.0, "step": 0.5},
    "handle_span": {"min": 20.0, "max": 120.0, "step": 0.5},
    "handle_drop": {"min": 20.0, "max": 100.0, "step": 0.5},
    "handle_pair_gap": {"min": 0.0, "max": 24.0, "step": 0.5},
    "handle_thickness": {"min": 1.0, "max": 8.0, "step": 0.05},
    "eyelet_radius": {"min": 1.2, "max": 8.0, "step": 0.05},
    "eyelet_thickness": {"min": 0.5, "max": 3.0, "step": 0.05},
    "eyelet_count": {"min": 2, "max": 10, "step": 1},
    "eyelet_drop": {"min": 4.0, "max": 26.0, "step": 0.5},
    "drawstring_thickness": {"min": 0.4, "max": 4.0, "step": 0.05},
    "drawstring_drop": {"min": 6.0, "max": 60.0, "step": 0.5},
    "target_triangles": {"min": 1000, "max": 1000000, "step": 1000},
}

COMMON_DESCRIPTIONS = {
    "width_mm": "Ancho general de la lámpara en milímetros (motor SCAD).",
    "height_mm": "Altura general de la lámpara en milímetros (motor SCAD).",
    "depth_mm": "Profundidad general de la lámpara en milímetros (motor SCAD).",
    "shade_thickness_mm": "Espesor de pared de pantalla/casco en milímetros (motor SCAD).",
    "num_arms": "Cantidad de brazos para motores tipo chandelier.",
    "base_diameter_mm": "Diámetro base de soporte o montaje en milímetros.",
    "cord_length_mm": "Largo de cable/varilla en milímetros para lámparas colgantes.",
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
    "cube_mix": "Cuanto se empuja la seccion desde circular hacia cubica.",
    "cube_roundness": "Que tan filoso o redondeado queda el cubo.",
    "outer_smoothing": "Cuanto se alisa la piel exterior contra la forma base.",
    "inner_smoothing": "Cuanto se alisa la cara interior para dejarla mas limpia.",
    "top_style": "Estilo de cierre superior: 0 plano, 1 domo, 2 piramide, 3 inset.",
    "flow_sway": "Cuanto ondulan lateralmente las nervaduras mientras suben sobre la esfera.",
    "flow_wave_count": "Cantidad de oscilaciones verticales del patron fluido sobre la superficie.",
    "opening_radius": "Tamano de la boca inferior para alojar foco o soporte.",
    "opening_softness": "Que tan suave se mezcla la zona de la boca con el resto de la esfera.",
    "lamp_clearance": "Espacio interior reservado para la lampara en la cavidad central.",
    "width": "Ancho maximo del bolso medido de lateral a lateral.",
    "depth": "Profundidad frontal del bolso en su panza principal.",
    "top_scale": "Cuanto se cierra la boca respecto del cuerpo inferior.",
    "body_roundness": "Balance entre base mullida y seccion mas recta tipo bolsito.",
    "side_tuck": "Cuanto se recogen los laterales hacia la boca.",
    "belly": "Cuanto se infla el frente y la espalda del cuerpo.",
    "pleat_depth": "Intensidad del frunce vertical del cuerpo.",
    "pleat_count": "Cantidad de panos o pliegues principales alrededor del bolso.",
    "rim_wave_amp": "Altura de la ondulacion delicada en la boca.",
    "rim_wave_count": "Cantidad de ondas suaves en el borde superior.",
    "rim_band_height": "Altura de la zona superior donde se concentra el frunce.",
    "handle_span": "Separacion lateral efectiva entre apoyos de las asas.",
    "handle_drop": "Altura extra que gana el arco del asa sobre la boca.",
    "handle_pair_gap": "Separacion entre la asa delantera y la trasera.",
    "handle_thickness": "Radio del tubo usado para las asas.",
    "eyelet_radius": "Radio del herraje circular para el pasacordon.",
    "eyelet_thickness": "Espesor del herraje circular.",
    "eyelet_count": "Cantidad de ojales visibles en el frente.",
    "eyelet_drop": "Distancia vertical entre la boca y la linea de ojales.",
    "drawstring_thickness": "Espesor del cordon frontal.",
    "drawstring_drop": "Caida vertical de las puntas del cordon.",
    "target_triangles": "Cantidad objetivo de triangulos para la preview interactiva de este motor.",
}

COMMON_SAFE_FLOORS = {
    "width_mm": 0.001,
    "height_mm": 0.001,
    "depth_mm": 0.001,
    "shade_thickness_mm": 0.0,
    "num_arms": 1,
    "base_diameter_mm": 0.001,
    "cord_length_mm": 0.001,
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
    "width": 0.001,
    "depth": 0.001,
    "top_scale": 0.001,
    "body_roundness": 0.001,
    "side_tuck": 0.0,
    "belly": 0.0,
    "pleat_depth": 0.0,
    "pleat_count": 1,
    "rim_wave_amp": 0.0,
    "rim_wave_count": 1,
    "rim_band_height": 0.001,
    "handle_span": 0.001,
    "handle_drop": 0.001,
    "handle_pair_gap": 0.0,
    "handle_thickness": 0.001,
    "eyelet_radius": 0.001,
    "eyelet_thickness": 0.001,
    "eyelet_count": 1,
    "eyelet_drop": 0.001,
    "drawstring_thickness": 0.001,
    "drawstring_drop": 0.001,
}

def subset_map(defaults: dict[str, Any], mapping: dict[str, Any]) -> dict[str, Any]:
    return {key: mapping[key] for key in defaults if key in mapping}

def merged(base: dict[str, Any], **updates: Any) -> dict[str, Any]:
    payload = dict(base)
    payload.update(updates)
    return payload

def lamp_defaults(engine_id: str) -> dict[str, Any]:
    engine = ENGINES[engine_id]
    defaults = _safe_lamp_defaults_from_engine(engine)
    if defaults is None:
        return {}
    return defaults

def wire_defaults(engine_id: str) -> dict[str, Any]:
    engine = ENGINES[engine_id]
    params_cls = getattr(engine, "WireParams", None)
    if params_cls is None:
        return {}
    try:
        instance = params_cls()
    except Exception:
        return {}
    defaults = _defaults_from_params_instance(instance)
    return defaults or {}

def build_family_presets(
    defaults: dict[str, Any],
    family: str,
    supports_modes: bool = False,
    supports_close_top: bool = False,
    supports_dome_mode: bool = False,
) -> dict[str, dict[str, Any]]:
    presets = {"default": dict(defaults)}

    # Generic presets (work across families when keys exist)
    if "height" in defaults:
        presets["tall"] = merged(defaults, height=float(defaults["height"]) * 1.25)
        presets["short"] = merged(defaults, height=float(defaults["height"]) * 0.85)
    if "r_base" in defaults:
        presets["wide"] = merged(defaults, r_base=float(defaults["r_base"]) * 1.18)
        presets["narrow"] = merged(defaults, r_base=float(defaults["r_base"]) * 0.9)
    if "thickness" in defaults:
        presets["thin_wall"] = merged(defaults, thickness=max(0.4, float(defaults["thickness"]) * 0.75))
        presets["thick_wall"] = merged(defaults, thickness=float(defaults["thickness"]) * 1.25)
    if "bulb_amp" in defaults:
        presets["bulbous"] = merged(defaults, bulb_amp=float(defaults["bulb_amp"]) * 1.4)
    if "cube_mix" in defaults:
        presets["boxy"] = merged(defaults, cube_mix=min(1.0, float(defaults["cube_mix"]) + 0.18))
    if "weave_amp" in defaults:
        presets["woven"] = merged(defaults, weave_amp=float(defaults["weave_amp"]) * 1.25)

    if family == "pb":
        presets["tall_shell"] = merged(
            defaults,
            height=float(defaults.get("height", 160.0)) * 1.25,
            r_base=float(defaults.get("r_base", 35.0)) * 0.92,
            bulb_amp=float(defaults.get("bulb_amp", 8.0)) * 1.15,
            seam_pitch=float(defaults.get("seam_pitch", 2.8)) * 1.1,
            seam_height=float(defaults.get("seam_height", 1.6)) * 1.15,
        )
        presets["lantern_bloom"] = merged(
            defaults,
            height=float(defaults.get("height", 160.0)) * 1.08,
            r_base=float(defaults.get("r_base", 35.0)) * 1.16,
            bulb_amp=float(defaults.get("bulb_amp", 8.0)) * 1.65,
            bulb_count=max(1.1, float(defaults.get("bulb_count", 2.0)) * 0.78),
            taper=max(0.005, float(defaults.get("taper", 0.04)) * 0.5),
            seam_width=float(defaults.get("seam_width", 4.0)) * 1.15,
        )
        presets["braided_column"] = merged(
            defaults,
            height=float(defaults.get("height", 160.0)) * 1.28,
            r_base=float(defaults.get("r_base", 35.0)) * 0.9,
            bulb_amp=float(defaults.get("bulb_amp", 8.0)) * 0.72,
            bulb_count=float(defaults.get("bulb_count", 2.0)) + 1.1,
            seam_count=max(10, int(round(float(defaults.get("seam_count", 18)) * 1.12))),
            seam_pitch=float(defaults.get("seam_pitch", 2.8)) * 1.22,
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
        presets["open_lattice"] = merged(defaults, **open_updates)
        presets["diamond_hourglass"] = merged(
            defaults,
            height=float(defaults.get("height", 160.0)) * 1.15,
            r_base=float(defaults.get("r_base", 35.0)) * 0.95,
            bulb_amp=float(defaults.get("bulb_amp", 8.0)) * 1.35,
            bulb_count=float(defaults.get("bulb_count", 2.0)) + 0.8,
            taper=max(0.005, float(defaults.get("taper", 0.04)) * 0.3),
            seam_count=max(12, int(round(float(defaults.get("seam_count", 18)) * 1.05))),
            seam_pitch=float(defaults.get("seam_pitch", 2.8)) * 0.95,
            seam_width=float(defaults.get("seam_width", 4.0)) * 0.9,
        )

    return presets

def get_engine_info(engine_id: str) -> dict[str, Any]:
    engine = ENGINES[engine_id]
    defaults = lamp_defaults(engine_id)
    family = engine_family(engine_id, engine)

    has_mode_mesh = callable(getattr(engine, "make_mesh_solid", None)) and callable(
        getattr(engine, "make_mesh_perforated", None)
    )
    supports_modes = ("mode" in defaults) or has_mode_mesh

    supports_close_top = "close_top" in defaults
    supports_dome_mode = "dome_mode" in defaults
    if has_mode_mesh:
        try:
            signature = inspect.signature(getattr(engine, "make_mesh_perforated"))
            supports_close_top = supports_close_top or ("close_top" in signature.parameters)
            supports_dome_mode = supports_dome_mode or ("dome_mode" in signature.parameters)
        except Exception:
            pass

    param_limits = subset_map(defaults, COMMON_LIMITS)
    param_descriptions = subset_map(defaults, COMMON_DESCRIPTIONS)
    param_safe_floors = subset_map(defaults, COMMON_SAFE_FLOORS)

    presets = build_family_presets(
        defaults, family, supports_modes, supports_close_top, supports_dome_mode
    )

    return {
        "id": engine_id,
        "family": family,
        "defaults": defaults,
        "limits": param_limits,
        "descriptions": param_descriptions,
        "safe_floors": param_safe_floors,
        "presets": presets,
        "supports_modes": supports_modes,
        "supports_close_top": supports_close_top,
        "supports_dome_mode": supports_dome_mode,
    }

class GenerationParams(BaseModel):
    params: dict = {}

@app.get("/api/")
async def root():
    return {"status": "Atlas Multiversal API online", "version": "1.0.0"}

@app.get("/config")
async def config():
    return {engine_id: get_engine_info(engine_id) for engine_id in ENGINES}

@app.post("/generate")
async def generate(data: dict):
    engine_id = data.get("engine")
    params = data.get("params", {})
    target_triangles = data.get("target_triangles", 120000)

    if engine_id not in ENGINES:
        raise HTTPException(status_code=404, detail="Engine not found")

    payload = {"engine": engine_id, "target_triangles": target_triangles, **params}
    meta, triangles = build_triangles(engine_id, payload, interactive=False)

    stl_data = io.BytesIO()
    header = b"aml_binary_stl".ljust(80, b"\0")
    stl_data.write(header)
    stl_data.write(struct.pack("<I", len(triangles)))
    for (v0, v1, v2) in triangles:
        normal = _stl_normal(v0, v1, v2)
        stl_data.write(struct.pack("<3f", *normal))
        stl_data.write(struct.pack("<3f", float(v0[0]), float(v0[1]), float(v0[2])))
        stl_data.write(struct.pack("<3f", float(v1[0]), float(v1[1]), float(v1[2])))
        stl_data.write(struct.pack("<3f", float(v2[0]), float(v2[1]), float(v2[2])))
        stl_data.write(struct.pack("<H", 0))
    stl_data.seek(0)
    return Response(content=stl_data.getvalue(), media_type="application/octet-stream")

@app.post("/export")
async def export(data: dict):
    engine_id = data.get("engine")
    params = data.get("params", {})
    filename = data.get("filename", f"{engine_id}_export.stl")

    if engine_id not in ENGINES:
        raise HTTPException(status_code=404, detail="Engine not found")

    payload = {"engine": engine_id, **params}
    meta, triangles = build_triangles(engine_id, payload, interactive=False)
    EXPORT_DIR.mkdir(exist_ok=True)
    export_path = (EXPORT_DIR / Path(filename).name).resolve()
    write_binary_stl(export_path, triangles)
    return {"status": "exported", "path": str(export_path), "triangle_count": len(triangles), "meta": meta}

@app.post("/api/generate/{generator_name}")
async def generate_old(generator_name: str, data: dict):
    """
    Endpoint para llamar a los scripts del HDD.
    """
    print(f"Generando {generator_name} con parÃƒÆ’Ã‚Â¡metros: {data}")
    
    # LÃƒÆ’Ã‚Â³gica de conexiÃƒÆ’Ã‚Â³n con los scripts reales
    # 1. Importar el script desde /generators/ (ej: from generators.lampgen import generate_lamp)
    # 2. Ejecutar la funciÃƒÆ’Ã‚Â³n con los parÃƒÆ’Ã‚Â¡metros recibidos
    # 3. Devolver la ruta del archivo STL generado
    
    if generator_name not in ["lamp", "drone", "planet"]:
        raise HTTPException(status_code=404, detail="Generador no encontrado")
        
    return {
        "status": "success",
        "message": f"{generator_name} generado correctamente",
        "path": f"/outputs/{generator_name}_model_0001.stl"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
