const state = {
  items: [],
  summary: null,
  selectedEngine: null,
};

async function fetchJson(url, options = {}) {
  const headers = { ...options.headers };
  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    const message = await response.text().catch(() => "");
    throw new Error(`${response.status} ${response.statusText}${message ? ` - ${message}` : ""}`);
  }
  return response.json();
}

function renderSummary() {
  const root = document.getElementById("wbSummary");
  const summary = state.summary || {};
  const entries = [
    ["ready", "Ready"],
    ["incompatible", "Incompatibles"],
    ["import_error", "Import errors"],
    ["ignored", "Ignorados"],
  ];
  root.innerHTML = "";
  for (const [key, label] of entries) {
    const chip = document.createElement("span");
    chip.className = "wbChip";
    chip.textContent = `${label}: ${summary[key] ?? 0}`;
    root.appendChild(chip);
  }
}

function statusClass(status) {
  return `wbStatus status-${status}`;
}

function matchesFilters(item) {
  const term = (document.getElementById("searchInput").value || "").trim().toLowerCase();
  const status = document.getElementById("statusFilter").value;
  const fullText = `${item.id || ""} ${item.file || ""} ${item.label || ""}`.toLowerCase();
  if (status !== "all" && item.status !== status) {
    return false;
  }
  if (!term) {
    return true;
  }
  return fullText.includes(term);
}

function setPreview(engineId) {
  state.selectedEngine = engineId;
  const frame = document.getElementById("previewFrame");
  const title = document.getElementById("previewTitle");
  const subtitle = document.getElementById("previewSubtitle");

  if (!engineId) {
    frame.src = "about:blank";
    title.textContent = "Preview: (sin engine seleccionado)";
    subtitle.textContent = "Selecciona un engine en estado Ready para abrirlo dentro del dashboard.";
    return;
  }

  frame.src = `/dashboard/?engine=${encodeURIComponent(engineId)}`;
  title.textContent = `Preview: ${engineId}`;
  subtitle.textContent = "Instancia embebida del dashboard con el engine preseleccionado.";
}

function renderList() {
  const root = document.getElementById("wbList");
  root.innerHTML = "";
  const visible = state.items.filter(matchesFilters);

  if (!visible.length) {
    const empty = document.createElement("p");
    empty.className = "wbMeta";
    empty.textContent = "No hay modelos que coincidan con el filtro.";
    root.appendChild(empty);
    return;
  }

  for (const item of visible) {
    const card = document.createElement("article");
    card.className = "wbCard";

    const head = document.createElement("div");
    head.className = "wbCardHead";

    const left = document.createElement("strong");
    left.textContent = item.id || item.label || item.file;

    const badge = document.createElement("span");
    badge.className = statusClass(item.status);
    badge.textContent = item.status;

    head.appendChild(left);
    head.appendChild(badge);
    card.appendChild(head);

    const meta = document.createElement("div");
    meta.className = "wbMeta";
    const label = item.label ? `label: ${item.label}\n` : "";
    meta.textContent = `${label}file: ${item.file}\nreason: ${item.reason || "-"}`;
    card.appendChild(meta);

    const actions = document.createElement("div");
    actions.className = "wbActions";

    if (item.status === "ready" && item.id) {
      const previewBtn = document.createElement("button");
      previewBtn.type = "button";
      previewBtn.className = "primary";
      previewBtn.textContent = "Preview";
      previewBtn.addEventListener("click", () => setPreview(item.id));
      actions.appendChild(previewBtn);

      const openBtn = document.createElement("button");
      openBtn.type = "button";
      openBtn.textContent = "Dashboard";
      openBtn.addEventListener("click", () => {
        window.location.href = `/dashboard/?engine=${encodeURIComponent(item.id)}`;
      });
      actions.appendChild(openBtn);
    }

    card.appendChild(actions);
    root.appendChild(card);
  }
}

async function loadWorkbenchData() {
  const payload = await fetchJson("/api/workbench/engines");
  state.summary = payload.summary || {};
  state.items = payload.items || [];
  renderSummary();
  renderList();

  if (!state.selectedEngine) {
    const firstReady = state.items.find((item) => item.status === "ready" && item.id);
    if (firstReady) {
      setPreview(firstReady.id);
    }
  }
}

function wireEvents() {
  document.getElementById("searchInput").addEventListener("input", renderList);
  document.getElementById("statusFilter").addEventListener("change", renderList);
  document.getElementById("refreshBtn").addEventListener("click", async () => {
    await loadWorkbenchData();
  });
  document.getElementById("openDashboardBtn").addEventListener("click", () => {
    const engine = state.selectedEngine;
    window.location.href = engine ? `/dashboard/?engine=${encodeURIComponent(engine)}` : "/dashboard/";
  });
  document.getElementById("openNewTabBtn").addEventListener("click", () => {
    const engine = state.selectedEngine;
    const url = engine ? `/dashboard/?engine=${encodeURIComponent(engine)}` : "/dashboard/";
    window.open(url, "_blank", "noopener");
  });
}

async function init() {
  wireEvents();
  await loadWorkbenchData();
}

init().catch((error) => {
  const root = document.getElementById("wbList");
  root.innerHTML = `<p class="wbMeta">Error cargando workbench: ${error.message}</p>`;
});
