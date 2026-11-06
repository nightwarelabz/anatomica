### 9. Native vs Browser Ceiling — What the OSS Community Actually Builds On [Supplement 1, extends Fronts 2/3]

**The actual stacks:**

| Platform | Internals | Rendering | License |
|---|---|---|---|
| **3D Slicer** | C++ core + Python scripting, **Qt** UI, built on **VTK** (visualisation) + **ITK** (segmentation/registration); modular extension system (SlicerIGT, SlicerVR, SlicerSOFA in progress via NA-MIC Project Weeks) | VTK OpenGL2 render windows; GPU volume ray-casting; VR via VTK's OpenVR/OpenXR support | **BSD-style Slicer licence** (no academic/commercial restriction; carries “not FDA-approved / research use” positioning) https://en.wikipedia.org/wiki/3D_Slicer |
| **VTK** (Kitware) | Pipeline dataflow (sources→filters→mappers), polydata/image/unstructured-grid data models, marching cubes/flying edges, DICOM IO | OpenGL today; VTK-m/Viskores GPU work and WebGPU experiments are the stated direction | **BSD-3-Clause** https://sources.debian.org/src/paraview/5.13.2%2Bdfsg-3/VTK/Documentation/docs/about.md/ |
| **SOFA** | C++ component DAG; each object has decoupled mechanical/collision/visual models joined by **mappings**; scenes authored in XML/Python; runSofa GUI is a thin shell | Built-in OpenGL visual model rendering (adequate, not pretty); many projects render externally (Slicer, Unity bridge) and use SOFA purely as the physics server | **Core LGPL-2.1+; apps/tutorials GPL** https://www.sofa-framework.org/about/features/ |
| **iMSTK** | C++ ECS + modules; PBD/SPH physics; **VTK viewer by default** (OSMesa offscreen option), experimental **Vulkan renderer**, PhysX among its physics backends, OpenHaptics device layer | VTK (OpenGL) primarily | **Apache-2.0; project sunset 2 May 2025** https://github.com/Kitware/iMSTK |
| **Pulse** (Front 3) | C++ engine, circuit solvers (Eigen), protobuf data model — *no renderer at all* by design; hosts embed it | n/a | Apache-2.0 |

Pattern: **the community builds C++/Qt/VTK desktops and treats rendering as the least differentiated layer.** Nobody in OSS medical simulation builds on a game engine first; game engines appear only via bridges (iMSTK→Unity, SOFA→Unity).

**Honest browser-vs-native comparison (the platform decision):**

| Dimension | Browser (WebGPU/WebGL, WASM) | Native (wgpu/Dawn/Vulkan/Metal + C++/Rust) |
|---|---|---|
| Reach | Zero-install, any OS, instant updates — unbeatable for atlas/imaging/quiz distribution | Installer + signing/notarisation per OS; institutional IT friction |
| GPU compute | Real compute shaders now, but **spec-default limits are low** (256 MiB max buffer, 128 MiB storage binding, 16 KiB workgroup memory, no FP64 guarantee, optional f16/subgroups), browser/driver variance, tab can be killed under memory pressure | Full Vulkan/Metal limits, multi-GB buffers, FP64 where hardware supports, CUDA available (PhysX GPU, custom FEM) |
| Tissue simulation ceiling | XPBD on modest tet meshes (tens of thousands of constraints) is feasible in WebGPU compute; **nonlinear FEM with implicit solvers, topology change (cutting) at scale, and coupled FEM+fluids are not credible in-browser today** | SOFA-class FEM, PhysX GPU FEM/PBD, MPM research codes (e.g., GPU MPM cutting/suturing demos) all run natively; still hard, but possible |
| Haptics | **Disqualifying for serious haptics:** browsers cannot guarantee a 500–1000 Hz servo loop (JS/WASM timers, GC, event-loop jitter); WebHID/WebUSB add latency and permission friction | Dedicated 1 kHz thread/process, direct USB SDK access — the only defensible haptics path |
| VR | WebXR works on Quest Browser but with store/discovery and performance compromises | Native OpenXR, full refresh/compositor control, Varjo-class headsets are PC-only |
| Assets/data | Multi-GB atlases must stream/chunk; offline is PWA-best-effort | Local multi-GB datasets, DICOM archives, patient data stay on-device (a privacy/regulatory plus) |
| Determinism/QA | Browser × OS × GPU matrix is unownable | Pinnable binaries, reproducible validation runs (matters for Front 11 evidence) |

**Recommendation encoded in this report:** *one body model, two shells* — native flagship (wgpu/Dawn + VTK volumes + SOFA/XPBD tissue + OpenXR + plugin haptics + Pulse physiology) and a browser companion (three.js/Cornerstone/OHIF) sharing the same asset pipeline, case format (FHIR-based) and scoring. Do not attempt tissue-cutting or haptics in the browser tier and claim parity.

---

