import random
import tkinter as tk
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tkinter import filedialog, ttk

from render_sim import render_mesh

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
EXPORTS = ROOT / "exports"
SERVER = REPO / "JouiVisualizer" / "server.py"
PREVIEW_TRI_LIMIT = 28000
GROUPS = [
    ("Shape", ["height", "r_base", "thickness", "bulb_amp", "bulb_count", "bulb_phase", "taper"]),
    ("Bag", ["width", "depth", "top_scale", "body_roundness", "side_tuck", "belly", "pleat_depth", "pleat_count", "rim_wave_amp", "rim_wave_count", "rim_band_height"]),
    ("Trim", ["handle_span", "handle_drop", "handle_pair_gap", "handle_thickness", "eyelet_radius", "eyelet_thickness", "eyelet_count", "eyelet_drop", "drawstring_thickness", "drawstring_drop"]),
    ("Seam", ["seam_count", "seam_pitch", "seam_width", "seam_height", "seam_softness", "valley_depth", "counter_strength", "counter_phase"]),
    ("Skin", ["membrane", "perforation", "inner_follow"]),
    ("Weave", ["weave_amp", "weave_theta", "weave_pitch", "weave_mix", "weave_round", "seam_twist", "strand_width", "weave_gap", "gap_round"]),
    ("Wire", ["radius", "wires", "rotations", "offset_b", "wire_width", "wire_thickness", "inner_radius", "seg_per_rot"]),
    ("Mount", ["n_lugs", "twist_deg", "entry_deg", "lug_deg", "mount_height", "wall", "socket_id", "clearance", "lug_thickness_z", "lug_radial", "detent_radial", "detent_deg"]),
    ("Res", ["target_triangles", "n_theta", "n_z"]),
]


def load_server():
    spec = spec_from_file_location("ejjoui_server", SERVER)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


srv = load_server()


def clamp(value, low, high):
    return max(low, min(high, value))


class Scroll(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#eadfd1")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.inner.bind("<Configure>", lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("ejjoui")
        self.root.geometry("1500x920")
        self.engine = srv.DEFAULT_ENGINE_ID
        self.cfg = srv.ENGINE_CONFIGS[self.engine]
        self.params = dict(self.cfg["defaults"])
        self.vars = {}
        self.mesh = None
        self.preview_source = "generated"
        self.job = None
        self.camera = {"yaw": 0.6, "pitch": -0.4, "distance_factor": 2.8, "projection": "orthographic"}
        self.drag = None
        self.status = tk.StringVar(value="Listo")
        self.stats = tk.StringVar(value="")
        self.mode = tk.StringVar(value="solid")
        self.close_top = tk.BooleanVar(value=False)
        self.dome = tk.StringVar(value="solid")
        self.target = tk.IntVar(value=24000)
        self.engine_var = tk.StringVar()
        self.preset_var = tk.StringVar(value="default")
        self.build_ui()
        self.load_engine(self.engine)

    def build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#d4c4b4")
        style.configure("Card.TLabelframe", background="#eadfd1")
        style.configure("Card.TLabelframe.Label", background="#eadfd1", foreground="#3d2417", font=("Georgia", 11, "bold"))
        shell = ttk.Frame(self.root, padding=12)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        left = ttk.Frame(shell, width=430)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_propagate(False)
        left.rowconfigure(3, weight=1)
        ttk.Label(left, text="ejjoui", font=("Georgia", 24, "bold"), background="#d4c4b4", foreground="#2d190f").grid(row=0, column=0, sticky="w")
        ttk.Label(left, text="Render desktop simulando el look del viewer web.", background="#d4c4b4", foreground="#6f5343").grid(row=1, column=0, sticky="w", pady=(0, 8))

        top = ttk.LabelFrame(left, text="Setup", style="Card.TLabelframe", padding=10)
        top.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        top.columnconfigure(1, weight=1)
        self.engine_box = ttk.Combobox(top, textvariable=self.engine_var, state="readonly", values=[f"{x['id']} | {x['label']}" for x in srv.ENGINE_LIST])
        self.engine_box.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.engine_box.bind("<<ComboboxSelected>>", self.on_engine)
        self.preset_box = ttk.Combobox(top, textvariable=self.preset_var, state="readonly")
        self.preset_box.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.preset_box.bind("<<ComboboxSelected>>", lambda _e: self.load_preset(self.preset_var.get()))
        ttk.Button(top, text="Generate Base", command=self.random_preset).grid(row=2, column=0, sticky="ew", pady=(8, 0), padx=(0, 4))
        ttk.Button(top, text="Reset", command=lambda: self.load_preset(self.preset_var.get())).grid(row=2, column=1, sticky="ew", pady=(8, 0), padx=(4, 0))
        self.mode_box = ttk.Combobox(top, textvariable=self.mode, values=["solid", "perforated"], state="readonly")
        self.mode_box.grid(row=3, column=0, sticky="ew", pady=(8, 0), padx=(0, 4))
        self.mode_box.bind("<<ComboboxSelected>>", lambda _e: self.schedule())
        self.dome_box = ttk.Combobox(top, textvariable=self.dome, values=["solid", "perforated"], state="readonly")
        self.dome_box.grid(row=3, column=1, sticky="ew", pady=(8, 0), padx=(4, 0))
        self.dome_box.bind("<<ComboboxSelected>>", lambda _e: self.schedule())
        ttk.Checkbutton(top, text="Close top", variable=self.close_top, command=self.schedule).grid(row=4, column=0, sticky="w", pady=(8, 0))
        tk.Spinbox(top, from_=1000, to=1000000, increment=1000, textvariable=self.target, justify="right").grid(row=4, column=1, sticky="ew", pady=(8, 0))
        ttk.Button(top, text="Export STL", command=self.export_stl).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Label(top, textvariable=self.status, background="#eadfd1", foreground="#6f5343", wraplength=360).grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.scroll = Scroll(left)
        self.scroll.grid(row=3, column=0, sticky="nsew")

        right = ttk.Frame(shell)
        right.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(right, bg="#f3ece4", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        ttk.Label(right, textvariable=self.stats, background="#2d241f", foreground="#fbf3eb", padding=8).place(relx=0.015, rely=0.02, anchor="nw")
        box = ttk.LabelFrame(right, text="Recent Exports", style="Card.TLabelframe", padding=10)
        box.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        box.columnconfigure(0, weight=1)
        self.exports = tk.Listbox(box, height=6, bg="#f7f1ea", fg="#40271a", borderwidth=0, highlightthickness=0)
        self.exports.grid(row=0, column=0, sticky="ew")
        ttk.Button(box, text="Refresh", command=self.refresh_exports).grid(row=0, column=1, sticky="ne", padx=(8, 0))

        self.canvas.bind("<Configure>", lambda _e: self.draw())
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.move_drag)
        self.canvas.bind("<ButtonRelease-1>", lambda _e: setattr(self, 'drag', None))
        self.canvas.bind("<MouseWheel>", self.zoom)

    def on_engine(self, _event):
        self.load_engine(self.engine_var.get().split('|', 1)[0].strip())

    def control_groups(self):
        seen, out = set(), []
        for title, keys in GROUPS:
            current = [key for key in keys if key in self.cfg["defaults"] and key in self.cfg["limits"]]
            seen.update(current)
            if current:
                out.append((title, current))
        extra = [key for key in self.cfg["defaults"] if key not in seen and key in self.cfg["limits"]]
        if extra:
            out.append(("More", extra))
        return out

    def build_controls(self):
        for child in self.scroll.inner.winfo_children():
            child.destroy()
        self.vars = {}
        row = 0
        for title, keys in self.control_groups():
            frame = ttk.LabelFrame(self.scroll.inner, text=title, style="Card.TLabelframe", padding=10)
            frame.grid(row=row, column=0, sticky="ew", padx=4, pady=6)
            row += 1
            for key in keys:
                limits = self.cfg["limits"][key]
                default = self.cfg["defaults"][key]
                description = self.cfg["descriptions"].get(key, key)
                ttk.Label(frame, text=f"{key} | {description}", background="#eadfd1", foreground="#6f5343", wraplength=360).pack(anchor="w")
                inner = ttk.Frame(frame)
                inner.pack(fill="x", pady=(1, 6))
                variable = tk.IntVar(value=int(self.params[key])) if isinstance(default, int) and not isinstance(default, bool) else tk.DoubleVar(value=float(self.params[key]))
                self.vars[key] = variable
                scale = tk.Scale(inner, from_=limits["min"], to=limits["max"], resolution=limits["step"], orient="horizontal", showvalue=False, variable=variable, command=lambda _v, name=key: self.sync(name), bg="#eadfd1", troughcolor="#c7ad95", activebackground="#9b6a4a", highlightthickness=0)
                scale.pack(side="left", fill="x", expand=True)
                spin = tk.Spinbox(inner, from_=limits["min"], to=limits["max"], increment=limits["step"], textvariable=variable, width=9, justify="right")
                spin.pack(side="left", padx=(8, 0))
                spin.bind("<Return>", lambda _e, name=key: self.sync(name))
                spin.bind("<FocusOut>", lambda _e, name=key: self.sync(name))

    def load_engine(self, engine_id):
        self.engine = engine_id
        self.cfg = srv.ENGINE_CONFIGS[engine_id]
        self.params = dict(self.cfg["defaults"])
        self.engine_var.set(f"{engine_id} | {self.cfg['label']}")
        self.preset_box.configure(values=list(self.cfg["presets"].keys()))
        self.preset_var.set("default")
        self.mode_box.configure(state="readonly" if self.cfg.get("supports_modes") else "disabled")
        self.dome_box.configure(state="readonly" if self.cfg.get("supports_dome_mode") else "disabled")
        self.build_controls()
        self.load_preset("default")

    def load_preset(self, name):
        preset = dict(self.cfg["presets"].get(name, self.cfg["presets"]["default"]))
        self.preset_var.set(name)
        for key in self.cfg["defaults"]:
            self.params[key] = preset.get(key, self.cfg["defaults"][key])
            if key in self.vars:
                self.vars[key].set(self.params[key])
        self.mode.set("perforated" if self.cfg.get("supports_modes") and preset.get("mode") == "perforated" else "solid")
        self.close_top.set(bool(preset.get("close_top", False)) if self.cfg.get("supports_close_top") else False)
        self.dome.set("perforated" if self.cfg.get("supports_dome_mode") and preset.get("dome_mode") == "perforated" else "solid")
        self.schedule()

    def random_preset(self):
        self.load_preset(random.choice(list(self.cfg["presets"].keys())))

    def sync(self, key):
        limits, default = self.cfg["limits"][key], self.cfg["defaults"][key]
        value = clamp(float(self.vars[key].get()), limits["min"], limits["max"])
        if isinstance(default, int) and not isinstance(default, bool):
            value = int(round(value))
        self.params[key] = value
        self.vars[key].set(value)
        self.schedule()

    def payload(self):
        data = {"engine": self.engine, **self.params, "target_triangles": int(self.target.get())}
        if self.cfg.get("supports_modes"):
            data["mode"] = self.mode.get()
        if self.cfg.get("supports_close_top"):
            data["close_top"] = self.close_top.get()
        if self.cfg.get("supports_dome_mode"):
            data["dome_mode"] = self.dome.get()
        return data

    def schedule(self):
        if self.job is not None:
            self.root.after_cancel(self.job)
        self.status.set("Generando preview...")
        self.job = self.root.after(150, self.preview)

    def preview(self):
        self.job = None
        try:
            meta, triangles = srv.build_triangles(self.engine, self.payload(), interactive=True)
            preview_triangles = triangles if len(triangles) <= PREVIEW_TRI_LIMIT else srv.decimate_triangles_for_preview(triangles, PREVIEW_TRI_LIMIT)
            self.mesh = srv.triangles_to_indexed_mesh(preview_triangles)
            self.preview_source = "generated"
            target_note = f" | target {meta['target_triangles']}" if meta.get("target_triangles") else ""
            reduced_note = f" | draw {len(preview_triangles)}/{len(triangles)}" if len(preview_triangles) != len(triangles) else ""
            self.stats.set(f"{self.engine} | {self.mesh['triangle_count']} tris | {self.mesh['vertex_count']} vertices{reduced_note}{target_note}")
            self.status.set("Preview listo")
            self.draw()
        except Exception as exc:
            self.status.set(f"Preview falló: {exc}")

    def draw(self):
        render_mesh(self.canvas, self.mesh, self.camera, self.preview_source)

    def start_drag(self, event):
        self.drag = (event.x, event.y)

    def move_drag(self, event):
        if not self.drag:
            return
        dx = event.x - self.drag[0]
        dy = event.y - self.drag[1]
        self.camera["yaw"] += dx * 0.01
        self.camera["pitch"] = clamp(self.camera["pitch"] + dy * 0.01, -1.3, 1.3)
        self.drag = (event.x, event.y)
        self.draw()

    def zoom(self, event):
        self.camera["distance_factor"] = clamp(self.camera["distance_factor"] + (-0.12 if event.delta > 0 else 0.12), 1.4, 6.0)
        self.draw()

    def export_stl(self):
        try:
            meta, triangles = srv.build_triangles(self.engine, self.payload(), interactive=False)
            EXPORTS.mkdir(exist_ok=True)
            path = filedialog.asksaveasfilename(title="Guardar STL", defaultextension=".stl", filetypes=[("STL", "*.stl")], initialdir=str(EXPORTS), initialfile=srv.export_file_name(self.engine, meta))
            if not path:
                return
            if self.engine == "bayonet":
                srv.ENGINES["bayonet"].write_binary_stl(path, triangles, header_text=b"ejjoui_bayonet_head")
            else:
                srv.ENGINES[self.engine].write_binary_stl(path, triangles)
            self.status.set(f"Exportado: {Path(path).name}")
            self.refresh_exports()
        except Exception as exc:
            self.status.set(f"Export falló: {exc}")

    def refresh_exports(self):
        EXPORTS.mkdir(exist_ok=True)
        self.exports.delete(0, tk.END)
        files = sorted(EXPORTS.glob("*.stl"), key=lambda item: item.stat().st_mtime, reverse=True)[:12]
        if not files:
            self.exports.insert(tk.END, "Todavia no hay exports en ejjoui/exports")
            return
        for item in files:
            self.exports.insert(tk.END, f"{item.name} | {round(item.stat().st_size / 1024)} KB")


def main():
    EXPORTS.mkdir(exist_ok=True)
    root = tk.Tk()
    app = App(root)
    app.refresh_exports()
    app.preview()
    root.mainloop()


if __name__ == "__main__":
    main()
