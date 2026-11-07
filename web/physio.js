"use strict";
/* ANATOMICA web shell — Physiology mode + shared engine plumbing.
   The wasm engines run in a module Web Worker (physio-worker.js):
   physio course/hormone runs take minutes of CPU and theatre
   debriefs tens of seconds, so calling them on the main thread
   would freeze the shell; the worker keeps the UI live and lets
   this file show a running state with elapsed time. If the worker
   cannot start (or dies), calls fall back to a dynamic import of
   the same pkg on the main thread — same numbers, frozen UI.
   ANAT_WASM.call(fn, args) resolves with the export's raw string.

   Mode switching extends imaging.js's imgSetMode pattern without
   touching it: Atlas/Imaging still go through imgSetMode; the new
   modes hide the same legacy panels the same way, toggle their own
   buttons' .on class, and show one left panel + one centre wrap
   each. This file loads first of the three new mode files and owns
   the coordination; theatre.js / cases-ui.js expose lazy boots. */

// ---------------- wasm client ----------------
const anatWasm = (() => {
  let worker = null, workerDead = false, seq = 0, mainMod = null;
  const pending = new Map();
  async function callMain(fn, args) {
    if (!mainMod) {
      mainMod = await import("./pkg/anatomica_wasm.js");
      await mainMod.default();
    }
    return mainMod[fn](...args);
  }
  function ensureWorker() {
    if (worker || workerDead) return;
    try {
      worker = new Worker("physio-worker.js", { type: "module" });
      worker.onmessage = (ev) => {
        const { id, ok, result, error } = ev.data || {};
        const p = pending.get(id);
        if (!p) return;
        pending.delete(id);
        if (ok) p.res(result); else p.rej(new Error(error || "engine worker error"));
      };
      worker.onerror = () => {
        workerDead = true;
        const stuck = [...pending.values()];
        pending.clear();
        // pending calls are re-issued on the main thread rather than lost
        for (const p of stuck) p.rej(new Error("__worker_died__"));
      };
    } catch (e) {
      workerDead = true;
      worker = null;
    }
  }
  async function call(fn, args) {
    ensureWorker();
    if (!worker || workerDead) return callMain(fn, args);
    const id = ++seq;
    try {
      return await new Promise((res, rej) => {
        pending.set(id, { res, rej });
        worker.postMessage({ id, fn, args });
      });
    } catch (e) {
      if (String(e && e.message) === "__worker_died__") return callMain(fn, args);
      throw e;
    }
  }
  return { call };
})();
window.ANAT_WASM = anatWasm;

// ---------------- shared formatting ----------------
const P_HASH_KEYS = new Set(["trace_hash", "resp_hash", "hash_at_standard_end"]);
function pFmt(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v !== "number") return String(v);
  if (!isFinite(v)) return String(v);
  if (Number.isInteger(v) && Math.abs(v) < 1e15) return String(v);
  if (v !== 0 && (Math.abs(v) >= 1e7 || Math.abs(v) < 1e-4)) return v.toExponential(4);
  return String(parseFloat(v.toFixed(6)));
}
function pVerdict(line) {
  if (line.pass) return line.soft
    ? '<span class="pill soft">SOFT-PASS</span>'
    : '<span class="pill pass">PASS</span>';
  return line.soft
    ? '<span class="pill soft">FAIL (soft)</span>'
    : '<span class="pill fail">FAIL</span>';
}
// Evaluation lines in the physiology shape: resting lines carry
// value/unit/range_text; course/hormone/respiratory lines carry
// baseline/post/delta/expected/magnitude_range. One renderer, fields
// shown only when the engine sent them.
function pLinesTable(lines) {
  if (!lines || !lines.length) return "";
  const has = (k) => lines.some((l) => l[k] !== undefined && l[k] !== null);
  const L = ['<table class="dtab"><tr><th>Output</th>'];
  if (has("value")) L.push('<th class="num">Value</th><th>Unit</th><th>Range</th>');
  if (has("baseline")) L.push('<th class="num">Baseline</th>');
  if (has("post")) L.push('<th class="num">Post</th>');
  if (has("delta")) L.push('<th class="num">Delta</th>');
  if (has("expected")) L.push("<th>Expected</th>");
  if (has("magnitude_range")) L.push("<th>Magnitude range</th>");
  L.push("<th>Verdict</th><th>Source</th></tr>");
  for (const l of lines) {
    L.push(`<tr><td>${esc(l.output)}</td>`);
    if (has("value")) L.push(`<td class="num" title="${esc(String(l.value))}">${esc(pFmt(l.value))}</td><td>${esc(l.unit || "")}</td><td>${esc(l.range_text || "")}</td>`);
    if (has("baseline")) L.push(`<td class="num" title="${esc(String(l.baseline))}">${esc(pFmt(l.baseline))}</td>`);
    if (has("post")) L.push(`<td class="num" title="${esc(String(l.post))}">${esc(pFmt(l.post))}</td>`);
    if (has("delta")) L.push(`<td class="num" title="${esc(String(l.delta))}">${esc(pFmt(l.delta))}</td>`);
    if (has("expected")) L.push(`<td>${esc(l.expected || "")}</td>`);
    if (has("magnitude_range")) L.push(`<td>${l.magnitude_range ? esc(l.magnitude_range.map(pFmt).join(" .. ")) : "—"}</td>`);
    L.push(`<td>${pVerdict(l)}</td><td class="srcnote">${esc(l.source || "")}</td></tr>`);
  }
  L.push("</table>");
  return L.join("");
}
// Flat readout object (respiratory readouts, window stats) as a table.
function pReadoutTable(obj, title) {
  if (!obj || typeof obj !== "object") return "";
  const rows = Object.entries(obj)
    .filter(([k]) => !P_HASH_KEYS.has(k))
    .map(([k, v]) => `<tr><th>${esc(k)}</th><td class="num" title="${esc(typeof v === "number" ? String(v) : "")}">${esc(pFmt(v))}</td></tr>`)
    .join("");
  return (title ? `<h3>${esc(title)}</h3>` : "") + `<table class="dtab">${rows}</table>`;
}
// ---------------- canvas line chart ----------------
const P_COLORS = ["#ffb454", "#7fb069", "#6aa6d8", "#d9704f", "#b48ed8", "#e0a23c", "#5fc2b8", "#c9c9c9"];
function pDrawChart(cv, series, xLabel, yLabel) {
  const ctx = cv.getContext("2d");
  const W = cv.width, H = cv.height, padL = 58, padR = 10, padT = 10, padB = 26;
  ctx.clearRect(0, 0, W, H);
  const pts = series.flatMap((s) => s.pts);
  if (!pts.length) { ctx.fillStyle = "#8b98a9"; ctx.fillText("no samples", 10, 20); return; }
  let x0 = Math.min(...pts.map((p) => p[0])), x1 = Math.max(...pts.map((p) => p[0]));
  let y0 = Math.min(...pts.map((p) => p[1])), y1 = Math.max(...pts.map((p) => p[1]));
  if (x0 === x1) { x0 -= 1; x1 += 1; }
  if (y0 === y1) { y0 -= 1; y1 += 1; }
  const yPad = (y1 - y0) * 0.08; y0 -= yPad; y1 += yPad;
  const X = (x) => padL + ((x - x0) / (x1 - x0)) * (W - padL - padR);
  const Y = (y) => H - padB - ((y - y0) / (y1 - y0)) * (H - padT - padB);
  ctx.strokeStyle = "#2b3646"; ctx.fillStyle = "#8b98a9"; ctx.font = "10px sans-serif"; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const v = y0 + ((y1 - y0) * i) / 4, y = Y(v);
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
    ctx.fillText(pFmt(v), 4, y + 3);
  }
  for (let i = 0; i <= 4; i++) {
    const v = x0 + ((x1 - x0) * i) / 4, x = X(v);
    ctx.fillText(pFmt(v), x - 8, H - 8);
  }
  ctx.fillText(xLabel, W - padR - ctx.measureText(xLabel).width, H - 8);
  ctx.fillText(yLabel, 4, padT + 2);
  series.forEach((s, si) => {
    ctx.strokeStyle = s.color || P_COLORS[si % P_COLORS.length];
    ctx.fillStyle = ctx.strokeStyle; ctx.lineWidth = 1.6;
    ctx.beginPath();
    s.pts.forEach(([x, y], i) => { if (i === 0) ctx.moveTo(X(x), Y(y)); else ctx.lineTo(X(x), Y(y)); });
    ctx.stroke();
    for (const [x, y] of s.pts) { ctx.beginPath(); ctx.arc(X(x), Y(y), 2.2, 0, 7); ctx.fill(); }
  });
}
function pLegend(series) {
  return '<div class="ctlrow">' + series.map((s, i) =>
    `<span><span style="color:${s.color || P_COLORS[i % P_COLORS.length]}">■</span> ${esc(s.label)}</span>`).join("") + "</div>";
}
function pChartBlock(id, series, xLabel, yLabel, heading) {
  return (heading ? `<h3>${esc(heading)}</h3>` : "") + pLegend(series) +
    `<canvas class="chart" id="${id}" width="920" height="250"></canvas>`;
}
function pPaintCharts(blocks) {
  requestAnimationFrame(() => {
    for (const b of blocks) {
      const cv = document.getElementById(b.id);
      if (cv) pDrawChart(cv, b.series, b.xLabel, b.yLabel);
    }
  });
}

// ---------------- mode coordination ----------------
const ANAT_NEW = ["physio", "theatre", "cases"];
const anatCap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
let anatMode = "atlas";
function anatSetMode(m) {
  anatMode = m;
  const legacy = m === "atlas" || m === "imaging";
  if (legacy) {
    imgSetMode(m); // imaging.js's own switch: body class, buttons, panels
  } else {
    img.mode = m; // keeps imaging's keyboard handler and solo state inert
    document.body.classList.remove("mode-imaging");
    $("btnModeAtlas").classList.toggle("on", false);
    $("btnModeImaging").classList.toggle("on", false);
    $("leftAtlas").hidden = true;
    $("leftImg").hidden = true;
    $("imgwrap").hidden = true;
  }
  document.body.classList.toggle("anat-new", !legacy);
  for (const nm of ANAT_NEW) {
    $("btnMode" + anatCap(nm)).classList.toggle("on", m === nm);
    $("left" + anatCap(nm)).hidden = m !== nm;
    $(nm + "Wrap").hidden = m !== nm;
  }
  if (m === "physio" && typeof physioBoot === "function") physioBoot();
  if (m === "theatre" && typeof theatreBoot === "function") theatreBoot();
  if (m === "cases" && typeof casesBoot === "function") casesBoot();
}
// imaging.js already bound Atlas/Imaging to imgSetMode; these handlers
// run after it (registered later) and reconcile the new modes' state.
$("btnModeAtlas").addEventListener("click", () => anatSetMode("atlas"));
$("btnModeImaging").addEventListener("click", () => anatSetMode("imaging"));
$("btnModePhysio").addEventListener("click", () => anatSetMode("physio"));
$("btnModeTheatre").addEventListener("click", () => anatSetMode("theatre"));
$("btnModeCases").addEventListener("click", () => anatSetMode("cases"));

// ---------------- physiology UI ----------------
const physioState = { booted: false, running: null, results: {}, elapsed: {} };
function physioBoot() {
  if (physioState.booted) return;
  physioState.booted = true;
  $("physioKind").addEventListener("change", () => physioShow($("physioKind").value));
  $("physioRun").addEventListener("click", physioRunClicked);
  physioShow($("physioKind").value);
}
function physioRunClicked() {
  const kind = $("physioKind").value;
  if (physioState.running) return;
  physioState.running = kind;
  $("physioRun").disabled = true;
  const t0 = performance.now();
  const status = $("physioStatus");
  status.textContent = "running… 0 s";
  const timer = setInterval(() => {
    status.textContent = `running… ${((performance.now() - t0) / 1000).toFixed(0)} s`;
  }, 250);
  anatWasm.call("physio", [JSON.stringify({ kind })]).then((raw) => {
    clearInterval(timer);
    physioState.running = null;
    $("physioRun").disabled = false;
    const secs = (performance.now() - t0) / 1000;
    let data = null;
    try { data = JSON.parse(raw); } catch (e) { /* surfaced below */ }
    if (!data) {
      status.textContent = "engine returned unparseable output";
      return;
    }
    if (data.error) {
      status.textContent = "error: " + data.error;
      return;
    }
    physioState.results[kind] = data;
    physioState.elapsed[kind] = secs;
    status.textContent = `done in ${secs.toFixed(1)} s`;
    physioDoneList();
    if ($("physioKind").value === kind) physioShow(kind);
  }).catch((e) => {
    clearInterval(timer);
    physioState.running = null;
    $("physioRun").disabled = false;
    status.textContent = "error: " + e.message;
  });
}
function physioDoneList() {
  const el = $("physioDoneList");
  const names = { resting: "Resting", course: "Haemorrhage course", hormones: "Hormones", respiratory: "Respiratory" };
  const done = Object.keys(physioState.results);
  el.innerHTML = done.length
    ? "<h3>Completed runs (kept)</h3>" + done.map((k) =>
        `<div>${esc(names[k] || k)} — ${physioState.elapsed[k].toFixed(1)} s</div>`).join("")
    : "";
}
function physioShow(kind) {
  const out = $("physioOut");
  const data = physioState.results[kind];
  if (!data) {
    out.innerHTML = `<p style="color:var(--dim)">No result yet for this run. Press Run — the engine computes it live; finished results are kept and redisplayed here.</p>`;
    return;
  }
  if (kind === "resting") physioRenderResting(out, data);
  else if (kind === "course") physioRenderCourse(out, data);
  else if (kind === "hormones") physioRenderHormones(out, data);
  else if (kind === "respiratory") physioRenderRespiratory(out, data);
}
function physioRenderResting(out, data) {
  const L = [`<h2>Resting — evaluation</h2>`];
  L.push(pLinesTable(data.lines));
  if (data.outcome && Array.isArray(data.outcome.causal_chain) && data.outcome.causal_chain.length)
    L.push("<h3>Causal chain (engine)</h3>" + data.outcome.causal_chain.map((c) => `<div>${esc(c)}</div>`).join(""));
  out.innerHTML = L.join("");
}
function physioCourseSeries(set, field) {
  // field: "map" | "hr" read from each sample's window stats
  return Object.entries(set).map(([key, arm], i) => ({
    label: (arm.samples && arm.samples[0] && arm.arm) || key,
    color: P_COLORS[i % P_COLORS.length],
    pts: (arm.samples || []).map((s) => [s.minutes_after_bleed_end, s.window[field]]),
  })).filter((s) => s.pts.length);
}
function physioRenderCourse(out, data) {
  const mapS = physioCourseSeries(data.set, "map");
  const hrS = physioCourseSeries(data.set, "hr");
  const L = [`<h2>Haemorrhage course — arms overlaid</h2>`];
  L.push(pChartBlock("physioChartMap", mapS, "minutes after bleed end", "MAP (mmHg)", "Mean arterial pressure"));
  L.push(pChartBlock("physioChartHr", hrS, "minutes after bleed end", "HR (beats/min)", "Heart rate"));
  L.push("<h3>Evaluation lines</h3>");
  L.push(pLinesTable(data.lines));
  out.innerHTML = L.join("");
  pPaintCharts([
    { id: "physioChartMap", series: mapS, xLabel: "minutes after bleed end", yLabel: "MAP (mmHg)" },
    { id: "physioChartHr", series: hrS, xLabel: "minutes after bleed end", yLabel: "HR (beats/min)" },
  ]);
}
function physioRenderHormones(out, data) {
  const set = data.set || {};
  // The four hormone arms carry samples[] timed by `minutes` with
  // osmolality / ADH fields; long_course carries CourseSamples.
  const timed = ["water_load", "water_control", "deprivation", "sodium_load"]
    .filter((k) => set[k] && Array.isArray(set[k].samples));
  const mk = (field) => timed.map((k, i) => ({
    label: k, color: P_COLORS[i % P_COLORS.length],
    pts: set[k].samples.map((s) => [s.minutes, s[field]]),
  })).filter((s) => s.pts.length && s.pts.every((p) => typeof p[1] === "number"));
  const osmS = mk("osmolality_mosm_kg");
  const adhS = mk("adh_pg_ml");
  const L = [`<h2>Hormones — arms over time</h2>`];
  const blocks = [];
  if (osmS.length) {
    L.push(pChartBlock("physioChartOsm", osmS, "minutes", "mOsm/kg", "Plasma osmolality"));
    blocks.push({ id: "physioChartOsm", series: osmS, xLabel: "minutes", yLabel: "mOsm/kg" });
  }
  if (adhS.length) {
    L.push(pChartBlock("physioChartAdh", adhS, "minutes", "pg/mL", "ADH (AVP)"));
    blocks.push({ id: "physioChartAdh", series: adhS, xLabel: "minutes", yLabel: "pg/mL" });
  }
  if (set.long_course) {
    const mapS = physioCourseSeries(set.long_course, "map");
    if (mapS.length) {
      L.push(pChartBlock("physioChartLongMap", mapS, "minutes after bleed end", "MAP (mmHg)", "Long haemorrhage course — MAP"));
      blocks.push({ id: "physioChartLongMap", series: mapS, xLabel: "minutes after bleed end", yLabel: "MAP (mmHg)" });
    }
  }
  L.push("<h3>Evaluation lines</h3>");
  L.push(pLinesTable(data.lines));
  out.innerHTML = L.join("");
  pPaintCharts(blocks);
}
function physioRenderRespiratory(out, data) {
  const L = [`<h2>Respiratory</h2>`];
  // The respiratory response carries no time series — its arms report
  // baseline/post readouts — so the chart is baseline vs post PaCO2
  // per arm, drawn from the arms' own readout fields.
  const arms = data.arms || [];
  L.push(pChartBlock("physioChartResp", [], "arm", "PaCO2 (mmHg)", "PaCO2 — baseline vs post, per arm"));
  L.push(pReadoutTable(data.resting_resp, "Resting respiratory readout"));
  for (const arm of arms) {
    L.push(`<h3>Arm — ${esc(arm.kind)}</h3>`);
    const base = arm.outcome && arm.outcome.baseline, post = arm.outcome && arm.outcome.post;
    if (base && post) {
      const keys = Object.keys(post).filter((k) => !P_HASH_KEYS.has(k));
      L.push('<table class="dtab"><tr><th>Readout</th><th class="num">Baseline</th><th class="num">Post</th></tr>' +
        keys.map((k) => `<tr><th>${esc(k)}</th><td class="num">${esc(pFmt(base[k]))}</td><td class="num">${esc(pFmt(post[k]))}</td></tr>`).join("") + "</table>");
    }
    if (arm.outcome && Array.isArray(arm.outcome.causal_chain) && arm.outcome.causal_chain.length)
      L.push('<div class="srcnote">' + arm.outcome.causal_chain.map(esc).join("<br>") + "</div>");
    for (const ev of arm.evaluations || []) {
      L.push(`<h3>Evaluation — ${esc(ev.case_id)}</h3>`);
      L.push(pLinesTable(ev.lines));
    }
  }
  out.innerHTML = L.join("");
  requestAnimationFrame(() => {
    const cv = document.getElementById("physioChartResp");
    if (!cv || !arms.length) return;
    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height, padL = 58, padB = 40, padT = 10, padR = 10;
    const vals = arms.flatMap((a) => [a.outcome.baseline.paco2, a.outcome.post.paco2]);
    const y1 = Math.max(...vals) * 1.15, y0 = 0;
    const Y = (v) => H - padB - ((v - y0) / (y1 - y0)) * (H - padT - padB);
    ctx.strokeStyle = "#2b3646"; ctx.fillStyle = "#8b98a9"; ctx.font = "10px sans-serif";
    for (let i = 0; i <= 4; i++) {
      const v = (y1 * i) / 4, y = Y(v);
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
      ctx.fillText(pFmt(v), 4, y + 3);
    }
    ctx.fillText("PaCO2 (mmHg)", 4, padT + 2);
    const slot = (W - padL - padR) / arms.length, bw = Math.min(22, slot / 4);
    arms.forEach((a, i) => {
      const cx = padL + slot * i + slot / 2;
      ctx.fillStyle = P_COLORS[0];
      ctx.fillRect(cx - bw - 2, Y(a.outcome.baseline.paco2), bw, Y(y0) - Y(a.outcome.baseline.paco2));
      ctx.fillStyle = P_COLORS[3];
      ctx.fillRect(cx + 2, Y(a.outcome.post.paco2), bw, Y(y0) - Y(a.outcome.post.paco2));
      ctx.fillStyle = "#8b98a9";
      const label = a.kind.length > 16 ? a.kind.slice(0, 15) + "…" : a.kind;
      ctx.fillText(label, cx - ctx.measureText(label).width / 2, H - 24);
    });
    ctx.fillStyle = P_COLORS[0]; ctx.fillText("■ baseline", padL, H - 8);
    ctx.fillStyle = P_COLORS[3]; ctx.fillText("■ post", padL + 80, H - 8);
  });
}
