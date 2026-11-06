# Source: BodyParts3D 4.0 (DBCLS — Database Center for Life Science, Japan)

- **Origin:** LSDB Archive (official DBCLS distribution),
  https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html —
  files served from `https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/`.
- **Retrieved:** 2026-11-06, direct HTTPS download of the published files.
  A pre-existing copy of the same release (ISA archive + extracted meshes +
  tables) also exists on this machine at `~/workspace/anatlas/` from an
  earlier local project; spot-checked meshes (FJ1252, FJ3400) are
  byte-identical to this download.
- **Release:** 4.0 (the `LATEST` tree). Polygon sets are the 99%
  polygon-reduction editions.

## Files and SHA-256 (computed at intake)

DBCLS does not publish checksums for these files (checked the download page,
`README_e.html`, and `release_4.0_e.html` on 2026-11-06 — no MD5/SHA listing
exists). The hashes below are therefore the project's own intake pins,
recorded in the provenance ledger (`ledger.json`); any future re-download
must match them or be treated as a new release.

| File | Bytes | SHA-256 |
|---|---|---|
| isa_BP3D_4.0_obj_99.zip | 142,903,898 | `40665852c49f218326590e204db91064a1ecfc3c6f8cbd7bbbcaac62c7cd409e` |
| partof_BP3D_4.0_obj_99.zip | 64,888,505 | `9fbc713fffeee924a5a657d9813d84d7eb957bded63adb854931dd5e3eb61c97` |
| isa_parts_list_e.txt | 128,086 | `ab7796deedd49205e77f3609a1cb8c53e2bbee14ecb5c9a6ca05227469780513` |
| partof_parts_list_e.txt | 59,351 | `9224080557053e6f1322f1e13ab27f0ecde0db19bb3b505f0631afad230eeebd` |
| isa_element_parts.txt | 1,142,159 | `a3de74423f943b0d724ae8f59b3a817f87c423a544f8db98113b1980817cbeaf` |
| partof_element_parts.txt | 651,179 | `3f5f6df1028eb122b30de77c711597b6bb8e5541658e5985859fd228adbf88ea` |
| isa_inclusion_relation_list.txt | 207,664 | `26e7d818e03a8c909fe09c561f38d0d513423c87681f9450a803bc38f5b07564` |
| partof_inclusion_relation_list.txt | 91,241 | `1b40738270931e3c1d955ce34e0fce0d8d10d8c5ad543463e40b4b4c0243007c` |

Both archives passed zip integrity testing (`testzip`: no bad entries) and
contain 2,234 (IS-A) and 1,258 (PART-OF) OBJ meshes respectively.

## License position (dual-recorded, per the research's version trap)

- **Current license page** (archived in-tree as `LICENSE-PAGE.html`, DBCLS
  page updated 2025-02-27): **CC BY 4.0**.
- **Every OBJ file header** (3,492 of 3,492, machine-checked) states:
  "BodyParts3D, (c) The Database Center for Life Science licensed under
  **CC Attribution-Share Alike 2.1 Japan**."
- Project position: attribute as "BodyParts3D, © The Database Center for Life
  Science"; distribute derived data so that it satisfies the stricter of the
  two readings (share-alike on the mesh data) until DBCLS's position is
  reconfirmed at a future pin. Both readings are recorded in the ledger —
  neither is hidden.

## Mapping files

- `isa_parts_list_e.txt` — 2,905 FMA concepts (concept id, representation id,
  English name).
- `isa_element_parts.txt` — concept → element file (FJ####) composition;
  many-to-many. The ISA element set is exactly the 2,234 files in the IS-A
  archive (verified bijection), so every listed concept composes from
  in-archive meshes.
- Inclusion-relation lists give the IS-A and PART-OF hierarchies.
