# 04 — Physiology Engine

## Purpose

A deterministic, inspectable simulation of the body's control systems, wired
into the Body Model: the same engine runs the monitor in the atlas's physiology
view, the patient under anaesthesia in the Theatre, and the case patient whose
labs the workbench orders.

## Architecture (Pulse-derived, per master plan §4)

Lumped-parameter, circuit-analog compartments, after the Pulse Physiology
Engine's published architecture (Apache-2.0; architecture adopted, validation
tables used as the external reference — code embedding is OD-04.1):

- **Cardiovascular circuit:** heart chambers as time-varying elastance;
  systemic/pulmonary/coronary/cerebral/renal/splanchnic segments as
  resistance–compliance–inertance elements keyed to Body Model vessel IDs, so
  occluding a named vessel in the model drops its territory's perfusion.
- **Respiratory:** single-compartment lung (compliance, airway resistance),
  ventilation control loop, gas exchange producing computed blood gases.
- **Fluids/electrolytes/acid–base:** ICF/ECF/plasma compartments, osmolarity,
  major ions; renal handling (GFR, tubular reabsorption) with drug hooks.
- **Metabolic/endocrine:** glucose–insulin loop; thyroid/adrenal axes at
  summary depth; calcium handling.
- **Pharmacology layer:** drug records (class, mechanism, dose range, onset/
  duration) whose effects are functions into the compartments — volatile and IV
  anaesthetics (MAC values; Marsh/Schnider/Eleveld TCI parameter sets),
  pressors/inotropes (norepinephrine first-line per SSC; vasopressin fixed-dose
  adjunct), fluids and blood products, antibiotics (timing modelled, spectra
  in the formulary). OpenTCI/SimTIVA (GPL-3.0) are reference implementations
  to reimplement from, never to link (see governance).

## Determinism contract

- Fixed timestep: 20 ms (Pulse's published step), integer tick counter; all
  integration in fixed order; no wall-clock, no unseeded randomness anywhere
  in the core. Same initial state + same input stream ⇒ bit-identical state
  hash at every tick, on both shells.
- Inputs are events on ticks (perturbation applied, drug bolus started,
  ventilator setting changed). Every run is recordable and replayable; the
  Theatre's assessment mode and the Cases debrief both run on replay.

## Causal-chain exposure

Every output variable keeps a bounded provenance ring: the last N contributing
events and parameter changes with magnitudes. The UI query "why did MAP fall"
returns the chain (e.g., blood volume −750 mL → venous return ↓ → stroke volume
↓ → cardiac output ↓ → MAP ↓, with the baroreflex compensation annotated).
A value without an explainable chain is a bug by definition here.

## Perturbation library (state interventions, composable)

Hemorrhage by ATLS class (I ≤750 mL … IV >2,000 mL, with the published validity
caveat carried in the module), tension pneumothorax, cardiac tamponade, MI by
coronary territory, pulmonary embolism, sepsis (Sepsis-3 definitions; SSC 2021
bundle timing modelled for scoring), anaphylaxis, DKA, stroke by territory.
Each perturbation is parameterised (rate, territory, onset) and cites its
defining source in the module file.

## Validation

- **Steady-state gate:** undisturbed, the engine holds published normal ranges
  indefinitely (CO 4–8 L/min, MAP 70–95 mmHg, ABG pH 7.35–7.45 / PaCO₂ 35–45 /
  HCO₃ 22–26, GFR ≈125 mL/min — values per research round 2 with sources).
- **External tables:** deviation report against Pulse's published validation
  tables (474 parameters, 397 within 10%) for the parameters we implement —
  our dossier states our numbers, not Pulse's.
- **VitalDB** (CC BY 4.0, no DUA): 6,388 surgical cases with 500 Hz waveforms
  (arterial line, ECG, PPG) — the shippable waveform-realism validation set.
- **Credentialed sets (MIMIC-IV, eICU, HiRID, AmsterdamUMCdb):** offline
  validation only by a credentialed developer; metrics and code may be
  published, data and derived files never ship. This boundary is a release gate.
- Every module ships a **validation dossier**: parameters, reference values,
  measured deviations, known simplifications — published in-tree.

## Interfaces

`tick(n)`, `apply(perturbation|drug|setting, at_tick)`, `query(variable) →
{value, unit, causal_chain}`, `snapshot()/restore()` (what-if branching),
`hash(tick)`. Outputs: monitor traces (HR, ECG, SpO₂ pleth, arterial waveform,
RR, EtCO₂, temperature), labs (CBC, BMP, ABG/VBG, coagulation, LFTs, troponin,
lactate) — all computed from state, in LOINC-coded result records for the
workbench (LOINC ships as a separately-licensed pack; see `07`).

## Verification gates

Steady-state gate in CI; replay-determinism gate; dossier completeness check
(no perturbation ships without source citation); waveform realism report
against VitalDB summary statistics per release.

## Open decisions

- **OD-04.1 Embed Pulse vs build our core.** Embedding (C++ via FFI in the
  native shell; wasm in web) buys a validated engine and costs a large foreign
  codebase whose state model must still be mapped onto our Body Model IDs and
  causal-chain requirement (Pulse does not expose causal chains — a wrapper
  would have to infer them). Building buys full control and the causal-chain
  contract, and costs years of validation — mitigated by validating against
  Pulse's published tables. Decide at P4 start with a time-boxed embedding
  spike; the causal-chain contract is non-negotiable either way.
- **OD-04.2** Respiratory depth: single-compartment vs two-compartment
  (V/Q mismatch needed for credible PE/shunt cases). Leaning two-compartment
  at P4; single-compartment prototype is acceptable for P2-era demos only if
  labelled as such (Messick honesty, see `10-governance.md`).
