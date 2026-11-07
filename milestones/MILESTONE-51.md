# Milestone 51 — Physiology: two-way coupling

## 1. What this milestone is

Milestone 47 built the respiratory module under a load-bearing
restriction: **one-way coupling**. Oxygen transport read the
circulation (cardiac output, haemoglobin) but no respiratory
quantity entered any circulation derivative, so the case-pinned
resting circulation trace hash (`0x6369b10e9a71c872`, cases
#1/#3/#6) survived by construction. Three couplings were deferred
by name: the hypoxic ventilatory drive, the Bohr shift, and the
metabolic–circulatory feedback (the sympathetic/metabolic
response to an oxygen-delivery shortfall).

This milestone builds the first and third, under the brief's hard
constraint: **the pinned resting baseline must still hold** — the
admissible design space is couplings that are exactly zero at the
resting equilibrium. Both couplings are built in that space:

- **Hypoxic ventilatory drive** — always live, respiratory-side
  only, constructed as an *increment about the captured operating
  point* so its value at rest is exactly zero (§2).
- **Metabolic–circulatory feedback** — a DO2-error term into the
  baroreflex heart-rate multiplier, zero inside a deadband around
  the captured resting delivery, and **scenario-armed** (disarmed
  by default in every shipped protocol), because §3.3 proves an
  always-on version cannot satisfy the full non-regression set.
  Even armed at rest it reproduces the pinned hash bit-for-bit
  (test-asserted, §5.1).

The Bohr shift remains deferred (§7).

New totals: **137 parameters** (was 130), **71 sources** (was
67), **15 perturbation cases** (was 13); parameter status counts
84 cited / 34 calibrated / 19 verify-flagged (was 79 / 34 / 17).

## 2. Coupling 1 — the hypoxic ventilatory drive

### 2.1 The cited form

Weil et al. (S68, *J Clin Invest* 1970) measured the ventilatory
response to hypoxia at controlled alveolar PCO2 and fit the
hyperbola

    VE = VE0 + A / (PAO2 − 32)

with **A = 180.2 ± 14.5** L/min·mmHg at the subjects' resting
PACO2 (10 subjects), the asymptote at **32 mmHg** (the paper's
fitted range is 30–40), and the response essentially complete in
18–23 s. The same paper measured A at clamped PACO2 ±5 mmHg
(6 subjects): **A = 453.4 ± 103** at +5 and **A = 30.2 ± 6.8** at
−5 — hypercapnia multiplies the hypoxic response ~2.5×,
hypocapnia nearly abolishes it. The control-of-breathing
literature states the same interaction qualitatively (S69):
peripheral chemoreceptors sense arterial PO2 (not content),
ventilation rises little until PaO2 falls below ~60 mmHg, and the
PO2×CO2 interaction is **synergistic — more than additive**.

### 2.2 The construction

The term added to the chemoreflex's minute-ventilation target is

    hyp(PaCO2, PaO2_s) = A_eff(PaCO2) × [ 1/(PaO2_s − 32) − 1/(PaO2_set − 32) ]

clamped to [0, 40] L/min, where:

- **PaO2_s is the sensed arterial PO2**, computed by the module's
  own gas-exchange construction (alveolar gas equation at the
  current PaCO2 → end-capillary content → Berggren mixing at the
  current admixture and metabolic rate → content inversion) at the
  **last completed beat's cardiac output** — the beat-window
  evaluation the M24 discipline established for transport
  readouts. The chemoreceptors sense PO2, not content (S69); this
  is the arterial PO2 of the model's own physiology, not the
  alveolar one.
- **PaO2_set is that same sensor's value at the captured resting
  operating point** (91.24 mmHg), captured in
  `set_reflex_setpoint` alongside the M47 chemoreflex setpoint and
  the baroreflex setpoint — the model's own operating point, the
  house construction.
- **A_eff(PaCO2) is Weil's shape parameter interpolated
  log-linearly between the paper's three anchors** (30.2 at
  PaCO2_set − 5, 180.2 at PaCO2_set, 453.4 at PaCO2_set + 5,
  clamped outside). This PaCO2-dependence *is* the cited
  interaction: the term is additive at the VE level, but its gain
  is potentiated by hypercapnia and withdrawn by hypocapnia
  exactly as S68's data and S69's "synergistic" statement require.
  Modelling CO2-only above a threshold was the alternative the
  brief allowed; the sources support the stronger form, so the
  stronger form is built.

**Zero at the resting equilibrium, by construction:** at the
operating point the two reciprocals are the same number, so the
term is A × 0 = 0 identically; the clamp additionally guarantees
the term never subtracts drive when the sensed PO2 sits above
the operating point. Measured at the resting readout: **0.0000
L/min** (validate asserts < 0.05; §5.1). The term is also
respiratory-side only — it enters `d_rr` and nothing else — so
the circulation hash is structurally unable to move, the M47
argument unchanged.

The rate override (`SetVentilationOverride`) suspends this limb
with the CO2 limb, as a held rate must. A new event,
`SetHypoxicDrive { enabled }` (default enabled), disables the
term alone, reproducing the M47 CO2-only controller exactly — the
A/B instrument of §5.2. The term is sampled once per tick from the
base state (the sensor's cited response time is 18–23 s; the tick
is 20 ms) rather than per RK4 stage, keeping the content
inversion out of the integrator's inner loop.

### 2.3 The coupled shunt — prediction before measurement

At admixture 0.20 the sensed PaO2 falls to ~61.5 mmHg. The
coupled equilibrium solves the PCO2 equation, the controller
(CO2 limb + hypoxic term) and the sensor simultaneously. Solved
**independently of the engine** (a from-the-equations solver over
the parameters.json constants, `work/m51/predict.py`):

| quantity | pure (M47) | coupled prediction |
|---|---|---|
| PaCO2 | 41.095 mmHg | **40.24 mmHg** |
| VE | 6.000 L/min | **6.13 L/min** |
| PaO2 | 61.31 mmHg | 61.53 mmHg |
| hypoxic term | — | 2.26 L/min (A_eff fallen to ~133) |

The fall is deliberately modest, and the mechanism is the
sources' own: as ventilation rises and PaCO2 falls, (a) the CO2
chemoreflex withdraws 2.5 L/min per mmHg (S58) and (b) A_eff
collapses toward Weil's hypocapnia anchor (180 → ~133 here;
toward 30.2 at −5 mmHg) — the poikilocapnic response is
self-limiting. An unopposed-drive construction would have driven
PaCO2 into the low 30s; the coupled case's band [38.5, 42.0]
gates the computed equilibrium and the engine's result lands on
the prediction (§5.2).

## 3. Coupling 2 — the metabolic–circulatory feedback

### 3.1 The cited mechanism

As oxygen delivery falls, the body defends oxygen consumption by
raising extraction and **raising cardiac output**; below a
critical delivery (DO2crit ≈ **300 mL/min** in adults, S71) VO2
becomes supply-dependent (S70, S71). The engine's dossiers have
named the delivery-error limb as missing since M47: the
baroreflex defends *pressure*, and nothing in the model senses
*delivery*.

### 3.2 The construction

When armed, a multiplier on the baroreflex heart-rate term:

    err  = (DO2_set − DO2_sensed) / (DO2_set − DO2crit)
    mult = 1 + gain × max(0, err − deadband)

- **DO2_set** is the sensed resting delivery captured at
  engagement through the module's own readout at the last
  completed beat's CO (~828 mL/min) — the operating-point
  capture, again.
- **DO2_sensed** is the same readout at the current state
  (PaCO2, haematocrit, sensor CO). DO2crit = 300 mL/min (S71,
  cited) sets the error's scale: err = 1 is delivery *at* the
  critical threshold.
- **gain 0.6** and **deadband 0.05** are **verify-flagged**
  project constructions — no consulted source states a lumped
  gain of this form, and the precision law forbids dressing them
  as cited. The product passes through the existing reflex HR
  clamp, so the feedback can never drive rate outside the
  baroreflex's own bounds.
- **Zero at the resting equilibrium, by construction:** at the
  operating point err = 0 (up to sub-1% beat noise), inside the
  5% deadband, so `max(0, err − deadband)` is exactly 0 and the
  multiplier is exactly 1.0 — and multiplication by 1.0 is a
  bitwise identity in IEEE arithmetic, so an *armed resting run
  still prints the pinned hash* (test-asserted, §5.1).

### 3.3 The design finding: always-on is impossible under the full constraint set

The brief's admissible space is couplings that are zero at the
resting equilibrium. This coupling satisfies that. But the
milestone's non-regression scope is wider than the resting hash:
theatre debriefs must stay byte-identical and the standard
haemorrhage window must pass *on its own terms*. Against that
full set, an **always-on** version has no admissible
construction:

- The theatre corpus contains a 1,500 mL loss (trace 22, external
  iliac bleed) whose delivery deficit at its nadir *exceeds* the
  −750 mL arm's. Any deadband/gain pair that engages in the
  −750 mL scenario arm engages there too — no threshold separates
  the two by magnitude, because the scenario arm is the *smaller*
  insult.
- Engaging during any theatre trace changes its beats, and the
  debriefs embed the engine's trace hash and beat data: the
  debrief set moves. Likewise the standard haemorrhage_750 run's
  window is a shipped gate (its armed standard-window HR measures
  115.2 against the unarmed course — inside the ATLS band, but a
  *different number*, and the run's hash moves).

So the coupling is **scenario-armed** (`Event::SetOxygenFeedback
{ armed }`, default disarmed): every shipped protocol — cases,
theatre, the standard runs — executes with the multiplier at
exactly 1.0, and a scenario that wants the mechanism arms it
explicitly, the way scenarios already arm bleeds and overrides.
This is reported as a design finding, not worked around: the
resting-zero construction exists and is proven; the always-on
form is what is impossible, and the milestone does not move a
single pinned or shipped number to accommodate it.

## 4. Parameters (Milestone 51 additions; append-only)

| parameter | value | status | source |
|---|---|---|---|
| `hypoxic_shape_a_l_min_mmhg` | 180.2 | cited | S68 (Weil 1970, resting PACO2) |
| `hypoxic_shape_a_at_paco2_plus5` | 453.4 | cited | S68 (PACO2 +5 mmHg) |
| `hypoxic_shape_a_at_paco2_minus5` | 30.2 | cited | S68 (PACO2 −5 mmHg) |
| `hypoxic_asymptote_mmhg` | 32.0 | cited | S68 (fitted range 30–40) |
| `do2_critical_ml_min` | 300.0 | cited | S71 (adult DO2crit) |
| `metabolic_feedback_deadband` | 0.05 | **verify-flagged** | — (project construction) |
| `metabolic_feedback_hr_gain` | 0.6 | **verify-flagged** | — (project construction) |

Sources added: **S68** Weil JV et al., *J Clin Invest* 1970
(hypoxic response hyperbola + PaCO2 anchors); **S69**
control-of-breathing textbook chapter (peripheral chemoreceptors
sense PaO2; sub-60 mmHg onset; synergistic interaction);
**S70** perioperative DO2 review (compensation by CO/extraction;
supply dependence below DO2crit); **S71** Final FRCA revision
corpus (DO2crit ≈ 300 mL/min; compensation routes). Perturbation
cases added: `shunt_hypoxic_coupled`, `hemorrhage_750_metabolic_feedback`.

## 5. Results

### 5.1 Resting preservation — the proof

Four independent witnesses, all measured on the final tree:

1. **Validate diffed against the pre-M51 baseline** (same binary
   inputs, `work/m51/validate-pre.txt` → `validate-post.txt`):
   the resting section is *unchanged line for line* outside one
   added line — the coupling line itself: `sensed PaO2 91.24
   mmHg, hypoxic drive term 0.0000 L/min (criterion < 0.05)
   PASS`. Every resting readout (PaCO2 41.10, PaO2 91.24, pH
   7.389, SaO2 0.965, CaO2 19.66, VE 6.00, DO2 828) prints its
   pre-M51 value. Exit 0, **ALL HARD GATES PASS**.
2. **Resting circulation hash: `0x6369b10e9a71c872`** — printed
   by validate, identical in every respiratory arm at the
   standard endpoint, and reproduced by the M51 test that arms
   the metabolic feedback on a resting run
   (`metabolic_feedback_armed_at_rest_keeps_pinned_hash`, with
   `oxygen_feedback_multiplier() == 1.0` asserted exactly).
3. **Circulation-case identity**: no circulation case line
   appears in the validate diff at all — haemorrhage, bolus,
   course and hormone runs are bit-identical, including the
   module-live haemorrhage arm's hash at tick 12000
   (`0xbc683bf2721147ae`, the standard haemorrhage_750 hash) and
   its M18 standard-window gate.
4. **Theatre**: run-all over the 25 traces regenerates debriefs
   byte-identical to the pre-M51 set (md5-verified, §6) — the
   feedback is disarmed there by construction, and the hypoxic
   drive is respiratory-side only.

### 5.2 The shunt, coupled — M47 picture vs M51 picture

| at +30 min, admixture 0.20 | pure (drive disabled) | coupled (drive live) | mechanism |
|---|---|---|---|
| PaCO2 | 41.10 mmHg | **40.24 mmHg** | hypoxic drive adds ventilation; CO2 limb + A-collapse limit the fall |
| VE | 6.00 L/min | **6.13 L/min** | Weil term +2.26 L/min at the sensor, −2.13 withdrawn by the CO2 limb |
| PaO2 | 61.32 mmHg | 61.54 mmHg | oxygenation **unrepaired** at fixed admixture — the drive trades PaCO2, not shunt fraction |
| A–a gradient | 39.20 mmHg | 40.00 mmHg | widens slightly as alveolar PO2 rises with VA |
| resp trace hash | `0x52d94cb3aa3b1755` | `0x086de28caccca717` | the pure arm's hash equals the pre-M51 shunt arm's exactly |

Engine vs independent prediction (§2.3): PaCO2 **40.24 vs
40.24**, VE **6.13 vs 6.13**, PaO2 **61.54 vs 61.53** — agreement
at print precision on every quantity. The pure arm reproduces
M47's picture *bit-for-bit* (same resp hash), so the contrast is
an A/B on one binary, not a comparison across versions. The
legacy `shunt_20pct` case still passes on the coupled run (its
PaCO2 band is the resting band; the coupled case's own lines are
what gate the coupling). The metabolic-doubling arm also moves
slightly with the drive live — PaCO2 43.26 → 43.00, VE 11.40 →
11.47 (sensed PaO2 ~83 mmHg sits in Weil's shallow region; the
term there computes to ~0.7 L/min) — all its legacy gates pass
unchanged.

### 5.3 The haemorrhage, feedback armed — against M47 and against the cited direction

Same −750 mL protocol, feedback armed at engagement vs the M47
unarmed arm, read at +30 min (steady state, M24 discipline):

| | unarmed (M47) | armed (M51) | cited expectation (S70/S71) |
|---|---|---|---|
| final-window HR | 92.3 /min | **102.3 /min** (+10.0) | compensation raises rate/CO toward the deficit ✓ |
| DO2 at the mark | 689.7 mL/min | **691.1 mL/min** (+1.4) | delivery defended toward, never above, baseline ✓ (still −17% vs rest: partial compensation, no volume created) |
| standard-window HR | (M18 course) | **115.2 /min ∈ [100, 120] PASS** | the M18 ATLS Class II gate holds with the feedback live |
| circulation hash @12000 | `0xbc683bf2721147ae` | differs (feedback live during the bleed — the point of the arm) | — |

The HR course is the mechanism's visible signature; the DO2 gain
at +30 min is small for a stated reason: by then refill and
recruitment have already restored most of the deficit (the
normalised error is ~0.26, multiplier ~1.13), and in this engine
cardiac output at that state is preload/elastance-limited, so
extra rate buys little flow — the feedback's larger effects are
in the early window (the standard-window HR carries it, +~10
/min over the unarmed course). Both cross-run assertions (DO2
and HR must rise against the unarmed arm) are hard gates in
validate, and both pass. The unarmed module-live arm itself is
nearly untouched by the hypoxic limb (PaCO2 41.10 → 41.07, DO2
689.66 → 689.68): at PaO2 89.7 the Weil term computes to ~0.08
L/min — disclosed here because the arm's resp hash moves for it;
its circulation hash and gates do not move at all.

## 6. Verification matrix (final tree)

- physiology `cargo test --release`: **30/30** (27 pre-existing +
  3 M51: resting zero + coupled-shunt A/B; armed-resting pinned
  hash; armed-haemorrhage direction).
- physiology `validate`: **exit 0, ALL HARD GATES PASS**; diff vs
  the pre-M51 baseline confined to the M51 additions and the
  three drive-live respiratory arms (§5).
- theatre `cargo test --release`: **16/16**; run-all 25 traces,
  debriefs **byte-identical** to the pre-M51 md5 set.
- `tools/case_check.py`: **10,298 passed, 0 failed** (unchanged —
  the cases pin the resting hash, which did not move).
- `tools/readme_check.py`: **64 PASS** — with the README's
  physiology figures updated to the re-derived counts (137
  parameters, 71 sources, 84/34/19, 15 perturbation cases), the
  M51 index row and file-index entry added.
- `tools/assembly_check_all.py`: ALL GATED CHECKS PASS;
  `tools/verify_web.js`: ALL CHECKS PASS; native verify: 99 PASS
  / 0 FAIL data assertions (headless-GPU exit tolerated as
  before).

## 7. Honest limits

- **Sensor flow is the last completed beat's CO** — beat-window
  sensing, the M24 pattern. Intra-beat flow variation is unseen
  by both couplings; both terms are sampled once per tick (20 ms)
  rather than per RK4 stage, a numerics choice that is immaterial
  against the cited response times and is disclosed in the code.
- **The hypoxic limb rides the lumped 90 s chemoreflex tau**
  (S59). Weil's subjects equilibrated in 18–23 s (S68), so the
  real hypoxic limb is probably *faster* than the CO2 limb; the
  module has one rate state and one tau, and splitting them is a
  structure change this milestone did not make. Steady-state
  results (everything gated here) are unaffected.
- **Weil's anchors are small-n and isocapnic** (10 subjects at
  resting PACO2, 6 at ±5 mmHg, healthy young men, 1970). Applied
  poikilocapnically, the interpolation between three anchors is
  this project's construction; log-linear vs linear interpolation
  moves A_eff at the coupled point from ~133 to ~149 and the
  predicted PaCO2 by ~0.15 mmHg — inside the gated band either
  way, but the anchor set's thinness is the term's real
  uncertainty, not the interpolation.
- **DO2crit's source is a revision corpus (S71), not a primary
  measurement.** It enters only as the error's normalisation
  scale (and the deadband keeps it from binding at rest); the
  feedback's *gain* has no citable value in the consulted
  literature and is verify-flagged rather than dressed up.
- **VO2 is still never supply-limited.** Below DO2crit the real
  body accrues an oxygen debt; the feedback senses the delivery
  error, but consumption stays at its set rate and no debt/lactate
  state exists. The sensor half of supply dependence is built;
  the metabolic half is not.
- **The feedback acts on heart rate only.** The sources name CO
  (rate × stroke volume) and extraction; the contractility
  effector existed and could have carried a share, and extraction
  (O2ER) remains a readout, not an actuator. HR-only is the
  smallest construction that expresses the mechanism.
- **The Bohr shift is still absent** (M47 deferral stands): the
  sensor's Hill curve is the fixed one; acidemia does not shift
  P50, so in the hypoventilation arm the sensed PO2 is the
  un-shifted value.

## 8. Next steps

1. An oxygen-debt state (supply-dependent VO2 below DO2crit with
   a lactate/acid–base consequence) — the metabolic half of S70's
   mechanism, which would also give the feedback a second,
   slower signal to sense.
2. Split chemoreflex time constants (fast hypoxic limb ~20 s,
   S68; lumped CO2 limb 90 s, S59) if a transient-response case
   ever gates the approach rather than the equilibrium.
3. The Bohr shift (M47's remaining deferral): a pH/PaCO2-shifted
   P50 in the content equation — it changes resting readouts not
   at all (the shift is zero at the resting pH by the same
   operating-point construction) but re-opens every gas gate, so
   it wants its own milestone.
4. A primary-source DO2crit (the anaesthesia/critical-care
   literature behind S71's figure) to promote `do2_critical_ml_min`
   from a corpus citation, and any citable lumped gain for the
   feedback to retire its verify flag.
