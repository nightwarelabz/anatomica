# ANATOMICA — Milestone 4: Muscular System Module v1

Date: 2026-11-06. Status: **built and checked locally; not uploaded.**
Method: Milestone 2's discipline applied to muscle — census from the
BodyParts3D 4.0 / FMA release tables (never from memory), exact lookups
only, geometry counted by streaming the OBJ files, clinical fields only
from sources consulted during the build, everything else verify-flagged,
and an independent checker that re-derives every claim from the raw
tables and files.

## Deliverables

| File | Content |
|---|---|
| `data/muscular/muscle-inventory.json` | 359 muscle records censused from the tables, with the counting convention stated in its meta |
| `data/muscular/muscle-geometry.json` | per-record BP3D mesh compositions with measured vertex/face counts |
| `data/muscular/muscles.json` | 127 clinical records (origin / insertion / actions / innervation / arterial supply), per-field source citations |
| `tools/muscle_map.py` | inventory + geometry builder |
| `tools/build_muscle_records.py` | clinical tranche builder (all values transcribed from consulted sources) |
| `tools/muscle_check.py` | independent checker (shares no code with the builders) |

## 1. Inventory — 359 records from 690 concepts

The muscle concepts of BP3D 4.0 live in four disjoint subtrees of the
IS-A inclusion tree (re-censused independently by the checker):

| Subtree | Concepts |
|---|---|
| Muscle organ (FMA5022) | 535 |
| Zone of muscle organ (FMA10474) | 63 |
| Head of muscle organ (FMA85453) | 68 |
| Musculature set tree | 24 |
| **Total concept universe** | **690** |

Counting convention (as stated in the inventory meta): one record per
lateralised instance where the tables lateralise; one record for an
un-sided class the tables model jointly; one record per side for a
parts-composite muscle (a muscle with no whole-muscle concept in the
tables, represented only by lateralised head/part concepts — heads and
parts are geometry components, never records); numbered instances
(lumbricals, interossei) count individually per side and number as FMA
names them; where FMA models a muscle only as a set, the set is one
record per side where lateralised, else one un-sided record. Groups,
families, zones and part concepts are not records.

| Representation | Records |
|---|---|
| Whole-concept (per side) | 308 |
| Parts-composite (per side) | 27 |
| Set-concept | 14 |
| Whole-concept, un-sided | 10 |
| **Total** | **359** |

## 2. Geometry — coverage 359/359

Every inventory record resolves to BP3D meshes. Checker-measured
(streaming recount of every file on disk):

- **417 distinct IS-A mesh files — 1,704,260 vertices / 2,365,492 faces**
- plus 54 PART-OF files; 471 distinct paths in total —
  2,053,557 vertices / 2,954,408 faces
- The IS-A partition is exact: no mesh file appears in more than one
  record, and the summed-over-records totals equal the distinct-file
  totals.
- Zone compositions were verified at build time to be subsets of the
  union of the sides' part files, so zones are recorded as provenance
  (`zone_concept_ids`) and excluded from per-side geometry (including
  them double-counted the opposite side's files).

## 3. Clinical tranche — 127 records, field-sourced or flagged

Field-sourcing rule (precision law): every non-null value was entered
only from a source consulted in the build session — 29 sources in the
bibliography (TeachMeAnatomy region articles, StatPearls, Geeky Medics,
lecture tables, Wikipedia muscle tables, among others) — and is cited
per field in each record's `sources` map. A field with no consulted
source is null and carries an explicit entry in the record's `verify`
list. Terminologia Anatomica names appear in none of the consulted
sources and are not carried by the tables, so `ta_name` is null and
verify-flagged on all 127 records.

Sourcing tiers — A: every clinical field sourced; B: sourced except
arterial supply and/or innervation root values; C: at least one core
field (origin, insertion, actions, innervation) verify-flagged:

| Region | Records | A | B | C |
|---|---|---|---|---|
| Back | 31 | 0 | 22 | 9 |
| Upper limb | 44 | 21 | 22 | 1 |
| Lower limb | 38 | 25 | 13 | 0 |
| Neck | 8 | 4 | 4 | 0 |
| Thorax | 5 | 1 | 2 | 2 |
| Abdomen | 1 | 0 | 0 | 1 |
| **Total** | **127** | **51** | **63** | **13** |

Linkage: the 127 clinical records link **241 of the 359** inventory
records (per-side instances collapse into class-level clinical
records). The remaining **118 inventory records are inventory-only**
in this tranche — by BP3D region group: neck 41, lower limb 30
(foot intrinsics and remaining leg classes), head 23, no regional
group 15, vertebral column 6, pelvis 2, perineal 1.

One clinical record has **no geometry**: multifidus (see gaps).

## 4. Independent checker — all hard checks pass

`tools/muscle_check.py` (run 2026-11-06, exit 0):

- T1: concept universe re-censused from the raw inclusion table —
  690, subtrees 535 / 63 / 68 / 24, disjoint — matches the inventory.
- T2: every concept id referenced by the inventory exists in the
  release tables and inside the universe; the 391 instance concepts
  claimed by the 359 records form an exact partition (no overlaps).
- G1/G2: all 471 mesh paths exist; every file's vertex/face counts
  re-measure exactly as recorded; coverage meta consistent (359/359).
- C1/C2: all 127 clinical records — every non-null field carries a
  citation that resolves to the bibliography; every null field
  carries a verify flag; every geometry link references a real
  inventory record.
- X1/X2: no duplicate record ids in any file; geometry ids ==
  inventory ids.

C3 (reported, not gated): innervation names cannot be cross-validated
against the tables in this release — the BP3D 4.0 tables carry only
**55 nerve-named concepts** (mostly cranial nerves and nerve trunks);
the peripheral nerves named in the clinical records (femoral, median,
ulnar, tibial, …) are not concepts in the release at all. 0 of 120
innervation phrases resolve; 49 distinct phrases are listed by the
checker. A nerve-concept source is needed before this validation can
run (see next steps).

## 5. Flagged gaps — recorded, never filled

1. **Absent from the tables entirely** (stem search, 0 hits across all
   six release tables; no concept, no record): latissimus dorsi,
   masseter, temporalis, rectus abdominis, multifidus, frontalis,
   occipitofrontalis, orbicularis oculi, orbicularis oris, buccinator,
   zygomaticus major, zygomaticus minor, iliopsoas, transversus
   abdominis, internal oblique, pyramidalis, cremaster, arrector,
   detrusor, levator labii, depressor anguli oris, nasalis, procerus,
   risorius, palatoglossus, tensor tympani, stapedius; also quadratus
   lumborum and psoas minor.
2. **Multifidus** is the sharpest case: clinically sourced (record
   present, Tier B) but with no BP3D concept and therefore no
   geometry — the record's geometry is null and verify-flagged.
3. **Longus colli asymmetry:** BP3D lateralises this muscle on the
   left only; the un-sided part classes' compositions are just the
   left files. The record `left longus colli` carries the asymmetry
   note; no right record exists.
4. **Set-only modelling:** hand dorsal/palmar interossei and hand
   lumbricals exist only as sets; foot dorsal interossei exist only
   as part concepts (no records under the convention), while foot
   plantar interossei and lumbricals do have records. Levatores
   costarum and the cervical/lumbar interspinales likewise exist
   only as sets.
5. **Jointly modelled classes:** the three intercostal classes and
   the thoracic rotator are single un-sided FMA concepts spanning
   both sides (the intercostal geometry is an FJ/FJM mirrored file
   pair per class).
6. **Composite groups are not records:** levator ani and quadriceps
   femoris have no records of their own; their components
   (pubococcygeus, iliococcygeus, puborectalis; rectus femoris and
   the three vasti) are the records.
7. **Source conflicts found and handled in the records:**
   StatPearls' shoulder article gives levator scapulae the
   thoracodorsal nerve and latissimus actions (an apparent copy error
   — TeachMeAnatomy values used); gives flexor carpi ulnaris a median
   nerve (ulnar nerve used, root values flagged); gives teres minor
   the teres major origin (TeachMeAnatomy origin used); gives
   extensor pollicis brevis a distal-phalanx insertion (field
   verify-flagged, not entered — the tranche's one upper-limb Tier C
   record). Root values for flexor digitorum longus and flexor
   hallucis longus conflict between two consulted sources (S1,S2 vs
   S2,S3) and are verify-flagged on both records.
8. **Tier C records (13)** are partial by design: the minor deep back
   sets (interspinales / intertransversarii / levatores costarum —
   innervation not stated in the consulted article), innermost
   intercostal, transversus thoracis, external oblique (attachments
   only in the consulted extract), and extensor pollicis brevis.

## 6. Next steps

1. Head/neck clinical tranche (41 neck + 23 head inventory records
   awaiting records: infrahyoid/suprahyoid groups, tongue, pharynx,
   larynx, palate, extraocular muscles).
2. Foot-intrinsic and remaining lower-limb tranche; pelvis/perineal
   records; the 15 records with no BP3D regional group.
3. A TA2 (Terminologia Anatomica 2) pass to fill `ta_name` from a
   citable source and clear the tranche-wide flag.
4. A nerve-concept source (full FMA or TA) so checker C3 can
   validate innervation names instead of only reporting them.
5. Geometry decision for the absent muscles (multifidus first):
   TotalSegmentator-derived meshes or a later BP3D release, under
   the same provenance rules — no hand-modelled substitutes.
6. Tier B → A upgrades: per-muscle arterial-supply sourcing for the
   back (22 records) and the remaining root-value gaps.

*Local build only. Nothing in this milestone has been uploaded; the
batch is presented for approval as a unit.*
