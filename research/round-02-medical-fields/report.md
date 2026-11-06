# Medical Simulation System — Authoritative, Quantitative State of Knowledge
## For an open-source (AGPL-3.0) system: 3D anatomy atlas · physiology engine · imaging suite · surgical procedure simulator · clinical-reasoning workbench

Research date: 5–6 November 2026 (CST). Method: web index searches, primary publisher / society / agency pages preferred. **Openness verdict key:** ✅ OPEN — can be built on / redistributed in an AGPL educational product (with attribution as stated) · 🟡 CITE-ONLY / NON-COMMERCIAL — read, link, cite numbers as facts, do not copy text/data wholesale · 🔴 PAYWALLED / LICENCE-REQUIRED — do not ingest; teach from own paraphrase of facts or obtain licence. *Facts (numbers, classifications) are not copyrightable in themselves in most jurisdictions; expression, tables as published, images and databases are. This report is not legal advice.*

## Summary

A citable open foundation exists for the **engine** of the system — physiology numbers (OpenStax, Guyton-derived published values), imaging physics (Hounsfield scale), drug classification (WHO ATC/DDD searchable free), US drug labels/adverse events (openFDA, public domain), PK/PD models (OpenTCI / SimTIVA GPL, R `tci` CRAN), 3D anatomy geometry (BodyParts3D + HuBMAP Human Reference Atlas, both CC BY 4.0; Visible Human, no licence required since 2019), epidemiology base rates (CDC WONDER public aggregates; GBD non-commercial), and rare-disease nomenclature (Orphadata Science CC BY 4.0).

The **clinical authority layer remains largely paywalled or non-commercial**: Bergman's, Gray's 42e, Schwartz 11e, Guyton & Hall text, ATLS manuals, JAMA Rational Clinical Examination / JAMAevidence, DrugBank (CC BY-NC, commercial use barred), Radiopaedia (CC BY-NC-SA, contributor-owned images), GBD (non-commercial only). A simulator can *teach to* these standards and *cite their headline numbers*, but cannot copy their text, tables or images into an AGPL product without licence.

Highest-leverage build order is in §11(b): OpenStax + openFDA + ATC/DDD + BodyParts3D/HRA + Visible Human + OpenTCI/SimTIVA + CDC WONDER + WHO Checklist/ERAS free PDFs + Surviving Sepsis 2021 + Orphadata Science.

---

## Findings

### 1. Anatomy Science

**1.1 Bergman's Comprehensive Encyclopedia of Human Anatomic Variation — Tubbs, Shoja & Loukas (eds.), Wiley-Blackwell, 3rd ed. 2016**
- Content: The definitive variant catalogue. 1,432–1,456 pp., ~110 chapters by system — bones, muscles, nerves, arteries (e.g. Ch.54 Abdominal aorta), heart, GI — each variant with prevalence in cadaveric/imaging series where known. Successor to Bergman's *Compendium / Catalog of Human Variation* (Univ. of Iowa).
- Publisher: John Wiley & Sons. 🔴 PAYWALLED — ©2016 Wiley, all rights reserved; library/ProQuest institutional access only. Cite prevalence facts; do not reproduce entries/illustrations.
- URL: https://library.upstate.edu/news/news-articles/20240502-bergmans.php

**1.2 Gray's Anatomy: The Anatomical Basis of Clinical Practice — Standring (ed.), Elsevier, 42nd ed. Oct 2020**
- Content: Standard regional/surgical anatomy reference in surgical training (listed as the anatomy text for postgraduate orthopaedic/surgical exams alongside Schwartz). First published 1858; 42nd ed. remains "the doctors' bible" per secondary sources.
- 🔴 PAYWALLED (Elsevier). Note: the 1918 20th edition is public domain and is the historical source for many open illustrations — usable, but anatomy/nomenclature is a century old.
- URL: https://myorthospot.com/adm/files/760043139.pdf

**1.3 Schwartz's Principles of Surgery — Brunicardi et al., McGraw Hill, 11th ed. 2019**
- Content: Foundational surgical-training text (physiology of surgical disease, perioperative care, procedure principles) since 1969. Companion surgical corpus used in training: Sabiston, Bailey & Love, Farquharson's — all commercial.
- 🔴 PAYWALLED (McGraw Hill AccessSurgery).
- URL: https://myorthospot.com/adm/files/760043139.pdf (same recommended-text list)

**1.4 NLM Visible Human Project (VHP) — U.S. National Library of Medicine**
- Content: Cross-sectional anatomy standard. Complete cryosection + CT + MRI of one male (released 1994; 1,871 sections at 1 mm) and one female (1995; 5,189 images at 0.33 mm). Designed as (1) anatomy reference, (2) public-domain test data for imaging algorithms, (3) model for image libraries.
- ✅ OPEN — Public-domain library; **since 2019 no licence agreement is required** to download; acknowledgement of NLM requested. ~4,000 former licensees in 66 countries.
- URLs: https://zenodo.org/records/16114440 ; https://en.wikipedia.org/wiki/Visible_Human_Project

**1.5 BodyParts3D — Database Center for Life Science (DBCLS), Japan**
- Content: 3D structure database for anatomical concepts (Mitsuhashi et al., *Nucleic Acids Res* 2009). Current release 4.0: ~2,234 structures / 3,432 named concepts, 15 systems, adult-male reference built from MRI (TARO) + illustration refinement.
- ✅ OPEN — **Relicensed to CC BY 4.0 on 2025-02-27** (files' headers still carry legacy CC BY-SA 2.1 Japan notice; current licence page controls). Attribution: "BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International."
- URL: https://github.com/slorksmo/human-atlas/blob/HEAD/public/ATTRIBUTION.md

**1.6 HuBMAP Human Reference Atlas (HRA) — NIH Human BioMolecular Atlas Program**
- Content: 3D reference organ library built on Visible Human male/female; versioned GLB organs with DOIs, creators/reviewers per organ (e.g. Female 3D Reference Organ Set v1.10, Browne & Schlehlein). Female set ~1,220 structures / 1,439 concepts, 18 systems in downstream viewers.
- ✅ OPEN — CC BY 4.0, no fee, commercial and non-commercial use allowed.
- URL: https://github.com/opening-science/open-twin-xr/blob/HEAD/ASSETS_LICENSE.md

**1.7 Z-Anatomy — open 3D atlas (community, ex-Blender Anatomy)**
- Content: Musculoskeletal completeness HRA/BodyParts3D lack — skeleton, muscles, joints. ⚠️ Mixed file-level licences inside the distribution (some components CC BY-NC, e.g. kidney, inner ear) despite a blanket CC BY-SA badge — audit per-file before shipping.
- 🟡 OPEN WITH CARE — CC BY-SA 4.0 for most files; share-alike is compatible in spirit with AGPL for assets kept as separate files, but NC components must be excluded/replaced.
- URL: https://github.com/opening-science/open-twin-xr/blob/HEAD/ASSETS_LICENSE.md

**1.8 OpenStax Anatomy and Physiology 2e — Rice University, OpenStax**
- Content: Complete undergraduate anatomy + physiology (1,420 pp. in 1e), by-system, with normal values throughout. The only textbook-scale anatomy/physiology source that is truly open.
- ✅ OPEN — CC BY 4.0 in most listings (BCcampus: "CC BY 4.0 except where otherwise noted"). ⚠️ One OpenStax preface fetch rendered a CC BY-NC-SA 4.0 statement for 2e — **verify the licence page for the exact edition/excerpt before redistribution**; conflicting licence statements were found in sources.
- URL: https://collection.bccampus.ca/textbook/jLnD8djx/

**1.9 Embryology / development — Langman's Medical Embryology (Wolters Kluwer) & Moore, *The Developing Human* (Elsevier)**
- Content: Standard sources for developmental sequences that explain congenital variants (branchial, cardiac septation, gut rotation, diaphragmatic, renal ascent anomalies) that Bergman's catalogues in adults.
- 🔴 PAYWALLED — no open edition found. Teach developmental mechanisms in original text; cite. No authoritative open embryology atlas at textbook depth was verified (see Could not verify).

**1.10 Published anatomical measurement datasets — normal organ/vessel sizes**
- Content (ultrasound/radiology nomograms, multiple series agree): Liver mid-clavicular span **<15.5–16 cm** (mean ~14 cm); spleen length **<12–13 cm**; kidney bipolar length **9–12 cm** (adult, left > right by <1.5 cm, volume <~140 cc, cortex ≥1 cm); portal vein **<13 mm**; common bile duct **4–8 mm (usually ≤6 mm)**; gallbladder wall **≤3 mm**, length <10 cm. Large nomogram example: 3,699 subjects (Chattogram) — adult liver 11.1–11.6 cm (different measurement convention), spleen 8.2–9.0 cm, kidney R 9.0–9.7 / L 9.6–10.2 cm — illustrating that *method and population move the "normal" by centimetres*; a simulator must store method + population with every range.
- 🟡 CITE-ONLY — journal articles/nomograms are citable facts; Radiogyan compilation is a secondary aggregator, not a primary standard.
- URLs: https://radiogyan.com/normal-radiology-measurements/ ; https://banglajol.info/index.php/CMOSHMCJ/article/view/77677

### 2. Quantitative Physiology & Pathophysiology

**2.1 Guyton and Hall Textbook of Medical Physiology — Elsevier, 14th ed. lineage (Hall)**
- Content: The quantitative canon the physiology engine should implement: circulation divided systemic (84% of blood volume) vs heart+lungs (16%); aortic velocity ~33 cm/s vs capillary ~0.3 mm/s; cardiac output ~100 mL/s (≈5–5.6 L/min men, 4.9 L/min women; cardiac index ~3 L/min/m²); total peripheral resistance **1 PRU** (range 0.2 vasodilated – 4 PRU constricted); total pulmonary resistance **0.14 PRU**; mean aortic pressure ~100 mmHg (120/80), mean pulmonary arterial **16 mmHg**, mean left atrial ~2 mmHg, functional capillary ~17 mmHg, glomerular capillary ~60 mmHg.
- 🔴 PAYWALLED text (Elsevier) — numbers above are published facts, widely reproduced; implement equations (Ohm/Poiseuille, Frank-Starling, renal autoregulation) in original code.
- URL: https://doctorlib.org/physiology/textbook-medical-physiology/14.html (12th-ed. chapter text, index only — do not copy into product)

**2.2 Standard haemodynamic normal ranges (critical-care consensus tables)**
- CO **4–8 L/min**; CI **2.5–4.2 L/min/m²**; SVR **770–1,500 dyn·s/cm⁵** (other tables 900–1,400); PVR **20–120 dyn·s/cm⁵**; MAP **70–95 mmHg** (target ≥65 in shock); RA mean 0–5, RV 17–32/1–7, PA 17–32/1–7 mean 9–19, PCWP/LA mean **4–12**, LV 90–140/5–12, aorta 90–140/60–90 mmHg; EF **60–70%** (tables vary 55–70).
- 🟡 CITE-ONLY — teach as ranges with source variance, not single values.
- URL: https://study-notes-pdfs.s3.us-west-2.amazonaws.com/28458757.pdf

**2.3 Lung mechanics / spirometry normals**
- FEV₁ and FVC **80–120% predicted**; FEV₁/FVC **0.70–0.80** normal, **<0.70 = obstruction**, normal/raised with both reduced = restriction; TLC/FRC/RV 75–120% predicted; tidal volume ~500 mL, residual volume ~1,200 mL; FVC ~4.5–5.0 L men, 3.0–3.5 L women; RR 12–20/min; PaO₂ 80–100, PaCO₂ 35–45 mmHg.
- 🟡 CITE-ONLY (GLI reference equations are the modern standard — spirometry must be %predicted by age/sex/height, never fixed litres alone).
- URL: https://www.slideshare.net/slideshow/pft-253869759/253869759

**2.4 Renal clearances**
- GFR (inulin clearance) **~125 mL/min/1.73 m²**; creatinine clearance ~135 mL/min measured (secretion adds ~10%); eGFR **>90** normal, **<60 for >3 months = CKD range**; renal plasma flow ~660 mL/min in Guyton lineage. Pregnancy: GFR +50% (see §9).
- 🟡 CITE-ONLY facts.
- URL: https://www.scribd.com/document/732394647/Physiology2-merged (index summary of standard teaching values)

**2.5 ATLS haemorrhage classes — see §3.3 for full table** (Class I <15%/<750 mL → Class IV >40%/>2,000 mL, HR <100 → >140, urine >30 → negligible mL/h).

**2.6 Sepsis-3 + Surviving Sepsis Campaign 2021 — Singer et al. JAMA 2016; Evans et al., SCCM/ESICM**
- Definitions: Sepsis = life-threatening organ dysfunction from dysregulated host response, operationalised as **SOFA rise ≥2** (>10% in-hospital mortality). Septic shock = vasopressor to keep **MAP ≥65 mmHg + lactate >2 mmol/L** despite adequate fluids.
- Hour-1 bundle (begin immediately): measure lactate (repeat q2–4h if raised), blood cultures *before* antibiotics (don't delay antibiotics >45 min for them), broad-spectrum antibiotics **within 1 h for shock / within 3 h for possible sepsis without shock**, **30 mL/kg balanced crystalloid** for hypotension or lactate ≥4 mmol/L, norepinephrine first-line (add vasopressin at NE ~0.25–0.50 mcg/kg/min, then epinephrine; hydrocortisone if refractory), source control within 6–12 h. SSC 2021 recommends *against* qSOFA as a sole screening tool vs SIRS/NEWS/MEWS.
- 🟡 CITE-ONLY / FREE TO READ — guideline PDFs widely available free via SCCM; text is society copyright. Numbers and bundle steps are teachable facts.
- URLs: https://emottawablog.com/2022/06/surviving-sepsis-the-2021-review/

**2.7 Acid–base interpretation standards**
- Normal ABG (OpenStax, ✅ CC-licensed table): **pH 7.35–7.45, PaO₂ 80–100 mmHg, PaCO₂ 35–45 mmHg, HCO₃⁻ 22–26 mEq/L, SaO₂ 95–98%**. Metabolic acidosis = pH <7.35 + HCO₃⁻ <22. Standard method to teach: pH → primary disorder (PaCO₂ vs HCO₃⁻) → compensation (Winter's formula etc.) → anion gap (Na⁺−[Cl⁻+HCO₃⁻], normal ~8–16) → delta checks. Stewart physicochemical approach is the alternative formalism — present as advanced/optional.
- ✅ OPEN for the normal-values table via OpenStax; interpretation algorithms are standard facts.
- URL: https://openstax.org/books/medical-surgical-nursing/pages/10-4-acid-base-imbalance

### 3. Surgery & Perioperative Standards

**3.1 WHO Surgical Safety Checklist — World Health Organization, 2008/2009**
- Content: **19 items, 3 pause points** — Sign In (before induction), Time Out (before incision), Sign Out (before leaving OR).
- Evidence: Haynes et al., *NEJM* 2009, 8 hospitals, 7,688 patients (3,733 before / 3,955 after): major complications **11% → 7%**, inpatient death **1.5% → 0.8%** (>⅓ reduction). Norway stepped-wedge RCT: complications 19.9% → 11.5%, mortality 1.6% → 1.0%, LOS −0.8 days. Used in ~70% of countries a decade after launch.
- ✅ OPEN — WHO checklist and implementation manual are free WHO publications; reproduce with WHO attribution per its terms.
- URLs: https://www.who.int/news-room/questions-and-answers/item/safe-surgery-saves-lives-frequently-asked-questions ; https://www.who.int/news/item/11-12-2010-checklist-helps-reduce-surgical-complications-deaths

**3.2 ERAS® Society Protocols — ERAS Society**
- Content: Procedure-specific perioperative pathways (colorectal flagship + ~20 specialties). Colorectal 2025 update (Gustafsson et al., *Surgery* 2025; de novo GRADE guideline, 23 items, >800 studies graded): preop counselling/optimisation, carbohydrate loading + clear fluids to 2 h, no routine bowel prep except rectal (2025: combined mechanical + oral antibiotic prep in elective colorectal), antibiotic prophylaxis <60 min, normothermia, goal-directed / slightly-positive fluid balance (2025 change from near-zero), minimally invasive surgery as standard (no clear robotic vs laparoscopic difference), no routine drains/NG tubes, multimodal opioid-sparing analgesia, mobilisation **≥3 h/day from POD1** (lowered from 6 h), early oral diet, IV fluids off within 6 h postop in summaries. Full ERAS implementation: complications ~**50% ↓**, LOS **−2 to 3 days**.
- ✅ OPEN — "All ERAS Society Guidelines are available for free" as PDFs from ERAS Society site.
- URLs: https://erassociety.org/guidelines/?speciality=colorectal ; https://www.surgjournal.com/article/S0039-6060(25)00249-1/fulltext

**3.3 ATLS® — Advanced Trauma Life Support, American College of Surgeons Committee on Trauma**
- Current edition: **10th edition (2018) was the long-standing current manual ($152 via ACS store); an 11th edition (2025) is now cited in course pages** — a simulator must state which edition it teaches and track the transition. Core: primary survey ABCDE, shock index HR/SBP, AMPLE, 1 L crystalloid initial bolus in adults (10th-ed. change from 2 L), 20 mL/kg in children <40 kg, early TXA + blood products over crystalloid, permissive hypotension / damage-control resuscitation, base deficit + lactate over HR/BP alone for shock grading.
- Haemorrhage classes (70-kg adult, blood volume ~7% body weight ≈5 L): **I: ≤750 mL, ≤15%, HR <100, BP normal, RR 14–20, urine >30 mL/h, slightly anxious · II: 750–1,500 mL, 15–30%, HR 100–120, BP normal/narrow pulse pressure, RR 20–30, urine 20–30, anxious · III: 1,500–2,000 mL, 30–40%, HR 120–140, BP ↓, RR 30–40, urine 5–15, confused · IV: >2,000 mL, >40%, HR >140, BP ↓↓, RR >35, urine negligible, lethargic.** Caveat to teach: validation studies (Guly et al.; TARN ~165,000 patients) show vital signs alone classify poorly — classes are a teaching scaffold, not a diagnostic rule.
- 🔴 PAYWALLED — ACS course manual is commercial, course-gated. Headline algorithm facts are teachable; do not copy manual text/tables verbatim.
- URLs: https://store.facs.org/atls-student-course-manual-10th-edition ; https://www.lsuhs.edu/departments/school-of-medicine/surgery/atlscourse

**3.4 Damage-Control Surgery / Resuscitation — EAST Practice Management Guidelines; Emergency War Surgery (Borden Institute, US Army)**
- Principles: Restore physiology, not anatomy, in 3 phases — (1) abbreviated operation: haemorrhage + contamination control only, packing, temporary closure; (2) ICU resuscitation: rewarm, correct coagulopathy/acidosis; (3) planned reoperation 24–72 h for definitive repair. Triggers = **lethal triad: hypothermia <35 °C, acidosis pH <7.2, coagulopathy (INR >1.5 / PT >19 s, PTT >60 s)**, plus >10 units RBC, inaccessible injuries, combined hollow-viscus + vascular injury. DCR companions: permissive hypotension, crystalloid minimisation, balanced (1:1:1) blood-product transfusion, early TXA.
- ✅/🟡 — Emergency War Surgery chapter is a US-government publication (public domain as a federal work, verify chapter notice); EAST guidelines are free to read on EAST/J Trauma sites, society copyright for text.
- URLs: https://permanent.fdlp.gov/lps101451/www.bordeninstitute.army.mil/other_pub/ews/Chp12DamageControl.pdf ; https://tsaco.bmj.com/content/2/1/e000063 (open-access review)

**3.5 ASA Standards for Basic Anesthetic Monitoring — American Society of Anesthesiologists**
- Content: Standard I — qualified anaesthesia personnel continuously present. Standard II — continually evaluate **oxygenation** (inspired O₂ analyser with low-O₂ alarm; pulse oximetry with variable-pitch tone + low alarm), **ventilation** (chest excursion/bag, quantitative end-tidal CO₂ — capnography — expired volume, disconnect alarm; ETT/LMA position verified clinically + ETCO₂), **circulation** (continuous ECG; BP + HR at least **every 5 minutes**; plus palpation/auscultation/arterial trace/pulse-oximetry plethysmography), **temperature** (monitor when significant changes anticipated/intended). Applies to general, regional and monitored anaesthesia care. Last major amendments 2010–2020 lineage; ASA posts the standards free.
- ✅ FREE TO READ on ASA site (asahq.org) — society copyright; simulator checklist can implement the requirements as facts.
- URL (secondary summary, index): https://www.slideshare.net/slideshow/asa-recommended-monitoring/248128789 — *use ASA's own standards PDF as product source; see Could not verify.*

**3.6 Antibiotic Prophylaxis — ASHP / IDSA / SIS / SHEA Clinical Practice Guidelines (Bratzler et al. 2013; joint update listed as in development, est. Q4 2026 in a 2026 review)**
- Rules a simulator must score: Give **within 60 min before incision** (vancomycin / fluoroquinolones: begin **within 120 min**); **cefazolin 2 g IV (3 g if ≥120 kg)**, paediatric 30 mg/kg, redose **q4h** intraop (≈2× half-life rule) and after blood loss **>1,500 mL**; cefoxitin 2 g redose q2h; colorectal adds metronidazole 500 mg or single-dose ertapenem 1 g; **single dose / stop at closure** for most clean & clean-contaminated cases (CDC: no post-closure doses; legacy limit ≤24 h, cardiac ≤48 h).
- 🟡 FREE-TO-READ guideline PDF via ASHP; society copyright. Dosing facts are teachable.
- URLs: https://eguideline.guidelinecentral.com/i/109326-ashp-surgical-prophylaxis-guidelines/7 ; https://deepmedicine.in/clinical/protocols/antibiotics-prophylaxis.html (summary)

**3.7 Foundational procedures — current evidence a simulator must teach**

- *Laparoscopic cholecystectomy — Critical View of Safety (Strasberg 1995; Strasberg & Brunt 2010).* Bile-duct injury: **~0.4–0.5% laparoscopic vs ~0.2% open** (early lap era 1–3 per 1,000 major injuries, up to 2.8% in learning-curve series). CVS = 3 criteria, all required before clipping anything: (1) hepatocystic (Calot) triangle cleared of fat/fibrous tissue, (2) lower gallbladder separated from cystic plate, (3) **two and only two structures** seen entering gallbladder (cystic duct + cystic artery). If CVS unattainable → bailout: subtotal (fenestrating/reconstituting) cholecystectomy, fundus-first, cholangiography, or conversion — never blind clipping. Series using CVS for target identification report thousands of cases without misidentification injury, but evidence level is observational. Tokyo Guidelines TG18/TG23: early laparoscopic cholecystectomy for Grade I–II acute cholecystitis (window now argued to ~10 days in fit patients), severity grading I/II/III drives drainage-vs-surgery in unfit patients.
  URLs: https://ales.amegroups.org/article/view/3940/4771 ; https://www.droracle.ai/articles/372453/what-is-the-management-approach-for-acute-cholecystitis-according (TG summary, index)
- *Appendicectomy — WSES Jerusalem Guidelines, 2025 update (in JAMA Surgery, Jan 2026).* ~17 million appendicitis cases/year worldwide. Uncomplicated appendicitis selected for surgery: **laparoscopic appendicectomy within 24 h** of admission; single preop antibiotic dose for uncomplicated cases, no extra antibiotics while waiting; complicated cases get therapeutic antibiotics if surgery delayed; adults ≥35 with nonoperatively managed complicated appendicitis: interval appendicectomy at **6–12 weeks** to exclude neoplasm. Antibiotics-first (APPAC/CODA lineage) remains a shared-decision alternative for uncomplicated disease — teach both pathways and their recurrence trade-off.
  URL: https://www.instagram.com/reel/DbYnNS8mKpY/ (JAMA Network summary of the guideline, index — cite the WSES/JAMA Surgery paper in product)
- *Hernia repair:* No dedicated primary guideline was retrieved in this round (see Could not verify). Established frame to verify before building: HerniaSurge international guidelines for groin hernia (mesh-based Lichtenstein / laparoscopic TEP-TAPP as standards, watchful waiting acceptable for minimally symptomatic men) and EHS/AHS ventral hernia guidance. Do not ship hernia numbers until sourced.

### 4. Pharmacology (Quantitative)

**4.1 openFDA — U.S. Food and Drug Administration**
- Content: Free REST/JSON APIs — drug labels (Structured Product Labeling), adverse events (FAERS, ~20M+ reports since 1968 in downstream counts), NDC Directory, Drugs@FDA approvals (1939– ), recalls/enforcement, shortages. No key needed to try; free key raises limits (~240 req/min, 120k/day with key in secondary summaries; anonymous per-IP limits are lower).
- ✅ OPEN — US federal data, public domain / open-data terms; free for commercial and educational reuse. Pair with NLM DailyMed (full label text, public domain) and RxNorm (NLM, free licence) for identifiers — DailyMed/RxNorm not separately fetched this round, verify their current terms before bulk ingestion.
- URL: https://open.fda.gov/apis/drug/ndc/how-to-use-the-endpoint/

**4.2 WHO ATC/DDD System — WHO Collaborating Centre for Drug Statistics Methodology (Norwegian Institute of Public Health, Oslo)**
- Content: Anatomical Therapeutic Chemical classification — 5 levels, 14 first-level anatomical groups — plus Defined Daily Dose: "the assumed average maintenance dose per day for a drug used for its main indication in adults." One DDD per ATC code + route; no DDDs for most topicals, sera, vaccines, antineoplastics (L01), anaesthetics (N01), contrast (V08). Endorsed by WHO 1996 as the international drug-utilisation standard; index updated annually (2026 index current).
- ✅ SEARCHABLE FREE online; full index in Excel/XML/paper is ordered (paid) from the Centre. DDD is a *statistical unit, not a recommended dose* — a simulator must not present DDD as dosing guidance.
- URLs: https://www.who.int/toolkits/atc-ddd-toolkit/about-ddd ; https://atcddd.fhi.no/filearchive/publications/2026_guidelines_for_atc_classification_and_ddd_assignment.pdf

**4.3 DrugBank — OMx Personal Health Analytics Inc. (ex-Univ. of Alberta)**
- Content: Richest curated drug knowledgebase (DrugBank 6.0, *NAR* 2024): chemistry, pharmacology, targets (11,510+ protein targets in commercial tier), 1.37M interactions / 140,000+ adverse effects in paid tiers.
- 🔴/🟡 RESTRICTED — Website browsing free; academic datasets under **CC BY-NC 4.0** (non-commercial only, application required, **academic downloads temporarily paused** at check); any commercial use, redistribution, product embedding or derivative database requires a paid commercial licence; terms (updated 2025-09-17) bar copying/derivative works beyond the limited internal educational licence. **Incompatible with distributing its data inside an AGPL product** without a licence. Small CC0 "open data" identifier subsets historically existed — do not assume they cover clinical content.
- URLs: https://trust.drugbank.com/drugbank-trust-center/terms-of-use ; https://go.drugbank.com/releases/latest

**4.4 Anaesthetic pharmacology parameter sets (published facts)**
- MAC (alveolar concentration preventing movement to incision in 50%, ~40-yr adult, O₂): **sevoflurane ~1.8–2.1%, isoflurane 1.15–1.2%, desflurane 6.0–6.6%, halothane 0.75%, N₂O 104–105%**; 1.5 MAC ≈ 90% immobile; MAC-awake ~0.3 MAC. Blood:gas partition: desflurane 0.42–0.45, sevoflurane 0.6–0.69, isoflurane 1.4, halothane 2.3, N₂O 0.47 (lower = faster on/off). Metabolism: halothane ~20%, sevoflurane 3–5%, enflurane 2%, isoflurane 0.2%, desflurane 0.02%.
- Propofol TCI models: **Marsh** — weight-proportional volumes (V1 = 0.228 L/kg lineage), plasma-targeted, larger initial bolus; **Schnider** — fixed V1 (4.27 L), V2/V3 and clearances from age/weight/height via lean-body-mass (James formula, fails at BMI >40), effect-site targeted, ke0 0.456/min (tpeak 1.6 min); **Eleveld** — general-purpose model (children→elderly, obese) using fat-free mass (Al-Sallami), now preferred default; Paedfusor/Kataria for children. Typical effect-site for loss of consciousness ~2.5–3 mcg/mL propofol alone, 2–2.5 with remifentanil; maintenance TCI 2.5–4.0 mcg/mL in comparative studies.
- 🟡 Published parameters are citable facts — implement from primary papers (Marsh 1991, Schnider 1998/99, Eleveld 2018) with citation; textbook tables are paywalled.
- URLs: https://www.sciencedirect.com/topics/medicine-and-dentistry/blood-gas-partition-coefficient ; https://accessanesthesiology.mhmedical.com/content.aspx?bookid=572&sectionid=42543645

**4.5 Opioid context-sensitive half-times (CSHT)**
- CSHT = time for plasma concentration to fall 50% after stopping an infusion of a given duration. **Remifentanil: ~3–6 min, independent of infusion duration** (ester hydrolysis, clearance 40–60 mL/kg/min, elimination t½ 5–14 min) — the outlier. **Alfentanil: ~50–60 min plateau** (~23→30 min in TIVA summaries). **Fentanyl: rises steeply — ~25 min after 1 h, >100 min after 4 h, up to ~300 min after prolonged infusion** (large Vd ~4–6 L/kg, hepatic CYP3A4). Sufentanil intermediate. Teaching point: elimination half-life ≠ CSHT; recovery prediction requires CSHT curves.
- 🟡 CITE-ONLY facts from primary PK literature / exam literature.
- URLs: https://derangedphysiology.com/main/cicm-primary-exam/past-papers/2018-paper-1-saqs/question-5 ; https://propofoltiva.com/tiva/opioid-bioequivalence/

**4.6 Pressor / vasoactive dosing ranges (adult, titrate to MAP ≥65 in septic shock unless stated)**
- **Norepinephrine (first-line): start 0.05–0.1 mcg/kg/min** (label fixed-dose start 8–12 mcg/min), usual 0.01–0.5, refractory reports to 3+ mcg/kg/min; add second agent at ~0.25–0.5. **Vasopressin: fixed 0.03 units/min** (range 0.01–0.04), second-line, catecholamine-sparing. **Epinephrine: 0.01–0.5 mcg/kg/min** infusion (anaphylaxis/arrest bolus dosing separate). **Phenylephrine: 20–200 mcg/min** or 0.5–9 mcg/kg/min ranges in references, bolus 100–200 mcg. **Dopamine: 2–20 mcg/kg/min** (arrhythmia risk — no longer first-line in sepsis). **Dobutamine: 2–20 mcg/kg/min** (inotrope for septic cardiomyopathy / cardiogenic component, typical range 5–15 in one summary — verify per primary source). Ranges vary by source/convention (weight-based vs fixed) — store both and label them.
- 🟡 Guideline/label facts (SSC 2021 + FDA labels via openFDA/DailyMed).
- URLs: https://www.medicine.com/drug/norepinephrine/hcp ; https://ercrashcart.com/__l5e/assets-v1/162fc6a9-ad08-4fda-ab73-932d44e075a9/vasopressor-inotrope-cheat-sheet.pdf (secondary)

**4.7 Open PK/PD model libraries**
- **OpenTCI Initiative (opentci.org)** — community repository of anaesthetic PK/PD datasets + **STANPUMP** code (Shafer), de-identified dose/concentration/effect data, mainly propofol + remifentanil. ✅ Freely available.
- **SimTIVA (Terence Luk)** — open-source TCI/TIVA simulator, **GPL-3.0**, implements Marsh, Schnider, Paedfusor, Eleveld (propofol), Minto, Eleveld (remifentanil), Maitre (alfentanil); calculations based on STANPUMP. ✅ Directly reusable in an AGPL project (GPL-3.0 compatible).
- **R package `tci` (CRAN)** — TCI algorithms (Jacobs/Shafer), population models Marsh/Schnider/Eleveld + Minto/Kim/Eleveld, with Eleveld PK/PD datasets. ✅ Open (CRAN).
- URLs: https://www.mdpi.com/2077-0383/11/9/2487 ; https://search.r-project.org/CRAN/refmans/tci/html/00Index.html

### 5. Imaging Science

**5.1 CT Hounsfield Units — reference values by tissue**
- Definition: HU = 1000 × (μ − μ_water)/(μ_water − μ_air); **water = 0 HU, air = −1000 HU** by definition; 12-bit CT range −1024 to +3071.
- Table (published approximations — vary with kV, reconstruction, contrast phase): Air **−1000** · Lung **−700 to −600** (some tables −500) · Fat **−120 to −90** · Water **0** · CSF **~15** · White matter 20–30, grey matter ~37–45 · Blood **+30 to +45** (clotted higher, 50–75 in many tables) · Muscle **+35 to +55** (10–40 in head-CT tables) · Liver **+40 to +60** · Soft tissue on contrast CT **+100 to +300** · Cancellous bone **+300 to +400** · Cortical bone **+500 to +1,900** (dense bone to +3,000) · Metal **>+3,000**. ⚠️ Flag the low-quality source found in search that inverted air/bone signs — HU tables must be proofed against the definition, a good in-product teaching example of source error.
- ✅ OPEN AS FACTS — scale is a standard; Wikipedia table is CC BY-SA and cross-checks against radiology texts.
- URL: https://en.wikipedia.org/wiki/Hounsfield_scale

**5.2 ACR Appropriateness Criteria® — American College of Radiology**
- Content: Evidence-based imaging-selection guidelines, ~200+ topics (older counts 175–197) with variants, narrative + 1–9 appropriateness rating tables + relative radiation level, developed by expert panels using RAND/UCLA + GRADE, reviewed annually. CMS-recognised for Appropriate Use Criteria / clinical decision support.
- 🟡 FREE TO BROWSE, NOT OPEN TO REDISTRIBUTE — full criteria are readable free at acsearch.acr.org with no subscription; ACR retains copyright, and EHR-embedded decision support is licensed commercially as CareSelect Imaging. A simulator may *link, cite ratings as facts, and teach the method*; it may not scrape/republish the tables without ACR licence.
- URLs: http://www.acr.org/Clinical-Resources/Clinical-Tools-and-Reference/Appropriateness-Criteria ; https://www.acpjournals.org/doi/10.7326/acpi-20111101_7

**5.3 Ultrasound / FAST–eFAST evidence base**
- Protocol: FAST = 4 views (perihepatic/Morison, perisplenic, pelvic, pericardial/subxiphoid) for free fluid; eFAST (2004– ) adds anterior/lateral thoracic views for pneumothorax/haemothorax. Needs ~100–200 mL fluid to turn positive; does not grade organ injury and misses retroperitoneal bleeding.
- Accuracy: Derivation (Rozycki, 1,540 patients) sensitivity 83.3%, specificity 99.7% (100%/100% in hypotensive blunt trauma subgroup). **Cochrane 2018 (34 studies, 8,635 patients, blunt thoracoabdominal): pooled sensitivity 0.74 (95% CI 0.65–0.81), specificity 0.96 (0.94–0.98)**; abdominal-only sensitivity 0.68. Meta-analysis 2019 (75 studies, 24,350 patients): pericardial effusion sens 91% / spec 94%; pneumothorax sens ~69% / spec 99% (superior to supine CXR for pneumothorax). Verdict to teach: **high-specificity rule-in test, moderate sensitivity — a negative FAST never rules out injury**, especially in children and stable patients. Endorsed by ATLS, EAST, Western Trauma Association. Learning curve flattens after ~30–100 scans (DEGUM requires 25 supervised FAST).
- 🟡 CITE-ONLY — Cochrane/meta-analysis numbers are citable; full Cochrane text is licensed.
- URLs: https://ecgwaves.com/tools/fast-exam ; https://www.mdpi.com/2077-0383/14/10/3457 (open-access review)

**5.4 MRI contrast basics — authoritative open sources**
- No single open MRI-contrast monograph was verified this round. Safe citable frame: gadolinium-based contrast agents shorten T1 (bright on T1-weighted), classified macrocyclic vs linear (macrocyclic = higher kinetic stability, preferred after NSF/deposition concerns); NSF risk concentrated in eGFR <30 with older linear agents; ACR Manual on Contrast Media is the standard reference and is posted free by ACR — **verify current edition/URL before linking in product** (see Could not verify). Teach T1/T2/FLAIR/DWI signal behaviour from OpenStax-level physics + Radiopaedia articles (licence below), not from copied tables.

**5.5 Radiopaedia — Radiopaedia.org / Radiopaedia Australia Pty Ltd**
- Content: Wiki radiology encyclopaedia + case repository — 16,719 articles, 56,720 cases (Dec 2023 count). Editorial-board peer review.
- 🟡⚠️ RESTRICTED — FLAG PRECISELY: Free to read. **Most content is under a Creative Commons NonCommercial licence (CC BY-NC-SA 3.0, modified Radiopaedia licence for cases/images); platform and text are owned by Radiopaedia Australia Pty Ltd; image copyright stays with contributors** who license to Radiopaedia and its users. Consequences: (1) **NonCommercial blocks use in any monetised product** and creates ambiguity even for free-but-donated open-source distribution; (2) **NoDerivs variants (CC BY-NC-ND) on some drawings** block cropping/relabelling; (3) cases are patient images — no bulk scraping/redistribution right. Verdict: **link and cite; do not ingest cases/images into an AGPL product.** Individual items reused via AnatomyTOOL carry their own CC BY-NC-SA / BY-NC-ND tags — same restrictions travel with them.
- URLs: https://en.wikipedia.org/wiki/Radiopaedia ; https://anatomytool.org/content/radiopaedia-drawing-gyri-and-sulci-superior-surface-brain-no-labels (per-item licence example)

### 6. Diagnostic Reasoning Evidence

**6.1 JAMA Rational Clinical Examination (RCE) series — JAMA / American Medical Association; book: JAMAevidence (McGraw Hill)**
- Content: Systematic reviews, one clinical question per article ("Does this patient have…?"), reporting precision + **likelihood ratios for history/exam findings** — the quantitative spine of a reasoning workbench. Worked examples: *MI* — new ST elevation LR 5.7–53.9, new Q wave 5.3–24.8, pain radiating to both arms LR 7.1, S3 LR 3.2, hypotension LR 3.1; normal ECG LR 0.1–0.3, pleuritic pain LR 0.2, pain reproduced by palpation LR 0.2–0.4. *Heart failure / LV dysfunction* — S3 LR+ 11, pulmonary venous congestion on CXR LR+ 12, JVP LR+ 5.1, rales LR+ 2.8; abnormal ECG LR− 0.03. *Child abuse (2024–25 update)* — patterned bruising LR+ 2.0–66, buttock bruising 15–83, retinal haemorrhages LR+ 11.
- 🔴 PAYWALLED — JAMA/JAMAevidence subscription. **LRs themselves are citable facts**; build the workbench's LR database from primary articles with citation per value, not by copying RCE tables wholesale.
- URLs: https://jamanetwork.com/journals/jama/article-abstract/1107536 ; https://jamaevidence.mhmedical.com/content.aspx?bookid=845&sectionid=61357503

**6.2 Sensitivity/specificity compendia**
- No single open, curated sens/spec database exists. Practice: per-test values live in primary studies, Cochrane DTA reviews, and RCE articles. A simulator should store each value as {test, target condition, sens, spec, LR+, LR−, population, N, citation} — the structure matters more than any one compendium. (OpenFDA labels and ACR criteria supply test-context, not accuracy.)

**6.3 Diagnostic error — *Improving Diagnosis in Health Care* (2015), National Academy of Medicine (Institute of Medicine), National Academies Press**
- Headline findings: **Most people will experience ≥1 diagnostic error in their lifetime; ~5% of US adults seeking outpatient care experience one each year; diagnostic errors contribute to ~10% of patient deaths and 6–17% of hospital adverse events; they are the leading category of paid malpractice claims and ~2× as likely to involve death as other claims.** Causes are systems + cognition: poor collaboration/communication, work systems ill-designed for diagnosis, almost no feedback to clinicians on diagnostic accuracy, culture discouraging disclosure. 8 goals (teamwork, education, health IT, identify/learn from errors, work-system redesign, reporting/learning system, payment reform, research funding).
- ✅ FREE — National Academies Press PDFs are free to download; cite freely.
- URLs: https://www.eurekalert.org/news-releases/770275 ; https://www.healthitanswers.net/new-report-outlines-goals-and-recommendations-to-reduce-diagnostic-errors/

**6.4 Cognitive bias & debiasing literature**
- Canon: Croskerry (2003) catalogue of biases in emergency medicine; Graber et al. — ~75% of diagnostic errors have a cognitive component, faulty reasoning in ~70% of ED error analyses in debiasing reviews. Biases to simulate explicitly: **anchoring** (fixating on early features, insufficient adjustment), **premature closure** ("when the diagnosis is made, the thinking stops" — most frequent), **confirmation bias**, **availability**, **base-rate neglect**, search satisficing, framing/triage cueing. Debiasing with best (still modest) support: metacognition / structured reflection, **diagnostic time-out** ("What else could this be? Consider the opposite"), checklists / differential generators (e.g. VINDICATES), deliberate System-1→System-2 switching, feedback on outcomes. Honest evidence note for learners: awareness training alone shows weak transfer; forcing strategies + feedback outperform lectures on bias.
- 🟡/✅ — key reviews are open in PMC.
- URLs: https://pmc.ncbi.nlm.nih.gov/articles/PMC6001502/ ; https://www.dovepress.com/cognitive-bias-in-clinical-practice-nurturing-healthy-skepticism-among-peer-reviewed-fulltext-article-AMEP

**6.5 Pretest probability & calibration**
- Resources: RCE prior-probability ranges per presentation (e.g. dyspnoeic ED patient without obvious cause: ~50% probability of LV dysfunction, range 34–83%) + disease prevalence from GBD/WONDER (§7) supply priors; Fagan nomogram / odds form of Bayes (post-test odds = pre-test odds × LR) is the computable core. Calibration training evidence: outcome feedback with case volume improves calibration; confidence-accuracy dissociation is the target phenomenon — a workbench should score Brier/calibration, not just top-1 diagnosis. No single open calibration-training platform was verified; this is a build opportunity, not a buy.

### 7. Disease & Epidemiology Data

**7.1 Global Burden of Disease — Institute for Health Metrics and Evaluation (IHME), Univ. of Washington**
- Scope: GBD 2023 (current guide) / GBD 2021 (published analyses): **204 countries/territories, 371 diseases & injuries, 88 risk factors**, 1990–present; incidence, prevalence, mortality, YLDs, DALYs, HALE by age/sex/location via GBD Results / GBD Compare / GHDx.
- 🟡 NON-COMMERCIAL ONLY — "freely available for non-commercial use"; non-commercial users may use/share/modify/build under IHME Free-of-Charge Non-Commercial User Agreement (Lancet GBD page also references Open Data Commons Attribution for downloads); **commercial organisations must license via services@healthdata.org**; single GBD Results download capped at 100,000 rows (increases by request, +100k increments, institutional email). For an AGPL educational (non-commercial) product: usable with attribution + agreement compliance; flag that any future monetisation breaks the licence.
- URLs: https://www.healthdata.org/research-analysis/about-gbd/gbd-data-and-tools-guide ; https://www.thelancet.com/gbd/about

**7.2 CDC WONDER — Centers for Disease Control and Prevention / NCHS**
- Content: Free public query system — mortality (NVSS), natality, cancer incidence, HIV/TB, vaccinations, VAERS, census denominators; tables/maps/charts/extracts with crude + age-adjusted rates, 95% CIs. US Cancer Statistics on WONDER: incidence 1999–2022 (PR 2005–2022) by site/age/race/sex/state/MSA.
- ✅ OPEN — US federal public-use data, no registration for aggregate queries; small-cell suppression rules apply. Best US source for simulated-case base rates.
- URLs: https://wonder.cdc.gov/wonder/help/cancer-v2022.html ; https://www.cdc.gov/united-states-cancer-statistics/about/tools.html

**7.3 SEER — Surveillance, Epidemiology, and End Results, National Cancer Institute**
- Content: Premier US cancer statistics — incidence, prevalence, survival, mortality by site/race/age/sex, via SEER*Stat. Public *statistics* pages and USCS aggregates on WONDER are open.
- 🟡 GATED MICRODATA — Case-level SEER Research / Research Plus data require registration, identity verification and a signed **Data Use Agreement** (renewed per submission year); Research Plus + a USCS request form are needed for the USCS public-use database. Aggregates ✅; microdata may not be redistributed — a simulator may publish derived rates with citation, not case records.
- URL: https://www.cdc.gov/united-states-cancer-statistics/public-use/access-data.html

**7.4 Orphanet / Orphadata — INSERM (France), Orphanet consortium**
- Content: Rare-disease inventory with ORPHAcodes, cross-referenced to OMIM, ICD-10, SNOMED CT, MeSH, MedDRA, UMLS, GARD; genes, phenotypes (HPO-linked signs thesaurus), prevalence, age of onset, inheritance; orphan-drug and expert-resource directories.
- ✅/🟡 SPLIT LICENCE — CURRENT POSITION (Orphadata FAQ): **Orphadata Science datasets & APIs are CC BY 4.0** — copy, distribute, commercial use allowed with credit + indicate changes (+ AI/LLM-use disclaimer requested). Older Orphanet database terms were **CC BY-ND 3.0** (no derivatives without permission) and **Orphadata Products** (full database, expert directory, orphan drugs) require a **Data Transfer Agreement / service contract**. Verdict: build only on the Science (CC BY 4.0) extracts; treat portal text and Products as licence-required.
- URLs: https://www.orphadata.com/faq/ ; https://reusabledata.org/orphanet-open.html (older ND assessment — shows why layer matters)

**7.5 Natural history / base-rate assembly for simulated cases**
- Recipe (all citable): priors by age/sex/geography from GBD (global) + WONDER (US); cancer natural history/survival from SEER aggregates; rare-disease priors from Orphadata Science; presentation-conditional priors from RCE articles (§6.1). No single "natural history textbook" is open — *Harrison's* / *Cecil* are paywalled; StatPearls (NCBI Bookshelf) is free-to-read, referenced, and frequently updated, and is the practical open substitute for disease summaries — verify its per-article licence before republishing text (reading/linking is unrestricted).

### 8. Medical Education Science

**8.1 USMLE Content Outline — FSMB + NBME (joint program)**
- Content: The coverage map for "what a physician must know." Single outline across Steps, organised by system (Human Development; Immune; Blood/Lymphoreticular; Behavioural/Nervous; Skin/Musculoskeletal; Cardiovascular; Respiratory; GI; Renal; Pregnancy/Childbirth; Gender/Breast/Reproductive; Endocrine; Multisystem; Biostatistics/Epidemiology; Social Sciences) + Physician Tasks/Competencies outline. Weightings (secondary summaries of official specs): Step 1 — Pathology 45–55%, Physiology 30–40% by discipline (overlapping), Medical Knowledge/Foundational Science 60–70% of tasks; system weights e.g. Cardiovascular 7–11% (Step 1) / 6–12% (Step 2 CK). Formats: Step 1 280 items / 8 h (pass/fail since 2022), Step 2 CK up to 318 items / 9 h, Step 3 two days + computer-based case simulations. Outline © FSMB/NBME, published free as PDF.
- ✅ FREE TO READ / USE AS MAP — cite as the coverage taxonomy; do not reproduce NBME items (none are public beyond sample items).
- URL: https://sup1rpfvr1b9ro.vcksoqhao.top/sites/default/files/2022-01/USMLE_Content_Outline_0.pdf (mirror of official outline PDF, index — obtain the current outline from usmle.org for product use)

**8.2 AAMC curriculum references**
- AAMC publishes the Curriculum Inventory, Core Entrustable Professional Activities for Entering Residency (Core EPAs, 13 activities, free PDF), and MedEdPORTAL (peer-reviewed teaching resources, CC-licensed per item). Not separately fetched this round — treat Core EPAs as the undergraduate anchor for §8.5 and verify current AAMC page before citing edition/year.

**8.3 Simulation-Based Mastery Learning — McGaghie, Wayne, Barsuk et al. (Northwestern)**
- Evidence: McGaghie et al., *Acad Med* 2011 meta-analysis (1990–2010, 3,742 articles screened, 14 studies): SBME with deliberate practice vs traditional clinical education, **overall effect size 0.71 (95% CI 0.65–0.76, p<.001)** for skill acquisition. Cook et al. 2011 (609 studies, 35,226 trainees): large effects vs no intervention, small-moderate vs other instruction, moderate for patient outcomes. Mastery-learning exemplars: simulation-based mastery learning for central-line insertion cut ICU complications (Barsuk 2009); surgical RCT — mastery-trained residents did laparoscopic hernia repair in **34 vs 48 min** with fewer complications (Zendejas 2011, as summarised in Lecturio review). 2025 competency-based simulation meta-analysis (Vermylen/McGaghie et al.): competency-based > non-competency-based simulation, large effect for skills, small for behaviours/patient effects. Design rules to implement: minimum passing standard, deliberate practice with feedback, no advancement until mastery, uniform outcomes with variable time.
- ✅ Key papers open in PMC.
- URLs: https://pmc.ncbi.nlm.nih.gov:443/articles/PMC3102783/ ; https://pubmed.ncbi.nlm.nih.gov/41217357/

**8.4 OSCE / assessment standards**
- Frame: Harden's OSCE (structured stations, standardised checklists/global ratings), Miller's pyramid (knows → knows how → shows how → does) as the assessment map, and programmatic assessment (many low-stakes observations aggregated). Scoring a surgical trainee should combine checklist completion, global rating (e.g. OSATS — Martin et al.), time/motion economy, and error counts — the same metrics OR Black Box / robotic kinematics research uses (§10). No single open OSCE standard document was retrieved; cite Harden/Miller/OSATS primary papers in product.

**8.5 Competency frameworks — ACGME Milestones + EPAs (ten Cate)**
- ACGME: 6 core competencies (Patient Care, Medical Knowledge, Practice-Based Learning & Improvement, Interpersonal & Communication Skills, Professionalism, Systems-Based Practice); specialty Milestones describe 4–5 developmental levels per subcompetency, reported semi-annually. EPAs (ten Cate 2005/2013): units of professional work that can be *entrusted* — observable, measurable, integrating multiple competencies; entrustment scaled in 5 supervision levels (observe → indirect supervision → unsupervised → supervise others). AAMC Core EPAs = the 13 EPAs expected on day 1 of residency. For simulator scoring: map every procedure/case to {Milestone subcompetencies + EPA + supervision level achieved} — that is the interoperable record residency programmes understand.
- 🟡 Framework documents are free from ACGME/AAMC; Milestones text is ACGME copyright — implement structure, cite, don't republish verbatim guides wholesale.
- URLs: https://www.ubiquitypress.com/chapters/123/files/4ad8b482-efc2-4e86-8f3b-168a3cf3646e.pdf (open-access EPA/Milestones chapter) ; https://www.codeihnrg.com.ar/pluginfile.php/77811/mod_folder/content/0/Nuts%20and%20Bolts%20of%20Entrustable%20Professional%20Activities.pdf?forcedownload=1 (ten Cate, JGME 2013)

**8.6 Spaced repetition evidence**
- Systematic review 2026 (Luu et al., *Cureus*; 314 records, 21 studies): most controlled studies show spaced retrieval improves exam performance/retention; observational Anki studies are mixed and at serious risk of bias (self-selection). Primary signals: above-average "mature card" (>21-day interval) users scored **71.5% vs 60.0%** on CBSE in a UNLV cohort (n=36, p=0.002 for mature cards); Gilbert et al. 2023 reported **+6.2 to +10.7 percentage points** on standardised exams for Anki users (secondary summary); Cepeda et al. 2006 distributed-practice meta-analysis is the general foundation. Anki itself is open-source (AGPL) — embed FSRS/SM-2 scheduling for the workbench's review queue.
- ✅ Reviews open in PMC/PubMed.
- URLs: https://pubmed.ncbi.nlm.nih.gov:443/42866698/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC12357012/

### 9. Special Populations & Variation

**9.1 Paediatrics — Broselow Pediatric Emergency Tape (Broselow & Luten) + PALS normals**
- System: Length-based (head-to-heel colour zones) estimate of 50th-percentile weight-for-length for children **up to ~12 years / 36 kg / ~146 cm**; each zone prints drug doses, fluid volumes, ETT/defibrillator sizes. Known limits: underestimates weight in obese children, overestimates in undernourished — habitus-adjusted methods (PAWPER, Handtevy age+length) outperform it in modern cohorts. Tape itself is a commercial product (Armstrong Medical); the *method and zone logic* are published.
- Scaling formulas (EMS/PALS teaching): weight (kg) ≈ **(2 × age) + 8–10**; systolic BP mean ≈ **90 + 2×age**, lower limit ≈ **70 + 2×age**; uncuffed ETT ≈ **(age/4) + 4**, cuffed ≈ (age/4) + 3.5; ETT depth ≈ 3 × tube size. Paediatric ATLS bolus 20 mL/kg (<40 kg). Normal vitals move with age: newborn HR 100–160, RR 30–60, systolic >60–70; converging to adult values by ~12 years. Blood volume ~80 mL/kg (child) vs 70 (adult) — children tolerate ~40% loss before hypotension (vs ~30% adults in teaching tables), making hypotension a *late* sign.
- 🟡 Method is citable; do not reproduce the printed tape artwork.
- URLs: https://dhs.saccounty.gov/content/dam/dhs/public-health/boards-committees/ems-mac-oac/2026/2026-june11/9016%20Pediatric%20Parameters.pdf ; https://www.ems1.com/pediatric-care/evaluating-todays-options-for-pediatric-weight-based-treatment-tools

**9.2 Obstetric physiology — published pregnancy adaptations (Soma-Pillay et al., *Cardiovasc J Afr* 2016, and concordant texts)**
- Cardiovascular: **cardiac output +30–50%** (≈4.5 → 6–7 L/min; +20% by 8 weeks, peak 20–32 weeks), **stroke volume +20–30%, heart rate +10–20 bpm, SVR −25–35%**, systolic BP −5–9 mmHg with mid-pregnancy nadir (16–24 weeks) then return to baseline; supine aortocaval compression can cut CO ~40%. Blood: **plasma volume +40–50% (+1.2–1.5 L), red-cell mass +20–30%** → dilutional anaemia (Hct nadir ~35% at 30–32 weeks), total blood volume +30–45% (~+1.5 L). Respiratory: minute ventilation **+40–50%**, PaCO₂ ~30 mmHg, compensated HCO₃⁻ ~21, FRC −20%, TLC −5%. Renal: **GFR +30–50%** (creatinine clearance 150–200 mL/min), normal creatinine in pregnancy ~0.46 mg/dL, BUN ~8.5 — a "normal" non-pregnant creatinine is abnormal in pregnancy. Labour: each contraction autotransfuses ~300–500 mL; CO rises a further 40–80% in second/third stage.
- ✅ Review is open-access; values agree across ≥3 sources fetched.
- URLs: https://ecgwaves.com/articles/cardiac-physiology-in-exercise-and-pregnancy ; https://pipador.co.uk/wp-content/uploads/2026/10/126_Cardiovascular_Changes_in_Pregnancy.pdf (revision notes, secondary)

**9.3 Geriatric changes**
- Established quantitative frame (Guyton/geriatrics literature, to be primary-sourced before shipping numbers): GFR declines ~0.75–1 mL/min/1.73 m²/year after ~40 (creatinine masks it as muscle mass falls); maximal heart rate ≈ 220 − age; arterial stiffening widens pulse pressure; baroreflex blunting + reduced β-responsiveness blunt tachycardic response to haemorrhage/sepsis (elderly patients may not mount ATLS-expected HR); total body water falls, fat fraction rises (larger Vd for lipophilic drugs, smaller for hydrophilic). Frailty (Clinical Frailty Scale) predicts surgical outcomes better than age alone. ⚠️ No dedicated geriatric primary source was fetched this round — flag as partially verified (see Could not verify).

**9.4 Sex-based differences**
- Citable anchors: resting CO 5.6 (men) vs 4.9 L/min (women) in Guyton teaching; FVC 4.5–5.0 vs 3.0–3.5 L; blood volume scales with body composition, not sex per se; QT interval longer in women (drug torsades risk); MAC and propofol requirements show small sex effects (Eleveld model includes sex/FFM covariates). Authoritative frame: NIH Sex as a Biological Variable (SABV) policy + FDA sex-specific labelling via openFDA. A simulator should parameterise by size/composition/age first and sex as a covariate where a primary source supports it — not by stereotyped "male/female patients."

**9.5 Body-habitus variation**
- Data needed and available: BMI-stratified dosing rules already in guidelines (cefazolin 3 g ≥120 kg, §3.6); lean/fat-free mass formulas (James — fails BMI >40; Janmahasatian; Al-Sallami FFM in Eleveld PK) for TCI; Broselow habitus failure modes (§9.1); organ-size dependence on body size (§1.10). Obesity physiology to model: increased CO/blood volume, reduced FRC (desaturation speed), OSA prevalence, dosing-scalar choice per drug (TBW vs LBW vs adjusted BW) — each drug needs its scalar cited individually.

### 10. Frontier Clinical Technology

**10.1 Robotic surgery platforms & training ecosystems — Intuitive da Vinci (Xi, 5) + entrants**
- Incumbent: Intuitive da Vinci. **da Vinci 5** (current flagship): >150 design innovations, ~10,000× computing power vs earlier generation (vendor claim), **Force Feedback** instruments (surgeons delivered up to 43% less force on tissue in vendor-cited study), My Intuitive+ analytics, Case Insights (AI evaluation of kinematics + video), Telepresence for observation/mentoring, **SimNow 2 simulator with >65 exercises**. Training ecosystem: dual-console proctoring, Intuitive Learning curriculum, dVRK (below). Entrants a state-of-the-art survey must track (landscape, not fetched in depth): Medtronic Hugo, CMR Surgical Versius, J&J Ottava, Moon Surgical Maestro, plus single-port (da Vinci SP) — verify current FDA status per platform before publishing claims.
- Research platform: **da Vinci Research Kit (dVRK)** — retired da Vinci components + open control stack (Johns Hopkins / Stanford / Intuitive collaboration), the standard testbed for surgical automation, force estimation and training research.
- 🟡 Vendor pages are marketing — cite specifications as vendor claims; clinical claims need peer-reviewed sources.
- URLs: https://www.intuitive.com/en-us/products-and-services/da-vinci/5?linkId=363411603 ; http://src.stanford.edu/demo/robot-assisted-surgery-with-the-da-vinci-research-kit

**10.2 Surgical data science / OR Black Box® — Surgical Safety Technologies (renamed Aimbient, July 2026), Grantcharov (Toronto → Stanford)**
- System: Synchronised OR video + audio + device/physiology + environmental data, AI-analysed for errors, teamwork, distractions, efficiency — aviation-black-box model. Scale (secondary/vendor summaries): ~450 procedure rooms (North America/Europe), >100,000 surgeries recorded in 2025 reporting, >100 peer-reviewed publications. Findings a simulator should teach: adverse events usually arise from *accumulations* of small deviations (distractions — median **81 distractions/hour** in hybrid-OR study, mostly door traffic — communication failures, equipment issues), not single blunders; checklist *quality* observed on video (47% items completed) diverges sharply from EMR-reported completion (89%) in gynae-OR study (45 cases) — i.e. ticking ≠ doing. dVLogger line of work (Hung, USC): kinematic metrics (time per step, instrument/camera path length, camera-move frequency) over 100 prostatectomies separated novice from expert — the metric set a simulator can compute natively.
- 🟡 Commercial/proprietary platform; research findings are citable, platform/data are not open.
- URLs: https://magazine.utoronto.ca/research-ideas/health/operating-room-black-box-makes-surgery-safer/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC12408729/ ; https://hscnews.usc.edu/black-box-recorder-watches-surgeons-robotic-surgery-skills

**10.3 Intraoperative navigation / AR guidance**
- State of evidence (high level): navigation is standard-of-care-adjacent in neurosurgery/ENT/spine (frameless stereotaxy), investigational-to-early-adoption for soft-tissue abdominal surgery because deformable registration remains unsolved; fluorescence guidance (ICG) is the pragmatic "augmentation" with the broadest current adoption (perfusion, biliary anatomy, sentinel node) and RCT-level support in colorectal perfusion assessment; AR overlay trials show accuracy gains in phantoms/cadavers with limited patient-outcome RCTs. A simulator should implement ICG + navigation concepts and label AR outcome claims as early evidence. No primary AR source was fetched this round — partially verified.

**10.4 FDA-cleared AI in radiology / surgery — FDA AI-Enabled Medical Device List**
- Landscape (counts move monthly — date-stamp any in-product figure): JAMA Health Forum cross-section counted **950 AI/ML devices cleared/approved as of 7 Aug 2024**; trade tallies of the FDA list put the cumulative total at **~1,451 through end-2025, ~76% radiology** (1,104 devices), with 2025 alone contributing ~331–335 authorisations; later 2026 tallies reach 1,614 entries (76.2% radiology panel, 96.2% via 510(k)). Radiology leaders by cumulative authorisations: GE HealthCare (~120), Siemens Healthineers (~89), Philips, Canon, Aidoc. Surgery-specific AI (video analysis, guidance) remains a small minority vs imaging. FDA list itself is public and downloadable — the authoritative source; FDA cautions the list is "not comprehensive."
- ✅ OPEN — FDA list is a US-government publication; download and cite the list directly in product, with retrieval date.
- URLs: https://intuitionlabs.ai/articles/fda-approved-ai-medical-devices-list (secondary tally, index) ; https://lymyvoyage.com/articles/fda-ai-medical-devices-radiology (independent tally agreeing on 76% radiology share)

**10.5 Telementoring / telesurgery status**
- Arc: **Lindbergh Operation, 7 Sept 2001** — Marescaux (New York) → patient in Strasbourg, transatlantic robotic cholecystectomy; then ~20 years of pilots, blocked by latency/cost/regulation. Telementoring/teleproctoring (dual-console, telestration, Telepresence) became routine first. Post-2020 5G/fibre revival: acceptable latency generally **<200–300 ms round trip**; reported series include China multicentre mean delay ~55 ms (37 patients, 2023–24), China→Kuwait ~181 ms over 7,000 km (Dec 2024), Florida→Angola prostatectomy ~7,000 miles in a first FDA-approved transcontinental telesurgery trial (2025, secondary reporting), and a May 2026 Guyana→India case at ~20,000 km / 290–300 ms (review reporting). Status verdict: **telementoring is deployable now; true telesurgery is demonstrated and in early trials, not standard care** — governance, licensure, liability and reimbursement frameworks lag the technology (2026 *J Robot Surg* review).
- 🟡 Review/open reporting; individual case claims are single reports — present as milestones, not outcomes evidence.
- URLs: https://link.springer.com/article/10.1007/s11701-026-03962-w ; https://www.ircad.fr/telesurgery-a-lever-for-equity-in-access-to-healthcare-worldwide/

---

### 11(a). Coverage Map — what has a citable open foundation vs paywalled / expert-only

| Field | Open foundation (build now) | Cite-only (teach facts, link out) | Paywalled / expert-only (licence or rewrite) |
|---|---|---|---|
| Anatomy geometry | ✅ BodyParts3D CC BY 4.0, HRA CC BY 4.0, Visible Human (no licence since 2019) | Organ-size nomograms | — |
| Anatomy text/variation | ✅ OpenStax A&P | — | 🔴 Bergman's, Gray's 42e, Netter atlases, embryology (Langman/Moore) |
| Physiology engine | ✅ OpenStax values, published Guyton numbers as facts | Haemodynamic/PFT/renal range tables | 🔴 Guyton & Hall, Boron & Boulpaep full text/models |
| Perioperative standards | ✅ WHO Checklist, ERAS free PDFs, War Surgery (federal) | SSC 2021, ASHP/IDSA prophylaxis, ASA standards (free to read) | 🔴 ATLS manual/course content |
| Surgery procedures | ✅ WSES guidelines (World J Emerg Surg, CC BY), Tokyo Guidelines summaries | CVS literature (observational) | 🔴 Schwartz, Sabiston, operative atlases (Zollinger's) |
| Pharmacology data | ✅ openFDA, DailyMed/RxNorm (verify terms), ATC/DDD searchable | Published MAC/CSHT/TCI parameters as cited facts | 🔴 DrugBank data (NC + commercial licence), Goodman & Gilman's |
| PK/PD code | ✅ OpenTCI/STANPUMP, SimTIVA GPL-3.0, R `tci` | Eleveld/Minto primary papers | Commercial TCI pump firmware models |
| Imaging | ✅ HU scale/facts, FAST accuracy (Cochrane numbers) | ACR Appropriateness Criteria (browse free, no redistribution) | 🔴 Radiopaedia content/images (NC), core radiology texts |
| Diagnostic reasoning | ✅ NAM diagnostic-error report, PMC debiasing reviews | RCE likelihood ratios as cited facts | 🔴 JAMA RCE full text, JAMAevidence |
| Epidemiology | ✅ CDC WONDER aggregates, Orphadata Science CC BY 4.0 | GBD (non-commercial only), SEER aggregates | 🔴 SEER microdata (DUA-gated), GBD commercial use |
| Med-ed framework | ✅ USMLE outline (as map), PMC mastery-learning papers, Anki (AGPL) | ACGME Milestones structure, Core EPAs | 🔴 NBME items, commercial Qbanks/OSCE banks |
| Special populations | ✅ Pregnancy review (open), PALS/Broselow method facts | Paediatric nomograms | 🔴 Broselow tape product, Harriet Lane, Nelson |
| Frontier tech | ✅ FDA AI device list (federal) | OR Black Box / dVRK research papers | 🔴 Vendor platforms, kinematics datasets, Hugo/Versius data |

### 11(b). Ten Highest-Value Sources to Build On First

1. **OpenStax Anatomy and Physiology 2e** (Rice) — the only open textbook spine for anatomy + physiology text and normal values. Resolve the CC BY vs BY-NC-SA edition discrepancy first. https://collection.bccampus.ca/textbook/jLnD8djx/
2. **BodyParts3D (DBCLS, CC BY 4.0) + HuBMAP Human Reference Atlas (CC BY 4.0)** — together, a complete, redistributable male + female 3D anatomy foundation. https://github.com/slorksmo/human-atlas/blob/HEAD/public/ATTRIBUTION.md
3. **NLM Visible Human Project** — cross-sectional ground truth linking the atlas to CT/MRI slices; no licence required since 2019. https://zenodo.org/records/16114440
4. **openFDA (+ DailyMed/RxNorm)** — public-domain drug labels, adverse events and approvals; the pharmacology data layer DrugBank cannot legally provide. https://open.fda.gov/apis/drug/ndc/how-to-use-the-endpoint/
5. **WHO ATC/DDD Index** (Oslo Centre) — the international drug classification + dose-unit standard; free searchable. https://www.who.int/toolkits/atc-ddd-toolkit/about-ddd
6. **OpenTCI / STANPUMP + SimTIVA (GPL-3.0) + R `tci`** — ready-made, citable PK/PD models (Marsh/Schnider/Eleveld/Minto) that make the anaesthesia engine quantitative on day one. https://search.r-project.org/CRAN/refmans/tci/html/00Index.html
7. **WHO Surgical Safety Checklist + ERAS Society guidelines** — free, evidence-quantified perioperative standards (checklist: mortality 1.5%→0.8%; ERAS: complications ~−50%) that double as simulator scoring rubrics. https://www.who.int/news/item/11-12-2010-checklist-helps-reduce-surgical-complications-deaths ; https://erassociety.org/guidelines/?speciality=colorectal
8. **Surviving Sepsis Campaign 2021 + Sepsis-3** — SOFA ≥2, MAP ≥65, lactate >2, 30 mL/kg, hour-1 bundle: a complete, computable acute-care scenario specification. https://emottawablog.com/2022/06/surviving-sepsis-the-2021-review/
9. **CDC WONDER (+ GBD Results for global, non-commercial)** — realistic base rates for every simulated case, by age/sex/place. https://wonder.cdc.gov/wonder/help/cancer-v2022.html ; https://www.healthdata.org/research-analysis/about-gbd/gbd-data-and-tools-guide
10. **JAMA Rational Clinical Examination likelihood-ratio corpus (as cited facts) + NAM *Improving Diagnosis in Health Care*** — the quantitative core (LRs, priors, error epidemiology: 5%/year outpatient, ~10% of deaths) for the reasoning workbench; free NAM report anchors the curriculum, RCE values are entered one-by-one with citations. https://jamanetwork.com/journals/jama/article-abstract/1107536 ; https://www.eurekalert.org/news-releases/770275

## Could not verify

- **Hernia repair guidelines (HerniaSurge / EHS-AHS):** no primary guideline retrieved this round; hernia section deliberately withheld from numeric claims until sourced.
- **ASA standards:** verified via secondary summaries; the product should cite ASA's own current standards PDF (asahq.org) — fetch and date-check it at build time.
- **ACR Manual on Contrast Media / MRI contrast:** standard reference identified by reputation, current edition and open URL not fetched; MRI section is therefore framed conservatively.
- **Open embryology atlas, geriatric primary datasets, AR-navigation primary trials, entrant robot FDA statuses (Hugo/Versius/Ottava), DailyMed/RxNorm licence texts, AAMC Core EPA edition:** not fetched this round; flagged inline where relied on as framing only.
- **OpenStax 2e licence conflict:** sources disagreed (CC BY 4.0 vs CC BY-NC-SA 4.0 statements). Must be resolved on OpenStax's own licence page before redistributing 2e content.
- **ATLS edition transition:** 10th ed. is the stocked manual; 11th ed. (2025) is cited by a university course page. Confirm ACS's official current edition at build time and version the simulator's trauma content accordingly.
- All research was via the web index; no paywalled full texts were opened. Numbers reported are as published in the cited sources, with inter-source ranges preserved where sources disagree.

## Sources

All URLs are listed verbatim under each item above. Publisher/society/agency sources: WHO (who.int), ERAS Society (erassociety.org), ACS Store (store.facs.org), NLM/NIH (zenodo.org record of IDC conversion), DBCLS/HuBMAP (via attribution records), FDA (open.fda.gov, medicine.com label summary), WHO Collaborating Centre Oslo (atcddd.fhi.no, who.int), IHME (healthdata.org, thelancet.com/gbd), CDC (cdc.gov, wonder.cdc.gov), INSERM Orphadata (orphadata.com), ACR (acr.org, acpjournals.org), National Academies (via eurekalert.org, healthitanswers.net), FSMB/NBME outline (usmle.org mirror), Intuitive (intuitive.com), Stanford Robotics Center, Univ. of Toronto Magazine, Springer (link.springer.com), IRCAD. Secondary/summary sources are labelled as such inline (e.g. Slideshare ASA summary, cheat-sheet pressor summary, revision notes for pregnancy) and should be replaced by primary PDFs at build time where flagged.
