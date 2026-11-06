# Milestone 9 — Nervous system module v1

Status: built and checked locally. Not uploaded; presented for
approval as a unit, as with Milestones 2–8.

Method follows Milestones 4 and 5: inventory from the release tables
→ geometry mapping by exact lookup and streamed counting → a clinical
tranche whose values come only from sources consulted during the
build, cited per field → an independent checker that shares no code
with the builders. This module also closes Milestone 4's open finding
C3, which it quantifies exactly (below).

## Deliverables

| File | Content |
|---|---|
| `tools/nerve_map.py` | Census + geometry builder (rerunnable) |
| `data/nervous/nervous-inventory.json` | Concept census and the 133 derived records |
| `data/nervous/nervous-geometry.json` | Per-record mesh lists with measured vertex/face counts |
| `tools/build_nerve_records.py` | Clinical tranche builder (sources S1–S11 in its header) |
| `data/nervous/nervous.json` | 52 clinical records |
| `tools/nerve_check.py` | Independent checker (fresh census, re-measured geometry, probe re-runs, citation/flag/tier validation, M4-C3 continuity report) |

## Inventory (from the BodyParts3D 4.0 tables)

Universe: **286 concepts**.

| Source set | Concepts |
|---|---|
| IS-A neural tree (root FMA11195 "segment of neural tree organ") | 62 |
| IS-A cranial-nerve class line (root FMA5865) | 4 |
| IS-A neuraxis part trees (20 "… of neuraxis" roots) | 170 |
| IS-A subdivision lines (nervous / autonomic / parasympathetic) | 5 |
| IS-A dura line + tentorium cerebelli | 3 |
| IS-A name-sweep additions (hippocampus line, region of cerebral cortex) | 4 |
| PART-OF nervous system (root FMA7157) + brainstem line | 91 |

How the release files the system (established by inspection, all
re-derived at run time): peripheral nerves hang under the neural-tree
root, which also carries the ganglion line — its only specific
ganglion is the ciliary ganglion. The "cranial nerve" class hangs
outside that tree and carries only the trochlear line; the optic
nerve travels inside the tree as a nerve trunk, and the short ciliary
nerve is filed under the parasympathetic subdivision line. Central
structures hang in IS-A under generic neuraxis part roots, as the
heart parts did in Milestone 5. The brain as an organ exists only in
PART-OF; its tree carries the lateralised lobes, gyri, hemispheres
and ventricles and the spinal cord, while the brainstem line (brainstem
+ medulla oblongata) hangs under head proper and the cerebellum —
an IS-A neuraxis concept — hangs under head proper in PART-OF too;
both are counted once, in the union.

**133 records** under the stated counting convention (one record per
lateralised instance where the tables lateralise; one record for an
un-sided class modelled jointly; the brain and spinal cord keyed on
their PART-OF organ concepts; named PART-OF-only parts keyed on
PART-OF concepts; structural roots, generic part classes,
segment/zone/region/subdivision classes, nerve branch-of classes and
aggregate concepts are not records):

| Representation | Records |
|---|---|
| whole-concept (per side or un-sided) | 118 |
| partof-concept (PART-OF-only named parts) | 13 |
| partof-organ (brain, spinal cord) | 2 |

By subtree: peripheral 34 (the cranial-nerve II/III/IV/V1 records,
the ciliary ganglion pair, the optic chiasm and tracts), central IS-A
83, central PART-OF 15, meningeal 1 (tentorium cerebelli).

Two filing asymmetries are recorded as released, not repaired: the
release carries a **left stria terminalis only** (class + left
instance; no right instance exists), and the short ciliary nerve is
a single un-sided record.

## Geometry

Coverage **133 / 133 records** have meshes — but read the composition
caveat below. Counts were measured by streaming every OBJ file and
re-measured independently by the checker with zero mismatches over
338 mesh entries:

| Tree | Distinct files | Vertices | Faces |
|---|---|---|---|
| IS-A | 133 | 249,660 | 455,356 |
| PART-OF | 60 | 179,170 | 322,990 |

The IS-A compositions partition exactly (summed-over-records equals
distinct: 133 files). The PART-OF compositions nest, as in Milestone
5: 205 entries over records against 60 distinct files — the brain
organ record's composition (59 files) contains its parts' files.
Coverage is a statement about the release's element compositions:
many central records are keyed on class concepts whose composition
is the class mesh set as released; no mesh was hand-made or borrowed
from another structure.

TotalSegmentator overlap: of the 104 TS v1 labels, exactly **one**
is neural-adjacent — `brain`, which maps to the PART-OF brain organ
record (checker-verified against the Milestone 3 intake and a fresh
label census). TS v1 has **no** spinal cord, nerve or ganglion label,
so TotalSegmentator adds no peripheral coverage at all.

## Clinical tranche

**52 clinical records** written against 11 consulted sources
(TeachMeAnatomy neuroanatomy and plexus/nerve articles, OpenStax
brain-region summaries, spinal-cord lecture notes). Every entered
value is cited per field; everything not sourced is null plus an
explicit `verify` entry. TA names are null and verify-flagged on all
52 records — the consulted sources do not give them; the TA2 pass
owed since Milestone 4 is still owed.

Tiers (nerve records: A = root values, branches and both territories
sourced; B = root values and both territories sourced, branches
flagged; C = root values or a territory flagged. Cranial records:
core = modality/function/exit foramen. Central records: A = function
and connections sourced; B = function only; C = function flagged):

| Group | Records | A | B | C |
|---|---|---|---|---|
| Cranial nerves | 12 | 1 | 11 | 0 |
| Spinal cord and plexuses | 4 | 4 | 0 | 0 |
| Peripheral nerves — upper limb | 5 | 0 | 5 | 0 |
| Peripheral nerves — lower limb | 13 | 4 | 9 | 0 |
| Brain regions | 18 | 4 | 9 | 5 |
| **Total** | **52** | **13** | **34** | **5** |

The five Tier C records are the brain structures whose function no
consulted source stated in this session — insula, limbic lobe,
thalamus, hippocampus, corpus callosum: geometry-linked, function
verify-flagged, nothing entered. The Tier B pattern is disclosed:
for most nerve records it is the `branches` field (the consulted
article gives roots and functions without enumerating named
branches); for most brain records it is `connections`.

Clinical records link **67 of the 133** inventory records as their
geometry; 66 inventory records are inventory-only in v1 (individual
gyri and nuclei beyond the lobe-level records, the geniculate
bodies, brachia, striae, fornix and commissure records, the
ventricular parts). **29 of the 52 clinical records link nothing at
all** — every one of them a structure the release does not contain,
with the absence recorded on the record (checker-gated: an empty
link list is accepted only with a recorded absence).

## Checker results (`tools/nerve_check.py`, exit 0)

All 24 hard checks pass, including: independent recount of every
subtree from the raw tables (62 / 4 / 170 / 5 / 3 / 4 / 91, universe
286 in full agreement); the nerve-named census (55, all inside the
universe); the concept partition (133 claims, no overlaps); geometry
paths exist and v/f counts re-measure exactly (338 entries);
coverage re-derived (133/133); all 126 absence probes re-run over
all six tables with identical hit counts and exact-concept flags;
TS overlap (1/1); citation completeness, null-field flag
completeness and tier recomputation on all 52 clinical records;
geometry-link resolution.

Reported, not gated — **the Milestone 4 C3 continuity**: the muscle
module carries 45 distinct innervation nerve names. After this
module, **11 resolve to a sourced clinical record here** (accessory,
axillary, femoral, inferior gluteal, median, musculocutaneous,
obturator, radial, superior gluteal, tibial, ulnar) and **0 resolve
to a geometry record**. The remaining 34 still cannot be validated
against the release, for the reason quantified next.

## Gap analysis — quantified, recorded, never filled

**The peripheral nervous system is essentially absent from BP3D
4.0.** The release carries exactly **55 nerve-named concepts**
(Milestone 4's C3 figure, now censused as this module's universe):
every one belongs to cranial nerves II, III, IV or the ophthalmic
division of V, their branch classes, or the ciliary ganglion
communications. Of the twelve cranial nerves, four have any concept
at all (II complete; III as two branch lines without a trunk; IV
complete; V as the ophthalmic division only) and **eight have none**
(I, VI, VII, VIII, IX, X, XI, XII — probe-verified over all six
tables, as are the trigeminal ganglion and the maxillary and
mandibular divisions: "trigeminal nerve" scores probe hits only via
the class "branch of trigeminal nerve").

**126 absence probes** were run over all six release tables;
**116 returned zero hits**, and of the 10 with hits only 3 name an
exact concept that exists (mammillary body, corpus callosum,
anterior commissure — all records here). The zero-hit set includes,
in full:

- **Every spinal nerve structure**: spinal nerve, cervical /
  thoracic / lumbar / sacral / coccygeal nerves, dorsal and ventral
  roots, dorsal root ganglion, ramus communicans — and therefore
  **every plexus**: brachial, cervical, lumbar, sacral, lumbosacral
  and the lumbosacral trunk. The module's plexus records are
  sourced text with no geometry, and every limb-nerve record
  inherits that status.
- **Every named limb and trunk nerve**: median, ulnar, radial,
  axillary, musculocutaneous, suprascapular, long thoracic,
  thoracodorsal, phrenic, intercostal, subcostal, iliohypogastric,
  ilioinguinal, genitofemoral, femoral, obturator, sciatic, tibial,
  common fibular/peroneal, both gluteal nerves, pudendal, posterior
  cutaneous, lateral cutaneous, saphenous, sural, superficial and
  deep fibular, digital and plantar nerves (45 named nerves probed,
  all absent; the tibial and common fibular *portions* of the
  sciatic are likewise nameless in the release).
- **The autonomic system beyond one ganglion**: sympathetic trunk,
  sympathetic ganglion (probe hits arise only inside
  "parasympathetic ganglion"), superior cervical, stellate and
  celiac ganglia, splanchnic nerves, and every autonomic plexus
  (cardiac, celiac, hypogastric, myenteric, enteric). The ciliary
  ganglion pair is the release's only autonomic structure.
- **The spinal cord's named anatomy**: segments, cervical and
  lumbosacral enlargements, conus medullaris, cauda equina, filum
  terminale, denticulate ligament — the cord's PART-OF subtree is
  two concepts (cord + central canal), so the sourced cord record
  is text over a single whole-cord composition.
- **The meninges**: pia mater and arachnoid mater occur in neither
  table; "subarachnoid space" and "dura mater" score hits only via
  class concepts (subdivision of subarachnoid space, subarachnoid
  incisure; region of dura mater, subdivision of cranial dura
  mater). The tentorium cerebelli is the only specific meningeal
  structure; falx cerebri, falx cerebelli and diaphragma sellae are
  absent outright.
- **Named central structures**: substantia nigra, red nucleus,
  dentate nucleus, inferior olivary complex, striatum, lentiform
  nucleus, claustrum, external and extreme capsules, cerebral
  peduncle (the release's nearest concept is "peduncle of
  midbrain", a record here), basal ganglia as a named concept (only
  the generic class "basal ganglion of telencephalon" exists; the
  caudate, putamen and globus pallidus are records), cerebellar
  vermis, flocculus, tonsil and fastigial nucleus, septum
  pellucidum, ependyma, interthalamic adhesion, superior medullary
  velum, and the posterior limb of internal capsule as a named part
  (probe hits only; the capsule itself is a lateralised record
  pair). The choroid plexus exists only as the single class
  "choroid plexus of cerebral hemisphere" — no plexus of the third
  or fourth ventricle is named.

## Next steps

1. A nerve-concept source (full FMA or TA-based) is now the single
   largest blocker in the whole Body Model: it unblocks peripheral
   geometry, checker validation of the muscle module's innervation
   names (34 still unresolvable), and any Theatre procedure that
   names a nerve at risk. Same class of decision as Milestones 4
   and 5 recorded for absent muscles and vessels; no hand-modelled
   substitutes.
2. TA2 pass to fill `ta_name` across the tranche (owed jointly
   with Milestones 4 and 5).
3. Tier C → sourced: insula, limbic system, thalamus, hippocampus
   and corpus callosum functions from a consulted neuroanatomy
   source; Tier B → A branch enumerations for the five upper-limb
   nerves from their individual articles.
4. Cranial-nerve nuclei and the cord's internal structure (grey
   matter columns, named tracts) belong to the same future source
   decision as (1); among the release's 14 tract-named concepts
   the optic tract is the only neural tract (the rest are
   gastrointestinal, respiratory and urinary tracts and the
   iliotibial tract).
