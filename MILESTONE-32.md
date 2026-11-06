# ANATOMICA — Milestone 32: Imaging — second subject through the full pipeline + viewer subject switching

**State: built and verified locally. Not uploaded (per-item approval stands).**

Milestone 19 derived one TotalSegmentator subject (s0778) into a
DICOM-structured synthetic CT series with a Body Model crosswalk;
Milestone 31 gave that volume tri-plane MPR. This milestone runs
the **second** subject through the identical pipeline, restructures
the web manifest into a combined multi-subject form, teaches the
viewer to switch subjects coherently, and parameterizes the W7/W10
checkers so both subjects are exercised end to end. `web/viewer.js`
remains byte-untouched.

## 1. Subject selection — the Milestone 19 rule, computed

M19's rule: the most complete locally held subject, measured by
non-empty label masks. The ranking below was recomputed from the
masks on disk for all 10 subjects (104 labels each):

| rank | subject | non-empty /104 | study type (meta.csv) | age/sex | dims (cols×rows×slices) | z-extent |
|---|---|---|---|---|---|---|
| 1 | **s0778** (derived, M19) | 98 | ct thorax-abdomen-pelvis | 57 m | 262×262×431 | 646.5 mm |
| 2 | **s1090** (this milestone) | **95** | ct thorax-abdomen-pelvis | 80 m | 257×257×439 | 658.5 mm |
| 3 | s0480 | 71 | ct abdomen | 73 m | 233×233×328 | 492.0 mm |
| 4 | s1405 | 70 | ct angiography abdomen-pelvis | 74 m | 255×255×287 | 430.5 mm |
| 5 | s0937 | 67 | ct angiography pelvis-leg | 81 m | 253×253×548 | 822.0 mm |
| 6 | s0330 | 41 | ct intervention | 67 f | 330×330×88 | 132.0 mm |
| 7 | s1250 | 40 | ct aortic valve | 73 m | 219×219×59 | 88.5 mm |
| 8 | s0167 | 37 | ct neck | 35 f | 177×177×149 | 223.5 mm |
| 9 | s0000 | 21 | ct pelvis | 32 f | 294×192×179 | 268.5 mm |
| 10 | s0633 | 15 | ct upper leg left | 76 f | 166×166×326 | 489.0 mm |

The best remaining subject is **s1090** (80 y, male, institute A,
train split) — no exception to the rule was needed: its coverage is
the same thorax-abdomen-pelvis class as s0778, so the crosswalk and
case links carry the same meaning. (Its one known gap, the urinary
bladder, was already noted at M19.)

## 2. What was built

- **Derivation of s1090** by the unmodified pipeline route
  (`python3 tools/imaging_derive.py s1090 "Milestone 32"`):
  `data/imaging/s1090/` — 439 DICOM instances (58,688,706 bytes),
  `series.json`, `crosswalk.json` — plus web slice bins under
  `web/data/imaging/s1090/` (878 files, 86,986,533 bytes). Every M19
  assertion held for this subject: diagonal sform asserted, spacing
  read from the sform (1.5 mm isotropic, not assumed), and the
  **int32 → int16 conversion asserted lossless** (stored range
  −3457…+3931, inside int16). No remapping, no resampling; HU
  statistics computed before the watermark; the watermark is the
  identical discipline (SYNTHETIC glyphs at 3071 HU, same offsets,
  metadata + pixels): 123 voxels/slice × 439 = **53,997** glyph
  voxels.
- **Tool parameterization** (`tools/imaging_derive.py`): the
  milestone label and the per-subject selection reason are now
  inputs (DICOM Study ID / implementation name / ImageComments
  follow the milestone), defaulting to exactly the Milestone 19
  values, so s0778's derivation recipe is unchanged. The web
  manifest write became a **merge**: the tool emits its subject's
  block and preserves the others.
- **Combined web manifest** (`web/data/imaging.json`): shared meta
  (synthetic declaration, the dual-cited window presets, HU table
  sources, the provenance note) + `default_subject` + one block per
  subject (banner, subject provenance, pixel route, geometry, file
  patterns, crosswalk totals, labels). s0778's block was **folded
  in verbatim** from the M19/M31 flat manifest — the earlier subject
  was NOT re-derived; its `series.json`, UIDs and DICOM hashes are
  the M19 originals (W7 re-verifies them below).
- **Viewer subject switching** (`web/imaging.js`, `#imgSubjects`
  in `web/index.html`): one button per manifest subject.
  `imgApplySubject()` makes a subject active — `img.man` becomes
  its effective manifest (shared meta merged with its block) — and
  rebuilds the banner (which names the active subject), series
  list, and legend, and resets the slice slider range, canvas size
  and MPR slider ranges. **No volatile state crosses a switch:**
  the slice cache and the whole MPR volume are dropped, label
  isolation is released, MPR closes (its volume belongs to the old
  subject), the hover readout clears, and the crosshair re-centres;
  the start slice follows the M19 rule for the new subject (its
  liver-centroid slice). Two async guards close the mid-flight
  races: a slice fetch that completes after a switch is not written
  into the new subject's cache, and a volume load that finishes
  after a switch is discarded instead of installed. Event handlers
  are registered once and read the active subject at event time.
  MPR works for both subjects unchanged — the M31 core reads only
  dims/spacing/IPP from the active manifest.
- **Checkers** (`tools/verify_web.js`): W7 and W10 are parameterized
  per subject and run against **both** subjects (§5).

## 3. Per-subject census, side by side

| | s0778 (M19) | s1090 (M32) |
|---|---|---|
| subject | 57 y m, institute A, train | 80 y m, institute A, train |
| study | ct thorax-abdomen-pelvis | ct thorax-abdomen-pelvis |
| dims | 262×262×431 | 257×257×439 |
| spacing | 1.5 mm isotropic (sform) | 1.5 mm isotropic (sform) |
| first-slice IPP (LPS mm) | (−209.999, −384.685, 1243.918) | (−191.154, −151.354, −672.250) |
| stored HU range | −9571…+3526 | −3457…+3931 |
| labels present | 98 | 95 |
| labels absent | 6 — brain, vertebrae_C1–C5 | 9 — brain, face, urinary_bladder, vertebrae_C1–C6 |
| mapped + present | 87 | 85 |
| mapped + absent | 6 | 8 |
| unmapped + present | 11 | 10 |
| unmapped + absent | 0 | 1 (face) |
| records reachable (present labels) | 90 | 88 |
| records reachable (all mapped labels) | 96 | 96 |
| mask voxel claims | 6,424,824 | 5,779,826 |
| contested voxels (≥2 masks) | 6,103 | 5,037 |
| labelled voxels (reconciles exactly) | 6,418,721 | 5,774,789 |
| DICOM | 431 instances, 59,860,063 B | 439 instances, 58,688,706 B |
| web bins | 862 files, 88,756,692 B | 878 files, 86,986,533 B |
| watermark glyph voxels | 53,013 | 53,997 |

Differences stated as data: s1090's present-label set is a **strict
subset** of s0778's — the only labels present in s0778 but absent
here are `face`, `urinary_bladder` and `vertebrae_C6`. The three
fewer reachable records (90 → 88) follow from the bladder and C6
absences. Nothing about the second subject extends label coverage;
what it adds is a second individual (§6).

## 4. Crosswalk — one mapping table, two accountings

The label → record mapping is label-level, not subject-level: the
tool builds it once from the M3 skeletal rules + the inventory
`totalsegmentator_overlap` blocks, identically for any subject.
That is now **proven, not just constructed**: W7 asserts the mapping
fields (status, record ids, note, candidates, system group, colour)
of every label are identical in the two subject blocks, and
re-derives the expected table independently for each subject.
Per-subject accounting — presence, voxel counts, HU statistics,
LPS geometry — differs, as the census shows. Both subjects: 93
mapped / 11 unmapped of 104.

HU spot comparison (label medians, HU; statistics computed
pre-watermark in both):

| structure | s0778 | s1090 |
|---|---|---|
| muscle, median-of-medians (10 labels) | 49.5 | 42.0 |
| liver | 95 | 101 |
| kidney L / R | 116 / 117 | 118 / 116 |
| spleen | 90 | 96 |
| aorta | 115 | 116 |
| lung lobes, medians | −907…−649 | −892…−768 |
| bone (skeletal labels), median | 242.5 | 294.0 |

Reading, with the M19 caveats carried over unchanged: muscle sits
inside the cited 35–55 band in **both** subjects (49.5 and 42.0) —
the one cited-range validation now holds on two individuals. The
soft-tissue pattern (liver/kidney/spleen/aorta ≈ 90–118) is again
consistent with IV contrast enhancement; the source metadata does
not state contrast phase for either subject, so that remains an
inference from the numbers, flagged, in both. Bone whole-mask
medians sit below the cited cortical range for the M19 reason
(masks enclose trabecular bone and marrow; p95 reaches cortical).
Background disclosure, s1090: **26.40%** of voxels are below
−1000 HU and 6,383,076 below the −1024 floor — non-physical values
in the air/padding region **of the source data as distributed**,
carried unaltered under the no-remapping rule (s0778: 22.05%).

## 5. Verification — full matrix

- `node tools/verify_web.js` — **ALL CHECKS PASS** (W1–W10).
  W7 now checks, per subject: manifest/series agreement, crosswalk
  == independent re-derivation, totals reconcile, per-label voxel
  recount from the shipped bins, watermark glyphs in every web
  slice and every DICOM instance, DICOM SHA-256 == series.json,
  EVLE metadata, IPP arithmetic, DICOM↔bin pixel identity — plus
  the combined-manifest checks (subjects == series on disk,
  default valid, every banner names its subject, mapping table
  shared). W10 executes the shipped MPR core per subject:
  s0778 reproduces the M31 numbers exactly (gallbladder centroid
  (88, 78, 208), vertebrae_L3 (132, 172, 176), 8,620 + 3,017 glyph
  voxels in the coronal/sagittal reslices); s1090 passes the same
  suite on its own geometry (gallbladder (78, 81, 202),
  vertebrae_L3 (125, 145, 187); 8,780 + 3,073 glyph voxels =
  glyph positions × 439 slices); the anisotropic-spacing probe
  still proves the physical-extent derivation.
- `python3 tools/case_check.py` — **5,145 passed, 0 failed**.
- `python3 tools/theatre_check.py` — **245 checks, 0 failures**.
- `python3 tools/assembly_check_all.py` — **ALL GATED CHECKS PASS**.
- physiology `cargo run --release -- validate` — **ALL HARD
  GATES PASS**.
- native `cargo run --release -- verify` — **99 checks passed,
  0 failed** (data/pack assertions); the GPU render stage cannot
  initialise on this VM (no wgpu adapter — the standing M28–M31
  limitation; this milestone changes no native code, packs or
  geometry).

## 6. What the second subject proves — and what it does not

Proves:
- The pipeline is subject-general, not fitted to s0778: a different
  grid (257×257×439 vs 262×262×431), a different IPP, a different
  stored range and different absence pattern all flowed through
  with every derivation assertion holding (diagonal sform, int16
  losslessness, claim reconciliation to the voxel).
- The crosswalk is genuinely label-level: one mapping table,
  asserted identical across subjects, with per-subject accounting.
- MPR inherits for free, as M31 predicted: the reslice core needed
  no subject-specific change, and W10 proves exactness on the
  second volume independently.
- The viewer has coherent multi-subject state discipline (switch =
  rebuild + reset, with the mid-flight fetch races closed).

Does not prove:
- **Anything cohort-shaped.** Two subjects is not a cohort. Both
  are male, both from institute A, both train split, both the same
  study type, both (by the HU inference) contrast-enhanced
  acquisitions. The muscle-band agreement is two points, not a
  validation distribution.
- **New anatomy.** s1090's label set is a subset of s0778's (§3);
  coverage of the *label space* did not grow. The remaining eight
  subjects are mostly narrower studies (next by rule: s0480,
  abdomen, 71 labels) — deriving them adds individuals, and in
  some cases (neck, pelvis, leg) field-of-view variety, but the
  93/11 mapping split will not move until a mapping tranche does.
- **Rendered behaviour.** See §7.

## 7. What is NOT real

- **Not exercised in a real browser on this VM** — the standing
  M6/M7/M16/M19/M31 limitation, now applying to the switcher too.
  What is proven: both subjects' data by independent recount, the
  MPR math by verbatim execution per subject, and the switching
  wiring/state discipline by source-level assertion (W7). The
  rendered-pixel behaviour of a subject switch is unverified here.
- **Not validated by a DICOM toolkit** — the M19 debt stands for
  both series (stdlib writer + in-project EVLE readers only).
- **Contrast phase unstated** for both subjects (§4) and the
  sources' sub−1000 background values are properties of the
  adopted dataset, disclosed rather than corrected.
- **No co-registration** between either imaging subject and the
  atlas individual (or between the two imaging subjects) is
  claimed — identity is shared, space is not, now ×2.

## 8. Next steps

1. Remaining subjects are derivable on demand in rule order
   (s0480 next). Each is a mechanical run + checker pass now; the
   decision worth making explicitly is whether narrower-coverage
   series (neck s0167, pelvis s0000) earn their place in the viewer
   or stay derived-only.
2. OD-06.1 remains decidable with the 2D suite complete and now
   multi-subject.
3. The DICOM toolkit validation pass (pydicom/dcmtk) is still owed
   before either series is offered to external DICOM tooling as
   proven.
4. The generative route decision from M19 §9 (design/06 label-map
   synthesis for the atlas subject vs derived-only imaging) is
   still open and still a real fork.
