# Milestone 66 — Case #10: recurrent chest pain after a negative workup (the evidence-of-absence anchor)

Case library 10 of 12. One new case for the workbench, built in the
exact idiom of Cases #1–#9: a staged presentation, a differential
board the learner must commit numbers to, one mechanically evaluated
score block, likelihood ratios only where consulted sources price
them, links only where they are honest, and one anchoring event of a
shape the library has not used before.

## The topic, and why this one

Two candidates were weighed: acute cholangitis (Tokyo Guidelines
TG18) and acute coronary syndrome. ACS was chosen, on the evidence
available to consult in-session:

- **Finding-level likelihood ratios exist for ACS and were
  consultable.** Fanaroff 2015 (the Rational Clinical Examination
  for chest pain, JAMA) prices individual findings — radiation to
  both arms, ST-segment depression — from its abstract, read in
  full. Cholangitis has no comparable finding-level source; TG18
  prices criteria membership, not findings, so a cholangitis case
  would have run its board on criteria alone or on ratios this
  milestone could not consult.
- **A first-class admission score exists and fits the shipped
  machinery.** The HEART score (Six 2008, full text including
  Table 1 read in-session) is a five-item 0–2 score whose troponin
  item is defined on the first sample — a natural fit for the
  `score` block kind and for the admission-values discipline
  Case #9 established with Blatchford.
- **The tenth anchoring shape is native to this presentation.**
  The prior-negative-workup story — "already ruled out last
  month" — is the canonical ACS miss, and the consulted evidence
  is fused with it: the same review that prices the findings
  prices a prior *abnormal* stress test at LR 3.1 and offers no
  ratio for a prior normal one. The anchor's premise and its
  refutation come out of the same source.

ACS had appeared in the library only as a rival hypothesis
(Cases #1, #6, #7), never as the truth or the presentation.

## The case

`cases/case.recurrent-chest-pain.010.json` — a 58-year-old
warehouse supervisor whose central chest pain was worked up six
weeks ago in the same department (serial troponins negative,
resting ECG normal, exercise stress test negative for ischemia;
discharged "non-cardiac chest pain, likely gastro-oesophageal
reflux", omeprazole since) and who returns with the same pain at
rest, radiating to both arms, diaphoretic and nauseated, with
**new** 1.5 mm ST-segment depression V4–V6. First troponin I
0.34 ng/mL (8.5× the 0.04 threshold); repeat 1.72 ng/mL (a
5.06-fold rise). Angiography: 90% proximal LAD stenosis with
thrombus; drug-eluting stent placed. Truth: type 1
non-ST-elevation myocardial infarction under the Fourth Universal
Definition (C75) — rise, ischemic symptoms, new ischemic ECG
changes, thrombus at angiography.

Six hypotheses (all priors verify-flagged placeholders, the
library's standing discipline): ACS-NSTEMI 0.30; the recurrence
frame 0.26; other-unspecified 0.20; pneumonia 0.12; pulmonary
embolism 0.08; aortic dissection 0.04.

## The tenth anchoring shape: installed by a prior negative workup

The library's nine shapes, and the defence against each:

1. **Pattern-completion** (#1) — no gestalt is matched; a
   documented test result is quoted.
2. **Treatability** (#2) — the frame promises no easier therapy;
   discharge on the old diagnosis is not a treatment.
3. **Feared-outcome** (#3) — the frame does not shield the learner
   from a dreaded diagnosis; it exposes him to the most dangerous
   miss in the building.
4. **Clinician-frame** (#4) — no colleague's spoken label is
   inherited. The installer is the record of the patient's *own*
   prior encounter — the same institution's discharge conclusion,
   with data attached. A colleague's frame can be discounted as
   opinion; this one cannot, because it is not opinion.
5. **Self-installed exposure** (#5) — the learner created nothing;
   the premise predates his involvement by six weeks.
6. **Result-installed value** (#6) — that anchor is a result
   arriving *mid-case*; this one arrived six weeks *before* the
   case and is re-imported into it.
7. **Social pressure** (#7) — the patient repeats the conclusion,
   but the pressure is documentary, not interpersonal; the learner
   would hold the frame if the patient never spoke.
8. **Premature closure by inheritance** (#8) — the nearest
   neighbour, and the distinction is the teaching point. Case #8's
   inherited frame was an *interpretation* passed along with no
   test behind it, and it collapsed at the first measurement that
   touched it. This frame has real tests behind it — performed
   correctly, read correctly — which is exactly why it survives
   first contact with contradictory data: at stage 2 the learner
   does not ignore the troponin, he *re-interprets* it ("a leak, a
   demand effect"), an option an evidence-backed frame always has
   and an interpretation-only frame does not.
9. **Installed by the patient himself** (#9) — the patient quotes
   the conclusion but did not coin it and could not have; it was
   issued to him, with tests attached.

The shape's name: the **evidence-of-absence anchor**. The error is
a scope error. A negative workup is *episode-indexed* — no
necrosis then; no flow-limiting stenosis under stress then. The
anchor reads it as *patient-indexed* immunity. Plaque rupture is
precisely the event a stress test cannot exclude, at lesions it
cannot see. The machinery enacts it exactly once: the workbench
rules the recurrence out at stage 2 (0.0043, on the first
troponin); the learner holds it at 0.22, rationalising the
troponin inside the frame; the repeat he ordered himself — to
watch the level fall — returns five-fold higher and breaks the
frame at stage 3. Error direction: under-triage, the library's
second (after Case #9), mirroring Case #7's over-testing.

## Evidence and prices

Three likelihood ratios, no more:

| finding | ratio | status | source |
|---|---|---|---|
| pain radiation to both arms | LR+ 2.6 (CI 1.8–3.7) | cited | C71 Fanaroff 2015 |
| ST-segment depression | LR+ 5.3 (CI 2.1–8.6) | cited | C71 Fanaroff 2015 |
| first troponin elevated (0.34 ng/mL) | LR+ 14.4 | computed | C74 Al-Saleh 2014: 0.72 / (1 − 0.95) |

Deliberately **unpriced**: the prior negative workup (C71 prices a
prior *abnormal* stress test at 3.1 and offers no converse — the
asymmetry is recorded in the finding's own text); the rising
repeat troponin (a constituent of the diagnosis under C75, not
evidence for it); the angiogram (direct inspection); the authored
absences (tearing pain, fever, pleuritic pain).

Workbench board (computed by the runner, recomputed by the
checker): stage 1 — truth 0.8552, frame 0.0538 (not yet ruled
out), PE 0.0165 and dissection 0.0083 ruled out; stage 2 onward —
truth 0.9884, frame 0.0043. Board movement comes only from the
three priced findings; stages 3–4 add definitional and anatomical
evidence the board does not price, and the record says so.

## The HEART block

`heart_score`, kind `score`, source C72 (Six 2008, Table 1 and
methods read in full; the printed table's "≤65 year" top age row
is an evident misprint the methods text resolves to "65 years or
older", and the register records this). Stage by stage:
**6 partial** at stage 1 (history 2 + ECG 2 + age 1 + risk
factors 1; troponin not assessed — a floor that already excludes
the 0–3 discharge band) → **8** at stage 2 (first troponin 2,
above twice the limit) → **8, 8**. Admission-values discipline is
checker-proven: the troponin item's atoms reference
`lab.troponin-i-first` only, and the stage-3 repeat never
re-enters the block. Bands carry both consulted cohorts' outcome
figures (C72: 2.5% / 20.3% / 72.7%; C73 Backus validation: 1.7% /
16.6% / 50.1%). Risk-factor counting is Six's own list — the
patient's hypertension and family history count (2 factors,
1 point); his nine-years-quit smoking, undiagnosed "borderline"
cholesterol, absent diabetes and BMI 27 do not, and the case
says why in the finding text.

A machinery-honesty note, recorded rather than disguised: the
workbench classifies the repeat troponin and the angiography
orders **non-contributory** — its taxonomy prices board and
criteria movement only, and the definitional rise and the direct
inspection move neither. The case's checker profile asserts
exactly those classifications. The first troponin classifies
discriminating. Resource tally: 3 orders, 10 cost units /
125 minutes (verify-flagged placeholders, house rule); the chest
radiograph stays on the menu un-ordered, as Case #7's discipline
records availability separately from use.

## Links — and their stated gaps

- **Physiology: identity link + stated absence.** The pinned
  resting baseline (hash `0x6369b10e9a71c872`, the seven outputs
  cases 1–9 record) in Case #7's simple form. The gap is stated
  in the link itself: the engine has no ischemic myocardium, no
  plaque, no coronary state and no troponin — there is no
  perturbation arm for this presentation, and no neighbouring arm
  was borrowed and renamed (Case #9's hemorrhage arms price
  volume, not ischemia).
- **Imaging: localisation only.** s0778 `heart_myocardium`
  (crosswalk index 24 → Body Model record `heart`; 53 slices,
  files 255–307; 48,784 voxels recounted from the shipped bins by
  the checker; max cross-section file 262, 1,381 voxels; volume
  164.65 mL; z-range reproducing the crosswalk bbox). The
  label-absence block states that the 104-label set holds no
  coronary plaque, thrombus or stenosis label — no coronary
  artery label at all — so the series cannot show this pathology;
  the honesty block keeps the three individuals separate and
  notes the CT is not the diagnostic test for this presentation.
- **Theatre: no handoff — a named gap.** The definitive act is
  catheter-laboratory angiography with PCI; the Theatre's seven
  procedures contain no coronary intervention. `management`
  carries `theatre_note` + `theatre_link_verified` in the
  Cases #6/#7 form, naming all seven procedures; the case carries
  no `theatre_link` key. A coronary-intervention Theatre
  procedure is recorded here as a gap for a future milestone,
  exactly as Case #9 recorded endoscopy at M61 (built at M62,
  linked at M64). Whether the loop closes the same way is a
  future milestone's decision, not this one's claim.

## Ontology (EBI OLS, in-session)

Verified: MONDO:0004781 acute myocardial infarction (truth);
MONDO:0007186 gastroesophageal reflux disease (the anchor's named
disease — the hypothesis is the claim built on it, as in
Case #9); MONDO:0005279 and MONDO:0005249 carried from C10.
HPO: HP:0100749 (carried), HP:0000975 hyperhidrosis,
HP:0012250 ST segment depression, HP:0002018 nausea;
HP:0012251 ST segment elevation asserted as an explicit
**absence** in the ground truth (the NSTEMI fork).

Two refusals, recorded in the hypotheses' notes and the C10/C11
addenda: (1) an OLS search for a non-ST-elevation MI class
returned no class (numFound 0) — the truth is coded to the
general AMI class with the qualifier in prose (Case #8
precedent); (2) no general aortic-dissection class exists in
OLS — only familial (MONDO:0019625) and syndromic
(MONDO:0022470) classes — so the dissection hypothesis carries
Mondo null; the patient has no familial disease and no class was
bent to fit him.

## Register

C71–C77 added (Fanaroff 2015; Six 2008; Backus 2013; Al-Saleh
2014; Thygesen 2018 UDMI; Gulati 2021 AHA/ACC chest-pain
guideline, consulted via its official slide set and pocket guide;
MedlinePlus troponin page). Three LR derivations registered (two
cited, one computed). C10/C11 carry dated Milestone 66 addenda.
`extended_at_milestone` 61 → 66; the two profile assertions that
pin the register's extent (cases 8 and 9) were updated to match,
per the M61 precedent. StatPearls/NCBI is cited for nothing, as
throughout. One recorded scope note: C74's target condition is
adjudicated MI, applied here to the ACS hypothesis, with the
scope stated in the derivation; and the case's assay is the
conventional one the HEART item was defined on, against C76's
high-sensitivity preference — recorded in the case's validity
block, the substitution not made silently in either direction.
Recorded for the register's hygiene: the two cited derivations'
prose was amended during verification to carry their LR values
explicitly (2.6, 5.3), after the new profile's assertion caught
their absence — the checker profile doing its job on its own
milestone.

## Management

Admission to a monitored coronary-care bed; antiplatelet and
anticoagulant therapy per the consulted guideline's high-risk
NSTE-ACS pathway (C76) — strategy named, doses not fixed by any
source consulted this milestone and therefore not stated;
angiography with PCI (the guideline's high-risk triad: new
ischemic ECG changes, troponin-confirmed injury, high-risk score)
— performed, stent placed. Three alternatives refused on the
record: discharge under the recurrence frame; a repeat stress
test (re-asking the question the troponin answered, against the
guideline pathway); and treatment as reflux. Secondary
prevention includes annotating the six-week-old discharge
diagnosis in the chart as superseded — correct about its episode,
closed as a premise — so the next presentation does not inherit
it.

## Verification

- `tools/case_check.py`: **ALL CHECKS PASS — 16,136 passed,
  0 failed** (previous total 14,964 at M64; delta **+1,172** =
  28 assertions in the new `profile_case10` + the generic §1–§6
  machinery running over a tenth case — its findings, labs,
  hypotheses, orders, boards and criteria at every stage — with
  cases 1–9's profiles unmoved apart from the two register-extent
  assertions). The profile proves, among the rest: the HEART
  stage totals [6 partial, 8, 8, 8] and item composition; the
  admission-values discipline (first-troponin-only atoms); the
  single anchoring event's stage, hypothesis and both boards;
  the troponin arithmetic (8.5×; 5.06-fold rise); the imaging
  recount from the shipped bins; both ontology refusals; the
  theatre absence naming all seven procedures.
- `tools/theatre_check.py`: **872 checks, 0 failures** — unmoved,
  as expected: this milestone touches nothing in the Theatre.
- All other `tools/*_check.py` (assembly, cv, dig, endo, the four
  FMA passes, imaging toolkit, integ, lymph, major-nerve, muscle,
  muscle-assembly, nerve, repro, resp, skeletal, uri): **all
  PASS**. `tools/verify_web.js`: **ALL CHECKS PASS**.
- `tools/readme_check.py` (root README, not touched by this
  milestone): **exactly 7 failures, every one a figure this
  milestone moves** — R7 case files == cases/ (9 → 10 cases),
  R7 register size == parameters.json (70 → 77 sources),
  R7 register extent stated (C1–C70 → C1–C77),
  R9 case_check total == its printed output (14,964 → 16,136),
  R10 milestone index rows == MILESTONE-*.md on disk (65 → 66),
  R11 file index [cases] == tracked set (30 → 33 files: the case,
  its attempt, its debrief), R11 file index [milestones] ==
  tracked set (70 → 71). No other rule fails — the R12 geometry
  statements and the remainder of the guard stay green. These
  seven are listed here for the next README pass, per the M65
  pattern.
- Byte-identity census (sha256 over the whole `cases/` tree,
  before vs after): the only changes are the intended ones —
  modified: `cases/README.md`, `cases/parameters.json`; added:
  `cases/case.recurrent-chest-pain.010.json`,
  `cases/attempts/attempt.case-recurrent-chest-pain-010.model-learner.json`,
  `cases/debriefs/debrief.case-recurrent-chest-pain-010.model-learner.json`.
  Cases #1–#9 and all their attempts and debriefs are
  sha256-byte-identical.

## Governance

Expert-review gate **UNMET** — stated in the case's review block
(required roles: cardiologist, emergency physician;
`recorded_reviewers: []`, none fabricated), exactly as every prior
case records it. Content `dual-sourced-draft`; scores
formative-only; no composite score anywhere in the new files
(checker-asserted). Public copy is neutral project documentation
throughout.

## Landing batch (for the parent, under upload-as-you-finish)

Modified: `cases/parameters.json`, `cases/README.md`,
`tools/case_check.py`. New: `cases/case.recurrent-chest-pain.010.json`,
`cases/attempts/attempt.case-recurrent-chest-pain-010.model-learner.json`,
`cases/debriefs/debrief.case-recurrent-chest-pain-010.model-learner.json`,
`milestones/MILESTONE-66.md`. Root `README.md` untouched.

## What remains open

The case library stands at **10 of 12**. Case #10 leaves one named
gap on the record: a coronary-intervention procedure for the
Theatre (angiography/PCI), the natural counterpart milestone if
the library chooses to close this loop as it closed Case #9's.
Cases #11 and #12 each still need a structurally distinct
anchoring shape — eleven shapes will then be taken.
