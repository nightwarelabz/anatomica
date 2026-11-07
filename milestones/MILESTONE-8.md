# Milestone 8 — Physiology engine v0: deterministic core + cardiovascular compartment model

Status: built and verified locally. Not uploaded; presented for
approval as a unit, as with Milestones 2–7.

Method follows the precision law as in Milestones 4–5: every number in
the model comes from a source consulted during the build and cited
in-file (`physiology/parameters.json`, 46 parameters, 12 sources);
anything unsourced is an explicit `verify` status in that file, never
filled from recall. The resting case was gated against published
normal ranges **before** any perturbation was trusted, per design/04.

## Deliverables

| File | Content |
|---|---|
| `physiology/Cargo.toml` | Package `anatomica-physiology`, binary `anatomica-physiology`; serde/serde_json only |
| `physiology/parameters.json` | The full parameter set with units, cited ranges, per-entry source + status (`cited` / `calibrated` / `verify`), the 12 validation ranges, and the perturbation expectations with their sources |
| `physiology/src/params.rs` | Loader with a provenance schema gate: a parameter that is neither cited, calibrated within its cited range, nor verify-flagged fails to load |
| `physiology/src/engine.rs` | The deterministic core: 8-compartment lumped circuit, time-varying-elastance ventricles, Bernoulli valves, tick events, snapshot/restore, FNV trace hash, query + event-log causal chain |
| `physiology/src/cases.rs` | Case protocol (settle → baseline window → reflex on → events → post window) and the validation evaluators |
| `physiology/src/main.rs` | CLI: `validate` (full tables, exit code = hard gates), `run resting\|hemorrhage\|infusion`, `determinism` |
| `physiology/tests/engine_tests.rs` | 8 integration tests: provenance schema, bit-identical determinism, snapshot/restore replay, volume conservation, resting gates, both perturbation direction suites, query interface |
| `MILESTONE-8.md` | This dossier |

## 1. Language decision

design/04 names no implementation language, and OD-04.1 (embed Pulse
vs build our core) remains open — this milestone is the "build" track
executed at v0 scope; it does not close OD-04.1. Within "build", the
core is **Rust**, mirroring `native/` conventions (edition 2021,
AGPL-3.0-only, serde), because design/04's purpose statement has the
same engine running inside the (Rust) native shell's atlas monitor,
Theatre and case workbench, and its determinism contract requires a
bit-identical state hash "on both shells" — one portable core, not a
Python reference that a second implementation would later have to
match digit-for-digit. A Python prototype was the alternative and was
rejected for that reason.

## 2. Architecture as built

- **Compartments (state = 8 volumes):** LV, systemic arteries,
  systemic capillaries, systemic veins, RV, pulmonary arteries,
  pulmonary capillaries, pulmonary veins. The brief's four named
  vascular compartments are present; the source model's capillary
  segments are retained between artery and vein on both circuits
  because the cited parameter set (S1) is defined on that
  segmentation — collapsing it would silently change the meaning of
  the cited compliances. Vessels: `P = (V − Vu)/C`, `Q = ΔP/R`.
- **Ventricles (design/04's choice: time-varying elastance)**, in the
  published form of S1: diastolic `Pd = A·(e^{K(V−Vu)} − 1)`, systolic
  `Ps = E·(V − Vd)·(1 − KR·Q)·v(t)`, chamber pressure
  `P = Pd·(1 − v(t)) + Ps`, activation `v(t) = sin²(π·τ/tv)`,
  `tv = 0.45 s` at the 1 s cycle. The ventricle/valve pair is solved
  jointly in closed form (the KR term makes chamber pressure depend
  on ejection flow; the Bernoulli valve law is quadratic in flow).
- **Valves:** Bernoulli law from S1's cited orifice areas (AV valves
  7 cm², semilunar 5 cm²) and consulted blood density (1,060 kg/m³);
  fully competent (no regurgitation), one-way. AV valves carry their
  upstream segment resistance in series (S1's Rsv / pulmonary-vein R).
- **Determinism:** 20 ms tick (S10/design/04, Pulse's published step),
  integer tick counter, fixed-order RK4 at a fixed 0.5 ms substep
  (40/tick, verify-flagged numerical choice), no wall clock, no
  randomness of any kind. Events land on tick boundaries. Per-tick
  FNV-1a trace hash over tick + state bits. Interfaces per design/04:
  `tick(n)`, `apply(event, at_tick)`, `query(variable) → (value,
  unit)`, `snapshot()/restore()`, `hash(tick)`.
- **Baroreflex (v0, deliberately partial):** first-order low-passed
  MAP (τ = 3 s) drives two effectors — heart rate and the systemic
  peripheral resistance (S1's capillary segment) — through saturating
  proportional multipliers. The setpoint is the model's own measured
  resting MAP (no external setpoint value is asserted). **All reflex
  gains, bounds and the lag are verify-flagged engineering
  placeholders with no literature source** (§6). Venomotor
  (unstressed-volume) recruitment and contractility effects are not
  modelled — the omission is measurable in §5.
- **Causal chain (v0 depth):** `query` returns value + unit; the
  chain is the applied-event log with ticks and magnitudes (e.g.
  "tick 6000: haemorrhage 750 mL over 60 s begins: external volume
  flow set to −12.500 mL/s"). It is event-level provenance, **not**
  the contribution-weighted chain design/04 ultimately requires;
  that gap is recorded, not papered over.

## 3. Parameters and the one calibration

All vascular and cardiac parameters are S1's published tables
verbatim (compliances, unstressed volumes, resistances; chamber
A/K/Vu/E/Vd/KR). Two source ambiguities are disclosed in
`parameters.json` rather than silently resolved: S1's supplement
labels the pulmonary-artery resistance cell "Rpv" (colliding with
the pulmonary-vein name), and its KR row's two values are assigned
to the RV/LV columns because S1's Eq. 5 defines KR for ventricles
only.

**Total blood volume is the single calibrated parameter.** Cited
range 4,900 mL (70 mL/kg × 70 kg, S8) to 5,570 mL (S1's own model
baseline). Measured sweep (resting post-window, all else identical):

| TBV (mL) | MAP (70–95) | CO (4–8) | CVP (2–6) | PA sys (15–25) | PV mean (6–12) | Verdict |
|---|---|---|---|---|---|---|
| 5,570 (S1) | 96.4 ✗ | 5.51 ✓ | 6.67 ✗ | 34.4 ✗ | 11.5 ✓ | pressures overshoot |
| 5,300 | 86.1 ✓ | 4.95 ✓ | 5.58 ✓ | 29.6 ✗ | 9.1 ✓ | PA systolic only |
| 5,100 | 77.7 ✓ | 4.47 ✓ | 4.79 ✓ | 26.0 ✗ | 7.4 ✓ | PA systolic only |
| **5,000 (S8)** | **73.1 ✓** | **4.21 ✓** | **4.39 ✓** | **24.2 ✓** | **6.6 ✓** | **all gates pass** |
| 4,900 | 68.3 ✗ | 3.94 ✗ | 4.00 ✓ | 22.3 ✓ | 5.8 ✗ | undershoot |

The shipped value is **5,000 mL — S8's textbook figure for the
70-kg reference adult ("about 5 L")**, inside the cited range. The
mechanism of the sweep is disclosed: v0 omits S1's atrial chambers
and pericardium, whose diastolic compliance holds volume at low
pressure in S1's model, so S1's 5,570 mL over-pressurises this
reduced compartment set; PA systolic binds from above (it scales
with stroke volume through the ejection transient) while MAP/CO/PV
bind from below. The resulting reference patient is **low-normal**:
thinnest margins are CO +0.21 L/min above its floor, PV mean
+0.56 mmHg above its floor, MAP +3.1 mmHg above its floor, PA
systolic 0.84 mmHg below its ceiling. Stated, not hidden.

## 4. Validation results (measured, final build)

Resting case, post window (reflex engaged, ticks 10500–12000,
31 beats). Baseline (reflex off) was 99.3/62.2, MAP 72.9, CO 4.17 —
the reflex changes nothing material at rest, as it should with a
self-set setpoint.

| Output | Value | Published range | Source | Result |
|---|---|---|---|---|
| Heart rate | 61.16 /min | 60–100 | S11 | PASS |
| Systolic BP | 99.05 mmHg | 90–120 (soft) | S2 | SOFT-PASS |
| Diastolic BP | 62.41 mmHg | 60–80 (soft) | S2 | SOFT-PASS |
| Mean arterial pressure | 73.09 mmHg | 70–95 | S10 (S2: 70–110) | PASS |
| Pulse pressure fraction | 0.37 of systolic | ≥ 0.25 | S2 | PASS |
| Cardiac output | 4.21 L/min | 4–8 | S10, S3, S11, S5 | PASS |
| Stroke volume (LV) | 68.90 mL | 55–100 | S11 | PASS |
| Central venous pressure | 4.39 mmHg | 2–6 | S4 (S3: 1–7) | PASS |
| PA systolic | 24.16 mmHg | 15–25 | S4, S3 | PASS |
| PA diastolic | 9.42 mmHg | 8–15 | S4 (S3: 6–12) | PASS |
| PA mean | 14.43 mmHg | 10–20 | S4 (S3: ~15) | PASS |
| Mean PV pressure (PCWP proxy) | 6.56 mmHg | 6–12 | S4 (S3: 8–12) | PASS |
| Steady-state drift (window halves) | MAP 0.000% / CO 0.003% | < 1% (engineering criterion) | parameters.json | PASS |
| LV vs RV stroke volume | 68.9 vs 68.9 mL | < 5% (series identity) | — | PASS |
| Volume conservation error | 1.46×10⁻¹¹ mL | < 0.01 mL (identity) | — | PASS |

The two BP lines are **soft** gates, disclosed in `parameters.json`:
S2 was consulted for the typical values (systolic "typically around
120", diastolic "usually about 80"); the 90/60 lower bounds are the
conventional hypotension thresholds and were **not** read in a
consulted source this session, so a miss would be reported but
would not fail the build. Both lines pass at the shipped values.
MAP is the engine's true time-mean of arterial pressure, not the
cuff approximation (diastolic + pulse/3) S2 describes. The PV-mean
line is labelled a *proxy*: it is the pulmonary venous compartment's
mean pressure, not a wedge measurement — v0 has no left atrium.

Perturbations (baseline → post, directions gated; sources per line
in `parameters.json`):

| Case | Output | Baseline | Post | Δ | Expected | Result |
|---|---|---|---|---|---|---|
| Haemorrhage −750 mL | MAP | 72.91 | 45.63 | −27.28 | falls | PASS |
| | Heart rate | 60.0 | 114.0 | +54.0 | rises | PASS |
| | Pulse pressure | 37.17 | 10.87 | −26.30 | narrows | PASS |
| | Cardiac output | 4.17 | 1.54 | −2.63 | falls | PASS |
| Infusion +1,000 mL | MAP | 72.91 | 78.61 | +5.70 | rises | PASS |
| | CVP | 4.36 | 9.32 | +4.97 | rises | PASS |
| | Cardiac output | 4.17 | 5.39 | +1.22 | rises | PASS |

Trace hashes: resting `0x98fa0a8dacf6c83d`, haemorrhage
`0x4e49241d2ec235dc`, infusion `0x452f5014aacd014a`. `determinism`
re-runs the resting protocol twice: identical hashes. `cargo test
--release`: **8 passed, 0 failed**. CLI `validate` exit code 0.

## 5. Magnitude honesty — what the directions conceal

The perturbation gates are directional, as briefed. The magnitudes
are **not** validated, and two are frankly off; both are recorded
here with their mechanisms rather than tuned away with unsourced
knobs:

- **Haemorrhage −750 mL over-responds.** Post MAP 45.6 mmHg, SV
  13.5 mL, CO 1.54 L/min is a near-terminal picture, where ATLS
  (S6/S7) puts a 750 mL loss at the Class I/II boundary — blood
  pressure normal, heart rate <100–120 — and S2 notes compensation
  can keep a patient asymptomatic through 10–20% volume loss
  (750 mL ≈ 15% of the 5,000 mL reference volume). The model's
  heart-rate response (114/min) lands in the ATLS Class II band,
  but its pressure collapse is disproportionate. Mechanism, by
  construction: the dominant real compensation — sympathetic
  venoconstriction recruiting the venous unstressed volume
  (2,747 mL in this parameter set) into the stressed volume, plus
  transcapillary refill — **is not modelled**; volume removed from
  the venous compartment therefore cuts stressed volume 1:1, and
  the two placeholder-gain effectors (HR, resistance) cannot
  replace it. A sourced venomotor model is next-step #1. The ATLS
  caveat of S7 also stands in the other direction: ATLS vital-sign
  magnitudes are themselves contested (Mutschler reappraisal), so
  ATLS is used for direction only, never as a magnitude target.
- **Infusion +1,000 mL does not re-equilibrate.** Post CVP
  9.32 mmHg, PV mean 16.2 mmHg, PA mean 26.3 mmHg sit above the
  resting ranges and HR falls to 45.3/min under the placeholder
  reflex gain. A closed lumped circuit with no renal excretion, no
  transcapillary escape and no lymphatic return has nowhere to put
  a sustained +20% volume load; the case validates direction only,
  and its post state is not a sustainable physiology claim.

## 6. Verify-flagged items (no literature source — complete list)

All in `parameters.json` with status `verify`: integration substep
(0.5 ms); systole-duration heart-rate scaling exponent (0.5 — S1
fixes HR at 60 bpm and gives no scaling law); valve Bernoulli
regularisation (0.002 mmHg·s/mL, numerical only); baroreflex lag
(3 s), HR gain (4.0), resistance gain (3.0), HR multiplier bounds
[0.7, 1.9], resistance multiplier bounds [0.75, 1.8]; steady-state
drift tolerance (1%, an engineering acceptance criterion). None of
these is a physiological claim; the reflex set is the model's
weakest-sourced component and is labelled as such wherever it is
described.

## 7. Simplifications and what is NOT modelled

Documented simplifications (the law requires them in-product; this
section is the v0 record): atria are compartments of S1's model but
not of v0 — the mitral/tricuspid inflows are driven directly by the
pulmonary-venous/systemic-venous compartments, so there is no
atrial kick and no separate atrial pressure; pericardium omitted
(no ventricular interaction or pericardial constraint); inertance
omitted (S1's L values are cited in `parameters.json` as
cited-but-unused); valves are ideal diodes (no regurgitation, no
stenosis); bronchial circulation (S1's Rbc) omitted; haemorrhage is
removed from, and infusion added to, the venous reservoir
compartment as the lumped site (blood is in reality lost from and
added to the whole circuit); the baroreflex senses mean pressure
only, with two effectors and placeholder gains; systole duration
scales with the square root of cycle length by an unsourced
engineering rule.

Not modelled at all in v0: respiratory system and gas exchange;
fluids/electrolytes/acid–base; renal handling and any fluid
excretion; pharmacology; coronary/cerebral/renal/splanchnic
territory segmentation (design/04 keys segments to Body Model
vessel IDs — Milestone 5's inventory is the join target, not yet
joined); temperature; any pathology beyond the two volume
perturbations; waveform outputs (ECG, pleth, EtCO₂) and labs.
Pulse's published validation tables (474 parameters) have not yet
been differenced against this engine — design/04's external-table
deviation report is owed, and nothing here claims Pulse-grade
validation: v0 is validated against published normal **ranges** and
sourced directional expectations only.

## 8. Next steps

1. Sourced venomotor/unstressed-volume recruitment (and
   transcapillary refill) so haemorrhage magnitudes, not just
   directions, can be gated — the single largest known defect.
2. Territory segmentation keyed to Milestone 5's vessel records
   (coronary first: design/04's MI-by-territory perturbation needs
   it) and the remaining design/04 perturbation library, each with
   its defining source cited in-module.
3. Pulse validation-table deviation report for the parameters v0
   implements (design/04 validation dossier requirement), and the
   OD-04.1 embed-vs-build decision taken with this core as the
   "build" evidence.
4. Respiratory single-compartment module (OD-04.2 labelling
   applies) and computed blood gases, so the steady-state gate can
   extend to the ABG ranges design/04 lists.
5. Contribution-weighted causal chains: per-output provenance with
   magnitudes, replacing the v0 event log.
