# Milestone 41 — Case #4: carpal tunnel syndrome (the localization case)

Case Workbench case #4, `case.carpal-tunnel.004`: a 47-year-old woman
with eight months of nocturnal median-distribution paresthesias,
type 2 diabetes, and a neck hypothesis installed by another clinician
before the case begins. The case is built on the M20/M22/M29 machinery
unchanged in kind — staged findings, a Bayesian board over declared
priors, mechanically evaluated criteria, order classification, exactly
one anchoring event — and adds no new block kind: the guideline
instrument (the CTS-6) runs on the `score` block machinery M29 built.
The case's links run forward into the newest modules: the M39 median
nerve clinical record, the M33 inventory nerves, and the M35
innervation pass — including one place where the honest link is to a
trunk record because the named branch has no record, stated as such.

## 1. Case design rationale

The first three cases are visceral/abdominal: a diagnosis made inside
a body cavity, from scores, imaging and (case 2) the record of a prior
operation. Case #4 moves the workbench to a different reasoning shape:
**localization**. The differential is one nerve at two levels (wrist
vs elbow), one root (C6/C7), one plexus, and one generalized process
(diabetic polyneuropathy) — and the decisive evidence is not a picture
of the lesion but a *segment*: conduction slowed across the wrist and
normal across the forearm, with a needle examination that clears the
neck. The case was chosen because its machinery stresses differ from
the first three in instructive ways:

- **The board must be allowed to move backwards.** The stage-2
  examination's strongest board evidence is *against* the diagnosis:
  normal thumb abduction strength carries LR 0.5 in the same review
  that supplies the case's positive LRs (C23), and the workbench's
  carpal-tunnel posterior dips 0.7778 → 0.6364 at stage 2 — even as
  the CTS-6 completes at 16.5/26, deep in its positive band. A
  workbench that only multiplies favourable evidence is not honest
  machinery; this case makes the dip structural, and the profile
  section asserts the exact trajectory.
- **The famous signs are the weak members.** Phalen's and Tinel's
  signs are positive, and carry **no board likelihood ratio**: the
  Rational Clinical Examination pools them at LR 1.3 and 1.4 and
  concludes they have little or no diagnostic value (C23). They act
  through the CTS-6, where the instrument's author weighted them,
  and nowhere else. Durkan's compression test is recorded
  qualitatively for the same reason (no consulted source pools it).
- **The guideline and the workup visibly part company — and the case
  says so.** The AAOS 2024 guideline (C24) holds that the CTS-6
  diagnoses carpal tunnel syndrome as effectively as ultrasound, NCS
  or EMG, and that most patients it diagnoses need no further study.
  This workbench ordered both anyway, because a live, anchored rival
  (the neck) had to be excluded by the one instrument that can
  exclude it (the AANEM protocol, C25). The adjudication's
  `score_comparison` records the tension and the reason; the order
  tally counts the cost. The learner's cervical MRI enjoys no such
  defence: the guideline recommends against it outright, and the
  machinery classifies it non-contributory.
- **The anchor is installed before stage 1.** Cases 1–3 seed their
  anchors inside the case (a finding, a test not yet resulted, a
  score misread). Case #4's anchor arrives with the patient: an
  urgent-care clinician has already told her the problem is her neck,
  citing spondylosis on an old plain film. The learner's error is
  then not inventing the hypothesis — carrying it at 0.28 at stage 1
  is defensible — but failing to retire it when the localizing
  instrument speaks: renormalization feeds it at stage 2 (the neck's
  board share rises because evidence argued against its *rival*, not
  for it), a degenerative MRI feeds it at stage 3, and it survives a
  clean C5–T1 needle examination at 0.15 at stage 4. Exactly one
  anchoring event, at the stage where the workbench rules the
  hypothesis out (0.0015).

## 2. The staged presentation

| Stage | Content | Board (CTS) | CTS-6 |
|---|---|---|---|
| 1 | History: nocturnal median-distribution paresthesias, flick sign, daytime provocation; neck ache (the decoy); diabetes history; hypalgesia + Katz diagram on first examination | 0.7778 | 7.5, partial (4 items not assessed), intermediate band |
| 2 | Hand battery: Phalen/Tinel/Durkan positive; thenar bulk normal, thumb abduction 5/5, 2PD preserved; thenar-eminence sensation intact; no radicular signs. HbA1c 6.8% | 0.6364 (the LR− dip) | 16.5/26, positive band |
| 3 | Wrist ultrasound: CSA 13 mm² (R) / 11 mm² (L), no secondary cause. Learner's cervical MRI: spondylosis, no root compression | 0.9114 | 16.5 (unchanged) |
| 4 | NCS/EMG (AANEM protocol): lesion localized to the wrist segment; comparison nerves normal; needle EMG clears C5–T1 | 0.9943 | 16.5 (unchanged) |

Rule-outs (posterior < 0.02, the workbench convention): pronator
syndrome, diabetic polyneuropathy and brachial plexopathy first fall
at stage 3 (the ultrasound stage — a renormalization effect of the
CTS mass rising, disclosed as such in the case); cervical
radiculopathy and the residual fall only at stage 4. The asymmetry is
the design: nothing before the electrodiagnostic protocol can retire
the neck, and the case does not pretend the ultrasound does.

Census: 4 stages, 24 findings (9 history/examination at stage 1
including two recorded absences, 9 at stage 2 including the three
CTS-6 negative items recorded as examined absences, 3 at stage 3,
3 at stage 4), 1 laboratory value (HbA1c), 3 measurements (median CSA
13 mm²; distal motor latency 5.6 ms; sensory peak latency 4.4 ms —
all case data), 5 orderable tests, 6 hypotheses, 1 criteria block.

## 3. Per-value source table

Every likelihood ratio on the board, with its source as consulted
in-session (register: `cases/parameters.json`, extended at this
milestone — sources C23–C29, derivations now 13):

| Finding | Value | Status | Source |
|---|---|---|---|
| f.median-hypalgesia | LR+ 3.1 (95% CI 2.0–5.1) | cited | C23 — D'Arcy & McGee, JAMA 2000 (RCE), via the review abstract + DARE appraisal |
| f.katz-classic-diagram | LR+ 2.4 (95% CI 1.6–3.5) | cited, **single-study flagged** (1 study, 145 hands) | C23 |
| f.thumb-abduction-normal | LR− 0.5 (95% CI 0.4–0.7) | cited — the negative branch of the same finding whose positive branch is LR+ 1.8 | C23 |
| f.us-csa-enlarged | LR+ 5.8788 = 0.776 / (1 − 0.868) | computed | C27 — Fowler et al. 2011 meta-analysis (19 studies, 3,131 wrists; sens 77.6%, spec 86.8%), abstract read at the publisher and PMC, agreeing |
| f.ncs-median-neuropathy | LR+ 17.0 = 0.85 / (1 − 0.95) | computed **at stated bounds — a disclosed floor**, not an estimate | C25 — Jablecki et al. 2002 practice parameter (sens > 85%, spec > 95%), via the AAN release + consulted EDX review |

Values deliberately **not** taken, and why:

- Phalen (pooled LR 1.3) and Tinel (pooled LR 1.4), C23: the review's
  own conclusion is that they have little or no diagnostic value;
  they act only as CTS-6 items. Multiplying them into the board as
  well would double-count weak evidence through two instruments.
- The AFP adaptation's CTS-6 likelihood ratios (LR+ 4.5 / LR− 0.14
  at ≥ 12, C26): the score is never multiplied into the board — the
  standing two-instruments rule from cases 1 and 3.
- Durkan's test, Spurling's manoeuvre, the cervical MRI finding, the
  thenar-eminence finding, the EMG/NCS exclusion legs: qualitative.
  No likelihood ratio for any of them was taken from a source
  consulted for this case, so none carries board weight. The
  exclusions they support are argued as conjunctions in the
  adjudication, not as products.
- Bland electrodiagnostic severity grading: not consulted to a
  citable standard in-session, so the case does not grade severity
  by it; it says "moderate, electrodiagnostically confirmed" as case
  data and no more.

Guideline application (C24): the AAOS *Management of Carpal Tunnel
Syndrome* Evidence-Based Clinical Practice Guideline, adopted
May 17–18, 2024 (replacing the 2016 edition), consulted via the
peer-reviewed summary (Shapiro & Kamal et al., J Am Acad Orthop
Surg 2025) and the AFP guideline summary (2025), read in full. Its
operative statements in this case: CTS is a clinical diagnosis; the
CTS-6 performs as effectively as US/NCS/EMG (strong recommendation);
most CTS-6-diagnosed patients need no further study; further
US/NCS/EMG when the CTS-6 is negative but suspicion is high, and
electrodiagnosis may be considered where diagnostic uncertainty
remains; MRI and neurodynamic testing are not recommended;
corticosteroid injection gives short-term relief only (high-quality
evidence, no long-term benefit); open vs endoscopic release have
similar long-term outcomes. The disposition follows the guideline;
the one deliberate departure (confirmatory testing after a positive
CTS-6) is adjudicated in the open in `score_comparison`.

CTS-6 (C26): items and weights verified identical across three
independent consulted reproductions (J Hand Surg Glob Online 2026
analysis Table 1; Thai validation Table 1; QCTS-6 validation):
median-territory numbness 3.5, nocturnal numbness 4, thenar
atrophy/weakness 5, Phalen 5, two-point loss 4.5, Tinel 4 — total 26.
One reproduction states the positive threshold as ">12" and another
as "≥12"; the patient's 16.5 is clear of the discrepancy, and the
band declaration in the block says so. Stage-1 partial 7.5 sits in
the intermediate band (>5 ↔ 25% probability) with four items
not-assessed — never assumed.

Ontology (C10/C11 addenda, OLS-verified in-session): CTS
MONDO:0007275; diabetic polyneuropathy MONDO:0001583; brachial
plexus neuropathy MONDO:0006683 ("brachial plexopathy" an exact
synonym); cervical radiculopathy — **no cervical-specific Mondo
class exists**; the generic radiculopathy class MONDO:0002959 is
used with a stated note. Pronator syndrome — **no Mondo class**;
MONDO:0003598 (median nerve neuropathy) was found and refused,
because its own description covers median neuropathy at all sites
and would describe both the hypothesis and the diagnosis. HPO:
Hand paresthesia HP:0033660, Paresthesia HP:0003401, Positive carpal
Tinel sign HP:0033672, Constrictive median neuropathy HP:0012185,
Neck pain HP:0030833.

Project-output sources (C28): the M39 record `major.median`
(roots C6–T1; the palmar cutaneous branch does not traverse the
carpal tunnel — the anatomical basis of the thenar-eminence finding;
Tinel/Phalen named as its clinical tests) and its M33 inventory
geometry links; the M35 innervation pass, in which "recurrent branch
of the median nerve" — the nerve the thenar muscle records name — is
an **unresolved phrase whose single component is absent** (no FMA
class, no inventory record). The case therefore links its thenar
examination to `muscle.abductor-pollicis-brevis` and the median
trunk records, and the checker asserts the pass really does say
that: the honesty claim is itself checked.

## 4. The anchoring event

One, by construction and by recomputation (the profile section
recomputes the events from the attempt boards and the workbench
rule-out stages, independently of the runner):

**(stage 4, hyp.cervical-radiculopathy)** — learner 0.15, workbench
0.0015, ruled out at stage 4.

The event is late by design, and its lateness is the teaching point:
the neck is *legitimately live* through stage 3 (workbench 0.0234,
above the 0.02 line). The learner's failure is not early suspicion;
it is the residue after the protocol's needle leg — the leg that
exists, per C25, to exclude exactly this — comes back clean, and
after conduction localizes the lesion to the wrist. The learner's
stated defence ("the ache is real; the MRI showed degeneration") is
answered in the adjudication: both premises are true, and neither is
evidence for the hypothesis. Learner boards: CTS 0.40 / 0.38 / 0.55 /
0.70 against the workbench's 0.7778 / 0.6364 / 0.9114 / 0.9943 —
the learner is behind the board at every stage, and the Brier scores
(learner 0.4724 / 0.5084 / 0.2724 / 0.1220; workbench 0.0608 /
0.1629 / 0.0097 / 0.0000, as the runner computes them) include the
stage-2 inversion where the learner's board worsens while the
workbench's honestly dips.

## 5. Order classifications (recomputed, asserted)

| Order | Placed → results | Classification | Basis (runner's) |
|---|---|---|---|
| test.hand-exam-battery | 1 → 2 | discriminating | lead moves 0.7778 → 0.6364 (the LR− 0.5) |
| test.hba1c | 1 → 2 | safety-net | must-not-miss hyp.diabetic-polyneuropathy |
| test.wrist-ultrasound | 2 → 3 | discriminating | lead moves 0.6364 → 0.9114 |
| test.cervical-mri | 2 → 3 | **non-contributory** | no posterior, criteria, or safety-net effect |
| test.ncs-emg | 3 → 4 | discriminating | cervical crosses the rule-out line 0.0234 → 0.0015 |

Criteria-completing: none — the battery also settles four CTS-6
items, but the classification cascade gives discriminating priority,
and the case file's note on the battery says both things. Resource
tally: 170 min, 21 cost units (verify-flagged placeholders, as
throughout the module). The MRI is the menu's most expensive item
(45 min, 8 units) and its only non-contributory one: the anchor's
purchase receipt, kept on the menu deliberately.

## 6. What is absent, stated

- **Imaging link: none, on two grounds.** Both shipped series were
  re-read at this milestone: the TotalSegmentator v1.0 label set is
  *identical* for s0778 and s1090 (104 labels) and contains no nerve
  label of any kind — no median, carpal, wrist or hand label — and
  both studies are CT thorax-abdomen-pelvis, so the wrist is outside
  the imaged volume entirely. Case 3 could localize by a neighbour
  label (colon, for the appendix); here there is no neighbour in the
  field of view. The case therefore carries an `imaging_assessment`
  block instead of `imaging_link`, and the profile section asserts
  every clause of it from the shipped files. The case's ultrasound
  is an authored encounter (case data), as case 3's CT was. The
  atlas contrast is recorded: the Body Model *does* hold the
  structure (M33 inventory nerves, M39 clinical record) — coverage
  asymmetry stated, not smoothed.
- **Physiology link: none.** The engine has no peripheral-nerve,
  entrapment or demyelination state; case 2's precedent governs —
  no decorative baseline link. `ground_truth.engine_state` says so.
- **Theatre handoff: none.** The Theatre contains exactly two
  procedures (`proc.chole.lap`, `proc.appy.lap` — asserted by the
  profile against the shipped files) and no carpal tunnel release.
  The disposition names the operation the simulator does not have;
  authoring that procedure is recorded as a next step, not asserted
  as a link.
- **FHIR export: none.** Case 1's alone, standing practice.

## 7. Machinery and checker

No new block kind. The CTS-6 runs on M29's `score` machinery
(fractional points are native to it); `case_run.py` is untouched.
`tools/case_check.py` gains `profile_case4` (30 assertions):
CTS-6 partial/final recomputation and the adjudication's stated
comparison; the exact posterior trajectory including the stage-2
dip; rule-out stage structure; the anchoring events recomputed from
first principles; the imaging absence re-verified from both
crosswalks and both series files (label counts, label-set identity,
no nerve-ish label, study types); the M39/M33/M35 link claims
(including the recurrent-branch unresolved status); the
no-physiology-link and no-handoff claims (the Theatre's procedure
set asserted equal to exactly the two shipped procedures); the
ontology discipline of §3; and the debrief's classifications and
tally. Total: **case_check 6,393 passed / 0 failed** (was 5,145).

Two defects were caught by the machinery during the build, both in
the new case's own authoring, both fixed before this report: the
adjudication initially lacked the `mondo` field the generic ontology
section requires to agree three ways (ground truth / adjudication /
hypothesis), and the profile's first trajectory assertion compared
unrounded checker boards against the runner's rounded display values
(the assertion now rounds, as the machinery's own display does).

## 8. Honest limits

- **Four cases are not a calibration series.** The priors are
  verify-flagged authoring choices in every case, this one included;
  nothing in the module yet supports claims about how the board's
  probabilities perform across a case population. The P7 target
  remains 12 cases. What case #4 adds is a new *shape* (localization,
  a backwards-moving board, a pre-installed anchor), not a fourth
  point on a calibration curve anyone should draw.
- **The electrodiagnostic LR is a floor used as a point.** C25
  states bounds (>85% / >95%); 17.0 is the smallest LR+ the
  parameter supports. The direction of the approximation is
  disclosed wherever the number appears, but a reader should know
  the stage-4 posterior (0.9943) is, on this leg, *understated*
  relative to the parameter — and that the case's conclusions do not
  depend on the difference (the cervical crossing happens on the
  conjunction in the adjudication, of which the LR is one part).
- **The ultrasound LR inherits a pooled, heterogeneous pair.**
  Fowler's 19 studies used different CSA cutoffs (6.5–12 mm²) and
  different reference standards; the patient's 13 mm² sits above the
  cutoff range, which cuts in the case's favour, but the LR itself
  is the pooled one and is labelled as such.
- **Independence is assumed, as always in this module.** The board
  multiplies LRs as if findings were conditionally independent
  (parameters.json, `lr_combination_rule`); hypalgesia and the Katz
  diagram are plainly not fully independent observations. The board
  is a teaching instrument; the guideline instrument (CTS-6) is
  evaluated separately and reported alongside, and the diagnosis
  rests on the adjudicated conjunction, not on any single product.
- **Diabetes and entrapment are not independent stories.** The
  adjudication states it: excluding polyneuropathy as the
  explanation of *this* presentation does not make her diabetes
  irrelevant to her median nerve, and the case does not claim
  otherwise.
- **The expert-review gate remains UNMET** — for this case as for
  the module: no named reviewers exist, the case's status is
  `dual-sourced-draft`, and its scores are formative-only. Nothing
  in this milestone changes that, and nothing fabricates movement
  toward it.
- **The disposition is the exercise's.** A real service would put
  the splint/injection/release choice to the patient; the case says
  so in `alternatives_considered`.

## 9. Gate matrix

- `tools/case_check.py`: **6,393 passed / 0 failed** (generic
  machinery over all four cases + profiles for cases 1–4).
- All other Python checkers in `tools/` (assembly, cv, dig, endo,
  the four FMA tranche checkers, integ, lymph, major_nerve, muscle,
  muscle_assembly, nerve, repro, resp, skeletal, uri): exit 0.
- `tools/theatre_check.py`: 245 checks / 0 failures — Theatre
  untouched, re-verified.
- Physiology engine: `cargo test --release` **25 passed / 0 failed** —
  untouched by this milestone (the case declares no physiology link),
  re-verified at the standing count.
- Native shell verify: not re-run — this milestone touches nothing
  under `native/` or `web/`; the standing GPU-stage limitation on
  this VM is unchanged from M28–M40.
- Regression: cases #1–#3 case files and all three debriefs are
  SHA-256-identical before and after this milestone (case files
  9cf8b808…, 4c3d8d48…, 46c2b61b…; debriefs d16f7209…, 492727f4…,
  5f5005a5…), with the full runner re-run over all four cases in
  between. No data file outside `cases/` changed except
  `tools/case_check.py` (the new profile) — geometry packs
  byte-identical by non-touch.

## 10. Files of this milestone

- `cases/case.carpal-tunnel.004.json` (new)
- `cases/attempts/attempt.case-carpal-tunnel-004.model-learner.json` (new)
- `cases/debriefs/debrief.case-carpal-tunnel-004.model-learner.json` (generated)
- `cases/parameters.json` (extended: C23–C29, 5 LR derivations,
  dated C10/C11 Milestone 41 addenda, `extended_at_milestone` 41;
  workbench constants unchanged)
- `tools/case_check.py` (`profile_case4` added and wired)
- `cases/README.md` (module line, register range, case-4 entry,
  attempts note, check count)
- `MILESTONE-41.md` (this file)

## 11. Next steps

- **Theatre procedure #3 — carpal tunnel release.** This case's
  disposition names an operation the Theatre does not have; a
  CTA-authored release (with its own safety gates — the palmar
  cutaneous and recurrent motor branches are the structures a
  release must not take) would close the case→theatre loop for a
  non-abdominal procedure for the first time, and case 4's
  management section is its declared trigger.
- **Case #5 candidates:** a second localization case at a different
  level (ulnar neuropathy at the elbow, against the same machinery),
  or a return to the loop pattern (a case whose prior probability is
  set by a Theatre trace). The calibration-series gap (§8) argues
  for volume; the shape-coverage gap argues for variety. Either is
  defensible; neither is started here.
- **The recurrent-branch gap** is now load-bearing in two places
  (M35's unresolved phrase; this case's thenar link). It closes only
  with geometry or a sourced branch record — it belongs to the
  geometry line (the M34 decision), not to case work.
