# Registration sketch — BodyParts3D frame → ANATOMICA canonical frame

Status: design note for pipeline stage 4 (design/03-geometry-pipeline.md).
Everything quantitative below was **measured** from the extracted BP3D 4.0
meshes resolved in `data/skeletal/skeleton-geometry.json` (Milestone 2) —
vertex streams, not headers — except where a header claim is explicitly
identified as such and corroborated by measurement.

## The two frames

- **BP3D source frame** (measured below): millimetres; x+ = subject's left,
  y+ = posterior, z+ = superior; right-handed.
- **ANATOMICA canonical frame** (design 03, the Phase-1 convention):
  centimetres, anatomical position, x+ = subject's right, y+ = up,
  z+ = anterior, ground at y = 0.

## Measured evidence (skeletal meshes only, 199 mapped records)

Whole-skeleton union bounding box (IS-A compositions), in source units:

```
min  (-323.91, -236.04,  -70.48)
max  ( 323.94,   18.00, 1636.27)
span ( 647.85,  254.05, 1706.75)
```

Axis identification, from named bones whose anatomy fixes a direction:

| Axis | Direction | Evidence (bounding boxes, source units) |
|---|---|---|
| z | **+ = superior** | Top of body: parietal bone max z = 1636.27 (the union max). Bottom: distal phalanx of little toe reaches z = −70.48 (the union min). Frontal bone z 1520.9–1629.9; right femur z 368.2–834.3 (its 466.1 mm span is the femur's length, knee→hip). |
| y | **+ = posterior** | Sternum (anterior chest wall) y = −213.8…−130.8; thoracic vertebra T6 y = −65.2…−1.2; occipital bone reaches y = +18.00 (the union's posterior extreme); the anterior extreme is the foot: distal phalanx I of right foot y = −236.04. Anterior is therefore −y. |
| x | **+ = subject's left** | Right femur x = −150.1…−31.9 (centre −91.0); left femur x = +32.0…+150.2 (centre +91.1). Midline bones centre on x ≈ 0: frontal −0.65, sacrum −0.7, mandible −0.6. Lateral extremes are the hands: thumb distal phalanges at x = ∓323.9. |

Units: OBJ headers state `Bounds(mm)`, and measurement corroborates
millimetres — the superior–inferior span is 1706.75 units ≈ 170.7 cm, a
plausible standing height, and the femur's 466.1-unit span ≈ 46.6 cm.
Canonical frame is centimetres, so the scale factor is 0.1.

Handedness: (left, posterior, superior) is a right-handed triple
(x̂ × ŷ = ẑ on the measured directions), so BP3D's frame is right-handed.
The canonical (right, up, anterior) triple is left-handed as defined.
The conversion below therefore has determinant −1: it is a rotation,
a scale, **and one mirror**. Triangle winding flips under it; shells must
flip index winding (or equivalently adjust culling/normals) at import.
This is a known, mechanical step — but it must not be discovered later by
a renderer showing inside-out bones.

## The frame conversion (per-vertex, before any pose registration)

```
app_x = -bp_x * 0.1     (subject right, cm)
app_y =  bp_z * 0.1     (up, cm)
app_z = -bp_y * 0.1     (anterior, cm)
```

plus a translation that registration must still determine (see origins).

## Origins — what is known and what is not

- **x = 0 is the mid-sagittal plane.** Verified by symmetry: the union is
  x-symmetric to 0.03 units (±323.9) and midline bones centre within
  0.7 units of 0. No x translation needed.
- **z = 0 is not the ground.** The skeleton's lowest point is −70.48
  (toe tip); the calcaneus bottom is −68.5. The source pose has
  plantar-flexed feet (toes point down; the heel never reaches a ground
  plane), so z = 0 sits ~70 mm above the lowest point, near ankle level.
  The exact landmark, if any, is **unknown**. Registration must place the
  body on the canonical ground plane itself.
- **y = 0 has no identified landmark.** Posterior extreme is +18.0
  (occiput); vertebral-body centres sit at y ≈ −33…−42. The y offset must
  be solved from anatomy (e.g. aligning the vertebral column / sacrum to
  the Phase-1 anchor chain), not assumed from the origin.

## Pose differences the frame conversion does NOT fix

The source model is one individual in a near-anatomical pose, not the
Phase-1 canonical pose: feet plantar-flexed (above); arms hang lateral to
the trunk with the humerus spanning z 1029–1337 (shoulder→elbow) and the
hands reaching |x| ≈ 324. Per-part rigid registration against the
articulation-chain anchors (design 03, stage 4) remains necessary; the
frame conversion only makes the two coordinate systems commensurate.

## Archive facts registration can rely on (measured)

- For every skeletal part present in both archives, the IS-A and PART-OF
  files carry **identical vertex/face streams** (199/199 shared FJ ids;
  only headers differ — Representation ID namespaces differ per tree and
  PART-OF headers add a `Volume(cm3)` line). Registry build can treat the
  trees as geometric duplicates for the skeleton and pick per design 03
  (IS-A primary).
- **Hyoid anomaly:** the hyoid concept owns two IS-A files, FJ2772 and
  FJ3201, with byte-identical vertex/face content and the same
  Representation ID (BP8836) — duplicate representations of one bone.
  Assembly must de-duplicate or the hyoid renders doubled.
- The sternum exists only in the PART-OF tree; its composition is exactly
  its three anatomical parts (manubrium FJ3290, body of sternum FJ3178,
  xiphoid process FJ3153).

## Still unknown (flagged, not assumed)

1. Whether all 2,905 concepts (soft tissues included) share this single
   global frame — only the 199 skeletal concepts were measured here.
2. The anatomical meaning, if any, of the y and z origins.
3. Pose-normalisation strategy: per-bone rigid transforms onto the
   Phase-1 anchor frame vs. accepting the source pose as the canonical
   pose and re-deriving anchors. Design 03 stores a transform per part;
   the choice is a Milestone-3 decision, informed by how large the
   per-bone residuals are.
4. The source subject's proportions vs. the Phase-1 nominal 170 cm
   frame: measured height span 170.7 cm, but segment proportions are
   this individual's and will differ in detail from the anchor model.
