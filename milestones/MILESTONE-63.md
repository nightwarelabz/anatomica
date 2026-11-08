# Milestone 63 — Tier B geometry intake + deferent-duct claim

Executes the geometry ruling of 2026-11-08 on the Milestone 34
Z-Anatomy audit: **Tier B intake proceeds; the deferent-duct mesh
pair is claimed; Tier C is not intaken (it stays gated on a
derivation that validates against the audit's held-out criteria);
Tier D is excluded permanently.** No Tier C object and no Tier D
object was intaken, under any justification. One Tier B object was
excluded at intake on re-examination (§3). The Body Model inventory
is unchanged at 2,236 records; records gained geometry, none were
created. Records with geometry: **1,545 → 1,566** (measured, §6).

## 1. Transform re-verification (recomputed, not cited)

The audit's brain-assembly similarity transform was re-derived from
scratch before any intake: fresh Blender census of the template
(842 nervous-collection objects: 460 MESH / 249 CURVE / 133 FONT —
identical to the audit), fresh extraction
(`tools/zanatomy_extract.py`), and fresh runs of
`tools/zanatomy_correspond.py` and `tools/zanatomy_clearance.py`.
The recomputation is **bit-identical** to the landed audit:

- scale **1030.957191** (Δ 0.0), rotation and translation identical
  to the last bit;
- pooled fit: 7,556 points, residual mean **0.2276 mm**, p95
  **1.1280 mm**;
- split-half held-out (14 fit / 13 test): scale 1030.746371,
  residual mean **0.2739 mm**, median **0.2639 mm**, p95
  **0.4998 mm**;
- verdict census identical (521 attributable / 255 helpers /
  34 clean / 32 NOT separable); all 842 per-object verdicts,
  origins, concepts and curve courses identical; tier sets
  A/B/C/D identical; `fma_hits.B` identical.

Independent placement check (new at this milestone, recorded in
the intake manifest): each of the 27 measured brain-assembly
members was placed by the single shared transform and its vertices
measured against its BodyParts3D mesh — surface distance mean per
object **0.043–1.190 mm, median 0.261 mm** (worst member: lateral
geniculate body, left, mean 1.190 mm). The intake therefore rests
on a transform re-verified three ways: bit-identical re-derivation,
the audit's held-out protocol reproduced exactly, and per-member
surface measurement under the shared transform.

## 2. What was built

- `tools/zanatomy_extract_full.py` (new): full-geometry extraction
  of Tier B objects from the template (world-space vertices +
  loop triangles for meshes, winding corrected where the world
  matrix mirrors; splines + bevel + world scale for curves).
  Vertex counts match the fresh census for all 236 objects; no
  corrupt (|coord| ≥ 2) vertices exist in any Tier B mesh, so no
  trimming was needed anywhere.
- `tools/zanatomy_intake.py` (new): builds the derived OBJ set,
  writes the intake manifest, and performs both record
  re-filings. Every mesh statistic it writes into a geometry
  entry is measured by streaming the OBJ file it names. The tool
  is idempotent: a second full run reproduced all four data
  JSONs byte-identically (SHA-256 verified).
- `data/sources/z-anatomy-derived/` (new, 239 files, 18 MB): the
  landed source of record for the derived geometry (the 306 MB
  upstream `.blend` is not redistributable in-tree): 235 OBJ
  files, `SOURCE.md`, `intake-manifest.json` (per-object
  provenance chain, measured counts/bbox, SHA-256, attachment,
  flags), and the provenance ledger (`ledger.json`,
  `ledger-summary.md`; 237 pinned entries — the 235 OBJ files
  plus SOURCE.md and the manifest — CC BY-SA 4.0, 0
  unknown-license files).

## 3. Tier B intake — 235 of 236 objects; one exclusion

Construction: mesh objects carry their template datablock
geometry, transformed; curve objects are rendered as tubes at the
template's own bevel radius (0.0005 template units ≈ **0.515 mm**;
the single exception is flagged below; parallel-transport frames,
8 radial segments, capped ends; Bezier splines sampled 16 steps
per segment). All 235
centroids sit inside the audit's assembly region (its own
criterion: the matched-centroid box + 50 mm margin).

**Exclusion — `Cochlear nerve.l`** (curve, unattached): its
elimination origin cannot exclude the one alternative source that
matters — it sits in the Dundee inner-ear named region
(**CC BY-NC-SA**), and its un-sided mesh namesake (`Cochlear
nerve`) is adjudicated to that region in Tier D. For the
cranial-nerve-region curves the same logical gap is harmless (the
Dundee cranial inclusion is CC BY 4.0 — intake-compatible under
either attribution, recorded alongside in each manifest chain);
here the alternative attribution is license-incompatible, so the
object's Bar-1 status is ambiguous with consequence, and the
standing rule — never resolve ambiguity in intake's favour — was
applied. The exclusion is pinned in the intake tool and recorded
in the manifest. It maps to no record; no other intake depends on
it. No other object raised a Bar-1 question on re-examination:
the fresh recompute matched the audit on all 842 objects.

Flagged objects carried openly in the manifest: the trochlear
curves (§7) and the ophthalmic curves (course non-correspondence,
median 53 mm; intaken unattached, flagged, not resolved).
`Central canal'` carries the set's only non-standard bevel
(0.0015 → tube radius 1.546 mm), flagged on its manifest entry.

Provenance discipline: Z-Anatomy as distributed is **not** a
product source (parts are CC BY-NC-SA and excluded). Each intaken
object's eligibility rests on its audit Bar-1 chain, stated per
object in the manifest: 231 objects Z-Anatomy-original by
elimination (16 of them cranial-nerve curves with the Dundee
CC BY 4.0 attribution recorded alongside), 2 curve-course-
consistent (the optic nerve curves), 2 curve-course-unresolved
(trochlear). License carried: CC BY-SA 4.0 (the distribution's
headline), share-alike, per the ledger.

A name screen of the 217 unattached objects against every
geometry-absent record in all eleven system inventories found
**zero** further correspondences: the 19 attachments below are
the complete record-level intake, and the remaining 217 objects
are held as derived assets only.

## 4. Per-record intake table (the 19)

All 19 records are Milestone 33 FMA concept records
(`source: fma-5.1.0`); all 19 objects' provenance is
Z-Anatomy-original by elimination (16 of the 18 curves carry
the Dundee cranial-nerves attribution recorded alongside, §3;
the maxillary pair's audit rows carry no named region, and the
falx is a mesh with none). None of the
19 has a BodyParts3D counterpart to measure a course against —
placement rests on the assembly transform of §1 (held-out mean
0.274 mm / p95 0.500 mm) for every row. Post-intake, the nine
sided pairs also pass the assembly mirror-symmetry gate
(tools/assembly_check_all.py A4 nervous: 58 pairs, worst
transform deviation 1.7e-14 cm, 0 pairs ≥ 1.0 cm).

| Record | Object | Kind | Vertices | Faces |
|---|---|---|---|---|
| nerve.falx-cerebri | Falx cerebri | mesh | 844 | 1,675 |
| nerve.left-abducens-nerve | Abducens nerve (VI).l | curve (tube) | 2,196 | 4,384 |
| nerve.right-abducens-nerve | Abducens nerve (VI).r | curve (tube) | 2,196 | 4,384 |
| nerve.left-facial-nerve | Facial nerve (VII).l | curve (tube) | 12,152 | 24,256 |
| nerve.right-facial-nerve | Facial nerve (VII).r | curve (tube) | 12,152 | 24,256 |
| nerve.left-glossopharyngeal-nerve | Glossopharyngeal nerve (IX).l | curve (tube) | 5,958 | 11,888 |
| nerve.right-glossopharyngeal-nerve | Glossopharyngeal nerve (IX).r | curve (tube) | 5,958 | 11,888 |
| nerve.left-hypoglossal-nerve | Hypoglossal nerve (XII).l | curve (tube) | 7,248 | 14,464 |
| nerve.right-hypoglossal-nerve | Hypoglossal nerve (XII).r | curve (tube) | 7,248 | 14,464 |
| nerve.left-maxillary-nerve | Maxillary nerve.l | curve (tube) | 3,506 | 6,992 |
| nerve.right-maxillary-nerve | Maxillary nerve.r | curve (tube) | 3,506 | 6,992 |
| nerve.left-oculomotor-nerve | Oculomotor nerve (III).l | curve (tube) | 3,910 | 7,792 |
| nerve.right-oculomotor-nerve | Oculomotor nerve (III).r | curve (tube) | 3,910 | 7,792 |
| nerve.left-olfactory-nerve | Olfactory nerve (I).l | curve (tube) | 12,006 | 23,920 |
| nerve.right-olfactory-nerve | Olfactory nerve (I).r | curve (tube) | 12,006 | 23,920 |
| nerve.left-trigeminal-nerve | Trigeminal nerve (V).l | curve (tube) | 1,044 | 2,080 |
| nerve.right-trigeminal-nerve | Trigeminal nerve (V).r | curve (tube) | 1,044 | 2,080 |
| nerve.left-vestibulocochlear-nerve | Vestibulocochlear nerve (VIII).l | curve (tube) | 788 | 1,568 |
| nerve.right-vestibulocochlear-nerve | Vestibulocochlear nerve (VIII).r | curve (tube) | 788 | 1,568 |
| **Total** | | | **98,460** | **196,363** |

(Left/right counts are identical per pair because the template's
sided objects are mirror constructions with equal spline/segment
counts; their geometry is not identical — bounding boxes mirror,
and the A4 gate above measures the sided deviations.)

## 5. Deferent-duct claim accounting

Under the Milestone 40 adjudication (the pair is the Body Model's
only inventory↔geometry collision: BP3D carries FMA19235/FMA19236
under the preferred name "deferent duct"), the two Milestone 38
records were re-filed as geometry-carrying over the real
BodyParts3D 4.0 meshes, measured by streaming the shipped files:

- `repro.left-deferent-duct` ← **FJ3135**: 863 v / 1,110 f
  (exactly the Milestone 40 figures);
- `repro.right-deferent-duct` ← **FJ3140**: 787 v / 944 f
  (exactly the Milestone 40 figures).

Claim alone: **1,545 → 1,547**. With Tier B's 19: expected 1,566;
**measured 1,566** (§6) — no difference to reconcile.

## 6. Before/after census (measured)

| Measure | Before | After | Δ |
|---|---|---|---|
| Inventory records | 2,236 | 2,236 | 0 |
| Records with geometry | 1,545 | **1,566** | +21 |
| Concept-only records | 691 | 670 | −21 |
| Nervous records with geometry | 133 | 152 | +19 |
| Reproductive records with geometry | 13 | 15 | +2 |
| Atlas triangles (pack faces, 11 layers) | 8,087,374 | **8,285,791** | +198,417 |
| Nervous layer vertices / faces | 624,682 / 1,125,178 | 723,142 / 1,321,541 | +98,460 / +196,363 |
| Reproductive layer vertices / faces | 10,787 / 11,026 | 12,437 / 13,080 | +1,650 / +2,054 |
| Canonical pack bytes (11 packs) | 304,367,896 | **311,136,996** | +6,769,100 |
| Nervous pack bytes | 40,059,000 | 46,740,940 | +6,681,940 |
| Reproductive pack bytes | 511,644 | 598,804 | +87,160 |
| Gzip delivery bytes (11 packs) | 117.6 MiB (M16 published) | **125,760,132** | — |
| records.json listed records | 2,314 | 2,314 | 0 (21 gained slots) |
| W6 pick-codec slot cases | 1,545 | **1,566** | +21, 0 failures |

The other nine layers' canonical packs are byte-identical to
their pre-milestone bytes after a full repack (deterministic
repack; SHA-256 census, §8).

## 7. Named flags carried, not absorbed

- **Trochlear 5.4 mm discrepancy**: the Z-Anatomy trochlear
  curves deviate from BodyParts3D's trochlear course (median
  5.389 mm, p95 13.402 mm under the assembly transform). The
  flag is carried on the records themselves: both
  `nerve.left-trochlear-nerve` and `nerve.right-trochlear-nerve`
  now carry an inventory `note` stating the discrepancy, that
  their geometry remains their BodyParts3D mesh, and that the
  Z-Anatomy curve is intaken unattached with the flag in the
  manifest. The trochlear records' geometry is byte-identical
  to before (§8).
- **Ophthalmic curves** (median 53 mm non-correspondence):
  flagged on their manifest entries; unattached.
- **`Cochlear nerve.l` exclusion**: §3.

## 8. Non-regression census

- **Pack payloads**: per-record payload hashes (positions +
  normals bytes; indices re-based record-local) computed for all
  packs before and after: **0 pre-existing records changed, 0
  missing, exactly 21 new** (the 19 + the pair). No existing
  record's geometry changed by a single vertex.
- **Tree census** (SHA-256, data/ + web/data, 3,848 files
  before): changes confined to the intake's files — the six
  nervous/reproductive data JSONs, the new derived source tree,
  and web/data's nervous + reproductive packs (bin + gz),
  records.json, manifest.json, delivery.json. One further delta,
  disclosed: `data/integumentary/integumentary-assembled.json`
  differs in exactly one meta field (`records_without_geometry`:
  landed `[]` → the 53 FMA concept records the current assembler
  correctly lists as skipped; the file's six records are
  JSON-deep-equal to the landed file and its pack payload is
  byte-identical). The landed file's empty list was a Milestone
  16 artifact (the assembled file was never regenerated after
  the Milestone 38 extension); the regenerated file is the house
  tool's current, truthful output and is included in the batch
  on that basis.
- **Checker matrix** (all exit 0): fma_nerve_check ALL PASS;
  repro_check 69/69; fma_integ_male_check ALL PASS;
  fma_uri_repro_check ALL PASS; attribution_sweep ALL SYSTEMS
  CONSISTENT (19 × adjudicated-tier-b, 2 × adjudicated-claimed,
  zero drift); assembly_check ALL PASS; assembly_check_all ALL
  GATED CHECKS PASS; muscle_assembly_check ALL GATED PASS;
  nerve_check ALL HARD CHECKS PASS; major_nerve_check ALL PASS
  (clinical census 401 unchanged); cv / dig / endo /
  fma_lymph_endo / integ / lymph / muscle / resp / skeletal /
  uri checks ALL PASS; imaging_toolkit_check PASS (84 hard
  checks); pack_geometry --check ALL PASS (11/11 layers).
- **case_check 14,919 / 0** and **theatre_check 872 / 0** —
  unmoved, exactly as required.
- **verify_web ALL CHECKS PASS**, including W6 pick codec over
  all 1,566 slots (0 failures) — picking behaviour for the new
  geometry verified in the web idiom.
- **Native verify**: 99 data-assertion PASS / 0 FAIL before and
  after (the assertion structure is per-layer; the nervous and
  reproductive assertions now read 152 / 15 records at the new
  totals), then the identical GPU-initialisation failure,
  exit 2 — this VM has no GL/Vulkan adapter, the standing
  disclosed limitation; the render-stage assertions (silhouette,
  translucency, native picking) remain un-runnable here, as at
  every prior milestone.

### Checker amendments (adjudicated, pinned — never weakened)

The claimed exceptions are pinned as invariants and re-measured
from disk; every other record stays under the original
assertions. No assertion was deleted or loosened.

- `tools/fma_nerve_check.py`: CLAIMED set of exactly the 19;
  G1 requires the mesh-carrying extension set to equal it, each
  entry's fj/path to equal the pinned derivation, counts/bbox/
  totals re-measured from the OBJ files; the other 267 stay
  mesh-less; G2 pins the derived-geometry flag; coverage
  286 → 267.
- `tools/repro_check.py`: CLAIMED_PAIR {FJ3135}/{FJ3140};
  the pair is validated and re-measured exactly like BP3D
  entries; the Milestone 40 collision gate
  (`collisions == ADJUDICATED_COLLISIONS`) is unchanged;
  coverage 13 → 15 (male 10 → 12).
- `tools/fma_integ_male_check.py`: G1/G2 pair exception with
  re-measurement and the pinned claim flags; coverage
  arithmetic −2 for reproductive.
- `tools/fma_uri_repro_check.py`: one line — its combined-file
  coverage arithmetic spans the pair (its own Milestone 37
  record sets are untouched); −2 there.
- `tools/attribution_sweep.py`: the pair must now ship exactly
  its pinned derivation (`adjudicated-claimed`); the 19 Tier B
  records are pinned as ZA_CLAIMED with empty BP3D derivation
  (`adjudicated-tier-b`); any other FMA record carrying meshes,
  or any unpinned derivation, fails the sweep.
- `tools/assembly_check_all.py`: census anchor updated in the
  house idiom (nervous geometry 133 → 152, reproductive
  13 → 15, each with its milestone annotation); A1's set
  equality itself is unchanged.

## 9. README figures for its next pass (README.md not touched)

New figures: geometry **1,566** of 2,236 (concept-only **670**);
nervous geometry 152, reproductive 15; triangles **8,285,791**;
canonical pack bytes **311,136,996**; gzip bytes **125,760,132**;
file index deltas: [data] +4 (the derived tree's four non-OBJ
files; the OBJ directory itself is one tree entry in the
checker's counting), [tools] +2 (zanatomy_extract_full.py,
zanatomy_intake.py), [milestones] +1 (this dossier). Two R12
status statements the guard checks for presence become **false**
when this milestone lands and must be rewritten by the next
reconciliation: "The geometry decision is open" and "no
Z-Anatomy geometry has been intaken". (readme_check's other
failures — theatre R6/R9, milestone rows, web/wasm/theatre index
groups — predate this milestone and belong to the standing
reconciliation backlog.)

## 10. What remains

- **Tier C stays gated**: 285 objects / 64 records. No validated
  derivation exists for them (the audit's global registration
  was refuted; the brain-assembly transform does not extend
  beyond its validated region). Intake happens only if a
  derivation validates against the audit's held-out gates.
  Tier D (32 objects) is excluded permanently.
- **Nerve-geometry consequence**: the 18 cranial-nerve records
  (abducens, facial, glossopharyngeal, hypoglossal, maxillary,
  oculomotor, olfactory, trigeminal, vestibulocochlear — both
  sides) plus the falx cerebri gained geometry. The optic nerve
  records already carried BodyParts3D geometry and are
  unchanged; the trochlear records likewise keep their
  BodyParts3D geometry, with the 5.4 mm flag now on the records
  (§7). **The recurrent laryngeal nerve still has no Body Model
  record at all** (the Milestone 56 finding) — this intake does
  not change that: no record exists to attach geometry to, and
  none was created. The remaining 267 FMA nerve records —
  the peripheral and autonomic nerves, Tier C territory —
  remain concept-only.
- The expert-review gate remains UNMET for all Theatre
  procedures and Cases (no named reviewers); this milestone's
  geometry is a data derivation, not reviewed clinical content,
  and the atlas remains an educational/simulation artefact, not
  a clinical device.

## 11. Landing batch (exact)

New: `milestones/MILESTONE-63.md`;
`tools/zanatomy_extract_full.py`, `tools/zanatomy_intake.py`;
`data/sources/z-anatomy-derived/` (239 files: 235 OBJ +
SOURCE.md + intake-manifest.json + ledger.json +
ledger-summary.md).
Amended tools: `tools/fma_nerve_check.py`,
`tools/repro_check.py`, `tools/fma_integ_male_check.py`,
`tools/fma_uri_repro_check.py`, `tools/attribution_sweep.py`,
`tools/assembly_check_all.py`.
Data: `data/nervous/nervous-inventory.json`,
`data/nervous/nervous-geometry.json`,
`data/nervous/nervous-assembled.json`,
`data/reproductive/reproductive-inventory.json`,
`data/reproductive/reproductive-geometry.json`,
`data/reproductive/reproductive-assembled.json`,
`data/integumentary/integumentary-assembled.json` (§8
disclosure).
Web: `web/data/nervous.bin`, `web/data/nervous.bin.gz`,
`web/data/reproductive.bin`, `web/data/reproductive.bin.gz`,
`web/data/records.json`, `web/data/manifest.json`,
`web/data/delivery.json`.
262 files in total. README.md is not in the batch.
