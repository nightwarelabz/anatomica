# Milestone 3 — TotalSegmentator intake + skeleton registration/assembly

Date: 2026-11-06. Scope: local working tree only; nothing uploaded anywhere.

## Delivered

- `tools/ts_intake.py` — TotalSegmentator subset intake via HTTP range
  requests (see below), CRC-verified extraction.
- `data/sources/totalsegmentator-1.0/` — `SOURCE.md`, `subset/`
  (meta.csv + 10 complete subjects), `index-census.json`,
  `labels.json` / `labels.md` (by `tools/ts_census.py`), provenance
  `ledger.json` / `ledger-summary.md`.
- `data/skeletal/gap-analysis.md` — per-bone verdicts for the 7
  NOT-FOUND records.
- `tools/assemble_skeleton.py` + `data/skeletal/skeleton-assembled.json`
  — the register_sketch conversion applied to all 199 geometry-bearing
  records.
- `tools/assembly_check.py` — independent checker; **all 7 checks PASS**
  (full output summarised below).

## 1. TotalSegmentator intake

**Source:** Zenodo record 6802614, dataset v1.0, **CC BY 4.0** (license
id read from the Zenodo record metadata at intake). The full dataset is
a single zip of **28,404,091,806 bytes** (Zenodo-published MD5
`f0fbb3f91d9d99f2169863545f577b30`).

**What was downloaded, exactly:** the full zip was *not* downloaded —
a measured 32 MiB probe ran at ~0.95 MB/s (≈8 h for 28.4 GB), which is
impractical in-session. Instead, range requests fetched:

- the zip's complete central directory (19,627,618 B; 128,830
  entries) — the archive's own index;
- `meta.csv` in full (header + 1,204 subject rows);
- **10 complete subject folders** evenly spaced across the index
  (s0000, s0167, s0330, s0480, s0633, s0778, s0937, s1090, s1250,
  s1405): **1,051 files, 328,668,874 bytes**. Every file was verified
  against the CRC-32 in the archive's central directory at extraction
  (all passed) and SHA-256-hashed; the inventory is
  `index-census.json`. On-disk re-verification: every subset subject
  carries exactly the 104-label set plus its CT. NIfTI spot check
  (s0000) parses cleanly (sacrum mask 294×192×179, 1 byte/voxel; CT
  4 bytes/voxel; decompressed sizes exact).

**Not downloaded:** the other 1,194 subject folders (~28.1 GB) —
pixel data whose label sets the index census already proves identical.
Provenance ledger over the source directory: **1,055 files,
328,909,790 bytes, 0 unknown licenses.**

**Label census** (from the full index, `tools/ts_census.py`):
**1,204 subjects; 104 distinct labels; every label present in all
1,204 subjects**; exact agreement with the code package's published
`total_v1` map (104 labels, zero differences in either direction).

**Overlap with the Body Model:** **59 TS labels map onto 59 of the
206 skeletal records** (all 24 presacral vertebrae, all 24 ribs,
femur/humerus/scapula/hip/clavicle pairs, sacrum) under the explicit
rules in `tools/ts_census.py`. The other 45 labels are non-skeletal
and group by system as: cardiovascular 13, muscular 10, digestive 8,
respiratory 6, urinary 3, endocrine 2, lymphatic 1, nervous 1,
integumentary/other 1 (`face` — a soft-tissue label, deliberately
**not** mapped to any bone). Notable skeletal absences in TS v1: no
sternum (v2-only), no tibia/fibula/patella, no hand/foot bones, no
individual skull bones, **no ossicles, no coccyx** (either version —
the v2 map's 117 labels were also enumerated: no ear or coccyx label).

## 2. Gap analysis (7 NOT-FOUND bones) — verdicts

Full analysis: `data/skeletal/gap-analysis.md`. Summary:

- **Ossicles ×6 — genuinely uncovered** by every verified source
  checked: absent from BP3D (M2 proof), absent from TS v1+v2 label
  sets, absent from HaN-Seg's 30 OAR masks (listed from its archive
  index; HaN-Seg segments the cochlea but no ossicles — and is
  CC BY-NC-ND 4.0, license-excluded regardless). Zenodo-wide searches
  surfaced no human ossicle segmentation dataset.
- **Coccyx — genuinely uncovered**: absent from BP3D; TS carries only
  a single `sacrum` class (whether its masks include coccygeal voxels
  is unverified, and carving one out would be modelling, not
  adoption — not planned); VerSe remains an **unverified lead**
  (Zenodo holds only its CC BY-ND design document).
- **Fallback for all seven, in order:** (1) Z-Anatomy per-object
  clearance under OD-03.2 — the ossicles and coccyx exist as
  individual objects in Z-Anatomy's per-object source, but their
  per-object licenses have **not** been read and are not assumed;
  the merged GLBs stay excluded. (2) Failing clearance, the records
  keep empty, flagged geometry slots.
- Consequence: the design-03 P2 exit criterion (full 206-record
  skeletal coverage by adoption) is **not met**; it now depends on
  the OD-03.2 decision.

## 3. Registration + assembly

`tools/assemble_skeleton.py` applies the register_sketch conversion
(`app = (−bp_x, bp_z, −bp_y) × 0.1`, winding flip recorded) by
streaming every vertex of the resolved meshes — IS-A composition
primary, PART-OF for the sternum, hyoid de-duplicated on its
geometry stream (FJ3201 dropped as a content-identical duplicate of
FJ2772; its differing header File ID is why whole-file hashing was
replaced by geometry-stream hashing). Output:
`data/skeletal/skeleton-assembled.json` — **199 records, 201 mesh
files, 283,091 vertices, 511,968 faces**, each with a canonical-frame
bounding box measured from the transformed vertices.

**Assembly measurements (canonical frame, cm):**

- Whole-body union: min (−32.394, −7.048, −1.800),
  max (32.391, 163.627, 23.604) → **width 64.785 × height 170.675 ×
  depth 25.405 cm**, exactly the register_sketch source spans.
- Mirror symmetry: 83 left/right pairs; worst bbox deviation
  **0.414 cm** (inferior nasal conchae), then lacrimal 0.401,
  parietal 0.380, maxilla 0.332 cm — a real individual's asymmetry,
  inside the checker's declared 1.0 cm tolerance.
- Vertical sanity: frontal bone y ∈ [152.09, 162.99]; calcanei
  y ∈ [−6.85, −1.92] (R) / [−6.84, −1.91] (L); the global y-min
  belongs to the left distal phalanx of the little toe (−7.048 cm)
  and the y-max to the right parietal bone (163.627 cm).
- Checker (`tools/assembly_check.py`, independent path via
  corner-transformed M2 boxes): C1 record set 199/199; C2 boxes match
  with worst diff 0.00 cm; C3 bounds as above; C4 mirror as above;
  C5 skull-above-feet; C6 no NaN/Inf; C7 hyoid de-duplicated
  (687 v / 1 file assembled vs 1,374 v / 2 files in M2). **Exit 0.**

## Flagged unknowns carried forward (not fixed, not hidden)

1. **Ground placement not applied.** Canonical y = −7.048 cm at the
   toe tip is the *source* origin showing through: BP3D z = 0 sits
   ~70 mm above the lowest point with no identified landmark, so the
   assembled skeleton floats/sinks relative to canonical ground
   (y = 0) by an unsolved offset.
2. **Anterior–posterior origin unregistered.** Source y = 0 has no
   identified landmark; canonical z spans −1.800 (occiput) to
   +23.604 (toe tips) on the source's say-so only.
3. **Pose not normalised.** Boxes are the source pose frame-converted:
   feet plantar-flexed, arms hanging lateral (union width 64.785 cm
   is fingertip-to-fingertip of hanging arms, not shoulder width).
   Per-part registration against the Phase-1 anchor chain remains to
   be done; the transform-per-part registry slot is where it lands.
4. **One individual's proportions.** The 170.675 cm span and all
   segment proportions are the BP3D subject's, vs the Phase-1
   nominal 170 cm frame — close, not identical; residuals per bone
   are a registration-prototype output, not yet measured.
5. **Soft-tissue frame sharing unverified.** Only the 199 skeletal
   concepts have been measured in the BP3D frame; whether all 2,905
   concepts share it is still assumed, not proven.

## Next steps

1. Per-part registration prototype: solve the y/z origin offsets and
   per-bone residuals against the Phase-1 anchor chain; store
   transforms in the registry (design 03 stage 4–5).
2. OD-03.2 decision support: adopt the Z-Anatomy per-object source
   and read the ossicle/coccyx object licenses — the only verified
   route to 206/206.
3. Convert the skeletal module to the design-02 JSON schema with
   `fma` populated (input ready since M2); prove the 206 census
   survives conversion.
4. Muscular + cardiovascular data modules (design 02), with census
   checkers — TS's 59-label skeletal overlap and 45 non-skeletal
   labels are now available as a CT-consistent second source.
