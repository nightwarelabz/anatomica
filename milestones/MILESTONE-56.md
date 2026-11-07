# Milestone 56 — Theatre procedure #6: total thyroidectomy

The Theatre's sixth procedure is a total thyroidectomy
(`proc.thyroidectomy.total`), authored by cognitive task analysis
from seven sources consulted in-session (register T42–T48). Its
safety gate is the specialty's own: on each side, before the
inferior pedicle and the ligament of Berry are divided, the
recurrent laryngeal nerve must be identified and preserved, the
parathyroid glands accounted for with their perfusion preserved,
and the external branch of the superior laryngeal nerve accounted
for at the superior pole. The gate is enforced **per side** — the
right side's demonstrations do not transfer to the left — and
intraoperative nerve monitoring is modelled as the sources frame
it: an adjunct to visual identification, never its substitute, so
the gate cannot be satisfied by monitoring alone.

## What was built

- `theatre/procedures/proc.thyroidectomy.total.json` — 9 phases,
  9 steps, **47 microsteps (43 required in the standard
  configuration**; 44 in the branching-variant configuration; 44
  in the devascularised-parathyroid scenario), a 29-entry structure
  register (**19 Body Model records, 10 documented absences**),
  6 decision points, 8 scored errors, 1 variant, and the safety
  gate `gate.nerve-parathyroid-account` (unlocks step.4.1 and
  step.6.1, the two lobectomy steps).
- Engine support in `theatre/src/runner.rs`, all additive and
  procedure-keyed, reusing the existing gate machinery: a per-side
  division handler, the devascularised-parathyroid scenario
  mechanism (an additive optional `CaseSpec` field, on the
  Milestone 49 defect precedent), scoring-time parathyroid and
  haemostasis rules, injury management wiring, and thyroid pearls.
  `theatre/src/model.rs` gains exactly that one additive optional
  field; the parallel workstream's public `TheatreParams::from_str`
  refactor in the same file is untouched.
- Five shipped traces (26–30) and twelve new Rust probes pinning
  every criterion boundary both ways.
- Register extensions: sources **T42–T48** appended to
  `theatre/parameters.json` (48 sources; **parameters unchanged at
  17**, 12 verify-flagged — this milestone adds no parameter), and
  three instruments added to `theatre/instruments.json` (30 → 33):
  the nerve monitor (T43), the right-angle clamp and the thyroid
  retractor (T44).
- `tools/theatre_check.py` extended (595 → **736 checks, 0
  failures**), including a §8 block probing the absence discipline
  against the whole Body Model data tree.
- `tools/case_check.py`: procedure-set maintenance only — the four
  profile assertions that enumerate the Theatre's procedure set now
  name six procedures, in the Milestone 44 maintenance pattern. No
  case file changed; **the case_check total is unmoved at
  11,884 passed / 0 failed**.

## CTA rationale

The task analysis follows the operative standards' own critical
steps (T44 §10) in their own order: positioning and exposure;
strap-muscle separation; middle thyroid vein division for medial
mobility; the side's three accounts (nerve, parathyroids, external
branch); a pre-division pause; superior pedicle, inferior pedicle
and Berry division; specimen inspection (the consulted standard's
own parathyroid checkpoint — a gland on the specimen is an
autotransplant indication, T42 Recommendation 43 / T44 Rec 27b);
the second side on the same discipline, with the monitoring
sequence (V1–R1–R2–V2, T43) framing the complete-versus-stage
decision; then closure only on a confirmed dry field, and the
postoperative plan. Two decision points carry the operation's real
judgment calls: dp4, the devascularised-parathyroid decision
(autotransplant, per T44 Rec 27b, versus leave-and-monitor), and
dp5, complete-versus-stage after first-side signal loss (the
two-stage pathway of T43 and its applying series).

## The gate, against the specialty standard

The gate's text is the guidelines' text. T42 Recommendation 42A:
"Visual identification of the recurrent laryngeal nerve (RLN)
during dissection is required in all cases. Steps should also be
taken to preserve the external branch of the superior laryngeal
nerve (EBSLN) during dissection of the superior pole."
Recommendation 42B makes stimulation/monitoring a "may be
considered" adjunct (Weak/Low) — so crit1 is demonstrated only by
the visual-identification microsteps (m3.1 right, m5.2 left), and
a Rust probe performs every monitoring microstep, omits only the
identification, and pins that the Berry division still fails.
T42 Recommendation 43 and T44 Recommendations 27a/27b ground
crit2 (capsular dissection; parathyroids and their blood supply
preserved; a gland that cannot be preserved is autotransplanted).
T44 Recommendation 25 (superior pole vessels ligated close to the
capsule to avoid EBSLN injury) and T48's framing (most surgeons
avoid rather than routinely expose the EBSLN) ground crit3 as a
territorial account at the superior pole.

Resolution, by criterion, as the brief's discipline requires:

- **crit1 unmet at an inferior-pedicle or Berry division** →
  `err.divide-unidentified` (critical-fail) and a
  recurrent-laryngeal-nerve-injury resolved onto that side's nerve
  entry; the attempt FAILS at the division. If the other side
  already carries the injury, a
  bilateral-recurrent-laryngeal-nerve-injury is computed as well —
  the catastrophic outcome T42 names (bilateral paralysis,
  respiratory distress, tracheostomy risk) and T44 quantifies
  (bilateral vocal fold dysfunction 0.1–0.4%, life-threatening).
- **crit3 unmet at a superior-pedicle division** →
  `err.ebsln-unaccounted` (major, not a fail — the fail is
  reserved for the RLN, the scoring consequence for the
  parathyroids) and an external-laryngeal-nerve-injury.
- **crit2 unmet on a side whose gated work was done** →
  hypocalcemia computed at scoring, resolved onto
  `gland.parathyroid-glands`, with `err.parathyroid-unaccounted`
  (major). The computation is keyed on division: an account omitted
  on a side that is never divided computes nothing (probe-pinned).
  Its cited course: median transient hypocalcemia 27% (IQR 19–38),
  permanent hypoparathyroidism 1% (0–3) (T47); management per
  T44 Recommendations 60–61 (calcium/vitamin D strategy; oral
  calcium first-line, calcitriol as necessary, IV calcium if
  severe) is dp6's calcium-replacement-protocol plan.
- **Devascularised gland** (scenario) not autotransplanted →
  `err.devascularized-gland-not-autotransplanted` (major) and the
  same hypocalcemia computation. T47's honesty is carried in the
  error text: autotransplantation is itself associated with
  transient hypocalcemia (OR 2.03) as a marker of a gland that
  could not be preserved in situ.
- **Haemostasis unconfirmed** (m7.4) after Berry work →
  `err.unconfirmed-haemostasis` (major) and a neck-hematoma
  resolved onto `airway.trachea` (T44 Recommendation 58: suspected
  hematoma demands immediate intervention; the mechanism is
  tracheal compression). Structural only — no bleed volume is
  computed, because no consulted source gives a rate; this
  milestone adds no theatre parameter.

## Variants

One variant is authored, at a cited prevalence above the 1% gate:
**extralaryngeal branching of the RLN**, 39.2% — the
intraoperative pooled prevalence of T45 (28,387 nerves; cadaveric
pooling 73.3% is recorded in the register text, the operative
figure is the one the variant carries). It adds the branch-survey
microstep m3.5 to the required set; dividing the inferior pedicle
with the survey unperformed resolves as `err.missed-variant`
(critical-fail), checked before the plain crit1 resolution, and
probe-pinned both ways. The variant is authored on the right side;
the dossier records that asymmetry rather than silently mirroring
it.

The **non-recurrent laryngeal nerve is deliberately not authored**:
T46's pooled prevalence is 0.7% across 33,571 sides — below the
≥1% variant gate. It is a named non-variant: the register text and
the m2.3 survey label carry its association with an aberrant right
subclavian artery, and the decision is on the record here.

## Prophylaxis, withheld by design

Microstep m0.8 is the withholding microstep: T44 states
postoperative antibiotics are not indicated in thyroid surgery
(6,778-patient no-prophylaxis series, infection 0.49%). It carries
no `fulfills: "prophylaxis"` marker, so a perfect attempt scores
process 4 of 5 — the Milestone 42/44/49 ceiling-by-design pattern,
asserted of traces 26 and 21 alike by the checker.

## Absence register

Ten register entries are documented absences, each probed by
`tools/theatre_check.py` §8 against every id in the Body Model
data tree: the right and left **recurrent laryngeal nerves** (the
M39 major-nerve tranche covers the vagus trunk — `major.cn-10-vagus`
and `nerve.{right,left}-vagus-nerve` are records — not its
laryngeal branches), the right and left **external laryngeal
branches**, the right and left **superior thyroid arteries**, the
right and left **ligaments of Berry**, and the right and left
**middle thyroid veins**. The gate's injuries resolve onto these
documented absences, never onto invented records. The 19 records
(gland, lobes, isthmus, pyramidal lobe, parathyroids collective and
per-gland, inferior thyroid arteries, vagus nerves, trachea,
cricothyroids, right sternothyroid) are asserted present by the
same probe block.

## Two first-demonstration semantics fixes, disclosed

Authoring a bilateral gate exposed the same single-demonstration
assumption in two places, and both were repaired the same way —
**first demonstration wins** — with neutrality proven, not
asserted:

1. `theatre/src/runner.rs`: the criteria map recorded the LAST
   demonstration time, so the left side's phase-5 demonstration
   overwrote the right side's timely one and end-of-run safety
   scoring measured the criteria against the second side's times
   (a clean thyroidectomy scored safety 1/4). The registration now
   keeps the first time (`entry().or_insert()`).
2. `tools/theatre_check.py` §4: the reachability map likewise
   recorded the last demonstration phase; it now records the
   first, with the reason commented in place.

Every earlier procedure demonstrates each criterion exactly once,
so first-wins is indistinguishable there — and the proof is in the
run: after both fixes and a full regeneration, **all 25 prior
debriefs are sha256-byte-identical** to their pre-milestone bytes.

## Traces and probes

- trace-26-thyroid-clean — PASS, 43/43 (100%), safety 4/4,
  process 4/5 (the withholding ceiling), no errors, no
  complications.
- trace-27-thyroid-divide-before-id — FAIL at the inferior pedicle
  division (t=1380.0 s) with the RLN injury on
  `nerve.right-recurrent-laryngeal-nerve`; management 5/5 does not
  rescue the verdict; the failed attempt declares the injury only.
- trace-28-thyroid-variant-branching — PASS, required 44, 100%,
  no errors.
- trace-29-thyroid-parathyroid-devascularized — PASS, required 44
  (the scenario-inserted autotransplant), 100%, no hypocalcemia.
- trace-30-thyroid-parathyroid-unaccounted — PASS, missing exactly
  [m3.2], hypocalcemia computed at scoring, management 5/5.

Twelve Rust probes pin what the traces do not exercise: crit1
missing on the right (fail, on the right nerve); **monitoring
alone does not satisfy the gate**; crit3 missing (EBSLN injury,
major, PASS) and crit3 demonstrated (clean); the bilateral
catastrophe (two injuries + the bilateral computation, fail at
the first side's division); per-side enforcement (right account
complete, left crit1 missing → fail on the left nerve only); the
branching division without the survey (`err.missed-variant`,
checked before the plain resolution); the devascularised gland
without autotransplant (hypocalcemia; m7.1 required and missing);
crit2 unaccounted with no division (nothing computed); the
unconfirmed-haemostasis hematoma and its dp6 plan; the dp2
no-bailout arm; and RLN repair by referral (plan 1, control 0,
management 4 — referral is not control).

## Case handoff

None. No shipped case names a thyroidectomy — the case files were
scanned; "thyroid" appears only in passing in cases #4 and #5 — so
no handoff is authored, and the absence is stated here as at
Milestone 49. The case profiles' procedure-set assertions were
updated to the six-procedure set (see above); no case's content,
trajectory or handoff changed.

## Sources (register T42–T48)

| ID | Source | Consulted | Grounds |
|----|--------|-----------|---------|
| T42 | ATA 2015 differentiated thyroid cancer guidelines (Haugen et al., Thyroid 2016;26(1):1–133; PMC4739132) | full text | Rec 42A (visual RLN identification required; EBSLN preservation), Rec 42B (monitoring an adjunct), Rec 43 (parathyroid preservation, autotransplant), bilateral-paralysis consequence |
| T43 | INMSG standards Part I (Schneider et al., Laryngoscope 2018;128 Suppl 3:S1–S17) + its applying prospective series (Ann R Coll Surg Engl 2019;101(8):589–595; PMC6818062) | abstract/record level + series full text | LOS definition (EMG < 100 µV), V1–R1–R2–V2 discipline, staged two-stage pathway (dp5) |
| T44 | AAES guidelines for definitive management of thyroid disease (Patel et al., Ann Surg 2020;271(3):e21–e93) | full text | §10 critical steps, Rec 25 (superior pole close to capsule), Rec 26 (RLN identified), Rec 27a/27b (capsular dissection; autotransplant), Rec 58 (hematoma), Rec 59 (repair), Rec 60–61 (calcium), no-prophylaxis rule, VFD rates |
| T45 | Henry et al., extralaryngeal branching meta-analysis (Langenbecks Arch Surg 2016;401(7):913–923; PMC5086344) | abstract/pooled table | variant prevalence 39.2% intraoperative (28,387 nerves) |
| T46 | Henry et al., non-recurrent laryngeal nerve meta-analysis (PeerJ 2017;5:e3012) | pooled figures via comparative prevalence table | 0.7% pooled prevalence — below the variant gate; the not-authored decision |
| T47 | Edafe et al., hypocalcemia systematic review (Br J Surg 2014;101(7):307–320) | full text | transient 27% (IQR 19–38), permanent 1% (0–3); fewer-than-two-glands predictor; autotransplant OR 2.03 |
| T48 | INMSG EBSLN standards (Barczyński et al., Laryngoscope 2013;123 Suppl 4:S1–S14) | abstract | IONM an adjunct to visual identification; EBSLN avoided rather than routinely exposed → territorial crit3 |

StatPearls/NCBI was unreachable in-session (reCAPTCHA), as at
every prior milestone, and is cited for nothing.

## Verification

- `cargo run -- validate`: PASS — thyroidectomy 9 phases, 47
  microsteps (43 required standard), 29 structures, 1 gate,
  6 decision points, 8 errors, 1 variant; parameters 17 (12
  verify-flagged); instruments 33.
- `cargo run --release -- run-all`: **30 traces, 0 expectation
  failures**; all 25 prior debriefs sha256-byte-identical after
  regeneration.
- `cargo test --release`: **50 passed, 0 failed** (38 prior + 12
  new probes; the shipped-traces harness now enumerates 30).
- `tools/theatre_check.py`: **736 checks, 0 failures** (was 595).
- `tools/case_check.py`: **11,884 passed, 0 failed** — unmoved.
- Physiology `cargo run -- validate`: ALL HARD GATES PASS.
- `tools/imaging_toolkit_check.py`: ALL HARD CHECKS PASS,
  0 findings. The remaining `tools/*_check.py` data checkers all
  pass. Native verify: 99 PASS / 0 FAIL data assertions on this
  machine (no GPU adapter; the 8 render-dependent assertions are
  the documented other world, as recorded since Milestone 55).
- Tree scope: against the pre-milestone hash census, changed
  source files are exactly `theatre/{parameters.json,
  instruments.json, src/model.rs, src/runner.rs,
  tests/runner_tests.rs}`, `tools/{theatre_check.py,
  case_check.py}`; new source files are the procedure, five
  traces and five debriefs. Nothing under `web/`, `wasm/`,
  `cases-harness/`, `physiology/`, `cases/` or `data/` was touched
  by this milestone.

## Honest limits

- The expert-review gate remains **UNMET** for this procedure, as
  for every Theatre procedure and Case: no named reviewers exist.
  Content status is `dual-sourced-draft`, formative-only; there is
  no composite score and the module makes no summative claim.
- Hypocalcemia is a computed complication with its cited incidence
  and management pathway; the physiology engine carries no calcium
  axis, so no serum calcium is simulated and none is claimed.
- The hematoma is structural (airway compression, T44 Rec 58);
  no rate was consulted, so no bleed volume is computed and no
  parameter was invented to carry one.
- T43, T45 and T48 were consulted at abstract/record level and
  T46's pooled figures through a comparative table; the table
  above states the depth per source rather than flattening it.
- The branching variant is authored on the right side only, as
  built; a left-sided branching configuration is future work, not
  a silent mirror.
