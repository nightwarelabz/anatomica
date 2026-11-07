# Milestone 5 — Cardiovascular module v1

Status: built and checked locally. Not uploaded; presented for
approval as a unit, as with Milestones 2–4.

Method follows Milestone 4: inventory from the release tables →
geometry mapping by exact lookup and streamed counting → a clinical
tranche whose values come only from sources consulted during the
build, cited per field → variant records under the variant gate → an
independent checker that shares no code with the builders.

## Deliverables

| File | Content |
|---|---|
| `tools/cv_map.py` | Census + geometry builder (rerunnable) |
| `data/cardiovascular/cv-inventory.json` | Concept census and the 646 derived records |
| `data/cardiovascular/cv-geometry.json` | Per-record mesh lists with measured vertex/face counts |
| `tools/build_cv_records.py` | Clinical tranche builder (sources S1–S20 in its header) |
| `data/cardiovascular/cardiovascular.json` | 69 clinical records + 8 variant records |
| `tools/cv_check.py` | Independent checker (fresh census, re-measured geometry, citation/flag/tier/branch/variant validation) |

## Inventory (from the BodyParts3D 4.0 tables)

Universe: **1,112 concepts** — arterial subtree rooted at FMA86187
"segment of arterial tree organ" **701** (the FMA50720 "artery"
subtree, 618, is a proper subset; the other 83 are the segment/trunk
line); venous subtree rooted at FMA86188 "segment of venous tree
organ" **324**; heart IS-A part set **38**; heart PART-OF set **72**
(49 of them PART-OF-only). The two vessel subtrees are disjoint.
There is no lymphatic-tree concept in the release.

**646 records** under the stated counting convention (one record per
lateralised instance where the tables lateralise; one record for an
un-sided class modelled jointly; branch-class-only classes are one
un-sided record; the heart and the aorta are records keyed on their
PART-OF-only organ concepts):

| Representation | Records |
|---|---|
| whole-concept (per side) | 518 |
| whole-concept, un-sided | 117 |
| partof-organ (heart, aorta) | 2 |
| partof-concept (chambers, valves, fibrous skeleton) | 9 |

Instance grouping: 414 direct, 4 deep, 85 standalone; orphan
instances 0. The heart record set additionally carries the 15 IS-A
valve-cusp/leaflet and papillary-muscle records listed in the
inventory meta (papillary muscles were assigned to this module by
Milestone 4).

## Geometry

Coverage **646 / 646 records** have meshes. Counts were measured by
streaming every OBJ file, and re-measured independently by the
checker with zero mismatches over 1,577 distinct files:

| Tree | Distinct files | Vertices | Faces |
|---|---|---|---|
| IS-A | 952 | 891,477 | 1,630,986 |
| PART-OF | 625 | 456,063 | 812,446 |

Note: PART-OF compositions for vessels are the regional compositions
as the tables give them and can be broad (e.g. the brachiocephalic
artery record's PART-OF composition spans 93 files); the IS-A
composition is the vessel's own mesh set. Both are recorded as
released, as in Milestones 2 and 4.

TotalSegmentator overlap: all **13** cardiovascular labels of the TS
v1 label set map to inventory records (checker-verified against the
Milestone 3 intake). Approximate correspondences are flagged in the
inventory meta (iliac artery/vena labels keyed to the common iliac
records; `heart_myocardium` keyed to the heart organ record — the
myocardium exists only as PART-OF part concepts of the ventricular
walls; `portal_vein_and_splenic_vein` keyed to the right/left portal
vein records plus the splenic vein record).

## Clinical tranche

**69 clinical records** (the heart organ record + 68 vessel records)
and **8 variant records**, written against 20 consulted sources
(TeachMeAnatomy articles, StatPearls/NCBI anatomy articles,
OpenStax-based study material, JoVE Core, UAMS anatomy tables, and
the hepatic-variant literature for prevalences). Every entered value
is cited per field; everything not sourced is null plus an explicit
`verify` entry. TA names are null and verify-flagged on all 69
records — the consulted sources do not give them; a TA2 pass is
still owed, exactly as after Milestone 4.

Tiers (A = every clinical field sourced; B = sourced except
territory and/or termination; C = at least one core field —
origin/course/branches — verify-flagged):

| Group | Records | A | B | C |
|---|---|---|---|---|
| Heart | 1 | 1 | 0 | 0 |
| Coronary | 5 | 2 | 1 | 2 |
| Aorta and great vessels | 6 | 6 | 0 | 0 |
| Head and neck | 8 | 5 | 2 | 1 |
| Upper limb | 7 | 5 | 0 | 2 |
| Abdomen — visceral arteries | 9 | 8 | 0 | 1 |
| Pelvis and lower limb | 7 | 5 | 0 | 2 |
| Systemic veins | 20 | 11 | 0 | 9 |
| Portal venous system | 4 | 4 | 0 | 0 |
| Pulmonary | 2 | 0 | 0 | 2 |
| **Total** | **69** | **47** | **3** | **19** |

The Tier C pattern is narrow and disclosed: in 15 of the 19 cases the
only flagged core field is `branches`/`tributaries`, where the
consulted sources describe the vessel without enumerating its
branches (e.g. saphenous tributaries, LAD diagonal/septal branches).
The heart record is complete for chambers, valves, conduction system
(text), coronary supply and venous drainage — with the conduction
system, septa, chordae and pericardium flagged as absent from the
source data (below), not modelled.

Clinical records link **107 of the 646** inventory records as their
geometry; the remaining 539 inventory records are inventory-only in
v1 (named branches, segmental vessels, cusps/leaflets and the long
tail of lateralised branches).

### Variant records (variant gate: prevalence is a cited range, never a point value)

| Variant | Prevalence | Sources |
|---|---|---|
| Replaced right hepatic artery from SMA (Michels III) | 8.7–11.0% | S13 (corroborated S14) |
| Replaced left hepatic artery from left gastric (Michels II) | 3.0–10.0% | S14, S15 |
| Accessory left hepatic artery from left gastric (Michels V) | 8.0–11.0% | S15, S16 |
| Accessory right hepatic artery from SMA (Michels VI) | 7.0–10.7% | S13 |
| Common hepatic artery from SMA (Michels IX) | 1.0–4.5% | S13 |
| Right coronary dominance | 70–80% | S7 |
| Left coronary dominance | 5–10% | S7 |
| Coronary codominance | 10–20% | S7 |

Right dominance is the pattern the v1 coronary records describe
(marked modelled); every other variant carries an explicit
`unmodeled_note` per the gate. No prevalence was recorded for any
variant the consulted sources did not quantify (e.g. aberrant right
subclavian artery — not recorded).

## Checker results (`tools/cv_check.py`, exit 0)

All 26 hard checks pass, including: independent recount of both
vessel subtrees and the heart PART-OF set from the raw tables
(701 / 324 / 72, tags in full agreement); the concept partition (no
concept claimed by two records); re-probe of all 27 absence stems
over both tables (all absent); geometry paths exist and v/f counts
re-measure exactly (1,577 files); TS overlap (13/13); citation
completeness, null-field flag completeness, and tier recomputation
on all 69 clinical records; variant-gate validation on all 8
variants.

Reported, not gated: **58 branch/tributary names** carried in the
clinical records have no exactly matching concept or record name in
the release (class-level names where the release only lateralises,
and small branches the release omits). Each is flagged on its own
record by the builder's resolution pass; the full list is printed by
the checker.

## Flagged gaps — recorded, never filled

**Vessels with no concept of their own in the release** (clinical
records exist; no geometry can be linked):

- **External carotid artery** — absent entirely. Of its eight named
  branches in the consulted source, superior thyroid, lingual and
  facial arteries are also absent; the external carotid system is
  the module's largest single gap.
- **Middle cerebral artery** — absent; only its named branches exist
  as concepts/records.
- **Posterior cerebral artery** — absent; only its posteromedial
  central branch exists.
- **External jugular vein** — absent; only a "tributary of external
  jugular vein" family concept exists.
- **Pulmonary vein** — present only as an undivided family concept
  (FMA66643, 84 IS-A element files) with no lateralised instances;
  under the counting convention it produced no record. The anatomical
  four-vein pattern is stated in the clinical record and flagged.

**Absent outright** (27 probe stems re-verified over all six release
tables): the conduction system entire (sinoatrial node, AV node,
bundle of His, Purkinje fibres), pericardium, interatrial and
interventricular septa, chordae tendineae, ductus arteriosus /
ligamentum arteriosum, foramen ovale, thoracic duct, and the named
vessels: cystic artery, superficial palmar arch, profunda femoris
(deep artery of thigh — the femoral artery's main branch; present in
the clinical record as sourced text, flagged), profunda brachii,
thoracoacromial artery, obturator artery, superior gluteal artery,
ovarian artery, uterine artery, umbilical artery, median sacral
artery, lingual / facial / superior thyroid arteries.

**Named but recordless**: the fibular (peroneal) artery — the release
carries fibular *veins* only; the posterior tibial record flags its
fibular branch accordingly. The gastroduodenal artery exists only as
"trunk of gastroduodenal artery"; the clinical record links that
record and says so.

## Next steps

1. A source for the external carotid system, cerebral arteries and
   external jugular vein (a later BP3D release or another
   provenance-clean dataset) — the same class of decision Milestone 4
   recorded for the absent muscles; no hand-modelled substitutes.
2. TA2 pass to fill `ta_name` across the tranche (owed jointly with
   Milestone 4's).
3. Tier C → A upgrades: branch enumerations for the saphenous veins,
   coronary branches and the internal iliac artery from a consulted
   operative/anatomy source.
4. Variant geometry for the hepatic arterial variants once a
   variant-capable geometry source exists; until then the prevalence
   records stand as the gate requires.
5. The pulmonary vein family concept: decide whether the counting
   convention should admit specific named vessel families as un-sided
   records (would add this one record and change no other count).
