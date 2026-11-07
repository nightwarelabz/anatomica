# Milestone 34 — Z-Anatomy nervous geometry: per-object provenance audit and registration derivation

Status: audit only, built and checked locally. No intake, no Body
Model data changes, nothing uploaded. This milestone produces the
evidence Milestone 33 §1(c) named as the unblock condition for the
Z-Anatomy route (OD-03.2): a per-object provenance audit of the
nervous-system objects in the upstream template, and a registration
derivation against BodyParts3D with measured residuals. It ends
with the decision that evidence puts in front of Chase.

**Outcome in one paragraph:** Bar 1 (provenance separability) is
**cleared for 555 of the 587 anatomical objects** in the template's
nervous-system collection — 34 measured as BodyParts3D-derived
geometry, 521 attributable to Z-Anatomy itself with stated evidence
— and **failed by 32 named objects** (the cortical gyri, whose
surface is a different model consistent with the named University
of Washington "Brainder" inclusion; the Dundee inner-ear objects,
which sit under a CC BY-NC-SA inclusion; the telencephalic white
matter, UW-named with license unstated; the colliculi, tentorium
and stria terminalis, which match nothing measurably). Bar 2
(registration) splits by region: a single global transform is
**refuted** (held-out centroid RMS 28.66 mm against a 2.0 mm
threshold), and per-bone ICP shows the skeleton was re-proportioned
part by part, so no bone-anchored route carries the limbs at nerve
scale — but the **brain assembly is a single intact block** in the
template, and a similarity fitted over its measured members
generalises to held-out members at **0.27 mm mean / 0.50 mm p95**.
Clearing both bars today: 34 BP3D-derived objects (redundant — the
project already holds that geometry from BodyParts3D directly) and
**236 Z-Anatomy-original objects in the cranial region**, among
them the curves of cranial nerves I, II, III, IV, V, VI, VII,
VIII, IX and XII and geometry for **19 of the 286**
geometry-absent FMA records.
The peripheral prize — 211 nerve curves of the spinal cord, plexuses
and limbs, covering 64 further FMA records — clears bar 1 only.

## 1. The artefact and the instruments

- **Source obtained in-session** from the upstream repository
  (Z-Anatomy/Models-of-human-anatomy, master): `Z-Anatomy.zip`,
  86,734,957 bytes, SHA-256
  `e029688545627bd0214b269e1063143abb580aad72b2c2445d6d8a9a0d9da736`,
  containing the template `Z-Anatomy/Startup.blend`
  (306,838,281 bytes, Blender 3.5 format), the upstream
  `License.txt`, the readme, and a TA2 table. The distributor GLB
  exports already in-tree (`data/sources/z-anatomy-glb/`) remain
  reference-only and were used only to validate the extractor.
- **Census** (tool: `tools/zanatomy_blend.py`, a streaming DNA-driven
  .blend parser written for this audit — Blender itself cannot load
  the 306 MB template on this machine's 7 GB of RAM): the file holds
  **7,184 objects** (4,569 mesh, 1,660 text, 951 curve, 3 lattice,
  1 armature) in 1,944 collections. The collection *7: Nervous
  system & Sense organs* holds **842 objects: 587 anatomical**
  (338 meshes, 249 curves) **and 255 non-anatomical helpers**
  (joint markers, label anchors, text labels). The peripheral nerves
  are **curves**, not meshes (bevel depth 0.0005 m throughout).
  Sided meshes share one datablock; the left copy is placed by a
  determinant −1 mirror matrix — the readme's "cloning symmetrical
  structures" is literal.
- **The template carries no provenance metadata at all.** All
  7,184 objects' custom properties were decoded: every key is a
  display or add-on flag (cross-section toggles, shader and
  measurement settings). No source, origin, author or license field
  exists on any object. The in-file text block `1.Licence` states
  the file is "a mixed and modified version of several open source
  files… Most of it comes from two different files made by
  BodyParts3D (CC BY-SA 2.1 Japan)" and lists Z-Anatomy's own
  contributions (mesh repair, weight reduction, symmetrical
  cloning, TA2 renaming/organisation, integrating missing
  structures, materials, muscular insertions); it does not mention
  the third-party inclusions. Those are named only in the
  repository `License.txt`: "Brainder" and "White matter"
  (University of Washington, **license not stated**), "Cranial
  Nerves and Foramina" (University of Dundee CAHID, **CC BY 4.0**),
  "Anatomy of the Inner Ear" (University of Dundee, **CC BY-NC-SA
  4.0**) and "Kidney" (CC BY-NC 4.0, not nervous), under the
  headline **CC BY-SA 4.0**.
- **Geometry extraction** (tool: `tools/zanatomy_extract.py`) loads
  object libraries without scene evaluation and dumps world-space
  vertices and curve splines; validated against the distributor
  GLB's world bounding boxes to ≤ 0.8 mm on test bones (the
  residual is version drift between the GLB export and the
  template). One data-quality finding: the template contains
  corrupt vertices (e.g. one frontal-bone vertex at z = −5.65e29);
  all correspondence work trims outliers by a percentile rule
  recorded in the tools.

## 2. Bar 1 — per-object provenance

**Method** (tool: `tools/zanatomy_correspond.py`; full table:
`MILESTONE-34-provenance.json`). For every anatomical object:
(a) a **name crosswalk** against every mesh-bearing BodyParts3D
concept in the project's geometry resolutions — audited at token
level, the misses are anatomical, not lexical (BodyParts3D has no
sulci, lemnisci, fasciculi, tracts or white matter; exactly one
synonym pair was needed, *aqueduct of midbrain* = *cerebral
aqueduct*); (b) for meshes with a BP3D counterpart, **two ICP
tests** initialised from the §3 global fit — free-scale similarity,
and rigid at the **model-pair scale** (the median fitted scale of
the confident fits: **1030.1**, i.e. the template's unit is
1/1030.1 of a BP3D millimetre; the figure was re-scaled to
≈ 175 cm) — with **both directions measured** (a sided object whose
forward fit is exact but whose reverse fit fails is a fragment;
sided pairs are then tested jointly against the whole concept, and
left objects under the mirror hypothesis). Bands: *same* = mean
≤ 1.0 mm, p95 ≤ 2.5 mm, reverse mean ≤ 2.0 mm, fitted scale within
±8 % of the pair scale (a p95-marginal sub-band to 3.0 mm is
reported as same with its numbers visible); *borderline* (mean
≤ 2.0, p95 ≤ 5.0) never rounds into a pass. (c) For nerve curves
with a BP3D mesh counterpart, a **course test** under the §3 brain
assembly transform. (d) The upstream inclusion list applied as
**suspicion, never proof**: a measured BP3D match overrides a named
region; an unmatched object inside an NC-named region fails.

**Results** (587 anatomical objects):

| Origin (measured / evidenced) | Verdict | Count |
|---|---|---|
| BP3D-derived, measured per object | cleanly attributable | 27 |
| BP3D-derived fragments, pair-union measured | cleanly attributable | 7 |
| Z-Anatomy-original by elimination | attributable with stated evidence | 515 |
| Z-Anatomy curve, course-consistent with BP3D | attributable with stated evidence | 2 |
| Z-Anatomy curve, course unresolved | attributable with stated evidence | 4 |
| Named third-party region (inner ear NC-SA; UW white matter) | **NOT separable** | 7 |
| Different geometry from the BP3D namesake | **NOT separable** | 13 |
| Borderline geometry | **NOT separable** | 7 |
| Fragment, pair-union fails | **NOT separable** | 5 |

- **The 34 clean objects** are the deep brain: caudate, putamen,
  globus pallidus, thalamus, hypothalamus, hippocampus, the
  ventricles, corpus callosum (the one p95-marginal case: mean
  0.88, p95 2.71, reverse 0.85), the commissures, habenula, optic
  chiasm and optic tracts, and — as fragments tiling one BP3D
  concept each — midbrain, pons, medulla and the left half of the
  optic chiasm. Many fits are vertex-exact (mean ≈ 0.00 mm at the
  pair scale). These objects are BP3D geometry carried through the
  template; the project already holds them from BodyParts3D
  itself.
- **The 515 elimination-class objects** have no BP3D counterpart to
  be derived from — spinal roots and cord tracts, plexus divisions,
  limb and autonomic nerves (as curves), brain nuclei Z-Anatomy
  added, cerebellar lobules, sulci — and sit in no named inclusion
  region. Their attribution is the template's own account
  (Z-Anatomy's listed contributions: integrating missing
  structures; converting vessels and nerves to curves — the second
  point corroborated by the LUMC AnatomyTool project history) plus
  the measured absence of any other candidate source. License
  consequence: **CC BY-SA 4.0** (the distribution's headline), with
  share-alike carried into the provenance ledger on any intake.
  The cranial-nerve curves deserve one note: the Dundee "Cranial
  Nerves and Foramina" inclusion (CC BY 4.0) cannot be isolated
  object-by-object from Z-Anatomy's own curve work — the two optic
  nerve curves are *measured* course-consistent with BodyParts3D's
  optic nerve meshes (median 0.67 / 0.69 mm), the trochlear curves
  deviate (median 5.4 mm) and the ophthalmic curves do not
  correspond at all (median 53 mm; whatever Z-Anatomy drew there,
  it is not the course of BodyParts3D's ophthalmic nerve) — so the
  curves are attributed to Z-Anatomy as distributed, with the
  Dundee attribution recorded alongside.
- **The 32 failures** (full list in the provenance table):
  - **18 cortical gyri** (superior/middle/inferior frontal and
    temporal, postcentral, precentral, superior parietal,
    angular, supramarginal — both sides): free-scale ICP shrinks
    them (fitted scales 465–966, all different), fixed-scale
    forward means 2.2–3.3 mm with reverse means 3.2–5.9 mm — a
    genuinely different cortical surface model, consistent with
    the named UW **Brainder** inclusion (FreeSurfer-derived), whose
    license no gathered document states. NOT separable.
  - **White matter of telencephalon .l/.r** (67,646 vertices each):
    UW-named inclusion, license unstated; BodyParts3D has no
    white-matter concept. NOT separable.
  - **Cochlea .l/.r, Vestibule .l/.r, and the un-sided Cochlear
    nerve mesh**: the Dundee inner-ear region, CC **BY-NC-SA** —
    non-commercial terms fail the license bar outright. This
    refines Milestone 33 §1(c)'s summary: the inner-ear model's
    objects do sit inside the nervous collection, and a cochlear
    nerve mesh with no BP3D counterpart sits with them. (The
    cochlear *nuclei* are brainstem objects, are not part of that
    inclusion, and classify as Z-Anatomy-original by elimination.)
  - **Colliculi (4), tentorium cerebelli (2), stria terminalis .l**:
    Z-Anatomy's objects are measurably larger/different from the
    BP3D concepts of the same name (pair-union tentorium fit: mean
    11.1 mm); no attribution the evidence supports. NOT separable.

## 3. Bar 2 — registration derivation

**Stated threshold** (in `tools/zanatomy_register.py`): held-out
centroid RMS ≤ 2.0 mm, held-out surface mean ≤ 1.0 mm, worst
surface p95 ≤ 3.0 mm — the nerves at stake are 1–5 mm structures
and BodyParts3D's own facet scale is ~1–3 mm, so a registration
must be at or below the resolution of the data it joins.

**Global similarity — REFUTED.** Fitted by Umeyama on the centroids
of 16 axial landmark bones (scale 980.36, rotation within 0.3° of
identity — the frames are already axis-aligned, template x+ =
subject left, y+ = posterior, z+ = up): train centroid RMS
**7.88 mm**; held-out (14 limb/girdle bones) centroid RMS
**28.66 mm**, surface mean-of-means **12.68 mm**, worst p95
**45.92 mm**. The template re-articulated the figure; no single
transform exists. Full per-landmark table:
`MILESTONE-34-registration.json`.

**Per-bone ICP — no general route.** All 30 landmarks fitted
individually (free scale, and fixed at the pair scale 1030.1),
each also split-half (fit on half the vertices, residuals on the
held half; full table `MILESTONE-34-bone-icp.json`). Free per-bone
scales scatter from 901 to 1030 in bone-specific clusters
(vertebrae ≈ 941–956, skull vault ≈ 1020–1028): the template
re-proportioned the skeleton part by part. Split-half held means:
skull vault 0.53–0.89 mm, vertebrae 0.77–1.09 (free) — but temporal
bones 3.0, mandible 2.9, hip bones 3.4, femur 3.3–3.6, tibia 4.7
(free) — above nerve scale in exactly the regions the peripheral
nerves run through. (The calcaneus free fit degenerates to zero
scale and is reported as a failed fit; its fixed-scale numbers,
1.76–2.00 mm, stand.)

**Brain-assembly similarity — DERIVED, held-out-validated.** The
27 individually measured brain objects were fitted *jointly*: one
similarity (scale **1030.96**) maps the template's brain block into
the BP3D frame with pooled residual mean **0.23 mm**, p95
**1.13 mm** over 7,556 points. Split-half by object — fit on 14
objects, tested on the 13 never fitted: scale 1030.75, residual
mean **0.27 mm**, median 0.26, p95 **0.50 mm**. The template kept
BodyParts3D's brain assembly intact as a unit (rescaled once),
which is why this transform exists while the global one does not.
Its region of validity is the cranial cavity; membership for
clearance is operationalised as an object's centroid falling
inside the matched objects' centroid bounding box expanded by
50 mm (box and rule recorded in `MILESTONE-34-clearance.json`).

## 4. Final clearance list

(Tool: `tools/zanatomy_clearance.py`; machine list:
`MILESTONE-34-clearance.json`.)

| Tier | Meaning | Objects | Of them curves | FMA records given geometry |
|---|---|---|---|---|
| **A** | Both bars — BP3D-derived, measured | 34 | 0 | 0 (maps to the 133 BP3D records instead) |
| **B** | Both bars — Z-Anatomy-original, inside the validated assembly region | **236** | 38 | **19** |
| **C** | Bar 1 only — attributable, no validated transform covers its location | 285 | 211 | 64 |
| **D** | Neither — NOT separable | 32 | 0 | 0 |

- **Tier B** (236) is the cranial block: brain nuclei and tracts
  Z-Anatomy added, cerebellar lobules, sulci, meninges (falx
  cerebri), and 38 curves — the cranial nerves I, II, III, IV,
  V (with its divisions and branches), VI, VII, VIII (the
  vestibular and cochlear nerves), IX and XII, plus chorda
  tympani and the buccal and lingual nerves. The 19 FMA records it
  covers are the cranial nerves (I, III, V, VI, VII, VIII, IX,
  XII, both sides) plus the falx. Two recorded caveats ride with
  this tier: the trochlear (IV) curves sit in the region but carry
  the §2 course discrepancy (5.4 mm median from BodyParts3D's
  trochlear course), and the cortical-surface objects in the tier
  (sulci, partial gyri) are Z-Anatomy's own drawings on the
  non-BodyParts3D cortical model — their *placement* is validated
  by the assembly transform; their surface fidelity has no
  reference to be validated against. Sense-organ objects sharing
  the collection (retina, eyeball segments, tympanic membrane,
  auditory tube — 10 objects) are in this tier and flagged as
  sense-organ scope in the table.
- **Tier C** (285) is the actual peripheral prize: 211 curves —
  spinal nerve roots and rami, the cauda equina, every plexus
  division, the named limb and autonomic nerves — plus 74 meshes
  (spinal cord tracts and horns, eyeball segments, lacrimal
  apparatus). Attributable today; placeable only by a derivation
  that does not yet exist at nerve scale (§3: bone-anchored
  per-part ICP measures 2–4.7 mm in the limbs).
- **Tier D** (32) is the §2 failure list. Nothing in it is
  intakeable under any reading of the evidence.
- Name-level correspondence was found for **83 of the 286** FMA
  records (19 in B, 64 in C); the remaining 203 records (finer
  branches and autonomic subdivisions) have no Z-Anatomy object of
  the same name — Z-Anatomy geometry, even fully cleared, was
  never going to cover the whole FMA tranche.

## 5. The decision this puts in front of Chase

Intake, or not, of the cleared subset — concretely:

1. **Intake Tier B now** (236 objects; 19 FMA records gain
   geometry; the remaining 217 objects are cranial structures
   beyond the M33 tranche): extraction from the upstream template
   by the tools in this milestone, placement by the recorded
   brain-assembly transform (scale 1030.96, held-out 0.27 mm
   mean), provenance recorded per object in the ledger under
   **CC BY-SA 4.0 attribution/share-alike handling** (Z-Anatomy's
   attribution carried on every derived artefact; the Dundee
   cranial-nerves attribution recorded alongside the cranial
   curves), with the two tier caveats (trochlear course, cortical
   surface fidelity) written into the records' verify flags.
2. **Commission the Tier C derivation as its own milestone**
   (285 objects; 64 FMA records): a per-region registration that
   beats the measured bone-anchored numbers — the audit's evidence
   says this needs anchors beyond bone ICP (muscle-part anchors or
   a non-rigid derivation), and it is unproven work, scoped and
   gated by the same held-out thresholds used here.
3. **Decline Z-Anatomy geometry entirely**: the 286 FMA records
   stay geometry-absent; the nervous gap stays as Milestone 33
   left it.

Tier A is not a decision: it duplicates BodyParts3D geometry the
project already holds. Tier D is not a decision: it failed.

## 6. Deliverables and tree state

New files (all local; nothing uploaded): `MILESTONE-34.md`,
`MILESTONE-34-provenance.json` (the full 842-object table),
`MILESTONE-34-clearance.json`, `MILESTONE-34-registration.json`,
`MILESTONE-34-bone-icp.json`, and the re-runnable tools
`tools/zanatomy_blend.py`, `tools/zanatomy_extract.py`,
`tools/zanatomy_register.py`, `tools/zanatomy_correspond.py`,
`tools/zanatomy_clearance.py`. No file under `data/` was created,
modified or deleted; the upstream download lives outside the
project tree (`~/workspace/zanatomy-m34/`).

Checker matrix, run after the audit (the tree is untouched —
every result at its standing baseline): assembly
`ALL GATED CHECKS PASS`; web `verify_web.js` `ALL CHECKS PASS`;
cases **5,145 passed, 0 failed**; theatre **245 checks,
0 failures**; physiology `cargo test --release` **25 passed,
0 failed** (all hard gates); native verify **99/99 data
assertions PASS** (the GPU render stage cannot initialise on
this machine — no wgpu adapter — the standing disclosed
limitation, unchanged).
