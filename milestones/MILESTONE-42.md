# Milestone 42 — Theatre procedure #3: open carpal tunnel release

**Status: built and verified locally; not uploaded.** The Theatre
gains its third procedure, `proc.carpal-release` — the operation
case #4 (`case.carpal-tunnel.004`, Milestone 41) named in its
disposition and could not hand off to, because the Theatre did not
hold it. The case now carries the handoff, checker-verified, with
its adjudication untouched. The procedure is CTA-authored to the
Milestone 17/28 discipline: phases, steps and microsteps from data;
the safety gate is the specialty's identification-and-protection
discipline, evaluated by the generalized engine, not a fork; every
complication is engine-computed; scoring is formative-only with no
composite; and the expert-review gate is recorded UNMET, verbatim,
as for both prior procedures.

## 1. What was built

- `theatre/procedures/proc.carpal-release.json` — 9 phases, 13
  steps, 34 microsteps (29 required in the standard configuration,
  30 in either variant configuration), 11 register entries, 2 gates,
  4 decision points, 8 error classes, 2 variants.
- Engine extensions in `theatre/src/runner.rs`, all additive and
  procedure-keyed, following the Milestone 28 generalization
  pattern: the carpal divide resolution (`on_divide_carpal`), the
  carpal microstep rules (wrong-plane dissection, routine
  neurolysis, repair), the transligamentous criterion deferral
  (reusing the appendectomy retrocecal deferral mechanism,
  generalized), the scoring-time incomplete-release consequence, a
  `repair_done` management state paralleling `drain_placed`, the
  dp2 no-bailout arm, and the carpal PEARLS builder. The engine was
  not forked; §5 proves the prior procedures are untouched by it.
- Five shipped traces (`theatre/traces/trace-11…15`), six Rust
  probes for the rules the traces do not exercise
  (`theatre/tests/runner_tests.rs`; suite now 22 tests).
- `theatre/parameters.json`: sources T21–T28 and one new
  verify-flagged parameter (§7). `theatre/instruments.json`: nine
  instruments added (28 total), each with function and
  injury-potential text in catalogue discipline.
- Case #4's handoff (§6), `tools/case_check.py` profile revision,
  `tools/theatre_check.py` extension (245 → 355 checks),
  `cases/README.md` updated.

## 2. CTA sourcing (sources consulted in-session)

| id | source | what it grounded |
|---|---|---|
| T21 | "Open Techniques for Carpal Tunnel Release", Green's Operative Hand Surgery chapter (read in full) | the step sequence itself; the standard incision (Kaplan's line to the distal wrist crease, axis of the radial border of the ring finger, 3–5 mm ulnar to the thenar crease); the ligament "must be clearly visible and exposed" before division; division on the ulnar aspect toward the ring finger; the distal fat pad / superficial arch as the completeness landmark; antebrachial fascia release ~2.5 cm proximal; the Freer-elevator completeness check; the intraligamentous branch released from the ligament when found; neurolysis/epineurotomy/tenosynovectomy "rarely indicated", not routine; palmar cutaneous branch preservation as the step against painful neuroma; antibiotics not required |
| T22 | "Palmar Approaches", Green's operative exposures chapter (read in full) | tunnel extent (Kaplan's cardinal line to the wrist flexion crease); the superficial palmar arch typically 18 mm distal to the ligament's distal edge; ligament attachments (scaphoid/trapezium radially, pisiform and hook of hamate ulnarly); the ulnar-border approach protecting the recurrent branch; PCBMN arising ~5–6 cm proximal, protected by staying ulnar and dividing fascia under vision |
| T23 | Lanz U. Anatomical variations of the median nerve in the carpal tunnel. J Hand Surg Am 1977;2(1):44–53 | the variant classification (groups I–IV) the variant gate is keyed to |
| T24 | Henry BM et al. 2015 meta-analysis (31 studies, 3,918 hands), pooled prevalences as summarised in the Lanz classification reference consulted | transligamentous recurrent branch 11.3% pooled (subligamentous 13.5%, extraligamentous 75.2% recorded alongside) |
| T25 | Sonographic study of bifid median nerve and persistent median artery, Clinics (São Paulo), 160 wrists, ultrasound + Doppler | bifid nerve 9.4% (15/160), persistent median artery 7.5% (12/160), coexisting 6.3% (10/160) — coexistence more probable than either alone |
| T26 | Harness NG et al. J Hand Surg Am 2010;35(2):189–196 | 3,003 releases, 11 surgical-site infections; antibiotics did not decrease infection, including in 546 patients with diabetes — routine prophylaxis not indicated (the design basis of §4's process ceiling) |
| T27 | "Revision of Carpal Tunnel Surgery", J Clin Med 2022 (read in full) | open release remains the gold standard; incomplete release of the ligament is the most common reason for persistent symptoms (distal at the palmar arch, proximal at the antebrachial fascia; inadequate exposure the mechanism); the iatrogenic injury list (palmar cutaneous, digital, median and ulnar nerves); endoscopic release among the risk factors for revision |
| T28 | AAOS Management of Carpal Tunnel Syndrome clinical practice guideline (adopted May 2024; summary Shapiro & Kamal, JAAOS 2025) — the case module's C24 | surgery the most effective long-term treatment; strong evidence of no outcome difference, mini-open vs endoscopic; limited evidence prophylactic antibiotics not indicated; local anaesthetic alone usable |

StatPearls/NCBI returned a reCAPTCHA interstitial on every attempt
this session (the same block recorded at Milestone 39); the
dedicated StatPearls carpal tunnel release article was **not read
and is cited for nothing**.

## 3. The safety gate — identification and protection before division

`gate.nerve-id`, the procedure's first safety gate, unlocks the
division step (step.6.1) and is demonstrated before it:

- **crit1** — the median nerve is identified where it enters the
  tunnel at the proximal edge of the retinaculum and protected, the
  nerve being immediately deep to the ligament along its whole
  length (demonstrated by m4.1; T21).
- **crit2** — the recurrent motor branch's course is accounted for
  and the division line set on the ulnar side of the ligament,
  directed toward the ring finger (m5.1; T21, T22).
- **crit3** — the division's limits are established: distally the
  superficial palmar arch (typically 18 mm beyond the ligament's
  distal edge, announced by the fat pad) and medially the ulnar
  neurovascular bundle at Guyon's canal and the hook of the hamate
  (m4.2; T21, T22).

The pre-division pause checkpoint (`gate.pre-division-pause`,
fulfilling `pre-division-pause`) is sourced to T20 and labelled in
the procedure file as module safety culture, not specialty
literature — the same honesty the prior procedures apply to their
pause.

**Master rule (engine-computed):** dividing
`ligament.transverse-carpal` with the gate unmet computes
`median-nerve-injury` (resolved onto `major.median`), raises
`err.divide-unidentified` (critical-fail) and FAILS the attempt at
the division instant. **Variant resolution:** in the
transligamentous configuration, if crit2 is the *only* missing
criterion, the division instead computes
`recurrent-branch-injury` (resolved onto the register's
`nerve.recurrent-branch-median` absence) with `err.missed-variant`
— the injury the anatomy assigns to that exact omission, neither
softened nor escalated to the master rule. A Rust probe pins the
boundary both ways: crit2 alone missing → branch injury; crit1 also
missing → the master rule.

## 4. The prophylaxis design — a ceiling stated, not hidden

This operation has **no antibiotic-prophylaxis microstep**, by
evidence: elective carpal tunnel release does not require local or
systemic antibiotics (T21), prophylaxis did not decrease infection
in 3,003 releases including in diabetes (T26), and the AAOS
guideline finds it not indicated (T28). Instead, m0.8 is an authored
required microstep — confirming prophylaxis is withheld and the
withholding is evidence-based — carrying no `fulfills` marker, so
the engine's process component caps at **4 of 5 for every carpal
attempt, including the perfect one**. The ceiling is documented in
the procedure's scoring block, in trace-11's case note, and here:
it is a property of the operation's evidence base, recorded
deliberately, not a defect awaiting a repair that would mean
inventing a prophylaxis step the literature says not to perform.

Two further scored departures follow the literature: radial
dissection across the palmar cutaneous branch's territory computes
`palmar-cutaneous-branch-injury` + `err.palmar-cutaneous-injury`
(major; T27 lists the injury, T21/T22 name its avoidance the most
important step against painful neuroma), and routine internal
neurolysis in a primary release raises `err.unnecessary-neurolysis`
(judgment; "rarely indicated", T21).

**Incomplete release** is a scoring-time consequence on the
appendectomy abscess pattern: a ligament divided without the
completeness confirmation (m6.2, the Freer-elevator free-passage
check, T21) computes `incomplete-release` — persistent symptoms,
the most common reason the revision literature gives (T27) — with
`err.incomplete-release` (major). The verdict stays PASS; the
consequence is managed at dp4 (`return-theatre` earns the plan
point). A failed attempt is excluded from this rule by construction:
its division resolved onto the nerve, and its declared outcome is
the injury.

## 5. Variants (variant gate: ≥1% prevalence, cited)

| variant | prevalence | source | mechanical effect |
|---|---|---|---|
| `variant.transligamentous-recurrent-branch` | 11.3% pooled | T24 (classification T23) | adds the branch to the field; crit2 cannot be demonstrated at m5.1 (the branch is inside the ligament substance) and is deferred to m5.5, identifying and freeing it; dividing with crit2 alone missing computes the branch injury (§3) |
| `variant.persistent-median-artery` | 7.5% (12/160) | T25 (Lanz group III, T23) | adds the artery (with the bifid nerve it accompanies in that group); m5.6 protects it; dividing gate-met but unprotected starts an engine bleed from the artery at the verify-flagged rate (§7) until controlled — a major error, not a fail |

The bifid median nerve (9.4%, T25) is **not** a standalone variant:
the consulted sonographic series shows it coexisting with the
persistent median artery more often than chance (6.3% of all
wrists), and the artery variant is authored as the Lanz group III
configuration that carries it. A standalone bifid variant is a
named next step (§9), not silently folded away — it is recorded in
the variant's own note in the procedure file.

**Endoscopic release is a named non-goal.** The guideline finds no
long-term outcome difference between the configurations (T28), open
release remains the gold standard with the field under direct
vision (T27), and endoscopic release is among the risk factors for
revision (T27); the sources consulted in-session did not support
authoring an endoscopic configuration to the same CTA standard.
The non-goal is recorded in the procedure's scoring notes and in
case #4's revised theatre note.

## 6. Traces — outcomes computed by the engine

| trace | configuration | outcome |
|---|---|---|
| trace-11 clean | standard | PASS; checklist 29/29 (100%); safety 4/4; process 4/5 (§4 ceiling); no errors, no complication |
| trace-12 divide-before-id | standard | **FAIL at t=1020 s** (the division); `median-nerve-injury` on `major.median`; `err.divide-unidentified`; management 5/5 (recognise → senior help → microscope repair at dp3 → repair performed) does not rescue the verdict |
| trace-13 variant transligamentous | variant | PASS; 30/30; gate 4/4 — crit2 deferred at m5.1, demonstrated at m5.5 when the branch is freed |
| trace-14 variant persistent median artery | variant | PASS; 30/30; artery protected at m5.6 |
| trace-15 incomplete release | standard | PASS with consequence; 28/29 (m6.2 the only omission); `incomplete-release` + `err.incomplete-release` computed at scoring; management 5/5 via dp4 `return-theatre` |

Probes additionally pin: the unprotected-artery bleed (300 s ×
1.0 mL/s = 300 mL, engine identity and event integral agreeing);
the transligamentous resolution boundary (§3); the wrong-plane and
neurolysis departures (§4); and a nerve injury managed by referral
without repair scoring control 0 of the management components
(`repair_done` is earned only by performing the repair microstep).

**Non-regression.** After `run-all` (15 traces, 0 expectation
failures), all ten cholecystectomy and appendectomy debriefs are
**sha256-byte-identical** to their pre-Milestone-42 hashes. The
Theatre Rust suite passes 22/22, including the updated shipped-
traces test (now fifteen traces, three procedures).

## 7. Parameters

One parameter added, verify-flagged as the discipline requires:
`bleed_rate_persistent_median_artery_ml_s` = 1.0 mL/s (engineering
placeholder — no flow measurement for this vessel was consulted;
the model uses it only to price an unprotected division until
control). The theatre parameter set is now 15 parameters, 28
sources; the verify-flagged census is 10 (the nine standing
placeholders plus this one), listed by `theatre_check` §9 at every
run.

Nine instruments were added (28 total): scalpel No. 15 and tenotomy
scissors, Ragnell retractor, Adson forceps, Freer elevator, vessel
loop, bipolar forceps, arm tourniquet, operating microscope. Those
the technique chapter names carry `cited` status (T21); the rest
are `verify`-flagged catalogue entries, as the catalogue's own
discipline allows.

## 8. The register, and the recurrent branch stated plainly

Eleven entries. Four resolve to records: `major.median` and
`major.ulnar` (Milestone 39 clinical records,
`data/nervous/major-nerves.json`), `muscle.palmaris-longus`
(`data/muscular/muscles.json`), `hamate_right`
(`data/skeletal/skeleton-geometry.json`). Seven are **absences**,
each with a substantive note: the transverse carpal ligament
itself, the superficial palmar arch, the palmar cutaneous branch,
the persistent median artery, Guyon's canal, Kaplan's cardinal
line — and the recurrent motor branch.

The recurrent branch deserves its own paragraph, because it is the
structure the gate most protects and the Body Model most lacks.
Milestone 35's innervation pass found the phrase "recurrent branch
of the median nerve" in muscle records' supply text but could not
resolve it to any record; Milestone 39's median nerve record states
the division into recurrent and palmar digital branches in cited
prose; Milestone 41 recorded the gap from the case side. No record
exists — `theatre_check` now probes the whole data tree at every
run and asserts that no id in it names a recurrent branch, a
retinaculum, a palmar arch, a persistent median artery, or Guyon's
canal, so the absence entries cannot silently go stale. The gate
protects the branch as a *course to be accounted for* (crit2), the
variant adds it to the field as an absence entry, and its injury
resolves onto the absence — the same treatment the cholecystectomy
gives the cystic artery. Giving the branch a record is Body Model
work (the Milestone 34 geometry line owns the nerve-geometry
question); it is a next step (§9), not something this milestone
fabricates.

## 9. Case #4's handoff — exactly what changed

- `cases/case.carpal-tunnel.004.json`, `management` block only:
  `handoff` added (procedure `proc.carpal-release`, standard/open
  configuration, from stage 4, with the basis: EDX-confirmed median
  neuropathy + CTS-6 16.5/26 + eight months of sleep-disrupting
  symptoms, per the case's own C24 guideline pathway) and
  `theatre_link_verified` added (the checker re-verifies the
  procedure id and the register resolution of `major.median` at
  every run); `theatre_note` revised to a dated record that the
  procedure now exists and the handoff is live, with the
  endoscopic non-goal stated. **The adjudication, findings, board,
  criteria and every other section are untouched** — the case file's
  change is confined to those three management fields.
- `cases/attempts/attempt.case-carpal-tunnel-004.model-learner.json`:
  the stage-4 commit's management string gains the handoff clause
  in the case-1/3 phrasing ("— Theatre handoff to procedure
  proc.carpal-release (open configuration), as the case's management
  block specifies"); nothing else in the attempt changed.
- Case #4's debrief, regenerated by `tools/case_run.py`, is
  **byte-identical** to its Milestone 41 hash — the runner does not
  consume the commit, and no board, order or score moved.
- Cases #1–#3, their attempts and their debriefs: sha256-verified
  byte-identical to baseline. `case_check` profile_case4 was
  revised to assert the handoff instead of its absence (the
  physiology-link absence assertion is kept): **6,406 checks, 0
  failures** (was 6,393).

## 10. Validity and review — stated, not softened

Content status `dual-sourced-draft`, scores formative-only, no
composite score — as both prior procedures. **Expert-review gate:
UNMET.** The procedure file's review block reads, verbatim as the
checker asserts it for all three procedures: no named reviewer has
examined this module's content; no reviewer is named because none
exists; the gate is unmet and this text is its record, not a
substitute for it. Eight of the theatre's fifteen parameters remain
verify-flagged placeholders (§7); the carpal additions inherit that
honesty rather than borrowing confidence.

## 11. Verification matrix (this milestone)

- Theatre: `cargo build --release` clean; `validate` PASS for all
  three procedures; `cargo test --release` 22/22; `run-all` 15
  traces, 0 expectation failures; prior debriefs byte-identical
  (§6).
- `tools/theatre_check.py`: **355 checks, 0 failures** (was 245).
- `tools/case_check.py`: **6,406 passed, 0 failed** (was 6,393).
- All 20 `tools/*_check.py` exit 0, including the Milestone 40
  `repro_check` repair.
- Physiology `cargo test --release`: 25/25 (module untouched).
- `tools/verify_web.js` and `tools/assembly_check_all.py`: green
  (web and assembly untouched).
- Native shell verify: 99/99 data assertions; the GPU render stage
  remains unavailable on this VM image (no Vulkan ICD) — the
  standing disclosed limitation, unchanged since Milestone 28.
  Nothing under `native/` or `web/` was touched by this milestone.

## 12. Next steps

1. Case #5 candidates, as recorded at Milestone 41: a second
   localization case (ulnar neuropathy at the elbow is the natural
   pair to case #4) or a return to the loop pattern.
2. A standalone bifid-median-nerve variant (§5) if a consulted
   source supports authoring its distinct operative consequence.
3. The recurrent branch as a Body Model record — owned by the
   Milestone 34 geometry line, not by the Theatre.
4. The imaging pydicom/dcmtk toolkit pass owed for both subjects
   (standing debt, unrelated to this milestone).
