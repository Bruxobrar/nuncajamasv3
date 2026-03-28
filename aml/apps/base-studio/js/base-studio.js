'use strict';

const state = {
  selection: null,
  context: null,
  params: {},
  previewMesh: null,
  lampMesh: null,
  baseGenerator: null,
  showLampPreview: true,
  showFitGuide: true,
  requestToken: 0,
  camera: {
    yaw: 0.72,
    pitch: -0.42,
    distanceFactor: 2.9,
    projection: 'orthographic',
  },
};

const GROUPS = [
  ['Base', ['base_radius', 'base_height', 'stem_outer_diameter', 'stem_height']],
  ['Connector', ['interface_diameter', 'plug_height', 'plug_wall', 'fit_clearance', 'cable_hole_radius']],
  ['Bayonet', ['n_lugs', 'twist_deg', 'lug_deg', 'mount_height', 'lug_thickness_z', 'lug_radial']],
  ['Preview', ['n_theta']],
];

const canvas = document.getElementById('baseViewportCanvas');
const ctx = canvas.getContext('2d');
const statusLine = document.getElementById('baseStatusLine');
const meshStats = document.getElementById('baseMeshStats');
const WORLD_UP = [0, 0, 1];
const lightDir = normalizeVector([-0.45, -0.7, 0.55]);

function debounce(fn, wait) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

async function fetchJson(url, options = {}) {
  const token = localStorage.getItem('token');
  const headers = { ...options.headers };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

function selectionPayload() {
  return state.selection?.model || null;
}

function collectPayload() {
  return {
    model: {
      ...(selectionPayload() || {}),
      base_generator: state.baseGenerator,
    },
    params: state.params,
  };
}

function humanizeKey(key) {
  return key
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function sanitizeNumericParam(key, value) {
  const fallback = state.context.defaults[key];
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return fallback;
  }
  return Number.isInteger(fallback) ? Math.round(numeric) : numeric;
}

function clampToLimits(key, value) {
  const limits = state.context.limits[key];
  const fallback = state.context.defaults[key];
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return fallback;
  }
  const clamped = Math.max(limits.min, Math.min(limits.max, numeric));
  return Number.isInteger(fallback) ? Math.round(clamped) : clamped;
}

function shouldShowKey(key) {
  if (key === 'n_lugs' || key === 'twist_deg' || key === 'lug_deg' || key === 'mount_height' || key === 'lug_thickness_z' || key === 'lug_radial') {
    return state.params.interface_type === 'bayonet_female';
  }
  return true;
}

function buildControls() {
  const root = document.getElementById('baseControlGroups');
  root.innerHTML = '';

  for (const [title, keys] of GROUPS) {
    const visibleKeys = keys.filter((key) => key in state.context.defaults && key in state.context.limits && shouldShowKey(key));
    if (!visibleKeys.length) {
      continue;
    }

    const box = document.createElement('section');
    box.className = 'controlGroup';

    const header = document.createElement('div');
    header.className = 'panelHeader';
    header.innerHTML = `<h2>${title}</h2><p>${visibleKeys.length} controls</p>`;
    box.appendChild(header);

    const body = document.createElement('div');
    body.className = 'groupBody';

    for (const key of visibleKeys) {
      const limits = state.context.limits[key];
      const row = document.createElement('div');
      row.className = 'control';
      row.title = state.context.descriptions[key] || key;

      const labelRow = document.createElement('div');
      labelRow.className = 'controlLabel';
      labelRow.innerHTML = `
        <label>${humanizeKey(key)}</label>
        <span class="valuePill">${state.params[key]}</span>
      `;

      const controlRow = document.createElement('div');
      controlRow.className = 'controlRow';

      const slider = document.createElement('input');
      slider.type = 'range';
      slider.min = limits.min;
      slider.max = limits.max;
      slider.step = limits.step;
      slider.value = clampToLimits(key, state.params[key]);

      const number = document.createElement('input');
      number.type = 'number';
      number.min = limits.min;
      number.max = limits.max;
      number.step = limits.step;
      number.value = state.params[key];

      const pill = labelRow.querySelector('.valuePill');
      const syncValue = (value) => {
        const numeric = sanitizeNumericParam(key, value);
        state.params[key] = numeric;
        slider.value = clampToLimits(key, numeric);
        number.value = numeric;
        pill.textContent = numeric;
        debouncedPreview();
      };

      slider.addEventListener('input', () => syncValue(slider.value));
      number.addEventListener('change', () => syncValue(number.value));

      controlRow.appendChild(slider);
      controlRow.appendChild(number);
      row.appendChild(labelRow);
      row.appendChild(controlRow);
      body.appendChild(row);
    }

    box.appendChild(body);
    root.appendChild(box);
  }
}

function renderSelection() {
  const modelLine = document.getElementById('selectedModelLine');
  const mountLine = document.getElementById('selectedMountLine');
  const footprintLine = document.getElementById('selectedFootprintLine');
  const fitLowerLine = document.getElementById('selectedFitLowerLine');
  const fitUpperLine = document.getElementById('selectedFitUpperLine');
  if (!state.selection || !state.context) {
    modelLine.textContent = 'Sin modelo confirmado.';
    mountLine.textContent = 'Volve al dashboard y confirma un modelo.';
    footprintLine.textContent = '';
    fitLowerLine.textContent = '';
    fitUpperLine.textContent = '';
    return;
  }

  modelLine.textContent = `${state.selection.engineLabel || state.selection.engine} | preset ${state.selection.preset || 'default'}`;
  const baseFamilyLabel = state.selection.baseFamily ? ` | base ${state.selection.baseFamily}` : '';
  modelLine.textContent += baseFamilyLabel;
  const mount = state.context.mount_interface || {};
  const label = mount.type === 'bayonet_female' ? 'bayonet hembra' : mount.type === 'ring' ? 'aro / plug' : (mount.type || 'unknown');
  const diameter = typeof mount.female_id_mm === 'number' ? `${mount.female_id_mm.toFixed(1)} mm` : 'sin diametro';
  mountLine.textContent = `Interface detectada: ${label} | ${diameter}`;
  const footprint = state.context.footprint || {};
  if (footprint.sample_count > 0) {
    footprintLine.textContent = `Huella boca: avg ${Number(footprint.diameter_avg || 0).toFixed(1)} mm | X ${Number(footprint.diameter_x || 0).toFixed(1)} | Y ${Number(footprint.diameter_y || 0).toFixed(1)} | p90 ${Number((footprint.radius_p90 || 0) * 2).toFixed(1)} mm`;
  } else {
    footprintLine.textContent = 'Huella boca: sin muestras suficientes.';
  }
  const fitProfile = state.context.fit_profile || {};
  const lower = fitProfile.lower || {};
  const upper = fitProfile.upper || {};
  fitLowerLine.textContent = lower.inner_diameter_safe
    ? `Fit lower 0-4 mm: interior seguro ${Number(lower.inner_diameter_safe).toFixed(1)} mm | exterior ${Number(lower.diameter_avg || 0).toFixed(1)} mm`
    : '';
  fitUpperLine.textContent = upper.inner_diameter_safe
    ? `Fit upper 16-20 mm: interior seguro ${Number(upper.inner_diameter_safe).toFixed(1)} mm | exterior ${Number(upper.diameter_avg || 0).toFixed(1)} mm`
    : '';

  const generatorSelect = document.getElementById('baseGeneratorSelect');
  if (generatorSelect && state.context?.base_generators?.length) {
    generatorSelect.innerHTML = '';
    for (const generator of state.context.base_generators) {
      const option = document.createElement('option');
      option.value = generator.id;
      option.textContent = generator.label;
      generatorSelect.appendChild(option);
    }
    generatorSelect.value = state.baseGenerator || state.context.base_generator;
  }
}

async function requestPreview() {
  const token = ++state.requestToken;
  statusLine.textContent = 'Generating base preview...';
  try {
    const lampPromise = state.lampMesh
      ? Promise.resolve({ mesh: state.lampMesh })
      : fetchJson('/api/preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(selectionPayload()),
        });
    const data = await fetchJson('/api/base/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(collectPayload()),
    });
    const lampData = await lampPromise;

    if (token !== state.requestToken) {
      return;
    }

    state.previewMesh = data.mesh;
    state.lampMesh = lampData.mesh;
    state.params = { ...data.params };
    meshStats.textContent = `Ensamble | base ${data.mesh.triangle_count} tris | cabezal ${state.lampMesh.triangle_count} tris`;
    statusLine.textContent = 'Assembly preview ready';
    buildControls();
    draw();
  } catch (error) {
    statusLine.textContent = `Preview failed: ${error.message}`;
  }
}

async function exportCurrent() {
  statusLine.textContent = 'Exporting base STL...';
  try {
    const data = await fetchJson('/api/base/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(collectPayload()),
    });
    statusLine.textContent = `Exported ${data.file}`;
  } catch (error) {
    statusLine.textContent = `Export failed: ${error.message}`;
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

  const forward = normalizeVector([target[0] - eye[0], target[1] - eye[1], target[2] - eye[2]]);
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
  const orthoScale = Math.min(width, height) / Math.max(120, camera.distance * 0.9);
  return {
    x: vx * orthoScale + width * 0.5,
    y: -vy * orthoScale + height * 0.55,
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
  return {
    localVertices: vertices.map((vertex) => [
      vertex[0] - anchor[0],
      vertex[1] - anchor[1],
      vertex[2] - anchor[2],
    ]),
    target: [0, 0, (bounds.max[2] - bounds.min[2]) * 0.2],
  };
}

function drawBackdrop(width, height) {
  const gradient = ctx.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, '#f8f1e8');
  gradient.addColorStop(0.5, '#e7ddd0');
  gradient.addColorStop(1, '#cbc0b4');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = 'rgba(96, 76, 58, 0.10)';
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
  shadow.addColorStop(0, 'rgba(55, 40, 29, 0.26)');
  shadow.addColorStop(1, 'rgba(55, 40, 29, 0.0)');

  ctx.fillStyle = shadow;
  ctx.beginPath();
  ctx.ellipse(centerX, centerY, shadowWidth, shadowHeight, 0, 0, Math.PI * 2);
  ctx.fill();
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

  const assembly = buildAssemblyScene();
  const { radius, target } = assembly;
  const camera = buildCamera(radius, target);
  const focal = Math.min(width, height) * 0.95;
  drawGroundShadow(assembly.shadowVertices, radius, width, height, camera, focal);
  for (const item of assembly.items) {
    renderMesh(item, camera, focal, width, height);
  }
  if (state.showFitGuide) {
    drawFitGuide(camera, focal, width, height);
  }
}

function buildAssemblyScene() {
  const base = state.previewMesh;
  const lamp = state.lampMesh;
  const baseLocal = getAnchoredVertices(base);
  const items = [];
  const shadowVertices = [];

  items.push({
    localVertices: baseLocal.localVertices,
    triangles: base.triangles,
    color: { base: [209, 147, 86], highlight: [255, 229, 198], shadow: [108, 68, 40] },
  });
  shadowVertices.push(...baseLocal.localVertices);

  let target = [0, 0, (base.bounds.max[2] - base.bounds.min[2]) * 0.18];
  let radius = base.radius;

  if (lamp) {
    const lampLocal = getAnchoredVertices(lamp);
    const fitDepth = Number(state.context?.fit_profile?.fit_depth_mm || state.params.socket_depth || 20);
    const socketFloor = getSocketSeatHeight();
    const lampOffsetZ = socketFloor;
    const transformedLamp = lampLocal.localVertices.map((vertex) => [vertex[0], vertex[1], vertex[2] + lampOffsetZ]);
    if (state.showLampPreview) {
      items.push({
        localVertices: transformedLamp,
        triangles: lamp.triangles,
        color: { base: [178, 178, 182], highlight: [245, 245, 248], shadow: [92, 92, 100] },
      });
      shadowVertices.push(...transformedLamp);
      radius = Math.max(radius, lamp.radius);
      target = [0, 0, Math.max(target[2], lampOffsetZ + fitDepth * 0.65)];
    }
  }

  return { items, shadowVertices, radius, target };
}

function drawFitGuide(camera, focal, width, height) {
  const fitProfile = state.context?.fit_profile;
  if (!fitProfile || !state.previewMesh) {
    return;
  }

  const plinthHeight = getSocketSeatHeight();
  const lowerDiameter = Number(fitProfile.lower?.inner_diameter_safe || fitProfile.lower?.inner_diameter || 0);
  const upperDiameter = Number(fitProfile.upper?.inner_diameter_safe || fitProfile.upper?.inner_diameter || 0);
  const fitDepth = Number(fitProfile.fit_depth_mm || state.params.socket_depth || 20);
  if (!(lowerDiameter > 0) || !(upperDiameter > 0)) {
    return;
  }

  const guidePoints = [
    [-lowerDiameter * 0.5, 0, plinthHeight],
    [lowerDiameter * 0.5, 0, plinthHeight],
    [-upperDiameter * 0.5, 0, plinthHeight + fitDepth],
    [upperDiameter * 0.5, 0, plinthHeight + fitDepth],
  ].map((point) => projectPoint(point, camera, focal, width, height));

  ctx.save();
  ctx.strokeStyle = 'rgba(73, 159, 255, 0.85)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(guidePoints[0].x, guidePoints[0].y);
  ctx.lineTo(guidePoints[1].x, guidePoints[1].y);
  ctx.moveTo(guidePoints[2].x, guidePoints[2].y);
  ctx.lineTo(guidePoints[3].x, guidePoints[3].y);
  ctx.moveTo(guidePoints[0].x, guidePoints[0].y);
  ctx.lineTo(guidePoints[2].x, guidePoints[2].y);
  ctx.moveTo(guidePoints[1].x, guidePoints[1].y);
  ctx.lineTo(guidePoints[3].x, guidePoints[3].y);
  ctx.stroke();
  ctx.restore();
}

function getSocketSeatHeight() {
  const params = state.params || {};
  if (Number.isFinite(Number(params.plinth_height)) && Number.isFinite(Number(params.orbit_height))) {
    return Number(params.plinth_height) + Number(params.orbit_height) * 0.72;
  }
  if (Number.isFinite(Number(params.skirt_height))) {
    return Number(params.skirt_height);
  }
  return Number(params.plinth_height || params.base_height || 18);
}

function renderMesh(item, camera, focal, width, height) {
  const projected = item.localVertices.map((local) => projectPoint(local, camera, focal, width, height));
  const faces = item.triangles.map((triangle) => {
    const a = projected[triangle[0]];
    const b = projected[triangle[1]];
    const c = projected[triangle[2]];
    const ar = item.localVertices[triangle[0]];
    const br = item.localVertices[triangle[1]];
    const cr = item.localVertices[triangle[2]];
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
  for (const face of faces) {
    if (face.facing <= 0) {
      continue;
    }
    const [ia, ib, ic] = face.triangle;
    const a = projected[ia];
    const b = projected[ib];
    const c = projected[ic];
    const litColor = mixColor(item.color.shadow, item.color.highlight, 0.22 + face.light * 0.78);
    const fillColor = mixColor(item.color.base, litColor, 0.5 + face.rim * 0.22);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.lineTo(c.x, c.y);
    ctx.closePath();
    ctx.fillStyle = rgba(fillColor, 0.96);
    ctx.fill();
    if (face.winding < 0) {
      ctx.strokeStyle = rgba([255, 245, 232], 0.08 + face.rim * 0.12 + face.light * 0.08);
      ctx.stroke();
    }
  }
}

function attachViewportInteraction() {
  let dragging = false;
  let lastX = 0;
  let lastY = 0;

  canvas.addEventListener('pointerdown', (event) => {
    dragging = true;
    lastX = event.clientX;
    lastY = event.clientY;
    canvas.setPointerCapture(event.pointerId);
  });

  canvas.addEventListener('pointermove', (event) => {
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

  canvas.addEventListener('pointerup', () => {
    dragging = false;
  });

  canvas.addEventListener('wheel', (event) => {
    event.preventDefault();
    state.camera.distanceFactor += event.deltaY * 0.001;
    state.camera.distanceFactor = Math.max(1.4, Math.min(6.0, state.camera.distanceFactor));
    draw();
  }, { passive: false });
}

async function init() {
  document.getElementById('backToDashboardBtn')?.addEventListener('click', () => {
    window.location.href = '/dashboard/';
  });

  const rawSelection = sessionStorage.getItem('amlSelectedLampModel');
  if (!rawSelection) {
    statusLine.textContent = 'No hay modelo confirmado. Volve al dashboard.';
    renderSelection();
    return;
  }

  state.selection = JSON.parse(rawSelection);
  state.baseGenerator = state.selection.baseGenerator || 'lampbase1';
  state.context = await fetchJson('/api/base/context', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...(selectionPayload() || {}),
      base_generator: state.baseGenerator,
    }),
  });
  state.baseGenerator = state.context.base_generator;
  state.params = { ...state.context.defaults };
  renderSelection();
  buildControls();
  attachViewportInteraction();

  document.getElementById('baseGeneratorSelect')?.addEventListener('change', async (event) => {
    state.baseGenerator = event.target.value;
    state.context = await fetchJson('/api/base/context', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...(selectionPayload() || {}),
        base_generator: state.baseGenerator,
      }),
    });
    state.params = { ...state.context.defaults };
    renderSelection();
    buildControls();
    await requestPreview();
  });

  document.getElementById('refreshBasePreviewBtn')?.addEventListener('click', requestPreview);
  document.getElementById('exportBaseBtn')?.addEventListener('click', exportCurrent);
  document.getElementById('showLampPreviewInput')?.addEventListener('change', (event) => {
    state.showLampPreview = event.target.checked;
    draw();
  });
  document.getElementById('showFitGuideInput')?.addEventListener('change', (event) => {
    state.showFitGuide = event.target.checked;
    draw();
  });

  await requestPreview();
  window.addEventListener('resize', draw);
}

init().catch((error) => {
  statusLine.textContent = `Startup failed: ${error.message}`;
});
