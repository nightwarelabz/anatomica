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

