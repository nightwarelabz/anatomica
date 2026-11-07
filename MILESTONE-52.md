# Milestone 52 — Physiology: the Bohr shift

The third and last of Milestone 47's deferred respiratory
couplings: the haemoglobin–oxygen dissociation curve now moves
with arterial pH. In acidosis the curve shifts right (P50 rises,
affinity falls — the tissues unload more easily and the lung
loads less); in alkalosis it shifts left. The shift trades
loading for unloading; it creates no oxygen. In this engine
delivery changes only through the content term, and this
milestone's two arms measure exactly that change, in both
directions, against predictions computed from the cited relation
before the engine was run.

With this milestone the **Milestone 47 deferral list is closed**:
hypoxic ventilatory drive (M51), metabolic–circulatory feedback
(M51), and the Bohr shift (this milestone). What the respiratory
module still cannot do is named in §7.

Discipline, as at Milestone 51: the parameter edit is append-only
in the file's original formatting; the coupling is anchored so
it is *exactly zero at the resting equilibrium* — not small,
zero; predictions were computed from the cited relation by an
independent solver (`work/m52/predict.py`, parameters.json
constants only, no engine code) before the engine arms were run;
the full validate output was diffed against the pre-milestone
baseline (`work/m52/validate-pre.txt` →
`work/m52/validate-post.txt`) and every differing line accounted
for.

## 1. The cited relation and its coefficient (S72)

The Bohr effect in the form this engine uses: the logarithm of
P50 varies linearly with pH,

    Δlog₁₀P50 / ΔpH = −0.48

cited to **S72** — Imai K, Morimoto H, Tamura M, et al. "A New
Look on the Position of the Oxygen Equilibrium Curve of Human
Adult Hemoglobin and an Interpretation of Its Bohr Effect."
*Zoological Science* 2001;18(7):905–918 (doi:10.2108/zsj.18.905):
"Under the physiological conditions, the Bohr coefficient for
human adult Hb is −0.48." The same paper's standard curve is
whole blood at 37 °C, pH 7.4, PCO₂ 40 torr with P50 26.7 torr —
the same curve family as the engine's Hill P50 (26.6 mm Hg,
calibrated within the S63 whole-blood range [25, 29]).

**The spread found in session, and the grounds for the pick.**
Consulted values for the human coefficient: **−0.48** (S72,
whole blood under physiological conditions; also the figure in a
2021 haemoglobin-review table, *J Clin Med* 2021;10:1039);
**≈ −0.5** (fresh human red cells per tetramer, *Front Physiol*
2024;15:1469496); **−0.56** for *stripped* human HbA in dilute
solution (J Exp Biol 2013;216:2340, citing Weber 1992) — a
different preparation, lacking the red cell's 2,3-BPG and
chloride environment; and a cross-species air-breathing range of
**−0.35 to −0.5** (J Appl Physiol 2017;123:1240, citing Lapennas
1986). The engine's dissociation curve is a whole-blood curve,
so the whole-blood physiological value −0.48 is the applicable
one; the parameter stores the cited signed figure and says so,
with the spread recorded in its note. One new parameter
(`bohr_coefficient_logp50_per_ph`, cited, S72) and one new
source (S72) were appended. Library totals after M52:
**138 parameters, 72 sources, 19 perturbation cases** (status
counts 85 cited / 34 calibrated / 19 verify-flagged).

## 2. The anchored construction

    P50_effective = P50_rest × 10^( coefficient × (pH − pH_rest) )

with `coefficient` = −0.48 (S72) and `pH_rest` = the engine's own
resting pH, computed in `Model::from_params` by exactly the
operations `arterial_ph()` performs at the resting state
(7.3893; the resting readout prints pH 7.39). At the resting
state the exponent is therefore zero and the multiplier exactly
1.0 — not approximately: a fresh engine's `arterial_ph()` equals
`ph_rest` bit-for-bit and its effective P50 equals the resting
P50 bit-for-bit, asserted in the test suite
(`bohr_anchor_is_exact_at_the_resting_ph`). Every M47/M51
resting readout and hash is preserved by construction, and §5
shows it in measurement.

**One curve position, everywhere oxygen is computed.** The
engine's oxygen side now routes through a single accessor,
`Engine::effective_p50_mmhg()`, used by: end-capillary loading
(alveolar PO₂ → content), the Berggren mixing inversion (mixed
content → arterial PO₂, by bisection), arterial saturation, and
the chemoreflex sensor's sensed PaO₂. Loading and inversion use
the *same* effective P50 at a state, or the inversion would be
inconsistent with the loading that produced the content; the
test `bohr_loading_and_inversion_use_the_same_effective_p50`
proves the identity (content at a PO₂ on the shifted curve
inverts back to that PO₂ within 1e-6 mm Hg at pH 7.16 / 7.389 /
7.61) and proves the mismatched pairing is detectable (reading
shifted content on the unshifted curve is off by > 1 mm Hg at
the arm states), so the consistency is a real proof, not a
tautology. The shift is engaged wherever the M47 oxygen algebra
runs: the resting readout, the shunt / metabolic / haemorrhage
arms, the case RespReadouts, and the `effective_p50` query.

**No new state, no path into the circulation.** Arterial pH is
a pure function of the PaCO₂ state the respiratory module
already carries, so the Bohr shift adds no state variable, no
derivative, and no route into the circulation integrator: the
circulation trace hash cannot move through it, and does not
(§5). A scenario event, `SetBohrShift`, disables the shift —
restoring the M47 fixed curve exactly — for the A/B arms,
following M51's `SetHypoxicDrive` instrument pattern. The shift
is live by default in every shipped protocol.

## 3. Arm (a): hypoventilation, acidosis — prediction before measurement

The M47 hypoventilation arm (rate held at 6 /min, chemoreflex
suspended by the override) re-run with the shift live. The CO₂
store settles at the same state as M47 measured (PaCO₂ 81.41,
pH 7.160) — the override suspends every path by which the shift
could reach the store. Predictions from `work/m52/predict.py`
at that measured state, before the engine arm was run:

| quantity (at PaCO₂ 81.41, pH 7.1598) | unshifted (M47 curve) | shifted (predicted) |
|---|---|---|
| effective P50 | 26.60 mm Hg | **34.28 mm Hg (×1.289)** |
| end-capillary content CcO₂ | 17.50 mL/dL | **15.32 mL/dL** |
| arterial content CaO₂ | 17.26 mL/dL | **15.18 mL/dL** |
| SaO₂ (at the arm's PaO₂) | 0.852 | **0.748** |
| PaO₂ (Berggren inversion) | 50.85 mm Hg | **51.31 mm Hg** |
| DO₂ (at the arm's flow) | 727 mL/min | **639 mL/min** |

The solver's unshifted PaO₂ (50.85) reproduces M47's engine
measurement exactly, validating the solver against the engine
before it is trusted with the shifted prediction. The two
textbook directions, kept separate because the arm mixes them:
at fixed PaO₂ the saturation falls by 0.113 (loading side); at
fixed content the PO₂ rises by +14.25 mm Hg (unloading side).
The arm's net PaO₂ barely moves (+0.46 predicted) because the
end-capillary content falls almost as much as the PO₂ needed
for a given content rises.

**Measured (post-M52 validate):** PaCO₂ 81.4, pH 7.160,
P50eff 34.28, PaO₂ 51.3, SaO₂ 0.748, CaO₂ 15.2, DO₂ 639 — the
prediction table at print precision. The arm **gates** (new
case `hypoventilation_bohr`, bands set around the predictions):
CaO₂ ∈ [14.5, 15.9], SaO₂ ∈ [0.71, 0.79], PaO₂ ∈ [48.0, 54.5],
DO₂ ∈ [600, 680] — all PASS; the curve position itself
(P50eff ∈ [33.5, 35.0], measured 34.28) is asserted in the test
suite. The shift-
disabled twin (`HypoventilationPure`) reproduces the M47
picture exactly (PaO₂ 50.9 printed, CaO₂ 17.30, DO₂ 727, P50eff
26.60) and passes both the new `hypoventilation_bohr_pure` case
and the legacy `hypoventilation_halved` case. The cross-run
assertions in validate: PaCO₂, pH, the respiratory trace hash
and the circulation hash are **identical** across the pair, and
the live-vs-disabled deltas land on the computed amounts —
ΔCaO₂ ≈ 2.1 (band [1.5, 2.8]), ΔSaO₂ ≈ 0.104 ([0.07, 0.14]),
ΔDO₂ ≈ 88 ([60, 120]) — all PASS. The test suite additionally
proves delivery moved *only* through content: the two runs
share their final-window cardiac output bit-for-bit, and the
DO₂ delta equals the content delta × that shared flow to 1e-6.

## 4. Arm (b): hyperventilation, alkalosis — the left shift

A dedicated hyperventilation arm (rate held at 24 /min,
alveolar ventilation doubled) was chosen over re-using the
coupled shunt: the shunt's pH excursion is only +0.007, an
effect too small to gate, whereas this arm drives pH to ≈ 7.61.
Predictions at the computed steady state (PaCO₂ 20.55 by the
S51/S66 alveolar relation at the doubled ventilation; pH 7.609
by the model's acute acid–base algebra):

| quantity | unshifted | shifted (predicted) |
|---|---|---|
| effective P50 | 26.60 mm Hg | **20.87 mm Hg (×0.785)** |
| end-capillary content CcO₂ | 20.09 mL/dL | **20.23 mL/dL** |
| arterial content CaO₂ | 19.97 mL/dL | **20.11 mL/dL** |
| SaO₂ | 0.978 | **0.986** |
| PaO₂ | 108.87 mm Hg | **102.06 mm Hg** |
| DO₂ | 841 mL/min | **847 mL/min** |

At fixed content the left shift puts the same oxygen at a PO₂
**18.9 mm Hg lower** — the unloading penalty, the mirror of arm
(a)'s loading penalty; at fixed PaO₂ the saturation rises by
0.010. **Measured:** PaCO₂ 20.6, pH 7.608, P50eff 20.89,
PaO₂ 102.0, SaO₂ 0.986, CaO₂ 20.15, DO₂ 847. The arm **gates**
(case `hyperventilation_alkalosis`): PaCO₂ ∈ [19, 22],
pH ∈ [7.55, 7.66], CaO₂ ∈ [19.85, 20.35], SaO₂ ∈ [0.981, 0.991],
PaO₂ ∈ [98.5, 105.5] — all PASS, and P50eff ∈ [20.3, 21.5]
(measured 20.89) is asserted in the test suite; the disabled
twin passes `hyperventilation_bohr_pure`. Cross-run
assertions (identical PaCO₂ / pH / both hashes): ΔCaO₂ ≈ +0.14
([0.05, 0.30]), ΔSaO₂ ≈ +0.008 ([0.004, 0.013]), and PaO₂
**falls** by ≈ 6.8 mm Hg with the shift live ([3, 10]) — the
left-shift signature at the arm's content — all PASS.

**The physiological point, plainly.** In acidosis the right
shift costs the lung content (arm (a): −2.1 mL/dL, −88 mL/min
of delivery at unchanged flow) and buys easier unloading at the
tissues; in alkalosis the left shift buys a little content
(+0.14 mL/dL) and charges for it at the tissues. Neither
direction creates or destroys oxygen: consumption, production
and flow are untouched by the mechanism, and every delivery
change above is the content term alone, in the computed amount.

**Where else the shift engages.** In the M51 coupled shunt the
equilibrium pH sits at 7.396 (ΔpH +0.007), so the effect is
small by arithmetic, not by exemption: the independent coupled
solver (`work/m52/predict_coupled.py`) predicted PaO₂
61.55 → 61.25 and VE 6.140 → 6.142 with the shift live; the
engine measured PaO₂ 61.3 and VE 6.13 (pre-M52: 61.54 / 6.13) —
inside all legacy and coupled bands, no case changed. In the
metabolic arm (pH 7.373, P50eff 27.09) PaO₂ moved 82.8 → 83.3,
inside its legacy bands. In the haemorrhage arms the pH sits
within ~0.001 of rest and the readouts are unchanged at print
precision (CaO₂ 19.03, DO₂ 690 unarmed / 691 feedback-armed).

## 5. Hash accounting — what holds, what moves, and why

| trace | pre-M52 | post-M52 | verdict |
|---|---|---|---|
| resting circulation (all cases) | `0x6369b10e9a71c872` | `0x6369b10e9a71c872` | **holds, bit-identical** |
| resting respiratory readouts | PaO₂ 91.24, SaO₂ 0.965, CaO₂ 19.66, DO₂ 828 | identical | **hold** (anchor, §2) |
| pure shunt resp (M47 picture) | `0x52d94cb3aa3b1755` | `0x52d94cb3aa3b1755` | **holds** — its PaCO₂ never leaves rest, so pH = pH_rest and the multiplier is exactly 1 on every tick |
| hypoventilation resp (live and disabled) | `0xecd45b6defcdefbb` | `0xecd45b6defcdefbb` | **holds** — the override suspends the sensor path; the shift reaches only readouts, never the hashed state |
| hyperventilation resp (live and disabled) | — (new arm) | `0x11e8dea7c599df9c` (both forms) | new; identical across the A/B pair for the same reason |
| coupled shunt resp | `0x086de28caccca717` | `0x706b1b92daa2fda4` | **moves, as expected**: the shift is live inside the chemoreflex sensor (sensed PaO₂), the arm's protocol now includes it; equilibrium values stay inside every band (§4) |
| metabolic resp | `0x50630334f28e97a3` | `0xd726fb354bf79f48` | **moves, as expected**: same sensor reason (pH 7.373, P50eff 27.09) |
| haemorrhage resp (unarmed) | `0xbfb2cafc36cfe506` | `0x4fd5743b78a8a847` | **moves, as expected**: same sensor reason at microscopic size; readouts unchanged at print precision (PaO₂ 89.75 → 89.74 on the gated line), and the standard-endpoint circulation hash `0xbc683bf2721147ae` holds. The feedback-armed arm's resp hash is not a pinned quantity in either milestone (validate does not print it); its gates hold — DO₂ 691.11 → 691.12, standard-window HR 115.2 → 115.1, both inside their bands |
| every circulation trace hash | — | — | **none moves**: the shift has no path into the circulation integrator (§2) |

The validate diff in full: 21 lines changed, 56 added, every
one inside the respiratory sections — the Bohr anchor line, the
hypoventilation arm's shifted gated line and readout, the
coupled shunt's oxygen lines (PaO₂ 61.54 → 61.26, A–a
40.00 → 40.29, PaCO₂ 40.24 → 40.23), the metabolic arm's
last-digit equilibrium moves (VE 11.47 → 11.46,
PaCO₂ 43.00 → 43.01), the haemorrhage arms' last-digit moves
above, and the M52 A/B sections entire. Everything from the
transcapillary-refill section onward — renal, hormonal, every
other case and arm — is byte-identical to the pre-M52 baseline,
as is every resting line.

## 6. Non-regression

- **Physiology validate: ALL HARD GATES PASS** (all M47/M51
  gates, resting lines and hashes unchanged; the only edited
  pre-existing lines are the oxygen readouts of the arms whose
  protocols now include the shift, each accounted in §5).
- **Cargo tests: 34 passed / 0 failed** (30 pre-existing + 4 new
  Milestone 52: anchor exactness, loading/inversion consistency,
  and the two A/B arms at identical states).
- **Theatre: cargo tests green; run-all 25 traces, 0 expectation
  failures, all 25 debriefs byte-identical** to the pre-M52 md5
  set (which itself equals the pre-M51 set).
- **Case checker: 10,298 PASS / 0 FAIL** — the pre-milestone
  count, exactly.
- **README checker: ALL CHECKS PASS (65 PASS lines)** (README
  figures updated to the new computed counts: 138 parameters,
  72 sources, 85 cited / 34 calibrated / 19 verify-flagged,
  19 perturbation cases; M52 row added to the milestone index
  and file index).
- **Full matrix: `tools/assembly_check_all.py` ALL GATED CHECKS
  PASS; `tools/verify_web.js` ALL CHECKS PASS; native verify
  99 PASS / 0 FAIL data assertions** (via readme_check R9;
  headless-GPU exit tolerated as before).

## 7. Honest limits — and what the module still cannot do

This is a **fixed-coefficient** Bohr model, and its limits are
named, not implied away:

- **No temperature term.** Fever and hypothermia shift the
  curve independently of pH (the temperature coefficient is of
  comparable textbook standing); the engine has no temperature
  state, so no term was added. The consulted sources support
  naming this as a real, separate effect (S72's coefficient is
  stated at 37 °C).
- **No 2,3-BPG state.** Chronic hypoxia and anaemia raise
  red-cell 2,3-BPG over hours-to-days and right-shift the curve
  independently of pH; the stripped-vs-whole-blood spread in §1
  (−0.56 vs −0.48) is partly this chemistry. The engine carries
  no BPG state and no chronic timescale, so the adaptation is
  absent, not approximated.
- **One lumped arterial pH.** End-capillary blood is evaluated
  at the arterial pH; the small alveolar-to-arterial pH
  difference across the capillary (CO₂ still leaving) is not
  modelled — the same lumping M47 already used for its gas
  algebra.
- **Acute acid–base only**, inherited from M47: the bicarbonate
  slope is the acute in-vivo buffering line; there is no renal
  compensation, so the arm pH values are acute values.

Beyond the shift, the respiratory module still cannot do what
M47/M51 already named: no regional V/Q distribution (one
compartment, one lumped shunt), no diffusion limitation, no
chronic adaptation of any kind, no oxygen-debt or
supply-dependent consumption accounting (VO₂ stays a scenario
input), no split central/peripheral chemoreflex time constants,
and no mechanical coupling of intrathoracic pressure back into
the circulation. The three M47 deferrals are closed; these are
absences of structure, not deferrals with a design waiting.

## 8. Next steps

1. **Temperature and 2,3-BPG** are the two named curve-position
   effects now outstanding; either needs its own state
   (temperature; a slow BPG integrator) and its own cited
   coefficient, and either would be anchored the same way —
   exactly zero at the resting equilibrium.
2. The respiratory module's remaining structural absence with a
   clinical consumer waiting is **regional V/Q**: case work
   (Case #6's embolism) currently reads the lumped shunt; a
   two-compartment V/Q split is the natural next module
   milestone, gated like this one.
3. Nothing here changes any case, theatre procedure, or web
   surface; no follow-up repair is owed by this milestone.
