### 4. Medical Imaging Tech

| Item | What it gives us | License verdict | URL |
|---|---|---|---|
| **OHIF Viewer** | Zero-footprint web DICOM platform: DICOMweb out of the box, modes/extensions, 2D/3D/MPR/MIP, segmentation (DICOM SEG), structured reports, whole-slide | **MIT. YES** | https://v3-docs.ohif.org/ |
| **Cornerstone3D** | The rendering/annotation engine under OHIF: WebGL rendering, WASM codecs, volume rendering, tools | **MIT. YES** | https://github.com/cornerstonejs/cornerstone3D/blob/main/README.md |
| **Weasis** | Mature cross-platform Java DICOM viewer (desktop counterpart) | Open source (verify current MPL/EPL terms at pin time). YES as a separate desktop tool | (not pinned this pass) |
| **3D Slicer** | Desktop imaging suite — see Front 9 | **BSD-style. YES**, with its “research software, not for clinical use” disclaimer inherited as a product-positioning fact | https://en.wikipedia.org/wiki/3D_Slicer |

**Synthetic CT from a label map (the imaging module's core trick):** assign each label a Hounsfield range from published tissue values (air ≈ −1000, fat ≈ −100…−50, water/soft tissue ≈ 0…+60 by organ, trabecular/cortical bone ≈ +300…+1900), render the label volume with partial-volume blending at boundaries, add calibrated noise + a point-spread blur, and optionally cross-check against real TotalSegmentator CTs. This is legitimate *if the UI permanently labels the study “synthetic, derived from [model], not patient data.”* **Volume rendering in the browser** is Cornerstone3D (WebGL) today, WebGPU compute paths emerging (Fronts 6/9). **Validation datasets:** TotalSegmentator CT/MRI (CC BY 4.0), plus the Front-1 research corpora under their own terms.

