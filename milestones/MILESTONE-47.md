# Milestone 47 — Physiology: the respiratory module

Ventilation and gas exchange, coupled one-way to the circulation:
a lumped CO2 store with a chemoreflex controller, the alveolar gas
equations, arterial blood gases, and oxygen content/delivery read
off the engine's own cardiac output and hematocrit state. Local
build only; nothing uploaded.

## 1. Design

### The load-bearing wall: one-way coupling

The case workbench pins the resting circulation trace hash
(`0x6369b10e9a71c872`, cases #1/#3), and every Theatre debrief
embeds an engine trace hash. The respiratory module is therefore
built so that **no respiratory state or input enters any
circulation derivative**: PaCO2 and respiratory rate are integrated
as new states, but `evaluate()` reads them only for their own
derivatives, and every oxygen-transport quantity is a pure readout
function of state plus a caller-supplied cardiac output. The
circulation trajectory is bit-identical by construction — the
module at rest is a true no-op on the pinned baseline, not merely
a small perturbation (§5 proves it three ways). The respiratory
states fold into a **separate** FNV-1a chain (`resp_hash`, same
offset basis, folded per tick over tick + PaCO2 + rate bits), so
the module's own determinism is pinned without touching the
circulation fold.

### What is dynamic, what is algebraic

- **CO2 is a dynamic store.** dPaCO2/dt = (VCO2 − PaCO2·VA/(1000·0.863))
  / C_store per minute, with VA = RR·(VT − VD). The elimination
  term is the PCO2 equation (S51) rearranged, so the store's steady
  state *is* the cited equation: PaCO2 = 0.863·VCO2/VA. The store
  initialises at that equation's resting value (41.095 mmHg), where
  its derivative vanishes — the house equilibrium construction
  (M25/M26/M30 pattern), so the resting settle is undisturbed.
- **The chemoreflex is a controller, like the baroreflex.** When
  the reflex engages (`set_reflex_setpoint`, the same call the
  baroreflex uses), the module captures its operating point — the
  model's own resting (PaCO2, minute ventilation). Thereafter
  VE_target = VE_set + slope·(PaCO2 − PaCO2_set) (S58), allocated
  to respiratory rate alone at the current tidal volume, clamped
  to the flagged actuator bounds [4, 40] /min; the rate state
  approaches its target at the lumped chemoreflex time constant
  (S59). A scenario override (`SetVentilationOverride`) holds the
  rate with the chemoreflex suspended; releasing it returns
  control to the reflex.
- **Oxygen is algebraic** (its stores equilibrate in seconds
  against the CO2 store's minutes; disclosed as a simplification):
  PAO2 by the full alveolar gas equation
  PAO2 = FiO2(PB − 47) − PaCO2·(FiO2 + (1−FiO2)/R) (S52/S53);
  end-capillary content by the content equation at PAO2 with the
  Hill dissociation curve (S61/S63/S67); arterial content by the
  Berggren venous-admixture mixing relation
  CaO2 = CcO2 − (fs/(1−fs))·(VO2/CO) (S57); PaO2 by fixed-iteration
  bisection inversion of the content equation (200 halvings, the
  house MCFP-solve style — deterministic, no data-dependent
  termination); CvO2 = CaO2 − VO2/CO and DO2 = CO·CaO2·10 by Fick
  (S55). Haemoglobin enters through the MCHC identity on the
  Milestone 26 hematocrit state, Hb = MCHC × Hct — the coupling
  that carries bleeding and dilution into oxygen content.
  Readouts take the cardiac output from the caller's beat window
  (a steady-state quantity in the M24 sense), never from an
  instantaneous transient sample.
- **Acid–base is Henderson–Hasselbalch with acute buffering only:**
  pH = 6.1 + log10(HCO3/(0.03·PaCO2)) (S66), HCO3 = 24 + the acute
  slope applied to the PaCO2 deviation from the model's own
  operating point (+0.1 mEq/L per mmHg up, −0.2 per mmHg down —
  S66 Rules 1 and 3, asymmetric as the source states them). No
  renal/chronic compensation is modelled (§6).

### Scenario inputs (new events, house enum pattern)

`SetMetabolicRate` (VO2 mL/min; VCO2 = RQ·VO2), `SetVentilation`
(tidal volume and/or dead space), `SetVentilationOverride`
(rate hold/release), `SetVenousAdmixture` (the lumped shunt
fraction). New `query()` variables: arterial_pco2, arterial_ph,
respiratory_rate, minute_ventilation, alveolar_ventilation,
oxygen_consumption, co2_production, hemoglobin, alveolar_po2,
arterial_po2, arterial_oxygen_saturation, arterial_oxygen_content,
oxygen_delivery, aa_gradient, bicarbonate.

### Named simplifications (in-product, per the precision law)

Single-compartment lung; the lumped venous-admixture fraction is
the only V/Q structure (no regional distribution, no diffusion
limitation, no separate dead-space gas-exchange term beyond
VA = RR·(VT − VD)); no hypoxic ventilatory drive — the controller
is CO2-only, so a pure shunt produces normocapnia (§4), which is
the model's honest consequence, stated rather than patched; fixed
dissociation-curve position (no Bohr/2,3-BPG/temperature shift);
ventilatory response allocated to rate alone (tidal volume and
dead space are scenario anatomy, not controller outputs); no
intrathoracic-pressure effect on venous return; metabolic rate is
a scenario input with **no circulatory coupling** (the module
models no cardiac-output response to exercise — the metabolic arm
therefore gates ventilation and PaCO2 only, by design); oxygen
side algebraic; acid–base acute-only. Hematocrit's tracked-but-
inert status in the circulation is unchanged — it now also
carries oxygen content, a readout coupling, still no viscosity or
mechanics coupling (none was cited for one).

## 2. Parameters (26 added; sources S51–S67 registered)

parameters.json edited append-only, in its original formatting
(the M25 rule): 50 → 67 sources, 104 → 130 parameters, 21 → 29
validation ranges, 9 → 13 perturbation cases; every pre-existing
entry verified identical in parsed form after the edit.

| Parameter | Value | Status | Source |
|---|---|---|---|
| barometric_pressure_mmhg | 760 mmHg | cited | S53 |
| water_vapor_pressure_mmhg | 47 mmHg | cited | S53 |
| body_temperature_c | 37 °C | cited | S53 |
| inspired_o2_fraction | 0.21 | cited | S52 |
| tidal_volume_ml | 500 mL | cited | S52 |
| dead_space_ml | 150 mL (Williams' 0.2 L alternative disclosed in-file) | cited | S51 |
| respiratory_rate_resting_per_min | 12 /min | cited | S64 |
| vo2_resting_ml_min | 250 mL/min | cited | S54 |
| respiratory_quotient | 0.8 | cited | S54 |
| alveolar_ventilation_constant | 0.863 | cited | S51 |
| venous_admixture_resting_fraction | 0.03 | cited | S57 |
| co2_store_capacitance_ml_mmhg | 45 mL/mmHg | calibrated [33.3, 95.2] | S60 |
| hill_p50_mmhg | 26.6 mmHg | calibrated [25, 29] | S63 |
| hill_coefficient | 2.7 | cited | S63 |
| hufner_constant_ml_g | 1.34 mL/g (S56's 1.39 disclosed) | cited | S61 |
| o2_solubility_ml_dl_mmhg | 0.003 mL/dL/mmHg | cited | S61 |
| mchc_g_dl | 33.3 g/dL | calibrated [32, 36] | S62 |
| bicarbonate_resting_meq_l | 24 mEq/L | cited | S52 |
| henderson_hasselbalch_pk | 6.1 | cited | S66 |
| co2_solubility_hh_mmol_l_mmhg | 0.03 | cited | S66 |
| acute_hco3_rise_per_mmhg | 0.1 mEq/L per mmHg | cited | S66 |
| acute_hco3_fall_per_mmhg | 0.2 mEq/L per mmHg | cited | S66 |
| chemoreflex_slope_l_min_mmhg | 2.5 L/min/mmHg | calibrated [1, 4] | S58 |
| chemoreflex_tau_seconds | 90 s | calibrated [60, 150] | S59 |
| resp_rate_min_per_min | 4 /min | **verify** | — |
| resp_rate_max_per_min | 40 /min | **verify** | — |

Sources: S51 Martin, *The Four Most Important Equations in
Clinical Practice* + companion ch. 4 (opened in full); S52
Williams, BMJ 1998;317:1213–6 (opened in full); S53 StatPearls,
Alveolar Gas Equation (search extract — the NCBI page itself was
reCAPTCHA-blocked on open; the formula and constants are also in
S52); S54 StatPearls, Respiratory Quotient; S55 Pittman,
*Regulation of Tissue Oxygenation* ch. 7; S56 McLellan, BJA CEACCP
2004; S57 Deranged Physiology, venous admixture (opened in full);
S58 StatPearls, Carbon Dioxide Response Curve; S59 hypercapnic-
response textbook summaries (ScienceDirect Topics); S60 apneic
CO2-rise studies (Sci Rep 2024; J Clin Anesth 1988); S61 Phillips,
Boston Medical Center oxygen-transport teaching deck; S62 MCHC
reference range 32–36 g/dL; S63 Baynes & Dominiczak, *Medical
Biochemistry*; Ferrell, J Biol 2009; S64 cal67 alveolar minute
volume table; S65 pulmolearn minute ventilation; S66 Brandis,
*Acid-Base Physiology*; S67 cal67 arterial oxygen content guide.
StatPearls pages reached only via search extract are cited for
nothing the extract did not show; no field rests on an unopened
source alone where a second opened source carries it (S52/S57
opened in full anchor the gas equation and the mixing relation).

## 3. Resting gates — all inside their cited bands

From `anatomica-physiology validate` (resting table; the eight
respiratory ranges are hard gates in `evaluate_resting`, asserted
by the CLI and by the test suite alike):

| Output | Value | Cited band | Source |
|---|---|---|---|
| PaCO2 | 41.10 mmHg | 35–45 | S51 |
| PaO2 | 91.24 mmHg | 80–100 | S52 |
| pH | 7.39 | 7.35–7.45 | S52 |
| SaO2 | 0.965 | 0.95–1.00 | S52 |
| CaO2 | 19.66 mL/dL | 17–20 | S67 |
| Minute ventilation | 6.00 L/min | 5–8 | S65 |
| Alveolar ventilation | 4.20 L/min | 4–6 | S64 |
| Oxygen delivery | 828 mL/min | 800–1,000 | S61 |

Reported alongside (not gated): PAO2 100.5 mmHg, A–a gradient
9.3 mmHg, CvO2 13.73 mL/dL, haemoglobin 14.99 g/dL, bicarbonate
24.00 mEq/L, VO2 250 / VCO2 200 mL/min, **oxygen extraction ratio
0.302**. The extraction ratio is reported, not gated, and the
reason is disclosed rather than hidden: the consulted bands
disagree at the edge (S56: 0.2–0.3; S61: 22–32%), and the value is
not a free output — by the Fick identity O2ER = VO2/(CO·CaO2·10)
it is fixed once VO2, content and cardiac output are fixed. The
engine's CO rests at 4.21 L/min, the low end of its own cited
[4, 8] band, which puts DO2 at the low end of its band (828 of
800–1,000) and the extraction ratio correspondingly at the cited
bands' upper region (0.302 against S56's 0.30 edge, inside S61's
22–32%). Gating it would gate the CO band's low end a second
time; the arithmetic is shown here instead. The DO2 band question
was settled the same way: S61 publishes 800–1,000 mL/min as the
normal delivery range (S55's worked point, 1,000 mL/min at CO
5.0 L/min, sits at its top; other consulted statements span
600–1,100) — the range is registered with the spread disclosed in
the parameter file, and the model lands inside it by arithmetic,
not by tuning: no parameter was adjusted to reach any resting
gate. Every resting value above follows from the cited resting
inputs (VO2 250, RQ 0.8, VT 500, VD 150, RR 12, admixture 0.03)
through the cited equations.

## 4. Scenario arms — measured against computed predictions

All reads at steady-state marks (the M24 sampling rule): the CO2
store's time constant at resting ventilation is ~5.2 min, so
marks sit at +30 to +75 min, never on a transient.

**Hypoventilation** (rate held at 6 /min, VA halved 4.20 → 2.10
L/min, read +75 min; store time constant at the halved ventilation
~18.5 min, so the read is within ~2% of steady state):
PaCO2 41.10 → **81.41** mmHg — the PCO2 equation predicts
0.863·200/2.1 = 82.2 at full steady state (band [70, 95], a
project tolerance around the computed value in the M24 pattern)
PASS; PaO2 91.16 → 50.85 falls PASS; pH 7.39 → 7.16 falls PASS.

**Shunt** (venous admixture 0.03 → 0.20, read +30 min):
A–a gradient 9.36 → **39.20** mmHg — the Berggren relation at the
model's resting contents predicts ≈39 (band [28, 50]) PASS;
PaO2 91.16 → 61.32 falls PASS; PaCO2 41.10 → 41.10, in [35, 45]
PASS — unchanged by construction and by physiology: admixture
carries no CO2 term in this lump and the chemoreflex sees no CO2
error, the classic pure-shunt picture (normocapnic hypoxaemia),
recorded as the model's behaviour, not corrected toward a
textbook mixed picture.

**Metabolic rate doubled** (VO2 250 → 500, VCO2 200 → 400,
chemoreflex live, read +45 min): minute ventilation 6.00 →
**11.40** L/min (band [9.5, 15]; computed ≈11.9, and the cited
slope span's equilibria, 11.2–13.4, sit inside the band) PASS;
alveolar ventilation 4.20 → **7.98** L/min (band [7.0, 10.5];
computed ≈8.0) PASS; PaCO2 41.10 → **43.26** mmHg (band [38, 47];
the controller/store equilibrium computed from the cited
relations is 43.28; the cited slope span gives 42.5–45.9) PASS —
ventilation tracks VCO2 and holds PaCO2 near the operating point,
with the finite-slope offset the cited controller law predicts,
not a perfect hold and not a failure to respond (both failure
modes fall outside the band).

**Haemorrhage −750 mL, module live** (the M18 protocol; post read
at +30 min after the bleed ends, the M18 refill horizon):
DO2 819.99 → **689.66** mL/min falls PASS (flow and content both
fall, S55); CaO2 19.66 → **19.03** mL/dL falls PASS (haemoglobin
carried down by cell-free refill through the M26 hematocrit
state: Hct ≈ 0.437 at the read); PaO2 91.16 → 89.72, in [70, 100]
PASS; PaCO2 41.10, in [35, 45] PASS. The circulation gates hold
on their own terms on this very run: standard-window HR 102.1 in
the ATLS Class II band [100, 120] PASS, and §5's hash identity.

## 5. Baseline preservation — the proof

1. **By construction:** no respiratory state, input or readout
   enters any circulation derivative in `evaluate()` (the
   respiratory block computes only d_paco2/d_rr, appended after
   every circulation quantity); the trace-hash fold is untouched,
   and the respiratory states fold into the separate `resp_hash`.
2. **By measurement:** the full `validate` output is bit-identical
   to the pre-milestone baseline outside the M47 additions (whole-
   file diff, this session): every pre-existing line, every
   pre-existing trace hash (resting `0x6369b10e9a71c872`,
   haemorrhage_750 `0xbc683bf2721147ae`, and all course/refill/
   hormone hashes), and the FAIL set is exactly the pre-existing
   disclosed soft lines — no new failure of any kind.
3. **By cross-check inside the run:** the haemorrhage arm's
   circulation hash at the standard protocol endpoint (tick
   12,000) equals the standard haemorrhage_750 outcome's hash
   (`0xbc683bf2721147ae`) — asserted in `validate`, printed as
   HOLDS. The resting-protocol arms' endpoint hashes equal the
   pinned resting hash.
4. **By the consumers:** theatre run-all regenerates all 20
   debriefs byte-identical (md5-verified) with the new engine;
   `tools/case_check.py` passes 7,589/0 including its pinned-hash
   assertions; `cargo test` 27/27 (two new tests: the pinned hash
   with the module present, and respiratory determinism + shunt
   behaviour).

## 6. Honest limits

A one-compartment lung cannot say anything regional: no V/Q
scatter, no zone model, no diffusion limitation, no shunt
*anatomy* — the admixture fraction is a lumped effect size, not a
place. Oxygen transport is algebraic, so nothing here speaks to
the seconds-scale transients of a desaturation event. The
controller is CO2-only: hypoxic drive, acid–base drive from
metabolic acidosis, and behavioural/cortical control are absent,
so the module must not be read as predicting ventilation in
primary metabolic acidosis or at altitude. Acid–base is
acute-only: a chronic hypercapnia scenario would need the renal
compensation rules, which are deliberately not modelled (the
harness reads its arms inside the acute window). The dissociation
curve never shifts (no Bohr effect), so PaO2 readouts in severe
acidosis carry that named error. Metabolic rate does not drive
the circulation, so exercise physiology beyond the ventilatory
response is out of scope. The CO2 capacitance is calibrated from
apneic-rise rates measured under apneic oxygenation and breath-
holding — whole-body effective values, not a measured tissue
store. The rate actuator bounds [4, 40] /min are verify-flagged:
no consulted source states them as limits.

## 7. Verification matrix (this session)

- physiology `validate`: exit 0; every resting-table line PASS
  (27 range lines, including the 8 new respiratory lines);
  13 perturbation cases
  including the 4 new arms, all hard expectations PASS; FAIL set
  identical to the pre-milestone baseline (disclosed soft lines
  only); resting hash `0x6369b10e9a71c872`.
- physiology `cargo test --release`: 27 passed, 0 failed.
- theatre: run-all 20 traces, 0 expectation failures, debriefs
  byte-identical; `tools/theatre_check.py` 463/0.
- `tools/case_check.py` 7,589/0. `tools/assembly_check_all.py`
  all gated checks PASS. `tools/verify_web.js` all PASS.
- native `anatomica verify`: 99 PASS / 0 FAIL data assertions;
  the GPU render stage cannot initialise on this VM (no Vulkan
  ICD) — the standing disclosed limitation, unchanged.

## 8. Files in this batch

- `physiology/parameters.json` — append-only: sources S51–S67,
  26 parameters, 8 validation ranges, 4 perturbation cases.
- `physiology/src/engine.rs` — respiratory states, chemoreflex,
  gas-exchange readouts, 4 events, separate `resp_hash`, queries.
- `physiology/src/cases.rs` — `RespReadout` on every case outcome,
  respiratory resting evaluation, `run_respiratory_case` /
  `evaluate_respiratory`.
- `physiology/src/main.rs` — respiratory validate section
  (including the haemorrhage hash-identity and M18 HR assertions),
  `run respiratory`.
- `physiology/tests/engine_tests.rs` — pinned-hash and
  respiratory-determinism/shunt tests.
- `MILESTONE-47.md` — this dossier.

## 9. Next steps

- Chronic acid–base compensation (S66's chronic rules) as a slow
  state beside the ADH/aldosterone axes, if a chronic scenario is
  ever authored.
- A dead-space arm distinct from the shunt arm (raised VD via
  `SetVentilation`) — the machinery exists; no case authored yet.
- Theatre/case consumers may now read blood gases through
  `query()`; no consumer change is required by this milestone and
  none was made.
