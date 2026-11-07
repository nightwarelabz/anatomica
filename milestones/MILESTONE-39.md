# Milestone 39 — A sourced clinical tranche for the major nerves

**State: built and verified locally. Not uploaded; no repository
writes. Awaiting a per-item approval tap, like every milestone.**

The Milestone 33 dossier (§5.2) named this tranche: the FMA 5.1.0
intake gave the Body Model inventory records for the major nerves
(286 concept records, geometry-absent), and "a sourced clinical
tranche for the major nerves (the records exist to be linked)" was
left as the follow-on. Milestone 39 authors that tranche:
**40 clinical records of type `major_nerve`** in a new additive
file, `data/nervous/major-nerves.json`, each linking the inventory
records it describes.

## 1. The frozen target set

The set was fixed from the inventory records that exist
(Milestones 9 and 33) before authoring, and is gated verbatim by
the checker (§5):

| Group | Records | Count |
|---|---|---|
| Cranial nerves | olfactory (I), optic (II), oculomotor (III), trochlear (IV), trigeminal (V), abducens (VI), facial (VII), vestibulocochlear (VIII), glossopharyngeal (IX), vagus (X), accessory (XI), hypoglossal (XII) | 12 |
| Brachial plexus — trunks and cords | superior trunk, middle trunk, inferior trunk, lateral cord, posterior cord, medial cord | 6 |
| Peripheral nerves — upper limb | suprascapular, long thoracic, musculocutaneous, axillary, radial, median, ulnar, medial cutaneous nerve of arm, medial cutaneous nerve of forearm | 9 |
| Peripheral nerves — lower limb | femoral, obturator, lateral femoral cutaneous, saphenous, superior gluteal, inferior gluteal, sciatic, tibial, common fibular, superficial fibular, deep fibular, sural, pudendal | 13 |
| **Total** | | **40** |

Deliberate exclusions, stated rather than silent: the lateral
cutaneous nerve of the forearm has no inventory record of its own
(it is the continuation of the musculocutaneous nerve) and is
covered inside the musculocutaneous record's fields; the plexus
roots and divisions are not separate inventory records and were
not made records; smaller named nerves that the Milestone 35
innervation pass links (intercostal, phrenic, pectoral, subscapular
nerves, nerve to piriformis, nerve to quadratus femoris) are
outside the frozen set and remain candidates for a later tranche.

## 2. Record shape and field discipline

Each record carries the five content fields of the tranche —
`root_values` (origin / segmental values; for cranial nerves, the
brainstem or cerebral origin as the source states it), `course`,
`motor_distribution`, `sensory_distribution`, and
`clinical_testing` (bedside testing and lesion signs) — plus the
house apparatus: per-field `sources`, a `verify` list, a `note`,
`geometry_record_ids` linking the inventory, and TA2 fields (§4).

Field discipline for type `major_nerve`, declared in the builder
and re-derived independently by the checker:

- **Core fields:** `root_values`, `motor_distribution`,
  `sensory_distribution`.
- **Soft fields:** `course`, `clinical_testing`.
- **Tier A** — all five fields sourced. **Tier B** — the three
  core fields sourced, one or both soft fields null + flagged.
  **Tier C** — any core field null + flagged.

Two conventions, stated openly. (1) For purely sensory nerves,
`motor_distribution` is a sourced "none" statement where the
consulted source states it (e.g. the lumbar-plexus article's
"Motor Functions: None" for the lateral cutaneous nerve of thigh;
the UAMS tables' "no cutaneous branches" analogues for sensory
fields); a sourced none is a value, not a null. (2) For the
trunks and cords, which distribute rather than terminate, the
motor and sensory fields are distribution statements grounded in
the plexus article's formation and branch account and in the
linked terminal nerves' own consulted articles — where the plexus
article states a lesion pattern (Erb's, Klumpke's), that pattern
is the distribution evidence and is phrased as such.

## 3. Sources consulted — and what each actually grounded

Every non-null field cites, in the record's own sources map, a
source that was opened and read during this build session. The
register (also in the file's meta):

- **TeachMeAnatomy** (teachmeanatomy.info) — the per-structure
  articles: *Summary of the Cranial Nerves* (origins, exits,
  modalities, and the per-nerve function breakdown for all twelve
  cranial records), *The Brachial Plexus* (formation, trunks,
  divisions, cords, branches, Erb's and Klumpke's patterns),
  *The Lumbar Plexus*, *The Sacral Plexus*, and the dedicated
  articles for the median, musculocutaneous, axillary, radial,
  ulnar, femoral, obturator, sciatic, tibial, common fibular and
  pudendal nerves (roots, course, motor and sensory distributions,
  and the lesion patterns quoted in the records).
- **University of Arkansas for Medical Sciences, Department of
  Neuroscience — nerve tables** (medicine.uams.edu): the upper-limb
  table grounded the suprascapular and long thoracic records
  (including scapular winging as the long thoracic lesion sign),
  both medial cutaneous nerves, and the accessory nerve's dual
  root; the lower-limb table grounded the gluteal rows, the
  fibular divisions, and the sural nerve's formation and territory.
- **OpenStax, Anatomy and Physiology 2e, §14.7 "The Cranial Nerve
  Exam"** (read via the Oregon State University OpenStax mirror):
  the bedside-testing content of all twelve cranial records —
  smell testing and anosmia, Snellen acuity, visual-field testing,
  the pupillary light reflex and its localisation patterns,
  pen-tracking gaze tests and diplopia, sharp/dull discrimination
  for the trigeminal nerve, taste testing, the Rinne and Weber
  tuning-fork tests, the gag reflex and its afferent/efferent
  split, the "lah-kah-pah" palate test, the shoulder-shrug test,
  and tongue protrusion with deviation toward the lesion.
- **TA2** — only as carried by the linked records (§4); no TA
  value was looked up independently for this tranche.

Consultation limits, honestly: StatPearls via NCBI Bookshelf —
the standard clinical companion for several of these nerves —
returned a reCAPTCHA check page on every attempt this session,
and the Europe PMC mirror returned HTTP 403. StatPearls is
therefore **not cited for any field**; fields it would typically
ground (notably lesion signs for the suprascapular and gluteal
nerves) stayed null rather than being filled from recall (§7).

## 4. TA discipline

`ta_name` / `ta_code` follow the linked inventory records, and
the checker asserts equality record by record:

- For the 38 records linking FMA records: the Milestone 35 TA2
  outcome already carried by those records (both sided records of
  a pair share the code, and the checker asserts they agree).
- For the two records linking BodyParts3D records — **optic** and
  **trochlear**, the two cranial nerves with no FMA inventory
  records (BodyParts3D already owns the class) — the Milestone 23
  TA2 outcome carried by the Milestone 9 clinical records
  `nerve.cn-02-optic` (6183, nervus opticus) and
  `nerve.cn-04-trochlear` (6191, nervus trochlearis).
- One disclosed wrinkle: the accessory record carries **6356,
  nervus accessorius spinalis**, the Milestone 35 outcome of its
  linked FMA *spinal accessory* records; the Milestone 9
  whole-nerve record carries 6352, nervus accessorius. Both are
  TA2 entries; the tranche follows its links, and the record's
  note says so.

## 5. The checker

`tools/major_nerve_check.py` gates the tranche independently of
the builder (the frozen set, field discipline and tier rule are
re-declared in it):

- **N1** exactly the frozen 40 records, ids unique, type
  `major_nerve`;
- **N2** citation discipline — every non-null field cited from the
  file's register, every null field verify-flagged, no other
  sources-map keys;
- **N3** tier re-derivation — shipped tiers equal re-derived
  tiers;
- **N4** link integrity — every `geometry_record_ids` entry
  resolves to the nervous inventory: **72 links over 72 distinct
  inventory records**;
- **N5** TA equality against the linked records (§4);
- **N6** both-ways innervation consistency — for every resolved
  component of the Milestone 35 innervation-link pass, if any of
  its inventory records is linked by a tranche record, all of them
  are linked by that same record: **17 tranche records are
  corroborated by the muscle module's innervation links** naming
  the identical inventory records (the accessory nerve under both
  of its pass names);
- **N7** census — nervous clinical records 52 + 40 = **92**;
  all-system clinical tranche **361 → 401**.

The existing `tools/nerve_check.py` is untouched and still gates
the Milestone 9 file alone.

## 6. Tier census and per-nerve outcome

**Milestone 39 tranche: A 30, B 9, C 1.** Clinical tranche
overall: **361 → 401 records** (nervous 52 → 92).

- **Tier A (30):** all twelve cranial nerves; superior trunk and
  inferior trunk; long thoracic, musculocutaneous, axillary,
  radial, median, ulnar; femoral, obturator, lateral femoral
  cutaneous, saphenous, sciatic, tibial, common fibular,
  superficial fibular, deep fibular, pudendal.
- **Tier B (9)** — core complete, `clinical_testing` null because
  no consulted source states a test or lesion pattern specific to
  the structure: lateral cord, posterior cord, medial cord,
  suprascapular, medial cutaneous nerve of arm, medial cutaneous
  nerve of forearm, superior gluteal, inferior gluteal, sural.
- **Tier C (1):** middle trunk — `sensory_distribution` and
  `clinical_testing` both null (no consulted source states a
  sensory distribution or lesion pattern specific to the C7
  trunk); its root values, course and motor distribution are
  sourced.

## 7. Honest limits

- The nine null `clinical_testing` fields and the middle trunk's
  two null fields are the tranche's open edge: they are null
  because the sources that could be consulted this session do not
  state the values — most conspicuously the Trendelenburg test
  for the superior gluteal nerve, which appears in **no**
  consulted source and was not entered from recall. A future pass
  with a consultable clinical source (StatPearls-class, if it
  becomes reachable) can close most of them.
- The pudendal record's `clinical_testing` is the pudendal nerve
  block — a clinical procedure, the clinical content its
  consulted article states — not a lesion pattern; the value is
  phrased as a procedure so it cannot be misread as one.
- Cranial-nerve `course` values are origin-plus-exit compositions
  from the consulted summary for the nerves whose fuller course
  narratives were not separately consulted; they state nothing
  beyond origin, exit and (where the exam text states it) central
  course.
- The records link geometry-absent FMA concept records (38 of 40)
  and say so in their notes; the tranche adds clinical knowledge,
  not geometry. The geometry question remains the open
  Milestone 34 decision.
- **Pre-existing failure found, not caused:** `tools/repro_check.py`
  exits 1 on one check — a geometry re-measurement mismatch
  ("isa fj set") for `repro.left-deferent-duct` /
  `repro.right-deferent-duct`. Every input that checker reads is
  byte-identical to its pre-Milestone-39 state (§8), so the
  failure predates this milestone; it is recorded here rather
  than silently passed over, and repairing it is outside this
  tranche's scope.

## 8. Integration and non-regression

The web and derived files were extended to carry a second
nervous clinical file, in the smallest way that keeps every
existing behaviour:

- `tools/pack_geometry.py` — a layer's clinical slot may now be a
  tuple of files, merged by `clinical_links()`; the nervous layer
  passes both nervous files; the FMA-inventory listing pass now
  emits each record's real `clinical_ids` instead of a constant
  empty list (previously no clinical record linked an FMA record,
  so the constant was invisible; Milestone 39 is the first
  tranche to link them).
- `tools/verify_web.js` — `SYSTEMS.nervous.clin` is the same pair
  of files, merged by a new `loadClin()` helper at all three
  clinical call sites; the W5 clinical-map expectation is derived
  from the sources and now totals **409 entries** (369 + 40).
- `tools/assembly_check_all.py` — the census anchor for nervous
  moves to (419 inventory, 133 with geometry, **92 clinical**)
  with a Milestone 39 comment, and the A8 count sums both nervous
  clinical files.
- `web/data/records.json` — regenerated by the packer.

Non-regression proof, against a SHA-256 snapshot of 3,579 files
(data, web/data, native, physiology, theatre, cases) taken before
any Milestone 39 edit:

- Exactly **one** snapshotted file changed: `web/data/records.json`.
  All eleven geometry packs, the manifest and `delivery.json` are
  **byte-identical**; every inventory and clinical data file is
  byte-identical (the tranche is a new additive file only).
- The `records.json` diff is exactly the intended one: clinical
  map **+40 `major.*` entries**, no existing entry changed or
  removed; listed records unchanged at **2,314**; meta clinical
  count 369 → 409; exactly **72 listed entries changed**, all
  confined to their `clinical_ids`, and the changed set is
  exactly the 72 inventory records the tranche links.
- The packer is deterministic over the new state: a second full
  run reproduces records.json, all packs, the manifest and
  delivery.json byte-identically (identical aggregate SHA-256).

## 9. Gate matrix

All run against the finished state:

- Tranche checkers: skeletal, muscle, muscle assembly,
  cardiovascular, nerve (M9), FMA nerve (M33), **major nerve
  (M39, N1–N7)**, respiratory, digestive, urinary, lymphatic,
  endocrine, integumentary, FMA lymphatic/endocrine, FMA
  urinary/reproductive, FMA integumentary/male — **all pass**;
  reproductive checker — the one pre-existing failure of §7.
- `assembly_check` and `assembly_check_all` — **all gated checks
  pass**, A8 reporting nervous clinical 92 against the new anchor.
- `verify_web.js` — **all checks pass** (W5 clinical map 409).
- `theatre_check` — **245 checks, 0 failures**.
- `case_check` — **5,145 passed, 0 failed**.
- Native `anatomica verify` — **99/99 data assertions pass**; the
  GPU initialisation stage cannot run on this machine (no wgpu
  adapter), the standing disclosed limitation of every milestone
  verified here.
- Physiology crate tests — **25/25 pass**.

## 10. Files of this milestone

New: `MILESTONE-39.md`, `data/nervous/major-nerves.json`,
`tools/build_major_nerve_records.py`, `tools/major_nerve_check.py`.
Modified: `tools/pack_geometry.py`, `tools/verify_web.js`,
`tools/assembly_check_all.py`, `web/data/records.json`
(regenerated).

## 11. Next steps

- Source the nine null `clinical_testing` fields and the middle
  trunk's sensory field from a consultable clinical reference
  when one is reachable in-session; each closure is a small,
  separately-gated edit.
- A second major-nerve tranche can cover the named nerves left
  outside this frozen set (intercostal, phrenic, pectoral and
  subscapular nerves, and the small plexus branches) on the same
  discipline.
- The tranche's records are ready to surface wherever clinical
  records are presented; their inventory targets remain
  geometry-absent until the geometry question (Milestone 34) is
  decided.
