# Anatomica — State of the Art: Open-Source Medical Education & Simulation System
### Including Supplement 1 (Fronts 7–9: Native, VR/Haptics, Browser Ceiling), Supplement 2 (Front 10: The Frontier), Supplement 3 (Front 11: Accuracy & Validation)

*Research date: 2026-11-05/06. Basis: web index searches and page texts read in-session; items are flagged `index` unless noted. License verdicts are engineering assessments for an AGPL-3.0 product, not legal advice — every “adopt” item still needs a pinned-version license file check before vendoring.*

## Summary

- **The buildable core is genuinely open.** One verified body model can be derived legally today from **BodyParts3D (CC BY 4.0 as currently published by DBCLS)** supplemented by **TotalSegmentator (dataset CC BY 4.0, code Apache-2.0, 104 structures / 1,204 CTs)** and **Z-Anatomy (CC BY-SA 4.0, with non-commercial sub-parts that must be excluded)**, labelled with **FMA / TA2 terms (individual terms are public domain)** and cross-walked via **Uberon (CC BY)**.
- **Physiology:** do not write a validated engine from scratch if you can avoid it — **Pulse Physiology Engine (Apache-2.0)** is a real, validated, lumped-parameter whole-body engine forked from BioGears. A from-scratch educational engine should copy its architecture (circuit-analog compartments, 20 ms timestep, per-system literature validation tables), not its code if clean-room is required.
- **Imaging:** **OHIF Viewer + Cornerstone3D (both MIT)** are the uncontested web DICOM stack. Synthetic CT from a label map (label → Hounsfield mapping + noise/PSF) is standard practice and defensible for education if labelled as synthetic.
- **Native flagship (Supplement 1):** the AGPL-safe native stack is **wgpu (MIT/Apache) or Dawn (BSD-3) / bgfx (BSD-2) / raw Vulkan+Metal, VTK (BSD-3) for volumes, SOFA (LGPL core) or PhysX 5 (BSD-3) for tissue, Godot (MIT) as the only full game engine that is actually open source.** Unreal and Unity are *source-available / proprietary* and cannot be redistributed inside an AGPL product.
- **VR/haptics:** target **OpenXR** on **Quest 3** (default training headset); **HoloLens 2 is end-of-life** (production ended Oct 2024, support to 31 Dec 2027) — do not start on it. Apple Vision Pro is not OpenXR. Haptic SDKs (OpenHaptics, Force Dimension SDK) are proprietary freeware — isolate them behind a plugin boundary so the AGPL core never depends on them.
- **The frontier (Supplement 2):** even €100M+ / $350M+ programmes (EDITH, SPARC) have *not* produced a single integrated whole-body twin; they produced standards, repositories, organ models and roadmaps. The reachable frontier for a small OSS team is exactly those artefacts: **CellML/SBML/FieldML/SED-ML interoperability, SPARC/Physiome model repositories, and one-organ-at-a-time validated models** — not a cell-to-organ whole human.
- **Validation (Supplement 3):** correctness is the safety case. The field's standards are **Messick validity evidence, cognitive task analysis (CTA) authoring with expert Delphi consensus, proficiency-based progression with OSATS/GOALS scoring, and explicit anatomical-variant modelling with published prevalences.** Bile-duct injury data show harm comes overwhelmingly from *misperceived anatomy* (~97% perceptual, ~3% technical in the classic analysis) — a simulator that teaches one “normal” anatomy trains exactly that failure.

---

## Findings

## Shortlist — Highest-Leverage Assets to Adopt or Learn From

1. **BodyParts3D (CC BY 4.0)** as primary geometry + **TotalSegmentator (CC BY 4.0 / Apache-2.0)** for imaging-consistent labels — the only fully-clean, full-body foundation found.
2. **Pulse Physiology Engine (Apache-2.0)** — adopt or architecturally clone; do not compete with it on validation volume.
3. **OHIF + Cornerstone3D (MIT)** for the imaging suite; **FHIR (CC0 spec)** as the case-interchange format.
4. **Native stack: wgpu/Dawn or bgfx + VTK + SOFA (LGPL libraries) / custom XPBD (MIT reference) + OpenXR + Godot (MIT) where a full engine is wanted** — the only fully AGPL-compatible flagship combination.
5. **Physiome standards & repositories (CellML/SBML/FieldML/SED-ML, PMR) + SPARC Portal data** — free frontier interoperability and the missing autonomic-nervous-system anatomy.
6. **CTA + Delphi authoring pipeline with Messick-labelled validity evidence** — cheaper than any rendering feature, and the actual moat (Front 11).
7. **FMA/TA2/Uberon/Mondo (CC BY/CC0 family)** as the naming spine; SNOMED/LOINC only as separately-licensed packs.

## Licensing Traps to Avoid

- **SNOMED CT in the public repo** — affiliate licensing is territorial and non-redistributable; core-dependency = fatal.
- **Unreal / Unity as the “open-source” flagship's engine** — proprietary EULAs (Unreal: 5% royalty >$1M, Epic owns engine modifications) make the product not open source.
- **Z-Anatomy / BodyParts3D blanket imports** — Z-Anatomy contains CC BY-NC parts; BodyParts3D's legacy files say CC BY-SA 2.1 JP while the current DBCLS page says CC BY 4.0. Per-file provenance or nothing.
- **Visible Human “public domain” assumption** — it is NLM Terms & acknowledgement, not a CC licence.
- **TA2 / ICD-11 derivatives** — both are NoDerivatives for the *publication/classification*; use terms/codes as-is (TA2's individual terms are explicitly public domain).
- **HPO modification** — HPO forbids altering its content/relationships; layer beside it.
- **PK-Sim / Open Systems Pharmacology linking (GPL-2.0)** and **SOFA's GPL applications** — reimplement / use libraries only, pending a formal compatibility check.
- **PhysX GPU path as sole physics** — BSD-3 code, CUDA-only acceleration: a hardware trap, not a licence trap.
- **Proprietary haptic SDKs (OpenHaptics, Force Dimension) linked into the AGPL core** — isolate in optional plugins.
- **Sketchfab / TurboSquid / Zygote / BioDigital assets** — per-model NC/ND/editorial terms; never source the core atlas there.
- **HoloLens 2 as a new platform bet** — end-of-life hardware (support ends 31 Dec 2027).

## Could not verify

- **CT-ORG, MSD, SAROS, AbdomenAtlas individual licences** were not pinned to primary licence texts in this pass; §1 treats them conservatively (validation-only) until each is verified at its TCIA/project page.
- **DXplain, Isabel, Human Dx Project** current product/licensing status and effect sizes for Bayesian/calibration training were described from background knowledge, not pinned pages — verify before external citation.
- **Weasis** current licence, **Open Systems Pharmacology** current licence version, **CHAI3D** current dual-licence terms, and **PositionBasedDynamics** licence file should be confirmed at pin time (flagged in-line).
- **Dassault “Living Human”** as a product distinct from the Living Heart + organ-by-organ virtual-twin marketing was not separately documented from primary sources in this pass.
- No **documented case of a patient harmed specifically by inaccurate simulator content** was found in the literature searched — §11.5 reports the documented mechanisms (misidentification, negative training, conformity) instead of inventing one.
- Several 2026-dated sources returned by the index (e.g. market/aggregator pages) were used only for corroboration, never as sole support for a licence verdict.

## Sources

All URLs are cited in-line beside the facts they support. Principal primary sources: DBCLS BodyParts3D licence page; FIPAT/TA2 (Dalhousie); NLM Visible Human (https://www.nlm.nih.gov/research/visible/getting_data.html); SPL/Open Anatomy (nac.spl.harvard.edu, openanatomy.org); Pulse/Kitware (physiology.kitware.com, pulse.kitware.com); SOFA (sofa-framework.org, github.com/sofa-framework/sofa); iMSTK (github.com/Kitware/iMSTK, Frontiers in Virtual Reality 2023); OHIF (v3-docs.ohif.org); Cornerstone3D (github.com/cornerstonejs/cornerstone3D); wgpu (github.com/gfx-rs/wgpu); Dawn (dawn.googlesource.com); bgfx (bkaradzic.github.io/bgfx); Godot (docs.godotengine.org); Unreal (unrealengine.com); The Forge (github.com/ConfettiFX/The-Forge); PhysX (developer.nvidia.com, cgchannel.com 2025-04); 3D Slicer/VTK (en.wikipedia.org/wiki/3D_Slicer, Debian VTK sources); Khronos OpenXR conformance (khronos.org); Physiome Project (physiomeproject.org); SPARC outcomes (pubmed.ncbi.nlm.nih.gov/42693487, scienmag.com); EDITH/EU VHT (edith-csa.eu, digital-strategy.ec.europa.eu, virtualhumantwins.eu); Dassault (3ds.com); NVIDIA healthcare (nvidia.com); Medivis (emergenresearch.com, Core77); Intuitive curricula (Springer); Messick/CTA/validation and variation literature as cited in §11 and notes/front11-validation.md; working notes in notes/fronts7-10.md and notes/front11-validation.md.
