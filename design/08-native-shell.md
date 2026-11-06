# 08 — Native Shell (Flagship)

## Purpose

The flagship application: engine-grade rendering, tissue simulation, volume
imaging, and VR/haptics readiness — one Rust codebase over wgpu
(Vulkan/Metal/D3D12), consuming the same Body Model package and geometry
registry as the web shell.

## Stack (license positions verified in research round 1)

| Layer | Choice | License |
|---|---|---|
| Language | Rust | — |
| GPU abstraction | wgpu | MIT / Apache-2.0 |
| Windowing/input | winit + egui (UI chrome) — custom clinical UI layer on top | MIT / Apache-2.0 |
| Volume rendering | VTK via FFI, isolated in one crate | BSD-3 |
| Tissue physics | Custom XPBD core; SOFA (LGPL **libraries only**, never its GPL applications) where it earns its place | LGPL-2.1 libs |
| Rigid physics (instruments) | PhysX 5 permitted but never sole-path (GPU path is CUDA-only) | BSD-3 |
| XR | OpenXR (openxr crate); default target Quest 3; Varjo XR-4 compatible. Vision Pro is not OpenXR; HoloLens 2 is end-of-life — neither targeted | Apache-2.0 |
| Haptics | Plugin boundary only (3D Systems Touch / Force Dimension SDKs are proprietary freeware) | outside core |

Explicitly excluded: Unreal, Unity (proprietary EULAs — an AGPL flagship
cannot be built on them), iMSTK as a dependency (sunset May 2025).

## Rendering

- Mesh rendering from the geometry registry with per-structure LODs; tissue
  materials by structure kind; translucency and layer-peeling for dissection;
  arbitrary clipping planes with live cross-section fill from the label map
  (the same labels the imaging suite slices).
- Performance discipline: the graphics ceiling is set by the lab's standing
  target hardware class (integrated-GPU laptops must hold interactive rates
  on the mid LOD; discrete GPUs unlock full LOD + volumes). Frame budgets are
  measured in CI on recorded camera paths — a regression in the budget fails
  the build like a failed test.
- Volumes: VTK ray-cast CT volumes (real teaching sets) alongside synthetic
  label-map volumes from `06`.

## Tissue simulation

XPBD soft-body core with per-tissue parameters stored as **ranges with method
tags** (research round 3: published moduli vary ~an order of magnitude by
method — brain 0.1–1 kPa, liver 0.3–6 kPa, muscle 8–17 kPa, skin MPa range,
ligament 25–93 MPa, bone 1–20 GPa; shear vs Young's conflation is the known
trap). Cutting/deformation is credible here and only here; the web shell
never claims it. Electrosurgery and energy devices model thermal spread as
cited ranges (single-digit mm), not constants.

## Theatre runtime

Hosts the procedure runtime (guided/practice/assessment), the anaesthesia
panel, and the engine. Engine ticks are driven by the shell's fixed-step
scheduler (20 ms simulation step, decoupled render rate). Session recording =
engine input stream + camera/instrument stream; replay is bit-exact for the
engine portion (determinism contract, `04`).

## XR & haptics

OpenXR mode renders the Theatre in VR (Quest 3 default). Haptics load as
optional plugins behind a versioned C ABI; the core builds, runs, and is
fully assessable with no haptic device — justified by the evidence (2025
meta-analysis: box trainers beat haptic VR on learning curve, no significant
transfer difference). Marketing and UI copy may not claim haptic benefit
beyond the evidence (governance).

## Packaging

Single-binary installers per platform (Windows/macOS/Linux); the Body Model
package and content packs are data directories beside the binary, updated
independently of code releases. Fully offline after install.

## Verification gates

- Builds clean on all three platforms in CI; frame-budget tests pass.
- Registry/model version handshake: the shell refuses a model package whose
  schema major version it does not implement (no silent misreads).
- No-proprietary-linkage audit: binary dependency scan proves no haptic SDK
  or GPL-application code is linked into the core.

## Open decisions

- **OD-08.1** VTK via FFI vs a native Rust volume renderer long-term. VTK is
  the P6-era answer (BSD-3, field standard); a Rust renderer is a possible
  P9+ consolidation. Flagged, not decided.
- **OD-08.2** UI framework depth: egui for chrome + custom canvas for clinical
  views is the starting point; if the Theatre's instrument UI outgrows it,
  revisit with a spike. Decide at P5.
