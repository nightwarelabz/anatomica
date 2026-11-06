# ANATOMICA — Milestone 6: Muscular Assembly + Web Shell v2 (real geometry)

Date: 2026-11-06. Status: **built and verified locally at data level; not
uploaded.** Visual (screenshot) verification was **not** performed — see
§5 for the exact reason; no visual claim is made anywhere in this file.

Method: Milestones 2–4 discipline, continued. The muscular layer is
assembled with the identical frame conversion as the skeleton
(Milestone 3) and checked against it; the web viewer consumes only
assembled data, packed by a tool that re-asserts every count it reads;
a Node smoke test re-derives every number the viewer displays from the
source files on disk.

## Deliverables

| File | Content |
|---|---|
| `tools/assemble_muscles.py` | Muscular assembler (mirrors `tools/assemble_skeleton.py`) |
| `data/muscular/muscles-assembled.json` | 359 muscular records, canonical-frame bboxes from streamed vertices |
| `tools/muscle_assembly_check.py` | Independent assembly checker (K1–K7); exit 0 |
| `tools/pack_web_geometry.py` | Packs merged GPU buffers + `records.json` + `manifest.json` into `web/data/` |
| `web/index.html`, `web/viewer.js` | Web shell v2 — raw WebGL2, zero dependencies |
| `tools/verify_web.js` | Node smoke test over everything the viewer loads (W1–W5); exit 0 |

## 1. Muscular assembly — the M3 conversion, applied unchanged

Mesh-set rule identical to Milestone 3 (IS-A primary; PART-OF only
where IS-A is empty; geometry-identical duplicates de-duplicated —
none occurred). The assembler additionally verifies per record that
the PART-OF fj set adds nothing beyond the IS-A set (true for all
359; 49 records list PART-OF meshes, all redundant copies).

- **359 records assembled, 0 skipped, 0 de-duplicated.**
- Totals: **417 mesh files, 1,704,260 vertices, 2,365,492 faces** —
  streamed counts asserted against Milestone 4 for every file.
- Muscular union (canonical cm): min (−31.938, −7.281, −1.987),
  max (31.938, 153.697, 22.645); span **63.876 × 160.978 × 24.632**.

## 2. Assembly check (K1–K7) — all gated checks pass

- **K1** record set: assembled = geometry = inventory = **359**.
- **K2** every assembled bbox equals the corner-transformed union of
  the stored M4 per-mesh source boxes — worst diff **0.00e+00 cm**
  (independent computation path from the assembler's vertex stream).
- **K3 layer coherence vs the skeletal assembly** (skeletal union
  64.785 × 170.675 × 25.405 cm, Milestone 3): muscle span sits inside
  the skeletal envelope on x (inside by 0.456 / 0.453 cm) and at the
  top (inside by 9.930 cm — muscles do not reach the skull vault);
  it **exceeds** the skeletal envelope by **0.233 cm at min-y** and
  **0.187 cm at min-z** (muscles reach slightly below the lowest bone
  and behind the most posterior bone — measured, small, and
  anatomically plausible for toe flexors in the plantar-flexed source
  pose and posterior neck musculature; reported, not adjusted).
  Gated part: **no** muscle record's bbox is disjoint from the
  skeletal union expanded by 2.0 cm (0 violations). Together with K2's
  exactness this is the first evidence on register_sketch unknown 1:
  the soft-tissue concepts do share the skeletal frame.
- **K4 mirror symmetry** — distributional gate (a frame error would
  shift the whole distribution): **median deviation 0.0000 cm, p90
  0.1438 cm** over 154 left/right pairs. **9 pairs ≥ 1.0 cm**, each
  listed with its measured mechanism in K4c: in 8 of 9, the RIGHT
  concept's BP3D mesh includes bulk geometry across the mid-sagittal
  plane (cross-midline vertex fraction: puborectalis 10.09%,
  thyrohyoid 5.45%, pubococcygeus 4.29%, rectus capitis anterior
  3.20%, iliococcygeus 2.65%, aryepiglotticus 2.18%,
  sternocleidomastoid 0.84%, cricothyroid 0.32%; the left mesh is
  0.000% in every outlier pair). These are midline sling / neck
  muscles; the pattern is a BP3D source-modeling property, not an
  assembly error. The 9th, **stylopharyngeus (1.264 cm, a y-extent
  difference, cross-midline fractions 0.000% / 0.000%), has NO
  identified mechanism and is flagged as such.**
  Trimmed (1–99 pct) readings confirm the split: sternocleidomastoid's
  deviation collapses (sparse tail), the pelvic-floor group's does
  not (bulk crossing).
- **K5 [report]** 11 records intersect no bone bbox — all are
  laryngeal muscles (crico-arytenoids, lateral/posterior; arytenoids;
  vocalis; cricothyroid). The larynx is cartilage, not bone, and its
  muscles sit in a gap between bone bboxes; expected anatomy, listed
  in full in the checker output.
- **K6** no NaN/Inf. **K7** distinct paths 417, grand totals equal
  the Milestone-4 IS-A sums exactly; per-record sums ok.

The same cross-midline measurement, made by the packer over the
skeleton, finds 5 skull bones above 0.5%: nasal (left) 44.1%,
parietal (left) 34.1%, parietal (right) 9.3%, maxilla (left) 7.9%,
palatine (left) 5.1% — midline-suture bones whose source meshes
straddle the sagittal plane. Consistent with the M3 skeletal mirror
check having passed on bboxes (worst 0.414 cm); recorded here as a
measured source property, mechanism not further investigated.

## 3. Web data pack (tools/pack_web_geometry.py)

One merged static buffer set per layer (format ANW1 v2): positions
float32 (canonical cm), smooth normals int8 snorm (computed from the
converted, winding-flipped faces), per-vertex record slot uint32,
indices uint32, plus a unique-edge index buffer for wireframe.

| Layer | Bytes | Vertices | Faces | Edges | Records | Mesh files |
|---|---|---|---|---|---|---|
| skeleton.bin | 18,190,236 | 283,091 | 511,968 | 798,084 | 199 | 201 |
| muscles.bin | 94,585,848 | 1,704,260 | 2,365,492 | 4,014,327 | 359 | 417 |
| **Total** | **112,776,084** | **1,987,351** | **2,877,460** | **4,812,411** | **558** | **618** |

`records.json` (664,801 B) lists **566 records**: all 206 verified
bones (199 with geometry; the 7 Milestone-3 no-geometry bones listed
and marked, never dropped), 359 muscular instances (241 linked to a
clinical record, 118 inventory-only and marked as such), and
multifidus as a clinical-only entry (geometry null in Milestone 4).
Packing asserted every file's streamed v/f counts against the
assembled JSONs (618 files, 0 mismatches) and took 98 s.

## 4. The viewer (web/)

Raw WebGL2, no libraries, no build step. Serve `web/` statically
(e.g. `python3 -m http.server` in `web/`) and open `index.html`.

- **Draw strategy (as implemented):** one merged buffer set per layer;
  **1 draw call per layer** with no region filter (2 total), **+1
  LINES draw per layer** with wireframe on; with a region filter
  active, per-record range draws instead (up to 558). Picking is an
  id-buffer pass rendered on demand (click, and throttled hover), not
  per frame. Face culling is intentionally disabled (double-sided);
  normals are computed post-conversion from the flipped faces, so
  lighting does not depend on the cull path.
- Orbit / zoom / pan (pointer + two-finger pinch), reset view.
- Click a mesh → record panel: bones show the verified Phase-1 record
  (TA name, division/region/subgroup, side, classification,
  articulations, description where present); muscles show the
  inventory identity plus, when linked, the Milestone-4 clinical
  record (origin, insertion, actions, innervation, arterial supply,
  field sources, sourcing tier) with **verify flags displayed in
  full**. Records whose source mesh carries > 0.5% of vertices across
  the mid-sagittal plane show that measured fact in the panel.
- Search across both layers (name, TA name, id, clinical name);
  record list with honest badges (`no geometry`, `inventory-only`,
  `⚠ n verify`); layer toggles with counts; region filter over both
  layers (bone `region` / muscle `region_group`); labels toggle
  (projected bbox centres, screen-size threshold, top 140 by size);
  wireframe toggle; dim-others-on-select toggle.
- **Integrity strip** computes from the loaded data at runtime:
  listed records, records with geometry, drawn records / meshes /
  triangles under the current toggles+filter, draw calls of the last
  frame, frame ms (EMA), and measured load ms.

## 5. Verification — what was and was not checked

**Node smoke test (`node tools/verify_web.js`, 9 s, ALL CHECKS PASS):**
W1 counts (199 / 359 in the manifest; 206 / 360 in records.json);
W2 bin headers and exact byte sizes; W3 decoded positions reproduce
every record's canonical bbox (worst diff **7.6e-6 cm**, float32
rounding), per-vertex slots constant per record, all indices inside
their record's vertex range; W4 all **618 OBJ files re-counted from
disk, 0 mismatches** against the assembled and geometry JSONs;
W5 the 7 no-geometry bones are exactly Milestone 3's set, all 127
clinical links resolve, exactly 1 clinical-only entry. `viewer.js`
passes `node --check`.

**Screenshot / visual verification: NOT performed.** The only browser
binary on this VM is the managed Muse Browser
(`/opt/meta-chromium/chrome`), which refuses headless startup outside
its service ("Hatch WebGL domain policy is required for browser
startup"); no other Chromium or Firefox binary exists on the machine.
Consequences, stated plainly: **load time and frame rate in a real
browser are unmeasured** (the viewer measures and displays both at
runtime; the numbers in this milestone are data-side only), and
shader-level appearance (lighting, highlight, label placement) has
not been seen by anyone. The first visual run remains an open
verification step — the data path it renders is verified end-to-end,
the pixels are not.

## 6. Known defects and carried unknowns

1. **No visual verification yet** (§5) — the largest open item.
2. **Wireframe overlay is layer-global:** with a region filter
   active, edges are not drawn (the edge buffer is not partitioned
   per record). Triangles still filter correctly.
3. **Cross-midline source meshes render as sourced:** the 9 K4c
   muscle pairs (and, mildly, the 5 skull bones) include geometry
   across the midline in one side's mesh; where the pair's own mesh
   also covers that territory, surfaces coincide and may z-fight.
   Nothing is silently corrected; affected records disclose their
   measured fraction in the panel.
4. **Hover picking costs a full id pass** per pointer-move frame
   (~2.88M triangles re-rendered offscreen). Click picking is exact
   and cheap by comparison; on weak GPUs hover may lag.
5. **Pack size:** 112.8 MB of `.bin` (muscles 94.6 MB) — positions
   are float32 by a fidelity-first choice. Fine on local disk;
   a quantized/compressed pack is future work before any network
   distribution.
6. **Frame unknowns carried from Milestone 3, unchanged:** ground
   placement is not applied (skeleton union min-y −7.05 cm, muscles
   −7.28 cm — the source origin, not the sole), AP origin
   unregistered, source pose not normalized (plantar-flexed feet,
   hanging arms). The viewer's home view targets the combined union
   centre, so the body is framed correctly despite this.
7. **stylopharyngeus** left/right y-extent asymmetry (1.264 cm),
   mechanism unidentified (K4c) — flagged, not explained away.

## 7. Next steps

1. First visual run + screenshot verdict (blocked on a drivable
   browser); then lighting/label tuning from what is actually seen.
2. Per-record edge ranges so wireframe follows the region filter.
3. Pose/ground registration decisions (Milestone 3 unknowns) before
   the muscular layer is posed against the skeleton interactively.
4. Quantized pack (per-mesh uint16 positions) to cut download size,
   with the same W-series checks re-run against it.
