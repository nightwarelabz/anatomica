# 06 — Imaging

## Purpose

Radiology rendered from the same Body Model the atlas shows and the Theatre
operates on — so an image, a slice, and the 3D structure are one fact in three
views, identified by the same name in the same place.

## Architecture

Patterned on OHIF Viewer + Cornerstone3D (both MIT) — the field's open DICOM
stack — adapted to a synthetic-first pipeline:

- **Study model:** DICOM-shaped objects (study/series/instance metadata, our
  own synthetic UIDs) so real DICOM tooling and habits transfer; real DICOM
  import is supported for teaching sets whose licenses allow (TCIA: most
  collections CC BY 3.0/4.0 with DOI citation; CC BY-NC and Limited Access
  collections excluded).
- **Viewports:** hanging protocols, MPR (axial/coronal/sagittal), window/level
  presets (soft tissue / bone / lung), measurement and annotation tools with
  structure-ID binding — click a structure in a slice, the atlas record opens;
  select a structure in the atlas, its slices highlight.

## Synthetic CT

Generated from the Body Model label map (TotalSegmentator label set as the
floor — 104 structures; BodyParts3D-registered labels as they land):

- Per-structure Hounsfield assignment from published tables (water 0, air
  −1000, fat ≈ −120…−90, liver 40–60, cortical bone +500…+1900), stored as
  **cited ranges per structure kind**, sampled per voxel with noise and a
  point-spread model so slices read as the modality, not as a diagram.
- Pathology is engine/model state (effusion, pneumothorax, fracture, occlusion)
  — the pneumothorax on the film is the one the physiology engine is
  simulating and the one the Theatre decompresses.
- **Watermarking:** every synthetic image carries a burned-in "SYNTHETIC —
  educational model" marker plus metadata flags. Non-removable in export
  paths the product controls. (Precision/governance rule; also the regulatory
  line in round 3, front 10.)
- **Calibration:** synthesis parameters are validated against real CT
  (TotalSegmentator's dataset; TCIA open collections) by comparing per-structure
  HU histograms; the calibration report ships per release.

## Other modalities

- **Radiographs:** density projections from the label map at any angle;
  structure identification on hover/click.
- **Ultrasound:** probe-driven fan views for FAST and standard windows at
  schematic fidelity, honestly labelled — FAST is taught with its real
  performance (Cochrane 2018: sensitivity 0.74, specificity 0.96 — rules in,
  never out) and the workbench scores reliance on a negative FAST accordingly.
- **MRI-style weightings:** T1/T2 emphasis as rendering modes over the same
  label map with per-kind signal tables (cite-only sources flagged where the
  primary text could not be verified — round 2 noted MRI basics among its
  partially verified items; the tables ship only when dual-sourced).

## Reference content policy

ACR Appropriateness Criteria: free to browse, © ACR, redistribution not
permitted — the workbench may *link and cite*, never ingest. Radiopaedia:
CC BY-NC-SA 3.0 with contributor-owned images — link/cite only, never ingest.
These fences are enforced by the content checker (a content pack referencing
an ingested asset from a fenced source fails validation).

## Verification gates

- HU table dual-source check (each kind's range has ≥2 citations).
- Watermark presence test on every synthetic export path.
- Slice↔model agreement test: for a sample of structures, the centroid of the
  label in the slice stack matches the registry bounding box within tolerance.
- Calibration report present and current per release.

## Open decisions

- **OD-06.1** Volume rendering in the web shell: WebGPU compute vs server-free
  2D MPR only. Native shell uses VTK volumes regardless. Decide at P6 with
  measured WebGPU coverage; MPR is the guaranteed floor in both shells.
- **OD-06.2** Real-DICOM teaching sets: adopt a TCIA CC BY collection in-tree
  (size cost) vs link-only. Leaning: one small, high-value collection in-tree
  for calibration; the rest link-only with DOIs.
