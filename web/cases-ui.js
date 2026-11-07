"use strict";
/* ANATOMICA web shell — Cases workbench UI.
   Steps through a case's presentation stages. Every number on
   screen is computed by web/cases.js (window.ANATOMICA_CASES, the
   verified port of tools/case_run.py): the workbench board beside
   the user's inputs is createRun().board(stage), criteria come
   from criteriaItems()/evalBlock()/severity(), and at the end the
   user's own committed boards and orders are assembled into an
   attempt object in the authored attempt shape and scored by
   runDebrief() — exactly like the shipped model-learner attempt,
   whose runDebrief() is rendered alongside. The UI computes
   nothing clinical itself; its only arithmetic is percent <->
   fraction conversion of the user's own inputs (validated to sum
   to 100, then normalised so the engine's sum-to-1 gate holds). */

const CS_CASE_FILES = [
  "case.acute-dyspnea.006.json", "case.appendicitis.003.json",
  "case.carpal-tunnel.004.json", "case.pe-ruleout.007.json",
  "case.post-op-jaundice.002.json", "case.ruq-pain.001.json",
  "case.ulnar-neuropathy.005.json",
];
const CS_ATTEMPT_FILES = [
  "attempt.case-acute-dyspnea-006.model-learner.json",
  "attempt.case-appendicitis-003.model-learner.json",
  "attempt.case-carpal-tunnel-004.model-learner.json",
  "attempt.case-pe-ruleout-007.model-learner.json",
  "attempt.case-post-op-002.model-learner.json",
  "attempt.case-ruq-pain-001.model-learner.json",
  "attempt.case-ulnar-neuropathy-005.model-learner.json",
];

const csState = {
  booted: false, loading: false,
  cases: [],            // {file, case}
  attempts: new Map(),  // case_id -> attempt object (unwrapped)
  params: null,
  caseId: null, run: null, caseObj: null,
  stageIdx: 0, userBoards: {}, userOrders: [], ordered: new Set(),
  finished: false,
};

function csPct(frac) {
  if (typeof frac !== "number" || !isFinite(frac)) return "—";
  return String(parseFloat((frac * 100).toFixed(2))) + "%";
}
function csHypName(run, id) {
  const h = run.case.hypotheses.find((x) => x.id === id);
  return h ? (h.name || h.label || h.id) : id;
}
// Generic renderer for case-data values (patient block, adjudication
// extras, criteria block results): scalars inline, lists as bullets,
// objects as small tables — the case files' own content, unedited.
function csVal(v, depth) {
  depth = depth || 0;
  if (v === null || v === undefined || v === "") return '<span style="color:var(--dim)">—</span>';
  if (typeof v !== "object") return esc(v);
  if (depth >= 3) return esc(JSON.stringify(v));
  if (Array.isArray(v)) {
    if (!v.length) return '<span style="color:var(--dim)">—</span>';
    if (v.every((x) => typeof x !== "object" || x === null))
      return v.map((x) => esc(x ?? "—")).join("; ");
    return "<ul>" + v.map((x) => `<li>${csVal(x, depth + 1)}</li>`).join("") + "</ul>";
  }
  const rows = Object.entries(v)
    .map(([k, x]) => `<tr><th>${esc(k)}</th><td>${csVal(x, depth + 1)}</td></tr>`).join("");
  return `<table class="dtab">${rows}</table>`;
}

async function casesBoot() {
  if (csState.booted || csState.loading) return;
  csState.loading = true;
  try {
    const [caseDocs, attemptDocs, params] = await Promise.all([
      Promise.all(CS_CASE_FILES.map((f) => fetch("data/cases/" + f).then((r) => r.json()))),
      Promise.all(CS_ATTEMPT_FILES.map((f) => fetch("data/cases/attempts/" + f).then((r) => r.json()))),
      fetch("data/cases/parameters.json").then((r) => r.json()),
    ]);
    csState.cases = CS_CASE_FILES.map((f, i) => ({ file: f, case: caseDocs[i].case }));
    for (const d of attemptDocs) csState.attempts.set(d.attempt.case_id, d.attempt);
    csState.params = params;
    const sel = $("csCaseSel");
    sel.innerHTML = csState.cases.map((c) =>
      `<option value="${esc(c.case.id)}">${esc(c.case.title || c.case.id)}</option>`).join("");
    sel.addEventListener("change", () => csStartCase(sel.value));
    csState.booted = true;
    csStartCase(csState.cases[0].case.id);
  } catch (e) {
    $("csMain").innerHTML = `<p>Failed to load case data: ${esc(e.message)}</p>`;
  } finally {
    csState.loading = false;
  }
}

function csStartCase(caseId) {
  const entry = csState.cases.find((c) => c.case.id === caseId);
  if (!entry) return;
  csState.caseId = caseId;
  csState.caseObj = entry.case;
  csState.run = window.ANATOMICA_CASES.createRun(entry.case, null, csState.params);
  csState.stageIdx = 0;
  csState.userBoards = {};
  csState.userOrders = [];
  csState.ordered = new Set();
  csState.finished = false;
  const c = entry.case, pat = c.patient || {};
  $("csCaseSel").value = caseId;
  $("csCaseMeta").innerHTML =
    `<div><b>${esc(c.id)}</b></div>` +
    (pat.age !== undefined || pat.sex ? `<div class="srcnote">Patient (case data): ${esc(pat.age ?? "")}${pat.sex ? " · " + esc(pat.sex) : ""}</div>` : "") +
    `<div class="srcnote">Hypotheses: ${c.hypotheses.length} · stages: ${csState.run.stages.join(", ")}</div>`;
  csRenderStageNav();
  csRenderStage();
}
function csRenderStageNav() {
  const run = csState.run;
  $("csStageNav").innerHTML = run.stages.map((s, i) => {
    const st = csState.caseObj.presentation_stages.find((x) => x.stage === s);
    const mark = csState.finished || i < csState.stageIdx ? "✓" : i === csState.stageIdx ? "▸" : "·";
    return `<div>${mark} Stage ${esc(s)} — ${esc(st ? st.title : "")}</div>`;
  }).join("") + (csState.finished ? `<div>✓ Adjudication revealed</div>` : "");
}
function csYieldHTML(run, id) {
  if (run.findings[id]) {
    const f = run.findings[id];
    return `<div><b>${esc(id)}</b> (finding) — ${esc(f.text)}${f.presence ? ` <span class="srcnote">presence: ${esc(f.presence)}</span>` : ""}</div>`;
  }
  if (run.labs[id]) {
    const l = run.labs[id];
    const rr = l.reference_range
      ? `reference ${esc(pFmt(l.reference_range.low))}–${esc(pFmt(l.reference_range.high))} ${esc(l.reference_range.unit || l.unit || "")}`
      : (l.reference_range_note ? esc(l.reference_range_note) : "");
    return `<div><b>${esc(id)}</b> (lab) — ${esc(l.analyte)}: ${esc(pFmt(l.value))} ${esc(l.unit || "")} <span class="srcnote">${esc(l.interpretation || "")}${rr ? " · " + rr : ""}</span></div>`;
  }
  if (run.measurements[id]) {
    const m = run.measurements[id];
    return `<div><b>${esc(id)}</b> (measurement) — ${esc(m.name)}: ${esc(pFmt(m.value))} ${esc(m.unit || "")}</div>`;
  }
  return `<div><b>${esc(id)}</b></div>`;
}
function csRenderStage() {
  const run = csState.run, c = csState.caseObj;
  const s = run.stages[csState.stageIdx];
  const stObj = c.presentation_stages.find((x) => x.stage === s);
  const L = [];
  L.push(`<h2>${esc(c.title || c.id)}</h2>`);
  L.push(`<h3>Stage ${esc(s)} of ${esc(run.stages[run.stages.length - 1])} — ${esc(stObj ? stObj.title : "")}</h3>`);
  if (stObj && stObj.narrative) L.push(`<p class="narr">${esc(stObj.narrative)}</p>`);
  if (csState.stageIdx === 0) {
    L.push(`<h3>Patient (case data)</h3>${csVal(c.patient, 0)}`);
  }
  // evidence the case data reveals at this stage
  const fHere = c.findings.filter((f) => f.stage === s);
  const lHere = c.labs.filter((l) => l.stage === s);
  const mHere = (c.measurements || []).filter((m) => m.stage === s);
  L.push(`<h3>Findings revealed at stage ${esc(s)} (${fHere.length})</h3>`);
  L.push(fHere.length ? fHere.map((f) => {
    let lr = "";
    if (f.lr) lr = `<div class="srcnote">LR — for ${esc(f.lr.for_hypothesis)}` +
      (f.lr.lr_plus !== undefined ? ` · LR+ ${esc(pFmt(f.lr.lr_plus))}` : "") +
      (f.lr.lr_minus !== undefined ? ` · LR− ${esc(pFmt(f.lr.lr_minus))}` : "") +
      (f.lr.note ? ` · ${esc(f.lr.note)}` : "") + `</div>`;
    else if (f.lr_note) lr = `<div class="srcnote">${esc(f.lr_note)}</div>`;
    return `<div style="margin:4px 0"><b>${esc(f.id)}</b> <span class="srcnote">${esc(f.kind || "")}${f.presence ? " · " + esc(f.presence) : ""}</span><br>${esc(f.text)}${lr}</div>`;
  }).join("") : '<p style="color:var(--dim)">No findings carry this stage in the case data.</p>');
  if (lHere.length) {
    L.push(`<h3>Labs with stage ${esc(s)} (${lHere.length})</h3>`);
    L.push(lHere.map((l) => csYieldHTML(run, l.id)).join(""));
  }
  if (mHere.length) {
    L.push(`<h3>Measurements with stage ${esc(s)} (${mHere.length})</h3>`);
    L.push(mHere.map((m) => csYieldHTML(run, m.id)).join(""));
  }
  // orders
  const avail = c.available_tests.filter((t) => t.available_from_stage <= s && !csState.ordered.has(t.id));
  L.push(`<h3>Order from the case's available tests</h3>`);
  L.push(avail.length ? avail.map((t) =>
    `<div class="mrow"><span class="mlab"><b>${esc(t.name)}</b> <span class="srcnote">${esc(t.id)} · ${esc(t.kind || "")} · time ${esc(pFmt(t.time_min.value))} min · cost ${esc(pFmt(t.cost_units.value))} units</span><br><span class="srcnote">${esc(t.note || "")}</span></span><button data-order="${esc(t.id)}">Order</button></div>`
  ).join("") : '<p style="color:var(--dim)">No further tests available at this stage.</p>');
  const mine = csState.userOrders.filter((o) => o.placedStage === s);
  if (mine.length) {
    L.push(`<h3>Ordered at this stage — declared yields</h3>`);
    for (const o of mine) {
      const t = run.tests[o.testId];
      L.push(`<div style="margin:6px 0"><b>${esc(t.name)}</b> (${esc(t.id)})` +
        t.yields.map((y) => csYieldHTML(run, y)).join("") + `</div>`);
    }
  }
  const earlier = csState.userOrders.filter((o) => o.placedStage < s);
  if (earlier.length)
    L.push(`<div class="srcnote">Ordered earlier: ${earlier.map((o) => `${esc(o.testId)} @ stage ${esc(o.placedStage)}`).join(", ")}</div>`);
  // board + user probabilities
  const board = run.board(s);
  const prefill = csState.stageIdx === 0 ? run.priors
    : csState.userBoards[run.stages[csState.stageIdx - 1]];
  L.push(`<h3>Probability board — stage ${esc(s)}</h3>`);
  L.push(`<table class="dtab"><tr><th>Hypothesis</th><th class="num">Prior</th><th class="num">Workbench board (engine)</th><th class="num">Your %</th></tr>` +
    run.hyps.map((h) => {
      const hyp = c.hypotheses.find((x) => x.id === h);
      return `<tr><td>${esc(csHypName(run, h))}<br><span class="srcnote">${esc(h)}${hyp && hyp.mondo ? " · " + esc(hyp.mondo) : ""}</span></td>` +
        `<td class="num">${esc(csPct(run.priors[h]))}</td>` +
        `<td class="num">${esc(csPct(board[h]))}</td>` +
        `<td class="num"><input class="pct" type="number" min="0" max="100" step="0.1" data-hyp="${esc(h)}" value="${esc(String(Math.round((prefill[h] || 0) * 1000) / 10))}"></td></tr>`;
    }).join("") + `</table>`);
  L.push(`<div class="ctlrow"><span>Sum: <b id="csSum">—</b> (must be 100)</span>` +
    `<button id="csCommit">${csState.stageIdx === run.stages.length - 1 ? "Commit final board — reveal adjudication" : "Commit board — next stage"}</button>` +
    `<span id="csBoardErr" style="color:var(--bad)"></span></div>`);
  // criteria at this stage (engine)
  L.push(`<h3>Criteria — engine evaluation at stage ${esc(s)}</h3>`);
  const items = run.criteriaItems(s);
  L.push('<table class="dtab"><tr><th>Item</th><th>State</th></tr>' +
    Object.entries(items).map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join("") + "</table>");
  for (const b of run.blocks) {
    L.push(`<div style="margin:6px 0"><b>${esc(b.id)}</b> (${esc(b.kind)})</div>${csVal(run.evalBlock(b, s), 0)}`);
  }
  if (c.adjudication && Object.prototype.hasOwnProperty.call(c.adjudication, "severity_grade")) {
    const sev = run.severity(s);
    L.push(`<div style="margin:6px 0"><b>Severity grade (engine, stage ${esc(s)})</b>: ${esc(sev[0])}</div>`);
  }
  $("csMain").innerHTML = L.join("");
  // wiring
  const inputs = [...$("csMain").querySelectorAll("input.pct")];
  const sumEl = $("csSum");
  const upd = () => {
    const sum = inputs.reduce((a, i) => a + (parseFloat(i.value) || 0), 0);
    sumEl.textContent = String(parseFloat(sum.toFixed(2)));
    sumEl.style.color = Math.abs(sum - 100) <= 0.5 ? "var(--ok)" : "var(--bad)";
  };
  inputs.forEach((i) => i.addEventListener("input", upd));
  upd();
  $("csMain").querySelectorAll("[data-order]").forEach((btn) =>
    btn.addEventListener("click", () => {
      csState.ordered.add(btn.dataset.order);
      csState.userOrders.push({ testId: btn.dataset.order, placedStage: s });
      csRenderStage();
    }));
  $("csCommit").addEventListener("click", () => {
    const probs = {};
    let sum = 0;
    for (const i of inputs) {
      const v = parseFloat(i.value);
      if (!isFinite(v) || v < 0 || v > 100) {
        $("csBoardErr").textContent = "Every hypothesis needs a number from 0 to 100.";
        return;
      }
      probs[i.dataset.hyp] = v / 100;
      sum += v;
    }
    if (Math.abs(sum - 100) > 0.5) {
      $("csBoardErr").textContent = `Probabilities sum to ${parseFloat(sum.toFixed(2))}, not 100 — adjust before advancing.`;
      return;
    }
    // normalise so the engine's sum-to-1 board gate holds exactly
    const tot = Object.values(probs).reduce((a, x) => a + x, 0);
    for (const k of Object.keys(probs)) probs[k] = probs[k] / tot;
    csState.userBoards[s] = probs;
    if (csState.stageIdx === run.stages.length - 1) {
      csState.finished = true;
      csRenderFinal();
    } else {
      csState.stageIdx++;
      csRenderStage();
    }
    csRenderStageNav();
  });
}

function csDebriefTable(deb, stages, run) {
  // per-stage comparison rows from one runDebrief() output
  return `<table class="dtab"><tr><th>Stage</th><th class="num">Brier (this board)</th><th class="num">Brier (workbench)</th><th class="num">Rank of truth (this board)</th><th class="num">Rank of truth (workbench)</th><th class="num">P(truth) (this board)</th><th class="num">P(truth) (workbench)</th></tr>` +
    deb.per_stage.map((r) =>
      `<tr><td>${esc(r.stage)}</td><td class="num">${esc(pFmt(r.learner_brier))}</td><td class="num">${esc(pFmt(r.workbench_brier))}</td><td class="num">${esc(pFmt(r.learner_rank_of_truth))}</td><td class="num">${esc(pFmt(r.workbench_rank_of_truth))}</td><td class="num">${esc(csPct(r.learner_probability_on_truth))}</td><td class="num">${esc(csPct(r.workbench_probability_on_truth))}</td></tr>`
    ).join("") + "</table>";
}
function csOrdersTable(deb) {
  if (!deb.orders.length) return "<div>None.</div>";
  return `<table class="dtab"><tr><th>Test</th><th class="num">Placed at stage</th><th class="num">Results stage</th><th>Classification (engine)</th><th>Basis</th><th class="num">Time (min)</th><th class="num">Cost (units)</th></tr>` +
    deb.orders.map((o) =>
      `<tr><td>${esc(o.test_id)}</td><td class="num">${esc(pFmt(o.placed_at_stage))}</td><td class="num">${esc(pFmt(o.results_stage))}</td><td>${esc(o.classification)}</td><td class="srcnote">${esc(o.basis)}</td><td class="num">${esc(pFmt(o.time_min))}</td><td class="num">${esc(pFmt(o.cost_units))}</td></tr>`
    ).join("") + "</table>" +
    `<div>Resource tally (engine): total time ${esc(pFmt(deb.resource_tally.total_time_min))} min · total cost ${esc(pFmt(deb.resource_tally.total_cost_units))} units<br><span class="srcnote">${esc(deb.resource_tally.status)}</span></div>`;
}
function csAnchoringTable(deb) {
  if (!deb.anchoring_events.length) return "<div>No anchoring events (engine).</div>";
  return `<table class="dtab"><tr><th>Stage</th><th>Hypothesis</th><th class="num">Board probability</th><th class="num">Workbench probability</th><th class="num">Ruled out by workbench at stage</th></tr>` +
    deb.anchoring_events.map((a) =>
      `<tr><td>${esc(pFmt(a.stage))}</td><td>${esc(a.hypothesis)}</td><td class="num">${esc(csPct(a.learner_probability))}</td><td class="num">${esc(csPct(a.workbench_probability))}</td><td class="num">${esc(pFmt(a.ruled_out_at_stage))}</td></tr>`
    ).join("") + "</table>";
}
function csRenderFinal() {
  const run = csState.run, c = csState.caseObj;
  const modelAttempt = csState.attempts.get(c.id);
  const userAttempt = {
    id: "attempt.web-ui-user",
    case_id: c.id,
    stages: run.stages.map((s) => ({
      stage: s,
      board: csState.userBoards[s],
      orders: csState.userOrders.filter((o) => o.placedStage === s).map((o) => o.testId),
    })),
  };
  let userDeb = null, modelDeb = null, err = "";
  try {
    userDeb = window.ANATOMICA_CASES.createRun(c, userAttempt, csState.params).runDebrief();
  } catch (e) { err = "User debrief failed: " + e.message; }
  if (modelAttempt) {
    try {
      modelDeb = window.ANATOMICA_CASES.createRun(c, modelAttempt, csState.params).runDebrief();
    } catch (e) { err += (err ? " · " : "") + "Model debrief failed: " + e.message; }
  }
  const adj = c.adjudication || {};
  const L = [];
  L.push(`<h2>Adjudication — ${esc(c.title || c.id)}</h2>`);
  L.push(`<table class="dtab">
    <tr><th>Adjudicated diagnosis</th><td><b>${esc(adj.diagnosis_label || "")}</b></td></tr>
    <tr><th>Diagnosis hypothesis</th><td>${esc(csHypName(run, run.truth))} (${esc(run.truth)})</td></tr>
    ${adj.mondo ? `<tr><th>MONDO</th><td>${esc(adj.mondo)}</td></tr>` : ""}
    ${adj.decided_by ? `<tr><th>Decided by</th><td>${esc(adj.decided_by)}</td></tr>` : ""}
    ${adj.note ? `<tr><th>Note</th><td>${esc(adj.note)}</td></tr>` : ""}</table>`);
  if (c.ground_truth) L.push(`<h3>Ground truth (case data)</h3>${csVal(c.ground_truth, 0)}`);
  if (adj.evidence_chain && adj.evidence_chain.length)
    L.push(`<h3>Evidence chain</h3>${csVal(adj.evidence_chain, 0)}`);
  if (adj.excluded && adj.excluded.length)
    L.push(`<h3>Excluded hypotheses (adjudication)</h3>` +
      adj.excluded.map((x) => `<div style="margin:4px 0"><b>${esc(csHypName(run, x.hypothesis))}</b> (${esc(x.hypothesis)})<br>${esc(x.basis)}</div>`).join(""));
  if (err) L.push(`<p style="color:var(--bad)">${esc(err)}</p>`);
  if (userDeb) {
    L.push(`<h3>Your attempt — per-stage scores (engine runDebrief)</h3>`);
    L.push(csDebriefTable(userDeb));
    L.push(`<h3>Your orders — evidence classification (engine)</h3>`);
    L.push(csOrdersTable(userDeb));
    L.push(`<h3>Your anchoring flags (engine)</h3>`);
    L.push(csAnchoringTable(userDeb));
    L.push(`<h3>Ruled out by workbench (engine)</h3>` +
      (Object.keys(userDeb.ruled_out_by_workbench).length
        ? Object.entries(userDeb.ruled_out_by_workbench).map(([h, s]) =>
            `<div>${esc(csHypName(run, h))} (${esc(h)}) — from stage ${esc(s)}</div>`).join("")
        : "<div>None.</div>"));
    L.push(`<h3>Criteria at final stage (engine)</h3>${csVal(userDeb.adjudicated_diagnosis.criteria_final, 0)}`);
    if (userDeb.adjudicated_diagnosis.tg18_severity_grade)
      L.push(`<div>TG18 severity grade (engine): <b>${esc(userDeb.adjudicated_diagnosis.tg18_severity_grade)}</b></div>`);
    if (userDeb.adjudicated_diagnosis.tg18_status_final)
      L.push(`<div>TG18 status, final (engine): <b>${esc(userDeb.adjudicated_diagnosis.tg18_status_final)}</b></div>`);
    L.push(`<h3>Scoring components — your attempt (engine)</h3>${csVal(userDeb.scoring_components, 0)}`);
  }
  if (modelDeb) {
    L.push(`<h3>Model learner attempt (${esc(modelAttempt.id)}) — per-stage scores (engine runDebrief)</h3>`);
    L.push(csDebriefTable(modelDeb));
    L.push(`<h3>Model learner orders — evidence classification (engine)</h3>`);
    L.push(csOrdersTable(modelDeb));
    L.push(`<h3>Model learner anchoring flags (engine)</h3>`);
    L.push(csAnchoringTable(modelDeb));
    const pz = modelDeb.pearls || {};
    for (const sec of ["reactions", "description", "analysis", "summary"])
      if (pz[sec]) L.push(`<h3>PEARLS — ${esc(sec)} (model attempt debrief text)</h3><p class="narr">${esc(pz[sec])}</p>`);
  } else {
    L.push(`<p style="color:var(--dim)">No shipped model-learner attempt file for this case.</p>`);
  }
  L.push(`<div class="ctlrow"><button id="csRestart">Restart this case</button></div>`);
  $("csMain").innerHTML = L.join("");
  $("csRestart").addEventListener("click", () => csStartCase(csState.caseId));
  $("csMain").scrollIntoView({ block: "start" });
}
