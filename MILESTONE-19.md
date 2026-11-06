# ANATOMICA — Milestone 19: Imaging v1 — synthetic CT derived from the Body Model's label space

**State: built and verified locally. Not uploaded (per-item approval stands).**

Milestone 16 put every Body Model record on screen as geometry;
Milestone 17 made one procedure attemptable. This milestone gives the
system its first imaging study: a complete, DICOM-structured CT series
derived from a real TotalSegmentator subject already held locally,
whose voxels are labelled in the Body Model's own terms — click a
structure in a slice and the same record panel opens that the atlas
shows, because both are wired to the same `records.json`.

## 1. What was built

- **`tools/imaging_derive.py`** (new) — the derivation pipeline:
  reads one TS subject's CT + 104 segmentation masks, builds the
  combined label volume under a stated assignment rule, computes
  per-label HU statistics and LPS geometry, burns the synthetic
  watermark, and writes every output below. (Dependency note: earlier
  ANATOMICA tools are stdlib-only; this one uses numpy 1.26.4 —
  present in the environment — because it streams ~3 GB of voxels.
  Recorded here rather than hidden.)
- **DICOM series** — `data/imaging/s0778/dicom/`: 431 instances,
  59,860,063 bytes, PS3.10 files (128-byte preamble + `DICM`), CT
  Image Storage SOP class, Explicit VR Little Endian, written by a
  stdlib writer in the tool. `data/imaging/s0778/series.json` is the
  derivation manifest (provenance, geometry, per-instance SHA-256,
  watermark spec); `crosswalk.json` is the full label accounting;
  `data/imaging/README.md` states the folder's rules.
- **Web slice data** — `web/data/imaging.json` (viewer manifest:
  geometry, cited window presets, per-label crosswalk + HU stats)
  and `web/data/imaging/s0778/{hu,lbl}-XXXX.bin` (862 files,
  88,756,692 bytes): per-slice int16 HU and uint8 label index, the
  same build-product status as the atlas packs. DICOM pixel data and
  web HU bins are byte-identical per slice (asserted in W7).
- **Imaging mode in the web shell** — `web/imaging.js` (new) + mode
  toggle and containers in `web/index.html`. `web/viewer.js` is
  byte-untouched: the atlas is intact and the W6 pick-codec gate
  passes unchanged.
- **`tools/verify_web.js` W7** (new) — imaging verification at the
  data level (§7).

## 2. Subject and provenance

**s0778** — TotalSegmentator dataset v1.0 (Zenodo 6802614, **CC
BY 4.0**), intake at Milestone 3 (CRC-verified). meta.csv row: 57 y,
male, institute A, "ct thorax-abdomen-pelvis", train split. Chosen as
the most complete of the 10 locally held subjects: **98 of 104 label
masks non-empty** (next best, s1090, has 95 and lacks the bladder),
646.5 mm z-extent. The six absent labels are `brain` and
`vertebrae_C1`–`C5` — the scan starts at C6; the crosswalk carries
them as mapped-but-absent, not silently dropped.

Two provenance facts stated wherever the series is presented (banner
in the viewer, metadata in the files, manifest):

- TotalSegmentator is a **published research dataset**; no real
  patient data of any ANATOMICA user exists in this project.
- The atlas Body Model is a **different individual** (BodyParts3D
  subject). Imaging and atlas share structure *identity* (record
  ids) only — **no spatial co-registration between the two subjects
  is claimed or implied**.

## 3. Derivation route — exactly what happened to the pixels

- **Intensities:** the subject's own CT, as stored (int32, scl_slope
  1.0, scl_inter 0.0 — Hounsfield units, unscaled). **No intensity
  remapping, no resampling, no synthetic HU generation.** The single
  conversion, int32 → int16, is asserted lossless for this subject
  (stored range −9571…+3526, inside int16) by the tool at run time.
- **Geometry, from the source, not assumed:** 262 × 262 × 431 voxels
  at 1.5 mm isotropic (the dataset's resampled grid), read from the
  NIfTI sform (asserted diagonal, shared identically by CT and all
  104 masks).
- **Orientation:** NIfTI voxel order is (right, anterior, superior).
  The stored order used by both the DICOM files and the web bins
  flips both in-plane axes, yielding standard DICOM axial display —
  ImageOrientationPatient `[1,0,0, 0,1,0]`, first-slice
  ImagePositionPatient (−209.999, −384.685, 1243.918) mm LPS — so a
  DICOM viewer and the web canvas render the same picture (patient
  left on screen right, anterior up).
- **Label assignment:** masks overlap on **6,103 voxels** (0.095% of
  6,424,824 mask claims). Contested voxels go to the smallest
  claiming mask (ties by label index) — measured, stated, and the
  resulting labelled total (6,418,721) reconciles exactly.

## 4. Watermark (design/06 rule, both halves enforced)

- **Metadata:** DICOM BurnedInAnnotation (0028,0301) = `YES`;
  ImageType `DERIVED\SECONDARY`; "SYNTHETIC" in StudyDescription,
  SeriesDescription, and a full ImageComments statement; synthetic
  2.25-root UIDs; PatientID `ANATOMICA-SYNTH-0778` — no source
  identifier is carried into the series.
- **Pixels:** the word SYNTHETIC in 5×7 glyphs at **3071 HU** (the
  12-bit maximum in the round-02 table — white under all three
  shipped window presets), rows 6–12, cols 6–58 of every slice in
  stored orientation: 123 voxels per slice, 53,013 total. Burned
  **after** all HU statistics were computed from unaltered values;
  the exact glyph offsets are recorded in `series.json` and asserted
  voxel-by-voxel in W7 for both the DICOM files and the web bins.
  The label volume is not watermarked (it is overlay data, not the
  image).

## 5. Crosswalk census — the exact accounting

104 source labels. Mapped = **93**, using only mappings established
before this milestone:

| route | labels | source |
|---|---|---|
| skeletal rules | 59 | Milestone 3 census (`labels.json` skeletal_overlap, re-asserted against `tools/ts_census.py` in the tool) |
| inventory adjudications | 34 | `totalsegmentator_overlap` blocks written by Milestones 5, 9–15 into the per-system inventory files |

Unmapped = **11**, staying source labels, flagged in the viewer:
the 10 muscular labels (`autochthon`, `gluteus maximus/medius/
minimus`, `iliopsoas` ×2 — the M4 tranche recorded no overlap
adjudication; same-name records, where they exist, are listed in the
manifest as **unadjudicated candidates**, displayed as text only and
never opened as records) and `face` (the M3 census deliberately maps
it to no record; M15 records TS overlap 0 for integumentary).

By presence in s0778: mapped+present **87**, mapped+absent **6**
(brain, C1–C5), unmapped+present **11**, unmapped+absent **0**.
Two mapped labels span several records (adjudicated that way by
their tranches): `portal_vein_and_splenic_vein` → 3 records,
`pulmonary_artery` → 2 — the viewer's click panel lists all of them
rather than picking one silently. **Records reachable from imaging:
90** (from present labels; 96 from all mapped labels), every one
resolving in `records.json` (asserted). The verifier re-derives the
entire crosswalk from the milestone sources independently (W7) —
the shipped numbers are not taken on the tool's word.

## 6. HU validation — measured against the cited tables

Per-label statistics (mean/median/p5/p95/min/max over the assigned
label volume) ship in `crosswalk.json` and the viewer manifest.
Against the project's cited references (design/06 ranges; round-02
front 05 §5.1 table — the project's dual sources for HU):

- **Muscle** (10 labels): median-of-medians **49.5 HU**, inside the
  cited 35–55 range. Extremes as measured: gluteus minimus right 23
  (small deep muscle, partial-volume), iliopsoas 57–58.
- **Lung** (5 lobes): medians −649…−907. Only the left lower lobe
  sits inside the cited −700…−600 band; the other four sit closer
  to air — well-inflated lobes measure lower, and the round-02 table
  itself flags variants (some tables −500). Reported as measured;
  no verdict forced.
- **Bone** (59 labels): whole-mask medians 151–517 (median 242.5).
  The cited cortical range (+500…+1900) is a *cortical sample*
  expectation; TS bone masks enclose trabecular bone and marrow, so
  whole-mask medians sit lower while p95 values reach cortical
  (T6 719, femur 958). The statistic and the range measure different
  things — stated, not reconciled away.
- **Liver 95, kidneys 116/117, spleen 90, aorta 115, chambers
  101–111, portal vein 112** — a coherent pattern at the enhanced
  soft-tissue band (round-02: soft tissue on contrast CT +100…+300;
  unenhanced blood +30…+45, unenhanced liver +40…+60 per design/06).
  Reading: this acquisition is **consistent with IV contrast
  enhancement**. The source metadata does not state contrast phase
  or agent, so that reading is recorded as an inference from the
  numbers — flagged, not asserted as a metadata fact.
- **Background disclosure:** 22.05% of the volume's voxels are below
  −1000 HU and 1,121,386 below the −1024 floor — non-physical values
  in the air/padding region **of the source data as distributed**
  (min −9571), carried unaltered under the no-remapping rule. Any
  window clips them to black like air; per-structure statistics are
  computed inside masks and unaffected in kind.

## 7. Viewer and verification

The imaging mode follows design/06's OHIF pattern at v1 scope:
series list (CT series + SEG overlay entry with the crosswalk
census), slice navigation (slider, buttons, wheel, arrow/page keys),
window/level with three presets — **soft tissue W350/L50, lung
W1600/L−600, bone W2000/L500**, each attested by ≥2 sources consulted
in-session (Stepwards' CT windowing fundamentals; FireVoxel's
grayscale-window documentation; citations ship in `imaging.json`) —
plus free W/L sliders, overlay toggle + opacity, a per-label legend
grouped by system (click isolates a label), hover HU/label readout,
and click-to-identify wired to the atlas record panel in both
directions (an atlas-selected record highlights its label here).
The SYNTHETIC banner is permanent in imaging mode.

`node tools/verify_web.js` — **ALL CHECKS PASS**, W1–W6 unregressed
plus W7: manifest synthetic declaration; presets == cited table;
crosswalk re-derived and equal; every mapped/candidate record id
resolves; per-label voxel counts **recounted from the shipped label
bins** and equal; watermark glyphs verified in every web slice and
every DICOM instance; all 431 DICOM files SHA-256-matched to
`series.json`, EVLE-parsed (BurnedInAnnotation, ImageType,
SeriesDescription, SOP Instance UID, InstanceNumber, IPP arithmetic
to 1e-3 mm), pixel data byte-identical to the web bins; viewer
wiring located. During the build, an independent parse caught a real
bug — the first DICOM writer omitted VR fields — fixed and
re-derived before verification.

Design/06's slice↔model agreement gate is **not** run in its stated
form: it presumes the registry and the slices describe one subject,
and here they deliberately do not (§2). The shipped substitute —
independent recount of the shipped bins + DICOM/bin pixel identity —
proves the series agrees with *itself* and with the manifest; it
does not prove spatial agreement with the atlas, and nothing here
claims it does.

## 8. What is NOT real

- **Single subject, axial only.** No MPR (coronal/sagittal reslicing),
  no volume rendering, no measurements/annotations yet — OD-06.1 is
  untouched. One study exists; nine more subjects are already local
  for later series.
- **The generative route in design/06 is unbuilt.** Design/06
  describes synthetic CT generated from the Body Model label map
  with per-structure HU sampling; v1 instead derives label map *and*
  intensities from one real research subject, per this milestone's
  specification. The two routes are different instruments (the
  generative one can render the atlas subject and engine pathology;
  this one is a real acquisition's intensities) — the difference is
  recorded here, not papered over.
- **Not validated by a DICOM toolkit.** No pydicom/dcmtk exists on
  this VM; conformance rests on the stdlib writer + two independent
  in-project EVLE readers (the build-time check and W7). A toolkit
  pass (pydicom/dcmtk validation) is owed before the series is
  offered to external DICOM tooling as proven.
- **Not exercised in a real browser on this VM** — the standing
  M6/M7/M16 limitation. What is proven: the data by independent
  readers, the codec-level wiring by source checks, the manifest
  contract by W7. Rendered-pixel behaviour of the imaging mode is
  unverified here.
- **Contrast phase unstated** (§6) and the source's sub−1000
  background values (§6) are properties of the adopted dataset,
  disclosed rather than corrected.

## 9. Next steps

1. MPR: coronal/sagittal reslicing from the same volume (the stored
   orientation makes this a pure re-index), then OD-06.1 can be
   decided with the 2D suite complete.
2. More subjects as series (nine already local), and the generative
   route decision: build design/06's label-map synthesis for the
   atlas subject, or keep imaging derived-only — a real fork, to be
   decided explicitly.
3. DICOM toolkit validation pass when a toolkit can be installed.
4. Still queued from earlier milestones: physiology contractility
   effector (M18), per-layer opacity in both shells (M16), pack
   compression/streaming for the web tier (M16).
