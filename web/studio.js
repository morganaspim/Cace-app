"use strict";

const NODE_W = 220;
const HEADER_H = 50;
const ROW_H = 26;
const WORLD_SIZE = 5000;
const AUTOSAVE_KEY = "cace-browser-autosave-v1";
const HISTORY_LIMIT = 100;

const state = {
  modules: new Map(),
  claims: [],
  experiment: freshExperiment(),
  selectedNodes: new Set(),
  selectedEdge: null,
  pendingOutput: null,
  zoom: 1,
  panX: 35,
  panY: 35,
  history: [],
  future: [],
  clipboard: null,
  pasteGeneration: 0,
  lastReport: null,
  activeRun: null,
  sourceInfo: null,
  spaceDown: false,
};

const el = {};

function freshExperiment() {
  return {
    schema_version: 2,
    graph_schema_version: 1,
    name: "Untitled",
    nodes: [],
    edges: [],
    groups: [],
    metadata: {},
  };
}

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function nowStamp() {
  return new Date().toLocaleTimeString();
}

function log(message) {
  const line = `[${nowStamp()}] ${message}`;
  el.console.textContent += (el.console.textContent ? "\n" : "") + line;
  el.console.scrollTop = el.console.scrollHeight;
}

function setRunStatus(text, kind = "idle") {
  el.runStatus.textContent = text;
  el.runStatus.className = `status-pill ${kind}`;
}

function apiErrorMessage(payload, fallback) {
  if (payload && typeof payload.detail === "string") return payload.detail;
  if (payload && payload.error) return payload.error;
  return fallback;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  let payload = null;
  try {
    payload = await response.json();
  } catch (_) {
    payload = null;
  }
  if (!response.ok) {
    throw new Error(apiErrorMessage(payload, `${response.status} ${response.statusText}`));
  }
  return payload;
}

function snapshot() {
  return deepClone(state.experiment);
}

function pushHistory() {
  state.history.push(snapshot());
  if (state.history.length > HISTORY_LIMIT) state.history.shift();
  state.future = [];
  syncToolbar();
}

function invalidateRun(reason) {
  if (state.lastReport) {
    state.lastReport = null;
    log(`Previous run evidence detached from edited graph: ${reason}.`);
    renderVerification();
  }
}

function persistAutosave() {
  try {
    localStorage.setItem(
      AUTOSAVE_KEY,
      JSON.stringify({ saved_at: new Date().toISOString(), experiment: state.experiment }),
    );
  } catch (error) {
    log(`Autosave failed: ${error.message}`);
  }
  syncToolbar();
}

function commitChange(reason, render = true) {
  invalidateRun(reason);
  persistAutosave();
  if (render) renderGraph();
  renderInspector();
  renderWorkspaceStats();
  syncToolbar();
}

function nodeById(id) {
  return state.experiment.nodes.find((node) => node.id === id);
}

function moduleForNode(node) {
  return node ? state.modules.get(node.module_id) : null;
}

function edgeKey(edge) {
  return `${edge.source_node}::${edge.source_port}>>${edge.target_node}::${edge.target_port}`;
}

function selectedNodeArray() {
  return state.experiment.nodes.filter((node) => state.selectedNodes.has(node.id));
}

function newId(prefix, existing) {
  let id;
  do {
    id = `${prefix}_${crypto.getRandomValues(new Uint32Array(1))[0].toString(16).padStart(8, "0")}`;
  } while (existing.has(id));
  return id;
}

function nodeHeight(node) {
  const mod = moduleForNode(node);
  if (!mod) return 90;
  return HEADER_H + 10 + ROW_H * Math.max(1, mod.inputs.length, mod.outputs.length);
}

function moduleLabel(mod) {
  return mod?.metadata?.name || "Unknown module";
}

function screenToWorld(clientX, clientY) {
  const rect = el.canvas.getBoundingClientRect();
  return {
    x: (clientX - rect.left - state.panX) / state.zoom,
    y: (clientY - rect.top - state.panY) / state.zoom,
  };
}

function worldToScreen(x, y) {
  const rect = el.canvas.getBoundingClientRect();
  return {
    x: rect.left + state.panX + x * state.zoom,
    y: rect.top + state.panY + y * state.zoom,
  };
}

function applyView() {
  el.world.style.transform = `translate(${state.panX}px, ${state.panY}px) scale(${state.zoom})`;
  drawMinimap();
}

function portPoint(node, portName, output) {
  const mod = moduleForNode(node);
  const specs = output ? mod.outputs : mod.inputs;
  const index = Math.max(0, specs.findIndex((port) => port.name === portName));
  return {
    x: node.position[0] + (output ? NODE_W : 0),
    y: node.position[1] + HEADER_H + 5 + index * ROW_H + ROW_H / 2,
  };
}

function connectionReason(sourceNode, sourcePort, targetNode, targetPort) {
  if (!sourceNode || !targetNode) return "missing node";
  if (sourceNode.id === targetNode.id) return "cannot connect a node to itself";
  const sm = moduleForNode(sourceNode);
  const tm = moduleForNode(targetNode);
  const sp = sm?.outputs.find((port) => port.name === sourcePort);
  const tp = tm?.inputs.find((port) => port.name === targetPort);
  if (!sp) return `unknown output port: ${sourcePort}`;
  if (!tp) return `unknown input port: ${targetPort}`;
  if (sp.type_name !== "any" && tp.type_name !== "any" && sp.type_name !== tp.type_name) {
    return `type mismatch: ${sp.type_name} → ${tp.type_name}`;
  }
  const su = sp.unit ?? null;
  const tu = tp.unit ?? null;
  if (!((su === null && tu === null) || (su !== null && su === tu))) {
    return `unit mismatch: ${su ?? "<unspecified>"} → ${tu ?? "<unspecified>"}`;
  }
  if (state.experiment.edges.some(
    (edge) => edge.target_node === targetNode.id && edge.target_port === targetPort,
  )) {
    return `input already connected: ${targetNode.id}.${targetPort}`;
  }
  if (state.experiment.edges.some(
    (edge) =>
      edge.source_node === sourceNode.id &&
      edge.source_port === sourcePort &&
      edge.target_node === targetNode.id &&
      edge.target_port === targetPort,
  )) {
    return "connection already exists";
  }
  if (wouldCreateCycle(sourceNode.id, targetNode.id)) return "connection would create a cycle";
  return null;
}

function wouldCreateCycle(sourceId, targetId) {
  const adjacency = new Map(state.experiment.nodes.map((node) => [node.id, []]));
  for (const edge of state.experiment.edges) {
    if (adjacency.has(edge.source_node)) adjacency.get(edge.source_node).push(edge.target_node);
  }
  adjacency.get(sourceId)?.push(targetId);
  const seen = new Set();
  const stack = [targetId];
  while (stack.length) {
    const current = stack.pop();
    if (current === sourceId) return true;
    if (seen.has(current)) continue;
    seen.add(current);
    for (const next of adjacency.get(current) || []) stack.push(next);
  }
  return false;
}

function addNode(moduleId, x, y) {
  const mod = state.modules.get(moduleId);
  if (!mod) {
    log(`Cannot add unknown module ${moduleId}`);
    return;
  }
  pushHistory();
  const ids = new Set(state.experiment.nodes.map((node) => node.id));
  const node = {
    id: newId("n", ids),
    module_id: moduleId,
    params: {},
    position: [Math.max(0, x), Math.max(0, y)],
  };
  state.experiment.nodes.push(node);
  state.selectedNodes = new Set([node.id]);
  state.selectedEdge = null;
  commitChange("node added");
  log(`Added ${mod.metadata.name} (${node.id}).`);
}

function connectPorts(sourceNodeId, sourcePort, targetNodeId, targetPort) {
  const sourceNode = nodeById(sourceNodeId);
  const targetNode = nodeById(targetNodeId);
  const reason = connectionReason(sourceNode, sourcePort, targetNode, targetPort);
  if (reason) {
    log(`Connection rejected: ${reason}.`);
    return false;
  }
  pushHistory();
  state.experiment.edges.push({
    source_node: sourceNodeId,
    source_port: sourcePort,
    target_node: targetNodeId,
    target_port: targetPort,
  });
  state.pendingOutput = null;
  commitChange("connection added");
  log(`Connected ${sourceNodeId}.${sourcePort} → ${targetNodeId}.${targetPort}.`);
  return true;
}

function deleteSelection() {
  const nodeIds = new Set(state.selectedNodes);
  const edge = state.selectedEdge;
  if (!nodeIds.size && !edge) return;
  pushHistory();

  state.experiment.edges = state.experiment.edges.filter((item) => {
    if (nodeIds.has(item.source_node) || nodeIds.has(item.target_node)) return false;
    if (edge && edgeKey(item) === edge) return false;
    return true;
  });
  if (nodeIds.size) {
    state.experiment.nodes = state.experiment.nodes.filter((node) => !nodeIds.has(node.id));
    state.experiment.groups = state.experiment.groups
      .map((group) => ({ ...group, node_ids: group.node_ids.filter((id) => !nodeIds.has(id)) }))
      .filter((group) => group.node_ids.length);
  }
  state.selectedNodes.clear();
  state.selectedEdge = null;
  state.pendingOutput = null;
  commitChange("selection deleted");
  log("Deleted selected graph items.");
}

function selectNode(id, additive = false) {
  if (!additive) state.selectedNodes.clear();
  if (additive && state.selectedNodes.has(id)) state.selectedNodes.delete(id);
  else state.selectedNodes.add(id);
  state.selectedEdge = null;
  updateSelectionClasses();
  renderInspector();
  renderVerification();
  syncToolbar();
}

function selectEdge(key) {
  state.selectedNodes.clear();
  state.selectedEdge = key;
  updateSelectionClasses();
  renderInspector();
  renderVerification();
}

function clearSelection() {
  state.selectedNodes.clear();
  state.selectedEdge = null;
  state.pendingOutput = null;
  updateSelectionClasses();
  renderInspector();
  renderVerification();
}

function updateSelectionClasses() {
  el.nodeLayer.querySelectorAll(".node").forEach((nodeEl) => {
    nodeEl.classList.toggle("selected", state.selectedNodes.has(nodeEl.dataset.nodeId));
  });
  el.edgeLayer.querySelectorAll(".edge-group").forEach((group) => {
    group.classList.toggle("selected", group.dataset.edgeKey === state.selectedEdge);
  });
  el.nodeLayer.querySelectorAll(".port-dot.output").forEach((port) => {
    const pending = state.pendingOutput;
    port.classList.toggle(
      "pending",
      !!pending &&
        pending.nodeId === port.dataset.nodeId &&
        pending.port === port.dataset.port,
    );
  });
}

function renderModuleLibrary() {
  const query = el.moduleSearch.value.trim().toLowerCase();
  el.moduleLibrary.replaceChildren();
  const grouped = new Map();
  const modules = [...state.modules.values()].filter((mod) => {
    const haystack = [
      mod.metadata.name,
      mod.metadata.module_id,
      mod.metadata.category,
      mod.metadata.description,
      mod.metadata.maturity,
    ].join(" ").toLowerCase();
    return !query || haystack.includes(query);
  });
  modules.sort((a, b) =>
    a.metadata.category.localeCompare(b.metadata.category) ||
    a.metadata.name.localeCompare(b.metadata.name)
  );
  for (const mod of modules) {
    if (!grouped.has(mod.metadata.category)) grouped.set(mod.metadata.category, []);
    grouped.get(mod.metadata.category).push(mod);
  }
  for (const [category, items] of grouped) {
    const section = document.createElement("div");
    section.className = "category";
    const title = document.createElement("div");
    title.className = "category-title";
    title.textContent = category;
    section.appendChild(title);
    for (const mod of items) {
      const card = document.createElement("div");
      card.className = "module-card";
      card.draggable = true;
      card.dataset.moduleId = mod.metadata.module_id;
      card.title = mod.metadata.description || mod.metadata.module_id;
      const name = document.createElement("div");
      name.className = "name";
      name.textContent = mod.metadata.name;
      const id = document.createElement("div");
      id.className = "id";
      id.textContent = mod.metadata.module_id;
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = `${mod.metadata.maturity} · ${mod.inputs.length} in / ${mod.outputs.length} out`;
      card.append(name, id, meta);
      card.addEventListener("dragstart", (event) => {
        event.dataTransfer.setData("application/x-cace-module", mod.metadata.module_id);
        event.dataTransfer.setData("text/plain", mod.metadata.module_id);
        event.dataTransfer.effectAllowed = "copy";
      });
      card.addEventListener("dblclick", () => {
        const rect = el.canvas.getBoundingClientRect();
        const point = screenToWorld(rect.left + rect.width / 2, rect.top + rect.height / 2);
        addNode(mod.metadata.module_id, point.x - NODE_W / 2, point.y - 50);
      });
      section.appendChild(card);
    }
    el.moduleLibrary.appendChild(section);
  }
  el.moduleCount.textContent = String(modules.length);
}

function makePortSide(node, spec, output) {
  const side = document.createElement("div");
  side.className = `port-side ${output ? "output" : "input"}`;
  const label = document.createElement("span");
  label.className = "port-label";
  label.textContent = spec.name;
  side.appendChild(label);
  if (spec.unit) {
    const unit = document.createElement("span");
    unit.className = "port-unit";
    unit.textContent = ` [${spec.unit}]`;
    side.appendChild(unit);
  }
  const dot = document.createElement("button");
  dot.type = "button";
  dot.className = `port-dot ${output ? "output" : "input"}`;
  dot.dataset.nodeId = node.id;
  dot.dataset.port = spec.name;
  dot.title = `${output ? "Output" : "Input"}: ${spec.name}\nType: ${spec.type_name}\nUnit: ${spec.unit ?? "unspecified"}`;
  dot.addEventListener("pointerdown", (event) => event.stopPropagation());
  dot.addEventListener("click", (event) => {
    event.stopPropagation();
    if (output) {
      state.pendingOutput = { nodeId: node.id, port: spec.name };
      updateSelectionClasses();
      log(`Connection source selected: ${node.id}.${spec.name}. Choose an input port.`);
    } else if (state.pendingOutput) {
      const pending = state.pendingOutput;
      connectPorts(pending.nodeId, pending.port, node.id, spec.name);
    }
  });
  side.appendChild(dot);
  return side;
}

function renderNodes() {
  el.nodeLayer.replaceChildren();
  for (const node of state.experiment.nodes) {
    const mod = moduleForNode(node);
    if (!mod) continue;
    const box = document.createElement("div");
    box.className = "node";
    box.dataset.nodeId = node.id;
    box.style.left = `${node.position[0]}px`;
    box.style.top = `${node.position[1]}px`;
    if (state.selectedNodes.has(node.id)) box.classList.add("selected");

    const header = document.createElement("div");
    header.className = "node-header";
    const title = document.createElement("div");
    title.className = "node-title";
    title.textContent = mod.metadata.name;
    const meta = document.createElement("div");
    meta.className = "node-meta";
    meta.textContent = `${mod.metadata.category} · ${mod.metadata.maturity}`;
    header.append(title, meta);

    const rows = document.createElement("div");
    rows.className = "port-rows";
    const count = Math.max(1, mod.inputs.length, mod.outputs.length);
    for (let i = 0; i < count; i += 1) {
      const row = document.createElement("div");
      row.className = "port-row";
      if (mod.inputs[i]) row.appendChild(makePortSide(node, mod.inputs[i], false));
      else {
        const empty = document.createElement("div");
        empty.className = "port-side empty";
        row.appendChild(empty);
      }
      if (mod.outputs[i]) row.appendChild(makePortSide(node, mod.outputs[i], true));
      else {
        const empty = document.createElement("div");
        empty.className = "port-side empty";
        row.appendChild(empty);
      }
      rows.appendChild(row);
    }
    box.append(header, rows);

    box.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 || event.target.classList.contains("port-dot")) return;
      selectNode(node.id, event.shiftKey);
      event.stopPropagation();
    });
    header.addEventListener("pointerdown", (event) => startNodeDrag(event, node.id));
    el.nodeLayer.appendChild(box);
  }
  updateSelectionClasses();
}

function startNodeDrag(event, nodeId) {
  if (event.button !== 0) return;
  event.preventDefault();
  event.stopPropagation();
  if (!state.selectedNodes.has(nodeId)) selectNode(nodeId, event.shiftKey);
  const movingIds = [...state.selectedNodes];
  const startClient = { x: event.clientX, y: event.clientY };
  const starts = new Map(
    movingIds.map((id) => {
      const node = nodeById(id);
      return [id, [...node.position]];
    }),
  );
  pushHistory();
  let moved = false;

  function move(moveEvent) {
    const dx = (moveEvent.clientX - startClient.x) / state.zoom;
    const dy = (moveEvent.clientY - startClient.y) / state.zoom;
    if (Math.abs(dx) > 0.25 || Math.abs(dy) > 0.25) moved = true;
    for (const id of movingIds) {
      const node = nodeById(id);
      const origin = starts.get(id);
      node.position = [Math.max(0, origin[0] + dx), Math.max(0, origin[1] + dy)];
      const box = el.nodeLayer.querySelector(`.node[data-node-id="${CSS.escape(id)}"]`);
      if (box) {
        box.style.left = `${node.position[0]}px`;
        box.style.top = `${node.position[1]}px`;
      }
    }
    renderEdges();
    renderGroups();
    drawMinimap();
  }

  function up() {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", up);
    if (moved) {
      commitChange("node moved", false);
      renderWorkspaceStats();
    } else {
      state.history.pop();
      syncToolbar();
    }
  }

  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", up, { once: true });
}

function renderEdges() {
  el.edgeLayer.replaceChildren();
  el.edgeLayer.setAttribute("viewBox", `0 0 ${WORLD_SIZE} ${WORLD_SIZE}`);
  for (const edge of state.experiment.edges) {
    const source = nodeById(edge.source_node);
    const target = nodeById(edge.target_node);
    if (!source || !target) continue;
    const a = portPoint(source, edge.source_port, true);
    const b = portPoint(target, edge.target_port, false);
    const ns = "http://www.w3.org/2000/svg";
    const group = document.createElementNS(ns, "g");
    group.setAttribute("class", "edge-group");
    group.dataset.edgeKey = edgeKey(edge);
    if (state.selectedEdge === edgeKey(edge)) group.classList.add("selected");

    const visible = document.createElementNS(ns, "path");
    visible.setAttribute("class", "edge-visible");
    const hit = document.createElementNS(ns, "path");
    hit.setAttribute("class", "edge-hit");
    const bend = Math.max(45, Math.abs(b.x - a.x) * 0.42);
    const path = `M ${a.x} ${a.y} C ${a.x + bend} ${a.y}, ${b.x - bend} ${b.y}, ${b.x} ${b.y}`;
    visible.setAttribute("d", path);
    hit.setAttribute("d", path);
    hit.addEventListener("pointerdown", (event) => {
      event.stopPropagation();
      selectEdge(edgeKey(edge));
    });
    group.append(visible, hit);
    el.edgeLayer.appendChild(group);
  }
}

function renderGroups() {
  el.groupLayer.replaceChildren();
  for (const group of state.experiment.groups) {
    const nodes = group.node_ids.map(nodeById).filter(Boolean);
    if (!nodes.length) continue;
    const left = Math.min(...nodes.map((node) => node.position[0])) - 18;
    const top = Math.min(...nodes.map((node) => node.position[1])) - 28;
    const right = Math.max(...nodes.map((node) => node.position[0] + NODE_W)) + 18;
    const bottom = Math.max(...nodes.map((node) => node.position[1] + nodeHeight(node))) + 18;
    const box = document.createElement("div");
    box.className = "group-box";
    box.style.left = `${left}px`;
    box.style.top = `${top}px`;
    box.style.width = `${right - left}px`;
    box.style.height = `${bottom - top}px`;
    const label = document.createElement("div");
    label.className = "group-label";
    label.textContent = group.name;
    box.appendChild(label);
    el.groupLayer.appendChild(box);
  }
}

function renderGraph() {
  renderNodes();
  renderEdges();
  renderGroups();
  applyView();
  el.canvasHint.classList.toggle("hidden", state.experiment.nodes.length > 0);
}

function addInfoRow(parent, label, value) {
  const row = document.createElement("div");
  row.className = "info-row";
  const strong = document.createElement("strong");
  strong.textContent = label;
  const body = document.createElement("div");
  body.textContent = value;
  row.append(strong, body);
  parent.appendChild(row);
}

function renderInspector() {
  const selected = selectedNodeArray();
  el.properties.replaceChildren();
  el.proof.replaceChildren();
  if (selected.length !== 1) {
    el.properties.className = "inspector-empty";
    el.properties.textContent = selected.length > 1
      ? `${selected.length} nodes selected. Select one node to edit parameters.`
      : "Select a node to edit its parameters.";
    el.proof.className = "inspector-empty";
    el.proof.textContent = selected.length > 1
      ? `${selected.length} nodes selected.`
      : "Select a node to inspect declared capabilities.";
    return;
  }

  const node = selected[0];
  const mod = moduleForNode(node);
  el.properties.className = "";
  const title = document.createElement("h3");
  title.className = "inspector-title";
  title.textContent = mod.metadata.name;
  const id = document.createElement("div");
  id.className = "inspector-id";
  id.textContent = `${node.id} · ${mod.metadata.module_id}`;
  el.properties.append(title, id);

  if (!mod.parameters.length) {
    const empty = document.createElement("div");
    empty.className = "inspector-empty";
    empty.textContent = "This module declares no editable parameters.";
    el.properties.appendChild(empty);
  }

  for (const spec of mod.parameters) {
    const field = document.createElement("div");
    field.className = "field";
    const label = document.createElement("label");
    label.textContent = spec.unit ? `${spec.name} [${spec.unit}]` : spec.name;
    let input;
    if (spec.type_name === "bool") {
      input = document.createElement("select");
      const yes = document.createElement("option");
      yes.value = "true"; yes.textContent = "true";
      const no = document.createElement("option");
      no.value = "false"; no.textContent = "false";
      input.append(yes, no);
      input.value = String(node.params[spec.name] ?? spec.default ?? false).toLowerCase();
    } else {
      input = document.createElement("input");
      input.type = ["number", "integer"].includes(spec.type_name) ? "number" : "text";
      if (spec.type_name === "integer") input.step = "1";
      input.value = String(node.params[spec.name] ?? spec.default ?? "");
    }
    input.addEventListener("change", () => {
      let value = input.value;
      try {
        if (spec.type_name === "number") value = Number.parseFloat(value);
        else if (spec.type_name === "integer") value = Number.parseInt(value, 10);
        else if (spec.type_name === "bool") value = value === "true";
        if (["number", "integer"].includes(spec.type_name) && !Number.isFinite(value)) {
          throw new Error("value must be numeric");
        }
        pushHistory();
        node.params[spec.name] = value;
        commitChange(`parameter ${spec.name} changed`, false);
        log(`${node.id}: ${spec.name} = ${JSON.stringify(value)}`);
      } catch (error) {
        log(`Parameter update rejected: ${error.message}`);
        renderInspector();
      }
    });
    field.append(label, input);
    if (spec.description) {
      const help = document.createElement("div");
      help.className = "field-help";
      help.textContent = spec.description;
      field.appendChild(help);
    }
    el.properties.appendChild(field);
  }

  el.proof.className = "";
  const proofTitle = document.createElement("h3");
  proofTitle.className = "inspector-title";
  proofTitle.textContent = mod.metadata.name;
  const proofId = document.createElement("div");
  proofId.className = "inspector-id";
  proofId.textContent = "Declared capability metadata — not run evidence";
  const list = document.createElement("div");
  list.className = "info-list";
  addInfoRow(list, "Maturity", mod.metadata.maturity);
  addInfoRow(list, "GPU-capable", String(mod.supports_gpu));
  addInfoRow(list, "Assumptions", (mod.metadata.assumptions || []).join("; ") || "none declared");
  addInfoRow(
    list,
    "Declared evidence capabilities",
    (mod.declared_proof_status.evidence || []).join(", ") || "none",
  );
  addInfoRow(list, "Unit tests", String(!!mod.declared_proof_status.unit_tests));
  addInfoRow(list, "Property tests", String(!!mod.declared_proof_status.property_tests));
  addInfoRow(list, "Formal artifact", mod.declared_proof_status.formal_artifact || "none");
  addInfoRow(
    list,
    "Limitations",
    (mod.declared_proof_status.limitations || []).join("; ") || "none declared",
  );
  el.proof.append(proofTitle, proofId, list);
}

function renderVerification() {
  el.verification.replaceChildren();
  if (!state.lastReport) {
    el.verification.className = "inspector-empty";
    el.verification.textContent = state.activeRun
      ? "Run is active. Evidence will appear after completed module checkpoints."
      : "No run evidence yet.";
    return;
  }
  el.verification.className = "";
  const selected = selectedNodeArray();
  const report = state.lastReport;
  const title = document.createElement("h3");
  title.className = "inspector-title";
  title.textContent = selected.length === 1
    ? `Run Evidence · ${selected[0].id}`
    : "Run Evidence · Graph";
  el.verification.appendChild(title);

  if (selected.length === 1) {
    const nodeId = selected[0].id;
    const records = report.verification?.[nodeId] || [];
    const cert = (report.certificates || []).find((item) => item.node_id === nodeId);
    if (cert) {
      const summary = document.createElement("div");
      summary.className = "evidence-card";
      const heading = document.createElement("div");
      heading.className = "evidence-title";
      heading.textContent = `Device: ${cert.actual_device} / ${cert.backend}`;
      const sub = document.createElement("div");
      sub.className = "evidence-sub";
      sub.textContent = `Evidence: ${(cert.evidence || []).join(", ") || "none"}`;
      summary.append(heading, sub);
      el.verification.appendChild(summary);
    }
    if (!records.length) {
      const empty = document.createElement("div");
      empty.className = "inspector-empty";
      empty.textContent = "Module generated no verification evidence for this run.";
      el.verification.appendChild(empty);
    }
    for (const record of records) {
      const card = document.createElement("div");
      card.className = `evidence-card ${record.state}`;
      const heading = document.createElement("div");
      heading.className = "evidence-title";
      heading.textContent = `[${String(record.state).toUpperCase()}] ${record.kind}`;
      const claim = document.createElement("div");
      claim.className = "claim-statement";
      claim.textContent = record.claim;
      const sub = document.createElement("div");
      sub.className = "evidence-sub";
      sub.textContent = `${record.verifier} · ${record.method}`;
      const metrics = document.createElement("pre");
      metrics.className = "json-view";
      metrics.textContent = JSON.stringify(record.metrics || {}, null, 2);
      card.append(heading, claim, sub, metrics);
      el.verification.appendChild(card);
    }
    const output = document.createElement("pre");
    output.className = "json-view";
    output.textContent = JSON.stringify(report.outputs?.[nodeId] ?? {}, null, 2);
    el.verification.appendChild(output);
  } else {
    const summary = document.createElement("div");
    summary.className = `evidence-card ${report.all_verifiers_passed ? "pass" : "not-run"}`;
    const heading = document.createElement("div");
    heading.className = "evidence-title";
    heading.textContent = report.all_verifiers_passed
      ? "All generated verification records passed"
      : "Run completed without an all-verifiers PASS";
    const sub = document.createElement("div");
    sub.className = "evidence-sub";
    sub.textContent = `Run ${report.run_id} · scope ${report.run_scope} · seed ${report.seed}`;
    summary.append(heading, sub);
    el.verification.appendChild(summary);
    const cert = document.createElement("pre");
    cert.className = "json-view";
    cert.textContent = JSON.stringify(report.graph_certificate || {}, null, 2);
    el.verification.appendChild(cert);
  }
}

function renderClaims() {
  el.claims.replaceChildren();
  if (!state.claims.length) {
    el.claims.className = "inspector-empty";
    el.claims.textContent = "No canonical claims were returned.";
    return;
  }
  el.claims.className = "";
  for (const claim of state.claims) {
    const card = document.createElement("div");
    card.className = "claim-card";
    const stateTag = document.createElement("span");
    stateTag.className = `claim-state chip ${claim.current_head_qualified ? "good" : "warn"}`;
    stateTag.textContent = claim.qualification_state;
    const id = document.createElement("div");
    id.className = "claim-id";
    id.textContent = claim.claim_id;
    const statement = document.createElement("div");
    statement.className = "claim-statement";
    statement.textContent = claim.statement;
    const source = document.createElement("div");
    source.className = "evidence-sub";
    source.textContent = `Source: ${claim.qualification_source} · ceiling: ${claim.evidence_ceiling}`;
    card.append(stateTag, id, statement, source);
    el.claims.appendChild(card);
  }
}

function renderWorkspaceStats() {
  const groups = state.experiment.groups.length;
  el.workspaceStats.textContent =
    `${state.experiment.nodes.length} nodes · ${state.experiment.edges.length} connections · ${groups} groups\n` +
    `Selected: ${state.selectedNodes.size} node(s)`;
  el.recoverBtn.disabled = !localStorage.getItem(AUTOSAVE_KEY);
}

function renderAll() {
  renderModuleLibrary();
  renderGraph();
  renderInspector();
  renderVerification();
  renderClaims();
  renderWorkspaceStats();
  syncToolbar();
}

function syncToolbar() {
  el.undoBtn.disabled = !state.history.length;
  el.redoBtn.disabled = !state.future.length;
  el.copyBtn.disabled = !state.selectedNodes.size;
  el.pasteBtn.disabled = !state.clipboard;
  const active = !!state.activeRun;
  const paused = !!state.activeRun?.paused;
  el.runBtn.disabled = active || !state.experiment.nodes.length;
  el.runSelectedBtn.disabled = active || !state.selectedNodes.size;
  el.pauseBtn.disabled = !active || paused;
  el.resumeBtn.disabled = !active || !paused;
  el.cancelBtn.disabled = !active;
}

function undo() {
  if (!state.history.length) return;
  state.future.push(snapshot());
  state.experiment = state.history.pop();
  state.selectedNodes.clear();
  state.selectedEdge = null;
  state.pendingOutput = null;
  invalidateRun("undo");
  persistAutosave();
  renderAll();
  log("Undo.");
}

function redo() {
  if (!state.future.length) return;
  state.history.push(snapshot());
  state.experiment = state.future.pop();
  state.selectedNodes.clear();
  state.selectedEdge = null;
  state.pendingOutput = null;
  invalidateRun("redo");
  persistAutosave();
  renderAll();
  log("Redo.");
}

function copySelection() {
  const nodes = selectedNodeArray();
  if (!nodes.length) return;
  const ids = new Set(nodes.map((node) => node.id));
  const originX = Math.min(...nodes.map((node) => node.position[0]));
  const originY = Math.min(...nodes.map((node) => node.position[1]));
  state.clipboard = {
    nodes: nodes.map((node) => ({
      source_id: node.id,
      module_id: node.module_id,
      params: deepClone(node.params),
      relative_position: [node.position[0] - originX, node.position[1] - originY],
    })),
    edges: state.experiment.edges.filter(
      (edge) => ids.has(edge.source_node) && ids.has(edge.target_node),
    ).map(deepClone),
    origin: [originX, originY],
  };
  state.pasteGeneration = 0;
  syncToolbar();
  log(`Copied ${nodes.length} node(s).`);
}

function pasteSelection() {
  if (!state.clipboard) return;
  pushHistory();
  state.pasteGeneration += 1;
  const offset = 30 * state.pasteGeneration;
  const existing = new Set(state.experiment.nodes.map((node) => node.id));
  const idMap = new Map();
  for (const fragment of state.clipboard.nodes) {
    const id = newId("n", existing);
    existing.add(id);
    idMap.set(fragment.source_id, id);
    state.experiment.nodes.push({
      id,
      module_id: fragment.module_id,
      params: deepClone(fragment.params),
      position: [
        state.clipboard.origin[0] + fragment.relative_position[0] + offset,
        state.clipboard.origin[1] + fragment.relative_position[1] + offset,
      ],
    });
  }
  for (const edge of state.clipboard.edges) {
    state.experiment.edges.push({
      source_node: idMap.get(edge.source_node),
      source_port: edge.source_port,
      target_node: idMap.get(edge.target_node),
      target_port: edge.target_port,
    });
  }
  state.selectedNodes = new Set(idMap.values());
  commitChange("selection pasted");
  log(`Pasted ${idMap.size} node(s).`);
}

function alignSelection(axis, strategy) {
  const nodes = selectedNodeArray();
  if (nodes.length < 2) {
    log("Alignment requires at least two selected nodes.");
    return;
  }
  pushHistory();
  const index = axis === "x" ? 0 : 1;
  const values = nodes.map((node) => node.position[index]);
  const target = strategy === "min"
    ? Math.min(...values)
    : values.reduce((a, b) => a + b, 0) / values.length;
  for (const node of nodes) node.position[index] = target;
  commitChange("nodes aligned");
}

function createGroup() {
  const nodes = selectedNodeArray();
  if (!nodes.length) {
    log("Create group: select at least one node.");
    return;
  }
  const grouped = new Set(state.experiment.groups.flatMap((group) => group.node_ids));
  const collision = nodes.find((node) => grouped.has(node.id));
  if (collision) {
    log(`Create group rejected: ${collision.id} is already grouped.`);
    return;
  }
  const name = prompt("Group name:", `Group ${state.experiment.groups.length + 1}`);
  if (!name?.trim()) return;
  pushHistory();
  const ids = new Set(state.experiment.groups.map((group) => group.id));
  state.experiment.groups.push({
    id: newId("g", ids),
    name: name.trim(),
    node_ids: nodes.map((node) => node.id).sort(),
  });
  commitChange("group created");
  log(`Created group "${name.trim()}" with ${nodes.length} node(s).`);
}

function ungroupSelection() {
  const selected = new Set(state.selectedNodes);
  if (!selected.size) return;
  const before = JSON.stringify(state.experiment.groups);
  const next = state.experiment.groups
    .map((group) => ({ ...group, node_ids: group.node_ids.filter((id) => !selected.has(id)) }))
    .filter((group) => group.node_ids.length);
  if (JSON.stringify(next) === before) {
    log("Selected nodes are not members of a group.");
    return;
  }
  pushHistory();
  state.experiment.groups = next;
  commitChange("nodes ungrouped");
  log("Removed selected nodes from groups.");
}

function fitGraph() {
  if (!state.experiment.nodes.length) return;
  const rect = el.canvas.getBoundingClientRect();
  const left = Math.min(...state.experiment.nodes.map((node) => node.position[0]));
  const top = Math.min(...state.experiment.nodes.map((node) => node.position[1]));
  const right = Math.max(...state.experiment.nodes.map((node) => node.position[0] + NODE_W));
  const bottom = Math.max(...state.experiment.nodes.map((node) => node.position[1] + nodeHeight(node)));
  const width = Math.max(1, right - left);
  const height = Math.max(1, bottom - top);
  state.zoom = Math.max(0.2, Math.min(1.6, Math.min((rect.width - 100) / width, (rect.height - 100) / height)));
  state.panX = (rect.width - width * state.zoom) / 2 - left * state.zoom;
  state.panY = (rect.height - height * state.zoom) / 2 - top * state.zoom;
  applyView();
}

function resetView() {
  state.zoom = 1;
  state.panX = 35;
  state.panY = 35;
  applyView();
}

function drawMinimap() {
  const ctx = el.minimap.getContext("2d");
  const w = el.minimap.width;
  const h = el.minimap.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#09111c";
  ctx.fillRect(0, 0, w, h);
  if (!state.experiment.nodes.length) return;

  const left = Math.min(...state.experiment.nodes.map((node) => node.position[0])) - 80;
  const top = Math.min(...state.experiment.nodes.map((node) => node.position[1])) - 80;
  const right = Math.max(...state.experiment.nodes.map((node) => node.position[0] + NODE_W)) + 80;
  const bottom = Math.max(...state.experiment.nodes.map((node) => node.position[1] + nodeHeight(node))) + 80;
  const scale = Math.min(w / Math.max(1, right - left), h / Math.max(1, bottom - top));

  ctx.strokeStyle = "#35516e";
  ctx.lineWidth = 1;
  for (const edge of state.experiment.edges) {
    const aNode = nodeById(edge.source_node);
    const bNode = nodeById(edge.target_node);
    if (!aNode || !bNode) continue;
    const a = portPoint(aNode, edge.source_port, true);
    const b = portPoint(bNode, edge.target_port, false);
    ctx.beginPath();
    ctx.moveTo((a.x - left) * scale, (a.y - top) * scale);
    ctx.lineTo((b.x - left) * scale, (b.y - top) * scale);
    ctx.stroke();
  }

  for (const node of state.experiment.nodes) {
    ctx.fillStyle = state.selectedNodes.has(node.id) ? "#59b4ff" : "#31516e";
    ctx.fillRect(
      (node.position[0] - left) * scale,
      (node.position[1] - top) * scale,
      Math.max(3, NODE_W * scale),
      Math.max(3, nodeHeight(node) * scale),
    );
  }

  const canvasRect = el.canvas.getBoundingClientRect();
  const viewLeft = -state.panX / state.zoom;
  const viewTop = -state.panY / state.zoom;
  const viewWidth = canvasRect.width / state.zoom;
  const viewHeight = canvasRect.height / state.zoom;
  ctx.strokeStyle = "#d2eaff";
  ctx.lineWidth = 1.5;
  ctx.strokeRect(
    (viewLeft - left) * scale,
    (viewTop - top) * scale,
    viewWidth * scale,
    viewHeight * scale,
  );
}

function downloadExperiment() {
  const filename = `${(state.experiment.name || "experiment").replace(/[^a-z0-9_-]+/gi, "-")}.cace`;
  const blob = new Blob([JSON.stringify(state.experiment, null, 2) + "\n\n"], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
  log(`Saved ${filename}.`);
}

function loadExperimentObject(documentValue, sourceLabel) {
  if (!documentValue || typeof documentValue !== "object") throw new Error("experiment must be a JSON object");
  const schema = Number(documentValue.schema_version);
  if (![1, 2].includes(schema)) throw new Error(`unsupported experiment schema: ${documentValue.schema_version}`);
  const exp = deepClone(documentValue);
  if (schema === 1) {
    exp.schema_version = 2;
    exp.graph_schema_version = 1;
    exp.groups = [];
  }
  exp.nodes ||= [];
  exp.edges ||= [];
  exp.groups ||= [];
  exp.metadata ||= {};
  for (const node of exp.nodes) {
    if (!state.modules.has(node.module_id)) throw new Error(`unknown module: ${node.module_id}`);
    if (!Array.isArray(node.position) || node.position.length !== 2) node.position = [0, 0];
    node.params ||= {};
  }
  pushHistory();
  state.experiment = exp;
  state.selectedNodes.clear();
  state.selectedEdge = null;
  state.pendingOutput = null;
  state.lastReport = null;
  persistAutosave();
  renderAll();
  fitGraph();
  log(`Opened ${sourceLabel}.`);
}

function recoverAutosave() {
  const raw = localStorage.getItem(AUTOSAVE_KEY);
  if (!raw) {
    log("No browser autosave is available.");
    return;
  }
  try {
    const wrapper = JSON.parse(raw);
    loadExperimentObject(wrapper.experiment, `browser autosave from ${wrapper.saved_at || "unknown time"}`);
  } catch (error) {
    log(`Autosave recovery failed: ${error.message}`);
  }
}

function newExperiment() {
  if (state.experiment.nodes.length && !confirm("Start a new experiment? The current browser workspace is autosaved.")) return;
  pushHistory();
  state.experiment = freshExperiment();
  state.selectedNodes.clear();
  state.selectedEdge = null;
  state.pendingOutput = null;
  state.lastReport = null;
  state.activeRun = null;
  resetView();
  persistAutosave();
  renderAll();
  log("New experiment.");
}

async function startRun(selectedOnly) {
  if (state.activeRun) return;
  const targets = selectedOnly ? [...state.selectedNodes] : [];
  if (selectedOnly && !targets.length) {
    log("Run Selected requires at least one selected node.");
    return;
  }
  if (!state.experiment.nodes.length) {
    log("Nothing to run.");
    return;
  }
  try {
    setRunStatus("STARTING", "running");
    const payload = await api("/api/runs", {
      method: "POST",
      body: JSON.stringify({
        experiment: state.experiment,
        seed: Number.parseInt(el.seedInput.value || "0", 10),
        target_node_ids: targets,
        gpu_enabled: el.gpuToggle.checked,
      }),
    });
    state.activeRun = payload;
    state.lastReport = null;
    log(`Run job ${payload.job_id} started${targets.length ? ` for selected/upstream targets ${targets.join(", ")}` : ""}.`);
    syncToolbar();
    renderVerification();
    pollRun(payload.job_id);
  } catch (error) {
    state.activeRun = null;
    setRunStatus("FAILED", "fail");
    log(`Run start failed: ${error.message}`);
    syncToolbar();
  }
}

async function pollRun(jobId) {
  if (!state.activeRun || state.activeRun.job_id !== jobId) return;
  try {
    const job = await api(`/api/runs/${encodeURIComponent(jobId)}`);
    state.activeRun = job.status === "running" || job.status === "queued" ? job : state.activeRun;
    if (job.paused) setRunStatus("PAUSED", "paused");
    else if (["running", "queued"].includes(job.status)) setRunStatus(job.status.toUpperCase(), "running");
    syncToolbar();

    if (["completed", "cancelled", "failed"].includes(job.status)) {
      state.activeRun = null;
      if (job.status === "completed") {
        state.lastReport = job.result;
        const passed = !!job.result?.all_verifiers_passed;
        setRunStatus(passed ? "PASS" : "REVIEW", passed ? "pass" : "paused");
        log(`Run ${job.result?.run_id || jobId} completed: ${passed ? "all generated verifiers passed" : "not all-verifiers PASS"}.`);
      } else if (job.status === "cancelled") {
        state.lastReport = job.result || null;
        setRunStatus("CANCELLED", "paused");
        log(`Run job ${jobId} cancelled at a module boundary.`);
      } else {
        setRunStatus("FAILED", "fail");
        log(`Run job ${jobId} failed: ${job.error?.error_type || "Error"}: ${job.error?.error || "unknown error"}`);
      }
      syncToolbar();
      renderVerification();
      return;
    }
    setTimeout(() => pollRun(jobId), 450);
  } catch (error) {
    state.activeRun = null;
    setRunStatus("FAILED", "fail");
    log(`Run status failed: ${error.message}`);
    syncToolbar();
  }
}

async function controlRun(action) {
  if (!state.activeRun) return;
  try {
    const job = await api(
      `/api/runs/${encodeURIComponent(state.activeRun.job_id)}/${action}`,
      { method: "POST", body: "{}" },
    );
    state.activeRun = job;
    if (action === "pause") setRunStatus("PAUSE REQUESTED", "paused");
    if (action === "resume") setRunStatus("RUNNING", "running");
    if (action === "cancel") setRunStatus("CANCEL REQUESTED", "paused");
    log(`${action[0].toUpperCase() + action.slice(1)} requested; control takes effect at module boundaries.`);
    syncToolbar();
  } catch (error) {
    log(`Run control failed: ${error.message}`);
  }
}

function initCanvasInteraction() {
  el.canvas.addEventListener("dragover", (event) => {
    event.preventDefault();
    el.canvas.classList.add("drag-over");
  });
  el.canvas.addEventListener("dragleave", () => el.canvas.classList.remove("drag-over"));
  el.canvas.addEventListener("drop", (event) => {
    event.preventDefault();
    el.canvas.classList.remove("drag-over");
    const moduleId =
      event.dataTransfer.getData("application/x-cace-module") ||
      event.dataTransfer.getData("text/plain");
    if (!state.modules.has(moduleId)) return;
    const point = screenToWorld(event.clientX, event.clientY);
    addNode(moduleId, point.x - NODE_W / 2, point.y - 25);
  });

  el.canvas.addEventListener("wheel", (event) => {
    if (!event.ctrlKey) return;
    event.preventDefault();
    const rect = el.canvas.getBoundingClientRect();
    const mx = event.clientX - rect.left;
    const my = event.clientY - rect.top;
    const wx = (mx - state.panX) / state.zoom;
    const wy = (my - state.panY) / state.zoom;
    const factor = event.deltaY < 0 ? 1.15 : 1 / 1.15;
    state.zoom = Math.max(0.15, Math.min(3, state.zoom * factor));
    state.panX = mx - wx * state.zoom;
    state.panY = my - wy * state.zoom;
    applyView();
  }, { passive: false });

  el.canvas.addEventListener("pointerdown", (event) => {
    if (event.target.closest(".node") || event.target.closest(".edge-hit")) return;
    if (event.button === 1 || (event.button === 0 && state.spaceDown)) {
      event.preventDefault();
      const start = { x: event.clientX, y: event.clientY, px: state.panX, py: state.panY };
      const move = (moveEvent) => {
        state.panX = start.px + moveEvent.clientX - start.x;
        state.panY = start.py + moveEvent.clientY - start.y;
        applyView();
      };
      const up = () => {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", up);
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", up, { once: true });
      return;
    }
    if (event.button !== 0) return;

    const rect = el.canvas.getBoundingClientRect();
    const start = { x: event.clientX - rect.left, y: event.clientY - rect.top };
    el.selectionBox.classList.remove("hidden");
    el.selectionBox.style.left = `${start.x}px`;
    el.selectionBox.style.top = `${start.y}px`;
    el.selectionBox.style.width = "0px";
    el.selectionBox.style.height = "0px";

    const move = (moveEvent) => {
      const x = moveEvent.clientX - rect.left;
      const y = moveEvent.clientY - rect.top;
      el.selectionBox.style.left = `${Math.min(start.x, x)}px`;
      el.selectionBox.style.top = `${Math.min(start.y, y)}px`;
      el.selectionBox.style.width = `${Math.abs(x - start.x)}px`;
      el.selectionBox.style.height = `${Math.abs(y - start.y)}px`;
    };

    const up = (upEvent) => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      const x = upEvent.clientX - rect.left;
      const y = upEvent.clientY - rect.top;
      const box = {
        left: Math.min(start.x, x) + rect.left,
        right: Math.max(start.x, x) + rect.left,
        top: Math.min(start.y, y) + rect.top,
        bottom: Math.max(start.y, y) + rect.top,
      };
      const isClick = Math.abs(x - start.x) < 4 && Math.abs(y - start.y) < 4;
      if (!upEvent.shiftKey) state.selectedNodes.clear();
      if (isClick) {
        if (!upEvent.shiftKey) clearSelection();
      } else {
        el.nodeLayer.querySelectorAll(".node").forEach((nodeEl) => {
          const r = nodeEl.getBoundingClientRect();
          const intersects = r.right >= box.left && r.left <= box.right && r.bottom >= box.top && r.top <= box.bottom;
          if (intersects) state.selectedNodes.add(nodeEl.dataset.nodeId);
        });
        state.selectedEdge = null;
        updateSelectionClasses();
        renderInspector();
        renderVerification();
      }
      el.selectionBox.classList.add("hidden");
      syncToolbar();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up, { once: true });
  });
}

function bindButtons() {
  el.newBtn.addEventListener("click", newExperiment);
  el.openBtn.addEventListener("click", () => el.fileInput.click());
  el.saveBtn.addEventListener("click", downloadExperiment);
  el.undoBtn.addEventListener("click", undo);
  el.redoBtn.addEventListener("click", redo);
  el.copyBtn.addEventListener("click", copySelection);
  el.pasteBtn.addEventListener("click", pasteSelection);
  el.fitBtn.addEventListener("click", fitGraph);
  el.resetViewBtn.addEventListener("click", resetView);
  el.alignLeftBtn.addEventListener("click", () => alignSelection("x", "min"));
  el.alignTopBtn.addEventListener("click", () => alignSelection("y", "min"));
  el.alignColumnBtn.addEventListener("click", () => alignSelection("x", "mean"));
  el.alignRowBtn.addEventListener("click", () => alignSelection("y", "mean"));
  el.groupBtn.addEventListener("click", createGroup);
  el.ungroupBtn.addEventListener("click", ungroupSelection);
  el.recoverBtn.addEventListener("click", recoverAutosave);
  el.runBtn.addEventListener("click", () => startRun(false));
  el.runSelectedBtn.addEventListener("click", () => startRun(true));
  el.pauseBtn.addEventListener("click", () => controlRun("pause"));
  el.resumeBtn.addEventListener("click", () => controlRun("resume"));
  el.cancelBtn.addEventListener("click", () => controlRun("cancel"));
  el.clearConsoleBtn.addEventListener("click", () => { el.console.textContent = ""; });
  el.moduleSearch.addEventListener("input", renderModuleLibrary);

  el.fileInput.addEventListener("change", async () => {
    const file = el.fileInput.files?.[0];
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text());
      loadExperimentObject(parsed, file.name);
    } catch (error) {
      log(`Open failed: ${error.message}`);
    } finally {
      el.fileInput.value = "";
    }
  });

  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("active"));
      button.classList.add("active");
      document.getElementById(`tab-${button.dataset.tab}`).classList.add("active");
    });
  });
}

function bindKeyboard() {
  window.addEventListener("keydown", (event) => {
    if (event.code === "Space" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) {
      state.spaceDown = true;
    }
    const editing = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);
    if (editing && !event.ctrlKey && !event.metaKey) return;
    const ctrl = event.ctrlKey || event.metaKey;
    if (ctrl && event.key.toLowerCase() === "z" && event.shiftKey) { event.preventDefault(); redo(); }
    else if (ctrl && event.key.toLowerCase() === "z") { event.preventDefault(); undo(); }
    else if (ctrl && event.key.toLowerCase() === "y") { event.preventDefault(); redo(); }
    else if (ctrl && event.key.toLowerCase() === "c") { event.preventDefault(); copySelection(); }
    else if (ctrl && event.key.toLowerCase() === "v") { event.preventDefault(); pasteSelection(); }
    else if (ctrl && event.key.toLowerCase() === "s") { event.preventDefault(); downloadExperiment(); }
    else if (ctrl && event.key.toLowerCase() === "o") { event.preventDefault(); el.fileInput.click(); }
    else if (ctrl && event.key.toLowerCase() === "n") { event.preventDefault(); newExperiment(); }
    else if (ctrl && event.key.toLowerCase() === "r") { event.preventDefault(); startRun(false); }
    else if (ctrl && event.key === "0") { event.preventDefault(); resetView(); }
    else if (!ctrl && event.key.toLowerCase() === "f" && !editing) { event.preventDefault(); fitGraph(); }
    else if (["Delete", "Backspace"].includes(event.key) && !editing) { event.preventDefault(); deleteSelection(); }
    else if (event.key === "Escape") { clearSelection(); }
  });
  window.addEventListener("keyup", (event) => {
    if (event.code === "Space") state.spaceDown = false;
  });
}

function cacheElements() {
  const ids = {
    console: "console",
    runStatus: "run-status",
    sourceStatus: "source-status",
    canvas: "canvas-shell",
    canvasHint: "canvas-hint",
    world: "world",
    edgeLayer: "edge-layer",
    groupLayer: "group-layer",
    nodeLayer: "node-layer",
    selectionBox: "selection-box",
    minimap: "minimap",
    moduleSearch: "module-search",
    moduleLibrary: "module-library",
    moduleCount: "module-count",
    properties: "properties-panel",
    proof: "proof-panel",
    verification: "verification-panel",
    claims: "claims-panel",
    workspaceStats: "workspace-stats",
    fileInput: "file-input",
    seedInput: "seed-input",
    gpuToggle: "gpu-toggle",
    newBtn: "new-btn",
    openBtn: "open-btn",
    saveBtn: "save-btn",
    undoBtn: "undo-btn",
    redoBtn: "redo-btn",
    copyBtn: "copy-btn",
    pasteBtn: "paste-btn",
    fitBtn: "fit-btn",
    resetViewBtn: "reset-view-btn",
    alignLeftBtn: "align-left-btn",
    alignTopBtn: "align-top-btn",
    alignColumnBtn: "align-column-btn",
    alignRowBtn: "align-row-btn",
    groupBtn: "group-btn",
    ungroupBtn: "ungroup-btn",
    recoverBtn: "recover-btn",
    runBtn: "run-btn",
    runSelectedBtn: "run-selected-btn",
    pauseBtn: "pause-btn",
    resumeBtn: "resume-btn",
    cancelBtn: "cancel-btn",
    clearConsoleBtn: "clear-console-btn",
  };
  for (const [name, id] of Object.entries(ids)) el[name] = document.getElementById(id);
}

async function bootstrap() {
  cacheElements();
  bindButtons();
  bindKeyboard();
  initCanvasInteraction();
  setRunStatus("LOADING", "running");
  log("Loading canonical CACE module registry and claim view…");

  try {
    const [registryPayload, claimsPayload, sourcePayload] = await Promise.all([
      api("/api/modules"),
      api("/api/claims"),
      api("/api"),
    ]);
    for (const mod of registryPayload.modules || []) {
      state.modules.set(mod.metadata.module_id, mod);
    }
    state.claims = claimsPayload.claims || [];
    state.sourceInfo = sourcePayload;
    el.sourceStatus.textContent =
      `app source: ${sourcePayload.deployed_source_commit} · formal baseline: ${sourcePayload.formal_baseline_commit} · qualification run: ${sourcePayload.formal_qualification_run_id}`;
    setRunStatus("IDLE", "idle");
    renderAll();
    log(`Loaded ${state.modules.size} modules and ${state.claims.length} canonical claims.`);
    log("Drag modules onto the canvas. Click an output port, then an input port, to connect them.");
    if (localStorage.getItem(AUTOSAVE_KEY)) {
      log("A browser autosave is available. Use Recover Browser Autosave to restore it.");
    }
  } catch (error) {
    setRunStatus("API ERROR", "fail");
    log(`Studio initialization failed: ${error.message}`);
    el.moduleLibrary.textContent = "Could not load module registry.";
  }
}

window.addEventListener("resize", drawMinimap);
window.addEventListener("DOMContentLoaded", bootstrap);
