# Milestone 2 — FMA-ID mapping + skeletal geometry conversion

Date: 2026-11-06. Scope: local working tree only; nothing uploaded anywhere.
The Phase-1 dataset (`~/workspace/anatomica-app/data/skeleton.js`) was read
as ground truth and not modified.

## Delivered

- `tools/fma_map.py` — rule-based mapper + geometry resolver (stdlib only).
  Every candidate name a rule produces is verified by exact lookup in the
  BP3D release tables; no fuzzy matching anywhere.
- `data/skeletal/fma-mapping.json` — one row per skeletal record (206/206):
  record id, FMA concept id, concept name, representation id, primary mesh
  file, mapping kind, and the evidence for the match (table, row, rule, and
  corroboration from the OBJ header of the concept's own mesh).
- `data/skeletal/skeleton-geometry.json` — per record, the resolved mesh
  lists (IS-A composition and PART-OF composition, separately) with
  vertex/face counts and bounding boxes measured by streaming each OBJ.
- `tools/skeletal_check.py` — independent checker (no shared code with the
  mapper). Full run below.
- `tools/register_sketch.md` — registration design note with measured
  bounding boxes and frame analysis.

## Mapping distribution (206 records, all accounted for)

| Kind | Count | Meaning |
|---|---|---|
| exact-class | 198 | Concept denotes exactly this bone, including laterality / level / digit in the concept name |
| class+side | 0 | (supported by the tool; never triggered — see below) |
| class+level | 0 | (supported by the tool; never triggered — see below) |
| part-of-composite | 1 | Sternum — concept exists only in the PART-OF tree |
| NOT-FOUND | 7 | Ossicles ×6, coccyx — concepts provably absent from BP3D 4.0 |
| **Total** | **206** | |

**Correction to the Milestone-1 expectation.** The M1 census characterised
the 145 name-unmatched bones as records "whose FMA naming is
class-level/ordinal". That was wrong about FMA/BP3D: the release *does*
carry lateralised and per-level concepts throughout — "right femur"
(FMA24474), "third cervical vertebra" (FMA12521), "right first rib"
(FMA7857), "proximal phalanx of right index finger" (FMA24451),
"navicular bone of right foot" (FMA24500). The naive match failed on
naming *forms*, not missing concepts: ordinal words vs digits ("Rib 1"
vs "first rib"), side placement ("(right)" suffix vs "right …" prefix /
"… of right foot"), and name variants (our "Triquetrum" = FMA "triquetral";
our "Ethmoid bone" = FMA "ethmoid"). True concept coverage is 199/206.

`class+side` and `class+level` came out at zero for the same reason: there
was no paired bone and no vertebra for which BP3D offers only the un-sided
or regional class. The kinds remain in the mapper (they are the honest
outcome if a future dataset lacks the specific concept) and their zero
counts are reported, not hidden.

## NOT-FOUND list (7) — with reasons

| Record | Reason |
|---|---|
| malleus_right, malleus_left | No malleus concept in either BP3D 4.0 parts list; stem "malleus" occurs 0 times across all six release tables |
| incus_right, incus_left | Same; stem "incus" 0 occurrences |
| stapes_right, stapes_left | Same; stem "stapes" 0 occurrences |
| coccyx | No coccyx concept in either parts list; stem "coccyx" 0 occurrences in all six tables (the coccygeus *muscles* exist — they contain "coccyge-", not "coccyx") |

These are absences in the source dataset, established by exhaustive search
and re-verified by the checker's rule R7. Nothing was force-matched to a
neighbouring concept. The ossicles and coccyx therefore have records but
no BP3D geometry; sourcing them is a separate decision (see Next steps).

## Geometry resolution

- 199 mapped records resolve to **401 distinct mesh paths** (199 IS-A +
  202 PART-OF). Every mapped bone's IS-A composition is exactly one mesh,
  except the hyoid (two files — an anomaly, below). Summed over records,
  IS-A compositions total **278,146 vertices / 505,050 faces**.
- For all 199 parts present in both archives, the IS-A and PART-OF files
  carry **identical vertex/face streams** (headers differ: per-tree
  Representation IDs; PART-OF headers add a Volume line). The registry can
  treat the trees as geometric duplicates for the skeleton.
- **Sternum** (the one part-of-composite): no IS-A entry at all; its
  PART-OF composition is exactly its three anatomical parts — manubrium
  FJ3290 (1,446 v / 2,546 f), body of sternum FJ3178 (3,691 v / 4,646 f),
  xiphoid process FJ3153 (495 v / 922 f).
- **Hyoid anomaly:** the concept owns two IS-A files, FJ2772 and FJ3201,
  with byte-identical vertex/face content and the same Representation ID
  (BP8836) — duplicate representations of one bone in the archive. The
  geometry file lists both (faithful to the archive's composition); the
  checker flags it as a note, and assembly must de-duplicate.

## Checker output summary (`tools/skeletal_check.py`, exit 0)

All 18 checks PASS, 0 failures:

- (a) mapping and geometry each cover exactly the 206 record ids;
- (b) all 401 referenced mesh paths exist on disk;
- (c) table counts re-derived = census (2,905 ISA concepts; 2,234 IS-A
  files; 1,258 PART-OF files); every record's mesh lists equal the tables'
  element composition recomputed independently; every stored vertex/face
  count equals an independent recount; every referenced mesh's OBJ header
  agrees (File ID matches; header Concept ID is the record's concept or
  its descendant in the tree);
- (d) anatomy spot rules R1–R8, 0 violations: ribs→rib concepts;
  vertebrae→vertebra/atlas/axis/sacrum; skull records never map to
  limb/trunk concepts; side coherence; hand phalanges→finger/thumb and
  foot phalanges→toe concepts; metacarpal/metatarsal stems; NOT-FOUND set
  exactly the provably-absent seven; ordinal/digit coherence;
- (e) 2 anomaly notes, both the hyoid duplicate (one per archive tree).

## Measured bounding boxes (source units = mm; full analysis in tools/register_sketch.md)

Whole-skeleton union (IS-A): min (−323.91, −236.04, −70.48),
max (323.94, 18.00, 1636.27); span (647.85, 254.05, 1706.75) mm.

| Structure | min (x, y, z) | max (x, y, z) |
|---|---|---|
| Right femur (FJ3365) | (−150.1, −112.2, 368.2) | (−31.9, −49.5, 834.3) |
| Frontal bone (FJ3200) | (−63.3, −177.4, 1520.9) | (62.0, −106.6, 1629.9) |
| Sacrum (FJ3393) | (−59.6, −81.4, 782.8) | (58.2, 7.3, 927.2) |
| Sternum (PART-OF union) | (−27.4, −213.8, 1164.0) | (27.4, −130.8, 1325.2) |

Frame findings (measured, details in the sketch): BP3D frame is
millimetres, right-handed, x+ = subject's **left**, y+ = **posterior**,
z+ = **superior**; x = 0 is the mid-sagittal plane, but z = 0 is ~70 mm
above the lowest (toe) point and y = 0 has no identified landmark — both
offsets are registration unknowns. Conversion to the canonical frame is a
signed permutation × 0.1 with determinant −1 relative to the canonical
frame's own handedness, so triangle winding flips and must be handled at
import. The source pose (plantar-flexed feet, arms hanging lateral) is
not the canonical pose; per-part registration is still required.

## Flagged observations

- **Ground-truth quirk (not modified):** records `phalanxI_mid_*` and
  `toephalanxI_mid_*` carry ids saying "mid" but names saying "Distal
  phalanx I" — anatomically the name is right (thumb and hallux have no
  middle phalanx). Mapping followed the names; the dataset stands as-is.
- The `fma` field population for the design-02 JSON conversion of the
  skeletal module is now unblocked: `fma-mapping.json` is the input.

## Next steps

1. Registration prototype (Milestone 3): implement the frame conversion,
   solve the y/z origin offsets against the Phase-1 anchor chain, store
   per-part transforms in the geometry registry, de-duplicate the hyoid,
   and run the generalised assembly sanity check.
2. Convert the skeletal module to the design-02 JSON schema with `fma`
   populated from this mapping; prove the 206 census survives conversion.
3. Decide the ossicle/coccyx geometry source (BP3D cannot supply them) —
   candidates are a per-object-cleared Z-Anatomy adoption or a later
   TotalSegmentator-derived segmentation; flagged, not decided here.
4. Muscular + cardiovascular data modules; TotalSegmentator intake —
   unchanged from the Milestone-1 list.
