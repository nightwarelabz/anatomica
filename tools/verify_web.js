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
   W7  imaging (Milestone 19; combined manifest, Milestone 32):
       web/data/imaging.json — shared meta + one block per derived
       subject — + the derived DICOM series under
       data/imaging/<subject>/. Run per subject for every subject in
       the manifest (whose set must equal the series on disk), plus:
       the label->record mapping table is asserted identical across
       subject blocks (the mapping is label-level; presence, voxel
       counts, HU statistics and geometry are per-subject). The
       TS-label ->
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
   W8  per-layer opacity (Milestone 21): FS_SHADE declares uOpacity
       and writes it as the fragment alpha; the shipped
       layerOpacity() is sliced out of viewer.js and executed
       against stub sliders (value mapping + clamping + the
       no-slider opaque default); the draw path partitions opaque
       layers before the blended, depth-mask-off translucent pass
       and restores GL state after it; the per-layer sliders and
       the glass-shell preset are wired in boot(); and the pick()
       id pass is asserted to contain no reference to opacity,
       blending or depth masking — opacity cannot corrupt picking
       by construction (the pixel-level proof is the native
       shell's; no browser exists on this VM, as at W6/W7).
   W9  delivery (Milestone 27): web/data/delivery.json names a
       gzip delivery encoding for every layer; both files' sizes
       and SHA-256 hashes are recomputed from disk and compared;
       each .gz is gunzipped (node zlib) and the decoded bytes
       must hash identically to the canonical pack — byte-identity
       of the delivery encoding, proven per layer — and the
       largest layer is additionally decoded through the platform
       DecompressionStream, the exact API the viewer uses. The
       viewer's LOAD_ORDER literal must equal delivery.json's
       load_order (a permutation of the 11 systems, skeletal and
       muscular first, integumentary last); the progressive
       wiring is asserted in the viewer source (loop started
       before the un-awaited loader; fetchPack prefers the
       compressed file, guards the decoded byte count, and falls
       back to the canonical pack), and pick()'s absent-layer
       skip — the line that makes picking degrade gracefully
       while a layer is still in flight — is asserted present.
   W10 MPR (Milestone 31; per subject, Milestone 32): the pure MPR
       core is sliced out of the shipped web/imaging.js and executed
       verbatim — against EVERY subject in the combined manifest,
       each with its own dims/spacing/IPP and its own present
       known-structure targets: plane
       dimensions must equal the volume-derived values and the
       physical extents must come from the recorded spacing (an
       anisotropic probe case proves the derivation, not a
       hardcode); the shipped mprExtract must equal an independent
       reslice of the shipped bins, full planes, HU and labels;
       two known-structure centroids per subject (gallbladder +
       vertebrae_L3 where present, else the next present structures
       with recorded geometry; recounted from the bins) must land on
       the same voxel in all three planes,
       with LPS coordinates matching the manifest; the crosshair
       mapping mprPixel/mprVoxel must roundtrip on a sampled set;
       the burned-in watermark glyph voxels (3071 HU) must appear
       in the resliced coronal and sagittal planes in exactly the
       glyph-position counts; and the tri-plane wiring (panes,
       toggle, volume loader, on-screen SYNTHETIC overlay, one
       shared shading path) is located in index.html / imaging.js.

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
const pendingAsync = [];  // W9's DecompressionStream proof registers here
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
      const geom = loadJSON(path.join(ROOT, SYSTEMS[key].geom));
      const links = clinicalLinks(loadJSON(path.join(ROOT, SYSTEMS[key].clin)));
      // Listed = every inventory record (the geometry file's record
      // set; assembled geometry-bearing records plus any
      // geometry-absent inventory records, e.g. the Milestone 33
      // FMA concept records of the nervous system) + clinical-only
      // + variants.
      expected = geom.records.length + links.only.length + links.variants.length;
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

// ---------- W7: imaging (Milestone 19; combined manifest + per-subject
// parameterization, Milestone 32) ----------
{
  const crypto = require("crypto");
  const imgTop = loadJSON(path.join(WEB, "imaging.json"));
  const census = loadJSON(path.join(ROOT, "data", "sources", "totalsegmentator-1.0", "labels.json"));
  const recIds = new Set(records.map(r => r.id));
  const SUBJS = Object.keys(imgTop.subjects || {}).sort();

  check(imgTop.meta.synthetic === true && SUBJS.length >= 2 &&
        SUBJS.includes(imgTop.default_subject) &&
        SUBJS.every(s => /SYNTHETIC/.test(imgTop.subjects[s].meta.banner) &&
                         imgTop.subjects[s].meta.banner.includes(s)),
        "W7 imaging manifest (Milestone 32): combined manifest declares synthetic; >= 2 subject blocks; default valid; every banner names its active subject",
        `subjects: ${SUBJS.join(", ")}; default ${imgTop.default_subject}`);
  const diskSubjs = fs.readdirSync(path.join(ROOT, "data", "imaging"))
    .filter(d => fs.existsSync(path.join(ROOT, "data", "imaging", d, "series.json"))).sort();
  check(JSON.stringify(diskSubjs) === JSON.stringify(SUBJS),
        "W7 manifest subjects == derived series on disk (data/imaging/*/series.json)",
        diskSubjs.join(", "));
  const wantPresets = { "soft-tissue": [350, 50], "lung": [1600, -600], "bone": [2000, 500] };
  let presetsOk = imgTop.meta.preset_sources.length >= 2;
  for (const p of imgTop.meta.presets) {
    const w = wantPresets[p.id];
    if (!w || w[0] !== p.window_width || w[1] !== p.window_level) presetsOk = false;
  }
  check(presetsOk && Object.keys(wantPresets).length === imgTop.meta.presets.length,
        "W7 window/level presets == cited table (soft 350/50, lung 1600/-600, bone 2000/500), >= 2 sources (shared meta)");

  // expected crosswalk, re-derived from the milestone sources
  // (label-level: one mapping table for every subject)
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

  // the mapping table is label-level: the mapping fields of every
  // label must be identical in every subject block — only presence,
  // voxel counts, HU statistics and geometry may differ per subject
  const mapKey = e => JSON.stringify([e.mapping_status, [...(e.record_ids || [])].sort(),
    e.mapping_note || "", [...(e.candidate_record_ids || [])].sort(),
    e.system_group, e.color_rgb]);
  let sharedOk = SUBJS.length > 0;
  if (SUBJS.length) {
    const ref = new Map(imgTop.subjects[SUBJS[0]].labels.map(e => [e.label, mapKey(e)]));
    for (const s of SUBJS.slice(1)) {
      if (imgTop.subjects[s].labels.length !== ref.size) sharedOk = false;
      for (const e of imgTop.subjects[s].labels)
        if (ref.get(e.label) !== mapKey(e)) sharedOk = false;
    }
  }
  check(sharedOk, "W7 label->record mapping table shared across subjects (mapping fields identical per label in every subject block; accounting is per-subject)");

  // DICOM EVLE walker (subject-independent)
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

  for (const SUBJ of SUBJS) {
    const blk = imgTop.subjects[SUBJ];
    const imgMan = { meta: Object.assign({}, imgTop.meta, blk.meta),
                     geometry: blk.geometry, files: blk.files,
                     crosswalk_totals: blk.crosswalk_totals, labels: blk.labels };
    const series = loadJSON(path.join(ROOT, "data", "imaging", SUBJ, "series.json"));
    const geo = imgMan.geometry, dims = geo.dims_voxels;

    check(series.subject.id === SUBJ && imgMan.meta.subject.id === SUBJ &&
          series.geometry.dims_voxels.cols === dims.cols &&
          series.geometry.dims_voxels.rows === dims.rows &&
          series.geometry.dims_voxels.slices === dims.slices,
          `W7 ${SUBJ} series.json subject + geometry == manifest subject block`);

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
      T.labels_absent_in_subject === imgMan.labels.filter(e => !e.present_in_subject).length &&
      T.mapped_and_present + T.mapped_and_absent === T.labels_mapped &&
      T.unmapped_and_present + T.unmapped_and_absent === T.labels_unmapped &&
      T.mapped_and_present + T.unmapped_and_present === T.labels_present_in_subject &&
      T.records_reachable_from_present_labels === reachP.size &&
      T.records_reachable_from_all_mapped_labels === reachA.size;
    check(cwOk && totalsOk, `W7 ${SUBJ} label->record crosswalk == re-derived M3 + inventory adjudications; totals reconcile`,
          cwDetail.slice(0, 4).join("; ") ||
          `${T.labels_mapped} mapped / ${T.labels_unmapped} unmapped; ${T.labels_present_in_subject} present; ${reachP.size} records reachable from present labels`);

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
    check(recountOk, `W7 ${SUBJ} slice bins: sizes exact; per-label voxel counts == imaging.json (recounted)`,
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
          `W7 ${SUBJ} watermark glyphs present in every web slice (${offs.length} voxels/slice @ 3071 HU)`);

    // DICOM file set: hashes, EVLE structure, metadata + pixel watermark
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
    check(dcmOk, `W7 ${SUBJ} DICOM set: sha256 == series.json; EVLE tags, synthetic metadata, IPP arithmetic, pixel identity with web bins, pixel watermark`,
          dcmDetail.slice(0, 4).join("; ") || `${inst.length} instances`);
  }

  // viewer wiring (once; covers the subject switcher)
  const indexHtml = fs.readFileSync(path.join(ROOT, "web", "index.html"), "utf8");
  const imagingJs = fs.readFileSync(path.join(ROOT, "web", "imaging.js"), "utf8");
  check(indexHtml.includes('id="imgCanvas"') && indexHtml.includes('id="btnModeImaging"') &&
        indexHtml.includes('id="imgSubjects"') && indexHtml.includes('src="imaging.js"') &&
        imagingJs.includes("imaging.json") && imagingJs.includes("select(") &&
        imagingJs.includes("imgApplySubject") && imagingJs.includes("imgBuildSeries") &&
        imagingJs.includes("imgBuildLegend"),
        "W7 imaging mode wired in index.html + imaging.js (manifest fetch; subject switcher + per-subject rebuild of series/legend; atlas select() panel reuse)");
}

// ---------- W8: per-layer opacity (Milestone 21) ----------
{
  const fsShade = viewerSrc.match(/const FS_SHADE = `#version 300 es([\s\S]*?)`;/)[1];
  check(/uniform float uOpacity;/.test(fsShade) && /o = vec4\(col, uOpacity\);/.test(fsShade),
        "W8 FS_SHADE declares uOpacity and writes it as the fragment alpha");

  const loBody = viewerSrc.match(/function layerOpacity\(key\) \{([\s\S]*?)\n\}/);
  check(!!loBody, "W8 layerOpacity() located in viewer.js");
  if (loBody) {
    const els = {};
    const stub$ = id => (id in els ? els[id] : null);
    const layerOpacity = new Function("$", "key", loBody[1]);
    const cases = [
      ["integumentary", "15", 0.15],
      ["integumentary", "100", 1],
      ["integumentary", "250", 1],
      ["integumentary", "0", 0.01],
      ["integumentary", "abc", 1],
      ["nervous", null, 1],
    ];
    let ok = true; const det = [];
    for (const [key, val, want] of cases) {
      if (val === null) delete els["op-" + key]; else els["op-" + key] = { value: val };
      const got = layerOpacity(stub$, key);
      if (Math.abs(got - want) > 1e-12) { ok = false; det.push(`${key}=${val} -> ${got}, want ${want}`); }
    }
    check(ok, "W8 layerOpacity() executed: slider mapping, clamping, opaque default",
          det.join("; ") || "15->0.15, 100->1, 250->1, 0->0.01, unparseable->1, no slider->1");
  }

  const iOpaque = viewerSrc.indexOf("layerOpacity(name) >= 1");
  const iBlend = viewerSrc.indexOf("gl.enable(gl.BLEND)");
  const iMaskOff = viewerSrc.indexOf("gl.depthMask(false)");
  const iMaskOn = viewerSrc.indexOf("gl.depthMask(true)");
  const iBlendOff = viewerSrc.indexOf("gl.disable(gl.BLEND)");
  check(iOpaque >= 0 && iBlend > iOpaque && iMaskOff > iBlend && iMaskOn > iMaskOff && iBlendOff > iMaskOn &&
        /gl\.blendFunc\(gl\.SRC_ALPHA, gl\.ONE_MINUS_SRC_ALPHA\)/.test(viewerSrc),
        "W8 draw partition: opaque pass, then blended depth-mask-off translucent pass, GL state restored");

  check(viewerSrc.includes('id="op-${key}"') && viewerSrc.includes('id="btnGlass"') &&
        viewerSrc.includes('setOpacity(key, key === "integumentary" ? 15 : 100)'),
        "W8 per-layer opacity sliders + glass-shell preset wired in boot()");

  const pickStart = viewerSrc.indexOf("function pick(x, y, mvp) {");
  const pickEnd = viewerSrc.indexOf("\n}\n", pickStart);
  const pickSrc = pickStart >= 0 ? viewerSrc.slice(pickStart, pickEnd) : "";
  check(pickSrc.length > 0 && !/layerOpacity|uOpacity|BLEND|depthMask|setOpacity/.test(pickSrc),
        "W8 pick() id pass contains no opacity/blend/depth-mask reference — picking is opacity-blind by construction");
}

// ---------- W9: delivery encoding + progressive loading (Milestone 27) ----------
{
  const crypto = require("crypto");
  const zlib = require("zlib");
  const shaFile = p => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
  let del = null;
  try { del = loadJSON(path.join(WEB, "delivery.json")); } catch (e) { /* reported below */ }
  check(!!del && del.codec && del.codec.name === "gzip" &&
        JSON.stringify(Object.keys(del.layers || {}).sort()) === JSON.stringify([...KEYS].sort()),
        "W9 delivery.json present, codec gzip, covers exactly the 11 layers");
  if (del) {
    let identOk = true, metaOk = true; const det = [];
    let totC = 0, totG = 0;
    for (const key of KEYS) {
      const e = del.layers[key], lay = manifest.layers[key];
      const cPath = path.join(WEB, e.file), gPath = path.join(WEB, e.compressed_file);
      if (e.file !== lay.file || e.bytes !== lay.bytes ||
          fs.statSync(cPath).size !== e.bytes || fs.statSync(gPath).size !== e.compressed_bytes ||
          shaFile(cPath) !== e.sha256 || shaFile(gPath) !== e.compressed_sha256) {
        metaOk = false; det.push(`${key} metadata`);
      }
      const gz = fs.readFileSync(gPath);
      if (gz[0] !== 0x1f || gz[1] !== 0x8b) { identOk = false; det.push(`${key} gzip magic`); }
      const out = zlib.gunzipSync(gz);
      const h = crypto.createHash("sha256").update(out).digest("hex");
      if (out.length !== e.bytes || h !== e.sha256) { identOk = false; det.push(`${key} decode`); }
      totC += e.bytes; totG += e.compressed_bytes;
    }
    check(metaOk, "W9 delivery metadata == files on disk (names, sizes, SHA-256 of both encodings)",
          det.join("; ") || "11 layers");
    check(identOk && totC === del.canonical_total_bytes && totG === del.compressed_total_bytes,
          "W9 byte-identity: gunzip(.gz) is byte-identical to the canonical pack, every layer",
          det.join("; ") || `${totC} B canonical -> ${totG} B delivered (${(totG / totC).toFixed(4)}x)`);
    // the exact API the shipped viewer decodes with, on the largest layer
    pendingAsync.push((async () => {
      const e = del.layers.muscular;
      const gz = fs.readFileSync(path.join(WEB, e.compressed_file));
      const buf = await new Response(
        new Blob([gz]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();
      const h = crypto.createHash("sha256").update(new Uint8Array(buf)).digest("hex");
      check(buf.byteLength === e.bytes && h === e.sha256,
            "W9 DecompressionStream('gzip') decode of muscular == canonical pack (browser API path)");
    })());
    const loMatch = viewerSrc.match(/const LOAD_ORDER = \[([^\]]*)\]/);
    const viewerOrder = loMatch ? [...loMatch[1].matchAll(/"(\w+)"/g)].map(m => m[1]) : [];
    check(JSON.stringify(viewerOrder) === JSON.stringify(del.load_order) &&
          JSON.stringify([...del.load_order].sort()) === JSON.stringify([...KEYS].sort()) &&
          del.load_order[0] === "skeletal" && del.load_order[1] === "muscular" &&
          del.load_order[del.load_order.length - 1] === "integumentary",
          "W9 viewer LOAD_ORDER == delivery.json load_order (permutation; skeletal, muscular first; integumentary last)",
          del.load_order.join(" -> "));
  }
  const iLoop = viewerSrc.indexOf("loop();");
  const iLoad = viewerSrc.indexOf("loadLayersProgressive(t0).catch");
  check(iLoop >= 0 && iLoad > iLoop && !viewerSrc.includes("await loadLayersProgressive") &&
        viewerSrc.includes('fetch("data/delivery.json")') &&
        viewerSrc.includes('new DecompressionStream("gzip")') &&
        viewerSrc.includes("buf.byteLength !== ent.bytes") &&
        viewerSrc.includes("manifestData.layers[key].file"),
        "W9 progressive wiring: render loop starts before the un-awaited loader; fetchPack prefers .gz, guards decoded size, falls back to canonical");
  const pkStart = viewerSrc.indexOf("function pick(x, y, mvp) {");
  const pkEnd = viewerSrc.indexOf("\n}\n", pkStart);
  const pkSrc = pkStart >= 0 ? viewerSrc.slice(pkStart, pkEnd) : "";
  check(pkSrc.includes("if (!lay || !layerVisible(name)) continue;"),
        "W9 pick() skips layers with no GPU buffers — picking degrades gracefully while a layer is in flight");
}

// ---------- W10: MPR (Milestone 31; exercised per subject, Milestone 32) ----------
{
  const imgTop = loadJSON(path.join(WEB, "imaging.json"));
  const SUBJS = Object.keys(imgTop.subjects || {}).sort();
  const imagingJs = fs.readFileSync(path.join(ROOT, "web", "imaging.js"), "utf8");
  const indexHtml = fs.readFileSync(path.join(ROOT, "web", "index.html"), "utf8");

  // the shipped MPR core, executed verbatim (the W6/W8 pattern)
  const iB = imagingJs.indexOf("// === MPR CORE BEGIN");
  const iE = imagingJs.indexOf("// === MPR CORE END ===");
  let api = null;
  if (iB >= 0 && iE > iB) {
    try {
      api = new Function(imagingJs.slice(iB, iE) +
        "\nreturn { mprPlaneDims, mprPlanePhysical, mprVoxel, mprPixel, mprExtract, mprLps };")();
    } catch (e) { api = null; }
  }
  check(!!api, "W10 MPR core located in imaging.js and executable");

  if (api) {
    // the derivation must respond to spacing, not hardcode the
    // subject's shape: anisotropic probe (subject-independent)
    const d2 = { cols: 10, rows: 20, slices: 30 }, s2 = [1, 2, 3];
    const a2 = api.mprPlanePhysical("axial", d2, s2),
          c2 = api.mprPlanePhysical("coronal", d2, s2),
          g2 = api.mprPlanePhysical("sagittal", d2, s2);
    check(a2.wMm === 10 && a2.hMm === 40 && c2.wMm === 10 && c2.hMm === 90 &&
          g2.wMm === 40 && g2.hMm === 90,
          "W10 physical extents derive from the spacing argument (anisotropic probe 1/2/3 mm -> axial 10x40, coronal 10x90, sagittal 40x90 mm)");

    for (const SUBJ of SUBJS) {
      const blk = imgTop.subjects[SUBJ];
      const imgMan = { meta: Object.assign({}, imgTop.meta, blk.meta),
                       geometry: blk.geometry, files: blk.files,
                       crosswalk_totals: blk.crosswalk_totals, labels: blk.labels };
      const series = loadJSON(path.join(ROOT, "data", "imaging", SUBJ, "series.json"));
      const geo = imgMan.geometry, dims = geo.dims_voxels, spacing = geo.spacing_mm;

      // plane dimensions from THIS subject's volume shape; physical
      // extents from ITS recorded spacing
      const pd = { axial: api.mprPlaneDims("axial", dims), coronal: api.mprPlaneDims("coronal", dims),
                   sagittal: api.mprPlaneDims("sagittal", dims) };
      const pp = { axial: api.mprPlanePhysical("axial", dims, spacing),
                   coronal: api.mprPlanePhysical("coronal", dims, spacing),
                   sagittal: api.mprPlanePhysical("sagittal", dims, spacing) };
      const dimsOk = pd.axial.w === dims.cols && pd.axial.h === dims.rows &&
        pd.axial.through === "k" && pd.axial.max === dims.slices - 1 &&
        pd.coronal.w === dims.cols && pd.coronal.h === dims.slices &&
        pd.coronal.through === "r" && pd.coronal.max === dims.rows - 1 &&
        pd.sagittal.w === dims.rows && pd.sagittal.h === dims.slices &&
        pd.sagittal.through === "c" && pd.sagittal.max === dims.cols - 1;
      const physOk = Math.abs(pp.axial.wMm - dims.cols * spacing[0]) < 1e-9 &&
        Math.abs(pp.axial.hMm - dims.rows * spacing[1]) < 1e-9 &&
        Math.abs(pp.coronal.wMm - dims.cols * spacing[0]) < 1e-9 &&
        Math.abs(pp.coronal.hMm - dims.slices * spacing[2]) < 1e-9 &&
        Math.abs(pp.sagittal.wMm - dims.rows * spacing[1]) < 1e-9 &&
        Math.abs(pp.sagittal.hMm - dims.slices * spacing[2]) < 1e-9;
      check(dimsOk && physOk,
            `W10 ${SUBJ} plane dims == volume-derived (axial ${dims.cols}x${dims.rows} through k; coronal/sagittal ${dims.cols}x${dims.slices} / ${dims.rows}x${dims.slices} through r/c); physical extents from spacing`,
            `axial ${pp.axial.wMm}x${pp.axial.hMm} mm, coronal ${pp.coronal.wMm}x${pp.coronal.hMm} mm, sagittal ${pp.sagittal.wMm}x${pp.sagittal.hMm} mm`);

      // assemble the volume from the shipped bins (independent reads)
      const NV = dims.cols * dims.rows;
      const volHu = new Int16Array(NV * dims.slices), volLbl = new Uint8Array(NV * dims.slices);
      for (let k = 0; k < dims.slices; k++) {
        const hb = fs.readFileSync(path.join(WEB, "imaging", SUBJ, `hu-${String(k).padStart(4, "0")}.bin`));
        const lb = fs.readFileSync(path.join(WEB, "imaging", SUBJ, `lbl-${String(k).padStart(4, "0")}.bin`));
        volHu.set(new Int16Array(hb.buffer, hb.byteOffset, NV), k * NV);
        volLbl.set(lb, k * NV);
      }
      // independent reference reslice, from the M19 geometry statement
      // alone (stored[c,r,k]; coronal/sagittal v measured down from the
      // superior end; sagittal u = r, viewed from the patient's left)
      function refVoxel(plane, idx, u, v) {
        if (plane === "axial") return [u, v, idx];
        if (plane === "coronal") return [u, idx, dims.slices - 1 - v];
        return [idx, u, dims.slices - 1 - v];
      }
      function centroidOf(labelIdx) {
        let sc = 0, sr = 0, sk = 0, n = 0;
        for (let k = 0; k < dims.slices; k++) for (let r = 0; r < dims.rows; r++) {
          const base = (k * dims.rows + r) * dims.cols;
          for (let c = 0; c < dims.cols; c++)
            if (volLbl[base + c] === labelIdx) { sc += c; sr += r; sk += k; n++; }
        }
        return { c: sc / n, r: sr / n, k: sk / n, n };
      }
      // known-structure targets for THIS subject: the Milestone 31
      // pair where present, else the next present structures with
      // recorded geometry, in this preference order
      const targets = [];
      for (const name of ["gallbladder", "vertebrae_L3", "liver", "spleen", "femur_left", "kidney_left"]) {
        const e = imgMan.labels.find(x => x.label === name);
        if (e && e.present_in_subject && e.geometry_lps) {
          targets.push({ name, e, cen: centroidOf(e.index) });
          if (targets.length === 2) break;
        }
      }

      // shipped extraction == independent reslice, full planes
      const gb = targets.length ? targets[0].cen : { c: dims.cols / 2, r: dims.rows / 2, k: dims.slices / 2 };
      const planeIdx = { axial: [Math.round(gb.k), 0, dims.slices - 1],
                         coronal: [Math.round(gb.r), 0, dims.rows - 1],
                         sagittal: [Math.round(gb.c), 0, dims.cols - 1] };
      let extractOk = true; const exDet = [];
      for (const plane of ["axial", "coronal", "sagittal"]) {
        for (const idx of planeIdx[plane]) {
          const p = api.mprExtract(volHu, volLbl, dims, plane, idx);
          const d = api.mprPlaneDims(plane, dims);
          if (p.w !== d.w || p.h !== d.h) { extractOk = false; exDet.push(plane + " dims"); continue; }
          let bad = false;
          for (let v = 0; v < d.h && !bad; v++) for (let u = 0; u < d.w; u++) {
            const [c, r, k] = refVoxel(plane, idx, u, v);
            const s = (k * dims.rows + r) * dims.cols + c, t = v * d.w + u;
            if (p.hu[t] !== volHu[s] || p.lbl[t] !== volLbl[s]) {
              extractOk = false; exDet.push(`${plane}@${idx} pixel (${u},${v})`); bad = true; break;
            }
          }
        }
      }
      check(extractOk, `W10 ${SUBJ} shipped mprExtract == independent reslice (full planes, HU + labels)`,
            exDet[0] || "9 planes compared pixel-for-pixel");

      // known-structure centroids: same voxel in all three planes, LPS == manifest
      let cenOk = targets.length === 2; const cenDet = [];
      if (targets.length !== 2) cenDet.push(`only ${targets.length} present target structures`);
      for (const { name, e, cen } of targets) {
        const manVox = [0, 1, 2].map(i =>
          (e.geometry_lps.centroid_lps_mm[i] - geo.ipp_first_slice_lps_mm[i]) / spacing[i]);
        if (cen.n !== e.voxels || Math.abs(cen.c - manVox[0]) > 1 ||
            Math.abs(cen.r - manVox[1]) > 1 || Math.abs(cen.k - manVox[2]) > 1) {
          cenOk = false; cenDet.push(name + " recount centroid != manifest");
        }
        const lps = api.mprLps({ c: cen.c, r: cen.r, k: cen.k }, geo);
        if (lps.some((x, i) => Math.abs(x - e.geometry_lps.centroid_lps_mm[i]) > spacing[i]))
          { cenOk = false; cenDet.push(name + " mprLps != manifest centroid"); }
        const vox = { c: Math.round(cen.c), r: Math.round(cen.r), k: Math.round(cen.k) };
        const sIdx = (vox.k * dims.rows + vox.r) * dims.cols + vox.c;
        if (volLbl[sIdx] !== e.index) { cenOk = false; cenDet.push(name + " centroid voxel unlabelled"); continue; }
        for (const plane of ["axial", "coronal", "sagittal"]) {
          const px = api.mprPixel(plane, vox, dims);
          const p = api.mprExtract(volHu, volLbl, dims, plane, px.idx);
          const t = px.v * p.w + px.u;
          if (p.lbl[t] !== e.index || p.hu[t] !== volHu[sIdx]) {
            cenOk = false; cenDet.push(`${name} disagrees in ${plane}`);
          }
        }
      }
      check(cenOk, `W10 ${SUBJ} known-structure centroids (${targets.map(t => t.name).join(" + ")}) land at the same voxel in all three planes; mprLps == manifest LPS centroid`,
            cenDet.join("; ") || targets.map(t => `${t.name} @ (c ${Math.round(t.cen.c)}, r ${Math.round(t.cen.r)}, k ${Math.round(t.cen.k)})`).join("; "));

      // crosshair correspondence roundtrip on a deterministic sample
      const samples = [{ c: 0, r: 0, k: 0 },
        { c: dims.cols - 1, r: dims.rows - 1, k: dims.slices - 1 },
        ...targets.map(t => ({ c: Math.round(t.cen.c), r: Math.round(t.cen.r), k: Math.round(t.cen.k) }))];
      let seed = 123456789;
      const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
      for (let i = 0; i < 300; i++)
        samples.push({ c: Math.floor(rnd() * dims.cols), r: Math.floor(rnd() * dims.rows),
                       k: Math.floor(rnd() * dims.slices) });
      let rtOk = true;
      for (const vox of samples) for (const plane of ["axial", "coronal", "sagittal"]) {
        const px = api.mprPixel(plane, vox, dims);
        const back = api.mprVoxel(plane, px.idx, px.u, px.v, dims);
        if (back.c !== vox.c || back.r !== vox.r || back.k !== vox.k) rtOk = false;
      }
      check(rtOk, `W10 ${SUBJ} crosshair correspondence: mprPixel/mprVoxel roundtrip from the shared voxel`,
            `${samples.length} voxels x 3 planes`);

      // watermark glyph voxels ride the resliced planes (exact counts:
      // 3071 HU occurs nowhere in this volume except the glyph slab)
      const offs = series.pixel_route.watermark_offsets_row_col;
      const corR = 9, sagC = 30, kProbe = Math.min(100, dims.slices - 1);
      const expCor = offs.filter(([r]) => r === corR).length * dims.slices;
      const expSag = offs.filter(([, c]) => c === sagC).length * dims.slices;
      const pCor = api.mprExtract(volHu, volLbl, dims, "coronal", corR);
      const pSag = api.mprExtract(volHu, volLbl, dims, "sagittal", sagC);
      let nCor = 0, nSag = 0;
      for (const x of pCor.hu) if (x === 3071) nCor++;
      for (const x of pSag.hu) if (x === 3071) nSag++;
      let wmOk = nCor === expCor && nSag === expSag; const wmDet = [];
      if (nCor !== expCor) wmDet.push(`coronal count ${nCor} != ${expCor}`);
      if (nSag !== expSag) wmDet.push(`sagittal count ${nSag} != ${expSag}`);
      for (const [r, c] of offs) {
        if (r === corR) {
          const px = api.mprPixel("coronal", { c, r, k: kProbe }, dims);
          if (pCor.hu[px.v * pCor.w + px.u] !== 3071) { wmOk = false; wmDet.push("coronal glyph position"); }
        }
        if (c === sagC) {
          const px = api.mprPixel("sagittal", { c, r, k: kProbe }, dims);
          if (pSag.hu[px.v * pSag.w + px.u] !== 3071) { wmOk = false; wmDet.push("sagittal glyph position"); }
        }
      }
      check(wmOk, `W10 ${SUBJ} watermark in MPR planes: 3071-HU glyph voxels in shipped coronal (r=9) + sagittal (c=30) extractions == glyph positions x ${dims.slices} slices, every glyph position present`,
            wmDet.join("; ") || `${nCor} coronal + ${nSag} sagittal glyph voxels`);
    }

    // wiring: panes + toggle + loader + on-screen watermark + one shading path
    check(indexHtml.includes('id="mprGrid"') && indexHtml.includes('id="imgAx"') &&
          indexHtml.includes('id="imgCor"') && indexHtml.includes('id="imgSag"') &&
          indexHtml.includes('id="imgMprBtn"') && indexHtml.includes('id="mprAx"') &&
          indexHtml.includes('id="mprCor"') && indexHtml.includes('id="mprSag"') &&
          imagingJs.includes("imgLoadVolume") && imagingJs.includes('fillText("SYNTHETIC"') &&
          imagingJs.includes("display-only") && (imagingJs.match(/imgPaint\(/g) || []).length >= 3,
          "W10 MPR wiring: tri-plane panes + sliders + toggle in index.html; volume loader, on-screen SYNTHETIC overlay, display-only note, shared imgPaint shading in imaging.js");
  }
}

Promise.all(pendingAsync).then(() => {
  console.log(failures ? `\n${failures} CHECK(S) FAILED` : "\nALL CHECKS PASS");
  process.exit(failures ? 1 : 0);
});
