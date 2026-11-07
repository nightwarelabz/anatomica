# ANATOMICA — Milestone 7: Native Shell Skeleton (Rust + wgpu)

Date: 2026-11-06. Status: **built and verified locally, including
rendered-frame inspection; not uploaded.** The native shell renders
the real ANW1 packs on this headless VM through wgpu's GL backend on
llvmpipe — which also closes Milestone 6's largest open item: the
assembled body has now been *seen*, from four angles plus two
state variants, and the pixels match the data.

## Deliverables

| File | Content |
|---|---|
| `native/Cargo.toml` | Package `anatomica-native`, binary `anatomica`; wgpu 27, winit 0.30, glam, bytemuck, pollster, image, serde |
| `native/src/pack.rs` | ANW1 v2 pack reader with version handshake and full layout validation |
| `native/src/model.rs` | manifest.json / records.json model, slot-scheme resolution, record-panel text, pick-id codec |
| `native/src/camera.rs` | Orbit camera — the web shell's parameterisation and constants |
| `native/src/render.rs` | wgpu renderer: merged-buffer layers, shade + wireframe + pick pipelines, offscreen readback |
| `native/src/main.rs` | `anatomica verify` (headless verification renderer) and `anatomica view` (winit orbit viewer) |
| `native/tests/pack_data.rs` | Data-path integration tests over the real packs |
| `native/frames/*.png` | The six verification frames (release run; hashes below) |

## 1. Architecture as built vs design/08

The governing doc is `design/08-native-shell.md` (the brief's
"08-native-architecture.md" name does not exist; the shell doc was
followed). Built this milestone: the mesh-rendering core of the
flagship — Rust + wgpu, the same Body Model packs as the web shell,
per-structure records with the shared slot scheme.

Deviations and scope notes, named:

1. **Only the viewer slice of design/08 exists so far.** Not built:
   VTK volume rendering, the XPBD tissue core, the Theatre runtime,
   OpenXR, haptics plugins, egui chrome, installers. The design
   sequences those for later phases (UI depth is OD-08.2, decided at
   P5); this milestone is the render/data spine they attach to. The
   windowed mode's record panel is console text — the brief's
   sanctioned hook; no UI claim beyond that.
2. **Crate name:** design/08 names no crate. Chosen: package
   `anatomica-native`, binary `anatomica`.
3. **Version handshake:** design/08 requires the shell to refuse a
   model package whose schema major it does not implement. No
   separate Body-Model-package schema version exists yet, so the
   handshake is implemented against what does exist: the ANW1 pack
   version (only v2 accepted) plus a full manifest assertion at
   startup (§2) — a mismatched pack stops the shell before any
   rendering, in both modes.
4. **Pick-id layer byte — a web-shell bug found and NOT reproduced.**
   The web viewer's pick shader packs `(layer_bit << 24) | slot`
   into an RGBA8 target but writes only the low three bytes (alpha is
   fixed at 1.0); its decoder reconstructs 24 bits and computes
   `id >>> 24`, which is therefore always 0, so *every web pick
   resolves against the muscle ranges* regardless of what was
   clicked. Milestone 7's roundtrip unit test caught this before any
   native frame was drawn. The native shell keeps the documented id
   layout and slot scheme, but writes byte 3 into the alpha channel
   (alpha was already the hit flag: 0 = miss; layer bits are 1/2, so
   alpha ≠ 0 still means hit, and now carries the layer). The web
   viewer itself was **not** modified (out of scope here); fixing
   its decoder is a listed next step for a web milestone. Native
   pick results in §4 are layer-correct.
5. **Shading parity is deliberate:** the WGSL reproduces the web
   shell's two-light diffuse + specular model, layer colours,
   selection highlight (orange mix + dim-others 0.62), wireframe
   colour, background (0.043, 0.055, 0.075), FOV 0.72, near/far
   0.5/2000, and its orbit-camera equations, so the two shells show
   the same body the same way.
6. **View-mode surface format:** prefers a non-sRGB surface format
   so presented values match the offscreen path byte-for-byte, as
   the web canvas does. The view mode is compiled and code-complete
   but **has not been run** — this VM has no display; its first run
   is a next step, stated plainly.

## 2. Startup assertions (both modes, before any rendering)

18/18 PASS, printed by `verify` and enforced by `view`: per layer,
pack header vs manifest — records (199 / 359), vertices
(283,091 / 1,704,260), indices (1,535,904 / 7,096,476), edge indices
(1,596,168 / 8,028,654), exact file bytes (18,190,236 /
94,585,848) — plus range-table sums and a contiguity/dense-slot
tiling check over all 558 ranges.

## 3. Tests

`cargo build` and `cargo build --release`: green, zero warnings.
`cargo test` (debug and release): **8/8 pass** — 3 camera unit tests
(eye placement, centre projection, behind-camera rejection) and 5
integration tests over the real packs: manifest agreement (above);
per-record slot constancy across all 558 ranges with every index
proven local to its record's vertex range; per-record bounding boxes
recomputed from pack positions reproducing records.json for all 558
records (tolerance 2e-4 cm; the web smoke test's measured worst case
was 7.6e-6); pick-id roundtrip for both layers; version handshake
refusing a mutated v3 header and a bad magic.

## 4. Headless rendering — adapter, frames, verdicts

**Adapter actually used:** `llvmpipe (LLVM 20.1.2, 256 bits)`,
backend **Gl**, device type **Cpu**. The fallback chain worked as
designed: Vulkan initialisation failed first (`vkCreateInstance:
Found no drivers!` — this VM has no Vulkan ICD), then the GL backend
enumerated llvmpipe. GPU buffer upload of both layers: 633 ms
(release run).

Frames are 1024×1024, release binary. "Render" is wall time for
encode + submit + wait (llvmpipe is a CPU rasteriser — these are
floor numbers for this data, not GPU figures; the first frame also
carries pipeline/driver warm-up). Non-background fraction = pixels
differing from the clear colour.

| Frame | Render ms | Non-bg | Verdict (inspected) |
|---|---|---|---|
| front_skeleton | 863 | 0.0509 | Coherent full skeleton, anterior: skull with orbits and dentition, ribcage, hanging arms, hands, pelvis, legs; source pose visible (plantar-flexed feet). Lighting smooth, no inside-out shading. |
| side_skeleton | 320 | 0.0319 | Right-side profile (anterior screen-left, as the RH frame dictates): skull profile, spinal curves, ribcage slope, arm along the body, foot in profile. Coherent. |
| top_skeleton | 364 | 0.0177 | From directly above (posterior screen-up): skull vault with sagittal/coronal sutures centred, clavicles/shoulders, rib arcs, hands at the sides; the body's small footprint (64.8 × 25.4 cm) centred in frame, as projected. |
| close_skull | 588 | 0.2934 | Frontal-bone close view (az 0.35, pol 1.15, r 42 cm): sutures, specular highlight, orbits, nasal cavity, zygomatic arches, mandible with teeth, cervical column, clavicle. Dense facial meshes read correctly. |
| front_combined | 2,385 | 0.0916 | Both layers: musculature (red) over bone, registered to the same frame — skull exposed (head muscles are largely inventory-only in M4), sternum and abdominal midline show bone where M4 recorded muscles absent from BP3D (rectus abdominis among them) — the documented gap, visible, not papered over. |
| front_selection | 190 | 0.0509 | femur_right in the web shell's orange highlight, all other records dimmed ×(1−0.62); the highlighted femur is screen-left = subject right, as an anterior view requires. |

SHA-256 of the frames on disk (release run; the inspected debug-run
frames are byte-identical — same hashes): front_skeleton
`d012658a…`, side_skeleton `c3296dd3…`, top_skeleton `05744bfc…`,
close_skull `de8c49b7…`, front_combined `c635dc9e…`,
front_selection `2fc49148…`.

**Silhouette check** (skeleton frames): the GPU silhouette's pixel
extents vs two CPU references under the identical MVP — (a) every
pack vertex projected, (b) the assembled union box's 8 corners
projected. The union measured from records.json in-process:
**64.785 × 170.675 × 25.404 cm**, matching Milestone 3.

| View | GPU x / y | CPU-vertices x / y | Union-box x / y | Worst |GPU−CPU| |
|---|---|---|---|---|
| front | 362..661 / 127..914 | 361.9..662.1 / 126.8..914.8 | 358.6..665.4 / 107.3..915.6 | 1.08 px PASS |
| side | 452..568 / 123..920 | 451.6..569.3 / 123.1..921.3 | 447.0..576.1 / 77.6..945.2 | 1.30 px PASS |
| top | 368..655 / 435..566 | 368.0..656.0 / 435.1..567.5 | 306.6..717.4 / 432.1..593.1 | 1.45 px PASS |

The silhouette sits inside the union-box projection in every view
(the box's corners are mostly empty space — e.g. the front view's
box top at y 107 is the fingertip-span corner plane, not bone), and
tracks the exact vertex projection to ≤1.45 px (subpixel + coverage
rounding). Readback adds 1–6 ms per frame.

**Picking** (front view, both layers, id pass + 1-pixel readback):
forehead probe at the frontal bone's projected bbox centre →
**skeleton slot 0, "Frontal bone"**, with the full verified record
panel printed (TA name, classification, 12 articulations, bbox).
Thigh probe at femur_right's projected bbox centre → **muscles
slot 77, "right vastus medialis"** — the correct front-most surface
there (the muscle covers the femur from the front; the probe aimed
at the femur's centre, and depth did its job). Corner probe (4,4) →
no hit. Self-consistency: re-rendering the id pass with only the
picked record's range reproduces the same (layer, slot) — PASS.

## 5. What this closes, and what remains open

- **Milestone 6's open visual verification is now done** — by the
  native shell, on the same packs: the assembled skeleton and
  muscular layer are coherent, correctly framed, correctly lit, and
  pixel-consistent with CPU projections of the source data. (The
  web viewer's own in-browser appearance is still unmeasured, as
  M6 §5 states; the data it renders is now visually proven.)
- Frame unknowns carried from Milestone 3 are unchanged and still
  visible: no ground placement (feet float at the source origin),
  AP origin unregistered, source pose unnormalised. The camera
  targets the union centre, so framing is correct despite them.
- Known native-shell gaps: the `view` mode is unrun (no display);
  no LODs (full 2.88M triangles every frame — llvmpipe needs
  ~2.4 s for the combined frame at 1024²; a discrete GPU is the
  design's assumption, and design/08's frame-budget CI needs a GPU
  runner that does not exist yet); hover picking (web parity) not
  implemented — click picking only; the pick pass re-renders the
  full scene per query, as the web shell does.

## 6. Next steps

1. First `view` run on a machine with a display + a discrete-GPU
   frame-time reading on a recorded camera path (design/08 budget
   discipline starts there).
2. Fix the web viewer's pick decode (the dropped layer byte, §1.4)
   in a web milestone — one-line shader change there, plus its
   decode guard.
3. Pack the cardiovascular layer (M5 data) as a third ANW1 layer
   and add it to both shells.
4. LOD generation in the packer (per-structure decimation with the
   W-series checks re-run), then translucency/layer-peeling per
   design/08.
5. egui chrome + the clinical UI layer when OD-08.2 falls due (P5).
