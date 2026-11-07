# ANATOMICA — Milestone 37

**FMA concept intake #3: the urinary interior and the female
reproductive tract, plus the Milestone 35 plexus label
re-verification.**

Local only. Nothing uploaded.

Tools: `tools/fma_uri_repro_map.py` (builder),
`tools/fma_uri_repro_check.py` (independent checker),
`tools/fma_plexus_correct.py` (plexus correction),
`tools/ta2_match_fma37.py` / `tools/ta2_decide_fma37.py` /
`tools/ta2_pass_fma37.py` (the TA2 pass). Accounting artifact:
`data/fma-intake-37.json`.

## 1. What was absent

**Urinary (Milestone 12).** The module carried 6 BP3D records —
the two kidneys (exterior wholes), the two ureters, the bladder,
the urethra — and nothing inside any of them. The Milestone 12
census probed 92 concept names and got zero hits for the entire
interior: no cortex, medulla, pyramid, papilla or column; no
renal pelvis, calyx, sinus, lobe, fascia, capsule or hilum; no
nephron, corpuscle, glomerulus, tubule segment, loop of Henle,
collecting duct, juxtaglomerular apparatus or vasa recta; no
bladder part, trigone or detrusor; no ureteric junction; and the
urethra unsexed and undivided. 21 absence probes were re-run for
this intake against the current urinary inventory; all returned
zero (`data/fma-intake-37.json` §urinary.absence_probes).

**Reproductive (Milestone 14).** The module carried 13 BP3D
records. Its own census measured the asymmetry exactly: BP3D
carries 14 male concepts against exactly **one** female concept
(the mons pubis, shared-rated by that milestone). The entire
internal female tract — ovary, uterine tube, uterus, vagina,
vulva — has no BP3D concept at all, and TotalSegmentator v1 has
zero reproductive labels, so the gap could not be closed from
any source already in the tree. 15 absence probes re-run for
this intake; all zero (§reproductive.absence_probes).

These were the last two systems on the standing blocker list
whose thinness was a *concept* gap in a source already cleared
for intake (FMA 5.1.0, CC BY 4.0, hash-pinned at Milestone 33).

## 2. Resolution discipline (as Milestones 33/36)

Absence census → frozen target list → mechanical resolution
against `fma.owl` under the **depth-aware** parser (the naive
block parser is known-defective: `preferred_name` can sit after
dozens of restriction axioms; Milestone 36 §5.1) → records
carrying FMAID, the verbatim preferred name, the IS-A group
path to *Anatomical entity*, source `fma-5.1.0`, geometry
`absent` and dated verify flags → an independent checker that
re-parses the OWL as XML and shares no code with the builder →
the TA2 pass through the Milestone 35/36 parameterized pipeline
→ a per-target accounting file.

Sided targets resolve to a left/right record pair only when
**both** sided classes exist and each is an IS-A child of the
un-sided class (parent-verified mechanically for all 21 sided
targets). The FMA names sided kidney parts in the suffix form
("Cortex of left kidney"); the checker's side/name fidelity
rule covers both that form and the prefix form ("Left renal
pelvis").

**Exclusions (mechanical, checker-verified).** Five frozen
targets named classes already owned elsewhere in the Body
Model and were excluded rather than duplicated:

| Target | FMAID(s) | Owned by |
|---|---|---|
| Kidney | FMA7205 / FMA7204 | urinary `kidney.left-kidney` / `kidney.right-kidney` (BP3D) |
| Ureter | FMA15572 / FMA15571 | urinary `ureter.left-ureter` / `ureter.right-ureter` (BP3D) |
| Urinary bladder | FMA15900 | urinary `urinary-bladder` (BP3D) |
| Urethra | FMA19667 | urinary `urethra` (BP3D) |
| Mons pubis | FMA20218 | reproductive `mons-pubis` (BP3D) |

Zero targets were not found in the FMA. Granularity deferrals
(classes that exist but sit below the intake's granularity, or
boundary calls) are named in the accounting artifact, not
silently dropped: urinary defers the renal arterial segment
set, the ureteric bud, the bladder neck's smooth-muscle
sphincter (an FMA-zone reading that collides with the
sphincter family — named for a ruling), papillary ducts,
arteriolae rectae and the perirenal fat capsule; reproductive
defers the perineal membrane and pouches (boundary structures
with urinary and pelvic-floor claims), the epoophoron /
paroophoron remnants, and the paraurethral glands — the FMA
carries those only as a *set* class (FMA265251) plus duct and
orifice classes, no single gland class (see §8).

**Boundary call, recorded.** The perineal body (FMA20209) is a
sex-shared midline structure; Milestone 14 probed it on the
shared line and found it absent there too. It is recorded
under reproductive — the module that owns the perineum
records — with `sex_line: "shared"` carried on the record
itself.

## 3. The records taken

| System | Targets | Resolved | Excluded | Records added | Census |
|---|---|---|---|---|---|
| urinary | 63 | 59 | 4 | **67** (8 sided pairs + 51) | 6 → **73** |
| reproductive | 45 | 44 | 1 | **57** (13 sided pairs + 31) | 13 → **70** |

Urinary by subtree: kidney interior 19 (12 sided) · nephron
and microvasculature 20 (2 sided) · bladder parts 9 · ureter
parts 7 (2 sided) · urethra divided 12. Reproductive by
subtree: ovary 11 (6 sided) · uterine tube 9 (4 sided) ·
uterus 19 (8 sided) · vagina 5 · vulva 12 (8 sided) ·
perineum (shared) 1.

**Body Model census: 1,983 → 2,107 inventory records.**
Records with geometry: **1,545, unchanged.** Clinical records:
361, unchanged. Every new record is concept-only: the FMA is
an ontology and carries no mesh data, and no geometry source
has cleared the project's license and registration bars for
these structures (the Milestone 34 audit governs Z-Anatomy).

Two naming facts the intake surfaced, recorded rather than
smoothed over: the FMA's name for the perimetrium is carried
on the class "Serosa of uterus" (FMA17744) — the record keeps
the verbatim FMA name and the target-name correspondence is in
the accounting file; and the FMA's detrusor class (FMA68018)
is named simply "Detrusor".

## 4. TA2 name pass (FIPAT 2nd ed., version 2.07)

Same parameterized pipeline as Milestones 35/36, with urinary
and reproductive class vocabularies added. Every FMA record
either gained `ta_name` / `ta_code` / a TA2 entry in `sources`,
or carries exactly one dated `ta_name:` verify flag stating
the outcome and its reason. The pass is mechanical (artifact
section written in the same step), idempotent (byte-identical
on re-run), and touched FMA records only — gated in both
scoped tranche checkers by `ta2_discipline`.

| Intake | Records | Resolved | Ambiguous | Not found |
|---|---|---|---|---|
| urinary (M37) | 67 | 42 | 2 | 23 |
| reproductive (M37) | 57 | 56 | 0 | 1 |
| **all FMA intakes** | **555** | **422** | **103** | **30** |

What the outcomes mean, per family:

- **The urinary not-found block is one fact, not 23 failures:**
  TA2's served table carries no nephron-segment terms at all.
  Glomerulus, the tubule segments, the collecting duct, the
  macula densa, the juxtaglomerular apparatus and the vasa
  recta are Terminologia Histologica territory; TA2 proper
  does not name them. The ureteropelvic and ureterovesical
  junctions and the bulbous part of the urethra are likewise
  unnamed in TA2. No correspondence was forced for any of
  them.
- **TA2 divides two urinary structures by sex** that the FMA
  carries unsexed — the urethral orifice (3432 ♂ / 3458 ♀) and
  the external urethral sphincter (3431 ♂ / 3454 ♀) — recorded
  ambiguous with both candidates on the flag.
- **Prostatic urethra is a chapter twin** (3445 urinary /
  3658 male genital, same Latin name). Resolved to the
  urinary chapter's entry: the urethra is this module's
  record, and TA2's urinary chapter is where the urethral
  segmentation lives.
- **Collective terms, reproductive side:** TA2 names several
  FMA singular classes only as plural collectives — fimbriae
  of the uterine tube (3489, taken by the un-sided record; the
  sided fimbria records stay unresolved on the same
  collective-term ground as the calices), the lesser
  vestibular glands (3564), and on the urinary side the renal
  columns (3370) and major/minor calices (3385/3389). The
  basis is stated in each record's artifact rule.
- Follicle of ovary is not found: TA2 names only the vesicular
  (Graafian) stage (3482), not the generic follicle class.

## 5. Plexus label re-verification — the Milestone 35 note does NOT stand

Milestone 35 §5 recorded that the un-sided classes FMA5906 /
FMA5907 / FMA5908 (brachial / lumbosacral / lumbar nerve
plexus) "carry an `rdfs:label` but no `fma:preferred_name`",
so their six sided records were built with
`class_concept_id: null` and a null entry in the group path.
Milestone 36 flagged the note for re-derivation under the
depth-aware parse, suspecting the naive-parser defect class.

**Re-derived two independent ways** — the depth-aware regex
parse and an ElementTree XML parse of `fma.owl` — all nine
classes (the three un-sided and their six sided children)
carry `fma:preferred_name` **identical to** their
`rdfs:label`. The note was a naive-parser artifact: in these
class blocks the preferred name sits after long restriction
axiom lists, exactly the Milestone 36 §5.1 defect. Parse
evidence is recorded per class in
`data/fma-intake-37.json` §plexus_reverification.

**Correction applied** (`tools/fma_plexus_correct.py`,
2026-11-06): the six sided records in
`data/nervous/nervous-inventory.json`
(`nerve.left/right-brachial-nerve-plexus`,
`nerve.left/right-lumbar-nerve-plexus`,
`nerve.left/right-lumbosacral-nerve-plexus`) had exactly two
fields corrected — `class_concept_id` null → FMA5906 / 5907 /
5908, and the null group-path entry → the class's preferred
name. The corrected paths were asserted equal to the recorded
paths with the null slot filled: nothing else about the paths
was wrong. Record identity re-verified after correction:
FMAIDs unchanged, TA2 outcomes unchanged (brachial 6395
*plexus brachialis*, lumbar 6517 *plexus lumbalis*,
lumbosacral 6516 *plexus lumbosacralis*), and the nervous
inventory's diff against the pre-milestone snapshot is exactly
these 6 records × 2 fields. The correction is gated by checks
P1–P4 of the new checker.

**Adjacent observation, NOT corrected (outside this
milestone's named scope):** `nerve.left-oculomotor-nerve` and
`nerve.right-oculomotor-nerve` carry the same Milestone 33
artifact — null `class_concept_id` and one null group-path
entry — although their IS-A parent FMA50864 "Oculomotor
nerve" does carry a preferred name under the depth-aware
parse. Named here and in the artifact for a future ruling;
checker P4 asserts the correction stayed exactly scoped
(these two are the only records in the nervous inventory
retaining the artifact).

## 6. Non-regression

- **Snapshots first.** Before any write: SHA-256 of 3,785
  files under `data/`, `web/`, `anatomica-app/data`, plus
  parsed snapshots of both target inventories, both geometry
  files, the nervous inventory/geometry and the TA2 artifact.
- **Changed data files: exactly 9** — the urinary and
  reproductive inventory / geometry / assembled files, the
  nervous inventory (plexus correction only), the TA2
  artifact, and `web/data/records.json`. Everything else is
  byte-identical to the pre-build hashes, including **all 23
  geometry pack files** (11 packs, their `.gz` forms and
  `delivery.json`; pack totals unchanged at 304,367,896 B).
- **Pre-existing records identical in parsed form:** the
  urinary 6 and reproductive 13 BP3D records asserted
  record-by-record against the snapshots (only counter meta
  keys plus the new `fma_extension` block changed); the
  nervous diff is exactly the six plexus corrections; every
  pre-existing section of the TA2 artifact parsed-identical.
  `records.json`: +124 entries, all `has_geometry: false`,
  regenerated from inputs that are hash-proven unchanged for
  the other nine systems (the pack run is the identity proof:
  identical inputs, byte-identical packs).
- **Builder idempotent:** second run byte-identical.
  **TA2 pass idempotent:** byte-identical on re-run.
- **Assembly anchors updated:** urinary (73, 6, 6),
  reproductive (70, 13, 16) in `assembly_check_all.py`;
  assembled geometry records unchanged, the assembled metas
  now list the 67 + 57 geometry-absent records.
- `uri_check.py` and `repro_check.py` were partition-scoped
  exactly as `lymph_check.py` was at Milestone 36: every
  concept / record / disposition / clinical check re-derives
  the BP3D partition as shipped; the FMA records are gated by
  the new checker and the TA2 discipline block.

## 7. Gate matrix

| Gate | Result |
|---|---|
| `fma_uri_repro_check.py` (new, independent) | **ALL CHECKS PASS** — L1/L2 license pins; C0 partitions (6/13); F1/F2/F3 fidelity of all 124 records vs an XML re-parse of the OWL (group paths reach *Anatomical entity* 124/124); B1 zero FMAID overlap anywhere in the Body Model; B2 the five exclusions re-derived; G1/G2 geometry correspondence and verify flags; C1 census arithmetic; A1 accounting reconciliation; P1–P4 plexus re-verification (note refuted, correction exact-scoped, identity re-verified) |
| `uri_check.py` | **ALL HARD CHECKS PASS** (BP3D re-derivation partition-scoped; incl. the five M37 TA2 discipline assertions: 67 records, 42/2/23) |
| `repro_check.py` | **all checks pass** (incl. the five M37 TA2 discipline assertions: 57 records, 56/0/1) |
| All other tranche checkers | skeletal FAILURES: 0 · muscle ALL HARD CHECKS PASS · cv PASS · nerve ALL HARD CHECKS PASS · fma_nerve ALL CHECKS PASS · fma_lymph_endo ALL CHECKS PASS · resp ALL HARD CHECKS PASSED · dig ALL HARD CHECKS PASSED · lymph PASS (M36-scoped) · endo PASS (M36-scoped) · integ PASS |
| `assembly_check_all.py` | **ALL GATED CHECKS PASS** (anchors: urinary 73 inventory / 6 assembled; reproductive 70 / 13) |
| `verify_web.js` | **ALL CHECKS PASS** (W1–W10; W6 pick-codec slot census unchanged at **1,545**; W1 listed census 2,185) |
| `theatre_check.py` | **245 checks, 0 failures** |
| `case_check.py` | **5,145 passed, 0 failed** |
| Physiology `validate` | **VALIDATION: ALL HARD GATES PASS** |
| Native `verify` | **99 data assertions PASS / 0 FAIL**; the GPU render stage cannot initialise on this VM (no wgpu adapter) and exits 2 — the standing disclosed limitation of every recent milestone; no data assertion is affected |


## 8. Honest limits

- **Geometry is still absent for everything intaken here** —
  the FMA carries none, and no other source has cleared the
  license and registration bars. These are concept records:
  they complete the model's *inventory*, not its atlas. The
  viewer lists them `has_geometry: false`.
- **TA2 does not cover the nephron.** The 23 urinary
  not-found records are a terminology-coverage fact (those
  structures live in Terminologia Histologica), not an
  intake defect; a TH pass would be a new source decision,
  not a repair of this one.
- **FMA granularity cuts both ways.** Below this intake's
  granularity the FMA carries more (renal segment classes,
  papillary ducts, the epoophoron/paraoophoron remnants) —
  deferred and named in the artifact, not silently dropped.
  And at two points the FMA is *coarser* than TA2: TA2 names a
  cervical canal (3515) and an isthmus of uterus (3510) for
  which the FMA carries no class — those structures remain
  without an FMA concept record, and no substitute class was
  pressed into service.
- **The paraurethral glands have no single FMA class** (a set
  class and duct/orifice classes only), so they were not
  intaken as a record; inventing a class id was not an option.
- **No clinical tranche** was authored for the new records;
  every new record carries the standing `clinical:` verify
  flag saying exactly that, and no clinical value was entered
  anywhere.
- **The oculomotor correction is pending a ruling** (§5): the
  same parser artifact sits on two records outside this
  milestone's named plexus scope. It is documented, gated as
  untouched, and not silently fixed.
- The plexus correction changes **name provenance only** —
  `class_concept_id` and one group-path entry on six records.
  No record was added, removed or renamed; no TA2 outcome
  moved.

## 9. Closing census — what remains blocked, and by what

With this intake, every system on the standing blocker list
whose thinness was a concept gap in an already-cleared source
has been addressed at concept level (lymphatics and
thyroid/parathyroids at Milestone 36; kidney/urinary interior
and the female reproductive tract here). The Body Model
stands at **2,107 inventory records: 1,545 with geometry,
562 concept-only**. What remains separates cleanly into two
kinds of blocked:

**Geometry-blocked (concepts complete; no mesh source has
cleared the license + registration bars):**

- All **555 FMA-sourced concept records** — nervous 286,
  lymphatic 131, endocrine 14, urinary 67, reproductive 57 —
  plus the 7 geometry-absent records that predate the FMA
  intakes. The FMA carries no geometry by design.
- Nerve geometry specifically remains gated by the
  Milestone 34 audit: Z-Anatomy (CC BY-SA 4.0) is blocked on
  per-object provenance separability and the absence of a
  derived registration transform. Until a source clears both
  bars, the atlas's geometry census stays at **1,545**.

**Concept-blocked (no record exists yet, each for a stated
reason):**

- **Skin layers** (integumentary): BP3D 4.0 and TS v1 carry
  no layer concepts; the FMA carries the classes but no
  intake has been run. A named follow-on FMA intake, same
  discipline — the last system on the original blocker list
  not yet addressed at concept level.
- **Male reproductive remainder** (ductus deferens,
  ejaculatory duct, scrotum, bulbourethral glands, penile
  divisions): absent from BP3D beyond the 14 male concepts
  Milestone 14 censused; the FMA carries the classes. Same
  follow-on intake shape; outside this milestone's
  female-tract scope.
- **Paraurethral glands**: blocked *inside the source* — the
  FMA offers only a set class (FMA265251) plus duct/orifice
  classes. No record until a source carries the gland itself.
- **Cervical canal; isthmus of uterus**: named in TA2 (3515 /
  3510) but no FMA class exists to intake. Concept-blocked in
  the cleared source.
- **Deferred-by-granularity classes** (renal segments,
  papillary ducts, perineal membrane and pouches, epoophoron
  / paroophoron, pituitary and adrenal interiors from
  Milestone 36): FMA classes exist; each needs its own
  granularity or boundary ruling before intake, and each is
  named in its milestone's accounting artifact.
- **The nephron's TA2 names**: the records exist (this
  intake); their Latin names are blocked on a Terminologia
  Histologica source decision, not on the FMA.

**Next steps, in order:** (1) the oculomotor pair — rule on
correcting the same artifact on `nerve.*-oculomotor-nerve`
(the correction tool and evidence pattern from §5 apply
unchanged); (2) the skin-layer FMA intake, which closes the
original blocker list at concept level; (3) the male
reproductive remainder intake; (4) geometry — nothing moves
until a source clears the Milestone 34 bars; the concept
inventory is now complete enough that geometry, not concepts,
is the atlas's binding constraint.
