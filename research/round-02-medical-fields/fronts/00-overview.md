# Medical Simulation System — Authoritative, Quantitative State of Knowledge
## For an open-source (AGPL-3.0) system: 3D anatomy atlas · physiology engine · imaging suite · surgical procedure simulator · clinical-reasoning workbench

Research date: 5–6 November 2026 (CST). Method: web index searches, primary publisher / society / agency pages preferred. **Openness verdict key:** ✅ OPEN — can be built on / redistributed in an AGPL educational product (with attribution as stated) · 🟡 CITE-ONLY / NON-COMMERCIAL — read, link, cite numbers as facts, do not copy text/data wholesale · 🔴 PAYWALLED / LICENCE-REQUIRED — do not ingest; teach from own paraphrase of facts or obtain licence. *Facts (numbers, classifications) are not copyrightable in themselves in most jurisdictions; expression, tables as published, images and databases are. This report is not legal advice.*

## Summary

A citable open foundation exists for the **engine** of the system — physiology numbers (OpenStax, Guyton-derived published values), imaging physics (Hounsfield scale), drug classification (WHO ATC/DDD searchable free), US drug labels/adverse events (openFDA, public domain), PK/PD models (OpenTCI / SimTIVA GPL, R `tci` CRAN), 3D anatomy geometry (BodyParts3D + HuBMAP Human Reference Atlas, both CC BY 4.0; Visible Human, no licence required since 2019), epidemiology base rates (CDC WONDER public aggregates; GBD non-commercial), and rare-disease nomenclature (Orphadata Science CC BY 4.0).

The **clinical authority layer remains largely paywalled or non-commercial**: Bergman's, Gray's 42e, Schwartz 11e, Guyton & Hall text, ATLS manuals, JAMA Rational Clinical Examination / JAMAevidence, DrugBank (CC BY-NC, commercial use barred), Radiopaedia (CC BY-NC-SA, contributor-owned images), GBD (non-commercial only). A simulator can *teach to* these standards and *cite their headline numbers*, but cannot copy their text, tables or images into an AGPL product without licence.

Highest-leverage build order is in §11(b): OpenStax + openFDA + ATC/DDD + BodyParts3D/HRA + Visible Human + OpenTCI/SimTIVA + CDC WONDER + WHO Checklist/ERAS free PDFs + Surviving Sepsis 2021 + Orphadata Science.

---

## Findings

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
