# Source: Z-Anatomy Tier B derived geometry — Milestone 63 intake

- **Origin:** derived in-project from the Z-Anatomy template
  (`Z-Anatomy/Models-of-human-anatomy`, `Startup.blend`, Blender 3.5
  format) as audited at Milestone 34 (see
  `milestones/MILESTONE-34.md` and the audit artifacts
  `milestones/MILESTONE-34-provenance.json` /
  `milestones/MILESTONE-34-clearance.json`).
- **Upstream archive SHA-256:**
  `e029688545627bd0214b269e1063143abb580aad72b2c2445d6d8a9a0d9da736`
  (the `.blend` itself is not redistributed here; the derived OBJ
  files under `obj/` are the landed source of record).
- **Scope:** 235 of the audit's 236 Tier B objects — provenance
  cleared on the audit's Bar 1 and placement validated on its
  Bar 2. One Tier B object, `Cochlear nerve.l`, is **excluded at
  intake**: its elimination origin cannot exclude the Dundee
  inner-ear source (CC BY-NC-SA named region), and the standing
  rule is that Bar-1 ambiguity is never resolved in intake's
  favour; the exclusion is recorded in `intake-manifest.json`
  and in the Milestone 63 dossier. No Tier C object (gated: no
  validated derivation exists) and no Tier D object (excluded
  permanently: provenance inseparable / CC BY-NC-SA
  contamination) is present.
- **Derivation:** `tools/zanatomy_extract_full.py` (full geometry
  extraction from the template) + `tools/zanatomy_intake.py`
  (placement + re-filing). Mesh objects carry their template
  datablock geometry; curve objects are rendered as tubes at the
  template's own bevel radius. All objects are placed into the
  BodyParts3D millimetre frame by the audit's brain-assembly
  similarity transform (scale 1030.957191; split-half held-out
  mean 0.274 mm), re-derived and re-verified bit-identically at
  Milestone 63.
- **Per-object record:** `intake-manifest.json` carries, for every
  object, its provenance chain exactly as the audit established
  it, its measured vertex/face counts and bounding box, its
  SHA-256, and whether it is attached to a Body Model record
  (19 of the 236 attach; the rest are held as derived assets).

## License position

- Z-Anatomy as a whole distribution is **not** a product source:
  parts of it are CC BY-NC-SA, and those parts are excluded. The
  Tier B objects' eligibility rests solely on the Milestone 34
  Bar-1 finding recorded per object in the manifest (BodyParts3D-
  derived by elimination, or Z-Anatomy-original under the
  distribution's headline license).
- License carried for these derived files: **CC BY-SA 4.0** (the
  Z-Anatomy distribution's headline license, upstream
  `License.txt`); share-alike applies. The Dundee "Cranial Nerves
  and Foramina" inclusion (CC BY 4.0) cannot be isolated
  object-by-object from Z-Anatomy's own curve work and is
  attributed alongside the cranial-nerve curves in the manifest,
  exactly as the audit recorded it.
