### 2. Surgical Simulation State of the Art

**Commercial / academic systems — interaction & assessment models to learn from (all proprietary; learn, do not reuse code or assets):**

| Item | What it gives us (as a benchmark) | License verdict |
|---|---|---|
| **Touch Surgery** (Digital Surgery / Medtronic) | Cognitive simulation: each procedure decomposed into steps + decision points (“learn” then unsupervised “test” mode), 3D + video. ~400 procedures / 17 specialties as of June 2025; 30+ peer-reviewed validation papers; integrated into 100+ US residency programmes | **Closed.** Free-to-use app, no reuse rights. Its *authoring model* (Front 11) is the lesson. https://en.wikipedia.org/wiki/Touch_Surgery |
| **Osso VR** | VR psychomotor training on Quest-class headsets, procedure modules with performance analytics; published RCT evidence for orthopaedic tasks | **Closed SaaS.** Benchmark for VR module design + metrics |
| **FundamentalVR / Fundamental Surgery** | VR + haptic arms (HapticVR), “surgical skills course” model with data capture per gesture | **Closed.** Benchmark for haptics-in-VR (Front 8) |
| **PrecisionOS** | VR orthopaedic training, deliberate-practice framing, cadaver-free repetition | **Closed** |
| **Surgical Science** (Simbionix LapMentor, RobotiX Mentor, etc.) | High-fidelity physical/VR hybrid laparoscopy & robotics trainers with validated metrics, the historical validation-study workhorse | **Closed hardware+software** |
| **CAE Healthcare / Medical Realities** | Scenario-based simulation / 360° and streamed operative content respectively | **Closed** |

**Open-source frameworks:**

| Item | What it gives us | License verdict for AGPL use | URL |
|---|---|---|---|
| **SOFA Framework** | FEM-first interactive simulation: DAG scene graph, separate mechanical / collision / visual models joined by mappings, tetra/hexa topologies, CUDA + multithreading options, haptics plugins. The research standard for deformable tissue | **YES with structure.** **Core LGPL-2.1-or-later; applications/tutorials GPL.** LGPL libraries link cleanly into an AGPL product; keep SOFA as libraries, do not vendor its GPL applications as your code base | https://github.com/sofa-framework/sofa/blob/HEAD/README.md ; https://www.sofa-framework.org/about/features/ |
| **iMSTK** (Kitware) | C++ surgical-sim toolkit: ECS scenes, PBD + SPH + level-set, continuous collision, haptics (OpenHaptics, Haply), VTK viewer (and a Vulkan renderer option), Unity/Unreal bridges. Used for lap. cholecystectomy, hiatal hernia, osteotomy, kidney biopsy sims | **Code YES (Apache-2.0) — project NO as a living dependency: SUNSET.** Kitware discontinued support/development **2 May 2025**; repo is archived and a 2026 reproducibility audit failed to build it from unresolved dependencies. Fork-and-own it, or mine it — do not plan on upstream | https://github.com/Kitware/iMSTK ; https://www.frontiersin.org/journals/virtual-reality/articles/10.3389/frvir.2023.1130156/full |
| **OpenSurgSim** (SimQuest) | FEM + rigid + SPH surgical platform with haptics | **Apache-2.0 but inactive** (developer defunct; no recent support). Reference only | (via comparison table: https://www.frontiersin.org/journals/virtual-reality/articles/10.3389/frvir.2023.1130156/full) |
| **PLUS Toolkit + 3D Slicer extensions** | Image-guided therapy plumbing: device tracking (OpenIGTLink), ultrasound, calibration; SlicerIGT / SlicerVR extensions | **BSD-style (Slicer ecosystem). YES.** The pragmatic route to tracked instruments / VR display inside a Slicer-based app | https://en.wikipedia.org/wiki/3D_Slicer |

**Evidence base (what actually transfers — see also Front 11):** deliberate practice to a **proficiency benchmark** (not time-based practice), distributed practice, expert feedback, and curriculum integration. Landmark: Seymour et al. RCT — VR-trained residents were 29% faster in the OR, 9× less likely to fail to progress, ~5–6× less likely to injure the gallbladder / burn non-target tissue. Sroka et al. RCT — FLS training *to proficiency* improved OR GOALS scores far more than controls (gain 6.1 vs 1.8 points). Scoring standards: **OSATS** (global rating + checklist, Reznick) and **GOALS** (laparoscopic global rating). https://pmc.ncbi.nlm.nih.gov/articles/PMC2917931/

