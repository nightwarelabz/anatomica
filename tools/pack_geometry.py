#!/usr/bin/env python3
"""ANATOMICA geometry packer — Milestone 16 (successor to
tools/pack_web_geometry.py, which packed the skeletal and muscular
layers for Milestone 6 and remains in the tree as that milestone's
record; this tool supersedes it and packs ALL eleven Body Model
layers).

Outputs under web/data/:
  <system>.bin for each of the 11 systems — one merged static buffer
  set per layer, ANW1 v2 layout identical to Milestone 6:
      header 128 B: magic 'ANW1', u32 version=2, u32 vertexCount,
      u32 indexCount, u32 recordCount, u32 edgeIndexCount,
      u64 offsets (positions, normals, recordIds, indices, edges).
      positions: float32 x3 per vertex, canonical cm frame
      normals:   int8 x4 per vertex (snorm xyz, pad 0), smooth,
                 computed here from the converted faces
      recordIds: uint32 per vertex (record slot within the layer)
      indices:   uint32 x3 per face, winding flipped (the frame
                 conversion has determinant -1)
      edges:     uint32 x2 per unique undirected edge of the layer
      => one draw call per layer in the shells when unfiltered.
  records.json — every record the shells list: all 1,552 Body Model
      inventory records (1,545 with geometry; the 7 geometry-less
      bones listed and marked), the 70 clinical records that link no
      inventory record (clinical-only, listed and marked), and the
      8 cardiovascular variant records (listed and marked) — 1,630
      listed records, plus the full clinical map (361 clinical
      records + 8 variants) keyed by id.
  manifest.json — per-layer counts/sizes/ranges actually written,
      plus each layer's pick bit, display label and colour (the
      manifest is the single source of truth for those; the web
      viewer's literals are asserted against it by
      tools/verify_web.js check W1/W6).

Source OBJ streams are converted with the canonical transform
app = (-bp_x, bp_z, -bp_y) * 0.1. Streamed vertex/face counts are
asserted against the assembled JSONs for every file (an assertion
failure aborts the pack). Cross-midline vertex fractions for sided
records are measured during packing (canonical x on the
anatomically wrong side of x=0) and stored in records.json and the
manifest ranges.

Sections are streamed to per-layer temp files and concatenated, and
the unique-edge set is built in 256 key-ordered buckets, so peak
memory stays bounded (the Milestone-6 tool held whole layers in
RAM). Stdlib only.

Usage: python3 tools/pack_geometry.py [--check]
  --check re-derives every manifest range from the assembled JSONs
  and the pack headers and compares (no packing).
"""
import gc
import json
import math
import os
import struct
import sys
from array import array

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
WEB_DATA = os.path.join(ROOT, "web", "data")
TMPDIR = os.path.join(WEB_DATA, ".packtmp")
APP_DATA = os.path.join(ROOT, "..", "anatomica-app", "data")

# key, label, pick bit, colour [r,g,b], assembled JSON, clinical JSON (or None),
# milestone that authored the system's clinical tranche (for notes)
LAYERS = [
    ("skeletal", "Skeletal", 1, [0.78, 0.72, 0.60],
     "data/skeletal/skeleton-assembled.json", None, None),
    ("muscular", "Muscular", 2, [0.55, 0.22, 0.19],
     "data/muscular/muscles-assembled.json", "data/muscular/muscles.json", 4),
    ("cardiovascular", "Cardiovascular", 3, [0.80, 0.16, 0.28],
     "data/cardiovascular/cv-assembled.json", "data/cardiovascular/cardiovascular.json", 5),
    ("nervous", "Nervous", 4, [0.90, 0.78, 0.35],
     "data/nervous/nervous-assembled.json", "data/nervous/nervous.json", 9),
    ("respiratory", "Respiratory", 5, [0.45, 0.65, 0.85],
     "data/respiratory/respiratory-assembled.json", "data/respiratory/respiratory.json", 10),
    ("digestive", "Digestive", 6, [0.75, 0.50, 0.30],
     "data/digestive/digestive-assembled.json", "data/digestive/digestive.json", 11),
    ("urinary", "Urinary", 7, [0.85, 0.55, 0.15],
     "data/urinary/urinary-assembled.json", "data/urinary/urinary.json", 12),
    ("lymphatic", "Lymphatic", 8, [0.35, 0.70, 0.35],
     "data/lymphatic/lymphatic-assembled.json", "data/lymphatic/lymphatic.json", 13),
    ("endocrine", "Endocrine", 9, [0.60, 0.40, 0.75],
     "data/endocrine/endocrine-assembled.json", "data/endocrine/endocrine.json", 13),
    ("reproductive", "Reproductive", 10, [0.80, 0.45, 0.60],
     "data/reproductive/reproductive-assembled.json", "data/reproductive/reproductive.json", 14),
    ("integumentary", "Integumentary", 11, [0.88, 0.62, 0.45],
     "data/integumentary/integumentary-assembled.json", "data/integumentary/integumentary.json", 15),
]
LAYER_KEYS = [l[0] for l in LAYERS]


def convert(x, y, z):
    return (-x * 0.1, z * 0.1, -y * 0.1)


def parse_obj(path):
    """(positions array('d') converted flat, faces array('I') flipped
    0-based, normals bytearray snorm8x4) for one OBJ file."""
    pos = array("d")
    faces = array("I")
    with open(path, "rb") as fh:
        for line in fh:
            if line.startswith(b"v "):
                p = line.split()
                pos.extend(convert(float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith(b"f "):
                idx = []
                nv = len(pos) // 3
                for tok in line.split()[1:]:
                    i = int(tok.split(b"/")[0])
                    if i < 0:
                        i = nv + i + 1
                    idx.append(i - 1)
                idx.reverse()
                for k in range(1, len(idx) - 1):
                    faces.extend((idx[0], idx[k], idx[k + 1]))
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
    nrm = bytearray()
    for i in range(n):
        x, y, z = acc[3 * i], acc[3 * i + 1], acc[3 * i + 2]
        ln = math.sqrt(x * x + y * y + z * z)
        if ln == 0.0:
            nrm.extend((0, 0, 127, 0))
        else:
            for v in (x, y, z):
                q = max(-127, min(127, round(127 * v / ln)))
                nrm.append(q & 0xFF)
            nrm.append(0)
    return pos, faces, bytes(nrm)


def pack_layer(key, assembled):
    os.makedirs(TMPDIR, exist_ok=True)
    sec = {name: open(os.path.join(TMPDIR, f"{key}.{name}"), "wb")
           for name in ("pos", "nrm", "ids", "idx", "edg")}
    cache = {}
    buckets = [array("Q") for _ in range(256)]
    ranges = []
    v_total = i_total = 0
    mesh_files = 0
    for slot, rec in enumerate(assembled["records"]):
        v_start, i_start = v_total, i_total
        side = rec.get("side")
        wrong = total = 0
        for m in rec["meshes"]:
            path = os.path.join(ROOT, m["path"])
            if m["path"] not in cache:
                cache[m["path"]] = parse_obj(path)
            pos, faces, nrm = cache[m["path"]]
            nv, nf = len(pos) // 3, len(faces) // 3
            assert nv == m["vertices"] and nf == m["faces"], \
                f"COUNT MISMATCH {key} {rec['record_id']} {m['path']}: {nv}/{nf} vs {m}"
            mesh_files += 1
            array("f", pos).tofile(sec["pos"])
            sec["nrm"].write(nrm)
            buf = array("I")
            buf.frombytes(struct.pack("<I", slot) * nv)
            buf.tofile(sec["ids"])
            gidx = array("I", (v_total + f for f in faces))
            gidx.tofile(sec["idx"])
            for t in range(0, len(faces), 3):
                a, b, c = v_total + faces[t], v_total + faces[t + 1], v_total + faces[t + 2]
                for p, q in ((a, b), (b, c), (c, a)):
                    k = (p << 32) | q if p < q else (q << 32) | p
                    buckets[k >> 56].append(k)
            if side in ("left", "right"):
                for vi in range(nv):
                    cx = pos[3 * vi]
                    total += 1
                    if (side == "left" and cx > 0) or (side == "right" and cx < 0):
                        wrong += 1
            v_total += nv
            i_total += len(faces)
        ranges.append({
            "slot": slot, "record_id": rec["record_id"],
            "vertex_start": v_start, "vertex_count": v_total - v_start,
            "index_start": i_start, "index_count": i_total - i_start,
            "mesh_files": len(rec["meshes"]),
            "cross_midline_fraction": (wrong / total) if side in ("left", "right") and total else None,
        })
    del cache
    edge_count = 0
    for b in buckets:
        if not b:
            continue
        prev = -1
        for k in sorted(b.tolist()):
            if k == prev:
                continue
            prev = k
            array("I", (k >> 32, k & 0xFFFFFFFF)).tofile(sec["edg"])
            edge_count += 1
    del buckets
    for fh in sec.values():
        fh.close()
    sizes = {name: os.path.getsize(os.path.join(TMPDIR, f"{key}.{name}"))
             for name in sec}
    offsets = {}
    off = 128
    for name, field in (("pos", "positions"), ("nrm", "normals"),
                        ("ids", "record_ids"), ("idx", "indices"), ("edg", "edges")):
        offsets[field] = off
        off += sizes[name]
    out_path = os.path.join(WEB_DATA, f"{key}.bin")
    with open(out_path, "wb") as out:
        out.write(bytes(128))
        for name in ("pos", "nrm", "ids", "idx", "edg"):
            with open(os.path.join(TMPDIR, f"{key}.{name}"), "rb") as fh:
                while True:
                    chunk = fh.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
        total_size = out.tell()
        out.seek(0)
        out.write(struct.pack("<4sIIIIIQQQQQ", b"ANW1", 2, v_total, i_total,
                              len(ranges), edge_count * 2,
                              offsets["positions"], offsets["normals"],
                              offsets["record_ids"], offsets["indices"],
                              offsets["edges"]))
    for name in sec:
        os.remove(os.path.join(TMPDIR, f"{key}.{name}"))
    gc.collect()
    return {
        "file": f"{key}.bin", "bytes": total_size, "vertices": v_total,
        "indices": i_total, "faces": i_total // 3, "edges": edge_count,
        "edge_indices": edge_count * 2, "records": len(ranges),
        "mesh_files": mesh_files, "ranges": ranges,
    }


def load_json(rel):
    with open(os.path.join(ROOT, rel)) as fh:
        return json.load(fh)


def region_of(rec):
    st = rec.get("subtree")
    if not st:
        return None
    for suf in ("-isa", "-partof"):
        if st.endswith(suf):
            return st[:-len(suf)]
    return st


def clinical_links(clin_file):
    """clinical id -> record; inventory id -> [clinical ids];
    clinical records with no inventory link; variants.
    The Milestone-4 tranche keys its records 'record_id'; the
    Milestone-5+ tranches key theirs 'id' — both are the record's
    canonical id, resolved here."""
    by_id, inv_links, clin_only, variants = {}, {}, [], []
    if clin_file is None:
        return by_id, inv_links, clin_only, variants
    clin = load_json(clin_file)
    for c in clin["records"]:
        cid = c.get("record_id") or c.get("id")
        by_id[cid] = c
        g = c.get("geometry_record_ids")
        if g is None and isinstance(c.get("geometry"), dict):
            g = c["geometry"].get("inventory_record_ids")
        if not g:
            clin_only.append((cid, c))
        for rid in g or []:
            inv_links.setdefault(rid, []).append(cid)
    for v in clin.get("variants", []):
        by_id[v["id"]] = v
        variants.append(v)
    return by_id, inv_links, clin_only, variants


def main():
    check_only = "--check" in sys.argv
    assembled = {}
    for key, _label, _bit, _color, asm_rel, _clin, _ms in LAYERS:
        assembled[key] = load_json(asm_rel)

    if check_only:
        manifest = json.load(open(os.path.join(WEB_DATA, "manifest.json")))
        bad = 0
        for key in LAYER_KEYS:
            lay = manifest["layers"][key]
            with open(os.path.join(WEB_DATA, lay["file"]), "rb") as fh:
                hdr = fh.read(128)
            magic, ver, vc, ic, rc, ec = struct.unpack("<4sIIIII", hdr[:24])
            offs = struct.unpack("<5Q", hdr[24:64])
            assert magic == b"ANW1" and ver == 2
            exp_v = sum(r["totals"]["vertices"] for r in assembled[key]["records"])
            exp_i = sum(r["totals"]["faces"] * 3 for r in assembled[key]["records"])
            ok = (vc, ic, rc) == (exp_v, exp_i, len(assembled[key]["records"])) \
                and lay["vertices"] == vc and lay["indices"] == ic \
                and offs[0] == 128 and offs[1] == 128 + vc * 12 \
                and offs[2] == offs[1] + vc * 4 and offs[3] == offs[2] + vc * 4 \
                and offs[4] == offs[3] + ic * 4 \
                and lay["bytes"] == offs[4] + ec * 4
            print(f"{'PASS' if ok else 'FAIL'} check {key}: header {vc} v / {ic} i / "
                  f"{rc} records / {ec} edge indices; manifest bytes {lay['bytes']}")
            bad += 0 if ok else 1
        print("PACK CHECK:", "ALL PASS" if not bad else f"{bad} FAILURES")
        return 1 if bad else 0

    manifest_layers = {}
    ranges_by_layer = {}
    for key, label, bit, color, _a, _c, _m in LAYERS:
        info = pack_layer(key, assembled[key])
        info["pick_bit"] = bit
        info["label"] = label
        info["color"] = color
        manifest_layers[key] = info
        ranges_by_layer[key] = {r["record_id"]: r for r in info["ranges"]}
        print(f"packed {key}: {info['vertices']} v, {info['faces']} f, "
              f"{info['edges']} edges, {info['bytes']} B")

    # ---- records.json ----
    records = []
    clinical_map = {}
    counts = {}
    for key, _label, _bit, _color, _a, clin_rel, ms in LAYERS:
        by_id, inv_links, clin_only, variants = clinical_links(clin_rel)
        for cid, c in by_id.items():
            c2 = dict(c)
            c2["layer"] = key
            clinical_map[cid] = c2
        asm = assembled[key]
        rng = ranges_by_layer[key]
        n_listed = 0
        if key == "skeletal":
            raw = open(os.path.join(APP_DATA, "skeleton.js")).read()
            skel = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
            asm_by_id = {r["record_id"]: r for r in asm["records"]}
            for bone in skel["bones"]:
                e = dict(bone)
                e["layer"] = "skeletal"
                a = asm_by_id.get(bone["id"])
                e["record_kind"] = "inventory"
                e["region"] = bone.get("region")
                e["clinical_ids"] = []
                if a:
                    r = rng[bone["id"]]
                    e["has_geometry"] = True
                    e["slot"] = r["slot"]
                    e["bbox_canonical_cm"] = a["bbox_canonical_cm"]
                    e["cross_midline_fraction"] = r["cross_midline_fraction"]
                else:
                    e["has_geometry"] = False
                    e["slot"] = None
                    e["bbox_canonical_cm"] = None
                    e["cross_midline_fraction"] = None
                    e["geometry_note"] = ("no FMA concept exists in the BodyParts3D 4.0 "
                                          "release for this bone (Milestone 2/3 gap analysis)")
                records.append(e)
                n_listed += 1
        else:
            muscle_inv = None
            if key == "muscular":
                muscle_inv = {x["record_id"]: x for x in
                              load_json("data/muscular/muscle-geometry.json")["records"]}
            for rec in asm["records"]:
                r = rng[rec["record_id"]]
                e = {"layer": key, "id": rec["record_id"], "name": rec["name"],
                     "side": rec.get("side"), "representation": rec.get("representation")}
                if key == "muscular":
                    g = muscle_inv[rec["record_id"]]
                    e["region_group"] = g.get("region_group")
                    e["group_path"] = g.get("group_path")
                    e["region"] = g.get("region_group")
                else:
                    e["subtree"] = rec.get("subtree")
                    e["group_path"] = rec.get("group_path")
                    e["region"] = region_of(rec)
                e["concept_ids"] = rec.get("concept_ids")
                e["concept_names"] = rec.get("concept_names")
                for extra in ("sex_line", "line"):
                    if rec.get(extra) is not None:
                        e[extra] = rec[extra]
                e["record_kind"] = "inventory"
                e["has_geometry"] = True
                e["slot"] = r["slot"]
                e["bbox_canonical_cm"] = rec["bbox_canonical_cm"]
                e["cross_midline_fraction"] = r["cross_midline_fraction"]
                e["clinical_ids"] = inv_links.get(rec["record_id"], [])
                records.append(e)
                n_listed += 1
            for cid, c in clin_only:
                e = {"layer": key, "id": cid, "name": c.get("name"),
                     "side": None, "representation": None,
                     "record_kind": "clinical-only", "has_geometry": False,
                     "slot": None, "bbox_canonical_cm": None,
                     "cross_midline_fraction": None,
                     "clinical_ids": [cid],
                     "region": c.get("region") or c.get("region_group") or c.get("group"),
                     "geometry_note": ("clinical record with no linked inventory geometry "
                                       f"in the BodyParts3D census (Milestone {ms} gap)")}
                if key == "muscular":
                    e["geometry_note"] = ("clinical record with no geometry: no inventory "
                                          "record resolved in the BodyParts3D tables "
                                          "(Milestone 4 gap)")
                records.append(e)
                n_listed += 1
            for v in variants:
                e = {"layer": key, "id": v["id"], "name": v.get("name"),
                     "side": None, "representation": None,
                     "record_kind": "variant", "has_geometry": False,
                     "slot": None, "bbox_canonical_cm": None,
                     "cross_midline_fraction": None,
                     "clinical_ids": [v["id"]], "region": None,
                     "geometry_note": v.get("unmodeled_note") or
                     "anatomical variant — prevalence cited in the clinical record; "
                     "not separately modeled in geometry"}
                records.append(e)
                n_listed += 1
        counts[key] = n_listed

    records_doc = {
        "meta": {"title": "ANATOMICA shell records — Milestone 16 (Body Model v1, all systems)",
                 "listed_records": len(records),
                 "per_system_listed": counts,
                 "clinical_records": len(clinical_map)},
        "records": records,
        "clinical": clinical_map,
    }
    with open(os.path.join(WEB_DATA, "records.json"), "w") as fh:
        json.dump(records_doc, fh, indent=1)

    manifest = {
        "title": "ANATOMICA shell geometry manifest — Milestone 16",
        "generated_by": "tools/pack_geometry.py",
        "canonical_frame": "centimetres; x+ = subject right, y+ = up, z+ = anterior",
        "draw_strategy": "one merged static buffer set per layer (positions float32, "
                         "normals int8 snorm, per-vertex record slot uint32, indices "
                         "uint32, unique-edge index buffer for wireframe); one draw "
                         "call per layer when no region filter is active (plus one "
                         "LINES draw per layer with wireframe on), per-record range "
                         "draws when filtered",
        "layer_order": LAYER_KEYS,
        "layers": manifest_layers,
    }
    with open(os.path.join(WEB_DATA, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    for stale in ("skeleton.bin", "muscles.bin"):
        p = os.path.join(WEB_DATA, stale)
        if os.path.exists(p):
            os.remove(p)
            print(f"removed stale Milestone-6 pack {stale}")
    if os.path.isdir(TMPDIR) and not os.listdir(TMPDIR):
        os.rmdir(TMPDIR)
    tot_f = sum(l["faces"] for l in manifest_layers.values())
    tot_b = sum(l["bytes"] for l in manifest_layers.values())
    print(f"records.json: {len(records)} listed records, {len(clinical_map)} clinical entries")
    print(f"TOTAL: {tot_f} faces across 11 packs, {tot_b} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
