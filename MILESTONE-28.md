# Milestone 28 — Theatre procedure #2: laparoscopic appendicectomy

**Status: built and verified locally. Not uploaded.** The Theatre
module now carries two procedures on one engine. Procedure #2 —
laparoscopic appendicectomy (`proc.appy.lap`) — is authored by the
same cognitive-task-analysis discipline as Milestone 17's
laparoscopic cholecystectomy, runs on the same physiology engine,
and is scored by the same component scheme (no composite score).
Nothing in the cholecystectomy procedure, its traces, or its
debriefs changed: the five chole debriefs are **byte-identical**
(sha256) to their pre-Milestone-28 state, and the Cases module is
untouched (`case_check` still 3,280/0).

## 1. What was built

- `theatre/procedures/proc.lap-appendectomy.json` — the procedure
  model: 9 phases, 21 steps, **47 microsteps**, **36 required** in
  the standard configuration. Every microstep carries named cues,
  instruments, and at least one consulted source.
- The engine (`theatre/src/`) was generalized, not forked: the
  runner now loads all procedures, dispatches each trace by its
  `procedure` field, reads gate criteria from the procedure file,
  resolves drug/checklist actions by their `fulfills` markers, and
  computes the appendicectomy-specific rules (artery control,
  closure–base-condition matching, retrocecal deferral, drain and
  lavage discipline) alongside the cholecystectomy rules.
- Five shipped traces (`trace-06` … `trace-10`), five debriefs in
  the existing format, eight additional engine probes in the test
  suite (16/16 tests pass), and the independent checker extended
  to both procedures: **245 checks, 0 failures** (Milestone 17:
  131).

## 2. Decomposition census

| Configuration | Required microsteps |
|---|---|
| Standard (uncomplicated, standard anatomy) | 36 |
| Clean attempt, closure chosen at dp3 | 37 |
| Pelvic variant | 38 |
| Retrocecal variant (mobilization pair added) | 39 |
| Perforated severity (suction + antibiotic course added) | 39 |

5 decision points (grading; base unidentifiable; closure method;
cecal injury; postoperative plan), 13 error definitions, 12
structure-register entries (9 resolved to Body Model records,
3 documented absences: the taeniae-convergence landmark, the
retrocecal space, the pelvic region — none is a Body Model record).

Body Model honesty, recorded in the register: the appendix and
cecum are real records (`canal.appendix`, `canal.cecum`, compound
clinical record `dig.cecum-appendix`, Milestone 11). The
appendiceal artery **exists as an inventory record**
(`artery.appendicular-artery`) but has **no clinical record** in
`cardiovascular.json` — the register says exactly that, and the
checker asserts it, in deliberate contrast to the cholecystectomy,
whose cystic artery is absent from the data entirely.

## 3. Safety gates, as the specialty defines them

**gate.base-id** (the appendicectomy analogue of the Critical View
of Safety; sources T16, T19, design/05): all three criteria must be
demonstrated before any clip or division — (1) the taeniae coli
traced to their convergence at the cecal pole, (2) the appendix
seen arising from that convergence, (3) the condition of the base
assessed (healthy / inflamed / necrotic). Dividing a presumed
appendix before this gate opens resolves, anatomically, to a
**full-thickness cecal injury** and **fails the attempt**,
mirroring the CVS rule's spirit.

**gate.artery-control**: the appendiceal artery identified, then
occluded, before the mesoappendix or the appendix is divided.
Enforced as a computation rule: division with the artery
uncontrolled starts a haemorrhage the physiology engine
integrates until control (see §5).

**gate.pre-division-pause** (checkpoint): a structured pause
before division, fulfilled by the same WHO-checklist discipline as
Milestone 17. No appendicitis guideline states this pause; its
source is recorded honestly as the project's own design (T20).

## 4. Variants and severity branches — evidence first

- **Retrocecal position** (variant, shipped trace): prevalence
  43.5% in the 377-cadaver series of de Souza et al. 2015 (T16),
  with Wakeley's 10,000-case figure of 65.28% recorded in the same
  source — both numbers are in the procedure file, neither is
  silently picked. The correct adaptation is scored: cecal
  mobilization (m3.5/m3.6) becomes required, and an identification
  claimed *before* mobilization does not open the gate (the
  criterion is deferred by the engine; a probe proves division in
  that state still fails with the cecal injury).
- **Pelvic position** (variant, shipped trace): 9.3% in the same
  series (31.01% in Wakeley's). Delivery of the appendix out of
  the pelvis (m3.7) becomes required.
- **Perforated / gangrenous severity**: management follows the
  WSES Jerusalem guidelines 2020 (T14) and the SAGES systematic
  review (T15), and the rubric scores *against* habit where the
  evidence says so:
  - suction of contamination is required; **lavage is scored as
    an error** (T14 Rec 4.8, strong recommendation 1B: suction
    alone; T15 KQ5: no significant difference) — a probe proves a
    perforated attempt that omits suction computes an
    intra-abdominal abscess as a postoperative consequence;
  - **routine drain placement is scored as an error** (T14:
    drains discouraged in adults; T15 KQ6) — the one scored
    exception is a drain placed after a repaired cecal injury;
  - a postoperative antibiotic course is **required** when
    complicated and scored as an error when uncomplicated
    (T14: single preoperative dose suffices if uncomplicated;
    ≤3–5 days when complicated with source control).
- **Closure method is a scored decision** (dp3), matched to base
  condition: endoloop or polymeric clips on a healthy base;
  endostapler when the base is inflamed or necrotic (T14:
  endoloops/suture or polymeric clips recommended, staplers in
  complicated cases per judgment; T17 Cochrane: no complication
  difference, very-low-quality evidence; T18). An endoloop on a
  necrotic base computes a **stump leak** — a postoperative
  consequence in the debrief, never a random event. Division with
  no closure at all computes the same leak.

## 5. Complications are computed, as in Milestone 17

- **Appendiceal artery haemorrhage**: bleed rate
  `bleed_rate_appendiceal_artery_ml_s = 1.5 mL/s` — **verify-flagged**
  (no measured rate was consulted; placed between the existing
  cystic-branch and cystic placeholders). Probe: division at
  t=540 s, control at t=840 s → 300 s × 1.5 mL/s = **450 mL**,
  agreeing to <5 mL between the event integral and the engine's
  volume identity (which now also carries the Milestone 25/26
  intake/urine and protein state).
- **Cecal injury**: from division before base identification
  (trace-08), resolved onto `canal.cecum`.
- **Stump leak** and **intra-abdominal abscess**: postoperative
  consequences computed from closure mismatch / uncontrolled
  contamination, scored through the management component.

## 6. Trace outcomes (actual debrief numbers)

| Trace | Verdict | Checklist | Safety | Process | Physio | Mgmt |
|---|---|---|---|---|---|---|
| 06 clean, endoloop | PASS | 37/37 (100%) | 4/4 | 5/5 | 7/7 | n/a |
| 07 retrocecal variant | PASS | 39/39 (100%) | 4/4 | 5/5 | 7/7 | n/a |
| 08 divide-unidentified | **FAIL** @ t=1740 s | 19/36 (52.8%) | 0/4 | 2/5 | 7/7 | 5/5 |
| 09 perforated, stapler | PASS | 39/39 (100%) | 4/4 | 5/5 | 7/7 | n/a |
| 10 pelvic variant | PASS | 38/38 (100%) | 4/4 | 5/5 | 7/7 | n/a |

Trace-08 mirrors trace-02 deliberately: the clip lands on the
cecum first (clip-on-cecum, t=1680 s), the division resolves to
the cecal injury, and exemplary management (5/5) does not rescue
the verdict. All five cholecystectomy traces still meet their
expectations with debriefs byte-identical to baseline.

## 7. Verify-flagged parameters — listed openly

`parameters.json` now holds 14 parameters; **9 are verify-flagged**
(placeholders from Milestone 17's discipline, none presented as
measured): the three cholecystectomy bleed rates, five physiology
rubric bands, and the one added here —
`bleed_rate_appendiceal_artery_ml_s` (1.5 mL/s). Sources T14–T20
were added for this milestone (WSES Jerusalem 2020; SAGES
systematic review; de Souza 2015 positional anatomy; Cochrane
stump-closure review; Can J Surg 2012 endoloop-vs-stapler;
operative-technique chapters; project sources). The shared
rubric bands remain placeholders pending a sourced rubric —
GOALS/OSATS rubric data is still not populated for either
procedure, by the same stated rule as Milestone 17.

## 8. Expert-review gate — UNMET, stated verbatim

> "UNMET — design/05 and design/10 require at least two named
> independent expert reviewers with Delphi sign-off before this
> procedure's content status can rise above dual-sourced-draft.
> No reviewers exist for this project; the gate is reported as
> unmet, never satisfied on paper."

The appendicectomy's review block carries this status with
`recorded_reviewers: []`, exactly as the cholecystectomy's does;
the checker asserts it for both. Content status:
`dual-sourced-draft`. Scores are **formative-only**.

## 9. Verification matrix

- theatre `cargo test --release`: **16/16** (incl. 8 new
  appendicectomy probes).
- theatre `validate`: both procedures pass (appy 9/21/47, 36
  required, 12 structures, 3 gates, 5 decision points, 13 errors,
  2 variants; chole unchanged 9/21/86, 64 required).
- `tools/theatre_check.py`: **245 checks, 0 failures**.
- `tools/case_check.py`: **3,280 passed, 0 failed** (Cases
  untouched; case #2's link to the cholecystectomy debrief
  re-verified against the unchanged file).
- physiology `validate`: ALL HARD GATES PASS.
- `tools/verify_web.js`: ALL CHECKS PASS.
- `tools/assembly_check_all.py`: ALL GATED CHECKS PASS.
- native verify: 99 PASS / 0 FAIL structural assertions; the
  GPU-render stage cannot run in this shell environment (no
  adapter) — no native file was changed by this milestone.

## 10. What remains

- Interactive 3D manipulation of either procedure is still
  future shell work; traces remain scripted.
- A third case for the Case Workbench could link to an
  appendicectomy debrief the way case #2 links to trace-02 — not
  done here; the Cases module was deliberately undisturbed.
- The verify-flagged bleed rate and rubric bands await sourced
  values; the expert-review gate awaits real reviewers.
- Subhepatic and other rarer positions are recorded in the
  variant sources but not modeled as variants (below the
  project's ≥1%-prevalence variant gate in the consulted series'
  primary figures, or unquantified there).

## 11. Next steps

Per the standing queue: physiology depth (lymphatic return as a
dynamic, hormonal axes) or imaging MPR, then Case Workbench
case #3 — which can now close the same hash-real loop onto an
appendicectomy debrief.
