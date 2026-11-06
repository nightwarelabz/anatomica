# 07 — Cases & Hypothesis Workbench

## Purpose

Diagnosis practiced as explicit reasoning: a simulated patient on the
physiology engine, a differential board the clinician must commit to, tests
with real cost and information value, and a debrief that replays the reasoning
against the ground truth.

## Case format

```json
{
  "id": "case.chest-pain.001",
  "ground_truth": {"engine_state": "…", "mondo": "MONDO:…", "hpo": ["HP:…"]},
  "patient": {"age": 58, "sex": "M", "habitus": "…", "history": ["…"],
              "medications": ["drug.…"]},
  "presentation": [{"stage": 1, "text": "…", "vitals_from_engine": true}],
  "exam_findings": [{"id": "…", "finding": "…", "lr_plus": null, "source": "…"}],
  "available_tests": ["test.…"],
  "resource_tier": "enhanced",
  "authoring": {"sources": ["…"], "review": ["…"]}
}
```

- The patient *is* an engine state: presentation vitals, exam findings, labs,
  and imaging are computed from the ground-truth perturbation/pathology, so a
  case cannot contradict itself (the troponin rises when the engine's MI says
  so). Staged presentation reveals findings in the order a clinician would
  meet them; the engine clock runs during deliberation — delay has the
  consequences the literature says it has (e.g., torsion salvage ~100% <6 h →
  <10% at 24 h; TXA window ≤3 h).
- **Base rates are data:** case priors come from published epidemiology
  (CDC WONDER open aggregates; GBD — non-commercial terms, so GBD-derived
  numbers ship only where their license permits, else re-derived from open
  sources; SEER aggregates open, microdata DUA-gated and never shipped).
  Sepsis priors are ranges by source and geography (pneumonia commonest
  ~30%; culture-negative up to ~30%) — a case that teaches a single base rate
  for the world fails review.

## Knowledge spine (all license-clean)

Mondo (CC BY 4.0) and Disease Ontology (CC0) for disease identity; HPO for
phenotypes — HPO terms are **layered beside, never altered** (its license
forbids modification); Orphadata Science (CC BY 4.0) for rare disease.
LOINC and RxNorm ship as **separately-licensed data packs**, clearly fenced
from the AGPL core. **SNOMED CT never enters the repository** — at most an
optional user-supplied pack under the user's own affiliate license.
IDSA guidelines are cite-only (© OUP); stewardship teaching builds on CDC's
public-domain Core Elements (incl. the 48-hour antibiotic timeout).

## The reasoning workflow

1. Presentation (staged). 2. **Differential board:** the clinician lists
   hypotheses with explicit priors (the UI forces a number — vague
   differentials cannot be scored or calibrated). 3. **Test ordering:** exam
   maneuvers, labs, imaging (from `06`), each with cost, time, and published
   test characteristics where they exist (JAMA Rational Clinical Examination
   likelihood ratios are *citable* — e.g., S3 gallop LR+ ≈ 11 for heart
   failure — the underlying series is paywalled, so LRs enter only as cited
   values, never scraped text). 4. **Posterior revision:** the board re-ranks
   as results land. 5. **Management & disposition** (pharmacology layer,
   Theatre referral for operative findings, admit/discharge). 6. **Debrief:**
   ground truth revealed, pivotal evidence highlighted, the clinician's path
   replayed from the deterministic engine log; debrief follows the PEARLS
   structure (reactions → description → analysis → summary) per the human-
   factors research.

## Calibration as the headline metric

Per-clinician calibration curve (stated confidence vs outcome frequency) and
Brier-style scoring across cases, stored locally; the workbench's home metric
is calibration, not raw accuracy — the diagnostic-error literature (National
Academy 2015: ~5% of outpatients yearly, ~10% of deaths) and the debiasing
evidence (~70–75% of errors carry a cognitive component; consider-the-opposite
and diagnostic time-outs outperform bias lectures) shape the debrief prompts.

## Interchange

Cases export/import as **FHIR** (spec CC0) bundles — Patient, Condition
(Mondo-mapped), Observation (LOINC-coded from the pack), DiagnosticReport —
so cases are portable beyond ANATOMICA and educators can exchange them.
Theatre post-op complications generate case stubs in the same format (the
missed bile-duct injury returns as a case), closing the loop between modules.

## Case builder

Educator tool: set ground truth on the engine, stage the presentation, attach
findings/tests, preview as a learner, publish the case file. Builder output
passes the same validators (dual-source findings, cited LRs, review block)
before it can be marked shareable.

## Verification gates

- Case self-consistency: engine replay produces every presented value.
- Every LR/test characteristic carries a citation; uncited numbers fail.
- Priors declared as ranges with sources; geography stated.
- Review block (≥2 reviewers) before a case counts as library content.

## Open decisions

- **OD-07.1** GBD-derived base rates: ship re-derived open-source rates only,
  or also offer an optional GBD pack under its non-commercial terms for
  non-commercial deployments? Leaning: open-only in the repo; document the
  option. Decide before Cases v1 content work (P7).
- **OD-07.2** Learner data: calibration history is local-only by default;
  any educator dashboard (aggregate export) needs an explicit privacy design.
  Decide at P7; default is local-only, no telemetry, ever.
