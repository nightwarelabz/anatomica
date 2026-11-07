# ANATOMICA — Milestone 16: Shells integration — all 11 system layers in both shells

**State: built and verified locally. Not uploaded (per-item approval stands).**

Milestone 15 closed the Body Model v1 census as *data*: 1,552 inventory
records across 11 systems, 1,545 with geometry, 361 clinical records. Only
two of those systems (skeletal, muscular) had ever reached a shell. This
milestone carries the remaining nine systems through the full pipeline —
assembly, packing, and presentation — so that both shells now present the
complete Body Model v1: every system is a layer, every record is listed,
every clinical record is reachable from its geometry, and the pick codec
that Milestone 7-FIX repaired is regression-gated across all eleven layers.

## 1. What was built

- **`tools/assemble_systems.py`** (new) — generalized assembler for the
  nine Milestone 5/9–15 systems, following the M3/M6 pattern exactly:
  IS-A meshes are a record's geometry; PART-OF meshes are used only where
  IS-A is empty (the sternum/heart/brain/lung/liver pattern — 87 records
  across the nine systems are PART-OF-sourced); byte-identical-geometry
  duplicates inside one composition are de-duplicated (13 occurrences:
  cardiovascular 5 records, digestive 2, respiratory 1, skeletal's hyoid
  precedent). One rule from M6 does **not** generalize and is recorded as
  such: for 65 records (62 cardiovascular, 2 nervous, 1 digestive) the
  PART-OF tree carries files *beyond* the IS-A set — descendant rollups
  (a branch vessel's PART-OF set contains its sub-branches' meshes, which
  are other records' own geometry). Those files are set aside, counted,
  and listed in each assembly's meta (`partof_rollup_records`); assembling
  them would double-draw other records' geometry. Outputs:
  `data/<system>/<system>-assembled.json` × 9, canonical-frame bboxes
  computed from actually-transformed vertices. Skeletal/muscular
  assemblies were not regenerated (verified M3/M6 outputs; the checker
  below verifies all 11 uniformly).
- **`tools/assembly_check_all.py`** (new) — generalized assembly checker
  for all 11 systems (§3).
- **`tools/pack_geometry.py`** (new) — successor to
  `tools/pack_web_geometry.py` (kept as the M6 record). Packs all 11
  layers into ANW1 v2 packs (format unchanged), writes `records.json`
  and `manifest.json`. Sections stream through temp files and the
  unique-edge set is built in 256 key-ordered buckets, so peak memory
  stays bounded where the M6 tool held whole layers in RAM. A `--check`
  mode re-derives every header/manifest number without packing.
- **Web shell** (`web/viewer.js`, `web/index.html`) — generalized from
  2 hardcoded layers to the manifest's 11: layer toggles generated from
  the manifest (skeletal + muscular on by default; the opaque
  integumentary shell starts off so it does not hide the interior),
  unified layer keys (the M6 skeleton/muscles vs skeleton/muscle naming
  asymmetry is abolished — one key per system everywhere), region filter
  and search across all layers, specialized panels kept for skeletal
  (Phase-1 fields) and muscular (M4 clinical fields), a generic clinical
  panel renderer for the other nine systems' tranches (authored field
  shapes rendered recursively; sources, notes and verify flags in full),
  badges for no-geometry / inventory-only / clinical-only / variant
  records with verify counts summed across linked clinical records.
  The pick codec is byte-for-byte the Milestone-7-FIX codec (FS_PICK
  unchanged in behaviour; the decoder resolves the layer bit through
  the generalized LAYER_BIT table).
- **Native shell** (`native/`) — the hardcoded `LayerKind` enum is
  gone: layers are `LayerInfo` values read from the manifest
  (`layer_order`, per-layer pick bit / label / colour — the manifest is
  now the single source of truth for all three in both shells).
  Visibility is a key set; a focus set dims non-focus layers through
  the selection machinery (slot `u32::MAX` matches nothing). Packs are
  asserted at startup and loaded transiently, so resident memory no
  longer holds eleven decoded packs. Verify mode renders 10 frames
  (§5); view mode toggles layers by S/M, digits 1–0 in manifest order,
  I (integumentary), A (all). `cargo build` + `cargo build --release`
  green with zero warnings; `cargo test` 8/8.
- **`tools/verify_web.js`** — generalized W1–W6 over all 11 layers (§4).

## 2. Census reconciliation — exact

Listed records per system in the shells = inventory + clinical-only +
variants, derived independently from the source files by the verifier
(W1/W5), not copied from this table:

| system | inventory (M15 census) | with geometry | clinical (A/B/C) | listed in shells |
|---|---|---|---|---|
| Skeletal | 206 | 199/206 | — | 206 |
| Muscular | 359 | 359/359 | 127 (51/63/13) | 360 (359 + multifidus clinical-only) |
| Cardiovascular | 646 | 646/646 | 69 (47/3/19) + 8 variants | 659 (646 + 5 clinical-only + 8 variants) |
| Nervous | 133 | 133/133 | 52 (13/34/5) | 162 (133 + 29 clinical-only) |
| Respiratory | 83 | 83/83 | 37 (37/0/0) | 94 (83 + 11) |
| Digestive | 93 | 93/93 | 31 (30/1/0) | 95 (93 + 2) |
| Urinary | 6 | 6/6 | 6 (6/0/0) | 6 |
| Lymphatic | 4 | 4/4 | 4 (2/2/0) | 6 (4 + 2) |
| Endocrine | 3 | 3/3 | 6 (5/1/0) | 7 (3 + 4) |
| Reproductive | 13 | 13/13 | 16 (7/8/1) | 22 (13 + 9) |
| Integumentary | 6 | 6/6 | 13 (11/0/2) | 13 (6 + 7) |
| **Total** | **1,552** | **1,545/1,552** | **361 (209/112/40)** | **1,630** |

The clinical map in `records.json` holds 369 entries = 361 clinical
records + 8 variants; every entry in every system's `clinical_ids`
resolves (W5). The 7 geometry exceptions are exactly the M3 set —
coccyx, malleus/incus/stapes ×2 — re-derived from the geometry file by
W5, not hardcoded. No count anywhere differs from the Milestone 15
census; there were no mismatches to explain.

## 3. Assembly check (tools/assembly_check_all.py — 75 PASS, 0 FAIL, 102 findings reported)

- **A1** record sets and census counts exact for all 11 systems.
- **A2** every assembled bbox equals the corner-transformed union of its
  meshes' stored source boxes — worst diff **0.00 cm** on all 11 systems
  (independent computation path: stored boxes, not re-streamed vertices).
- **A3** layer coherence vs the skeletal envelope (union 64.785 ×
  170.675 × 25.405 cm): **zero records in any layer are disjoint from
  the skeletal union + 2 cm** — the gated part. Exceedances are measured,
  not gated: cardiovascular reaches 0.049/0.051 cm past the skeletal
  width and 0.210 cm below its base (fingertip and toe vessels in soft
  tissue past the bone tips); integumentary exceeds on every axis
  (x +0.889/+1.021, y +0.763/+1.536, z +2.725/+1.074 cm) — skin lies
  outside bone, as it must. The muscular A3 line reproduces Milestone
  6's numbers exactly (min-y +0.233, min-z +0.187).
- **A4** mirror symmetry, gate redesigned on evidence (documented in the
  checker): the gated statistic is now **transform invariance** — each
  pair's canonical-frame mirror deviation must equal 0.1× its
  source-frame deviation; worst error across all 505 pairs is
  **2.3×10⁻¹⁴ cm**. The M6 distributional gate (median ≤ 0.1, p90 ≤ 0.5)
  conflated transform correctness with source symmetry; skeletal
  (0.022/0.134) and muscular (0.000/0.144) still pass it, and it is
  reported for every system. The new systems' distributions are source
  anatomy, characterized in the checker's output: cardiovascular median
  0.003 cm with a long tail (49/168 pairs ≥ 1 cm — visceral name-pairs
  such as the hepatic lobes, colic arteries and portal branches are not
  mirror anatomy; the left renal vein's 2.48 cm deviation is correct
  anatomy, since it crosses to the IVC); respiratory median 1.95 cm
  (bronchopulmonary segments are genuinely asymmetric — 10 right vs 11
  left segments, and the worst pair, the anterior segments at 23.1 cm,
  is a source segmentation artifact carried as found); nervous is
  uniformly ~0.13 cm (a tight distribution — the source brain meshes'
  own slight asymmetry; the skull pairs in the same region sit at
  0.02 cm median, so it is not a frame shift). One named source anomaly:
  **both ascending lumbar veins lie entirely across the midline from
  their labels** (100% cross-midline vertices each) — a source
  labelling property, assembled as found.
- **A5** (report-only, M6 K5 precedent) records intersecting no bone
  bbox: muscular 11 (the M6 laryngeal set, identical), respiratory 13
  (laryngeal cartilages/ligaments — cartilage suspended between bones),
  cardiovascular 14 (deep abdominal/pancreatic branches, penile vein),
  reproductive 6 (external genitalia, testes), integumentary 2 (hair),
  all other systems 0.
- **A6/A7/A8** no NaN/Inf anywhere; per-system totals equal the geometry
  files' chosen compositions occurrence-for-occurrence (including the
  13 de-duplicated occurrences); clinical counts equal the census for
  all 10 tranche systems.

Two source findings the assemblies make visible:
- **The nervous layer is head-only.** BP3D's spinal-cord record carries
  a single 3.6 cm thread-like mesh at y 145.9–149.4 (the same file as
  the central canal record); the layer's union is 13.9 × 17.2 × 19.6 cm
  inside the head. There is no cord running the vertebral column in the
  release — the M9 concept gap, now visible in the shells.
- The integumentary union (66.694 × 172.974 × 29.203 cm) is the body's
  outer bound in both shells' framing.

## 4. Packs and web verification

Per-layer packs (ANW1 v2, canonical cm), all written by
`tools/pack_geometry.py` and re-derived by three independent readers
(the packer's `--check`, `tools/verify_web.js`, and the native
shell's startup assertions — 99/99 PASS, 9 per layer):

| layer | bytes | vertices | faces | unique edges | records |
|---|---|---|---|---|---|
| skeletal | 18,190,236 | 283,091 | 511,968 | 798,084 | 199 |
| muscular | 94,585,848 | 1,704,260 | 2,365,492 | 4,014,327 | 359 |
| cardiovascular | 74,688,188 | 1,164,695 | 2,103,182 | 3,269,497 | 646 |
| nervous | 40,059,000 | 624,682 | 1,125,178 | 1,757,887 | 133 |
| respiratory | 19,199,216 | 318,838 | 515,680 | 829,271 | 83 |
| digestive | 46,780,860 | 844,763 | 1,175,774 | 1,972,023 | 93 |
| urinary | 350,920 | 5,402 | 9,944 | 15,428 | 6 |
| lymphatic | 197,044 | 3,099 | 5,490 | 8,632 | 4 |
| endocrine | 254,368 | 3,758 | 7,454 | 11,204 | 3 |
| reproductive | 511,644 | 10,787 | 11,026 | 20,433 | 13 |
| integumentary | 9,550,572 | 161,107 | 256,186 | 406,759 | 6 |
| **total** | **304,367,896 (290.3 MiB)** | **5,124,482** | **8,087,374** | **13,103,545** | **1,545** |

Continuity: the regenerated skeletal and muscular packs are byte-size
identical to Milestone 6's (18,190,236 and 94,585,848 B) — same inputs,
same format. `records.json` is 1,727,037 B; `manifest.json` 396,195 B.
Packs are build products and stay out of git, as at M6.

`node tools/verify_web.js` — **ALL CHECKS PASS (41 PASS lines)**:
W1 layer set/bits/literals/counts; W2 headers/offsets for all 11 packs;
W3 packed bboxes vs records.json (worst diff 7.57×10⁻⁶ cm — the same
float32 floor M6 measured), slot ids and per-record index ranges clean
across 24.3M indices; W4 totals vs geometry compositions; W5 records
consistency (1,545 geometry records listed exactly once, clinical-only
and variant sets equal to source-derived sets, 369-entry clinical map,
no-geometry set exact); **W6 the pick codec: the shipped FS_PICK
encoder expressions and the shipped pick() decoder block are parsed
out of `web/viewer.js` and executed — all 1,545 slots roundtrip to
their own records, the miss pixel and an unknown layer bit (200) both
decode to null.** The M7-FIX regression gate now covers every layer.

Draw-call accounting (web shell): one draw per visible layer per frame
unfiltered (2 in the default skeletal+muscular view; 11 with all layers
on), plus one LINES draw per visible layer with wireframe on; a region
filter replaces the merged draw with per-record range draws of the
matching records; picking is an on-demand id pass, not a per-frame
cost. Native shell: one `draw_indexed` per visible layer per pass
(+1 wireframe draw per layer when enabled) — the all-layers frame is
11 draws for 8,087,374 triangles.

## 5. Native verification (llvmpipe, release, 1024×1024)

Adapter: llvmpipe (LLVM 20.1.2, GL backend, Cpu device) — the M7
adapter. GPU upload 5,304 ms for 11 layers. `anatomica verify` exit 0:
**ALL HARD CHECKS PASS** — 99/99 pack/manifest assertions; silhouette
gates (GPU silhouette vs CPU projection of the same packs, ≤ 2 px):
front/side/top skeleton worst 1.08/1.30/1.45 px (M7's numbers were
≤ 1.45), **front_all_layers worst 1.00 px**, **front_skin worst
1.00 px**. Skeletal union reproduced exactly (64.785 × 170.675 ×
25.404 cm). Frame times are llvmpipe software-rasterizer floors with
large run-to-run variance (two full runs taken; the second run's
figures): front_skeleton 1,814 ms, side 518, top 907, close_skull 561,
front_combined 1,946, front_selection 311, front_all_layers 5,736,
front_cv_nervous_focus 7,291, front_cv_nervous 3,704, front_skin 918;
readback 1–2 ms (one 68 ms first-frame outlier). These numbers
characterize the CPU rasterizer, not the data path — M7's guidance
stands.

Picking, all at pixel level through the real id pass:
- skeletal+muscular state (the M7 setup): forehead → **skeletal slot
  0, Frontal bone**; thigh → **muscular slot 77, right vastus
  medialis** — M7's exact results.
- all-layers state: forehead → **integumentary slot 0, skin** (the
  shell covers the forehead — layer-correct).
- cardiovascular+nervous state: heart-centre probe → **cardiovascular
  slot 629, right ventricle** (the anterior chamber is what a frontal
  ray meets first — anatomically correct).
- corner probe → no hit; range-restricted self-consistency re-render
  returns the same id (PASS). Record panels print for the picked
  frontal bone, the femur, and the heart (with its five verify flags
  in full).

Frame verdicts (visually inspected):
- **front_skin** — the integumentary layer alone: a complete, coherent
  body surface — face with features, hair shell at the scalp, trunk
  relief carried by the source skin mesh, hands, feet, toes. The layer
  is a true outer shell, which the A3 exceedances already promised.
- **front_all_layers** — the same body; the opaque skin shell occludes
  the interior, with small flashes of interior layers where source
  meshes reach or cross the surface (muscle at the neck, a respiratory
  tip at the nose, vessel/muscle specks at the flank and medial knees).
  The source layers share a frame; they were not modeled to nest
  perfectly, and the frame shows that honestly.
- **front_cv_nervous** (cardiovascular + nervous only) — the vascular
  tree is complete and coherent: arch branches, the heart, dense
  thoracic/abdominal branching, iliac bifurcation, runoffs to hands
  and feet. Above the neck it is joined only by the yellow brain —
  **the nervous system's absence below the head is visible at a
  glance** (see §3).
- **front_cv_nervous_focus** (all layers, focus = CV + nervous) — the
  focus mechanism works (non-focus layers at 22% brightness) but, as a
  front view, it cannot show the heart or brain through the still-
  opaque dimmed skin shell; the focus layers read only where they
  reach the surface (optic structures glinting in the orbits, leg
  vessels). Dimming is not transparency — recorded as a limitation,
  §6. The isolated-layers frame above is the informative CV+nervous
  view today.
- **front_combined / front_selection** — M7 continuity: the écorché
  (skull, sternum, spine, patellae, hand/foot bones through the muscle
  layer) and the femur selection highlight with dimming both render
  as before.

## 6. Known defects and limitations

1. **Focus-dimming is not transparency** (above). A highlighted-systems
  view that reads through the shell needs per-layer opacity or
  shell-off pairing; the shells' layer toggles already allow the
  manual version (shell off, systems on).
2. **Web shell not exercised in a real browser on this VM** — the
  standing M6/M7 limitation. What is proven: the data files by three
  independent readers, the viewer's decoder by verbatim execution
  (W6), the codec at pixel level natively, and the scene itself by
  the native renders of the same packs. Rendered-pixel web picking
  remains unexercised.
3. **Web data weight**: the access tier now downloads 290.3 MiB of
  packs + 2.1 MB of JSON. No compression or streaming exists yet;
  on a slow connection the layer-by-layer load (with progress) is
  the only mitigation. Pack compression / level-of-detail is future
  work, not attempted here.
4. **Source geometry intersections**: interior meshes protrude through
  the skin shell at a few small spots (§5). This is source data as
  modeled, shown as sourced per the precision law — not corrected.
5. **View mode** (winit window) still cannot run on this headless VM;
  it compiles warning-free and shares the verified draw code, as at
  M7. Its layer keys are documented in the source header.
6. The nervous layer's head-only extent, the ascending-lumbar
  labelling, the bronchopulmonary segment asymmetries (§3) are
  dataset properties carried from BP3D, flagged here and in the
  checker output — resolving them needs the dataset source decision
  already standing from M9–M15 (a nerve/full-FMA source), not shell
  work.
7. `records.json` region values for the newer systems come from each
  tranche's own grouping (`subtree` for inventory records, `group`
  for clinical-only records) — serviceable for filtering, not a
  unified regional ontology. Unifying region vocabulary across
  tranches is data work for a later milestone.

## 7. Next steps

1. The Theatre: procedures authored against this Body Model, now that
  every system is present and pickable in both shells.
2. Per-layer opacity in both shells (defect 1) — small, shared-uniform
  change; makes focus views clinically readable.
3. Pack delivery for the web tier: compression and/or progressive
  per-layer streaming (defect 3) before any public hosting.
4. Dataset blockers unchanged and quantified (nerves first): a source
  beyond BP3D 4.0 + TS v1 — the full-FMA/TA pass remains the named
  route; the TA2 `ta_name` pass is still owed across all tranches.
5. Physiology: venoconstriction / transcapillary-refill modeling
  (M8's named next step), now with the full cardiovascular layer
  pickable in both shells as its anatomical front end.
