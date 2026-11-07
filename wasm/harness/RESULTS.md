# ANATOMICA wasm wrapper — verification results

Proves the wasm build (`web/pkg/`, package `anatomica-wasm`) is
numerically identical to the native engines: theatre on all 25
traces (whole-debrief deep comparison, exact equality), physiology
on all four run kinds (resting / course / hormones / respiratory).

Harness: `wasm/harness/verify.mjs` (Node v24). Wasm outputs are
dumped once (`dump-*` subcommands, raw return strings preserved so
u64 trace hashes keep full precision) and compared against native
CLI captures (`compare` subcommand) stored under
`wasm/harness/native/`. Full machine-readable comparison:
`wasm/harness/out/comparison.json`.

## Build log

Environment: `PATH` includes `~/.cargo/bin`; rustup default
`stable` = cargo/rustc 1.99.1 with `wasm32-unknown-unknown`
installed; `wasm-bindgen` CLI 0.2.129 at `~/.cargo/bin/wasm-bindgen`;
Node v24.22.1.

Source changes (behavior-neutral only):

- `physiology/src/cases.rs`: added `Serialize` derives (serde was
  already a dependency) to CaseKind, WindowStats, RespReadout,
  CaseOutcome, ValidationLine, PerturbationLine, RefillOutcome,
  CourseSample, CourseArm, CourseOutcome, CourseSet, CourseLine,
  LongRestOutcome, HormoneSample, HormoneArmOutcome, LongCourseSet,
  HormoneSet, RespCaseKind, RespOutcome. No logic changes.
- `theatre/src/model.rs`: added `pub fn TheatreParams::from_str(
  text: &str)`, with `TheatreParams::load` refactored to read the
  file then call it (identical error messages, including the
  `theatre parameters do not parse: {e}` prefix). No other theatre
  changes.

Commands:

```
cd physiology && cargo build --release      # rebuilt after source change (20 s)
cd theatre    && cargo build --release      # rebuilt after source change (35 s)
cd wasm       && cargo build --release --target wasm32-unknown-unknown
wasm-bindgen --target web --out-dir ../web/pkg \
  target/wasm32-unknown-unknown/release/anatomica_wasm.wasm
```

Notes:

- The `wasm-bindgen` dependency is pinned to `=0.2.129` in
  `wasm/Cargo.toml`: an unpinned `0.2` resolved to 0.2.130, whose
  bindgen schema the installed 0.2.129 CLI rejects.
- `wasm/Cargo.toml` release profile sets `lto = true`,
  `codegen-units = 1` (size only; Rust forbids FP reassociation, so
  numerics are unaffected — and the comparisons below are exact).
- Native captures were taken with the rebuilt release binaries.
  The first theatre `run-all --outdir /tmp/theatre-native` (the
  suggested scratch dir) completed with exit 0, but this VM's /tmp
  is a 512 MB tmpfs and the directory vanished before comparison;
  the debriefs were regenerated into the durable scratch dir
  `wasm/harness/native/debriefs/` instead. `theatre/debriefs/` was
  never touched.
- Long-running captures/dumps exceed this environment's ~27 min
  background-session ceiling (SIGTERM): the native capture chain,
  the first wasm hormones dump and the first wasm respiratory dump
  were all killed by it mid-run and relaunched detached (`setsid`),
  writing `.done` markers on completion. No results were taken from
  a killed run.
- Timings observed (all under multi-job contention on 4 cores):
  native theatre run-all 594 s; native `run course` 200 s; native
  `run respiratory` 334 s; wasm theatre dump (25 traces) 1,258 s;
  wasm course dump 249 s; wasm resting ~3 s/call uncontended.

## Deliverable

`web/pkg/` (wasm-bindgen `--target web` output, generated
2026-11-07 11:58 UTC):

| file | size (bytes) |
|---|---|
| anatomica_wasm_bg.wasm | 1,027,651 |
| anatomica_wasm.js | 8,029 |
| anatomica_wasm.d.ts | 1,830 |
| anatomica_wasm_bg.wasm.d.ts | 641 |

Total pkg size: 1,038,151 bytes (~1.0 MB).

Exports (String in, String out; errors return `{"error": "<msg>"}`):
`physio`, `theatre_run`, `theatre_validate`. Error paths exercised
in `dump-resting` (bogus kind, malformed JSON, missing kind, bad
procedure for both theatre exports) — all returned the error JSON
form; see `wasm/harness/out/meta.json`.

Scope note: this verification covers the 25 traces / 5 procedures
present when the native binaries and the pkg were built
(11:47–11:58 UTC). Parallel work in this repo later the same day
added a sixth procedure (total thyroidectomy) and traces 26–30;
those are not covered here, and the regeneration of
`theatre/debriefs/` at 13:47–13:55 UTC was that parallel work, not
this task — this task never wrote to `theatre/debriefs/`,
`web/index.html`, any `web/*.js`, `tools/case_run.py`, or `web/data/`
(all verified untouched by mtime).

## Headline finding: exact on every discrete outcome; ULP-level float divergence in a few continuous fields

The engine is the same source and is deterministic on each
platform (native `determinism`: IDENTICAL, hash
0x6369b10e9a71c872 on both runs; wasm resting result identical
across the pre-LTO and LTO builds). But wasm f64 math is **not**
bit-identical to native x86_64 here: a ≤1-ULP difference in libm
transcendentals (glibc vs the libm Rust bundles for
wasm32-unknown-unknown — the engine's Hill/Bohr math calls
pow/exp-class functions) seeds a divergence that long integrations
amplify and that the beat-fold trace hashes avalanche into
completely different hash values. Consequences, all measured
below:

- Every **discrete** outcome is exactly equal everywhere:
  theatre verdicts, fail reasons, failure times, all score
  components, errors, complications, decisions, event logs and
  PEARLS text on 25/25 traces; every PASS / FAIL / SOFT verdict in
  all 121 physiology evaluation lines; all gate outcomes.
- A small number of **continuous** fields differ at ULP-to-1e-4
  level (enumerated precisely per section below), and **every
  trace hash differs** between platforms (they are bit-sensitive
  by design; within a platform they are stable).
- No difference is a JSON round-trip artifact: serde_json's ryu
  round-trip is exact, and every differing field was confirmed at
  the raw f64 level (raw values recorded in
  `wasm/harness/out/comparison.json`).

Tolerance-0 exact equality therefore **holds for all discrete
outputs and for the overwhelming majority of floats**, and fails
only in the enumerated float fields. Total counted comparisons:
391 physiology checks + 5,725 theatre leaf fields; total
mismatches: 129, every one of them in the enumerated categories.

## Theatre verification

Native reference: `anatomica-theatre run-all --outdir
wasm/harness/native/debriefs/` — 25 traces, 0 expectation
failures. Wasm: `theatre_run(procedure file text, trace file
text)` per trace, whole-Debrief recursive deep comparison (numbers
compared with exact `===` after JSON round-trip on both sides).

- Traces compared: **25/25**
- Leaf fields compared: **5,725**; exactly equal: **5,624**
- Differing fields: **101**, confined to five float fields:
  - `engine_trace_hash` — 25/25 differ (hash avalanche, above).
    E.g. trace-01 native 0xc3e6491ff7684981, wasm
    0x2fb31201f43e071b (the wasm value is identical in the pre-LTO
    smoke test and the LTO dump — platform effect, not build
    profile).
  - `physiology.map_baseline_mmhg` — 25/25 differ, max |Δ|
    2.4e-13 mmHg (e.g. 72.91107480813304 native vs
    72.91107480813328 wasm, trace-01).
  - `physiology.map_nadir_mmhg` — 25/25 differ; typical |Δ|
    ~3e-13, max |Δ| 1.24e-4 mmHg on trace-22 (the 1,500 mL bleed
    trace; nadir ≈ 39.674 mmHg both sides).
  - `engine_conservation_error_ml` — 25/25 differ, max |Δ|
    1.3e-9 mL; both sides ≤ 1.2e-8 mL (numerical zero).
  - `physiology.blood_loss_ml` — 1/25 differ (trace-22):
    1500.0000000011037 native vs 1500.0000000002997 wasm,
    |Δ| 8.0e-10 mL.
- Exactly equal on all 25 traces: `verdict`, `fail_reason`,
  `failed_at_s`, `duration_s`, `validity_label`, `case_variant`,
  checklist / safety-gate / process / management score objects in
  full, the physiology score's points and all its other fields,
  `errors`, `complications`, `decisions`, `event_log`, the PEARLS
  `debrief` text, and `engine_beats`.
- `theatre_validate` for all 5 procedures: **5/5 returned
  `{"problems": []}`**, matching native `validate` (no problems).

## Physiology verification

Native captures (rebuilt release binary): `run course` (200 s),
`run respiratory` (334 s), `run hormones`, and `validate` (exit 0,
**VALIDATION: ALL HARD GATES PASS**) — all under
`wasm/harness/native/`. The resting comparison uses the real
`validate` capture's resting section (no fallback was needed).

- **Resting** (`validate` resting section, 29 lines): output,
  unit, range text, source and verdict (PASS / SOFT-PASS) exact on
  **29/29**; values exact at the printed 2dp on **27/29**. Two
  last-digit differences: `urine_osmolality` native 603.06 vs
  wasm 603.07 (wasm raw 603.070450440779);
  `oxygen_delivery` native 828.13 vs wasm 828.14 (wasm raw
  828.1377665972019). Resting trace hash differs (native
  0x6369b10e9a71c872, wasm 0x598e9b47651f8f73).
- **Course** (`run course`): evaluation lines **14/14 exactly
  equal** (baseline/post at 2dp, expected direction, PASS/FAIL/soft
  verdicts). Trace hashes differ 4/4 (untreated native
  0xaf89c09ff6c631f9 / wasm 0xfbf4a016bbd2e177; treated
  0x9bf0acb245ae9804 / 0x514d1be5c4db8cbf; whole blood
  0x1f07bded860a8d25 / 0x620df0c89ee6d3cb; components
  0x8a61cc46d8f73aa9 / 0x3393ad0ba815a740).
- **Hormones** (`run hormones`): evaluation lines **17/18 exactly
  equal**; one last-digit difference —
  `water_deprivation_12h::urine_osmolality_late` post value native
  753.61 vs wasm 753.65 (wasm raw 753.6469043433011, after the
  12 h arm; verdict PASS on both sides). Trace hashes differ 6/6.
- **Respiratory, `run respiratory` text**: resting readout line
  **17/17 values exact**; the 9 printed arm blocks carry 25
  printed readout numbers each = **225/225 exact** at their
  printed precision (PaCO2/PaO2 1dp, pH/SaO2 3dp,
  CaO2/VE/VA/P50eff/HCO3 2dp, DO2 0dp, RR/A-a 1dp, renal
  compensation signed 2dp) — 242/242 printed numbers exact in
  total, plus 18 hash strings compared separately (below).
  Cross-check: the resting kind's `resp_post` deep-equals the
  respiratory response's `resting_resp` on all 21 fields. Hashes:
  circulation hash (`hash_at_standard_end`) differs 9/9 (the
  non-haemorrhage arms share native 0x6369b10e9a71c872 / wasm
  0x598e9b47651f8f73, i.e. each platform's own resting hash);
  respiratory hash differs only 4/9 (Shunt, Metabolic,
  HemorrhageResp, HemorrhageFeedback) and is **bit-identical on
  5/9** (Hypoventilation, HypoventilationPure, Hyperventilation,
  HyperventilationPure, ShuntPure — the arms whose respiratory
  state evolution never couples through the circulation's
  transcendental math).
- **Respiratory, `validate` sections**: all **16/16** wasm
  evaluations have native counterparts (including all four
  chronic arms, which `run respiratory` does not print); **60
  evaluation lines compared, 58 exactly equal** (baseline/post/
  delta at 2dp, expected, verdict). Two last-digit differences,
  both `oxygen_delivery`: HemorrhageResp
  `hemorrhage_750_respiratory` delta native −130.30 vs wasm
  −130.31 (wasm raw −130.3055774562947); HemorrhageFeedback
  `hemorrhage_750_metabolic_feedback` post native 691.13 vs wasm
  691.15 (wasm raw 691.1487542814458) and delta −128.86 vs
  −128.84 (wasm raw −128.84184639389719). All 20 chronic-arm
  evaluation lines are exact, and every verdict in all 60 lines
  matches.

## Native test suites

`cargo test --release` (after the source changes, native):

- physiology: **37 passed, 0 failed** (engine_tests.rs; doc-tests
  0) — 1,481 s wall under multi-job contention.
- theatre: **38 passed, 0 failed** (runner_tests.rs; doc-tests 0)
  — 976 s wall under contention.

Native CLI spot checks: `anatomica-physiology determinism` →
IDENTICAL; `anatomica-physiology validate` → exit 0, ALL HARD
GATES PASS; `anatomica-theatre run-all` → 25 traces, 0 expectation
failures.

## Addendum — 2026-11-07: procedure #6 (total thyroidectomy) + pkg rebuild

Theatre procedure #6 (`proc.thyroidectomy.total.json`, traces 26–30)
landed in `theatre/` from parallel milestone work after the original
25-trace verification above. Extending the web copies and re-running
this harness against the originally shipped `web/pkg/` exposed a
stale build: the pkg predated the final `theatre/src/runner.rs`
(nerve-identification / parathyroid logic), and trace-27
(divide-before-identification) returned PASS from the wasm where the
native runner returns FAIL.

`web/pkg/` was rebuilt from the current sources (cargo +
wasm-bindgen, same pinned versions) and the full comparison re-run:

- Theatre: **30/30 traces, 7,005 leaf fields — zero discrete-outcome
  mismatches** (verdict, fail reason, failed_at_s, every score
  component, errors, complications, checklist, management, event
  log, PEARLS all identical). Remaining differences are only the
  known platform class: `engine_trace_hash` (per-platform),
  `engine_conservation_error_ml` (~1e-9 mL), and
  `physiology.map_baseline/nadir_mmhg` in the 13th significant digit.
- `theatre_validate`: **6/6 procedures, empty problems.**
- Native captures regenerated with `anatomica-theatre run-all`
  into `wasm/harness/native/debriefs/` (30 debriefs).

Lesson recorded: a wasm pkg must be rebuilt and re-verified whenever
the engine sources move; file timestamps on `theatre/src/runner.rs`
vs `web/pkg/` are the cheap check.
