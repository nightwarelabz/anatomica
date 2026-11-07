# Milestone 48 — Case #6: acute dyspnoea (the first cardiopulmonary case)

Case Workbench case #6 (`case.acute-dyspnea.006`): a 71-year-old
woman, twelve days after a left total knee arthroplasty, presents
with six hours of acute dyspnoea and right pleuritic chest pain.
The adjudicated diagnosis is acute bilateral pulmonary embolism,
ESC 2019 intermediate-high risk. The case is the workbench's first
cardiopulmonary case and its most heavily instrumented: five
declared criteria blocks (Wells, PERC, CURB-65, an A–a
classification, and the ESC severity classification), four
likelihood ratios, a physiology link that records the Milestone 47
respiratory resting readout beside the pinned circulation hash,
and an imaging link bounded to anatomical localisation. Local
build only; nothing uploaded.

## 1. Design rationale

Cases #1–#5 were abdominal, post-operative biliary, and peripheral
nerve localization problems. The brief for #6 was a cardiopulmonary
case whose PE arm is *mechanically serious*: not a story about a
clot, but the actual guideline machinery — a Wells score evaluated
from the case's own atoms at every stage, PERC evaluated with its
use condition stated, a D-dimer weighed at its published weakness
with the age-adjusted cutoff on record, and CTPA as the decisive
test whose classification follows the machinery's rules. Three
design commitments follow from that brief:

1. **Every number that moves the board or a block comes from a
   source consulted in-session** (C35–C47, §4), or is case data
   labelled as such, or is a verify-flagged authoring choice
   (the priors). Where a consulted source family could not be
   used, the design adapted rather than citing from memory —
   StatPearls was unreachable this session (as in M39–M44) and is
   cited for nothing.
2. **The instruments are blocks, not prose.** Wells, PERC and
   CURB-65 are `score` blocks; the gas pattern and the ESC class
   are `classification` blocks. The runner evaluates them from
   atoms at every stage, the checker re-evaluates them with an
   independent implementation, and `profile_case6` pins their
   stage-by-stage states. Partial scores stay partial and visible:
   the stage-1 Wells is 3.0 with its highest-weight item *not yet
   assessed*, and the case is built so that state matters (§5).
3. **The case's spine is a blood gas the engine can check.** The
   patient's ABG is authored case data, but it is authored to
   satisfy the Milestone 47 module's own equations exactly, and
   the checker re-derives the A–a gradient from the case's numbers
   with the module's alveolar gas equation (§7). The physiology
   link records both resting readouts and states plainly that the
   engine has no thromboembolic state (§8).

## 2. The frozen hypothesis set, with grounds

Eight hypotheses. The set is what the consulted sources' shared
differential for acute dyspnoea in this presentation supports;
priors are verify-flagged authoring choices (no consulted source
gives base rates for this staged presentation in a defined
population), recorded as such in every prior's note.

| Hypothesis | Prior | Mondo | Grounds |
|---|---|---|---|
| hyp.pulmonary-embolism | 0.36 | MONDO:0005279 | The presentation's engine: major joint surgery 12 days prior + sustained immobility (C35, C41 frame the whole diagnostic pathway around this story). |
| hyp.pneumonia | 0.15 | MONDO:0005249 (note: no CAP class exists) | A leading cause of acute dyspnoea with tachypnoea at 71; CURB-65 (C42) is carried for it. OLS: "community-acquired pneumonia" returned numFound 0 — coded to the parent class with the refusal recorded. |
| hyp.other-unspecified (residual) | 0.17 | null (by design) | The module's standing residual; retires arithmetically. |
| hyp.heart-failure | 0.12 | MONDO:0005252 (note: no human acute class) | Age, hypertension, bilateral ankle oedema on record at stage 1. OLS: "acute heart failure" returned only non-human-animal classes — coded to the generic class, noted. |
| hyp.acute-coronary-syndrome | 0.08 | MONDO:0005542 | Chest pain + dyspnoea at 71 is a must-not-miss; the case carries a declared ECG/troponin safety-net pair for it. |
| hyp.pneumothorax | 0.05 | MONDO:0002076 | Pleuritic pain + acute dyspnoea; retired by the stage-2 film. |
| hyp.copd-exacerbation | 0.04 | MONDO:0005002 | In the standard dyspnoea differential; the record argues against it from stage 1 (never-smoker, no history). |
| hyp.asthma-exacerbation | 0.03 | MONDO:0004979 | Carried for completeness; no history at any age. First retirement (stage 2, by renormalisation alone). |

## 3. The case in numbers

37 findings, 10 labs, 10 measurements, 10 orderable tests, 5
criteria blocks, 4 stages. Findings stage 1: 23 (history, vitals,
examination — including the examined absences the differential
turns on: no orthopnoea, no haemoptysis, no prior VTE, no
malignancy, no oestrogen use, no chronic cardiopulmonary disease,
never-smoker, JVP not raised, no crackles, no wheeze, no
confusion); stage 2: 11 (ECG pair, troponin, BNP, D-dimer, gas,
the measured calf, four film findings); stage 3: 3 (CTPA pair, the
B-line-negative ultrasound). Labs (all stage 2, each with a cited
reference range): PaO2 62, PaCO2 30, pH 7.49, HCO3 22 (C44); BNP
385 pg/mL (ref 0–100, C36); D-dimer 3,850 µg/L FEU (ref 0–500,
C38); troponin 34 ng/L (ref 0–14, C41); WBC 9.6 (C7); CRP 18 mg/L
(C45); urea 6.2 mmol/L (C47).

## 4. Per-value source table (C35–C47, all consulted 2026-11-06)

| Source | What it grounds in this case |
|---|---|
| C35 Wells 2000 (+ Christopher 2006 two-tier) | The Wells block: item set and points (DVT signs 3; PE-top-diagnosis 3 — *excluded*, §5; HR >100 1.5; immobilisation ≥3 d / surgery ≤4 wk 1.5; prior VTE 1.5; haemoptysis 1; malignancy 1), three-tier bands, two-tier cut ≤4 / >4. |
| C36 Maisel 2002 (Breathing Not Properly) | BNP reference cutoff 100 pg/mL; sensitivity 0.90 / specificity 0.76 → LR+ 3.75 (the consulted review table's tabulated 3.75 agrees). |
| C37 Kline 2004/2008 (PERC) | The PERC block: 8 criteria, the all-absent negative definition, and the use condition — gestalt pretest probability < 15% — stated unmet in this case. |
| C38 Righini 2014 (ADJUST-PE) | D-dimer fixed cutoff 500 µg/L FEU; age-adjusted cutoff age × 10 for age > 50 → 710 µg/L for this patient; the case's 3,850 is positive against both. |
| C39 Patel 2020 (+ Stein 2004) | Pooled D-dimer sensitivity 0.97 / specificity 0.41 → LR+ 1.6441; Stein's "positive LRs in the general range 1.5–2.5" corroborates. The pooled CTPA pair (0.94/0.98) was consulted and *not* used (§6). |
| C40 Stein 2006 (PIOPED II) | CTPA sensitivity 0.83 (150/181) / specificity 0.96 (567/592) → LR+ 20.75 — the conservative primary-study pair the case weighs. |
| C41 ESC/ERS 2019 (Konstantinides) | The diagnostic algorithm; the severity table and sPESI items behind `esc_pe_risk`; RV/LV ≥ 1.0 as the CT RV-dysfunction threshold; troponin threshold 14; and the anchor's mechanism — BNP elevated in ~50% of acute PE via RV pressure overload. |
| C42 Lim 2003 (CURB-65) | The CURB-65 block: 5 items, bands 0–1 / 2 / 3–5. Grades severity only. |
| C43 CJEM systematic review (lung US) | B-lines for ADHF: pooled sensitivity 0.896 / specificity 0.884 → LR− 0.1176 (published pooled LR− 0.13 recorded in the derivation). |
| C44 MedlinePlus blood gases (+ BMJ 1998) | ABG reference ranges: PaO2 75–100, PaCO2 35–45, pH 7.35–7.45, HCO3 22–26. |
| C45 Medscape (Pagana) CRP | CRP reference < 10 mg/L. |
| C46 Mellemgaard 1966 | Age-expected A–a gradient = 2.5 + 0.21 × age → 17.41 mmHg at 71 (the age/4 + 4 alternative was consulted and is recorded in the block note). |
| C47 MedlinePlus BUN | Urea reference 2.5–7.1 mmol/L (the CURB-65 item's lab). |

Likelihood-ratio derivations are registered in
`cases/parameters.json` with their worked arithmetic, as the
machinery requires; §6 states each.

## 5. Criteria arithmetic, stage by stage

**Wells (`wells_score`, max 12.5).** Six objective items only. The
seventh — "PE as likely as or more likely than an alternative
diagnosis" (+3) — is a clinician-judgment item, and a
self-contained case cannot score it without circularity: its value
would be the author's verdict wearing the score's clothing. It is
excluded, and the block note shows the sensitivity instead
(6.0 scored; 9.0 with the item — three-tier moderate at its ceiling
vs high; the CTPA destination is identical on every reading).

- Stage 1 (partial): tachycardia 1.5 (HR 112 > 100) + surgery
  1.5 (arthroplasty 12 days ago, inside 4 weeks) = **3.0**, band
  "PE unlikely (two-tier)" — with `dvt_signs` *not assessed*: the
  calves had not been measured. Prior VTE, haemoptysis and
  malignancy items are assessed zeros (examined absences on
  record). The case keeps the partial flag visible because the
  stage-1 D-dimer order is placed in exactly this state — which is
  the one defensible reading of the ESC pathway here: on a partial
  score the patient *looks* PE-unlikely. The block, completed,
  disagrees — and the case's stage-2 note says the partial Wells
  is not a Wells.
- Stage 2 (complete): + DVT signs 3.0 (measured calf asymmetry
  2.5 cm with deep-vein tenderness, on the side *opposite* the
  operated knee) = **6.0**, "PE likely (two-tier)".

**PERC (`perc_rule`, max 8).** Counts criteria *present*
(age ≥ 50, HR ≥ 100, SpO2 < 95%, prior VTE, surgery ≤ 4 weeks,
haemoptysis, oestrogen use, unilateral leg swelling). Stage 1:
4 assessed-present with leg swelling unassessed → already PERC
positive. Stage 2: **5**. The block's note states the stronger
fact: PERC's use condition (gestalt < 15%, C37) was never met by
this post-operative, tachycardic, hypoxaemic patient — the rule
is evaluated so that its refusal is mechanical, and it refuses
twice over.

**CURB-65 (`curb65`, max 5).** Age ≥ 65 fires (1); confusion
absent; RR 26 < 30; BP 118/72 clears both thresholds; urea item
unassessed at stage 1, assessed 0 at stage 2 (6.2 ≤ 7.0). Total
**1**, low severity band, from stage 2. The block grades the
pneumonia hypothesis's severity *if true*; it never diagnoses,
and the adjudication records the pneumonia exclusion on the film,
the temperature and the white count instead.

**A–a classification (`aa_assessment`).** Inputs: hypoxaemia
(PaO2 < 80), widened gradient (measured A–a > 17.41), infiltrate
on film. Pending at stage 1 ("awaiting the arterial gas and the
chest film"). From stage 2: (true, true, false) →
**ventilation/perfusion mismatch**.

**ESC severity (`esc_pe_risk`).** Inputs: haemodynamic
instability (SBP < 90 — a stated proxy simplification of the
guideline's instability definition), sPESI ≥ 1 (any of age > 80,
HR ≥ 110, SBP < 100, SpO2 < 90, malignancy, chronic
cardiopulmonary disease), RV dysfunction (CTPA RV/LV ≥ 1.0),
troponin > 14 ng/L. Pending at stages 1–2 *by design* — the RV
input is unmeasured until the CTPA exists. Note the boundary the
case sits on deliberately: SpO2 is exactly 90%, which does **not**
fire the sPESI "< 90%" item; the sPESI point comes from HR 112.
From stage 3: stable + sPESI ≥ 1 + RV dysfunction + troponin
elevated → **intermediate-high**.

## 6. The four likelihood ratios

- `f.bnp-elevated` → HF, LR+ **3.75** = 0.90 / (1 − 0.76), C36.
  Honestly entered at full published weight — the anchor (§9)
  only means anything if the machinery itself moves.
- `f.ddimer-positive` → PE, LR+ **1.6441** = 0.97 / (1 − 0.41),
  C39. Deliberately **no LR− is registered**: in a patient 12 days
  after major joint surgery, a below-cutoff D-dimer was never
  going to be allowed to exclude PE, so the case does not pretend
  the assay has a usable negative direction here. The positive
  direction is weighed at its published weakness and described as
  such everywhere it appears.
- `f.ctpa-pe-positive` → PE, LR+ **20.75** = 0.83 / (1 − 0.96),
  C40 (PIOPED II). Two larger pairs were consulted — CTA+CTV
  (LR+ 18, smaller) and the pooled contemporary pair in C39
  (0.94/0.98, LR+ 47) — and the conservative primary-study figure
  was registered, with the choice recorded in the derivation.
- `f.lus-no-blines` → HF, LR− **0.1176** = (1 − 0.896) / 0.884,
  C43 (the review's published pooled LR− is 0.13; the
  pair-computed value is registered per this register's
  derivation discipline and sits inside its interval).

The troponin finding carries **no LR**: myocardial injury is not
infarction, no consulted source quantifies troponin for either
hypothesis in this differential, and its mechanical role is the
ESC block's marker input.

## 7. The A–a verification

The patient's gas (stage 2, room air): PaO2 62, PaCO2 30, pH 7.49,
HCO3 22. The checker verifies three consistencies from the case's
own numbers, using the Milestone 47 module's constants
(PB 760 mmHg, PH2O 47 mmHg, R 0.8, FiO2 0.21):

- Alveolar gas: PAO2 = 0.21 × (760 − 47) − PaCO2 × (0.21 +
  0.79/0.8) = 149.73 − 35.93 = **113.8 mmHg**; A–a = 113.8 − 62 =
  **51.8 mmHg** — exactly the recorded measurement the
  classification block consumes (tolerance 0.15).
- Henderson–Hasselbalch: 6.1 + log10(22 / (0.03 × 30)) = 7.488 →
  the recorded pH 7.49 (tolerance 0.01). The bicarbonate also sits
  on the engine's acute-buffering rule (PaCO2 −11.1 from the
  resting 41.1 → HCO3 ≈ 24 − 2.2 = 21.8 ≈ 22).
- Age-expected gradient (C46): 2.5 + 0.21 × 71 = **17.41 mmHg**;
  the patient's 51.8 is three times it, and six times the
  engine's resting gradient (9.3 mmHg) the physiology link
  records.

## 8. The two links, and their stated limits

**Physiology.** The link records the pinned circulation baseline
(trace hash `0x6369b10e9a71c872`, the same seven outputs as cases
#1/#3 — the checker asserts hash identity with case 1's link, so
the M47 module provably did not move the circulation chain) **and**,
for the first time in the module, the respiratory resting readout:
all 17 values, re-run and compared value-by-value by
`profile_case6` (the resting protocol prints no respiratory hash;
the state is pinned by its full readout, and the link says why).
The gap statement is explicit: the engine has **no thromboembolic
state** — no pulmonary vascular obstruction perturbation exists or
is claimed. The M47 module owns the equations this patient's gas
obeys; it does not simulate her. Her gases are authored case data,
arithmetic-verified (§7).

**Imaging.** A localisation link only, to s0778's
`pulmonary_artery` label (index 48), carrying both lateralised
Body Model records with the asymmetry stated (the TS label covers
trunk and both branches; the case's dominant lesion is
right-sided). The checker recounts the label from the shipped web
bins — files 302–343, 42 slices, 23,547 voxels, max cross-section
file 327 (DICOM instance 328) at 1,278 voxels — and re-verifies
the crosswalk HU statistics, bbox, z-arithmetic and volume
arithmetic (79.47 mL). The honesty block states the boundary in
the case itself: the shipped 104-label set contains **no embolus
or filling-defect label, no consolidation label, and no pleura or
pleural-effusion label** (asserted for both subjects by the
profile); the lungs *are* in the field (five lobes, both TAP
subjects), the embolus is not a label; the s0778 series is
segmentation anatomy, not angiography; the case's CTPA is an
authored encounter — case data. Three individuals (case patient,
s0778, atlas subject) are never conflated.

**No Theatre handoff.** The adjudicated management is medical
(monitored admission, anticoagulation on the ESC intermediate-high
strategy, rescue reperfusion on deterioration — agent and dose are
the treating service's, not authored). The Theatre holds exactly
four procedures, none treats PE, and none was authored here; the
case's management block states the absence (`theatre_note` +
`theatre_link_verified`, no `handoff` key), and the profile
asserts it — the M43 pattern, kept.

## 9. The anchoring event — result-installed

Exactly one, recomputed by the checker: **(stage 3,
hyp.heart-failure)** — the learner holds HF at 0.16 while the
workbench rules it out at 0.0041. Its shape is new to the module,
the third installation mechanism in the series: case #4's anchor
was installed by another clinician before the case began; case
#5's was self-installed from a true exposure history at stage 1.
This one is **installed mid-case, by a test result**. At stage 1
the learner's board is defensible (PE 0.22, HF 0.20). At stage 2
the BNP returns at 385 pg/mL — a true number, fed by two innocent
stage-1 exhibits (symmetric ankle oedema with immobility and
amlodipine on record) — and the learner converts a rising
differential into a diagnosis (HF 0.42, PE down to 0.18). The
workbench, applying the *same* BNP weight, keeps PE ahead
(0.3790 vs 0.2881) because it also weighs the D-dimer and cannot
un-measure the calf. The frame then survives a completed Wells
score of 6.0 and a CTPA showing bilateral emboli; it is released
only at the commit stage (0.05), a stage late. The closing
symmetry is the lesson the debrief teaches: the test that ends
the anchor is the learner's own lung ultrasound, ordered to
confirm pulmonary oedema, returning no B-lines (LR− 0.1176).
And the mechanism is in the cited guideline itself: BNP rises
with right-ventricular strain in PE (C41) — a peptide reports
ventricular strain, not ventricular identity.

## 10. Posterior trajectory and order classifications

Workbench board for the truth: **0.36 → 0.3790 → 0.9554 →
0.9554**. Stage 2 is the case in miniature: HF more than doubles
(0.12 → 0.2881) on the honestly weighed BNP, PE edges up on the
weak D-dimer, and PE still leads — the machinery models the
temptation and resists it for stated reasons. Rule-outs: asthma
at stage 2 (renormalisation alone; no finding addresses it —
recorded as such), every other rival at stage 3.

Order classifications (all ten, machinery-assigned, profile-pinned):
ECG **safety-net** (ACS); troponin **criteria-completing** — ordered
under a declared safety-net intent, it lands in the ESC block's
marker slot (the case's quiet second lesson: an order's declared
purpose and its mechanical effect are different facts, and the
debrief reports the mechanical one); ABG **criteria-completing**
(A–a inputs); BNP **discriminating** — it moves the lead by
0.1015, *away from the truth*; D-dimer **discriminating** (lead
changes HF → PE on the counterfactual board); bloods
**criteria-completing** (CURB-65 urea item); chest film
**criteria-completing** (A–a infiltrate input — its pneumothorax
exclusion is real but unquantified, as the test's note states);
examination battery **criteria-completing** (Wells DVT item +
PERC leg item); CTPA **discriminating** (0.5081 → 0.9554 on the
counterfactual); lung ultrasound **discriminating** (HF crosses
the rule-out line, 0.0340 → 0.0041). Tally: 215 min / 27 cost
units (verify-flagged accounting, as all cases).

## 11. Honest limits

- **Expert-review gate UNMET**, as for every case: no named
  independent expert reviewers exist for this project; the review
  block records the gate unmet with an empty reviewer list, the
  content status stays `dual-sourced-draft`, and scores are
  formative-only. Six cases are still not a calibration series —
  the case's validity block says so.
- **Priors are authoring choices**, verify-flagged in every
  prior's note; no consulted source grounds base rates for this
  staged presentation. The trajectory's shape is driven by the
  cited LRs; its starting point is declared fiction.
- **The Wells judgment item is excluded, not resolved.** A reader
  who believes the item should be scored should read the block
  note's sensitivity (9.0, three-tier high) — the pathway is
  unchanged, but the exclusion is a judgment call and is labelled
  one.
- **The pathway's other branch is not exercised.** This patient
  was always going to CTPA once the score completed. The
  PE-unlikely + negative-D-dimer exclusion pathway (ESC/C38) is
  on record in the sources and the D-dimer finding's note, but no
  stage of this case walks it; a case that does would need a
  different patient, not a different branch of this one.
- **Simplifications, stated where they sit:** SBP < 90 as the
  instability proxy (the ESC definition is broader); RV
  dysfunction read from the CTPA ratio alone; the sPESI chronic
  cardiopulmonary item read from the history finding. Each is
  named in its block.
- **StatPearls was unreachable** this session (as in M39–M44) and
  is cited for nothing; every field it might have grounded is
  grounded elsewhere or left to the sources above.
- The case is synthetic and educational; it is not a clinical
  device and adjudicates no real patient.

## 12. Verification matrix (this session)

- `tools/case_check.py`: **10,298 passed, 0 failed** — generic
  §1–§6 over all six cases plus `profile_case6` (blocks at every
  stage, A–a/Henderson–Hasselbalch recomputation, trajectory,
  single anchoring event, physiology link re-runs incl. the
  17-value respiratory readout, imaging recount from the shipped
  bins, ontology refusals, no-handoff assertions, debrief
  classifications and tally).
- Regression: cases #1–#5 case files, attempts and debriefs
  **byte-identical** to the pre-milestone SHA-256 baseline after
  regeneration; `parameters.json` differs only by the intended
  surgical extension (C35–C47 appended, C10/C11 addenda,
  4 derivations, milestone counter) — verified by diff (three
  changed lines, all insertions otherwise).
- `tools/theatre_check.py`: 463/0. Physiology
  `cargo run --release -- validate`: exit 0, respiratory section
  included, resting hash unchanged. Imaging
  `tools/imaging_toolkit_check.py`: PASS, 0 findings standing.
  All 18 remaining `tools/*_check.py`: exit 0.
- Native `anatomica verify`: 99 PASS / 0 FAIL data assertions;
  the GPU render stage cannot initialise on this VM (no Vulkan
  ICD) — the standing disclosed limitation, unchanged.

## 13. Files in this batch

- `cases/case.acute-dyspnea.006.json` — the case (new).
- `cases/attempts/attempt.case-acute-dyspnea-006.model-learner.json`
  — the authored attempt (new).
- `cases/debriefs/debrief.case-acute-dyspnea-006.model-learner.json`
  — generated by `tools/case_run.py` (new).
- `cases/parameters.json` — surgical extension: sources C35–C47,
  4 LR derivations, C10/C11 Milestone 48 addenda,
  `extended_at_milestone` 43 → 48.
- `tools/case_check.py` — `profile_case6` added and wired.
- `cases/README.md` — case-6 bullet, register range C1–C47,
  case-6 learner note, check count.
- `MILESTONE-48.md` — this dossier.

## 14. Next steps

- A validated thromboembolic perturbation for the physiology
  engine (dead-space state on the M47 machinery) would let a
  future PE case link a simulated patient instead of the resting
  baseline; until then the gap statement stands.
- A second cardiopulmonary case walking the PE-unlikely +
  D-dimer-negative exclusion pathway would exercise the branch
  this case records but does not walk.
- The expert-review gate remains the module's standing unmet
  gate; nothing here fills it in on paper.
