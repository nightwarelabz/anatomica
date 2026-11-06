# data/imaging — derived synthetic imaging series

Products of `tools/imaging_derive.py` (Milestone 19). Each subject
folder holds a DICOM-structured series derived from one
TotalSegmentator v1.0 subject held locally since the Milestone 3
intake, plus the derivation manifest (`series.json`: provenance,
geometry, per-instance SHA-256, watermark spec) and the label →
Body Model record accounting (`crosswalk.json`).

- Source data: TotalSegmentator dataset v1.0 (Zenodo 6802614),
  **CC BY 4.0**. The dataset is a published research dataset; no
  real patient data of any ANATOMICA user exists anywhere in this
  project.
- The series is **synthetic**: synthetic identifiers throughout,
  DICOM BurnedInAnnotation = YES, "SYNTHETIC" burned into the pixels
  of every slice and stated in Study/Series descriptions and
  ImageComments. Pixel values are the source subject's own CT
  intensities (see `series.json` pixel_route for the exact route).
- The DICOM files and the web slice bins under `web/data/imaging/`
  are build products of the derivation tool; re-running it
  regenerates them with fresh UIDs.
