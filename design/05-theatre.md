# 05 — The Theatre (Surgical Suite)

## Purpose

The centrepiece: operations performed as step graphs over the actual anatomy,
with the physiology engine running the patient underneath, authored by
cognitive task analysis (CTA) and scored by the field's validated instruments.

## Procedure format (CTA graph)

A procedure is a data file (`data/` content pack, JSON), authored against
named operative references, decomposed phases → steps → microsteps:

```json
{
  "id": "proc.lap-cholecystectomy",
  "title": "Laparoscopic cholecystectomy",
  "sources": ["…operative reference…", "…CTA source…"],
  "review": [{"reviewer": "…", "role": "…", "date": "…", "verdict": "signed"}],
  "setup": {"position": "supine, reverse Trendelenburg",
            "anaesthesia": "…", "prophylaxis": {"drug": "cefazolin", "dose": "2 g",
            "timing_min_before_incision": 60},
            "instruments": ["instrument.…"]},
  "phases": [{
    "id": "exposure", "title": "Exposure of the hepatocystic triangle",
    "steps": [{
      "id": "cvs", "title": "Achieve the Critical View of Safety",
      "microsteps": ["…"],
      "targets": ["structure.…"], "danger": ["artery.cystic", "duct.bile.common"],
      "safety_gate": true,
      "decision_points": [{"prompt": "…", "options": ["…"], "bailout": "…"}],
      "errors": [{"id": "divide-before-id", "description": "…",
                  "consequence": {"perturbation": "…"}}],
      "tips": ["…"]
    }]
  }],
  "variants": ["artery.hepatic.right.replaced-from-sma", "…"],
  "resource_tiers": ["basic", "limited", "enhanced", "maximal"]
}
```

Format rules, drawn from the published CTA literature (lap-chole CTA: 19 steps
→ 97 microsteps; robotic bypass CTA: 83 subtasks, 75 errors, 60 tips, 15
decision points):

- Every step names `targets` and `danger` by Body Model ID — the step renders
  on the body, and the risk list is generated, not prose.
- `errors` are first-class: each known error carries the engine perturbation
  or management branch it triggers. Complications are detected from trainee
  action + engine state, never rolled dice.
- `decision_points` always include the field's bailout (e.g., subtotal
  cholecystectomy / conversion) — bailing out correctly scores *positively*.
- **Safety gates:** a step flagged `safety_gate` must be *achieved and
  demonstrated* (the Critical View of Safety's three criteria, Strasberg 1995)
  before dependent steps unlock in assessment mode. Dividing or clipping a
  critical structure that has not been identified **fails the attempt** —
  because the harm literature attributes bile-duct injury ~97% to perceptual
  misidentification (baseline BDI 0.4–0.5% laparoscopic vs 0.2% open).
- **Variants are examinable:** each procedure lists the Body Model variant
  records it can present (variant gate: ≥1% prevalence + injury consequence).
  Assessment draws variants at published prevalence, so a trainee meets the
  replaced right hepatic artery (10–16%) at roughly life rates.
- **Resource tiers:** every procedure declares how it degrades across
  basic/limited/enhanced/maximal resource settings (ASCO-pattern), including
  equipment substitutions — the same operation, honestly taught for a district
  hospital and a tertiary centre.
- **Review block is mandatory:** no procedure ships without ≥2 named expert
  reviewers and a Delphi-style sign-off recorded in the file (governance §8.2).

## Modes

- **Guided** — walk the graph; rationale, danger callouts, anatomy live-linked.
- **Practice** — trainee drives: next step, instrument, approach at decision
  points. Errors perturb the engine; the patient deteriorates and must be
  managed (transfusion per AABB thresholds — 7 / 7.5 / 8 g/dL by population;
  conversion; repair) with the anaesthesia monitor running throughout.
- **Assessment** — timed, hints off; structured score (below); replayable from
  the engine's determinism contract for review and appeals.

## Scoring

- **Rubrics:** OSATS global rating + procedure-specific checklist; GOALS for
  laparoscopic depth perception/efficiency/autonomy domains; GEARS where a
  robotic variant exists. Rubric anchors ship in the module with citations.
- **Safety:** any unidentified-critical-structure division = attempt fail,
  regardless of other scores. Safety-gate completion is scored separately.
- **Physiology management:** scored against engine state (time below MAP 65,
  blood loss vs transfusion timing, TXA inside its ≤3 h window where trauma
  applies — CRASH-2 14.5% vs 16.0% mortality; late TXA scores as an error).
- **Proficiency-based progression:** module unlocks at a published benchmark
  score, not at attempt count (evidence: proficiency-trained residents'
  OR GOALS +6.1 vs +1.8 controls; VR-trained 29% faster, ~5–6× fewer
  gallbladder injuries in the classic RCT).
- Scores are labelled with the module's Messick validity level (see
  `10-governance.md`); until construct evidence exists, scores are
  **formative only** and the UI says so.

## Anaesthesia panel

Induction/maintenance agents from the pharmacology layer (MAC-anchored depth),
airway choice per the ASA Difficult Airway algorithm (2022; 3+1 attempt limit
modelled), ventilation per ARDSNet numbers where applicable (VT 6 mL/kg PBW,
plateau ≤30 cmH₂O), fluids/blood, positioning consequences. Surgeon and
anaesthetist read the same engine state.

## Instruments

Catalogue as data: each instrument record states function, sizes, uses, and
injury potential; suture materials carry published tensile/absorption profiles
(e.g., Vicryl ~75% strength at 2 weeks, absorbed 56–70 days). Practice mode
requires correct selection; a wrong-instrument choice is a scored error with
the consequence modelled where one exists (electrosurgery thermal spread is
single-digit mm — the engine models injury radius as a cited range, not a
constant; see biomechanics ranges in `04`/`10`).

## Verification gates

- CTA completeness checker: every step has targets, danger, ≥1 error or an
  explicit no-error note; every safety gate has criteria; every decision point
  has a bailout.
- Review gate: ≥2 sign-offs present.
- Variant gate: listed variants resolve to Body Model variant records.
- Negative-training audit sign-off per procedure (governance).

## Open decisions

- **OD-05.1** Robotic variants in scope for Wave 1? GEARS is specified, da
  Vinci 5 / dVRK ecosystems are researched, but Wave 1 stays laparoscopic/open
  unless the owner directs otherwise.
- **OD-05.2** ATLS edition pin for trauma procedures: 10th edition is the
  widely held text; an 11th (2025) is cited in round-2 research with the
  transition flagged. Trauma content does not author until the edition is
  pinned by name in the module.
