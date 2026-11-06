#!/usr/bin/env node
/* ANATOMICA web-shell verifier — Milestone 16 (generalized from the
   Milestone-6 verifier, whose W1–W5 covered the skeletal and
   muscular layers and whose W6 was added by Milestone 7-FIX).
   Independent of the packer (tools/pack_geometry.py): re-derives
   counts from the source data files on disk. The OBJ-level truth is
   bound by the assertion chain: the assemblers asserted streamed
   OBJ counts against the geometry JSONs, and the packer asserted
   streamed OBJ counts against the assembled JSONs (a mismatch
   aborts either tool), so W4's JSON-level equalities close the
   loop from the packs back to the on-disk meshes.

   W1  layer set and counts: manifest layers == viewer LAYER_BIT /
       LAYER_STYLE keys == the 11 systems; per-layer manifest
       pick_bit / label / colour == the viewer literals (the
       manifest is the shells' source of truth, the literals are
       asserted against it); records.json listed counts per system
       re-derived from the source files (assembled JSONs, clinical
       tranches, the Phase-1 skeleton.js).
   W2  pack headers: magic, version 2, counts == manifest, section
       offsets arithmetic == actual file size, range sums == header.
   W3  pack content: per-record bounding boxes recomputed from the
       packed float32 positions equal the records.json boxes
       (tolerance 1e-3 cm — float32 rounding); per-vertex record
       slots: sampled per range and range-checked globally; every
       index of a record stays inside its vertex range.
   W4  assembled totals per system == the module geometry files'
       chosen compositions (IS-A primary, PART-OF fallback, minus
       the de-duplicated occurrences recorded in the assembled
       meta), and manifest range totals == assembled totals.
   W5  records.json consistency: every assembled record listed
       exactly once with its slot; the geometry-less skeletal set is
       exactly the Milestone-3 set (6 ossicles + coccyx); every
       clinical_ids entry resolves into the clinical map; the
       clinical map holds every authored clinical record and
       variant (369 entries); the listed clinical-only and variant
       sets equal the source-derived sets.
   W6  pick codec, bound to the shipped web/viewer.js: the FS_PICK
       encoder expressions and the pick() decoder block are parsed
       out of the viewer source and evaluated — the decoder block is
       executed verbatim via new Function against the real manifest
       ranges and records, fed with pixels produced by the parsed
       encoder. Every slot of every layer (1,545 cases) must
       roundtrip to its own record, the miss pixel [0,0,0,0] must
       decode to null, and an unknown layer bit must decode to null.
       This is the Milestone-7-FIX regression gate, generalized.
   W7  imaging (Milestone 19): web/data/imaging.json + the derived
       DICOM series under data/imaging/<subject>/. The TS-label ->
       Body Model record crosswalk is re-derived independently
       (Milestone-3 skeletal rules + the inventories'
       totalsegmentator_overlap blocks) and compared exactly;
       per-label voxel counts are recounted from the shipped label
       bins; every DICOM instance is hash-checked against
       series.json, parsed (EVLE walk), and asserted for the
       synthetic watermark in metadata (BurnedInAnnotation,
       ImageType, SeriesDescription) and in pixels (glyph voxels ==
       3071 at the recorded offsets), with DICOM pixel data byte-
       identical to the web HU bins; window/level presets equal the
       cited table and cite >= 2 sources; the viewer's imaging
       wiring is located in index.html / imaging.js.

   Run: node tools/verify_web.js   (exit 0 iff all checks pass)
*/
"use strict";
const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const WEB = path.join(ROOT, "web", "data");
const APP_DATA = path.join(ROOT, "..", "anatomica-app", "data");
const VIEWER = process.env.VIEWER_JS || path.join(ROOT, "web", "viewer.js");
let failures = 0;
function check(ok, label, detail = "") {
  console.log(`[${ok ? "PASS" : "FAIL"}] ${label}${detail ? " — " + detail : ""}`);
  if (!ok) failures++;
}
function loadJSON(p) { return JSON.parse(fs.readFileSync(p, "utf8")); }

const SYSTEMS = {
  skeletal:     { geom: "data/skeletal/skeleton-geometry.json",         asm: "data/skeletal/skeleton-assembled.json",         clin: null },
  muscular:     { geom: "data/muscular/muscle-geometry.json",           asm: "data/muscular/muscles-assembled.json",          clin: "data/muscular/muscles.json" },
  cardiovascular:{ geom: "data/cardiovascular/cv-geometry.json",        asm: "data/cardiovascular/cv-assembled.json",         clin: "data/cardiovascular/cardiovascular.json" },
  nervous:      { geom: "data/nervous/nervous-geometry.json",           asm: "data/nervous/nervous-assembled.json",             clin: "data/nervous/nervous.json" },
  respiratory:  { geom: "data/respiratory/respiratory-geometry.json",   asm: "data/respiratory/respiratory-assembled.json",     clin: "data/respiratory/respiratory.json" },
  digestive:    { geom: "data/digestive/digestive-geometry.json",       asm: "data/digestive/digestive-assembled.json",         clin: "data/digestive/digestive.json" },
  urinary:      { geom: "data/urinary/urinary-geometry.json",           asm: "data/urinary/urinary-assembled.json",             clin: "data/urinary/urinary.json" },
  lymphatic:    { geom: "data/lymphatic/lymphatic-geometry.json",       asm: "data/lymphatic/lymphatic-assembled.json",         clin: "data/lymphatic/lymphatic.json" },
  endocrine:    { geom: "data/endocrine/endocrine-geometry.json",       asm: "data/endocrine/endocrine-assembled.json",         clin: "data/endocrine/endocrine.json" },
  reproductive: { geom: "data/reproductive/reproductive-geometry.json", asm: "data/reproductive/reproductive-assembled.json",   clin: "data/reproductive/reproductive.json" },
  integumentary:{ geom: "data/integumentary/integumentary-geometry.json", asm: "data/integumentary/integumentary-assembled.json", clin: "data/integumentary/integumentary.json" },
};
const KEYS = Object.keys(SYSTEMS);

const manifest = loadJSON(path.join(WEB, "manifest.json"));
const recordsDoc = loadJSON(path.join(WEB, "records.json"));
const records = recordsDoc.records;
const clinical = recordsDoc.clinical;
const viewerSrc = fs.readFileSync(VIEWER, "utf8");

// viewer literals
const bitBlock = viewerSrc.match(/const LAYER_BIT = \{([^}]*)\}/)[1];
const LAYER_BIT = {};
for (const m of bitBlock.matchAll(/(\w+):\s*(\d+)/g)) LAYER_BIT[m[1]] = +m[2];
const styleBlock = viewerSrc.match(/const LAYER_STYLE = \{([\s\S]*?)\n\};/)[1];
const LAYER_STYLE = {};
for (const m of styleBlock.matchAll(/(\w+): \{ color: \[([0-9.,\s]+)\], label: "([^"]+)" \}/g))
  LAYER_STYLE[m[1]] = { color: m[2].split(",").map(s => +s), label: m[3] };

const chosen = rec => (rec.isa_meshes && rec.isa_meshes.length) ? rec.isa_meshes : (rec.partof_meshes || []);
function clinicalLinks(clin) {
  const byId = new Map(), only = [], variants = [];
  if (!clin) return { byId, only, variants };
  for (const c of clin.records) {
    const cid = c.record_id || c.id;
    byId.set(cid, c);
    let g = c.geometry_record_ids;
    if (g === undefined && c.geometry) g = c.geometry.inventory_record_ids;
    if (!g || !g.length) only.push(cid);
  }
  for (const v of clin.variants || []) { byId.set(v.id, v); variants.push(v.id); }
  return { byId, only, variants };
}

// ---------- W1 ----------
{
  const mKeys = Object.keys(manifest.layers).sort();
  check(JSON.stringify(mKeys) === JSON.stringify([...KEYS].sort()) &&
        JSON.stringify(manifest.layer_order) === JSON.stringify(KEYS) &&
        JSON.stringify(Object.keys(LAYER_BIT).sort()) === JSON.stringify([...KEYS].sort()) &&
        JSON.stringify(Object.keys(LAYER_STYLE).sort()) === JSON.stringify([...KEYS].sort()),
        "W1 layer set == 11 systems in manifest, LAYER_BIT, LAYER_STYLE");
  const bits = Object.values(LAYER_BIT);
  check(new Set(bits).size === 11 && Math.min(...bits) === 1 && Math.max(...bits) === 11,
        "W1 pick bits are exactly 1..11, unique");
  let agree = true, listedOk = true; const listedDetail = [];
  const listedByLayer = {};
  for (const r of records) listedByLayer[r.layer] = (listedByLayer[r.layer] || 0) + 1;
  for (const key of KEYS) {
    const lay = manifest.layers[key];
    const st = LAYER_STYLE[key];
    if (lay.pick_bit !== LAYER_BIT[key] || lay.label !== st.label ||
        JSON.stringify(lay.color) !== JSON.stringify(st.color)) agree = false;
    let expected;
    if (key === "skeletal") {
      const raw = fs.readFileSync(path.join(APP_DATA, "skeleton.js"), "utf8");
      const skel = JSON.parse(raw.slice(raw.indexOf("{"), raw.lastIndexOf("}") + 1));
      expected = skel.bones.length;
    } else {
      const asm = loadJSON(path.join(ROOT, SYSTEMS[key].asm));
      const links = clinicalLinks(loadJSON(path.join(ROOT, SYSTEMS[key].clin)));
      expected = asm.records.length + links.only.length + links.variants.length;
    }
    if (listedByLayer[key] !== expected) { listedOk = false; listedDetail.push(`${key}: listed ${listedByLayer[key]} vs source-derived ${expected}`); }
  }
  check(agree, "W1 manifest pick_bit/label/colour == viewer literals for all 11 layers");
  check(listedOk && recordsDoc.meta.listed_records === records.length,
        "W1 records.json listed counts == source-derived counts per system",
        listedDetail.join("; ") || `${records.length} listed records total`);
}

// ---------- W2 + W3 ----------
for (const key of KEYS) {
  const lay = manifest.layers[key];
  const buf = fs.readFileSync(path.join(WEB, lay.file));
  const magic = buf.toString("ascii", 0, 4);
  const ver = buf.readUInt32LE(4), nv = buf.readUInt32LE(8), ni = buf.readUInt32LE(12),
        nrec = buf.readUInt32LE(16), ne = buf.readUInt32LE(20);
  const off = i => Number(buf.readBigUInt64LE(24 + 8 * i));
  const sizeOk = buf.length === lay.bytes &&
    off(0) === 128 && off(1) === 128 + nv * 12 && off(2) === off(1) + nv * 4 &&
    off(3) === off(2) + nv * 4 && off(4) === off(3) + ni * 4 && buf.length === off(4) + ne * 4;
  const sumV = lay.ranges.reduce((s, r) => s + r.vertex_count, 0);
  const sumI = lay.ranges.reduce((s, r) => s + r.index_count, 0);
  check(magic === "ANW1" && ver === 2 && nv === lay.vertices && ni === lay.indices &&
        nrec === lay.records && ne === lay.edge_indices && sizeOk && sumV === nv && sumI === ni,
        `W2 ${key} pack header/offsets/ranges`,
        `${nv} v, ${ni} i, ${nrec} records, ${buf.length} B`);
  // W3: per-record bboxes from packed positions; slot + index sanity
  const byIdRec = new Map(records.filter(r => r.layer === key && r.has_geometry).map(r => [r.id, r]));
  let worst = 0, slotBad = 0, idxBad = 0;
  const idsBase = off(2), idxBase = off(3);
  for (const rng of lay.ranges) {
    const rec = byIdRec.get(rng.record_id);
    const mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
    const base = off(0) + rng.vertex_start * 12;
    for (let i = 0; i < rng.vertex_count; i++) {
      for (let a = 0; a < 3; a++) {
        const v = buf.readFloatLE(base + i * 12 + a * 4);
        if (v < mn[a]) mn[a] = v;
        if (v > mx[a]) mx[a] = v;
      }
    }
    for (let a = 0; a < 3; a++) {
      worst = Math.max(worst, Math.abs(mn[a] - rec.bbox_canonical_cm.min[a]),
                       Math.abs(mx[a] - rec.bbox_canonical_cm.max[a]));
    }
    for (const vi of [rng.vertex_start, rng.vertex_start + (rng.vertex_count >> 1), rng.vertex_start + rng.vertex_count - 1])
      if (buf.readUInt32LE(idsBase + vi * 4) !== rng.slot) slotBad++;
    for (let i = 0; i < rng.index_count; i++) {
      const ix = buf.readUInt32LE(idxBase + (rng.index_start + i) * 4);
      if (ix < rng.vertex_start || ix >= rng.vertex_start + rng.vertex_count) idxBad++;
    }
  }
  let globalSlotBad = 0;
  for (let i = 0; i < nv; i++) if (buf.readUInt32LE(idsBase + i * 4) >= nrec) globalSlotBad++;
  check(worst <= 1e-3 && slotBad === 0 && idxBad === 0 && globalSlotBad === 0,
        `W3 ${key} packed bboxes == records.json; slots/indices consistent`,
        `worst bbox diff ${worst.toExponential(2)} cm; slot mismatches ${slotBad}; out-of-range indices ${idxBad}; out-of-range slots ${globalSlotBad}`);
}

// ---------- W4 ----------
for (const key of KEYS) {
  const geom = loadJSON(path.join(ROOT, SYSTEMS[key].geom));
  const asm = loadJSON(path.join(ROOT, SYSTEMS[key].asm));
  const dropped = new Set((asm.meta.deduped_files || []).map(d => d.record_id + "|" + d.dropped));
  let ev = 0, ef = 0;
  for (const r of geom.records)
    for (const m of chosen(r)) {
      if (dropped.has(r.record_id + "|" + m.fj)) continue;
      ev += m.vertices; ef += m.faces;
    }
  const av = asm.records.reduce((s, r) => s + r.totals.vertices, 0);
  const af = asm.records.reduce((s, r) => s + r.totals.faces, 0);
  const lay = manifest.layers[key];
  const rv = lay.ranges.reduce((s, r) => s + r.vertex_count, 0);
  const ri = lay.ranges.reduce((s, r) => s + r.index_count, 0);
  check(ev === av && ef === af && rv === av && ri === af * 3,
        `W4 ${key} assembled totals == geometry compositions == pack ranges`,
        `${av} v / ${af} f (geometry-derived ${ev} v / ${ef} f)`);
}

// ---------- W5 ----------
{
  let ok = true; const detail = [];
  const seen = new Set();
  for (const key of KEYS) {
    const asm = loadJSON(path.join(ROOT, SYSTEMS[key].asm));
    const listed = new Map(records.filter(r => r.layer === key).map(r => [r.id, r]));
    for (const a of asm.records) {
      const e = listed.get(a.record_id);
      if (!e || !e.has_geometry || e.slot === null) { ok = false; detail.push(`${key}:${a.record_id} missing/slotless`); continue; }
      const rng = manifest.layers[key].ranges[e.slot];
      if (!rng || rng.record_id !== a.record_id) { ok = false; detail.push(`${key}:${a.record_id} slot mismatch`); }
      if (seen.has(key + ":" + a.record_id)) { ok = false; detail.push(`${key}:${a.record_id} listed twice`); }
      seen.add(key + ":" + a.record_id);
    }
    const links = clinicalLinks(SYSTEMS[key].clin ? loadJSON(path.join(ROOT, SYSTEMS[key].clin)) : null);
    const listedOnly = records.filter(r => r.layer === key && r.record_kind === "clinical-only").map(r => r.id).sort();
    const listedVar = records.filter(r => r.layer === key && r.record_kind === "variant").map(r => r.id).sort();
    if (JSON.stringify(listedOnly) !== JSON.stringify([...links.only].sort())) { ok = false; detail.push(`${key} clinical-only set differs`); }
    if (JSON.stringify(listedVar) !== JSON.stringify([...links.variants].sort())) { ok = false; detail.push(`${key} variant set differs`); }
  }
  const geom = loadJSON(path.join(ROOT, SYSTEMS.skeletal.geom));
  const noGeo = geom.records.filter(r => !chosen(r).length).map(r => r.record_id).sort();
  const listedNoGeo = records.filter(r => r.layer === "skeletal" && !r.has_geometry).map(r => r.id).sort();
  if (JSON.stringify(noGeo) !== JSON.stringify(listedNoGeo)) { ok = false; detail.push(`skeletal no-geometry set differs: ${listedNoGeo}`); }
  let expectedClin = 0;
  for (const key of KEYS) {
    if (!SYSTEMS[key].clin) continue;
    const links = clinicalLinks(loadJSON(path.join(ROOT, SYSTEMS[key].clin)));
    expectedClin += links.byId.size;
    for (const cid of links.byId.keys())
      if (!clinical[cid] || clinical[cid].layer !== key) { ok = false; detail.push(`clinical ${cid} missing/wrong layer`); }
  }
  if (Object.keys(clinical).length !== expectedClin) { ok = false; detail.push(`clinical map ${Object.keys(clinical).length} vs ${expectedClin}`); }
  for (const r of records)
    for (const cid of r.clinical_ids || [])
      if (!clinical[cid]) { ok = false; detail.push(`${r.layer}:${r.id} -> unresolved clinical ${cid}`); }
  check(ok, "W5 records.json consistency (slots, no-geometry set, clinical-only/variant sets, clinical map)",
        detail.slice(0, 6).join("; ") || `${seen.size} geometry records listed once each; clinical map ${Object.keys(clinical).length} entries; no-geometry bones: ${listedNoGeo.join(", ")}`);
}

// ---------- W6: execute the shipped pick encoder + decoder ----------
{
  // encoder: parse FS_PICK's id expression and channel expressions
  const fsPick = viewerSrc.match(/const FS_PICK = `#version 300 es([\s\S]*?)`;/)[1];
  const idExpr = fsPick.match(/uint id = ([^;]+);/)[1]
    .replace(/uLayerBit/g, "bit").replace(/vSlot/g, "slot").replace(/(\d+)u\b/g, "$1");
  const chanExprs = fsPick.match(/o = vec4\(([\s\S]*?)\);/)[1].split(",").map(s => {
    const inner = s.match(/float\((.*)\)\s*\/\s*255\.0/)[1].replace(/(\d+)u\b/g, "$1");
    return new Function("id", `return (${inner});`);
  });
  const encode = new Function("bit", "slot",
    `const id = (${idExpr}) >>> 0; return id;`);
  const encodePixel = (bit, slot) => {
    const id = encode(bit, slot);
    return new Uint8Array(chanExprs.map(f => f(id) & 255));
  };
  // decoder: slice the shipped statements and execute them verbatim
  const start = viewerSrc.indexOf("if (px[3] === 0)");
  const endMarker = 'return rng ? byId.get(layerName + ":" + rng.record_id) : null;';
  const end = viewerSrc.indexOf(endMarker);
  check(start >= 0 && end > start && chanExprs.length === 4,
        "W6 encoder/decoder slices located in viewer.js");
  if (start >= 0 && end > start) {
    const code = viewerSrc.slice(start, end + endMarker.length);
    const layersStub = {};
    for (const key of KEYS) layersStub[key] = { ranges: manifest.layers[key].ranges };
    const byIdStub = new Map(records.map(r => [r.layer + ":" + r.id, r]));
    const decode = new Function("px", "LAYER_BIT", "layers", "byId",
      code + "\nreturn null;");
    let cases = 0, bad = 0;
    for (const key of KEYS) {
      const bit = LAYER_BIT[key];
      for (const rng of manifest.layers[key].ranges) {
        const hit = decode(encodePixel(bit, rng.slot), LAYER_BIT, layersStub, byIdStub);
        cases++;
        if (!hit || hit.layer !== key || hit.id !== rng.record_id) bad++;
      }
    }
    const miss = decode(new Uint8Array([0, 0, 0, 0]), LAYER_BIT, layersStub, byIdStub);
    const unknown = decode(encodePixel(200, 3), LAYER_BIT, layersStub, byIdStub);
    check(bad === 0 && miss === null && unknown === null,
          "W6 pick codec roundtrip — every slot of every layer",
          `${cases} slot cases, ${bad} failures; miss pixel -> ${miss}; unknown bit 200 -> ${unknown}`);
  }
}

// ---------- W7: imaging (Milestone 19) ----------
{
  const crypto = require("crypto");
  const imgMan = loadJSON(path.join(WEB, "imaging.json"));
  const SUBJ = imgMan.meta.subject.id;
  const series = loadJSON(path.join(ROOT, "data", "imaging", SUBJ, "series.json"));
  const census = loadJSON(path.join(ROOT, "data", "sources", "totalsegmentator-1.0", "labels.json"));
  const geo = imgMan.geometry, dims = geo.dims_voxels;
  const recIds = new Set(records.map(r => r.id));

  check(imgMan.meta.synthetic === true && /SYNTHETIC/.test(imgMan.meta.banner),
        "W7 imaging manifest declares the series synthetic, banner carries it");
  const wantPresets = { "soft-tissue": [350, 50], "lung": [1600, -600], "bone": [2000, 500] };
  let presetsOk = imgMan.meta.preset_sources.length >= 2;
  for (const p of imgMan.meta.presets) {
    const w = wantPresets[p.id];
    if (!w || w[0] !== p.window_width || w[1] !== p.window_level) presetsOk = false;
  }
  check(presetsOk && Object.keys(wantPresets).length === imgMan.meta.presets.length,
        "W7 window/level presets == cited table (soft 350/50, lung 1600/-600, bone 2000/500), >= 2 sources");

  // expected crosswalk, re-derived from the milestone sources
  function skeletalRecord(label) {
    if (label.startsWith("vertebrae_")) return "vert_" + label.split("_").slice(1).join("_");
    if (label.startsWith("rib_left_")) return "rib" + label.split("_").pop() + "_left";
    if (label.startsWith("rib_right_")) return "rib" + label.split("_").pop() + "_right";
    const direct = { femur_left: "femur_left", femur_right: "femur_right",
      humerus_left: "humerus_left", humerus_right: "humerus_right",
      scapula_left: "scapula_left", scapula_right: "scapula_right",
      hip_left: "hip_left", hip_right: "hip_right", sacrum: "sacrum",
      clavicula_left: "clavicle_left", clavicula_right: "clavicle_right" };
    return direct[label] || null;
  }
  const expected = new Map();
  for (const lab of Object.keys(census.labels)) {
    const r = skeletalRecord(lab);
    if (r) expected.set(lab, [r]);
  }
  for (const dir of fs.readdirSync(path.join(ROOT, "data"))) {
    const dpath = path.join(ROOT, "data", dir);
    if (!fs.statSync(dpath).isDirectory()) continue;
    for (const f of fs.readdirSync(dpath).filter(f => f.endsWith("-inventory.json"))) {
      const doc = loadJSON(path.join(dpath, f));
      (function walk(o) {
        if (o && typeof o === "object") {
          if (o.totalsegmentator_overlap)
            for (const e of o.totalsegmentator_overlap.labels || [])
              expected.set(e.label, [...e.inventory_record_ids].sort());
          for (const v of Object.values(o)) walk(v);
        }
      })(doc);
    }
  }
  let cwOk = true; const cwDetail = [];
  const manByLabel = new Map(imgMan.labels.map(e => [e.label, e]));
  if (imgMan.labels.length !== Object.keys(census.labels).length) cwOk = false;
  for (const lab of Object.keys(census.labels)) {
    const e = manByLabel.get(lab), exp = expected.get(lab);
    if (!e) { cwOk = false; cwDetail.push(lab + " missing"); continue; }
    if (exp) {
      if (e.mapping_status !== "mapped" ||
          JSON.stringify([...e.record_ids].sort()) !== JSON.stringify(exp))
        { cwOk = false; cwDetail.push(lab + " mapping differs"); }
    } else if (e.mapping_status !== "unmapped" || (e.record_ids || []).length)
      { cwOk = false; cwDetail.push(lab + " should be unmapped"); }
    for (const rid of [...(e.record_ids || []), ...(e.candidate_record_ids || [])])
      if (!recIds.has(rid)) { cwOk = false; cwDetail.push(`${lab} -> unresolved ${rid}`); }
  }
  const T = imgMan.crosswalk_totals;
  const reachP = new Set(), reachA = new Set();
  for (const e of imgMan.labels) if (e.mapping_status === "mapped") {
    for (const rid of e.record_ids) { reachA.add(rid); if (e.present_in_subject) reachP.add(rid); }
  }
  const totalsOk = T.labels_in_source_set === imgMan.labels.length &&
    T.labels_mapped === expected.size &&
    T.labels_unmapped === imgMan.labels.length - expected.size &&
    T.labels_present_in_subject === imgMan.labels.filter(e => e.present_in_subject).length &&
    T.records_reachable_from_present_labels === reachP.size &&
    T.records_reachable_from_all_mapped_labels === reachA.size;
  check(cwOk && totalsOk, "W7 label->record crosswalk == re-derived M3 + inventory adjudications; totals reconcile",
        cwDetail.slice(0, 4).join("; ") ||
        `${T.labels_mapped} mapped / ${T.labels_unmapped} unmapped; ${reachP.size} records reachable from present labels`);

  // series integrity + per-label recount from the shipped label bins
  const recount = new Array(imgMan.labels.length + 1).fill(0);
  let binsOk = true;
  for (let k = 0; k < dims.slices; k++) {
    const hp = path.join(WEB, "imaging", SUBJ, `hu-${String(k).padStart(4, "0")}.bin`);
    const lp = path.join(WEB, "imaging", SUBJ, `lbl-${String(k).padStart(4, "0")}.bin`);
    const hb = fs.readFileSync(hp), lb = fs.readFileSync(lp);
    if (hb.length !== dims.cols * dims.rows * 2 || lb.length !== dims.cols * dims.rows) binsOk = false;
    for (let i = 0; i < lb.length; i++) if (lb[i]) recount[lb[i]]++;
  }
  let recountOk = binsOk;
  for (const e of imgMan.labels)
    if (recount[e.index] !== e.voxels || e.present_in_subject !== (e.voxels > 0)) recountOk = false;
  check(recountOk, "W7 slice bins: sizes exact; per-label voxel counts == imaging.json (recounted)",
        `${dims.slices} slice pairs; ${recount.reduce((a, b) => a + b, 0)} labelled voxels`);

  // watermark in pixels (web bins) at the recorded glyph offsets
  const offs = series.pixel_route.watermark_offsets_row_col;
  let wmOk = true;
  for (let k = 0; k < dims.slices && wmOk; k++) {
    const hb = fs.readFileSync(path.join(WEB, "imaging", SUBJ, `hu-${String(k).padStart(4, "0")}.bin`));
    for (const [r, c] of offs)
      if (hb.readInt16LE((r * dims.cols + c) * 2) !== 3071) { wmOk = false; break; }
  }
  check(wmOk && /SYNTHETIC/.test(series.pixel_route.watermark),
        `W7 watermark glyphs present in every web slice (${offs.length} voxels/slice @ 3071 HU)`);

  // DICOM file set: hashes, EVLE structure, metadata + pixel watermark
  function parseDicom(buf) {
    if (buf.toString("ascii", 128, 132) !== "DICM") return null;
    let pos = 132; const tags = {};
    while (pos + 8 <= buf.length) {
      const g = buf.readUInt16LE(pos), e = buf.readUInt16LE(pos + 2);
      const vr = buf.toString("ascii", pos + 4, pos + 6);
      let len, start;
      if (["OB", "OW", "OF", "SQ", "UC", "UR", "UT", "UN"].includes(vr)) {
        len = buf.readUInt32LE(pos + 8); start = pos + 12;
      } else { len = buf.readUInt16LE(pos + 6); start = pos + 8; }
      if (g === 0x7FE0 && e === 0x0010) { tags.pixels = { start, len }; break; }
      tags[`${g},${e}`] = buf.toString("ascii", start, start + len).replace(/[\s\x00]+$/, "");
      pos = start + len;
    }
    return tags;
  }
  let dcmOk = true; const dcmDetail = [];
  const inst = series.dicom.instances;
  if (inst.length !== dims.slices) { dcmOk = false; dcmDetail.push("instance count"); }
  for (let k = 0; k < inst.length; k++) {
    const p = path.join(ROOT, "data", "imaging", SUBJ, inst[k].file);
    const buf = fs.readFileSync(p);
    const sha = crypto.createHash("sha256").update(buf).digest("hex");
    if (sha !== inst[k].sha256) { dcmOk = false; dcmDetail.push(`k${k} sha`); continue; }
    const t = parseDicom(buf);
    if (!t || !t.pixels) { dcmOk = false; dcmDetail.push(`k${k} parse`); continue; }
    const ipp = (t["32,50"] || "").split("\\").map(Number);
    const good = t["40,769"] === "YES" && /^DERIVED/.test(t["8,8"] || "") &&
      /SYNTHETIC/.test(t["8,4158"] || "") && t["8,24"] === inst[k].sop_instance_uid &&
      t["32,19"] === String(k + 1) && t.pixels.len === dims.cols * dims.rows * 2 &&
      Math.abs(ipp[2] - (geo.ipp_first_slice_lps_mm[2] + k * geo.spacing_mm[2])) < 1e-3;
    if (!good) { dcmOk = false; dcmDetail.push(`k${k} tags`); continue; }
    const web = fs.readFileSync(path.join(WEB, "imaging", SUBJ, `hu-${String(k).padStart(4, "0")}.bin`));
    if (!buf.subarray(t.pixels.start, t.pixels.start + t.pixels.len).equals(web)) {
      dcmOk = false; dcmDetail.push(`k${k} pixels != web bin`); continue;
    }
    for (const [r, c] of offs)
      if (buf.readInt16LE(t.pixels.start + (r * dims.cols + c) * 2) !== 3071) {
        dcmOk = false; dcmDetail.push(`k${k} watermark`); break;
      }
  }
  check(dcmOk, "W7 DICOM set: sha256 == series.json; EVLE tags, synthetic metadata, IPP arithmetic, pixel identity with web bins, pixel watermark",
        dcmDetail.slice(0, 4).join("; ") || `${inst.length} instances`);

  // viewer wiring
  const indexHtml = fs.readFileSync(path.join(ROOT, "web", "index.html"), "utf8");
  const imagingJs = fs.readFileSync(path.join(ROOT, "web", "imaging.js"), "utf8");
  check(indexHtml.includes('id="imgCanvas"') && indexHtml.includes('id="btnModeImaging"') &&
        indexHtml.includes('src="imaging.js"') && imagingJs.includes("imaging.json") &&
        imagingJs.includes("select("),
        "W7 imaging mode wired in index.html + imaging.js (manifest fetch; atlas select() panel reuse)");
}

console.log(failures ? `\n${failures} CHECK(S) FAILED` : "\nALL CHECKS PASS");
process.exit(failures ? 1 : 0);
