# 03 — Geometry Pipeline

## Purpose

Turn adopted, license-clean segmented anatomy into the geometry registry both
shells render — with per-file provenance as a build gate, and registration onto
Body Model records so a mesh is never just a shape: it is a named structure.

## Sources (adopted, in-tree under `data/sources/`)

| Source | Release | License position | Role |
|---|---|---|---|
| BodyParts3D (DBCLS) | 4.0, IS-A + PART-OF OBJ sets (99% polygon reduction) | CC BY 4.0 per the current DBCLS license page (2025-02-27); legacy OBJ headers may read CC BY-SA 2.1 JP — recorded per file | Primary full-body geometry |
| TotalSegmentator dataset | pinned at adoption | Data CC BY 4.0, code Apache-2.0 | Imaging-consistent labels; CT-derived meshes |
| Z-Anatomy | per-object | CC BY-SA 4.0 overall; specific objects CC BY-NC / BY-NC-SA (kidneys, inner ear per the license audit) — **excluded until individually cleared** | Supplementary fills |

Not sources: Visible Human raw data (NLM Terms — acknowledgement-only,
never relabeled CC), any marketplace model (Sketchfab/Zygote/BioDigital terms),
NIH 3D bulk harvests (per-model licenses only).

Each source directory carries a `SOURCE.md`: origin URL, retrieval date,
release, license text or archived license-page snapshot, and the SHA-256 of
every archive as downloaded.

## The provenance ledger

`tools/provenance.py` walks a source directory and emits:

- `ledger.json` — one entry per file: `path`, `bytes`, `sha256`, `format`,
  `source` (dataset + release), `license` (SPDX-style string as recorded in the
  source's own license file/page), `license_evidence` (path to the archived
  license text inside the source dir), `structure_id` (filled at registration;
  `null` until then).
- `ledger-summary.md` — counts by format/license/source, total bytes, and a
  list of files whose license could not be determined (`UNKNOWN` — these fail
  the gate).

**Gate:** a geometry file may be referenced by the registry only if it has a
ledger entry with a determined license compatible with the project's
compatibility table (CC BY 4.0 ✓; CC BY-SA 4.0 ✓ with share-alike noted;
CC BY-NC* ✗ excluded; UNKNOWN ✗ excluded). The gate runs in the registry build,
not by convention.

## Pipeline stages

1. **Intake** — archives verified against `SOURCE.md` hashes; extracted to a
   working area outside `data/sources/` (sources stay byte-identical).
2. **Inventory** — per-file census: format, vertex/face counts (parsed, not
   estimated), source part ID (BodyParts3D FJ/FMA key; TotalSegmentator label).
3. **Mapping** — source part ID → Body Model structure ID, via the naming spine
   (FMA ID → `fma` field; TA term match). Unmapped parts are reported, never
   force-matched; ambiguous mappings are flagged `verify`.
4. **Registration** — adopted parts arrive in the source's own coordinate frame
   (BodyParts3D: its published frame; TotalSegmentator: per-scan frames).
   Registration aligns parts onto the Body Model's canonical frame
   (centimetres, anatomical position, x+ = subject right, y+ = up, z+ =
   anterior — the Phase-1 convention) using the skeletal module as the anchor
   set: bone anchors derived from articulation chains are the fixed reference,
   soft-tissue parts register against their skeletal neighbours. Transform per
   part is stored in the registry; the source mesh is never destructively
   edited.
5. **Registry build** — emits `geometry-registry.json`: per structure ID,
   mesh references (per source, per LOD), canonical transform, bounding box,
   and the ledger hash of each referenced file. Shells consume only this.
6. **LOD generation** — decimation levels generated from the adopted meshes
   (the 99%-reduced BodyParts3D set is the mid LOD by construction; full and
   further-reduced levels are generated, never hand-authored).

## Coverage census

`tools/census.py geometry` reports, per body system: Body Model target count,
structures with ≥1 registered mesh, structures with records but no mesh,
meshes with no record (unmapped). Numbers come from the registry and the model
— never from the source dataset's marketing counts. Gaps are listed by ID.
This census is the P2 exit criterion: skeletal coverage must reach the full
206-record set (by adoption + mapping) before muscular work begins.

## Verification gates

- Hash check of every source archive against `SOURCE.md` at intake.
- Ledger completeness: every file under `data/sources/` appears in the ledger.
- Parse check: every adopted mesh parses (vertex/face counts > 0, indices in range).
- Registration sanity: registered bounding boxes fall inside the canonical
  body envelope and overlap their articulation neighbours within tolerance
  (the Phase-1 assembly check, generalised).

## Open decisions

- **OD-03.1** TotalSegmentator adoption timing: dataset is large and per-scan;
  P2 may register BodyParts3D only, deferring TotalSegmentator meshes to P6
  (imaging) while adopting its *label set* now as the imaging floor (see
  OD-02.2). Decide after the BodyParts3D census in Milestone 1.
- **OD-03.2** Z-Anatomy per-object clearance requires reading each object's
  license inside the .blend/GLB exports; the GLB exports found on this machine
  are per-system merges, which cannot be cleared per-object. Z-Anatomy stays
  supplementary/reference-only until a per-object source is adopted.
