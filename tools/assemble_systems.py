#!/usr/bin/env python3
"""ANATOMICA generalized assembly — Milestone 16.

Extends the Milestone-3/6 assembly step to the nine system modules
built after the shells (Milestones 5, 9-15). The skeletal and muscular
assemblies already exist and are verified (tools/assemble_skeleton.py,
tools/assemble_muscles.py); this tool covers the remaining systems and
applies the identical conversion and mesh-set rule:

    app_x = -bp_x * 0.1    (subject right, cm)
    app_y =  bp_z * 0.1    (up, cm)
    app_z = -bp_y * 0.1    (anterior, cm)
(tools/register_sketch.md; signed permutation x 0.1, determinant -1 —
triangle winding flips at import, recorded in each output's meta.)

Mesh-set rule (design 03, same as Milestones 3 and 6): the record's
IS-A composition is primary; its PART-OF composition is used only
where IS-A is empty (the sternum pattern — here: the heart, the
brain, the lungs, the liver and the other organ composites that
BodyParts3D defines by composition only). Byte-identical duplicate
files inside one composition are de-duplicated by geometry-stream
digest and reported.

One measured difference from the muscular module is recorded, not
smoothed over: in Milestone 4 every record's PART-OF fj set was a
subset of its IS-A set, so PART-OF contributed nothing. In these
systems the PART-OF lists of whole-concept records are descendant
rollups (a named artery's PART-OF composition includes its branches'
meshes — geometry that belongs to other records). Under the mesh-set
rule those rollups are not the record's own geometry and are not
assembled into it; the assembler counts and lists every such record
in the output meta ("partof_rollup_records") instead of asserting
the muscular subset property.

Canonical-frame bounding boxes are computed by streaming and
transforming every vertex of every distinct mesh file (no header
values, no stored source bboxes trusted). Streamed vertex AND face
counts are asserted against the module geometry JSON for every mesh
entry; a per-run cache streams each distinct file once and the
assertion is applied per entry against the cached measurement.

Ground placement and AP origin registration are NOT applied (frame
conversion only), exactly as in Milestones 3 and 6 — the carried
unknowns are restated in each output's meta.

Stdlib only.
"""
import hashlib
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# (system key, geometry file, assembled file, source milestone)
SYSTEMS = [
    ("cardiovascular", "data/cardiovascular/cv-geometry.json",
     "data/cardiovascular/cv-assembled.json", "Milestone 5"),
    ("nervous", "data/nervous/nervous-geometry.json",
     "data/nervous/nervous-assembled.json", "Milestone 9"),
    ("respiratory", "data/respiratory/respiratory-geometry.json",
     "data/respiratory/respiratory-assembled.json", "Milestone 10"),
    ("digestive", "data/digestive/digestive-geometry.json",
     "data/digestive/digestive-assembled.json", "Milestone 11"),
    ("urinary", "data/urinary/urinary-geometry.json",
     "data/urinary/urinary-assembled.json", "Milestone 12"),
    ("lymphatic", "data/lymphatic/lymphatic-geometry.json",
     "data/lymphatic/lymphatic-assembled.json", "Milestone 13"),
    ("endocrine", "data/endocrine/endocrine-geometry.json",
     "data/endocrine/endocrine-assembled.json", "Milestone 13"),
    ("reproductive", "data/reproductive/reproductive-geometry.json",
     "data/reproductive/reproductive-assembled.json", "Milestone 14"),
    ("integumentary", "data/integumentary/integumentary-geometry.json",
     "data/integumentary/integumentary-assembled.json", "Milestone 15"),
]


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
    """Hash of the geometry stream only (v/vt/vn/f lines) — the
    Milestone-3 rule (catches content-identical duplicates whose
    header File IDs differ)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for line in f:
            if line[:2] in (b"v ", b"vt", b"vn", b"f "):
                h.update(line)
    return h.hexdigest()


def assemble_system(key, geom_rel, out_rel, milestone, stream_cache, digest_cache):
    with open(os.path.join(ROOT, geom_rel)) as f:
        geom = json.load(f)

    records = []
    skipped = []
    dedupes = []
    rollup_records = []
    partof_sourced = 0
    union_min = [float("inf")] * 3
    union_max = [float("-inf")] * 3

    for rec in geom["records"]:
        rid = rec["record_id"]
        isa = rec.get("isa_meshes") or []
        partof = rec.get("partof_meshes") or []
        if isa:
            tree, meshes = "isa", isa
            extra = {m["fj"] for m in partof} - {m["fj"] for m in isa}
            if extra:
                rollup_records.append({"record_id": rid,
                                       "partof_files_beyond_isa": len(extra)})
        elif partof:
            tree, meshes = "partof", partof
            partof_sourced += 1
        else:
            skipped.append(rid)
            continue

        seen = {}
        kept = []
        for m in meshes:
            path = os.path.join(ROOT, m["path"])
            if path not in digest_cache:
                digest_cache[path] = geometry_digest(path)
            digest = digest_cache[path]
            if digest in seen:
                dedupes.append({"record_id": rid, "kept": seen[digest],
                                "dropped": m["fj"]})
                continue
            seen[digest] = m["fj"]
            kept.append(m)

        mn = [float("inf")] * 3
        mx = [float("-inf")] * 3
        out_meshes = []
        tv = tf = 0
        for m in kept:
            path = os.path.join(ROOT, m["path"])
            if path not in stream_cache:
                stream_cache[path] = stream_counts_bbox(path)
            bmn, bmx, nv, nf = stream_cache[path]
            if nv != m["vertices"] or nf != m["faces"]:
                print(f"COUNT MISMATCH {key} {rid} {m['fj']}: streamed "
                      f"{nv} v / {nf} f != geometry JSON "
                      f"{m['vertices']} v / {m['faces']} f", file=sys.stderr)
                return None
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

        out_rec = {
            "record_id": rid,
            "name": rec.get("name"),
            "side": rec.get("side"),
            "representation": rec.get("representation"),
            "concept_ids": rec.get("concept_ids"),
            "concept_names": rec.get("concept_names"),
            "source_tree": tree,
            "meshes": out_meshes,
            "totals": {"files": len(out_meshes), "vertices": tv, "faces": tf},
            "source_totals": rec.get("totals"),
            "bbox_canonical_cm": {"min": mn, "max": mx},
        }
        for opt in ("sex_line", "line"):
            if rec.get(opt) is not None:
                out_rec[opt] = rec[opt]
        records.append(out_rec)

    out = {
        "meta": {
            "title": f"ANATOMICA assembled {key} layer — Milestone 16",
            "generated_by": "tools/assemble_systems.py",
            "input": f"{geom_rel} ({milestone})",
            "canonical_frame": "centimetres; x+ = subject right, y+ = up, z+ = anterior (Phase-1 convention)",
            "transform": "app = (-bp_x, bp_z, -bp_y) * 0.1; signed permutation, determinant -1 vs canonical handedness",
            "winding": "triangle winding flips under this transform; shells must flip index winding (or culling/normals) at import",
            "mesh_set_rule": "IS-A composition primary; PART-OF only where IS-A is empty; byte-identical duplicates within a composition de-duplicated",
            "partof_rollup_records": rollup_records,
            "partof_rollup_note": (
                f"{len(rollup_records)} records list PART-OF files beyond their IS-A "
                "composition. In these modules the PART-OF lists of whole-concept "
                "records are descendant rollups (branches' meshes belonging to other "
                "records), not the record's own geometry; under the mesh-set rule "
                "they are not assembled into the record. (In the muscular module "
                "the PART-OF set was a subset of IS-A for every record — verified "
                "at Milestone 6; that property does not hold here and is not "
                "asserted.)"),
            "records_sourced_from_partof": partof_sourced,
            "flagged_unknowns": [
                "Register_sketch unknown 1: a single global frame for all concepts was assumed at Milestone 3 for soft tissues and measured coherent for the muscular layer at Milestone 6. This assembly applies the skeletal transform unchanged to every system; per-layer coherence against the skeletal envelope is measured by tools/assembly_check_all.py, not assumed here.",
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
    out_path = os.path.join(ROOT, out_rel)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=1, sort_keys=False)
    span = [union_max[i] - union_min[i] for i in range(3)]
    print(f"{key}: assembled {len(records)} records "
          f"({partof_sourced} from PART-OF, {len(rollup_records)} with PART-OF "
          f"rollups set aside); skipped (no geometry): {skipped}")
    print(f"  deduped: {dedupes}")
    print(f"  union min {union_min} max {union_max}")
    print(f"  span cm: width(x)={span[0]:.3f} height(y)={span[1]:.3f} depth(z)={span[2]:.3f}")
    print(f"  wrote {out_path}")
    return out


def main():
    only = sys.argv[1:] or None
    stream_cache = {}
    digest_cache = {}
    for key, geom_rel, out_rel, milestone in SYSTEMS:
        if only and key not in only:
            continue
        if assemble_system(key, geom_rel, out_rel, milestone,
                           stream_cache, digest_cache) is None:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
