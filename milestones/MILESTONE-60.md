# Milestone 60 — Case #8: the physiology link to the calcium axis

**Status: built and verified locally; landing batch handed to the parent agent.**

Case #8 (post-thyroidectomy hypocalcemia, Milestone 57) was the
only case in the series whose central trajectory the physiology
engine could not speak to at all: its `physiology_link` carried
the pinned circulation baseline by data-identity with case 1 and
then stated the gap in terms — *"THE ENGINE HAS NO CALCIUM
AXIS"* — because at Milestone 57 there wasn't one. Milestone 58
built the axis and closed its dossier by naming this link as
the next step. This milestone makes it: the case's patient is
now pinned to the engine's PTH-loss arm at her own postoperative
marks, the recorded outputs are the engine's measured values
from a run made in this session, the checker verifies the link
on every run, and the case's three statements of the old gap
have been replaced by the link description and the Milestone 58
consonance result — including the POD1 disagreement, carried
verbatim, not smoothed.

## The arm the link pins

The scenario is the shipped Milestone 58 arm, exactly as
defined in `physiology/src/cases.rs` (`run_calcium_arm`,
`CalciumArmKind::PTHLoss`) and driven by the command recorded
in the link:

    cd physiology && cargo run --release -- run calcium

- Protocol: the house engaged-engine skeleton (settle, baseline
  window, engagement at tick 6000). At engagement the arm
  applies `Event::SetPTHSecretion { capacity: 0.09 }` —
  parathyroid secretion capacity cut to 9%, in the code's own
  words *"the remnant fraction Case #8's measured POD2 PTH
  implies"*. Her glands were devascularised, not excised; the
  arm is that physiology with residual function, not a
  parathyroidectomy.
- The arm is UNTREATED. The case's disposition executes the
  trace-30 debrief's dp6 calcium-replacement protocol; that
  protocol is a management decision, not an input to the arm,
  and the comparison is against her untreated trajectory as
  filed (the Milestone 58 dossier's bound, carried here).
- Samples at 360 / 720 / 1440 / 2880 / 4320 min after
  engagement. The link records the engagement (resting) sample
  and the two samples at the case's own marks — 1440 min =
  postoperative day 1, 2880 min = postoperative day 2.

## The measurement of record

The values in the link were not taken from the Milestone 58
dossier's prose: the command above was run in this session
against the shipped release binary, and the link records what
it printed. The full listing is preserved at
`work/m60/run-calcium.txt`. The PTH-loss arm as measured:

| Mark | Ionized | Total | Corrected | PTH | (mmol/L; PTH pg/mL) |
|---|---|---|---|---|---|
| rest (engagement) | 1.2000 | 2.500 | 2.400 | 19.82 | |
| +360 min | 1.1685 | 2.434 | 2.328 | 3.15 | |
| +720 min | 1.1322 | 2.359 | 2.250 | 5.14 | |
| +1440 min (POD1) | 1.0605 | 2.209 | **2.096** | 7.53 | |
| +2880 min (POD2) | **0.9357** | 1.949 | **1.830** | **8.08** | |
| +4320 min | 0.8407 | 1.752 | 1.629 | 8.10 | |

Arm hashes as printed: circulation trace hash
`0x4a8b2abf3b82eb43` — identical to the disabled-axis A/B
twin's, as the resting-zero construction requires (the axis
never enters a circulation derivative, so this link leaves the
case's pinned baseline untouched); respiratory trace hash
`0x0125fcd2dd4cc67a`. Every figure agrees with the Milestone 58
dossier's prediction-vs-measured and consonance tables to the
printed digit.

One prose discrepancy in the Milestone 58 dossier is recorded
here rather than silently inherited: its consonance section
twice calls this arm the "capacity-0 limit". The shipped code
(the `cases.rs` doc comment, the `main.rs` section title —
"PTH LOSS — secretion capacity 9%"), the parameters, and the
measured values are the 9%-remnant arm's; at capacity 0 the
PTH state would relax toward the sigmoid's floor, not to
8.08 pg/mL. The numbers were always the 9% arm's. Milestone
58's dossier is not edited — it is the historical record —
and this note is the correction of record.

## The link, in the case file

`physiology_link` keeps its baseline half byte-for-byte (role
line extended) and gains, in the case-6 idiom of a named
recorded-outputs block inside the link:

- `calcium_command` — the command above.
- `calcium_scenario` — the arm definition, the untreated
  bound, the marks, and the A/B hash identity.
- `calcium_recorded_outputs` — `resting` / `pod1_24h` /
  `pod2_48h`, each {ionized, total, corrected, PTH} at the
  command's print precision.
- `calcium_arm_trace_hash` / `calcium_arm_resp_hash` — as
  printed by the run.

## How the checker verifies it (and why not by re-running)

`tools/case_check.py`'s case-8 profile now asserts, on every
run:

1. The baseline half by data-identity with case 1, unchanged.
2. The gap statement records the closure and carries the
   +0.146 figure.
3. The recorded outputs' structure, with the resting sample on
   the axis's gated resting values.
4. **The pin of record:** the recorded POD1/POD2 values and
   the arm circulation hash are identical to the values in
   Milestone 58 dossier's measured tables (the checker reads
   the dossier and requires the strings to be there and the
   numbers to match).
5. **Consonance, recomputed from the case's own atoms:**
   POD2 corrected |1.830 − 1.83| < 0.005 (against the
   adjudication's own SI figure), ionized |0.9357 − 0.94|
   < 0.0051, PTH |8.08 − 8| < 0.1.
6. **The disagreement, checked as a band:** the POD1 gap,
   computed as the arm's 2.096 minus the case's POD1 corrected
   (7.8 mg/dL × 0.25 = 1.95), must lie in (0.10, 0.20) —
   measured +0.146. A future "improvement" that silently
   closed the gap would fail this check, as it should.

The command is NOT re-run by the checker, deliberately, and
the case's `verification` text says so: the four-arm listing
took **75 minutes of wall time** in this session (the PTH-loss
arm alone spans 4,320 simulated minutes), and
`physiology/src/main.rs` records of this exact command that
*"nothing re-runs it under a timeout (the case workbench
re-runs `run respiratory`, not this command)"*. The engine's
own authors drew the line there; the link follows the module's
other pinning idiom (data-identity, as cases 3, 7 and this
case's baseline use) instead of the re-run idiom of cases 1
and 6, whose commands are cheap. The honest cost of that
choice is stated under Limits below.

## The consonance — and the disagreement, verbatim

From the Milestone 58 dossier, carried into the case's
`gap_statement` and `ground_truth.engine_state` without
softening:

At **POD2 (48 h)** the consonance is as close as the module's
lumping permits: ionized 0.9357 against her 0.94 (Δ −0.004),
corrected 1.830 against 1.83 (Δ 0.000 at print precision),
PTH 8.08 against 8 (+0.08).

At **POD1 (24 h)** the engine runs HIGH: corrected 2.096
against her 1.95 mmol/L, **a gap of +0.146**. The disagreement
is disclosed, not tuned away, and its candidate causes are
named in the case's own terms: (i) her glands were
devascularised mid-operation and her POD1 draw integrates an
earlier effective insult start than the arm's t = 0 step;
(ii) her albumin is 3.6 g/dL post-operatively against the
arm's resting ~45.7 g/L, so part of her total-calcium fall is
a binding fall the arm's resting-albumin circulation does not
reproduce; (iii) the arm's bone transient is at its slowest
exactly here (formation τ = 10 d), so the model's first-day
fall is carried mostly by the renal limb. A tuning path
existed and was REFUSED on the record at Milestone 58: raising
the renal amplitude toward ~0.55 closes much of the POD1 gap
but drives the chronic untreated equilibrium to ~0.62 mmol/L
— a value no consulted source supports.

One further honesty point, which the link's framing must not
obscure: the arm's 9% capacity was chosen *from* her measured
POD2 PTH, so the PTH agreement at POD2 is substantially by
construction. The load-bearing agreements are the two calcium
values at POD2 — ionized and corrected — which are outputs of
the dynamics, not inputs; and POD1, where nothing was fitted,
is where the model and the patient part company by +0.146.
The link claims exactly that much, no more.

## Case-file edits — the complete census

The case JSON was edited by raw-text splice (never
re-serialised); a parsed semantic diff of before/after proves
the entire change is these ten paths and nothing else:

- changed prose: `synthetic_note` (one clause),
  `ground_truth.engine_state`, `physiology_link.role`,
  `physiology_link.gap_statement`,
  `physiology_link.verification` (a Milestone 60 paragraph
  appended, in the case-1 re-recording manner);
- added: `physiology_link.calcium_command`,
  `calcium_scenario`, `calcium_recorded_outputs`,
  `calcium_arm_trace_hash`, `calcium_arm_resp_hash`.

No finding, lab, measurement, hypothesis, score, stage,
classification or disposition moved. The `synthetic_note`
clause is flagged as this milestone's one judgement call: the
brief named the link and limitation blocks, and the note is
the case's provenance statement, not clinical content — but
it carried the same now-false present-tense claim ("the
physiology engine has no calcium axis"), and leaving it would
have left the case contradicting its own link. The repair is
minimal (the clause now records that the axis postdates the
operation's record and that the case cross-checks against it)
and is recorded here so it can be reverted if judged out of
scope. The trace-30 debrief's own complication text, which
also states the old position, is the operation's shipped
record and is NOT touched — the case now quotes it as history,
which is what it is.

`cases/README.md`'s case-8 entry carried the same gap
sentence; it now records the closure with the same figures.

## Checker deltas

- **case_check: 13,135 → 13,160 passed / 0 failed** (+25: the
  physiology section's 1 assertion replaced by 6, +5; and the
  generic composite-score walk visits every JSON key, so the
  20 new keys in the link add 20). All six Milestone 60
  assertions pass (see the enumeration above).
- **theatre_check: 736 / 0** — unmoved; all 30 debriefs
  untouched, the trace-30 loop assertions in the case profile
  pass as before.
- **Cases #1–#7 byte-identical** (sha256 against the
  pre-milestone manifest, all OK).
- **Every other `tools/*_check.py` exits 0** (21 checkers run,
  including imaging_toolkit and assembly), and
  `tools/verify_web.js` reports ALL CHECKS PASS.
- **readme_check: exactly one failure, the expected one** —
  R9, "case_check total == its printed output" (README 13135
  vs printed 13160). README.md and `tools/readme_check.py`
  were NOT touched, per the milestone's constraint. **The new
  figure for the README's next pass: case_check 13,160**
  (cases still 8; nothing else the README prints moved).

## Honest limits

- **The pin's strength is bounded, and the bound is named.**
  The checker pins the recorded outputs against the Milestone
  58 dossier (a document) and against the case's own labs
  (arithmetic). If the engine's calcium arm is changed in a
  future milestone, this pin will not notice — the dossier
  will still say what it says. What guards the arm itself is
  physiology's own validate (its perturbation-case gates carry
  magnitude bands from the frozen solver pass). A milestone
  that moves the axis owes this link a re-measurement, exactly
  as the resting-baseline links were re-recorded at
  Milestones 21/25/26/30. The link's `verification` text
  records the mechanism so the obligation is visible in-case.
- The arm is a lumped model: the fixed 0.48 ionized fraction,
  the absent phosphate/magnesium/FGF23 axes, and the absent
  parathyroid-recovery ramp are Milestone 58's disclosed
  limits and are inherited here unchanged. Her implied
  ionized fraction is 0.514; the POD2 corrected agreement is
  partly that arithmetic cancelling the content gap
  (Milestone 58's note, still true).
- The comparison window is POD1–POD2 because those are the
  case's filed marks; the arm's 72 h continuation (0.8407) is
  recorded in the run listing but deliberately not linked —
  the case files no POD3 value to read it against.
- As with every case: the expert-review gate remains
  **UNMET** (no named reviewers), the content status is
  `dual-sourced-draft`, and all scores are formative and
  educational only. This is a simulation, not a clinical
  device.

## Landing batch

Four files, all local, handed to the parent agent to land
under the ANATOMICA upload-as-you-finish rule:

- `cases/case.post-thyroid-hypocalcemia.008.json` — 67,489 B,
  sha256 `c170af9584a6eb0eedeed6aa8500a11b48df112e1ae624103f8e9e2e6abc210f`
- `tools/case_check.py` — 130,761 B,
  sha256 `d79ab9dace392b079855373cd78cecb5248daa78735723a22fb411bca6639643`
- `cases/README.md` — 25,441 B,
  sha256 `1209a170ef61ac73605fa9f9baf6f6e712e05e4fa345396625d7846696bc865a`
- `milestones/MILESTONE-60.md` (this dossier)

Working record (not landed): `work/m60/run-calcium.txt` (the
full four-arm listing as measured), `work/m60/case8-before.json`
and `work/m60/before-hashes.txt` (the pre-milestone state),
`work/m60/case_check-before.txt` / `case_check-after.txt`,
`work/m60/edit_case8.py` (the splice script, with its
assertions).
