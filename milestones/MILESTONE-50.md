# Milestone 50 — README reconciliation + the drift guard

**State: built and verified locally. Not uploaded (per-item approval
rule). This batch is designated to land LAST in the pending queue,
after Milestones 34–49.**

The repository README was last fully indexed at Milestone 15. The
local tree has since run through Milestone 49 — Body Model 2,236
records, 401 clinical records, 5 Theatre procedures / 25 traces,
6 cases, a physiology engine with a respiratory module, and two
externally validated imaging subjects. The README therefore
understated and in places misstated the system's contents. This
milestone reconciles it claim by claim against the tree's ground
truth and adds the guard that keeps it reconciled.

Method rule, applied throughout: **dossiers are claims, checkers
and data files are evidence.** Every figure below was computed
from the data files or read from a checker's own printed output in
this session; where a dossier and the tree disagreed, the tree won
(one instance, §3).

## 1. Ground truth established this session (all live runs)

- Full checker matrix re-run: all 21 `tools/*_check.py` +
  `tools/assembly_check_all.py` + `tools/verify_web.js` exit 0.
- `tools/assembly_check_all.py` — ALL GATED CHECKS PASS (its census
  anchor agrees with the data-file census computed independently
  for this milestone).
- `tools/theatre_check.py` — 595 checks, 0 failures.
- `tools/case_check.py` — 10,298 passed, 0 failed.
- `tools/imaging_toolkit_check.py` — 84 hard checks PASS,
  0 conformance findings standing.
- `tools/verify_web.js` — ALL CHECKS PASS (W1–W10).
- physiology `cargo run --release -- validate` — VALIDATION: ALL
  HARD GATES PASS; resting trace hash `0x6369b10e9a71c872`
  (unchanged; the hash recorded in the physiology-linked cases).
- native `cargo run --release -- verify` — 99 PASS / 0 FAIL
  data/pack assertions; the GPU render stage cannot initialise on
  this VM (no graphics adapter) — the standing disclosed limitation,
  unchanged; exit 2 is that stage, not a data assertion.

## 2. Claim-by-claim reconciliation (old README → ground truth → disposition)

| # | Old claim (M15-index state) | Ground truth | Disposition |
|---|---|---|---|
| 1 | "Milestones 1–15 are complete and in this repository" | 50 milestones complete; index extended in the established style | Rewritten (Status, Milestones) |
| 2 | "Body Model v1 is complete: 1,552 inventory records … geometry for 1,545 of 1,552" | 2,236 inventory records; 1,545 with geometry; 691 concept-only | Rewritten (Status, Atlas table) |
| 3 | "the only exceptions are the six auditory ossicles and the coccyx" | Still the only Body-Model-v1 records without geometry — now 7 of the 691 concept-only records | Kept, reframed precisely |
| 4 | "361 sourced clinical records (Tier A 209 / Tier B 112 / Tier C 40)" | 401 (Tier A 239 / Tier B 121 / Tier C 41), computed from the clinical tranche files | Updated |
| 5 | Gap paragraph: nerves beyond CN II–V1, lymph nodes, thyroid/parathyroid, urinary interior, female tract, skin "await a further source (a full FMA / Terminologia Anatomica pass is the named route)" | The FMA 5.1.0 intake arc (M33–M38) closed those concept gaps: 684 concept records intaken. Open instead: geometry for the 691 (decision open, M34 audit: 555/587 provenance-cleared, global registration refuted, brain-assembly transform validated, no intake); 6 structures have no FMA class; nephron-segment names await a Terminologia Histologica source | Rewritten (Status, Atlas) |
| 6 | Layout table with no `theatre/` or `cases/` rows | Both modules exist (M17/M20) and are on repo main; the table omitted them | Rows added |
| 7 | "the physiology engine's resting cardiovascular outputs validate against published normal ranges" | 29 resting ranges gated (cardiovascular, renal, oncotic, endocrine, respiratory), ALL HARD GATES PASS, resting hash pinned by three cases | Extended (Physiology section) |
| 8 | No TA2 statement | TA2 ledger (`data/ta2-name-pass.json`): resolved 854 of 1,045 covered (361 clinical + 684 FMA); 117 ambiguous; 74 not found — computed from the ledger, whose clinical sections store counts and FMA sections store lists (the guard reads either form) | Added (Atlas section) |
| 9 | No pack totals in the module text | Manifest: 8,087,374 triangles, 304,367,896 bytes canonical; delivery: 123,352,401 bytes gzip | Added (Atlas section) |
| 10 | No Theatre / Cases / Imaging module sections, no totals | Theatre: 5 procedures, 45 phases / 79 steps / 243 microsteps, 25 traces, 41 sources (T1–T41), 17 parameters (12 verify-flagged), 30 instruments. Cases: 6 case files, register 47 sources (C1–C47). Imaging: 431 + 439 DICOM instances; crosswalks 93/104 labels mapped, 90 / 88 records reachable | Added (module sections) |
| 11 | No verification totals anywhere | Verification table added; the totals are re-asserted by the guard against the checkers' own printed output (R9) | Added (Verification section) |
| 12 | Status silent on expert review | The README now states it plainly: the expert-review gate is UNMET for every Theatre procedure and every case; content `dual-sourced-draft`; scores formative-only; no composite score | Added (Status; guard R12 pins the wording) |
| 13 | Status silent on the DICOM defect | Stated as found (M45) and repaired (M46); toolkit check stands at 0 findings | Added (Imaging section; guard R12) |
| 14 | File index: "All 246 files" — root 19, data 54, tools 44, web 4, physiology 9 | Regenerated under the same exclusion rule: **455 files** — root 58, assets 1, cases 21, data 87, design 10, film-engine 51 (carried, §4), native 9, physiology 10, research 45, theatre 64, tools 93, web 6 | Regenerated |
| 15 | design "10 documents"; research "3 rounds, 31 fronts" | Re-verified live: 10 files in `design/`; 31 `FRONT.md` files in `research/` | Kept |
| 16 | `cases/README.md` counts | Audited: register C1–C47, "10,298 checks at Milestone 48", six case summaries — all agree with ground truth; M49/M50 moved none of them | **Not modified** (nothing in it moved) |

## 3. The one dossier-vs-tree disagreement found

MILESTONE-49.md states "All 20 `tools/*_check.py` exit 0". The
tree holds **21** `tools/*_check.py` files (the 21st is
`imaging_toolkit_check.py`, added at M45), and all 21 exit 0.
The dossier's count is stale; the tree wins. The reconciled README
carries no bare checker-family count for exactly this reason ("every
checker in `tools/` exits 0"), and the guard asserts totals per
checker, not a family count.

## 4. The guard — `tools/readme_check.py`

Stdlib-only; re-runs four sibling checkers as subprocesses (plus the
native verifier) and recomputes everything else from the data.
Assertion groups:

- **R1** census table rows + Total row == per-system counts from
  the geometry/assembled/clinical files (the assembly checker's
  file map, recomputed independently).
- **R2** concept-only total and its FMA decomposition == inventory
  minus geometry and the TA2 ledger's intake sum; tier split ==
  clinical files.
- **R3** TA2 resolved/covered/ambiguous/not-found == the pass
  ledger (counts-or-lists read uniformly).
- **R4** pack triangles and canonical/gzip byte totals == manifest
  + delivery files.
- **R5** physiology parameter/source/range/case counts and status
  split == `physiology/parameters.json`; resting trace hash ==
  the hash recorded in the three physiology-linked case files.
- **R6** theatre procedure/trace counts, phase/step/microstep sums,
  source/parameter/instrument counts == the theatre data files.
- **R7** case-file count and register size/extent == `cases/`.
- **R8** per-subject DICOM instance counts and crosswalk totals
  (labels mapped, records reachable) == `data/imaging/`.
- **R9** checker totals: theatre_check (595), case_check (10,298),
  imaging_toolkit_check (84 PASS, ALL HARD CHECKS PASS),
  verify_web (ALL CHECKS PASS, W-set of 10), native verify
  (99 PASS / 0 FAIL data assertions; its headless GPU exit is
  tolerated and reported, never counted as a data failure).
- **R10** milestone index: one row per `MILESTONE-*.md` on disk
  (1–50) plus the Milestone 7 fix row, every referenced file exists.
- **R11** file index: per-directory lists == the tracked set
  regenerated under the documented exclusion rule (adopted source
  binaries incl. `.nii.gz` masks and the TS subset / BP3D extracted
  trees; `target/` build output; `native/frames/`; DICOM series;
  web packs, gzip variants, slice bins and `web/data/imaging.json`
  as regenerable artifacts). The `film-engine/` group is REPORTED,
  not gated (§5).
- **R12** the required status statements are present verbatim
  (expert-review UNMET, formative-only, geometry decision open,
  DICOM defect found and repaired, no Z-Anatomy intake claimed).

Prose figures are matched against a whitespace-flattened copy of
the README, so a line wrap can never silently break — or fake — a
match; tables and indexes are parsed from the raw text. On the
reconciled tree the guard prints **64 PASS lines, 0 FAIL, exit 0**
(the film-engine R11 group is REPORT-only, §5).

## 5. Honest limits

- **The film-engine group is carried over, not verified.** Those
  51 files live in the repository (PR-landed, indexed at M15) but
  not in this local tree. A staging copy exists at
  `~/workspace/anatomica-engine-stage/film-engine`, but it is a
  working copy, not the repo state: it holds three scripts the
  repo group does not (`film_engine.py`, `film_act4.py`,
  `sound_design.py` — still owed to the repo under the
  engine-to-repo directive) and lacks the `geometry/*.npz` set.
  Reconciling that group belongs to the film thread; this batch
  carries the repo's verified list unchanged and the guard reports
  the group as not locally verifiable rather than pretending.
- **Environment note.** `imaging_toolkit_check.py` requires
  pydicom 3.0.2 + nibabel 5.4.2 (its own header pins them; numpy
  1.26.4 is a system package). Both were importable for this
  session's first matrix run and missing later in the same
  session; they were reinstalled at exactly the pinned versions
  and the toolkit check then passed in full. The guard's R9
  inherits this documented requirement.
- **Resting physiology values in prose** (MAP 73.1, CO 4.21,
  PaCO₂ 41.1, PaO₂ 91.2, pH 7.39, DO₂ 828) are engine outputs
  quoted from this session's `validate` run. The guard pins them
  indirectly — via the resting trace hash (R5) and the
  parameters.json counts — rather than re-running the
  several-minute validation; a changed engine output changes the
  hash and fails R5 through the case files.
- **The README describes the post-landing repository.** On the
  local tree it is true of the tree itself, with two named
  exceptions: the film-engine group (above) and the Status
  framing, which is written for the moment this batch lands (see
  §6). Nothing in it claims Z-Anatomy intake or nerve geometry;
  the geometry decision is stated as open.

## 6. Landing order and the re-verification step

This batch lands **last**, after M34–M49 are on main, because its
numbers describe the tree those batches produce. At landing time,
in a fresh checkout of main with all batches landed:

1. Install the imaging checker's pinned requirements if absent
   (`pydicom==3.0.2`, `nibabel==5.4.2`).
2. Run `python3 tools/readme_check.py` — it must exit 0 on the
   landed tree. If any earlier batch was skipped, altered, or
   landed partially, R1/R10/R11 fail loudly; correct the README
   (or the landing) before this batch lands — do not land a
   README whose guard fails.
3. Verify the one group the guard cannot recompute locally:
   compare the README's `film-engine/` list against the
   repository's actual `film-engine/` contents at that moment.
4. Confirm the Status section's framing ("Milestones 1–50 are
   complete") matches what has actually landed; it is written to
   become true exactly when this batch lands on top of M34–M49.

## 7. Batch files

- `README.md` — reconciled in place (Status rewritten; module
  sections for Atlas / Physiology / Imaging / Theatre / Cases;
  Verification section; milestone index extended 16–50; file
  index regenerated).
- `tools/readme_check.py` — new; wired into the checker family
  (the matrix now runs it with the other `tools/*_check.py`).
- `MILESTONE-50.md` — this dossier.
- `cases/README.md` — audited, **unchanged** (§2 row 16).

No other file changed: the final tree diff against the pre-edit
baseline (10,048 files hashed before and after) is exactly these
three files — one modified, two new; even the `target/` build
output is byte-identical (the cargo artifacts were already
current), and this session's scratch lives in the untracked
`work/m50/`. All prior byte-identities (theatre debriefs, case
debriefs, data files) intact; full matrix green including the
new guard.

## 8. Next steps

- On Chase's tap sequence, land M34–M49 in numeric order, then
  this batch with the §6 re-verification.
- The Terminologia Histologica source decision (nephron-segment
  names) and the M34 geometry decision remain Chase's, unchanged
  by this milestone; the README now states both as open.
