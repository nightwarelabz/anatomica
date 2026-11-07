# Milestone 59 — README final pass: figures and indexes current through M58 and the landed browser build; landing batch prepared

**Status: COMPLETE (local).** This milestone finishes the reconciliation
Milestone 55 built and held. M55's landing was held because its regenerated
file index named `web/`, `wasm/` and `cases-harness/` files that were not yet
on main; that blocker is gone — the browser batch ("Full system in the
browser") has landed on main — and the tree has since moved through
Milestones 56–58. This pass brings every README figure and index to the
current tree, re-proves the merged "How to use" section byte-identical, and
prepares the landing batch. **Build local only; no GitHub writes were made by
this milestone.** The landing batch is exactly three files (§8).

## 1. Baseline: the tree against main, and the starting failures

Remote state was read with `~/workspace/landing/diff_tree.py` against repo
main at tip `e10c0d82a70b513fdf2252e0175e975b79cb7a3c` (540 remote blobs,
comparison not truncated). Result: **CHANGED (3)** — `.gitignore`,
`README.md`, `native/tests/pack_data.rs`; **MISSING-LOCALLY (51)** = exactly
the `film-engine/` group the local tree never carries (repository-only files,
PR-landed; the guard reports them, it does not gate on them); **NEW** = the
expected unlanded and untracked material: `milestones/MILESTONE-55.md` (the
held dossier, §8), this tree's regenerable scratch (`work/`,
`native/frames/*.png`, `web/data/imaging.json`), and the `data/sources/` raw
payloads the file-index rule excludes (TotalSegmentator NIfTI subsets,
Z-Anatomy GLBs, the BodyParts3D zip and page captures).

Two of the three CHANGED files are standing, pre-M59 deltas, investigated and
left untouched by design:

- `native/tests/pack_data.rs` — the M16-era test generalisation that has
  never landed; predates this milestone, out of scope, unchanged here.
- `.gitignore` — **the local copy is stale, in the direction opposite to the
  README.** Main's `.gitignore` carries a three-line browser-artifacts block
  (`web/pkg/`, `wasm/target/`, `wasm/harness/out/`) added by the web batch;
  the local file predates it and lacks the block. This is a web-workstream
  delta, outside this milestone's write scope, and it is **not** in the
  landing batch: landing the local copy would regress main. The local file
  should instead be refreshed from main. Recorded here so the delta is
  explained, not silently carried.

The two deltas the brief anticipated investigating are closed:
`physiology/src/cases.rs` and `theatre/src/model.rs` no longer differ from
main — their earlier local changes landed inside the M58 and M56 batches
respectively (M56's commit carried the `TheatreParams::from_str` refactor in
the same file as its CaseSpec field; verified intact there). Nothing else in
the tree differs from main.

**Environment, verified before any checker run:** `/usr/bin/python3` imports
pydicom 3.0.2 and nibabel 5.4.2 from the user site-packages
(`/home/hatch/.local/lib/python3.12/site-packages`, `pip --user`) — the
imaging toolkit check's requirement, and the environment defect M55
diagnosed. The baseline run below confirms the toolkit check passes (84).

**Baseline checker run** (`python3 tools/readme_check.py`, before this pass):
**25 failures**, every one of them README staleness in five families — no
other kind:

| Family | Failures | Shape |
|---|---|---|
| R5 physiology census (7) | parameters 141, sources 74, ranges 29, cases 23, cited 87, calibrated 35, verify 19 — all stale vs `parameters.json` | M58 growth |
| R6 theatre census (7) | procedures 5, phases 45, steps 79, microsteps 243, traces 25, sources 41, instruments 30 — all stale vs the theatre data | M56 growth |
| R7 cases (3) | case files 7, register 51, register extent C51 — stale vs `cases/` and the register | M57 growth |
| R9 printed totals (2) | theatre_check 595, case_check 11,884 — stale vs the checkers' own printed output (736; 13,135) | M56/M57 growth |
| R10/R11 indexes (6) | milestone rows 55 vs 58 dossiers on disk; file-index groups cases 24, milestones 60, theatre 64, wasm 74, web 57 — stale vs the tracked set (27, 63, 75, 88, 67) | M56–M58 + web batch |

Everything else passed at baseline, including the resting trace hash, the
imaging toolkit count (84), the verify_web W-set (W1–W10 — the browser batch
did not extend it), the native verify count (99 on this GL-less VM), the
Body Model census, TA2, geometry and DICOM families, and all five R12
status statements.

## 2. The "How to use" re-proof

The property M55 established must survive this pass: Chase's "How to use"
section, merged byte-identical, is never edited. Re-proven against main
directly, not against M55's record:

- Main's README blob at the current tip is `3da287fca732e8f6f6cda67c7a1a0b080767e8eb`
  (21,728 B) — **unchanged since M55's anchor**: the browser batch did not
  touch `README.md`, so the blob M55 merged from is still main's blob.
- The section span (from `## How to use` to just before `## Layout`)
  extracted from main's blob: sha256
  `bfae051e25b33b9261d7a18a682dc865758cb69f7f1842525193688358c7e18d`, 5,226 B.
- The same span extracted from the local README **before** this pass:
  identical hash, identical bytes.
- The same span extracted **after** all edits of §3–§5: identical hash,
  identical bytes (final verification, §7). No edit in this pass touches the
  section; every replacement string was anchored outside it and asserted to
  occur exactly once before any write.

## 3. Figure-by-figure changes

Every new figure was computed from the tree's own data files or read from a
checker's printed output in this session — none was taken from the brief.
"Source" names the ground truth the guard itself reads.

| # | README location | Was | Now | Ground-truth source |
|---|---|---|---|---|
| 1 | Status, milestone extent | Milestones 1–55 … `MILESTONE-55.md` | Milestones 1–59 … `MILESTONE-59.md` | `milestones/` on disk (this dossier) |
| 2 | Status, physiology ranges | 29 resting ranges gated | 33 resting ranges gated | `physiology/parameters.json` ranges (33) |
| 3 | Physiology module census | **141 parameters**, **74 sources** (87 cited, 35 calibrated, 19 verify-flagged), 29 ranges, 23 cases | **161 parameters**, **80 sources** (90 cited, 44 calibrated, 27 verify-flagged), 33 ranges, 26 cases | `physiology/parameters.json` (M58 census) |
| 4 | Physiology resting values | …oxygen delivery 828 mL/min | …828 mL/min, ionized calcium 1.20 mmol/L, PTH 19.8 pg/mL | M58 resting readout (axis resting values inside cited normals) |
| 5 | Physiology module prose | respiratory module "coupled one-way" | + the calcium–PTH axis (Brown sigmoid secretion; renal, bone and gut limbs) folded into the respiratory-side state; circulation baseline bit-identical by construction | M58 design as landed |
| 6 | Theatre module census | **5 authored procedures**, 45 / 79 / 243, 25 traces, 25 debriefs | **6 authored procedures**, 54 phases / 88 steps / 290 microsteps, 30 traces, 30 debriefs | theatre procedure/trace/debrief files |
| 7 | Theatre procedure list | five procedures | + total thyroidectomy (per-side RLN identification and parathyroid preservation; monitoring adjunct-only, cannot satisfy the gate) | `theatre/data/proc.thyroidectomy.total.json` (M56) |
| 8 | Theatre sources line | **41 sources** (T1–T41), **17 parameters**, 12 verify-flagged, **30 instruments** | **48 sources** (T1–T48; T42–T48 added at Milestone 56 to the T1–T41), **17 parameters**, 12 verify-flagged, **33 instruments** | theatre parameters/sources/instruments data (M56) |
| 9 | Theatre engine prose | "All five procedures … (theatre_check: 595 checks, 0 failures)" | "All six procedures … (theatre_check: 736 checks, 0 failures)" | `tools/theatre_check.py` printed total, this session |
| 10 | Cases module census | **7 cases**; register (51 sources, C1–C51) | **8 cases**; register (62 sources, C1–C62) | `cases/` files; case source register (M57) |
| 11 | Cases module prose | case #7 passage ended the case narratives | + Case #8 paragraph: the trace-30 patient on postoperative day 1, hash-linked to the Theatre debrief, Trousseau LR+ 23.5 at the conservative end, the inherited anxiety/hyperventilation anchor | `cases/case.post-thyroid-hypocalcemia.008.json` (M57) |
| 12 | Cases checker prose | case_check: 11,884 checks passed | case_check: 13,135 checks passed | `tools/case_check.py` printed total, this session |
| 13 | Verification table | theatre_check 595; case_check 11,884 | theatre_check **736 checks, 0 failures**; case_check **13,135 checks passed, 0 failed** | the checkers' printed output, this session |
| — | Verification table, unchanged rows | imaging toolkit 84; verify_web W1–W10; native verify 99 | unchanged — re-printed identically by the baseline run | §1 |

Theatre parameters (17) and verify-flagged parameters (12) were already
current and are unchanged; the sources line's new phrasing keeps the
historical T1–T41 extent named because it is true (T42–T48 were added to
it at M56) — see the guard observation, §6.

## 4. Layout table and milestone index

- **Layout table:** the `web/` row now describes what landed — WebGL2
  atlas/imaging viewer, the WebAssembly engine package (`pkg/`), and the
  case workbench; the full system runs in the browser. Two rows the M55
  layout omitted while its own file index listed the directories are added:
  `cases-harness/` (golden-debrief harness for the web case-workbench port)
  and `wasm/` (the physiology and Theatre engines as a wasm-bindgen crate,
  with its native-vs-wasm verification harness). A layout-completeness fix,
  recorded as such.
- **Milestone index:** rows 56–59 added in the established one-line style —
  56, Theatre procedure #6 (total thyroidectomy; monitoring adjunct-only;
  the first-demonstration criteria fix with all 25 prior debriefs
  byte-identical); 57, Case #8 (post-thyroidectomy hypocalcemia, the
  trace-30 patient, hash-linked); 58, the physiology calcium–PTH axis
  (Brown sigmoid; Case #8's day-2 values reproduced; resting baseline
  bit-identical); 59, this pass. Row 59's "readme_check fully green" claim
  is written only as §7's final run proves it — the precedent row 55 set.

## 5. File index regeneration

The index was regenerated by a script replicating the guard's own tracked-set
rule exactly (the `tracked()` function was extracted from
`tools/readme_check.py` and executed, not re-implemented), grouped in the
established order, with the `film-engine/` group's 51 entries carried
verbatim from the previous README (repository-only files; the guard reports
the group, it does not gate on it). Group counts, before → after:

| Group | Was | Now | Δ and cause |
|---|---|---|---|
| Root | 3 | 3 | — |
| `assets/` | 1 | 1 | — |
| `cases/` | 24 | 27 | +3: Case #8 case, attempt, debrief (M57) |
| `cases-harness/` | 2 | 2 | — |
| `data/` | 87 | 87 | — |
| `design/` | 10 | 10 | — |
| `film-engine/` | 51 | 51 | carried verbatim |
| `milestones/` | 60 | 64 | +4: dossiers 56–59 |
| `native/` | 9 | 9 | — |
| `physiology/` | 10 | 10 | — |
| `research/` | 45 | 45 | — |
| `theatre/` | 64 | 75 | +11: thyroidectomy procedure, 5 traces, 5 debriefs (M56) |
| `tools/` | 93 | 93 | — |
| `wasm/` | 74 | 88 | +14: the verification harness's thyroidectomy run outputs (native and wasm debriefs, markers, logs) |
| `web/` | 57 | 67 | +10: Case #8 data (3) and thyroidectomy Theatre data (7) mirrored for the browser build |
| **Total** | **590** | **632** | preamble updated to match |

Note on the `wasm/` group: the guard's tracked-set rule does not consult
`.gitignore`, so harness output files are indexed even though main's
`.gitignore` (the browser-artifacts block of §1) ignores some of them for
git purposes. The index follows the guard's rule, as it did at M55.

## 6. Guard observation (reported, not a blocking defect)

`tools/readme_check.py`'s R6 theatre-parameters pattern hardcodes the
literal register extent `T41\)` — it extracts the parameter count from the
text immediately following "T41)". At M55 that was simply the register's
extent. The register is now T1–T48, and the assertion remains satisfiable
**truthfully**: the README's new sources sentence names the historical
extent ("T42–T48 added at Milestone 56 to the T1–T41"), and the count that
follows it (17) is the true current parameter count, independently confirmed
by the data. No assertion was weakened and this milestone does not edit
`tools/` (outside its write scope). Recorded as a latent brittleness for a
future tools batch: if a later register change removes the T1–T41 reference
or the parameter count changes, the pattern should be generalised to
`T\d+\)` in the same change, or R6 will fail on a truthful README.

## 7. Final verification

**Final checker run** (`python3 tools/readme_check.py`, after all edits and
the index regeneration, with this dossier in place): **67 PASS / 0 FAIL**,
plus the one standing REPORT line (the `film-engine/` group, carried, not
locally verifiable — by design), ending **ALL CHECKS PASS**, exit 0. Every
baseline failure of §1 is closed by a README correction; no assertion was
weakened, skipped or edited — `tools/readme_check.py` is byte-unchanged
(sha256 `d66fa54e4e43277fffa9c80318177151ce3b3c834fa2146d8b247eb6b5962552`
before and after). The previously failing lines now read, in the final run's
own words: R5 161/80/33/26 and 90/44/27 against `parameters.json`; R6 6
procedures, 54/88/290, 30 traces, 48 sources, 17 parameters, 12
verify-flagged, 33 instruments; R7 8 cases, register 62, extent C62; R9
theatre_check 736 and case_check 13,135 against the checkers' printed
output, imaging toolkit 84, verify_web W1–W10, native verify 99; R10 rows
59 == 59 dossiers; R11 groups 27/64/75/88/67 with stated total 632 == index
sum 632. The full output is preserved at `work/m59/check-final.txt` (local
scratch, untracked); the baseline output at `work/m59/check-baseline.txt`.

Content verification beyond the guard (house rule — a landed repair must be
shown present in the artifact): every new figure string of §3 was
grep-confirmed present in the final README exactly as written, and every
stale string (`**141 parameters**`, `theatre_check: 595`, `case_check:
11,884`, `C1–C51`, `All 590 files`, the five-procedure and seven-case
censuses) grep-confirmed absent.

**How-to-use, post-edit:** the §2 extraction repeated on the final README —
span sha256 `bfae051e25b33b9261d7a18a682dc865758cb69f7f1842525193688358c7e18d`,
5,226 B, **byte-identical to main's section**. The property survives the pass.

**Byte-identity discipline:** the tree (4,299 files; exclusions `work/`,
`*/target/*`, `.git`) was sha256-manifested before and after. The complete
attribution of this milestone is exactly two entries:

- `README.md` modified: sha256
  `5fe4300c09caeb0596105584f26aefd6919ad3234ede80e9c85aedf699b15e3a` (the M55
  artifact) → `d3fb93b0c74df90427ac7484276e2dc15e52c9ec49a365d385a4170ed082fc25`,
  58,999 B.
- `milestones/MILESTONE-59.md` created (this dossier).

`milestones/MILESTONE-55.md` is byte-untouched: sha256
`1c80e8626b75665bf9a32eb516ba470889d165bdf5d001f2d596f37960b3d7cd` before and
after, as §8 requires. (This dossier's own §7 completion postdates the
manifest by minutes and changes no other file; the manifest pair is preserved
at `/tmp/m59/tree-before.txt` / `tree-after.txt` for the landing check.)

## 8. Landing batch

Exactly three files land together, in one batch, blob-verified after landing:

- `README.md` — this pass (§§3–5).
- `milestones/MILESTONE-55.md` — the held reconciliation dossier, byte-untouched
  by this milestone (its sha256 is unchanged from before this pass; §7), landing
  as the record of the merge it documents.
- `milestones/MILESTONE-59.md` — this dossier.

Nothing else. In particular `.gitignore` is **not** in the batch (§1: the
local copy is stale; landing it would regress main), and
`native/tests/pack_data.rs` remains unlanded as it has since M16.
