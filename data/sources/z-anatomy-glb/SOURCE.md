# Source: Z-Anatomy GLB exports (per-system merges)

- **Origin:** Z-Anatomy ("Models of human anatomy", derived from BodyParts3D),
  exported to per-system GLB files. These copies were found on this machine at
  `~/workspace/anatlas/za/public/models/` (an earlier local project) and copied
  byte-identical on 2026-11-06; hashes are in the provenance ledger.
- **Files:** `cardiovascular.glb`, `joints.glb`, `lymphatic.glb`,
  `muscular.glb`, `nervous.glb`, `skeletal.glb`, `visceral.glb`, plus the
  upstream `License.txt`.
- **License position — RESTRICTED, reference only.** The upstream notice
  (`License.txt`, copied with the models) states the Z-Anatomy content is
  CC-BY-SA 4.0 over BodyParts3D (attributed there as CC-BY-SA 2.1 Japan), but
  it also lists embedded models under non-commercial terms:
  "Anatomy of the Inner Ear" (CC-BY-NC-SA 4.0) and "Kidney" (CC-BY-NC 4.0).
  The distributor's own notice for this export states: *"The work as
  distributed is non-commercial (CC BY-NC-SA 4.0)."*
- **Consequence:** because these GLBs are per-system merges, the NC-licensed
  components cannot be separated per object. **No part of these files may be
  used in ANATOMICA product data.** They are held for census/reference only
  (structure naming and coverage comparison), exactly as design document
  `03-geometry-pipeline.md` (OD-03.2) prescribes. A per-object Z-Anatomy
  source with per-object license clearance is required before any Z-Anatomy
  geometry is adopted.
