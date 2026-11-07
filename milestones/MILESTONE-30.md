# Milestone 30 — Physiology: the hormonal volume axes (ADH + RAAS/aldosterone)

**Status: built and verified locally. Not uploaded (per-item approval stands).**

Milestones 24–26 built the volume arc: the Guyton venous-return
readout (M24), the renal excretion curve and the finite interstitial
reservoir (M25), and the oncotic state with the blood-product channel
(M26). Every one of those milestones carried the same standing caveat:
*the hormonal axes are absent* — the kidney excreted what the pressure
curve said, with no antidiuretic hormone to concentrate the urine and
no renin–angiotensin–aldosterone system to defend sodium. This
milestone closes that caveat. The engine now carries an extracellular
sodium/osmolality lump with an intracellular water buffer, an ADH axis
on the classic osmolality–secretion relation with a secondary volume
limb, and an aldosterone effect state that shifts the chronic
pressure-natriuresis curve in Guyton's formulation, on the cited
genomic timescale of hours.

Everything integrates with the existing arc rather than sitting beside
it: ADH acts on the M25 renal curve's output through the urine's
osmole load; aldosterone shifts the M25/M26 chronic natriuresis curve;
the sodium lump rides the M25 boundary-flux bookkeeping (intake,
urine, the event channel, the M26 product channel) and the M25
interstitial reservoir gains the intracellular lump as a second
exchange partner.

**Headline results.** All pre-existing hard gates hold (full matrix in
§5). The resting trajectory is undisturbed at print precision — the
hormonal states sit at their equilibrium-construction values at the
operating point — and the resting hour now additionally reports plasma
osmolality 286 mOsm/kg (cited band 275–295), plasma sodium 138 mmol/L
(135–145), urine osmolality 603 mOsm/kg, plasma ADH 1.75 pg/mL, all
inside their cited normals. The three new scenario arms each show
their axis in its own regime (§6): a 1 L water load drives ADH to
0.14 pg/mL and a ~10× diuresis; a 5× sodium load is fully excreted
within 24 h at a MAP cost of +0.5 mmHg because aldosterone suppression
carries the natriuresis; and the −1,500 mL haemorrhage course,
extended to 12 h, shows what the axes add — maximal antidiuresis and
complete sodium conservation — and, stated as plainly, what they do
not add on this horizon: the MAP recovery is M26's recovery, extended,
not a new one.

---

## 1. Formulation

All relations below are implemented in `physiology/src/engine.rs`;
every quantity is a parameter in `physiology/parameters.json` with its
source or its flag. New sources are S36–S50 (§3).

### 1.1 The sodium/osmolality lump

One new conserved state, `na_mmol`: total extracellular sodium
content. It is initialised by equilibrium construction — the M25
intake construction applied to sodium — as the cited resting
concentration (138 mmol/L, S48's band) times the resting
extracellular volume (plasma 2,750 mL + interstitial 11,000 mL from
the existing compartments):

    na_mmol(0) = 138 mmol/L × 13,750 mL = 1,897.5 mmol

Plasma sodium concentration is then a derived identity at every tick,
`[Na+] = na_mmol / V_ecf`, where `V_ecf` is the sum of the existing
plasma and interstitial volumes — so the concentration moves exactly
when content and water move apart, and for no other reason. Plasma
osmolality is derived from the concentration by the standard clinical
estimator's structure (S47: calculated osmolality = 2[Na+] + glucose
and urea terms; S47's own worked example puts the non-sodium terms at
≈10 mOsm/kg for normal glucose/BUN):

    Osm = 2·[Na+] + 10 mOsm/kg        ⇒   Osm(0) = 286 mOsm/kg

inside S47's cited normal band 275–295 mOsm/kg, and consistent with
S36's ~290 for plasma. Glucose and urea are not states; their
contribution is the constant term, named in the caveat ledger (§8).

Sodium fluxes ride the existing boundary bookkeeping, each at the
concentration of the fluid that carries it: intake enters at the
scenario's sodium intake rate; haemorrhage removes sodium at the
plasma concentration of the blood being lost, stage by stage with the
existing bleed staging; the event (crystalloid) channel carries its
cited sodium concentration (140 mmol/L nominal, S50's crystalloid
range 130–154); blood products carry sodium at the plasma fraction's
concentration (M26 channel); urine removes sodium at the renal
curve's excretion rate (§1.3). Starling filtration and the
intracellular exchange are internal water movements and carry no
sodium across the lump boundary — filtration within the ECF moves
sodium between plasma and interstitium, both inside the lump.

### 1.2 The intracellular buffer

One new state, `icf_ml`: intracellular water volume, initialised at
28,000 mL (S46: ICF 25–28 L of the ~42 L total body water). The lump's
solute content is fixed at construction (resting osmolality × resting
volume = 8,008 mOsm) — the lump buffers water, it does not gain or
lose solute, the standard lumped treatment. Water exchanges with the
interstitium down the osmotic gradient,

    Q_icf = k_icf · (Osm_icf − Osm_ecf)   [mL/s into the interstitium],

with the conductance `k_icf` CALIBRATED so a 1 L water load's
extracellular dilution equilibrates on the cited water-distribution
timescale (the load's osmolality nadir is an ECF transient, 267.6;
the whole-body value is back to 273.5 by +15 min and the distribution
is essentially complete within the hour — cf. S39's water-load
account). Because the flux enters the interstitial reservoir, the
M25 reservoir identity gains the ICF term exactly:
`V_isf + refill + (V_icf − 28,000) = 11,000 mL` at all times, and the
reservoir's pressure feedback now reads the net interstitial
deviation from both exchange partners. The M26 test that pins the
identity was amended to the three-term form, with the measured ICF
term (~+1.4 mL over 30 min after a −750 mL bleed) recorded in the
test's comment.

### 1.3 The ADH axis

Secretion: the classic osmolality relation is Robertson & Athar's
(S37), measured recumbent — plasma AVP rises linearly above an
osmotic threshold with slope 0.35 pg/mL per mOsm/kg:

    AVP_osm = max(0, 0.35 · (Osm − 281))

At the engine's resting osmolality this gives 1.75 pg/mL, inside
S49's cited span (0.5–5 pg/mL covers the full urine-osmolality
range) and S38's picture (threshold ~283 in children; maximal
antidiuresis from ~5 pg/mL). The volume limb is secondary and
thresholded, as the sources require (S36: a 5–10% volume fall is
needed for a comparable AVP rise; S38: ≥8% fall triggers, −25%
drives AVP to 20–30× normal): below an 8% MAP deficit against the
reflex setpoint it contributes nothing; from 8% to 25% deficit it
rises to a calibrated ceiling of +50 pg/mL. The plasma state relaxes
toward the secretion target with τ = 1,080 s (S36: AVP half-life
~18 min; S38 gives 5–10 min — the parameter is CALIBRATED inside the
300–1,600 s band the two sources span, disclosed in its note).

Action: AVP sets the kidney's concentrating state through the
AVP–urine-osmolality response curve (S39: urine osmolality spans
50–1,200 mOsm/kg; S49: the span is covered by AVP 0.5–5 pg/mL;
S36/S38 concur):

    Uosm_curve(A) = 50 + 1,150 · A² / (A² + 1.83²)   [mOsm/kg]

whose half-saturation (1.83 pg/mL, CALIBRATED) puts the resting point
at ~600 mOsm/kg, S39's resting value. Urine flow is then determined
by the solute load the urine must carry — S39's mechanism, stated in
his chapter: AVP moves water at nearly constant solute excretion.
The total urinary osmole excretion rate is the sodium limb's osmoles
plus a fixed non-sodium solute rate (urea and other solutes,
CALIBRATED so the resting osmole rate is ~0.6 mOsm/min):

    osmole_rate = 2·U_Na + 0.378 mOsm/min
    urine flow  = renal_mult_acute(MAP) · osmole_rate / Uosm_curve(ADH)

At rest this reduces exactly to the M25 baseline flow (the acute
pressure multiple is 1, the osmole rate over the curve value is the
calibrated resting flow), which is why the resting trajectory is
undisturbed. ADH therefore concentrates or dilutes the urine by
moving its water content against a solute load set by the pressure
curve and the sodium axis — the three systems share one urine, as
they should.

The urine osmolality READOUT is the osmole rate over the flow
whenever flow is above 0.5 mL/min — it equals the response curve's
value whenever the pressure multiple is 1, by construction. In
oliguria (flow < 0.5 mL/min) the readout reports the concentrating
state `Uosm_curve(ADH)` instead of the ratio, for a measured reason
(§7): as filtration collapses the constant-solute assumption fails,
and the raw ratio fabricates values above the cited 1,200 ceiling.
Every gated use of the readout sits above the threshold.

### 1.4 The RAAS/aldosterone axis

Renin and angiotensin are not separate states (named in §8); their
integrated effect is carried by one normalised aldosterone EFFECT
state, `aldo_state`, resting value 1.0. Its target is

    target = clamp(1 + 6·perf_err − 25·na_err, 0.25, 3.5)

where `perf_err` is the fractional renal perfusion (MAP) deficit
against the setpoint and `na_err` is the fractional sodium-CONTENT
excess over the resting content. The gains are VERIFY-flagged
engineering parameters; the floor and ceiling are VERIFY-flagged
(the floor reflects the cited profound suppression of the axis on
high salt intake, S43's subject; the ceiling the retention state of
volume depletion). The state approaches its target with
τ = 7,200 s — the genomic timescale the sources demand (S41:
aldosterone's sodium effect lags ~20–60 min, peaks at 2–4 h; S42:
plasma half-life ~20 min but effect onset ~45 min and peak at hours,
the action being genomic; S40: mineralocorticoid latency 10–30 min).
This is deliberately the slowest limb in the engine: on any horizon
under an hour the axis has barely moved, and the arms in §6 show it.

The sodium input is the CONTENT error, not the concentration error,
for a measured reason (§7): water follows sodium, so under an
isotonic load the concentration error saturates below 1% while the
content error reaches +21% — a concentration input cannot express
the suppression S43 describes. The content error is the lump's
expansion signal; the renin pathway's real inputs (renal perfusion,
macula-densa delivery, atrial stretch) all track the expanded state,
not the clamped concentration.

Effect: aldosterone shifts the chronic pressure-natriuresis curve
along the pressure axis — Guyton's formulation (S23: the hormonal
state is among the determinants that shift the renal function curve;
S43: suppression of the axis on high salt "greatly amplifies" the
effectiveness of pressure natriuresis):

    U_Na = U_Na0 · renal_mult(5 · (d − shift)),   shift = 25 · (aldo − 1) mmHg

The chronic curve is the M25 acute curve's shape with its pressure
axis compressed ×5 (CALIBRATED steepening, S43's amplification made
quantitative) and shifted by the aldosterone term (25 mmHg per unit
state, CALIBRATED against the declared target in §7). At rest
(aldo = 1) the shift vanishes and the resting excretion is the M25
value. Water excretion stays on the acute curve — a disclosed
asymmetry: the chronic curve in Guyton's account is a sodium curve,
and the water limb's chronic behaviour emerges here through the
osmole load (§1.3) rather than through a second shifted curve.

Pre-engagement (before the reflex setpoint exists), urine water and
sodium equal the current intake rates exactly — the M25 equilibrium
construction is preserved, which is what keeps the resting gates
bit-stable in kind.

### 1.5 New scenario plumbing

Two new events: `SetIntake { water_ml_min, sodium_mmol_min }`
(scenario intake control; deprivation and both loads are built from
it) and `SetWaterFlow { rate_ml_s }` — a dedicated solute-free water
channel with its own boundary integral in the volume identity. The
second channel exists because of a measured incident (§7): the first
water-load build routed the load through the crystalloid channel and
delivered 1 L of isotonic saline-equivalent. Pure water now has its
own channel, and the volume conservation identity closes over all
channels exactly (the validator's conservation lines still read
< 0.01 mL).

New trace outputs alongside the M26 hematocrit/oncotic readouts:
plasma osmolality, plasma sodium, plasma ADH, aldosterone state,
urine osmolality, urine sodium rate, ECF/ICF volumes, total body
water, cumulative urine sodium and sodium intake. The five new
states (sodium content, ICF volume, ADH, aldosterone state,
cumulative urine sodium) are folded into the trace hash after the
M26 protein states; the exact integrals (sodium intake, water
channel) are boundary terms, not folded, like M25's product integral.

---

## 2. What was deliberately not built

Named here so the ledger in §8 can be short: renin and angiotensin
II as separate states (subsumed into the aldosterone target — their
own kinetics are faster than the effector they drive and no arm
here could distinguish them); AVP's V1 pressor action (AVP here is
purely antidiuretic; the volume limb's secretion already encodes the
emergency, and a second pressor effector would double-count the
M21/M24 machinery); thirst (intake is a scenario input — and its
absence is not silent: §6.2 measures exactly what it costs);
insensible losses (absent, as they have been since M25; §6.1
measures the bound this puts on the deprivation arm).

---

## 3. Sources (S36–S50, consulted in-session)

- **S36** — Boron & Boulpaep, *Medical Physiology*, water-control
  chapter: plasma osmolality ~290 mOsm/kg; AVP osmotic threshold
  ~280; AVP half-life ~18 min; a 5–10% blood-volume fall is required
  for an AVP rise comparable to the osmotic drive.
- **S37** — Robertson & Athar, *J Clin Endocrinol Metab* 1976;
  42:613–620 (PMID 1262438): plasma AVP = 0.35 × (Osm − 281.0)
  pg/mL, recumbent — the secretion relation used verbatim.
- **S38** — Rudolph's *Pediatrics*, water-homeostasis chapter:
  osmotic threshold ~283 mOsm/kg; AVP maximum ~20 pg/mL at 320;
  volume falls ≥8% engage the volume limb, −25% drives AVP to
  20–30× normal; maximal antidiuresis from ~5 pg/mL; AVP half-life
  5–10 min.
- **S39** — Guyton & Hall, *Textbook of Medical Physiology*, ch. 28
  (kidney fluid control, full chapter): urine osmolality range
  50–1,200 (to 1,400) mOsm/kg; resting ~600; after 1 L of water,
  urine flow rises to ~6× normal within 45 min and urine osmolality
  falls 600 → ~100, solute excretion ~constant — the flow law's
  mechanism and the water arm's yardstick.
- **S40** — Ganong, *Review of Medical Physiology*, 23e:
  mineralocorticoid latency 10–30 min; reduced salt intake raises
  aldosterone with slowly developing falls in sodium excretion;
  water diuresis begins ~15 min, maximal ~40 min.
- **S41** — Sonnenblick, Cannon & Laragh, *J Clin Invest* 1961:
  aldosterone's sodium effect lags ~20–60 min, peaks at 2–4 h,
  total action ~6 h — the effect-state time constant's anchor.
- **S42** — Guyton & Hall ch. 77 (adrenal hormones): aldosterone
  plasma half-life ~20 min; genomic onset ~45 min, peak effect at
  hours.
- **S43** — Hall, Guyton & Mizelle 1990 (PMID 2220409): suppression
  of angiotensin II/aldosterone on high salt intake "greatly
  amplifies" the effectiveness of pressure natriuresis; inappropriate
  activation forces arterial pressure up to maintain sodium balance —
  the chronic curve's steepening and shift, and the sodium arm's
  yardstick.
- **S44** — Guyton & Hall ch. 19, long-term pressure control
  (carried by a flashcard reproduction — the weakest carrier in this
  set, used softly): raising salt AND water intake together ~6×
  raises MAP only ~6 mmHg with the renin system intact. The sodium
  arm's protocol (salt and water raised together) and its pressure
  regime come from here.
- **S45** — Mayo Clinic 24-h urine sodium reference: dietary sodium
  130–260 mmol/day; excretion ≈ intake at balance; population mean
  excretion ~159 mmol/day — the resting excretion/intake calibration
  range (0.111 mmol/min ≈ 160 mmol/day).
- **S46** — body-fluid compartments corpus: total body water ~42 L,
  ICF 25–28 L, ECF ~14 L.
- **S47** — osmolality corpus: normal plasma osmolality 275–295
  mOsm/kg; calculated osmolality = 2[Na+] + glucose/18 + BUN/2.8,
  worked example (Na 140, glucose 90, BUN 14) → 290, i.e. a
  non-sodium contribution of ≈10 mOsm/kg — the osmolality identity
  and its resting gate.
- **S48** — WikiLectures, plasma sodium: normal 137–144 mmol/L (the
  135–145 clinical range is used as the gate band; the resting
  construction value 138 sits inside both).
- **S49** — Brenner & Rector's *The Kidney*: plasma AVP 0.5–5 pg/mL
  spans the full urine-osmolality range — the response curve's span
  and the resting ADH gate.
- **S50** — crystalloid composition corpus: 0.9% NaCl 154 mmol/L,
  lactated Ringer's 130, Plasma-Lyte 140 — the event channel's
  sodium concentration and its cited band.

Dual-source check on the safety-relevant relations: the AVP
secretion relation (S37 primary; S36/S38 concur on threshold and
steepness), the urine-osmolality span (S39 + S49), the aldosterone
timescale (S41 + S42 + S40), the osmolality band (S47 + S36), the
sodium band (S48 + S47's worked example).

---

## 4. Parameter census

parameters.json: 80 → **104 parameters**, 35 → **50 sources**, 5 →
**9 perturbation cases**, 17 → **21 validation ranges**. All edits
were append-only insertions in the file's original formatting (the
M25 serializer law); the M30 additions are exactly the 24 parameters
whose notes open "Milestone 30", the 15 sources S36–S50, the 4 cases
and the 4 resting ranges. The file was never re-serialized.

The 24 new parameters: **7 cited** (osmolality non-sodium term 10
mOsm/kg [S47]; ADH osmotic threshold 281 [S37]; ADH osmotic slope
0.35 [S37]; ADH volume threshold 8% [S38/S36]; ADH volume full-scale
25% [S38]; urine osmolality floor 50 and ceiling 1,200 [S39]);
**13 calibrated** (resting sodium 138 mmol/L [S48 band]; ICF volume
28,000 mL [S46]; ICF exchange conductance; ADH volume ceiling
50 pg/mL; ADH τ 1,080 s [S36/S38 span]; response-curve
half-saturation 1.83 pg/mL [S39/S49 shape, resting point 600];
baseline sodium excretion and sodium intake 0.111 mmol/min [S45];
non-sodium osmole rate 0.378 mOsm/min; crystalloid sodium 140
[S50]; aldosterone τ 7,200 s [S41/S42]; curve shift 25 mmHg/unit
[§7]; chronic steepening ×5 [S43]); **4 verify-flagged**
(aldosterone perfusion gain 6, sodium-content gain 25, target floor
0.25, target ceiling 3.5 — the RAAS limb's gains have no cited
lumped values and are flagged rather than dressed as cited).

The 4 new resting validation ranges: plasma osmolality [275, 295]
(S47), plasma sodium [135, 145] (S48), urine osmolality [300, 900]
(S39's resting ~600 with a disclosed engineering tolerance),
plasma ADH [0.5, 5.0] (S49). All four PASS at rest (§5).

---

## 5. Gate matrix — before / after

`validate` exits 0: **ALL HARD GATES PASS**, before and after. The
resting post-window vitals are identical at print precision (HR 63.3,
BP 97.7/62.7, MAP 73.1, CO 4.21, SV 66.6, CVP 4.38, RAP proxy 1.55);
MSFP 6.29 mmHg; RVR empirical 0.0675 vs formula 0.0719 (6.1%).
Three in-band quantities moved, each by a named mechanism:

| Quantity | M26 (before) | M30 (after) | Reading |
|---|---|---|---|
| equilibrium urine | 1.01 mL/min | 1.03 mL/min | band [0.7, 1.4] both. The resting MAP sits +0.2 mmHg over the setpoint (pre-existing); the chronic curve's cited steepness now acts on that offset and raises sodium (hence osmole, hence water) excretion ~10% — Guyton's point, operating at rest. |
| boundary balance (engaged hour) | urine 60.4 vs intake 60.0 (net +0.4) | 61.6 vs 60.0 (net +1.6) | criterion \|net\| < 15 both; same mechanism as above. |
| net refill at +30 min (−750 mL) | 126.6 mL | 122.9 mL | band [112.5, 262.5] both; early antidiuresis retains slightly more urine-side water in the first 30 min. |
| steady-state drift | MAP 0.008% / CO 0.028% | MAP 0.003% / CO 0.011% | criterion < 1% both. |

Soft lines: the seven pre-existing disclosed soft-fails are the same
seven (ATLS window lines ×4, the 60-min refill envelope — now
408.0 mL against [500, 1,000], deepened by antidiuresis, mechanism in
§6.3 — bolus retention, whole-blood retention). No new soft-fail was
created; one M30 soft line (deprivation urine flow) PASSES on the
final formulation (§7). Trace hashes all moved (five new folded
states) — the full set is in §9. Determinism: IDENTICAL.
Tests: physiology 25/25 (20 pre-existing + 5 new), theatre 16/16.

---

## 6. The scenario arms

### 6.1 Water: load and deprivation (the ADH axis)

**Load** — 1,000 mL of solute-free water over 60 s at engagement,
paired control arm. The load lands in the ECF first: osmolality
nadirs at **267.6 mOsm/kg** ([Na+] 128.8) at load end, then the ICF
buffer shares it — 273.5 by +15 min, ICF volume peaking at 28,521 mL
(+521 mL of the litre parked intracellularly). ADH collapses on the
cited relation: 1.75 → 0.72 (+15 min) → **0.14 pg/mL at +45 min**.
Urine flow peaks at 12.2 mL/min instantaneous (peak 15-min interval
ratio **10.57×** the paired control) with urine osmolality at the
peak **55 mOsm/kg**, against the response curve's cited 50 floor.
Excess urine over control at 4 h: **678.7 mL**. Against S39: his 1 L
is oral (absorbed over tens of minutes) and peaks at ~6× within
45 min with urine osmolality falling to ~100; this arm is
intravenous over 60 s, so the excursion is faster and deeper, and
the gate band [3, 12] is set from the model's own response-curve
ceiling ratio (600/50) with the route difference disclosed in the
case text. The direction, the ADH timescale, the dilution floor and
the ~⅔-of-load excreted by 4 h are the cited physiology operating.

**Deprivation** — intake zeroed for 12 h. Every cited direction
fires: osmolality 286.0 → 287.9, ADH 1.75 → **2.41 pg/mL**,
aldosterone state → 1.40 (the content limb sensing the −34.5 mmol
sodium drift), urine sodium rate → 0.008 mmol/min (conservation
nearly complete), urine flow → **0.51 mL/min**, urine osmolality
606 → **754 mOsm/kg**. The excursion is small — and that is itself
the arm's finding, stated in the case text: this engine has no
insensible losses, so urine is the only water exit, and 12 h of
zero intake costs the model only ~0.5 L against a real body's
additional ~0.25–0.5 L/day of insensible loss. The arm demonstrates
the axis and bounds the missing term; it does not overclaim a
deprivation physiology the engine cannot yet represent.

### 6.2 Sodium load (the RAAS axis) — and the thirst finding

Protocol (S44's): sodium intake ×5 (0.555 mmol/min ≈ 800 mmol/day)
with water intake ×3 in parallel, 24 h — salt and water raised
together, as the cited experiments raised them. The axis answers on
its own timescale: aldosterone falls through 0.56 at 3 h to a
minimum ~0.32 at 6 h, settling at **0.42**; sodium excretion
overshoots to 0.67 mmol/min at 6 h, then settles onto the intake
rate — final-hour balance ratio **1.00**. At 24 h: retained sodium
only **+41 mmol** of the 800 delivered beyond baseline, [Na+]
137.6 mmol/L, osmolality 285.2, urine flow 3.0 mL/min matching the
raised water intake, and the MAP cost of the whole manoeuvre is
**+0.5 mmHg**. This is S43's mechanism measured: with the axis free
to suppress, balance is regained by natriuresis, not by pressure;
S44's regime (single-digit mmHg for a ~6× load) holds with room to
spare.

**The thirst finding.** The same 5× sodium load with water intake
held at baseline (×1) was run as a variant on the final engine.
Balance still closes (final UNa ≈ 0.53–0.57 vs intake 0.555;
retained +37 mmol) — but the body pays on the concentration axis
instead: [Na+] climbs to **141.8 mmol/L**, osmolality to
**293.6 mOsm/kg**, ADH sustains **4.40 pg/mL**, urine osmolality
1,014, and the ICF gives up 708 mL. In a real body that osmolality
signal is precisely the thirst drive, and intake would rise to meet
it. The engine has no thirst — intake is a scenario input — so the
pair of arms is the measurement of what that missing behaviour
decides: not whether sodium balance closes (it closes either way),
but whether it closes isotonically or hypertonically.

### 6.3 The haemorrhage course at 12 h (both axes together)

The M26 course, extended: −1,500 mL over 60 s, untreated and
1 L-crystalloid arms, marks to 720 min.

What the axes add, measured. Untreated: ADH spikes to **16.8 pg/mL
at +10 min** on the volume limb (the osmotic limb is silent —
osmolality never leaves 286–287; the loss is isotonic), then decays
as MAP recovers (5.7 at 60 min). Aldosterone climbs on the content
limb (the bleed removed ~21% of the sodium content at plasma
concentration) to **×2.55 by 4 h**, holding ×2.54 at 6 h. Sodium
excretion reads **0.000 mmol/min at every mark for 12 h** — complete
conservation — and urine totals **303.9 mL over 12 h** at
0.3–0.5 mL/min with urine osmolality 1,094–1,186 in the early hours:
maximal antidiuresis, sustained. The first-hour urine is 18.6 mL,
which is also why the M25/M26 60-min refill envelope soft line reads
deeper this milestone (net refill 408.0 mL): the kidney is no longer
leaking the volume the interstitium is trying to return.

What they do not add, stated plainly: the MAP trajectory is M26's.
MAP at +60 min is 66.5 (M26: 66.3), at 12 h 67.5 and still rising
slowly on refill and recruitment — the axes conserve what the
circulation recovers; they do not recover it. No hormonal limb in
this formulation is a pressor or a volume source, and the −1,500 mL
outcome is not materially changed on this horizon. The treated arm
shows the mirror image: the bolus's sodium suppresses aldosterone
to ×0.77 by 12 h, sodium excretion recovers to 0.112 mmol/min ≈
baseline, urine totals 538 mL, and the treated MAP advantage at 6 h
is +0.37 mmHg — the axes' contribution on the day timescale is
bookkeeping and conservation, not rescue. That is the honest
finding, and it matches the cited timescales: aldosterone's peak
effect is hours, its full action the better part of a day.

---

## 7. Development measurements that changed the formulation

Four findings during the build changed the design; all four are
recorded here and in the parameter notes they touched, in the
M24/M25 manner.

1. **The isotonic water load.** The first water-load build routed
   the litre through the M25 crystalloid event channel; the sodium
   state then read exactly +140 mmol — the "water" load was 1 L of
   isotonic saline-equivalent, and osmolality never moved. The fix
   is structural, not parametric: a dedicated solute-free water
   channel (`SetWaterFlow`) with its own boundary integral.
2. **The concentration signal saturates.** With the aldosterone
   target sensing plasma sodium CONCENTRATION, the 5× load arm
   asymptoted at 0.53–0.66 of balance over 24 h across two
   protocols: water follows sodium, [Na+] moves ~1%, and the
   suppression signal dies. Sensing the sodium CONTENT error (the
   expansion signal) closes balance at ratio 1.00. The parameter
   note for `aldosterone_sodium_gain` carries the mechanism.
3. **The shift calibration is a measurement.** The curve shift was
   calibrated against a target declared in advance (S44's regime:
   balance regained at single-digit MAP rise). At 12 mmHg/unit the
   arm asymptotes at 0.53 of balance — in this lump the Starling
   balance defends plasma volume and absorbs most of the pressure
   signal, so the hormonal limb must carry the natriuresis, which
   is S43's stated mechanism. At 25 the suppression carries it.
   The note in parameters.json records both measurements.
4. **The oliguria readout artefact.** The first flow law reported
   urine osmolality as solute-rate/flow with a constant solute
   term; in early shock (flow ~0.14 mL/min) it printed 2,156
   mOsm/kg — above the cited concentrating ceiling, because a real
   kidney's solute excretion falls as its filtration collapses.
   The readout now reports the concentrating state below
   0.5 mL/min (§1.3); the long course's early Uosm reads
   1,094–1,186, under the ceiling, and every gated use sits above
   the threshold.

The deprivation arm's soft line also has a history: under the
concentration formulation its final-hour flow read 1.02 vs resting
1.00 (a disclosed soft miss — sodium excretion stayed up and floored
the flow). Under the content formulation the flow falls to 0.51 and
the line passes; it remains SOFT because the arm is still bounded
by the absent insensible-loss term (§6.1).

---

## 8. Caveat ledger

**Deliberately out, named:**
- **ANP / natriuretic peptides** — no state, no parameter. The
  atria's fast natriuretic limb is absent; the sodium arm's first
  hours are therefore carried by pressure and aldosterone alone.
- **Thirst** — intake is a scenario input, never a state. §6.2 is
  its measured price.
- **Insensible losses** — absent since M25; §6.1 is the bound it
  puts on deprivation.
- **Potassium handling** — no K+ state exists; aldosterone's
  kaliuresis is unmodelled, and the aldosterone target's cited K+
  input is absent with it.
- **AVP V1 pressor action** — not modelled (§2).
- **Renin / angiotensin II as states** — subsumed into the
  aldosterone target (§2).
- **Non-osmotic sodium stores** (bone/skin reservoirs) — excluded
  from the lump; all body sodium here is osmotically active ECF
  sodium.
- **Glucose/urea as states** — the +10 mOsm/kg constant (§1.1); a
  hyperglycaemic or uraemic osmolality cannot be represented.

**Carried standing items (unchanged):** single linear interstitial
compliance; lymphatic volume return subsumed in the reservoir;
fixed albumin fraction in the product channel; the reflection
coefficient σ lumped; baroreflex and RAAS gains verify-flagged
where flagged (§4); **the expert-review gate for Theatre/Cases
remains UNMET** — formative-only labelling stands.

**Closed by this milestone:** "hormonal axes absent" — the standing
caveat carried since M24 — is retired.

---

## 9. Trace hashes (final engine)

Resting 0x6369b10e9a71c872 · −750 mL 0xbc683bf2721147ae · infusion
0x2dc2a305fcc4eec2 · −1,500 mL 0xaaa722ae4bb76857 · refill
observation 0xbeebab66142aa951 · course untreated (60 min)
0xaf89c09ff6c631f9 · course crystalloid 0x9bf0acb245ae9804 · whole
blood 0x1f07bded860a8d25 · components 0x8a61cc46d8f73aa9 · long rest
0x273e0335ec80c632 · water load 0x8c6c52a3c2acf65a · water control
0x853284d42fc7447b · deprivation 0xe771a4c1a2ae2bb3 · sodium load
0xfe5b4598aff43902 · long course untreated 0x21b9979d6ed4a6b4 · long
course crystalloid 0xff03fa296e485aa3.

**Downstream re-recordings (M25/M26 pattern).** The resting hash
moved 0xcee16b0ddee95d76 → 0x6369b10e9a71c872; cases
`case.ruq-pain.001` and `case.appendicitis.003` re-record it with
MILESTONE 30 paragraphs appended to their verification strings, and
`tools/case_check.py`'s pinned hash is updated. No recorded case
output moved. Theatre debriefs were regenerated: every clinical
field is identical across all 10 traces; only engine bookkeeping
moved (trace hashes, conservation error ~1e-9 mL, beat counts +1/+2
on six traces) — plus one pre-existing drift the regeneration
surfaced: trace-08's prophylaxis error detail now reads "antibiotic
prophylaxis", the appendectomy-specific label the current theatre
source has carried (the shipped debrief predated it); error id,
timing and meaning unchanged. `case.post-op-jaundice.002`'s
theatre link re-records trace-02's debrief SHA-256
(74e13c0e… → bf5b5313…) with its own MILESTONE 30 paragraph.
**Full matrix: case_check 5,145 passed / 0 failed; theatre_check
245/0; assembly checks ALL GATED PASS; verify_web ALL CHECKS PASS.**

## 10. Next steps

- The febrile/inflammatory state remains the cases' named gap
  (cases 1 and 3 link to the resting baseline only because the
  engine cannot yet represent their patients) — the natural M31.
- Insensible losses are now the binding omission on the water axis:
  a cited insensible term would unbind the deprivation arm.
- ANP and a K+ state are the named omissions on the sodium axis;
  either is a smaller milestone than this one.
- Upload of M25–M30 awaits per-item approval, as before.
