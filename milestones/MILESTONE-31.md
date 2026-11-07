# ANATOMICA — Milestone 31: Imaging MPR — coronal/sagittal reslicing of the s0778 volume

**State: built and verified locally. Not uploaded (per-item approval stands).**

Milestone 19 shipped the imaging study axial-only and named MPR as
its first next step ("the stored orientation makes this a pure
re-index"). This milestone builds exactly that: the web imaging
viewer gains a tri-plane MPR layout — axial, coronal and sagittal
planes resliced from the same in-memory volume, crosshair-linked
from one shared voxel, with the label overlay and identification
behaving identically in every plane. `web/viewer.js` remains
byte-untouched; all of this lives in `web/imaging.js` + containers
in `web/index.html`, keeping the M19 module separation.

## 1. What was built

- **Tri-plane layout** (`#mprGrid` in `web/index.html`, toggled by
  the **MPR planes** button in the imaging bar): three panes, each
  with a plane canvas, a position readout in LPS mm, and a plane
  slider. The single-plane axial view remains the default and is
  unchanged.
- **Whole-volume load** (`imgLoadVolume`): on first MPR entry the
  viewer assembles the volume from the existing per-slice bins
  through the existing fetch path (862 files, 59.2 MB int16 HU +
  29.6 MB uint8 labels in memory). The stored DICOM series and bins
  are never written to; **MPR is display-only — no MPR files exist.**
- **Reslicing core** (`MPR CORE` block in `web/imaging.js`):
  `mprPlaneDims`, `mprPlanePhysical`, `mprVoxel`, `mprPixel`,
  `mprExtract`, `mprLps` — pure functions, no DOM, no viewer state,
  so the verifier can execute them verbatim (§5).
- **Navigation**: per-plane sliders, mouse wheel over any pane
  (steps that plane's through-coordinate), click in any pane (moves
  the shared crosshair voxel and identifies the voxel through the
  same panel path as the axial view), arrow/Page keys and the
  imaging-bar slice slider continue to drive the axial index, which
  the crosshair follows.
- **One shading path**: the axial renderer's per-pixel loop was
  factored into `imgPaint()`, now used by the axial view and all
  three MPR panes — window/level presets and overlay blending apply
  identically across planes by construction, not by parallel copies.

## 2. Geometry derivation — from the recorded sform, not assumed

Everything derives from the geometry Milestone 19 recorded in
`web/data/imaging.json` (read from the source NIfTI sform, asserted
diagonal at derivation):

- Dims (stored): cols 262 × rows 262 × slices 431.
- Spacing: (1.5, 1.5, 1.5) mm. First-slice IPP (LPS):
  (−209.998611, −384.684639, 1243.917969) mm.
- Stored voxel (c, r, k) centre in LPS mm:
  **x = −209.998611 + 1.5·c,  y = −384.684639 + 1.5·r,
  z = 1243.917969 + 1.5·k** (`mprLps`).

| plane | index | pixels (u × v) | physical extent | u axis | v axis |
|---|---|---|---|---|---|
| axial | k | c × r = 262 × 262 | 393.0 × 393.0 mm | c: patient left on screen right | r: anterior up |
| coronal | r | c × k = 262 × 431 | 393.0 × 646.5 mm | c: patient left on screen right | k: superior up (v = slices−1−k) |
| sagittal | c | r × k = 262 × 431 | 393.0 × 646.5 mm | r: anterior on screen left (viewed from the patient's left side) | k: superior up (v = slices−1−k) |

**Anisotropy**: this volume is isotropic (1.5 mm on every axis,
from the sform), so no axis needs corrective scaling and none is
applied — display aspect equals voxel aspect *because the spacings
are equal*, not because aspect is ignored. The pane fit is computed
from `mprPlanePhysical(plane, dims, spacing)` — physical extents
derived from the recorded spacing — so an anisotropic volume would
render true-shape. W10 proves the derivation responds to spacing
with an anisotropic probe (1/2/3 mm → axial 10×40 mm, coronal
10×90 mm, sagittal 40×90 mm on a 10×20×30 test shape). Nothing is
ever silently stretched: the only scaling is the uniform pane fit.

**Exactness law**: an MPR pixel *is* a stored voxel. Extraction is
pure re-indexing of the in-memory volume — no interpolation, no
resampling, no derived MPR data on disk. HU values and label
indices in the coronal and sagittal planes are the stored values,
byte-for-byte (proven in §5).

## 3. Crosshair correspondence

One shared voxel `img.vox = {c, r, k}` is the single source of
truth. Each plane's index is the voxel's coordinate on that plane's
through-axis (axial: k, coronal: r, sagittal: c); each plane draws
its crosshair at `mprPixel(plane, vox)` — the exact inverse of the
`mprVoxel(plane, idx, u, v)` that turns a click back into a voxel.
Clicking any plane therefore moves the lines in the other two, and
stepping any plane moves the crosshair in the other two, all from
the same coordinates. W10 roundtrips the pair on 304 voxels ×
3 planes (corners, both structure centroids, and a deterministic
pseudo-random sample).

## 4. Labels, window/level, watermark

- **Labels**: the label volume reslices through the same
  `mprExtract`, so hover and click in any plane read the identical
  label index the axial view reads, and identification runs through
  the one generalized `imgIdentify(c, r, k, plane)` — the M19
  crosswalk (93 mapped labels → Body Model records; the same record
  panel opens) and the 11 unmapped labels' ⚠ flagging are shared
  code, not per-plane copies.
- **Window/level**: one `imgPaint()` path (§1) — the three
  dual-cited presets (soft tissue W350/L50, lung W1600/L−600, bone
  W2000/L500) and the free sliders act on all planes identically.
- **Watermark**: MPR writes no files, so the file-level discipline
  has nothing new to attach to; it is enforced as:
  (a) *metadata* — unchanged: the manifest declares the series
  synthetic, the SYNTHETIC banner is permanent in imaging mode, the
  DICOM metadata verified by W7 is untouched;
  (b) *pixels* — the burned-in glyph voxels live in the volume data
  itself, so every MPR plane crossing the glyph slab carries them:
  the coronal plane at row 9 contains **8,620** glyph voxels
  (20 glyph columns at that row × 431 slices) and the sagittal
  plane at column 30 contains **3,017** (7 glyph rows × 431),
  counted in the shipped extraction by W10. (3071 HU occurs nowhere
  else in this volume — the whole-volume count is exactly the
  53,013 glyph voxels — so the counts are exact, not sampled.);
  (c) *on-screen* — every MPR pane additionally draws a SYNTHETIC
  overlay label, so planes that do not cross the glyph slab are
  still marked on screen.

## 5. Verification — W10, executed against the shipped data

`node tools/verify_web.js` gains **W10** (the W6/W8 pattern: the
shipped MPR core is sliced out of `imaging.js` and executed
verbatim in the verifier):

- plane dims equal the volume-derived values; physical extents
  equal spacing-derived values (393 / 646.5 mm) and follow the
  anisotropic probe;
- shipped `mprExtract` == an independent reslice written from the
  M19 geometry statement alone — 9 full planes (centroid and both
  extreme indices per orientation), HU and labels, pixel-for-pixel;
- **known-structure correspondence**: gallbladder centroid recounted
  from the bins at voxel (c 88, r 78, k 208), vertebrae_L3 at
  (c 132, r 172, k 176); `mprLps` of each equals the manifest LPS
  centroid (−77.54, −267.59, 1555.27) / (−12.73, −126.34,
  1508.35) mm, and the centroid voxel carries the same label and
  the same HU in all three planes (the M20 gallbladder recount's
  2,720 voxels reconcile with the manifest count in the recount);
- crosshair roundtrip, 304 voxels × 3 planes;
- watermark counts in the coronal/sagittal extractions (§4b), with
  every individual glyph position asserted present;
- wiring: panes, sliders, toggle, volume loader, on-screen
  SYNTHETIC overlay, shared `imgPaint` path located in source.

Full matrix after the change (baseline in parentheses — identical):

- `node tools/verify_web.js` — **ALL CHECKS PASS** (W1–W10).
- `python3 tools/case_check.py` — **5,145 passed, 0 failed**.
- `python3 tools/theatre_check.py` — **245 checks, 0 failures**.
- `python3 tools/assembly_check_all.py` — **ALL GATED CHECKS PASS**.
- physiology `cargo run --release -- validate` — **ALL HARD GATES
  PASS** (58 hard gates, exit 0; re-run after this milestone).
- native `cargo run --release -- verify` — **99 checks passed,
  0 failed** (468 assertions), render skipped (no wgpu adapter on
  this VM — the verify tool's own summary: "data and codec proven;
  pixels not proven on this machine"; the standing M28/M29-
  disclosed limitation; this milestone touches no native code,
  packs or geometry).

## 6. What is NOT real

- **Single subject still.** MPR reslices s0778; the other nine
  local subjects remain future series (M19 §9).
- **Oblique planes are out of scope — and are *not* implied by
  this math.** The reslice is exact because the sform is diagonal
  and the stored orientation axis-aligned: orthogonal planes are
  index permutations. An oblique plane cuts between voxels and
  would require interpolation, breaking the exact-voxel property
  §2 states. Building obliques is a separate decision with a
  stated interpolation rule, not a small extension of this code.
- **Thick-slab / MIP / minIP are different features** (aggregation
  across voxels — the displayed value would no longer be a stored
  voxel) — named future work, not built.
- **No MPR export.** Display-only is a deliberate scope line: an
  exported MPR image would need the file-level watermark
  discipline (metadata + burned pixels in the export itself)
  extended and verified first.
- **Not exercised in a real browser on this VM** — the standing
  M6/M7/M16/M19 limitation. What is proven: the data by
  independent readers, and the shipped reslice/crosshair math by
  verbatim execution (W10). Rendered-pixel behaviour of the
  tri-plane layout is unverified here.
- **First MPR entry loads the whole volume** (~89 MB of typed
  arrays, 862 fetches through the slice path, progress shown in
  the hover readout). Acceptable for the access tier's local/
  intranet setting; a packed single-file volume transfer is the
  obvious optimisation and is not built.

## 7. Next steps

1. **OD-06.1 can now be decided** with the 2D suite complete:
   axial + MPR + crosswalk identification are all in, verified at
   the data level.
2. More subjects as series (nine already local), each inheriting
   MPR for free — the core reads only dims/spacing/IPP from the
   manifest.
3. The DICOM toolkit validation pass (pydicom/dcmtk) still owed
   from M19 before the series is offered to external DICOM tooling
   as proven.
4. If oblique planes or slab modes are ever wanted, they enter as
   their own milestone with an explicit interpolation/aggregation
   rule and their own checker section — never as a silent option
   on this exact-reslice core.
