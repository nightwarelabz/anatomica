# Milestone 64 — Case #9's Theatre hash-link (the endoscopy loop closed)

**Status: COMPLETE (local).** Case #9 (`case.upper-gi-bleed.009`, Milestone 61)
recorded a standing absence — NO THEATRE HANDOFF — because the Theatre then
held no endoscopy procedure. Milestone 62 authored `proc.upper-gi-endoscopy`
(traces 31–37). This milestone closes the loop in the cases #2/#8 idiom: the
case carries a `theatre_link` pinning its endoscopic act to the one trace
whose lesion, classification, therapy and outcome its course actually
follows — **trace-31-endo-clean** — and `tools/case_check.py` recomputes
that debrief's SHA-256 and matches its fields against the case's claims on
every run. No new trace was needed: the correspondence already existed. No
clinical content changed. No new sources: the case register stays C1–C70.

## 1. The correspondence argument

Case #9's authored course (stage 3, unchanged by this milestone): at 6 h the
patient hematemeses; endoscopy finds an **18 mm ulcer on the posterior wall
of the duodenal bulb, Forrest IIa (non-bleeding visible vessel)**;
**epinephrine injection plus two through-the-scope clips** achieve
hemostasis; the stomach and oesophagus survey is normal; there is **no
rebleed** (stage 4).

Trace 31 is the procedure's clean run under its standard configuration,
on the scenario lesion **`duodenal-ulcer:iia`** (the trace's case block:
*"Case 9's own lesion (Milestone 61) — the posterior-bulb ulcer identified
and localised, classified Forrest IIa and declared; pause; epinephrine
injection followed by through-the-scope clips; hemostasis confirmed;
complete survey — and the case's stage-4 course (no rebleed) follows"*).
Milestone 62 authored the trace for this case's lesion; the case's course
and the trace are the same act at the level the #2/#8 links operate at —
lesion, site, classification, modality, process, outcome.

**Why no second (contrast) trace.** The link idiom pins the trace the
patient's course *followed*. The other six traces correspond to paths this
patient never took: 32 treats before classification (a critical fail with
perforation), 33 misclassifies IIa as IIc and leaves it untreated
(rebleeding), 34 is epinephrine monotherapy on a Forrest Ib lesion
(rebleeding), 35–36 are the Dieulafoy variant (clean and missed), 37 runs
the ongoing-hematemesis configuration and takes `err.unprotected-airway`
(aspiration) — the case's patient hematemesed at 6 h as an encounter event
but the case authors no airway error, and the trace's scenario represents a
different presentation state. Linking any of them would assert a course the
case does not contain. The role text in the link says so.

**Honest bounds (recorded in the link's own note).** Two case facts are
*not* carried by the trace and are not claimed as matched: the ulcer's
**18 mm** size (microstep m3.1 records site/size as acts, not values) and
the **two-clip** count (m5.3 is the clip modality). The debrief's
`physiology.blood_loss_ml` is 0.0 — an intra-procedure engine quantity; the
case's patient bled *before* the scope, and that quantity is deliberately
not matched (the case's blood loss lives in its physiology link, Milestone
61). The trace carries no patient identity (no age, no NSAID history):
correspondence is at lesion/site/classification/modality/process/outcome
level, exactly the level of the #2 and #8 links.

## 2. Field-by-field match — recomputed verdict: PASS

The checker re-reads `theatre/debriefs/debrief-31-endo-clean.json`,
recomputes its SHA-256, and matches each field below mechanically (the
digest is also pinned inside the case file and in
`management/theatre_link_verified`).

| Field | Debrief 31 (recomputed) | Case #9 claim |
|---|---|---|
| debrief SHA-256 | `e2906344e7e035c9c79b3dc9110965b674561f8fbba484866aea927a711bba8c` | pinned identically in `theatre_link` |
| verdict | PASS | adjudication: Forrest IIa, therapy delivered, no rebleed |
| failed_at_s | null | course completed |
| checklist | 27/27, missing [] | full gate-path act (identify → classify → pause → treat → confirm) |
| safety_gate | 4/4; criteria before first gated act = 3; pause before first gated act = true | gate `gate.identify-classify-before-therapy` met before therapy |
| process | 4/5 (prophylaxis_in_window false — the pathway's designed ceiling, no prophylaxis act) | no prophylaxis act in the case either |
| management | null (no rebleeding pathway scored) | no rebleed (stage 4) |
| errors | [] | no scored error in the endoscopic act |
| complications | [] | none |
| decision dp1 | `proceed-endoscopy` @ 540.0 s | endoscopy performed |
| decision dp3 | `forrest-iia` @ 1140.0 s | Forrest block: IIa (C66, Milestone 61) |
| engine_trace_hash | `0x40534c106d3f1427` | pinned in `theatre_link` |
| trace lesion (trace file) | `duodenal-ulcer:iia` | finding `endoscopy-ulcer`: posterior wall of duodenal bulb |
| therapy (case side) | m5.2 epinephrine → m5.3 clips, *"applied to the identified, classified lesion (declared forrest-iia)"*; m6.1 hemostasis confirmed | `management/endoscopic_therapy`: epinephrine + two clips; finding `endoscopy-hemostasis` |

**Verdict: PASS** — the loop's third form. Cases #2 and #8 link a case
*written after* its procedure (verdicts FAIL and PASS respectively);
case #9 was written *before* its procedure existed, and the procedure
Milestone 62 built for its lesion returns PASS on the course the case
authored. (The expert-review gate remains unmet, as everywhere: content
stays `dual-sourced-draft`, scores formative-only.)

## 3. The edits — confinement proof

Three asserted raw-text splices in the M60 manner
(`work/m64/edit_case9.py`), all inside the case's link/handoff blocks:

- **(A)** `theatre_link` inserted at case root (before `physiology_link`):
  debrief/trace file paths, the recomputed digest, procedure and trace
  ids, the lesion, the role, the matched fields of §2, and the note
  carrying the §1 bounds.
- **(B)** `management/theatre_note` replaced: the Milestone-61 absence
  record is preserved as history and the closure recorded after it, in
  the case-4 note-after-closure voice — *"THEATRE HANDOFF EXISTS — the
  absence recorded here at Milestone 61 is closed…"*.
- **(C)** `management/theatre_link_verified` inserted after the note: the
  verification prose in the #2/#8 idiom, carrying the digest.

**Proofs (both printed by the edit script and re-verified):** (1) *byte
confinement* — removing insertions (A) and (C) and restoring the old note
text reproduces the original file **byte-for-byte**; (2) *parsed semantic
diff* — exactly three paths differ: `case/theatre_link` (added),
`case/management/theatre_note` (changed), `case/management/
theatre_link_verified` (added). Findings, scores, stages, LRs, physiology
and imaging links, disposition: untouched. New file: 67,933 bytes,
sha256 `7f9400716327d0fffc344c0f1443f082d5f77055eb5a939387aa7947f95d17bd`
(was `37e9555a…`).

`tools/case_check.py`: the NO-HANDOFF assertion in `profile_case9` was
replaced by the slimmed management assertion (PPI, refused discharge
retained) plus an 11-assertion LINK block named above; profile header and
banner updated in prose only. `cases/README.md`: the case-9 entry's stale
*"No Theatre handoff exists…"* sentence now records the third-form link.
The case register was **not** extended (unlike case #8's C62 citation):
the link's ground is the shipped debrief and trace files themselves, so
`cases/parameters.json` and every register-extent assertion stand
untouched.

## 4. Checker census

- **case_check: 14,919 → 14,964 passed, 0 failed.** Delta +45, reconciled
  exactly: **+11** profile assertions (−1 NO-HANDOFF assertion removed,
  +1 slimmed management assertion, +11 LINK assertions — the digest check
  plus ten field/correspondence matches) and **+34** from the generic
  composite walk, which counts one assertion per dict key: the case
  file's key census rose 891 → 925, precisely the `theatre_link` block
  (21 keys) and its matched-fields content as authored.
- **theatre_check: 872/0, unmoved** — no trace added, no theatre file
  touched.
- **All 22 `tools/*_check.py` exit 0 except `readme_check.py` (exit 1)**,
  whose failure set is the pre-existing Milestone-62/63 set **plus exactly
  one new member**: `R9 case_check total == its printed output` (README
  prints 14,919; the true total is now 14,964). README.md was **not**
  touched, per instructions. (Writing this dossier moves the on-disk
  milestone count 63 → 64 inside the already-failing R10/R11 lines; the
  next README pass reconciles all of it.)
- **Non-regression:** cases #1–#8 and every case attempt/debrief are
  sha256-byte-identical to the pre-milestone census
  (`work/m64/census-cases-before.txt` vs `-after.txt`: the only changed
  line in the whole cases tree is case #9's own file). Theatre debriefs
  untouched (no theatre file in the batch).

## 5. Figures for the next README pass

- case_check total: **14,964** (case count stays 9; register stays
  C1–C70).
- Case #9's entry: Theatre handoff now exists — hash-link to trace 31,
  verdict PASS (third form: case first, procedure after).
- Milestone index: +1 row (Milestone 64); file index [milestones] +1,
  [cases] and [tools] counts unchanged in file number (contents changed).

## 6. Landing batch (4 files)

1. `cases/case.upper-gi-bleed.009.json` — the `theatre_link`, the closed
   `theatre_note`, `theatre_link_verified`.
2. `tools/case_check.py` — profile_case9 LINK block (11 assertions).
3. `cases/README.md` — case-9 entry: handoff recorded.
4. `milestones/MILESTONE-64.md` — this dossier.

Nothing else. No engine, theatre, physiology, imaging, atlas or data
file changed; no GitHub writes were made by this milestone — the parent
lands the batch.
