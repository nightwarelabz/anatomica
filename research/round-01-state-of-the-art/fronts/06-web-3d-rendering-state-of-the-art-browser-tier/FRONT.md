### 6. Web 3D / Rendering State of the Art (browser tier)

| Item | What it gives us | License verdict | URL |
|---|---|---|---|
| **three.js** | De-facto WebGL/WebGPU JS engine; glTF pipeline, meshoptimizer ecosystem | **MIT. YES** | (standard — not pinned this pass) |
| **Babylon.js** | Full web engine with WebGPU-first renderer, strong medical demos | **Apache-2.0. YES** | (not pinned this pass) |
| **WebGPU (browser)** | Compute shaders + explicit GPU memory in Chrome (2023), Firefox on Windows (v141, 2025), Safari 26 (2025) — now cross-browser, but limits are conservative by spec (default maxBufferSize 256 MiB, maxStorageBufferBindingSize 128 MiB, 16 KiB workgroup storage, 256 invocations/workgroup) and platform gaps persist (Firefox on Linux/Android lagged at the Nov 2025 web.dev announcement) | **Standard, no licence barrier.** Design to runtime feature-detection, never assumption | https://www.aicassindra.com/blogs/gpu/gpu_webgpu.html ; https://wpdean.com/what-is-webgl/ |
| **Mesh-from-labels pipeline** | Marching cubes (and flying-edges / surface-nets variants) per label → decimation (meshoptimizer) → quantized glTF/GLB chunks streamed by system. Proven at BodyParts3D scale (2,234 meshes) by multiple downstream viewers | **Algorithms public domain / libraries MIT-Apache. YES** | https://github.com/enruben/human-atlas/blob/HEAD/public/ATTRIBUTION.md |
| **Open Anatomy Browser / TA2Viewer** (§1) | Reference UX: synced 3D + cross-section + hierarchy tree | See §1 | — |
| **Z-Anatomy / Open Anatomy Atlas (Shiv Nadar Univ. Chennai)** | Worked examples of a browser atlas on BodyParts3D/Z-Anatomy with peel-by-system, click-to-name, CT-like sectioning, quizzing | **Atlas code MIT (the Chennai project); data licences as §1.** Study the UX patterns | https://github.com/CognitionLabSNUC/open-anatomy-atlas |
| **BioDigital Human / Zygote / Sketchfab models** | Commercial polish benchmarks | **TRAPS:** BioDigital is a paid platform (embedding/API terms, no asset reuse); Zygote models are licensed per-product and not redistributable; Sketchfab downloads carry *per-model* licences including NC and no-derivatives variants and “editorial use” restrictions — a model that *looks* free there can poison an AGPL release. **Do not source anatomy from Sketchfab/TurboSquid/CGTrader for the core atlas** | (policy statement — no URL pinned this pass) |

**LOD strategy that works at whole-body scale:** per-system GLBs, per-structure quantized meshes, screen-size-based streaming, and a low-poly “proxy body” always resident. The browser is an excellent *atlas and imaging* tier — its simulation ceiling is Front 9.

---

