# Milestone 12 — Urinary system module v1

Status: built and checked locally. Not uploaded; presented for
approval as a unit, as with Milestones 2–11.

Method follows Milestones 4, 5, 9, 10 and 11: inventory from the
release tables → geometry mapping by exact lookup and streamed
counting → a clinical tranche whose values come only from sources
consulted during the build, cited per field → an independent
checker that shares no code with the builders.

## Deliverables

| File | Content |
|---|---|
| `tools/uri_map.py` | Census + geometry builder (rerunnable) |
| `data/urinary/urinary-inventory.json` | Concept census and the 6 derived records |
| `data/urinary/urinary-geometry.json` | Per-record mesh lists with measured vertex/face counts and bounding boxes |
| `tools/build_uri_records.py` | Clinical tranche builder (sources S1–S6 in its header) |
| `data/urinary/urinary.json` | 6 clinical records |
| `tools/uri_check.py` | Independent checker (fresh census, adrenal filing re-derived, re-measured geometry incl. bounding boxes, probe re-runs, disposition accounting, cross-module resolution, citation/flag/tier validation) |

## Inventory (from the BodyParts3D 4.0 tables)

Universe: **15 concepts** — 11 named in the IS-A tables, 12 in
the PART-OF tables, 8 in both. The urinary system is the smallest
and shallowest system census in the Body Model so far, and its
shape is the finding: the release carries the organs and nothing
inside them.

| Source set | Concepts |
|---|---|
| PART-OF urinary system (root FMA7159) | 10 |
| IS-A kidney line (root FMA7203) | 3 |
| IS-A ureter line (root FMA9704) | 3 |
| IS-A bladder + urethra (leaves, no shared root) | 2 |
| Adrenal gland, IS-A line (root FMA9604) — endocrine cross-reference | 3 |
| Adrenal gland instances, PART-OF — endocrine cross-reference | 2 |

Counting convention (stated in the inventory file): one record
per lateralised instance where the tables lateralise (right/left
kidney, right/left ureter), each keyed on its instance concept
with the side-stripped class concept carried as
`class_concept_id`; one record for each un-sided organ (urinary
bladder, urethra). The system root, the two upper urinary tracts
and the lower urinary tract are grouping classes — censused, not
records (the Milestone 11 tract-root pattern).

The PART-OF urinary tree in full: urinary system → right/left
upper urinary tract (each carrying one kidney and one ureter) and
lower urinary tract (urinary bladder, urethra). There is no IS-A
urinary-system root at all — FMA7159 does not occur in the IS-A
table; the IS-A side contributes the class concepts (kidney,
ureter) that PART-OF lacks, the bladder and urethra filed as
leaves under generic organ classes.

**Records: 6** — all whole-concept:

- Kidneys 2: right kidney, left kidney (instances; class FMA7203
  carried).
- Ureters 2: right ureter, left ureter (instances; class FMA9704
  carried).
- Urinary bladder 1 (un-sided, both tables).
- Urethra 1 (un-sided, both tables) — a single **unsexed,
  undivided** concept: no male or female form and no named part
  exists (see the gap analysis).

Disposition accounting for the 15 universe concepts, verified
exactly by the checker: **6 records**, **2 class-carried** (the
kidney and ureter classes), **4 grouping classes** (urinary
system, right/left upper urinary tract, lower urinary tract),
**3 endocrine cross-references** (the adrenal class and its two
instances). Nothing in the universe is unaccounted, and there
are zero subtree-internal concepts — this system has no interior
to be internal to.

A name sweep over both tables for urinary terms outside the
universe rejected **39 names**, every one adjudicated: 38 are
vessels — the renal, suprarenal and ureteric-segment arteries
and veins, which are cardiovascular records (the cardiovascular
census carries those 38 concepts in 27 records, including the
`artery.renal-artery` and `vein.renal-vein` clinical records this
module cites) — and one is the gallbladder, a digestive record
whose name contains "bladder". No urinary organ hides outside
the universe; the checker re-derives the sweep and gates that
every rejected name is a vessel or the gallbladder.

## The adrenal filing (cross-reference, recorded, not duplicated)

The task for this module included censusing where the release
files the adrenal glands. The finding, re-derived from the
tables by the checker: **the release files them under endocrine,
not urinary.** In PART-OF, the right and left adrenal glands
(FMA15629/FMA15630) are direct children of FMA9668 "endocrine
system" and occur nowhere in the urinary system subtree. In
IS-A, the class FMA9604 "adrenal gland" hangs under a generic
organ class (corticomedullary organ) beside the kidney, with the
two instances as its only descendants. The TotalSegmentator
census (Milestone 3) concurs: `adrenal_gland_left/right` are
filed under endocrine there too. The three concepts are censused
in this module as an endocrine cross-reference with the finding
recorded in the inventory's `adrenal_filing` block; they get **no
urinary record and no clinical record here** — the endocrine
module (queued) owns them. The kidney clinical record notes the
one sourced anatomical relation (the glands sit immediately
superior to the kidneys within a separate envelope of the renal
fascia, S1) and nothing more. The release's name is "adrenal
gland" only: the synonym "suprarenal gland" is probe-verified
absent as a concept, although the suprarenal *vessels* exist as
cardiovascular records.

## Geometry

Coverage **6/6 records** in both tables combined. The independent
checker re-measured all **12 mesh entries** by streaming —
vertex counts, face counts AND bounding boxes — and verified the
FJ-file attribution of every record against the element-parts
tables: **0 mismatches**.

Distinct mesh files: IS-A 6 files (5,402 vertices / 9,944 faces);
PART-OF 6 files (5,402 vertices / 9,944 faces) — each organ
carries exactly one mesh per table, and the two tables' meshes
for these concepts measure identically.

## TotalSegmentator overlap

Of the 104 TotalSegmentator v1 labels, **exactly 3 are urinary**:
`kidney_right`, `kidney_left`, `urinary_bladder`, each present
in all 1,204 subjects of the M3 census. All three map to
inventory records. TS adds nothing the release lacks: there is
**no ureter label and no urethra label** in v1, and nothing below
the organ level. The `adrenal_gland_left/right` labels are filed
under endocrine in that census (2 of the 104), concurring with
the BP3D filing above.

## Clinical tranche

**6 records, Tier A 6 / B 0 / C 0** — every field sourced from
the 6 sources consulted during the build (TeachMeAnatomy
articles on the kidneys, ureters and urinary bladder; OpenStax
A&P 2e §25.2 for urine transport and the nephron, §25.3 for the
gross kidney), cited per field in each record's `sources` map.
TA names were not given by the consulted sources and are null +
verify-flagged on all records, as in Milestones 4/5/9/10/11.

| Group | Records |
|---|---|
| Kidney (kidney organ, nephron) | 2 |
| Urinary pathway (ureter, urinary pathway) | 2 |
| Lower urinary tract (urinary bladder, urethra) | 2 |

Geometry linkage: **6 of 6** clinical records link at least one
inventory record, and **6 of 6** inventory records are linked
from the tranche (the pathway record links all six organs). No
clinical record links nothing — but two records (nephron, and
the pathway's intrarenal stations) carry recorded absences for
their own sub-structures, checker-gated in the Milestone 9/10/11
pattern.

Notable items:

- **Kidney structure in sourced order.** Coverings deep to
  superficial (renal capsule → perirenal fat → renal fascia →
  pararenal fat, S1); parenchyma as cortex and medulla, the
  cortex extending in as renal columns that divide the kidney
  into 6–8 lobes (S1/S6); drainage papilla → minor calyx →
  major calyx → renal pelvis (S1/S6); hilum with the veins
  leaving anterior to the arteries (S1); supply from the renal
  arteries — anterior division 75% / posterior 25%, five
  segmental end arteries, the interlobar → arcuate →
  interlobular → afferent sequence (S1) — cited to the
  cardiovascular module's records, never duplicated.
- **The nephron as the sources structure it.** Segments in
  filtrate order: renal corpuscle (glomerulus + glomerular
  capsule) → proximal convoluted tubule → loop of Henle →
  distal convoluted tubule → collecting duct (S5); cortical
  vs juxtamedullary types with the sourced ~15% juxtamedullary
  share and the vasa recta; the juxtaglomerular apparatus and
  macula densa (S5). The record is text on the two whole-kidney
  geometry records — the nephron itself has no concept.
- **The three ureteric constrictions, as a sourced list in
  course order** (S2): ureteropelvic junction; pelvic inlet,
  where the ureter crosses the iliac vessels; ureterovesical
  junction, the narrowest. The record also carries S2's own
  caveat that recent evidence puts impaction predominantly at
  the upper ureter and the UVJ. Course, the uterine-artery and
  vas-deferens relations at risk, supply and T11–L2 sensory
  levels are all from S2; the oblique bladder entry as a
  physiological sphincter is dual-sourced (S2/S4).
- **A source disagreement, recorded rather than resolved.** The
  ureter's length is ~25 cm in TeachMeAnatomy (S2) and ~30 cm in
  OpenStax (S4); the record's extent field carries the range
  25–30 cm with both citations. Bladder capacity is likewise
  carried as 400–600 mL (S3) with OpenStax's 500–600 mL noted
  (S4).
- **Bladder parts and the trigone.** Apex, body, fundus, neck in
  order (S3); the trigone as the smooth triangular area within
  the fundus marked by the two ureteric orifices and the
  internal urethral orifice, of mesonephric-duct origin (S3/S4);
  the detrusor as crisscrossing smooth muscle (S3/S4); control —
  sympathetic hypogastric T12–L2 relaxing the detrusor,
  parasympathetic pelvic S2–S4 contracting it, pudendal S2–S4
  to the external sphincter (S3).
- **The urethra's sex difference, stated against an unsexed
  inventory.** The urethra is the only urinary structure that
  differs significantly between the sexes (S4): female ~4 cm;
  male ~20 cm in four regions in order (preprostatic,
  prostatic, membranous, spongy). The clinical record carries
  both, and flags on both fields that neither has a BP3D
  concept — the release's single urethra is unsexed, so the
  sexed anatomy is text over one shared geometry record.

## Checker results (`tools/uri_check.py`, exit 0)

**136 hard checks PASS, 0 FAIL.** Highlights: the full concept
universe re-derived from the six tables set-by-set (15 concepts,
all 6 set counts exact); anchor concepts verified by name in
both tables; the adrenal filing re-derived from PART-OF
parentage and subtree membership (endocrine, not urinary) and
matched against the inventory's recorded finding;
cross-reference census re-derived (3 endocrine); rejected-sweep
census re-derived (39 names, all vessels or the gallbladder);
record concept sets exact and disjoint; disposition accounting
partitions the universe exactly (6 + 2 + 4 + 3 = 15, zero
subtree-internal); geometry fully re-measured (12 entries,
counts + bounding boxes, FJ attribution exact, 0 mismatches);
TS census parsed independently (104 labels, 3 urinary, all
mapped; no ureter/urethra label); absence probes re-run (below);
cardiovascular pointers resolve (the renal clinical records;
the renal/suprarenal census re-counted at 38 concepts / 27
records); clinical citation/flag/tier discipline re-validated
for all 6 records against the checker's own core/soft table,
including pathway station order, nephron segment order, kidney
covering order, the three constrictions in course order, the
four bladder parts, the urethra's sourced sex difference — and
the gate that no adrenal record exists anywhere in this module.

## Gap analysis — quantified, recorded, never filled

**92 absence probes** were run as occurrence counts over all six
release tables; **74 returned zero hits**. The checker re-ran
the identical probe set and reproduced the identical absent
list. Probe-verified absences, by consequence:

- **The kidney has no interior in this release.** No cortex or
  medulla of kidney, no renal pyramid, papilla or column, no
  renal pelvis, no major or minor calyx (the string "calyx"
  occurs nowhere in the six tables), no renal capsule, hilum,
  sinus, lobe or segment concept. Every internal field of the
  kidney clinical record is sourced text on whole-organ
  geometry. A kidney procedure cannot be staged against
  intrarenal geometry from this dataset.
- **The nephron does not exist as data.** No nephron, glomerulus
  or glomerular capsule, no proximal or distal tubule, no loop
  of Henle, no collecting duct, no juxtaglomerular apparatus or
  macula densa, no vasa recta or peritubular capillary, no
  afferent or efferent arteriole concept. The functional unit
  the physiology engine will eventually model segment-by-
  segment is, in the Body Model, one sourced text record.
- **The bladder is one undivided volume.** No apex, body, fundus
  or neck concept; no trigone; no detrusor; no uvula or
  interureteric ridge; no internal urethral orifice. And its
  vessels are missing with it: "vesical artery" and "vesical
  vein" return zero hits — the cardiovascular census carries no
  vesical record either (checker-gated on the bladder record's
  verify list), so the bladder's supply is text-only from both
  sides of the module boundary.
- **The urethra is unsexed and undivided.** No male urethra, no
  female urethra, no preprostatic/prostatic/membranous/spongy
  part, no internal or external urethral sphincter, no external
  urethral orifice. The single most sex-differentiated structure
  in the system is the one the release refuses to differentiate;
  catheterisation and urethral procedures have no geometry
  beyond the one shared tube.
- **The ureter has no junctions.** No ureteropelvic,
  ureterovesical or vesicoureteric junction, no abdominal/pelvic/
  intramural part, no ureteric orifice. The three constrictions —
  the surgically load-bearing list of this module — are sourced
  text on whole-ureter geometry.
- **The adrenal glands have no interior either** (recorded here
  because the glands were censused here): no adrenal cortex or
  medulla, no zona glomerulosa/fasciculata/reticularis. The gap
  belongs to the endocrine module's census, but it is measured
  now: the endocrine module will inherit glands as undivided as
  the urinary organs.
- **TS ceiling:** TotalSegmentator v1 stops at three urinary
  labels (kidneys, bladder) and has no ureter or urethra label
  at all, so CT-derived geometry cannot fill any of the above
  either.

Cross-module continuities confirmed while building: the renal
and suprarenal vessels are the cardiovascular module's records
(38 concepts / 27 records, cited per field); the prostate —
the bladder neck's inferior neighbour in the male — is a
reproductive-module concept (present in both tables under the
genital system) and is referenced in text only; the adrenal
glands are the endocrine module's records-to-be, cross-referenced
under a re-derived filing. The urinary module invents no record
for another module's structure.

## Next steps

1. A TA2 pass for `ta_name` across the urinary records (owed
   jointly with the muscular/nervous/respiratory/digestive TA
   debt since Milestone 4).
2. The dataset-shaped gaps — kidney interior, nephron, bladder
   parts and trigone, sexed/divided urethra, ureteric junctions —
   need a source beyond BP3D 4.0 + TS v1: the same class of
   blocker as Milestone 9's peripheral-nerve gap, Milestone
   10's pleura gap and Milestone 11's common-bile-duct gap, and
   the most complete one yet: this system's gap is its entire
   interior. Recorded, not filled.
3. Endocrine module (queued): it inherits the adrenal records
   this module censused as a cross-reference, with the filing
   finding and the adrenal-interior gap already measured; the
   endocrine census should key its adrenal records on FMA9604 /
   FMA15629 / FMA15630 so the two modules' boundary closes by
   construction.
4. Physiology follow-on: the nephron record's segment order
   (corpuscle → PCT → loop of Henle → DCT → collecting duct)
   and the kidney's segmental end-artery sequence are the unit
   list a renal compartment would attach to in the Milestone 8
   engine; the bladder's sourced capacity range (400–600 mL) is
   the storage parameter.
5. Theatre follow-on: the ureteric constriction list and the
   ureter's relations at risk (uterine artery, vas deferens)
   are the at-risk structure list a pelvic procedure would be
   authored against — but with no junction geometry, a
   ureteric-stone procedure can be staged only at whole-organ
   resolution until step 2 lands.
6. Remaining systems queue per the Master Plan: lymphatic,
   endocrine, reproductive, integumentary.
