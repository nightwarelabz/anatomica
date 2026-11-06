# Milestone 23 — The TA2 Name Pass

**Date:** 2026-11-06 · **Status:** complete, local only (no upload performed; the batch is listed at the end for per-item approval)

## What this milestone retires

Since Milestone 4, essentially every clinical record in the body
model carried `ta_name: null` with a verify flag: the Latin names
of Terminologia Anatomica 2 (TA2) had never been consulted, and
the precision law forbids entering a Latin name from recall. This
milestone consults the actual TA2 source, resolves every clinical
record it supports, and re-flags the rest with dated, specific
reasons. **340 of 361 records (94.2%) now carry a TA2 Latin name
with its TA2 id; 9 are flagged ambiguous and 12 not found, each
with its reason recorded on the record itself.**

Scope note: the pass covers exactly the **361 clinical records**
in the ten system tranches. The skeletal tranche's 206 bones are
inventory-level records and carry no `ta_name` field; they are out
of scope for this pass and `skeletal_check.py` is unchanged.

## Provenance — the source consulted

- **Source:** FIPAT. *Terminologia Anatomica.* 2nd ed. 2019
  (approved and adopted by the IFAA General Assembly, 2020),
  **TA version 2.07** (errata v2.07, 16 August 2021). Consulted
  2026-11-06.
- **Route:** the publication's own PDF route at
  `FIPAT.library.dal.ca/TA2/` **failed** through the available
  fetch tooling in this session (no HTTP status returned) and was
  not retried through another route; the PDFs were not downloaded.
  The pass instead consulted **TA2Viewer**
  (ta2viewer.openanatomy.org) — the official digital version of
  the same publication (a joint project of the IFAA and the Open
  Anatomy Project; its front page states "TA version 2.07" and
  names FIPAT as publisher; Halle, Kikinis & Neumann, *Clin Anat*
  37:640–648, 2024). The viewer serves the complete terminology as
  one JSON payload embedded in its main JavaScript bundle;
  `tools/ta2_extract.py` parses that payload into the vendored
  table `data/sources/ta2-2.07/ta2-terms.json` (SHA-256
  `b8fe4726…`, bundle hashes pinned in
  `data/sources/ta2-2.07/SOURCE.md`). No source substitution was
  taken silently: this is the same official publication in its
  database form, and the failed route is recorded in SOURCE.md.
  Not used: the viewer's Wikidata label bundle (unofficial
  synonyms) and Z-Anatomy's TA2.csv (third-party derivative with
  documented label errors).
- **License, as stated by FIPAT:** the publication is CC BY-ND
  4.0; **the individual terms are in the public domain**. This
  project stores and cites individual terms only, with FIPAT's
  bibliographic citation.
- **Integrity observations (recorded, not corrected):** the
  served 2.07 data holds exactly 7,112 term objects, ids spanning
  1–7113 — the published figures. Exactly one id is unassigned:
  **2259**; id 2590 *is* assigned (*vinculum breve tendinis*),
  contradicting secondary sources that name 2590 as the gap. The
  pass cites ids as served. All 7,112 terms carry Latin; 315
  carry no English. The viewer term objects carry **no FMA ids**
  (its FMA links are external, via Wikidata), so record identity
  was corroborated by record type, the records' own FMA class
  names in the inventory files, and the TA2 chapter — never by a
  viewer-supplied FMA link.
- One served string carries trailing whitespace — TA2 4366
  `"carotis communis "`; the entered value is trimmed and the
  anomaly is logged in `data/ta2-name-pass.json`.

## Method and the resolution rule

Candidates were generated mechanically (`tools/ta2_match.py`:
exact preferred-term, listed-synonym, listed related-term, and
class-word-stripped matches against TA2's Latin and English,
with diacritic and ae/oe/e folding applied to match keys only —
entered values are always TA2's exact strings). Every candidate
set was then curated (`tools/ta2_decide.py`, whose decision
record is kept at `work/ta2/decisions.json`) under one rule:

> A record resolves to a TA2 term only when TA2's own naming
> apparatus (preferred term, listed synonym, or listed related
> term) names that term for a structure **identical** to the
> record's — identity corroborated by the record's type, its FMA
> class names, and the TA2 chapter — and no other TA2 term
> denotes the record with an equal claim. Anything else is
> ambiguous (candidates listed) or not found (probe evidence
> recorded).

Resolution bases across the 340: preferred term 289, listed
synonym 38, class-word form 4, plural collective term 3, listed
related term 2, Latin synonym 2, Latin-only term 2. Notable
judgements, all recorded in the decision file: TA2's plural
collectives (*arteriae pulmonales* 4074, *venae pulmonales*
4107, *venae hepaticae* 4994) resolve the corresponding unsided
records; the brachiocephalic trunk resolves to 4179 *truncus
brachiocephalicus* via its listed related term; the eight
Couinaud liver segments and the eighteen bronchopulmonary
segments resolve via TA2's own listed synonyms ("segment N of
liver", "segment N of right/left lung"); the served TA2
respiratory tree ends at 3282 *bronchiolus*, which is why the
distal-airway records below are not found rather than
approximated.

Application is by `tools/ta2_pass.py` (idempotent; re-running it
reproduces the same bytes). A structural diff against the
pre-pass files confirms the pass touched **only** `ta_name`,
`ta_code`, `sources["ta_name"]`, ta_name verify entries, and the
meta source register / `ta_name_status` / `ta2_pass` blocks —
nothing else in any tranche changed. Caveat: the per-tranche
`build_*_records.py` builders predate the pass and would clobber
it if re-run; `ta2_pass.py` is the applying tool of record.

## Coverage

| System | Records | Resolved | Ambiguous | Not found |
|---|---:|---:|---:|---:|
| Cardiovascular | 69 | 68 | 1 | 0 |
| Digestive | 31 | 28 | 3 | 0 |
| Endocrine | 6 | 6 | 0 | 0 |
| Integumentary | 13 | 10 | 1 | 2 |
| Lymphatic | 4 | 2 | 1 | 1 |
| Muscular | 127 | 126 | 1 | 0 |
| Nervous | 52 | 51 | 1 | 0 |
| Reproductive | 16 | 14 | 0 | 2 |
| Respiratory | 37 | 31 | 1 | 5 |
| Urinary | 6 | 4 | 0 | 2 |
| **Total** | **361** | **340** | **9** | **12** |

**Ambiguous (9)** — full candidate lists and reasons in
`data/ta2-name-pass.json`; each record's verify entry carries the
same reason, dated 2026-11-06:
renal vein (TA2 lists only the sided pair 5000/5006 — no unpaired
term); cecum-and-appendix (compound record; 2970 *caecum*, 2976
*appendix vermiformis*); biliary tree (parts only, no whole-tree
term); dentition (TA2 repeats *dentes* in two chapters, 901 and
2818, and has no "dentition" term); mammary gland and breast
(compound: 7097 *mamma*, 7099 *glandula mammaria*); lymph nodes
and lymphoid tissue (5191 denotes nodes only); posterior
cervical intertransversarii set (TA2 splits it: 2238 laterales,
2297 mediales); basal ganglia (TA2 names "basal ganglia" only as
a *related term* of 5559 *corpus striatum*, a different
structure); pleurae and pleural cavities (compound: 3322
*pleura*, 3316 *cavitas pleuralis*).

**Not found (12)** — probe tokens recorded per record in the
decision file and artifact: generic hair and hair of trunk (TA2
names hairs regionally only; no *pilus* term); lymphatic
drainage, male reproductive, female reproductive, and urinary
pathways (project pathway constructs, not structures); segmental
bronchi as a class (TA2 names twenty individually, no class
term); respiratory bronchioles, alveolar ducts and sacs, alveoli
(the served respiratory tree ends at *bronchiolus*; TA2's
"alveoli" are dental); respiratory mechanics (measurements, not
a structure); nephron (the string occurs in no TA2 term, synonym,
or related term).

## Checker changes

- **New: `tools/ta2_discipline.py`** — independent assertions
  re-derived from the shipped data, the vendored TA2 table, and
  `data/ta2-name-pass.json` (never from the pass's working
  files): a non-null `ta_name` must equal the table's Latin for
  its integer `ta_code`, cite TA2, and carry no ta_name flag; a
  null `ta_name` must carry no `ta_code` and exactly one dated
  TA2 verify entry stating ambiguous or not found; counts,
  record sets, and codes must reconcile with the artifact; the
  meta must carry the TA2 register entry and a matching
  `ta2_pass` block.
- **All ten tranche checkers** now invoke that discipline
  (cardiovascular, digestive, endocrine, integumentary,
  lymphatic, muscular, nervous, reproductive, respiratory,
  urinary). Their own legacy assertions of the old discipline —
  "ta_name must be null + flagged", exact record key sets, exact
  S-key source registers — were updated in place to the M23 rule
  (entered name ⇒ TA2 citation + `ta_code`; register ⇒ S-keys +
  TA2; key sets ⇒ `ta_code` admitted). The muscular tranche keeps
  its scalar source-key convention (`"TA2"`, not `["TA2"]`).
- `skeletal_check.py` unchanged (no clinical records, no
  `ta_name` fields).

## Verification matrix (all run 2026-11-06, after the pass)

| Check | Result |
|---|---|
| cv_check / dig_check / endo_check / integ_check / lymph_check | PASS |
| muscle_check / nerve_check / repro_check / resp_check / uri_check | PASS |
| skeletal_check | PASS |
| assembly_check_all | PASS — ALL GATED CHECKS PASS |
| verify_web (node) | PASS — ALL CHECKS PASS |
| case_check | PASS — 3,280 passed, 0 failed |

Independent content census (not via the pass tooling): 361
records; 340 with `ta_name` + `ta_code` + TA2 citation; 21 dated
M23 verify entries; **zero** old-wording ta_name flags remain.

## What remains flagged, and why

The 21 records above stay `ta_name: null` — deliberately. Each is
either a compound or project-level construct TA2 does not name
as one term, a sided-pair asymmetry in TA2 itself, or a
structure the served TA2 2.07 does not reach (distal airways,
nephron). Resolving any of them requires either splitting the
record (a modelling decision) or a future TA2 errata version —
not a coined Latin name. The flags on the records state which,
with candidates or probe evidence.

## Batch contents (for per-item upload approval)

- Data: the 10 tranche files above; `data/ta2-name-pass.json`;
  `data/sources/ta2-2.07/SOURCE.md` + `ta2-terms.json`.
- Tools: `ta2_extract.py`, `ta2_match.py`, `ta2_decide.py`,
  `ta2_pass.py`, `ta2_discipline.py`; the 10 updated tranche
  checkers.
- This report. Working files (`work/ta2/`: bundles, worksheet,
  decisions, pre-pass backups) stay local.
