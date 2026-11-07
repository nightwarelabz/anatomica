# Milestone 36 — FMA concept intake #2: lymphatic system + endocrine glands

**Date:** 2026-11-06
**Scope:** the second FMA 5.1.0 concept intake, on the Milestone 33
pattern, for the two most-absent systems in the Body Model. Local
only; nothing uploaded.
**Tools:** `tools/fma_lymph_endo_map.py` (builder),
`tools/fma_lymph_endo_check.py` (independent checker),
`tools/ta2_match_fma36.py` → `tools/ta2_decide_fma36.py` →
`tools/ta2_pass_fma36.py` (TA2 sibling pipeline).
**Accounting:** `data/fma-intake-36.json`.

---

## 1. Result

| Census | Before | After | Delta |
|---|---|---|---|
| Lymphatic inventory records | 4 | **135** | +131 FMA concept records (93 targets: 76 sided / 55 un-sided records) |
| Endocrine inventory records | 3 | **17** | +14 FMA concept records (10 targets: 8 sided / 6 un-sided records) |
| Body Model inventory records | 1,838 | **1,983** | +145 |
| Records with geometry | 1,545 | 1,545 | unchanged — every new record is geometry-absent |
| Clinical records | 361 | 361 | unchanged (no clinical tranche authored) |
| Shell listed records (`records.json`) | 1,916 | 2,061 | +145, all `has_geometry: false` |
| Geometry packs (23 files incl. `delivery.json`) | — | — | **byte-identical, hash-asserted** |

One target was excluded by the mechanical rule (the pineal, §3).
No target failed to resolve. Every new record carries its FMAID,
the verbatim FMA preferred name, its IS-A path to *Anatomical
entity*, source `fma-5.1.0`, `geometry: "absent"`, and the two
Milestone 36 verify flags (geometry absent — ontology source; no
clinical tranche). The license position is Milestone 33's: the
FMA 5.1.0 package's own LICENSE file is CC BY 4.0, hash-pinned in
`data/sources/fma-5.1.0/`; the independent checker re-hashes it
(L1/L2).

## 2. The absence census (what lacked records)

From Milestone 13's inventories and 52-probe gap analyses, as they
stood post-M33/M35:

**Lymphatic — 4 records (spleen, thymus, two thymus lobes).**
Absent entire: the conducting system (lymphatic vessels and
capillaries, the thoracic duct, the right lymphatic duct, the
cisterna chyli, all five lymphatic trunks); every named lymph node
group in every region (the string "lymph" occurs in **no**
BodyParts3D concept name — there is no lymphatic root in the
release at all); the tonsils and MALT; bone marrow (Milestone
13's gap analysis records it as this module's absence); the
interiors of the two carried organs (splenic pulp and its
divisions, the splenic trabecula, the thymic lobule/cortex/
medulla).

**Endocrine — 3 records (pituitary, two adrenals).** Absent
entire: the thyroid gland and its gross parts; the parathyroid
glands; the endocrine pancreas as a concept (the clinical
tranche's `gland.pancreatic-islets` was text-only); the
paraganglia and carotid body. The pineal is **not** absent — it
is the nervous module's record (`brain.pineal-body`, FMA62033),
and the endocrine clinical record points at it. The pancreas
organ is the digestive module's record (FMA7198) and was not
targeted; only the islet concept crosses into this inventory,
mirroring Milestone 13's clinical boundary.

## 3. Verdicts per target

**Lymphatic — 93 targets, all resolved (131 records).** Conducting
(11 targets): lymphatic vessel, lymphatic capillary, thoracic
duct, right lymphatic duct (the FMA's class is intrinsically the
right-sided duct — no left counterpart and no un-sided class
exists; recorded as released, its name carrying the side, with
the fact on the record), cisterna chyli, and the jugular,
subclavian, bronchomediastinal, lumbar and intestinal trunks
(sided pairs). Node groups (66 targets): head and neck 16,
axillary/upper limb 9, thoracic 14, abdominal 16, pelvic/lower
limb 11 — occipital through popliteal, per the frozen list in
the builder. Group-form classes recorded as released, with the
fact on the record: pectoral axillary, anterior mediastinal and
lumbar (the FMA names these aggregates only as group classes);
the axillary aggregate keys on the un-sided class (its sided
forms exist only as group classes — noted on the record); the
subscapular record is the FMA's class for the posterior axillary
group (noted). Tonsils and MALT (6): the tonsil generic, palatine
(sided), pharyngeal, lingual (sided), tubal (sided), and the
aggregated lymphoid follicle of small intestine — the FMA's
class for Peyer's patches (its regional ileal class FMA72027 is
not separately recorded; the correspondence is on the record).
Marrow (3): bone marrow, red, yellow. Interiors (7): splenic
pulp, red pulp, white pulp, trabecula of spleen; lobule, cortex
and medulla of thymus.

**Endocrine — 11 targets: 10 resolved (14 records), 1 excluded.**
Thyroid (4): the gland (FMA9603), its lobes (sided), isthmus,
pyramidal lobe. Parathyroids (3): the generic gland, superior
(sided), inferior (sided). Islets (1): pancreatic islet
(FMA16016), boundary note on the record. Paraganglia (2): the
generic paraganglion, the carotid body (sided).
**Excluded (1): Pineal body — FMA62033 is already inventoried as
the nervous module's `brain.pineal-body`.** The target was frozen
into the list deliberately so the exclusion fired mechanically;
the checker re-verifies the ownership (B2).

**Not in the FMA under the probed names** (absence probes in the
accounting artifact, all zero-hit under a full XML parse of the
OWL, 103,687 preferred names): superficial cervical lymph node,
deep cervical lymph node (as such), pancreaticosplenic lymph
node (the FMA splits the territory into the pancreatic and
splenic classes — both recorded), splenic hilum, thymic
corpuscle, intestinal trunk, lymphatic trunk (as a class name),
Peyer patch / aggregated lymphoid nodule (as names), endocrine
pancreas (no class; the islet class is the content), islet of
Langerhans (as a preferred name — it is the islet class's
synonym), aortic body, glomus jugulare, jugulotympanic
paraganglion, parafollicular cell, pineal gland (as a preferred
name — the class is *Pineal body*).

**Deferred, existing in the FMA, with reasons** (accounting
artifact): the endocrine interiors of already-recorded organs —
adenohypophysis (FMA74627), neurohypophysis (FMA74628), adrenal
cortex (FMA15632), medulla (FMA15633) and the three zonae
(FMA69225/69234/69236) — a named follow-on class, not part of a
whole-gland absence intake; the thyroid follicle (FMA68805,
histological unit, below record granularity); accessory thyroid
(FMA55533) and parathyroid (FMA55567) glands (variants, not
census records); per-level intercostal node classes and segmental
bronchopulmonary classes (below the frozen list's granularity —
the generic classes are recorded); 'Set of …' aggregates (not
records, by the standing convention).

## 4. The TA2 pass — the pipeline extends; no new matcher machinery

The Milestone 35 sibling pipeline extended cleanly:
`ta2_match_fma36.py` is the M35 matcher parameterized by system
(identical candidate machinery; the class-word vocabularies gain
the new systems' class nouns — trunk, tonsil, nodus/nodi, lobe,
isthmus, follicle, insula, paraganglion), `ta2_decide_fma36.py`
runs rules M1–M3 unchanged plus a stated M4 (a record the matcher
left with no candidate is not found; its probes are its own
names, re-asserted absent from the whole apparatus), and
`ta2_pass_fma36.py` applies. `ta2_discipline.py` gained
`run_fma_inventory_multi` — F1–F5 parameterized, no new assertion
machinery — wired into both tranche checkers. The clinical
sections of `data/ta2-name-pass.json` and the M35 `fma_inventory`
section are parsed-identical after the pass (asserted); the new
sections are `fma_inventory_lymphatic` / `fma_inventory_endocrine`,
the extension recorded under meta key `extension_36`.

| TA2 census | Resolved | Ambiguous | Not found |
|---|---|---|---|
| Lymphatic (131) | **117** (73 collective-term, 39 preferred, 2 latin-term, 2 latin-synonym, 1 class-word-form) | 8 | 6 |
| Endocrine (14) | **13** (11 preferred, 2 collective-term) | 1 | 0 |

The TA2 discipline now spans all 431 FMA-sourced records of the
Body Model (with Milestone 35's nervous 194/92/0): **324 resolved,
101 ambiguous, 6 not found**.

The dominant lymphatic pattern: TA2 names node groups as regional
plural collective terms (*nodi occipitales*, *nodi axillares*, …)
where the FMA carries a class per group — 47 class-level
collective-term resolutions where the regional name corresponds
exactly, plus TA2's own sided terms where it has them (gastric
5283/5284, colic 5310/5314, lumbar 5270/5275, entered per record).
Ambiguous, with dated reasons (TA2 divides what the FMA holds
whole, or the FMA's class spans two TA2 terms): parotid
[5201, 5202], deep lateral cervical [5225, 5229], paratracheal
[5222 cervical, 5260 thoracic], diaphragmatic [5253, 5279],
mesenteric [5302, 5312], sacral [5324, 5338], the aggregated
lymphoid follicle [2960 ileal, 2978 appendiceal — the FMA class
is broader than either], and the parathyroid gland [3871, 3872].
Not found, with probes: the tonsil generic (TA2 names no generic
tonsil), the anterior mediastinal group and posterior mediastinal
nodes (TA2 folds the territory into brachiocephalic/pericardial
and juxta-oesophageal/prevertebral terms), the superior
mediastinal nodes (inside the mediastinal heading the mediastinal
record takes), the common hepatic nodes (inside the undivided
hepatic term). Tonsils are named twice by TA2 (digestive and
lymphoid chapters, identical Latin); the lymphoid-chapter terms
are entered, with the reason on each decision. Two FMA classes —
superior diaphragmatic and superior phrenic — take the one TA2
term 5253 between them.

## 5. Two defects the build caught in its own tooling

1. **The naive OWL block parser truncates classes at nested
   restriction axioms.** FMA9603 (thyroid gland) carries its
   `fma:preferred_name` after ~55 restriction axioms; a streaming
   block parse that ends a class at the first nested
   `</owl:Class>` reads the class as label-only, and the first
   build recorded it on that basis. The independent checker —
   parsing with ElementTree — failed the record, and the XML
   ground truth showed the name present. The builder's parser now
   counts nesting depth (net of self-closing class references)
   and agrees with the XML parse on preferred names (103,687
   classes carry one). Total effect on the built data: three
   field corrections (the thyroid's class pointer and note, the
   right lymphatic duct's note); all 145 records' names, FMAIDs
   and IS-A paths were already correct, re-verified pair-by-pair
   against the XML parse. Every not-in-FMA verdict was re-probed
   against the full XML parse and stands. **Consequence beyond
   this milestone:** any earlier reading of the OWL made with the
   naive parser — including Milestone 35's note that six plexus
   classes carry a label but no preferred name — should be
   re-checked under a depth-aware parse before it is relied on;
   the M33/M35 records themselves are unaffected (their checker
   parses with ElementTree and gates name equality).
2. **The first builder was not idempotent.** Its exclusion sweep
   read every inventory including its own previous output, so a
   second run excluded every target against itself and collapsed
   the two inventories to their BP3D partitions. The independent
   checker failed that run (census arithmetic), the sweep now
   skips the records of the two inventories being rebuilt, and
   idempotency is proven: two consecutive full runs produce
   identical censuses and a green checker.
3. The new checker's G2 was first written as exact equality of
   the verify list — true before the TA2 pass, false after it
   (the pass appends its dated `ta_name` flag to unresolved
   records). G2 now gates the invariant in its correct form: the
   two Milestone 36 flags first, any later entry a `ta_name`
   flag (whose format the TA2 discipline gates separately). The
   checker passes on the final, post-pass state.

## 6. Non-regression

- BP3D partitions of both inventories and both geometry files:
  **identical in parsed form** to the pre-build snapshots
  (asserted record-by-record); the `concepts` arrays untouched.
- Geometry packs: all 23 files (11 packs, their `.gz` forms and
  `delivery.json`) **byte-identical** by SHA-256 to the pre-build
  hashes; pack totals unchanged (304,367,896 B canonical →
  123,352,401 B compressed).
- The TA2 pass changed FMA records only in `ta_name` / `ta_code` /
  `sources` / the one dated verify flag (asserted field-by-field
  against pre-pass snapshots); BP3D records in both files
  byte-identical in parsed form.
- Assembled geometry records identical; the assembled metas now
  list the 131 + 14 geometry-absent records. Assembly anchors
  updated: lymphatic (135, 4, 4), endocrine (17, 3, 6).
- `records.json`: all 1,916 pre-existing entries parsed-identical;
  +145 entries, all `has_geometry: false`.

## 7. Gate matrix

| Gate | Result |
|---|---|
| `fma_lymph_endo_check.py` (new, independent) | **ALL CHECKS PASS** — L1/L2 license pins; F1/F2/F3 fidelity of all 145 records vs an XML re-parse of the OWL (group_paths reach *Anatomical entity* 145/145); B1 zero FMAID overlap anywhere in the Body Model; B2 pineal exclusion verified; G1/G2 geometry correspondence and flags; C1 census arithmetic; A1 accounting reconciliation |
| `lymph_check.py` | **47/47** (BP3D re-derivation partition-scoped; incl. the five M36 TA2 discipline assertions) |
| `endo_check.py` | **52/52** (incl. M12 boundary closure and the five M36 TA2 discipline assertions) |
| All other tranche checkers | skeletal FAILURES: 0 · muscle ALL HARD CHECKS PASS · cv PASS · nerve ALL HARD CHECKS PASS · fma_nerve ALL CHECKS PASS · resp ALL HARD CHECKS PASSED · dig ALL HARD CHECKS PASSED · uri ALL HARD CHECKS PASS · repro 63 PASS / 0 FAIL · integ 44/44 |
| `assembly_check_all.py` | **ALL GATED CHECKS PASS** (A1 anchors: lymphatic 135 inventory / 4 assembled; endocrine 17 / 3) |
| `verify_web.js` | **ALL CHECKS PASS** (W1–W10; W6 slot census unchanged at 1,545; W9 byte-identity of the compressed packs re-proven) |
| `theatre_check.py` | **245 checks, 0 failures** |
| `case_check.py` | **5,145 passed, 0 failed** (cases #1–#3 byte-identical) |
| Physiology `validate` | **VALIDATION: ALL HARD GATES PASS** (exit 0; the disclosed soft lines are unchanged in kind) |
| Native `verify` | **99 data assertions PASS / 0 FAIL**; the GPU render stage cannot initialise on this VM (no wgpu adapter) and exits 2 — the standing disclosed limitation of every recent milestone; no data assertion is affected |

## 8. Honest limits

- **FMA granularity, lymph nodes:** the FMA carries ~1,088
  lymph-node classes — per-level, per-segment and set classes
  below any regional census. The frozen list is the standard
  regional census (93 lymphatic targets), not the FMA's node
  space exhausted; the deferred classes are named in the
  accounting artifact, not silently dropped.
- **TA2's lymph model differs from the FMA's:** TA2 names most
  groups only as regional collectives and a few named singles;
  73 of 117 lymphatic resolutions are collective-term
  correspondences, and 14 records stay ambiguous or not found for
  structural reasons stated per record. No correspondence was
  forced.
- **Geometry is still absent for everything intaken here** — the
  FMA carries none, and no other source has cleared the license
  and registration bars (the Milestone 34 audit governs
  Z-Anatomy). These are concept records: they complete the
  model's *inventory*, not its atlas.
- **No clinical tranche** was authored for the new records; the
  four lymphatic and six endocrine clinical records are unchanged,
  and the new records carry the standing no-clinical-tranche flag.
- The label-pin mechanism designed early in this build was
  **retired unused** — its premise (a label-only thyroid class)
  was a parser artifact (§5.1).

## 9. Next steps

- The remaining FMA concept intakes, same pattern: **urinary
  interior** (kidney interior, ureter/bladder parts) and the
  **female reproductive tract** — the last two dataset blockers
  with a named source — then skin layers if a source clears.
- The six existing-but-unintaken nerve classes named at
  Milestone 35 §5.1, and the anterior interosseous name question,
  remain open (the latter needs a curation ruling).
- Endocrine interiors (pituitary divisions, adrenal cortex/
  medulla/zonae) as a named follow-on intake class.
- Re-verify Milestone 35's six "label-only" plexus classes under
  the depth-aware OWL parse (§5.1) and correct the record if the
  names are present.
