#!/usr/bin/env node
// ANATOMICA wasm verification harness.
//
// Proves wasm == native for the theatre runner (all traces, deep
// exact comparison of the whole debrief object) and for the
// physiology engine (resting / course / hormones / respiratory),
// comparing the wasm outputs against the native CLI's printed
// output captured under wasm/harness/native/.
//
// Usage:
//   node verify.mjs dump-theatre        # wasm theatre_run (all traces) + theatre_validate (all procedures)
//   node verify.mjs dump-resting        # wasm physio resting (+ error-path checks)
//   node verify.mjs dump-course         # wasm physio course
//   node verify.mjs dump-hormones       # wasm physio hormones
//   node verify.mjs dump-respiratory    # wasm physio respiratory (all 13 arms)
//   node verify.mjs compare             # compare all dumps vs native captures
//
// Dumps land in wasm/harness/out/ as the RAW strings returned by the
// wasm exports (u64 trace hashes keep their full precision there;
// JSON.parse would round them through f64).

import { readFileSync, writeFileSync, readdirSync, existsSync, mkdirSync } from 'node:fs';

const ROOT = new URL('../../', import.meta.url);
const OUT = new URL('./out/', import.meta.url);
mkdirSync(OUT, { recursive: true });
const read = (rel) => readFileSync(new URL(rel, ROOT), 'utf8');
const writeOut = (name, text) => writeFileSync(new URL(name, OUT), text);

let wasm = null;
async function loadWasm() {
  if (wasm) return wasm;
  const mod = await import('../../web/pkg/anatomica_wasm.js');
  await mod.default({ module_or_path: readFileSync(new URL('web/pkg/anatomica_wasm_bg.wasm', ROOT)) });
  wasm = mod;
  return wasm;
}

const procIdToFile = () => {
  const map = {};
  for (const f of readdirSync(new URL('theatre/procedures/', ROOT)).filter((x) => x.endsWith('.json')).sort()) {
    const id = JSON.parse(read(`theatre/procedures/${f}`)).procedure.id;
    map[id] = f;
  }
  return map;
};

// ---------------------------------------------------------------- dumps

async function dumpTheatre() {
  const { theatre_run, theatre_validate } = await loadWasm();
  const id2file = procIdToFile();
  const dir = new URL('./theatre/', OUT);
  mkdirSync(dir, { recursive: true });
  const traces = readdirSync(new URL('theatre/traces/', ROOT)).filter((x) => x.endsWith('.json')).sort();
  for (const t of traces) {
    const traceText = read(`theatre/traces/${t}`);
    const trace = JSON.parse(traceText).trace;
    const procFile = id2file[trace.procedure ?? 'proc.chole.lap'];
    const t0 = Date.now();
    const out = theatre_run(read(`theatre/procedures/${procFile}`), traceText);
    writeFileSync(new URL(t.replace(/\.json$/, '.json'), dir), out);
    console.log(`theatre_run ${t} (${procFile}) ${(Date.now() - t0) / 1000}s bytes=${out.length} ${out.startsWith('{"error"') ? out : ''}`);
  }
  const validates = {};
  for (const f of Object.values(id2file).sort()) {
    validates[f] = JSON.parse(theatre_validate(read(`theatre/procedures/${f}`)));
  }
  writeOut('theatre-validates.json', JSON.stringify(validates, null, 2));
  console.log('theatre_validate:', JSON.stringify(validates));
}

async function dumpPhysio(kind, file) {
  const { physio } = await loadWasm();
  const t0 = Date.now();
  const out = physio(JSON.stringify({ kind }));
  writeOut(file, out);
  const parsed = JSON.parse(out);
  console.log(`physio ${kind}: ${(Date.now() - t0) / 1000}s bytes=${out.length} ${parsed.error ? 'ERROR ' + parsed.error : 'ok'}`);
  return out;
}

async function dumpResting() {
  const { physio } = await loadWasm();
  const meta = {
    bogus_kind: physio('{"kind":"bogus"}'),
    malformed_json: physio('not json'),
    missing_kind: physio('{}'),
    theatre_run_bad_procedure: null,
    theatre_validate_bad: null,
  };
  const { theatre_run, theatre_validate } = await loadWasm();
  meta.theatre_run_bad_procedure = theatre_run('{}', '{}');
  meta.theatre_validate_bad = theatre_validate('{}');
  writeOut('meta.json', JSON.stringify(meta, null, 2));
  console.log('error paths:', JSON.stringify(meta));
  await dumpPhysio('resting', 'wasm-resting.json');
}

// ---------------------------------------------------------------- compare helpers

const f0 = (v) => v.toFixed(0);
const f1 = (v) => v.toFixed(1);
const f2 = (v) => v.toFixed(2);
const f3 = (v) => v.toFixed(3);
const fSigned2 = (v) => (v >= 0 ? '+' : '') + v.toFixed(2);
const hex64 = (b) => '0x' + b.toString(16).padStart(16, '0');
function extractAll(text, key) {
  const re = new RegExp(`"${key}":(\\d+)`, 'g');
  return [...text.matchAll(re)].map((m) => BigInt(m[1]));
}
// Rust f64 Display for the plain decimals used in parameters.json.
const rustNum = (v) => String(v);

function deepCompare(a, b, path, acc) {
  if (typeof a !== typeof b) { acc.mismatches.push(`${path}: type native=${typeof a} wasm=${typeof b}`); return; }
  if (a === null || b === null) {
    acc.fields++;
    if (a !== b) acc.mismatches.push(`${path}: native=${JSON.stringify(a)} wasm=${JSON.stringify(b)}`);
    return;
  }
  if (Array.isArray(a)) {
    if (!Array.isArray(b) || a.length !== b.length) { acc.mismatches.push(`${path}: array length native=${a.length} wasm=${Array.isArray(b) ? b.length : 'n/a'}`); return; }
    a.forEach((x, i) => deepCompare(x, b[i], `${path}[${i}]`, acc));
    return;
  }
  if (typeof a === 'object') {
    const ka = Object.keys(a).sort();
    const kb = Object.keys(b).sort();
    if (JSON.stringify(ka) !== JSON.stringify(kb)) acc.mismatches.push(`${path}: keys native=[${ka}] wasm=[${kb}]`);
    for (const k of ka) if (k in b) deepCompare(a[k], b[k], `${path}.${k}`, acc);
    return;
  }
  acc.fields++;
  if (a !== b) acc.mismatches.push(`${path}: native=${JSON.stringify(a)} wasm=${JSON.stringify(b)}`);
}

const verdictRun = (line) => (line.pass ? 'PASS' : line.soft ? 'SOFT-FAIL (disclosed, not gating)' : 'FAIL');
const verdictValidate = (line) => (line.pass ? (line.soft ? 'SOFT-PASS' : 'PASS') : line.soft ? 'SOFT-FAIL (disclosed, not gating)' : 'FAIL');

function compareEvalLines(nativeLines, wasmLines, label, verdictFn, acc) {
  acc.sections[label] = { lines: nativeLines.length, mismatches: 0 };
  if (nativeLines.length !== wasmLines.length) {
    acc.mismatches.push(`${label}: line count native=${nativeLines.length} wasm=${wasmLines.length}`);
    acc.sections[label].mismatches++;
  }
  const n = Math.min(nativeLines.length, wasmLines.length);
  for (let i = 0; i < n; i++) {
    const nl = nativeLines[i];
    const wl = wasmLines[i];
    const probs = [];
    if (nl.output !== wl.output) probs.push(`output native=${nl.output} wasm=${wl.output}`);
    if (f2(wl.baseline) !== nl.baseline) probs.push(`baseline printed=${nl.baseline} wasm=${f2(wl.baseline)} (raw ${wl.baseline})`);
    if (f2(wl.post) !== nl.post) probs.push(`post printed=${nl.post} wasm=${f2(wl.post)} (raw ${wl.post})`);
    if (nl.delta !== undefined && fSigned2(wl.delta) !== nl.delta) probs.push(`delta printed=${nl.delta} wasm=${fSigned2(wl.delta)} (raw ${wl.delta})`);
    if (nl.expected !== wl.expected) probs.push(`expected native=${nl.expected} wasm=${wl.expected}`);
    if (verdictFn(wl) !== nl.verdict) probs.push(`verdict printed=${nl.verdict} wasm=${verdictFn(wl)} (pass=${wl.pass} soft=${wl.soft})`);
    if (probs.length) {
      acc.sections[label].mismatches++;
      acc.mismatches.push(`${label}[${i}] ${wl.output}: ${probs.join('; ')}`);
    }
  }
  acc.linesCompared += n;
}

const EVAL_RE_RUN = /^ {2}(\S+) +(-?\d+\.\d{2}) -> +(-?\d+\.\d{2}) +expected +(\S+) +(PASS|FAIL|SOFT-FAIL \(disclosed, not gating\))\s*$/;
function parseRunEvalLines(text) {
  const lines = [];
  for (const raw of text.split('\n')) {
    const m = raw.match(EVAL_RE_RUN);
    if (m) lines.push({ output: m[1], baseline: m[2], post: m[3], expected: m[4], verdict: m[5] });
  }
  return lines;
}

// ---------------------------------------------------------------- compare: theatre

function compareTheatre(acc) {
  // The task's suggested scratch dir /tmp/theatre-native was used for
  // the first native run-all, but this VM's /tmp is a small tmpfs and
  // the directory vanished before comparison; the debriefs were
  // regenerated into this durable scratch dir instead (theatre/debriefs/
  // itself is never touched).
  const nativeDir = new URL('wasm/harness/native/debriefs/', ROOT).pathname;
  const files = existsSync(nativeDir) ? readdirSync(nativeDir).filter((x) => x.endsWith('.debrief.json')).sort() : [];
  acc.sections.theatre = { traces: files.length, fields: 0, mismatches: 0 };
  for (const f of files) {
    const stem = f.replace(/\.debrief\.json$/, '');
    const wasmPath = new URL(`./theatre/${stem}.json`, OUT);
    if (!existsSync(wasmPath)) { acc.mismatches.push(`theatre ${stem}: wasm dump missing`); acc.sections.theatre.mismatches++; continue; }
    const native = JSON.parse(readFileSync(`${nativeDir}${f}`, 'utf8'));
    const wasmText = readFileSync(wasmPath, 'utf8');
    const wasmDebrief = JSON.parse(wasmText);
    if (wasmDebrief.error) { acc.mismatches.push(`theatre ${stem}: wasm error ${wasmDebrief.error}`); acc.sections.theatre.mismatches++; continue; }
    const sub = { fields: 0, mismatches: [] };
    deepCompare(native, wasmDebrief, stem, sub);
    acc.sections.theatre.fields += sub.fields;
    acc.sections.theatre.mismatches += sub.mismatches.length;
    for (const m of sub.mismatches) acc.mismatches.push(`theatre: ${m}`);
  }
  const vpath = new URL('theatre-validates.json', OUT);
  if (existsSync(vpath)) {
    const validates = JSON.parse(readFileSync(vpath, 'utf8'));
    const entries = Object.entries(validates);
    acc.sections.theatreValidate = { procedures: entries.length, emptyProblems: entries.filter(([, v]) => Array.isArray(v.problems) && v.problems.length === 0).length };
    for (const [f, v] of entries) if (!v.problems || v.problems.length !== 0) acc.mismatches.push(`theatre_validate ${f}: problems=${JSON.stringify(v.problems)}`);
  }
}

// ---------------------------------------------------------------- compare: physiology

function compareCourse(acc) {
  const nativeText = read('wasm/harness/native/run-course.txt');
  const wasmText = readFileSync(new URL('wasm-course.json', OUT), 'utf8');
  const wasmParsed = JSON.parse(wasmText);
  if (wasmParsed.error) { acc.mismatches.push(`course: wasm error ${wasmParsed.error}`); return; }
  compareEvalLines(parseRunEvalLines(nativeText), wasmParsed.lines, 'course', verdictRun, acc);
  const nativeHashes = [...nativeText.matchAll(/^(untreated|treated|whole blood|components)\s+trace hash: (0x[0-9a-f]+)\s*$/gm)].map((m) => [m[1], m[2]]);
  const wasmHashes = extractAll(wasmText, 'trace_hash').map(hex64);
  const labels = ['untreated', 'treated', 'whole blood', 'components'];
  acc.sections.courseHashes = { compared: Math.min(nativeHashes.length, wasmHashes.length), mismatches: 0 };
  for (let i = 0; i < labels.length; i++) {
    if (nativeHashes[i]?.[1] !== wasmHashes[i]) {
      acc.sections.courseHashes.mismatches++;
      acc.mismatches.push(`course hash ${labels[i]}: native=${nativeHashes[i]?.[1]} wasm=${wasmHashes[i]}`);
    }
  }
  acc.linesCompared += acc.sections.courseHashes.compared;
}

function compareHormones(acc) {
  const nativeText = read('wasm/harness/native/run-hormones.txt');
  const wasmText = readFileSync(new URL('wasm-hormones.json', OUT), 'utf8');
  const wasmParsed = JSON.parse(wasmText);
  if (wasmParsed.error) { acc.mismatches.push(`hormones: wasm error ${wasmParsed.error}`); return; }
  compareEvalLines(parseRunEvalLines(nativeText), wasmParsed.lines, 'hormones', verdictRun, acc);
  const nativeHashes = [...nativeText.matchAll(/^(.+?)\s+trace hash: (0x[0-9a-f]+)\s*$/gm)].map((m) => [m[1].trim(), m[2]]);
  const wasmHashes = extractAll(wasmText, 'trace_hash').map(hex64);
  acc.sections.hormoneHashes = { compared: Math.min(nativeHashes.length, wasmHashes.length), mismatches: 0, nativeLabels: nativeHashes.map((h) => h[0]) };
  for (let i = 0; i < Math.min(nativeHashes.length, wasmHashes.length); i++) {
    if (nativeHashes[i][1] !== wasmHashes[i]) {
      acc.sections.hormoneHashes.mismatches++;
      acc.mismatches.push(`hormones hash ${nativeHashes[i][0]}: native=${nativeHashes[i][1]} wasm=${wasmHashes[i]}`);
    }
  }
  acc.linesCompared += acc.sections.hormoneHashes.compared;
}

function compareResting(acc, validateText) {
  const wasmParsed = JSON.parse(readFileSync(new URL('wasm-resting.json', OUT), 'utf8'));
  if (wasmParsed.error) { acc.mismatches.push(`resting: wasm error ${wasmParsed.error}`); return; }
  const REST_RE = /^ {2}(\S+) +(-?\d+\.\d{2}) +(.+?) +range +(.+?) +\[(.+?)\] +(PASS|SOFT-PASS|FAIL|SOFT-FAIL \(disclosed, not gating\))\s*$/;
  let nativeLines = [];
  if (validateText) {
    let inResting = false;
    for (const raw of validateText.split('\n')) {
      if (raw.startsWith('=== RESTING CASE')) { inResting = true; continue; }
      if (inResting && raw.startsWith('=== ') && !raw.startsWith('=== RESTING')) break;
      if (inResting) {
        const m = raw.match(REST_RE);
        if (m) nativeLines.push({ output: m[1], value: m[2], unit: m[3], range_text: m[4], source: m[5], verdict: m[6] });
      }
    }
  }
  if (nativeLines.length > 0) {
    acc.sections.resting = { mode: 'validate-capture', lines: nativeLines.length, mismatches: 0 };
    if (nativeLines.length !== wasmParsed.lines.length) {
      acc.mismatches.push(`resting: line count native=${nativeLines.length} wasm=${wasmParsed.lines.length}`);
      acc.sections.resting.mismatches++;
    }
    const n = Math.min(nativeLines.length, wasmParsed.lines.length);
    for (let i = 0; i < n; i++) {
      const nl = nativeLines[i];
      const wl = wasmParsed.lines[i];
      const probs = [];
      if (nl.output !== wl.output) probs.push(`output native=${nl.output} wasm=${wl.output}`);
      if (f2(wl.value) !== nl.value) probs.push(`value printed=${nl.value} wasm=${f2(wl.value)} (raw ${wl.value})`);
      if (nl.unit !== wl.unit) probs.push(`unit native=${nl.unit} wasm=${wl.unit}`);
      if (nl.range_text !== wl.range_text) probs.push(`range native="${nl.range_text}" wasm="${wl.range_text}"`);
      if (verdictValidate(wl) !== nl.verdict) probs.push(`verdict printed=${nl.verdict} wasm=${verdictValidate(wl)} (pass=${wl.pass} soft=${wl.soft})`);
      if (probs.length) { acc.sections.resting.mismatches++; acc.mismatches.push(`resting[${i}] ${wl.output}: ${probs.join('; ')}`); }
    }
    acc.linesCompared += n;
  } else {
    // Fallback: recompute the resting ranges from parameters.json.
    const params = JSON.parse(read('physiology/parameters.json'));
    const ranges = params.validation_ranges;
    acc.sections.resting = { mode: 'parameters-fallback (no validate capture)', lines: Math.min(ranges.length, wasmParsed.lines.length), mismatches: 0 };
    const n = Math.min(ranges.length, wasmParsed.lines.length);
    for (let i = 0; i < n; i++) {
      const r = ranges[i];
      const wl = wasmParsed.lines[i];
      const probs = [];
      const expectRange = r.high != null ? `${rustNum(r.low)} .. ${rustNum(r.high)}` : `>= ${rustNum(r.low)}`;
      const expectPass = wl.value >= r.low && (r.high == null || wl.value <= r.high);
      if (wl.output !== r.output) probs.push(`output params=${r.output} wasm=${wl.output}`);
      if (wl.unit !== r.unit) probs.push(`unit params=${r.unit} wasm=${wl.unit}`);
      if (wl.range_text !== expectRange) probs.push(`range_text params="${expectRange}" wasm="${wl.range_text}"`);
      if (wl.pass !== expectPass) probs.push(`pass recomputed=${expectPass} wasm=${wl.pass} (value ${wl.value})`);
      if (probs.length) { acc.sections.resting.mismatches++; acc.mismatches.push(`resting-fallback[${i}] ${wl.output}: ${probs.join('; ')}`); }
    }
    acc.linesCompared += n;
  }
}

const RESP_RUN_KINDS = ['Hypoventilation', 'HypoventilationPure', 'Hyperventilation', 'HyperventilationPure', 'Shunt', 'ShuntPure', 'Metabolic', 'HemorrhageResp', 'HemorrhageFeedback'];

function compareRespiratoryRun(acc) {
  const nativeText = read('wasm/harness/native/run-respiratory.txt');
  const wasmText = readFileSync(new URL('wasm-respiratory.json', OUT), 'utf8');
  const wasmParsed = JSON.parse(wasmText);
  if (wasmParsed.error) { acc.mismatches.push(`respiratory: wasm error ${wasmParsed.error}`); return; }
  const armByKind = Object.fromEntries(wasmParsed.arms.map((a) => [a.kind, a]));
  acc.sections.respiratoryRun = { values: 0, mismatches: 0 };
  const cmp = (label, printed, wasmVal, fmt) => {
    acc.sections.respiratoryRun.values++;
    acc.linesCompared++;
    if (fmt(wasmVal) !== printed) {
      acc.sections.respiratoryRun.mismatches++;
      acc.mismatches.push(`respiratory-run ${label}: printed=${printed} wasm=${fmt(wasmVal)} (raw ${wasmVal})`);
    }
  };
  // resting line
  const restLine = nativeText.split('\n').find((l) => l.startsWith('resting:'));
  if (restLine) {
    const get = (label) => restLine.match(new RegExp(`${label} (-?[\\d.]+)`))?.[1];
    const r = wasmParsed.resting_resp;
    cmp('resting PaCO2', get('PaCO2'), r.paco2, f1);
    cmp('resting PAO2(alv)', restLine.match(/PAO2 (-?[\d.]+)/)?.[1], r.alveolar_po2, f1);
    cmp('resting PaO2', restLine.match(/PaO2 (-?[\d.]+)/)?.[1], r.pao2, f1);
    cmp('resting pH', get('pH'), r.ph, f3);
    cmp('resting SaO2', get('SaO2'), r.sao2, f3);
    cmp('resting CaO2', get('CaO2'), r.cao2, f2);
    cmp('resting CvO2', get('CvO2'), r.cvo2, f2);
    cmp('resting DO2', get('DO2'), r.do2, f0);
    cmp('resting O2ER', get('O2ER'), r.o2er, f3);
    cmp('resting VE', get('VE'), r.minute_ventilation, f2);
    cmp('resting VA', get('VA'), r.alveolar_ventilation, f2);
    cmp('resting RR', get('RR'), r.resp_rate, f1);
    cmp('resting VO2', get('VO2'), r.vo2, f0);
    cmp('resting VCO2', get('VCO2'), r.vco2, f0);
    cmp('resting Hb', get('Hb'), r.hemoglobin, f2);
    cmp('resting HCO3', get('HCO3'), r.bicarbonate, f2);
    cmp('resting A-a', get('A-a'), r.aa_gradient, f1);
    // cross-check: the resting kind's resp_post must equal resting_resp exactly
    const restingDump = JSON.parse(readFileSync(new URL('wasm-resting.json', OUT), 'utf8'));
    const sub = { fields: 0, mismatches: [] };
    deepCompare(restingDump.outcome.resp_post, r, 'resp_post-vs-resting_resp', sub);
    acc.sections.respiratoryRun.crossCheckFields = sub.fields;
    for (const m of sub.mismatches) acc.mismatches.push(`respiratory cross-check: ${m}`);
    acc.sections.respiratoryRun.mismatches += sub.mismatches.length;
  }
  // arm blocks in file order
  const L1 = /^ {2}PaCO2 (\S+) -> (\S+) mmHg\s+PaO2 (\S+) -> (\S+)\s+pH (\S+) -> (\S+)\s+CaO2 (\S+) -> (\S+) mL\/dL\s+DO2 (\S+) -> (\S+) mL\/min\s*$/;
  const L2 = /^ {2}VE (\S+) -> (\S+) L\/min\s+VA (\S+) -> (\S+)\s+RR (\S+) -> (\S+) \/min\s+A-a (\S+) -> (\S+) mmHg\s+SaO2 (\S+) -> (\S+)\s+P50eff (\S+) -> (\S+) mmHg\s*$/;
  const L3 = /^ {2}HCO3 (\S+) -> (\S+) mEq\/L \(renal compensation (\S+) mEq\/L at the mark, M53\)\s*$/;
  const L4 = /^ {2}circulation hash @ tick 12000: (0x[0-9a-f]+)\s+resp hash: (0x[0-9a-f]+)\s+conservation error: (\S+) mL\s*$/;
  const lines = nativeText.split('\n');
  const blocks = [];
  for (let i = 0; i < lines.length; i++) {
    const m1 = lines[i].match(L1);
    if (!m1) continue;
    const m2 = lines[i + 1]?.match(L2);
    const m3 = lines[i + 2]?.match(L3);
    const m4 = lines[i + 3]?.match(L4);
    if (m2 && m3 && m4) blocks.push({ m1, m2, m3, m4 });
  }
  acc.sections.respiratoryRun.blocks = blocks.length;
  if (blocks.length !== RESP_RUN_KINDS.length) acc.mismatches.push(`respiratory-run: parsed ${blocks.length} arm blocks, expected ${RESP_RUN_KINDS.length}`);
  // hash extraction aligned with wasm arms order
  const stdHashes = extractAll(wasmText, 'hash_at_standard_end').map(hex64);
  const respHashes = extractAll(wasmText, 'resp_hash').map(hex64);
  const armOrder = wasmParsed.arms.map((a) => a.kind);
  blocks.forEach((blk, bi) => {
    const kind = RESP_RUN_KINDS[bi];
    const arm = armByKind[kind];
    if (!arm) { acc.mismatches.push(`respiratory-run ${kind}: wasm arm missing`); return; }
    const b = arm.outcome.baseline;
    const p = arm.outcome.post;
    const [, bPaCO2, pPaCO2, bPaO2, pPaO2, bPh, pPh, bCaO2, pCaO2, bDO2, pDO2] = blk.m1;
    cmp(`${kind} PaCO2 base`, bPaCO2, b.paco2, f1); cmp(`${kind} PaCO2 post`, pPaCO2, p.paco2, f1);
    cmp(`${kind} PaO2 base`, bPaO2, b.pao2, f1); cmp(`${kind} PaO2 post`, pPaO2, p.pao2, f1);
    cmp(`${kind} pH base`, bPh, b.ph, f3); cmp(`${kind} pH post`, pPh, p.ph, f3);
    cmp(`${kind} CaO2 base`, bCaO2, b.cao2, f2); cmp(`${kind} CaO2 post`, pCaO2, p.cao2, f2);
    cmp(`${kind} DO2 base`, bDO2, b.do2, f0); cmp(`${kind} DO2 post`, pDO2, p.do2, f0);
    const [, bVE, pVE, bVA, pVA, bRR, pRR, bAa, pAa, bSaO2, pSaO2, bP50, pP50] = blk.m2;
    cmp(`${kind} VE base`, bVE, b.minute_ventilation, f2); cmp(`${kind} VE post`, pVE, p.minute_ventilation, f2);
    cmp(`${kind} VA base`, bVA, b.alveolar_ventilation, f2); cmp(`${kind} VA post`, pVA, p.alveolar_ventilation, f2);
    cmp(`${kind} RR base`, bRR, b.resp_rate, f1); cmp(`${kind} RR post`, pRR, p.resp_rate, f1);
    cmp(`${kind} A-a base`, bAa, b.aa_gradient, f1); cmp(`${kind} A-a post`, pAa, p.aa_gradient, f1);
    cmp(`${kind} SaO2 base`, bSaO2, b.sao2, f3); cmp(`${kind} SaO2 post`, pSaO2, p.sao2, f3);
    cmp(`${kind} P50eff base`, bP50, b.p50_eff, f2); cmp(`${kind} P50eff post`, pP50, p.p50_eff, f2);
    const [, bHCO3, pHCO3, comp] = blk.m3;
    cmp(`${kind} HCO3 base`, bHCO3, b.bicarbonate, f2); cmp(`${kind} HCO3 post`, pHCO3, p.bicarbonate, f2);
    cmp(`${kind} renal comp`, comp, p.hco3_comp, fSigned2);
    const ai = armOrder.indexOf(kind);
    cmp(`${kind} circulation hash`, blk.m4[1], stdHashes[ai], (v) => v);
    cmp(`${kind} resp hash`, blk.m4[2], respHashes[ai], (v) => v);
  });
}

const RESP_SECTIONS = [
  ['HYPOVENTILATION — BOHR SHIFT DISABLED', 'HypoventilationPure', 'hypoventilation_bohr_pure', { legacy: 'hypoventilation_halved' }],
  ['SHUNT — HYPOXIC DRIVE DISABLED', 'ShuntPure', 'shunt_20pct', {}],
  ['HAEMORRHAGE -750 mL, METABOLIC FEEDBACK ARMED', 'HemorrhageFeedback', 'hemorrhage_750_metabolic_feedback', {}],
  ['HYPOVENTILATION — RATE HELD AT 6', 'Hypoventilation', 'hypoventilation_halved', { bohr: 'hypoventilation_bohr' }],
  ['SHUNT — VENOUS ADMIXTURE', 'Shunt', 'shunt_20pct', { coupled: 'shunt_hypoxic_coupled' }],
  ['METABOLIC RATE DOUBLED', 'Metabolic', 'metabolic_doubled', {}],
  ['HAEMORRHAGE -750 mL, MODULE LIVE', 'HemorrhageResp', 'hemorrhage_750_respiratory', {}],
  ['HYPERVENTILATION — RATE HELD AT 24', 'Hyperventilation', 'hyperventilation_alkalosis', {}],
  ['HYPERVENTILATION — BOHR SHIFT DISABLED', 'HyperventilationPure', 'hyperventilation_bohr_pure', {}],
  ['SUSTAINED HYPOVENTILATION — FIVE DAYS, RENAL COMPENSATION LIVE', 'ChronicHypoventilation', 'chronic_hypoventilation_compensated', {}],
  ['SUSTAINED HYPOVENTILATION — FIVE DAYS, RENAL COMPENSATION DISABLED', 'ChronicHypoventilationPure', 'chronic_hypoventilation_uncompensated', {}],
  ['SUSTAINED HYPERVENTILATION — THREE DAYS, RENAL COMPENSATION LIVE', 'ChronicHyperventilation', 'chronic_hyperventilation_compensated', {}],
  ['SUSTAINED HYPERVENTILATION — THREE DAYS, RENAL COMPENSATION DISABLED', 'ChronicHyperventilationPure', 'chronic_hyperventilation_uncompensated', {}],
];
const EVAL_RE_VALIDATE = /^ {2}(?:\[(coupled|bohr|legacy)\] )?(\S+) +(-?\d+\.\d{2}) -> +(-?\d+\.\d{2}) +\(delta ([+-]?\d+\.\d{2})\) +expected +(\S+?)(?:\s+band \[[^\]]*\])?\s+\[(.+?)\] +(PASS|FAIL|SOFT-FAIL \(disclosed, not gating\))\s*$/;

function compareRespiratoryValidate(acc, validateText) {
  const wasmParsed = JSON.parse(readFileSync(new URL('wasm-respiratory.json', OUT), 'utf8'));
  if (wasmParsed.error) return;
  const armByKind = Object.fromEntries(wasmParsed.arms.map((a) => [a.kind, a]));
  // parse validate into (kind, caseId) -> native lines
  const native = new Map();
  let ctx = null;
  for (const raw of validateText.split('\n')) {
    if (raw.startsWith('=== ')) {
      ctx = null;
      for (const [sub, kind, defCase, prefixes] of RESP_SECTIONS) {
        if (raw.includes(sub)) { ctx = { kind, defCase, prefixes }; break; }
      }
      continue;
    }
    if (!ctx) continue;
    const m = raw.match(EVAL_RE_VALIDATE);
    if (!m) continue;
    const caseId = m[1] ? ctx.prefixes[m[1]] : ctx.defCase;
    if (!caseId) { acc.mismatches.push(`respiratory-validate: unmapped prefix [${m[1]}] in section ${ctx.kind}: ${raw.trim()}`); continue; }
    const key = `${ctx.kind}::${caseId}`;
    if (!native.has(key)) native.set(key, []);
    native.get(key).push({ output: m[2], baseline: m[3], post: m[4], delta: m[5], expected: m[6], verdict: m[8] });
  }
  let covered = 0;
  for (const [key, lines] of native.entries()) {
    const [kind, caseId] = key.split('::');
    const arm = armByKind[kind];
    const ev = arm?.evaluations.find((e) => e.case_id === caseId);
    if (!ev) { acc.mismatches.push(`respiratory-validate ${key}: wasm evaluation missing`); continue; }
    covered++;
    compareEvalLines(lines, ev.lines, `resp-validate ${key}`, verdictValidate, acc);
  }
  // every wasm evaluation should have been covered
  for (const arm of wasmParsed.arms) {
    for (const ev of arm.evaluations) {
      const key = `${arm.kind}::${ev.case_id}`;
      if (!native.has(key)) acc.mismatches.push(`respiratory-validate: wasm evaluation ${key} has NO native validate lines (uncovered)`);
    }
  }
  acc.sections.respiratoryValidate = { evaluationsCovered: covered, nativeKeys: native.size };
}

async function compare() {
  const acc = { linesCompared: 0, sections: {}, mismatches: [] };
  const guard = (name, fn) => {
    try { fn(); } catch (e) { acc.sections[name] = { missing: String(e.message || e) }; }
  };
  guard('theatre', () => compareTheatre(acc));
  guard('course', () => compareCourse(acc));
  guard('hormones', () => compareHormones(acc));
  let validateText = null;
  const vpath = new URL('wasm/harness/native/validate.txt', ROOT);
  if (existsSync(vpath)) {
    const t = readFileSync(vpath, 'utf8');
    if (t.includes('=== RESTING CASE')) validateText = t;
  }
  acc.validateCaptureUsed = !!validateText;
  guard('resting', () => compareResting(acc, validateText));
  guard('respiratoryRun', () => compareRespiratoryRun(acc));
  if (validateText) guard('respiratoryValidate', () => compareRespiratoryValidate(acc, validateText));
  writeOut('comparison.json', JSON.stringify(acc, null, 2));
  console.log(JSON.stringify({ linesCompared: acc.linesCompared, validateCaptureUsed: acc.validateCaptureUsed, sections: acc.sections, mismatchCount: acc.mismatches.length }, null, 2));
  for (const m of acc.mismatches.slice(0, 80)) console.log('MISMATCH:', m);
  if (acc.mismatches.length > 80) console.log(`... and ${acc.mismatches.length - 80} more (see out/comparison.json)`);
}

// ---------------------------------------------------------------- main

const cmd = process.argv[2];
const t0 = Date.now();
try {
  if (cmd === 'dump-theatre') await dumpTheatre();
  else if (cmd === 'dump-resting') await dumpResting();
  else if (cmd === 'dump-course') await dumpPhysio('course', 'wasm-course.json');
  else if (cmd === 'dump-hormones') await dumpPhysio('hormones', 'wasm-hormones.json');
  else if (cmd === 'dump-respiratory') await dumpPhysio('respiratory', 'wasm-respiratory.json');
  else if (cmd === 'compare') await compare();
  else { console.error('usage: verify.mjs dump-theatre|dump-resting|dump-course|dump-hormones|dump-respiratory|compare'); process.exit(2); }
  console.log(`[${cmd}] total ${(Date.now() - t0) / 1000}s`);
} catch (e) {
  console.error(`[${cmd}] FAILED:`, e);
  process.exit(1);
}
