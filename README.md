# ANATOMICA

![The cardiovascular system — a still from ANATOMICA's surgical simulation film](assets/anatomica-hero.jpg)

*The cardiovascular system — a still from ANATOMICA's surgical simulation film.*

An open medical surgical and anatomy system: a 3D anatomical atlas, a physiology
simulation engine, an imaging suite, a surgical procedure simulator, and a clinical
case and hypothesis workbench — all reading one verified model of the human body.

ANATOMICA is an educational and simulation system. It is not a clinical device, it
carries no real patient data, and it is not for diagnosis or treatment of real persons.

## Principles

- **One body, one truth.** Every module derives from the same Body Model; modules
  never keep private copies of anatomy or physiology.
- **Data before rendering.** A structure exists because its record is verified —
  nomenclature, counts, and relations traceable to named sources. Uncertain items
  carry a visible *verify* flag instead of a silently chosen answer.
- **Derived, never invented.** Geometry comes from segmented human anatomy adopted
  under compatible licenses, tracked per file in a provenance ledger.
- **Computed, not scripted.** Vitals and labs are outputs of a running physiological
  state; complications in the operating theatre are computed by the engine.
- **Open forever.** The whole system is licensed AGPL-3.0.

## Layout

| Path | Contents |
|---|---|
| `design/` | Buildable design documents for every area of the system (10 documents) |
| `data/` | Body Model data modules, one folder per body system; `data/sources/` holds adopted source datasets with their provenance |
| `tools/` | Verification tooling: provenance ledger builder, censuses, checkers, assemblers and record builders |
| `native/` | The native application (flagship) — Rust + wgpu |
| `web/` | The browser application (universal-access companion) — WebGL2 viewer |
| `physiology/` | The deterministic physiology engine — Rust |
| `film-engine/` | The surgical simulation film engine — Blender pipeline, geometry inputs, and the patient scene archive (see `film-engine/README.md`) |
| `research/` | The research library the design rests on (3 rounds, 31 fronts) |
| `assets/` | README and project imagery |
| `MILESTONE-*.md` | The milestone reports, one per landed milestone (listed below) |

## Status

**Milestones 1–15 are complete and in this repository** (plus the Milestone 7
pick-layer fix), recorded in `MILESTONE-1.md` through `MILESTONE-15.md`.

**Body Model v1 is complete:** 1,552 inventory records across all eleven body
systems, with geometry for 1,545 of 1,552 — the only exceptions are the six
auditory ossicles and the coccyx, which no adoptable dataset carries as separate
structures. 361 sourced clinical records (Tier A 209 / Tier B 112 / Tier C 40).

Both shells render the real assembled geometry — the native Rust + wgpu flagship
and the WebGL2 browser companion — and the deterministic physiology engine's
resting cardiovascular outputs validate against published normal ranges.

Known dataset gaps are recorded on the records themselves, not smoothed over:
nerves beyond cranial nerves II–V1, lymphatic vessels and nodes, thyroid and
parathyroid geometry, kidney and urinary interior, the internal female
reproductive tract, and skin layers / nails / glands have no concepts in
BodyParts3D 4.0 + TotalSegmentator v1 and await a further source (a full
FMA / Terminologia Anatomica pass is the named route).

## Milestones

| Milestone | Report | What landed |
|---|---|---|
| 1 | `MILESTONE-1.md` | Design complete (10 design documents) + P2 geometry foundation and repo scaffold |
| 2 | `MILESTONE-2.md` | Skeletal system: FMA-ID mapping and geometry conversion for all 206 bones |
| 3 | `MILESTONE-3.md` | TotalSegmentator intake (10 subjects, full 1,204-subject index) + registered skeleton assembly: 199 records, 511,968 faces |
| 4 | `MILESTONE-4.md` | Muscular system: 359 inventory / geometry records, 127 sourced clinical records |
| 5 | `MILESTONE-5.md` | Cardiovascular system: 646 records, 69 clinical records + 8 variant records |
| 6 | `MILESTONE-6.md` | Muscular assembly + Web Shell v2 rendering the real assembled skeleton and muscle layers |
| 7 | `MILESTONE-7.md` | Native shell: Rust + wgpu application rendering the real Body Model packs |
| 7 (fix) | `MILESTONE-7-FIX.md` | Web viewer pick-layer bug fix, with a regression check that executes the shipped decoder |
| 8 | `MILESTONE-8.md` | Physiology engine v0: deterministic cardiovascular compartment model, 46 cited parameters, resting outputs inside all cited normal ranges |
| 9 | `MILESTONE-9.md` | Nervous system: 133 records, 52 sourced clinical records; the nerve-concept gap quantified exactly |
| 10 | `MILESTONE-10.md` | Respiratory system: 83 records, 37 clinical records (all Tier A) |
| 11 | `MILESTONE-11.md` | Digestive system: 93 records, 31 clinical records, all eight Couinaud liver segments |
| 12 | `MILESTONE-12.md` | Urinary system: 6 records, 6 clinical records (all Tier A) — the system's entire interior is absent from the source datasets |
| 13 | `MILESTONE-13.md` | Lymphatic system (4 records, 4 clinical) + endocrine system (3 records, 6 clinical) |
| 14 | `MILESTONE-14.md` | Reproductive system: 13 records, 16 clinical records — 14 male concepts vs 1 female concept in the source release |
| 15 | `MILESTONE-15.md` | Integumentary system: 6 records, 13 clinical records — closes the eleven-system census: Body Model v1 |

## File index

All 246 files in this repository, by directory. Adopted source-dataset binaries (meshes, archives, GLBs) and build output are not tracked in git — see `.gitignore`; their provenance is recorded in `data/sources/*/ledger.json` and `SOURCE.md`.


### Root — 19 files

- `.gitignore`
- `LICENSE`
- `MILESTONE-1.md`
- `MILESTONE-10.md`
- `MILESTONE-11.md`
- `MILESTONE-12.md`
- `MILESTONE-13.md`
- `MILESTONE-14.md`
- `MILESTONE-15.md`
- `MILESTONE-2.md`
- `MILESTONE-3.md`
- `MILESTONE-4.md`
- `MILESTONE-5.md`
- `MILESTONE-6.md`
- `MILESTONE-7-FIX.md`
- `MILESTONE-7.md`
- `MILESTONE-8.md`
- `MILESTONE-9.md`
- `README.md`


### `assets/` — 1 file

- `assets/anatomica-hero.jpg`


### `data/` — 54 files

- `data/cardiovascular/cardiovascular.json`
- `data/cardiovascular/cv-geometry.json`
- `data/cardiovascular/cv-inventory.json`
- `data/digestive/digestive-geometry.json`
- `data/digestive/digestive-inventory.json`
- `data/digestive/digestive.json`
- `data/endocrine/endocrine-geometry.json`
- `data/endocrine/endocrine-inventory.json`
- `data/endocrine/endocrine.json`
- `data/integumentary/integumentary-geometry.json`
- `data/integumentary/integumentary-inventory.json`
- `data/integumentary/integumentary.json`
- `data/lymphatic/lymphatic-geometry.json`
- `data/lymphatic/lymphatic-inventory.json`
- `data/lymphatic/lymphatic.json`
- `data/muscular/muscle-geometry.json`
- `data/muscular/muscle-inventory.json`
- `data/muscular/muscles-assembled.json`
- `data/muscular/muscles.json`
- `data/nervous/nervous-geometry.json`
- `data/nervous/nervous-inventory.json`
- `data/nervous/nervous.json`
- `data/reproductive/reproductive-geometry.json`
- `data/reproductive/reproductive-inventory.json`
- `data/reproductive/reproductive.json`
- `data/respiratory/respiratory-geometry.json`
- `data/respiratory/respiratory-inventory.json`
- `data/respiratory/respiratory.json`
- `data/skeletal/fma-mapping.json`
- `data/skeletal/gap-analysis.md`
- `data/skeletal/skeleton-assembled.json`
- `data/skeletal/skeleton-geometry.json`
- `data/sources/bodyparts3d-4.0/SOURCE.md`
- `data/sources/bodyparts3d-4.0/isa_element_parts.txt`
- `data/sources/bodyparts3d-4.0/isa_inclusion_relation_list.txt`
- `data/sources/bodyparts3d-4.0/isa_parts_list_e.txt`
- `data/sources/bodyparts3d-4.0/ledger-summary.md`
- `data/sources/bodyparts3d-4.0/ledger.json`
- `data/sources/bodyparts3d-4.0/partof_element_parts.txt`
- `data/sources/bodyparts3d-4.0/partof_inclusion_relation_list.txt`
- `data/sources/bodyparts3d-4.0/partof_parts_list_e.txt`
- `data/sources/totalsegmentator-1.0/SOURCE.md`
- `data/sources/totalsegmentator-1.0/index-census.json`
- `data/sources/totalsegmentator-1.0/labels.json`
- `data/sources/totalsegmentator-1.0/labels.md`
- `data/sources/totalsegmentator-1.0/ledger-summary.md`
- `data/sources/totalsegmentator-1.0/ledger.json`
- `data/sources/z-anatomy-glb/License.txt`
- `data/sources/z-anatomy-glb/SOURCE.md`
- `data/sources/z-anatomy-glb/ledger-summary.md`
- `data/sources/z-anatomy-glb/ledger.json`
- `data/urinary/urinary-geometry.json`
- `data/urinary/urinary-inventory.json`
- `data/urinary/urinary.json`


### `design/` — 10 files

- `design/01-architecture.md`
- `design/02-body-model-schema.md`
- `design/03-geometry-pipeline.md`
- `design/04-physiology-engine.md`
- `design/05-theatre.md`
- `design/06-imaging.md`
- `design/07-cases.md`
- `design/08-native-shell.md`
- `design/09-web-shell.md`
- `design/10-governance.md`


### `film-engine/` — 51 files

- `film-engine/README.md`
- `film-engine/compose_still.py`
- `film-engine/diag.py`
- `film-engine/dump_groups.py`
- `film-engine/fix_clip.py`
- `film-engine/fix_islands.py`
- `film-engine/fix_lung.py`
- `film-engine/fix_lung2.py`
- `film-engine/fix_mats.py`
- `film-engine/fix_skin.py`
- `film-engine/geometry/artery.npz`
- `film-engine/geometry/artery_keep.npz`
- `film-engine/geometry/bone.npz`
- `film-engine/geometry/bone_keep.npz`
- `film-engine/geometry/brain.npz`
- `film-engine/geometry/brain_keep.npz`
- `film-engine/geometry/cartilage.npz`
- `film-engine/geometry/cartilage_keep.npz`
- `film-engine/geometry/heart.npz`
- `film-engine/geometry/heart_keep.npz`
- `film-engine/geometry/liver.npz`
- `film-engine/geometry/liver_keep.npz`
- `film-engine/geometry/lung.npz`
- `film-engine/geometry/lung_keep.npz`
- `film-engine/geometry/muscle.npz`
- `film-engine/geometry/muscle_keep.npz`
- `film-engine/geometry/nerve.npz`
- `film-engine/geometry/nerve_keep.npz`
- `film-engine/geometry/organ.npz`
- `film-engine/geometry/organ_keep.npz`
- `film-engine/geometry/skin.npz`
- `film-engine/geometry/skin_keep.npz`
- `film-engine/geometry/vein.npz`
- `film-engine/geometry/vein_keep.npz`
- `film-engine/islands.py`
- `film-engine/islands2.py`
- `film-engine/islands3.py`
- `film-engine/make_skin.py`
- `film-engine/make_skin2.py`
- `film-engine/patient.blend.xz.part-aa`
- `film-engine/patient.blend.xz.part-ab`
- `film-engine/patient.blend.xz.part-ac`
- `film-engine/patient.blend.xz.part-ad`
- `film-engine/patient.py`
- `film-engine/plates.py`
- `film-engine/probe.py`
- `film-engine/probe2.py`
- `film-engine/probe3.py`
- `film-engine/restore_patient.sh`
- `film-engine/restore_render_env.sh`
- `film-engine/scene.py`


### `native/` — 9 files

- `native/Cargo.lock`
- `native/Cargo.toml`
- `native/src/camera.rs`
- `native/src/lib.rs`
- `native/src/main.rs`
- `native/src/model.rs`
- `native/src/pack.rs`
- `native/src/render.rs`
- `native/tests/pack_data.rs`


### `physiology/` — 9 files

- `physiology/Cargo.lock`
- `physiology/Cargo.toml`
- `physiology/parameters.json`
- `physiology/src/cases.rs`
- `physiology/src/engine.rs`
- `physiology/src/lib.rs`
- `physiology/src/main.rs`
- `physiology/src/params.rs`
- `physiology/tests/engine_tests.rs`


### `research/` — 45 files

- `research/INDEX.md`
- `research/round-01-state-of-the-art/SOURCE-AGENTS.md`
- `research/round-01-state-of-the-art/fronts/00-overview.md`
- `research/round-01-state-of-the-art/fronts/01-open-anatomical-data-and-ontologies/FRONT.md`
- `research/round-01-state-of-the-art/fronts/02-surgical-simulation-state-of-the-art/FRONT.md`
- `research/round-01-state-of-the-art/fronts/03-physiology-engines/FRONT.md`
- `research/round-01-state-of-the-art/fronts/04-medical-imaging-tech/FRONT.md`
- `research/round-01-state-of-the-art/fronts/05-clinical-reasoning-diagnosis-training/FRONT.md`
- `research/round-01-state-of-the-art/fronts/06-web-3d-rendering-state-of-the-art-browser-tier/FRONT.md`
- `research/round-01-state-of-the-art/fronts/07-native-real-time-3d-and-simulation-technology-supplement-1/FRONT.md`
- `research/round-01-state-of-the-art/fronts/08-vr-ar-and-haptics-for-surgical-training-supplement-1/FRONT.md`
- `research/round-01-state-of-the-art/fronts/09-native-vs-browser-ceiling-what-the-oss-community-actually-bu/FRONT.md`
- `research/round-01-state-of-the-art/fronts/10-the-frontier-whole-body-digital-human-digital-twin-programme/FRONT.md`
- `research/round-01-state-of-the-art/fronts/11-accuracy-and-validation-standards-supplement-3/FRONT.md`
- `research/round-01-state-of-the-art/notes/front11-validation.md`
- `research/round-01-state-of-the-art/notes/fronts7-10.md`
- `research/round-01-state-of-the-art/report.md`
- `research/round-02-medical-fields/SOURCE-AGENTS.md`
- `research/round-02-medical-fields/fronts/00-overview.md`
- `research/round-02-medical-fields/fronts/01-anatomy-science/FRONT.md`
- `research/round-02-medical-fields/fronts/02-quantitative-physiology-and-pathophysiology/FRONT.md`
- `research/round-02-medical-fields/fronts/03-surgery-and-perioperative-standards/FRONT.md`
- `research/round-02-medical-fields/fronts/04-pharmacology-quantitative/FRONT.md`
- `research/round-02-medical-fields/fronts/05-imaging-science/FRONT.md`
- `research/round-02-medical-fields/fronts/06-diagnostic-reasoning-evidence/FRONT.md`
- `research/round-02-medical-fields/fronts/07-disease-and-epidemiology-data/FRONT.md`
- `research/round-02-medical-fields/fronts/08-medical-education-science/FRONT.md`
- `research/round-02-medical-fields/fronts/09-special-populations-and-variation/FRONT.md`
- `research/round-02-medical-fields/fronts/10-frontier-clinical-technology/FRONT.md`
- `research/round-02-medical-fields/notes/sources-index.md`
- `research/round-02-medical-fields/report.md`
- `research/round-03-depth-specialization/SOURCE-AGENTS.md`
- `research/round-03-depth-specialization/fronts/00-overview.md`
- `research/round-03-depth-specialization/fronts/01-open-clinical-data-and-signals/FRONT.md`
- `research/round-03-depth-specialization/fronts/02-anesthesia-and-critical-care-deep/FRONT.md`
- `research/round-03-depth-specialization/fronts/03-emergency-and-resuscitation/FRONT.md`
- `research/round-03-depth-specialization/fronts/04-surgical-subspecialty-evidence/FRONT.md`
- `research/round-03-depth-specialization/fronts/05-tissue-biomechanics-and-surgical-physics/FRONT.md`
- `research/round-03-depth-specialization/fronts/06-laboratory-medicine-and-pathophysiology-depth/FRONT.md`
- `research/round-03-depth-specialization/fronts/07-infectious-disease-and-antimicrobials/FRONT.md`
- `research/round-03-depth-specialization/fronts/08-human-factors-safety-and-debriefing-science/FRONT.md`
- `research/round-03-depth-specialization/fronts/09-global-and-resource-tiered-medicine/FRONT.md`
- `research/round-03-depth-specialization/fronts/10-regulatory-and-ethics-boundaries-for-educational-medical-sof/FRONT.md`
- `research/round-03-depth-specialization/notes/coverage-log.md`
- `research/round-03-depth-specialization/report.md`


### `tools/` — 44 files

- `tools/assemble_muscles.py`
- `tools/assemble_skeleton.py`
- `tools/assembly_check.py`
- `tools/build_cv_records.py`
- `tools/build_dig_records.py`
- `tools/build_endo_records.py`
- `tools/build_integ_records.py`
- `tools/build_lymph_records.py`
- `tools/build_muscle_records.py`
- `tools/build_nerve_records.py`
- `tools/build_repro_records.py`
- `tools/build_resp_records.py`
- `tools/build_uri_records.py`
- `tools/census.json`
- `tools/census.md`
- `tools/census.py`
- `tools/cv_check.py`
- `tools/cv_map.py`
- `tools/dig_check.py`
- `tools/dig_map.py`
- `tools/endo_check.py`
- `tools/endo_map.py`
- `tools/fma_map.py`
- `tools/integ_check.py`
- `tools/integ_map.py`
- `tools/lymph_check.py`
- `tools/lymph_map.py`
- `tools/muscle_assembly_check.py`
- `tools/muscle_check.py`
- `tools/muscle_map.py`
- `tools/nerve_check.py`
- `tools/nerve_map.py`
- `tools/pack_web_geometry.py`
- `tools/provenance.py`
- `tools/register_sketch.md`
- `tools/repro_check.py`
- `tools/repro_map.py`
- `tools/resp_check.py`
- `tools/resp_map.py`
- `tools/skeletal_check.py`
- `tools/ts_intake.py`
- `tools/uri_check.py`
- `tools/uri_map.py`
- `tools/verify_web.js`


### `web/` — 4 files

- `web/data/manifest.json`
- `web/data/records.json`
- `web/index.html`
- `web/viewer.js`

## License

AGPL-3.0. See `LICENSE`. Adopted datasets keep their own licenses, recorded
per file in the provenance ledger under `data/sources/`.
