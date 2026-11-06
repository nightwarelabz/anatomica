# Milestone 22 — Case #2, the loop case: the Theatre's bile duct injury comes back as a patient

Milestone 20 named its own next step #1: "the trace-02
bile-duct-injury case (loop case #2)". Milestone 17's trace-02 is a
laparoscopic cholecystectomy that fails — a common bile duct divided
before the Critical View of Safety, a Stewart–Way class III injury,
recognised and managed on the table (drain, refer). Milestone 20's
case 1 is the patient *before* that operation: acute cholecystitis,
adjudicated mechanically, handed off to `proc.chole.lap`. This
milestone closes the loop the master plan describes: case 2 is the
same patient, four days after the operation trace-02 performed
badly, presenting with the injury's sequelae — and the case's
operative-history evidence is the shipped trace-02 debrief itself,
verified field by field, not retold.

Everything is built on the Milestone 20 machinery. The runner and
checker were generalised (parameterised over every case in
`cases/`), not forked; case 1's computed debrief is bit-for-bit the
same on every scored value after the migration (see §6).

## 1. The case — `case.post-op-jaundice.002`

54-year-old woman (case 1's patient), postoperative day 4 after
laparoscopic cholecystectomy at which a bile duct injury was
recognised, drained, and referred (trace-02, decision dp4). Now at
the hepatobiliary centre: deepening jaundice, dark urine, pale
stools, pruritus; afebrile; a surgical drain in situ with falling
output. Four stages, 25 findings, 7 labs, 1 measurement, 6 orderable
tests, 6 hypotheses.

**Stage 1 — referral and examination.** The operative history is
stage-1 evidence, quoted from the debrief (see §2): transection of
the common bile duct at the index operation, clip placed at t=1860 s
(class I mechanism), duct divided at t=1920 s (class III injury),
drain-and-refer at t=2220 s. Examination: jaundice, choluria, fecal
acholia, pruritus (the obstructive picture C14 describes for
complete occlusion); afebrile; no peritonism; drain output low and
falling.

**Stage 2 — the panel and the ultrasound.** Bilirubin 6.8 mg/dL
(C8 range 0.1–1.2); ALP 520 U/L (4.0× the cited ULN 129); ALT 96
(2.7× ULN 36); AST 88 (2.7× ULN 33) — the cholestatic pattern.
WBC 8.9 (inside C7's range, below TG18's 10.0 threshold); CRP
8 mg/L (below TG18's 10 threshold). Ultrasound: intrahepatic and
extrahepatic duct dilatation above the clip level; no collection.

**Stage 3 — ERCP (the attempt's error, available to any learner).**
Cholangiogram from below: distal duct clear, cut-off at surgical
clips, no filling above, nothing extracted. Consistent with — and
only with — a duct that does not continue past the clips. C14 states
ERCP's limits in exactly this anatomy: it cannot opacity ducts
upstream of a complete obstruction.

**Stage 4 — MRCP.** Complete transection of the common bile duct;
proximal stump measured 25 mm below an intact confluence; no stone
in any duct; no leak from a minor duct; no aberrant-duct involvement
(the absent findings do the excluding — they are recorded as
findings, not assumed). MRCP is, per C14, the gold standard for
complete morphological evaluation of a bile duct injury, showing the
anatomy proximal and distal to the injury.

## 2. The loop, demonstrated

The case file's `theatre_link` block names the shipped debrief
`theatre/debriefs/trace-02-divide-before-cvs.debrief.json`, records
its SHA-256 (**7bb98df467e1e35992464b5ef4548d7b51e13c83bf6d0dbe27556b5a3af301b6**,
15,184 bytes), and declares the fields the case relies on. The
checker re-reads the file, recomputes the hash, and compares every
field. What it matched, verbatim from the debrief:

- `verdict` = **FAIL**; `failed_at_s` = **1920.0**; `fail_reason`
  contains **err.divide-unidentified** ("an unidentified critical
  structure (duct.cystic-duct) was divided before the Critical View
  of Safety").
- `checklist` = **32/64** completed; `safety_gate.points` = **0**.
- `management` = **5/5** — recognition and escalation scored full
  marks in the Theatre and *do not rescue the case*, exactly as they
  did not rescue trace-02's attempt.
- Complication `bile-duct-injury`: Stewart–Way class **III**,
  `resolved_structure` = **duct.common-bile**, `t_onset_s` = 1920.0,
  `recognised` = true. Complication `clip-on-common-bile-duct`:
  class **I (mechanism)**, t=1860.0.
- Decision **dp4 = drain-refer** at t=2220.0; the drain microstep
  **m7.6** ("Place a closed drain to the gallbladder fossa") is
  present in the event log — the drain in case 2's stage-1
  examination is that drain.

Change any byte of that debrief and the case fails its checker. The
patient's history is a computed artifact of another module, held to
the same standard as a lab value.

## 3. The classification, computed — Strasberg E1 / Bismuth I

The case declares a `classification` criteria block (the third
block kind, after Milestone 20's grouped TG18 blocks and k_of_n
Atlanta): ten named inputs, each a disjunction of evidence atoms,
and nine ordered rules transcribed from C14's Table 2 mapping
(Strasberg A–D for leaks/occlusions of minor or aberrant ducts;
E1–E5 by stump length and confluence state: stump >2 cm = Bismuth
I/E1; <2 cm = II/E2; confluence intact but stump <1 mm = III/E3;
confluence destroyed = IV/E4; main-duct injury plus an isolated
right duct = V/E5).

Evaluated mechanically at each stage: **stages 1–3, not yet
classifiable** (the level-determining evidence has not been
revealed; the operative history establishes *transection* but not
its level). At stage 4 the inputs resolve — transection true (three
independent atom paths: operative history, ERCP cut-off, MRCP),
confluence intact (the MRCP finding, whose *absence* would flip the
input), stump 25 mm ≥ 20 mm true, <20 mm false, every leak/aberrant
input false on recorded absent findings — and rule E1 fires:
**Strasberg E1 / Bismuth I**. The adjudication block declares the
expected result; the checker recomputes it from the findings and
fails the build if they disagree. Nothing about the class is
asserted anywhere it is not also computed.

## 4. The differential and the scoring discipline

Six hypotheses: major bile duct injury (adjudicated truth), retained
CBD stone (MONDO:0006699), minor bile leak, acute cholangitis
(MONDO:0001930), hepatocellular injury, and the declared residual.
Three carry **no Mondo class**: an EBI OLS search in-session found
no Mondo class for bile duct injury, bile duct stricture, or bile
leak (MONDO:0001710, perforation of bile duct, is a different lesion
and was not substituted); the hypotheses carry `mondo: null` with
the absence stated, the same discipline that dropped acute
hepatitis from case 1 rather than misapply a chronic-flavoured
class (MONDO:0002251 is defined ">6 months" — recorded, not used).

The whole case carries **exactly one likelihood ratio**: MRCP
showing no stone, LR− 0.0794 against the retained stone, computed
from C15 (single-centre retrospective, n=691; MRI/MRCP sensitivity
92.7%, specificity 91.9% for CBD stones; LR− = (1−0.927)/0.919).
It is labelled single-study wherever used. Every other finding
moves the case through the criteria and classification blocks, not
through invented numbers: the workbench board therefore sits at the
priors (injury leading at 0.35 from stage 1) until stage 4, when
the stone falls 0.20 → **0.0195**, across the declared 0.02
rule-out line. The workbench Brier is flat at 0.5150 for three
stages and improves only to 0.4053 — reported as-is; that flatness
is what one honest LR looks like.

All six priors are verify-flagged case-author values. No consulted
source publishes a probability distribution over the causes of
day-4 post-cholecystectomy jaundice; the case says so on every
prior rather than dressing author judgement as epidemiology.

**TG18 cholangitis, mechanically:** group B met (bilirubin ≥2;
enzymes >1.5× ULN), group C met (duct dilatation), **group A unmet
at every stage** — afebrile, WBC 8.9 ≤ 10.0, CRP 8 < 10 — so the
status is *not suspected* throughout, computed, while the
management block arms cholangitis surveillance as the case's live
risk: an obstructed, undrained system is the setup for it, and the
pathway on fever is named (antibiotics plus percutaneous
transhepatic drainage — C14 names PTBD as useful for septic
complete obstruction precisely because ERCP cannot reach above it).

## 5. The attempt — a designed, scored failure

The model learner anchors on the retained stone: the treatable
diagnosis. Boards: stone 0.40 → 0.45 → 0.30 → 0.25; injury
0.25 → 0.30 → 0.45 → 0.60. It orders the right first panel (CBC,
CRP, LFTs, ultrasound — all scored criteria-completing), then the
attempt's pivotal error: **ERCP at stage 2, as therapy for the
presumed stone, before the anatomy is defined.** The ERCP is scored
**non-contributory** — it changed no board, no criterion, and no
classification input the record did not already establish. MRCP,
ordered one stage late, is scored **discriminating** (it carries
the case's only rule-out crossing). At stage 4 the learner commits
to the injury with the correct disposition — but still holds the
stone at 0.25, one stage after the workbench ruled it out at
0.0195: **exactly one anchoring event**, (stage 4,
hyp.retained-cbd-stone), computed by the declared rule. Learner
Brier: 0.7550 → 0.7118 → 0.4148 → 0.2306. Resource tally:
225 min, 25 cost units (verify-flagged accounting placeholders, as
in case 1). The PEARLS debrief is carried in the attempt file and
names the consider-the-opposite prompt the design prescribes: *if
this is the injury I already know about, what would the stone story
have to explain away?*

**Disposition (stage 4, as committed):** the patient is already at
the hepatobiliary centre the trace-02 referral named (C14 statement
7.3's pathway, effected). Postoperative day 4 places her in C14's
**72-hour-to-3-week band** (statement 7.4 — the band is recomputed
from `postoperative_day` by the checker): no collection exists, so
there is no drainage target; no infection, so no antibiotics (C14:
antibiotics may not be required in obstruction without leak or
sepsis); the drain is monitored; cholangitis surveillance is armed.
Definitive management is C14 statement 4.2's treatment of choice
for a major injury: **Roux-en-Y hepaticojejunostomy, after a
minimum of 3 weeks**, once the acute situation has resolved. ERCP
has no definitive role — it cannot bridge a transection.

## 6. Machinery changes (no fork)

- `cases/parameters.json`: sources **C14** (WSES 2020/2021 bile
  duct injury guidelines, Birindelli et al., World J Emerg Surg
  2021;16:30), **C15** (Cureus 2025 MRI/MRCP accuracy study),
  **C16** (project loop outputs) appended; C10/C11 consulted texts
  extended with the Milestone 22 OLS verifications (MONDO:0006699;
  HP:0001396 cholestasis, HP:0000989 pruritus; the recorded Mondo
  absences); one LR derivation added. Workbench constants unchanged.
- Case 1 migrated to declared criteria blocks: its TG18
  cholecystitis evaluation gained explicit `status_rules` (the
  suspected/definite logic that Milestone 20's runner hard-coded),
  and its cholangitis and Atlanta evaluations — computed by
  hard-coded functions at Milestone 20 — are now declarative
  `criteria_blocks` in the case file (including the adjudicated
  "pain not characteristic" judgement, carried as a declared
  constant atom with its basis, so the judgement is data).
- `tools/case_run.py` rewritten as one generic runner: discovers
  every case and attempt, evaluates grouped / k_of_n /
  classification blocks and the TG18 severity grade from the case
  files alone, and writes each debrief. Case 1's regenerated
  debrief was diffed against the shipped Milestone 20 debrief:
  **every computed value identical** (boards, Briers, the single
  anchoring event, order classes 2/3/2/1, tally 265/20, TG18
  definite at stage 3, Grade I, three not-assessed Grade III
  items). Differences are additive (a `criteria` block per stage)
  and cosmetic (clearer item names in order bases; the generator
  string).
- `tools/case_check.py` parameterised over both cases with per-case
  profile sections. Case 1's Milestone 20 profile is preserved in
  full (lab arithmetic, severity items, the imaging recount from
  the shipped bins — 2,720 voxels, slices 195–218, max cross-section
  file 212/186 — the physiology engine re-run against the recorded
  M21 baseline, the Theatre handoff, the FHIR bundle). Case 2's
  profile adds the lab arithmetic, the classification arithmetic,
  the timing-band recomputation, and the §2 loop verification.

## 7. Verification (all run this session)

- `python3 tools/case_run.py` — both cases run; case 2: workbench
  stone 0.20 → 0.0195 at stage 4 (ruled out), classification E1/I
  at stage 4, cholangitis not suspected at all four stages, one
  anchoring event, tally 225/25.
- `python3 tools/case_check.py` — **3,280 checks, 0 failures**
  (both cases' generic sections plus both profiles, including the
  field-by-field loop verification and case 1's full Milestone 20
  profile: imaging recount, engine re-run, FHIR consistency).

## 8. Honest limits

- **Two cases are not a calibration series.** The workbench now
  holds eight staged learner Brier scores across two cases (case 1
  ending 0.0276; case 2 ending 0.2306). Design/07's calibration
  claims remain a property of the P7 series target (12 cases),
  stated as unmet.
- **Review gate UNMET** — recorded verbatim in the case; no named
  expert reviewers exist and none were fabricated. Content status
  `dual-sourced-draft`; scores formative-only.
- **All six priors are flagged.** There is no consulted distribution
  for this differential; the numbers are the case author's,
  disclosed per-prior.
- **One LR, single-study.** C15 is a single-centre retrospective
  study, not a meta-analysis; the case's entire quantitative update
  rests on it, and the milestone reports the resulting flat
  workbench Brier rather than inflating the case with unsourced
  LRs.
- **HIDA and CT are discussed, not orderable.** C14 gives HIDA
  higher leak sensitivity but poor spatial resolution and a stated
  pitfall in large duct defects, and CT a first-line role for
  collections; this case has no collection and a duct-level
  question, so neither is on the order menu — the reasoning is
  recorded in the MRCP finding's text rather than silently omitted.
- **No physiology link, by design.** The engine has no biliary or
  obstructive state (Milestone 21 added a contractility effector,
  not a biliary one); case 2 declares no `physiology_link` and its
  ground truth states why. Linking the resting baseline
  decoratively would repeat, in reverse, the conflation case 1's
  honesty block exists to prevent.
- **No FHIR export for case 2.** The Milestone 20 export machinery
  covers case 1; extending it is mechanical and was left out of
  this milestone's scope rather than half-done.
- **The stump is one measurement.** 25 mm is authored case data
  (flagged as such), chosen above the 20 mm boundary so rule E1 —
  not a boundary dispute — is what the case exercises. A case at
  the E1/E2 boundary belongs in the series, with the boundary
  behaviour of the block tested there.

## 9. Next steps

1. Case series toward the P7 target of 12: the natural third case
   is this patient's *next* presentation if cholangitis declares
   itself (the surveillance the management block arms) — the loop
   extended one more turn, with TG18 cholangitis reaching
   "suspected" mechanically.
2. A boundary case for the classification block (stump at the
   E1/E2 edge; an E4 confluence-destroyed variant) to exercise the
   rules case 2's findings leave dormant.
3. The inflammatory/biliary engine perturbation (still the named
   gap in case 1's physiology link and now case 2's) — when the
   engine grows a biliary state, both cases gain a real link.
4. FHIR export generalised to every case; shell integration of the
   workbench (the cases remain JSON + CLI at this milestone).
