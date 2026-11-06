"use strict";
/* ANATOMICA web shell — raw WebGL2, zero dependencies.
   Loads web/data/{manifest.json, records.json, <system>.bin x11}
   produced by tools/pack_geometry.py (merged static buffers, one
   draw call per layer when unfiltered; per-record range draws when
   a region filter is active). All eleven Body Model systems are
   layers; the manifest is the source of truth for each layer's
   pick bit, label and colour — the literals below are asserted
   against it by tools/verify_web.js (W1/W6). Picking renders an
   id pass on demand; the pick codec is the Milestone-7-FIX codec
   (byte 3 of the id rides in alpha) and must not regress.
   Milestone 21: per-layer opacity — a slider per layer (FS_SHADE's
   uOpacity) so a focus view can make the integumentary shell
   genuinely translucent instead of merely dimmed (Milestone-16
   defect 1). Opacity is shading state only: the id pass never
   reads it, and tools/verify_web.js W8 asserts that separation.
   Milestone 27: delivery — layers load progressively in
   LOAD_ORDER (skeletal first) and render as each arrives instead
   of waiting for all eleven; each pack is fetched in its gzip
   delivery encoding (data/delivery.json, produced by
   tools/pack_geometry.py --compress) and decoded with the
   platform DecompressionStream, falling back to the canonical
   pack on any failure. Zero dependencies, as ever; the pick
   codec and the id pass are untouched (verify_web.js W9 gates
   the delivery encoding's byte-identity and this wiring). */

const $ = id => document.getElementById(id);
const statusEl = $("status"), stripEl = $("strip"), panelEl = $("panel"), listEl = $("list");

let gl, shadeProg, pickProg, pickFBO, pickTex, pickDepth;
let layers = {};        // system key -> {vao, ibo, edgeBuf, indexCount, edgeIndexCount, ranges, ...}
let layerOrder = [];    // system keys in manifest order
let records = [];       // records.json entries (all layers)
let clinical = {};      // clinical records by id
let byId = new Map();   // layer:id -> record entry
let rangeByKey = new Map(); // layer:id -> manifest range
let selected = null;    // record entry or null
let hovered = null;
let drawCallsLastFrame = 0, frameMs = 0, loadMs = 0;
let visDirty = true, drawnStats = { records: 0, meshes: 0, tris: 0 };
let manifestData = null;  // manifest.json, kept for the layer loader
let delivery = null;      // delivery.json (Milestone 27) or null when absent
/* Progressive load priority (Milestone 27): skeletal first (the
   default-visible framing/reference layer), muscular second (it
   completes the default view); the remaining systems follow in
   manifest order (innermost -> outermost), which puts the
   default-off, occluding integumentary shell last. Must equal
   delivery.json's load_order — verify_web.js W9 asserts it. */
const LOAD_ORDER = ["skeletal", "muscular", "cardiovascular", "nervous", "respiratory", "digestive", "urinary", "lymphatic", "endocrine", "reproductive", "integumentary"];
const layerState = {};    // key -> { state: "queued"|"loading"|"ready"|"error", pct, encoding }
let firstLayerMs = 0;     // boot -> first layer ready (Milestone 27)

const LAYER_STYLE = {
  skeletal: { color: [0.78, 0.72, 0.60], label: "Skeletal" },
  muscular: { color: [0.55, 0.22, 0.19], label: "Muscular" },
  cardiovascular: { color: [0.80, 0.16, 0.28], label: "Cardiovascular" },
  nervous: { color: [0.90, 0.78, 0.35], label: "Nervous" },
  respiratory: { color: [0.45, 0.65, 0.85], label: "Respiratory" },
  digestive: { color: [0.75, 0.50, 0.30], label: "Digestive" },
  urinary: { color: [0.85, 0.55, 0.15], label: "Urinary" },
  lymphatic: { color: [0.35, 0.70, 0.35], label: "Lymphatic" },
  endocrine: { color: [0.60, 0.40, 0.75], label: "Endocrine" },
  reproductive: { color: [0.80, 0.45, 0.60], label: "Reproductive" },
  integumentary: { color: [0.88, 0.62, 0.45], label: "Integumentary" },
};
const LAYER_BIT = { skeletal: 1, muscular: 2, cardiovascular: 3, nervous: 4, respiratory: 5, digestive: 6, urinary: 7, lymphatic: 8, endocrine: 9, reproductive: 10, integumentary: 11 };
const DEFAULT_VISIBLE = new Set(["skeletal", "muscular"]);

// ---------- math (column-major mat4) ----------
function perspective(fovy, aspect, near, far) {
  const f = 1 / Math.tan(fovy / 2), nf = 1 / (near - far);
  return new Float32Array([f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1,
                           0, 0, 2 * far * near * nf, 0]);
}
function lookAt(eye, tgt, up) {
  let zx = eye[0] - tgt[0], zy = eye[1] - tgt[1], zz = eye[2] - tgt[2];
  let l = Math.hypot(zx, zy, zz); zx /= l; zy /= l; zz /= l;
  let xx = up[1] * zz - up[2] * zy, xy = up[2] * zx - up[0] * zz, xz = up[0] * zy - up[1] * zx;
  l = Math.hypot(xx, xy, xz); xx /= l; xy /= l; xz /= l;
  const yx = zy * xz - zz * xy, yy = zz * xx - zx * xz, yz = zx * xy - zy * xx;
  return new Float32Array([xx, yx, zx, 0, xy, yy, zy, 0, xz, yz, zz, 0,
                           -(xx * eye[0] + xy * eye[1] + xz * eye[2]),
                           -(yx * eye[0] + yy * eye[1] + yz * eye[2]),
                           -(zx * eye[0] + zy * eye[1] + zz * eye[2]), 1]);
}
function mul(a, b) {
  const o = new Float32Array(16);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) {
    let s = 0; for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k];
    o[c * 4 + r] = s;
  }
  return o;
}

// ---------- camera ----------
const cam = { az: 0.0, pol: 1.35, radius: 300, target: [0, 78, 11] };
const HOME = JSON.parse(JSON.stringify(cam));
function eyePos() {
  const sp = Math.sin(cam.pol), cp = Math.cos(cam.pol);
  return [cam.target[0] + cam.radius * sp * Math.sin(cam.az),
          cam.target[1] + cam.radius * cp,
          cam.target[2] + cam.radius * sp * Math.cos(cam.az)];
}

// ---------- shaders ----------
const VS_SHADE = `#version 300 es
layout(location=0) in vec3 aPos;
layout(location=1) in vec4 aNrm;
layout(location=2) in uint aSlot;
uniform mat4 uMVP; uniform mat4 uMV;
out vec3 vN; out vec3 vVP; flat out uint vSlot;
void main(){
  vec4 vp = uMV * vec4(aPos, 1.0);
  vVP = vp.xyz;
  vN = mat3(uMV) * aNrm.xyz;
  vSlot = aSlot;
  gl_Position = uMVP * vec4(aPos, 1.0);
}`;
const FS_SHADE = `#version 300 es
precision highp float;
in vec3 vN; in vec3 vVP; flat in uint vSlot;
uniform vec3 uColor; uniform uint uSelSlot; uniform int uSelActive;
uniform int uHoverActive; uniform uint uHoverSlot;
uniform float uDim; uniform int uWire; uniform float uOpacity;
out vec4 o;
void main(){
  vec3 n = normalize(vN);
  vec3 v = normalize(-vVP);
  vec3 l1 = normalize(vec3(0.45, 0.75, 0.65));
  vec3 l2 = normalize(vec3(-0.55, -0.25, 0.45));
  float d = 0.34 + 0.78 * max(dot(n, l1), 0.0) + 0.26 * max(dot(n, l2), 0.0);
  vec3 h = normalize(l1 + v);
  d += 0.18 * pow(max(dot(n, h), 0.0), 42.0);
  vec3 col = uColor * d;
  bool isSel = uSelActive == 1 && vSlot == uSelSlot;
  bool isHov = uHoverActive == 1 && vSlot == uHoverSlot;
  if (isSel) col = mix(col, vec3(1.0, 0.62, 0.18), 0.55) + vec3(0.10, 0.05, 0.0);
  else if (isHov) col *= 1.35;
  else if (uSelActive == 1 && uDim > 0.0) col *= (1.0 - uDim);
  o = vec4(col, uOpacity);
  if (uWire == 1) { /* wireframe drawn as separate LINES pass */ }
}`;
const VS_PICK = `#version 300 es
layout(location=0) in vec3 aPos;
layout(location=2) in uint aSlot;
uniform mat4 uMVP;
flat out uint vSlot;
void main(){ vSlot = aSlot; gl_Position = uMVP * vec4(aPos, 1.0); }`;
const FS_PICK = `#version 300 es
precision highp float;
flat in uint vSlot;
uniform uint uLayerBit;
out vec4 o;
void main(){
  uint id = (uLayerBit << 24) | vSlot;
  // byte 3 (the layer bit) rides in alpha: 0 = miss (the clear value),
  // 1..11 = hit + layer — the native shell's pick codec (native/src/model.rs)
  o = vec4(float(id & 255u) / 255.0, float((id >> 8) & 255u) / 255.0,
           float((id >> 16) & 255u) / 255.0, float((id >> 24) & 255u) / 255.0);
}`;

function compile(type, src) {
  const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
  return s;
}
function program(vs, fs) {
  const p = gl.createProgram();
  gl.attachShader(p, compile(gl.VERTEX_SHADER, vs));
  gl.attachShader(p, compile(gl.FRAGMENT_SHADER, fs));
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  return p;
}

// ---------- data loading ----------
async function fetchBytes(url, label, onProgress) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`${url}: HTTP ${resp.status}`);
  const total = +resp.headers.get("Content-Length") || 0;
  const reader = resp.body.getReader();
  const chunks = []; let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value); got += value.length;
    if (onProgress) onProgress(got, total);
    else statusEl.textContent = `loading ${label}… ${(got / 1048576).toFixed(1)} MB` +
      (total ? ` / ${(total / 1048576).toFixed(1)} MB` : "");
  }
  const buf = new Uint8Array(got); let off = 0;
  for (const c of chunks) { buf.set(c, off); off += c.length; }
  return buf.buffer;
}

/* Milestone 27 delivery: fetch one layer's pack, preferring the
   gzip delivery encoding named by delivery.json and decoding it
   with the platform DecompressionStream (zero dependencies). The
   decoded buffer must be exactly the canonical pack's byte count
   and begin with the ANW1 magic; any failure at any step falls
   back to the canonical pack, so a data directory without .gz
   files — or a browser without DecompressionStream — behaves
   exactly as the pre-Milestone-27 shell did. */
async function fetchPack(key, onProgress) {
  const ent = delivery && delivery.layers && delivery.layers[key];
  if (ent && ent.compressed_file && typeof DecompressionStream === "function") {
    try {
      const gz = await fetchBytes("data/" + ent.compressed_file, key,
        got => onProgress(got, ent.compressed_bytes));
      const buf = await new Response(
        new Blob([gz]).stream().pipeThrough(new DecompressionStream("gzip"))
      ).arrayBuffer();
      if (buf.byteLength !== ent.bytes)
        throw new Error(`decoded ${buf.byteLength} B, canonical is ${ent.bytes} B`);
      if (String.fromCharCode(...new Uint8Array(buf, 0, 4)) !== "ANW1")
        throw new Error("decoded buffer lacks ANW1 magic");
      return { buf, encoding: "gzip" };
    } catch (e) {
      console.warn(`ANATOMICA: compressed ${key} unusable (${e.message}); using canonical pack`);
    }
  }
  const buf = await fetchBytes("data/" + manifestData.layers[key].file, key, onProgress);
  return { buf, encoding: "identity" };
}

/* Milestone 27: progressive per-layer loading. Layers arrive in
   LOAD_ORDER; each is uploaded to the GPU the moment it lands and
   is drawable and pickable from that moment, while the rest keep
   loading. Toggling a layer that has not arrived yet records
   intent in its checkbox only: draw() and pick() skip layers with
   no GPU buffers, and the layer appears when it lands if its box
   is on. Per-layer progress rides in the layer's count span; the
   strip reports how many layers are ready. */
async function loadLayersProgressive(t0) {
  for (const key of LOAD_ORDER) {
    const st = layerState[key] = { state: "loading", pct: 0, encoding: "" };
    const cnt = $("cnt-" + key);
    try {
      const { buf, encoding } = await fetchPack(key, (got, total) => {
        st.pct = total ? Math.floor(100 * got / total) : 0;
        if (cnt) cnt.textContent = `loading… ${st.pct}%`;
      });
      layers[key] = uploadLayer(key, buf);
      layers[key].ranges = manifestData.layers[key].ranges;
      st.state = "ready"; st.pct = 100; st.encoding = encoding;
      if (!firstLayerMs) firstLayerMs = performance.now() - t0;
      const lay = manifestData.layers[key];
      if (cnt) cnt.textContent = `${lay.records} with geometry · ${(lay.faces).toLocaleString()} faces`;
      visDirty = true;
    } catch (e) {
      st.state = "error";
      if (cnt) cnt.textContent = "failed to load — " + e.message;
      console.error(e);
    }
  }
  loadMs = performance.now() - t0;
  visDirty = true;
}

function uploadLayer(name, arrayBuffer) {
  const dv = new DataView(arrayBuffer);
  if (String.fromCharCode(...new Uint8Array(arrayBuffer, 0, 4)) !== "ANW1")
    throw new Error(`${name}: bad magic`);
  const ver = dv.getUint32(4, true), nv = dv.getUint32(8, true),
        ni = dv.getUint32(12, true), nrec = dv.getUint32(16, true),
        ne = dv.getUint32(20, true);
  if (ver !== 2) throw new Error(`${name}: format version ${ver}, expected 2`);
  const off = i => Number(dv.getBigUint64(24 + 8 * i, true));
  const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
  const mk = (target, offBytes, size) => {
    const b = gl.createBuffer(); gl.bindBuffer(target, b);
    gl.bufferData(target, new Uint8Array(arrayBuffer, offBytes, size), gl.STATIC_DRAW);
    return b;
  };
  mk(gl.ARRAY_BUFFER, off(0), nv * 12);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
  mk(gl.ARRAY_BUFFER, off(1), nv * 4);
  gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 4, gl.BYTE, true, 0, 0);
  mk(gl.ARRAY_BUFFER, off(2), nv * 4);
  gl.enableVertexAttribArray(2); gl.vertexAttribIPointer(2, 1, gl.UNSIGNED_INT, 0, 0);
  const ibo = mk(gl.ELEMENT_ARRAY_BUFFER, off(3), ni * 4);
  gl.bindBuffer(gl.ARRAY_BUFFER, null);
  // edge buffer is filled via ARRAY_BUFFER; the draw code binds it as
  // the VAO's element buffer only for the wireframe pass, then restores ibo
  const eb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, eb);
  gl.bufferData(gl.ARRAY_BUFFER, new Uint8Array(arrayBuffer, off(4), ne * 4), gl.STATIC_DRAW);
  gl.bindBuffer(gl.ARRAY_BUFFER, null);
  gl.bindVertexArray(null);
  return { vao, ibo, edgeBuf: eb, vertexCount: nv, indexCount: ni, edgeIndexCount: ne, recordCount: nrec };
}

// ---------- record helpers ----------
const recRegion = r => r.region || "";
function layerVisible(key) {
  const el = $("lay-" + key);
  return el ? el.checked : DEFAULT_VISIBLE.has(key);
}
/* Per-layer opacity (Milestone 21): the layer's slider value as a
   fraction in [0.01, 1]. No slider (or an unparseable value) means
   opaque — the pre-Milestone-21 behaviour. Shading state only: the
   pick pass never calls this (asserted by verify_web.js W8). */
function layerOpacity(key) {
  const el = $("op-" + key);
  const v = el ? parseFloat(el.value) : 100;
  return isFinite(v) ? Math.min(100, Math.max(1, v)) / 100 : 1;
}
function setOpacity(key, pct) {
  const el = $("op-" + key);
  if (el) el.value = pct;
  const v = $("opv-" + key);
  if (v) v.textContent = pct + "%";
}
function regionFilter() { return $("regionSel").value; }
function recVisible(r) {
  if (!layerVisible(r.layer)) return false;
  const rf = regionFilter();
  return !rf || recRegion(r) === rf;
}
function linkedClinical(r) {
  return (r.clinical_ids || []).map(id => clinical[id]).filter(Boolean);
}
function verifyCount(r) {
  return linkedClinical(r).reduce((n, c) => n + (c.verify ? c.verify.length : 0), 0);
}

// ---------- selection / panel ----------
function esc(s) { return String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function listHTML(v) {
  if (!v || (Array.isArray(v) && !v.length)) return '<span class="empty">—</span>';
  if (Array.isArray(v)) return "<ul>" + v.map(x => `<li>${esc(x)}</li>`).join("") + "</ul>";
  return esc(v);
}
/* Recursive renderer for the clinical tranches whose schemas vary by
   system (Milestones 5, 9–15): scalars inline, lists as bullets,
   objects as small tables, depth-capped with JSON beyond. */
function valueHTML(v, depth) {
  if (v === null || v === undefined || v === "") return '<span class="empty">—</span>';
  if (typeof v !== "object") return esc(v);
  if (depth >= 3) return esc(JSON.stringify(v));
  if (Array.isArray(v)) {
    if (!v.length) return '<span class="empty">—</span>';
    if (v.every(x => typeof x !== "object" || x === null))
      return v.map(x => esc(x ?? "—")).join("; ");
    return "<ul>" + v.map(x => `<li>${valueHTML(x, depth + 1)}</li>`).join("") + "</ul>";
  }
  const rows = Object.entries(v).map(([k, x]) =>
    `<tr><th>${esc(k)}</th><td>${valueHTML(x, depth + 1)}</td></tr>`).join("");
  return `<table>${rows}</table>`;
}
function sourcesHTML(sources) {
  if (!sources || !Object.keys(sources).length) return "";
  const rows = Object.entries(sources).map(([k, v]) =>
    `<tr><th>${esc(k)}</th><td>${valueHTML(v, 1)}</td></tr>`).join("");
  return `<h3>Field sources</h3><table>${rows}</table>`;
}
function verifyHTML(c) {
  if (!c.verify || !c.verify.length) return "";
  const items = c.verify.map(v =>
    `<li>${esc(typeof v === "string" ? v : JSON.stringify(v))}</li>`).join("");
  return `<div class="verifybox"><div class="vh">Verify flags (${c.verify.length})</div><ul>${items}</ul></div>`;
}
function noteHTML(c) {
  if (!c.note) return "";
  const notes = Array.isArray(c.note) ? c.note : [c.note];
  return notes.map(n => `<p>${esc(typeof n === "string" ? n : JSON.stringify(n))}</p>`).join("");
}
function renderClinicalGeneric(c) {
  const L = [];
  const cid = c.record_id || c.id;
  L.push(`<h3>Clinical record — ${esc(cid)}</h3>`);
  if (c.sourcing_tier) L.push(`<table><tr><th>Sourcing tier</th><td>${esc(c.sourcing_tier)} (A full · B partial · C core field flagged)</td></tr></table>`);
  const skip = new Set(["record_id", "id", "name", "layer", "geometry_record_ids",
                        "geometry", "sources", "verify", "note", "sourcing_tier"]);
  const rows = Object.entries(c).filter(([k]) => !skip.has(k))
    .map(([k, v]) => `<tr><th>${esc(k)}</th><td>${valueHTML(v, 0)}</td></tr>`).join("");
  if (rows) L.push(`<table>${rows}</table>`);
  L.push(noteHTML(c));
  L.push(sourcesHTML(c.sources));
  L.push(verifyHTML(c));
  return L.join("");
}
function select(rec, focus = false) {
  selected = rec;
  document.querySelectorAll(".row.sel").forEach(e => e.classList.remove("sel"));
  if (rec) {
    const row = document.querySelector(`.row[data-key="${CSS.escape(rec.layer + ":" + rec.id)}"]`);
    if (row) { row.classList.add("sel"); row.scrollIntoView({ block: "nearest" }); }
    if (focus && rec.bbox_canonical_cm) {
      const b = rec.bbox_canonical_cm;
      cam.target = [0, 1, 2].map(i => (b.min[i] + b.max[i]) / 2);
    }
  }
  renderPanel();
}
function renderPanel() {
  const r = selected;
  if (!r) {
    panelEl.innerHTML = '<p class="empty">Select a structure — click a mesh in the view, or a row in the record list.</p>';
    return;
  }
  const L = [];
  L.push(`<h2>${esc(r.name)}</h2>`);
  L.push(`<div class="ta">${esc(LAYER_STYLE[r.layer].label)} system${r.record_kind && r.record_kind !== "inventory" ? " · " + esc(r.record_kind) + " record" : ""}</div>`);
  if (r.layer === "skeletal") {
    if (r.ta) L.push(`<div class="ta">${esc(r.ta)}</div>`);
    L.push(`<table>
      <tr><th>Division</th><td>${esc(r.division)}</td></tr>
      <tr><th>Region</th><td>${esc(r.region)}${r.subgroup ? " · " + esc(r.subgroup) : ""}</td></tr>
      <tr><th>Side</th><td>${esc(r.side)}</td></tr>
      <tr><th>Classification</th><td>${esc(r.classification)}</td></tr></table>`);
    if (r.description) L.push(`<p>${esc(r.description)}</p>`);
    L.push(`<h3>Articulations</h3>${listHTML(r.articulations)}`);
  } else if (r.layer === "muscular") {
    L.push(`<table>
      <tr><th>Side</th><td>${esc(r.side ?? "—")}</td></tr>
      <tr><th>Representation</th><td>${esc(r.representation ?? "—")}</td></tr>
      <tr><th>Region group</th><td>${esc(r.region_group ?? "—")}</td></tr>
      <tr><th>FMA concepts</th><td>${esc((r.concept_ids || []).join(", ") || "—")}</td></tr></table>`);
    const cs = linkedClinical(r);
    for (const c of cs) {
      L.push(`<h3>Clinical record — ${esc(c.record_id)}</h3><table>
        <tr><th>Region</th><td>${esc(c.region)}${c.subregion ? " · " + esc(c.subregion) : ""}</td></tr>
        <tr><th>Sourcing tier</th><td>${esc(c.sourcing_tier)} (A full · B partial · C core field flagged — Milestone 4)</td></tr></table>`);
      L.push(`<h3>Origin</h3>${listHTML(c.origin)}`);
      L.push(`<h3>Insertion</h3>${listHTML(c.insertion)}`);
      L.push(`<h3>Actions</h3>${listHTML(c.actions)}`);
      const inn = c.innervation ? `${esc(c.innervation.nerve || "—")}${c.innervation.root_values ? " (" + esc(c.innervation.root_values) + ")" : ""}` : "—";
      L.push(`<table><tr><th>Innervation</th><td>${inn}</td></tr>
        <tr><th>Arterial supply</th><td>${esc(c.arterial_supply ?? "—")}</td></tr></table>`);
      L.push(noteHTML(c));
      L.push(sourcesHTML(c.sources));
      L.push(verifyHTML(c));
    }
    if (!cs.length && r.has_geometry)
      L.push(`<div class="note">Inventory-only record: geometry and FMA identity are verified (Milestone 4), but no clinical record exists in the current tranche — origin / insertion / actions / innervation are not yet sourced for this muscle.</div>`);
  } else {
    L.push(`<table>
      <tr><th>Side</th><td>${esc(r.side ?? "—")}</td></tr>
      <tr><th>Representation</th><td>${esc(r.representation ?? "—")}</td></tr>
      <tr><th>Region</th><td>${esc(r.region ?? "—")}</td></tr>
      <tr><th>FMA concepts</th><td>${esc((r.concept_ids || []).join(", ") || "—")}</td></tr></table>`);
    const cs = linkedClinical(r);
    for (const c of cs) L.push(renderClinicalGeneric(c));
    if (!cs.length && r.has_geometry)
      L.push(`<div class="note">Inventory-only record: geometry and FMA identity are verified, but no clinical record in the current tranche links this inventory record.</div>`);
  }
  if (r.has_geometry) {
    const rng = rangeByKey.get(r.layer + ":" + r.id);
    const b = r.bbox_canonical_cm;
    L.push(`<h3>Geometry (canonical frame, cm)</h3><table>
      <tr><th>Mesh files</th><td>${rng.mesh_files}</td></tr>
      <tr><th>Vertices / faces</th><td>${(rng.vertex_count).toLocaleString()} / ${(rng.index_count / 3).toLocaleString()}</td></tr>
      <tr><th>BBox min</th><td>${b.min.map(v => v.toFixed(2)).join(", ")}</td></tr>
      <tr><th>BBox max</th><td>${b.max.map(v => v.toFixed(2)).join(", ")}</td></tr></table>`);
    if (r.cross_midline_fraction > 0.005)
      L.push(`<div class="note">Source-mesh property: ${(100 * r.cross_midline_fraction).toFixed(1)}% of this mesh's vertices lie across the mid-sagittal plane in the BodyParts3D source (measured during packing, tools/pack_geometry.py). The geometry is shown as sourced, not corrected.</div>`);
  } else {
    L.push(`<div class="note">${esc(r.geometry_note || "No geometry for this record.")}</div>`);
  }
  panelEl.innerHTML = L.join("");
}

// ---------- record list ----------
function buildList() {
  const q = $("search").value.trim().toLowerCase();
  const groups = new Map(layerOrder.map(k => [k, []]));
  for (const r of records) {
    if (q) {
      const hay = [r.name, r.id, r.ta || "", r.region || "",
                   ...linkedClinical(r).map(c => c.name || "")].join(" ").toLowerCase();
      if (!hay.includes(q)) continue;
    }
    if (!groups.has(r.layer)) groups.set(r.layer, []);
    groups.get(r.layer).push(r);
  }
  const frag = [];
  for (const layer of layerOrder) {
    const g = groups.get(layer) || [];
    frag.push(`<div class="lgroup">${LAYER_STYLE[layer].label} — ${g.length} shown</div>`);
    for (const r of g) {
      const badges = [];
      if (!r.has_geometry) {
        if (r.record_kind === "clinical-only") badges.push('<span class="badge inv">clinical-only</span>');
        else if (r.record_kind === "variant") badges.push('<span class="badge inv">variant</span>');
        else badges.push('<span class="badge nogeo">no geometry</span>');
      } else if (!r.clinical_ids || !r.clinical_ids.length) {
        badges.push('<span class="badge inv">inventory-only</span>');
      }
      const nv = verifyCount(r);
      if (nv) badges.push(`<span class="badge ver">⚠ ${nv} verify</span>`);
      frag.push(`<div class="row" data-key="${esc(r.layer + ":" + r.id)}"><span class="nm">${esc(r.name)}</span>${badges.join("")}</div>`);
    }
  }
  listEl.innerHTML = frag.join("");
  listEl.querySelectorAll(".row").forEach(row => {
    row.addEventListener("click", () => {
      const rec = byId.get(row.dataset.key);
      if (rec) select(rec, true);
    });
  });
  if (selected) {
    const row = listEl.querySelector(`.row[data-key="${CSS.escape(selected.layer + ":" + selected.id)}"]`);
    if (row) row.classList.add("sel");
  }
}

// ---------- picking ----------
function ensurePickTarget() {
  const w = gl.canvas.width, h = gl.canvas.height;
  if (pickFBO && pickTex && pickTex._w === w && pickTex._h === h) return;
  if (pickFBO) { gl.deleteFramebuffer(pickFBO); gl.deleteTexture(pickTex); gl.deleteRenderbuffer(pickDepth); }
  pickFBO = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, pickFBO);
  pickTex = gl.createTexture(); pickTex._w = w; pickTex._h = h;
  gl.bindTexture(gl.TEXTURE_2D, pickTex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, pickTex, 0);
  pickDepth = gl.createRenderbuffer(); gl.bindRenderbuffer(gl.RENDERBUFFER, pickDepth);
  gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT24, w, h);
  gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, pickDepth);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
}
function pick(x, y, mvp) {
  ensurePickTarget();
  gl.bindFramebuffer(gl.FRAMEBUFFER, pickFBO);
  gl.viewport(0, 0, gl.canvas.width, gl.canvas.height);
  gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  gl.enable(gl.DEPTH_TEST);
  gl.useProgram(pickProg);
  gl.uniformMatrix4fv(gl.getUniformLocation(pickProg, "uMVP"), false, mvp);
  const locLayer = gl.getUniformLocation(pickProg, "uLayerBit");
  for (const name of layerOrder) {
    const lay = layers[name];
    if (!lay || !layerVisible(name)) continue;
    gl.bindVertexArray(lay.vao);
    gl.uniform1ui(locLayer, LAYER_BIT[name]);
    drawLayerRanges(name, true);
  }
  const px = new Uint8Array(4);
  gl.readPixels(x, gl.canvas.height - y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  if (px[3] === 0) return null;
  const id = px[0] | (px[1] << 8) | (px[2] << 16) | (px[3] << 24);
  const bit = id >>> 24, slot = id & 0xffffff;
  const layerName = Object.keys(LAYER_BIT).find(k => LAYER_BIT[k] === bit) || null;
  if (!layerName) return null;
  const lay = layers[layerName];
  const rng = lay.ranges[slot];
  return rng ? byId.get(layerName + ":" + rng.record_id) : null;
}

// ---------- drawing ----------
function drawLayerRanges(name, forPick = false) {
  const lay = layers[name];
  const rf = regionFilter();
  if (!rf) {
    gl.drawElements(gl.TRIANGLES, lay.indexCount, gl.UNSIGNED_INT, 0);
    if (!forPick) drawCallsLastFrame++;
    return;
  }
  for (const rng of lay.ranges) {
    const rec = byId.get(name + ":" + rng.record_id);
    if (rec && recVisible(rec)) {
      gl.drawElements(gl.TRIANGLES, rng.index_count, gl.UNSIGNED_INT, rng.index_start * 4);
      if (!forPick) drawCallsLastFrame++;
    }
  }
}
function computeDrawnStats() {
  let recs = 0, meshes = 0, tris = 0;
  for (const r of records) {
    if (!r.has_geometry || !layers[r.layer] || !recVisible(r)) continue;
    const rng = rangeByKey.get(r.layer + ":" + r.id);
    recs++; meshes += rng.mesh_files; tris += rng.index_count / 3;
  }
  drawnStats = { records: recs, meshes, tris };
}
function draw() {
  const t0 = performance.now();
  const canvas = gl.canvas;
  gl.viewport(0, 0, canvas.width, canvas.height);
  gl.clearColor(0.043, 0.055, 0.075, 1);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  gl.enable(gl.DEPTH_TEST);
  const aspect = canvas.width / canvas.height;
  const proj = perspective(0.72, aspect, 0.5, 2000);
  const view = lookAt(eyePos(), cam.target, [0, 1, 0]);
  const mvp = mul(proj, view);
  drawCallsLastFrame = 0;
  gl.useProgram(shadeProg);
  gl.uniformMatrix4fv(gl.getUniformLocation(shadeProg, "uMVP"), false, mvp);
  gl.uniformMatrix4fv(gl.getUniformLocation(shadeProg, "uMV"), false, view);
  // Milestone 21: opaque layers (opacity 1) draw first, exactly as
  // before; translucent layers draw after them with alpha blending
  // and depth writes off, in layer order (manifest order runs
  // innermost -> outermost, the shell last), then the GL state is
  // restored so the pick pass and the next frame see the defaults.
  const vis = layerOrder.filter(name => layers[name] && layerVisible(name));
  for (const name of vis) if (layerOpacity(name) >= 1) drawOneLayer(name);
  const translucent = vis.filter(name => layerOpacity(name) < 1);
  if (translucent.length) {
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.depthMask(false);
    for (const name of translucent) drawOneLayer(name);
    gl.depthMask(true);
    gl.disable(gl.BLEND);
  }
  gl.bindVertexArray(null);
  if (visDirty) { computeDrawnStats(); visDirty = false; }
  drawLabels(mvp);
  frameMs = frameMs * 0.92 + (performance.now() - t0) * 0.08;
  updateStrip();
}

function drawOneLayer(name) {
  const lay = layers[name];
  const selSlot = selected && selected.has_geometry ? rangeByKey.get(selected.layer + ":" + selected.id) : null;
  gl.bindVertexArray(lay.vao);
  gl.uniform3fv(gl.getUniformLocation(shadeProg, "uColor"), LAYER_STYLE[name].color);
  const isSelLayer = selected && selected.layer === name && selSlot;
  gl.uniform1i(gl.getUniformLocation(shadeProg, "uSelActive"), isSelLayer ? 1 : 0);
  gl.uniform1ui(gl.getUniformLocation(shadeProg, "uSelSlot"), isSelLayer ? selSlot.slot : 0);
  const hovSlot = hovered && hovered.layer === name && hovered.has_geometry
    ? rangeByKey.get(hovered.layer + ":" + hovered.id) : null;
  gl.uniform1i(gl.getUniformLocation(shadeProg, "uHoverActive"), hovSlot ? 1 : 0);
  gl.uniform1ui(gl.getUniformLocation(shadeProg, "uHoverSlot"), hovSlot ? hovSlot.slot : 0);
  gl.uniform1f(gl.getUniformLocation(shadeProg, "uDim"), $("optDim").checked ? 0.62 : 0.0);
  gl.uniform1i(gl.getUniformLocation(shadeProg, "uWire"), 0);
  gl.uniform1f(gl.getUniformLocation(shadeProg, "uOpacity"), layerOpacity(name));
  drawLayerRanges(name);
  if ($("optWire").checked) {
    // wireframe overlay: same VAO positions, edge index buffer, plain dark lines
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, lay.edgeBuf);
    gl.uniform3fv(gl.getUniformLocation(shadeProg, "uColor"), [0.05, 0.05, 0.06]);
    gl.uniform1i(gl.getUniformLocation(shadeProg, "uSelActive"), 0);
    gl.uniform1i(gl.getUniformLocation(shadeProg, "uHoverActive"), 0);
    gl.uniform1f(gl.getUniformLocation(shadeProg, "uDim"), 0.0);
    if (!regionFilter()) { gl.drawElements(gl.LINES, lay.edgeIndexCount, gl.UNSIGNED_INT, 0); drawCallsLastFrame++; }
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, lay.ibo);
  }
}

// ---------- labels ----------
function drawLabels(mvp) {
  const cvs = $("labels"), ctx = cvs.getContext("2d");
  ctx.clearRect(0, 0, cvs.width, cvs.height);
  if (!$("optLabels").checked) return;
  const W = cvs.width, H = cvs.height;
  const proj = p => {
    const v = [p[0], p[1], p[2], 1];
    const o = [0, 0, 0, 0];
    for (let r = 0; r < 4; r++) for (let k = 0; k < 4; k++) o[r] += mvp[k * 4 + r] * v[k];
    if (o[3] <= 0) return null;
    return [(o[0] / o[3] * 0.5 + 0.5) * W, (0.5 - o[1] / o[3] * 0.5) * H, o[3]];
  };
  const items = [];
  for (const r of records) {
    if (!r.has_geometry || !layers[r.layer] || !recVisible(r)) continue;
    const b = r.bbox_canonical_cm;
    const c = proj([(b.min[0] + b.max[0]) / 2, (b.min[1] + b.max[1]) / 2, (b.min[2] + b.max[2]) / 2]);
    if (!c || c[0] < 0 || c[0] > W || c[1] < 0 || c[1] > H) continue;
    let size = 0;
    for (const x of [b.min[0], b.max[0]]) for (const y of [b.min[1], b.max[1]]) for (const z of [b.min[2], b.max[2]]) {
      const q = proj([x, y, z]); if (!q) continue;
      size = Math.max(size, Math.abs(q[0] - c[0]), Math.abs(q[1] - c[1]));
    }
    if (size > 26 || r === selected) items.push({ r, c, size });
  }
  items.sort((a, b) => b.size - a.size);
  ctx.font = "11px sans-serif";
  for (const it of items.slice(0, 140)) {
    const isSel = it.r === selected;
    ctx.fillStyle = isSel ? "#ffb454" : "rgba(215,222,232,0.85)";
    ctx.beginPath(); ctx.arc(it.c[0], it.c[1], isSel ? 3 : 2, 0, 7); ctx.fill();
    ctx.fillText(it.r.name, it.c[0] + 6, it.c[1] + 3);
  }
}

// ---------- integrity strip ----------
let stripTick = 0;
function updateStrip() {
  if (++stripTick % 20) return;
  const withGeo = records.filter(r => r.has_geometry).length;
  const on = layerOrder.filter(k => layerVisible(k)).length;
  const ready = layerOrder.filter(k => layers[k]).length;
  stripEl.innerHTML =
    `listed <b>${records.length}</b> records across <b>${layerOrder.length}</b> systems (${on} layers on) · ` +
    `with geometry <b>${withGeo}</b> · drawn <b>${drawnStats.records}</b> records · <b>${drawnStats.meshes}</b> meshes · ` +
    `<b>${drawnStats.tris.toLocaleString()}</b> triangles · draw calls (last frame) <b>${drawCallsLastFrame}</b> · ` +
    `frame <b>${frameMs.toFixed(1)} ms</b> · layers loaded <b>${ready}/${layerOrder.length}</b>` +
    (firstLayerMs ? ` · first layer <b>${firstLayerMs.toFixed(0)} ms</b>` : "") +
    (loadMs ? ` · full load <b>${loadMs.toFixed(0)} ms</b>` : ` · loading…`);
}

// ---------- interaction ----------
function setupControls(mvpRef) {
  const cvs = gl.canvas;
  const pointers = new Map();
  let lastPinch = 0;
  cvs.addEventListener("pointerdown", e => {
    pointers.set(e.pointerId, [e.clientX, e.clientY, e.clientX, e.clientY, performance.now()]);
    cvs.setPointerCapture(e.pointerId);
  });
  cvs.addEventListener("pointermove", e => {
    const p = pointers.get(e.pointerId);
    const rect = cvs.getBoundingClientRect();
    mouse.x = (e.clientX - rect.left) * (cvs.width / rect.width);
    mouse.y = (e.clientY - rect.top) * (cvs.height / rect.height);
    mouse.moved = true;
    if (!p) return;
    const dx = e.clientX - p[0], dy = e.clientY - p[1];
    p[0] = e.clientX; p[1] = e.clientY;
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      if (lastPinch) cam.radius = Math.min(900, Math.max(12, cam.radius * lastPinch / d));
      lastPinch = d;
      return;
    }
    if (e.shiftKey || e.buttons === 4 || e.buttons === 2) {
      // pan: move the target in the camera's right/up plane so the
      // scene follows the cursor
      const s = cam.radius * 0.0016;
      const eye = eyePos();
      const fwd = [cam.target[0] - eye[0], cam.target[1] - eye[1], cam.target[2] - eye[2]];
      const fl = Math.hypot(...fwd) || 1; const f = fwd.map(v => v / fl);
      // right = normalize(cross(f, worldUp))
      let r = [-f[2], 0, f[0]];
      const rl = Math.hypot(...r) || 1; r = r.map(v => v / rl);
      // upv = cross(right, f)
      const u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]];
      for (let i = 0; i < 3; i++) cam.target[i] += (-dx * r[i] + dy * u[i]) * s;
    } else if (e.buttons) {
      cam.az -= dx * 0.005;
      cam.pol = Math.min(3.05, Math.max(0.09, cam.pol - dy * 0.005));
    }
  });
  const up = e => {
    const p = pointers.get(e.pointerId);
    pointers.delete(e.pointerId);
    if (pointers.size < 2) lastPinch = 0;
    if (p && pointers.size === 0) {
      const moved = Math.hypot(e.clientX - p[2], e.clientY - p[3]);
      if (moved < 4 && performance.now() - p[4] < 500) {
        const rect = cvs.getBoundingClientRect();
        const hit = pick((e.clientX - rect.left) * (cvs.width / rect.width),
                         (e.clientY - rect.top) * (cvs.height / rect.height), mvpRef());
        select(hit || null);
      }
    }
  };
  cvs.addEventListener("pointerup", up);
  cvs.addEventListener("pointercancel", up);
  cvs.addEventListener("wheel", e => {
    e.preventDefault();
    cam.radius = Math.min(900, Math.max(12, cam.radius * Math.exp(e.deltaY * 0.0011)));
  }, { passive: false });
  cvs.addEventListener("contextmenu", e => e.preventDefault());
}
const mouse = { x: 0, y: 0, moved: false };

// ---------- boot ----------
async function boot() {
  const t0 = performance.now();
  const canvas = $("gl");
  gl = canvas.getContext("webgl2", { antialias: true });
  if (!gl) { statusEl.textContent = "WebGL2 is not available in this browser."; return; }
  shadeProg = program(VS_SHADE, FS_SHADE);
  pickProg = program(VS_PICK, FS_PICK);

  const [manifest, recs] = await Promise.all([
    fetch("data/manifest.json").then(r => r.json()),
    fetch("data/records.json").then(r => r.json()),
  ]);
  manifestData = manifest;
  // Milestone 27: the delivery manifest is optional by design —
  // without it (or without gzip entries in it) every layer falls
  // back to its canonical pack in fetchPack().
  delivery = await fetch("data/delivery.json")
    .then(r => (r.ok ? r.json() : null)).catch(() => null);
  layerOrder = manifest.layer_order;
  records = recs.records; clinical = recs.clinical;
  for (const r of records) byId.set(r.layer + ":" + r.id, r);
  for (const key of layerOrder)
    for (const rng of manifest.layers[key].ranges) rangeByKey.set(key + ":" + rng.record_id, rng);

  // layer toggles, generated from the manifest (skeletal + muscular
  // on by default; the opaque integumentary shell starts off so it
  // does not hide the interior systems)
  const toggles = $("layerToggles");
  for (const key of layerOrder) {
    const lay = manifest.layers[key];
    toggles.insertAdjacentHTML("beforeend",
      `<label class="chk"><input type="checkbox" id="lay-${key}"${DEFAULT_VISIBLE.has(key) ? " checked" : ""}> ${esc(lay.label)} <span class="cnt" id="cnt-${key}"></span></label>` +
      `<label class="chk op">opacity <input type="range" id="op-${key}" min="10" max="100" step="5" value="100" title="${esc(lay.label)} opacity"> <span id="opv-${key}">100%</span></label>`);
    layerState[key] = { state: "queued", pct: 0, encoding: "" };
    $(`cnt-${key}`).textContent = "queued";
  }
  // Milestone 21 presets: the glass-shell focus view (all layers on,
  // integumentary at 15% — the native shell's verified focus state)
  // and a reset back to the default layer state.
  toggles.insertAdjacentHTML("beforeend",
    `<div class="chk"><button id="btnGlass" type="button">glass shell — all layers, skin 15%</button> <button id="btnLayerReset" type="button">reset layers</button></div>`);
  $("btnGlass").addEventListener("click", () => {
    for (const key of layerOrder) {
      $("lay-" + key).checked = true;
      setOpacity(key, key === "integumentary" ? 15 : 100);
    }
    visDirty = true;
  });
  $("btnLayerReset").addEventListener("click", () => {
    for (const key of layerOrder) {
      $("lay-" + key).checked = DEFAULT_VISIBLE.has(key);
      setOpacity(key, 100);
    }
    visDirty = true;
  });
  toggles.addEventListener("input", e => {
    if (e.target.id && e.target.id.startsWith("op-")) {
      const v = $("opv-" + e.target.id.slice(3));
      if (v) v.textContent = e.target.value + "%";
    }
  });

  // region options (union over all layers, with counts)
  const counts = new Map();
  for (const r of records) { const g = recRegion(r); if (g) counts.set(g, (counts.get(g) || 0) + 1); }
  const sel = $("regionSel");
  for (const [g, n] of [...counts.entries()].sort((a, b) => b[1] - a[1]))
    sel.insertAdjacentHTML("beforeend", `<option value="${esc(g)}">${esc(g)} (${n})</option>`);

  buildList();
  const resize = () => {
    const wrap = $("viewwrap"), dpr = Math.min(devicePixelRatio || 1, 2);
    for (const c of [$("gl"), $("labels")]) {
      c.width = Math.max(2, wrap.clientWidth * dpr); c.height = Math.max(2, wrap.clientHeight * dpr);
    }
  };
  new ResizeObserver(resize).observe($("viewwrap")); resize();

  const mvpNow = () => {
    const aspect = gl.canvas.width / gl.canvas.height;
    return mul(perspective(0.72, aspect, 0.5, 2000), lookAt(eyePos(), cam.target, [0, 1, 0]));
  };
  setupControls(mvpNow);
  toggles.addEventListener("change", () => { visDirty = true; });
  for (const id of ["regionSel", "optDim"])
    $(id).addEventListener("change", () => { visDirty = true; });
  $("search").addEventListener("input", buildList);
  $("btnReset").addEventListener("click", () => Object.assign(cam, JSON.parse(JSON.stringify(HOME))));

  statusEl.textContent = "";
  const loop = () => {
    if (mouse.moved && !document.querySelector("canvas:active")) {
      mouse.moved = false;
      const hit = pick(mouse.x, mouse.y, mvpNow());
      hovered = hit;
      canvas.style.cursor = hit ? "pointer" : "grab";
      statusEl.textContent = hit ? hit.name : "";
    }
    draw();
    requestAnimationFrame(loop);
  };
  visDirty = true;
  loop();
  // Milestone 27: the render loop is already running; layers stream
  // in behind it in LOAD_ORDER and appear as each one lands.
  loadLayersProgressive(t0).catch(e => console.error(e));
}
boot().catch(e => { statusEl.textContent = "error: " + e.message; console.error(e); });
