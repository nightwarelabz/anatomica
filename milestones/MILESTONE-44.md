# Milestone 44 — Theatre procedure #4: ulnar nerve decompression at the elbow

**Status: built and verified locally; not uploaded.** The Theatre
gains its fourth procedure, `proc.ulnar-decompression` — the
operation case #5 (`case.ulnar-neuropathy.005`, Milestone 43)
named in its disposition and could not hand off to, because the
Theatre did not hold it. The case now carries the handoff,
checker-verified, with its adjudication untouched. The procedure
is CTA-authored to the Milestone 17/28/42 discipline: phases,
steps and microsteps from data; the safety gate is the specialty's
identification-and-protection discipline, evaluated by the
generalized engine, not a fork; every complication is
engine-computed; scoring is formative-only with no composite; and
the expert-review gate is recorded UNMET, verbatim, as for all
three prior procedures.

The operation's distinctive problem is one the first three
procedures did not have: it has **two legitimate configurations**
whose comparative effectiveness the evidence does not decide, and
exactly one intraoperative finding — nerve instability — that the
specialty consensus says should choose between them. Milestone 44
encodes that honestly: the configuration decision is mechanically
real (it rewrites the attempt's required set), the instability
rule is enforced as the consulted evidence supports, and the
equipoise around everything else is stated, not resolved by fiat
(§4).

## 1. What was built

- `theatre/procedures/proc.ulnar-decompression.json` — 9 phases,
  12 steps, 35 microsteps (30 required in the standard in-situ
  configuration, 33 in the anterior-transposition configuration as
  enacted by the dp5 decision), 9 register entries, 2 gates,
  5 decision points, 7 error classes, 1 variant.
- Engine extensions in `theatre/src/runner.rs`, all additive and
  procedure-keyed, following the Milestone 28/42 generalization
  pattern: the ulnar critical-structure set (the five fascial
  division targets) and `on_divide_ulnar` with its two-way
  misidentification resolution; `ulnar_microstep_rules` (the
  repair state); the dp2 no-bailout arm; the **dp5
  anterior-transposition decision arm, which drops the in-situ
  completion microstep and inserts the four transposition
  microsteps into the required set** — the appendicectomy's
  decision-required mechanism (Milestone 28) generalized from a
  closure method to a whole configuration; three scoring-time
  consequence blocks (incomplete release, unaddressed
  subluxation, new compression site); the management wiring (the
  ulnar injury kinds join the nerve-injury control rule; the
  three postoperative consequences share the dp4
  return-to-theatre plan rule); and `build_pearls_ulnar`. The
  engine was not forked; §10 proves the prior procedures are
  untouched by it.
- Five shipped traces (`theatre/traces/trace-16…20`) and six Rust
  probes for the rules the traces do not exercise
  (`theatre/tests/runner_tests.rs`; suite now 28 tests).
- `theatre/parameters.json`: sources T29–T35 added; **no new
  parameter** (§8). No new instruments: the 28-instrument
  catalogue already carries everything this operation uses
  (scalpel No. 15, tenotomy scissors, Ragnell retractor, vessel
  loop, Freer elevator, bipolar forceps, arm tourniquet,
  operating microscope — all added at Milestone 42).
- Case #5's handoff (§7), `tools/case_check.py` profile revisions
  (case 5's handoff assertions in the Milestone 42 pattern;
  case 4's procedure-set assertion updated to the real
  four-procedure set), `tools/theatre_check.py` extension
  (355 → 463 checks), `cases/README.md` updated.

## 2. CTA sourcing (sources consulted in-session)

All seven new sources were consulted in-session and are
registered in `theatre/parameters.json` with their `carries`
texts. StatPearls' cubital tunnel syndrome chapter was attempted
and was reCAPTCHA-blocked, as at Milestones 39 and 42; it is
cited for nothing.

| id | source | what it grounded |
|---|---|---|
| T29 | *Surgical Approaches and Their Outcomes in the Treatment of Cubital Tunnel Syndrome.* Front Surg. 2018;5:48 (full text) | The compression-site span (arcade of Struthers → cubital tunnel → distal Osborne's ligament) and the open approach's discipline of freedom along the whole course; MABC-distribution numbness among the most frequent complications of open decompression, with 8–10 cm incisions threatening the nerve; subcutaneous transposition bed + fascial sling; Chen et al. meta-analysis (equivalent outcomes, transposition complication rate significantly higher, p = 0.05); the transposition-for-subluxation consensus **with its evidence caveat** |
| T30 | Zlowodzki et al. *Anterior transposition compared with simple decompression… a meta-analysis of randomized, controlled trials.* J Bone Joint Surg Am. 2007 (abstract) | The equipoise: 4 RCTs, no significant difference in clinical scores (SMD −0.04, 95% CI −0.36 to 0.28) or motor conduction velocities; narrow intervals exclude clinically meaningful differences — for nerves **without** instability, neither configuration is evidence-preferred |
| T31 | *Open and endoscopic decompression for cubital tunnel syndrome…* Arch Orthop Trauma Surg. 2026 (full text) | The implemented protocol this procedure encodes: dynamic stability assessment through full flexion/extension after decompression; instability → anterior transposition, stability preserved → decompression alone. Technique: incision between medial epicondyle and olecranon; Osborne release; arcade of Struthers when present; FCU band until motor branches; submuscular transposition steps incl. perineural-vessel preservation and the full-range re-check; septum release + fascial sling in the assisted arm; brachial plexus block + tourniquet; ROM from day 3; one MABC injury in the open group |
| T32 | Childress HM. *Recurrent ulnar-nerve dislocation at the elbow.* Clin Orthop Relat Res. 1975;(108):168–173 (abstract) | Variant prevalence: recurrent luxation in 16.2% of the general population — with the register's honesty that this is a population anatomical prevalence, not a measured intraoperative frequency |
| T33 | Zheng A, Fowler JR. *The effectiveness of preoperative antibiotic prophylaxis in ulnar nerve release at the cubital tunnel.* Hand (N Y). 2024 (abstract) | The no-prophylaxis design, elbow-specific: 919 releases, infection 1.7% without vs 2.7% with prophylaxis, no significant change — prophylaxis does not demonstrate benefit (level 4, retrospective, stated as such) |
| T34 | *Evaluation and Treatment of Failed Ulnar Nerve Release at the Elbow.* Orthop Clin North Am. 2012;43(4):487–494 (key points + chapter text) | The failure taxonomy the consequence engine encodes: technical causes of failure are incomplete decompression, creation of a new compression site or subluxation, and injury to the cutaneous or ulnar nerves; revision = complete decompression from the arcade of Struthers to the FCU and flexor-pronator aponeurosis with a stable transposition |
| T35 | *Outcomes and intraoperative findings of revision surgery for failed subcutaneous transposition of the ulnar nerve.* JSES Int. 2025;9:893–901 (abstract + results) | The revision series' numbers behind the release-extent and septum discipline: residual compression at the arcade of Struthers in 71.4% of 21 revisions, intact medial intermuscular septum in 76.2%, deep flexor-pronator aponeurosis in 38% |

Shared sources T6 (WHO checklist), T8/T9 (GOALS/OSATS rubrics),
T10 (PEARLS) and T20 (project/design anchors) carry over as at
Milestones 28 and 42.

## 3. The safety gate — the specialty's critical discipline

`gate.nerve-protection` (the scored safety gate) plus the
`gate.pre-division-pause` checkpoint, in the Milestone 42 shape.
No fascial structure of the release may be divided until three
criteria are demonstrated by their microsteps:

- **crit1 — the ulnar nerve identified and protected** (m2.1:
  identified proximal to the tunnel, in undisected tissue, under
  a vessel loop, before any division). T31's technique order:
  the nerve is identified, then decompressed.
- **crit2 — the medial antebrachial cutaneous branches accounted
  for** (m1.3: identified in the subcutaneous plane and protected
  along the whole incision). This nerve is the operation's named
  iatrogenic injury, sourced three ways: among the most frequent
  complications of open decompression (T29), a named technical
  cause of a failed release (T34), and an injury that occurred in
  the consulted cohort's open group (T31). The register resolves
  it to a real Body Model record — the Milestone 33 FMA concept
  `nerve.medial-cutaneous-nerve-of-forearm` (FMA39079, TA2 6446) —
  probed by `theatre_check` at every run.
- **crit3 — the full release extent established** (m2.3: arcade
  of Struthers proximally to the flexor-pronator aponeurosis
  distally, nerve under vision along the whole length). The span
  is T34's complete-decompression span; its named sites are
  where T35's revision series finds residual compression.

**Enforcement.** The runner evaluates the gate at every division
on the critical set (arcade of Struthers, cubital tunnel
retinaculum, FCU aponeurosis, deep flexor-pronator aponeurosis,
medial intermuscular septum). A division with the gate unmet
resolves onto the structure the unmet criterion was protecting,
following the Milestone 42 variant-resolution pattern: nerve
unidentified (or extent unestablished) → the division passes
through the **ulnar nerve** (`err.divide-unidentified`,
`ulnar-nerve-injury` on `major.ulnar`, FAIL); only the
cutaneous account missing → the division crosses the
**unaccounted MABC branches** (`err.mabc-unaccounted`,
`mabc-injury` on the MABC record, FAIL). Both fail the attempt:
the tasking discipline for this operation — divide or injure
before identification, of either protected nerve — is the
specialty's own (T34 names both injuries technical failures),
and a Rust probe pins the boundary between the two resolutions
so neither can silently absorb the other (§6).

The stability discipline cannot be a division gate — its
decision point sits after the divisions — so it is enforced
where it belongs: at the dp5 decision and at scoring (§4).

## 4. The configuration question — equipoise, stated honestly

**What the evidence decides.** For a nerve that is **unstable**
— subluxating over the medial epicondyle on flexion — the
specialty consensus prefers anterior transposition: the review
states it as the literature's one consensus (T29), a consulted
cohort implements it as protocol (T31), and the failed-release
taxonomy names persistent or new subluxation a technical failure
of the primary operation (T34). The runner enforces exactly
this: in the subluxating configuration, completing in situ
without a transposition decision computes
`err.subluxation-unaddressed` and the `nerve-instability`
consequence (trace-19), managed at dp4 by return to theatre for
a stabilising transposition.

**What the evidence does not decide.** Everything else. For a
**stable** nerve, the randomised evidence finds no difference
between decompression and transposition worth the name (T30),
the review's transposition-for-subluxation preference rests —
by its own account — on biomechanical logic and one study's
subgroup rather than subset-specific comparative trials (T29),
and transposition carries the higher complication rate in the
meta-analysis the review cites (T29, Chen et al.). The runner
therefore does **not** score transposition-for-a-stable-nerve
as an error, and does not score in-situ-for-a-stable-nerve as
one either: dp5 in the standard configuration is a genuine
decision whose only mechanical effect is that the chosen
configuration's microsteps become the required ones. This is
the honest encoding of equipoise — the engine grades the
discipline (identify, protect, release completely, assess
stability, execute the chosen configuration completely), not a
preference the literature has not earned.

**The transposition configuration has its own completeness
rule.** Transposing over an intact medial intermuscular septum
creates the compression the operation exists to remove — T34's
"creation of a new area of compression", and the single
commonest residual finding at revision of failed transposition
(intact septum 76.2%, T35). A transposition performed (m6.5)
without the septum release (m6.4) therefore computes
`err.new-compression-site` and the `new-compression`
consequence at scoring (Rust probe, §6), managed at dp4. The
authored transposition follows T31's open description (bed in
the common flexor mass, nerve moved without tension, gliding
re-confirmed through the full range) with fascial-sling
retention as both T29 and T31's assisted arm describe; the
subcutaneous-vs-submuscular sub-plane is **not** separately
configured in v1 — the comparative sources consulted found no
significant difference between them (T29), and splitting the
configuration further would multiply traces without a sourced
distinction to grade.

**Named non-goals.** *Endoscopic decompression* is not
authored: the consulted review found no demonstrated
superiority for it and conflicting complication data (T29), and
the open operation is the configuration the consulted technique
sources describe in full — recorded here with its grounds, as
Milestone 42 recorded its own non-goal. *Medial
epicondylectomy* is not authored: the review confines it to
structural abnormality of the elbow (T29), outside this
procedure's case mix.

## 5. Variant census

One variant, past the ≥1% prevalence gate:

- `variant.subluxating-nerve` — recurrent luxation of the ulnar
  nerve in **16.2%** of the general population (Childress 1975,
  T32). The register entry carries the honesty the precision law
  requires: 16.2% is a population anatomical prevalence, not a
  measured frequency of instability found at operation after
  release, and the consulted sources do not state the latter
  quantity. The variant carries **no `required_additions`**: it
  changes which dp5 decision is correct, not the static required
  set — the transposition microsteps enter the required set only
  through the decision itself, which is the milestone's
  mechanical point. No other variant met the gate with a
  distinct operative consequence in the sources consulted.

## 6. Traces and probes

Five shipped traces, all engine-computed, all expectations met
(`run-all`: 20 traces, 0 failures):

| trace | configuration | outcome |
|---|---|---|
| trace-16-ulnar-clean | standard | **PASS**, 30/30, safety 4/4, process 4/5 (the by-design ceiling, T33), no errors |
| trace-17-ulnar-divide-before-id | standard | **FAIL at t=1140 s** — m2.1 omitted; the arcade division resolves onto the ulnar nerve (`ulnar-nerve-injury` on `major.ulnar`); management 5/5 does not rescue, as at Milestones 17/28/42 |
| trace-18-ulnar-variant-subluxating | subluxating | **PASS**, 33/33 — dp5 routes to transposition; the decision drops m6.2 and inserts m6.3–m6.6; no instability consequence |
| trace-19-ulnar-subluxation-unaddressed | subluxating | **PASS with consequence** — dp5 completes in situ over the unstable nerve; `nerve-instability` computes at scoring; management 5/5 at dp4 |
| trace-20-ulnar-incomplete-release | standard | **PASS with consequence** — checklist missing exactly `["m5.4"]`; persistent symptoms compute on the retinaculum; management 5/5 at dp4 |

Six Rust probes pin the rules the traces do not exercise: the
MABC resolution (divide with only crit2 missing → FAIL on the
cutaneous nerve, failed at the division); its boundary (crit3
missing instead → the master rule on the ulnar nerve, **not**
the MABC); the dp2 no-bailout arm; transposition without septum
release → `new-compression` (with required set 33 and m6.4 the
recorded omission); the instability rule keyed on the *absence*
of a transposition decision (a trace that never takes dp5 is
still unaddressed); and the repair/referral asymmetry (injury
managed by referral without the repair microstep scores control
0, plan 1, management 4 — the Milestone 42 asymmetry, inherited
deliberately). Suite: **28 tests, all passing.**

## 7. Case #5 handoff (the Milestone 42 pattern)

`cases/case.ulnar-neuropathy.005.json` changed **in its
management block only**: a `handoff` (procedure
`proc.ulnar-decompression`, standard/in-situ configuration, from
stage 4, with a basis that keeps Milestone 43's honesty — the
disposition consulted no treatment guideline, and the handoff
names the operation the referral seeks without borrowing
authority) and `theatre_link_verified` were added, and
`theatre_note` was revised to the dated Milestone 44 record.
The adjudication, findings, criteria block and ground truth are
untouched. The attempt file changed in its stage-4 commit string
only. The regenerated case-5 debrief is **byte-identical** to
its pre-milestone hash (the runner does not consume the commit),
and `tools/case_check.py`'s `profile_case5` now asserts the
handoff exactly as `profile_case4` was revised at Milestone 42 —
including re-verifying that the theatre register resolves both
`major.ulnar` and the MABC record. `profile_case4`'s
procedure-set assertion was updated to the real four-procedure
set; its handoff assertions are unchanged.

## 8. Parameters and verify-flagged census

**No new parameter.** This operation's computed harms are
structural nerve injuries; no consulted source gives a
haemodynamic rate for any vessel this operation endangers, and
no bleed placeholder was invented to fill the gap — the
physiology component consequently runs on zero computed loss
(7/7 on the clean traces through the time and nadir components),
and the procedure's scoring block says so. Theatre parameters
stand at **15 (10 verify-flagged)** — the census is unchanged
from Milestone 42, all ten flags pre-dating this milestone. New
sources: **T29–T35** (register 28 → 35), every one consulted
in-session (§2); StatPearls attempted and reCAPTCHA-blocked,
cited for nothing. Instruments: none added (28 total).

## 9. Expert-review gate

**UNMET** — recorded verbatim in the procedure file, as in every
Theatre and Cases artifact: design/05 and design/10 require at
least two named independent expert reviewers with Delphi
sign-off before this procedure's content status can rise above
`dual-sourced-draft`. No reviewers exist for this project; the
gate is reported as unmet, never satisfied on paper. Content
status `dual-sourced-draft`; validity label `formative-only`;
no composite score anywhere.

## 10. Verification matrix (this milestone)

- `theatre validate`: all **4 procedures PASS** (ulnar: 9 phases,
  12 steps, 35 microsteps, 30 required standard).
- `cargo test --release` (theatre): **28 / 28** (22 prior + 6
  ulnar probes + the shipped-traces harness now asserting
  per-trace facts for traces 16–20).
- `run-all`: **20 traces, 0 expectation failures.**
- **Non-regression, byte-exact:** against the pre-milestone
  sha256 snapshot, all **15 prior debriefs are byte-identical**
  after full regeneration; the full JSON-tree census (743 files)
  shows exactly **3 changed files** (`theatre/parameters.json` —
  the source append; `cases/case.ulnar-neuropathy.005.json` and
  its attempt — §7) and **11 new files** (the procedure, 5
  traces, 5 debriefs), nothing missing; all 5 case debriefs
  byte-identical including case #5's.
- `tools/theatre_check.py`: **463 checks / 0 failures** (from
  355; the ulnar procedure's full per-procedure sections, the
  absence probes, and trace-16…20 expectations).
- `tools/case_check.py`: **7,589 passed / 0 failed** (from
  7,577; the handoff assertions net of the removed absence
  assertions).
- Full matrix: every `tools/*_check.py` (20 checkers) exits 0;
  `tools/assembly_check_all.py` ALL GATED CHECKS PASS;
  `tools/verify_web.js` ALL CHECKS PASS; physiology
  `cargo test --release` **25 / 25**; native shell verify
  **99 / 99 data assertions** (the GPU render stage cannot
  initialise on the current VM image — the standing disclosed
  limitation, unchanged).

## 11. Next steps

- The Theatre holds four procedures; the case series stands at
  5 of the P7 target of 12, and case #6 is the queue's next case
  slot when directed. No case currently in the workbench lacks
  its operation: cases #1–#5 all carry checker-verified handoffs.
- The subluxation variant's prevalence honesty (§5) names the
  one quantity a future source could improve: a measured
  frequency of instability found at operation after release,
  which would let the register replace the population figure for
  the intraoperative one.
- The expert-review gate (§9) remains the binding constraint on
  every Theatre procedure's content status; nothing in this
  milestone changes that, and nothing should be read as
  softening it.
