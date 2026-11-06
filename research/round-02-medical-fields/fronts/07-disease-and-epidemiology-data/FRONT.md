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

