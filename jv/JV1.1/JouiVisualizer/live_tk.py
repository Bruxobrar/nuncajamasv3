import math
import tkinter as tk
from dataclasses import asdict
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
PB6_PATH = REPO_ROOT / "lampgen" / "pb6.py"


def load_pb6():
    spec = spec_from_file_location("pb6_module", PB6_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {PB6_PATH}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pb6 = load_pb6()
DEFAULT_PARAMS = asdict(pb6.LampParams())
PARAM_LIMITS = {
    "height": {"min": 80, "max": 260, "step": 1},
    "r_base": {"min": 18, "max": 80, "step": 1},
    "thickness": {"min": 0.8, "max": 4.0, "step": 0.05},
    "bulb_amp": {"min": 0.0, "max": 24.0, "step": 0.1},
    "bulb_count": {"min": 0.5, "max": 5.0, "step": 0.05},
    "bulb_phase": {"min": 0.0, "max": 1.0, "step": 0.01},
    "taper": {"min": 0.0, "max": 0.2, "step": 0.005},
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
    "n_theta": {"min": 48, "max": 480, "step": 1},
    "n_z": {"min": 32, "max": 360, "step": 1},
}
PRESETS = {
    "default": DEFAULT_PARAMS,
    "tall_solid": {
        **DEFAULT_PARAMS,
        "height": 210.0,
        "r_base": 36.0,
        "bulb_amp": 10.5,
        "bulb_count": 2.4,
        "seam_pitch": 3.1,
        "seam_height": 2.0,
    },
    "woven_perforated": {
        **DEFAULT_PARAMS,
        "mode": "perforated",
        "close_top": True,
        "dome_mode": "perforated",
        "height": 180.0,
        "r_base": 34.0,
        "seam_count": 16,
        "seam_pitch": 2.5,
        "membrane": 0.15,
        "perforation": 0.55,
        "rib_width_scale": 0.82,
        "rib_thickness": 1.45,
    },
    "lantern": {
        **DEFAULT_PARAMS,
        "mode": "solid",
        "height": 160.0,
        "r_base": 42.0,
        "bulb_amp": 14.0,
        "bulb_count": 1.7,
        "taper": 0.02,
        "seam_width": 5.0,
        "seam_height": 1.2,
    },
}
GROUPS = [
    ("Shape", ["height", "r_base", "thickness", "bulb_amp", "bulb_count", "bulb_phase", "taper"]),
    ("Seam Engine", ["seam_count", "seam_pitch", "seam_width", "seam_height", "seam_softness", "valley_depth", "counter_strength", "counter_phase"]),
    ("Skin", ["membrane", "perforation", "inner_follow"]),
    ("Perforated", ["rib_width_scale", "rib_thickness", "rib_seg_per_pitch", "dome_height_scale"]),
    ("Resolution", ["n_theta", "n_z"]),
]
WORLD_UP = (0.0, 0.0, 1.0)
LIGHT_DIR = (-0.45, -0.3, 0.84)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2) or 1.0
    return (vector[0] / length, vector[1] / length, vector[2] / length)


LIGHT_DIR = normalize(LIGHT_DIR)


def cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def subtract(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mix(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> str:
    color = (
        int(mix(a[0], b[0], t)),
        int(mix(a[1], b[1], t)),
        int(mix(a[2], b[2], t)),
    )
    return "#{:02x}{:02x}{:02x}".format(*color)


def triangles_to_indexed_mesh(triangles: list[tuple[Any, Any, Any]]) -> dict[str, Any]:
    vertices: list[tuple[float, float, float]] = []
    vertex_map: dict[tuple[float, float, float], int] = {}
    indices: list[tuple[int, int, int]] = []
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
                vertices.append(key)
                for axis in range(3):
                    bounds["min"][axis] = min(bounds["min"][axis], key[axis])
                    bounds["max"][axis] = max(bounds["max"][axis], key[axis])
            tri_indices.append(idx)
        indices.append(tuple(tri_indices))

    center = (
        (bounds["min"][0] + bounds["max"][0]) * 0.5,
        (bounds["min"][1] + bounds["max"][1]) * 0.5,
        (bounds["min"][2] + bounds["max"][2]) * 0.5,
    )
    size = (
        bounds["max"][0] - bounds["min"][0],
        bounds["max"][1] - bounds["min"][1],
        bounds["max"][2] - bounds["min"][2],
    )
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


def build_triangles(payload: dict[str, Any], interactive: bool) -> tuple[dict[str, Any], list[tuple[Any, Any, Any]]]:
    params = dict(DEFAULT_PARAMS)
    for key, default_value in DEFAULT_PARAMS.items():
        raw = payload.get(key, default_value)
        limits = PARAM_LIMITS.get(key)
        if isinstance(default_value, int) and not isinstance(default_value, bool):
            value = int(round(float(raw)))
        else:
            value = float(raw)
        if limits:
            value = clamp(value, limits["min"], limits["max"])
            if isinstance(default_value, int) and not isinstance(default_value, bool):
                value = int(round(value))
        params[key] = value

    mode = payload.get("mode", "solid")
    if mode not in {"solid", "perforated"}:
        mode = "solid"

    dome_mode = payload.get("dome_mode", "solid")
    if dome_mode not in {"solid", "perforated"}:
        dome_mode = "solid"

    close_top = bool(payload.get("close_top", False))

    if interactive:
        params["n_theta"] = min(params["n_theta"], 120)
        params["n_z"] = min(params["n_z"], 96)
        params["rib_seg_per_pitch"] = min(params["rib_seg_per_pitch"], 42)

    lamp_params = pb6.LampParams(**params)
    if mode == "solid":
        tris = pb6.make_mesh_solid(lamp_params)
    else:
        tris = pb6.make_mesh_perforated(lamp_params, close_top=close_top, dome_mode=dome_mode)

    return {
        "params": params,
        "mode": mode,
        "close_top": close_top,
        "dome_mode": dome_mode,
        "interactive": interactive,
    }, tris


class ScrollableControls(ttk.Frame):
    def __init__(self, master: tk.Misc):
        super().__init__(master)
        self.canvas = tk.Canvas(self, highlightthickness=0, background="#eef2f5")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.inner.bind("<Configure>", self._sync_scrollregion)
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def _sync_scrollregion(self, _event: tk.Event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))


class LivePB6App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PB6 Live Python Example")
        self.root.geometry("1480x920")
        self.root.configure(background="#dfe6eb")

        self.params = dict(DEFAULT_PARAMS)
        self.mode_var = tk.StringVar(value="solid")
        self.close_top_var = tk.BooleanVar(value=False)
        self.dome_mode_var = tk.StringVar(value="solid")
        self.preset_var = tk.StringVar(value="default")
        self.status_var = tk.StringVar(value="Moviendo parametros...")
        self.stats_var = tk.StringVar(value="")
        self.control_vars: dict[str, tk.Variable] = {}
        self.mesh = None
        self.last_triangles = []
        self.preview_job = None
        self.camera = {"yaw": -0.9, "pitch": 0.55, "distance_factor": 2.7}
        self.drag_origin: tuple[int, int] | None = None

        self._build_ui()
        self.load_preset("default")

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#eef2f5")
        style.configure("Panel.TFrame", background="#eef2f5")
        style.configure("Card.TLabelframe", background="#eef2f5")
        style.configure("Card.TLabelframe.Label", background="#eef2f5", font=("Segoe UI", 10, "bold"))
        style.configure("Title.TLabel", background="#eef2f5", font=("Segoe UI", 18, "bold"), foreground="#13212d")
        style.configure("Subtle.TLabel", background="#eef2f5", foreground="#4e5f6c")
        style.configure("Hud.TLabel", background="#1f2b36", foreground="#eef6fb", padding=8)

        shell = ttk.Frame(self.root, style="Panel.TFrame", padding=12)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=0)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        controls = ttk.Frame(shell, style="Panel.TFrame", width=420, padding=(8, 8, 14, 8))
        controls.grid(row=0, column=0, sticky="nsew")
        controls.grid_propagate(False)
        controls.columnconfigure(0, weight=1)
        ttk.Label(controls, text="PB6 Live Engine", style="Subtle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(controls, text="Python realtime example", style="Title.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 10))

        toolbar = ttk.Frame(controls, style="Panel.TFrame")
        toolbar.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        toolbar.columnconfigure(1, weight=1)
        toolbar.columnconfigure(3, weight=1)
        toolbar.columnconfigure(5, weight=1)

        ttk.Label(toolbar, text="Preset", style="Subtle.TLabel").grid(row=0, column=0, sticky="w")
        preset_box = ttk.Combobox(toolbar, textvariable=self.preset_var, values=list(PRESETS.keys()), state="readonly")
        preset_box.grid(row=0, column=1, sticky="ew", padx=(6, 10))
        preset_box.bind("<<ComboboxSelected>>", lambda _e: self.load_preset(self.preset_var.get()))

        ttk.Label(toolbar, text="Mode", style="Subtle.TLabel").grid(row=0, column=2, sticky="w")
        mode_box = ttk.Combobox(toolbar, textvariable=self.mode_var, values=["solid", "perforated"], state="readonly")
        mode_box.grid(row=0, column=3, sticky="ew", padx=(6, 10))
        mode_box.bind("<<ComboboxSelected>>", lambda _e: self.schedule_preview())

        ttk.Label(toolbar, text="Dome", style="Subtle.TLabel").grid(row=0, column=4, sticky="w")
        dome_box = ttk.Combobox(toolbar, textvariable=self.dome_mode_var, values=["solid", "perforated"], state="readonly")
        dome_box.grid(row=0, column=5, sticky="ew", padx=(6, 0))
        dome_box.bind("<<ComboboxSelected>>", lambda _e: self.schedule_preview())

        toggles = ttk.Frame(controls, style="Panel.TFrame")
        toggles.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        ttk.Checkbutton(toggles, text="Close top", variable=self.close_top_var, command=self.schedule_preview).pack(side="left")
        ttk.Button(toggles, text="Reset preset", command=lambda: self.load_preset(self.preset_var.get())).pack(side="right")
        ttk.Button(toggles, text="Export STL", command=self.export_stl).pack(side="right", padx=(0, 8))

        self.scroll = ScrollableControls(controls)
        self.scroll.grid(row=4, column=0, sticky="nsew")
        controls.rowconfigure(4, weight=1)
        self._build_controls()

        viewport = ttk.Frame(shell, style="Panel.TFrame", padding=(12, 0, 0, 0))
        viewport.grid(row=0, column=1, sticky="nsew")
        viewport.columnconfigure(0, weight=1)
        viewport.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(viewport, background="#f4f7fa", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        hud = ttk.Label(viewport, textvariable=self.stats_var, style="Hud.TLabel", anchor="w")
        hud.place(relx=0.015, rely=0.02, anchor="nw")
        status = ttk.Label(viewport, textvariable=self.status_var, style="Hud.TLabel", anchor="w")
        status.place(relx=0.015, rely=0.08, anchor="nw")

        self.canvas.bind("<Configure>", lambda _e: self.draw())
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_drag_end)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

    def _build_controls(self):
        for child in self.scroll.inner.winfo_children():
            child.destroy()
        self.control_vars.clear()

        row = 0
        for group_title, keys in GROUPS:
            frame = ttk.LabelFrame(self.scroll.inner, text=group_title, style="Card.TLabelframe", padding=10)
            frame.grid(row=row, column=0, sticky="ew", padx=4, pady=6)
            frame.columnconfigure(0, weight=1)
            row += 1

            for key in keys:
                limits = PARAM_LIMITS[key]
                param_row = ttk.Frame(frame, style="Panel.TFrame")
                param_row.pack(fill="x", expand=True, pady=4)
                ttk.Label(param_row, text=key, style="Subtle.TLabel").pack(anchor="w")

                inner = ttk.Frame(param_row, style="Panel.TFrame")
                inner.pack(fill="x", expand=True, pady=(2, 0))

                is_int = isinstance(DEFAULT_PARAMS[key], int) and not isinstance(DEFAULT_PARAMS[key], bool)
                var: tk.Variable
                if is_int:
                    var = tk.IntVar(value=int(self.params[key]))
                else:
                    var = tk.DoubleVar(value=float(self.params[key]))
                self.control_vars[key] = var

                scale = tk.Scale(
                    inner,
                    from_=limits["min"],
                    to=limits["max"],
                    resolution=limits["step"],
                    orient="horizontal",
                    showvalue=False,
                    variable=var,
                    command=lambda _value, name=key: self.on_slider_change(name),
                    background="#eef2f5",
                    highlightthickness=0,
                    troughcolor="#ced8df",
                    activebackground="#56768c",
                )
                scale.pack(side="left", fill="x", expand=True)

                spin = tk.Spinbox(
                    inner,
                    from_=limits["min"],
                    to=limits["max"],
                    increment=limits["step"],
                    textvariable=var,
                    width=8,
                    command=lambda name=key: self.on_spin_change(name),
                    justify="right",
                )
                spin.pack(side="left", padx=(8, 0))
                spin.bind("<Return>", lambda _e, name=key: self.on_spin_change(name))
                spin.bind("<FocusOut>", lambda _e, name=key: self.on_spin_change(name))

    def load_preset(self, name: str):
        preset = dict(PRESETS.get(name, PRESETS["default"]))
        self.preset_var.set(name)
        self.mode_var.set(preset.get("mode", "solid"))
        self.close_top_var.set(bool(preset.get("close_top", False)))
        self.dome_mode_var.set(preset.get("dome_mode", "solid"))
        for key in DEFAULT_PARAMS:
            self.params[key] = preset.get(key, DEFAULT_PARAMS[key])
            var = self.control_vars.get(key)
            if var is not None:
                var.set(self.params[key])
        self.schedule_preview()

    def on_slider_change(self, key: str):
        self.params[key] = self._coerce_ui_value(key, self.control_vars[key].get())
        self.schedule_preview()

    def on_spin_change(self, key: str):
        self.params[key] = self._coerce_ui_value(key, self.control_vars[key].get())
        self.control_vars[key].set(self.params[key])
        self.schedule_preview()

    def _coerce_ui_value(self, key: str, raw: Any) -> Any:
        limits = PARAM_LIMITS[key]
        default = DEFAULT_PARAMS[key]
        value = float(raw)
        value = clamp(value, limits["min"], limits["max"])
        if isinstance(default, int) and not isinstance(default, bool):
            return int(round(value))
        return value

    def collect_payload(self) -> dict[str, Any]:
        return {
            **self.params,
            "mode": self.mode_var.get(),
            "close_top": self.close_top_var.get(),
            "dome_mode": self.dome_mode_var.get(),
        }

    def schedule_preview(self):
        if self.preview_job is not None:
            self.root.after_cancel(self.preview_job)
        self.status_var.set("Generando preview...")
        self.preview_job = self.root.after(120, self.generate_preview)

    def generate_preview(self):
        self.preview_job = None
        try:
            _meta, triangles = build_triangles(self.collect_payload(), interactive=True)
            self.last_triangles = triangles
            self.mesh = triangles_to_indexed_mesh(triangles)
            self.stats_var.set(
                f"{self.mesh['vertex_count']} vertices | {self.mesh['triangle_count']} triangles | preview interactivo"
            )
            self.status_var.set("Preview listo")
            self.draw()
        except Exception as exc:
            self.status_var.set(f"Error: {exc}")

    def build_camera(self, radius: float) -> dict[str, tuple[float, float, float] | float]:
        distance = max(radius * self.camera["distance_factor"], 120.0)
        horizontal = math.cos(self.camera["pitch"]) * distance
        eye = (
            math.cos(self.camera["yaw"]) * horizontal,
            math.sin(self.camera["yaw"]) * horizontal,
            math.sin(self.camera["pitch"]) * distance,
        )
        forward = normalize((-eye[0], -eye[1], -eye[2]))
        right = cross(forward, WORLD_UP)
        if math.sqrt(dot(right, right)) < 1e-5:
            right = (1.0, 0.0, 0.0)
        else:
            right = normalize(right)
        up = normalize(cross(right, forward))
        return {"eye": eye, "forward": forward, "right": right, "up": up}

    def project_point(
        self,
        local: tuple[float, float, float],
        camera: dict[str, Any],
        focal: float,
        width: float,
        height: float,
    ) -> tuple[float, float, float]:
        relative = subtract(local, camera["eye"])
        vx = dot(relative, camera["right"])
        vy = dot(relative, camera["up"])
        vz = dot(relative, camera["forward"])
        depth = max(1.0, vz)
        scale = focal / depth
        return (vx * scale + width * 0.5, -vy * scale + height * 0.56, vz)

    def draw(self):
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        self._draw_backdrop(width, height)
        if not self.mesh:
            return

        vertices = self.mesh["vertices"]
        triangles = self.mesh["triangles"]
        center = self.mesh["center"]
        radius = self.mesh["radius"]
        bounds = self.mesh["bounds"]
        camera = self.build_camera(radius)
        focal = min(width, height) * 0.9
        local_vertices = [(v[0] - center[0], v[1] - center[1], v[2] - center[2]) for v in vertices]
        projected = [self.project_point(v, camera, focal, width, height) for v in local_vertices]

        self._draw_build_plate(bounds, center, radius, camera, focal, width, height)
        self._draw_shadow(local_vertices, bounds, center, radius, camera, focal, width, height)

        faces = []
        for tri in triangles:
            a = local_vertices[tri[0]]
            b = local_vertices[tri[1]]
            c = local_vertices[tri[2]]
            edge1 = subtract(b, a)
            edge2 = subtract(c, a)
            normal = normalize(cross(edge1, edge2))
            facing = dot(normal, camera["forward"])
            light = max(0.0, dot(normal, LIGHT_DIR))
            depth = (projected[tri[0]][2] + projected[tri[1]][2] + projected[tri[2]][2]) / 3.0
            faces.append((depth, facing, light, tri))
        faces.sort(key=lambda item: item[0])

        dark = (110, 133, 164)
        light = (197, 220, 245)
        fog = (238, 242, 246)
        outline = "#f4f8fb"
        for depth, facing, intensity, tri in faces:
            if facing <= 0.0:
                continue
            pa = projected[tri[0]]
            pb = projected[tri[1]]
            pc = projected[tri[2]]
            depth_fog = max(0.0, min(1.0, (depth - radius * 0.2) / (radius * 3.4 or 1.0)))
            lit_color = tuple(int(mix(dark[i], light[i], 0.25 + intensity * 0.75)) for i in range(3))
            color = mix_color(lit_color, fog, depth_fog * 0.25)
            points = [pa[0], pa[1], pb[0], pb[1], pc[0], pc[1]]
            self.canvas.create_polygon(points, fill=color, outline=outline, width=1)

        self._draw_axis_triad(camera, width, height)

    def _draw_backdrop(self, width: int, height: int):
        steps = 18
        top = (245, 247, 250)
        bottom = (232, 237, 242)
        for i in range(steps):
            y0 = int(height * i / steps)
            y1 = int(height * (i + 1) / steps)
            color = mix_color(top, bottom, i / max(1, steps - 1))
            self.canvas.create_rectangle(0, y0, width, y1, fill=color, outline=color)

    def _draw_build_plate(self, bounds: dict[str, Any], center: tuple[float, float, float], radius: float, camera: dict[str, Any], focal: float, width: int, height: int):
        min_x = bounds["min"][0] - center[0]
        max_x = bounds["max"][0] - center[0]
        min_y = bounds["min"][1] - center[1]
        max_y = bounds["max"][1] - center[1]
        min_z = bounds["min"][2] - center[2]
        plate_z = min_z - max(2.0, radius * 0.03)
        extent = max(abs(min_x), abs(max_x), abs(min_y), abs(max_y), radius) * 1.35

        corners = [
            self.project_point((-extent, -extent, plate_z), camera, focal, width, height),
            self.project_point((extent, -extent, plate_z), camera, focal, width, height),
            self.project_point((extent, extent, plate_z), camera, focal, width, height),
            self.project_point((-extent, extent, plate_z), camera, focal, width, height),
        ]
        plate_points = [coord for point in corners for coord in point[:2]]
        self.canvas.create_polygon(plate_points, fill="#e4e9ee", outline="#bac5cf", width=1)

        grid_step = 20 if radius > 90 else 10
        grid_color = "#c5ced6"
        x = -extent
        while x <= extent:
            a = self.project_point((x, -extent, plate_z), camera, focal, width, height)
            b = self.project_point((x, extent, plate_z), camera, focal, width, height)
            self.canvas.create_line(a[0], a[1], b[0], b[1], fill=grid_color, width=1)
            x += grid_step

        y = -extent
        while y <= extent:
            a = self.project_point((-extent, y, plate_z), camera, focal, width, height)
            b = self.project_point((extent, y, plate_z), camera, focal, width, height)
            self.canvas.create_line(a[0], a[1], b[0], b[1], fill=grid_color, width=1)
            y += grid_step

    def _draw_shadow(self, local_vertices: list[tuple[float, float, float]], bounds: dict[str, Any], center: tuple[float, float, float], radius: float, camera: dict[str, Any], focal: float, width: int, height: int):
        min_z = bounds["min"][2] - center[2]
        plate_z = min_z - max(2.0, radius * 0.03)
        points = []
        for vertex in local_vertices:
            dz = max(1.0, vertex[2] - plate_z)
            projected = (
                vertex[0] - LIGHT_DIR[0] * dz / LIGHT_DIR[2],
                vertex[1] - LIGHT_DIR[1] * dz / LIGHT_DIR[2],
                plate_z,
            )
            points.append(self.project_point(projected, camera, focal, width, height))
        if not points:
            return

        min_x = min(point[0] for point in points)
        max_x = max(point[0] for point in points)
        min_y = min(point[1] for point in points)
        max_y = max(point[1] for point in points)
        cx = (min_x + max_x) * 0.5
        cy = (min_y + max_y) * 0.5
        rx = max(50.0, (max_x - min_x) * 0.52)
        ry = max(24.0, (max_y - min_y) * 0.4)

        for ring in range(6, 0, -1):
            alpha = ring / 6.0
            color = mix_color((238, 242, 246), (70, 84, 97), 0.15 * alpha)
            self.canvas.create_oval(
                cx - rx * alpha,
                cy - ry * alpha,
                cx + rx * alpha,
                cy + ry * alpha,
                outline="",
                fill=color,
            )

    def _draw_axis_triad(self, camera: dict[str, Any], width: int, height: int):
        origin = (74, height - 72)
        scale = 28

        def project_vec(vector: tuple[float, float, float]) -> tuple[float, float]:
            return (
                origin[0] + dot(vector, camera["right"]) * scale,
                origin[1] - dot(vector, camera["up"]) * scale,
            )

        axes = [
            ("X", "#d4583d", (1.0, 0.0, 0.0)),
            ("Y", "#4e9a61", (0.0, 1.0, 0.0)),
            ("Z", "#4f7ed8", (0.0, 0.0, 1.0)),
        ]
        self.canvas.create_oval(origin[0] - 4, origin[1] - 4, origin[0] + 4, origin[1] + 4, fill="#f8fafc", outline="")
        for label, color, vector in axes:
            end = project_vec(vector)
            self.canvas.create_line(origin[0], origin[1], end[0], end[1], fill=color, width=2)
            self.canvas.create_text(end[0] + 8, end[1] + 4, text=label, fill=color, font=("Georgia", 12, "bold"))

    def on_drag_start(self, event: tk.Event):
        self.drag_origin = (event.x, event.y)

    def on_drag_move(self, event: tk.Event):
        if self.drag_origin is None:
            return
        dx = event.x - self.drag_origin[0]
        dy = event.y - self.drag_origin[1]
        self.camera["yaw"] += dx * 0.01
        self.camera["pitch"] += dy * 0.006
        self.camera["pitch"] = clamp(self.camera["pitch"], -0.15, 1.2)
        self.drag_origin = (event.x, event.y)
        self.draw()

    def on_drag_end(self, _event: tk.Event):
        self.drag_origin = None

    def on_mouse_wheel(self, event: tk.Event):
        delta = -1.0 if event.delta > 0 else 1.0
        self.camera["distance_factor"] = clamp(self.camera["distance_factor"] + delta * 0.12, 1.2, 6.0)
        self.draw()

    def export_stl(self):
        if not self.last_triangles:
            self.generate_preview()
            if not self.last_triangles:
                return
        path = filedialog.asksaveasfilename(
            title="Guardar STL",
            defaultextension=".stl",
            filetypes=[("STL files", "*.stl")],
            initialfile=f"pb6_{self.mode_var.get()}_{self.preset_var.get()}.stl",
        )
        if not path:
            return
        try:
            _meta, triangles = build_triangles(self.collect_payload(), interactive=False)
            pb6.write_binary_stl(path, triangles)
            self.status_var.set(f"Exportado: {Path(path).name}")
        except Exception as exc:
            self.status_var.set(f"Export fallo: {exc}")


def main():
    root = tk.Tk()
    app = LivePB6App(root)
    app.generate_preview()
    root.mainloop()


if __name__ == "__main__":
    main()
