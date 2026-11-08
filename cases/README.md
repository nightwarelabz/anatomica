# cases/ — the Case Workbench module (Milestones 20 + 22 + 29 + 41 + 43 + 48 + 54 + 57 + 61)

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
  to the sources registered in `parameters.json` (C1–C70), consulted
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

- `parameters.json` — source register (C1–C70), the workbench's
  scoring-rule constants (all flagged project conventions), and the
  likelihood-ratio derivations. Extended at Milestone 22 with C14
  (WSES bile-duct-injury guidelines), C15 (MRCP test characteristics),
  and C16 (this project's own computed outputs — the loop source).
  Extended at Milestone 29 with C17 (Alvarado 1986), C18 (AIR score,
  Andersson & Andersson 2008), C19 (appendicitis diagnostic-accuracy
  review — the Wagner LR lineage and the Kinner CT accuracy pair),
  C20 (WSES Jerusalem 2020), C21 (urinary hCG test characteristics),
  and C22 (project outputs: the appendicectomy procedure, the Body
  Model appendix records, the s0778 label set). Extended at
  Milestone 41 with C23 (the Rational Clinical Examination for carpal
  tunnel syndrome), C24 (the AAOS 2024 carpal tunnel guideline), C25
  (the AANEM/AAN electrodiagnostic practice parameter), C26 (the
  CTS-6 evaluation tool), C27 (the Fowler ultrasound meta-analysis),
  C28 (project outputs: the M39 median-nerve record, the M35
  innervation pass, both imaging subjects' label sets), and C29
  (MedlinePlus HbA1c ranges). Extended at Milestone 43 with C30
  (project outputs: the M39 ulnar-nerve record, the M35 innervation
  pass, both imaging subjects' label sets), C31 (the AAEM
  electrodiagnostic practice parameter for ulnar neuropathy at the
  elbow), C32 (the Chang et al. ultrasound meta-analysis), C33
  (Novak et al. provocative testing, with the Physio-pedia Tinel
  evidence table), and C34 (the McGowan grading, as reproduced in
  the consulted classification summary); the C10/C11 ontology
  registers carry dated Milestone 43 addenda. Extended at
  Milestone 48 with C35 (the Wells score, Wells 2000, with the
  Christopher Study two-tier cut), C36 (Maisel 2002 — BNP test
  characteristics), C37 (the PERC rule, Kline 2004/2008, with its
  low-gestalt use condition), C38 (ADJUST-PE — the age-adjusted
  D-dimer cutoff), C39 (Patel 2020 — pooled D-dimer and CTPA
  accuracy), C40 (PIOPED II — the CTPA pair this case weighs),
  C41 (the ESC/ERS 2019 pulmonary embolism guideline), C42
  (CURB-65, Lim 2003), C43 (the lung-ultrasound systematic
  review), C44 (MedlinePlus arterial blood gas ranges), C45 (CRP
  reference), C46 (the Mellemgaard age-expected A–a gradient)
  and C47 (MedlinePlus urea range); the C10/C11 ontology
  registers carry dated Milestone 48 addenda, including two
  recorded refusals (no Mondo class for community-acquired
  pneumonia; no human class for acute heart failure).
  Extended at Milestone 54 with C48 (the Fleischner Society 2017
  incidental-nodule guideline), C49 (the six-ED CTPA over-testing
  cohort, Acad Radiol 2019), C50 (the 2021 AHA/ACC chest-pain
  guideline) and C51 (Proulx & Zryd 2009 — the costochondritis
  review the Mondo refusal turns on), one further LR derivation
  (the D-dimer negative direction, computed from the C39 pooled
  pair — deliberately not registered at Milestone 48, registered
  now because in case 7's patient it is the pathway's operative
  direction), and dated Milestone 54 addenda to the C10/C11
  registers, including a third recorded refusal: the only Mondo
  class the costochondritis search returns is Tietze syndrome
  (MONDO:0001858), defined by the swellings case 7's patient
  lacks — refused, and the truth carries Mondo null.
  Extended at Milestone 57 with C52 (the ATA statement on
  postoperative hypoparathyroidism — the definition, the PTH
  thresholds, the supplementation tiers and the calcitriol
  criterion), C53 (Fong & Khan's hypocalcemia review — the
  hypoparathyroid profile, the Box 2 investigation panel, the
  intravenous criteria and regimen), C54 (Cooper & Gittoes —
  the albumin correction and the 1.9 mmol/L urgency
  threshold), C55 (the NEJM appraisal of Chvostek's and
  Trousseau's signs), C56-C58 (the MedlinePlus PTH, magnesium
  and phosphorus ranges), C59 and C60 (the ECG sources — the
  ST-segment mechanism, the sex-specific QTc thresholds and
  the 500 ms risk band), C61 (the hyperventilation-syndrome
  case report — the mimic's physiology: the ionized calcium
  falls, the total does not) and C62 (the Theatre module's
  trace-30 debrief, this case's operative-history evidence),
  one further LR derivation (Trousseau's sign, LR+ 23.5
  computed at the conservative end of the C53/C55 pair —
  0.94 / 0.04 — with the post-thyroidectomy counterweight
  carried in the prose), and dated Milestone 57 addenda to
  the C10/C11 registers: MONDO:0001220 verified, the
  postoperative subclass refused (no such class exists), and
  two recorded rejections (MONDO:0002945 resolves to a
  basal-cell carcinoma class; HP:0003473 to fatigable
  weakness, not tetany).
  Extended at Milestone 61 with C63 (Blatchford 2000 — the
  Glasgow-Blatchford score's item table and its validation
  finding), C64 (Srygley 2012 — the Rational Clinical
  Examination for upper gastrointestinal bleeding: melenic
  stool on examination LR 25, the urea:creatinine ratio
  summary LR 7.5, and the severe-bleeding pair, tachycardia
  4.9 and hemoglobin below 8 at 4.5–6.2), C65 (Villanueva
  2013 — the restrictive transfusion threshold), C66 (the
  ESGE 2021 nonvariceal upper-GI hemorrhage guideline),
  C67/C68 (the MedlinePlus hemoglobin and creatinine ranges)
  and C69/C70 (the ACG ulcer-bleeding guidelines of 2012 and
  2021 — a second guideline voice, concordant with C66),
  FOUR further LR derivations, every one a computed
  reciprocal of a C64 figure (the Milestone 54 D-dimer
  pattern in a new register: reciprocals, because the
  consulted ratios price the upper source and the severity
  the anchor denies, and the machinery enters them against
  the hypotheses they retire), and dated Milestone 61
  addenda to the C10/C11 registers: five Mondo classes
  verified (duodenal ulcer, MONDO:0005412, at the head), a
  fourth recorded refusal (no Mondo class for a
  lower-gastrointestinal bleeding source — the hypothesis
  names a location, not a disease, and was not coded to
  diverticulitis), and a recorded rejection (HP:0002321
  resolves to vertigo, not this patient's presyncopal
  lightheadedness).
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
- `case.carpal-tunnel.004.json` — the localization case (Milestone
  41): eight months of nocturnal median-distribution paresthesias in
  a 47-year-old woman with type 2 diabetes, against the neck
  hypothesis another clinician installed before the case begins.
  4 stages, 24 findings, 1 lab, 3 measurements, 5 orderable tests,
  6 hypotheses. The CTS-6 score block (new instrument, same `score`
  machinery) totals 16.5/26 — positive at stage 2 — while the board
  honestly dips there (normal thumb abduction, LR 0.5, C23) before
  ultrasound (LR+ 5.8788 computed, C27) and the AANEM-protocol
  electrodiagnosis (LR+ 17.0 computed at the parameter's stated
  bounds, C25) localize the lesion to the wrist. Phalen and Tinel
  carry no board LR at all (C23 pools them at 1.3/1.4 — little or no
  diagnostic value); they act through the CTS-6 only. No imaging
  link is declared: both subjects' identical 104-label sets contain
  no nerve label of any kind, and both series are
  thorax-abdomen-pelvis studies — the wrist is not even in the field
  of view; an `imaging_assessment` block records the double absence
  instead. No physiology link (no peripheral-nerve engine state) —
  the absence stated, not fabricated. At Milestone 41 there was
  likewise no Theatre handoff, the Theatre then holding no carpal
  tunnel release; Milestone 42 authored `proc.carpal-release`, and
  the case now hands off to it in its standard (open) configuration,
  checker-verified — the endoscopic configuration is a named
  non-goal of that milestone. The case links the M39
  clinical record `major.median` and the M33 inventory median
  nerves, and records that the recurrent branch those nerves' thenar
  muscles name has no Body Model record (M35 pass: unresolved).
- `case.ulnar-neuropathy.005.json` — the second localization case
  (Milestone 43): six months of ulnar-distribution paresthesias in a
  58-year-old man whose lesion SITE is the question — cubital tunnel
  (elbow) against Guyon's canal (wrist), C8 radiculopathy,
  lower-trunk/medial-cord plexopathy and neurogenic thoracic outlet
  syndrome. 4 stages, 30 findings, 0 labs, 5 measurements,
  4 orderable tests, 6 hypotheses. The discriminating content is
  branch anatomy: dorsal ulnar cutaneous involvement (the branch
  leaves the nerve in the forearm — a wrist lesion spares it, the
  pattern the M39 record `major.ulnar` states verbatim) and forearm
  motor involvement exclude the wrist level without any likelihood
  ratio, because no consulted source quantifies them; the board is
  moved by Tinel's sign at the elbow (LR+ 35.0 computed, C33, with
  its healthy-control spectrum caveat stated), elbow ultrasound
  (LR+ 9.4444 computed at the meta-analysis's 10 mm² cutoff, C32)
  and the AAEM-parameter electrodiagnostic protocol (LR+ 7.4
  computed at the parameter's least favourable supported
  combination — a disclosed floor, C31): 0.22 → 0.9080 → 0.9894 →
  0.9986. The McGowan grade is mechanically evaluated by a
  `classification` block (pending at stage 1, grade II from stage 2)
  and grades severity only — it never localizes, and the case says
  so. No imaging link (both subjects' identical 104-label sets hold
  no nerve, ulnar or elbow label, and both TAP fields of view
  exclude elbow AND wrist; an `imaging_assessment` block records
  the double absence), no physiology link (case-2 precedent). At
  Milestone 43 there was likewise no Theatre handoff — the Theatre
  held no ulnar-nerve procedure, the absence was stated, and none
  was authored there; Milestone 44 authored
  `proc.ulnar-decompression`, and the case now hands off to it in
  its standard (in-situ) configuration, checker-verified — the
  transposition configuration is the operation's own stability-
  assessment decision, not the case's. Ontology:
  cubital tunnel syndrome has its own Mondo class (MONDO:0043982);
  the wrist hypothesis is coded to the generic ulnar neuropathy
  class (MONDO:0007006) with the absent Guyon-specific class stated
  and refused, never fabricated.
- `case.acute-dyspnea.006.json` — the first cardiopulmonary case
  (Milestone 48): acute dyspnoea and pleuritic pain twelve days
  after a total knee arthroplasty. 4 stages, 37 findings, 10 labs,
  10 measurements, 10 orderable tests, 8 hypotheses. The PE arm is
  mechanically complete: a Wells `score` block (partial 3.0 at
  stage 1 with the DVT-signs item unassessed, completing at 6.0 —
  PE likely — when the examination battery measures a 2.5 cm calf
  asymmetry on the un-operated side; the subjective
  clinician-judgment item is excluded from the block, with its
  sensitivity stated), a PERC `score` block (positive at 5, its
  < 15% gestalt precondition stated unmet), a CURB-65 `score`
  block (1 — age alone; a severity statement, never a diagnosis),
  an A–a `classification` block (ventilation/perfusion mismatch:
  PaO2 62 with a gradient of 51.8 mmHg against an age-expected
  17.4, the checker re-deriving the gradient from the case's own
  gas with the physiology module's alveolar gas equation), and an
  ESC-2019 severity `classification` block (pending until the
  CTPA supplies its RV input, then intermediate-high). Four
  likelihood ratios, all computed from consulted pairs: BNP
  LR+ 3.75 (C36), D-dimer LR+ 1.6441 with deliberately no LR−
  registered (C39), CTPA LR+ 20.75 from the conservative PIOPED II
  pair (C40), absent B-lines LR− 0.1176 (C43): the board runs
  0.36 → 0.3790 (the stage where the BNP honestly lifts heart
  failure to 0.2881 and embolism still leads) → 0.9554. The
  physiology link is the module's first to record the respiratory
  resting readout (Milestone 47) beside the pinned circulation
  hash, with the gap stated: the engine has no thromboembolic
  state, and the patient's gases are authored data checked
  against the module's equations, not simulation. The imaging
  link is localisation only — the pulmonary artery label in
  s0778 (recounted from the shipped bins: files 302–343, 23,547
  voxels) — with the absence stated in the link itself: neither
  subject's 104-label set holds an embolus, consolidation, pleura
  or effusion label, so the series cannot show this pathology and
  the case's CTPA is an authored report. No Theatre handoff: PE
  management here is medical, the Theatre holds no embolectomy
  procedure, and the absence is stated in the case rather than a
  handoff being fabricated. Ontology carries two recorded
  refusals: no Mondo class exists for community-acquired
  pneumonia (coded to pneumonia, MONDO:0005249) and none for
  acute heart failure in humans (coded to heart failure,
  MONDO:0005252), both stated in the hypotheses' notes.
- `case.pe-ruleout.007.json` — the rule-out case (Milestone 54):
  the PE pathway case 6 recorded but deliberately did not walk,
  walked here in full. Two days of localized, palpation-
  reproducible costochondral chest pain in a 62-year-old woman.
  4 stages, 26 findings, 4 labs, 6 measurements, 5 orderable
  tests, 6 hypotheses. The machinery runs the exclusion at every
  stage: a Wells `score` block COMPLETE at 0.0 from stage 1 (all
  six objective items assessed zeros — the mirror of case 6's
  partial 3.0 completing at 6.0; the judgment item excluded with
  its +3 sensitivity stated), a PERC `score` block counting
  exactly 1 — the age criterion alone — with its < 15% gestalt
  precondition stated MET (the deliberate contrast with case 6,
  where it was stated unmet and the count was 5), and a D-dimer
  of 560 µg/L FEU sitting 60 µg/L above the fixed 500 cutoff and
  60 µg/L below the age-adjusted 620 (62 × 10, ADJUST-PE — the
  age-adjusted reading is the decision, not a refinement). The
  case carries exactly one likelihood ratio, and it is the
  pathway's operative one: D-dimer LR− 0.0732, computed from the
  C39 pooled pair — the negative direction case 6 deliberately
  never registered. The board runs truth 0.34 → 0.3825 with PE
  retiring at 0.0099 at stage 2: the PE pathway terminates at
  stage 2, and stages 3–4 exist to test whether the learner can
  hold it. The scored error is over-testing, the mirror of the
  prior cases' missed diagnoses: a CTPA demanded at stage 3 by
  the patient's husband and the covering colleague classifies
  non-contributory — the machinery's verdict is the error — and
  its harms are priced from the consulted cohort (C49: 10 mSv
  median dose, 24% incidental-findings rate, 14% contrast-
  induced nephropathy risk as cited there): the one incidental it
  buys is a 7 mm solid right-upper-lobe nodule, whose
  consequence — Fleischner 2017 surveillance, CT at 6–12 months
  (C48) — outlives the encounter. The decisive evidence (pain
  reproduced exactly on palpation; a mechanical precipitant;
  swelling absent) carries no LR anywhere, by design. The
  physiology link records the pinned circulation baseline by
  data-identity with case 1 and asserts NO respiratory readout
  (the respiratory surface was under parallel Milestone 53
  construction; contrast case 6). No imaging link: an
  `imaging_assessment` records that the series could not have
  decided either question (no embolus or nodule label in either
  subject's 104-label set — and the TAP series is not a CTPA in
  any case), while the 24 rib labels and both series' lungs are
  in field. No Theatre handoff, stated: the disposition is
  discharge with safety-netting and a surveillance letter.
  Ontology carries a recorded refusal: the costochondritis
  search returns only Tietze syndrome (MONDO:0001858), defined
  by the swellings this patient lacks (C51) — refused, and the
  truth hypothesis carries Mondo null with the refusal recorded.
- `case.post-thyroid-hypocalcemia.008.json` — the sequel case
  (Milestone 57): the trace-30 patient on postoperative days
  1-2, perioral and digital paresthesias progressing after a
  total thyroidectomy whose own debrief computed this
  outcome. 4 stages, 22 findings, 9 labs, 10 measurements,
  3 orderable tests, 6 hypotheses. The module's second loop,
  in its second form: case 2 linked a FAILED trace; this one
  links a PASSED trace (42/43 — m3.2, the right parathyroid
  account, the one unmet microstep), carries the debrief's
  SHA-256, and has the checker match the verdict, the
  checklist arithmetic, the error, the computed hypocalcemia
  complication and the dp6 calcium-replacement decision
  field-by-field; the disposition then EXECUTES that
  protocol. One likelihood ratio (Trousseau's sign, LR+ 23.5
  computed at the conservative end of the consulted pair,
  its post-thyroidectomy counterweight stated in the finding
  itself) and one classification block assembled from three
  consulted sources with the assembly disclosed: the
  hypocalcemia management tier, which classifies
  iv-calcium-indicated from stage 1 on the symptomatic limb
  alone (C53's criterion is unconditional — recorded, not
  smoothed) and reclassifies under its first rule when the
  panel lands (corrected calcium 7.3 mg/dL, fallen from 7.8;
  ionized 0.94 mmol/L; PTH 8 pg/mL; phosphate above range;
  magnesium normal; vitamin D replete; venous pH normal;
  QTc 486 ms). The scored error is premature closure: the
  ward note's anxiety/hyperventilation attribution — a real
  mechanism (C61) that cannot lower a TOTAL calcium — was
  inherited by the learner, absorbed a below-range day-1
  calcium filed unactioned, and delayed the panel by a
  stage. The physiology link is data-identity with case 1
  for the baseline, and since Milestone 60 it carries the
  calcium-axis link that closes the gap stated at Milestone
  57: the Milestone 58 PTH-loss arm (secretion capacity
  9 percent, untreated) reproduces the authored course at
  POD2 (corrected 1.830 against 1.83 mmol/L; ionized
  0.9357 against 0.94; PTH 8.08 against 8) with a disclosed
  +0.146 mmol/L disagreement at POD1 (2.096 against 1.95),
  pinned by the checker against the Milestone 58 dossier's
  measured tables and the case's own labs. The course
  itself remains authored data. No imaging link: an
  `imaging_assessment` records that neither subject's
  104-label set contains a thyroid or parathyroid label.
  Ontology: MONDO:0001220 verified for the truth; the
  postoperative subclass refused, as none exists.
- `case.upper-gi-bleed.009.json` — the bleeding case
  (Milestone 61): a 71-year-old with two days of melena who
  arrives carrying his own diagnosis — "gastritis", twice
  self-proven across two winters, never once investigated.
  4 stages, 31 findings, 6 labs, 11 measurements, 6
  orderable tests, 6 hypotheses. The library's first SCORE
  block and first CLASSIFICATION block in one case: the
  Glasgow-Blatchford score (C63), computed stage by stage —
  a partial 2 at stage 1 (the two blood items unmeasured,
  flagged partial by the machinery) completing at 6 on
  admission values, and never re-priced by the stage-3
  count — and the Forrest classification (C66), pending
  until the endoscopy exists, then IIa on the visible
  vessel. Four likelihood ratios, every one a computed
  reciprocal of a Rational Clinical Examination figure
  (C64): the examination melena (0.04) and the
  urea:creatinine ratio (0.1333) retire the lower source;
  the severity pair — tachycardia (0.2041) and hemoglobin
  below 8 (0.2222, the conservative end) — retire the
  anchor, which is defined by its severity claim because
  that is the claim the patient actually makes. The first
  hemoglobin (13.9, in range) carries no ratio and excludes
  nothing: the physiology link is the library's first
  PERTURBATION-arm link — the baseline by identity with
  case 1, the 750 mL hemorrhage arm re-run and hash-pinned
  by the checker (its post window prices the compensation
  pattern), and the course arm's hematocrit lag (0.432 at
  +1 min, 0.399 at +60 min on 408.04 mL of refill) pinned
  by dossier identity — whole blood leaves at its own
  concentration, so the count cannot fall until refill
  dilutes what remains. The transfusion question is
  answered against Villanueva's restrictive threshold
  (C65): nadir 7.6, no transfusion, 7.7 untransfused at
  24 hours. Management stops the ibuprofen permanently
  and treats the positive H. pylori with documented
  eradication (C69); the endoscopy's combination therapy
  and the 80 mg + 8 mg/h PPI follow C66, concordant with
  C70. The Theatre link is the library's third form: no
  handoff existed at Milestone 61 (the Theatre held no
  endoscopy procedure, and the case said so); Milestone 62
  authored proc.upper-gi-endoscopy and Milestone 64 linked
  the case to its trace-31 attempt — the same IIa bulb
  ulcer, epinephrine plus clips, PASS 27/27 — re-verified
  by the checker on every run. Imaging
  link is localisation only: the s0778 duodenum label
  (crosswalk index 10 → `canal.duodenum`; 49 slices,
  15,235 voxels recounted by the checker) — the label set
  holds no ulcer, and could not. Ontology: five Mondo
  classes verified; the lower-source hypothesis carries
  Mondo null with a fourth recorded refusal.
- `attempts/` — learner attempts (boards + orders per stage). Case
  2's model learner is deliberately imperfect in one documented way:
  it anchors on a retained CBD stone (ERCP ordered as therapy at
  stage 2, before MRCP) and still holds the stone at 0.25 at stage 4,
  after the workbench rules it out — one scored anchoring event.
  Case 3's model learner anchors on ectopic pregnancy at stage 2 —
  holding it at 0.15 at the very stage the negative pregnancy test
  retires it — also exactly one scored event. Case 4's model learner
  anchors on cervical radiculopathy — an anchor installed before the
  case begins, fed by a renormalization rise at stage 2 and by a
  degenerative cervical MRI the learner ordered against guideline
  advice (classified non-contributory) — and still holds it at 0.15
  at stage 4, after the electrodiagnostic protocol retires it: one
  scored event. Case 5's model learner anchors on Guyon's canal —
  an anchor he installs himself from a true exposure history (the
  patient is a weekend cyclist), holds through his own stage-2
  examination finding that excludes the wrist anatomically, and is
  still holding at 0.16 at stage 3 when the elbow ultrasound
  retires it on the board — one scored event, structurally the
  inverse of case 4's: self-installed, and surviving a refutation
  the learner personally elicited. Case 6's model learner anchors
  on heart failure — an anchor installed mid-case by a test
  result: the stage-2 BNP (385 pg/mL, honestly weighed by the
  workbench itself) converts his differential into a diagnosis,
  and he still holds heart failure at 0.16 at stage 3, after the
  CTPA and after his own B-line-negative lung ultrasound — ordered
  to confirm the frame — retires it on the board: one scored
  event, a third installation shape (result-installed, after case
  4's other-clinician and case 5's self-installed anchors). Case
  7's model learner anchors on pulmonary embolism — an anchor
  installed mid-case by social pressure alone: she releases PE to
  0.07 when the pathway completes at stage 2, then re-installs it
  at 0.13 at stage 3 under a husband's "just do the scan, to be
  safe" demand echoed by the covering colleague — a stage at
  which no clinical finding of any kind arrives — and orders the
  CTPA that is the anchor's purchase receipt; she re-walks the
  pathway and commits the truth at 0.55 at stage 4: one scored
  event, a fourth installation shape (social pressure, after case
  4's clinician-frame, case 5's self-installed and case 6's
  result-installed anchors). Case 8's model learner anchors on
  anxiety/hyperventilation — an anchor she neither installed nor
  was pressured into but INHERITED from the ward note before the
  case began: she leads with it at stage 1 (0.34 against the
  truth's 0.30), still holds it at 0.26 at stage 2 after
  eliciting Trousseau's sign with her own hands, and releases
  it only when the calcium panel returns — one scored event, a
  fifth installation shape (premature closure). Case 9's model
  learner anchors on gastritis — an anchor installed by the
  PATIENT: the historian himself supplies the benign
  diagnosis, confidently, from two winters of untested
  experience, in the first minute, and the learner adopts it
  as his stage-1 lead (0.36 against the truth's 0.30), keeps
  a hand on it through a reassuring first hemoglobin, and
  still holds it at 0.16 at stage 3 — the stage the severity
  arithmetic retires it — because the man in the bed still
  believes it: one scored event, a sixth installation shape
  and the ninth anchoring shape in the library
  (patient-installed self-diagnosis), and the library's
  first under-triage error — the mirror of case 7's
  over-testing.
- `debriefs/` — generated by `tools/case_run.py` (one generic runner
  for every case since Milestone 22); independently recomputed by
  `tools/case_check.py` (parameterised over all cases, with per-case
  profile sections; 14,919 checks at Milestone 61).
- `fhir/` — FHIR-shaped interchange export of the case (design/07);
  the case JSON is the source of truth and the checker fails the
  build if the export disagrees with it.
