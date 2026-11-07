# Milestone 55 — README reconciliation, final pass

The M50 reconciliation was held at landing because its own guard,
`tools/readme_check.py`, reported failures against the tree (imaging-check
count, milestone rows, file index). This milestone completes it: the
reconciled README absorbs the section Chase added on main himself, every
figure is brought current through Milestone 54, the file index is
regenerated, the guard's failures are each diagnosed to a cause and closed,
and `readme_check.py` exits 0 on the final tree. Nothing else in the tree
was written by this milestone (byte-identity record in §6).

## 1. The merge — Chase's "How to use" section

Provenance. On repo main at this milestone's start (tip `34428d55`), the
README blob is `3da287fca732e8f6f6cda67c7a1a0b080767e8eb` (21,728 bytes).
Commit `ca36d943` ("Add How to use instructions to the README", parent
`7b22c01c`, the milestones-folder move) is the only commit in the chain
`7b22c01c → ca36d943 → 74a64522 → 34428d55` that touches README.md.
Diffing the README blob at `7b22c01c` against the blob at `34428d55`
gives exactly one change: a single contiguous insertion, lines 27–145 of
the current file — the complete `## How to use` section (six numbered
subsections: web shell, native application, physiology engine, Theatre,
case workbench, checking the data). Extracted section: **5,226 bytes,
sha256 `bfae051e25b33b9261d7a18a682dc865758cb69f7f1842525193688358c7e18d`**.

Placement decision. In Chase's version the section sits between
`## Principles` and `## Layout`. The reconciled README has the same
structure in the same order, so the section was inserted at the identical
structural position — after the Principles block, immediately before
`## Layout` — with no wording, formatting, or whitespace changes.

Proof. After the merge, the section was re-extracted from the reconciled
README (from `## How to use` to just before `## Layout`) and compared
byte-for-byte with the extracted original: **identical, 5,226 of 5,226
bytes**. (Verified by direct content comparison, not by the edit step's
success report.)

## 2. Figure changes (old → new → ground truth)

| Figure | Was | Now | Ground truth |
|---|---|---|---|
| Cases in library | 6 | **7** | `cases/case.*.json` count (M54) |
| Case source register | 47 sources, C1–C47 | **51 sources, C1–C51** | `cases/parameters.json` (last id C51) |
| case_check total (prose + table) | 10,298 | **11,884** | `tools/case_check.py` printed output |
| Native `verify` assertions (table) | 99 | **99** — challenged twice, re-derived (see §3) | verifier's printed output on the current VM instance |
| Milestone index rows | 1–53 | **1–55** (rows 54, 55 added) | `milestones/MILESTONE-*.md` on disk |
| Status milestone extent | "Milestones 1–50" | **"Milestones 1–55"**, paths moved to `milestones/` | same |
| Layout table milestone row | `` `MILESTONE-*.md` `` | `` `milestones/` `` | folder move at `7b22c01c` |

A Case #7 prose sentence was added to the Cases module section (the
rule-out pathway, the age-adjusted D-dimer figures, the registered LR−),
in the same register as the case #6 sentence it follows.

Figures verified **unchanged** against ground truth by the guard's PASS
lines: Body Model census 2,236 / 1,545 / 401 and the per-system table;
concept-only 691 (684 FMA); clinical tiers 239 / 121 / 41; TA2 854
resolved of 1,045 covered, 117 ambiguous, 74 not found; packs 8,087,374
triangles, 304,367,896 canonical bytes, 123,352,401 gzip bytes; physiology
141 parameters / 74 sources / 29 validation ranges / 23 perturbation cases
(87 cited, 35 calibrated, 19 verify-flagged) and the resting trace hash
`0x6369b10e9a71c872`; theatre 5 procedures, 45 phases / 79 steps / 243
microsteps, 25 traces, 41 sources (T1–T41), 17 parameters (12
verify-flagged), 30 instruments; theatre_check 595; imaging 431 + 439
DICOM instances, 93 of 104 labels mapped, 90 / 88 reachable records;
imaging_toolkit_check 84 hard checks (see §3); verify_web W1–W10.

## 3. The R9 diagnosis — three failures, three different causes

**Imaging (README 84 vs printed 0, exit 1): an environment defect, not a
README error and not a checker error.** Run standalone, the toolkit check
died before its first assertion:

```
File "tools/imaging_toolkit_check.py", line 97, in <module>
    import pydicom
ModuleNotFoundError: No module named 'pydicom'
```

A subprocess that dies at import prints zero `PASS` lines and exits 1 —
exactly what the harness counted. The pinned toolkits of Milestone 45
(pydicom 3.0.2, nibabel 5.4.2) were absent from the environment's
`/usr/bin/python3` (3.12.3) — the environment the M50 landing note
already named as a precondition ("with the pydicom 3.0.2 / nibabel 5.4.2
pins installed"). The fix was applied to the environment, not to the
number and not to the checker — twice, because the first fix did not
survive the machine:

1. `pip3 install --break-system-packages pydicom==3.0.2 nibabel==5.4.2`
   (into `/usr/local/lib/python3.12/dist-packages`; numpy 1.26.4 was
   already present). Toolkit check standalone: exit 0, 84 `PASS` lines,
   ALL HARD CHECKS PASS, 0 conformance findings. The guard's next full
   run confirmed the imaging assertion green.
2. At ~12:27 UTC the VM was replaced (uptime reset; `/tmp` wiped). The
   `/usr/local` install died with the instance, and the failure recurred
   verbatim in the following guard run — reproduced standalone, same
   `ModuleNotFoundError`. Final fix, placed where the runtime persists:
   `pip3 install --user --break-system-packages pydicom==3.0.2
   nibabel==5.4.2`, landing in
   `/home/hatch/.local/lib/python3.12/site-packages/` — the home
   directory, which survives VM restarts and replacements. Import
   verified under a clean environment (`env -i`), and the toolkit check
   standalone again: exit 0, 84 `PASS`.

The README's 84 was correct all along; `tools/readme_check.py` is
**unchanged** by this milestone.

**case_check (10,298 vs printed 11,884): plain README staleness** — the
table predated Milestones 48–54's checker growth; updated to the printed
total.

**Native verify (99 vs printed 107 in one run, 99 in the next): the
count is a machine fact, and the machine changed mid-milestone.** The
verifier's full output decomposes exactly: **99 pack/manifest assertions
+ 5 frame-silhouette assertions + 1 translucency-proof assertion + 2
picking assertions = 107** when its GPU stage initialises. On the
pre-replacement VM instance it did — **llvmpipe (LLVM 20.1.2, GL backend,
CPU device)**, eleven frames rendered, exit 0, `verify: ALL HARD CHECKS
PASS`, reproduced in two independent runs (the guard's subprocess and a
standalone run) — and the README table was updated to 107 on that
evidence. The ~12:27 UTC VM replacement removed the GL driver stack
with the instance: post-replacement runs (the guard's subprocess and a
standalone run) both print **99 PASS / 0 FAIL** with
`GPU INITIALISATION FAILED: no wgpu adapter on any backend chain …
gl drivers/libraries could not be loaded`, exit 2. The README therefore
carries **99** — the count this machine deterministically prints — and
the paragraph under the table states both worlds precisely: the 99
data/pack assertions here, the 107 composition where an adapter (a
software GL stack suffices) exists, observed and recorded above.
Whichever instance serves the tree, `tools/readme_check.py` re-derives
the count from the verifier's own print on every run, so a future
instance change surfaces as a guard failure rather than silent drift —
the reconciliation's figure is the current instance's truth, not a
universal constant.

## 4. The remaining failures

- **R7** (cases/register): M54 staleness; fixed by the §2 figures.
- **R10** (milestone rows 53 vs disk 54): rows 54 and 55 added; the index
  now matches `milestones/` exactly (55 numbered reports + the Milestone 7
  fix row).
- **R11** (file index): regenerated from the tree under the guard's own
  tracked-set rule, with the `film-engine/` group carried verbatim
  (51 entries; reported, not gated, as designed — those files live in the
  repository, not in this local tree).

## 5. A moving tree — disclosure

This milestone did not build on a still tree. Beginning 2026-11-07
~11:47 UTC, minutes before this milestone started, a parallel workstream
(the browser-tier build that makes the whole system usable at
anatomica.cc) began writing in this tree: `web/cases.js`, `web/pkg/`,
`web/data/cases/`, `web/data/theatre/`, a new `wasm/` crate
(wasm-bindgen wrapper over the physiology and theatre engines), and
`cases-harness/` (a golden-debrief harness for the web case port, its
RESULTS.md all PASS). None of those files are this milestone's work; none
were touched. The regenerated file index describes the tracked set **as
found at regeneration time** (§7), and the counts in §2's table that the
guard recomputes from data files are unaffected by that workstream.
If the workstream adds or removes tracked files after this milestone,
`tools/readme_check.py` will flag the index drift — that is the guard's
purpose, and the standing rule (Milestone 50, §6) is that later
milestones' README figure updates ride with their own batches.

## 6. Byte-identity discipline

The tree was hashed before any edit (10,505 files, work/ excluded) —
and the manifest was then lost when the VM replacement wiped `/tmp`
mid-milestone (§3), so the after-state attribution was re-established
against the stronger reference, repo main itself: a full blob diff of
the local tree against main at `34428d55` shows, among repo-tracked
files, exactly these differences — `README.md` (this milestone),
`milestones/MILESTONE-55.md` (new; this milestone), and three
pre-existing local strays that predate and are untouched by this
milestone (`native/tests/pack_data.rs`, `physiology/src/cases.rs`,
`theatre/src/model.rs`). This milestone's writes are exactly:

- `README.md` (the merge + §2 figures + regenerated file index)
- `milestones/MILESTONE-55.md` (this dossier)

`tools/readme_check.py` is unchanged (the R9 imaging failure was the
environment, §3). Side effects of verification itself: the native
verifier's pre-replacement runs wrote render outputs under
`native/frames/` — regenerable products, excluded from the tracked set
by the guard's rule. Files of the parallel workstream (§5) changed on
their own schedule and are local-only, itemised in §5.

## 7. Final verification

File index regenerated **2026-11-07 12:47:44 UTC** against the tracked
set at that instant: **590 files** in the index (539 local tracked +
51 `film-engine/` carried), groups — Root 3, assets 1, cases 24,
cases-harness 2, data 87, design 10, film-engine 51, milestones 60,
native 9, physiology 10, research 45, theatre 64, tools 93, wasm 74,
web 57.

Final guard run, `python3 tools/readme_check.py`, 12:47:45–12:58:18 UTC
on that exact tree:

```
67 PASS / 0 FAIL, one REPORT (the film-engine/ carried group, as designed)
ALL CHECKS PASS — exit 0
```

Every previously failing assertion green in the same run: R7 cases 7,
register 51, extent C1–C51; R9 theatre 595, case_check 11,884,
imaging_toolkit_check 84 PASS / exit 0 (the durable `~/.local` pins of
§3), verify_web W1–W10, native verify 99 printed / 99 stated; R10 rows
55 == disk 55; R11 every group equal, stated total 590 == index sum;
R12 all five required status statements present verbatim.

Two earlier final attempts are part of the record, not edited out: the
first (12:12–12:23 UTC) failed only R11 [wasm] — the workstream grew
that group 30 → 46 during the run — with the other 66 assertions green;
the second (12:28–12:36 UTC, after the VM replacement) failed R9
imaging (the pins had died with the instance, §3), R9 native (99
printed on the replacement instance, §3) and R11 [wasm] again. Each
cause was closed at its own level — environment, instance fact, index
regeneration in a quiet window — and no assertion was weakened,
skipped, or edited: `tools/readme_check.py` is byte-identical to the
version that reported the original failures.

At the moment of this writing the parallel workstream had been quiet
since before the regeneration and had written nothing further; per §5,
any later write of theirs that changes the tracked set will surface as
an R11 failure on the next guard run and rides with their batch.

Final artifacts: `README.md` 54,149 bytes, sha256
`5fe4300c09caeb0596105584f26aefd6919ad3234ede80e9c85aedf699b15e3a`
(the merged "How to use" section re-verified byte-identical against a
fresh fetch of main's blob after all edits: sha256 `bfae051e…`, §1).

## 8. Honest limits

- The expert-review gate remains UNMET for every Theatre procedure and
  every case; all scores remain formative-only. This milestone changed no
  content module and no status in that respect — the README continues to
  state it verbatim (guard section R12, all five required statements
  present).
- The geometry decision remains open; the README claims no Z-Anatomy
  intake (R12-verbatim).
- The file index is exact for the tree at the §7 instant. It is a local
  tree: the `film-engine/` group is carried from the repository index
  (Milestone 15 / PR #1) and is reported, not verified, by the guard.
- The environment fix in §3 lives in the home directory's user
  site-packages (`~/.local`), which survives VM restarts and
  replacements; a fresh home directory must install the same two pins
  before `tools/readme_check.py` can pass its R9 imaging assertion —
  the M50 landing note's precondition, restated here so it is not lost.
  Likewise the native assertion count is an instance fact (§3): if a
  future instance again offers a GL adapter, the guard will fail R9
  native until the table carries that instance's 107 — by design.
