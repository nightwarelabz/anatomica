#!/usr/bin/env python3
"""ANATOMICA web-shell geometry packer — Milestone 6.

Packs the assembled Body Model geometry into the web viewer's data
files under web/data/:

  skeleton.bin / muscles.bin — one merged static buffer set per layer:
      header 128 B: magic 'ANW1', u32 version=2, u32 vertexCount,
      u32 indexCount, u32 recordCount, u32 edgeIndexCount,
      u64 offsets (positions, normals, recordIds, indices, edges).
      positions: float32 x3 per vertex, canonical cm frame
      normals:   int8 x4 per vertex (snorm xyz, pad 0), smooth,
                 computed here from the converted faces
      recordIds: uint32 per vertex (record slot within the layer)
      indices:   uint32 x3 per face, winding flipped (the frame
                 conversion has determinant -1; see register_sketch)
      edges:     uint32 x2 per unique undirected edge of the layer
                 (for the wireframe overlay: one LINES draw per layer)
      => one draw call per layer in the viewer when unfiltered.
  records.json  — every record the viewer lists: all 206 verified bone
      records (7 without geometry), all 359 muscular inventory records
      (241 linked to a clinical record, 118 inventory-only), and the 1
      clinical-only muscle record (multifidus, geometry null in M4).
  manifest.json — per-layer counts/sizes/ranges actually written.

Source OBJ streams are converted with the register_sketch transform
app = (-bp_x, bp_z, -bp_y) * 0.1. Streamed vertex/face counts are
asserted against the assembled JSONs for every file. Cross-midline
vertex fractions for sided records are measured during packing
(canonical x on the anatomically wrong side of x=0) and stored in
records.json — this is the quantity behind the K4c findings in
tools/muscle_assembly_check.py.

Stdlib only.
"""
import json
import math
import os
import struct
import sys
from array import array

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
WEB_DATA = os.path.join(ROOT, "web", "data")


def convert(x, y, z):
    return (-x * 0.1, z * 0.1, -y * 0.1)


def parse_obj(path):
    """Return (positions [converted, flat float list], faces [flat int list,
    winding-flipped, 0-based]). Polygons are fan-triangulated after
    reversal (equivalent to flipping each triangle's winding)."""
    pos = []
    faces = []
    with open(path, "rb") as fh:
        for line in fh:
            if line.startswith(b"v "):
                p = line.split()
                x, y, z = convert(float(p[1]), float(p[2]), float(p[3]))
                pos.extend((x, y, z))
            elif line.startswith(b"f "):
                idx = []
                for tok in line.split()[1:]:
                    i = int(tok.split(b"/")[0])
                    if i < 0:
                        i = len(pos) // 3 + i + 1
                    idx.append(i - 1)
                idx.reverse()
                for k in range(1, len(idx) - 1):
                    faces.extend((idx[0], idx[k], idx[k + 1]))
    return pos, faces


def compute_normals(pos, faces):
    n = len(pos) // 3
    acc = array("d", bytes(8 * 3 * n))
    for t in range(0, len(faces), 3):
        a, b, c = faces[t], faces[t + 1], faces[t + 2]
        ax, ay, az = pos[3 * a], pos[3 * a + 1], pos[3 * a + 2]
        ux, uy, uz = pos[3 * b] - ax, pos[3 * b + 1] - ay, pos[3 * b + 2] - az
        vx, vy, vz = pos[3 * c] - ax, pos[3 * c + 1] - ay, pos[3 * c + 2] - az
        cx, cy, cz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        for v in (a, b, c):
            acc[3 * v] += cx
            acc[3 * v + 1] += cy
            acc[3 * v + 2] += cz
    out = bytearray()
    for i in range(n):
        x, y, z = acc[3 * i], acc[3 * i + 1], acc[3 * i + 2]
        ln = math.sqrt(x * x + y * y + z * z)
        if ln == 0.0:
            out.extend((0, 0, 127, 0))
        else:
            for v in (x, y, z):
                q = max(-127, min(127, round(127 * v / ln)))
                out.append(q & 0xFF)  # two's complement; read back as signed byte
            out.append(0)
    return out


def pack_layer(layer_name, assembled, side_of):
    """side_of(record) -> 'left'|'right'|'midline'|other for the
    cross-midline measurement."""
    pos_all = array("f")
    nrm_all = bytearray()
    ids_all = array("I")
    idx_all = array("I")
    edge_set = set()
    edge_all = array("I")
    ranges = []
    cache = {}
    total_files = 0
    for slot, rec in enumerate(assembled["records"]):
        v_start = len(pos_all) // 3
        i_start = len(idx_all)
        side = side_of(rec)
        wrong = total = 0
        for m in rec["meshes"]:
            path = os.path.join(ROOT, m["path"])
            if m["path"] not in cache:
                cache[m["path"]] = parse_obj(path)
            pos, faces = cache[m["path"]]
            nv, nf = len(pos) // 3, len(faces) // 3
            if nv != m["vertices"] or nf != m["faces"]:
                print(f"COUNT MISMATCH {rec['record_id']} {m['fj']}: parsed {nv} v / {nf} f "
                      f"!= assembled {m['vertices']} v / {m['faces']} f", file=sys.stderr)
                sys.exit(1)
            nrm = compute_normals(pos, faces)
            base = len(pos_all) // 3
            pos_all.extend(array("f", pos))
            nrm_all.extend(nrm)
            ids_all.extend(array("I", [slot]) * nv)
            idx_all.extend(array("I", [base + i for i in faces]))
            for t in range(0, len(faces), 3):
                a, b, c = faces[t], faces[t + 1], faces[t + 2]
                for u, v in ((a, b), (b, c), (c, a)):
                    key = (base + u, base + v) if u < v else (base + v, base + u)
                    if key not in edge_set:
                        edge_set.add(key)
                        edge_all.extend(array("I", key))
            total_files += 1
            if side in ("left", "right"):
                for i in range(nv):
                    x = pos[3 * i]
                    total += 1
                    if (side == "left" and x > 0) or (side == "right" and x < 0):
                        wrong += 1
        ranges.append({
            "slot": slot,
            "record_id": rec["record_id"],
            "vertex_start": v_start, "vertex_count": len(pos_all) // 3 - v_start,
            "index_start": i_start, "index_count": len(idx_all) - i_start,
            "mesh_files": len(rec["meshes"]),
            "cross_midline_fraction": (wrong / total) if side in ("left", "right") and total else None,
        })
        if (slot + 1) % 100 == 0:
            print(f"  {layer_name}: {slot + 1}/{len(assembled['records'])} records", file=sys.stderr)

    nv, ni, ne = len(pos_all) // 3, len(idx_all), len(edge_all)
    header = bytearray(128)
    header[0:4] = b"ANW1"
    struct.pack_into("<IIIII", header, 4, 2, nv, ni, len(assembled["records"]), ne)
    off = 128
    offsets = {}
    for name, size in (("positions", nv * 12), ("normals", nv * 4),
                       ("record_ids", nv * 4), ("indices", ni * 4),
                       ("edges", ne * 4)):
        offsets[name] = off
        off += size
    struct.pack_into("<QQQQQ", header, 24, offsets["positions"], offsets["normals"],
                     offsets["record_ids"], offsets["indices"], offsets["edges"])
    out_path = os.path.join(WEB_DATA, layer_name + ".bin")
    with open(out_path, "wb") as fh:
        fh.write(header)
        pos_all.tofile(fh)
        fh.write(nrm_all)
        ids_all.tofile(fh)
        idx_all.tofile(fh)
        edge_all.tofile(fh)
    return {
        "file": layer_name + ".bin",
        "bytes": os.path.getsize(out_path),
        "vertices": nv,
        "indices": ni,
        "faces": ni // 3,
        "edges": ne // 2,
        "edge_indices": ne,
        "records": len(assembled["records"]),
        "mesh_files": total_files,
        "distinct_mesh_paths": len(cache),
        "ranges": ranges,
    }


def main():
    os.makedirs(WEB_DATA, exist_ok=True)

    skel_asm = json.load(open(os.path.join(ROOT, "data", "skeletal", "skeleton-assembled.json")))
    musc_asm = json.load(open(os.path.join(ROOT, "data", "muscular", "muscles-assembled.json")))
    inv = json.load(open(os.path.join(ROOT, "data", "muscular", "muscle-inventory.json")))
    clin = json.load(open(os.path.join(ROOT, "data", "muscular", "muscles.json")))

    raw = open(os.path.join(ROOT, "..", "anatomica-app", "data", "skeleton.js"),
               encoding="utf-8").read()
    bones_js = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
    bone_by_id = {b["id"]: b for b in bones_js["bones"]}

    print("packing skeleton layer...", file=sys.stderr)
    skel = pack_layer("skeleton", skel_asm, lambda r: bone_by_id[r["record_id"]].get("side"))
    print("packing muscle layer...", file=sys.stderr)
    musc = pack_layer("muscles", musc_asm, lambda r: r.get("side"))

    # ---- records.json -------------------------------------------------
    records = []
    skel_range = {r["record_id"]: r for r in skel["ranges"]}
    skel_bbox = {r["record_id"]: r["bbox_canonical_cm"] for r in skel_asm["records"]}
    for b in bones_js["bones"]:
        e = dict(b)
        e["layer"] = "skeleton"
        rng = skel_range.get(b["id"])
        e["has_geometry"] = rng is not None
        e["slot"] = rng["slot"] if rng else None
        e["bbox_canonical_cm"] = skel_bbox.get(b["id"])
        e["cross_midline_fraction"] = rng["cross_midline_fraction"] if rng else None
        if rng is None:
            e["geometry_note"] = ("no geometry: absent from the BodyParts3D 4.0 release "
                                  "(gap analysis, Milestone 3)")
        records.append(e)

    inv_by_id = {r["record_id"]: r for r in inv["records"]}
    clin_by_inv = {}
    for c in clin["records"]:
        g = c.get("geometry")
        if g:
            for iid in g["inventory_record_ids"]:
                clin_by_inv[iid] = c["record_id"]
    clin_by_id = {c["record_id"]: c for c in clin["records"]}
    musc_range = {r["record_id"]: r for r in musc["ranges"]}
    musc_bbox = {r["record_id"]: r["bbox_canonical_cm"] for r in musc_asm["records"]}
    for r in musc_asm["records"]:
        rid = r["record_id"]
        iv = inv_by_id[rid]
        rng = musc_range[rid]
        records.append({
            "layer": "muscle",
            "id": rid,
            "name": r["name"],
            "side": r["side"],
            "representation": r["representation"],
            "region_group": iv.get("region_group"),
            "group_path": iv.get("group_path"),
            "concept_ids": r["concept_ids"],
            "concept_names": r["concept_names"],
            "has_geometry": True,
            "slot": rng["slot"],
            "bbox_canonical_cm": musc_bbox[rid],
            "cross_midline_fraction": rng["cross_midline_fraction"],
            "clinical_id": clin_by_inv.get(rid),
        })
    linked = set(clin_by_inv.values())
    for c in clin["records"]:
        if c["record_id"] not in linked:
            records.append({
                "layer": "muscle",
                "id": c["record_id"],
                "name": c["name"],
                "side": None,
                "representation": None,
                "region_group": None,
                "group_path": None,
                "concept_ids": [],
                "concept_names": [],
                "has_geometry": False,
                "slot": None,
                "bbox_canonical_cm": None,
                "cross_midline_fraction": None,
                "clinical_id": c["record_id"],
                "geometry_note": ("clinical record with no geometry: no inventory record "
                                  "resolved in the BodyParts3D tables (Milestone 4 gap)"),
            })

    clinical = {c["record_id"]: {k: c.get(k) for k in
                                 ("record_id", "name", "ta_name", "region", "subregion",
                                  "origin", "insertion", "actions", "innervation",
                                  "arterial_supply", "sources", "verify", "note",
                                  "sourcing_tier")}
                for c in clin["records"]}

    with open(os.path.join(WEB_DATA, "records.json"), "w") as f:
        json.dump({"meta": {"title": "ANATOMICA web shell records — Milestone 6",
                            "bone_records": len(bones_js["bones"]),
                            "muscle_records": len(musc_asm["records"]),
                            "clinical_only_records": len(clin["records"]) - len(linked)},
                   "records": records, "clinical": clinical}, f, indent=1)

    manifest = {
        "title": "ANATOMICA web shell geometry manifest — Milestone 6",
        "generated_by": "tools/pack_web_geometry.py",
        "canonical_frame": "centimetres; x+ = subject right, y+ = up, z+ = anterior",
        "draw_strategy": ("one merged static buffer set per layer (positions float32, "
                          "normals int8 snorm, per-vertex record slot uint32, indices "
                          "uint32, unique-edge index buffer for wireframe); one draw "
                          "call per layer when no region filter is active (plus one "
                          "LINES draw per layer with wireframe on), per-record range "
                          "draws when filtered"),
        "layers": {"skeleton": skel, "muscles": musc},
    }
    with open(os.path.join(WEB_DATA, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)

    for name, lay in (("skeleton", skel), ("muscles", musc)):
        print(f"{name}: {lay['records']} records, {lay['mesh_files']} mesh files "
              f"({lay['distinct_mesh_paths']} distinct), {lay['vertices']} vertices, "
              f"{lay['faces']} faces, {lay['bytes']} bytes")
    print(f"records.json: {len(records)} listed records "
          f"({sum(1 for r in records if r['layer'] == 'skeleton')} skeleton, "
          f"{sum(1 for r in records if r['layer'] == 'muscle')} muscle)")
    print(f"wrote {WEB_DATA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
