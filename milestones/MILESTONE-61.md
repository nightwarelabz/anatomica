# Milestone 61 — Case #9: the diagnosis the patient brought with him

**Status: built and verified locally; landing with this batch. The
expert-review gate for this case is UNMET (no named reviewers exist;
none are fabricated), its content status is `dual-sourced-draft`, and
its scores are formative-only — as for every case in the library.**

---

## 1. What was built

Case #9 of the twelve the master plan mandates (P7): **acute upper
gastrointestinal bleeding** — `cases/case.upper-gi-bleed.009.json`, its
model-learner attempt, and its generated debrief. The plan does not
enumerate the remaining four cases, so the presentation was chosen
under the milestone brief's two tests: it exercises a physiology link
no case has used (the circulation side under perturbation — the
hemorrhage arms — rather than the calcium axis of Milestones 57–60),
and it is clinically disjoint from cases 1–8 (no shared presentation,
organ system in the lead, or reasoning shape).

The case also closes the README drift Milestone 60 left behind
(§11): the `case_check` figure, the case count, the register extent,
the milestone rows for 60 and 61, and the file index are all brought
current in the same batch, and `tools/readme_check.py` returns fully
green with no assertion edited.

## 2. The case

A 71-year-old retired joiner, two days of black tarry stool,
light-headed on standing. He explains himself before anyone examines
him: *"It's my gastritis again. It flares up every winter, burns for a
few days, and settles with the pink medicine and plain food."* Two
prior episodes, same story, both self-treated, **neither investigated**
— the word "gastritis" is his own coinage, never scoped, never tested.
Four years of self-medicated ibuprofen for knee osteoarthritis, no
gastroprotection. Arrival: pulse 102, BP 124/76.

Four stages: **(1)** arrival — his history, the examination, the
rectal examination (frankly melenic stool); **(2)** first bloods and
orthostatics — urea 33 against a creatinine of 1.0, a hemoglobin of
13.9 that is *inside the normal range*, a 20 mmHg systolic fall on
standing, and the risk score completing at 6; **(3)** deterioration
and endoscopy — fresh hematemesis at six hours, the repeat hemoglobin
at 7.6, and the scope: an 18 mm ulcer on the posterior wall of the
duodenal bulb with a non-bleeding visible vessel, treated with
epinephrine injection plus two clips to hemostasis, the stomach and
oesophagus surveyed normal; **(4)** the course — no rebleed, the
count 7.7 untransfused at 24 hours, the biopsy urease test positive.

Ground truth: bleeding duodenal ulcer, Forrest IIa, NSAID-associated
and *H. pylori*-positive. Six hypotheses (priors all verify-flagged
placeholders, flagged in their notes): duodenal ulcer 0.34,
gastritis-erosions *as the patient states it* 0.26, varices 0.10,
gastric malignancy 0.10, lower-GI source 0.12, Mallory-Weiss 0.08.

## 3. The evidence and its prices

Four likelihood ratios exist in this case. Every one is a **computed
reciprocal** of a figure from a source consulted in-session —
Srygley et al.'s Rational Clinical Examination (JAMA 2012, C64) —
registered in `cases/parameters.json` with its derivation, and the
checker verifies the finding, the registration, and the arithmetic
prose against each other on every run:

| finding | consulted figure (C64) | registered |
|---|---|---|
| melenic stool **on examination** | LR 25 (4–174), upper over lower source | lr− **0.04** vs lower-GI source |
| BUN:creatinine ratio 33 (> 30) | summary LR 7.5 (2.8–12.0), upper over lower | lr− **0.1333** vs lower-GI source |
| tachycardia 102 | LR 4.9 (3.2–7.6), severe over non-severe | lr− **0.2041** vs the anchor |
| hemoglobin 7.6 (< 8) | LR range 4.5–6.2, severe over non-severe | lr− **0.2222** vs the anchor (conservative end, per the register's C52 convention) |

The anchor hypothesis is *defined by its severity claim* — minor,
self-limited, settling without intervention — because that is the
claim the patient actually makes, and it is recorded in the
hypothesis's label so no reader can miss the move: the RCE's severity
ratios therefore price the anchor directly, in reciprocal form. The
bare word "gastritis" names a real disease; the case prices the
sentence, not the word.

What carries **no** ratio is as deliberate: patient-reported melena
(subsumed by the examination finding in the same source), the
preserved first hemoglobin (the RCE prices only the < 8 tail; the
case answers the number with mechanism instead, §7), the hematemesis
(the RCE prices nasogastric aspirate, a test this encounter never
performs), the orthostatic drop, the NSAID history, and every
endoscopy finding (direct inspection is not a sensitivity/specificity
pair in any consulted source). Each carries its reason in its text.

Workbench trajectory: ulcer 0.5016 → 0.5047 → 0.5376; the lower
source is ruled out at stage 1 (0.0071); the anchor is priced to
0.0783 at stage 1 and **ruled out at stage 3 (0.0186)**. Briers:
workbench 0.3121 → 0.2802; learner 0.6488 → 0.544 → 0.3314 → 0.0586.

## 4. The two declared blocks — the library's first score and first classification in one case

**Glasgow-Blatchford (C63)** — a `score` block on the original
bands (BUN mg/dL ≥70→6, ≥28→4, ≥22.4→3, ≥18.2→2; hemoglobin, men's
bands, <10→6, <12→3, <13→1; SBP <90→3, <100→2, <110→1; pulse ≥100→1;
melena→1; syncope→2; hepatic disease→2; cardiac failure→2; maximum
23). Stage 1 computes a **partial 2** (pulse + melena; both blood
items unmeasured, flagged `not_assessed` by the machinery — a partial
total is a floor, and the case's band text says so). Stage 2
completes it at **6** (BUN 4 + pulse 1 + melena 1; hemoglobin 0,
pressure 0, absences 0) — Blatchford's band in which over half the
validation group needed an intervention or died. Two disciplines are
checker-asserted: the items reference **admission values only**, so
the stage-3 hemoglobin of 7.6 never re-enters the score (it would
take the total to 12; the profile proves it stays 6), and the
stage-1 partial is asserted as partial, not quoted as a total.

**Forrest classification (C66)** — a `classification` block over
five endoscopy findings, each recorded present or absent as its own
finding so no class is reached by default: pending at stages 1–2,
**IIa** from stage 3 (the visible-vessel rule, index 1; the other
four stigmata absent). The classification is Forrest's (1974), cited
through the ESGE guideline that prices its consequence — the
original paper was not consulted and is not cited.

Orders (machinery classifications, asserted): admission bloods
*criteria-completing* (settles both Blatchford blood items);
endoscopy *criteria-completing* (settles all five Forrest inputs);
serial hemoglobin **discriminating** (its below-8 finding crosses
the anchor over the rule-out line at stage 3); orthostatics,
interval reassessment and post-endoscopy review *non-contributory*
— the case owns, in the checker text itself, that the two bedside
orders did clinical work the classification cannot price. Tally:
120 min / 13 units (verify-flagged placeholders, house rule).

## 5. The anchor — the ninth shape: installed by the patient

The library's anchoring series, one shape per case: **(1)**
pattern-completion (the Charcot triad completed from two of three);
**(2)** the treatability anchor (the stone the ERCP could reach);
**(3)** the feared-outcome anchor (the ectopic held past its
refutation); **(4)** clinician-frame (a label pre-installed by
another clinician); **(5)** self-installed exposure inference (the
learner's own reasoning from a true history); **(6)**
result-installed value (a laboratory number, mid-case); **(7)**
social pressure (a demand for action, supplying no diagnosis; the
error was over-testing); **(8)** premature closure by inheritance
(a frame absorbed from a note written for another purpose).

Case 9's installer is none of these. **The diagnosis is supplied by
the historian himself, at presentation, in the first minute, with
the authority of lived experience** — "it flares every winter, it
settled twice, they wanted to test me and it was nothing." Three
properties make it structurally distinct, not merely a new source
for an old shape. *First, the warrant is autobiographical:* cases
4–8's frames borrow the authority of a colleague, a result, a crowd
or a chart; this one's authority is the patient's own body and
memory, which a learner is trained to respect — taking the history
is the job, and the diagnosis arrives inside it, indistinguishable
in form from the facts around it. *Second, the frame is the benign
diagnosis:* the error direction is **under-triage** (a discharge
that has to be refused), the exact mirror of case 7. *Third, its
evidence is genuinely supportive and genuinely worthless:* two prior
episodes did settle — because an intermittently bleeding ulcer
settles, and because the label was never tested, the survival of
the unscoped episodes is presented as their verification. The
finding text names the trap: an unscoped "gastritis" and an
unscoped ulcer are the same story told twice.

The scored event is exactly one: the learner adopts the frame as
his stage-1 lead (0.36 against the truth's 0.30), is steadied by
the normal first hemoglobin through stage 2, and still holds it at
**0.16 at stage 3** — the stage the workbench rules it out
(0.0186) — because the man in the bed still believes it. He
converges at stage 4 and commits the truth with its full
management.

## 6. Management and disposition

Admit to a monitored bed (the completed Blatchford 6 and the
orthostatic drop jointly demand it; the patient's discharge plan is
refused *on the record*, as the alternatives list). Endoscopy early
— within 24 hours (ESGE 2021, C66; ACG 2021, C70, concordant) —
booked at stage 2 and expedited when the in-hospital hematemesis
met the guideline's very-early criteria; **not** urgent-at-arrival,
and the case records that routine ≤12 h endoscopy is what the
guideline recommends *against*, so the timing is argued, not
assumed. Combination hemostasis (epinephrine + clips; epinephrine
alone is never the standard). High-dose IV PPI 80 mg + 8 mg/h for
72 h after hemostasis (C66, C70). **No transfusion:** nadir 7.6
against the restrictive threshold of Villanueva 2013 (C65 —
transfuse below 7, target 7–9; the trial's exclusions, massive
exsanguination and acute coronary syndrome, do not apply), with the
untransfused 24-hour count of 7.7 as the recorded outcome.
Ibuprofen stopped permanently, with an alternative knee plan (an
unmanaged knee is how he would quietly restart it; C69's resumption
terms are cited). *H. pylori* eradication with documented
eradication (C69). Safety-netting that names the frame itself as
the risk. Refused on the record: transfusion at 7.6, routine
second-look endoscopy, first-line surgery/embolization. **No
Theatre handoff exists** — the Theatre holds no endoscopy
procedure — and the case states the absence in a `theatre_note`
rather than eliding it.

## 7. The physiology link — the library's first perturbation arm

Baseline: identity with cases 1–8 (the pinned resting run, trace
hash `0x6369b10e9a71c872`, the same seven outputs). The new work is
the two hemorrhage arms, run in-session against the shipped engine:

- **`run hemorrhage`** (750 mL over 60 s): engaged-baseline MAP
  72.9; post window — HR 102.1, BP 85.6/62.5, MAP 68.9, pulse
  pressure 23.2, CO 3.46, SV 33.9 mL, CVP 3.12; trace hash
  **`0xbc683bf2721147ae`**. It prices the compensation *pattern*:
  pressure defended while stroke volume halves and the pulse
  pressure narrows — the shape of his arrival vitals. (The post
  window's HR of 102.1 sits numerically near his 102; the case
  states this is a coincidence of bands, NOT an identity, and
  claims nothing from it.) The checker **re-runs this arm on
  every validation** and compares hash and every output — the
  first perturbation-arm pin of its kind in the library.
- **`run course`** (untreated −1,500 mL): hematocrit **0.432 at
  +1 min, 0.399 at +60 min**, net transcapillary refill
  **408.04 mL** at 60 minutes, trace hash `0xaf89c09ff6c631f9`.
  This arm is the case's central mechanism: whole blood is lost
  at its own concentration, so at the moment the bleeding stops
  the hematocrit is still the pre-bleed value, and the count
  falls only as refill (and administered crystalloid) dilute
  what remains. That is why a man two days into a significant
  bleed presents with a hemoglobin of 13.9 — and why the case
  forbids that number from closing anything. Pinned by identity:
  the hematocrit marks against Milestone 26's printed course
  table, the hash against Milestone 30's dossier, the refill
  figure against this dossier (the course run takes ~a minute;
  the checker does not re-run it — the M60 precedent).

**Gaps, stated in the case and not smoothed:** tempo (the engine
bleeds in seconds-to-minutes; he bled over ~two days — pattern and
lag transfer, magnitudes do not, and no engine number is presented
as his volume lost); subject (a standard adult, not 71; reflex
ageing unmodelled); anatomy (no gut, no ulcer, no endoscope exists
in the engine); chemistry (**urea is not an engine state** —
Milestone 30 carries it in the constant osmolality term — so the
BUN this case prices through Blatchford and the ratio finding is
authored data the engine cannot check); fluids (the crystalloid
litre is an encounter event; the engine's crystalloid course
variant exists but is not linked, because the claim needs only the
untreated lag).

## 8. The imaging link — localisation only, and why it can be no more

The s0778 **duodenum** label (crosswalk index 10 → Body Model
record `canal.duodenum`): files 166–214, 49 slices, **15,235
voxels** — recounted from the shipped web bins by the checker,
equal to the crosswalk's count; maximum cross-section file 176,
515 voxels; z-range 1492.92–1564.92 mm reproduced by slice
arithmetic; volume 51.42 mL. The link localises the *organ* the
endoscopy found the ulcer in. The label set holds organ labels
only — no ulcer, erosion or stigmata label exists, none was
invented, and a mucosal lesion is an endoscopic finding, not a
segmentation structure; the case's `ulcer_label_absence` block and
the standing three-individuals honesty block say all of this in
the file. The CT is not, and is not presented as, the diagnostic
test for this presentation.

## 9. Ontology — five classes verified, one refusal, one rejection

Via EBI OLS in-session, appended to the C10/C11 registers as dated
Milestone 61 addenda: **duodenal ulcer MONDO:0005412** ("An ulcer
in the duodenal wall"; parent peptic ulcer disease MONDO:0004247
verified at Milestone 20), gastritis MONDO:0004966, esophageal
varices MONDO:0001221, Mallory-Weiss syndrome MONDO:0043247,
gastric cancer MONDO:0001056. Phenotypes: melena HP:0002249,
hematemesis HP:0002248, tachycardia HP:0001649, orthostatic
hypotension HP:0001278; syncope HP:0001279 asserted as an explicit
**absence** (a scored Blatchford item).

**Refusal (the library's fourth):** the lower-GI-source hypothesis
carries Mondo **null**. Two OLS searches ("lower gastrointestinal
hemorrhage"; "diverticular disease") returned no Mondo class; the
hypothesis names a bleeding-source *location*, not one disease,
and its likeliest lesion (colonic diverticulosis) has a phenotype
term (HP:0002253) but no verified class in this pass. It was
specifically **not** coded to diverticulitis — an inflammation the
patient does not have. The refusal is written in the hypothesis,
the register addendum, and the checker asserts it. **Rejection:**
HP:0002321, the candidate for lightheadedness, resolves to
*vertigo* — a spinning sensation this presyncopal patient does not
describe — checked, not used, and recorded on C11.

## 10. Sources and the register

`cases/parameters.json`: register C1–C62 → **C1–C70**
(`extended_at_milestone` 57 → 61). New: **C63** Blatchford 2000
(the score's table and validation finding); **C64** Srygley 2012
(the RCE — every ratio in the case); **C65** Villanueva 2013 (the
restrictive threshold, exclusions recorded); **C66** ESGE 2021
(timing, Forrest therapy mapping, PPI, restrictive target); **C67**
MedlinePlus hemoglobin (male 13.8–17.2 g/dL); **C68** MedlinePlus
creatinine (men 0.7–1.3 mg/dL); **C69** ACG 2012 (H. pylori
eradication + documented cure; NSAIDs stopped); **C70** ACG 2021
(the second guideline voice — threshold, timing, therapy, PPI
concordant with C66; the safety-relevant management is therefore
dual-sourced, per the precision law). The urea range rides the
existing C47. LR derivations 22 → **26** (the four reciprocals).
The builder's deep-compare proved the register's prior content
unchanged apart from the intended edits and the C10/C11 addenda
(36 pre-existing `\u2014` escapes normalised to raw UTF-8 in the
re-serialisation — formatting only; every consumer parses JSON).
StatPearls/NCBI remains reCAPTCHA-blocked and is cited for nothing.

## 11. README reconciliation (this batch)

`README.md` edits, all forced by figures this milestone (or
Milestone 60) moved: **(1)** the case_check figure 13,135 → the
final post-M61 total (this also discharges Milestone 60's
13,135 → 13,160 correction — the README had been stale by two
milestones; the pre-batch `readme_check` baseline, measured
before any M61 file landed, failed on exactly three lines —
R9 (13,135 against the printed 13,160), R10 (59 milestone
rows against 60 on disk) and R11 [milestones] (64 against
65) — the complete drift this batch closes); **(2)** case count 8 → 9 and register extent
(62 sources, C1–C62) → (70 sources, C1–C70), with one sentence
added to the Cases paragraph for case #9; **(3)** milestone-index
rows for **60** and **61**; **(4)** the file index: `cases/` 27 →
30 files (the case, its attempt, its debrief), `milestones/` 64 →
66 files (MILESTONE-60.md had landed at Milestone 60 without an
index row — the second standing drift this batch closes — plus
MILESTONE-61.md), total 632 → 637. No `readme_check` assertion was
edited; the guard's R6 brittleness (a hardcoded `T41)` literal,
recorded at Milestone 59) is untouched because theatre's register
did not move.

`cases/README.md`: header milestone list (+61), register extent
(C1–C70, two places), the register-extension paragraph (C63–C70 and
the four reciprocal derivations), the case-9 contents entry, the
attempts paragraph (the ninth shape), and the debriefs line's
checker total brought current.

## 12. Verification

- `tools/case_check.py`: **13,160 → 14,919 checks, 0 failed** —
  the generic sections run over all nine cases unchanged, plus
  `profile_case9` (45 assertions: counts; the LR census and the
  no-LR list; the four derivations; the ratio and orthostatic
  arithmetic; Blatchford stage-by-stage including the partial and
  the admission-discipline proof; Forrest timing and rule index;
  both trajectories, rule-out stages and Briers; the single
  anchoring event and the learner's frame-adoption board; order
  classifications and tally; the baseline identity; the hemorrhage
  arm **re-run** with hash + outputs compared; the course pins;
  the duodenum recount; the Mondo refusal and the vertigo
  rejection; the register extent). `profile_case8`'s register
  assertion was updated 57 → 61 (it asserts the register's current
  extent, as its own text now states).
- `tools/theatre_check.py`: 736 checks, 0 failures (unmoved).
- Every other `tools/*_check.py`: exit 0; `tools/verify_web.js`:
  ALL CHECKS PASS; native `verify`: 99 data assertions PASS,
  0 FAIL (the GL/Vulkan render stage cannot initialise on this
  VM — the standing disclosed limitation).
- `tools/readme_check.py`: FULLY green (see §11) — including R9
  against the new case_check total and R10/R11 against the new
  index.
- Hash census before/after (`work/m61/census-before.txt` against
  the final tree): cases #1–#8, their attempts and their debriefs
  **byte-identical**; the only case-folder changes are the three
  new files, `cases/parameters.json` (intended edits only, §10),
  and `cases/README.md`.

## 13. The landing batch

Eight files: `cases/case.upper-gi-bleed.009.json` (new),
`cases/attempts/attempt.case-upper-gi-bleed-009.model-learner.json`
(new), `cases/debriefs/debrief.case-upper-gi-bleed-009.model-learner.json`
(new, generated by `tools/case_run.py`),
`cases/parameters.json`, `tools/case_check.py`, `cases/README.md`,
`README.md`, `milestones/MILESTONE-61.md`. Local working files
(`work/m61/`, including the case builder) are not landed, per house
practice.

## 14. What remains open

The case library stands at **9 of the plan's 12**; the expert-review
gate is UNMET for this case as for all (required roles recorded:
gastroenterologist, emergency physician — none named, none
invented). The Theatre still holds no endoscopy procedure, so this
case's procedural act has no hash-link to make; a future Theatre
endoscopy would give it the idiom cases 2 and 8 use. The two
standing ANATOMICA blockers are untouched by this milestone: the
geometry decision (Milestone 34 audit) and the Terminologia
Histologica source decision.
