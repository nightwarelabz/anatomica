# Milestone 29 — Case Workbench case #3: appendicitis, and the case of the two scores

**State: BUILT LOCAL. Not uploaded.** Case #3 of the Case Workbench
(`case.appendicitis.003`) is complete and the full verification matrix
is green. It closes the second case→Theatre loop: case #1 disposed to
Milestone 17's cholecystectomy and its failure became case #2; case #3
disposes to Milestone 28's laparoscopic appendicectomy
(`proc.appy.lap`). The milestone also generalises the workbench
machinery with a fourth declarative criteria-block kind — **`score`** —
because this case's teaching core is two published clinical scores
that disagree, and both had to be computed mechanically from the
findings, not asserted in prose.

## The case

A 26-year-old woman, 24 hours of pain that began periumbilical and
migrated to the right iliac fossa. The presentation was chosen so the
differential is genuinely contested in a woman of reproductive age:
appendicitis against ovarian torsion, ruptured ovarian cyst, ectopic
pregnancy, acute pyelonephritis, ureteric stone and pelvic
inflammatory disease, plus the residual category — **8 hypotheses**.
The menstrual history (LMP 3 weeks ago, sexually active, no hormonal
contraception) keeps ectopic pregnancy live at stage 1; the urine
pregnancy test retires it at stage 2. That ordering is deliberate and
is the case's central staging lesson.

Census: **4 stages, 25 findings, 3 labs, 2 measurements, 6 orderable
tests, 8 hypotheses**, of which 5 findings are explicitly recorded
absences (no urinary symptoms, no flank pain/CVA tenderness, no PID
features, no peritonism, no free fluid on ultrasound). All 8 priors
are verify-flagged placeholders — no consulted source quantifies this
differential's pre-test distribution, and the case says so on every
prior rather than borrowing a number. Test time/cost figures are
verify-flagged accounting placeholders, as in cases #1–#2.

## The two scores, computed item by item

Both instruments are declared as `score` blocks in the case file and
evaluated by the runner; the checker re-derives them with an
independent implementation and compares the full result dictionaries
at every stage. Unmeasured items are recorded **not-assessed**, never
assumed — at stage 1 both scores are partial totals.

**Alvarado (C17 — Alvarado 1986; MANTRELS):**

| Item | Evidence | Points |
|---|---|---|
| Migration of pain | f.pain-migration | 1 |
| Anorexia | f.anorexia | 1 |
| Nausea/vomiting | f.nausea-vomiting | 1 |
| RIF tenderness | f.rlq-tenderness | 2 |
| Rebound pain | meas.rebound-grade = 1 ≥ 1 | 1 |
| Temperature | 37.6 °C ≥ 37.3 °C | 1 |
| Leukocytosis | WBC 12.4 > 10.0 | 2 |
| Left shift | neutrophils 78% > 75% | 1 |
| **Total** | | **10/10 — "very probable"** |

Stage 1 partial: **7**, with leukocytosis and shift not-assessed.

**AIR — Appendicitis Inflammatory Response (C18 — Andersson &
Andersson 2008):**

| Item | Evidence | Points |
|---|---|---|
| Vomiting | f.nausea-vomiting | 1 |
| Pain in RIF | f.rlq-pain | 1 |
| Rebound, graded | grade 1 = light tier | 1 (of 3) |
| Temperature | 37.6 °C < 38.5 °C | 0 |
| PMN proportion | 78% in 70–84% tier | 1 (of 2) |
| WBC | 12.4 in 10.0–14.9 tier | 1 (of 2) |
| CRP | 26 mg/L in 10–49 tier | 1 (of 2) |
| **Total** | | **6/12 — "intermediate probability"** |

Stage 1 partial: **3**, with pmn, wbc and crp not-assessed.

**Where they agree and disagree** (the adjudication carries this as a
declared `score_comparison` block, and the checker asserts its stated
finals equal the computed ones). Agreement: same evidence base, same
rank-1 hypothesis, both complete only when the stage-2 bloods land.
Disagreement: different risk classes for the same patient, and the
divergence is mechanical. Alvarado prices *presence* — tenderness is
2 points at any severity, leukocytosis 2 points at any count above
10.0, and its temperature line (37.3 °C) is met by 37.6 °C — so this
patient's soft values saturate it at 10/10. AIR prices *magnitude* —
every one of those values lands in its lowest positive band, its
temperature line (38.5 °C) is not met, and it totals 6/12. The
consulted guideline (C20, WSES Jerusalem 2020) sides with AIR's
caution twice: Alvarado is not sufficiently specific to positively
confirm appendicitis in adults (statement 1.3), AIR is among the
best-performing scores (statement 1.4), and intermediate-risk
patients — women of reproductive age in particular — go to imaging.
The CT was therefore the adjudicating evidence the better-calibrated
instrument called for, not a formality after a 10/10; it also carried
the severity information that selected the Theatre branch.

## Likelihood ratios — only what was consulted

| Finding | LR | Status | Source |
|---|---|---|---|
| Migration of pain → appendicitis | LR+ 3.18 | cited | C19 (Wagner 1996 JAMA table lineage) |
| Negative urine β-hCG → ectopic pregnancy | LR− 0.0361 = (1−0.97)/0.83 | computed | C21 (single study; sens 97%, spec 83%, NPV 99.3%) |
| CT composite positive → appendicitis | LR+ 16.421 = 0.936/(1−0.943) | computed | C19 (Kinner et al. pair, as reported) |

Deliberately **not** used, with the reasons recorded in the case file:
the RLQ-pain LR (the consulted table reports a range, 7.3–8.5, and
the workbench multiplies point values only); any ultrasound LR (the
appendix was not visualised — non-visualisation is recorded as a
non-result, not a negative); any per-lab LR (the inflammatory
variables are priced by the score blocks; multiplying per-variable
LRs on top would double-count one evidence stream). The hCG figure
is labelled single-study wherever it appears, and the adjudication's
ectopic exclusion rests on the test **plus** two normal adnexal
imaging studies — the case records that a small minority of ectopic
pregnancies test negative and does not present the test as absolute.

Workbench board (priors → stage 4): appendicitis 0.33 → **0.6103**
(migration) → 0.6466 → 0.6466 → **0.9678** (CT). Ectopic pregnancy
0.10 → 0.0582 → **0.0022, ruled out at stage 2**; every rival first
crosses the 0.02 rule-out line at stage 4. Learner Brier by stage:
0.5150 / 0.3656 / 0.2370 / 0.0118; workbench: 0.1749 / 0.1470 /
0.1470 / 0.0012. Resource tally: 195 min, 19 cost units
(verify-flagged). Order classifications, all recomputed by the
checker: CBC and CRP **criteria-completing** (they settle exactly
alvarado.leukocytosis, alvarado.shift, air.wbc, air.pmn, air.crp),
urine hCG and CT **discriminating**, urinalysis and pelvic ultrasound
**safety-net**.

## The anchoring event — exactly one, by design

The model learner holds ectopic pregnancy at **0.15 at stage 2** —
the very stage the workbench rules it out (0.0022) on the negative
pregnancy test — reasoning that the test "might have been done too
early." One scored anchoring event: `(stage 2, hyp.ectopic-pregnancy)`.
The debrief's analysis names the inversion: the test's LR− already
prices its sensitivity, so a negative result is a conclusion, not a
suggestion; the warranted residue of vigilance is the imaging
conjunction the adjudication uses, not a 0.15 board entry. The
learner's diagnosis, branch and disposition are all correct — the
normal shape of a good case.

## Imaging link — an honestly bounded absence

Checked against the shipped s0778 series (TotalSegmentator v1.0,
104 labels), the finding is an asymmetry:

- **The imaging series has NO appendix label.** The full label list
  was read; the crosswalk has no appendix row. The series therefore
  cannot show the appendix, let alone this case's pathology — and
  s0778 is in any case a 57-year-old man, while the patient is a
  26-year-old woman. Three individuals (synthetic patient, imaging
  subject, atlas subject) are kept separate in the case's
  `honesty_block`, as in case #1.
- The link is localisation by neighbour: the **colon label (index 9 →
  Body Model record `large-intestine`)**, recounted from the shipped
  bins by the checker at every run: **324,670 voxels; slices (files,
  0-based) 45..248 = 204 slices (DICOM instances 46..249); max
  cross-section file 186 (instance 187) = 4,722 voxels; z range
  1311.42..1615.92 mm; volume 324,670 × 3.375 mm³ = 1,095.76 mL**;
  HU statistics equal to the crosswalk's.
- **The Body Model HAS the appendix**: `canal.appendix` is a real
  inventory/geometry/assembled record, and the compound clinical
  record `dig.cecum-appendix` exists — its own text records that the
  consulted sources do not describe the appendix's own structure or
  function, an inherited absence the case states rather than papers
  over. The appendix anatomy the learner operates on in the Theatre
  comes from the Body Model, not from s0778.

## Disposition and branch consistency

Disposition: admit, supportive care (case data), preoperative
antibiotics, and **early laparoscopic appendicectomy** — handoff to
`proc.appy.lap`, recorded exactly as case #1 records its
cholecystectomy handoff, and re-verified by the checker against the
procedure file (id match; register resolves `canal.appendix` to
`data/digestive/digestive-inventory.json`; standard configuration =
**36 required microsteps** of 47). Branch consistency is carried by
recorded findings, not assumptions: `f.ct-uncomplicated` records no
perforation, no abscess, no free gas, no generalised contamination,
and `f.ct-appendicitis` places the appendix in standard position —
so the **standard configuration** is invoked (the trace-06 pathway),
the perforated severity branch (trace-09) is not, neither variant
(retrocecal/pelvic) is, and the healthy-base endoloop closure of
decision point dp3 is the implied branch. The antibiotics-first
non-operative alternative (a live topic in C20) is recorded in the
case as considered; the disposition is operative by the workbench's
design, and the case says that too.

## Ontology

Verified in-session via EBI OLS (Milestone 29 addenda to the C10/C11
registers): appendicitis **MONDO:0005649**; ectopic pregnancy
**MONDO:0000755**; ovarian cyst **MONDO:0003282** (the class denotes
the cyst; no rupture-specific class exists — stated in the case);
acute pyelonephritis **MONDO:0003529**; ureterolithiasis
**MONDO:0007009**; pelvic inflammatory disease **MONDO:0000922**.
**Ovarian torsion has no Mondo class** — the full "torsion" result
set (39 classes) contains dystonias, spermatic-cord and non-human
torsions only — so the hypothesis carries `mondo: null` with the
absence recorded, per the standing rule. HPO terms are reused only
from the C11-verified register (HP:0002027, HP:0001945, HP:0002018,
HP:0002013, HP:0001974).

## Machinery: the `score` block kind

`tools/case_run.py` and `tools/case_check.py` (independent
implementations, as always) gained a fourth block kind. A score item
is flat (`points` + evidence) or tiered (tiers declared
highest-first; first satisfied tier wins). Three-valued semantics
mirror the existing items: satisfied / unsatisfied / **unknown** —
an item is unsatisfied only when *every* tier is unsatisfied, so a
partially revealed tiered item is not-assessed, never zero-assumed.
The block result carries per-item states and points, the total, the
not-assessed list, a partial flag, and the band status. Score items
join `criteria_items`/`crit_items` on both sides, which is what makes
the blood tests classify as criteria-completing through the ordinary
machinery. The physiology link declares the resting baseline only —
the engine has no febrile/inflammatory state, so the patient's
37.6 °C and HR 98 are labelled case data beside the engine's
HR 63.3 baseline, with the gap stated (trace hash `0xcee16b0ddee95d76`,
identical to case #1's current link; case #1's profile re-runs the
engine itself).

## Regression proof

Cases #1 and #2 are computationally identical after this milestone:
their case files, attempt files and regenerated debriefs are
**SHA-256-identical** to the pre-milestone baseline
(debriefs `d16f7209…` and `492727f4…`; case files `5fb6b947…` and
`1891625f…`). The only shared-file change is `cases/parameters.json`,
extended append-only in the Milestone 22 pattern (sources C17–C22,
three LR derivations, dated OLS addenda inside C10/C11 — load-bearing:
the checker's ontology section requires case #3's Mondo ids to appear
in C10's consulted text).

## Verification (all run at this milestone)

- `tools/case_check.py` — **5,145 passed, 0 failed** (Milestone 22
  baseline: 3,280), including all three per-case profiles, the
  case-#2 Theatre loop re-verification, and the case-#1 engine
  re-run.
- `tools/theatre_check.py` — **245 checks, 0 failures** (both
  procedures).
- Physiology `validate` — **ALL HARD GATES PASS**.
- `tools/verify_web.js` — **ALL CHECKS PASS**.
- `tools/assembly_check_all.py` — **ALL GATED CHECKS PASS**.
- Native: `cargo test` 8/8; `verify` data checks **99/99 PASS**. The
  verify run's GPU render stage could not initialise an adapter in
  this session's environment (no Vulkan ICD present on the VM image)
  and so did not execute; Milestone 29 changes no native code, packs
  or geometry, and the data stage it gates is fully green.

## Honest limits

- **Three cases are still not a calibration series.** The library
  now spans biliary, post-operative biliary injury, and appendiceal
  presentations; nothing about three authored cases validates the
  workbench's numbers against real cohorts. All priors in case #3
  are flagged placeholders; the hCG LR is single-study (C21, an
  early-pregnancy-presentation cohort, not the whole RLQ
  differential); the CT accuracy pair comes from a
  children-and-young-adults comparison (this patient is 26). Every
  one of those limits is stated in the case file where the number is
  used.
- **The expert-review gate remains UNMET** (`recorded_reviewers: []`,
  checker-asserted): this case, like #1 and #2, is
  `dual-sourced-draft` teaching material with formative-only scores
  until qualified clinicians review it.
- The urinary hypotheses carry no Body Model body-record: the v1
  urinary inventory does not cover kidney/ureter records, and the
  case records that dataset gap instead of asserting unverified
  references (the gap is already on the project's standing list).
- The engine still has no inflammatory state; case #3's fever and
  tachycardia are case data. That is now the binding physiology gap
  for the case library, ahead of further case authoring.

## Files in this milestone (for the upload tap)

New: `cases/case.appendicitis.003.json`,
`cases/attempts/attempt.case-appendicitis-003.model-learner.json`,
`cases/debriefs/debrief.case-appendicitis-003.model-learner.json`
(generated), `MILESTONE-29.md`.
Changed: `cases/parameters.json` (append-only extension),
`tools/case_run.py` and `tools/case_check.py` (score block kind +
case-3 profile), `cases/README.md`.

## Next steps

- Case #4 candidates: a presentation that exercises the physiology
  engine's existing states (so the case can link a *perturbed*
  engine state, not only the baseline), or the E1/E2 boundary the
  Strasberg classification was built for.
- Physiology: an inflammatory/febrile engine state is now the
  binding gap for the case library (fever, tachycardia, leukocyte
  response as computed state rather than case data).
- The dataset-gap decision (a full FMA/TA-class source) would unblock
  the urinary body-records here as well as the standing nerves-first
  gap list.
