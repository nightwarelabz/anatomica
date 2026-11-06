# Source: Terminologia Anatomica, 2nd edition (TA2) — FIPAT

- **Bibliographic reference (FIPAT's own citation form):** FIPAT.
  *Terminologia Anatomica.* 2nd ed. FIPAT.library.dal.ca. Federative
  International Programme for Anatomical Terminology, 2019. Approved
  and adopted by the IFAA General Assembly, 2020.
- **Version consulted:** TA version **2.07** (the current errata
  version; errata v2.07 dated 16 August 2021). The version string is
  carried in the consulted data itself (viewer metadata payload:
  `vocab: "2.07"`, `vocabId: 20703`, `dataFormat: "1.1"`).
- **Retrieved:** 2026-11-06.

## Route actually used — and the route that failed

TA2 is published by FIPAT in two forms: unaltered PDF files at
`FIPAT.library.dal.ca/TA2/`, and an online searchable database. In
this session the Dalhousie TA2 page fetch **failed** through the
available browser tooling (upstream fetch error, no HTTP status
returned), and the failed request was not retried through another
route. The PDFs were therefore **not** downloaded.

The pass instead consulted **TA2Viewer**
(`https://ta2viewer.openanatomy.org/`), the online database form of
the same official publication: a joint project of the IFAA and the
Open Anatomy Project (Brigham and Women's Hospital), which
"incorporates the official digital version of the second edition of
*Terminologia Anatomica* (TA2) as published by FIPAT" (Halle,
Kikinis & Neumann, *Clin Anat* 37:640–648, 2024; the viewer's own
front page states "TA version 2.07" and names FIPAT as publisher).
The viewer serves the complete terminology as one JSON payload
embedded in its main JavaScript bundle; `tools/ta2_extract.py`
unescapes and parses that payload. The bundle itself is third-party
application code and is **not** vendored here — only the terminology
terms are extracted. Bundle files as downloaded (kept locally under
`work/ta2/`, hashes pinned here for reproducibility):

| File | Bytes | SHA-256 |
|---|---|---|
| viewer index.html | 3,397 | `1f168b0615778fd10cf4011df5c560cbc284165dc689744eac0998742dae6ccc` |
| static/js/main.0f36751c.chunk.js | 1,668,673 | `978835a2f698efc11653a2d20f10c934ca73bf938abba69913e7785e488b52c7` |
| asset-manifest.json | — | `6e4784a51c5c01bdeebfbea30c731d8d8446ea15760f6c33e2ca9ed86e54df92` |

Extracted payload (terms array, as parsed): SHA-256
`68203c7a52a7a66ef650655187d85172212f13ab8fcf87249b17c9f806b20b33`.
Derived table in this directory (`ta2-terms.json`): SHA-256
`b8fe4726456d7a231de97493efed766426f6bb8d9d6b3ecbd00d49780062601d`.

**Integrity observations.** The extracted table holds exactly
**7,112 term objects with ids spanning 1–7113** — the published TA2
term count. Exactly one id in 1–7113 is unassigned in the served
2.07 data: **2259**; id 2590 *is* assigned (to *vinculum breve
tendinis*). Secondary sources (Wikipedia; the TA2019 outline site)
state that 2590 is the unassigned id. The discrepancy is recorded
here, not corrected away: the pass cites ids **as served by the
consulted source**. All 7,112 terms carry a Latin term; 315 carry
no English equivalent in the served data.

**Not used:** TA2Viewer's lazily loaded third bundle (Wikidata
multilingual labels) — explicitly unofficial synonyms, excluded.
Z-Anatomy's `TA2.csv` — a third-party derivative with documented
label errors; not the consulted source.

## License

As stated by FIPAT on the TA2 publication page (read in this
session): "The publication of Terminologia Anatomica is under a
Creative Commons Attribution-NoDerivatives 4.0 International
(CC BY-ND 4.0) license. **The individual terms in this terminology
are within the public domain.** Statements about terms being part
of this international standard terminology should use the above
bibliographic reference to cite this terminology. The unaltered PDF
files of this terminology may be freely copied and distributed by
users."

This project stores and cites **individual terms** (id, Latin term,
English equivalent, synonyms) — public domain per FIPAT's statement
— with the bibliographic citation above. The publication as a whole
is not reproduced.

## Contents of this directory

| Entry | What it is |
|---|---|
| `SOURCE.md` | this file |
| `ta2-terms.json` | the extracted TA2 2.07 term table (7,112 terms), derived by `tools/ta2_extract.py` from the TA2Viewer bundle |
