# Milestone 1 — Design complete + P2 geometry foundation

Date: 2026-11-06. Scope: local working tree only; nothing uploaded anywhere.

## Designed

Ten buildable design documents in `design/`, each with purpose, interfaces,
data formats, verification gates, and open decisions explicitly flagged
(OD-xx items — none silently resolved):

1. `01-architecture` — one Body Model, two shells, module boundaries, interface contracts.
2. `02-body-model-schema` — record kinds, relations graph, variant records with the ≥1% gate, census conventions, CellML/FieldML/SED-ML export.
3. `03-geometry-pipeline` — adoption sources, provenance ledger format and gate, registration onto records, coverage census as P2 exit criterion.
4. `04-physiology-engine` — Pulse-architecture compartments, 20 ms deterministic core, causal-chain exposure, VitalDB validation, credentialed-data boundary.
5. `05-theatre` — CTA graph format (microsteps/decision points/errors/tips/bailouts), safety gates with hard fails, OSATS/GOALS/GEARS, proficiency progression, resource tiers.
6. `06-imaging` — OHIF/Cornerstone3D patterns, synthetic CT from label→HU ranges, watermarking, ACR/Radiopaedia fences.
7. `07-cases` — case format on the engine, Mondo/HPO/DO spine, FHIR interchange, calibration as headline metric, LOINC/RxNorm packs, SNOMED excluded.
8. `08-native-shell` — Rust + wgpu, VTK volumes, XPBD tissue with range+method-tag parameters, OpenXR/Quest 3, haptics behind plugins only.
9. `09-web-shell` — Phase-1 lineage, WebGPU→WebGL2→software-renderer floor, shared Rust engine via wasm, honest scope per module.
10. `10-governance` — Precision Law enforcement, Messick labeling in-product, review/sign-off, negative-training audit, errata, licensing and claims gates, release gate list.

## Implemented (P2 foundation)

### Scaffold
Repo-shaped tree: AGPL `LICENSE`, neutral `README.md`, `data/` folders for all
eleven body systems plus `data/sources/`, `tools/`, `native/`, `web/`,
`design/`, and the existing `research/` library untouched.

### Asset location (searched the whole VM)
- **Correction (2026-11-06, after a slower full-filesystem search completed):**
  BodyParts3D **was** present on this machine — a prior download in
  `~/workspace/anatlas/` (ISA archive + its 2,234 extracted OBJs + the same
  mapping tables) from an earlier local project. An initial targeted search
  missed it and the first version of this section wrongly reported it absent;
  that statement is retracted. Spot-checked files (FJ1252, FJ3400) from the
  pre-existing copy are **byte-identical** to the fresh official download
  below, which cross-validates both. The fresh download was kept as the
  intake of record because it is complete (both trees, license page archived,
  hashes pinned). The film work's data file
  (`~/workspace/anatomica/anat3_data.py`) is hand-authored polygon
  coordinates, not BodyParts3D — that part of the original finding stands.
  Per-object Z-Anatomy remains absent (only the merged GLBs exist).
- **Z-Anatomy: present only as per-system merged GLBs** in
  `~/workspace/anatlas/za/public/models/` (7 GLBs + upstream license notice) —
  copied byte-identical into `data/sources/z-anatomy-glb/`.

### BodyParts3D 4.0 download
Downloaded from the official DBCLS/LSDB Archive (download page →
`dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/`): both polygon archives
(IS-A 99%-reduced, 142,903,898 B; PART-OF, 64,888,505 B) plus parts lists,
element lists, inclusion relations, release notes, and an archived copy of
the current license page. Both archives pass zip integrity tests.
**Published-hash verification: DBCLS publishes no checksums** (checked the
download page, README, and release notes) — so intake SHA-256 pins computed
here are recorded in `data/sources/bodyparts3d-4.0/SOURCE.md` and in the
ledger, and are the reference for any future re-download.

### Provenance (`tools/provenance.py`, executed)
- BodyParts3D source dir: 12 files, 210,113,088 B, 0 unknown licenses.
- Extracted meshes (`work/bp3d/`, scratch): 3,492 OBJ files, 697,171,673 B,
  0 unknown licenses.
- Z-Anatomy GLBs: 9 files, 18,973,436 B.
- License trap confirmed per-file: **all 3,492 OBJ headers state CC BY-SA
  2.1 Japan** while the current DBCLS license page states CC BY 4.0. Both
  readings are recorded in the ledgers and `SOURCE.md`; distribution will
  satisfy the stricter (share-alike) reading pending reconfirmation.

### Coverage census (`tools/census.py`, executed; full output in `tools/census.md`)
- BodyParts3D ISA: **2,905 FMA concepts** listed; **2,234 IS-A mesh files**;
  1,258 PART-OF mesh files. The element-parts mapping is an exact bijection
  with the archive (2,234 distinct element files, 0 missing, 0 unused), so
  **all 2,905 concepts compose from in-archive meshes**.
- Per-system breakdown of BodyParts3D: **not derivable** from the release
  files (no system field) — reported as such, not estimated.
- Z-Anatomy named nodes per system file (reference only): cardiovascular 676,
  muscular 669, nervous 580, joints 349, lymphatic 158, plus skeletal and
  visceral (see census) — **reference only**: as distributed, the export is
  CC BY-NC-SA 4.0 (it embeds CC BY-NC inner-ear and kidney models, inseparable
  in merged GLBs). **Excluded from product data** until a per-object-cleared
  source exists; the exclusion and its reason are recorded in
  `data/sources/z-anatomy-glb/SOURCE.md`.
- Skeletal name-match coverage vs the verified 206-bone inventory:
  BodyParts3D 61/206 by normalized name. The 145 unmatched are characterised,
  not hidden: 131 are instance-level records (vertebrae, ribs, numbered
  hand/foot bones, ossicles) whose FMA naming is class-level/ordinal, and 14
  are naming variants. Name matching is a floor; the FMA-ID mapping in the
  schema (design 02) is the real path and is the next pipeline task.

## Blockers / flags

- **Z-Anatomy is unusable as product geometry in its current form** (NC
  contamination in merged files). BodyParts3D carries P2; Z-Anatomy needs a
  per-object adoption with per-object license reading.
- **BodyParts3D license duality** (BY-SA 2.1 JP headers vs CC BY 4.0 page)
  needs a recorded position at each future pin; current position: satisfy the
  stricter reading.
- **TotalSegmentator not yet adopted** (OD-03.1): its label set is the imaging
  floor; dataset download is a separate intake with its own ledger run.
- Open design decisions OD-01.1…OD-10.2 stand as flagged in the design docs;
  OD-04.1 (embed Pulse vs build) is the largest and is scheduled at P4.

## Next steps

1. FMA-ID mapping pass: populate `fma` on the 206 skeletal records and map
   BodyParts3D concepts → structure IDs; convert the skeletal module to the
   design-02 JSON schema and prove the 206 census survives conversion.
2. Registration prototype: align BodyParts3D skeletal meshes onto the
   Phase-1 anchor frame; run the assembly sanity check.
3. Muscular + cardiovascular data modules (design 02), with census checkers.
4. Native shell skeleton: Rust + wgpu window rendering the registered
   skeletal meshes from the geometry registry.
5. TotalSegmentator intake (dataset + label set) with its own provenance run.
