# Milestone 54 — Case #7: The PE Rule-Out Pathway Walked

**Scope.** The seventh Case Workbench case: `case.pe-ruleout.007` —
the pulmonary-embolism rule-out pathway that Case #6 recorded but
deliberately did not walk, walked here in full. A low-risk acute
chest-pain presentation in which the adjudicated outcome is the
**exclusion of PE without imaging**, the correct management is
discharge with safety-netting, and the scored error is
**over-testing** — the mirror image of the prior cases' missed-
diagnosis errors. New sources C48–C51; one further LR derivation
(the D-dimer negative direction, the one Case #6 deliberately never
registered); `profile_case7` added to `tools/case_check.py`
(11,884 / 0). Local only; nothing uploaded.

---

## 1. Why this case, and why now

Case #6 (Milestone 48) built the complete PE machinery — Wells,
PERC, the age-adjusted D-dimer, the ESC 2019 pathway — and then
ran it on a patient who was PE-**likely** from the first stage:
Wells partial at 3.0 completing at 6.0, PERC positive at 5 with
its gestalt precondition stated UNMET, D-dimer 3,850 µg/L in a
post-surgical patient for whom the exclusion side of the pathway
"could never apply", and a CTPA whose LR+ 20.75 closed the case.
Its dossier (§11, §14) named the unwalked side explicitly: the
PE-unlikely patient, in whom the pathway's product is not a
diagnosis but an **exclusion**.

That is the pathway most PE work actually walks — the over-testing
cohort consulted here (C49) ran 14,782 CTPAs across six emergency
departments at a 9.24% yield — and it is the half of the machinery
this module had never exercised. Case #7 exercises it: every
instrument Case #6 declared, re-run in its exclusion direction,
with the pathway terminating at stage 2 and two further stages
spent on whether the learner can hold it.

## 2. The case

**Patient (synthetic, authored fiction).** A 62-year-old woman, a
school administrator, with two days of left parasternal chest
pain: sharp, localized to the left third and fourth
costochondral junctions, worse with deep inspiration, coughing
and twisting, onset the evening after a weekend of gardening and
moving boxes. The pain is reproduced exactly on palpation of the
affected junctions. Mild breathlessness she attributes to the
pain. Vitals: T 36.8 °C, HR 84, BP 128/78, RR 16, SpO₂ 98% on room
air. Calves symmetric; chest clear; **no swelling, heat or
erythema over the junctions**. Light ex-smoker (quit 22 years
ago, ~5 pack-years); no estrogen, no prior VTE, no surgery,
trauma or immobilisation within four weeks, no malignancy, no
regular medication.

**Hypotheses (priors sum exactly 1.00; all verify-flagged, as in
every case).** Musculoskeletal chest-wall pain, costochondritis-
class (**truth**, 0.34); other/unspecified (0.28); acute coronary
syndrome (0.14); pulmonary embolism (0.12); pneumonia (0.08);
pneumothorax (0.04).

**Counts.** 26 findings (20 at stage 1, 4 at stage 2, **0 at
stage 3**, 2 at stage 4), 4 labs, 6 measurements (all stage 1),
5 orderable tests, 2 criteria blocks, 4 stages.

## 3. The pathway, stage by stage

**Stage 1 — history, vitals, examination.** The Wells score is
**complete at 0.0** before any test is ordered: all six objective
items are assessed zeros from the staged evidence (no clinical
DVT signs — symmetric calves; no prior VTE; heart rate 84, not
> 100; no immobilisation or surgery ≤ 4 weeks; no malignancy; no
haemoptysis). The clinician-judgment item is excluded from the
block with its sensitivity stated in the block note, exactly as
Case #6 excluded it: awarding it the maximum +3 would score 3.0,
still PE-unlikely on the two-tier cut and moderate on the
three-tier scale — the pathway stands on either reading. This is
the deliberate mirror of Case #6, whose Wells ran partial → 6.0.

The PERC block evaluates **all eight criteria from stage-1
atoms** and counts **exactly 1** — the patient's age (62 ≥ 50)
and nothing else: pulse 84, SpO₂ 98%, no prior VTE, no recent
surgery or trauma, no haemoptysis, no estrogen, symmetric calves.
**The precondition contrast with Case #6 is stated in the block
note, as the brief required:** PERC applies only where the
clinician's gestalt pre-test probability is already below 15%
(Kline 2004/2008, C37); in Case #6 that precondition was stated
UNMET (the workbench's own PE weight was 0.36), here it is stated
**MET** (stage-1 PE weight 0.12, inside the envelope). And the
rule, speaking under its precondition for the first time in this
module, **still declines to exclude** — on the birthday alone.
That refusal is the case's first teaching point: PERC is a
one-way instrument. Its sensitivity is purchased by counting age
as a criterion, and a 62-year-old can never be PERC-negative on
age; the pathway therefore routes through the D-dimer, exactly as
the ESC 2019 pathway (C41) prescribes for the PE-unlikely tier.

**Stage 2 — first results; the pathway terminates.** ECG normal;
troponin 6 ng/L (reference 0–14, C41) — the ACS safety net the
guideline (C50) and the AFP review (C51) both keep in place for a
62-year-old, run and discharged here because nothing in this
differential quantifies it; bloods normal (WBC 6.8, CRP 4 — the
pneumonia safety net, on conjunction, not on a score: CURB-65 is
deliberately never declared, being a severity instrument whose
atoms (urea, confusion, respiratory rate ≥ 30) this presentation
does not carry).

The D-dimer results at **560 µg/L FEU** — the case's pivot, and
its arithmetic is the design:

- fixed cutoff (C38): 500 µg/L — the result is **60 µg/L above**
  it;
- age-adjusted cutoff (C38, ADJUST-PE: age × 10 for age > 50):
  62 × 10 = **620 µg/L** — the result is **60 µg/L below** it.

On the fixed reading the patient is "positive" and proceeds to
imaging; on the age-adjusted reading — the ESC 2019 pathway's
own reading, validated in ADJUST-PE (the 500-to-age-adjusted
band's untreated 3-month thromboembolic rate was 0.3%, C38) — PE
is **excluded and the pathway terminates**. The age adjustment is
not a refinement of the decision; it *is* the decision.

**The one likelihood ratio.** The case carries exactly one board
LR: D-dimer **LR− 0.0732**, computed from the C39 pooled pair
(sensitivity 0.97, specificity 0.41): (1 − 0.97) / 0.41 =
0.03 / 0.41. Case #6 registered LR+ 1.6441 from the same pair and
**deliberately registered no LR−**, because its post-surgical
patient's exclusion could never rest on it. Here the negative
direction *is* the operative direction, so it is registered —
from the same consulted pair, derivation shown in
`parameters.json`, with the less favourable comparator (Stein
2004's tabulated 0.13, in C39) named beside it. The workbench
board: PE 0.12 → **0.0099**, ruled out at stage 2 (the only
rule-out in the case); truth 0.34 → **0.3825** by renormalisation.
The case states in its adjudication that the exclusion rests on
the **pathway** (PE-unlikely tier + below-cutoff D-dimer, the
ADJUST-PE-validated combination), not on the board weight alone.

**Stage 3 — the demand.** No clinical finding of any kind arrives
at stage 3 — the case file carries zero stage-3 findings and
zero stage-3 labs, and the checker asserts it. The stage's entire
content is social: the patient's husband, whose brother died
suddenly the previous year with the family told "a clot", demands
"Just do the scan, to be safe," and the covering colleague echoes
it. The learner wobbles and orders the CTPA. See §5.

**Stage 4 — the scan returns; adjudication and disposition.** The
CTPA shows no embolus — and moves nothing on the workbench board
(it was already 0.0099; no LR is asserted for the negative scan,
because none was needed and the consulted pair's weight was never
the case's to spend twice). What the scan *does* produce is its
bill and its cascade: a **7 mm solid right-upper-lobe incidental
nodule**, for which the Fleischner Society 2017 guideline (C48)
prescribes CT at 6–12 months with a further look at 18–24 months
to consider — an obligation that outlives the encounter and that
the adjudicated pathway never incurred. The disposition is the
adjudicated one: discharge with analgesia and activity advice
(C51), explicit safety-netting (return immediately for worsening
breathlessness, haemoptysis, faintness, leg swelling, or pain
that changes character), and the Fleischner surveillance letter
the scan made necessary. **No Theatre handoff exists, and the
case states it.**

## 4. The scored error: over-testing

Every prior case scored a missed or delayed diagnosis. This one
scores its opposite, and the machinery's verdict is the scoring:
the stage-3 CTPA classifies **non-contributory** — no posterior,
criteria or safety-net effect — because the pathway had already
terminated. Its grounds are cited from the consulted cohort
(C49), exactly as that paper states them: CTPA carries a median
**10 mSv** of radiation (the equivalent of 137 chest radiographs,
after Smith-Bindman 2009); **incidental findings requiring
diagnostic follow-up in 24% of tests**; and a **14% risk of
contrast-induced nephropathy** per the prospective study the
paper cites (Mitchell et al.) — against a background yield of
9.24% across 14,782 scans. In resource terms the scan is 45 of
the attempt's 125 minutes and 8 of its 15 cost units: the menu's
most expensive item, purchased after the exclusion, deciding
nothing — and purchasing, in this instance, a nodule and its
two-year surveillance tail (C48).

The mirror error the brief named — D-dimer in a PERC-negative
patient — does **not** apply here, and the case says why in the
test's note: this patient is PERC-**positive** (on age), so the
D-dimer is the pathway's prescribed next step, not an excess. The
two errors are distinguished on the record rather than blurred.

The other four orders classify: ECG **safety-net** (ACS), bloods
**safety-net** (pneumonia), D-dimer **discriminating** (it retires
PE across the rule-out line on the counterfactual board), and
troponin **safety-net** — the deliberate contrast with Case #6,
where the same order classified criteria-completing because an
ESC severity block stood open to receive it. No severity block
exists in this case; the classification difference is structural,
not discretionary, and the debrief states it.

## 5. Anchoring: the fourth shape — social pressure

The module's anchoring taxonomy now has four installation shapes:

| Case | Shape | Installer |
|---|---|---|
| #4 | clinician-frame | another clinician, before the case begins |
| #5 | self-installed | the learner, from a true exposure history |
| #6 | result-installed | a test result, mid-case (BNP 385) |
| **#7** | **social pressure** | **the family and a colleague, mid-case, with no clinical content at all** |

The learner's arc is legible in her own numbers: PE held at 0.16
at stage 1 (overweighted against the workbench's 0.12 — the fear
is present from the start), **released to 0.07 at stage 2** when
the pathway completes, **re-installed at 0.13 at stage 3** by the
demand alone — the case's single scored anchoring event
(workbench 0.0099, ruled out at stage 2; learner 0.13 ≥ the 0.10
threshold) — and released at the stage-4 commit (0.04, truth
0.55). The CTPA order is the anchor's purchase receipt: it is
placed at the anchor's stage, by the anchor's pressure, against
the completed pathway.

The debrief's analysis names the mechanism: "just to be safe"
prices only one direction of error — it counts the missed clot
and not the radiation, the contrast, or the cascade — and a
family's grief is a real weight in the room that is nonetheless
not evidence about *this* patient's arteries. The recovery is
also the case's thesis: what retires the anchor is not a better
test (the scan decided nothing) but **re-walking the pathway**
— Wells, PERC, the age-adjusted cutoff, the ADJUST-PE band's
0.3% — aloud, with the family, until the exclusion is something
that can be said in the room rather than only computed in the
chart.

## 6. The truth, and its ontology refusal

The truth is musculoskeletal chest-wall pain, costochondritis-
class: inflammation of the costochondral junctions, usually at
multiple levels, **lacking swelling or induration**, with pain
reproduced by palpation of the affected segments (C51); the
AHA/ACC chest-pain guideline's examination table assigns
costochondral-joint tenderness to costochondritis / Tietze
syndrome, and tenderness on palpation markedly reduces ACS
likelihood (C50 — carried with the guideline's own caution:
tenderness shifts probability, it does not by itself exclude a
coronary cause, which is why the ECG/troponin safety net runs).
The decisive evidence — palpation-reproducibility, the mechanical
precipitant, the absent swelling — carries **no likelihood ratio
anywhere in the case**, because no consulted source quantifies it
for this differential; it acts as a stated conjunction in the
adjudication, the module's standing discipline (Cases #4/#5
precedent). ACS is likewise excluded by conjunction, with the
3–6% coronary-disease rate among chest-pain patients *with*
chest-wall tenderness (C51) stated, not hidden.

**The Mondo refusal (recorded, third in the module).** An OLS
search for "costochondritis" returns exactly one Mondo class:
**Tietze syndrome, MONDO:0001858**, which lists "Costochondritis"
among its exact synonyms — but whose returned definition
specifies painful nonsuppurative **swellings** of the costal
cartilages. C51 distinguishes the two conditions on exactly that
point: costochondritis lacks swelling; Tietze is defined by
visible enlargement. This patient has no swelling. The class is
therefore **not asserted**; the truth hypothesis carries
`mondo: null` with the refusal recorded in its `mondo_note`, the
register's C10 consulted text carries the dated Milestone 54
addendum recording the search and the refusal, and the checker
asserts both. A search for "chest wall pain" returns no
chest-wall class at all. (Case #2's refusal of MONDO:0001710 is
the precedent; Case #6's two parent-class codings the contrast.)

HPO layering (all verified in-session, C11 addendum): chest pain
HP:0100749 and pleuritic chest pain HP:0033771 on the pain
finding; **chest pain triggered by palpation HP:6000047** and
**costochondral pain HP:0006649** on the tenderness finding —
HP:6000047's own returned description names costochondritis as
what palpation-induced pain may indicate; dyspnea HP:0002094;
absent fever HP:0001945, absent cough HP:0012735, absent
haemoptysis HP:0002105. The diagnosis-shaped HPO class
"Costochondritis" HP:6001447 was verified and deliberately **not**
used on any finding — phenotypes layer beside the data; the
diagnosis is the adjudication's, not a finding's.

Body Model linkage for the truth: `rib3_left`, `rib4_left`,
`sternum` (skeletal geometry records) — the structures the
examination localizes to. No costal-cartilage inventory records
exist; the case does not pretend otherwise.

## 7. Links discipline

**Physiology.** The link records the pinned resting circulation
baseline — trace hash `0x6369b10e9a71c872`, the seven recorded
outputs, the recorded command — by **data-identity with Case
#1's link**, and the checker asserts that identity. **No
respiratory readout is asserted** (contrast Case #6's 17-value
readout): the respiratory surface was under parallel Milestone
53 construction, and the link's verification states that no
engine re-run was performed for this milestone. The engine has
no thromboembolic, chest-wall or coronary state; the patient's
vitals and gases are authored case data checked against the
consulted ranges, and the gap is stated in the link.

**Imaging.** No `imaging_link`. An `imaging_assessment` (Case #5
pattern) records, per subject (s0778, s1090; both label sets
recounted by the checker at 104): **no embolus label, no nodule
label, no cartilage or costochondral label** — so neither the PE
question nor the incidental nodule nor the chest-wall structure
is a label the series carries; and the shipped studies are
unenhanced thorax-abdomen-pelvis CT, not CT pulmonary
angiography, so the series could not have decided the PE question
in any case. What the series *does* carry is stated too: all 24
rib labels and all five lung lobes, in field — the anatomy
adjacent to both findings is present; neither finding is. In the
adjudicated pathway imaging was correctly not performed; the one
scan the attempt contains is an authored report whose finding
labels this paragraph has already accounted for.

**Theatre.** No handoff key exists in `management`; the absence
is stated in the case (`theatre_note`), against the Theatre's
real five-procedure set, which the checker re-reads.

## 8. Sources

New at this milestone (all consulted in-session; register texts in
`parameters.json`):

| ID | Source | What it carries in this case |
|---|---|---|
| C48 | Fleischner Society 2017 (MacMahon et al., Radiology 2017) | single solid 6–8 mm nodule → CT at 6–12 months, then consider 18–24 — the disposition's surveillance letter |
| C49 | Predictors of Overtesting in PE Diagnosis (Acad Radiol 2019) | 14,782 CTPAs, 9.24% yield; 10 mSv median (= 137 CXR); incidental findings in 24%; 14% CIN risk as cited — the scored error's grounds |
| C50 | 2021 AHA/ACC chest-pain guideline (Gulati et al., Circulation 2021) | tenderness on palpation markedly reduces ACS likelihood; costochondral tenderness → costochondritis / Tietze in the examination table; the no-single-element-excludes caution |
| C51 | Proulx & Zryd, Costochondritis (Am Fam Physician 2009) | definition (multiple levels, NO swelling), palpation reproduction, Tietze distinction, CAD in 3–6% with tenderness, ECG advice > 35 y, treatment — and the Mondo refusal's clinical ground |

Reused from the register: C35 (Wells), C37 (PERC + precondition),
C38 (ADJUST-PE cutoffs + the band's 0.3%), C39 (the pooled pair —
now both directions registered), C41 (ESC 2019 pathway + troponin
range), C7 (WBC range), C45 (CRP range), C10/C11 (ontology, with
Milestone 54 addenda). StatPearls/NCBI remains unreachable
(reCAPTCHA) and is cited for nothing, as throughout.

Per-value provenance: every clinical number in the case traces to
the register entry named in its field-level `source`; every
patient particular is labelled case data; priors are
verify-flagged population-shaped authoring judgments, as in all
seven cases.

## 9. Verification

- `tools/case_check.py`: **ALL CHECKS PASS — 11,884 passed, 0
  failed** (10,298 at Milestone 48; the growth is the generic
  machinery over a seventh case plus `profile_case7`). The profile
  asserts, among the generic checks: the single-LR discipline and
  its value/source/status; Wells 0.0 complete (never partial) at
  all four stages with the judgment item absent from the block;
  PERC total 1 at stage 1 with the age item satisfied and the
  other seven unsatisfied; the precondition-MET wording and the
  Case #6 contrast present in the block note; the D-dimer margin
  arithmetic recomputed from the lab value and the patient's age
  (560 vs 500 vs 62 × 10 = 620, margins 60 / 60); both board
  trajectories; `ruled_out == {PE: 2}` exactly; the anchoring
  event recomputed independently as exactly
  `[(3, hyp.pulmonary-embolism)]` with the learner's arc pinned
  (0.16 / 0.07 / 0.13 / 0.04, truth 0.55 at commit); zero stage-3
  findings and labs; physiology-link identity with Case #1 and
  the absence of any respiratory readout; both crosswalks
  recounted (104 labels; no embolus/nodule/cartilage label; 24
  rib labels; five lung labels); the Mondo refusal (truth /
  adjudication / ground truth all null, MONDO:0001858 named in the
  note); the no-handoff assertion against the real five-procedure
  set; the debrief's classification dict and the 125 min / 15 unit
  tally; the attempt commit matching the adjudication.
- Regression: Cases #1–#6 — case files, attempts and regenerated
  debriefs **byte-identical** to the pre-milestone snapshot
  (SHA-256 census taken before the build); `parameters.json`
  differs only by the intended extension (milestone marker 48 →
  54, one LR derivation, C48–C51, the two dated register addenda,
  the note addendum).
- Full matrix on the tree as found (Milestone 53's physiology
  included, untouched): `tools/theatre_check.py` **595 / 0**;
  `tools/imaging_toolkit_check.py` exit 0 (0 conformance findings
  standing); `tools/verify_web.js` **ALL CHECKS PASS**; native
  `cargo run --release -- verify` exit 0, **ALL HARD CHECKS PASS**
  (107 PASS / 0 FAIL lines) and native `cargo test --release`
  green; every other `tools/*_check.py` (assembly_check_all,
  skeletal, muscle, muscle_assembly, cv, nerve, major_nerve,
  resp, dig, uri, lymph, endo, repro, integ, fma_nerve,
  fma_uri_repro, fma_lymph_endo, fma_integ_male) exit 0.
  Physiology `cargo run --release -- validate` on the tree as
  found: the full circulation battery, every acute respiratory
  arm, and the first Milestone 53 chronic arm (five-day
  hypoventilation, renal compensation live — PaCO2 82.19,
  bicarbonate 40.35, renal compensation state 12.24, pH 7.31,
  effective P50 28.91, every gated line PASS) all passed in this
  session's run, with only the two long-standing disclosed
  Milestone 18 SOFT lines (systolic band and heart-rate band at
  −1,500 mL; reported, not gating, by design) standing. The
  remaining three chronic A/B arms are multi-day simulations
  (~17 CPU-minutes each on an idle core) and were still executing
  at this dossier's writing, zero failures observed, under a
  heavily shared VM; their completion on this identical tree
  state is already recorded by Milestone 53's own dossier
  (validate ALL HARD GATES PASS, run twice byte-identical), and
  the detached completion run's log persists at
  `~/workspace/m54-scratch/phys-validate-full.log`. The engine
  invocations `case_check.py` itself makes (resting runs for the
  Case #1/#3/#6 link assertions) all passed inside the 11,884
  above. No physiology file was touched by this milestone.

## 10. Honest limits

- **Expert-review gate UNMET**, as for every case in this module:
  no named independent expert reviewers exist; the case ships as
  `dual-sourced-draft`, formative-only, no composite score. The
  review block records this verbatim and the checker asserts it.
- **The exclusion is the pathway's, not the board's.** The
  workbench's 0.0099 is a renormalised weight driven by one
  pooled-pair LR−; the case states that the exclusion rests on
  the ESC pathway combination (PE-unlikely + below the
  age-adjusted cutoff), whose empirical warrant is ADJUST-PE's
  0.3% band rate (C38) — and that the pooled-pair LR− (0.0732) is
  more favourable to exclusion than Stein 2004's tabulated 0.13,
  which is named beside it rather than hidden.
- **The rivals are excluded by conjunction, not by board
  rule-out.** Only PE crosses the workbench's rule-out line. ACS,
  pneumonia and pneumothorax are retired by stated conjunctions
  (normal ECG + troponin 6 + pain reproduced exactly on
  palpation, with the 3–6% figure disclosed; afebrile + clear
  chest + normal WBC/CRP; symmetric air entry + SpO₂ 98% +
  pleuritic-but-localized pain), and the adjudication says that
  is what they are. The checker asserts no other hypothesis is
  board-retired, so the record cannot quietly upgrade them.
- **PERC's precondition is operationalised, not measured.** "Met"
  means the workbench's own stage-1 PE weight (0.12) sits inside
  Kline's < 15% envelope; a real clinician's gestalt is not a
  board weight, and the block note says the mapping is the
  module's standing operationalisation (Case #6 precedent).
- **Priors remain verify-flagged authoring judgments**, shaped by
  the consulted sources' populations, presented as no more than
  that — as in all seven cases.
- **The nodule's risk category** is carried as the patient's
  stated history (light ex-smoker, no family history recorded in
  the case data) against C48's low-risk definition; the
  disposition orders the 6–12 month CT that both risk categories
  share for a 7 mm solid nodule and words the 18–24 month look as
  "consider", as the guideline does.
- The case is an authored teaching fiction. It is not a clinical
  device, not a diagnostic instrument, and not guidance for any
  real patient (master plan §8).

## 11. Files in this batch

- `cases/case.pe-ruleout.007.json` (new)
- `cases/attempts/attempt.case-pe-ruleout-007.model-learner.json`
  (new)
- `cases/debriefs/debrief.case-pe-ruleout-007.model-learner.json`
  (new; generated by `tools/case_run.py`)
- `cases/parameters.json` (extended: C48–C51, one LR derivation,
  C10/C11 Milestone 54 addenda, milestone marker 54)
- `tools/case_check.py` (`profile_case7` + wiring + docstring)
- `cases/README.md` (seventh case documented)
- `milestones/MILESTONE-54.md` (this dossier)

No physiology files touched (Milestone 53 built in parallel; the
tree was taken as found and the physiology validation run against
it as found). No README.md at the project root touched — that
reconciliation is Milestone 55. Nothing uploaded.

## 12. Next steps

- **M55 — README reconciliation** (queued): the held root README
  and its `readme_check` failures, now also carrying a seventh
  case and an eighth physiology state to describe.
- The case library stands at seven of the plan's twelve (P7
  target); the remaining slots are unassigned. Candidates the
  dossiers have named along the way: the COPD chronic-hypercapnia
  case (Milestone 53's named next step, once a case may assert the
  chronic-compensation surface), and a metabolic acid–base case.
- The expert-review gate remains the module's standing unmet gate
  for all seven cases and all five Theatre procedures.
