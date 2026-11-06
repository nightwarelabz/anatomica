#!/usr/bin/env python3
"""ANATOMICA skeleton assembly — Milestone 3.

Applies the register_sketch frame conversion to the BP3D skeletal meshes
resolved in data/skeletal/skeleton-geometry.json (Milestone 2) and emits
data/skeletal/skeleton-assembled.json with canonical-frame bounding boxes
computed by streaming and transforming every vertex (no header values,
no stored source bboxes trusted).

Conversion (tools/register_sketch.md, measured):
    app_x = -bp_x * 0.1    (subject right, cm)
    app_y =  bp_z * 0.1    (up, cm)
    app_z = -bp_y * 0.1    (anterior, cm)
Signed permutation x 0.1, determinant -1 relative to the canonical
frame's handedness: triangle winding flips at import (recorded in the
output meta; this tool emits boxes/counts, not reordered meshes).

Mesh-set rule (design 03: IS-A primary):
  - use the record's IS-A composition when non-empty;
  - else its PART-OF composition (the sternum exists only there);
  - byte-identical duplicate files inside one composition are
    de-duplicated (the hyoid's FJ2772/FJ3201 anomaly) and reported.

Carried unknowns (NOT silently fixed): the source z=0 sits ~70 mm above
the lowest toe point (no identified landmark) and y=0 has no identified
landmark, so canonical y values here are frame-converted only — ground
placement and anterior-posterior origin are Milestone-3+ registration
decisions, flagged in the output meta.

Stdlib only.
"""
import hashlib
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GEOM = os.path.join(ROOT, "data", "skeletal", "skeleton-geometry.json")
OUT = os.path.join(ROOT, "data", "skeletal", "skeleton-assembled.json")


def convert(x, y, z):
    return (-x * 0.1, z * 0.1, -y * 0.1)


def stream_bbox(path):
    mn = [float("inf")] * 3
    mx = [float("-inf")] * 3
    nv = 0
    with open(path, "rb") as fh:
        for line in fh:
            if line.startswith(b"v "):
                p = line.split()
                v = convert(float(p[1]), float(p[2]), float(p[3]))
                nv += 1
                for i in range(3):
                    if v[i] < mn[i]:
                        mn[i] = v[i]
                    if v[i] > mx[i]:
                        mx[i] = v[i]
    return mn, mx, nv


def geometry_digest(path):
    """Hash of the geometry stream only (v/vt/vn/f lines).

    The hyoid's two IS-A files differ in header lines (their own File
    IDs) but carry byte-identical vertex/face content (Milestone 2);
    whole-file hashing would miss the duplication, geometry hashing
    catches exactly the duplication that matters for assembly."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for line in f:
            if line[:2] in (b"v ", b"vt", b"vn", b"f "):
                h.update(line)
    return h.hexdigest()


def main():
    with open(GEOM) as f:
        geom = json.load(f)

    records = []
    skipped = []
    dedupes = []
    union_min = [float("inf")] * 3
    union_max = [float("-inf")] * 3

    for rec in geom["records"]:
        rid = rec["record_id"]
        if rec["isa_meshes"]:
            tree, meshes = "isa", rec["isa_meshes"]
        elif rec["partof_meshes"]:
            tree, meshes = "partof", rec["partof_meshes"]
        else:
            skipped.append(rid)
            continue

        # de-duplicate geometry-identical files within the composition
        seen = {}
        kept = []
        for m in meshes:
            digest = geometry_digest(os.path.join(ROOT, m["path"]))
            if digest in seen:
                dedupes.append({"record_id": rid, "kept": seen[digest], "dropped": m["fj"]})
                continue
            seen[digest] = m["fj"]
            kept.append(m)

        mn = [float("inf")] * 3
        mx = [float("-inf")] * 3
        out_meshes = []
        tv = tf = 0
        for m in kept:
            bmn, bmx, nv = stream_bbox(os.path.join(ROOT, m["path"]))
            if nv != m["vertices"]:
                print(f"VERTEX COUNT MISMATCH {rid} {m['fj']}: streamed {nv} != M2 {m['vertices']}",
                      file=sys.stderr)
                return 1
            for i in range(3):
                mn[i] = min(mn[i], bmn[i])
                mx[i] = max(mx[i], bmx[i])
            out_meshes.append({"fj": m["fj"], "path": m["path"],
                               "vertices": m["vertices"], "faces": m["faces"]})
            tv += m["vertices"]
            tf += m["faces"]
        for i in range(3):
            union_min[i] = min(union_min[i], mn[i])
            union_max[i] = max(union_max[i], mx[i])

        records.append({
            "record_id": rid,
            "fma_id": rec["fma_id"],
            "concept_name": rec["concept_name"],
            "source_tree": tree,
            "meshes": out_meshes,
            "totals": {"files": len(out_meshes), "vertices": tv, "faces": tf},
            "m2_totals_carried": rec["totals"],
            "bbox_canonical_cm": {"min": mn, "max": mx},
        })

    out = {
        "meta": {
            "title": "ANATOMICA assembled skeleton — Milestone 3",
            "generated_by": "tools/assemble_skeleton.py",
            "input": "data/skeletal/skeleton-geometry.json (Milestone 2)",
            "canonical_frame": "centimetres; x+ = subject right, y+ = up, z+ = anterior (Phase-1 convention)",
            "transform": "app = (-bp_x, bp_z, -bp_y) * 0.1; signed permutation, determinant -1 vs canonical handedness",
            "winding": "triangle winding flips under this transform; shells must flip index winding (or culling/normals) at import",
            "mesh_set_rule": "IS-A composition primary; PART-OF only where IS-A is empty (sternum); byte-identical duplicates within a composition de-duplicated (hyoid)",
            "flagged_unknowns": [
                "Source z=0 sits ~70 mm above the lowest toe point (toe tip z=-70.48 mm); no landmark identified. Canonical y here is frame-converted only — ground placement (y=0 at sole) is NOT applied.",
                "Source y=0 has no identified anatomical landmark; canonical z origin is therefore unregistered (posterior extreme +18.0 mm source = occiput).",
                "Per-part pose registration (plantar-flexed feet, hanging arms) is not performed by this stage; boxes are in the source pose, frame-converted.",
            ],
            "records_with_geometry": len(records),
            "records_without_geometry": skipped,
            "deduped_files": dedupes,
            "union_bbox_canonical_cm": {"min": union_min, "max": union_max},
        },
        "records": records,
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, sort_keys=False)
    span = [union_max[i] - union_min[i] for i in range(3)]
    print(f"assembled {len(records)} records; skipped (no geometry): {skipped}")
    print(f"deduped: {dedupes}")
    print(f"union min {union_min} max {union_max}")
    print(f"span cm: width(x)={span[0]:.3f} height(y)={span[1]:.3f} depth(z)={span[2]:.3f}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
