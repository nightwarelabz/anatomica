#!/usr/bin/env python3
"""ANATOMICA muscular assembly — Milestone 6 (mirrors the Milestone-3
skeletal assembler, tools/assemble_skeleton.py).

Applies the register_sketch frame conversion to the BP3D muscular meshes
resolved in data/muscular/muscle-geometry.json (Milestone 4) and emits
data/muscular/muscles-assembled.json with canonical-frame bounding boxes
computed by streaming and transforming every vertex (no header values,
no stored source bboxes trusted). Streamed vertex AND face counts are
asserted against the Milestone-4 recorded counts for every file.

Conversion (tools/register_sketch.md, measured on the skeleton):
    app_x = -bp_x * 0.1    (subject right, cm)
    app_y =  bp_z * 0.1    (up, cm)
    app_z = -bp_y * 0.1    (anterior, cm)
Signed permutation x 0.1, determinant -1 relative to the canonical
frame's handedness: triangle winding flips at import (recorded in the
output meta; this tool emits boxes/counts, not reordered meshes).

Mesh-set rule (design 03, same as Milestone 3): IS-A composition
primary; PART-OF only where IS-A is empty. In the Milestone-4 muscular
resolution every record has a non-empty IS-A composition and every
PART-OF fj is already present in the record's IS-A composition, so the
PART-OF tree contributes no geometry to any record; that fact is
verified here per record and reported in the output meta.

Carried unknowns (NOT silently fixed): register_sketch unknown 1 —
whether all concepts (soft tissues included) share the skeletal frame
was unproven when only the 199 skeletal concepts had been measured.
This assembly applies the identical transform; whether the muscular
layer lands coherently on the skeleton is tested independently by
tools/muscle_assembly_check.py, not assumed here. Ground placement and
AP origin registration are likewise NOT applied (frame conversion only),
exactly as in Milestone 3.

Stdlib only.
"""
import hashlib
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GEOM = os.path.join(ROOT, "data", "muscular", "muscle-geometry.json")
OUT = os.path.join(ROOT, "data", "muscular", "muscles-assembled.json")


def convert(x, y, z):
    return (-x * 0.1, z * 0.1, -y * 0.1)


def stream_counts_bbox(path):
    mn = [float("inf")] * 3
    mx = [float("-inf")] * 3
    nv = nf = 0
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
            elif line.startswith(b"f "):
                nf += 1
    return mn, mx, nv, nf


def geometry_digest(path):
    """Hash of the geometry stream only (v/vt/vn/f lines) — same rule
    as the Milestone-3 assembler (catches content-identical duplicates
    whose header File IDs differ)."""
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
    partof_redundant = 0
    union_min = [float("inf")] * 3
    union_max = [float("-inf")] * 3

    for rec in geom["records"]:
        rid = rec["record_id"]
        if rec["isa_meshes"]:
            tree, meshes = "isa", rec["isa_meshes"]
            isa_fjs = {m["fj"] for m in rec["isa_meshes"]}
            extra = {m["fj"] for m in rec["partof_meshes"]} - isa_fjs
            if extra:
                print(f"PART-OF ADDS GEOMETRY {rid}: {sorted(extra)} — "
                      f"mesh-set rule assumption broken", file=sys.stderr)
                return 1
            if rec["partof_meshes"]:
                partof_redundant += 1
        elif rec["partof_meshes"]:
            tree, meshes = "partof", rec["partof_meshes"]
        else:
            skipped.append(rid)
            continue

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
            bmn, bmx, nv, nf = stream_counts_bbox(os.path.join(ROOT, m["path"]))
            if nv != m["vertices"] or nf != m["faces"]:
                print(f"COUNT MISMATCH {rid} {m['fj']}: streamed {nv} v / {nf} f "
                      f"!= M4 {m['vertices']} v / {m['faces']} f", file=sys.stderr)
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
            "name": rec["name"],
            "side": rec["side"],
            "representation": rec["representation"],
            "concept_ids": rec["concept_ids"],
            "concept_names": rec["concept_names"],
            "source_tree": tree,
            "meshes": out_meshes,
            "totals": {"files": len(out_meshes), "vertices": tv, "faces": tf},
            "m4_totals_carried": rec["totals"],
            "bbox_canonical_cm": {"min": mn, "max": mx},
        })

    out = {
        "meta": {
            "title": "ANATOMICA assembled muscular layer — Milestone 6",
            "generated_by": "tools/assemble_muscles.py",
            "input": "data/muscular/muscle-geometry.json (Milestone 4)",
            "canonical_frame": "centimetres; x+ = subject right, y+ = up, z+ = anterior (Phase-1 convention)",
            "transform": "app = (-bp_x, bp_z, -bp_y) * 0.1; signed permutation, determinant -1 vs canonical handedness",
            "winding": "triangle winding flips under this transform; shells must flip index winding (or culling/normals) at import",
            "mesh_set_rule": "IS-A composition primary; PART-OF only where IS-A is empty; byte-identical duplicates within a composition de-duplicated",
            "partof_note": (f"{partof_redundant} records also list PART-OF meshes; in every case the "
                            "PART-OF fj set is a subset of the record's IS-A fj set (verified per "
                            "record at assembly), so PART-OF contributes no geometry"),
            "flagged_unknowns": [
                "Register_sketch unknown 1: a single global frame for soft tissues was assumed, not proven, at Milestone 3. This assembly applies the skeletal transform unchanged; layer coherence is measured by tools/muscle_assembly_check.py.",
                "Ground placement (canonical y=0 at sole) and AP origin registration are NOT applied — frame conversion only, exactly as Milestone 3.",
                "Per-part pose registration is not performed; boxes are in the source pose.",
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
