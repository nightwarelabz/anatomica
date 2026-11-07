# Milestone 17 — Theatre v1: laparoscopic cholecystectomy, end to end

**State: built and verified locally. Not uploaded (per-item approval rule).**

Theatre v1 ships the first complete surgical procedure in ANATOMICA:
an authored procedure model for laparoscopic cholecystectomy, two
variant configurations, a headless Rust attempt runner that executes
scripted attempts against the procedure model **and the Milestone 8
physiology engine**, computes complications from attempt state, and
emits PEARLS-structured scored debriefs — plus an independent Python
checker. Everything lives in `theatre/` with the checker at
`tools/theatre_check.py`.

## The procedure as authored (`theatre/procedures/proc.lap-cholecystectomy.json`)

Census (recounted by the checker from the file): **9 phases, 21
steps, 86 microsteps**. Required set: **64** microsteps in the
standard configuration, **67** in the double-cystic-artery
configuration, **52** along the bailout path (the required set is
configuration-dependent by the rules below).

| Phase | Content | Microsteps |
|---|---|---|
| 0 | Planning (Step 0), prophylaxis, WHO Sign In, WHO Time Out | 9 |
| 1 | Access (Hasson) and four-port placement | 13 |
| 2 | Exploration and retraction | 5 |
| 3 | Hepatocystic triangle dissection | 15 |
| 4 | Critical View of Safety (plate, two-structure confirmation, pre-clip pause) | 6 |
| 5 | Intraoperative cholangiogram (optional, decision-gated) | 10 |
| 6 | Control and division (+ variant branch step, + subtotal bailout branch) | 15 |
| 7 | Liver bed, haemostasis, inspection, contingency drain | 6 |
| 8 | Extraction, fascial closure, WHO Sign Out | 7 |

**Authoring discipline.** The published cognitive task analysis of
this procedure resolved 19 expert-recalled steps into 97 microsteps
(Villarreal et al. 2023, source T5) — and experts omit 50–70% of
steps on unaided recall. The full published microstep list is not
public, so this file is an **independent decomposition** authored
against operative descriptions actually consulted in-session (T13),
at the granularity those sources support: dissection carries 15
microsteps and cholangiography 10, mirroring the published
instrument's two largest blocks; access and extraction are coarser
than the published instrument's, which is why the total is 86, not
97. Every microstep carries at least one source id; the checker
enforces this. Nothing is recalled unaided where a source could be
consulted, and anything unsourced is flagged in place (e.g. the VTE
prophylaxis microstep asserts no agent or dose — none was consulted).

**Structures register — 23 entries, every reference resolved or
absence-noted.** 17 entries resolve to real Body Model records in
`data/digestive/digestive.json`, `data/digestive/digestive-inventory.json`,
`data/cardiovascular/cardiovascular.json` and
`data/cardiovascular/cv-inventory.json` — the checker verifies each
id exists in the named file. Six entries are explicit absences:

- **`artery.cystic` — the cystic artery has no Body Model record at
  all** (no BP3D concept, probe-verified in Milestone 5; the checker
  re-verifies the absence against the data files). Its anatomy here
  is sourced from the consulted meta-analysis (T11: origin from the
  right hepatic artery 89%, CI 85–92; mean diameter 1.91 mm) and the
  gallbladder record's supply text.
- **`duct.common-bile` — the common bile duct has no BP3D concept**
  (Milestone 11; re-verified). It appears in the procedure only as
  the structure injured in the misidentification resolution — the
  anatomy the Body Model most needs for this procedure is the one it
  does not yet have. The gap is stated in the register, not papered
  over.
- `artery.cystic-branch-2` (second branch of a double cystic artery;
  same absence, variant anatomy from T11), `region.hepatocystic-triangle`
  and `region.cystic-plate` (surgical fields, defined by T2, not
  organs), `part.hartmann-pouch` (carried as a named part inside the
  gallbladder record).

**Safety gates.** `gate.cvs` is the Critical View of Safety exactly
as the specialty defines it (Strasberg & Brunt 2010, T2): (1) the
hepatocystic triangle cleared of fat and fibrous tissue — the common
bile duct and common hepatic duct do *not* have to be exposed; (2)
the lower one-third of the gallbladder separated from the liver to
expose the cystic plate; (3) two and only two structures seen
entering the gallbladder. Each criterion is demonstrated by a named
microstep (m3.11, m4.2, m4.5); the checker proves every criterion is
demonstrable no later than the division phase. The multi-society
guideline's pre-clip pause (T3) is modelled as a second, scored
checkpoint (`gate.preclip-pause`, microstep m4.6) rather than a
second blocking gate — a stated design choice; the blocking gate is
the View itself.

**Error model — 10 first-class errors**, including the master rule
from design/05: dividing an unidentified critical structure
(`err.divide-unidentified`) **fails the attempt regardless of all
other scores**. The runner's central mechanism is *misidentification
resolution*: clip and divide actions are resolved against the
attempt's identification state, not against the trace's belief about
what it is cutting. A clip placed on the presumed cystic duct before
the View resolves onto the common bile duct (Stewart-Way class I
mechanism state); dividing it resolves to a **class III bile duct
injury** — the dominant pattern in the Way et al. series (61% of 252
cases; primary cause a visual perceptual illusion in 97%, technical
faults 3%, T1). The full error set: clip-before-identification,
divide-unclipped artery (computed haemorrhage), divide-unclipped
duct (bile leak), energy applied to an unidentified duct (class II
thermal mechanism), prophylaxis outside the cited 60-minute window
(T7), WHO phase omission (T6), the two variant errors below, and
continuing dissection after declaring the View unobtainable
(`err.no-bailout`, T3).

**Decision points — 4**, each offering the field's bailouts, and
**bailouts score positively, never as failure** (design/05): dp1
findings at exploration; dp2 the View unobtainable (choices include
IOC, both subtotal subtypes per Strasberg 2016 T4, conversion,
calling for senior help, and the scored-error choice to continue
dissecting); dp3 bleeding escalation; dp4 injury recognised
(drain-and-refer is the guideline-preferred plan, T3).

**Variants (gate: ≥1% prevalence + injury consequence, design/05).**

1. **Replaced right hepatic artery from the SMA** (Michels III) —
   prevalence **8.7–11.0%** from the Milestone 5 variant record.
   Gate modification: microstep m3.12 is the survey point, and the
   runner requires an explicit `identify` of the variant vessel
   before any cystic artery division in this configuration; dividing
   without it resolves the cut vessel to the replaced artery
   (`err.missed-variant`: FAIL + computed haemorrhage at the larger
   rate).
2. **Double cystic artery** — prevalence **13% (95% CI 11–16%)**
   from the consulted meta-analysis (T11). Not present in the
   Milestone 5 records (the cystic artery has no concept at all);
   sourced at theatre level with that absence stated, as the
   precision law requires. Gate modification: the second-branch
   microsteps become required, and beginning liver-bed dissection
   with the branch uncontrolled computes haemorrhage from it
   (`err.uncontrolled-branch`) — a recoverable completeness failure,
   deliberately contrasted with the identification failures.

**Scoring.** Components per design/05: checklist % (configuration-
dependent required set), safety gate /4, process /5 (three WHO
phases, prophylaxis window, Step 0 planning), physiology /7 computed
from the engine run (time below MAP 65 mmHg, MAP nadir, blood loss —
bands are module rubric, verify-flagged), management /5 when a
complication occurs (recognition, control, escalation, plan).
**No composite score is computed**: design/05 defines components,
not weights, and inventing weights would violate the precision law.
GOALS (T8) and OSATS (T9) ship as rubric data for observed-
performance rating in the shells; a headless scripted runner has no
observed performance to rate, so debriefs report them **not
populated** rather than estimated. All scores carry the
**formative-only** validity label (design/10).

## The attempt runner (`theatre/`, crate `anatomica-theatre`)

Rust, path-dependent on `anatomica-physiology`, following its
conventions (including a parameter loader that hard-fails any
parameter that is neither cited, calibrated, nor verify-flagged).
An attempt runs the Milestone 8 case protocol — 6,000-tick settle,
baseline window, baroreflex setpoint = own baseline MAP — then
executes trace actions in simulated time, ticking the engine between
them. Haemorrhage and infusion share the engine's single external-
flow channel, so the runner nets active sources before applying.
Blood loss is reported two independent ways — the runner's event
integral (rate × time-to-control) and the engine's volume identity
— and the checker requires them to agree.

**Engine-semantics trap found and fixed during this build:** the
physiology engine's `total_volume_ml()` is the *conserved* quantity
by construction (compartment sum minus the external-flow integral)
and therefore cannot measure blood loss; circulating volume is the
raw compartment sum `volumes()`. The first bleed probe exposed it
(MAP fell to 45.6 mmHg while the "identity" read 0 mL); the runner
now measures from `volumes()`, and the two routes agree exactly
(750.0 vs 750.0 mL in the probe).

**Theatre parameters: 13** (5 cited, 8 verify-flagged). The flagged
ones are named here as the law requires: the three bleed rates
(2.5 / 5.0 / 1.2 mL/s — engineering placeholders, order-of-magnitude
anchored only to the cystic artery's published mean diameter) and
the five physiology rubric bands. No flagged value is presented
anywhere as clinical fact.

## The five shipped traces — outcomes line by line

| Trace | Verdict | Checklist | Safety | Process | Physiology | Management |
|---|---|---|---|---|---|---|
| 01 clean expert | **PASS** | 100% (64/64) | 4/4 | 5/5 | 7/7 | n/a |
| 02 divide-before-CVS | **FAIL** at t=1920 s | 50.0% (32/64) | 0/4 | 3/5 | 7/7 | **5/5** |
| 03 replaced RHA, identified | **PASS** | 100% (64/64) | 4/4 | 5/5 | 7/7 | n/a |
| 04 double cystic, both controlled | **PASS** | 100% (67/67) | 4/4 | 5/5 | 7/7 | n/a |
| 05 bailout, fenestrating subtotal | **PASS** | 100% (52/52) | 0/4 * | 5/5 | 7/7 | n/a |

\* Trace 05's safety points measure gate achievement only; the
debrief carries the note that the View was unobtainable by scenario
design and the bailout — the graded behaviour — was taken. Bailing
out is scored positively (the plus-analysis states it, citing T3/T4);
it is never a fail.

Trace 02's event spine, from its debrief: clip applied to the
presumed cystic duct at t=1860 s with 0 of 3 criteria demonstrated →
clip resolves onto the common bile duct (class I mechanism);
division at t=1920 s → **Stewart-Way class III transection of the
common bile duct, attempt FAILS**; injury recognised at t=2100 s,
hepatobiliary team called at t=2160 s, dp4 → drain-and-refer at
t=2220 s, drain placed. Management scores 5/5 and does not rescue the
verdict — the debrief's contrast is the teaching point. Its other
recorded errors: prophylaxis after incision (T7) and the omitted
Time Out (T6). Note trace 02's physiology is 7/7 *honestly*: a bile
duct injury is a structural catastrophe with no cardiovascular
signature in a v0 engine that has no biliary compartment — the
debrief says so rather than inventing a pressure response.

Engine trace hashes (determinism is test-asserted): 01
`0x2f642e693ee178b9`, 02 `0xd35f851ce4b24568`, 03 identical to 01
(the identification action does not touch the physiology — the hash
covers the physiology trace), 04 `0x79c89088088ec060`, 05
`0x854f7e67a9acda25`. Volume conservation error ≤ 1.6×10⁻¹⁰ mL in
all five.

**Synthetic probes** (Rust integration tests, for the rules the
shipped traces do not exercise): unclipped cystic artery division →
750 mL computed loss over 300 s, MAP nadir 45.6 mmHg, 248 s below
threshold; unrecognised replaced-RHA division → FAIL, 1,500 mL over
300 s; uncontrolled second branch → 360 mL over 300 s, stopped by
clipping the branch; misclip recognised and removed → near miss,
attempt passes, no injury; energy on the unidentified common hepatic
duct → class II thermal injury recorded, scored, not an automatic
fail. The MAP response magnitude inherits Milestone 8's disclosed
limitation (no venoconstriction / transcapillary refill yet, so the
model over-responds to haemorrhage); the *loss volumes* are exact by
construction, the *pressure magnitudes* are not yet validated.

## Verification (all run this session, full outputs in the build log)

- `anatomica-theatre validate` — PASS: census as above; no duplicate
  ids, no unregistered targets, no unknown instruments, every gate
  criterion demonstrated by some microstep, every decision point
  carrying a bailout.
- `cargo test --release` — **8/8 pass** (five probes, shipped-trace
  expectations, determinism, validation).
- `anatomica-theatre run-all` — **5 traces, 0 expectation failures**;
  debriefs written to `theatre/debriefs/`.
- `python3 tools/theatre_check.py` — **131 checks, 0 failures**:
  independent recounts, register resolution against the real data
  files (including re-verifying that the cystic artery and common
  bile duct are genuinely absent), gate reachability, and full
  recomputation of every debrief's scoring arithmetic from its own
  components.

Run it: `cd theatre && cargo run --release -- validate | run <trace.json> | run-all`,
then `python3 ../tools/theatre_check.py` from the theatre directory's
parent (repo root).

## Review gate — UNMET, reported not satisfied

Design/05 and design/10 require **≥2 named independent expert
reviewers with Delphi sign-off** before a procedure's content status
can rise above dual-sourced-draft. **No reviewers exist for this
project.** The procedure file records the gate verbatim as UNMET
with an empty reviewer list; the checker asserts it stays that way.
The content status is `dual-sourced-draft`, the validity label
`formative-only`, and the design/10 negative-training audit has not
been performed. None of this is filled in on paper.

## What is NOT yet real — the interaction model, stated honestly

- **There is no interactive 3D manipulation.** v1 is the authored
  procedure plus *evaluated scripted attempts*: a trace declares
  actions (perform a microstep, identify a structure, decide, infuse,
  control a bleed), and the theatre judges them against the model
  and the physiology. Free manipulation in the shells — picking
  structures in the assembled Body Model, clipping with a tool,
  having the view state computed from where the camera and
  instruments actually are — is later work, now possible in
  principle because Milestone 16 made every record pickable in both
  shells.
- GOALS/OSATS are unpopulated rubric data (see Scoring).
- Bleed rates are verify-flagged placeholders; haemorrhage pressure
  magnitudes inherit the physiology engine's unvalidated-magnitude
  status (Milestone 8).
- A bile duct injury has **no physiology representation** (no
  biliary compartment in engine v0): it is a structural outcome with
  management scoring, and the debrief states this.
- Cholangiography is evaluated as steps; no fluoroscopy image is
  rendered (that belongs to the imaging module).
- Resource tiers are recorded with the attempt, not yet scored or
  simulated (no consumables, no team model).

## Sources consulted in-session (full citations in `theatre/parameters.json`)

T1 Way et al., Ann Surg 2003 (252 BDI cases; 97% perceptual;
Stewart-Way classes). T2 Strasberg & Brunt, J Am Coll Surg 2010
(CVS criteria). T3 Brunt et al., Surg Endosc 2020 (multi-society
guideline). T4 Strasberg et al., J Am Coll Surg 2016 (subtotal
subtypes). T5 Villarreal et al., Surg Endosc 2023 (CTA, 19→97).
T6 WHO Surgical Safety Checklist 2008/09 + Haynes et al., NEJM 2009.
T7 Bratzler et al., Am J Health-Syst Pharm 2013 (cefazolin). T8
Vassiliou et al., Am J Surg 2005 (GOALS). T9 Martin et al., Br J
Surg 1997 (OSATS). T10 Eppich & Cheng, Simul Healthc 2015 (PEARLS).
T11 Asghar et al., Clin Ter 2024 (cystic artery meta-analysis). T12
project sources (Milestone 5 variants and absences, Milestone 11
records, design/05). T13 operative technique references (four-port
American configuration).

## Next steps

1. Shell integration: traces played back against the pickable Body
   Model in the web and native shells; then interactive attempts
   (the gate state computed from demonstrated view, not declarations).
2. Physiology: venoconstriction and transcapillary refill
   (Milestone 8's named next step) so haemorrhage magnitudes can be
   validated; a biliary compartment when the imaging/cases modules
   need one.
3. A sourced haemodynamics reference for the bleed rates, replacing
   the placeholders.
4. Imaging module: cholangiogram rendering for phase 5.
5. Second procedure (laparoscopic appendicectomy, design/05 wave 1)
   reusing this model wholesale.
6. External dependency, not schedulable from here: named expert
   reviewers for the review gate.
