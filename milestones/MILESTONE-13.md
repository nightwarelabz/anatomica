# Milestone 13 — Lymphatic + endocrine system modules v1

Status: built and checked locally. Not uploaded; presented for
approval as a unit, as with Milestones 2–12.

Method follows Milestones 4, 5, 9, 10, 11 and 12, applied to two
systems as strictly separate data modules with separate map
tools, records builders and checkers: inventory from the release
tables → geometry mapping by exact lookup and streamed counting →
a clinical tranche per system whose values come only from sources
consulted during the build, cited per field → an independent
checker per system that shares no code with its builders.

The two systems share one property that dominates both censuses:
**the release carries their organs and almost nothing of their
substance.** The lymphatic system's conducting and filtering
apparatus does not exist in the data at all — the string "lymph"
occurs in no concept name in either parts list. The endocrine
system's most surgically consequential glands — thyroid,
parathyroids — likewise do not exist, and no gland the release
does carry has any interior. Both modules therefore pair a small
exact geometry layer with sourced clinical text records that
carry the systems' content and record the absences on their face.

## Deliverables

| File | Content |
|---|---|
| `tools/lymph_map.py` | Lymphatic census + geometry builder (rerunnable) |
| `data/lymphatic/lymphatic-inventory.json` | Concept census and the 4 derived records |
| `data/lymphatic/lymphatic-geometry.json` | Per-record mesh lists with measured vertex/face counts and bounding boxes |
| `tools/build_lymph_records.py` | Lymphatic clinical tranche builder (sources S1–S3 in its header) |
| `data/lymphatic/lymphatic.json` | 4 clinical records |
| `tools/lymph_check.py` | Independent lymphatic checker (37 checks) |
| `tools/endo_map.py` | Endocrine census + geometry builder (rerunnable) |
| `data/endocrine/endocrine-inventory.json` | Concept census and the 3 derived records |
| `data/endocrine/endocrine-geometry.json` | Per-record mesh lists with measured vertex/face counts and bounding boxes |
| `tools/build_endo_records.py` | Endocrine clinical tranche builder (sources S1–S8 in its header) |
| `data/endocrine/endocrine.json` | 6 clinical records |
| `tools/endo_check.py` | Independent endocrine checker (42 checks, incl. the Milestone 12 boundary closure) |

---

# Part I — Lymphatic system

## Inventory (from the BodyParts3D 4.0 tables)

Universe: **5 concepts** — 4 named in the IS-A table, 3 in the
PART-OF table, 2 in both. It is the smallest system census in the
Body Model, and its shape is the finding:

| Source set | Concepts |
|---|---|
| IS-A spleen (FMA7196, a leaf) | 1 |
| IS-A thymus lobe line (class FMA71193 + 2 instances) | 3 |
| PART-OF thymus (organ FMA9607 + its 2 lobes) | 3 |

There is **no lymphatic system root in either table** — nothing
to census as a grouping class. The spleen exists in IS-A only, as
a leaf under the generic class "corticomedullary organ"; it occurs
nowhere in PART-OF. The thymus exists as an organ in PART-OF only,
filed under "content of anterior mediastinum", with its two lobes
as its only parts; IS-A carries the lobe line and no thymus organ
concept. The lobes are the only concepts present in both tables.

**Records: 4** — 3 whole-concept, 1 partof-organ:

- Spleen 1 (un-sided; keyed on its IS-A concept, the only table
  that carries it).
- Thymus 1 (un-sided organ; keyed on its PART-OF concept — the
  Milestone 9 partof-organ pattern).
- Thymus lobes 2: right lobe of thymus, left lobe of thymus
  (instances; class FMA71193 carried as `class_concept_id` — the
  Milestone 12 instance pattern).

Disposition accounting for the 5 universe concepts, verified
exactly by the checker: **4 records**, **1 class-carried** (the
lobe class). There are no grouping classes, no cross-references
and no subtree-internal concepts: this system has no root and no
interior to account for.

A name sweep over both tables for lymphatic terms (lymph, spleen,
splenic, thymus, thymic, tonsil, marrow, peyer) outside the
universe rejected exactly **4 names**, all cardiovascular and
already owned by Milestone 5: splenic artery, splenic vein,
subdivision of splenic artery, tributary of splenic vein. The
vermiform appendix — the one MALT-bearing organ the release does
carry — is the digestive module's record (Milestone 11) and is
adjudicated there, not claimed here.

## Geometry

Coverage **4/4 records**:

| Record | Table | Files | Vertices | Faces |
|---|---|---:|---:|---:|
| spleen | IS-A | 1 | 689 | 1,330 |
| thymus | PART-OF | 2 | 1,205 | 2,080 |
| thymus-lobe.right-lobe-of-thymus | each table | 1 | 599 | 1,030 |
| thymus-lobe.left-lobe-of-thymus | each table | 1 | 606 | 1,050 |

The thymus organ's PART-OF mesh set is exactly the union of its
two lobes' files (FJ3150/FJ3151), and the checker gates that each
of those files is shared by exactly the organ record and its own
lobe record, in the Milestone 5/9 nested-composition pattern. The
spleen has an IS-A mesh and no PART-OF mesh, matching its
IS-A-only filing. Per-record entry totals (shared files counted
per owning record): IS-A 1,894 v / 3,410 f; PART-OF 2,410 v /
4,160 f; 7 mesh entries re-measured by the checker with bounding
boxes, 0 mismatches.

## TotalSegmentator overlap

Exactly **1 of the 104 TS v1 labels is lymphatic**: `spleen`,
present in all 1,204 subjects, mapping to the spleen record. TS
has no thymus, node, vessel, trunk or duct label, so it adds no
coverage the release lacks.

## Clinical tranche

**4 records, tiers A2 / B2**, sources S1 TeachMeAnatomy "The
Spleen", S2 OpenStax A&P 2e §21.1, S3 StatPearls "Anatomy, Head
and Neck, Thymus" (consulted at search-excerpt level; the full
page was blocked by a robot check, and the source entry says so):

| Record | Tier | Geometry | Content |
|---|---|---|---|
| `organ.spleen` | B | spleen | Position, internal structure (capsule, surfaces, red/white pulp), function; splenic artery/vein fields cross-referencing the cardiovascular records; coeliac-plexus innervation; pancreaticosplenic-node drainage. **Null: relations** — the consulted page's relations table did not render in the fetch; flagged, not filled. |
| `organ.thymus` | B | thymus + both lobes | Position (mediastinum, manubrium, cervical extensions), lobule/cortex/medulla structure, T-cell maturation function, involution rates. **Null: arterial supply** — no consulted source states it; flagged. |
| `pathway.lymphatic-drainage` | A | none (absence recorded) | The drainage pathway in the consulted source's order — capillaries → vessels → trunks → ducts → the jugular-subclavian venous junction — with daily fluid volumes, the no-pump mechanism, and both ducts' territories incl. the cisterna chyli. The checker gates the station order in the stored sequence. |
| `structure.lymph-nodes` | A | none (absence recorded) | Nodes (~500–600, internal flow path), tonsils, and MALT incl. Peyer's patches — all as sourced text; none exists in the dataset. |

## Gap analysis (probe-verified)

52 probes over all six release tables: **44 zero-hit, 8 present**
(every present probe is a control: the 5 universe names, the two
splenic vessels, the appendix). The zero-hit set is the system
itself:

- **The conducting system, entire**: lymph, lymphatic system,
  lymph node, lymphatic vessel, lymphatic trunk, lymphatic duct,
  **thoracic duct (re-verified absent; Milestone 5's finding
  stands)**, right lymphatic duct, cisterna chyli, lymphatic
  capillary, lymphoid tissue of every named kind.
- **Every named node group**: cervical, axillary, inguinal,
  mesenteric, bronchopulmonary, pancreaticosplenic, coeliac,
  lumbar — none exists.
- **Tonsils and MALT**: tonsil, palatine/pharyngeal/lingual
  tonsil, adenoid, peyer, mucosa-associated lymphoid tissue —
  none exists.
- **Bone marrow**: marrow, bone marrow, red/yellow bone marrow —
  none exists; the other primary lymphoid organ is as absent as
  the nodes.
- **Interiors of the two organs present**: splenic pulp, red
  pulp, white pulp, splenic hilum, trabecula of spleen; lobule,
  cortex and medulla of thymus — none exists.

## Checker

`tools/lymph_check.py`: **37/37 checks PASS**, exit 0 — universe,
records and dispositions re-derived; sweep re-derived; all 52
probes re-run identically; geometry re-measured incl. bounding
boxes and FJ attribution; TS overlap re-derived from the M3 label
index; clinical citation/flag/tier discipline re-derived against
the checker's own field table; content gates on the pathway
station order and the splenic cross-references resolving to
cardiovascular clinical records.

---

# Part II — Endocrine system

## Inventory (from the BodyParts3D 4.0 tables)

Universe: **10 concepts** — 9 named in the IS-A table, 6 in the
PART-OF table, 5 in both.

| Source set | Concepts |
|---|---|
| PART-OF endocrine system (root FMA9668) | 4 |
| IS-A adrenal line (class FMA9604 + 2 instances) | 3 |
| IS-A pituitary gland (FMA13889, both tables) | 1 |
| Pineal body (FMA62033) — nervous cross-reference | 1 |
| Pancreas (FMA7198) — digestive cross-reference | 1 |
| IS-A testis line (class FMA7210 + 2 instances) — reproductive cross-reference | 3 |

The PART-OF tree the release itself names endocrine contains
exactly three members below its root: the pituitary gland and the
two adrenal glands. The IS-A side contributes the class concepts
(adrenal gland) hung under generic organ classes — the adrenal
under "corticomedullary organ", the pituitary under "lobular
organ" — and **no IS-A concept name contains the word
"endocrine" at all**.

**Records: 3** — all whole-concept:

- Pituitary gland 1 (un-sided; carried by both tables).
- Adrenal glands 2: right adrenal gland, left adrenal gland
  (instances; class FMA9604 carried as `class_concept_id`).

Disposition accounting for the 10 universe concepts, verified
exactly by the checker: **3 records**, **1 class-carried** (the
adrenal class), **1 grouping class** (the endocrine system root),
**5 cross-references** — pineal body to the nervous module
(its record `brain.pineal-body`, Milestone 9), pancreas to the
digestive module (Milestone 11), and the testis class with its
two instances to the reproductive module, queued next. Nothing
is unaccounted; there are no subtree-internal concepts.

**The Milestone 12 boundary closes by construction, and the
checker gates it**: the urinary module censused exactly three
adrenal concepts (FMA9604, FMA15629, FMA15630) as an endocrine
cross-reference and made no records; this module's adrenal census
— the class-carried class plus the two instance records — is
exactly that set.

A name sweep over both tables for endocrine terms (endocrine,
gland, thyroid, parathyroid, pituitary, pineal, adrenal,
suprarenal, hypophysis, islet) outside the universe rejected
**37 names**, every one adjudicated: the salivary set belongs to
the digestive module (Milestone 11); the **lacrimal gland set
(FMA59101 + right/left instances) has no owning module yet** —
recorded here, claimed by no one; the suprarenal and inferior
thyroid vessels are cardiovascular inventory records; the thyroid
cartilage is skeletal; the sternothyroid and cricothyroid lines
are muscular; "organ component gland" is a generic class. One
composition quirk is recorded, not used: the endocrine root's
PART-OF element set lists 7 files including the pancreas's,
because the release's own composition reaches across the module
boundary — the root is a grouping class and no geometry is taken
from it.

## Geometry

Coverage **3/3 records**; both tables carry identical meshes for
every record:

| Record | Files (per table) | Vertices | Faces |
|---|---:|---:|---:|
| pituitary-gland | 1 | 609 | 1,164 |
| adrenal-gland.right-adrenal-gland | 1 | 1,149 | 2,294 |
| adrenal-gland.left-adrenal-gland | 1 | 2,000 | 3,996 |

Totals per table: 3,758 v / 7,454 f. 6 mesh entries re-measured by
the checker with bounding boxes, 0 mismatches; every file is
single-owned per table.

## TotalSegmentator overlap

Exactly **2 of the 104 TS v1 labels are endocrine**:
`adrenal_gland_right` and `adrenal_gland_left`, each present in
all 1,204 subjects, mapping to the two adrenal records. TS has no
pituitary, pineal, thyroid or parathyroid label; the pancreas
label maps to the digestive module's record, cross-referenced
here.

## Clinical tranche

**6 records, tiers A5 / B1**, sources S1 TeachMeAnatomy "The
Pituitary Gland", S2 TeachMeAnatomy "The Thyroid Gland", S3
TeachMeAnatomy "The Adrenal Glands", S4–S8 OpenStax A&P 2e §§17.3,
17.4, 17.5, 17.7, 17.9. Hormone names are asserted only where a
consulted source lists them; the checker gates the pituitary
record's product field against the consulted table's full list:

| Record | Tier | Geometry | Content |
|---|---|---|---|
| `gland.pituitary-gland` | A | pituitary gland | Sella position; two-part structure (Rathke's pouch anterior, hypothalamic posterior); products — anterior GH, PRL, TSH, ACTH, FSH, LH, intermediate MSH, posterior release of hypothalamic ADH and oxytocin; relations incl. the optic chiasm; the hypophyseal portal system; hypothalamic control. |
| `gland.thyroid-gland` | A | none (absence recorded) | C5–T1 position, lobes and isthmus, follicle/colloid structure, T4/T3 and calcitonin; superior/inferior thyroid supply (the inferior pair resolving to cardiovascular inventory records; the superior thyroid artery's parent, the external carotid, is a Milestone 5 absence); venous and lymphatic drainage; **the recurrent laryngeal nerve's full course and surgical risk, cross-referencing the nervous module's `nerve.cn-10-vagus`**; TSH-axis control. |
| `gland.parathyroid-glands` | B | none (absence recorded) | Posterior-thyroid position (usually four glands), chief-cell PTH and its calcium actions, oxyphil cells, the calcitonin pairing. **Null: arterial supply** — no consulted source states it in citable form; flagged. |
| `gland.adrenal-gland` | A | both adrenal records | Suprarenal position and relations, perinephric fascia; cortex with its three zones **in anatomical order** (checker-gated: glomerulosa → fasciculata → reticularis) and their products; medullary chromaffin catecholamines; three-tier arterial supply naming the cardiovascular suprarenal records; the asymmetric venous drainage (right → IVC, left → left renal vein); innervation; lymphatics. Cortex/medulla/zones have no concepts — sourced text on the whole-gland records, flagged on the record. |
| `gland.pineal-gland` | A | none — geometry held by the nervous module | Diencephalic position; pinealocyte melatonin; circadian function (with the source's own "not entirely understood" caveat carried); the retina–SCN–spinal regulation pathway. The record's verify entry names the nervous inventory record `brain.pineal-body` (FMA62033) as the geometry holder, and the checker resolves that pointer rather than accepting an absence. |
| `gland.pancreatic-islets` | A | none (absence recorded) | Definition, the four cell varieties with the consulted source's proportions (alpha ~20%, beta ~75%, delta ~4%, PP ~1%) and their products; host-organ field pointing at the digestive module's `pancreas` / `organ.pancreas` records, resolved by the checker. |

## Gap analysis (probe-verified)

52 probes over all six release tables: **41 zero-hit, 11
present** (every present probe is a control: the endocrine root,
the pituitary, the pineal body, the adrenal line, the pancreas,
the testis line, the hypothalamus). The zero-hit set:

- **The thyroid gland, entire**: thyroid gland, lobe, isthmus,
  follicle, parafollicular cells, pyramidal lobe — none exists.
  The release carries the gland's arteries, its cartilage
  namesake and two muscles named for it, but not the gland.
- **The parathyroid glands, entire**: parathyroid in any form,
  superior/inferior parathyroid, chief cell — zero hits anywhere.
- **The endocrine pancreas**: pancreatic islet, islet,
  Langerhans, endocrine pancreas — none exists; the pancreas
  record is exocrine-side data only.
- **Every gland interior**: adenohypophysis, neurohypophysis,
  both pituitary lobes by name, pars distalis/nervosa/intermedia,
  infundibulum (zero hits in all six tables); adrenal cortex,
  adrenal medulla, all three zonae, chromaffin tissue; the
  synonym "suprarenal gland" itself; "pineal gland" as a name
  (the release's name is "pineal body"); pinealocyte; any generic
  "endocrine gland" class.
- **The gonad asymmetry the reproductive module inherits**: the
  testis line exists (IS-A only); **ovary, ovarian, ovarian
  follicle and corpus luteum score zero hits in both parts
  lists** — the female gonad has no data in the release at all.
  Seminiferous and Leydig concepts are likewise absent.

## Checker

`tools/endo_check.py`: **42/42 checks PASS**, exit 0 — universe,
records and dispositions re-derived; the **Milestone 12 boundary
closure gated as an equality** (urinary endocrine cross-reference
set == this module's adrenal census); sweep re-derived incl. the
lacrimal no-owner adjudication; all 52 probes re-run identically;
geometry re-measured incl. bounding boxes and FJ attribution; TS
overlap re-derived; clinical citation/flag/tier discipline
re-derived against the checker's own field table; content gates
on the cortical zone order, the pituitary hormone list, and every
cross-module pointer resolving (nervous vagus record, nervous
pineal record, digestive pancreas records, eight named
cardiovascular inventory records).

---

# Cross-module continuities

- **M12 → M13 (adrenals)**: closed by construction and gated —
  see Part II.
- **M5 → M13**: the thoracic duct's absence is re-verified; the
  spleen's supply fields resolve to Milestone 5's splenic
  clinical records, and the adrenal/thyroid fields to its
  suprarenal and inferior-thyroid inventory records; the superior
  thyroid artery remains unrecordable because its parent, the
  external carotid artery, is a Milestone 5 concept absence.
- **M9 → M13**: the pineal split is kept symmetric — geometry in
  the nervous module, endocrine account here, each side pointing
  at the other; the thyroid record's load-bearing nerve relation
  resolves to the nervous module's vagus record. Milestone 9's
  finding stands and deepens: 11 of 45 muscle innervation names
  resolved to nervous clinical records and 0 to geometry; the
  lymphatic module now adds that the nodes those nerves' immune
  organs drain to have no geometry either.
- **M11 → M13**: the pancreas boundary is symmetric with the
  adrenal one — digestive owns the organ and its geometry, this
  module carries the islets as sourced text with the absence
  recorded, and the checker resolves the pointer.
- **Lacrimal glands (no owner)**: FMA59101 with its right/left
  instances exists in the release and belongs to no system module
  built so far. It is recorded in this census's sweep and left
  unclaimed; assigning it (a head/sensory grouping, or the
  integumentary module's adnexa) is an open decision, flagged
  here rather than resolved silently.

# Next steps

1. **Reproductive module (next in the queue)** — inherits from
   this milestone: the testis cross-reference set
   {FMA7210, FMA7211, FMA7212} to convert into its own census,
   the total absence of ovary/ovarian concepts as its headline
   gap, and from Milestone 12 the single unsexed urethra concept
   whose sexed anatomy the release does not carry.
2. **Integumentary module (last system)**, after which the Body
   Model's system census is complete.
3. **Dataset-gap blockers, now twice the same shape**: the
   lymphatic system beyond two organs, the thyroid/parathyroid/
   islet glands, and every gland interior are absent from BP3D
   4.0 and from TotalSegmentator v1 alike — the same blocker class
   as Milestone 9's nerve concepts. Closing any of them needs a
   source beyond the two adopted datasets (full FMA/TA remains
   the named candidate); nothing here is filled in the meantime.
4. The TA2 `ta_name` pass remains owed across the Milestone
   4/5/9/10/11/12 tranches and now both Milestone 13 tranches
   (every record in both new tranches carries the flag).
5. The lacrimal-gland ownership decision, above.
