# Milestone 53 — Physiology: chronic acid–base compensation

The slow axis Milestone 47 named as its omission and its §9
next step: the respiratory module's acid–base was Henderson–
Hasselbalch with acute buffering only (S66 Rules 1 and 3), a
picture that is only true for minutes-to-hours. A disturbance
held for days is answered by the kidney: plasma bicarbonate is
driven to a second, chronic compensated value, and the pH
recovers most — never all — of the way back. This milestone
builds that renal compensation as a slow state beside the
Milestone 30 hormonal axes, on the chronic companion rules of
the same source text the acute rules came from, and measures it
in two sustained arms (five days of held hypoventilation, three
days of held hyperventilation) against predictions computed
before the engine was run.

Discipline, as at Milestones 51/52: the parameter edit is
append-only in the file's original formatting (every
pre-existing entry verified identical in parsed form after the
edit); the state is constructed to be *exactly zero at the
resting equilibrium* — state, target and derivative all zero —
so the pinned resting baseline holds bit-identically;
predictions were computed by an independent solver
(`work/m53/predict.py`, parameters.json constants only, no
engine code) before the engine arms were run; the full validate
output was diffed against the pre-milestone baseline
(`work/m53/validate-pre.txt` → `work/m53/validate-final.txt`)
and every differing line is accounted for in §6.

## 1. The cited relations and the timescale (S73, S74)

The chronic rules are Brandis's, the chronic companions of the
acute rules already in the engine (S66 is the same text):

- **Rule 2 — chronic respiratory acidosis (S73):** "the average
  increase in plasma [HCO3−] in chronic respiratory acidosis is
  **4 mmol/l per 10 mmHg** increase in PaCO2" — a chronic total
  slope of **+0.4 mEq/L per mmHg**. The renal response "is
  underway by 6 to 12 hours and usually takes a few days to
  reach its maximal value… the maximal effect is usually
  reached by **3 to 4 days**", and the compensation "is usually
  NOT sufficient to return the pH to normal… typically, the pH
  will still be slightly acidotic".
- **Rule 4 — chronic respiratory alkalosis (S73):** the
  bicarbonate falls **5 mmol/L per 10 mmHg** decrease in PaCO2 —
  a chronic total slope of **−0.5 mEq/L per mmHg**. "It takes
  **2 to 3 days** to reach maximal renal compensation"; "the
  limit of compensation is reached when the [HCO3−] falls to
  **12 to 15 mmol/l**".

The relations **differ by direction** (0.4 up, 0.5 down), as do
the acute rules they extend (0.1 up, 0.2 down); the engine
carries the two chronic totals as separate parameters, exactly
as the source states them. Both are applied about the model's
own operating point (resting PaCO2 41.095 mmHg, bicarbonate
24 mEq/L), the same construction Milestone 47 used for the
acute rules, rather than about the source's 40 mmHg reference.

**Second source (S74):** eClinpath (Cornell) — the renal
response to a respiratory disturbance "begins within hours but
takes **3–5 days** to have a full effect", stated for **both**
directions; its expected-bicarbonate formulas use **0.35** per
mmHg (chronic acidosis) and **0.55** per mmHg (chronic
alkalosis). The days-scale and the direction-split form are
therefore dual-sourced; the exact slopes are not identical
across sources.

**The spread found in session, and the grounds for the pick.**
Consulted chronic slopes: acidosis **0.35** (S74), **0.4**
(S73 bedside rule), **0.51** (Martinu et al. 2003's measured
mean in stable chronic hypercapnic patients, cited in S73's
own chapter), 0.35 again in secondary reviews ("3.5 per 10");
alkalosis **0.5** (S73), **0.55** (S74), 0.4–0.5 in secondary
reviews. The S73 bedside-rule pair (0.4 / 0.5) is taken, on
stated grounds: they are the chronic rules of the *same source
text* as this engine's Henderson–Hasselbalch form and acute
Rules 1 and 3 (S66), so acute and chronic relations form one
internally consistent rule set, and both sit inside the
consulted spans. Sensitivity, disclosed: at the acidosis arm's
PaCO2 the Martinu slope would predict a chronic total of
45.4 mEq/L and a compensated pH of ≈7.34, against the engine's
40.4 and 7.314 — the pick is worth ≈0.03 of pH at that
disturbance, inside the spread the sources themselves carry
(S74 attaches ±2 mmol/L to its formulas).

**The time constant is calibrated, and the dossier says so
plainly.** No consulted source states a first-order time
constant; the sources state *times to maximal compensation*
(3–4 d acidosis, 2–3 d alkalosis, S73; 3–5 d both directions,
S74). The state's τ is **24 h** (`chronic_compensation_tau_seconds`,
status *calibrated*, cited range [12 h, 36 h] from those
windows): the approach reaches 63% of target at 1 day, 86% at
2 days, 95% at 3 days, 99.3% at 5 days, so the cited maximal
windows read as the approach's 95–99% span. One τ serves both
directions: the sources' windows overlap and no source
supports resolving them into two constants.

Appended: three parameters (`chronic_hco3_rise_per_mmhg`
0.4, cited S73; `chronic_hco3_fall_per_mmhg` 0.5, cited S73;
`chronic_compensation_tau_seconds` 86400, calibrated S73) and
two sources (S73, S74). Library totals after M53:
**141 parameters, 74 sources, 23 perturbation cases** (status
counts 87 cited / 35 calibrated / 19 verify-flagged).

## 2. The state construction and its resting-zero proof

The state `hco3_comp_meq_l` is the **renal increment**: the
bicarbonate the kidney adds *beyond acute buffering*. Its
target at the current PaCO2 is

    target(PaCO2) = chronic_total(PaCO2) − acute_total(PaCO2)

with each total taken from its own cited rule pair (chronic
0.4/0.5, acute 0.1/0.2, each about the operating point). Its
derivative is the first-order relaxation
`d(state) = (target − state) / τ`, RK4-integrated like every
other state in the engine, staged on the stage PaCO2. A derived
observation on the consulted rule set: the increment is
(0.4 − 0.1) = **0.3 mEq/L per mmHg in acidosis** and
(0.5 − 0.2) = **0.3 per mmHg in alkalosis** — the same
increment in both directions. That coincidence is *reported,
not built in*: the code parameterises the two chronic totals,
so a revision of either direction's relation revises that
direction alone.

**Resting zero, exactly.** At the resting PaCO2 the chronic and
acute totals coincide (both are the resting bicarbonate plus a
slope × 0 deviation), so the target is exactly 0.0; the state
is initialised at exactly 0.0; its derivative there is exactly
0.0. The total bicarbonate the Henderson–Hasselbalch readout
sees is acute + state, so at rest the readout is the Milestone
47 value bit-for-bit. Asserted in the validator (resting
compensation line: state +0.0000, PASS) and in the test suite
(state, target and total all exact at a fresh engine; the
resting protocol's readout carries comp = 0.0 and the pinned
hash). The state is respiratory-side only — it feeds no
circulation derivative — and it folds into `resp_hash` (§6).
`Event::SetChronicCompensation` disables it (derivative
identically zero; a state initialised at 0.0 stays exactly
0.0) — the A/B instrument, in the M51/M52 pattern.

**The Bohr interaction, and the anchor.** Every pH the engine
computes now reads the *total* bicarbonate: the resting
readout (unchanged — the state is zero there), `RespReadout.ph`
and `.bicarbonate`, and the pH input to Milestone 52's Bohr
term through `Engine::arterial_ph()`. So in a sustained arm the
compensated pH pulls P50_eff back toward the resting P50 — the
arms measure this (§4). **The anchor does not drift:**
`Model::ph_rest` is a construction constant, computed once in
`Model::from_params` from the resting PaCO2 and bicarbonate; no
state writes it. The compensation moves the pH that is
*compared against* the anchor, never the anchor. The test
suite asserts this directly: after a day of compensated
hypoventilation the arm's pH has moved 0.105 toward the anchor
while a fresh engine's `ph_rest` is bit-identical and the
zero-compensation pH function still evaluates to it exactly.

## 3. The long-course protocol

The chronic arms follow the standard respiratory protocol
(settle to tick 4500, baseline window 4500–6000, reflex
setpoint captured and events fired at tick 6000, standard span
to tick 12000 with its endpoint circulation hash recorded) and
then continue to the arm's mark under the Milestone 24
long-course precedent, the post readout taken over the final
30 s window at the mark:

- **Chronic hypoventilation:** the M47 protocol (rate held at
  6/min, alveolar ventilation halved) held to **+5 days**
  (final tick 21,606,000). Five days is past both cited maximal
  windows for acidosis (3–4 d S73; 3–5 d S74) and is 99.3% of
  the state's approach.
- **Chronic hyperventilation:** the M52 protocol (rate held at
  24/min, alveolar ventilation doubled) held to **+3 days**
  (final tick 12,966,000) — S73's cited 2–3 d maximal horizon
  for alkalosis, 95.0% of the approach.

Each arm runs in compensation-live and compensation-disabled
forms (four new perturbation cases). A measured engineering
consequence, recorded here rather than discovered downstream:
the four arms add ≈69M ticks to `validate`, and they are
**not** listed in the standalone `run respiratory` command —
that listing is re-run by `tools/case_check.py` for case #6
under a 900 s timeout, and the multi-day arms pushed it past
that consumer's contract (measured: the re-run timed out at
900 s while the arms were listed). The arms are gated in
`validate` and in the test suite's one-day forms; the listing
carries a comment saying exactly this.

## 4. Prediction before measurement

The independent solver (`work/m53/predict.py`) integrates the
CO2 store, the rate state and the compensation ODE from
parameters.json constants only (RK4 at 1 s), and evaluates the
oxygen algebra at the resting cardiac output in the M52
solver's form. It was run and recorded
(`work/m53/predictions.txt`) **before** the new engine arms.

**Chronic respiratory acidosis — held hypoventilation, +5 d:**

| quantity | predicted | measured (validate) |
|---|---|---|
| PaCO2 (mmHg) | 82.19 | 82.19 |
| renal compensation (mEq/L) | +12.24 (target +12.33) | +12.24 |
| total bicarbonate (mEq/L) | 40.35 (chronic steady 40.44) | 40.35 |
| pH | 7.314 (acute-only 7.157; rest 7.389) | 7.314 |
| P50_eff (mmHg) | 28.91 | 28.91 |

The disabled twin measures the acute picture held for five
days: bicarbonate 28.11, renal state exactly 0.00, pH 7.157,
P50_eff 34.39 — all as predicted. The A/B deltas at +5 d:
bicarbonate **+12.24 mEq/L**, pH **+0.157**, P50_eff **−5.48**
(the Bohr right shift mostly unwound by the pH recovery) — the
validator's computed values and its bands agree to the printed
digit. The pH recovers *toward, not to,* normal (7.314 against
resting 7.389) — S73's stated behaviour, reproduced by the
arithmetic rather than asserted.

**Chronic respiratory alkalosis — held hyperventilation, +3 d:**

| quantity | predicted | measured (validate) |
|---|---|---|
| PaCO2 (mmHg) | 20.55 | 20.55 |
| renal compensation (mEq/L) | −5.86 (target −6.16) | −5.86 |
| total bicarbonate (mEq/L) | 14.03 (chronic steady 13.73) | 14.03 |
| pH | 7.457 (acute-only 7.609; rest 7.389) | 7.457 |
| P50_eff (mmHg) | 24.67 | 24.67 |

The chronic steady total 13.73 sits inside S73's stated
12–15 mEq/L limit of compensation for this direction (no clamp
is built; no shipped scenario drives the formula below the
limit — §7). Disabled twin: bicarbonate 19.89, pH 7.609,
P50_eff 20.87, as predicted. A/B deltas: bicarbonate
**−5.86 mEq/L**, pH **−0.151**, P50_eff **+3.80**.

Oxygen readouts at the marks are evaluated by the engine at
its final-window cardiac output, the solver at the resting
output; the small differences (e.g. chronic-acidosis CaO2
15.99 measured vs 16.53 at the resting output) are that
window-flow difference, not acid–base disagreement — every
gated quantity (PaCO2, bicarbonate, the state, pH, P50_eff) is
cardiac-output-independent and agrees exactly.

**The acute windows move only by the computed amount.** The
brief's constraint — compensation negligible inside the
existing arms' gated windows — is asserted numerically, not
assumed. At the hypoventilation arm's +75 min the solver
computes the state at +0.464 mEq/L (3.8% of its target): pH
7.160 → **7.167**, P50_eff 34.28 → **34.01**, Bohr CaO2 15.21 →
**15.29** — the engine measures exactly these, and every
pre-M53 gate band the arm carries still passes (§6). At the
hyperventilation arm's +30 min: state −0.102, pH 7.608 →
**7.606**, P50_eff 20.89 → **20.94**. The test suite pins both
arms' states and pH values in bands around the computed
amounts.

## 5. Clinical coherence — stated, not gated

The compensated steady picture these arms produce — a
sustained PaCO2 elevation with the bicarbonate sitting on the
chronic relation and the pH pulled back to just short of
normal — *is* the resting picture of chronic hypercapnia: it
is the state a patient with long-standing CO2 retention
presents in, and the state a chronic-hypercapnia case would
have to start from (an acute decompensation case then reads as
an acute disturbance *on top of* this compensated baseline —
acute-on-chronic — which is precisely the distinction the
bedside rules exist to make). **This milestone is the enabling
step for a future COPD case; the case is not built here**, and
nothing in the case library changes. The arms' disturbance (a
halved alveolar ventilation, PaCO2 82) is more severe than a
typical compensated presentation; the *structure* — elevated
PaCO2, bicarbonate on the Rule-2 relation, pH near-normal but
not normal — is the coherence claim, and it is stated, not
gated, beyond the engine-vs-solver agreement of §4.

## 6. Hash accounting — what holds, what moves, and why

**The circulation hash holds everywhere.** The compensation
state is respiratory-side only (it enters no circulation
derivative and is never folded into the circulation chain), so:

| trace | pre-M53 | M53 | verdict |
|---|---|---|---|
| resting protocol | 0x6369b10e9a71c872 | 0x6369b10e9a71c872 | **holds, bit-identical** |
| haemorrhage −750 circulation | 0xbc683bf2721147ae | 0xbc683bf2721147ae | holds |
| infusion +1000 | 0x2dc2a305fcc4eec2 | 0x2dc2a305fcc4eec2 | holds |
| haemorrhage −1500 | 0xaaa722ae4bb76857 | 0xaaa722ae4bb76857 | holds |
| every respiratory arm @ tick 12000 | resting / 0xbc683bf2721147ae per arm | identical per arm | holds |
| refill observation | 0xbeebab66142aa951 | 0xbeebab66142aa951 | holds |
| course arms (untreated / treated / whole blood / components) | 0xaf89c09ff6c631f9 / 0x9bf0acb245ae9804 / 0x1f07bded860a8d25 / 0x8a61cc46d8f73aa9 | identical | holds |
| long-horizon rest | 0x273e0335ec80c632 | 0x273e0335ec80c632 | holds |

**Every respiratory hash moves, by two accounted causes.**
(1) *Fold format:* the state joins the resp chain after
resp_rate — the fold order is part of that chain's format (the
M25/M26/M30 precedent), so every resp hash differs from its
M52 value even where the trajectory is bit-identical (within
each Bohr A/B pair the two hashes remain equal to each other,
as asserted). (2) *Trajectory:* where the state is non-zero it
reaches the chemoreflex sensor through pH → P50_eff → sensed
PaO2 (the M51/M52 path), moving the rate trajectory
microscopically in the live-reflex arms.

| resp trace | pre-M53 | M53 |
|---|---|---|
| hypoventilation (both Bohr forms) | 0xecd45b6defcdefbb | 0xf892f894750496c7 |
| shunt, coupled | 0x706b1b92daa2fda4 | 0x78f0d42a6209707e |
| metabolic doubled | 0xd726fb354bf79f48 | 0xc4455f6d4429bee5 |
| haemorrhage, module live | 0x4fd5743b78a8a847 | 0x21d2690a25623abe |
| hyperventilation (both Bohr forms) | 0x11e8dea7c599df9c | 0xd379a66ee1d70f2c |
| chronic hypo, live (+5 d) | — | 0x0ad2e7181615112a |
| chronic hyper, live (+3 d) | — | 0xfdca5f2727c6cf84 |

**The validate diff, line by line.** Outside the M53 additions
(the resting compensation line and the four chronic sections),
the differing lines in the pre/post diff are exactly:
hypoventilation readout values moved by the §4 computed
amounts (pH 7.160→7.167, P50_eff 34.28→34.01, Bohr CaO2
15.21→15.29, DO2 639→643, PaO2 51.31→51.30) and its M52 A/B
delta line recomputed at the compensated pH (CaO2 fall
2.09→2.01, SaO2 0.104→0.100, DO2 88→84 — all inside their
bands); hyperventilation likewise (pH 7.608→7.606, P50_eff
20.89→20.94, PaO2 102.05→102.12, A/B PaO2 fall 6.8→6.7);
coupled-shunt PaO2 61.26→61.27 (the sensor-path micro-shift);
metabolic P50_eff print 27.09→27.08; the armed-feedback arm's
final-window HR 102.29→102.30 and DO2 691.12→691.13 (the same
sensor path at print precision); and the resp-hash lines
above. Every moved gate value remains inside its pre-M53 band,
and the full validate was run twice on the final tree with
**byte-identical output** (determinism across runs, not just
within one).

**Baseline caveat, disclosed.** The captured pre-M53 validate
was truncated by a host restart at the hormonal-axes header
(271 lines — it contains the resting, circulation,
respiratory, refill, course and long-rest sections complete,
including every pre-M53 resp hash above). The sections beyond
it (hormonal arms and 12 h courses) have no pre-M53 counterpart
in that file; they are circulation/hormonal trajectories the
new state cannot reach by construction (no respiratory input
changes in those arms; at their resting PaCO2 the state's
target is exactly zero), and their expectations are
independently pinned by the unchanged pre-existing test suite
(§7). Their post-M53 trace hashes are recorded in
`work/m53/validate-final.txt` (water load 0x8c6c52a3c2acf65a,
water control 0x853284d42fc7447b, deprivation 0xe771a4c1a2ae2bb3,
sodium load 0xfe5b4598aff43902, long course untreated
0x21b9979d6ed4a6b4, crystalloid 0xff03fa296e485aa3).

## 7. Non-regression

- physiology `validate`: **ALL HARD GATES PASS**, run twice on
  the final tree, byte-identical outputs
  (`work/m53/validate-final.txt`).
- physiology `cargo test --release`: **37 passed, 0 failed**
  (34 pre-existing, unmodified, plus 3 Milestone 53 tests: the
  resting-zero/anchor construction, the one-day A/B pair with
  the anchor-drift assertions, and the acute-window amounts).
- theatre: `theatre_check` **595 checks, 0 failures**; all
  **25 debriefs byte-identical** (md5 sets in `work/m53/`).
- `tools/case_check.py`: **ALL CHECKS PASS: 10,298 passed,
  0 failed** (after the §3 listing fix: with the chronic arms
  listed in `run respiratory`, case #6's re-run of that command
  timed out at the checker's 900 s cap — a consumer-contract
  failure, found and repaired by unlisting the arms, which are
  gated in `validate` instead).
- `tools/readme_check.py`: **ALL CHECKS PASS** on the final
  tree (README updated: physiology counts 141 parameters /
  74 sources / 23 cases, status counts 87/35/19, the M53 index
  row, and the file index reconciled to the milestones/
  layout — dossiers moved by a layout change during this
  milestone; root now carries 3 files and `milestones/`
  carries 58, this dossier among them; total 458 files).
- `tools/assembly_check_all.py`: ALL GATED CHECKS PASS;
  `tools/verify_web.js`: ALL CHECKS PASS. (Native verify counts
  are re-checked inside readme_check R9: 99 PASS / 0 FAIL. One
  environment note: readme_check's first run on this tree
  failed its R9 imaging line because the VM image lacks
  pydicom/nibabel (`imaging_toolkit_check` printed 0 PASS,
  exit 1); with the two packages installed for the system
  Python the toolkit check passes standalone — 84 PASS, ALL
  HARD CHECKS PASS — and readme_check is green end-to-end. No
  tree file was involved in that failure.)

## 8. Honest limits — and what the module still cannot do

- **Respiratory disturbances only.** The state compensates a
  sustained PaCO2 disturbance. There are **no metabolic
  acid–base disorders** in the engine: no metabolic acid load
  exists as a state or input (the metabolic arm varies VO2,
  not acid), so there is nothing for a metabolic compensation
  to answer, and **no respiratory response to a metabolic
  disturbance** is built — the chemoreflex as constructed
  (M47/M51) senses PaCO2 and PaO2, not pH or bicarbonate. The
  consulted sources do state the respiratory response to
  metabolic disorders (Winter's-formula family), but scoping
  it honestly requires the metabolic disturbance itself first;
  it is named here as unbuilt rather than half-built.
- **The chronic relations are bedside rules**: population
  averages with a real spread (§1: 0.35–0.51 acidosis,
  0.5–0.55 alkalosis, ±2 mmol/L bands in S74). The engine
  reproduces one consistent rule set exactly; it does not
  model the inter-patient variance the spread represents.
- **One time constant, calibrated, both directions** (§1): the
  approach *shape* (first-order) and its τ are the model's
  conversion of cited maximal-effect windows, not cited
  physiology. A reader who needs the trajectory at 12–48 h to
  better than a few tenths of a mEq/L needs a source this
  build does not have.
- **The alkalosis compensation limit is not clamped** (S73:
  bicarbonate does not fall below ≈12–15 mEq/L). The shipped
  alkalosis arm's chronic total is 13.73, inside the limit;
  the linear rule extrapolated to extreme hypocapnia
  (PaCO2 ≲ 17) would cross it. No shipped scenario goes there;
  the limit is disclosed in the parameter note and here.
- **Override arms suspend the reflex**, so in the gated arms
  ventilation does not itself respond to the compensated pH —
  by protocol design (the disturbance is *held*). In
  live-reflex arms the compensated pH reaches ventilation only
  through the existing PaCO2/PaO2 sensor paths; a direct
  pH-sensitive ventilatory term is not modelled (the M47
  controller's stated form).
- Still unmodelled from earlier lists: 2,3-BPG (a real
  chronic-hypoxia/acidosis effect on the same curve the Bohr
  term positions — M52's named limit, unchanged), temperature,
  intrathoracic-pressure effects on venous return.

## 9. Next steps

1. **The COPD case** (§5): a chronic-hypercapnia case on this
   compensated baseline, with an acute-on-chronic decompensation
   arm — the case workbench's first respiratory-primary case,
   and the consumer this milestone was the enabling step for.
2. **Metabolic acid–base**: an acid-load state/input with its
   cited generation/clearance, the Henderson–Hasselbalch
   readout already generalises (it reads the total
   bicarbonate) — then the respiratory response to metabolic
   disturbance (Winter's-formula family) as the symmetric
   slow/fast pairing, with its own sources.
3. A **2,3-BPG state** on the dissociation curve, if a
   consulted source supports its kinetics — it shares the
   curve-position machinery with M52's Bohr term and this
   milestone's pH path.
