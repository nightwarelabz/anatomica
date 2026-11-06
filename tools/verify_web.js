#!/usr/bin/env node
"use strict";
/* ANATOMICA web shell smoke test — Milestone 6.
   Verifies, in Node, every data file the web viewer loads:
     W1 manifest.json + records.json parse; counts: 199 skeletal
        geometry records in the manifest, 359 muscular; records.json
        lists 206 bones (199 with geometry, 7 without) and 360 muscle
        entries (359 with geometry + multifidus clinical-only);
     W2 each .bin header parses (magic ANW1, version 2) and counts /
        section sizes reproduce the file's exact byte size and the
        manifest's numbers;
     W3 decoded positions reproduce every record's canonical bbox from
        records.json (tolerance 0.01 cm — float32 rounding), per-vertex
        record slots are constant within each record's vertex range,
        and every index of a record stays inside its vertex range;
     W4 every OBJ mesh referenced by the assembled JSONs (201 skeletal
        + 417 muscular files) is re-counted from disk (v / f lines)
        and matches the counts recorded in the Milestone-2 / -4
        geometry JSONs;
     W5 cross-references: muscle clinical_id links resolve; the 7
        no-geometry bones are exactly Milestone 3's records_without_
        geometry; clinical-only muscle entries carry a geometry note;
     W6 pick-id codec roundtrip, bound to the shipped web/viewer.js:
        LAYER_BIT, the FS_PICK encoder (id expression + the four vec4
        channel expressions) and the pick() decoder block are parsed
        out of the viewer source and evaluated — the decoder block is
        executed verbatim via new Function against the real manifest
        ranges and records. Every slot of both layers (skeleton
        0..198, muscles 0..358) must roundtrip to its own record, and
        the miss pixel [0,0,0,0] must decode to null. This is the
        check that would have caught the Milestone-7 §1.4 defect
        (layer byte dropped: alpha fixed at 1.0, decoder reading only
        24 bits, every pick resolving against the muscle ranges).
        Set VIEWER_JS to point the W6 binding at another viewer.js
        copy (e.g. a pre-fix one) — data files still come from web/.
   Exit 0 iff all checks pass. */
const fs = require("fs");
const path = require("path");
const ROOT = path.join(__dirname, "..");
const WEB = path.join(ROOT, "web", "data");

let failures = 0;
function report(ok, label, detail = "") {
  console.log(`[${ok ? "PASS" : "FAIL"}] ${label}${detail ? " — " + detail : ""}`);
  if (!ok) failures++;
}

const manifest = JSON.parse(fs.readFileSync(path.join(WEB, "manifest.json"), "utf8"));
const recordsDoc = JSON.parse(fs.readFileSync(path.join(WEB, "records.json"), "utf8"));
const records = recordsDoc.records, clinical = recordsDoc.clinical;

// ---- W1 counts ----
const skelRecs = records.filter(r => r.layer === "skeleton");
const muscRecs = records.filter(r => r.layer === "muscle");
report(manifest.layers.skeleton.records === 199 && manifest.layers.muscles.records === 359,
  "W1 manifest record counts",
  `skeleton ${manifest.layers.skeleton.records}, muscles ${manifest.layers.muscles.records}`);
report(skelRecs.length === 206 && skelRecs.filter(r => r.has_geometry).length === 199 &&
       muscRecs.length === 360 && muscRecs.filter(r => r.has_geometry).length === 359,
  "W1 records.json counts",
  `bones ${skelRecs.length} (${skelRecs.filter(r => r.has_geometry).length} with geometry), ` +
  `muscles ${muscRecs.length} (${muscRecs.filter(r => r.has_geometry).length} with geometry)`);

// ---- W2/W3 bins ----
const recByKey = new Map(records.map(r => [r.layer + ":" + r.id, r]));
for (const [lname, layerName] of [["skeleton", "skeleton"], ["muscles", "muscle"]]) {
  const lay = manifest.layers[lname];
  const buf = fs.readFileSync(path.join(WEB, lay.file));
  const dv = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  const magic = String.fromCharCode(...buf.subarray(0, 4));
  const ver = dv.getUint32(4, true), nv = dv.getUint32(8, true),
        ni = dv.getUint32(12, true), nrec = dv.getUint32(16, true),
        ne = dv.getUint32(20, true);
  const off = i => Number(dv.getBigUint64(24 + 8 * i, true));
  const expectBytes = off(4) + ne * 4;
  report(magic === "ANW1" && ver === 2 && nv === lay.vertices && ni === lay.indices &&
         ne === lay.edge_indices && nrec === lay.records && expectBytes === buf.length &&
         buf.length === lay.bytes,
    `W2 ${lname}.bin header/size`,
    `v${ver}, ${nv} vertices, ${ni} indices, ${ne} edge indices, ${buf.length} bytes`);

  // decode positions + ids once
  const pos = new Float32Array(buf.buffer, buf.byteOffset + off(0), nv * 3);
  const ids = new Uint32Array(buf.buffer, buf.byteOffset + off(2), nv);
  const idx = new Uint32Array(buf.buffer, buf.byteOffset + off(3), ni);
  let worst = 0, slotBad = 0, idxBad = 0;
  for (const rng of lay.ranges) {
    const rec = recByKey.get(layerName + ":" + rng.record_id);
    const mn = [1 / 0, 1 / 0, 1 / 0], mx = [-1 / 0, -1 / 0, -1 / 0];
    for (let i = 0; i < rng.vertex_count; i++) {
      const v = rng.vertex_start + i;
      if (ids[v] !== rng.slot) slotBad++;
      for (let a = 0; a < 3; a++) {
        const x = pos[3 * v + a];
        if (x < mn[a]) mn[a] = x;
        if (x > mx[a]) mx[a] = x;
      }
    }
    const b = rec.bbox_canonical_cm;
    for (let a = 0; a < 3; a++) {
      worst = Math.max(worst, Math.abs(mn[a] - b.min[a]), Math.abs(mx[a] - b.max[a]));
    }
    for (let i = 0; i < rng.index_count; i++) {
      const ix = idx[rng.index_start + i];
      if (ix < rng.vertex_start || ix >= rng.vertex_start + rng.vertex_count) idxBad++;
    }
  }
  report(worst <= 0.01 && slotBad === 0 && idxBad === 0,
    `W3 ${lname}.bin content vs records.json`,
    `worst bbox diff ${worst.toExponential(2)} cm (tol 0.01), slot mismatches ${slotBad}, out-of-range indices ${idxBad}`);
}

// ---- W4 OBJ recount ----
function countObj(file) {
  const s = fs.readFileSync(file, "latin1");
  let v = 0, f = 0;
  for (const line of s.split("\n")) {
    if (line.startsWith("v ")) v++;
    else if (line.startsWith("f ")) f++;
  }
  return [v, f];
}
for (const [asmFile, geomFile, label] of [
    ["data/skeletal/skeleton-assembled.json", "data/skeletal/skeleton-geometry.json", "skeletal"],
    ["data/muscular/muscles-assembled.json", "data/muscular/muscle-geometry.json", "muscular"]]) {
  const asm = JSON.parse(fs.readFileSync(path.join(ROOT, asmFile), "utf8"));
  const geom = JSON.parse(fs.readFileSync(path.join(ROOT, geomFile), "utf8"));
  const geomMesh = new Map();
  for (const r of geom.records)
    for (const tree of ["isa_meshes", "partof_meshes"])
      for (const m of r[tree] || []) geomMesh.set(m.path, m);
  let files = 0, bad = 0, tv = 0, tf = 0;
  const seen = new Set();
  for (const r of asm.records) for (const m of r.meshes) {
    if (seen.has(m.path)) continue;
    seen.add(m.path); files++;
    const [v, f] = countObj(path.join(ROOT, m.path));
    const g = geomMesh.get(m.path);
    if (v !== m.vertices || f !== m.faces || !g || g.vertices !== v || g.faces !== f) bad++;
    tv += v; tf += f;
  }
  const expV = asm.records.reduce((s, r) => s + r.totals.vertices, 0);
  const expF = asm.records.reduce((s, r) => s + r.totals.faces, 0);
  // note: expV/expF count shared files per record; tv/tf count distinct files once
  report(bad === 0, `W4 ${label} OBJ recount`,
    `${files} distinct files re-counted from disk, ${bad} mismatches vs assembled + geometry JSONs; distinct-file totals ${tv} v / ${tf} f`);
}

// ---- W5 cross-references ----
const skelAsm = JSON.parse(fs.readFileSync(path.join(ROOT, "data/skeletal/skeleton-assembled.json"), "utf8"));
const noGeo = skelRecs.filter(r => !r.has_geometry).map(r => r.id).sort();
const expNoGeo = [...skelAsm.meta.records_without_geometry].sort();
report(JSON.stringify(noGeo) === JSON.stringify(expNoGeo),
  "W5 no-geometry bones == Milestone 3 set", noGeo.join(", "));
let badLinks = 0, clinOnly = 0;
for (const r of muscRecs) {
  if (r.clinical_id && !clinical[r.clinical_id]) badLinks++;
  if (!r.has_geometry) { clinOnly++; if (!r.geometry_note) badLinks++; }
}
report(badLinks === 0 && clinOnly === 1, "W5 clinical links",
  `${Object.keys(clinical).length} clinical records; clinical-only entries ${clinOnly} (multifidus)`);

// ---- W6 pick-id codec roundtrip, bound to the shipped viewer.js ----
// Binding: nothing here restates the codec. LAYER_BIT, the encoder's
// expressions and the decoder's statements are extracted from the
// viewer source at run time; the decoder block is executed verbatim.
// If the shipped code's shape changes so the extraction no longer
// matches, W6 fails loudly instead of testing a private copy.
const viewerPath = process.env.VIEWER_JS || path.join(ROOT, "web", "viewer.js");
const vsrc = fs.readFileSync(viewerPath, "utf8");
const w6problems = [];

// LAYER_BIT from the shipped source
const lbM = vsrc.match(/const LAYER_BIT = \{\s*skeleton:\s*(\d+),\s*muscle:\s*(\d+)\s*\};/);
const LB = lbM ? { skeleton: +lbM[1], muscle: +lbM[2] } : null;
if (!LB) w6problems.push("LAYER_BIT declaration not found in viewer source");

// FS_PICK encoder: translate the shipped GLSL expressions to JS.
// float(x) -> (x) keeps parentheses balanced; Nu -> N.
function glslFn(expr, params) {
  const js = expr
    .replace(/\buLayerBit\b/g, "uLayerBit")
    .replace(/(\d+)u\b/g, "$1")
    .replace(/\bfloat\(/g, "(");
  return new Function(...params, `"use strict"; return (${js});`);
}
let encodePick = null;
const fsM = vsrc.match(/const FS_PICK = `([\s\S]*?)`;/);
if (!fsM) w6problems.push("FS_PICK shader not found in viewer source");
else {
  const idM = fsM[1].match(/uint id = ([^;]+);/);
  const vecM = fsM[1].match(/o = vec4\(([^;]+)\);/);
  if (!idM) w6problems.push("FS_PICK: `uint id = ...;` statement not found");
  if (!vecM) w6problems.push("FS_PICK: `o = vec4(...);` statement not found");
  if (idM && vecM) {
    // split the vec4 argument list on top-level commas
    const args = []; let depth = 0, cur = "";
    for (const ch of vecM[1]) {
      if (ch === "(") depth++;
      if (ch === ")") depth--;
      if (ch === "," && depth === 0) { args.push(cur); cur = ""; }
      else cur += ch;
    }
    args.push(cur);
    if (args.length !== 4) w6problems.push(`FS_PICK: vec4 has ${args.length} channels, expected 4`);
    else {
      try {
        const idFn = glslFn(idM[1], ["uLayerBit", "vSlot"]);
        const chanFns = args.map(a => glslFn(a, ["id"]));
        encodePick = (layerBit, slot) => {
          const id = idFn(layerBit, slot) >>> 0;
          return chanFns.map(f => Math.round(Math.min(1, Math.max(0, f(id))) * 255));
        };
      } catch (e) { w6problems.push("FS_PICK expression evaluation failed: " + e.message); }
    }
  }
}

// pick() decoder: extract the shipped statements from the hit test
// through the range-resolution return, and execute them verbatim.
let decodePick = null;
const pickM = vsrc.match(/function pick\(x, y, mvp\) \{([\s\S]*?)\n\}/);
if (!pickM) w6problems.push("pick() function not found in viewer source");
else {
  const body = pickM[1];
  const start = body.indexOf("if (px[3] === 0)");
  const endM = body.match(/return rng \?[^;]+;/);
  if (start < 0) w6problems.push("pick(): hit-test statement `if (px[3] === 0)` not found");
  if (!endM) w6problems.push("pick(): range-resolution return not found");
  if (start >= 0 && endM) {
    const segment = body.slice(start, endM.index + endM[0].length);
    try {
      decodePick = new Function("px", "LAYER_BIT", "layers", "byId",
        `"use strict";\n${segment}`);
    } catch (e) { w6problems.push("pick() decoder block failed to build: " + e.message); }
  }
}

if (!encodePick || !decodePick || !LB) {
  report(false, "W6 pick codec roundtrip (bound to shipped viewer.js)",
    "could not bind to shipped code: " + w6problems.join("; "));
} else {
  const layersStub = {
    skeleton: { ranges: manifest.layers.skeleton.ranges },
    muscles: { ranges: manifest.layers.muscles.ranges },
  };
  const byIdW6 = new Map(records.map(r => [r.layer + ":" + r.id, r]));
  let cases = 0, bad = 0; const badEx = [];
  for (const [recLayer, drawName] of [["skeleton", "skeleton"], ["muscle", "muscles"]]) {
    const ranges = manifest.layers[drawName].ranges;
    for (let slot = 0; slot < ranges.length; slot++) {
      const bytes = encodePick(LB[recLayer], slot);
      const rec = decodePick(bytes, LB, layersStub, byIdW6);
      cases++;
      if (rec !== byIdW6.get(recLayer + ":" + ranges[slot].record_id)) {
        bad++;
        if (badEx.length < 6)
          badEx.push(`${recLayer} slot ${slot} (bytes ${bytes.join("/")}) -> ` +
            (rec ? rec.layer + ":" + rec.id : "null"));
      }
    }
  }
  if (decodePick([0, 0, 0, 0], LB, layersStub, byIdW6) !== null) {
    bad++; badEx.push("miss pixel [0,0,0,0] did not decode to null");
  }
  report(bad === 0, "W6 pick codec roundtrip (bound to shipped viewer.js)",
    `${cases} encode->decode cases (every slot, both layers) + miss case; failures ${bad}` +
    (badEx.length ? "; e.g. " + badEx.join(" | ") : ""));
}

console.log(failures ? `\n${failures} FAILURE(S)` : "\nALL CHECKS PASS");
process.exit(failures ? 1 : 0);
