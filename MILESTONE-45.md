# ANATOMICA — Milestone 45: Imaging toolkit pass — independent DICOM validation of both series

**State: built and verified locally. Not uploaded (per-item approval stands).**

Milestone 19 shipped the first DICOM series with an explicit debt
(§8): *"Not validated by a DICOM toolkit. No pydicom/dcmtk exists on
this VM; conformance rests on the stdlib writer + two independent
in-project EVLE readers… A toolkit pass (pydicom/dcmtk validation)
is owed before the series is offered to external DICOM tooling as
proven."* Milestone 32 carried the same debt for the second series
(§7, §8 item 3). This milestone pays it: both series are validated
from **outside** the project's own code by a real DICOM toolkit, and
the source volumes are corroborated end-to-end by a second toolkit.
**The owed item is closed by name** — with one defect found (§5),
reported and left unfixed by design, and one half of the original
toolkit pair (dcmtk) recorded as unobtainable here (§1).

## 1. Toolkits — what was actually available

| toolkit | version | route | role in this pass |
|---|---|---|---|
| pydicom | **3.0.2** | `pip install pydicom` (this session) | DICOM parse, headers, pixel access for all 870 instances |
| nibabel | **5.4.2** | `pip install nibabel` (this session) | source NIfTI read: dtype, scaling, affine, raw voxels |
| numpy | 1.26.4 | pre-existing (M19 dependency) | array comparison |
| dcmtk | — | **not obtainable**: `apt-get install dcmtk` — package absent from the configured apt lists; `apt-get update` produced no output for over 10 minutes and was terminated | none — see below |

No vendored or hand-rolled DICOM/NIfTI reader was written or used
for the validation itself. The dcmtk half of the M19 wording
("pydicom/dcmtk") remains unrun for the environment reason above —
stated here rather than silently dropped; §8 keeps it as a named
residual. The second-toolkit corroboration this pass does have is
arguably the stronger one: nibabel reads the *source* volumes, so
the DICOM files are checked against their origin by a toolkit that
shares no code with the writer, instead of a second DICOM reader
re-reading the writer's own output.

## 2. Method — independence and coverage

- **New tool: `tools/imaging_toolkit_check.py`.** It imports no
  project module — pydicom, nibabel, numpy, stdlib only.
  `tools/imaging_derive.py` (the derivation under audit) and the
  in-project EVLE readers behind W7 are never imported or invoked.
  The claims under test are taken from each subject's `series.json`
  manifest and the milestone documents, not from the derivation's
  source code.
- **Full coverage, not sampling.** All **870 instances** (s0778:
  431; s1090: 439) are SHA-256-matched to their manifests, parsed
  unforced, header-audited element by element, and pixel-compared;
  all 870 source slices are voxel-diffed against their DICOM
  counterparts. Per-instance assertion families: file-set identity,
  hashes/byte counts, PS3.10 magic, parse, transfer syntax,
  file-meta/dataset UID agreement, SOP Class, SOP Instance UID vs
  manifest + uniqueness, Study/Series/Frame-of-Reference UIDs vs
  manifest, Modality, patient identity vs the recorded subject
  (synthetic PatientID, name, sex, age), milestone tags
  (StudyID / Implementation Version Name), Series Number, Instance
  Number sequence, date/time constancy, Rows/Columns, the
  1-sample MONOCHROME2 16/16/15 signed encoding set, Rescale
  Slope/Intercept, the three spacing elements, IOP, exact Pixel
  Data length, watermark metadata, watermark glyph values, pixel
  shape/dtype, and DICOM↔web-bin pixel identity.
- **Result: 84 hard checks PASS, 0 FAIL** (42 per subject — each an
  all-instances assertion), exit code 0, plus a value-length
  conformance audit whose single violation class is reported as a
  finding (§5), in the house pattern of counted-and-listed
  non-gating items (cf. theatre_check §9's verify-flagged
  parameters).

## 3. Per-series census

| | s0778 (M19) | s1090 (M32) |
|---|---|---|
| instances parsed by pydicom | 431/431 | 439/439 |
| SHA-256 + byte count == manifest | 431/431 | 439/439 |
| PS3.10 (preamble + DICM) | 431/431 | 439/439 |
| header assertion families green | all, every instance | all, every instance |
| DICOM pixels == web HU bins (pydicom) | 431/431 slices | 439/439 slices |
| voxels pixel-compared (DICOM vs bin) | 29,585,564 | 28,995,511 |
| glyph voxels verified at 3071 HU | 53,013 (123 × 431) | 53,997 (123 × 439) |
| source slices voxel-diffed (nibabel) | 431/431 | 439/439 |
| z steps verified == 1.5 mm | 430/430 | 438/438 |
| Study Date / Time (constant) | 20261106 / 121450 | 20261106 / 201122 |
| DICOM total bytes (manifest) | 59,860,063 | 58,688,706 |

## 4. Verdicts

**Parse and structure — corroborated.** Every file is a PS3.10
file, parses unforced under pydicom 3.0.2, declares Explicit VR
Little Endian, and its file-meta SOP Class/Instance agree with its
dataset. Pixel Data length is exactly Rows × Columns × 2 in all
870 instances — the uncompressed int16 arithmetic holds per
instance, not just in aggregate.

**Identity — corroborated.** SOP Instance UIDs equal the
manifests' per instance and are unique; Study, Series and Frame of
Reference UIDs are constant within each series and equal the
recorded values; patient identity in every instance is the
recorded synthetic one (`ANATOMICA-SYNTH-0778` / `-1090`,
`ANATOMICA^SYNTHETIC`, M, 057Y / 080Y — the source subjects' age
and sex carried in the manifest's meta.csv row); StudyID and
Implementation Version Name carry the deriving milestone's tag
(M19 / M32); Instance Numbers run 1..N in manifest order.

**The int32 → int16 conversion — corroborated three ways.**
(1) pydicom's global pixel range per series equals the recorded
stored range exactly: s0778 **[−9571, +3526]**, s1090
**[−3457, +3931]** — the recorded extremes survive in the series,
so nothing was clipped at either end. (2) nibabel reads the source
volumes as int32 with no scaling recorded (slope/intercept unset —
HU as stored); their int32 ranges equal the same recorded ranges
and sit inside int16. (3) The end-to-end voxel diff (§4,
watermark) proves every non-glyph voxel of every slice is the
flipped source value unchanged — the conversion and the flip are
exact at all 58,581,075 compared voxels, not just at the extremes.

**Geometry — corroborated, including from the source header.**
First-slice IPP equals the recorded IPP to 2e-6 mm in both series
(they are 6-decimal roundings of the same values). IPP x/y are
constant; all **868** consecutive z steps equal 1.5 mm to 1e-6;
Slice Location equals IPP z per instance; centre spans are
645.0 / 657.0 mm and full extents **646.5 / 658.5 mm** — the
figures Milestones 19/32 state. IOP is orthonormal with slice
normal (0,0,1). From the source side, nibabel's affine for both
volumes is exactly diagonal (max off-diagonal 0.0) with steps
[1.5, 1.5, 1.5], and its origin reproduces the recorded
first-slice IPP under the documented LPS relation to float32
precision (agreement ≤ 4.5e-7 mm). The "1.5 mm isotropic, read
from the sform" claim is therefore corroborated at the source,
not merely as re-expressed in the DICOM headers.

**Watermark — corroborated, and proven to be the only
alteration.** Metadata half: BurnedInAnnotation YES, ImageType
DERIVED\SECONDARY, and SYNTHETIC present in Study Description,
Series Description and Image Comments — in all 870 instances.
Pixel half: all 123 recorded glyph offsets hold 3071 HU in every
instance, read through pydicom; the slice-0 glyph box renders as
legible text (rows 6..12, cols 6..58, `#` = 3071 HU):

```
.###..#...#.#...#.#####.#...#.#####.#####..###...###.
#...#.#...#.##..#...#...#...#.#.......#.....#...#...#
#......#.#..#.#.#...#...#...#.#.......#.....#...#....
.###....#...#..##...#...#####.####....#.....#...#....
....#...#...#...#...#...#...#.#.......#.....#...#....
#...#...#...#...#...#...#...#.#.......#.....#...#...#
.###....#...#...#...#...#...#.#####...#....###...###.
```

Decisively: for **every one of the 870 slices**, the set of
voxels where the DICOM pixels differ from the flipped source
slice is *exactly* the 123 recorded glyph offsets (per-slice
differing-voxel counts: min 123, max 123), with 3071 at every
differing voxel. Two consequences: the watermark is the sole
source→series alteration anywhere in either volume; and no glyph
position coincided with a pre-existing 3071 source value on any
slice (that would have shrunk a diff set below 123) — all
**107,010** glyph voxels are genuine overwrites.

## 5. The one defect — SeriesDescription exceeds the VR LO length limit

The value-length audit (every string element in dataset + file
meta, per component, against its VR's PS3.5 maximum, all 870
files) finds exactly **one violation class**:

- **Element:** (0008,103E) SeriesDescription, VR **LO** (maximum
  64 characters).
- **Value:** `SYNTHETIC - educational model - derived from
  TotalSegmentator s0778` — **67 characters** (68 bytes as stored
  with the even-length pad); identically 67 for s1090.
- **Extent:** all **431/431** s0778 instances (SOP Instance UIDs
  `2.25.250897527427018584249495243277704591936.1` … `.431`) and
  all **439/439** s1090 instances (SOP Instance UIDs
  `2.25.25803153854017574726408693877940534641.1` … `.439`) — the
  value is series-constant, so the defect is uniform across both
  series' full UID sets as enumerated in their manifests.
- **Independent corroboration:** pydicom's own value validator
  flags the same element on access — `UserWarning: The value
  length (68) exceeds the maximum length of 64 allowed for VR LO`
  (pydicom valuerep, observed on stderr during this pass).
- **Everything else conforms:** StudyDescription (58 chars),
  ImageComments (285, LT), PatientID, Institution, Manufacturer,
  all CS/SH/AS/DA/TM/IS/DS/UI values in all 870 files were audited
  — no other violation exists.

**Severity, stated plainly.** The files parse and decode
identically under the toolkit; pixels, geometry, identity and the
watermark are unaffected. The defect is a value-validity
nonconformance against PS3.5 that a strict validator flags (and
pydicom does, as a warning): a consumer performing strict VR
validation could reject or truncate the element. It is the kind
of thing this pass existed to find — conformance had previously
rested on the writer + in-project readers, none of which enforce
VR length limits.

**Disposition: reported, NOT fixed.** Per the diagnosis-first
pattern (cf. M40), this milestone changes no data file and runs
no re-derivation. The fix belongs to a future derivation change:
shorten the writer's series-description string to ≤ 64 characters
(e.g. `SYNTHETIC - derived from TotalSegmentator s0778`, 47) in
`tools/imaging_derive.py` and re-derive — noting that
re-derivation re-rolls UIDs and dates by the pipeline's design,
so it is a data change to be tapped as such. The toolkit checker
recomputes the audit from the files on every run, so the finding
clears itself once the values conform; it stands in the tool's
output (2 findings) until then, deliberately not gated so the
matrix stays meaningful about the claims M19/M32 actually made.

## 6. What this pass does not prove

- **No dcmtk cross-read** (§1) and **no real DICOM viewer
  rendering**: the standing browser/viewer limitation is
  unchanged. What is proven is toolkit-level: an independent,
  widely used DICOM library parses, validates and decodes both
  series exactly, and a second toolkit ties every voxel back to
  the source volumes.
- **No formal PS3.3 IOD conformance-suite run.** pydicom ships no
  IOD module-table validator; the header assertions cover the
  recorded claims and the CT image attributes this project writes,
  and the value-length audit covers PS3.5 string limits, but a
  module-by-module Type 1/1C/2/2C audit against the CT Image IOD
  was not performed by any tool here.
- **Two subjects remain two subjects.** The M32 §6 cohort caveats
  are untouched by this pass; toolkit validity says nothing about
  coverage or representativeness.
- **The label bins were not re-audited here.** DICOM↔HU-bin
  identity is proven; the label side remains W7's in-project
  recount (the DICOM series carries no label data — labels live
  only in the web bins and crosswalk).

## 7. Verification — full matrix

- `python3 tools/imaging_toolkit_check.py` — **84 hard checks
  PASS, 0 FAIL** (42 per subject, each an all-instances
  assertion); **2 conformance findings standing** (§5, one per
  series — the same defect); exit 0. Runtime ~21 s.
- `node tools/verify_web.js` — **ALL CHECKS PASS** (W1–W10,
  including the in-project W7/W10 imaging suites this pass
  independently corroborates from outside).
- `python3 tools/assembly_check_all.py` — **ALL GATED CHECKS
  PASS**.
- `python3 tools/theatre_check.py` — **463 checks, 0 failures**.
- `python3 tools/case_check.py` — **7,589 passed, 0 failed**.
- physiology `cargo run --release -- validate` — **ALL HARD
  GATES PASS**.
- native `cargo run --release -- verify` — **99 PASS / 0 FAIL**
  data/pack assertions; the GPU render stage cannot initialise
  on this VM (no wgpu adapter — the standing M28–M44 disclosed
  limitation; this milestone changes no native code, packs or
  geometry).

This milestone's only tree changes are the two new files
(`tools/imaging_toolkit_check.py`, this dossier) and the
environment change (pydicom 3.0.2 + nibabel 5.4.2 pip-installed).
No data file was modified; no derivation was re-run.

## 8. Next steps

1. **Fix the §5 defect at the writer**: shorten
   `series_desc` in `tools/imaging_derive.py` to ≤ 64 characters
   and re-derive both series as a tapped data change (UIDs and
   dates re-roll by design; W7 + this checker re-verify; the
   finding then clears itself).
2. **dcmtk cross-check, if it ever becomes installable here**
   (`dcmftest` / `dcmdump` over both series) — the residual half
   of the M19 wording, kept named rather than forgotten.
3. Remaining subjects derivable in M19-rule order (s0480 next),
   each now gaining this toolkit pass as part of its derivation
   verification.
4. Unchanged open items from M32 §8: OD-06.1 with the 2D suite
   complete; the generative-route (design/06) decision.

## 9. Addendum — the §5 defect is fixed (Milestone 46, 2026-11-07)

The SeriesDescription defect reported in §5 was repaired at
Milestone 46 exactly along the §8 item 1 route: the writer's
string was shortened to `SYNTHETIC - derived from
TotalSegmentator <subject>` (47 characters), a permanent VR-length
gate was added to the writer so it refuses any non-conforming
value, and both series were re-derived as a tapped data change.
The UID ranges and Date/Time constants recorded in §3 and §5
describe the pre-fix files this pass audited and stand as that
audit's record; the live series now carry the Milestone 46
identifiers (enumerated in MILESTONE-46.md), with pixel data
proven identical per instance. Re-running
`tools/imaging_toolkit_check.py` now reports **0 conformance
findings** — the finding cleared itself, as §5 said it would. The
dcmtk residual (§1, §8 item 2) stands unchanged.
