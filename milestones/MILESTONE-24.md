# Milestone 24 — Physiology: venous return made first-class; the −1,500 mL "decompensation" resolved as a sampling artifact, and the scenario-input side built

Status: COMPLETE (local). Route taken: **route (2) of the brief** — on the
evidence below, the −1,500 mL decompensation is the transient nadir of a
60-second bleed sampled 30–60 s after the bleed ends, before the cited
compensation mechanisms have run; on presentation timescales the untreated
model recovers to a compensated, class-coherent shock picture, and the ATLS
classes themselves presume treatment has begun. So this milestone (A) makes
the Guyton venous-return formulation a computed, reported, and gated part of
the engine — it was always implicit in the circuit; it is now explicit —
and (B) implements the scenario-input side: a 60-minute haemorrhage-course
runner with an untreated arm and an ATLS-bolus arm. **No new model
parameter was added and no existing parameter, gain, bound, or dynamic was
changed**: every trace hash from Milestone 21 is reproduced bit-identically
(§8), Theatre debriefs are byte-identical, and the case checker needed no
re-recording. The precision law is followed throughout: new sources are
S17–S22, entered in `physiology/parameters.json` from texts consulted
in-session; every number below is measured output of the shipped code.

---

## 1. The question Milestone 21 left

Milestone 21 §A5 proved that at −1,500 mL the ventricles are preload-starved
(SV 7.6 mL, CVP 0.91 mmHg) and contractility saturates uselessly; it named
the binding omission as "stressed volume / venous return beyond the cited
630 mL recruitment + refill" and queued this milestone to model venous
return properly. Two hypotheses were open:

- **H1 (missing mechanism):** the circuit lacks return dynamics that real
  physiology has, and adding them (from sources) repairs the −1,500 mL
  picture inside the standard window.
- **H2 (wrong question):** the standard window samples a transient the
  sources never describe; the ATLS class table is a *presentation* table,
  and the honest gap is scenario inputs (resuscitation) and time horizon,
  not mechanism.

The milestone was briefed to follow the evidence. The evidence is H2, with
one genuine H1 component: the return formulation existed only implicitly,
so nothing in the product could state, check, or teach it. §2 makes it
explicit; §3–§5 carry the proof.

## 2. The formulation (now computed by the engine)

Guyton's framework (S17, Henderson et al. 2010; S18 for the canonical
normal values): venous return is driven by the gradient between the mean
systemic filling pressure and right atrial pressure, against the resistance
to venous return,

```
VR = (MSFP − RAP) / RVR ,        CO = VR at steady state,
```

where MSFP is the pressure the systemic circuit equilibrates to at zero
flow, set by the **stressed volume** (volume above the unstressed volumes)
and the total compliance. The intersection of this return curve with the
cardiac function curve — here, the curve the time-varying-elastance
ventricles imply — is the operating point. The engine now computes, from
its own state, at any instant:

- **Systemic stressed volume** (mL):
  `Σ (Vᵢ − Vuᵢ)` over SA/SC/SV, with the venous unstressed volume reduced
  by the venomotor recruited volume exactly as `evaluate()` applies it.
- **MSFP** (mmHg): stressed volume / systemic compliance
  `C_sys = C_sa + C_sc + C_sv = 118.00 mL/mmHg` — an identity in this
  circuit, because every systemic vessel is linear (`P = (V − Vu)/C`).
- **MCFP** (mmHg): the whole-circuit mean circulatory filling pressure by
  Guyton's own construction (S17, S21): redistribute the circuit's total
  volume over all eight compartments — ventricles on their S1 diastolic
  curves, vessels linear — until all pressures equalise (bisection,
  deterministic, fixed iteration count). This is the stop-flow
  equilibration pressure Drees & Rothe measured by fibrillation (S21).
- **RAP proxy** (mmHg): the model has no atrium. The pressure the veins
  actually drain against is the RV pressure while the tricuspid valve is
  open, so the proxy is the **flow-weighted mean RV pressure during
  tricuspid inflow**, accumulated per beat. It is a different point of the
  lumped path from the existing `cvp` output (the venous *reservoir*
  pressure, upstream of the venous outflow resistance and the valve) and
  the two are now reported side by side; the resting values (CVP 4.38,
  RAP 1.55) bracket the path exactly as anatomy says they should.
- **RVR, two ways.** Empirical: `(MSFP − RAP) / CO` at the operating
  point. Formula: the series-circuit compliance weighting
  `RVR = Σ Rₖ·(compliance upstream of Rₖ)/C_sys` at baseline resistances,
  with one correction Guyton's steady-flow derivation does not need but a
  pulsatile circuit does: the venous outflow segment's flow is
  intermittent (diastole only), so its mean gradient is its resistance law
  at the *flow-weighted moments* of inflow,
  `B·⟨q³⟩/⟨q⟩ + lin·⟨q²⟩/⟨q⟩`, divided by mean flow — not the law at mean
  flow. (Measured consequence of omitting the correction: the identity
  misses by 27.1%; with it, 6.1% — §3. The correction is derived from the
  model's own valve law in `engine.rs`, not fitted.)

Nothing in this section feeds back into the integration: the formulation
is a read-out of the existing dynamics, which is precisely the point —
the circuit already *was* a Guyton system; it now says so, in numbers
that can be gated.

### Parameters

**None added.** The formulation is computed from parameters already in
the file. What was added to `parameters.json`:

- Sources **S17–S22** (below).
- One validation range: `right_atrial_pressure_proxy` ∈ [1, 7] mmHg,
  gated, source S3 (whose locator carries the right-atrial range RA 1–7;
  S4's CVP range continues to gate the reservoir pressure separately).
- One perturbation case, `hemorrhage_1500_course` (§5), with four hard
  expectations and three soft lines whose interpretations are written
  into the case text itself.
- An appended **MILESTONE 24 RESOLUTION** on the `hemorrhage_1500`
  heart-rate expectation (append-only, per the file's discipline): the
  line stays soft, its window-relativity now measured.

| Source | What it carries here |
|---|---|
| S17 Henderson et al., Crit Care 2010 (full text, PMC) | The framework: MCFP set by stressed volume + compliance; VR = (MCFP − Pra)/RVR; cardiac/venous-return curve intersection; human measurements support Guyton's values |
| S18 LITFL "Venous Return" (secondary, status recorded) | Canonical normals as stated: MSFP ~7 mmHg; veins hold ~65% of blood volume |
| S19 Boron & Boulpaep, Medical Physiology 3e, "Response to Hemorrhage" (chapter read in full) | The course claim (§4); ≥30% loss = hypovolaemic shock (systolic usually <90, MAP <70); "increased sympathetic tone increases myocardial contractility but can increase stroke volume only after venous return also improves"; venoconstriction also *decreases venous compliance* (real, unquantified in the source — §7); refill ~75% of shed volume within an hour |
| S20 ATLS 10th ed. initial resuscitation (+ FPN response summary, status recorded) | The treated arm's shape: 1 L isotonic crystalloid bolus in adults; response classes — rapid (<10–20% loss), **transient (20–40%: improves, then deteriorates without blood/ongoing replacement)**, none (>40%); early blood products in Class III/IV |
| S21 Drees & Rothe, Circ Res 1974 (abstract) | Independent corroboration of the recruitment scale: reflexes intact, 17 mL/kg loss needed to bring PMC 10.7 → 4 mmHg vs 8 mL/kg blocked — active compensation ≈ 9 mL/kg ≈ 630 mL at 70 kg, matching S13's cited capacity from a second lineage; <half of first-5-min compensation from reflex venoconstriction |
| S22 Greenway, J Physiol 1974 (abstract, PMC) | The lumped venomotor response is predominantly splanchnic in the experimental record (62% of a 15% loss mobilised splanchnically) — evidence that one lumped venous compartment is the right granularity here; no splanchnic split is indicated |

## 3. Resting validation of the formulation

Measured at the resting case's end state (all values shipped-code output):

| Quantity | Measured | Reference | Verdict |
|---|---|---|---|
| MSFP | **6.29 mmHg** | ~7 mmHg (S17/S18) | PASS — hard gate, project tolerance band [5, 9] mmHg (disclosed as a tolerance, not a sourced band) |
| MCFP | 6.05 mmHg | stop-flow construction (S17/S21) | reported |
| RAP proxy | 1.55 mmHg | RA 1–7 (S3) | PASS — gated via the new validation range |
| CVP (reservoir) | 4.38 mmHg | 2–6 (S4) | PASS (pre-existing gate) |
| Systemic stressed volume | 742.1 mL | — | reported; whole-circuit stressed ≈ 1,120 mL ≈ 22% of the 5,000 mL total, inside the ~20–30% stressed fraction the consulted reviews state |
| RVR empirical | 0.0675 mmHg·s/mL = 1.125 mmHg·min/L | — | — |
| RVR formula | 0.0719 mmHg·s/mL = 1.198 mmHg·min/L | — | — |
| **RVR agreement** | **6.1%** | engineering identity criterion < 15% | **PASS — hard gate** (labelled in the harness as what it is: an engineering identity, MILESTONE-24) |

Both RVR values sit in the class the canonical construction implies
(gradient ≈ 5 mmHg driving ≈ 5 L/min ⇒ ≈ 1 mmHg·min/L). The resting
operating point is therefore Guyton-coherent in every quantity the
framework names — the return curve, the filling pressure, and the
resistance are the model's own numbers, not annotations.

A cross-check against S21's preparation, reported with its caveats (dog,
anaesthetised, ~20% volume steps): Drees & Rothe's reflex-intact control
PMC was 10.7 mmHg, ganglion-blocked 7.8 mmHg. The model's resting MSFP
(6.29) sits below both; its venomotor state rests at its operating point,
not at a constricted extreme, and no parameter was moved to chase the
dog preparation. What S21 corroborates — and what this milestone relies
on — is the *compensation scale* (≈630 mL), from an independent lineage.

Guyton end states for the other standard cases (reported, not gated —
the identity is a steady-state statement and two of these windows are
not steady):

| Case (post window) | Stressed (mL) | MSFP | MCFP | RVR emp. vs formula |
|---|---|---|---|
| −750 mL | 613.6 | 5.20 | 4.21 | 0.0792 vs 0.0740 (7.0%) |
| +1,000 mL infusion | 1,148.3 | 9.73 | 10.67 | 0.0746 vs 0.0841 (11.3%) |
| −1,500 mL (nadir window) | 267.1 | 2.26 | 1.49 | 0.1230 vs 0.0788 (56.2% — window MAP drift 22.7%; the formula is the baseline-resistance structural value and the empirical value carries the engaged reflex resistance; reported as the non-steady exception it is) |

Note the −750 row: after a 15% loss, recruitment + in-window refill hold
MSFP at 83% of its resting value (5.20 vs 6.29). That is the Guyton-space
statement of why the −750 mL hard gates pass.

## 4. The proof: the nadir is a sampling artifact

The standard protocol's post window is 30–60 s after the bleed ends. The
bleed itself lasts 60 s. The venomotor effector's cited time constant is
60 s (S13): at the moment the standard window closes, recruitment has had
**one** time constant since the bleed *began*, and the loss it answers was
still arriving for most of that time. The new course runner
(`cases::run_hemorrhage_1500_course`) keeps the identical protocol and
then simply watches for 60 minutes, sampling exact 30-second windows at
+1/+2/+5/+10/+20/+30/+60 min after the bleed ends. Its +1 min sample *is*
the standard post window (asserted in the test suite: MAP/HR agree to
<0.05 mmHg / <0.5 /min).

**Untreated arm** (measured):

| t after bleed end | HR | MAP | CO | SV | CVP | RAP | Stressed | MSFP | Recruited | Refill | Ino |
|---|---|---|---|---|---|---|---|---|---|---|---|
| +1 min | 144.0 | 29.6 | 1.10 | 7.6 | 0.91 | 0.01 | 267.1 | 2.26 | 517.8 | 150.2 | ×1.20 |
| +2 min | 144.0 | 47.7 | 1.65 | 11.5 | 1.45 | 0.13 | 374.5 | 3.17 | 588.7 | 214.2 | ×1.20 |
| +5 min | 144.0 | 59.7 | 2.32 | 16.1 | 2.12 | 0.27 | 483.3 | 4.10 | 627.9 | 315.3 | ×1.20 |
| +10 min | 143.4 | 64.5 | 2.84 | 19.8 | 2.69 | 0.39 | 562.6 | 4.77 | 630.0 | 418.6 | ×1.20 |
| +20 min | 115.0 | 67.5 | 3.25 | 28.2 | 2.92 | 0.52 | 592.6 | 5.02 | 571.2 | 538.0 | ×1.18 |
| +30 min | 108.2 | 68.2 | 3.35 | 31.0 | 3.00 | 0.58 | 609.3 | 5.16 | 496.6 | 635.9 | ×1.16 |
| +60 min | 93.8 | 69.7 | 3.60 | 38.4 | 3.24 | 0.74 | 635.8 | 5.39 | 336.8 | 858.9 | ×1.11 |

(Recruited falls after +10 min because refill is
restoring true volume and the reflex error — hence the recruitment it
drives — recedes: the two mechanisms hand over, in the open.)

Read against the sources:

- S19's course claim — "after its abrupt initial fall, arterial pressure
  tends to return to normal, although blood pressure falls irreversibly
  in some cases" — is exactly the branch this model is on: **hard gate
  `map_recovery_untreated` (+30 min MAP 68.2 > +2 min MAP 47.7): PASS.**
  The mechanism of recovery is the textbook's two lines of defence in
  order: reflex restoration first (recruitment completing over its cited
  τ, resistance and contractility saturated), then capillary exchange
  (refill, the slower line, dominant after +20 min).
- The settled untreated picture (+30 min: HR 108.2, MAP 68.2, systolic in
  the high-80s/low-90s region of the trace) is a compensated shock
  picture in S19's terms (MAP <70 = hypovolaemic shock at ≥30% loss) —
  not a normal patient and not a corpse: a patient who needs the blood
  they lost. The +30 min heart rate falls inside the ATLS Class II band
  [100, 120] — soft line, PASS — on the interpretation written into the
  case text: by then the model's own refill has replaced ~42% of the
  loss, so the *effective remaining deficit* (~860 mL) is Class II-sized.
  It is not claimed that a 1,500 mL patient "presents as Class II"; the
  +1/+2 min samples are the Class III-timescale reading, and there the
  model is in extremis, which for an *untreated* patient one minute
  after a one-minute 30% bleed is the physiology, not an error.
- 60-minute refill: **858.9 mL, inside S15's 500–1,000 mL envelope**
  (soft line, PASS — S15's figure is stated for moderate loss; applying
  it to 1,500 mL is an extrapolation, disclosed in the case text). S19's
  independent ~75%-within-an-hour statement would put the figure higher
  (~1,125 mL); the model sits between the two consulted claims, closer
  to the conservative one. No refill parameter was touched.

**Conclusion of the proof.** There is no missing return mechanism to add.
The recruitment capacity is corroborated by two independent lineages
(S13, S21); the return dynamics were already the circuit's dynamics; the
"decompensation" was the correct transient of a fast bleed read at a
timescale no consulted source describes. What was missing — and is now
built — is (a) the formulation as a first-class, gated read-out, and
(b) the scenario side: time horizon and treatment as inputs.

## 5. The scenario-input side: the ATLS bolus arm

Same course, treated arm: at the bleed end, the ATLS initial bolus —
**1,000 mL isotonic crystalloid over 60 s** (S20) — through the engine's
existing external-flow input (the same fluid path as the validated
infusion case; no new mechanism).

**Treated arm** (measured):

| t | HR | MAP | CO | SV | CVP | RAP | Stressed | MSFP | Recruited | Refill | Ino |
|---|---|---|---|---|---|---|---|---|---|---|---|
| +1 min | 106.6 | 69.4 | 3.43 | 36.0 | 3.62 | 0.84 | 801.5 | 6.79 | 386.6 | 88.1 | ×1.02 |
| +2 min | 76.0 | 71.6 | 3.94 | 51.9 | 3.67 | 1.07 | 682.2 | 5.78 | 206.4 | 89.5 | ×1.05 |
| +5 min | 80.3 | 71.1 | 3.85 | 47.9 | 3.57 | 0.98 | 699.7 | 5.93 | 184.5 | 98.9 | ×1.06 |
| +10 min | 79.5 | 71.2 | 3.87 | 48.6 | 3.60 | 0.99 | 674.3 | 5.71 | 175.4 | 114.4 | ×1.05 |
| +20 min | 78.1 | 71.4 | 3.89 | 49.9 | 3.65 | 1.03 | 708.6 | 6.01 | 159.1 | 142.9 | ×1.05 |
| +30 min | 76.9 | 71.5 | 3.92 | 51.0 | 3.69 | 1.06 | 670.5 | 5.68 | 144.6 | 168.5 | ×1.05 |
| +60 min | 73.9 | 71.9 | 3.98 | 53.8 | 3.80 | 1.14 | 719.2 | 6.10 | 110.4 | 231.2 | ×1.03 |

Hard expectations (all PASS): at +10 min the treated arm beats the
untreated arm on MAP (71.2 vs 64.5), on CO (3.87 vs 2.84), and relieves
heart rate (79.5 vs 143.4) — the mechanism-level content of S2's
volume–pressure–flow relation and S19's tachycardia-tracks-deficit
statement, in comparative form.

The ATLS response classification the model produces is **rapid and
sustained**, where S20's table leads one to expect a *transient* response
at 20–40% loss (improve, then deteriorate). The divergence is reported,
not smoothed over, and it has two named, structural reasons, both
disclosed in the case text before the run: (1) ATLS's transient response
is defined against **ongoing loss or inadequate replacement** — this
scenario's bleeding is controlled at t = 180 s by construction, so the
deterioration driver is absent; (2) the bolus **cannot redistribute** —
the engine has no interstitial compartment for crystalloid to leave into
beyond the bounded lumped escape, so in-model the litre stays
intravascular (and the lumped refill signal, referenced to the pre-bleed
capillary pressure, keeps trickling inward: treated refill +231 mL by
+60 min). Consequently the soft line `hr_treated_10min` ∈ Class III band
[120, 140] **SOFT-FAILS** (measured 79.5): the model's treated patient is
less tachycardic than the source presentation for a Class III patient
who has had crystalloid but no blood. That is a statement about the
missing interstitial/renal handling (§7), carried as a soft line with
its mechanism — the same discipline as every prior soft line in this
module. Blood products as a scenario input are not modelled (no
oxygen-carrying or oncotic distinction exists in the engine); S20's
"early blood in Class III/IV" is recorded here as the named next
scenario input, not silently approximated by more crystalloid.

## 6. Standard cases: before / after

Nothing moved. The formulation is read-only with respect to the
dynamics, so Milestone 21's table stands verbatim; the new read-outs
append to it:

| Case | HR | MAP | CO | Trace hash | vs M21 |
|---|---|---|---|---|---|
| Resting | 63.3 | 73.08 | 4.21 | `0xacbf44852f6a0382` | identical |
| −750 mL post | 102.1 | 68.9 | 3.46 | `0xedbe3d7a1d240880` | identical — Class II HR hard gate still PASS |
| +1,000 mL post | — | — | — | `0x3f673156038bf9ee` | identical |
| −1,500 mL post | 144.0 | 29.6 | 1.10 | `0x275b8d66afad77bb` | identical — now *interpreted* by §4 |
| Refill obs. +30 min | — | — | — | `0xf151bddc9bfae781` | identical — 187.6 mL (25.0%) PASS |

Course trace hashes (new): untreated `0xadc0e3cc23242721`, treated
`0x773cc379712abfd4`. Determinism check: IDENTICAL. Volume conservation:
≤ 2.9e-9 mL error in both course arms over 3.7 simulated hours total.

## 7. Caveats: retired and standing

**Retired by this milestone:**

- *"The binding omission is stressed volume / venous return beyond the
  cited 630 mL recruitment + refill"* (M21 §A5) — retired as stated. The
  return side is not omitted; it is now formulated, reported, and gated
  (§2–§3), and the behaviour it was blamed for is explained by sampling
  timescale (§4). What remains genuinely unmodelled on the volume side
  is listed below, precisely.
- *The −1,500 mL heart-rate soft line as an unexplained miss* — the line
  stays soft (an ATLS presentation band cannot gate a 60-second
  post-bleed transient), but it is no longer unexplained: the MILESTONE
  24 RESOLUTION appended to its source text in `parameters.json` carries
  the measured course.

**Standing, unchanged in substance:**

- **Renal excretion unmodelled** — now the binding volume-side omission:
  it is one of the two structural reasons the treated arm cannot show an
  ATLS transient response, and it caps every multi-hour claim this
  engine makes. Named companion work: a minimal interstitial state
  (crystalloid redistribution + a real Starling compartment) and renal
  excretion, which together unlock honest multi-hour courses and urine
  output as a case finding.
- **Infusion magnitudes unvalidated** (standing since Milestone 8): the
  bolus arm validates direction and comparative effect, not magnitude —
  no consulted source in any milestone session states a numeric MAP/CO
  response to a 1 L bolus in a form this engine can be gated against.
- **Venoconstriction's compliance effect** (S19: constriction "decreases
  both the capacity and the compliance of the large veins") — real in
  the source, unquantified there; the engine models the capacity
  (unstressed-volume) effect only. Named omission, no invented number.
- All reflex gains remain **verify-flagged placeholders** (M8/M18/M21
  disclosures stand); the −750 mL systolic soft miss (85.6 vs the
  90 mmHg edge whose bound was never read in a consulted source) is
  unchanged and still carried openly.
- The **review gate remains unmet**: no expert reviewers exist; content
  stays `dual-sourced-draft`, scores formative-only (system-wide
  statement, repeated here because the course case is new content under
  the same status).

## 8. Cross-module impact and checker matrix

Physiology dynamics are untouched, so nothing downstream moved:

- Theatre: `cargo test` 8/8; `run-all` re-ran all 5 traces;
  `tools/theatre_check.py` **131 checks, 0 failures**; debrief directory
  diffed against the pre-milestone (M21) set — **byte-identical, zero
  field diffs** (stronger than M18/M21, which each re-recorded fields).
- Cases: `tools/case_check.py` **ALL CHECKS PASS** — case 1's physiology
  link (resting trace hash) still matches, because the hash does.
- Assembly: `tools/assembly_check_all.py` **ALL GATED CHECKS PASS**.
- Web: `node tools/verify_web.js` **ALL CHECKS PASS** (web shell
  untouched this milestone).

Physiology itself: `validate` — **ALL HARD GATES PASS**, with exactly
three soft lines, all pre-disclosed with mechanisms (the inherited −750
systolic edge; the inherited −1,500 HR band, now explained; the new
treated-arm HR band, §5). `cargo test` **14/14** (12 prior + 2 new:
`guyton_quantities_close_at_rest`, `hemorrhage_course_recovers_
untreated_and_bolus_helps` — the latter also asserting the course's
+1 min sample equals the standard case's post window). `determinism`:
IDENTICAL. The Milestone 24 diagnostic probe is retained at
`physiology/examples/guyton_probe.rs`, rewritten over the shipped API so
it cannot drift from the validated paths.

Files changed: `physiology/src/engine.rs` (Guyton read-outs, RAP proxy,
beat flow moments — no integration change), `physiology/src/cases.rs`
(Guyton fields on outcomes; the course runner + evaluator),
`physiology/src/main.rs` (Guyton reporting, course section, `run course`
subcommand), `physiology/parameters.json` (S17–S22, RAP range, course
case, appended resolution), `physiology/tests/engine_tests.rs` (+2
tests), `physiology/examples/guyton_probe.rs` (new), this dossier.
Local only; no upload performed or implied.

## 9. Next steps

1. **Renal excretion + minimal interstitial state** — the named volume
   companion: unlocks crystalloid redistribution (the treated arm's
   missing physics), multi-hour courses, and urine output for the case
   workbench. Sources first, as always.
2. **Blood products as a scenario input** (S20's Class III/IV route) —
   requires an oncotic distinction the engine does not yet have; scope
   it with (1), not before.
3. The physiology line of the M21 next-steps list is otherwise as it
   stood: splanchnic split is now answered by evidence (S22 — not
   indicated); the reflex-gain identification problem remains the open
   methodological item for any future magnitude claims.
