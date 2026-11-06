# Milestone 26 — Physiology: oncotic state + blood products as scenario inputs

Milestone 25's caveat ledger named the binding volume-side omission:
oncotic/protein handling was absent, so blood products could not be a
scenario input at all — the engine could carry volume but not
composition. This milestone closes it. The engine gains a lumped
oncotic state (plasma and interstitial protein masses, red-cell
volume), the Starling driver gains its oncotic term in textbook form,
and blood products — whole blood, packed red cells, plasma — enter
through a second, composition-carrying event channel and as arms of
the −1,500 mL haemorrhage course.

Headline results, all measured this session:

- Resting state undisturbed: every Milestone 25 hard gate re-passes,
  and the new resting oncotic lines land on their cited values —
  hematocrit 0.45, plasma oncotic pressure 26.98 mmHg (S29's table:
  28.0; the Nitta relation at the cited concentration, §1.1),
  interstitial oncotic pressure 7.87 mmHg (S29: 8). Equilibrium urine
  output unmoved at 1.01 mL/min against its cited band.
- The oncotic term changes the course materially, in the direction
  the physiology says it should: untreated refill is now
  self-limiting (436.6 mL at +60 min; Milestone 25 read 682.4 mL
  without the term), and the crystalloid litre's advantage is
  transient — +7.5 mmHg of MAP at +10 min, nearly gone by +60 min
  (retention 0.08 on the difference metric, a disclosed soft miss
  analysed in §5.4) — while both product arms hold MAP ≈ 71 mmHg
  and heart rate ≈ 78/min flat for the full hour, their blood
  volumes essentially constant from +2 min on.
- No parameter was tuned toward any of these readings. The one
  calibration the new term touches (the refill conductance, through
  which the oncotic term acts) was swept across its cited band and
  σ across its cited span (§4): the shipped values stand, because
  the soft misses are robust to every in-band choice and the
  conductance floor fails a hard gate outright.

## 1. Formulation

### 1.1 The oncotic state

Three lumped states join the RK4 integration and the trace hash
(folded after the Milestone 25 urine/intake states, in the order
rbc, plasma protein, interstitial protein):

- **Red-cell volume** `V_rbc` (mL), initialised at the resting
  hematocrit × total blood volume = 0.45 × 5,000 = 2,250 mL.
- **Plasma protein mass** `M_p` (g), initialised at the cited
  resting concentration (S29: 7.3 g/dL = 0.073 g/mL) over the
  derived resting plasma volume (5,000 × (1 − 0.45) = 2,750 mL)
  = 200.75 g.
- **Interstitial protein mass** `M_i` (g), initialised at S29's
  interstitial concentration (≈3 g/dL = 0.030 g/mL) over the
  Milestone 25 reservoir volume (11,000 mL) = 330 g.

Concentrations are derived, never integrated directly: plasma
volume is `V_plasma = V_blood − V_rbc` (the identity hematocrit
feeds), interstitial volume is the Milestone 25 reservoir identity,
and `cp = M_p / V_plasma`, `ci = M_i / V_isf`. Oncotic pressures
follow from the concentrations through Nitta et al.'s corrected
Landis–Pappenheimer relation (S33, read in full this session),
concentrations in g/dL:

```
pi(c) = f * (2.8c + 0.18c^2 + 0.012c^3) + (1 - f) * (0.9c + 0.12c^2 + 0.004c^3)
```

with the albumin fraction `f` held at S29's own table ratio
(4.5/7.3 = 0.6164) in both pools — the lumped states track total
protein only, so the relation is applied at fixed composition
(disclosed; S33's exchange itself records 10–15% inter-equation
spread, partly from this ratio). Evaluated at the cited resting
points the relation gives 26.98 mmHg at 7.3 g/dL against S29's
28.0 (−3.6%) and 7.87 mmHg at 3.0 g/dL against S29's 8 (−1.6%):
the relation is used exactly as cited and the small anchor offsets
are carried openly — the resting validation bands (§3) span both
the table values and the relation's values.

**Hematocrit is tracked-but-inert, stated plainly.** It is the
ratio `V_rbc / V_blood`, reported by the query interface and used
by the plasma-volume identity and the product/dilution
bookkeeping. It drives no resistance and no elastance: no
viscosity coupling is modelled, because no sourced lumped
viscosity law was consulted and inventing one is refused. There is
no F-cell (whole-body vs large-vessel hematocrit) correction — the
lumped circulation has one hematocrit.

### 1.2 The Starling driver, completed

Before this milestone the refill driver was pressure-deficit only
(Milestones 18/25):

```
Q = k * [ (Pcap_ref - Pcap_lp) - refill / C_isf ]
```

It gains the oncotic term in its textbook Starling form, as the
deviation of the transcapillary oncotic difference from its own
resting value, both references captured at reflex engagement
exactly as `cap_ref` is:

```
Q = k * [ (Pcap_ref - Pcap_lp) - refill / C_isf
          + sigma * ((pi_c - pi_i) - (pi_c_ref - pi_i_ref)) ]
```

with σ = 0.9 cited (S30: total protein in muscle microvessels;
tissue span ≈ 0.7–0.99 quoted there — a lumped, muscle-dominated
value; the low-σ fenestrated beds are not distinguished, §6).

Protein crosses with the flow under a disclosed upstream
convention: on the inflow limb (refill, ISF → plasma) the incoming
fluid carries the interstitial concentration unsieved; on the
outflow limb (escape, plasma → ISF) it carries the sieved plasma
concentration `(1 − σ) · cp`. Haemorrhage removes whole blood at
the current composition (red cells at the current hematocrit,
protein at `cp` over the plasma fraction); the event channel's
inflow limb is crystalloid and carries neither; urine removes
protein-free water (protein mass untouched, concentration rises —
the renal curve's protein handling is not a urine-protein model,
§2).

The slow protein circulation rides on top: a transcapillary leak
out of plasma at the resting lymph-return flux scaled by the
plasma concentration ratio, `L0 · (cp/cp0)`, and lymphatic return
into plasma at `L0 · (ci/ci0)`, with L0 = 70 g/day calibrated
inside S32's cited band (protein returned via lymph in one day =
25–50% of the circulating pool = 50–100 g/day for this model's
200.75 g pool; the ~3 L/day lymph flow at interstitial
concentration cross-checks at 60–90 g/day). Albumin synthesis
(S31: 10.5 g/day) enters the plasma pool against a first-order
catabolic sink whose fraction is derived so the pair cancels
exactly at the operating point (κ = synthesis / resting pool =
6.05e-7 /s) — quiet-at-rest by construction, the same equilibrium
device as Milestone 25's intake = U0. Lymphatic VOLUME return
remains subsumed in the net Starling pathway (Milestone 25 ledger
stands); what is new is the protein flux riding on it.

**Does oncotic pressure recover on the course horizon? The sources
say no — and the model now shows why.** Synthesis restores ≈0.44 g
of protein per hour; the 1,500 mL bleed removes ≈60 g of plasma
protein (1,500 × (1 − 0.45) × 0.073). Full restoration is a
multi-day project at the cited synthesis rate. Within the hour,
plasma oncotic pressure recovers only by redistribution and
concentration (escape of protein-poor fluid raises `cp` — visible
in the crystalloid arm, §5.3), never by new mass. The diluted state
therefore persists across the course, which is precisely why the
product arms' protein return matters in §5.3.

### 1.3 Blood products as scenario inputs

A second event channel, `Event::SetProductFlow { rate, hematocrit,
protein_g_per_ml, label }`, carries composition into the systemic
venous compartment alongside the crystalloid/event channel. Its
boundary integral joins the volume identity (subtracted like the
event channel's), and the Theatre's loss identity is extended to
it in the Milestone 25 pattern (§7). Three products, all values
from parameters.json under the usual discipline:

| product | unit volume | hematocrit | protein | sources |
|---|---|---|---|
| whole blood | 513 mL (450 donor + 63 anticoagulant) | 0.40 [0.35–0.45] | 0.0438 g/mL (derived) | S35, S29 |
| packed red cells | 300 mL [250–350] | 0.60 [0.50–0.70] | 0.0292 g/mL (derived, residual plasma) | S34, S35, S29 |
| plasma (FFP class) | 225 mL [200–250] | 0.0 (acellular) | 0.073 g/mL (plasma) | S34, S35, S29 |

Course arms (§5.3): whole blood = 2 units over 60 s from the bleed
end (1,026 mL — volume-matched to the crystalloid litre within the
units' quantisation, disclosed); components = 2 units PRBC then 2
units plasma sequentially at the bolus's nominal rate (600 mL over
36 s, then 450 mL over 27 s). Red cells first, plasma after is the
scenario's stated order; the 1:1 unit pairing is a stated
simplification. There are no platelets and no cryoprecipitate:
the engine has no coagulation state and claims none — plasma here
is volume + protein, its factor activity unmodelled (§6).

Cross-read against S34's rule (one PRBC unit raises hematocrit
≈3 points in a non-bleeding 70 kg adult at volume equilibrium):
one in-model unit carries 300 × 0.60 = 180 mL of red cells, which
at constant 5,000 mL volume is +3.6 points — inside the span the
rule itself rounds (its unit definitions span 250–350 mL at
hematocrit 0.50–0.70, i.e. +2.5 to +4.9 points). Reported as a
cross-read, not gated; the engine test asserts the bookkeeping
identity itself.

## 2. Parameters and sources

Seven sources were consulted in-session and added (S29–S35):
Guyton & Hall ch. 16 via a lecture-slide reproduction (status
recorded in the file, as for S19/S23/S28) for the protein table
and oncotic anchors; Deranged Physiology's Starling chapter for
σ; Levitt & Levitt 2016 (PMC4956071) for albumin synthesis;
Ganong's 23rd ed. ch. 32 via reproduction for the lymph protein
return band; the J Appl Physiol 2003 letters (full text) for the
Nitta relation; Bloodworks Northwest's institutional transfusion
table for unit volumes and the per-unit rule; and
component-preparation teaching sources (Harmening 6e as
reproduced; Wikipedia's packed-red-blood-cells article) for unit
specifications. Nineteen parameters were appended (61 → 80), all
append-only insertions in the file's own formatting: 8 cited
(resting concentrations, σ, both Nitta coefficient triples, the
albumin fraction, synthesis, whole-blood unit volume, plasma
hematocrit and protein), 11 calibrated inside cited ranges
(resting hematocrit, lymph return flux, catabolic fraction, and
the products' volumes/hematocrits/derived protein concentrations
— each derivation stated in its note, including the two disclosed
overstatements: whole-blood protein neglects the anticoagulant's
≈12% dilution, and PRBC protein is a residual-plasma estimate
that additive-solution units undercut). Three resting validation
ranges were appended (hematocrit, both oncotic pressures) and six
course expectations (one hard — the whole-blood MAP advantage;
five soft, each labelled with its reason in its source text).

## 3. Resting validation — and the long horizon

`validate` reports **ALL HARD GATES PASS**. The resting window is
numerically undisturbed at the recorded precision of every prior
milestone (HR 63.3, BP 97.7/62.7, MAP 73.1, CO 4.21, SV 66.6,
CVP 4.38 — the protein fluxes cancel at the operating point by
construction), and the Milestone 25 lines re-pass exactly:
equilibrium urine 1.01 mL/min in [0.7, 1.4] (S24), MSFP 6.29 mmHg,
RVR two-way agreement 6.1%. New resting lines:

| output | value | band | source | verdict |
|---|---|---|---|---|
| hematocrit | 0.45 | [0.40, 0.50] | S35 | PASS |
| plasma oncotic pressure | 26.98 mmHg | [21, 30] | S29 (28.0) | PASS |
| interstitial oncotic pressure | 7.87 mmHg | [5, 11] | S29 (8) | PASS |

Long-horizon rest (60 engaged minutes): post-transient drift
MAP 0.008% / CO 0.028% (criterion < 1%), equilibrium urine
1.01 mL/min, boundary balance urine 60.4 vs intake 60.0 mL
(net +0.4 mL). One reported detail: the interstitial reservoir
gains 10.4 mL over the hour (net refill −10.43 mL) — during the
engagement transient the reflex redistributes a little plasma
volume, `cp` dips fractionally, and the oncotic term washes a
small protein-poor volume out before the state re-settles; it is
0.09% of the reservoir and does not recur (the drift gates are
computed on the post-transient windows and pass).

## 4. Calibration disclosure — the conductance and σ sweeps

The oncotic term acts through the existing refill conductance `k`
(Milestone 18's calibration, shipped value 0.04 mL/s/mmHg inside
its cited band [0.008, 0.08]); no separate oncotic conductance was
sourced, and inventing one was refused — so the term's gain is the
conductance's, and that structural choice is swept here instead.
Sweeps ran in a scratch copy; the shipped tree was not touched.
σ swept across S30's tissue span at the shipped `k`.

| configuration | refill obs @+30 min (gated band [112.5, 262.5]) | untreated refill @+60 min | untreated MAP/HR @+30 | crystalloid retention @+60 |
|---|---|---|---|---|
| **k = 0.04, σ = 0.90 (SHIPPED)** | **126.6 PASS** | **436.6 mL** | **66.0 / 129.6** | **0.080** |
| k = 0.008 (band floor) | 40.0 — FAILS the gate | 350.8 mL | 58.3 / 144.0 | 0.430 |
| k = 0.08 (band ceiling) | 162.8 PASS | 439.0 mL | 66.3 / 126.5 | 0.050 |
| σ = 0.70 (span low) | 134.4 PASS | 463.7 mL | 66.7 / 122.4 | 0.110 |
| σ = 0.99 (span high) | 123.3 PASS | 428.6 mL | 65.6 / 132.8 | 0.070 |

Readings:

- **The shipped point stands; nothing was re-tuned.** It is the
  only swept configuration that is mid-band on both parameters,
  and the conductance floor fails the hard refill-observation gate
  outright — the floor is not an available calibration, whatever
  it does to the soft retention line.
- **The untreated refill total is brake-limited, not
  conductance-limited.** Across σ's whole span and at the
  conductance ceiling it moves only 429–464 mL: once the
  conductance is adequate, the oncotic self-brake (§5.2) is what
  terminates refill. No in-band calibration reaches the S15
  envelope's 500 mL floor (§5.4) without breaking a hard gate.
- **Crystalloid retention is the most conductance-sensitive
  output in the model** (0.43 → 0.05 across k's band, because the
  same conductance carries the escape). The shipped reading of
  0.08 is reported with this span attached wherever it is quoted;
  across the σ span at the shipped conductance it reads 0.07–0.11.

## 5. Perturbation cases and the haemorrhage course, before / after

### 5.1 Standard cases

All hard lines pass; the two pre-disclosed soft lines (the −750 mL
systolic band, the −1,500 mL Class III heart-rate band) stand as
before. The −750 mL hard gate holds exactly: post heart rate
102.2/min inside the ATLS Class II band [100, 120] (Milestone 25:
102.1). The −1,500 mL standard window (30–60 s after the bleed
ends) is the nadir, and the oncotic term — a minutes-timescale
mechanism — leaves it as it was: MAP 29.5 mmHg, HR 144.0/min,
SV 7.6 mL (Milestone 24/25: 29.6 / 144.0 / 7.6). The +1,000 mL
infusion case passes all directional expectations (MAP 75.8,
CVP 7.88, CO 4.66 post).

### 5.2 Refill observation (−750 mL, 30 min)

Net refill: +1 min 6.4, +5 36.2, +10 62.7, +20 101.3,
**+30 min 126.6 mL (16.9% of the loss)** — inside the gated band
[112.5, 262.5] (Milestone 25: 167.6 mL, 22.3%). The reduction is
the oncotic brake in its mildest form: even 750 mL of refill at
the interstitial concentration dilutes plasma protein enough to
sag πc and slow its own source flow. Recruited volume at +30 min
322.6 mL. No re-tune of `k` was needed or made (§4).

### 5.3 The −1,500 mL course, four arms

Sampled as before (marks after the bleed ends). MAP / HR / CO /
blood volume / net refill / πc / hematocrit:

**Untreated**

| min | MAP | HR | CO | blood vol | refill | πc | Hct |
|---|---|---|---|---|---|---|---|
| +1 | 29.5 | 144.0 | 1.09 | 3,648 | +146.8 | 25.2 | 0.432 |
| +5 | 58.5 | 144.0 | 2.21 | 3,791 | +288.3 | 23.8 | 0.416 |
| +10 | 62.3 | 144.0 | 2.59 | 3,864 | +359.7 | 23.2 | 0.408 |
| +30 | 66.0 | 129.6 | 3.03 | 3,941 | +433.5 | 22.6 | 0.400 |
| +60 | 66.3 | 126.2 | 3.08 | 3,948 | +436.6 | 22.5 | 0.399 |

**Crystalloid (+1,000 mL from bleed end)**

| min | MAP | HR | CO | blood vol | refill | πc | Hct |
|---|---|---|---|---|---|---|---|
| +1 | 69.3 | 107.2 | 3.42 | 4,572 | +70.8 | 14.4 | 0.345 |
| +5 | 70.4 | 87.2 | 3.72 | 4,480 | −20.7 | 15.0 | 0.352 |
| +10 | 69.8 | 92.7 | 3.62 | 4,386 | −115.6 | 15.7 | 0.359 |
| +30 | 68.2 | 107.9 | 3.36 | 4,149 | −354.4 | 17.6 | 0.380 |
| +60 | 67.3 | 116.5 | 3.22 | 4,024 | −481.8 | 18.8 | 0.392 |

**Whole blood (2 units, 1,026 mL, from bleed end)**

| min | MAP | HR | CO | blood vol | refill | πc | Hct |
|---|---|---|---|---|---|---|---|
| +1 | 69.7 | 104.6 | 3.47 | 4,612 | +84.8 | 26.2 | 0.431 |
| +5 | 71.2 | 79.7 | 3.86 | 4,612 | +85.5 | 26.2 | 0.431 |
| +10 | 71.2 | 79.5 | 3.87 | 4,616 | +88.6 | 26.2 | 0.430 |
| +30 | 71.3 | 79.1 | 3.88 | 4,624 | +96.2 | 26.1 | 0.430 |
| +60 | 71.3 | 78.8 | 3.88 | 4,629 | +100.5 | 26.0 | 0.429 |

**Components (2 units PRBC, then 2 units plasma; 1,050 mL)**

| min | MAP | HR | CO | blood vol | refill | πc | Hct |
|---|---|---|---|---|---|---|---|
| +1 | 69.4 | 106.8 | 3.43 | 4,586 | +85.5 | 26.2 | 0.422 |
| +5 | 71.3 | 78.5 | 3.89 | 4,636 | +85.3 | 26.2 | 0.418 |
| +10 | 71.4 | 78.4 | 3.89 | 4,638 | +87.4 | 26.2 | 0.417 |
| +30 | 71.4 | 78.1 | 3.90 | 4,644 | +92.7 | 26.1 | 0.417 |
| +60 | 71.4 | 77.9 | 3.90 | 4,648 | +95.9 | 26.1 | 0.417 |

The four-arm picture is the milestone's central result:

- **Untreated recovery is now self-limiting.** Refill brings back
  protein-poor fluid; πc slides 25.2 → 22.5 mmHg across the hour
  and the flow that carries it brakes itself, plateauing at
  436.6 mL. MAP recovers to 66.3 (Milestone 25: 68.5) and heart
  rate only to 126.2 (Milestone 25: 104.6) — the untreated patient
  is better than the nadir and visibly not well, which is the
  textbook course the earlier driver overstated.
- **The crystalloid litre buys minutes, not the hour.** It restores
  MAP to ~70 within a minute, but it dilutes πc to 14.4 mmHg doing
  so, and the oncotic term then drives net escape for the rest of
  the hour (−481.8 mL of net Starling flow by +60 min; the
  interstitium ends at 11,481.8 mL). MAP sags to 67.3 and heart
  rate climbs back to 116.5. The bolus still wins its comparative
  hard gates at +10 min (MAP +7.5, CO +1.03, HR −51.3 vs untreated)
  — the advantage is real and transient, which is what the ATLS
  sequence (bolus, reassess, blood) encodes.
- **Blood products hold the hour.** Both product arms sit at
  MAP ≈ 71.3, HR ≈ 78–79, CO ≈ 3.9 from +5 min to +60 min with
  blood volume flat (whole blood 4,612 → 4,629 mL; components
  4,636 → 4,648 mL) and πc restored to ≈26 mmHg and held. The
  whole-blood arm passes its hard comparative gate (MAP advantage
  at +10 min, 62.3 → 71.2). Whole blood and components are
  indistinguishable on this horizon at these doses — expected:
  their compositions differ mainly in where the red cells and
  protein sit per unit, and the totals given are near-identical.

### 5.4 The retention question — soft-line ledger

Retention is measured on Milestone 25's difference construction
(arm blood-volume advantage over the untreated arm at +60 min,
divided by the input volume), for comparability. Four soft lines
miss this session; all four are carried openly, with their bands
unmoved (the measurement notes are appended to the expectations'
source texts in parameters.json):

| line | reading | band | status |
|---|---|---|---|
| bolus_retention_60min (crystalloid) | 0.08 | [0.20, 0.95] (S27) | SOFT-FAIL |
| net_refill_ml_at_60min_untreated | 436.6 mL | [500, 1,000] (S15) | SOFT-FAIL |
| hr_untreated_30min | 129.6/min | [100, 120] (S16 reading) | SOFT-FAIL |
| wb_retention_60min | 0.66 | [0.70, 1.05] (engineering expectation) | SOFT-FAIL |
| comp_retention_60min | 0.67 | [0.65, 1.05] | SOFT-PASS |
| wb_hematocrit_60min | 0.429 | [0.30, 0.50] | SOFT-PASS |
| wb_plasma_oncotic_60min | 26.0 mmHg | [18, 30] | SOFT-PASS |
| treated_plasma_oncotic_60min | 18.8 mmHg | [10, 24] | SOFT-PASS |
| hr_treated_10min | 92.7/min | [120, 140] (S16 reading) | SOFT-FAIL (pre-existing) |

Two of the misses are about the metric, and are reported as such.
The difference construction nets the untreated arm's own 436.6 mL
of refill recovery: a product that persisted perfectly would still
read ≈ (1,026 − 437 + excretion differences)/1,026 ≈ 0.6–0.7 on
it. The whole-blood arm's own trajectory — blood volume 4,610 mL
at +2 min, 4,629 mL at +60 min — is the direct evidence that the
product itself persists essentially completely; the 0.66 reading
and its 0.04 band miss are the construction's arithmetic, stated
in the expectation's own note. The crystalloid 0.08 is different
in kind: there the treated arm's own Starling integral is −481.8
mL — the litre genuinely redistributed — though the reading also
carries the metric's refill-netting and is the model's most
conductance-sensitive output (§4: 0.07–0.11 across σ at the
shipped conductance; 0.43 only at the conductance floor that
fails a hard gate). Hahn's ~0.20 (S27) is a plasma-expansion
fraction in volunteers; the comparison is reported, the
conditions differ, and the line stays soft for exactly those
reasons. The S15 refill-envelope miss is the oncotic brake's
signature (§4 shows it is calibration-robust), and the untreated
heart-rate miss is its downstream consequence.

### 5.5 Trace hashes (Milestone 26 format)

The hash fold gains the three oncotic states after intake, so all
hashes differ from Milestone 25's even where trajectories agree.

| run | hash |
|---|---|
| resting | 0xcee16b0ddee95d76 |
| haemorrhage −750 mL | 0x858804211323c0e5 |
| infusion +1,000 mL | 0x35adc8f64e7730f6 |
| haemorrhage −1,500 mL | 0x9eee7b7ba2e4e0e5 |
| refill observation | 0xf3c76cecf87711cd |
| course, untreated | 0x781abb2f6026b557 |
| course, crystalloid | 0x34fa157913eb7515 |
| course, whole blood | 0x8972cf3dfdccd7bb |
| course, components | 0xb283a735bb3e11b7 |
| long rest (60 min) | 0x510d2f0e32d16499 |

Determinism re-proven (`determinism`: IDENTICAL), debug and
release builds bit-identical.

## 6. Caveat ledger

**Closed by this milestone**

- *Oncotic/protein handling absent → blood products impossible as
  a scenario input* (Milestone 25's binding volume-side omission).
  Closed as formulated in §1: oncotic state, completed Starling
  driver, product channel, product course arms. Its residual
  sub-items are the new entries below.

**Still standing (carried from Milestone 25, accurately)**

- *Lymphatic return is not a separate dynamic.* Volume return
  remains subsumed in the net Starling pathway; Milestone 26 adds
  the protein flux that rides on it (leak/return pair, S32), not a
  lymph volume flow. An oedema or lymph-failure scenario still
  cannot be authored.
- *Hormonal axes absent* (ADH, aldosterone, RAAS, ANP): the renal
  curve is the acute shape (S23); its chronic steepening is
  unmodelled, and protein handling has no hormonal term either.
- *Single linear interstitial compliance* against S26's nonlinear
  fitted curve.
- *Intake constant and unregulated; the renal curve senses MAP
  only* (no tubular, osmotic, or protein-excretion modelling —
  urine carries no protein in this engine).

**New this milestone**

- *Albumin fraction fixed* at the resting plasma ratio in both
  pools (§1.1): the interstitial pool's true albumin fraction
  differs, and fraction changes in disease are outside a
  total-protein state. S33's recorded 10–15% inter-equation spread
  is the scale of this simplification.
- *σ is one lumped value* (0.9, muscle-dominated): fenestrated and
  discontinuous beds (liver, gut) exchange protein far more freely
  and are not distinguished.
- *The Starling protein-flux convention* (inflow limb unsieved at
  the interstitial concentration, outflow limb sieved at
  (1 − σ)·cp) is a modelling convention, disclosed as such; it is
  not itself a cited result, and the sieved-both-ways alternative
  would return less protein on refill and brake harder.
- *Synthesis is understated by construction*: the albumin rate
  (S31) is applied to the total-protein pool (albumin ≈ 60% of
  plasma protein mass), so oncotic mass recovery is slower than a
  full total-protein synthesis would give, never faster.
- *Product protein estimates*: whole-blood protein neglects the
  anticoagulant's ≈12% dilution (slight overstatement); PRBC
  protein is a residual-plasma estimate that additive-solution
  units undercut (overstatement). Both notes ride on their
  parameters.
- *Plasma is volume + protein only*: no coagulation state exists,
  so FFP's factor activity — its actual clinical purpose — is
  unmodelled and unclaimed.
- *Hematocrit is tracked-but-inert* (§1.1): no viscosity coupling,
  no F-cell correction.
- *The Theatre's product channel is single-flow*: one product
  composition at a time (a second transfuse replaces the flow);
  overlapping distinct products do not compose. No shipped trace
  transfuses yet (§8), so this bounds future trace authoring, not
  any current result.
- *Nitta anchor offsets*: the relation reads −3.6% / −1.6% against
  S29's table values at the two resting points (§1.1); it is used
  as cited and the offsets are carried, not corrected.

**Review gate: still UNMET, system-wide.** No named expert
reviewers exist for any ANATOMICA module; all content remains
`dual-sourced-draft`, formative-only. Nothing in this milestone
changes that status.

## 7. Cross-module impact and checker matrix

**Theatre.** The blood-loss identity gains the product term in the
Milestone 25 pattern — `(volume_at_start + infused_ml +
product_during + refill_during + intake_during − urine_during) −
volume_end`, with `product_during` read from the engine's own
product integral between attempt start and scoring. A `transfuse`
action naming a known product (`product: "whole_blood" | "prbc" |
"plasma"` — a new optional trace field) routes through the
product channel and is tallied separately (`physiology.
transfused_ml`, a new debrief field, 0.0 for every shipped trace);
an unnamed transfuse routes as volume only, as before, and the log
says so. All 5 traces re-run with **0 expectation failures**; the
field-level debrief diff against the Milestone 25 files is exactly
four fields per file — `engine_trace_hash` (fold changed),
`engine_beats` (small shifts, −4 to −27, from the oncotic term
acting during the attempts), `engine_conservation_error_ml`
(~1e-8, noise class), and the added `transfused_ml` — with every
clinical field (verdicts, timings, checklist, scores, complications,
measured blood loss) byte-identical.

**Cases.** Re-recordings in the established pattern, each verified
by the checker rather than asserted: case #1's `physiology_link`
hash → 0xcee16b0ddee95d76 with a Milestone 26 re-recording note (no
recorded output moved at the recorded precision); case #2's
`theatre_link.debrief_sha256` → 74e13c0e… with its re-recording
note (every matched field re-verified unchanged by the checker's
field-by-field comparison).

**Checker matrix (all run this session)**

| check | result |
|---|---|
| physiology `validate` | ALL HARD GATES PASS (soft ledger §5.4) |
| physiology `cargo test` | 20/20 (17 prior + 3 new: quiet-at-rest oncotic states, product-channel identity/bookkeeping, dilution + PRBC hematocrit) |
| physiology `determinism` | IDENTICAL |
| theatre `cargo test` | 8/8 |
| theatre `run-all` | 5 traces, 0 expectation failures |
| `tools/case_check.py` | 3,280 passed, 0 failed |
| `tools/assembly_check_all.py` | ALL GATED CHECKS PASS |
| `tools/verify_web.js` | ALL CHECKS PASS |

## 8. Next steps

1. A case authored against computed urine output (Milestone 25's
   named next step, still open): the Workbench now has resting and
   course urine trajectories to cite, plus an oncotic state, for a
   case whose findings turn on renal response.
2. A Theatre trace that transfuses: the product channel and the
   loss identity are ready end-to-end; a haemorrhage-management
   trace would exercise them and give the management score a
   transfusion decision to judge.
3. Shells/cases integration into the native shell (standing queue
   item, unchanged).
4. Nonlinear interstitial compliance (S26's fitted curve) when an
   oedema or multi-litre scenario is authored (standing).
5. A separate albumin-fraction state only if a sourced
   transcapillary albumin/globulin split is consulted; the fixed
   fraction is adequate for every scenario currently authored.
