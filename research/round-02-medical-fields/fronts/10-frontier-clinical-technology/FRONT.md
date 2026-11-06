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

