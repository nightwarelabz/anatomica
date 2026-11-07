# Milestone 25 — Physiology: renal excretion + interstitial compartment

**Status: built and validated locally. No upload performed or implied.**

Milestone 24 closed with the volume side precisely scoped: the venous-
return formulation was sound, and the two remaining omissions were
**renal excretion** ("now the binding volume-side omission") and the
**missing interstitial state** — together they were why the treated
bolus arm could not redistribute ("the bolus cannot redistribute — no
interstitial compartment beyond the bounded lumped escape, so the litre
stays intravascular") and why infusion magnitudes stayed unvalidated.
This milestone builds both, in the same discipline as every physiology
milestone: sources consulted in-session and cited per parameter,
calibrations inside cited bands with sweeps disclosed, nothing tuned
silently, soft lines kept soft.

**Headline results:**

- The resting steady state is now proven over a **full engaged hour**
  (Milestone 24's resting evidence was a 30-second window): post-
  transient drift MAP 0.050% / CO 0.164% against the project's 1%
  criterion, and the **equilibrium urine output is 1.01 mL/min**,
  inside its cited band [0.7, 1.4] mL/min (S24: 1–2 L/day). Over the
  engaged hour the kidney excretes 60.4 mL against 60.0 mL of intake —
  the model sits at Guyton's equilibrium point, measurably.
- The treated arm's bolus now **redistributes and is excreted**: the
  bolus's intravascular advantage at +60 min is **0.49 of the litre**
  on the plasma-expansion construction volume kinetics uses (treated
  minus untreated blood volume), against Hahn's ~20% post-distribution
  retention in normovolaemic volunteers (S27) — higher, in the
  direction hypovolaemia predicts (S28). The new soft line
  `bolus_retention_60min` ∈ [0.20, 0.95] **passes at 0.49**.
- Every prior hard gate holds, including the −750 mL Class II heart-
  rate band (102.1/min) and all Milestone 24 Guyton gates (resting
  MSFP 6.29 mmHg; RVR two-way agreement 6.1%). No existing parameter,
  gain, bound, or dynamic was changed in value; the refill conductance
  k = 0.04 was **not** re-tuned to compensate for the new feedback.

## 1. Formulation

### 1.1 The interstitial reservoir

The Milestone 18 refill state was always the net transfer integral
between blood and interstitium; what it lacked was the reservoir on the
other side. Milestone 25 gives the reservoir a finite capacity and a
pressure:

- **Capacity (identity, not a new ODE state):**
  `V_isf = interstitial_volume_ml − refill_ml`, with
  `interstitial_volume_ml = 11,000 mL` (S25; §2). The reservoir starts
  full at its cited resting volume and is drawn down or filled exactly
  by what the refill state transfers.
- **Pressure feedback in the Starling driver.** The reservoir's
  pressure deviation from its operating point is
  `ΔP_isf = −refill_ml / C_isf`, with `C_isf` a single lumped linear
  compliance (§2). The refill flow becomes

  ```
  Q_refill = k · [ (Pcap_ref − Pcap_lp) − refill_ml / C_isf ]
  ```

  Depleting the reservoir lowers its pressure and brakes further
  refill; filling it raises its pressure and brakes further escape.
  The driver remains self-referenced (operating-point deviations only,
  the engine's standing convention since v0) — the absolute
  interstitial pressure (−3 mmHg in the source tradition, S26) is a
  property of the operating point, not a state.
- **Bound.** The Milestone 18 hard bound (`|refill| ≤
  refill_reserve_ml`, 1,000 mL both ways) is **retired**: the flow now
  stops only at the reservoir's physical floor (no refill once
  `V_isf` would go negative — refill ≥ 11,000 mL, never approached in
  any shipped scenario) and is otherwise braked continuously by the
  pressure term. `refill_reserve_ml` remains in the parameter file
  with an appended amendment: S15's 500–1,000 mL figure is still the
  cited envelope the 60-minute course refill is read against; it no
  longer constrains any flow.

Because escape now meets a rising interstitial pressure, an infused
crystalloid load redistributes on the pathway's own time course
(the lumped conductance against a filling reservoir) instead of
staying intravascular behind an arbitrary symmetric cap.

### 1.2 The lumped renal function curve

A Guyton-tradition renal function curve (S23) — explicitly a **lumped
pressure–output relation, not nephron modelling** (the Body Model has
no nephron either: Milestones 12/23 record the urinary interior as
absent from the source anatomies, so the kidney exists in this system
only as this curve, which is also how Guyton's long-term pressure
control treats it).

Urine flow out of the systemic venous compartment:

```
U(map_lp) = U0 · m(map_lp − MAP_setpoint)

m(d) = 0                                  d ≤ −50 mmHg
       1 + d/50                           −50 < d < 0
       1 + d·(3−1)/50                     0 ≤ d ≤ +50      → 3× at +50
       3 + (d−50)·(7−3)/50                +50 < d ≤ +100   → 7× at +100
       7 + (d−100)·(7−3)/50               d > +100 (extrapolated slope)
```

The anchors are S23's cited shape (Figure 19-1: output essentially
zero at 50 mmHg, normal at 100, 6–8× at 200; Figure 19-3 analysis:
~3× intake at 150), applied **relative to the model's captured
operating point** — the same self-referencing device as the baroreflex
setpoint and the refill capillary reference, and necessary for the
same reason: the model's operating MAP (~73 mmHg, set by the lumped
S1 vascular parameters) is not the source's 100 mmHg. What is cited
and carried is the shape — offsets and multiples — not the source's
absolute pressure axis; this is disclosed on the parameters
themselves. The shipped curve is the chapter's **acute**
(isolated-kidney) shape; the chronic in-vivo curve is far steeper,
partly through sympathetic and hormonal mechanisms this engine does
not model (§6).

A constant lumped **intake** of 1.0 mL/min enters the same compartment,
set equal to U0 by the source's equilibrium construction (the
equilibrium point is where the intake line intersects the output
curve; the source figure ignores nonrenal losses, and so does this
term). Two engagement rules keep the protocol honest:

- **Before the reflex engages** (no operating point exists), urine
  output is held exactly equal to intake, so the 120-second settle
  and the baseline window are undisturbed by construction — the
  pre-engagement trajectory is the Milestone 24 trajectory plus two
  exactly-cancelling boundary fluxes.
- **After engagement** the curve acts on the sensed (low-passed) MAP.
  No additional lag is imposed: pressure diuresis in the source acts
  within minutes, and the sensing channel's 3-second lag is not the
  timescale that matters here; disclosed as a modelling choice.

Both cumulative states are RK4-integrated and **folded into the trace
hash** (after `ino_mult`; fold order is part of the trace format), so
every Milestone 25 hash differs from Milestone 24's even where
trajectories agree at print precision. The volume-conservation
identity extends to all four boundary fluxes (event channel, refill,
intake, urine) and still closes at ~1e-9 mL.

## 2. Parameters and sources

New sources consulted in-session (full citations and locators in
`physiology/parameters.json`):

| Source | What it carries |
|---|---|
| S23 Guyton & Hall, Textbook of Medical Physiology, ch. 19 (renal–body fluid system) | The renal output curve's anchors (zero at −50, ~3× at +50, 6–8× at +100); the equilibrium-point construction; intake as a determinant of long-term pressure; the chronic curve's greater steepness (partly hormonal) |
| S24 OpenStax Anatomy & Physiology 2e, §25.5 | Normal urine production 1–2 L/day (0.69–1.39 mL/min); worked value 0.9 mL/min = 1,296 mL/day |
| S25 Boundless A&P (LibreTexts), §25.2B | ECF typically 15 L, of which 12 L interstitial + 3 L plasma; "about 11 liters" of interstitial fluid on average |
| S26 Himeno et al. 2016, Integrative Medicine Research (PMC5381436) | The experimental interstitial pressure–volume relation as a fitted curve (their eq. 9′); P_isf0 = −3 mmHg; local slope at the operating point ⇒ whole-body compliance of order 200–370 mL/mmHg scaled to an 11 L interstitium |
| S27 Hahn 2024, Frontiers in Physiology 15:1439035 | Post-distribution plasma expansion ≈ 20% of the infused volume in volunteers; ≈ 50% during infusion; sequential recruitment of interstitial spaces by infusion size |
| S28 Hahn, "Crystalloid fluids" (Clinical Fluid Therapy in the Perioperative Setting; reproduction consulted, status recorded) | Distribution plasma→ISF completes in 25–30 min (half-life ≈ 8 min); elimination half-life ≈ 60 min (Ringer's) / ≈ 130 min (saline); both slowed by blood loss |

New parameters (7; 61 total):

| Parameter | Value | Status | Basis |
|---|---|---|---|
| `interstitial_volume_ml` | 11,000 mL | calibrated in [10,000, 12,000] | S25's two figures (11 L average; 12 L as the ECF split) and the classical 70-kg accounting |
| `interstitial_compliance_ml_mmhg` | 300 mL/mmHg | calibrated in [150, 550] | S26's fitted curve's local slope over the visited volume band; sweep in §4 |
| `baseline_urine_output_ml_min` (U0) | 1.0 mL/min | calibrated in [0.7, 1.4] | S24: 1–2 L/day; 1.0 = 1,440 mL/day |
| `fluid_intake_ml_min` | 1.0 mL/min | calibrated in [0.7, 1.4] | Set equal to U0 by S23's equilibrium construction (disclosed) |
| `renal_pressure_zero_offset_mmhg` | 50 mmHg | cited | S23 Fig. 19-1 (zero at 50, normal at 100) |
| `renal_multiple_at_plus_50_mmhg` | 3.0× | cited | S23 Fig. 19-3 analysis (~3× intake at +50) |
| `renal_multiple_at_plus_100_mmhg` | 7.0× | cited | S23 Fig. 19-1 (6–8× at +100; midpoint) |

Plus: a gated `urine_output` validation range [0.7, 1.4] mL/min (S24);
the course's new `bolus_retention_60min` soft expectation (S27, with a
measurement note correcting its own ceiling wording before first use —
on the difference construction Milestone 24's value derives to 0.37
from its published refill figures, and the ~1.0 figure describes the
bolus's own net Starling persistence, not this metric); and appended
amendments (never silent rewrites) on `refill_reserve_ml`,
`refill_conductance_ml_s_mmhg`, the course case, and the refill
observation.

## 3. Resting validation — and the long horizon

The standard resting case is **unchanged at recorded precision**: HR
63.3/min, BP 97.7/62.7 mmHg, MAP 73.1 mmHg, CO 4.21 L/min, SV 66.6 mL,
CVP 4.38 mmHg — every Milestone 24 value identical, because at the
operating point the kidney excretes exactly the intake and the
reservoir sits at its reference. All 14 gated ranges pass, including
the new `urine_output` line (1.01 mL/min), and the Milestone 24 Guyton
gates hold exactly: MSFP 6.29 mmHg (band [5, 9]), MCFP 6.05 mmHg,
stressed volume 742.0 mL, RAP proxy 1.55 mmHg, RVR empirical 0.0675 vs
formula 0.0719 mmHg·s/mL (agreement 6.1% < 15%).

The new **long-horizon resting run** (standard protocol, then 60
engaged minutes; `run longrest`) is the brief's steady-state proof:

| Window | HR | MAP | CO | SV (LV) | CVP |
|---|---|---|---|---|---|
| First 30 s engaged | 62.4 | 73.2 | 4.24 | 67.9 | 4.41 |
| +30 min (30 s) | 63.8 | 73.0 | 4.20 | 65.9 | 4.35 |
| +60 min (30 s) | 64.1 | 73.0 | 4.19 | 65.4 | 4.32 |

- **Drift, +30 → +60 min: MAP 0.050%, CO 0.164%** — inside the
  project's 1% steady-state criterion, gated. (First → last reads MAP
  0.313% / CO 1.093% and is reported ungated: the first window sits
  inside the engagement transient by construction — the same reason
  the standard protocol's post window starts 90 s after engagement —
  so a first-vs-last comparison would gate the transient, not the
  steady state. Both comparisons are printed by the harness; the
  construction is disclosed here and in `main.rs`.)
- **Equilibrium urine output (final 30 min): 1.01 mL/min**, inside the
  cited band — gated against S24.
- **Boundary balance over the engaged hour: urine 60.4 mL vs intake
  60.0 mL (net +0.4 mL)** against a ±15 mL engineering balance
  criterion — the renal curve, the reflex, and the intake meet at the
  equilibrium point and stay there.
- The reservoir moves once, early: 11,000.0 → 11,022.8 mL (a net
  22.8 mL escape during the post-engagement pressure settling), then
  holds — its final-window drift is the same ~0% as everything else.
- Conservation error 1.7e-9 mL over 186,000 ticks; trace hash
  `0x668c9b6338f54d1f`; determinism IDENTICAL.

## 4. Calibration disclosure — the compliance sweep

One genuinely new calibration exists this milestone: `C_isf`. The
conductance `k` was **not** re-tuned (the feedback only brakes flows
the Milestone 18 calibration produced), and U0/intake are set by
their cited constructions, not fitted. The sweep, run against the
full gate set before the value was fixed:

| Quantity | C = 200 | **C = 300 (shipped)** | C = 400 |
|---|---|---|---|
| Refill observation, +30 min (gate [112.5, 262.5]) | 158.9 | 167.6 | 172.2 |
| Course refill +60 min, untreated (soft [500, 1000]) | 615.8 | 682.4 | 720.1 |
| Bolus retention +60 min (soft [0.20, 0.95]) | 0.54 | 0.49 | 0.46 |
| Untreated +60 min HR / MAP | 109.2 / 68.1 | 104.6 / 68.5 | 102.1 / 68.8 |
| Treated +60 min HR | 77.2 | 76.3 | 75.7 |
| Resting post window | identical at all three cells | | |

Every hard gate and every soft line holds at all three cells; the
surface is shallow and monotone. Shipped 300 = the middle of the
fit-implied range over the volume band the scenarios actually visit
(S26's slope implies ≈ 235–370 mL/mmHg for V/V0 in 0.94–1.00); the
choice inside the sweep is a disclosed convention, not an
identification, and it is recorded on the parameter itself.

## 5. Perturbation cases and the haemorrhage course, before / after

### 5.1 Standard cases

- **−750 mL:** post HR **102.1/min — the ATLS Class II hard band
  [100, 120] holds**; MAP 68.9; CO 3.46. Identical to Milestone 24 at
  print precision (102.1 / 68.9): over the standard protocol's 60-second
  bleed and 30-second post window the new boundary fluxes move ~1 mL.
  The standing systolic soft miss is unchanged (85.6 vs the 90 mmHg
  edge whose bound was never read in a consulted source).
- **+1,000 mL infusion:** post MAP 75.8 (M24: 76.0), CVP 8.02 (M24:
  7.90), CO 4.67, HR 42.8 — all directional gates pass. The slightly
  higher CVP is the interstitial pressure feedback braking in-window
  escape, the mechanism working in the direction it was built for;
  the window (30–60 s after the infusion ends) is far inside S28's
  25–30-minute distribution course, so the effect is correctly small.
- **−1,500 mL (standard window):** post MAP 29.7, HR 144.0 — the
  transient nadir, as Milestone 24 established; the course below is
  the presentation-timescale reading.

### 5.2 Refill observation (−750 mL, 30 min)

Net refill at +30 min: **167.6 mL (22.3% of the loss)**, inside the
gated band [112.5, 262.5] — Milestone 24 measured 187.6 mL (25.0%)
with the unbounded-by-pressure driver; the interstitial pressure
feedback (at +30 min the reservoir is down 167.6 mL, ΔP_isf ≈
−0.56 mmHg and growing as refill proceeds) brakes the trajectory
toward the cited ~25% point from below rather than past it. The full
trajectory (M25): +1 min 6.4, +5 38.3, +10 69.8, +20 123.8, +30 167.6
mL. Final window HR 90.2, MAP 70.1.

### 5.3 The −1,500 mL course, both arms

**Untreated** (M24 above, M25 below; urine/ISF/blood columns are new):

| Mark | HR | MAP | CO | SV | CVP | Stressed | MSFP | Recruited | Refill |
|---|---|---|---|---|---|---|---|---|---|
| +1 min | 144.0 | 29.6 | 1.10 | 7.6 | 0.91 | 267.1 | 2.26 | 517.8 | 150.2 |
| +2 | 144.0 | 47.7 | 1.65 | 11.5 | 1.45 | 374.5 | 3.17 | 588.7 | 214.2 |
| +5 | 144.0 | 59.7 | 2.32 | 16.1 | 2.12 | 483.3 | 4.10 | 627.9 | 315.3 |
| +10 | 143.4 | 64.5 | 2.84 | 19.8 | 2.69 | 562.6 | 4.77 | 630.0 | 418.6 |
| +20 | 115.0 | 67.5 | 3.25 | 28.2 | 2.92 | 592.6 | 5.02 | 571.2 | 538.0 |
| +30 | 108.2 | 68.2 | 3.35 | 31.0 | 3.00 | 609.3 | 5.16 | 496.6 | 635.9 |
| +60 | 93.8 | 69.7 | 3.60 | 38.4 | 3.24 | 635.8 | 5.39 | 336.8 | 858.9 |

| Mark | HR | MAP | CO | SV | CVP | Stressed | MSFP | Recruited | Refill | Urine cum. (rate/min) | ISF | Blood |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| +1 min | 144.0 | 29.7 | 1.10 | 7.6 | 0.91 | 267.4 | 2.27 | 517.8 | 149.2 | 2.7 (—) | 10,850.8 | 3,650.5 |
| +2 | 144.0 | 47.7 | 1.65 | 11.5 | 1.45 | 374.1 | 3.17 | 588.7 | 211.8 | 3.1 (0.41) | 10,788.2 | 3,713.6 |
| +5 | 144.0 | 59.4 | 2.29 | 15.9 | 2.10 | 479.5 | 4.06 | 627.9 | 307.5 | 5.2 (0.67) | 10,692.5 | 3,810.3 |
| +10 | 144.0 | 64.0 | 2.78 | 19.3 | 2.61 | 553.1 | 4.69 | 630.0 | 400.7 | 9.1 (0.79) | 10,599.3 | 3,904.6 |
| +20 | 117.9 | 67.2 | 3.20 | 27.1 | 2.89 | 597.8 | 5.07 | 600.8 | 493.9 | 17.8 (0.87) | 10,506.1 | 3,999.2 |
| +30 | 113.3 | 67.6 | 3.27 | 28.9 | 2.94 | 606.2 | 5.14 | 549.9 | 558.3 | 26.7 (0.89) | 10,441.7 | 4,064.6 |
| +60 | 104.6 | 68.5 | 3.41 | 32.6 | 3.05 | 609.0 | 5.16 | 454.1 | 682.4 | 53.8 (0.90) | 10,317.6 | 4,191.6 |

The untreated recovery survives the new outflows: `map_recovery_
untreated` (+30 MAP 67.6 > +2 MAP 47.7) PASS; the 60-minute refill
682.4 mL stays inside S15's 500–1,000 mL soft envelope (M24: 858.9 —
the braking moves it down the envelope, not out of it); the +30 min
heart rate 113.3 stays inside the Class II soft band. The recovery is
slightly slower and slightly less complete than Milestone 24's —
correctly so: the patient now also excretes (urine rate recovering
0.41 → 0.90 mL/min as pressure returns — pressure diuresis read in
reverse) and the reservoir resists its own depletion. The kidney's
behaviour across the arm is the curve's shape made visible: near-zero
output in the depths, rising monotonically with MAP, still below
baseline at +60 min because MAP (68.5) is still below the operating
point (72.9).

**Treated** (M24 above, M25 below):

| Mark | HR | MAP | CO | SV | CVP | Stressed | MSFP | Recruited | Refill |
|---|---|---|---|---|---|---|---|---|---|
| +1 min | 106.6 | 69.4 | 3.43 | 36.0 | 3.62 | 801.5 | 6.79 | 386.6 | 88.1 |
| +2 | 76.0 | 71.6 | 3.94 | 51.9 | 3.67 | 682.2 | 5.78 | 206.4 | 89.5 |
| +5 | 80.3 | 71.1 | 3.85 | 47.9 | 3.57 | 699.7 | 5.93 | 184.5 | 98.9 |
| +10 | 79.5 | 71.2 | 3.87 | 48.6 | 3.60 | 674.3 | 5.71 | 175.4 | 114.4 |
| +20 | 78.1 | 71.4 | 3.89 | 49.9 | 3.65 | 708.6 | 6.01 | 159.1 | 142.9 |
| +30 | 76.9 | 71.5 | 3.92 | 51.0 | 3.69 | 670.5 | 5.68 | 144.6 | 168.5 |
| +60 | 73.9 | 71.9 | 3.98 | 53.8 | 3.80 | 719.2 | 6.10 | 110.4 | 231.2 |

| Mark | HR | MAP | CO | SV | CVP | Stressed | MSFP | Recruited | Refill | Urine cum. (rate/min) | ISF | Blood |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| +1 min | 106.6 | 69.4 | 3.43 | 36.1 | 3.62 | 804.4 | 6.82 | 386.5 | 87.4 | 3.2 (—) | 10,912.6 | 4,588.1 |
| +2 | 76.0 | 71.6 | 3.94 | 51.9 | 3.67 | 681.6 | 5.78 | 206.6 | 88.0 | 4.2 (0.98) | 10,912.0 | 4,588.8 |
| +5 | 80.5 | 71.1 | 3.85 | 47.8 | 3.57 | 679.4 | 5.76 | 185.8 | 95.4 | 7.1 (0.96) | 10,904.6 | 4,596.3 |
| +10 | 79.9 | 71.2 | 3.86 | 48.3 | 3.59 | 701.4 | 5.94 | 178.9 | 107.0 | 11.9 (0.97) | 10,893.0 | 4,608.1 |
| +20 | 78.8 | 71.3 | 3.88 | 49.2 | 3.62 | 706.2 | 5.99 | 167.0 | 127.3 | 21.6 (0.97) | 10,872.7 | 4,628.7 |
| +30 | 78.0 | 71.4 | 3.90 | 50.0 | 3.65 | 660.1 | 5.59 | 157.1 | 144.0 | 31.3 (0.97) | 10,856.0 | 4,645.7 |
| +60 | 76.3 | 71.6 | 3.93 | 51.6 | 3.71 | 677.2 | 5.74 | 136.9 | 179.0 | 60.4 (0.97) | 10,821.0 | 4,681.5 |

All three comparative hard gates hold at +10 min (MAP 71.2 vs 64.0;
CO 3.86 vs 2.78; HR relieved 79.9 vs 144.0).

### 5.4 The retention question — what is now validated, what stays soft

**The metric.** `bolus_retention_60min` = (treated blood volume −
untreated blood volume) at +60 min, as a fraction of the 1,000 mL
bolus — the plasma-expansion construction of volume kinetics (the
S27's expansion), which automatically nets out the arms' shared
haemorrhage, recruitment, and intake.

**Measured: 0.49** (blood 4,681.5 vs 4,191.6 mL). Milestone 24's value
on the same construction, derived from its published refill figures
through the volume identity: **0.37**. Its trajectory: 0.94 at +1 min
(the litre is intravascular while it is being given and just after),
settling to 0.49 by +60 min as redistribution and excretion act.

**Decomposition at +60 min (M25).** The 490 mL advantage is: +1,000 mL
bolus, −503 mL of **refill suppression** (the untreated arm pulled
682 mL from its interstitium; the treated arm, its capillary pressure
largely restored, needed only 179 mL — volume the bolus made
unnecessary, not volume the bolus lost), −7 mL urine differential
(treated 60.4 vs untreated 53.8 mL cumulative). Two honest
consequences follow:

1. Redistribution in this scenario acts mainly **through refill
   suppression and the interstitial pressure feedback**, not through
   net escape of the bolus itself: the treated patient remains
   ~320 mL below its initial blood volume at +60 min, so its Starling
   balance stays refill-ward and its net refill stays positive at
   every mark (as in Milestone 24). What Milestone 24 lacked — any
   mechanism by which the intravascular advantage of a bolus could
   decay — now exists and measurably acts: the advantage falls
   0.94 → 0.49 over the hour instead of persisting at the litre.
2. The comparison to S27's ~20% is a **cross-condition comparison**
   (awake normovolaemic volunteers vs a bled model patient whose
   vasculature has room and whose elimination/distribution slow with
   blood loss, S28): the model retaining more (0.49) is the direction
   the sources predict. That is why the line is **soft** — it is a
   magnitude reading against a cited figure under stated conditions,
   not a gate. It passes its soft band [0.20, 0.95].

**What remains soft, and why:**

- `hr_treated_10min` ∈ Class III [120, 140]: **still SOFT-FAIL**
  (79.9; M24: 79.5). The mechanism Milestone 24 named for it (the
  bolus cannot redistribute) is retired, and the line still fails —
  with redistribution and excretion both acting, the +10-minute
  treated picture barely moves, because by the Guyton quantities the
  bolus has already made the deficit good (stressed volume 701 mL vs
  resting 742; MSFP 5.94 vs resting 6.29): the model's reflex stands
  down because, volumetrically, there is little left to compensate.
  Whether a real Class III patient one litre in should still read
  120–140 turns on things this engine does not model (ongoing
  losses, pain/sympathetic drive independent of volume, blood
  products not given) and on the reflex gains, which remain
  verify-flagged placeholders. The line stays soft, the miss stays
  carried, and **no parameter was tuned toward it** — the sweep in §4
  shows it is not a compliance artefact either (treated +60 HR spans
  only 75.7–77.2 across the band).
- `net_refill_ml_at_60min_untreated` and `hr_untreated_30min`: soft,
  both PASS (682.4 in [500, 1000]; 113.3 in [100, 120]).
- **Infusion magnitudes in general** remain validated only in the
  retention sense above: still no consulted source states a numeric
  MAP/CO response to a 1 L bolus in gate-able form (standing since
  Milestone 8), so MAP/CO advantages stay comparative hard gates and
  the absolute treated MAP/CO are reported, not gated.

### 5.5 Trace hashes (Milestone 25 format)

Resting `0x036326df5f2d6e8b` · −750 `0x48e092929789a4b8` · infusion
`0x8a1f2d890d3461fa` · −1,500 `0xc2ba1dd648ed24e0` · refill
observation `0xd7804a47ac6a578d` · course untreated
`0x2f98edc338bf6da6` · course treated `0xce4262cccd9829a0` · long rest
`0x668c9b6338f54d1f`. `validate`: **ALL HARD GATES PASS** (three soft
lines, all pre-disclosed: the −750 systolic edge, the −1,500 HR band,
`hr_treated_10min`). `cargo test` **17/17** (14 prior + 3 new:
`renal_and_intake_balance_at_rest_over_an_hour`,
`interstitial_reservoir_identity_and_pressure_feedback`,
`urine_output_follows_the_renal_curve_directionally`).

## 6. Caveat ledger

**Retired by this milestone:**

- *"Renal excretion unmodelled — now the binding volume-side
  omission"* (M24 §7) — retired. The lumped renal function curve and
  intake are in, gated at rest and exercised in every scenario; urine
  output is now an engine output the case workbench can cite.
- *"A minimal interstitial state is the named companion work"* (M24
  §7) — retired. The reservoir is finite, cited, and pressurised; the
  treated bolus redistributes and its retention is measured against
  the volume-kinetics literature (§5.4).
- *The treated arm's second structural reason for no transient
  response* (M24) — half-retired: excretion now exists, so a volume
  load is genuinely transient-capable over hours. The first reason
  stands untouched: the ATLS transient class is defined against
  ongoing loss or inadequate replacement, and this scenario's
  bleeding is controlled at t = 180 s by construction.

**Standing / newly named, precisely:**

- **Lymphatic return is not a separate dynamic.** The Starling
  pathway in this engine is a *net* exchange (Milestone 18's standing
  disclosure), so at the operating point lymphatic return is subsumed
  in the balance — but lymph flow as a pressure-driven return that
  rises steeply with interstitial pressure (the edema relief valve of
  the source tradition) is absent. Consequence: sustained positive-
  balance states (multi-litre loading, edema formation) would
  overfill the reservoir against the linear compliance with no
  lymphatic escape; shipped scenarios stay within a few hundred mL
  of the operating point, where the net formulation is the cited
  behaviour. Named, not hidden.
- **Hormonal axes absent (ADH, aldosterone, RAAS, ANP).** The renal
  curve's shape is fixed. S23 is explicit that the chronic curve is
  far steeper than the acute curve partly *because* of these axes
  (and that they shift the curve under salt loading, heart failure,
  and cirrhosis). The model therefore cannot represent: chronic
  pressure adaptation over days, salt-intake changes shifting the
  setpoint, or any endocrine renal state. Its horizon of honest
  claim is the acute-to-hours course it is validated on.
- **Oncotic / protein handling still absent.** Refill and escape
  fluid is volume-identical to plasma; there is no plasma protein
  state, so dilution does not feed back on the Starling balance (the
  driver is hydrostatic-only and self-referenced, as since M18), and
  **blood products remain impossible as a scenario input** — the
  oncotic distinction they require still does not exist. This is now
  the binding volume-side omission for the Theatre's Class III/IV
  route (S20).
- **Single linear interstitial compliance** vs the source's strongly
  nonlinear curve (steep below the operating point, near-ballooning
  above zero pressure — S26). The shipped slope is the operating-
  region slope; deep depletion is over-braked less than the real
  curve would brake it and edema-range filling is over-braked more.
  Disclosed on the parameter; the nonlinear curve is the named
  upgrade if an edema or multi-litre scenario is ever authored.
- **Intake is a constant, not a regulated variable** (no thirst, no
  intake response to losses; nonrenal losses ignored, following the
  source figure's own construction, S23). Over multi-hour *unfed*
  scenarios the model's patient drinks at baseline rate throughout —
  stated here so no multi-hour reading mistakes it for physiology.
- **The renal curve senses MAP only.** No GFR autoregulation plateau,
  no tubular/glomerular dynamics, no electrolyte or acid–base state:
  urine *volume* is the only renal output, which is exactly the
  Guyton long-term-control abstraction and no more.
- Venoconstriction's **compliance effect** (S19) remains real in the
  source and unquantified there; capacity effect only, as before.
- All reflex gains remain **verify-flagged placeholders**; the −750
  mL systolic soft miss (85.6 vs the never-sourced 90 edge) stands.
- The **review gate remains unmet**: no expert reviewers exist;
  content stays `dual-sourced-draft`, scores formative-only.

## 7. Cross-module impact and checker matrix

Physiology dynamics changed, so both downstream consumers moved —
each by re-derivation, with field-level diffs, none by hand-waving:

- **Theatre — one required code fix.** The runner's blood-loss
  identity (`volume_at_start + infused + refill_during − volume_end`)
  predates the renal/intake boundary; with urine running, a quiet
  attempt would have reported its net boundary flux (~−30 mL over a
  long attempt: intake ~40 min × 1.0 mL/min minus urine) as blood
  loss. The identity now carries `+ intake_during − urine_during`
  (runner.rs, with the Milestone 18/25 accounting comments), and the
  attempt records the engine's cumulative urine/intake at start
  exactly as it already did for refill. `cargo test` **8/8** — the
  exact-loss assertions (750.0 / 1,500.0 / 360.0 mL by both the
  integral and engine routes) hold under the corrected identity.
  `run-all` regenerated all 5 debriefs; field-by-field diff against
  the Milestone 24 set: **every clinical and scoring field is
  identical** (verdicts, errors, blood losses — trace-01's measured
  loss stays exactly 0.0 — checklist/safety/management scores,
  timings, complications). Only three engine-bookkeeping fields move
  per debrief: `engine_trace_hash` (trace-format change),
  `engine_beats` (−2 to −12 over ~2,700–5,800 beats; the beat count
  rides the resting heart trajectory, which the boundary fluxes
  perturb in the third decimal), and `engine_conservation_error_ml`
  (~1e-8 mL, still zero at any meaningful precision).
  `tools/theatre_check.py`: **131 checks, 0 failures**.
- **Cases — two re-recordings, both hash-only in substance.**
  (a) Case 1's `physiology_link`: the resting trace hash changed
  with the trace format (`0xacbf44852f6a0382` →
  `0x036326df5f2d6e8b`); **no recorded output moved** at the recorded
  precision (HR 63.3, BP 97.7/62.7, MAP 73.1, CO 4.21, SV 66.6, CVP
  4.38), and the link's verification text carries the appended
  MILESTONE 25 RE-RECORDING, as M21's did. (b) Case 2's
  `theatre_link`: the trace-02 debrief file changed (above), so its
  SHA-256 was re-recorded (`7bb98df4…` → `02ab4d2d…`) in the link
  and in the stage-1 finding that quotes it, with a re-recording
  note on the link; every `matched_fields` value was verified
  unchanged against the new debrief before re-recording.
  `tools/case_check.py`: **ALL CHECKS PASS — 3,280 passed, 0
  failed**, the loop verification included.
- **Assembly:** `tools/assembly_check_all.py` **ALL GATED CHECKS
  PASS**. **Web:** `node tools/verify_web.js` **ALL CHECKS PASS**
  (the web shell does not consume the physiology engine; untouched).
- **Physiology:** `validate` **ALL HARD GATES PASS**; `cargo test`
  **17/17**; `determinism` IDENTICAL; the guyton probe example still
  compiles against the shipped API.

Files changed: `physiology/src/engine.rs` (reservoir + renal curve,
accounting, hash fold, query/accessors), `physiology/src/cases.rs`
(urine on windows and course samples, retention quantity, long-rest
runner), `physiology/src/main.rs` (long-horizon section, course
columns, `run longrest`), `physiology/parameters.json` (S23–S28, 7
parameters, urine range, retention expectation, appended amendments),
`physiology/tests/engine_tests.rs` (+3 tests), `theatre/src/runner.rs`
(loss identity), `theatre/debriefs/*.json` (regenerated),
`cases/case.ruq-pain.001.json` and `cases/case.post-op-jaundice.002.json`
(re-recordings), this dossier. Local only; no upload performed or
implied.

## 8. Next steps

1. **Oncotic state + blood products as a scenario input** — now the
   binding volume-side omission: a plasma-protein/oncotic term in
   the Starling driver would let the Theatre run S20's Class III/IV
   route (blood, not just crystalloid) and would make refill
   self-limiting by dilution as well as by pressure. Sources first
   (oncotic pressures and their dilution dynamics), as always.
2. **Urine output as a case finding** — the workbench can now cite a
   computed renal trajectory (the course's 0.41 → 0.90 mL/min
   recovery is a presentable finding class); a case authored against
   it needs its criteria sourced like case 2's were.
3. **The nonlinear interstitial curve** (S26's fit used whole) if an
   edema or multi-litre scenario is ever authored — the linear
   compliance is the operating-region approximation and says so.
4. Standing dataset blockers are unchanged by this milestone
   (nerves, lymphatics, thyroid/parathyroids, kidney/urinary
   interior, female reproductive tract, skin layers — the full
   FMA/TA pass remains the named route; the kidney's absence from
   the Body Model is now doubly visible, since the physiology
   kidney is a curve with no anatomy behind it).
