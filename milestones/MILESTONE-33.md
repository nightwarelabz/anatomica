# Milestone 33 — The nervous-system gap: source evaluation and FMA concept intake

Status: built and checked locally. Not uploaded; presented for
approval as a unit, as with Milestones 2–32.

Milestone 9 closed with the Body Model's largest single blocker:
the peripheral nervous system is essentially absent from
BodyParts3D 4.0 (55 nerve-named concepts, all cranial II/III/IV/V1;
eight cranial nerves, every spinal nerve, every plexus and every
named limb nerve absent — 116 of 126 probes at zero hits). This
milestone evaluates candidate sources against the project's two
bars — **license** (redistributable inside AGPL-3.0 product data)
and **content** (geometry, concepts, or both, derivable without
hand-placement) — and intakes what clears both.

**Outcome in one paragraph:** one source clears the license bar
with concept content — the Foundational Model of Anatomy (FMA)
5.1.0, whose official release package now ships CC BY 4.0 as its
license instrument. **286 FMA concept records** are intaken into
the nervous inventory (133 → 419 records; Body Model inventory
1,552 → 1,838), every one marked geometry-absent with verify
flags, because the FMA is an ontology and carries no geometry.
**No geometry source clears both bars this milestone**; the one
candidate with real peripheral-nerve geometry (Z-Anatomy) fails on
per-object provenance separability and the absence of a recorded
registration transform — the exact unblock conditions are named
in §3. Nothing was invented, drawn, or hand-placed.

## 1. Candidate evaluation

### (a) Foundational Model of Anatomy (FMA) — University of Washington

- **Availability route:** official UW distribution directory
  http://sig.biostr.washington.edu/share/downloads/fma/release/5.1.0/
  (named as the latest release by the UW "Summary of FMA Resources"
  page, http://si.washington.edu/projects/fma); also mirrored via
  NCBO BioPortal (https://bioportal.bioontology.org/ontologies/FMA)
  and GitHub. Release 5.1.0 (2019), 104,720 classes. Intaken files
  are hash-pinned in `data/sources/fma-5.1.0/` (ledger + SOURCE.md).
- **License evidence:** the release package ships a file named
  `LICENSE` (18,650 bytes, SHA-256 `7e7170e3…`) that is the full
  text of **Creative Commons Attribution 4.0 International**. Its
  operative grant (Section 2(a)(1)) gives a "worldwide,
  royalty-free, non-sublicensable, non-exclusive, irrevocable
  license" to "reproduce and Share the Licensed Material, in whole
  or in part" and to "produce, reproduce, and Share Adapted
  Material", conditioned only on attribution (Section 3(a)).
  **Recorded tension, not hidden:** BioPortal's FMA record shows an
  empty License field and notes that "The FMA is an intellectual
  property of the University of Washington"; the UW project page
  calls the FMA "open source" without naming a license. The
  project's position (recorded in the source entry): the license
  file inside the rights holder's own release package is the
  governing instrument for that release; UW ownership is undisputed
  and attribution is carried on every derived artifact.
- **License verdict: YES** — CC BY 4.0 data is redistributable in
  AGPL-3.0 product data (attribution-only; no NC, no SA condition
  on the data).
- **Content verdict: CONCEPTS ONLY.** The FMA is an ontology —
  preferred names, FMAIDs, synonyms, IS-A and part relations. It
  contains **no meshes, coordinates, or images of any kind**. What
  it lawfully gives is exactly what Milestone 9's next-steps named:
  the authoritative concept inventory in the same FMAID space the
  BodyParts3D tables already use. (Its TA_ID annotation axioms are
  TA-1998-era and were **not** adopted; the project's standard is
  TA2 via the Milestone 23 pipeline.)
- **Integration cost:** one streaming parse of `fma.owl`, a frozen
  target list resolved mechanically, an idempotent merge — done
  here as `tools/fma_nerve_map.py` + independent
  `tools/fma_nerve_check.py`.

### (b) Open Anatomy / SPL atlases (Brigham & Women's / 3D Slicer ecosystem)

- **License evidence:** the Open Anatomy Browser paper (Halle et
  al., *Frontiers in Neuroinformatics* 2017;
  https://pmc.ncbi.nlm.nih.gov/articles/PMC5366788/) states: "Our
  code, data and tools are licensed under the 3D Slicer open source
  license, which allows for liberal use, reuse, and redistribution
  for any purpose, including commercial applications."
- **License verdict: YES** (BSD-style, permissive).
- **Content verdict: DOES NOT ADDRESS THE GAP.** The published
  SPL atlases are the SPL/NAC **brain** atlas and CT-derived
  atlases of the head & neck, knee, and abdomen. There is no
  peripheral-nerve or whole-body nerve atlas in the set, and the
  brain is the one neural structure the Body Model already has
  from BodyParts3D. Nothing to intake for this gap.

### (c) Z-Anatomy (per-object route, OD-03.2)

- **Content — the geometry exists.** A census of the in-tree
  reference export (`data/sources/z-anatomy-glb/nervous.glb`,
  reference-only per its standing restriction) counts 580 named
  nodes, including the missing anatomy: cranial nerves I–XII as
  sided objects, sympathetic trunk and its ganglia, spinal roots
  and ganglia, musculocutaneous and the other limb nerves.
- **License position:** upstream (https://github.com/Z-Anatomy/
  Models-of-human-anatomy) states "All the code and content shared
  by 'Z-Anatomy' is under Creative Commons Attribution-ShareAlike
  4.0" and lists its included models individually — of which
  exactly two are non-commercial ("Anatomy of the Inner Ear",
  CC BY-NC-SA 4.0; "Kidney", CC BY-NC 4.0; neither is a nervous
  structure) and one nervous-adjacent item is permissive ("Cranial
  Nerves and Foramina", University of Dundee CAHID, CC BY 4.0).
  The distributor's merged export held in-tree states the work *as
  distributed* is CC BY-NC-SA, which is why it remains
  reference-only.
- **Verdict: DOES NOT CLEAR THIS MILESTONE — on evidence, not on
  headline license.** CC BY-SA 4.0 geometry would be acceptable in
  principle (the project already ships share-alike-attributed
  BodyParts3D mesh data). Two bars are unmet:
  1. **Per-object provenance is not separable from the artefact as
     published.** The models ship as one Blender template; objects
     are of mixed origin (BodyParts3D-derived, Z-Anatomy-original,
     Dundee CC BY) and the template carries no per-object license
     or provenance field. Adopting the nervous objects requires an
     extraction audit that establishes, object by object, that no
     NC-encumbered or misattributed object is among them — the
     standing OD-03.2 requirement of per-object clearance.
  2. **No recorded registration transform exists** from
     Z-Anatomy's Blender scene to the Anatomography canonical
     frame the shells are built in. The precision law admits
     geometry only as a derivation from source data with recorded
     transforms; a fitted-by-eye placement is hand-modelling by
     another name.
- **Exact unblock condition:** (i) a per-object extraction and
  provenance audit of the nervous-system objects from the upstream
  template, recorded in a provenance ledger like every other
  source; and (ii) a registration derivation against structures
  shared with BodyParts3D (the model's BP3D-derived base) with
  measured residuals, gated by the assembly checker like the
  Milestone 3 registration. Both are ordinary engineering tasks;
  neither was shortcut here.

### (d) Other candidates, evaluated and closed

- **Human Reference Atlas (HuBMAP HRA)** — 3D reference organ
  library, CC BY 4.0 (licence statement at https://humanatlas.io/,
  corroborated by downstream notices). License clears; content is
  organ-level reference models for cell-type mapping — **it
  publishes no peripheral-nerve models**. Nothing for this gap.
- **BodyParts3D later data versions (4.3i / "5.0")** — DBCLS's own
  pages (https://lifesciencedb.jp/bp3d/info_en/index.html) record
  that peripheral nerves were "under inspection" for a version 5.0
  in 2014; the LSDB archive's downloadable release remains **4.0**
  (page updated 2025-02-27), and the 4.3 line is a full-resolution
  re-issue of the same concept set served through the Anatomography
  viewer (with per-version coordinate differences), not new nerve
  concepts. No intake route exists through the official archive.
- **Commercial / NC model libraries** (Sketchfab-class listings,
  AnatomyWarehouse-style storefronts, Soma3D) — terms are
  per-item commercial licenses or CC BY-NC-SA
  (https://www.soma3d.nl/legal.html is representative). The NC and
  no-redistribution terms fail the license bar on their face;
  nothing was intaken or relied on.

### Verdict table

| Candidate | License | Content for the gap | Verdict |
|---|---|---|---|
| FMA 5.1.0 (UW) | CC BY 4.0 (in-package LICENSE) | Concepts + relations, **no geometry** | **INTAKEN (concepts)** |
| SPL / Open Anatomy | 3D Slicer license (permissive) | Brain + regional atlases; no peripheral nerves | Clears license, no content |
| Z-Anatomy (upstream) | CC BY-SA 4.0 headline; mixed per-object origins | Full peripheral geometry exists | **Blocked**: per-object audit + registration derivation (OD-03.2) |
| HRA (HuBMAP) | CC BY 4.0 | Organs only; no nerve models | Clears license, no content |
| BP3D 4.3 / 5.0 | CC BY 4.0 / BY-SA 2.1 JP | Same concept set / never released | No route |
| Commercial / NC libraries | NC or paid per-item | — | Fails license bar |

## 2. The intake — 286 concept records

`tools/fma_nerve_map.py` resolves a frozen target list (173
targets — Milestone 9's absent structures and their named parts)
against `fma.owl`: lateralised records where the FMA carries both
sided classes, otherwise one un-sided record — the Milestone 9
counting convention. Any candidate whose FMAID already appears in
the BodyParts3D inventory is excluded mechanically (exactly one
target hit this: the ophthalmic nerve, whose sided classes BP3D
already records). Every target resolved; none was dropped
silently.

| Group (disjoint, by record) | Records |
|---|---|
| Spinal nerves, all levels (C1–C8, T1–T12, L1–L5, S1–S5, Co) | 62 |
| Intercostal nerves T1–T11 + subcostal | 24 |
| Cranial apparatus (I, III trunk, V trunk + divisions + ganglion, VI–XII) | 26 |
| Somatic plexuses + brachial architecture (trunks, divisions, cords) | 24 |
| Named peripheral nerves (median → plantar set) | 79 |
| Autonomic (trunk, ganglia, splanchnics, plexuses) | 53 |
| Spinal cord parts (conus, cauda equina, filum, enlargements, denticulate ligament) | 6 |
| Meninges (pia, arachnoid, cranial/spinal dura, falces, diaphragma sellae) | 7 |
| Spinal nerve architecture (roots, ganglion, rami — generic classes) | 5 |
| **Total (228 lateralised + 58 un-sided)** | **286** |

(By subtree, as the checker counts them: peripheral 220,
autonomic 53, meningeal 7, central 6.)

Every record carries: its FMAID(s), the FMA preferred name
verbatim, its IS-A group path in the FMA tree (all 286 paths reach
the "Anatomical entity" root — the FMA's IS-A tree does not pass
through "Nervous system", which hangs off the part hierarchy; the
paths record the tree as it is), `source: "fma-5.1.0"`,
`geometry: "absent"`, and two verify flags (geometry absent —
ontology source; no clinical tranche authored). Records appear in
`records.json` in the shells list marked `has_geometry: false`
with the reason stated, exactly as the 7 geometry-less bones have
been listed since Milestone 16.

**What did not change:** the 133 BodyParts3D records are
byte-identical in parsed form (checker-asserted); all 11 geometry
packs are **byte-identical** (SHA-256 compared before/after); the
compressed delivery total is unchanged (123,352,401 B); the W6
pick roundtrip still covers exactly **1,545** geometry slots; the
52-record clinical tranche is untouched.

**Census deltas:** nervous inventory 133 → **419**; Body Model
inventory 1,552 → **1,838**; records with geometry 1,545 (nervous
133/419); shells listed records 1,630 → **1,916**.

## 3. Checker matrix — all green

| Suite | Result |
|---|---|
| `tools/fma_nerve_check.py` (new; XML re-parse, independent of the builder) | **ALL CHECKS PASS** — license + zip hashes pin to the ledger; all 286 records' FMAID/name/side/class fidelity vs the OWL; zero FMAID overlap with the BP3D inventory; zero extension names present in the BP3D parts lists; geometry correspondence 1:1, all mesh-less |
| `tools/nerve_check.py` (P2 scoped to the BP3D partition, Milestone 33 note in-file; P1 still spans both sources) | **ALL HARD CHECKS PASS** (24+ checks; C7/C8 reports now read over 419 inventory records) |
| `tools/assembly_check_all.py` (census anchor updated: nervous 419/133/52) | **ALL GATED CHECKS PASS** |
| `tools/pack_geometry.py` (+ `--compress`) | packs byte-identical; records.json 1,916 listed |
| `node tools/verify_web.js` (W1 expected counts now derived from each system's geometry-file record set) | **ALL CHECKS PASS** incl. W6 1,545 slots, W9 byte-identity |
| native `cargo run --release -- verify` | **99/99 data assertions PASS** (GPU render stage cannot initialise on this VM — no adapter; standing limitation, disclosed at Milestones 28/29; no native files changed) |
| `tools/theatre_check.py` | 245 checks, 0 failures |
| `tools/case_check.py` | 5,145 passed, 0 failed |
| physiology `cargo run --release -- validate` | **ALL HARD GATES PASS** |

Two defects were caught and fixed during the build, both in this
milestone's own tooling (a group-path root that the FMA's IS-A
tree does not contain, and a case-sensitivity bug in the first
checker draft) — the independent checker earned its keep; the
shipped data was re-derived after each fix.

## 4. Honest limits

- **The gap is now named, not filled.** Every absent nerve exists
  as a sourced concept record; none has geometry, a clinical
  tranche, or a TA2 name yet. A Theatre procedure still cannot
  stage against peripheral-nerve geometry.
- **FMA-internal absences, recorded:** the rami communicantes have
  no generic classes in the FMA (only set classes and specific
  instances from the superior cervical ganglion) — no record was
  taken for them; spinal cord *segments* exist only as a generic
  class, excluded under the Milestone 9 convention (segment
  classes are not records); roots/ganglion/rami are recorded as
  the generic classes the FMA releases, with that fact on each
  record.
- **Name-form note:** one record's FMA preferred name
  ("Posterior cutaneous nerve", FMA77561) is the FMA's name for
  the posterior femoral cutaneous nerve; the correspondence is
  recorded on the record rather than the name being edited.
- **C3 continuity, updated:** the muscle module's 45 innervation
  names still resolve to 11 sourced clinical records and 2
  inventory records by the nerve checker's curated matching; the
  underlying concepts for the named nerves now exist as inventory
  records, but re-pointing the clinical links is a separate,
  deliberate edit to Milestone 9's recorded-absence semantics —
  not done silently here.
- The FMA license position rests on the in-package LICENSE file;
  if UW ever republishes 5.1.0 with different terms, the ledger
  pin will catch the change on any re-download (hash mismatch =
  new release, per project convention).

## 5. Next steps / decisions

1. **Geometry remains the open decision (for Chase):** the
   Z-Anatomy route unblocks on (i) a per-object provenance audit
   of its nervous-system objects and (ii) a registration
   derivation with measured residuals (§1c). That is the named
   milestone whenever it is called; no other evaluated source
   offers lawful peripheral geometry.
2. Follow-ons now unblocked locally: a TA2 pass over the 286
   records (Milestone 23 tooling), and a sourced clinical tranche
   for the major nerves (the records exist to be linked).
3. The same FMA intake pattern is available for the other
   text-thin systems (lymphatics, thyroid/parathyroids, urinary
   interior, female tract) whenever those milestones are called —
   the license question that blocked them is answered by §1a.

## Batch for the per-item upload tap

New: `MILESTONE-33.md`, `tools/fma_nerve_map.py`,
`tools/fma_nerve_check.py`, `data/sources/fma-5.1.0/` (SOURCE.md,
ledger.json, ledger-summary.md, LICENSE, README.md, Version.txt,
ChangeLog.txt, fma.zip). Changed: `data/nervous/
nervous-inventory.json`, `data/nervous/nervous-geometry.json`,
`data/nervous/nervous-assembled.json` (meta only —
`records_without_geometry` now lists the extension),
`tools/nerve_check.py` (P2 partition scope),
`tools/assembly_check_all.py` (census anchor),
`tools/pack_geometry.py` (nervous geometry-absent listing),
`tools/verify_web.js` (W1 derivation), `web/data/records.json`
(regenerated; packs and delivery.json byte-identical).
