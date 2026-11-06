# cases/ — the Case Workbench module (Milestones 20 + 22 + 29)

Diagnosis practiced as explicit reasoning (design/07): a staged
presentation, a differential board the learner must commit numbers
to, tests with cost and information value, guideline criteria
evaluated mechanically from the staged evidence, and a PEARLS
debrief scored by stated rules.

## Rules of this folder

- **Synthetic cases only.** Every patient here is an authored
  fiction for teaching. No real patient data exists in this module
  or anywhere in ANATOMICA (education-only scope, master plan §8).
- **Facts are cited; fiction is labelled.** Clinical facts (criteria,
  likelihood ratios, reference ranges, test characteristics) trace
  to the sources registered in `parameters.json` (C1–C22), consulted
  in-session. The patient's particulars are *case data* and are
  labelled as such wherever they appear. Anything that could not be
  sourced carries a verify flag — never a quietly invented value.
- **No SNOMED CT, ever** (design/07): excluded from the public
  repository entirely. Conditions are coded in Mondo (CC BY 4.0);
  phenotypes in HPO, layered beside the data and never altered.
  LOINC is fenced into a separately-licensed data pack that is not
  in this repository, so labs carry local codes, including in the
  FHIR export.
- **Three individuals, never conflated.** A case's synthetic patient,
  an imaging series' research subject (Milestone 19), and the atlas
  Body Model subject are different people. A case may link an
  imaging series for anatomical localisation; it may never present
  that series as showing the case's pathology. Each case's
  `imaging_link.honesty_block` states this in full.
- **The engine honesty rule.** Design/07 specifies that the patient
  is a physiology-engine state. Where the engine has no state for a
  case's pathology (Milestone 20: no inflammatory/biliary
  perturbation exists), the case links the engine at the level that
  is true — here, the validated resting baseline — and states the
  gap in its `physiology_link`, rather than dressing authored vitals
  as simulation output.
- **Review gate.** A case counts as library content only with ≥2
  named independent expert reviewers (design/07 verification gates).
  Until then its status is `dual-sourced-draft`, its scores are
  formative-only, and its review block records the gate as UNMET.
  Reviewers are never invented to fill the block.

## Contents

- `parameters.json` — source register (C1–C22), the workbench's
  scoring-rule constants (all flagged project conventions), and the
  likelihood-ratio derivations. Extended at Milestone 22 with C14
  (WSES bile-duct-injury guidelines), C15 (MRCP test characteristics),
  and C16 (this project's own computed outputs — the loop source).
  Extended at Milestone 29 with C17 (Alvarado 1986), C18 (AIR score,
  Andersson & Andersson 2008), C19 (appendicitis diagnostic-accuracy
  review — the Wagner LR lineage and the Kinner CT accuracy pair),
  C20 (WSES Jerusalem 2020), C21 (urinary hCG test characteristics),
  and C22 (project outputs: the appendicectomy procedure, the Body
  Model appendix records, the s0778 label set).
- `case.ruq-pain.001.json` — the first worked case: acute calculous
  cholecystitis as a staged RUQ-pain presentation, 4 stages, 29
  findings, 9 labs, 8 orderable tests, 7 hypotheses, mechanical
  TG18/Atlanta adjudication, Theatre handoff to `proc.chole.lap`.
- `case.post-op-jaundice.002.json` — the loop case (Milestone 22):
  case 1's patient on postoperative day 4 after the operation that
  Theatre trace-02 failed. 4 stages, 25 findings, 7 labs, 1
  measurement, 6 orderable tests, 6 hypotheses. Its operative-history
  evidence is the shipped trace-02 debrief itself: the case carries
  the debrief's SHA-256 and the fields it relies on, and the checker
  re-reads that file and compares every field — the loop is verified
  data, not narrative. The Strasberg–Bismuth classification (E1/I)
  is computed by a declared classification block from the staged
  findings, including a measured 25 mm stump; TG18 cholangitis is
  evaluated mechanically and is *not suspected* at every stage
  (groups B and C met, group A unmet) while remaining the case's
  armed surveillance risk. No physiology link is declared: the
  engine has no biliary state, and the case says so rather than
  linking decoratively.
- `case.appendicitis.003.json` — the score-disagreement case
  (Milestone 29): migratory periumbilical-to-RLQ pain in a
  26-year-old woman, against a genuinely contested gynaecological
  differential. 4 stages, 25 findings, 3 labs, 2 measurements,
  6 orderable tests, 8 hypotheses. Two published scores are
  mechanically evaluated from the findings by the machinery's
  `score` block kind (new at this milestone): the Alvarado score
  totals 10/10 (very probable) while the AIR score totals 6/12
  (intermediate probability) — the adjudication derives the pathway
  from the disagreement (AIR's calibration + WSES guidance → CT as
  adjudicator), and the urine pregnancy test retires the ectopic
  hypothesis at stage 2 with a single-study LR labelled as such.
  Its imaging link records an absence: the s0778 label set has NO
  appendix label, while the Body Model HAS an appendix record —
  the link is localisation by the colon label only. Disposition
  hands off to Theatre `proc.appy.lap` in its standard
  configuration, with the branch consistency (uncomplicated,
  standard position) carried by recorded findings.
- `attempts/` — learner attempts (boards + orders per stage). Case
  2's model learner is deliberately imperfect in one documented way:
  it anchors on a retained CBD stone (ERCP ordered as therapy at
  stage 2, before MRCP) and still holds the stone at 0.25 at stage 4,
  after the workbench rules it out — one scored anchoring event.
  Case 3's model learner anchors on ectopic pregnancy at stage 2 —
  holding it at 0.15 at the very stage the negative pregnancy test
  retires it — also exactly one scored event.
- `debriefs/` — generated by `tools/case_run.py` (one generic runner
  for every case since Milestone 22); independently recomputed by
  `tools/case_check.py` (parameterised over all cases, with per-case
  profile sections; 5,145 checks at Milestone 29).
- `fhir/` — FHIR-shaped interchange export of the case (design/07);
  the case JSON is the source of truth and the checker fails the
  build if the export disagrees with it.
