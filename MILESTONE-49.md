# Milestone 49 — Theatre procedure #5: laparoscopic inguinal hernia repair (TAPP)

**Status: built and verified locally; not uploaded.** The Theatre
gains its fifth procedure, `proc.lap-inguinal-hernia` — laparoscopic
transabdominal preperitoneal (TAPP) inguinal hernia repair, right
side. It is CTA-authored to the Milestone 17/28/42/44 discipline:
phases, steps and microsteps from data; the safety gate is the
specialty's own danger-anatomy discipline, evaluated by the
generalized engine, not a fork; every complication is
engine-computed; scoring is formative-only with no composite; and
the expert-review gate is recorded UNMET, verbatim, as for all four
prior procedures.

The operation's named danger anatomy **is** the gate. The
preperitoneal dissection must account for the triangle of doom
(bounded by the vas deferens and the gonadal vessels, containing
the external iliac vessels) and the triangle of pain (the lateral
cutaneous / genitofemoral territory) before mesh placement,
division or fixation — and this operation has **two gated verbs**,
division and fixation, where the earlier procedures had one.

## 1. What was built

- `theatre/procedures/proc.lap-inguinal-hernia.json` — 9 phases,
  12 steps, 41 microsteps (33 required in the standard
  configuration; 36 in the fixation configuration as enacted by the
  dp5 decision; 34 in each variant configuration), 22 register
  entries, 2 gates, 6 decision points, 12 error classes,
  2 variants.
- Engine extensions in `theatre/src/runner.rs`, all additive and
  procedure-keyed, following the Milestone 28/42/44 generalization
  pattern: the hernia critical-structure set (sac + transversalis
  fascia) and a **new gated verb, `fixate`**; a shared three-way
  gate resolution (`hernia_gate_resolution`) used by both
  `on_divide_hernia` and `on_fixate_hernia`; `hernia_microstep_rules`
  (the two authored prohibited placements); the dp2 no-bailout arm;
  the **dp5 fixation decision arm, which inserts the three zonal
  fixation microsteps into the required set** — the ulnar
  transposition mechanism (Milestone 44) applied to a fixation
  configuration; two scoring-time blocks (the fixation judgment
  pair — unnecessary fixation, and recurrence after an unfixed
  large medial defect — and the unconfirmed peritoneal closure);
  the management wiring (hernia injury kinds take their plan at
  dp4, the postoperative consequences at dp6, and dp6 joins the
  escalation rule for this procedure); and `build_pearls_hernia`.
  `theatre/src/model.rs` gains one additive field,
  `CaseSpec.defect` (serde-defaulted; every prior trace parses
  unchanged). The engine was not forked; §11 proves the prior
  procedures are untouched by it.
- Five shipped traces (`theatre/traces/trace-21…25`) and ten Rust
  probes for the rules the traces do not exercise
  (`theatre/tests/runner_tests.rs`; suite now 38 tests).
- `theatre/parameters.json`: sources T36–T41 added; **two new
  parameters, both verify-flagged placeholders** (§9). The file's
  `milestone` field is left at 17, as Milestones 28/42/44 left it.
- `theatre/instruments.json`: two instruments added (mesh fixation
  tacker, fibrin glue applicator; 28 → 30), both cited to T36's
  fixation-methods list.
- `tools/theatre_check.py`: fifth procedure wired in; debrief
  census 20 → 25; a Milestone 49 section-8 block (absence probes +
  trace expectations). Checker now 595 checks (§11).
- `tools/case_check.py`: **maintenance only** (§10) — three
  procedure-set assertions updated to the real five-procedure set
  in the Milestone 44 pattern. No file under `cases/` was touched.

## 2. Approach: TAPP, and why

The task left TAPP vs TEP to the consulted sources. The specialty's
gate concept — the **critical view of the myopectineal orifice**
(Daes & Felix 2017, carried by T38) — is approach-shared, so the
gate did not decide it. TAPP was chosen because its intraperitoneal
survey (hernia typing, femoral canal inspection, consented
contralateral inspection after HerniaSurge) and its peritoneal-flap
closure discipline give the fuller cognitive task analysis: the
flap-closure completeness rule (§6) is TAPP-specific teaching
content no TEP model carries. The counterpoint is recorded in the
procedure file's `authority_basis`, not suppressed: the 2023
update (T37) notes that TEP exploration detects small contralateral
defects and cord lipomas more directly, since it dissects the
orifice itself. TEP is the named non-authored alternative. The
authored side is the **right**: the sliding variant's viscus is
then the cecum (see §7 for the sourcing care taken there).

## 3. CTA summary

Nine phases, following the golden rules' operative order (T38):
(0) planning, anaesthesia, bladder emptied, WHO points, and the
authored prophylaxis withholding (m0.8); (1) TAPP access and the
peritoneal flap incision ≥4 cm above the deep ring, ASIS to medial
umbilical fold (Rule 1); (2) intraperitoneal survey — classification,
femoral canal with the iliac vein in view (Rule 4), Retzius/bladder;
(3) preperitoneal dissection — Retzius to the symphysis and ≥2 cm
below the pubis (Rule 3), Bogros with fat kept on the floor
(Rule 2), sac reduction and cord-lipoma reduction (Rule 7);
(4) **the danger-anatomy account** — the three gate demonstrations
plus the two variant microsteps; (5) the gate phase — critical-view
confirmation, second look (dp2 anchor), pre-division pause;
(6) sac completion (division gated; large sacs transected with the
distal sac abandoned, only after the cord is identified — Rule 6),
mesh positioning (≥10×15 cm, overlap ≥3–4 cm, heavyweight for a
large direct defect — Rule 8, T37), the fixation assessment (dp5
anchor) and the zonal fixation step; (7) peritoneal closure by
suture (Rule 10) with its completeness confirmation, and the
injury-management step (dp4 anchor); (8) deflation under direct
vision (Rule 10), fascial closure of ≥1 cm ports, postoperative
plan (dp6 anchor), Sign Out.

Two authored **prohibited-placement** microsteps (m6.7, m6.8) sit
in the fixation step, required in no configuration: they exist so
the fixation-in-triangle departures are performable, scored acts
rather than unmodelled possibilities (§5).

## 4. Sources (all consulted in-session)

| id | source | carries |
|---|---|---|
| T36 | HerniaSurge Group, *Hernia* 2018;22(1):1–165 (PMC5809582) | Fixation rule: non-fixation in almost all types except large medial (M3 EHS) defects; atraumatic fixation to consider; prophylaxis **never** recommended in laparo-endoscopic repair; preperitoneal vascular injuries typically involve epigastric or aberrant obturator (corona mortis) vessels; exposed mesh → adhesions/obstruction; CPIP 10–12% |
| T37 | Stabilini et al., *BJS Open* 2023;7(5):zrad080 (2023 update) | Prophylaxis not suggested in any patient/environment; heavyweight mesh recommended especially in large/direct hernia; recurrence after non-fixated mesh in direct repairs RR 7.27 (Bakker, as reported); fixation evidence insufficient (chapter not updated); TEP-detects-occult-defects counterpoint |
| T38 | Claus et al., *Surg Endosc* 2020;34(4):1458–1464 — read in full | Ten golden rules; inverted Y and five triangles; critical view of the MPO (Daes & Felix 2017); the gating sentence (§5); nerves not systematically dissected (Rule 2); parietalization endpoint (Rule 5); fixation unnecessary in most repairs, recommended in large/direct (Rule 9); no traumatic fixation below the iliopubic tract, 2 cm above for safety; 5–6 points sufficient; suture flap closure (Rule 10) |
| T39 | Yang & Liu, *Ann Transl Med* 2016;4(19):372 (PMC5075841) — read in full | Verbatim definitions of both triangles (§5); corona mortis over Cooper's ligament ~5 cm from the symphysis, retracts into the obturator canal when cut; Cooper's ligament holds mesh and tacks; cord exposure via internal spermatic fascia incision |
| T40 | Sanna et al., *Injury* 2018;49:302–308, as reported in Konarska-Włosińska et al., *Int Urogynecol J* 2024 (PMC11150310) — read in full | Corona mortis prevalence **49.3%** (venous 41.7%, arterial 17.0%) — the variant prevalence |
| T41 | Gaspar et al., *Calif Med* 1956;85(5):330–334 (PMC1532016) — abstract read in full | Sliding hernia **2–5%** of indirect inguinal hernias, defined by a viscus forming part of the sac wall — the variant prevalence |

Shared: T6 (WHO), T8/T9 (GOALS/OSATS rubric data), T10 (PEARLS),
T20 (module safety culture / design-05 anchors).
**StatPearls was not consulted** — reCAPTCHA-blocked, as throughout
this project; it is cited for nothing. EHS defect-size centimetre
thresholds were **not** asserted: the guideline text read delegates
them to Miserez 2007, which was not opened, so the model keys on
the guideline's own gloss, "large medial (M3)".

## 5. The gate — text and resolution

Gate `gate.mpo-account` (statement, from the procedure file):

> No structure of this repair may be divided and no mesh fixation
> placed until the danger anatomy has been accounted for AND
> demonstrated (all three criteria): the triangle of doom delimited
> with the external iliac vessels identified inside it, the
> triangle of pain delimited with its lateral nerves accounted
> for, and the cord structures accounted for and parietalized. The
> specialty's own gating sentence: *"Only if all anatomical
> elements have been recognized, the steps of dissection described
> above have been completed and hemostasis achieved should the
> surgeon proceed with mesh placement"* (T38).

Criteria, each demonstrated by one phase-4 microstep:

- **crit1 — triangle of doom delimited; external iliac vessels
  identified** (m4.1). Definition verbatim-grounded in T39: the
  triangle is *"bound by the vas deferens, the testicular vessels
  and the peritoneal fold. Within the boundaries of this area, you
  can find the external iliac artery and vein."* The corona survey
  is part of this demonstration (T36 names the aberrant obturator
  vessels among the typical injuries; T39 places the vessel over
  Cooper's ligament).
- **crit2 — triangle of pain delimited; lateral nerves accounted
  for** (m4.2). T39 verbatim: the triangle is *"located lateral to
  the dangerous triangle and bound by the iliopubic tract, the
  testicular vessels and the peritoneal fold"*, containing
  lateral-to-medial the lateral femoral cutaneous nerve, the
  femoral branch of the genitofemoral nerve and the femoral nerve.
  **Accounted for does not mean dissected**: the golden rules state
  the nerves should not be systematically dissected or identified
  in the minimally invasive approach (T38, Rule 2); the account is
  territorial — tract line established, every fixation point
  planned ≥2 cm above it (T38, Rule 9).
- **crit3 — cord structures accounted for and parietalized**
  (m4.3): inverted-Y arms identified, internal spermatic fascia
  incised, peritoneum dissected until the vas crosses the external
  iliac vein, iliopsoas identified (T38 Rule 5; T39).

**Resolution — three-way, priority-ordered, probe-pinned.** A
divide or fixate act with the gate unachieved resolves onto the
structure the unmet criterion protected, in the stated total order
**crit1 → crit2 → crit3**:

| missing | error | injury (complication kind → record) | verdict |
|---|---|---|---|
| crit1 (any company) | `err.divide-unidentified` | vascular-injury → `artery.right-external-iliac-artery` + haemorrhage at the iliac placeholder rate | FAIL |
| only crit2 (or crit2+crit3) | `err.pain-triangle-injury` | nerve-injury → `nerve.genitofemoral` | FAIL |
| only crit3 | `err.vas-injury` | vas-deferens-injury → `repro.right-deferent-duct` | FAIL |

**Gated-act departures (gate achieved, prohibited act)** — the
Milestone 42 radial-dissection pattern, major with management, not
a fail: m6.7 (fixation below the iliopubic tract inside the pain
triangle) → `err.fixation-in-pain-triangle` + nerve-injury;
m6.8 (fixation inside the doom triangle) →
`err.fixation-in-doom-triangle` + vascular-injury with
engine-computed haemorrhage. The two classes are kept distinct in
the data and in the runner: a gate failure is an act on unaccounted
anatomy; a departure is an accounted account violated.

## 6. Fixation and prophylaxis discipline (evidence-scored)

**Fixation is a decision, mechanically real** (dp5, the
Milestone 44 configuration mechanism): `non-fixation` leaves the
required set at 33; `fixation` inserts m6.4–m6.6 (medial into
Cooper's ligament, superior, lateral only ≥2 cm above the tract).
The scoring follows the evidence both ways:

- Fixation performed for a defect that is **not** large medial →
  `err.unnecessary-fixation` (judgment; no complication): *"non-
  fixation of mesh is recommended in almost all hernia types
  except large medial defects"* (T36); *"mesh fixation is
  unnecessary in most MIS inguinal hernia repairs"* (T38).
- A **large medial (M3)** defect completed without fixation →
  `err.no-fixation-large-defect` (major) + a **recurrence**
  complication computed at scoring, managed at dp6: the
  HerniaSurge recommendation (T36), the golden rules (T38), and
  T37's reported recurrence signal for non-fixated direct repairs.
- **Peritoneal closure**: flap sutured (m7.1) without the
  completeness confirmation (m7.2) → `err.incomplete-peritoneal-
  closure` + **bowel-adhesion** computed at scoring (T36: exposed
  mesh causes adhesions/obstruction; T38 Rule 10: gaps should be
  closed), managed at dp6 — the Milestone 28/42/44 scoring-time
  consequence pattern.

**Prophylaxis: none, by design.** *"Antibiotic prophylaxis … is
never recommended in laparo-endoscopic repair"* (T36); *"not
suggested in elective laparo-endoscopic inguinal hernia repair in
any patient and in any risk environment"* (T37). The procedure
therefore carries no prophylaxis microstep; m0.8 authors the
withholding, and the process component's ceiling is **4 of 5 by
design** — documented in the procedure file's scoring block
exactly as at Milestones 42 and 44.

## 7. Variants (cited prevalence only)

| variant | prevalence | source | mechanics |
|---|---|---|---|
| `variant.corona-mortis` | **49.3%** of the population (venous 41.7%, arterial 17.0%) | T40 | Adds structure `artery.corona-mortis` (absence entry) and required microstep m4.4 (protect). Medial fixation (m6.4) in this configuration without m4.4 → `err.corona-unprotected` + haemorrhage at the corona placeholder rate — collateral, major, not a fail (the Milestone 42 persistent-median-artery pattern). The survey itself (m4.1) runs in every configuration. |
| `variant.sliding-hernia` | **2–5%** of indirect inguinal hernias | T41 | Adds required microstep m4.5 (sliding survey). Sac division (m6.1) without it → `err.missed-variant` + visceral-injury → `canal.cecum`, FAIL (the Milestone 17 identify-before-divide pattern). |

Both clear the ≥1% variant gate. **Sourcing care on the sliding
variant:** T41 defines the variant by a viscus forming part of the
sac wall and states it is usually left-sided; it does not name the
viscus by side. The right-sided cecum assignment is recorded in
the register, the variant entry and the procedure file as this
module's anatomical reading, never attributed to T41. Direct/
indirect sac anatomy is handled as survey content (m2.1) and the
defect characterisation the fixation rule keys on, not as variants
— no consulted source states a prevalence split the model could
carry as variant configurations, so none was invented.

## 8. Traces

| trace | configuration | verdict | key computed facts |
|---|---|---|---|
| 21 clean | standard, non-fixation | PASS | 33/33, gate 4/4, process 4/5 (by design), no errors |
| 22 fixate-before-account | no gate demonstrations; m6.4 at t=1200 | **FAIL @ 1200** | vascular-injury → external iliac artery; haemorrhage 300 s × 5.0 = **1500 mL**; management 5/5 does not rescue |
| 23 corona variant | m4.4 performed | PASS | 34/34 required |
| 24 sliding variant | m4.5 performed | PASS | 34/34 required |
| 25 incomplete closure | m7.2 omitted | PASS | missing exactly `[m7.2]`; bowel-adhesion → `peritoneum.peritoneum`; management 5/5 at dp6 |

Ten Rust probes pin what the traces do not: only-crit2 → nerve
FAIL; only-crit3 → vas FAIL; crit1+crit2 missing → vascular
(priority order); unprotected corona fixation → 360 mL two ways
(event integral = engine identity); pain-zone fixation with gate
met → major nerve injury, PASS; doom-zone fixation with gate met
→ 1500 mL, PASS; large-medial + non-fixation → recurrence;
small defect + fixation → unnecessary-fixation judgment with the
required set reconfigured to 36; sliding division without survey
→ cecum FAIL; dp2 continue-dissection → `err.no-bailout` + the
gate resolution.

## 9. Parameters and instruments

Per the Milestone 44 bleeding-rate refusal discipline, no consulted
source states a haemodynamic rate for any vessel in this operation,
and **no rate was presented as sourced**. Two verify-flagged
engineering placeholders were added, in the theatre's existing
placeholder classes, each carrying the full disclaimer text:
`bleed_rate_external_iliac_ml_s` = 5.0 (the replaced-RHA
axial-artery placeholder class) and `bleed_rate_corona_mortis_ml_s`
= 1.2 (the uncontrolled-branch placeholder class). Census: **17
parameters, 12 verify-flagged** (was 15 / 10). Insufflation reuses
the existing cited 15 mmHg parameter (T13) — no duplicate was
created. Instruments 28 → 30: the tacker and the glue applicator,
both cited to T36's fixation-methods list, the tacker's injury
potential grounded in T36/T38/T39.

## 10. Case handoff — none, and the case_check maintenance

No existing case's management names this operation (cases #1–#6
were checked at Milestone 48's state; case #6's profile asserts
the Theatre holds no PE procedure). **No handoff was added and no
file under `cases/` was edited.** Three procedure-set assertions
in `tools/case_check.py` (profiles for cases #4, #5, #6) enumerated
the four-procedure set; each was updated to the real five-procedure
set with its meaning preserved (case #6's "none is an embolectomy"
remains true), in the same maintenance pattern Milestone 44 applied
to case #4's assertion when the ulnar procedure landed. The
maintenance is documented in each assertion's message.
`case_check` passes unchanged in count: **10,298 / 0**.

## 11. Verification (all local, this milestone)

- Baseline discipline: a SHA-256 snapshot of 2,218 files (data/,
  theatre/, cases/, physiology/, tools/, design/) was taken before
  any edit; the post-build tree diff is exactly the batch —
  7 changed files, 11 new files, nothing under `data/`, `cases/`
  or `physiology/`.
- `cargo build --release` clean; `anatomica-theatre validate`:
  5/5 procedures PASS (hernia: 9 phases, 12 steps, 41 microsteps,
  33 required standard; parameters 17, 12 verify-flagged;
  instruments 30).
- `cargo test --release`: **38/38** (28 prior + 10 new probes).
- `run-all`: **25 traces, 0 expectation failures**; the **20 prior
  debriefs are SHA-256 byte-identical** to the baseline snapshot.
- `tools/theatre_check.py`: **595 checks, 0 failures** (was 463).
  One defect was caught by it during the build and repaired: four
  register entries first pointed at clinical files that carry the
  un-sided concepts; they now point at the inventory files that
  carry the sided records, with the notes stating the distinction.
- `tools/case_check.py`: **10,298 passed, 0 failed** (§10).
- All 20 `tools/*_check.py` exit 0; physiology `validate` hard
  gates pass; the native shell's data assertions stand at 99/99
  (GPU render stage unavailable on this VM image — the standing
  disclosed limitation, unchanged since Milestone 28; the native
  shell does not read the theatre module).

## 12. Absence register (8 of 22 entries)

`canal.inguinal` (the canal as a structure), `fascia.transversalis`,
`region.triangle-of-doom`, `region.triangle-of-pain`,
`region.myopectineal-orifice`, `ligament.pectineal` (Cooper's),
`sac.inguinal-hernia` (the general `peritoneum.peritoneal-sac` is a
different denotation and is not substituted), and
`artery.corona-mortis` — **doubly absent**: no anastomosis record
and no obturator artery record at all (the obturator vein and
nerve exist; the artery does not). Each carries a substantive note
and is probed against the full Body Model id set by
`theatre_check.py` every run. The 14 record entries resolve to real
records, including `repro.right-deferent-duct`, whose note carries
the Milestone 40 state exactly: FMA concept record, mesh FJ3140
real but **unclaimed** — claiming it remains a geometry decision
on the Milestone 34 line, not a fact this procedure assumes.

## 13. Honest limits

- **Expert-review gate UNMET** for this procedure, verbatim, as
  for all Theatre content: no named reviewers exist; content is
  `dual-sourced-draft`, scores formative-only, no composite score.
- Both bleed rates are verify-flagged placeholders (§9); volumes
  and physiology responses are engine-computed from them, and the
  rates themselves await a sourced haemodynamics reference.
- The EHS M3 size thresholds in centimetres are not asserted
  (delegated by T36 to a source not opened); the defect rule keys
  on the guideline's own "large medial (M3)" gloss.
- The corona prevalence (49.3%) counts any anastomosis, arterial
  or venous, per the meta-analysis's definition; the 2024 CTA
  study's own measured prevalence (21.74%) is recorded in T40's
  register entry — the variant carries the meta-analytic figure.
- Fixation evidence is genuinely unsettled at the margins (T37:
  trial sequential analysis insufficient; the fixation chapter was
  not updated in 2023). The model encodes the standing HerniaSurge
  recommendation and says so; it does not present the question as
  closed.
- TEP is not authored (§2); endoscopic and open repairs are out of
  scope. Femoral-hernia-specific repair content is survey-level
  only (m2.2), not a separate procedure.
- No physiology representation exists for nerve injury, vas injury,
  recurrence or adhesion; those consequences are structural, as
  with the earlier procedures' non-volume outcomes.

## 14. Next steps

- The Theatre now holds five procedures; the natural sixth
  candidate remains a procedure an existing case names (the case
  line, not this one, decides that).
- The deferent-duct geometry claim (FJ3140, with FJ3135) stays
  queued on the Milestone 34 geometry decision; if claimed, this
  procedure's register note is the first text to update.
- A TEP variant of this repair would reuse the gate unchanged
  (it is approach-shared); authoring it is a content decision,
  not an engine one.
