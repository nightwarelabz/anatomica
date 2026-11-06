# 10 — Governance: Precision, Validity, Release Gates

## Purpose

The operating law that keeps a surgical teaching system trustworthy: the
Precision Law from the master plan, made enforceable — who may assert what,
what evidence a claim needs, and what blocks a release.

## The Precision Law (binding on all content)

1. **Dual-source verification.** No anatomical fact, measurement, drug value,
   or procedural step enters from a single unverified pass. Safety-relevant
   content carries ≥2 authoritative sources, cited in the file.
2. **Nothing invented.** Unknown or contested = a visible *verify* flag or an
   omission. This applies to numbers, geometry, prevalences, and claims about
   the product itself. (Standing example: laser-safety figures had no primary
   source in research round 3 — they are absent, not estimated.)
3. **Every number checkable.** Counts, doses, dimensions, and physiological
   values carry units, normal ranges where applicable, and citations.
   Prevalences are cited ranges, never point values.
4. **Ranges with method tags** where measurement method moves the value
   (tissue biomechanics is the canonical case: ~10× spread by method).
5. **AI-drafted content is quarantined** until it passes the identical
   dual-source + reviewer gates as any other content. No exceptions.

## Messick validity labeling

Every module (data module, engine system, procedure, case, imaging mode)
carries a validity record:

```json
"validity": {
  "content": "expert-reviewed | dual-sourced-draft | draft",
  "response_process": "…", "internal_structure": "…",
  "relations": "…", "consequences": "…",
  "label": "formative-only | construct-evidenced | validated"
}
```

- The label **renders in the product** wherever scores or teaching claims are
  shown. Nothing is called "validated" without construct evidence (known-groups
  separation) at minimum; predictive claims require predictive evidence —
  which, per research, essentially no simulator literature yet has, so the
  word stays rare here too.
- Scores from formative-only modules are labelled formative-only in the UI,
  in exports, and in any educator-facing report. This is a release gate, not
  a style guide.

## Review & sign-off

- Procedures and cases: ≥2 independent expert reviewers, Delphi-style
  rounds for contested steps, sign-offs recorded in the content file
  (name, role, date, verdict). Reviewer identity ships with the module —
  open provenance is the project's answer to institutional co-authorship.
- Data modules: dual-source citations + census/consistency checkers green.
- Disagreements between reviewers are recorded as *verify* flags with both
  positions cited — never resolved by an editor's preference.

## Negative-training audit

Before release, every scenario (procedure, case, perturbation) is audited
against the documented failure modes: unrealistic-scenario negative transfer;
conformity/social-pressure artefacts; skills taught in a form that does not
transfer; simplifications that teach a falsehood (a simplification that is
merely incomplete is documented in-product; one that is *wrong* blocks the
release). Audit sign-off is a named field in the content file.

## Errata & error reporting

- In-product "report an error" on every record, step, and value, filing into
  a public errata log (versioned, in-repo): report → triage → correction or
  reasoned rejection → shipped in the next data release with the correction
  noted. A wrong fact found by any user becomes a tracked public correction.
- Data releases are versioned independently of code; errata reference data
  versions so a learner can tell whether their copy carries a correction.

## Licensing governance

- The provenance ledger (`03`) is the licensing system of record: per-file
  source, license, hash. Release builds fail on `UNKNOWN` or excluded
  licenses (CC BY-NC* in core data; SNOMED CT anywhere in the repo;
  Radiopaedia/ACR ingested content; DrugBank data in any form — its CC BY-NC
  terms are incompatible with AGPL distribution; use openFDA instead).
- License-bound packs (LOINC, RxNorm) ship as separate, clearly-fenced data
  packs with their own license files, never merged into core data.
- GPL-family code (SimTIVA GPL-3.0, Open Systems Pharmacology GPL-2.0,
  SOFA's GPL applications) is reference-only: reimplement from published
  descriptions; never link. SOFA LGPL libraries may link.
- Credentialed datasets (MIMIC-IV, eICU, HiRID, AmsterdamUMCdb): validation
  use only; no data or derived files in the repo, in releases, or in issues.
- Claims discipline (regulatory): the product is education on synthetic
  patients with no real-patient data pathway. Marketing or UI copy that
  implies clinical use is a release-blocking defect (FDA CDS 2022 criteria;
  EU MDR Rule 11 — the intended-purpose line is drawn by claims as much as
  by code).

## Release gates (all must pass)

1. Census + consistency checkers green for every shipped data module.
2. Provenance ledger complete; license audit clean.
3. Engine steady-state + determinism gates green; validation dossiers current.
4. Validity labels present and accurate for every shipped module.
5. Negative-training audit sign-offs present for scenarios.
6. Watermark present on all synthetic imaging export paths.
7. Errata log published with the release; data version stamped.

## Open decisions

- **OD-10.1** Reviewer recruitment is the project's scarcest resource
  (clinician time). The mechanism (advisory board vs per-module reviewers,
  honoraria vs attribution) is an owner decision; the *format* above does not
  depend on it, but P5 content throughput does.
- **OD-10.2** Whether the errata log also accepts anonymous reports.
  Leaning yes with moderation; decide before P10 public release.
