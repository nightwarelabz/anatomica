# Milestone 65 — README reconciliation through Milestone 64: the endoscopy, geometry-intake and hash-link figures; the geometry ruling recorded; guard R12 brought back to truth

**Status: COMPLETE (local).** This pass brings every README figure and
index current through Milestones 62–64 (Theatre procedure #7, the Tier B
geometry intake and deferent-duct claim, and Case #9's Theatre hash-link),
in the Milestone 55/59 manner: every number re-derived from the tree's own
data files or read from a checker's printed output in this session, the
merged "How to use" section re-proven byte-identical, and the file index
regenerated under the guard's own tracked-set rule. It also carries the
one guard change the facts force: R12's two geometry status statements
had become false — in the README and in the guard alike — and both move
together to the true statements (§5). **Build local only; no GitHub
writes were made by this milestone.** The landing batch is exactly three
files (§8).

## 1. Baseline: the tree against main, and the starting failures

Repo main at tip `f530175afef222088b7ee8d2f578d0beb4ad82d3` (571 blobs,
comparison not truncated), read with `~/workspace/landing/diff_tree.py`
plus a direct tree intersection against the guard's tracked set:

- **519 paths** are in both main's tree and the guard's local tracked
  set. Of those, **9 carry pre-existing content deltas** (local
  workstream state, none of them this milestone's, none in the batch):
  `cases-harness/RESULTS.md`, `native/tests/pack_data.rs` (the standing
  M16-era delta), `physiology/src/cases.rs`, `wasm/harness/verify.mjs`,
  `wasm/src/lib.rs`, `web/cases-ui.js`, `web/index.html`,
  `web/physio.js`, `web/theatre.js` — the browser-refresh workstream's
  unlanded changes.
- **52 main blobs are outside the guard's local set:** the 51
  `film-engine/` files (repository-only; the guard reports the group, it
  does not gate on it) and `data/sources/fma-5.1.0/fma.zip`, which the
  guard's documented rule excludes from the index as an adopted-source
  archive. 519 + 51 + 1 = 571.
- **109 guard-counted local files are not on main:** `wasm/` 89 (the
  verification harness's native captures and `out/` outputs — build
  output the guard's rule counts anyway, the standing Milestone 59
  note), `web/` 16 (the `web/pkg/` WebAssembly build output, 4; and the
  refresh-synced browser data for Case #8, Case #9 and the endoscopy
  procedure/traces, 12 — synced locally, not yet landed as a web batch),
  and `data/` 4 (BodyParts3D release-page captures under
  `data/sources/bodyparts3d-4.0/`). So the README's file index, which
  follows the guard's rule, counts the local tree plus the carried
  `film-engine/` group; it is not a dump of main's blob list, and the
  difference is fully accounted above.

**Baseline checker run** (`python3 tools/readme_check.py`, before this
pass): **43 PASS / 24 FAIL**, exit 1. Every failure is README staleness
in six families — no other kind:

| Family | Failures | Shape |
|---|---|---|
| R1 census (2) | nervous geometry 133, reproductive 13, total 1,545 — stale vs the data (152, 15, 1,566) | M63 intake |
| R2 concept-only (1) | 691 vs computed 670 | M63 intake |
| R4 packs (3) | 8,087,374 triangles, 304,367,896 canonical, 123,352,401 gzip — stale vs manifest/delivery (8,285,791; 311,136,996; 125,760,132) | M63 pack rebuild |
| R6 theatre census (9) | procedures 6, phases 54, steps 88, microsteps 290, traces 30, sources 48, parameters 17, verify-flagged 12, instruments 33 — all stale (7; 63; 97; 323; 37; 54; 18; 13; 39) | M62 growth |
| R9 printed totals (2) | theatre_check 736, case_check 14,919 — stale vs the checkers' printed output (872; 14,964) | M62 / M64 |
| R10/R11 indexes (7) | milestone rows 61 vs 64 dossiers; file-index groups data 87, milestones 66, theatre 75, tools 93, wasm 88, web 67 — stale vs the tracked set (91, 69, 90, 95, 94, 79) | M62–M64 |

Everything else passed at baseline, including TA2, physiology, imaging,
the resting trace hash, and all five R12 statements — the last group
only because the README and the guard still carried the same two
geometry statements, which the ruling and the M63 intake have since
made false (§5).

## 2. The "How to use" proof (before)

The section span (from `## How to use` to just before `## Layout`)
extracted from the local README before this pass: **5,226 B, sha256
`bfae051e25b33b9261d7a18a682dc865758cb69f7f1842525193688358c7e18d`** —
byte-identical to the span recorded at Milestones 55/59 from main's own
blob. No edit in this pass touches the section; every replacement was
anchored outside it and asserted to occur exactly once before any
write. The post-edit re-proof is in §7.

## 3. Figure-by-figure changes

Every new figure was computed from the tree's data files or read from a
checker's printed output in this session — none was taken from a
dossier. "Source" names the ground truth the guard itself reads.

| # | README location | Was | Now | Ground-truth source |
|---|---|---|---|---|
| 1 | Status, milestone extent | Milestones 1–59 … `MILESTONE-59.md` | Milestones 1–65 … `MILESTONE-65.md` | `milestones/` on disk (this dossier) |
| 2 | Status, Body Model geometry | geometry for 1,545; **691 concept records carry no geometry** | geometry for 1,566; **670 concept records carry no geometry**, with the intake-cohort sentence re-anchored (§4) | system assembled/inventory data (M63) |
| 3 | Atlas pack line | **8,087,374 triangles** (304,367,896 canonical, 123,352,401 gzip) | **8,285,791 triangles** (311,136,996 canonical, 125,760,132 gzip) | `web/data/manifest.json` + `delivery.json` |
| 4 | Atlas census table | nervous 133, reproductive 13, Total 1,545 with geometry | nervous 152, reproductive 15, Total **1,566** | the data files the guard's R1 reads |
| 5 | Theatre module census | **6 authored procedures**, 54 / 88 / 290, 30 traces, 30 debriefs | **7 authored procedures**, 63 phases / 97 steps / 323 microsteps, 37 traces, 37 debriefs | theatre procedure/trace/debrief files |
| 6 | Theatre procedure list | six procedures | + upper gastrointestinal endoscopy (identify-classify-before-therapy gate; Dieulafoy variant) | `theatre/procedures/proc.upper-gi-endoscopy.json` (M62) |
| 7 | Theatre sources line | **48 sources** (T1–T48 …), **17 parameters**, 12 verify-flagged, **33 instruments** | **54 sources** (T1–T54; T42–T48 added at Milestone 56 and T49–T54 at Milestone 62, both to the T1–T41), **18 parameters**, 13 verify-flagged, **39 instruments** | theatre parameters/sources/instruments data (M62) |
| 8 | Theatre engine prose | "All six procedures … (theatre_check: 736 checks, 0 failures)" | "All seven procedures … (theatre_check: 872 checks, 0 failures)" | `tools/theatre_check.py` printed total, this session |
| 9 | Cases module prose | Case #9 paragraph ended at the physiology link; case_check: 14,919 | + the Milestone 64 closure: the endoscopy hash-linked to trace 31 in the library's third form, verdict PASS; case_check: 14,964 | `cases/case.upper-gi-bleed.009.json` theatre_link; `tools/case_check.py` printed total, this session |
| 10 | Verification table | theatre_check 736; case_check 14,919 | theatre_check **872 checks, 0 failures**; case_check **14,964 checks passed, 0 failed** | the checkers' printed output, this session |
| — | Verification table, unchanged rows | imaging toolkit 84; verify_web W1–W10; native verify 99 | unchanged — re-printed identically by the baseline run | §1 |

Theatre parameters and the register extents in the Cases line (9 cases,
C1–C70) were already current and are unchanged.

## 4. Status prose

Two Status passages are rewritten, not just renumbered:

- **Concept-only decomposition.** The old sentence decomposed the 691
  concept-only records as "(684 of them FMA 5.1.0 concept records, the
  other 7 …)". That decomposition is now arithmetically false of the
  670 (21 of the cohort gained geometry at M63: the 19 Tier B records
  and the 2 deferent-duct records, all of them FMA-intaken records).
  The sentence is re-anchored to the cohort it truthfully describes —
  the 691 records that carried no geometry at the close of the
  concept-intake arc, 684 of them FMA concept records and 7 the
  ossicles/coccyx — followed by the M63 movement and the current
  figure: "**670 concept records carry no geometry**." The guard's R2
  assertions are untouched: the FMA figure it checks (684) is the TA2
  ledger's intake sum, and the README still states it, of the cohort
  it belongs to.
- **The geometry paragraph.** "**Concepts are complete; geometry is
  the open question**" and its companions ("no Z-Anatomy geometry has
  been intaken", "The geometry decision is open", the deferent-duct
  meshes "stay deliberately unclaimed until the geometry ruling") are
  replaced by the ruled state (§5). The named no-FMA-class gaps and
  the Terminologia Histologica sentence are unchanged.

## 5. The guard change (R12) — the asserted facts changed

`tools/readme_check.py` R12 required two statements that are no longer
true, so the README could not be made truthful without the guard
asserting a falsehood, nor the guard pass without the README
repeating one. Both move together, and the new assertions check the
new true statements with the same verbatim discipline:

| Was (README + guard) | Now (README + guard) |
|---|---|
| "The geometry decision is open" | "Tier B geometry was intaken at Milestone 63" |
| "no Z-Anatomy geometry has been intaken" | "Tier C remains gated on a validating derivation" |
| — | "Tier D is excluded permanently" |
| — | "the deferent-duct meshes are claimed" |

The ruling these record: the Tier B subset (236 objects clearing both
the provenance and registration bars of the Milestone 34 audit) was
intaken at Milestone 63 under the validated brain-assembly transform —
19 FMA records gained geometry — and the deferent-duct mesh pair
(FJ3135/FJ3140) was claimed for the left and right deferent-duct
records in the same milestone. Tier C (285 objects, provenance only)
remains gated: no intake unless a derivation that places them passes
the audit's held-out gates. Tier D is excluded permanently: its
provenance cannot be separated from CC BY-NC-SA material. The R12
docstring line is updated to name the ruling in place of the open
decision. No other guard code changes; no assertion was weakened,
skipped, or re-scoped — the two retired statements are replaced by
four statements that are stricter (each names a checkable fact), and
the expert-review UNMET and formative-only statements are untouched.

**R6 brittleness, disposition:** the Milestone 59 observation stands —
R6's theatre-parameters pattern hardcodes the literal `T41)`. The new
sources sentence keeps the T1–T41 reference truthfully (T42–T48 and
T49–T54 were both added to that register), so the pattern remains
satisfiable without editing it, and this milestone does not generalise
it. The latent note is carried forward unchanged: if a later register
change removes the T1–T41 reference, the pattern should be generalised
to `T\d+\)` in the same change.

## 6. Milestone index and file index

- **Milestone index:** rows 62–65 added in the established one-line
  style — 62, Theatre procedure #7 (upper gastrointestinal endoscopy;
  identify-classify-before-therapy gate; Dieulafoy variant); 63, the
  Tier B geometry intake and deferent-duct claim (geometry 1,545 →
  1,566; packs rebuilt); 64, Case #9's Theatre hash-link to trace 31
  (the loop's third form; verdict PASS; case_check 14,964); 65, this
  pass. Row 65's "readme_check fully green" claim is written only as
  §7's final run proves it — the precedent rows 55/59 set.
  Historical rows are not rewritten: row 34's "the geometry decision
  is open" stands as the record of Milestone 34's state, superseded
  in the Status section, which is the README's current-state voice.
- **File index:** regenerated by a script executing the guard's own
  `tracked()` function (extracted from `tools/readme_check.py`, not
  re-implemented), grouped in the established order, with the
  `film-engine/` group's 51 entries carried verbatim from the previous
  README. Group counts, before → after:

| Group | Was | Now | Δ and cause |
|---|---|---|---|
| Root | 3 | 3 | — |
| `assets/` | 1 | 1 | — |
| `cases/` | 30 | 30 | — (contents changed at M64; count unmoved) |
| `cases-harness/` | 2 | 2 | — |
| `data/` | 87 | 91 | +4: the M63 derived-source provenance set (`data/sources/z-anatomy-derived/`: SOURCE.md, intake-manifest.json, ledger.json, ledger-summary.md) |
| `design/` | 10 | 10 | — |
| `film-engine/` | 51 | 51 | carried verbatim |
| `milestones/` | 66 | 70 | +4: dossiers 62–65 |
| `native/` | 9 | 9 | — |
| `physiology/` | 10 | 10 | — |
| `research/` | 45 | 45 | — |
| `theatre/` | 75 | 90 | +15: endoscopy procedure, 7 traces, 7 debriefs (M62) |
| `tools/` | 93 | 95 | +2: `zanatomy_extract_full.py`, `zanatomy_intake.py` (M63) |
| `wasm/` | 88 | 94 | +7 endoscopy harness theatre outputs (traces 31–37), −1 stale marker (`harness/out/dump-respiratory.done`, no longer on disk) |
| `web/` | 67 | 79 | +12: browser data synced by the refresh workstream — Case #8/#9 case + attempt files (4), endoscopy procedure + traces 31–37 (8) |
| **Total** | **637** | **680** | preamble updated to match |

## 7. Final verification

**Final checker run** (`python3 tools/readme_check.py`, after all edits
and the index regeneration, with this dossier in place): **69 PASS /
0 FAIL**, plus the one standing REPORT line (the `film-engine/` group,
carried, not locally verifiable — by design), ending **ALL CHECKS
PASS**, exit 0. The count reconciles exactly against the baseline:
43 PASS + 24 FAIL = 67 gated assertions at baseline; R12's expansion
from five statements to seven adds two, giving 69. Every baseline
failure of §1 is closed by a README correction — the only guard change
is the R12 replacement of §5, where the asserted facts themselves had
changed. The previously failing lines now read, in the final run's own
words: R1 nervous (419, 152, 92) and reproductive (146, 15, 16), total
(2236, 1566, 401); R2 concept-only 670; R4 8,285,791 triangles,
311,136,996 canonical, 125,760,132 gzip; R6 7 procedures, 63/97/323,
37 traces, 54 sources, 18 parameters, 13 verify-flagged, 39
instruments; R9 theatre_check 872 and case_check 14,964 against the
checkers' printed output, imaging toolkit 84, verify_web W1–W10,
native verify 99; R10 rows 65 == 65 dossiers; R11 groups data 91,
milestones 70, theatre 90, tools 95, wasm 94, web 79 with stated total
680 == index sum 680. The full output is preserved at
`work/m65/check-final.txt` (local scratch, untracked); the baseline
output at `work/m65/check-baseline.txt`.

**Sibling family:** all 21 other `tools/*_check.py` plus
`tools/assembly_check_all.py` were run after the edits — **every one
exit 0**, including `tools/case_check.py` (ALL CHECKS PASS: 14,964
passed, 0 failed) and `tools/theatre_check.py` (872 checks,
0 failures). No new failure anywhere; this milestone changes no data
or engine file, and none was expected.

Content verification beyond the guard (house rule — a landed repair
must be shown present in the artifact): every new figure string of §3
was grep-confirmed present in the final README exactly as written, and
the stale strings (`1,545` geometry census, `691 concept`, the
8,087,374 / 304,367,896 / 123,352,401 pack figures, `736 checks`,
`14,919`, `All 637 files`, `Milestones 1–59`, and both retired R12
statements) grep-confirmed absent — the pack figure 8,087,374
survives only inside the Milestone 16 index row, where it is the true
historical record of that milestone, and the 1,545/691 pair only in
the new Milestone 63 row's movement statement (1,545 → 1,566;
691 → 670).

**How-to-use, post-edit:** the §2 extraction repeated on the final
README — span sha256
`bfae051e25b33b9261d7a18a682dc865758cb69f7f1842525193688358c7e18d`,
5,226 B, **byte-identical** to the pre-edit span and to main's merged
section. The property survives the pass.

**Byte-identity discipline:** the tree (4,568 files; exclusions
`work/`, `*/target/*`, `.git`, `__pycache__`) was sha256-manifested
before and after. The complete attribution of this milestone is
exactly three entries:

- `README.md` modified: sha256
  `86877082147922f358ec13d7a1f30f5a322961f5b859e38282782419eeb5e166` →
  `1940304515fcf0a91dee7a263d7ff80fb7e9090d9edfaf18168e9d0b995f281c`,
  65,467 B.
- `tools/readme_check.py` modified (R12 only, §5): sha256
  `d66fa54e4e43277fffa9c80318177151ce3b3c834fa2146d8b247eb6b5962552` →
  `a10697ed441a02157550eea5ee90e041b341e4f1c8fc6ac63ba3799c95a4ee38`,
  22,361 B.
- `milestones/MILESTONE-65.md` created (this dossier).

No other file changed — the checker runs themselves (which regenerate
debriefs and render frames) left every other hash untouched. (This
dossier's own §7 completion postdates the manifest by minutes and
changes no other file; the manifest pair is preserved at
`work/m65/tree-before.txt` / `tree-after.txt` for the landing check.)

## 8. Landing batch

Exactly three files land together, in one batch, blob-verified after
landing:

- `README.md` — this pass (§§3–6).
- `tools/readme_check.py` — the R12 change of §5 only (docstring line
  and the REQUIRED list); every other byte unchanged.
- `milestones/MILESTONE-65.md` — this dossier.

Nothing else. In particular none of the §1 pre-existing workstream
deltas is in the batch, and no data, engine, theatre, physiology,
cases, or web file is touched by this milestone.
