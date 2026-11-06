# Source: Foundational Model of Anatomy (FMA) 5.1.0 — Structural Informatics Group, University of Washington

- **Origin:** Official UW distribution directory,
  http://sig.biostr.washington.edu/share/downloads/fma/release/5.1.0/
  (the "Summary of FMA Resources" page at si.washington.edu names this as
  the latest release, version 5.1.0; the same release is mirrored on
  GitHub and via NCBO BioPortal, ontology IRI
  http://purl.org/sig/ont/fma.owl).
- **Retrieved:** 2026-11-06, direct HTTP download of the published
  release files (`fma.zip`, `LICENSE`, `README.md`, `Version.txt`,
  `ChangeLog.txt`). `fma.zip` contains `fma.owl` (208,047,132 bytes
  uncompressed) plus `docs/` and `puns/`; the extracted working copy
  lives under `work/fma/` (sources in `data/sources/` stay
  byte-identical, per project convention).

## Files and SHA-256 (computed at intake)

UW does not publish checksums for these files (checked the release
directory listing and README on 2026-11-06 — no checksum listing
exists). The hashes below are therefore the project's own intake
pins, recorded in the provenance ledger (`ledger.json`); any future
re-download must match them or be treated as a new release.

| File | Bytes | SHA-256 |
|---|---|---|
| fma.zip | 11,378,823 | `80fd652c33850c7f52448e12793347544d32fa4f820facca3b39a67c7f99cf1a` |
| LICENSE | 18,650 | `7e7170e3cebf88a9f60c7b8421418323c09304da1af4d5e90f4da1dc1c8a2661` |
| README.md | 1,299 | `88b49b04bea3b4f4f9f41fff3fb63fb9861d615bac5a1ab63b731af0ffbb985a` |
| Version.txt | 6 | `c0eacacd7e27bbf341d21e7e0e2997a363840a210d8e358d4babaebd765b5bfd` |
| ChangeLog.txt | 274 | `a352ab54525bf6528d85696f133fb7b0f3d29c49f9574828382b004b01c563de` |

## License position

- **The release package ships a `LICENSE` file that is the full text
  of Creative Commons Attribution 4.0 International (CC BY 4.0)** —
  first line "Attribution 4.0 International", operative grant at
  Section 2(a)(1): the licensor grants a "worldwide, royalty-free,
  non-sublicensable, non-exclusive, irrevocable license" to
  "reproduce and Share the Licensed Material, in whole or in part"
  and to "produce, reproduce, and Share Adapted Material", subject
  only to the attribution conditions of Section 3(a). The verbatim
  license text is held in-tree as `LICENSE` (hash above) and is the
  operative evidence.
- **Recorded tension, not hidden:** NCBO BioPortal's FMA record
  (https://bioportal.bioontology.org/ontologies/FMA) shows an *empty*
  License field and a Notes statement that "The FMA is an
  intellectual property of the University of Washington", and the
  UW project page (http://si.washington.edu/projects/fma) describes
  the FMA as "open source" without naming a license. The project's
  position: the license file inside the official release package,
  distributed by the rights holder from its own server alongside the
  data, is the governing instrument for that release; the BioPortal
  metadata gap is recorded here so a future re-pin can re-check both.
  Ownership by UW is not in dispute — CC BY 4.0 is a license from
  that owner, and attribution is given wherever FMA-derived data is
  distributed: "Foundational Model of Anatomy (FMA), © University of
  Washington, CC BY 4.0".
- CC BY 4.0 data is redistributable inside AGPL-3.0 product data
  (attribution-only condition; no share-alike, no non-commercial
  restriction). This matches the TA2 precedent (public-domain terms)
  in kind: a permissive instrument with an attribution duty.

## Content position

The FMA is an **ontology**: 104,720 classes in this release with
preferred names, FMAIDs, synonyms, IS-A (subClassOf) and part
relations. **It carries no geometry of any kind** — no meshes,
coordinates, or images. What it lawfully gives ANATOMICA is concept
inventory and nomenclature: the authoritative concept set (with
stable FMAIDs — the same identifier space BodyParts3D's tables
already use) for structures BP3D 4.0 does not contain, recorded as
concept records with geometry explicitly absent (Milestone 33).
FMA also carries TA_ID annotation axioms; these are TA (1998)-era
identifiers, **not adopted** — the project's terminology standard is
TA2 via the Milestone 23 pipeline, which can process these records
later on its own evidence.
