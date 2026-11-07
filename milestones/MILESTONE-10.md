# Milestone 10 — Respiratory system module v1

Status: built and checked locally. Not uploaded; presented for
approval as a unit, as with Milestones 2–9.

Method follows Milestones 4, 5 and 9: inventory from the release
tables → geometry mapping by exact lookup and streamed counting → a
clinical tranche whose values come only from sources consulted
during the build, cited per field → an independent checker that
shares no code with the builders.

## Deliverables

| File | Content |
|---|---|
| `tools/resp_map.py` | Census + geometry builder (rerunnable) |
| `data/respiratory/respiratory-inventory.json` | Concept census and the 83 derived records |
| `data/respiratory/respiratory-geometry.json` | Per-record mesh lists with measured vertex/face counts and bounding boxes |
| `tools/build_resp_records.py` | Clinical tranche builder (sources S1–S11 in its header) |
| `data/respiratory/respiratory.json` | 37 clinical records |
| `tools/resp_check.py` | Independent checker (fresh census, re-measured geometry incl. bounding boxes, probe re-runs, citation/flag/tier validation, cross-module resolution) |

## Inventory (from the BodyParts3D 4.0 tables)

Universe: **270 concepts** — 134 named in the IS-A tables, 163 in
the PART-OF tables, 27 in both. Counting convention (stated in the
inventory file): one record per lateralised instance where the
tables lateralise; one record for an un-sided class modelled
jointly; the nose and lungs are records keyed on their PART-OF-only
organ concepts; lobes, bronchopulmonary segments and named nose
parts that exist only in PART-OF are records keyed on PART-OF
concepts.

| Source set | Concepts |
|---|---|
| IS-A tracheobronchial tree (root FMA12224) | 37 |
| IS-A larynx cartilages (root FMA55108) | 12 |
| IS-A larynx ligaments (roots FMA55131/FMA55244/FMA55233) | 10 |
| IS-A thyrohyoid sweep (8 named concepts, admitted by sweep) | 8 |
| IS-A conus elasticus (root FMA55250; hangs under "membrane organ component", found by probe, admitted by sweep) | 3 |
| IS-A pharynx subdivisions (root FMA54877; carries the epiglottis, FMA55130) | 3 |
| IS-A pharyngeal raphe (FMA55077, sweep admission) | 1 |
| IS-A nasal cartilages (root FMA59502) | 8 |
| PART-OF respiratory system (root FMA7158; carries the tracheobronchial tree and the RIGHT lung) | 92 |
| PART-OF left lung (root FMA7310; hangs under the left pulmopleural compartment) | 43 |
| PART-OF nose (root FMA46472; hangs under face) | 25 |
| PART-OF airway sweep: "right main bronchus" (FMA7395), second concept id on the IS-A "right main bronchus proper" record | 1 |

Cross-references censused inside the universe, by design not
respiratory records: **cardiovascular 71** (the segmental pulmonary
vessels and bronchial vessels inside the lung PART-OF subtrees),
**muscular 49** (larynx muscle line FMA46562 + aryepiglotticus +
cricothyroid zone = 28 concepts; pharynx muscle line FMA46619 = 20;
diaphragm FMA13295 = 1 — the diaphragm record itself is
`muscle.diaphragm` in the muscular module, referenced, never
duplicated), **skeletal 3** (the inferior nasal conchae FMA54736/7/8
— the skeletal module's `concha_left`/`concha_right` records),
**compartment 2** (the pulmopleural compartments FMA85055/85056,
concepts in no module's record set).

A name sweep over both tables for respiratory terms outside the
universe rejected **42 names** — pulmonary arteries/veins and their
trees, bronchial arteries, pulmonary valve cusps, nasal bones,
pterygomandibular raphes — all cardiovascular or skeletal
neighbours, none admitted.

**Records: 83** — 51 whole-concept, 3 partof-organ (nose, right
lung, left lung), 29 partof-concept:

- Airway 24: trachea, left/right main bronchi, and **21 segmental
  bronchial tree records** (16 lateralised instances plus the
  un-sided lateral, medial, basal and two lingular trees). There
  are **no lobar bronchus concepts** in the release: the tree jumps
  from the main bronchi directly to the segmental trees.
- Larynx cartilages 8 lateralised/class records plus the epiglottis
  = the nine cartilages of the clinical sources.
- Ligaments and membranes 12: vocal ligaments L/R, thyrohyoid
  membranes L/R, lateral thyrohyoid ligaments L/R, median thyrohyoid
  ligament, median cricothyroid ligament, hyo-epiglottic and
  thyro-epiglottic ligaments, conus elasticus L/R.
- Nasal cartilages 5; pharyngeal raphe 1.
- Lobes 5; **bronchopulmonary segments 21** (10 right; 11 left —
  the left carries the apicoposterior segment AND separate apical
  and posterior segments as released).
- Nose parts 3: external nose, internal nose, nasal septum.

Of the 270 universe concepts, 102 are carried by records (directly
or as class concepts); the remaining **168 are accounted, not
dropped**: 151 organ-subtree internals (bronchial generations,
segmental vessels, parenchyma parts inside the lung/nose subtrees),
the larynx/pharynx muscle cross-reference lines and the two
pulmopleural compartment concepts; 4 cross-module anchors whose
records live in other modules (diaphragm, inferior nasal conchae);
13 grouping class concepts (subtree roots and intermediate classes
whose descendants are recorded). The checker verifies this
accounting exactly.

## Geometry

Coverage **83/83 records** in both tables combined. The independent
checker re-measured all **1,140 mesh entries** by streaming —
vertex counts, face counts AND bounding boxes — and verified the
FJ-file attribution of every record against the element-parts
tables: **0 mismatches**.

Distinct mesh files: IS-A 129 files (85,155 vertices / 124,814
faces); PART-OF 293 files (83,054 vertices / 139,968 faces).

## TotalSegmentator overlap

Of the 104 TotalSegmentator v1 labels, **exactly 6 are
respiratory**: `trachea` and the five lung lobes. All six map to
inventory records. TS adds nothing below lobe level — no bronchus,
segment, larynx, nose, pharynx or pleura label exists in v1.

## Clinical tranche

**37 records, Tier A 37 / B 0 / C 0** — every field sourced from the
11 sources consulted during the build (TeachMeAnatomy articles on
the lungs, tracheobronchial tree, pleurae, nasal cavity, larynx,
laryngeal cartilages and pharynx; Wikipedia's bronchopulmonary
segment article for the Jackson & Huber list; the ETSU lung
volumes and capacities page; LibreTexts BIO 50; OpenStax A&P 2e
§22.2), cited per field in each record's `sources` map. TA names
were not given by the consulted sources and are null +
verify-flagged on all 37 records, as in Milestones 4/5/9.

| Group | Records |
|---|---|
| Airway pathway (nares → alveoli, orders 1–13; conducting zone 1–10, respiratory zone 11–13) | 13 |
| Bronchopulmonary segments (right 10, left 8 — the clinical Jackson & Huber list) | 18 |
| Lungs (right/left organ records: lobes, fissures, root/hilum, relations, supply) | 2 |
| Upper airway (nasal cavity structure; pharynx) | 2 |
| Pleurae and pleural cavities | 1 |
| Respiratory mechanics (volumes and capacities) | 1 |

Geometry linkage: **26 of 37** clinical records link at least one
inventory record; **82 of 83** inventory records are linked from
the clinical tranche — the only unlinked record is the pharyngeal
raphe (a fibrous seam with no clinical-tranche structure to attach
to). Records for structures the release does not contain (the
pharyngeal parts, lobar bronchi, bronchioles, the whole respiratory
zone below the segmental bronchi, the pleura) link nothing and
carry the absence in their verify list instead — checker-gated.

Notable linkage detail: the left apico-posterior segment record
links **5** inventory records (the merged segment concept, both
constituent segment concepts, both segmental bronchial trees), and
the left anteromedial basal record links **4** — the release's 21
segment concepts are the un-merged anatomical instances, the
clinical list's 18 are the named surgical units, and the links
record the merger explicitly rather than hiding it.

Respiratory mechanics values are the consulted source's stated
approximates, transcribed as printed, with the source's own caveat
carried in the record: tidal volume 500 mL, IRV 3000 mL, ERV
1300 mL, RV 1200 mL, FRC 2500 mL, VC 5000 mL, TLC 6000 mL, minimal
volume 500 mL, anatomical dead space ≈150 mL, respiratory rate
12–15/min, minute volume 6000–7500 mL/min, alveolar ventilation
5250 mL/min at rest, FEV1 ≈80% of VC. (The source's FRC = ERV + RV
identity holds exactly; its VC and TLC are NOT arithmetically
consistent with its own components — they are transcribed, not
forced, and the caveat says so.)

## Checker results (`tools/resp_check.py`, exit 0)

**72 hard checks PASS, 0 FAIL.** Highlights: the full concept
universe re-derived from the six tables set-by-set (270 concepts,
all 17 set counts exact); cross-reference census re-derived
(71/49/3/2); rejected-sweep census re-derived (42 names); record
concept sets disjoint and inside the universe; unrecorded-concept
accounting exact (168 = 151 + 4 + 13); cross-module pointers
resolve (muscular `muscle.diaphragm`, skeletal
`concha_left`/`concha_right`, cardiovascular concept universe);
geometry fully re-measured (1,140 entries, counts + bounding
boxes, FJ attribution exact, 0 mismatches); TS census parsed
independently (104 labels, 6 respiratory, all mapped); absence
probes re-run (below); clinical citation/flag/tier discipline
re-validated for all 37 records, including pathway order 1–13,
zone split, the 10-right/8-left segment list, merger link counts
(5 and 4), and exact transcription of the mechanics table.

## Gap analysis — quantified, recorded, never filled

**114 absence probes** were run as occurrence counts over all six
release tables; **99 returned zero hits**. The checker re-ran the
identical probe set and reproduced the identical absent list.
Probe-verified absences, by consequence:

- **The pleura does not exist in this release at all.** No pleura,
  visceral pleura, parietal pleura, pleural cavity, costal/
  mediastinal/diaphragmatic/cervical pleura, and no pleural recess
  concept of any kind ("pleura" substring hits come only from
  "pulmopleural"). The clinical pleura record is sourced text with
  a recorded absence where its geometry would be. The two
  pulmopleural compartment concepts are the release's only
  pleura-adjacent structures, and they are hollow-organ
  compartments, not membranes.
- **The respiratory zone is entirely absent.** No bronchiole,
  respiratory/terminal/conducting bronchiole, alveolar duct,
  alveolar sac, alveolus or respiratory membrane concept exists.
  The release's airway ends at the segmental bronchial trees; every
  structure the clinical pathway names below order 9 is text-only.
- **No lobar bronchi.** The tree jumps main → segmental; the
  clinical lobar-bronchi record (3 right / 2 left, S2) has no
  geometry to link.
- **No organ concepts for pharynx, larynx or nasal cavity.** The
  pharynx exists only as its subdivision classes, its raphe and
  its muscles; the larynx only as cartilages, ligaments/membranes
  and muscles; the nasal cavity as a space not at all (the nose
  organ and its parts exist in PART-OF).
- **The nose is skeletal-poor as released:** superior and middle
  nasal conchae have no concepts (the inferior conchae exist, as
  skeletal cross-references); no meatus of any kind, no paranasal
  sinus (frontal/maxillary/sphenoid/ethmoid all absent), no
  auditory tube, no choanae, no semilunar hiatus or ethmoidal
  bulla. Every sinus-drainage opening in the clinical nasal record
  is therefore text-only.
- **No lung surface anatomy:** no fissure concepts (oblique/
  horizontal), no hilum or root of lung, no cardiac notch, no
  lingula as a concept, no apex/base/surface concepts, no lobule,
  no interlobular septum, no acinus. The lung organ records' lobes
  and fissures are sourced text; only the lobes have geometry.
- **No tracheal or laryngeal interior detail:** no carina, no
  tracheal cartilage/ring concepts, no trachealis (its concept is
  a muscular-module matter, absent here), no vocal or vestibular
  folds, no glottis/rima glottidis as concepts (substring hits
  only), no laryngeal cavity/ventricle/inlet, no piriform recess,
  no cricothyroid or quadrangular membrane, no sesamoid or
  triticeal cartilage, no epiglottic cartilage distinct from the
  epiglottis itself.
- **TS ceiling:** TotalSegmentator v1 stops at the lobes (6
  respiratory labels of 104), so CT-derived geometry cannot fill
  any of the above either.

Cross-module continuities confirmed while building: the diaphragm
is the muscular module's record (referenced, not duplicated); the
inferior nasal conchae are the skeletal module's records; the
segmental pulmonary vessels inside the lung subtrees are the
cardiovascular module's concepts. The respiratory module invents
no record for another module's structure.

## Next steps

1. A TA2 pass for `ta_name` across the respiratory records (owed
   jointly with the muscular/nervous TA debt since Milestone 4).
2. The respiratory-zone gap (bronchioles → alveoli) and the pleura
   gap are dataset-shaped, not effort-shaped: closing them needs a
   source beyond BP3D 4.0 + TS v1 — same class of blocker as
   Milestone 9's peripheral-nerve gap. Recorded, not filled.
3. Physiology follow-on: the mechanics record's volumes are the
   natural parameter source when the Milestone 8 engine grows a
   respiratory compartment; the values carry their approximates
   caveat with them.
4. Theatre follow-on: the 18 clinical bronchopulmonary segments,
   with their explicit merger links to the 21 released segment
   concepts, are the unit list a segmentectomy procedure would be
   authored against.
5. Remaining systems queue per the Master Plan: digestive,
   urinary, lymphatic, endocrine, reproductive, integumentary.
