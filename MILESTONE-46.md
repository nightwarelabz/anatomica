# ANATOMICA — Milestone 46: SeriesDescription repair and re-derivation of both imaging series

**State: built and verified locally. Not uploaded (per-item approval stands).**

Milestone 45's toolkit pass found one defect in the shipped DICOM
series: SeriesDescription (0008,103E), VR LO, carried a 67-character
value against the PS3.5 maximum of 64, in all 870 instances of both
series. M45 reported it and, per the diagnosis-first pattern,
changed no data. This milestone pays the fix exactly as M45 §8
item 1 scoped it: the writer's string is shortened, the writer is
gated so it can never emit a non-conforming value again, and both
series are re-derived end-to-end — with every consequence of the
re-derivation (re-rolled UIDs, new file hashes, moved recorded
references) handled explicitly and proven, not assumed. The one
thing that must not change — the pixel data — is proven unchanged
per instance against a pre-fix snapshot.

## 1. The writer fix

**The string.** In `tools/imaging_derive.py`, `series_desc` changes
from

```
SYNTHETIC - educational model - derived from TotalSegmentator s0778   (67 chars)
```

to

```
SYNTHETIC - derived from TotalSegmentator s0778                       (47 chars)
```

(identically 47 for s1090). This is the shortened form M45 §5
named. It remains series-constant, still states SYNTHETIC (the
watermark-metadata assertions in W7 and the toolkit checker require
it), and names the source dataset and subject. No other header
value was changed: both subjects were re-derived under their
original milestone tags (s0778 `"Milestone 19"`, s1090
`"Milestone 32"`), so Study ID, Implementation Version Name and
ImageComments carry the same deriving-milestone attribution as
before; StudyDescription (58 chars, always conforming) is
untouched.

**The permanent gate.** `_el()` — the single choke point through
which every element the writer emits passes, dataset and file meta
alike — now carries a PS3.5 length assertion for every string VR it
can emit (`_VR_MAX`: AE 16, AS 4, CS 16, DA 8, DS 16, DT 26, IS 12,
LO 64, LT 10240, PN 64, SH 16, ST 1024, TM 16, UI 64). Each value
is measured per component (multi-valued values split on `\`) after
stripping the even-length pad, and the writer **raises rather than
emitting** a non-conforming value. Negative-tested before the
re-derivation: the old 67-character string is refused with the
element, VR and lengths named; a 64-character LO passes and a
65-character LO is refused; UI, multi-component CS/DS, SH, AS, LT
and the OW pixel element all emit exactly as before. Any future
derivation — including the remaining subjects in M19-rule order —
runs under this gate.

## 2. The re-derivation and its proof census

Both series were re-derived end-to-end through the pipeline
(s0778 at 2026-11-07T02:29:37Z, s1090 at 2026-11-07T02:30:14Z).
Crosswalk accounting reconciles with the original derivations
(s0778 contested 6,103 / claims 6,424,824 / labelled 6,418,721 —
the M19 figures verbatim). Before re-deriving, the pre-fix series
were snapshotted (per-instance Pixel Data SHA-256, full-file
SHA-256, web-bin hashes, manifest hashes, and a preserved copy of
all 870 pre-fix DICOM files). Against that snapshot:

| proof | result |
|---|---|
| Pixel Data bytes identical, per instance | **870/870** (431 + 439) |
| Web HU/label bins byte-identical | **1,740/1,740** files (870 × 2) |
| Element-level diff, old vs new file (pydicom, every element) | confined to the **expected set** in all 870 files (below) |
| `series.json` deep-diff | only `derived_at_utc`, the 3 series-level UIDs, and per-instance `sop_instance_uid`/`sha256`/`bytes` (1,297 + 1,321 field diffs, all allowlisted, 0 others) |
| `crosswalk.json` | **byte-identical** for both subjects |
| `web/data/imaging.json` deep-diff | exactly **2** changed values: the two subjects' `geometry.frame_of_reference_uid` |

The element-level diff is the sharp statement of "no other header
changes": in every one of the 870 files, the set of elements whose
value differs from the pre-fix file is a subset of {SeriesDescription
(the fix); SOP Instance UID and its file-meta twin; Implementation
Class UID; Study, Series and Frame of Reference UIDs; Study/Series
Date; Study/Series Time} — the re-rolls the pipeline performs by
design on every derivation. In 90 s0778 instances the file-meta
group length (0002,0000) also moved: pure bookkeeping, tracking a
re-rolled UID whose stored length changed (the 2-digit instance
suffixes, where the new 38-digit instance root changed the padded
length by 2 bytes). The toolkit checker's end-to-end arm then
re-proves the watermark property on the new files: for every
slice, the DICOM-vs-source difference set is exactly the 123
recorded glyph offsets with 3071 HU at every differing voxel —
the watermark remains the only source→series alteration.

File sizes moved only as the arithmetic requires: s0778 totals
59,860,063 → 59,851,083 bytes (−20 per instance from the shortened
string, the rest UID stored-length variation); s1090 totals
58,688,706 → 58,679,926 bytes (−20 × 439 exactly).

## 3. New identifiers (the live values)

| | s0778 | s1090 |
|---|---|---|
| SeriesDescription | `SYNTHETIC - derived from TotalSegmentator s0778` (47) | `SYNTHETIC - derived from TotalSegmentator s1090` (47) |
| Study Instance UID | `2.25.111436186121315901016113655216657057019` | `2.25.12274486504345373834656626460475358455` |
| Series Instance UID | `2.25.257334890027282140845553906118231291421` | `2.25.161849003558963109385941427078439659322` |
| Frame of Reference UID | `2.25.183030832115787233563672588251471888591` | `2.25.127730395450260939289252419030042174495` |
| SOP Instance UIDs | `2.25.90617669443722634062410872182775451439.1` … `.431` | `2.25.38640571594457294879837139020476518799.1` … `.439` |
| Implementation Class UID | `2.25.15504894003479946880155066675727864904` | `2.25.223922495108798480292211154962426168283` |
| Study/Series Date, Time | 20261107, 022937 | 20261107, 023014 |

Superseded (recorded here so the old values remain findable; they
no longer identify any shipped file): s0778 Study
`2.25.163720870524478782057557218769442362356`, Series
`2.25.298438996343173801966697550196605545912`, Frame of Reference
`2.25.138788580965501814605140955475988516601`, instances
`2.25.250897527427018584249495243277704591936.1` … `.431`, Date/Time
20261106 / 121450; s1090 Study
`2.25.224504308787560426380101989092124810441`, Series
`2.25.198886170905011150555192303807107975295`, Frame of Reference
`2.25.296939406336287045166729170400060858252`, instances
`2.25.25803153854017574726408693877940534641.1` … `.439`, Date/Time
20261106 / 201122.

## 4. Every re-anchored reference

- **`data/imaging/s0778/series.json`, `data/imaging/s1090/series.json`**
  — regenerated by the derivation: new UIDs, `derived_at_utc`,
  per-instance SOP UIDs / SHA-256 / byte counts (§2's deep-diff
  proves nothing else in them moved).
- **`web/data/imaging.json`** — regenerated by the derivation
  merge: the only changed values are the two subjects'
  `geometry.frame_of_reference_uid` (§2). `manifest_milestone`
  remains `Milestone 32`, as before (s0778 derived first, s1090
  second — the original order).
- **`MILESTONE-19.md`** — dated addendum (§10) recording the
  re-derivation, the superseded M19 identifiers, and the new ones.
  The dossier body is unrewritten history.
- **`MILESTONE-32.md`** — dated addendum (§9) correcting the two
  statements the re-derivation supersedes, by name: §3's "s0778 was
  NOT re-derived; its UIDs and DICOM hashes are the M19 originals"
  (true until this milestone) and s1090's original identifiers.
- **`MILESTONE-45.md`** — dated addendum (§9): the §5 defect is
  fixed; its §3/§5 UID ranges and Date/Time constants stand as the
  audited pre-fix record.
- **`MILESTONE-31.md`** — checked: it records no UID, hash or
  Date/Time value (its W10 numbers are pixel-derived — gallbladder
  and L3 centroids, glyph counts — and pixels did not change), so
  there is nothing in it to re-anchor; W10 re-verifies it against
  the live files below.
- **Case files** — checked: no case file records a DICOM-side UID
  or hash. The case #1/#3 imaging profiles recount from the web
  bins (byte-identical, §2) and `case_check.py` passes unchanged
  at 7,589/0 (§5).
- **`data/imaging/README.md`** — already states that re-running
  the derivation "regenerates them with fresh UIDs"; no change
  needed.

## 5. Verification — full matrix

- `python3 tools/imaging_toolkit_check.py` — **84 hard checks
  PASS, 0 FAIL**, and **0 conformance findings standing** (was 2:
  one per series — the §5 defect of M45, now cleared automatically,
  exactly as M45 designed the audit to clear). The value-length
  audit reports "no PS3.5 violations" for both subjects, and
  reading the new files under pydicom with warnings-as-errors
  raises nothing (the pre-fix read raised the VR LO warning on
  every access).
- `node tools/verify_web.js` — **ALL CHECKS PASS** (W1–W10:
  W7 DICOM↔bin pixel identity and SHA-manifest agreement against
  the new series.json; W10 MPR on the unchanged pixels).
- `python3 tools/assembly_check_all.py` — **ALL GATED CHECKS
  PASS**.
- `python3 tools/theatre_check.py` — **463 checks, 0 failures**.
- `python3 tools/case_check.py` — **7,589 passed, 0 failed**
  (case #1/#3 imaging profiles unchanged, as §4 states).
- physiology `cargo run --release -- validate` — **ALL HARD
  GATES PASS**.
- native `cargo run --release -- verify` — **99 PASS / 0 FAIL**
  data/pack assertions; the GPU render stage cannot initialise on
  this VM (no wgpu adapter — the standing disclosed limitation,
  unchanged since M45; the process exit code 2 comes from that
  stage). This milestone changes no native code, packs or
  geometry, and the native shell does not read the DICOM series.

Tree census for this milestone: `tools/imaging_derive.py` (the
fix + gate), all 870 DICOM instances + both `series.json` files
regenerated, both `crosswalk.json` rewritten byte-identically,
all 1,740 web bins rewritten byte-identically,
`web/data/imaging.json` (2 values), dated addenda in
MILESTONE-19/32/45.md, and this dossier. Nothing else.

## 6. Honest limits

- **The dcmtk residual from M45 stands.** dcmtk remains
  unobtainable in this environment (package absent from the
  configured apt lists; `apt-get update` stalls), so the
  `dcmftest`/`dcmdump` cross-read named in M19's original wording
  is still unrun. The conformance position is: pydicom parses,
  validates and decodes both series with zero findings, and the
  writer now refuses non-conforming values at emission.
- **No formal PS3.3 IOD module-table audit** — unchanged from
  M45 §6; the value-length audit covers PS3.5 string limits, not
  Type 1/1C/2/2C module presence.
- **UID stability is still derivation-scoped.** Any future
  re-derivation re-rolls UIDs and dates again by design (and the
  series.json/man dossier addendum pattern of §4 is the standing
  way to record it). Nothing outside this project should cite
  these UIDs as permanent identifiers.
- Environment note: the pydicom/nibabel installs from M45 were
  lost to a VM service restart during this milestone and were
  re-installed at the same pinned versions (pydicom 3.0.2,
  nibabel 5.4.2) before verification; the derivations themselves
  depend only on stdlib + numpy and were unaffected.

## 7. Next steps

1. Remaining subjects derivable in M19-rule order (s0480 next),
   each now deriving under the writer gate and gaining the
   toolkit pass as part of its verification.
2. dcmtk cross-check if it ever becomes installable here — the
   residual half of the M19 wording, still named.
3. Unchanged open items from M32 §8: OD-06.1 with the 2D suite
   complete; the generative-route (design/06) decision.
