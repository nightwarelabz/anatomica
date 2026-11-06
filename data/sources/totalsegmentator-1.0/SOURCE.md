# Source: TotalSegmentator dataset v1.0 (Wasserthal et al.)

- **Origin:** Zenodo record 6802614, "Dataset with segmentations of 104
  important anatomical structures in 1204 CT images", version 1.0.
  File endpoint:
  `https://zenodo.org/api/records/6802614/files/Totalsegmentator_dataset.zip/content`
- **Retrieved:** 2026-11-06, by `tools/ts_intake.py` (range-request
  subset intake, see below).
- **Release:** dataset v1.0 (1,204 CT subjects, 104 structure labels).
  The TotalSegmentator *code* is Apache-2.0; no code was downloaded in
  this intake. One code-derived reference file was taken separately —
  the `total_v1` label list extracted from `totalsegmentator/
  map_to_binary.py` in the project's GitHub repository (Apache-2.0) —
  and is kept with the tools as `tools/ts_package_class_map_v1.json`,
  outside this source directory, so this directory carries one license.

## License

- **Dataset: CC BY 4.0** — as recorded in the Zenodo record's own
  metadata (`license: cc-by-4.0`, read from the Zenodo API at intake).
  Attribution: Wasserthal, J. et al., TotalSegmentator dataset, Zenodo
  DOI 10.5281/zenodo.6802614. (The dataset paper: "TotalSegmentator:
  Robust Segmentation of 104 Anatomic Structures in CT Images",
  Radiology: Artificial Intelligence 2023.)

## What was downloaded — and what was not, and why

The dataset is a **single zip of 28,404,091,806 bytes**. It was **not**
downloaded in full: a measured probe (32 MiB range read) ran at
~0.95 MB/s, putting a full download at roughly 8 hours — impractical
for this milestone's session. Instead, `tools/ts_intake.py` fetched,
via HTTP range requests against the official file endpoint:

1. The zip's end-of-central-directory and **complete central directory**
   (19,627,618 bytes; 128,830 entries) — the archive's own index. The
   label census (`labels.json` / `labels.md`, by `tools/ts_census.py`)
   is derived from this index and therefore covers **all 1,204
   subjects**, not just the subset: 104 distinct labels, each present
   in all 1,204 subjects, in exact agreement with the code package's
   published `total_v1` map (104 labels, no differences either way).
2. **`meta.csv`** (1,204 subject rows + header) in full.
3. **10 complete subject folders**, evenly spaced across the index
   (s0000, s0167, s0330, s0480, s0633, s0778, s0937, s1090, s1250,
   s1405): CT + all 104 segmentation NIfTIs each — 1,051 files total
   including meta.csv, 328,668,874 bytes. Every extracted file was
   verified against the CRC-32 recorded in the archive's central
   directory (all passed) and SHA-256-hashed at intake; the full
   inventory with hashes is `index-census.json` in this directory.
   On-disk re-verification after download: each subset subject carries
   exactly the 104-label set. NIfTI spot check (s0000): headers parse
   (348-byte header, `n+1` magic); sacrum mask 294×192×179 voxels at
   1 byte/voxel and CT at 4 bytes/voxel, decompressed sizes exact.

**Not downloaded:** the remaining 1,194 subject folders (~28.1 GB of
the zip). They are pixel data for subjects whose label sets are
already proven identical by the index census; the full zip remains
fetchable from the same endpoint, and Zenodo publishes its MD5
(`f0fbb3f91d9d99f2169863545f577b30`) for any future full intake. This
project's own intake hashes are the SHA-256 values in
`index-census.json` and `ledger.json`.

## Contents of this directory

| Entry | What it is |
|---|---|
| `SOURCE.md` | this file |
| `subset/` | the downloaded dataset content (meta.csv + 10 complete subjects), byte-identical extractions from the official zip |
| `index-census.json` | intake record by `tools/ts_intake.py`: index statistics + per-file SHA-256/CRC status of the subset |
| `labels.json`, `labels.md` | derived label census by `tools/ts_census.py` (derived from the dataset index; CC BY 4.0 with the dataset) |
| `ledger.json`, `ledger-summary.md` | provenance ledger by `tools/provenance.py` |

License evidence: the Zenodo record metadata (API response read at
intake; license id `cc-by-4.0`). No separate license file ships inside
the dataset zip's root.
