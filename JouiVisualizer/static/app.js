const state = {
  config: null,
  engineId: null,
  engineConfig: null,
  params: {},
  previewMesh: null,
  previewSource: "generated",
  requestToken: 0,
  currentPreset: "default",
  camera: {
    yaw: 0.6,
    pitch: -0.4,
    distanceFactor: 2.8,
    projection: "orthographic",
  },
  openGroup: "Shape",
};

const baseGroups = [
  ["Shape", ["height", "r_base", "thickness", "bulb_amp", "bulb_count", "bulb_phase", "taper"]],
  ["Seam Engine", ["seam_count", "seam_pitch", "seam_width", "seam_height", "seam_softness", "valley_depth", "counter_strength", "counter_phase"]],
  ["Skin", ["membrane", "perforation", "inner_follow"]],
  ["Perforated", ["rib_width_scale", "rib_thickness", "rib_seg_per_pitch", "dome_height_scale"]],
  ["Cube", ["cube_mix", "cube_roundness", "outer_smoothing", "inner_smoothing"]],
  ["Top Closure", ["top_style"]],
  ["Sphere", ["flow_sway", "flow_wave_count", "opening_radius", "opening_softness", "lamp_clearance"]],
  ["Weave", ["weave_amp", "weave_theta", "weave_pitch", "weave_mix", "weave_round", "seam_twist", "strand_width", "weave_gap", "gap_round"]],
  ["Wire Mesh", ["radius", "wires", "rotations", "offset_b", "wire_width", "wire_thickness", "inner_radius", "seg_per_rot"]],
  ["Mount", ["n_lugs", "twist_deg", "entry_deg", "lug_deg", "mount_height", "wall", "socket_id", "clearance", "lug_thickness_z", "lug_radial", "detent_radial", "detent_deg"]],
  ["Resolution", ["target_triangles", "n_theta", "n_z"]],
];

const canvas = document.getElementById("viewportCanvas");
const ctx = canvas.getContext("2d");
const statusLine = document.getElementById("statusLine");
const meshStats = document.getElementById("meshStats");
const WORLD_UP = [0, 0, 1];
const lightDir = normalizeVector([-0.45, -0.7, 0.55]);
const PARAM_TOOLTIPS = {
  height: "Altura total de la pieza en milimetros.",
  r_base: "Radio base del volumen principal.",
  thickness: "Espesor general de la pared o cascaron.",
  bulb_amp: "Cuanto se infla y se contrae el perfil a lo largo de Z.",
  bulb_count: "Cantidad de lobulos u ondas verticales en el perfil.",
  bulb_phase: "Desfase del patron de lobulos sobre la altura.",
  taper: "Cuanto se estrecha o abre la forma hacia arriba.",
  seam_count: "Cantidad de costillas o familias de seam alrededor del perimetro.",
  seam_pitch: "Paso helicoidal del seam a medida que sube en Z.",
  seam_width: "Ancho de cada seam o relieve.",
  seam_height: "Cuanto sobresale el seam respecto del cascaron.",
  seam_softness: "Dureza o suavidad del perfil del seam.",
  valley_depth: "Profundidad de los valles entre seams.",
  counter_strength: "Influencia de la segunda familia de seams cruzados.",
  counter_phase: "Desfase angular de la familia cruzada.",
  membrane: "Cantidad de piel continua que queda detras del patron.",
  perforation: "Cuanto se abre la perforacion entre costillas.",
  inner_follow: "Cuanto acompana la cara interna al relieve exterior.",
  rib_width_scale: "Escala del ancho de las costillas en modo perforado.",
  rib_thickness: "Espesor fisico de cada costilla.",
  rib_seg_per_pitch: "Resolucion de triangulos por paso helicoidal de costilla.",
  dome_height_scale: "Altura relativa del cierre superior tipo domo.",
  cube_mix: "Empuja la seccion desde circular hacia una silueta cubica con caras mas planas.",
  cube_roundness: "Controla cuanto se redondean o endurecen las esquinas del volumen cubico.",
  outer_smoothing: "Alisa la piel exterior para bajar ruido, picos y micro relieve visible.",
  inner_smoothing: "Alisa la cara interior para dejar la boca y el interior mas limpios.",
  top_style: "Elige el cierre superior en motores compatibles: 0 plano, 1 domo, 2 piramide, 3 inset.",
  flow_sway: "Cuanto ondulan lateralmente las nervaduras mientras suben sobre la esfera.",
  flow_wave_count: "Cantidad de oscilaciones verticales del patron fluido sobre la superficie.",
  opening_radius: "Tamano de la boca inferior para alojar foco o soporte.",
  opening_softness: "Que tan suave se mezcla la zona de la boca con el resto de la esfera.",
  lamp_clearance: "Espacio interior reservado para la lampara en la cavidad central.",
  n_theta: "Resolucion angular de la malla.",
  n_z: "Resolucion vertical de la malla.",
  r_min: "Radio minimo de seguridad para evitar colapsos.",
  radius: "Radio base del cilindro o cuerpo de alambre.",
  weave_amp: "Intensidad del relieve tejido o de la costura.",
  weave_theta: "Frecuencia angular del patron alrededor del perimetro.",
  weave_pitch: "Paso vertical del patron helicoidal o tejido.",
  weave_mix: "Balance entre las dos familias cruzadas del patron.",
  weave_round: "Suavizado y redondeo del cruce de hebras.",
  seam_twist: "Giro suave acumulado del patron con la altura.",
  strand_width: "Ancho aparente de cada hebra.",
  weave_gap: "Profundidad visual del hueco entre hebras.",
  gap_round: "Redondeo de los huecos del tejido.",
  wires: "Cantidad de alambres por familia alrededor del cilindro.",
  rotations: "Cantidad de vueltas helicoidales a lo largo de la altura.",
  offset_b: "Desfase angular entre la familia A y la familia B.",
  wire_width: "Ancho visual de cada cinta o alambre.",
  wire_thickness: "Espesor radial de cada alambre.",
  inner_radius: "Radio interior adicional para refuerzo.",
  seg_per_rot: "Resolucion por vuelta helicoidal del alambre.",
  n_lugs: "Cantidad de trabas del encastre bayoneta.",
  twist_deg: "Grados de giro necesarios para trabar la bayoneta.",
  entry_deg: "Apertura angular de cada ventana de entrada.",
  lug_deg: "Ancho angular de cada lug de la bayoneta.",
  mount_height: "Altura vertical del collar de encastre.",
  wall: "Espesor de pared del collar bayoneta.",
  socket_id: "Diametro interior de la hembra bayoneta.",
  clearance: "Holgura radial para compensar impresion FDM.",
  lug_thickness_z: "Espesor en Z del lug o repisa de trabado.",
  lug_radial: "Saliente radial de cada lug.",
  detent_radial: "Tamano radial del bulto de detent.",
  detent_deg: "Ancho angular del detent.",
  target_triangles: "Cantidad objetivo de triangulos para la preview interactiva de este motor.",
};

function debounce(fn, wait) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const message = await response.text().catch(() => "");
    throw new Error(`${response.status} ${response.statusText}${message ? ` - ${message}` : ""}`);
  }
  return response.json();
}

function clonePreset(name) {
  return JSON.parse(JSON.stringify(state.engineConfig.presets[name]));
}

function ensurePresetOption(name, label = name) {
  const presetSelect = document.getElementById("presetSelect");
  let option = Array.from(presetSelect.options).find((item) => item.value === name);
  if (!option) {
    option = document.createElement("option");
    option.value = name;
    presetSelect.appendChild(option);
  }
  option.textContent = label;
}

function getEngineConfig(engineId = state.engineId) {
  return state.config.engine_configs[engineId];
}

function getControlGroups() {
  const defaults = state.engineConfig?.defaults ?? {};
  const limits = state.engineConfig?.limits ?? {};
  const seen = new Set();
  const groups = baseGroups.map(([title, keys]) => {
    const existing = keys.filter((key) => key in defaults && key in limits);
    existing.forEach((key) => seen.add(key));
    return [title, existing];
  });

  const extras = Object.keys(defaults).filter((key) => !seen.has(key) && key in limits);
  if (extras.length) {
    groups.push(["More", extras]);
  }

  const filtered = groups.filter(([, keys]) => keys.length);
  if (filtered.length) {
    return filtered;
  }

  const allKeys = Object.keys(defaults).filter((key) => key in limits);
  return allKeys.length ? [["Properties", allKeys]] : [];
}

function slugify(title) {
  return title.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

function humanizeKey(key) {
  return key
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function sanitizeNumericParam(key, value) {
  const fallback = state.engineConfig.defaults[key];
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return fallback;
  }
  return Number.isInteger(fallback) ? Math.round(numeric) : numeric;
}

function clampToLimits(key, value) {
  const limits = state.engineConfig.limits[key];
  const fallback = state.engineConfig.defaults[key];
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return fallback;
  }
  const clamped = Math.max(limits.min, Math.min(limits.max, numeric));
  return Number.isInteger(fallback) ? Math.round(clamped) : clamped;
}

function applySliderLimits(slider, key) {
  const limits = state.engineConfig.limits[key];
  slider.min = limits.min;
  slider.max = limits.max;
  slider.step = limits.step;
}

function getParamDescription(key) {
  return state.engineConfig.descriptions?.[key] ?? PARAM_TOOLTIPS[key] ?? key;
}

function applyPayloadToState(payload) {
  const nextParams = {};
  for (const key of Object.keys(state.engineConfig.defaults)) {
    nextParams[key] = sanitizeNumericParam(key, payload[key] ?? state.engineConfig.defaults[key]);
  }

  state.params = nextParams;
  const supportsModes = Boolean(state.engineConfig.supports_modes);
  const supportsCloseTop = Boolean(state.engineConfig.supports_close_top);
  const supportsDomeMode = Boolean(state.engineConfig.supports_dome_mode);
  document.getElementById("modeSelect").value = supportsModes && payload.mode === "perforated" ? "perforated" : "solid";
  document.getElementById("closeTopInput").checked = supportsCloseTop ? Boolean(payload.close_top) : false;
  document.getElementById("domeModeSelect").value =
    supportsDomeMode && payload.dome_mode === "perforated" ? "perforated" : "solid";
  syncModeControls();
}

function buildControls() {
  const root = document.getElementById("controlGroups");
  root.innerHTML = "";
  const controlGroups = getControlGroups();

  for (const [title, keys] of controlGroups) {
    const box = document.createElement("section");
    box.className = "controlGroup";
    const groupId = slugify(title);
    const expanded = state.openGroup === title || (!state.openGroup && title === controlGroups[0][0]);
    box.dataset.group = groupId;
    if (expanded) {
      box.dataset.expanded = "true";
    }

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "groupToggle";
    toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
    toggle.innerHTML = `
      <span class="groupMeta">
        <span class="groupName">${title}</span>
        <span class="groupCount">${keys.length} controls</span>
      </span>
      <span class="groupChevron">${expanded ? "-" : "+"}</span>
    `;
    toggle.addEventListener("click", () => {
      state.openGroup = state.openGroup === title ? "" : title;
      buildControls();
    });
    box.appendChild(toggle);

    const body = document.createElement("div");
    body.className = "groupBody";
    body.hidden = !expanded;

    for (const key of keys) {
      const limits = state.engineConfig.limits[key];
      const row = document.createElement("div");
      row.className = "control";
      row.title = getParamDescription(key);

      const labelRow = document.createElement("div");
      labelRow.className = "controlLabel";
      const label = document.createElement("label");
      label.textContent = humanizeKey(key);
      label.title = getParamDescription(key);
      const info = document.createElement("span");
      info.className = "infoDot";
      info.title = getParamDescription(key);
      info.textContent = "?";
      const valuePill = document.createElement("span");
      valuePill.className = "valuePill";
      valuePill.textContent = state.params[key];
      labelRow.appendChild(label);
      labelRow.appendChild(info);
      labelRow.appendChild(valuePill);
      row.appendChild(labelRow);

      const controlRow = document.createElement("div");
      controlRow.className = "controlRow";

      const slider = document.createElement("input");
      slider.type = "range";
      applySliderLimits(slider, key);
      slider.value = clampToLimits(key, state.params[key]);
      slider.title = getParamDescription(key);

      const number = document.createElement("input");
      number.type = "number";
      number.step = limits.step;
      number.value = state.params[key];
      number.title = getParamDescription(key);

      const syncFromSlider = (value) => {
        const numeric = clampToLimits(key, value);
        slider.value = numeric;
        number.value = numeric;
        valuePill.textContent = numeric;
        state.params[key] = numeric;
        debouncedPreview();
      };

      const syncFromNumber = (value) => {
        const numeric = sanitizeNumericParam(key, value);
        slider.value = clampToLimits(key, numeric);
        number.value = numeric;
        valuePill.textContent = numeric;
        state.params[key] = numeric;
        debouncedPreview();
      };

      slider.addEventListener("input", () => syncFromSlider(slider.value));
      number.addEventListener("change", () => syncFromNumber(number.value));

      controlRow.appendChild(slider);
      controlRow.appendChild(number);
      row.appendChild(controlRow);
      body.appendChild(row);
    }

    box.appendChild(body);
    root.appendChild(box);
  }

  if (!root.childElementCount) {
    const message = document.createElement("p");
    message.className = "status";
    message.textContent = "No slider properties available.";
    root.appendChild(message);
  }
}

function loadPreset(name) {
  state.currentPreset = name;
  applyPayloadToState(clonePreset(name));
  buildControls();
  debouncedPreview();
}

function syncModeControls() {
  const supportsModes = Boolean(state.engineConfig?.supports_modes);
  const supportsCloseTop = Boolean(state.engineConfig?.supports_close_top);
  const supportsDomeMode = Boolean(state.engineConfig?.supports_dome_mode);

  document.getElementById("modeRow").hidden = !supportsModes;
  document.getElementById("closeTopRow").hidden = !supportsCloseTop;
  document.getElementById("domeModeRow").hidden = !supportsDomeMode;
  document.getElementById("modeSelect").disabled = !supportsModes;
  document.getElementById("closeTopInput").disabled = !supportsCloseTop;
  document.getElementById("domeModeSelect").disabled = !supportsDomeMode;
}

function loadEngine(engineId, preferredPreset = "default") {
  state.engineId = engineId;
  state.engineConfig = getEngineConfig(engineId);
  state.openGroup = "Shape";
  document.getElementById("targetTrianglesRow").hidden = "target_triangles" in state.engineConfig.defaults;

  const presetSelect = document.getElementById("presetSelect");
  presetSelect.innerHTML = "";
  for (const presetName of Object.keys(state.engineConfig.presets)) {
    ensurePresetOption(presetName);
  }

  const presetToLoad = state.engineConfig.presets[preferredPreset]
    ? preferredPreset
    : Object.keys(state.engineConfig.presets)[0];
  presetSelect.value = presetToLoad;
  loadPreset(presetToLoad);
}

function generateBaseModel() {
  const presetNames = Object.keys(state.engineConfig.presets);
  if (!presetNames.length) {
    return;
  }

  const pool = presetNames.filter((name) => name !== state.currentPreset);
  const choices = pool.length ? pool : presetNames;
  const selected = choices[Math.floor(Math.random() * choices.length)];
  document.getElementById("presetSelect").value = selected;
  loadPreset(selected);
  statusLine.textContent = `Base model: ${selected}`;
}

function collectPayload() {
  const payload = {
    engine: state.engineId,
    ...state.params,
  };
  if (state.engineConfig.supports_modes) {
    payload.mode = document.getElementById("modeSelect").value;
  }
  if (state.engineConfig.supports_close_top) {
    payload.close_top = document.getElementById("closeTopInput").checked;
  }
  if (state.engineConfig.supports_dome_mode) {
    payload.dome_mode = document.getElementById("domeModeSelect").value;
  }
  const targetTriangles = Number(document.getElementById("targetTrianglesInput")?.value || 0);
  if (targetTriangles > 0) {
    payload.target_triangles = Math.round(targetTriangles);
  }
  return payload;
}

async function requestPreview() {
  const token = ++state.requestToken;
  statusLine.textContent = "Generating preview...";

  try {
    const data = await fetchJson("/api/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectPayload()),
    });

    if (token !== state.requestToken) {
      return;
    }

    state.previewMesh = data.mesh;
    state.previewSource = "generated";
    const targetNote = data.meta?.target_triangles ? ` / target ${data.meta.target_triangles}` : "";
    meshStats.textContent = `${state.engineId} | ${data.mesh.vertex_count} vertices | ${data.mesh.triangle_count} triangles${targetNote} | preview`;
    statusLine.textContent = "Preview ready";
    draw();
  } catch (error) {
    statusLine.textContent = `Preview failed: ${error.message}`;
  }
}

const debouncedPreview = debounce(requestPreview, 160);

function normalizeVector(vector) {
  const length = Math.hypot(vector[0], vector[1], vector[2]) || 1;
  return [vector[0] / length, vector[1] / length, vector[2] / length];
}

function cross(a, b) {
  return [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];
}

function dot(a, b) {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

function subtract(a, b) {
  return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function mixColor(colorA, colorB, t) {
  return [
    Math.round(lerp(colorA[0], colorB[0], t)),
    Math.round(lerp(colorA[1], colorB[1], t)),
    Math.round(lerp(colorA[2], colorB[2], t)),
  ];
}

function rgba(color, alpha) {
  return `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${alpha})`;
}

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function buildCamera(radius, target) {
  const distance = Math.max(radius * state.camera.distanceFactor, 120);
  const horizontal = Math.cos(state.camera.pitch) * distance;
  const eye = [
    target[0] + Math.cos(state.camera.yaw) * horizontal,
    target[1] + Math.sin(state.camera.yaw) * horizontal,
    target[2] + Math.sin(state.camera.pitch) * distance,
  ];

  const forward = normalizeVector([
    target[0] - eye[0],
    target[1] - eye[1],
    target[2] - eye[2],
  ]);
  let right = cross(forward, WORLD_UP);
  if (Math.hypot(right[0], right[1], right[2]) < 1e-5) {
    right = [1, 0, 0];
  } else {
    right = normalizeVector(right);
  }
  const up = normalizeVector(cross(right, forward));
  return { eye, forward, right, up, distance };
}

function projectPoint(local, camera, focal, width, height) {
  const relative = subtract(local, camera.eye);
  const vx = dot(relative, camera.right);
  const vy = dot(relative, camera.up);
  const vz = dot(relative, camera.forward);

  if (state.camera.projection === "orthographic") {
    const orthoScale = Math.min(width, height) / Math.max(120, camera.distance * 0.9);
    return {
      x: vx * orthoScale + width * 0.5,
      y: -vy * orthoScale + height * 0.52,
      z: vz,
    };
  }

  const depth = Math.max(1, vz);
  const scale = focal / depth;

  return {
    x: vx * scale + width * 0.5,
    y: -vy * scale + height * 0.52,
    z: vz,
  };
}

function getAnchoredVertices(mesh) {
  const { vertices, bounds } = mesh;
  const anchor = [
    (bounds.min[0] + bounds.max[0]) * 0.5,
    (bounds.min[1] + bounds.max[1]) * 0.5,
    bounds.min[2],
  ];
  const height = bounds.max[2] - bounds.min[2];
  const targetHeight = height * (state.previewSource === "import" ? 0.18 : 0.28);

  return {
    localVertices: vertices.map((vertex) => [
      vertex[0] - anchor[0],
      vertex[1] - anchor[1],
      vertex[2] - anchor[2],
    ]),
    target: [0, 0, targetHeight],
  };
}

function draw() {
  resizeCanvas();
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;

  ctx.clearRect(0, 0, width, height);
  drawBackdrop(width, height);

  if (!state.previewMesh) {
    return;
  }

  const { triangles, radius } = state.previewMesh;
  const { localVertices, target } = getAnchoredVertices(state.previewMesh);
  const camera = buildCamera(radius, target);
  const focal = Math.min(width, height) * 0.95;
  const projected = localVertices.map((local) => projectPoint(local, camera, focal, width, height));

  const faces = triangles.map((triangle) => {
    const a = projected[triangle[0]];
    const b = projected[triangle[1]];
    const c = projected[triangle[2]];
    const ar = localVertices[triangle[0]];
    const br = localVertices[triangle[1]];
    const cr = localVertices[triangle[2]];
    const ux = b.x - a.x;
    const uy = b.y - a.y;
    const vx = c.x - a.x;
    const vy = c.y - a.y;
    const winding = ux * vy - uy * vx;
    const depth = (a.z + b.z + c.z) / 3;
    const edge1 = [br[0] - ar[0], br[1] - ar[1], br[2] - ar[2]];
    const edge2 = [cr[0] - ar[0], cr[1] - ar[1], cr[2] - ar[2]];
    const normal = normalizeVector(cross(edge1, edge2));
    const light = Math.max(0, dot(normal, lightDir));
    const rim = Math.pow(1 - Math.abs(normal[2]), 1.8);
    const facing = dot(normal, camera.forward);
    return { triangle, depth, winding, light, rim, facing };
  });

  faces.sort((left, right) => left.depth - right.depth);
  drawGroundShadow(localVertices, radius, width, height, camera, focal);

  const baseColor = [220, 162, 102];
  const highlightColor = [255, 229, 198];
  const shadowColor = [118, 74, 42];

  for (const face of faces) {
    if (face.facing <= 0) {
      continue;
    }
    const [ia, ib, ic] = face.triangle;
    const a = projected[ia];
    const b = projected[ib];
    const c = projected[ic];
    const depthFog = Math.max(0, Math.min(1, (face.depth + radius * 1.2) / (radius * 2.8 || 1)));
    const litColor = mixColor(shadowColor, highlightColor, 0.22 + face.light * 0.78);
    const fillColor = mixColor(baseColor, litColor, 0.5 + face.rim * 0.22);
    const foggedColor = mixColor(fillColor, [233, 225, 214], depthFog * 0.28);

    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.lineTo(c.x, c.y);
    ctx.closePath();
    ctx.fillStyle = rgba(foggedColor, 0.96);
    ctx.fill();

    if (face.winding < 0) {
      const edgeAlpha = 0.08 + face.rim * 0.16 + face.light * 0.1;
      ctx.strokeStyle = rgba([255, 245, 232], edgeAlpha);
      ctx.stroke();
    }
  }
}

function drawBackdrop(width, height) {
  const gradient = ctx.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, "#f8f1e8");
  gradient.addColorStop(0.5, "#e7ddd0");
  gradient.addColorStop(1, "#cbc0b4");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "rgba(96, 76, 58, 0.10)";
  ctx.lineWidth = 1;
  for (let index = 1; index < 6; index += 1) {
    const y = height * (0.36 + index * 0.09);
    ctx.beginPath();
    ctx.moveTo(width * 0.08, y);
    ctx.lineTo(width * 0.92, y);
    ctx.stroke();
  }
}

function drawGroundShadow(localVertices, radius, width, height, camera, focal) {
  if (!localVertices.length) {
    return;
  }

  let floorZ = Infinity;
  for (const vertex of localVertices) {
    floorZ = Math.min(floorZ, vertex[2]);
  }
  floorZ -= Math.max(2, radius * 0.05);

  const points = localVertices.map((vertex) => {
    const dz = Math.max(0, vertex[2] - floorZ);
    const shadowPoint = [
      vertex[0] - lightDir[0] * dz / Math.max(0.2, lightDir[2]),
      vertex[1] - lightDir[1] * dz / Math.max(0.2, lightDir[2]),
      floorZ,
    ];
    return projectPoint(shadowPoint, camera, focal, width, height);
  });

  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const point of points) {
    minX = Math.min(minX, point.x);
    maxX = Math.max(maxX, point.x);
    minY = Math.min(minY, point.y);
    maxY = Math.max(maxY, point.y);
  }

  const centerX = (minX + maxX) * 0.5;
  const centerY = maxY;
  const shadowWidth = Math.max(90, maxX - minX);
  const shadowHeight = Math.max(30, (maxY - minY) * 0.22);
  const shadow = ctx.createRadialGradient(centerX, centerY, shadowHeight * 0.2, centerX, centerY, shadowWidth * 0.75);
  shadow.addColorStop(0, "rgba(55, 40, 29, 0.26)");
  shadow.addColorStop(1, "rgba(55, 40, 29, 0.0)");

  ctx.fillStyle = shadow;
  ctx.beginPath();
  ctx.ellipse(centerX, centerY, shadowWidth, shadowHeight, 0, 0, Math.PI * 2);
  ctx.fill();
}

function attachViewportInteraction() {
  let dragging = false;
  let lastX = 0;
  let lastY = 0;

  canvas.addEventListener("pointerdown", (event) => {
    dragging = true;
    lastX = event.clientX;
    lastY = event.clientY;
    canvas.setPointerCapture(event.pointerId);
  });

  canvas.addEventListener("pointermove", (event) => {
    if (!dragging) {
      return;
    }
    state.camera.yaw += (event.clientX - lastX) * 0.01;
    state.camera.pitch += (event.clientY - lastY) * 0.01;
    state.camera.pitch = Math.max(-1.3, Math.min(1.3, state.camera.pitch));
    lastX = event.clientX;
    lastY = event.clientY;
    draw();
  });

  canvas.addEventListener("pointerup", () => {
    dragging = false;
  });

  canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    state.camera.distanceFactor += event.deltaY * 0.001;
    state.camera.distanceFactor = Math.max(1.4, Math.min(6.0, state.camera.distanceFactor));
    draw();
  }, { passive: false });
}

async function refreshExports() {
  try {
    const data = await fetchJson("/api/exports");
    const root = document.getElementById("exportList");
    root.innerHTML = "";

    if (!data.files.length) {
      root.textContent = "No exports yet.";
      return;
    }

    for (const file of data.files) {
      const item = document.createElement("div");
      item.className = "exportItem";
      item.innerHTML = `
        <div>
          <div class="exportName">${file.name}</div>
          <div class="exportMeta">${Math.round(file.size / 1024)} KB</div>
        </div>
        <a href="/api/download?name=${encodeURIComponent(file.name)}">download</a>
      `;
      root.appendChild(item);
    }
  } catch (error) {
    document.getElementById("exportList").textContent = `Failed to load exports: ${error.message}`;
  }
}

async function exportCurrent() {
  statusLine.textContent = "Exporting STL...";
  try {
    const data = await fetchJson("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectPayload()),
    });
    statusLine.textContent = `Exported ${data.file}`;
    await refreshExports();
  } catch (error) {
    statusLine.textContent = `Export failed: ${error.message}`;
  }
}

async function importModelFile(file) {
  try {
    statusLine.textContent = `Importing ${file.name}...`;
    const data = await fetchJson("/api/import", {
      method: "POST",
      headers: {
        "Content-Type": "application/octet-stream",
        "X-Filename": file.name,
      },
      body: file,
    });
    state.previewMesh = data.mesh;
    state.previewSource = "import";
    const previewNote = data.preview_triangle_count < data.triangle_count
      ? ` | preview ${data.preview_triangle_count}/${data.triangle_count} triangles`
      : " | imported mesh";
    meshStats.textContent = `${data.mesh.vertex_count} vertices | ${data.mesh.triangle_count} triangles${previewNote}`;
    buildControls();
    statusLine.textContent = `Imported ${data.file}. The controls still drive ${state.engineConfig.label} when you move them.`;
    draw();
  } catch (error) {
    statusLine.textContent = `Import failed: ${error.message}`;
  }
}

async function init() {
  state.config = await fetchJson("/api/config");

  const engineSelect = document.getElementById("engineSelect");
  for (const engine of state.config.engines) {
    const option = document.createElement("option");
    option.value = engine.id;
    option.textContent = engine.label;
    engineSelect.appendChild(option);
  }

  const presetSelect = document.getElementById("presetSelect");
  engineSelect.addEventListener("change", () => loadEngine(engineSelect.value));
  presetSelect.addEventListener("change", () => loadPreset(presetSelect.value));
  document.getElementById("modeSelect").addEventListener("change", debouncedPreview);
  document.getElementById("closeTopInput").addEventListener("change", debouncedPreview);
  document.getElementById("domeModeSelect").addEventListener("change", debouncedPreview);
  document.getElementById("generateBaseBtn").addEventListener("click", generateBaseModel);
  document.getElementById("targetTrianglesInput").addEventListener("change", debouncedPreview);
  document.getElementById("resetBtn").addEventListener("click", () => loadPreset(state.currentPreset));
  document.getElementById("importBtn")?.addEventListener("click", () => document.getElementById("importFileInput")?.click());
  document.getElementById("exportBtn").addEventListener("click", exportCurrent);
  document.getElementById("refreshExportsBtn").addEventListener("click", refreshExports);
  document.getElementById("importFileInput")?.addEventListener("change", async (event) => {
    const [file] = event.target.files;
    if (file) {
      await importModelFile(file);
    }
    event.target.value = "";
  });

  attachViewportInteraction();
  engineSelect.value = state.config.default_engine;
  loadEngine(state.config.default_engine, "default");
  await refreshExports();
  window.addEventListener("resize", draw);
}

init().catch((error) => {
  statusLine.textContent = `Startup failed: ${error.message}`;
});
















