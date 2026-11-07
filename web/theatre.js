"use strict";
/* ANATOMICA web shell — Theatre mode.
   Playback: pick one of the 5 procedures and one of ITS authored
   traces, run theatre_run (wasm, in the engine worker), render the
   full debrief. A trace's procedure is read from the trace data
   itself: trace.procedure, defaulting to proc.chole.lap when the
   field is absent — the model.rs rule (the Milestone 17 traces
   predate the field and are all cholecystectomy) and the same rule
   the wasm harness uses.
   Build: pick a procedure and a case configuration (the variants /
   severities that procedure's authored traces declare), then
   perform the attempt by clicking microsteps in declared order.
   Each microstep is encoded into a trace action exactly as the
   authored traces encode it (derived from runner.rs's dispatch and
   traces 01/06): a microstep whose fulfills marker is
   "prophylaxis" is sent as a drug action (drug string taken from
   the procedure's own traces), one whose marker is a WHO phase
   ("who.*") as a checklist action, everything else — including the
   pre-clip / pre-division pause microsteps — as a plain microstep
   action. The remaining runner action kinds (identify, decision,
   recognise, control, clip_remove, energy, infuse, transfuse,
   help, note) are offered in the additional-actions panel with
   their fields taken from model.rs's Action struct. The virtual
   clock starts at t=0 and advances 60 s per action. On Finish the
   assembled Trace JSON is run through theatre_run and rendered
   with the SAME debrief renderer as playback — so clipping and
   dividing before the safety gate is demonstrated resolves through
   the engine (Stewart–Way class III on the cholecystectomy, as in
   trace-02). */

const TH_PROC_FILES = [
  "proc.carpal-release.json", "proc.lap-appendectomy.json",
  "proc.lap-cholecystectomy.json", "proc.lap-inguinal-hernia.json",
  "proc.thyroidectomy.total.json", "proc.ulnar-decompression.json",
];
const TH_TRACE_FILES = [
  "trace-01-clean.json", "trace-02-divide-before-cvs.json",
  "trace-03-variant-replaced-rha.json", "trace-04-variant-double-cystic.json",
  "trace-05-bailout-subtotal.json", "trace-06-appy-clean.json",
  "trace-07-appy-variant-retrocecal.json", "trace-08-appy-divide-unidentified.json",
  "trace-09-appy-perforated.json", "trace-10-appy-variant-pelvic.json",
  "trace-11-carpal-clean.json", "trace-12-carpal-divide-before-id.json",
  "trace-13-carpal-variant-transligamentous.json",
  "trace-14-carpal-variant-persistent-median-artery.json",
  "trace-15-carpal-incomplete-release.json", "trace-16-ulnar-clean.json",
  "trace-17-ulnar-divide-before-id.json", "trace-18-ulnar-variant-subluxating.json",
  "trace-19-ulnar-subluxation-unaddressed.json", "trace-20-ulnar-incomplete-release.json",
  "trace-21-hernia-clean.json", "trace-22-hernia-fixate-before-account.json",
  "trace-23-hernia-variant-corona-mortis.json", "trace-24-hernia-variant-sliding.json",
  "trace-25-hernia-incomplete-closure.json",
  "trace-26-thyroid-clean.json", "trace-27-thyroid-divide-before-id.json",
  "trace-28-thyroid-variant-branching.json",
  "trace-29-thyroid-parathyroid-devascularized.json",
  "trace-30-thyroid-parathyroid-unaccounted.json",
];
const TH_CASE_FIELDS = ["variant", "severity", "base_condition", "defect", "parathyroid_devascularized"];

const thState = {
  booted: false, loading: false,
  procs: [],           // {file, text, proc}
  procById: new Map(),
  traces: [],          // {file, text, trace, procId}
  drugByProc: new Map(),
  build: null,         // {procId, actions:[], performed:Set, pendingDecision:null}
};

function thProc(id) { return thState.procById.get(id); }
function thTracesOf(procId) { return thState.traces.filter((t) => t.procId === procId); }

async function theatreBoot() {
  if (thState.booted || thState.loading) return;
  thState.loading = true;
  try {
    const [procTexts, traceTexts] = await Promise.all([
      Promise.all(TH_PROC_FILES.map((f) => fetch("data/theatre/procedures/" + f).then((r) => r.text()))),
      Promise.all(TH_TRACE_FILES.map((f) => fetch("data/theatre/traces/" + f).then((r) => r.text()))),
    ]);
    thState.procs = TH_PROC_FILES.map((f, i) => {
      const proc = JSON.parse(procTexts[i]).procedure;
      return { file: f, text: procTexts[i], proc };
    });
    for (const p of thState.procs) thState.procById.set(p.proc.id, p);
    thState.traces = TH_TRACE_FILES.map((f, i) => {
      const trace = JSON.parse(traceTexts[i]).trace;
      return { file: f, text: traceTexts[i], trace, procId: trace.procedure || "proc.chole.lap" };
    });
    // drug string per procedure, from its own authored traces
    for (const t of thState.traces) {
      const d = t.trace.actions.find((a) => a.do === "drug");
      if (d && d.drug && !thState.drugByProc.has(t.procId)) thState.drugByProc.set(t.procId, d.drug);
    }
    thWire();
    thState.booted = true;
  } catch (e) {
    $("thDebrief").innerHTML = `<p>Failed to load theatre data: ${esc(e.message)}</p>`;
  } finally {
    thState.loading = false;
  }
}

function thWire() {
  const procOpts = thState.procs.map((p) =>
    `<option value="${esc(p.proc.id)}">${esc(p.proc.name)} (${esc(p.proc.id)})</option>`).join("");
  $("thProcSel").innerHTML = procOpts;
  $("thBuildProcSel").innerHTML = procOpts;
  const def = thState.procById.has("proc.chole.lap") ? "proc.chole.lap" : thState.procs[0].proc.id;
  $("thProcSel").value = def;
  $("thBuildProcSel").value = def;
  $("thBtnPlay").addEventListener("click", () => thSetSubMode("play"));
  $("thBtnBuild").addEventListener("click", () => thSetSubMode("build"));
  $("thProcSel").addEventListener("change", () => { thFillTraces(); thValidateInto($("thProcSel").value, $("thValidate")); });
  $("thTraceSel").addEventListener("change", thShowTraceInfo);
  $("thRunBtn").addEventListener("click", thRunPlayback);
  $("thBuildProcSel").addEventListener("change", () => thStartBuild($("thBuildProcSel").value));
  $("thUndoBtn").addEventListener("click", () => { const b = thState.build; if (b && b.actions.length) { const a = b.actions.pop(); if (a.do === "microstep") b.performed.delete(a.id); if (a._mid) b.performed.delete(a._mid); thRenderBuild(); } });
  $("thClearBtn").addEventListener("click", () => { if (thState.build) { thState.build.actions = []; thState.build.performed = new Set(); thState.build.pendingDecision = null; thRenderBuild(); } });
  $("thFinishBtn").addEventListener("click", thFinishBuild);
  thFillTraces();
  thValidateInto(def, $("thValidate"));
  thStartBuild(def);
}
function thSetSubMode(m) {
  $("thBtnPlay").classList.toggle("on", m === "play");
  $("thBtnBuild").classList.toggle("on", m === "build");
  $("thPlayCtl").hidden = m !== "play";
  $("thBuildCtl").hidden = m !== "build";
  $("thPlayView").hidden = m !== "play";
  $("thBuildView").hidden = m !== "build";
}
function thFillTraces() {
  const pid = $("thProcSel").value;
  const ts = thTracesOf(pid);
  $("thTraceSel").innerHTML = ts.map((t) =>
    `<option value="${esc(t.file)}">${esc(t.trace.id)} — ${esc(t.trace.name)}</option>`).join("");
  thShowTraceInfo();
}
function thShowTraceInfo() {
  const t = thState.traces.find((x) => x.file === $("thTraceSel").value);
  if (!t) { $("thTraceInfo").innerHTML = ""; return; }
  const c = t.trace.case || {};
  const bits = [`expect_verdict: ${esc(t.trace.expect_verdict)}`];
  for (const f of TH_CASE_FIELDS) if (c[f]) bits.push(`${esc(f)}: ${esc(c[f])}`);
  $("thTraceInfo").innerHTML =
    `<div class="srcnote">${bits.join(" · ")}</div>` +
    (c.note ? `<p style="font-size:12px">${esc(c.note)}</p>` : "");
}
async function thValidateInto(procId, el) {
  const p = thProc(procId);
  if (!p || !el) return;
  el.innerHTML = '<span class="srcnote">validating procedure…</span>';
  try {
    const raw = await anatWasm.call("theatre_validate", [p.text]);
    const v = JSON.parse(raw);
    if (v.error) el.innerHTML = `<span class="pill fail">validate error</span> <span class="srcnote">${esc(v.error)}</span>`;
    else if (!v.problems || !v.problems.length) el.innerHTML = '<span class="pill pass">theatre_validate: no problems</span>';
    else el.innerHTML = '<span class="pill fail">theatre_validate problems</span>' +
      v.problems.map((x) => `<div class="srcnote">${esc(x)}</div>`).join("");
  } catch (e) {
    el.innerHTML = `<span class="srcnote">validate failed: ${esc(e.message)}</span>`;
  }
}
// Run an engine call with a running state + elapsed timer on a
// status element; the button is disabled for the duration.
async function thEngineCall(statusEl, btn, fn, args) {
  const t0 = performance.now();
  if (btn) btn.disabled = true;
  statusEl.textContent = "running… 0 s";
  const timer = setInterval(() => {
    statusEl.textContent = `running… ${((performance.now() - t0) / 1000).toFixed(0)} s`;
  }, 250);
  try {
    const raw = await anatWasm.call(fn, args);
    const data = JSON.parse(raw);
    if (data.error) throw new Error(data.error);
    statusEl.textContent = `done in ${((performance.now() - t0) / 1000).toFixed(1)} s`;
    return data;
  } catch (e) {
    statusEl.textContent = "error: " + e.message;
    return null;
  } finally {
    clearInterval(timer);
    if (btn) btn.disabled = false;
  }
}
async function thRunPlayback() {
  const p = thProc($("thProcSel").value);
  const t = thState.traces.find((x) => x.file === $("thTraceSel").value);
  if (!p || !t) return;
  const d = await thEngineCall($("thStatus"), $("thRunBtn"), "theatre_run", [p.text, t.text]);
  if (d) $("thDebrief").innerHTML = thRenderDebrief(d);
}

// ---------------- the debrief renderer (playback + build) ----------------
function thBool(v) { return v === true ? "yes" : v === false ? "no" : "—"; }
function thRenderDebrief(d) {
  const L = [];
  L.push(`<h2>Debrief — ${esc(d.trace_name || d.trace_id)}</h2>`);
  L.push(`<div><span class="verdict ${d.verdict === "PASS" ? "pass" : "fail"}">${esc(d.verdict)}</span>` +
    (d.fail_reason ? ` <span>— ${esc(d.fail_reason)}</span>` : "") + `</div>`);
  L.push(`<table class="dtab">
    <tr><th>Trace</th><td>${esc(d.trace_id)}</td><th>Procedure</th><td>${esc(d.procedure_id)}</td></tr>
    <tr><th>Case variant</th><td>${esc(d.case_variant ?? "—")}</td><th>Validity</th><td>${esc(d.validity_label)}</td></tr>
    <tr><th>Duration</th><td>${esc(pFmt(d.duration_s))} s</td><th>Failed at</th><td>${d.failed_at_s == null ? "—" : esc(pFmt(d.failed_at_s)) + " s"}</td></tr>
    <tr><th>Engine beats</th><td>${esc(pFmt(d.engine_beats))}</td><th>Trace hash</th><td>${esc(d.engine_trace_hash)}</td></tr>
    <tr><th>Conservation error</th><td colspan="3">${esc(pFmt(d.engine_conservation_error_ml))} mL</td></tr></table>`);
  const c = d.checklist || {};
  L.push(`<h3>Checklist — ${esc(pFmt(c.pct))}% (${esc(pFmt(c.completed))}/${esc(pFmt(c.required))})</h3>`);
  if (c.missing && c.missing.length)
    L.push(`<div>Missing required microsteps: ${c.missing.map(esc).join(", ")}</div>`);
  else L.push(`<div>No required microsteps missing.</div>`);
  const sg = d.safety_gate || {};
  L.push(`<h3>Safety gate — ${esc(pFmt(sg.points))}/${esc(pFmt(sg.max))} points</h3>
    <table class="dtab">
    <tr><th>Criteria before first clip/divide</th><td>${esc(pFmt(sg.criteria_before_first_clipdiv))}</td></tr>
    <tr><th>Pause before first clip</th><td>${thBool(sg.pause_before_first_clip)}</td></tr>
    ${sg.note ? `<tr><th>Note</th><td>${esc(sg.note)}</td></tr>` : ""}</table>`);
  const pr = d.process || {};
  L.push(`<h3>Process — ${esc(pFmt(pr.points))}/${esc(pFmt(pr.max))} points</h3>
    <table class="dtab">
    <tr><th>Sign in</th><td>${thBool(pr.sign_in)}</td><th>Time out</th><td>${thBool(pr.time_out)}</td><th>Sign out</th><td>${thBool(pr.sign_out)}</td></tr>
    <tr><th>Prophylaxis in window</th><td>${thBool(pr.prophylaxis_in_window)}</td><th>Planning complete</th><td>${thBool(pr.planning_complete)}</td><td></td><td></td></tr></table>`);
  const ph = d.physiology || {};
  L.push(`<h3>Physiology — ${esc(pFmt(ph.points))}/${esc(pFmt(ph.max))} points</h3>
    <table class="dtab">
    <tr><th>Time points</th><td>${esc(pFmt(ph.time_points))}</td><th>Nadir points</th><td>${esc(pFmt(ph.nadir_points))}</td><th>Loss points</th><td>${esc(pFmt(ph.loss_points))}</td></tr>
    <tr><th>MAP baseline</th><td>${esc(pFmt(ph.map_baseline_mmhg))} mmHg</td><th>MAP nadir</th><td>${esc(pFmt(ph.map_nadir_mmhg))} mmHg</td><th>Seconds below threshold</th><td>${esc(pFmt(ph.seconds_below_threshold))}</td></tr>
    <tr><th>Blood loss</th><td>${esc(pFmt(ph.blood_loss_ml))} mL</td><th>Loss crosscheck</th><td>${esc(pFmt(ph.blood_loss_crosscheck_ml))} mL</td><td></td><td></td></tr>
    <tr><th>Infused</th><td>${esc(pFmt(ph.infused_ml))} mL</td><th>Transfused</th><td>${esc(pFmt(ph.transfused_ml))} mL</td><td></td><td></td></tr></table>`);
  if (d.management) {
    const m = d.management;
    L.push(`<h3>Management — ${esc(pFmt(m.points))}/${esc(pFmt(m.max))} points</h3>
      <table class="dtab"><tr><th>Recognised</th><td>${esc(pFmt(m.recognised))}</td><th>Control</th><td>${esc(pFmt(m.control))}</td><th>Escalation</th><td>${esc(pFmt(m.escalation))}</td><th>Plan</th><td>${esc(pFmt(m.plan))}</td></tr></table>`);
  } else {
    L.push(`<h3>Management</h3><div>n/a (no complication)</div>`);
  }
  L.push(`<h3>Errors (${(d.errors || []).length})</h3>`);
  if ((d.errors || []).length)
    L.push('<table class="dtab"><tr><th>t (s)</th><th>Error</th><th>Detail</th></tr>' +
      d.errors.map((e) => `<tr><td>${esc(pFmt(e.t_s))}</td><td>${esc(e.id)}</td><td>${esc(e.detail)}</td></tr>`).join("") + "</table>");
  else L.push("<div>None recorded.</div>");
  L.push(`<h3>Complications (${(d.complications || []).length})</h3>`);
  if ((d.complications || []).length)
    L.push('<table class="dtab"><tr><th>Kind</th><th>Onset (s)</th><th>Detail</th><th>Resolved structure</th><th>Stewart–Way</th><th>Recognised</th><th>Controlled (s)</th><th>Loss (mL)</th></tr>' +
      d.complications.map((x) => `<tr><td>${esc(x.kind)}</td><td>${esc(pFmt(x.t_onset_s))}</td><td>${esc(x.detail)}</td><td>${esc(x.resolved_structure ?? "—")}</td><td>${esc(x.stewart_way_class ?? "—")}</td><td>${thBool(x.recognised)}</td><td>${x.controlled_s == null ? "—" : esc(pFmt(x.controlled_s))}</td><td>${x.loss_ml == null ? "—" : esc(pFmt(x.loss_ml))}</td></tr>`).join("") + "</table>");
  else L.push("<div>None computed.</div>");
  L.push(`<h3>Decisions (${(d.decisions || []).length})</h3>`);
  if ((d.decisions || []).length)
    L.push('<table class="dtab"><tr><th>t (s)</th><th>Decision point</th><th>Choice</th></tr>' +
      d.decisions.map((x) => `<tr><td>${esc(pFmt(x.t_s))}</td><td>${esc(x.id)}</td><td>${esc(x.choice)}</td></tr>`).join("") + "</table>");
  else L.push("<div>None recorded.</div>");
  const pb = d.debrief || {};
  for (const sec of ["description", "plus", "delta", "directive", "summary"]) {
    if (pb[sec] && pb[sec].length)
      L.push(`<h3>PEARLS — ${esc(sec)}</h3>` + pb[sec].map((x) => `<div>${esc(x)}</div>`).join(""));
  }
  L.push(`<h3>Event log (${(d.event_log || []).length})</h3><div class="logbox">` +
    (d.event_log || []).map((e) => `<div><span class="srcnote">[t=${esc(pFmt(e.t_s))}s · ${esc(e.kind)}]</span> ${esc(e.text)}</div>`).join("") + "</div>");
  L.push(`<details><summary style="cursor:pointer;color:var(--dim)">Full debrief JSON (engine output, unabridged)</summary><pre class="jsonbox">${esc(JSON.stringify(d, null, 1))}</pre></details>`);
  return L.join("");
}

// ---------------- build mode ----------------
function thEncodeMicrostep(procId, m) {
  if (m.fulfills === "prophylaxis") {
    const drug = thState.drugByProc.get(procId);
    return drug ? { do: "drug", drug } : { do: "microstep", id: m.id };
  }
  if (m.fulfills && m.fulfills.indexOf("who.") === 0) return { do: "checklist", phase: m.fulfills };
  return { do: "microstep", id: m.id };
}
function thEncodeNote(procId, m) {
  const a = thEncodeMicrostep(procId, m);
  if (a.do === "drug") return `as drug · ${a.drug} (fulfils ${m.id})`;
  if (a.do === "checklist") return `as checklist · ${a.phase} (fulfils ${m.id})`;
  return "as microstep";
}
function thStartBuild(procId) {
  thState.build = { procId, actions: [], performed: new Set(), pendingDecision: null };
  thBuildCaseControls(procId);
  thValidateInto(procId, $("thBuildValidate"));
  thRenderBuild();
}
function thCaseOfBuild() {
  // current case-field selections, null-normalised
  const b = thState.build, out = {};
  for (const f of TH_CASE_FIELDS) {
    const sel = document.getElementById("thCase-" + f);
    out[f] = sel ? (sel.value || null) : null;
  }
  return out;
}
function thBuildCaseControls(procId) {
  const p = thProc(procId).proc;
  const traces = thTracesOf(procId);
  const L = [];
  for (const f of TH_CASE_FIELDS) {
    let options = null;
    if (f === "variant") {
      const fromTraces = new Set(traces.map((t) => (t.trace.case || {}).variant || null));
      const vals = p.variants.map((v) => v.id);
      for (const v of fromTraces) if (v && !vals.includes(v)) vals.push(v);
      if (!vals.length && !fromTraces.has(null)) continue;
      options = [{ v: "", label: "— none / standard —" }]
        .concat(vals.map((id) => {
          const vd = p.variants.find((x) => x.id === id);
          return { v: id, label: vd ? `${vd.name} (${id})` : id };
        }));
      if (!fromTraces.has(null)) options.shift();
    } else {
      const vals = [...new Set(traces.map((t) => (t.trace.case || {})[f]).filter(Boolean))];
      if (!vals.length) continue;
      options = [{ v: "", label: "— not specified —" }].concat(vals.map((v) => ({ v, label: v })));
    }
    L.push(`<label>${esc(f)}<br><select id="thCase-${esc(f)}">${options.map((o) =>
      `<option value="${esc(o.v)}">${esc(o.label)}</option>`).join("")}</select></label>`);
  }
  $("thBuildCase").innerHTML = L.join("") + '<div id="thCaseNote" style="margin-top:6px"></div>';
  $("thBuildCase").querySelectorAll("select").forEach((s) =>
    s.addEventListener("change", thShowBuildCaseNote));
  thShowBuildCaseNote();
}
function thShowBuildCaseNote() {
  const el = $("thCaseNote");
  if (!el || !thState.build) return;
  const sel = thCaseOfBuild();
  const match = thTracesOf(thState.build.procId).find((t) => {
    const c = t.trace.case || {};
    return TH_CASE_FIELDS.every((f) => (c[f] || null) === (sel[f] || null));
  });
  el.innerHTML = match && match.trace.case && match.trace.case.note
    ? `<div class="srcnote">Matches authored trace ${esc(match.trace.id)}:</div><p style="font-size:12px">${esc(match.trace.case.note)}</p>`
    : "";
}
function thAddAction(a, mid) {
  const b = thState.build;
  a.t_s = b.actions.length * 60;
  if (mid) a._mid = mid;
  b.actions.push(a);
  if (mid) b.performed.add(mid);
  thRenderBuild();
}
function thDescribeAction(a) {
  const parts = [a.do];
  if (a.id) parts.push(a.id);
  if (a.drug) parts.push(a.drug);
  if (a.phase) parts.push(a.phase);
  if (a.choice) parts.push("→ " + a.choice);
  if (a.structure) parts.push(a.structure);
  if (a.complication) parts.push(a.complication);
  if (a.label) parts.push(a.label);
  if (a.text) parts.push(a.text);
  if (a.volume_ml != null) parts.push(pFmt(a.volume_ml) + " mL");
  if (a.product) parts.push(a.product);
  if (a.rate_ml_s != null) parts.push("at " + pFmt(a.rate_ml_s) + " mL/s");
  return parts.join(" · ");
}
function thRenderBuild() {
  const b = thState.build;
  if (!b) return;
  const p = thProc(b.procId).proc;
  $("thClock").textContent =
    `virtual clock: next action at t=${b.actions.length * 60} s · ${b.actions.length} action(s)`;
  // actions list
  $("thActionsList").innerHTML = b.actions.length
    ? b.actions.map((a, i) => `<div><span class="srcnote">#${i + 1} [t=${esc(pFmt(a.t_s))}s]</span> ${esc(thDescribeAction(a))}</div>`).join("")
    : '<p style="color:var(--dim)">None yet.</p>';
  // decision prompt
  const pd = b.pendingDecision;
  $("thDecisionPrompt").innerHTML = pd
    ? `<div class="verifybox" style="border:1px solid var(--warn);border-radius:4px;padding:8px;margin:8px 0">
         <b>${esc(pd.id)}</b> — ${esc(pd.question)}<div class="ctlrow">` +
       pd.choices.map((ch) => `<button data-dpchoice="${esc(ch.id)}">${esc(ch.label)} (${esc(ch.id)})</button>`).join("") +
       `<button data-dpdismiss="1">Decide later</button></div></div>`
    : "";
  if (pd) {
    $("thDecisionPrompt").querySelectorAll("[data-dpchoice]").forEach((btn) =>
      btn.addEventListener("click", () => {
        thAddAction({ do: "decision", id: pd.id, choice: btn.dataset.dpchoice });
        b.pendingDecision = null;
        thRenderBuild();
      }));
    const dis = $("thDecisionPrompt").querySelector("[data-dpdismiss]");
    if (dis) dis.addEventListener("click", () => { b.pendingDecision = null; thRenderBuild(); });
  }
  // microstep list in declared order
  const L = [];
  for (const ph of p.phases) {
    L.push(`<h3>${esc(ph.id)} — ${esc(ph.name)}</h3>`);
    for (const st of ph.steps) {
      L.push(`<div class="lgroup">${esc(st.id)} — ${esc(st.name)}</div>`);
      for (const m of st.microsteps) {
        const done = b.performed.has(m.id);
        const badges = [];
        if (m.required) badges.push('<span class="badge">required</span>');
        if (m.critical) badges.push('<span class="badge ver">critical</span>');
        if (m.demonstrates) badges.push(`<span class="badge">demonstrates ${esc(m.demonstrates)}</span>`);
        L.push(`<div class="mrow${done ? " done" : ""}">
          <span class="mid">${esc(m.id)}</span>
          <span class="mlab">${esc(m.label)}<br><span class="srcnote">${esc(m.verb)} · ${esc(thEncodeNote(b.procId, m))}${m.targets && m.targets.length ? " · targets: " + esc(m.targets.join(", ")) : ""}</span></span>
          ${badges.join("")}
          <button data-perform="${esc(m.id)}" ${done ? "disabled" : ""}>${done ? "done" : "Perform"}</button>
        </div>`);
      }
    }
  }
  $("thPhases").innerHTML = L.join("");
  $("thPhases").querySelectorAll("[data-perform]").forEach((btn) =>
    btn.addEventListener("click", () => thPerformMicrostep(btn.dataset.perform)));
  thRenderExtra(p);
}
function thPerformMicrostep(mid) {
  const b = thState.build;
  const p = thProc(b.procId).proc;
  let m = null;
  for (const ph of p.phases) for (const st of ph.steps) for (const x of st.microsteps)
    if (x.id === mid) m = x;
  if (!m || b.performed.has(mid)) return;
  thAddAction(thEncodeMicrostep(b.procId, m), mid);
  if (m.anchors_decision) {
    const dp = p.decision_points.find((d) => d.id === m.anchors_decision);
    if (dp) { b.pendingDecision = dp; thRenderBuild(); }
  }
}
function thRenderExtra(p) {
  const structs = p.structures.map((s) => `<option value="${esc(s.id)}">${esc(s.id)}</option>`).join("");
  const dps = p.decision_points.map((d) => `<option value="${esc(d.id)}">${esc(d.id)} — ${esc(d.question)}</option>`).join("");
  const firstDp = p.decision_points[0];
  const choices = firstDp ? firstDp.choices.map((c) => `<option value="${esc(c.id)}">${esc(c.label)} (${esc(c.id)})</option>`).join("") : "";
  $("thExtra").innerHTML = `
  <div class="ctlrow"><span style="width:110px">identify</span>
    <select id="thXIdentify">${structs}</select><button id="thXIdentifyBtn">Add</button></div>
  <div class="ctlrow"><span style="width:110px">decision</span>
    <select id="thXDp">${dps}</select><select id="thXChoice">${choices}</select><button id="thXDecisionBtn">Add</button></div>
  <div class="ctlrow"><span style="width:110px">recognise</span>
    <input type="text" id="thXRecognise" placeholder="complication kind (as the engine names it)"><button id="thXRecogniseBtn">Add</button></div>
  <div class="ctlrow"><span style="width:110px">control</span>
    <select id="thXControl">${structs}</select><button id="thXControlBtn">Add</button></div>
  <div class="ctlrow"><span style="width:110px">clip_remove</span>
    <select id="thXClipRemove">${structs}</select><button id="thXClipRemoveBtn">Add</button></div>
  <div class="ctlrow"><span style="width:110px">energy</span>
    <select id="thXEnergy">${structs}</select><button id="thXEnergyBtn">Add</button></div>
  <div class="ctlrow"><span style="width:110px">infuse</span>
    <input type="text" id="thXInfuseLabel" placeholder="label">
    <input type="number" id="thXInfuseVol" placeholder="volume mL" style="width:100px">
    <input type="number" id="thXInfuseRate" placeholder="rate mL/s" style="width:100px"><button id="thXInfuseBtn">Add</button></div>
  <div class="ctlrow"><span style="width:110px">transfuse</span>
    <input type="text" id="thXTransLabel" placeholder="label">
    <input type="number" id="thXTransVol" placeholder="volume mL" style="width:100px">
    <input type="number" id="thXTransRate" placeholder="rate mL/s" style="width:100px">
    <input type="text" id="thXTransProduct" placeholder="product (optional)"><button id="thXTransBtn">Add</button></div>
  <div class="ctlrow"><span style="width:110px">help</span>
    <input type="text" id="thXHelp" placeholder="label (who is called)"><button id="thXHelpBtn">Add</button></div>
  <div class="ctlrow"><span style="width:110px">note</span>
    <input type="text" id="thXNote" placeholder="text" style="flex:1"><button id="thXNoteBtn">Add</button></div>`;
  const on = (id, fn) => { const el = $(id); if (el) el.addEventListener("click", fn); };
  on("thXIdentifyBtn", () => thAddAction({ do: "identify", structure: $("thXIdentify").value }));
  on("thXDecisionBtn", () => thAddAction({ do: "decision", id: $("thXDp").value, choice: $("thXChoice").value }));
  on("thXRecogniseBtn", () => { const v = $("thXRecognise").value.trim(); if (v) thAddAction({ do: "recognise", complication: v }); });
  on("thXControlBtn", () => thAddAction({ do: "control", structure: $("thXControl").value }));
  on("thXClipRemoveBtn", () => thAddAction({ do: "clip_remove", structure: $("thXClipRemove").value }));
  on("thXEnergyBtn", () => thAddAction({ do: "energy", structure: $("thXEnergy").value }));
  on("thXInfuseBtn", () => {
    const a = { do: "infuse", volume_ml: parseFloat($("thXInfuseVol").value), rate_ml_s: parseFloat($("thXInfuseRate").value) };
    const lab = $("thXInfuseLabel").value.trim(); if (lab) a.label = lab;
    if (isFinite(a.volume_ml) && isFinite(a.rate_ml_s)) thAddAction(a);
  });
  on("thXTransBtn", () => {
    const a = { do: "transfuse", volume_ml: parseFloat($("thXTransVol").value), rate_ml_s: parseFloat($("thXTransRate").value) };
    const lab = $("thXTransLabel").value.trim(); if (lab) a.label = lab;
    const prod = $("thXTransProduct").value.trim(); if (prod) a.product = prod;
    if (isFinite(a.volume_ml) && isFinite(a.rate_ml_s)) thAddAction(a);
  });
  on("thXHelpBtn", () => { const v = $("thXHelp").value.trim(); if (v) thAddAction({ do: "help", label: v }); });
  on("thXNoteBtn", () => { const v = $("thXNote").value; if (v) thAddAction({ do: "note", text: v }); });
  $("thXDp").addEventListener("change", () => {
    const dp = p.decision_points.find((d) => d.id === $("thXDp").value);
    $("thXChoice").innerHTML = dp
      ? dp.choices.map((c) => `<option value="${esc(c.id)}">${esc(c.label)} (${esc(c.id)})</option>`).join("") : "";
  });
}
async function thFinishBuild() {
  const b = thState.build;
  if (!b) return;
  const p = thProc(b.procId);
  const sel = thCaseOfBuild();
  const caseObj = { variant: sel.variant };
  for (const f of ["severity", "base_condition", "defect", "parathyroid_devascularized"])
    if (sel[f]) caseObj[f] = sel[f];
  const trace = {
    id: "build-attempt",
    name: "Built attempt — " + p.proc.name,
    expect_verdict: "pass",
    case: caseObj,
    actions: b.actions.map((a) => { const { _mid, ...rest } = a; return rest; }),
  };
  if (b.procId !== "proc.chole.lap") trace.procedure = b.procId;
  const traceText = JSON.stringify({ trace }, null, 1);
  const d = await thEngineCall($("thBuildStatus"), $("thFinishBtn"), "theatre_run", [p.text, traceText]);
  if (d) {
    $("thBuildDebrief").innerHTML =
      `<details><summary style="cursor:pointer;color:var(--dim)">Assembled trace JSON (sent to theatre_run)</summary><pre class="jsonbox">${esc(traceText)}</pre></details>` +
      thRenderDebrief(d);
    $("thBuildDebrief").scrollIntoView({ block: "start" });
  }
}
