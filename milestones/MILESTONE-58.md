# Milestone 58 — Physiology: the calcium–PTH axis

**Status: built and verified locally; landing batch handed to the parent agent.**

Milestones 56 and 57 both closed with the same disclosed gap, in
the same words: *"the physiology engine has no calcium axis."*
Theatre #6 (total thyroidectomy) computed hypocalcemia at scoring
from an unmet gate criterion because the engine could not; Case
#8 (post-thyroidectomy hypocalcemia) authored its patient's
calcium course as case data for the same reason, and named the
axis "the single highest-value engine extension the case series
has identified". This milestone builds it: a lumped
calcium–parathyroid axis in the engine's established
hormone-module discipline (Milestones 30/47/51/52/53) —
extracellular ionized calcium as the regulated variable, PTH as
a secretion–clearance hormone state driven by a cited sigmoid of
ionized calcium, and three normalised PTH-effect states carrying
the renal, bone and intestinal limbs the consulted sources
support. The resting equilibrium is undisturbed by construction,
the case-pinned circulation hash `0x6369b10e9a71c872` is
bit-identical with the axis live, and the axis's perturbation
arms were predicted by an independent solver from
parameters.json constants before the engine ran — including the
post-thyroidectomy PTH-loss arm, whose 48-hour values land on
Case #8's authored POD2 measurements without the case being
touched.

## Sources consulted in-session (register S75–S80)

Six sources were consulted for this milestone and entered in
physiology/parameters.json's register (74 → 80 sources):

- **S75** — Brown EM, "Four-parameter model of the sigmoidal
  relationship between parathyroid hormone release and
  extracellular calcium concentration in normal and abnormal
  parathyroid tissue", J Clin Endocrinol Metab 1983;56(3):572–581
  (PMID 6822654). The secretion function's FORM: maximal release
  A, slope at the set-point B, set-point C (the calcium causing
  half-maximal inhibition), nonsuppressible minimum D.
- **S76** — Tinawi M, "Disorders of Calcium Metabolism:
  Hypocalcemia and Hypercalcemia", Cureus 2021;13(1):e12420 (full
  text, PMC7849212). The resting normals and the whole balance:
  total calcium 2.2–2.6 mmol/L, ionized 1.10–1.30 mmol/L;
  fractions ionized 48% / protein-bound 45% / complexed 7%; the
  albumin correction (+0.8 × (4.0 − albumin g/dL), i.e. +0.02
  mmol/L per g/L below 40); intake ~1,000 mg/day with ~400 mg
  absorbed and ~200 mg secreted into the gut (net 200 mg/day);
  bone↔ECF exchange ~500 mg/day; ~10,000 mg/day filtered with
  98% reabsorbed and ~200 mg/day excreted; PTH's three actions
  (bone resorption up, renal reabsorption up, calcitriol-mediated
  gut absorption up); vitamin D deficiency as a named
  hypocalcemia cause.
- **S77** — MedlinePlus, "Parathyroid hormone (PTH) blood test":
  the intact-PTH reference interval 10–65 pg/mL the resting PTH
  is gated against.
- **S78** — "Is It True Hypoparathyroidism? A Root Cause
  Analysis…" (PMC8751400), dual-stated with Garrett et al., Clin
  J Am Soc Nephrol 2013;8:299–312: intact PTH's plasma half-life
  is two to four minutes — the hormone time constant's cited
  range.
- **S79** — "Calcium metabolism and its disorders", Ch. 17 of
  Reproductive Endocrinology for the MRCOG and Beyond (Cambridge
  Core): bone turnover 10 mmol/day (against S76's ~12.5
  mmol/day exchange) — the bone flux's cited range.
- **S80** — "Postthyroidectomy Hypocalcemia", Korean Journal of
  Head & Neck Oncology (193-patient series), with the JCDR
  review consulted alongside: the post-thyroidectomy calcium
  nadir falls at 24–48 h, the monitoring window is 24–96 h, and
  most transient cases normalise in 5–6 days — the timescale the
  bone time constants are calibrated against, and the course the
  PTH-loss arm is read against.

StatPearls/NCBI was reCAPTCHA-blocked again this session and is
cited for nothing, as at every milestone since M39.

## Design

Five states join the integration, all on the respiratory side of
the engine (the side that reads the circulation and never writes
it):

| State | Unit | Construction at rest |
|---|---|---|
| `ca_mmol` — extracellular ionized calcium CONTENT | mmol | resting concentration × resting ECF volume (13.75 L) = 16.5 mmol |
| `pth_pg_ml` — plasma PTH | pg/mL | the secretion sigmoid's value at the resting calcium (19.82) |
| `bone_state` — bone-resorption effect | normalised | 1.0 |
| `form_state` — bone-formation effect | normalised | 1.0 |
| `vitd_state` — vitamin-D (calcitriol) effect | normalised | 1.0 |

The regulated variable is a CONTENT state, not a concentration —
the sodium state's own idiom (Milestone 30): its concentration
is the content over the live extracellular volume (plasma +
interstitial), so a volume shift moves the concentration exactly
as it moves sodium's, and the axis inherits the circulation's
volume dynamics as a one-way readout. No calcium or PTH quantity
enters any circulation derivative.

### The secretion function (S75)

PTH relaxes toward a capacity-scaled sigmoid of the stage
ionized calcium, at the hormone's time constant:

    PTH_target(Ca) = capacity × [ D + (A − D) / (1 + exp((Ca − C)/w)) ]
    dPTH/dt        = (PTH_target − PTH) / τ_pth

with A = 90 pg/mL (maximal release), D = 3 pg/mL (the
nonsuppressible minimum), C = 1.15 mmol/L (the set-point — the
calcium of half-maximal inhibition), w = 0.035 mmol/L (the
width; Brown's slope parameter B is −(A − D)/(4w) ≈ −621 pg/mL
per mmol/L at C). A, D and w are VERIFY-flagged: S75 fixes the
form and the parameters' meanings; the consulted abstract does
not print fitted values, so none are invented — the three are
chosen so the curve's resting value lands inside S77's
reference interval and its value at Case #8's ionized calcium
(0.94 mmol/L) is consistent with her measured PTH (see the
consonance analysis). The set-point is CALIBRATED inside the
cited construction (the sigmoid's midpoint must sit below the
resting ionized calcium for the resting secretion to lie on the
curve's lower shoulder, as the physiology requires). τ_pth =
240 s is CALIBRATED: the exponential time constant implied by
S78's 2–4 minute half-life is 173–346 s; 240 s sits inside.

At the resting calcium (1.20 mmol/L) the sigmoid gives
PTH_rest = 3 + 87/(1 + e^{0.05/0.035}) = **19.82 pg/mL** — inside
S77's 10–65 pg/mL, and the value the PTH state is initialised
at, computed in `Model::from_params` with the identical
operations the secretion function performs (the Milestone 30
`resting_adh_pg_ml` pattern), so the state's derivative
vanishes at the operating point bit-for-bit.

### The three limbs (S76's mechanisms, lumped)

All fluxes are mmol/min internally; each is constructed to take
its resting value exactly at the resting state, so the content
derivative cancels term by term at rest.

**Renal.** Excretion = resting excretion × filtered-load factor
× PTH factor:

    urine = U0 × (Ca/Ca_rest) × clamp(1 + a×(1 − PTH/PTH_rest), 0.2, 1.35)

U0 = 5.0 mmol/day (200 mg/day — S76's excreted figure, CALIBRATED
inside its cited balance). The filtered-load factor is the renal
module's own idiom — excretion proportional to the load the
glomerulus presents — applied to the renal side's output
quantity; the PTH factor is S76's distal-reabsorption action
(high PTH decreases excretion) as a lumped amplitude a = 0.35,
VERIFY-flagged (no consulted source prints a lumped gain). This
is a modulation of a renal OUTPUT (urine calcium), not a fork of
the renal module: urine water, urine sodium, osmolality and
every circulation quantity are untouched by the axis.

**Bone.** Resorption and formation are the same resting exchange
flux under two effect states:

    resorption = F0 × (1 + s×(bone_state − 1))
    formation  = F0 × (1 + s×(form_state − 1))

F0 = 10 mmol/day (S79's turnover figure, CALIBRATED inside the
S79–S76 cited range 10–12.5 mmol/day); s = 0.35 is the
PTH-sensitive share of the exchange, VERIFY-flagged. The two
states share one target — the clamped normalised PTH drive,
clamp(PTH/PTH_rest, 0, 3.0) — and differ only in time constant:
resorption τ = 36 h, formation τ = 10 days (both CALIBRATED
against S80's post-thyroidectomy course: the nadir at 24–48 h
and recovery over 5–6 days). Their transient DIFFERENCE is the
net bone flux: when PTH steps down, resorption falls within a
day or two while formation is still running near its old rate,
so the skeleton takes calcium up net — the mechanism that
deepens the post-thyroidectomy fall beyond what the kidney
alone computes, and the reason the arm's nadir lands at ~48–72 h
rather than in the first hours. At any CONSTANT PTH the two
states converge and the chronic net bone flux is zero, as
remodelling requires — the axis cannot mint or destroy calcium
through bone in steady state.

**Gut.** Net absorption = resting net influx × the vitamin-D
state's active share:

    gut = G0 × (0.40 + 0.60 × vitd_state)

G0 = intake × net fraction = 25 mmol/day × 0.20 = 5.0 mmol/day
(intake CITED from S76's ~1,000 mg/day; the 20% net fraction
CALIBRATED from S76's absorbed-minus-secreted arithmetic:
(400 − 200)/1000). The 0.40 passive (vitamin-D-independent)
share is VERIFY-flagged. The vitamin-D state relaxes at τ = 24 h
(CALIBRATED — calcitriol's genomic action is a days-scale
effect, S76's mechanism text) toward
`scale × clamp(PTH/PTH_rest, 0, 3)^0.25` — the quarter-power is
VERIFY-flagged and is the lump's one deliberate nonlinearity: a
saturating squeeze, so a rising PTH extracts more absorption
from a fixed vitamin-D substrate with diminishing returns, and
substrate deficiency (scale < 1) cannot be fully compensated by
PTH alone. That single property is what makes the chronic arm a
secondary-hyperparathyroidism picture rather than either a crash
or a perfect defence.

**Content balance.**

    d(ca_mmol)/dt = gut + resorption − formation − urine + IV input

At rest: 5.0/1440 + 10/1440 − 10/1440 − 5.0/1440 + 0 = 0 —
exactly, term by term, in the engine's arithmetic as in the
solver's (both evaluate the same free functions; the solver is
an independent RK4 re-implementation over a fixed ECF, the
engine the staged RK4 over the live ECF).

### Readouts

Ionized calcium (content / live ECF volume); total calcium =
ionized / 0.48 (S76's ionized fraction, CITED); albumin =
plasma protein concentration × the Milestone 26 albumin
fraction (45.0 g/L at rest); corrected calcium = total + 0.02 ×
(40 − albumin g/L) (S76's correction, CITED — the same
arithmetic the Case module applied to Case #8). At rest:
ionized **1.20**, total **2.50**, corrected **2.40** mmol/L, PTH
**19.82** pg/mL — all inside the cited normals, and all four are
gated resting validation ranges from this milestone (S76 for the
calcium values, S77 for PTH). Note the corrected value sits
BELOW the total at rest: the engine's resting albumin (45 g/L)
is above the correction's 40 g/L reference, so the correction
subtracts 0.10 mmol/L. That is the formula applied as written,
not an error — Case #8's patient, albumin 3.6 g/dL, corrected
UPWARD by the same formula.

### Scenario surface

Four events, all in the house pattern: `SetCalciumAxis`
(the A/B disable — all five derivatives exactly zero),
`SetPTHSecretion` (capacity fraction on the sigmoid),
`SetCalciumFlow` (intravenous calcium input, mmol/min — calcium
only; no volume, sodium or protein rides on it, disclosed), and
`SetVitaminD` (the vitamin-D target scale). The five states fold
into `resp_hash` after the Milestone 53 compensation state; the
circulation hash's fold is untouched.

## Prediction before measurement

As at Milestones 51 and 53, every scenario arm was computed
first by an independent solver — `work/m58/predict.py`, a
fixed-step RK4 over a fixed 13.75 L extracellular volume,
reading its constants from parameters.json — and the solver's
bands were written into cases.rs as magnitude gates before the
engine ran. The frozen pass is `work/m58/predictions-pass2.json`.

One design pass was REJECTED by the solver before any engine
code existed, and is recorded here because it is the milestone's
most instructive result. Pass 1 coupled the bone exchange's full
10 mmol/day to the effect states (no sensitive share) and used a
weaker renal amplitude: the chronic PTH-loss equilibrium ran
away to an ionized calcium of 0.266 mmol/L at seven days — the
formation state, relaxing ten days behind resorption, leaves a
net skeletal uptake of several mmol/day for days, and once the
content falls the PTH signal that would arrest the fall is
absent by construction. Pass 2 introduced the PTH-sensitive
share (0.35) and strengthened the renal amplitude to 0.35: every
arm then lands in a survivable, source-consonant range, and
those constants are the ones that shipped. The prediction
discipline caught a qualitative design defect at zero engine
cost — the bone states' uncoupling is a real mechanism, not a
bug, and its magnitude had to be bounded by the sensitive share
before the axis was safe to build.

## The resting-zero construction and the A/B proof

Four constructions and one measurement carry the resting-zero
law:

1. The PTH state initialises at the sigmoid's own output at the
   resting calcium (`Model::from_params`, identical operations
   to the secretion function) — its resting derivative vanishes
   bit-for-bit.
2. Each flux takes its resting value at the resting state by
   construction (filtered-load factor 1.0, PTH factors 1.0, bone
   states 1.0, gut share 1.0), so the content derivative cancels
   term by term.
3. The case-pinned circulation hash `0x6369b10e9a71c872` is
   **bit-identical** in the validate output with the axis live.
   Calcium and PTH enter no circulation derivative; the new
   states fold into `resp_hash` only.
4. The A/B pair (the resting case run twice — axis live, axis
   disabled — in `calcium_pth_loss_ab_pair_24h` and in the
   dedicated validate case): with the axis disabled the five
   derivatives are exactly zero and the states sit at their
   initialised values at every mark (**calcium (content)**,
   **PTH**, **bone**, **formation** and **vitamin-D** all print
   their resting values unchanged in the disabled arm), while
   the two arms' **circulation trace hashes are identical**
   (`0x4a8b2abf3b82eb43` in both). The respiratory hashes differ,
   as they must — the axis folds there. One disclosed artefact:
   in the disabled arm the ionized READOUT drifts up by
   +0.0023 / +0.0036 / +0.0045 mmol/L at 24/48/72 h even though
   the content state is frozen, because the readout divides the
   frozen content by the live extracellular volume, which itself
   drifts fractionally over three simulated days. The state is
   exact; the derived concentration carries the volume's own
   dynamics, disclosed here rather than hidden. (The corrected
   readout in the disabled arm prints 2.3999999944 for the same
   reason in miniature — the Milestone 26 protein state's
   rounding, ~3 × 10⁻⁷ mmol/L from 2.40.)

## Measured against the predictions

The engine was then run, and its values are tabulated against
the frozen solver's. The deltas have one systematic cause,
named in advance by the design: the engine divides the content
by the LIVE extracellular volume, which runs ~0.2–0.4% below
the solver's fixed 13.75 L across these arms, so engine ionized
calcium sits uniformly a few 10⁻⁴ mmol/L above the solver's at
the same content; the corrected readout additionally carries a
live-albumin term (the engine's albumin at the 24/48 h marks is
≈45.65 / ≈45.95 g/L against the solver's fixed resting 45.0 —
the circulation's own albumin dynamics, read by the correction
formula). Every gate passed.

**PTH loss (capacity 0 — the post-thyroidectomy arm):**

| Mark | Ionized, engine (solver) | PTH, engine (solver) | Corrected, engine (solver) |
|---|---|---|---|
| 6 h | 1.1685 (1.1682) | 3.15 (3.17) | — |
| 12 h | 1.1322 (1.1316) | — | — |
| 24 h | 1.0605 (1.0596) | 7.53 (7.54) | 2.096 (2.1075, Δ −0.011 albumin) |
| 48 h | 0.9357 (0.9345) | 8.08 (8.08) | 1.830 (1.8469, Δ −0.017 albumin) |
| 72 h | 0.8407 (0.8397) | — | — |

Urine calcium at 6 h rises to 6.30 mmol/day in both (the
kidney, unassisted by PTH, excretes more of a falling load —
the renal limb's sign is the arm's first mover, before the
bone transient deepens the fall).

**Calcium load (IV infusion, 0.02 mmol/min):** peak ionized
**1.5254 mmol/L in both** at infusion end; PTH at the peak 3.26
in both (suppressed toward the sigmoid's floor, as the
secretion function requires); at +6 h, 1.4678 (solver 1.4667);
at +24 h, 1.2700 (1.2682) with PTH 5.69 against the solver's
5.82 — the one visibly amplified delta (the sigmoid's steep
recovery limb magnifies a ≤0.002 mmol/L ionized difference into
0.13 pg/mL of PTH; the mechanism is named, the gate carried a
band wide enough for it).

**Chronic vitamin-D deficiency (scale 0.3, seven days):**
ionized calcium **1.1801 mmol/L in both** — compensated to
within 0.02 of rest; PTH 28.86 (solver 28.87), elevated into
the upper half of S77's interval: the secondary-
hyperparathyroidism picture, held by the bone and renal limbs
against a gut that can only deliver 58% of its resting influx.
Bone state 1.430 (1.431), formation state 1.200 (1.201).

## Consonance with Case #8 — stated honestly

Case #8's patient is the thyroidectomy trace-30 patient on
postoperative days 1–2: the parathyroid glands were
devascularised (not excised), and her filed course is corrected
calcium 7.8 mg/dL on POD1 (drawn, unactioned), then on POD2
corrected 1.83 mmol/L (7.3 mg/dL), ionized 0.94 mmol/L
(3.8 mg/dL), PTH 8 pg/mL, QTc 486 ms. The engine's PTH-loss arm
is the capacity-0 limit of that physiology — total secretory
failure, a harder insult than devascularisation with residual
function, and its readouts are read against her values without
the case being edited in any way.

At **POD2 (48 h)** the consonance is as close as the module's
lumping permits:

| Quantity | Engine (capacity-0, 48 h) | Case #8 (POD2) | Δ |
|---|---|---|---|
| Ionized calcium | 0.9357 mmol/L | 0.94 mmol/L | −0.004 |
| Corrected calcium | 1.830 mmol/L | 1.83 mmol/L | 0.000 at print precision |
| PTH | 8.08 pg/mL | 8 pg/mL | +0.08 |

At **POD1 (24 h)** the engine runs HIGH: corrected 2.096
against her 1.95 mmol/L, a gap of +0.146. The disagreement is
disclosed, not tuned away, and its candidate causes are named
in the case's own terms: (i) her glands were devascularised
mid-operation and her POD1 draw integrates an earlier effective
insult start than the arm's t = 0 step; (ii) her albumin is
3.6 g/dL post-operatively against the arm's resting ~45.7 g/L,
so part of her total-calcium fall is a binding fall the arm's
resting-albumin circulation does not reproduce; (iii) the
arm's bone transient is at its slowest exactly here (formation
τ = 10 d), so the model's first-day fall is carried mostly by
the renal limb. One structural note belongs on the record: her
implied ionized fraction is 0.94/1.83 = 0.514, against the
model's fixed cited 0.48 — at her albumin the bound fraction
falls, so a fixed-fraction readout will always read her total
slightly low relative to her ionized; the model's POD2
consonance is partly that arithmetic cancelling the content
gap, and claiming more precision than that would be invention.

A tuning path existed and was REFUSED on the record: raising
the renal amplitude toward ~0.55 closes much of the POD1 gap
but drives the chronic untreated equilibrium to ~0.62 mmol/L —
a value no consulted source supports for a survivable steady
state, and a constant chosen to fit one patient's day would
corrupt every other arm. The amplitude stays at the value the
solver's pass-2 discipline produced.

Two further honest bounds. First, the arm is UNTREATED: the
case's calcium-replacement protocol (dp6) is a disposition, not
a physiology input, and the engine arm applies none of it — the
comparison is against her untreated trajectory as filed, and
her management begins where the arm ends. Second, the arm's
own continuation beyond the gated window is solver-only: the
frozen solver's untreated course keeps falling toward ~0.70
mmol/L near one week before the renal equilibrium arrests it —
a severity the gates deliberately do not assert, because no
consulted source parameterises untreated total secretory
failure past the S80 monitoring window. Case #8's engine LINK
(a physiology link entry pinning an engine run, in the case
series' established form) is the named next step; this
milestone builds and verifies the axis it will pin.

## Non-regression

- **Baseline diff accounted in full.** The M58 validate output
  was diffed line-by-line against a pre-M58 baseline run of the
  release binary (`work/m58/validate-diff.txt`). The diff has
  exactly three families: (1) four ADDED resting readout lines —
  the calcium axis's own outputs; (2) eight changed lines, every
  one a `resp_hash` value and nothing else — the respiratory
  hash moves because the five new states fold into it, which is
  the design; every circulation trace hash is identical in every
  arm, including the pinned resting hash; (3) the calcium
  scenario section, a pure insertion. The soft-fail lines are
  byte-identical to baseline — the same disclosed set (the ATLS
  windows, the refill envelope 408.04, the bolus retention 0.08,
  the whole-blood figure 0.67) at the same values; no new soft
  failure was introduced, and no hard gate moved: **ALL HARD
  GATES PASS** in both runs.
- **Physiology test suite:** 40 passed / 0 failed (38 prior + 2
  new: `calcium_axis_resting_zero_and_pinned_hash`,
  `calcium_pth_loss_ab_pair_24h`).
- **Theatre:** all 30 debriefs sha256-byte-identical to the
  pre-milestone census; theatre_check 736 passed / 0 failed.
- **Cases:** case_check 13,135 passed / 0 failed — unmoved, as
  required; no case file was touched.
- **Tools:** every `tools/*_check.py` exits 0 (18 checkers);
  verify_web reports ALL CHECKS PASS.
- **Native verify:** 99 [PASS] / 0 [FAIL] data assertions, then
  the documented GL-less-VM GPU initialisation failure (exit 2)
  — the standing both-worlds signature of this host (107
  assertions where a graphics adapter exists); unchanged from
  every prior milestone on this VM.
- readme_check's only failures are the held README's stale
  figures — the known, expected families from the M56–M58
  figure moves, resolved when the reconciled README lands after
  the web batch; no new failure family appeared.

## Census delta

- Parameters: **141 → 161** (+20: 12 physiology constants, 8
  scenario parameters). By class: CITED 87 → 90 (ionized
  fraction, albumin correction, gut intake), CALIBRATED 35 → 44
  (set-point, τ_pth, urine excretion, bone flux, gut net
  fraction, vitamin-D and bone time constants, hormone capacity
  default, IV rate default), VERIFY-flagged 19 → 27 — the eight
  new flags, named: sigmoid maximal release A, nonsuppressible
  minimum D, sigmoid width w; renal PTH amplitude; bone
  PTH-sensitive share; gut passive share; vitamin-D
  PTH-exponent; effect-state ceiling.
- Sources: **74 → 80** (S75–S80, above).
- Resting validation ranges: **29 → 33** (+4 gated ranges:
  ionized calcium [1.1, 1.3], total [2.2, 2.6], corrected
  [2.2, 2.6] — all S76; PTH [10, 65] — S77. All PASS at rest.)
- Perturbation cases: **23 → 26** (PTH loss with the live/
  disabled A/B pair, calcium load, chronic vitamin-D
  deficiency). All 12 calcium gates PASS.

## Honest limits

- The ionized fraction is a single cited constant (0.48); in
  truth it moves with albumin and pH. The axis inherits the
  simplification and discloses it — the Case #8 analysis above
  shows exactly where it bites (her implied 0.514).
- There is no rapidly-exchangeable bone-surface pool: the
  infusion arm's decay is carried by the renal limb alone, and
  the real first-hour distribution into bone surface is faster
  than this lump computes. The peak is exact by construction of
  the input; the decay shape is the model's, flagged here.
- The chronic arms are bounded by their sources: S80's window
  parameterises days, not weeks; the untreated PTH-loss
  continuation past 72 h is solver-explored and deliberately
  ungated.
- Phosphate, magnesium, FGF23, calcitonin and PTHrP are absent —
  no axis, no states, no claims. Post-thyroidectomy magnesium
  interplay (a real contributor to refractory hypocalcemia) is
  outside the model until a source-grounded magnesium state
  exists.
- Parathyroid RECOVERY (devascularised glands recovering over
  days, S80's 5–6-day normalisation) is not modelled: the
  capacity event is a step the scenario sets and clears; a
  recovery ramp is future work, named here because it is the
  difference between the arm's course and most real transient
  courses.
- The IV channel carries calcium only — no volume, sodium or
  protein — so an infusion arm's concentration is a pure
  content effect; real calcium gluconate administrations are
  small-volume, and the simplification is disclosed rather than
  silently absorbed.
- Eight of the axis's constants are VERIFY-flagged by design:
  the consulted sources fix the mechanisms, the forms and the
  normals, and do not print lumped gains. The flags stand until
  a consultable source prints them; nothing in the arms' gates
  depends on hiding them.
- As with every physiology milestone: the expert-review gate
  remains **UNMET** (no named reviewers), the content status is
  `dual-sourced-draft`, and all scores and readouts are
  formative and educational only. This is a simulation, not a
  clinical device.

## Landing batch

Six files, all local, handed to the parent agent to land under
the ANATOMICA upload-as-you-finish rule:

- `physiology/parameters.json`
- `physiology/src/engine.rs`
- `physiology/src/cases.rs`
- `physiology/src/main.rs`
- `physiology/tests/engine_tests.rs`
- `milestones/MILESTONE-58.md` (this dossier)

No other tree file was touched by this milestone (verified by
mtime sweep over the tree: tools/, cases/, theatre/, data/ and
native/ carry no M58-window modifications; the theatre
runner/model sources and the web-tier workstream's files are
untouched).
