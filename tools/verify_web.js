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

console.log(failures ? `\n${failures} CHECK(S) FAILED` : "\nALL CHECKS PASS");
process.exit(failures ? 1 : 0);
