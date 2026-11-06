# Anatomica — Round 3: Depth & Specialization — Authoritative Quantitative Foundations

**System:** open-source (AGPL-3.0) medical simulation — 3D anatomy atlas, physiology engine, imaging suite, CTA-authored surgical simulator, clinical-reasoning workbench.
**Date researched:** 2026-11-05 (America/Chicago). **Method:** web-index research throughout; every fact below is flagged *index*. No claim in this round was verified in the live browser window — treat guideline *numbers* as high-confidence where two independent summaries agreed, and licence *verdicts* as careful readings of publisher/policy pages, not legal advice. **How to read openness:** **BUILD** = may embed data/text/numbers in the AGPL product (with attribution where required); **CITE-ONLY** = may teach the facts/numbers and link/cite, but may not copy text, figures, algorithms-as-images, or redistribute data; **CLOSED** = paywalled/subscription/credentialed content that cannot be shipped or scraped.

## Summary

The deep layer is buildable, but on a different basis than Rounds 1–2: the *numbers* of modern medicine (thresholds, doses, windows, pressures) are almost all facts that can be taught and encoded, while the *texts, charts and databases* that carry them are mostly cite-only or credentialed. Three hard boundaries dominate. (1) **Patient data:** only truly open sets (VitalDB CC BY 4.0, most PhysioNet Open Access sets, most TCIA CC BY collections) can ship with or train a distributed product; MIMIC-IV/eICU/HiRID/AmsterdamUMCdb are credentialed — usable by a credentialed developer for validation, never redistributable, so the engine must ship with synthetic/open data and treat MIMIC as an off-line validation harness. (2) **Guideline prose:** ASA, AHA, ASRA, IDSA, AABB, CLSI content is copyrighted even when PDFs are readable — encode the numbers as original logic, cite, never paste algorithms/figures. The big exceptions are US-government works (AHRQ TeamSTEPPS, CDC, WHO material, FLS-style facts via textbooks) which are genuinely reusable. (3) **Regulation:** a purely educational simulator with no patient-specific recommendation on real patients stays outside FDA device CDS and EU MDR device scope; the moment it processes a real patient's image/signal or directs a real patient's care it crosses Criterion 1 / Rule 11 into device territory (EU: at least Class IIa). Keep the educational intended-use statement, disclaimers, and “no real-patient use” boundary as load-bearing product features, not boilerplate.

---

## Findings

## (a) Consolidated Load-Bearing Numbers — by System Module

### ENGINE (physiology / monitoring / labs)
| Number | Value | Source front |
|---|---|---|
| ARDS VT / Pplat / oxygenation | 6 mL/kg PBW (4–8); Pplat ≤30 cmH₂O; SpO₂ 88–95% / PaO₂ 55–80 | §2 ARDSNet |
| MAP target, septic shock | ≥65 mmHg; NE → +vasopressin 0.03 U/min → +epinephrine | §2 SSC 2021 |
| RASS target (light sedation) | −2 to 0/+1 on −5…+4 scale | §2 RASS/PADIS |
| Transfusion triggers | 7 / 7.5 (cardiac) / 8 g/dL (ortho/CVD) | §2 AABB 2023 |
| Tissue moduli (ranges, method-tagged) | Brain 0.1–1 kPa; liver 0.3–6 kPa; muscle 8–17 kPa; skin MPa; bone 1–20 GPa | §5 |
| Reference interval definition | Central 95% (2.5th–97.5th %ile); n≥120/partition to establish, n=20 to verify | §6 CLSI EP28 |
| Critical values (representative) | K⁺ <2.5/>6.5; Na⁺ <120/>160; glucose <40/>500; Ca <6.0/>13.0 | §6 |
| Sepsis priors (ranges) | Pneumonia ~30% source; *E. coli* #1 (~21–32%); culture-negative up to ~30% | §7 |
| Pneumoperitoneum coupling | 12–15 mmHg → ↑SVR/PVR; ≥15 → ↓venous return/CO; renal flow −35–60% | §5 |

### THEATRE (anaesthesia / surgery / energy)
| Number | Value | Source front |
|---|---|---|
| Difficult-airway attempt limit | 3 + 1 (more skilled clinician) per modality; capnography confirms | §2 ASA 2022 |
| ASRA holds (neuraxial/deep block) | Enox low 12 h / high 24 h; apix high 72 h / low 36 h; clopidogrel 5–7 d; warfarin 5 d + INR normal; DOAC residual <30 ng/mL | §2 ASRA 5th |
| Electrosurgery | Cut = continuous low-V; coag = intermittent high-V; denature >60 °C, vaporise 100 °C; bipolar seals ≤7 mm; spread single-digit mm (0–7.64 range) | §5 |
| Insufflation | 12–15 mmHg adult working pressure; preset max 15; infants ~8 mmHg | §5 |
| Suture retention | Vicryl 75%@2wk; Monocryl ~50%@1wk; PDS 50%@4wk | §5 |
| Carotid / AAA | CEA symptomatic 70–99% NASCET ≤2 wk; AAA repair ≥5.5 cm (M) / ≥5.0 cm (F) | §4 |
| ICP / CPP / SBP (severe TBI) | Treat ICP >22; CPP 60–70; SBP ≥100/≥110 by age | §4 BTF |
| Compartment syndrome | Fasciotomy at ΔP ≤30 mmHg (diastolic − compartment) | §4 |
| Torsion salvage | ~100% <6 h; ~50% @12 h; <10% @24 h | §4 |

### IMAGING
| Number | Value | Source front |
|---|---|---|
| Carotid Doppler (≥70% NASCET) | PSV >230 cm/s; ICA/CCA >4.0; EDV >100 cm/s; NASCET vs ECST ≈ ×0.6+40 | §4 |
| Stroke imaging-linked windows | tPA ≤4.5 h; thrombectomy ≤6 h, selected ≤24 h; NIHSS ≥6, ASPECTS ≥6 | §3 |
| STEMI system times | ECG ≤10 min; D2B ≤90; transfer FMC-device ≤120; DIDO ≤30; lytic ≤30 min | §3 |
| TCIA use rule | CC BY collections shippable with DOI citation; BY-NC + Limited excluded/gated | §1 |

### CASES (reasoning / resuscitation / teamwork)
| Number | Value | Source front |
|---|---|---|
| Adult CPR | 100–120/min; 5–6 cm; epi 1 mg q3–5 min; biphasic 120–200 J / mono 360 J; amio 300→150 mg | §3 AHA 2020 |
| PALS | Depth ≥⅓ AP; 2→4→≤10 J/kg; epi 0.01 mg/kg; amio 5 mg/kg; cardioversion 0.5–1 J/kg | §3 AHA 2020 |
| NIHSS | 15 items, 0–42; Δ≥4 = significant | §3 |
| TXA | 1 g + 1 g/8 h (trauma); 1 g (PPH); benefit ≤3 h only | §3 CRASH-2/WOMAN |
| GCS | E1–4+V1–5+M1–6 = 3–15; severe 3–8 | §4 |
| Garden / Pauwels | I–IV displacement; <30° / 30–50° / >50° shear | §4 |
| Epistaxis ladder | Pressure 10–15 min → cautery → resorbable pack → posterior/admit | §4 AAO-HNS |
| Global targets | 5 bn unserved; +143 M procedures/yr; 20 SAO/100k; 5,000 procedures/100k | §9 |
| Validity reporting | Messick 5 sources; report ICC/α + standard-setting; unvalidated = formative only | §8 |

## (b) Updated Openness Map — Depth Layer

| Depth | Verdict | Examples |
|---|---|---|
| **BUILDABLE OPENLY** (ship it) | Data/facts under open or government licences + all bare clinical *numbers* re-expressed as original logic | VitalDB (CC BY 4.0); PhysioNet Open Access sets; TCIA CC BY collections; TeamSTEPPS/SBAR + CDC stewardship + WHO/DCP3 material (gov/CC); NIHSS & GCS & RASS scales; PEARLS/Reason/Messick as original implementations; all threshold/dose/window tables in this report |
| **CITE-ONLY** (teach + link, never copy) | Copyrighted guideline/journal content that is free or common to read | ASA 2022, AHA ACLS/PALS/ACS/stroke, ASRA 5th, PADIS/SCCM, SSC 2021, AABB guidelines, IDSA guidelines, AAO-HNS, BTF, ASCO strata, Lancet Commission report, Hoffman–Monroe paper, FLS physics *as taught in textbooks* (facts OK, modules not) |
| **CLOSED** (budget, licence, or stay out) | Paid, subscription, or credential-gated | MIMIC-IV / eICU / HiRID / AmsterdamUMCdb *data* (credentialed validation only, zero redistribution); TOXBASE monographs; Sanford Guide; Hopkins ABX; CLSI EP28 + AABB Standards (paid standards); AHA courseware/algorithm cards; SAGES FLS curriculum/tests; ASA/ASRA apps & figures |

**Net build rule for Round 3:** *Numbers are free; expression is owned; patient data is tiered.* If the team follows that one sentence — original wording/diagrams for every guideline, DOI/attribution for every open dataset, credentialed data kept entirely outside the shipped product, and an education-only intended-use boundary enforced in features as well as text — every depth in this round is buildable openly except the four CLOSED content sets, none of which is load-bearing.

## Could not verify

- **Laser-specific safety numbers** (wavelength exposure limits, plume/airway-fire quantified parameters): no primary source verified this round — §5 ships interim practice points explicitly unnumbered. Needs a dedicated pass (ANSI Z136.3 / AORN sources) before any laser wave.
- **TCCC May 2026 revision specifics** (tier expansion, suzetrigine analgesia, cefadroxil/ceftriaxone switch): single secondary source indexed; encode only the stable TCCC-vs-civilian contrasts until checked against the current JTS/Deployed Medicine guideline.
- **AHA/ASA/ACC full-text licence lines:** numbers were cross-checked across multiple agreeing secondary summaries because the primary *Circulation/JACC* texts sit in the journal ecosystem; before publication of the product's bibliography, confirm each number once against the primary guideline PDF.
- **DCP3 chapter-level licence:** DCP3 is distributed open-access in practice, but the exact CC line should be confirmed on the specific chapter used before mirroring any DCP3 table.
- **Arterial-wall high-strain modulus:** literature spans kPa (low-strain) to MPa (tensile) by method; the report gives both framings rather than a single value — the engine must pick a strain regime and document it.

## Sources

All retrieved via web index on 2026-11-05. Key URLs (verbatim): PhysioNet https://physionet.org/about/database/ · MIMIC https://mimic.mit.edu/docs/gettingstarted/ · TCIA https://www.cancerimagingarchive.net/data-usage-policies-and-restrictions/ · VitalDB licence https://vitaldb.metrology-atlas.org/data-and-licence.html · ASA 2022 (APSF) https://www.apsf.org/article/anesthesia-patient-safety-foundation-update-2022-american-society-of-anesthesiologists-practice-guidelines-for-management-of-the-difficult-airway/ · ARDSNet https://litfl.com/ardsnet-ventilation-strategy/ · AABB 2023 https://www.researchgate.net/publication/374681890_Red_Blood_Cell_Transfusion_2023_AABB_International_Guidelines · SCCM bundle https://sccm.org/blog/exploring-sccm-the-icu-centers-of-excellence-program · ASRA 5th https://lms.ehc.gov.eg/lms/mod/book/tool/print/index.php?id=742 · RASS https://www.physio-pedia.com/Richmond_Agitation-Sedation_Scale_(RASS) · Vasopressors https://www.uspharmacist.com/article/vasopressor-use-in-the-icu · ACLS https://deepmedicine.in/clinical/protocols/acls-algorithm.html · PALS https://www.statpearls.com/ArticleLibrary/viewarticle/18926 · NIHSS https://www.sismed-it.com/en/nihss-stroke-scale-calculator/ · STEMI 2025 https://sattimd.com/guidelines/acc-acs-2025.html · WOMAN https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(17)30638-4/fulltext · CRASH-2 https://coreem.net/journal-reviews/crash-2-tranexamic-acid-in-major-trauma/ · TCCC https://tccc.org.ua/en/guide/introduction-to-tccc · TOXBASE https://www.toxbase.org/information-for-toxbase-subscribers/ · Carotid/AAA https://thoracickey.com/vascular-trials/ · CABG https://www.mayoclinicproceedings.org/article/S0025-6196(22)00586-9/fulltext?sf174683232=1 · BTF/TBI https://sicu.eastbaysurgery.com/content/severe-tbi · GCS https://www.solvetutor.com/gcs/ · Garden/Pauwels https://achot.actavia.cz/pdfs/ach/2011/01/02.pdf · Torsion https://iaem.ie/download/197/paediatric/101064/testicular-torsion-v1-1.pdf · Cesarean https://www.acog.org/education-and-events/simulations/scog007/module · Epistaxis https://pcmedproject.com/ent/new-epistaxis-nosebleed-management-practice-guidelines/ · Moduli https://www.nature.com/articles/s41378-022-00412-z?error=cookies_not_supported&code=0dd99fa4-e844-481c-90ed-9ea274ba7b63 · Sutures https://wcvm.usask.ca/vsac205/Lab4/suture-materials.php · Thermal spread https://www.imrpress.com/journal/CEOG/46/6/10.12891/ceog5061.2019/htm · Insufflation https://www.Intechopen.com/chapters/18348 · Coagulation model https://derangedphysiology.com/main/cicm-primary-exam/haematological-system/Chapter-018/haemostasis-and-coagulation · CLSI EP28 https://meddeviceguide.com/blog/ivd-reference-interval-verification · Critical values https://www.ephlebotomytraining.com/critical-values-laboratory · IDSA https://www.idsociety.org/practice-guideline/all-practice-guidelines/ · Sanford access https://laneblog.stanford.edu/2025/07/01/be-an-antimicrobial-stewardship-with-sanford-guide/ · CDC stewardship https://www.in.gov/health/idepd/healthcare-associated-infections-and-antimicrobial-resistance-epidemiology/antimicrobial-stewardship/acute-care · Sepsis epi https://www.mdpi.com/2075-1729/16/1/121 · TeamSTEPPS https://www.ahrq.gov/teamstepps-program/curriculum/intro/teach/two-day.html · PEARLS https://www.healthysimulation.com/pearls-debriefing/ · Validity https://www.healthysimulation.com/healthcare-simulation-tool-validity/ · Global Surgery https://www.lse.ac.uk/lse-health/events/2022-23/surgical-outcomes/ · DCP3/volume https://pmc.ncbi.nlm.nih.gov/articles/PMC12435603/ · ASCO strata https://ascopubs.org/doi/pdfdirect/10.1200/GO.22.00217 · FDA CDS https://www.duanemorris.com/alerts/fda_issues_final_guidance_clinical_decision_support_software_1022.html · EU MDR Rule 11 https://www.meddevicecorp.com/mdr-classification/ · Simulation ethics https://www.dovepress.com/training-without-harm-rethinking-ethics-simulation-and-the-evolving-fu-peer-reviewed-fulltext-article-AMEP
