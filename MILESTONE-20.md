# Milestone 20 — Case Workbench v1: the fifth module, one case end to end

**State: built and verified locally. Not uploaded (per-item approval rule).**

Milestones 16–19 gave ANATOMICA a body, an operation, a validated
physiology, and an image. This milestone adds the module the
commission named alongside them — the case/hypothesis workbench of
design/07 — and proves it the way the other modules were proved:
one fully worked case, played from presentation to disposition,
with every clinical fact cited to a source consulted in-session,
every score computed by stated rules, and an independent checker
recomputing all of it. Everything lives in `cases/`, with the
runner at `tools/case_run.py` and the checker at
`tools/case_check.py`.

## 1. The case model (`cases/`)

Per design/07's format, extended where the design's own mechanics
require it:

- **Case** (`cases/case.ruq-pain.001.json`): patient block, staged
  presentation (4 stages), findings (29), labs (9) with units and
  cited reference ranges, orderable tests (8) each carrying cost
  and time (design/07: *tests with real cost and information
  value*), a hypothesis space (7: six named conditions + a declared
  residual), guideline criteria blocks, a mechanical adjudication,
  and module links (Body Model records, the Milestone 19 imaging
  series, the Milestone 18 physiology state, the Milestone 17
  Theatre procedure).
- **Hypothesis space**: every named hypothesis is a sourced record
  — Mondo identity (all verified in-session against the EBI
  Ontology Lookup Service, source C10), defining features,
  discriminating findings by id and direction, Body Model record
  references that the checker resolves in the real data files, and
  a prior with an explicit status (below).
- **Workbench state model**: the board is a probability
  distribution over the hypotheses, updated stage by stage.
  Updates use *only* likelihood ratios cited in-session
  (Trowbridge's JAMA Rational Clinical Examination for the exam
  findings, C3; Kiewiet's Radiology meta-analysis for the
  ultrasound composite, C4 — its LR+ of 4.7647 computed from the
  published sensitivity/specificity, derivation shown; the AAFP
  evidence review for lipase, C6), multiplied onto the declared
  priors under a declared naive-independence convention. Everything
  the literature does not quantify acts through the guideline
  criteria blocks instead — TG18 for cholecystitis (C1) and
  cholangitis (C2), revised Atlanta for pancreatitis (C5) — which
  the runner evaluates mechanically from the staged evidence,
  item by item, stage by stage.
- **Attempt + debrief**: `cases/attempts/` holds a model-learner
  attempt (per-stage boards and orders, the worked example in the
  same role as Milestone 17's shipped traces); `tools/case_run.py`
  computes the workbench board, the criteria evaluations, and all
  scores, and emits a PEARLS-structured debrief (design/07 step 6)
  to `cases/debriefs/`. `cases/fhir/` holds a FHIR-shaped
  interchange export (Patient, Mondo-coded Condition, nine
  Observations, the ultrasound DiagnosticReport, and the Theatre
  handoff as a ServiceRequest) — hand-authored, and the checker
  fails the build if it disagrees with the case file on any value.
  Labs carry local codes: design/07 fences LOINC into a
  separately-licensed pack that is not in this repository, and
  SNOMED CT appears nowhere, as the design requires.

## 2. The worked case — acute cholecystitis, stage by stage

A synthetic 54-year-old woman (the case declares itself synthetic
in its first block; no real patient data exists in this module):
8 hours of post-prandial RUQ pain radiating to the right scapula,
pain followed by vomiting, fever 38.4 °C, RUQ tenderness, Murphy's
sign positive, no jaundice, chest clear, no peritonism.

| Stage | Reveal | TG18 (C1) | Workbench board (top) | Learner board (top) | Brier learner / workbench |
|---|---|---|---|---|---|
| 1 | history, vitals, exam | suspected (A+B) | cholecystitis 0.700 | cholecystitis 0.40 | 0.4550 / 0.1073 |
| 2 | CBC, CRP, LFTs, lipase, ECG, troponin (+ amylase) | suspected (A+B) | cholecystitis 0.734 | cholecystitis 0.50 | 0.3336 / 0.0872 |
| 3 | RUQ ultrasound | **definite (A+B+C)** | cholecystitis 0.929 | cholecystitis 0.70 | 0.1184 / 0.0062 |
| 4 | adjudication, disposition | definite, **Grade I** | 0.929 | commits 0.85 | 0.0276 / 0.0062 |

The evidence mechanics, exactly as computed:

- **Stage 1** carries the only two quantified exam findings:
  pain-then-emesis (LR+ 2.5, C3 — *single-study*, flagged wherever
  used) and Murphy's sign (LR+ 2.8, C3 — 95% CI 0.8–8.6, includes
  1.0, and the case quotes C3's own conclusion that no single
  finding rules cholecystitis in or out). RUQ tenderness is
  deliberately *unquantified*: C3 publishes only its negative LR.
- **Stage 2** is where the rivals fall. Lipase 92 U/L (reference
  0–160, C9) triggers C6's LR− 0.03 for pancreatitis, which alone
  carries pancreatitis across the workbench rule-out line
  (0.048 → 0.0015); Atlanta independently reads 0 of 3. The
  cholestasis screen (bilirubin 0.9 mg/dL, ALP/ALT/AST inside
  reference) leaves TG18 cholangitis group B unmet.
- **Stage 3**'s ultrasound composite (stones, 6 mm wall,
  pericholecystic fluid, sonographic Murphy) applies C4's computed
  LR+ 4.7647, completes TG18 group C → **definite**, and leaves
  cholangitis unmet on group C as well (5 mm duct, no dilatation)
  — its workbench posterior crosses the rule-out line (0.0111).
  Peptic ulcer disease ends at 0.0201, a hair *above* the line;
  the adjudication excludes it clinically (no peritonism, imaged
  alternative) and says that is what happened, rather than letting
  the number pretend to have done it.
- **Severity (C1)**: Grade I. All four Grade II items are
  mechanically false (WBC 14.2k ≤ 18k; no mass; 8 h ≤ 72 h; no
  marked local inflammation). Of the Grade III items, three are
  recorded **not-assessed** — no PaO₂/FiO₂, no creatinine, no INR
  exist in the case's data — rather than assumed negative. The
  grade is stated with those items open.

**Scoring** (components only — design/07 defines no weights, so
none were invented; the checker asserts no composite exists):

- *Calibration of ranking*: per-stage Brier scores for both boards
  (table above) plus the true diagnosis's rank (1 on both boards
  at every stage) and its probability trajectory (learner
  0.40 → 0.50 → 0.70 → 0.85; workbench 0.700 → 0.734 → 0.929).
- *Anchoring*: one event, by the declared rule — at stage 3 the
  learner still assigns cholangitis 0.15 after the workbench has
  ruled it out. The attempt file states the learner's reasoning
  (fever + pain read as Charcot's triad); the debrief answers it
  with C2's numbers (triad sensitivity 26.4% in the derivation
  cohort) and design/07's consider-the-opposite prompt.
- *Discriminating-evidence credit*: of 8 orders — **discriminating
  2** (lipase: moves pancreatitis across the rule-out line;
  ultrasound: largest posterior move, +0.195, and the TG18 group C
  test), **criteria-completing 3** (CBC → TG18 item B3; CRP → B2;
  LFT panel → cholangitis B1/B2 settled), **safety-net 2** (ECG +
  troponin against the must-not-miss cardiac hypothesis),
  **non-contributory 1** (amylase beside lipase — C6's Choosing
  Wisely point, kept in the attempt deliberately as teaching
  content). Resource tally: 265 minutes, 20 cost units — both
  flagged verify (case-author accounting placeholders; design/07
  requires tests to carry cost/time, and no prices were consulted).

**Disposition and handoff.** Adjudicated diagnosis: acute
calculous cholecystitis, MONDO:0043994, HPO phenotypes
HP:0002027/1945/2018/2013/1974 with jaundice (HP:0000952)
recorded as an explicit *absence*. Management per C1's Grade I
pathway: early laparoscopic cholecystectomy → **Theatre procedure
`proc.chole.lap`** (Milestone 17), whose structures register
resolves the same organ (`organ.gallbladder`) this case is built
around — the case→Theatre loop of design/07 and master plan §7,
closed. The guideline's CCI/ASA conditions are recorded as not
assessed by the case, in those words.

## 3. The module links — and their honesty blocks

- **Imaging (Milestone 19).** The case links series s0778 for
  *anatomical localisation only*: gallbladder label 15, files
  195–218 (0-based) = DICOM instances 196–219, max cross-section
  file 212 / instance 213 (186 voxels), 2,720 voxels = 9.18 mL,
  HU median 34 / mean 35.66 (crosswalk values) — every number
  recounted by the checker from the shipped bins. The case's
  `imaging_link.honesty_block` states, and the milestone repeats:
  **the s0778 subject is a different individual from the synthetic
  case patient** (and from the atlas subject); TotalSegmentator's
  label set contains no wall/stone/fluid label, so **the series
  does not and cannot show this case's pathology**, and no
  cholecystitis diagnosis is recorded for s0778. The case's stage-3
  imaging evidence is an authored *ultrasound* report — case data.
- **Physiology (Milestone 18).** The case invokes the engine's
  resting case as the patient's *pre-morbid baseline*: the
  checker re-runs `cargo run --release -- run resting` and matches
  the trace hash (`0x67102f7c27db053d`) and all seven recorded
  outputs (HR 63.2, BP 97.8/62.7, MAP 73.1, CO 4.21, SV 66.6,
  CVP 4.38). The gap is stated in the case, not papered over:
  design/07 specifies that the patient *is* an engine state, but
  the engine has **no inflammatory, febrile, or biliary
  perturbation** — there is no engine state for cholecystitis, so
  the presentation's fever and tachycardia are authored case data,
  flagged on their findings. The baseline is the level at which
  the link is true.
- **Theatre (Milestone 17)**: §2 above; the checker re-verifies
  the procedure id and its gallbladder register entry.

## 4. The flagged inventory (precision law)

Named here as the law requires — every number in this module that
is *not* a cited or computed fact:

- **Five of seven priors are verify-flagged case-author values**
  (cholangitis 0.10, pancreatitis 0.12, peptic ulcer 0.18,
  pneumonia 0.08, MI 0.07) plus the residual 0.20. Only the
  cholecystitis prior is calibrated, inside its cited range
  [0.13, 0.34] (C12). No consulted source publishes a full
  distribution over this differential, and the files say so.
- **Three workbench constants are project conventions**
  (rule-out 0.02, anchoring 0.10, discriminating Δ 0.10) —
  bookkeeping rules for scoring, declared in `parameters.json`,
  never presented as clinical quantities. The naive-product LR
  combination rule is likewise declared a convention, with its
  independence caveat written into the parameter record.
- **Test times and cost units** (16 values) are verify-flagged
  accounting placeholders.
- **Unasserted rather than invented**: the troponin numeric range
  (assay-specific; the result is recorded against the assay's
  99th-percentile limit without a number), the amylase reference
  range, the general platelet reference range (the value is
  classified only against C1's Grade III threshold), a
  gallbladder-wall thickness cut-off (the case reports its
  authored report's characterisation instead), CCI/ASA for the
  TG18 flowchart, and two criteria systems never consulted
  (peptic ulcer, pneumonia — their hypotheses carry
  `criteria_note` gaps instead of recalled criteria).

## 5. Verification (all run this session)

- `python3 tools/case_run.py` — computes the boards, criteria,
  and scores above; writes the debrief.
- `python3 tools/case_check.py` — **373 checks, 0 failures**:
  parameter and ontology discipline; 40+ Body Model record
  references resolved in the real files; stage discipline
  (no evidence before its stage, order yields landing exactly one
  stage after placement); laboratory arithmetic against every
  cited range and threshold; **full independent recomputation** of
  boards, Briers, ranks, rule-outs, the anchoring event, all
  eight order classifications, the resource tally, the per-stage
  TG18/Atlanta statuses, and the severity grade, compared against
  the shipped debrief field by field; the imaging voxel recount
  (2,720 voxels, slices 195–218, max file 212) and z-arithmetic
  against `series.json`; the physiology engine re-run (hash +
  outputs); the theatre register re-verification; the FHIR
  export compared value-by-value; governance gates (below).

## 6. Review gate — UNMET, reported not satisfied

Design/07's verification gates require a review block (≥2
reviewers) before a case counts as library content; design/10
applies the same discipline project-wide. **No reviewers exist
for this project.** The case records the gate verbatim as UNMET
with an empty reviewer list; content status is
`dual-sourced-draft`, validity `formative-only`, and the
negative-training audit has not been performed — exactly as
Milestone 17 recorded for the procedure.

## 7. What is NOT real

- **One case.** Calibration — design/07's headline metric — is a
  property of a case *series* (a calibration curve and a Brier
  trend across cases). This milestone ships the machinery and one
  case's four staged scores; it does not and cannot claim a
  calibrated workbench. The debrief says so in its summary.
- **No case-builder UI, no shell integration.** Cases are files,
  a runner, and a checker. The workbench as an interactive
  surface in the web/native shells — board editing, staged reveal
  in the UI, the atlas/imaging panels opening from a case — is
  later work, now possible in principle because every link target
  resolves.
- **No free-form case authoring.** The case was authored by hand
  to the model; design/07's educator builder (set ground truth on
  the engine, stage, attach, preview, publish through the same
  validators) is unbuilt.
- **The patient is not an engine state** beyond the baseline
  (§3): no inflammatory/biliary perturbation exists, so in-case
  physiology does not evolve and delay has no modelled
  consequences yet — design/07's engine-clock mechanic is
  specified but unimplemented.
- **Two exclusions are clinical, not imaged**: pneumonia and
  perforated ulcer were excluded on examination findings; no
  chest imaging was obtained, and the adjudication records that
  residual gap instead of closing it on paper.
- **Priors for five hypotheses are placeholders** (§4) until a
  sourced RUQ-pain distribution is consulted; OD-07.1 (GBD base
  rates) and OD-07.2 (learner-data privacy) remain open decisions,
  untouched here.

## 8. Sources consulted in-session

Full register in `cases/parameters.json` (C1–C13): C1 Yokoe 2018
(TG18 cholecystitis); C2 Kiriyama 2018 (TG18 cholangitis); C3
Trowbridge, JAMA 2003 (Rational Clinical Examination); C4 Kiewiet,
Radiology 2012; C5 Banks 2013 (revised Atlanta); C6 Oppenlander,
Am Fam Physician 2022; C7 MedlinePlus WBC; C8 MedlinePlus liver
function tests + tabulated example ranges; C9 LA Care pancreatitis
validation guideline (lipase range); C10 Mondo via EBI OLS
(7 classes verified); C11 HPO via EBI OLS (8 classes verified);
C12 Mills AJR 2020 + Ali PBMJ 2022 (RUQ-pain cholecystitis
proportions); C13 project module outputs (Milestones 11/17/18/19).

## 9. Next steps

1. **The second case, from the loop design/07 names**: the
   Theatre's trace-02 bile-duct injury returns as a case (post-op
   jaundice/pain after cholecystectomy) — the first
   complication-generated case stub, exercising cholangitis from
   the other side.
2. **Case series + calibration tracking**: enough cases (the P7
   target is 12) for the per-learner calibration curve and Brier
   trend to exist; persistent local learner state (OD-07.2's
   local-only default).
3. **An inflammatory/biliary engine perturbation** (with
   Milestones 17/18's named biliary compartment), so a case
   patient can *be* an engine state and delay can carry modelled
   consequences.
4. **Shell integration**: the workbench surface over the atlas,
   imaging, and theatre links this case already declares.
5. External dependency, not schedulable from here: named expert
   reviewers for the review gate; OD-07.1's base-rate decision
   would retire §4's flagged priors.
