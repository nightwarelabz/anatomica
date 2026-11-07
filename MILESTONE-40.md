# Milestone 40 — The deferent-duct checker failure: diagnosis and repair

**State: built and verified locally. Not uploaded; no repository
writes. Awaiting a per-item approval tap, like every milestone.**

Milestone 39 (§7) disclosed a pre-existing failure it did not
cause: `tools/repro_check.py` exited 1 on one check — a
geometry re-measurement mismatch ("isa fj set") for
`repro.left-deferent-duct` / `repro.right-deferent-duct`, on
inputs byte-identical to their pre-Milestone-39 state.
Milestone 40 reproduces it, bisects it, decides which side is
wrong against the source tables, repairs that side, and lands
a regression gate that converts this class of drift from a
silent assumption into a named, pinned assertion.

## 1. The failure, reproduced

On the untouched tree, `python3 tools/repro_check.py` reported
**67/68 checks passed**, exit 1, the single failure:

```
FAIL all geometry entries re-measured (20 entries)
  — bad=[('repro.left-deferent-duct', 'isa fj set'),
         ('repro.right-deferent-duct', 'isa fj set')]
```

The checker's geometry section derives, for every record in
`data/reproductive/reproductive-geometry.json`, the expected
mesh-file (FJ) set as the union of the BP3D 4.0 element-table
rows for the record's concepts, and compares it to the shipped
set. For the two deferent-duct records the shipped IS-A set is
empty; the derivation is not.

## 2. Root cause, with the evidence chain

**Root cause.** BP3D 4.0 *does* carry the deferent duct —
under the FMA preferred name "deferent duct", which none of
Milestone 14's Latin-keyed instruments could see — so
Milestone 14 recorded the duct absent, Milestone 38's
inventory-ownership exclusion net therefore let the FMA pair
in as concept-only records with empty geometry entries, and
the one section of `repro_check.py` that Milestones 37/38 did
not partition-scope — the geometry re-measurement — applied
the BP3D element-table derivation to them and collided. Each
link, with its evidence:

1. **The source tables carry the duct, with meshes.**
   `isa_parts_list_e.txt`: FMA19234 "deferent duct",
   FMA19235 "right deferent duct", FMA19236 "left deferent
   duct". `isa_element_parts.txt`: FMA19235 → {FJ3140},
   FMA19236 → {FJ3135}, and the class FMA19234 → {FJ3135,
   FJ3140}. Both OBJ files exist in the IS-A tree. The
   PART-OF tables carry none of the three concepts.
2. **Milestone 14's derivation could not reach the line.**
   Its concept universe was built from organ-rooted lines
   (testis FMA7210, epididymis FMA18255, seminal vesicle
   FMA19386, glans zone FMA20247, perineal muscle FMA9623;
   genital FMA7160 and perineum FMA9579 in PART-OF). In
   BP3D's IS-A tree the deferent duct hangs under FMA30320
   "duct" → "organ segment" → the generic anatomical-
   structure classes — a descendant of none of those roots,
   and absent from the PART-OF tree entirely. Its name sweep
   (`SWEEP_TERMS` in `tools/repro_map.py`) and its absence
   probes keyed on the Latin forms — "ductus deferens",
   "vas deferens", "ampulla of ductus deferens" — all
   zero-hit in tables that name the concept in English.
   Milestone 14's dossier concluded "the duct system is
   missing … the segment a vasectomy interrupts is the
   segment the data lacks." For the duct proper that
   conclusion is **false**, and it is corrected here: the
   segment was in the release all along, filed under the
   name the probes did not cover.
3. **Milestone 38's exclusion net was inventory-based.**
   The intake (M33–M38 pattern) excluded FMA classes already
   owned by an inventory record (checker-verified B2).
   No record owned FMA19234/35/36 — link 2 is why — so the
   frozen "deferent duct" target resolved, and
   `tools/fma_integ_male_map.py` wrote the pair as
   concept-only records (`geometry: "absent"`) with
   mesh-less geometry entries, by the construction it
   applies to every FMA record. It never consults the BP3D
   element tables; for 131 of the file's 133 FMA records
   there is nothing in those tables to consult.
4. **The checker's geometry loop was the one unscoped
   section.** Milestones 37/38 partition-scoped the
   checker's universe, record, disposition and clinical
   sections (and `tools/uri_check.py` was re-scoped
   explicitly, docstring and filter). The geometry loop was
   left iterating all 146 records on the assumption —
   stated in its own scope note — that it "passes over the
   FMA entries' empty mesh lists mechanically", i.e. that
   the derivation over an FMA record's concepts is always
   empty. Links 1–3 are exactly the counterexample.
5. **Bisection.** The same derivation-vs-shipped computation
   over the milestone snapshots: pre-Milestone-37 tree
   (13 records) — 0 mismatches; pre-Milestone-38 tree
   (70 records, including Milestone 37's 57 FMA records,
   whose concepts all derive empty) — 0 mismatches; current
   tree (146 records) — exactly the 2 above, both records
   created by Milestone 38's male intake. The divergence
   was introduced by **Milestone 38**, and predates
   Milestone 39 exactly as Milestone 39 disclosed. One
   further record for honesty's sake: Milestone 38's gate
   matrix reported the reproductive checker green, but the
   failure is deterministic on Milestone 38's own output
   tree (Milestone 39 proved every input byte-identical
   since, and touched neither this checker nor this data),
   so that matrix line cannot have been a full exit-0 run
   of the final tree — a reporting miss in that milestone,
   recorded here rather than repeated.

## 3. Which side is wrong — and why the repair is the checker

The element tables arbitrate the factual core, and on the
facts the checker is *right*: FMA19236's IS-A element set is
{FJ3135} and FMA19235's is {FJ3140}. But a checker is not
only its derivations; it is also the rule it applies them
under, and the rule is where the wrongness sits. The
element-table derivation is the **BP3D partition's defining
rule** — it is what a BP3D record's geometry *is*. The
FMA-partition records are governed by the opposite rule,
asserted independently by `tools/fma_uri_repro_check.py`
(G1) and `tools/fma_integ_male_check.py` (G1): one geometry
entry each, **zero meshes**, geometry_status set, bounding
boxes null. `repro_check.py`'s geometry loop was the single
place in the suite applying one partition's rule to the
other partition's records.

The shipped data, by contrast, is consistent with everything
else that gates it — the FMA checkers' mesh-less rule, the
coverage arithmetic (13 records with meshes, all BP3D), the
assembly anchor (146 inventory / 13 assembled / 16 clinical),
the records' own `geometry: "absent"` fields and verify
flags, and the pack census (1,545). Attributing FJ3135 /
FJ3140 inside the geometry file alone — the superficially
available "fix" — would not be a repair but half of a
geometry intake: it would make the file contradict the
inventory records, both FMA checkers, the coverage meta and
the assembly anchor simultaneously, and it would upgrade two
concept records to geometry-carrying ones outside any
geometry-intake decision (the Milestone 34 line governs
geometry admissions). Regenerating through the existing
pipeline cannot produce it either: the pipeline has no code
path that attributes BP3D meshes to an FMA record, and
re-running it reproduces the shipped file byte-identically.
The artifact is what the pipeline, the doctrine and five
other gated artifacts agree on; the checker is the outlier.
**The checker is repaired.**

What the failure genuinely exposed — Milestone 14's false
absence, and two claimable BP3D meshes sitting unattributed
— is not scoped away. It is adjudicated on the record (§4)
and left as an explicit open item (§6).

## 4. The repair

All changes are in `tools/repro_check.py`; no data file is
touched.

- The geometry re-measurement loop is partition-scoped with
  the house idiom (`inv_rec[rid].get("source") ==
  "fma-5.1.0"`, as in `tools/uri_check.py`). The set-equality
  and concept-ids/sex-line correspondence checks still span
  all 146 records; the BP3D partition (13 records, 20 mesh
  entries) is re-measured exactly as before — same
  derivation, same OBJ re-reading, same totals and bounding
  boxes (IS-A 3284 v / 5130 f, PART-OF 7726 v / 6338 f,
  unchanged).
- FMA-partition entries are asserted mesh-less in the same
  section (mesh lists empty, bounding boxes null, totals
  zero), matching the FMA checkers' G1 rule.
- **The regression gate (new check).** The element-table
  derivation over FMA-partition concepts is still computed
  for every such record, and the resulting collision map
  must equal the adjudicated set exactly:

  ```
  repro.left-deferent-duct   isa {FJ3135}, partof {}
  repro.right-deferent-duct  isa {FJ3140}, partof {}
  ```

  with the adjudication written into the checker beside the
  constant: the concepts are BP3D-carried (link 1), the
  records stay concept-only until a geometry-intake decision
  re-files them, and the claimable meshes are pinned so
  that *any* change to the collision set — a newly
  BP3D-carried FMA concept appearing in an intake, a changed
  file set, or the pair's deliberate re-filing — fails
  loudly instead of drifting.
- The docstring scope note is rewritten to state the
  partition rule and the gate accurately (it previously
  described the mechanical pass-over that failed).
- **Negative tests.** The gate was proven to bite, in a
  sandboxed copy of the tree, three ways, each time as the
  *only* failing check (68/69, exit 1): (A) one adjudicated
  entry renamed in the checker; (B) FJ3135 added to the
  left record's shipped meshes (mesh-less violation);
  (C) a second record re-keyed onto a BP3D-carried concept
  (a new, unadjudicated collision).

Result: `repro_check: 69/69 checks passed`, exit 0 — the
68 pre-existing checks plus the gate.

## 5. Cross-system sweep

The same assertion pattern was run over the other ten
systems — every inventory record, derivation vs shipped,
partition-aware — first as a one-off computation and then as
a durable read-only tool, `tools/attribution_sweep.py`,
which now carries the adjudicated set and can be re-run at
any intake:

| System | Records | Outcome |
|---|---|---|
| skeletal | 206 | consistent (pre-inventory schema, keyed by its single `fma_id`; no FMA partition exists) |
| muscular | 359 | consistent, 0 collisions |
| cardiovascular | 646 | consistent, 0 collisions |
| nervous | 419 | consistent, 0 collisions |
| respiratory | 83 | consistent, 0 collisions |
| digestive | 93 | consistent, 0 collisions |
| urinary | 73 | consistent, 0 collisions |
| lymphatic | 135 | consistent, 0 collisions |
| endocrine | 17 | consistent, 0 collisions |
| reproductive | 146 | consistent; the 2 adjudicated collisions |
| integumentary | 59 | consistent, 0 collisions |

Total: 2,236 records swept; the deferent pair is the only
inventory↔geometry attribution collision in the Body Model.
No sibling drift exists; nothing else was repaired, and
nothing ambiguous was found to list. (The skeletal line runs
over the record's own `fma_id` because that module predates
the `concept_ids` schema; under that keying its derivation
matches its shipped sets for all 206 records × 2 trees.)

## 6. Honest limits and the open item

- **Milestone 14's absence census is corrected for one
  line only.** The deferent duct proper exists in BP3D 4.0
  (FJ3135/FJ3140). Milestone 14's wider claim — the duct
  *system* below the organ wholes (segments, ampulla,
  ejaculatory duct) — is untouched by this finding: those
  concepts have no BP3D element rows (the sweep's empty
  derivations for the Milestone 38 segment records prove
  it), and Milestone 38's intake of them as concepts
  stands. This milestone does not re-audit Milestone 14's
  universe derivation beyond the deferent line; other
  modules' root-and-sweep derivations could in principle
  hold analogous naming misses, and the sweep bounds the
  *geometry* consequence of any such miss (a missed concept
  can only collide if it is later intaken from the FMA —
  which the gate now catches at intake time for the
  reproductive file, and `attribution_sweep.py` catches
  model-wide when run).
- **The pair remains concept-only, deliberately.** The
  meshes FJ3135 (left) and FJ3140 (right) are real,
  measured and claimable — FJ3135: 863 vertices / 1,110
  faces, bounding box x [2.55, 102.62] (the model's left);
  FJ3140: 787 vertices / 944 faces, x [−84.08, −3.90] —
  but claiming them means re-filing
  two records as geometry-carrying, with the assembly,
  packing, W6-census (1,545 → 1,547) and Milestone 38
  accounting consequences that follow. That is a
  geometry-intake decision for the Milestone 34 line, not a
  checker repair; it is recorded here as an open item with
  everything needed to take it.
- The gate pins the collision set for the reproductive
  file inside its own checker. The model-wide sweep is a
  tool, not yet a wired-in gate for the other systems'
  checkers; their FMA checkers' mesh-less assertions plus
  this sweep, run at intakes, cover the same ground.

## 7. Gate matrix

All run against the finished state:

- Tranche checkers: skeletal, muscle, muscle assembly,
  cardiovascular, nerve (M9), FMA nerve (M33), major nerve
  (M39), respiratory, digestive, urinary, lymphatic,
  endocrine, integumentary, FMA lymphatic/endocrine, FMA
  urinary/reproductive, FMA integumentary/male — **all exit
  0**; reproductive — **69/69, exit 0** (was 67/68, exit 1).
- `attribution_sweep.py` — **ALL SYSTEMS CONSISTENT**,
  exit 0.
- `assembly_check_all` — **ALL GATED CHECKS PASS**.
- `verify_web.js` — **ALL CHECKS PASS** (W6 slot census
  unchanged at 1,545).
- `theatre_check` — **245 checks, 0 failures**.
- `case_check` — **5,145 passed, 0 failed**.
- Physiology `validate` — **VALIDATION: ALL HARD GATES
  PASS** (exit 0).
- Native `anatomica verify` — **99 data assertions PASS /
  0 FAIL**; exit 2 at the GPU initialisation stage (no wgpu
  adapter on this VM), the standing disclosed limitation of
  every milestone verified here.

Non-regression, proven by hashes: against Milestone 39's
pre-build snapshot (3,579 files over data, web/data, native,
physiology, theatre, cases), 3,578 files are byte-identical
today and the single changed file is
`web/data/records.json` — Milestone 39's own documented
regeneration. **Milestone 40 changed no data file at all**:
the geometry packs, manifest and `delivery.json` are
byte-identical, so no pack delta exists and W6 stands as
re-verified above. This milestone's footprint is
`tools/repro_check.py` (repaired), `tools/attribution_sweep.py`
(new) and this dossier.

## 8. Files of this milestone

Modified: `tools/repro_check.py`. New:
`tools/attribution_sweep.py`, `MILESTONE-40.md`. No data,
geometry, pack, web or native file is modified.
