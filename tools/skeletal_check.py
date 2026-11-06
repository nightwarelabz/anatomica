#!/usr/bin/env python3
"""ANATOMICA Milestone 2 — independent skeletal mapping/geometry checker.

Re-verifies the outputs of tools/fma_map.py from the primary sources,
without importing it:

  (a) COVERAGE   all 206 verified skeletal records are present in both
                 data/skeletal/fma-mapping.json and skeleton-geometry.json,
                 with no extra or missing record ids.
  (b) EXISTENCE  every mesh file referenced by skeleton-geometry.json
                 exists on disk.
  (c) CENSUS     the BP3D table counts re-derived here equal the Milestone-1
                 census (tools/census.json): 2,905 ISA concepts, 2,234 ISA
                 mesh files, 1,258 PART-OF mesh files; each record's mesh
                 lists equal the concept's element composition recomputed
                 from the release tables; every referenced file's vertex/
                 face counts are recounted by streaming the file and must
                 equal the stored values; each referenced file's OBJ header
                 Concept ID must be the record's concept or one of its
                 descendants in the corresponding tree.
  (d) ANATOMY    spot rules R1-R8 (documented inline below) that fail if a
                 record maps to a concept whose name contradicts its
                 anatomy, plus R7: the NOT-FOUND set is exactly the seven
                 records whose concepts are provably absent from all six
                 release tables.
  (e) ANOMALIES  non-fatal reports (e.g. duplicate-geometry mesh files
                 within one record's composition).

Exit code 0 iff no FAIL. Stdlib only. Run: python3 tools/skeletal_check.py
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources", "bodyparts3d-4.0")
SKELETON_JS = os.path.expanduser("~/workspace/anatomica-app/data/skeleton.js")
MAP_JSON = os.path.join(ROOT, "data", "skeletal", "fma-mapping.json")
GEO_JSON = os.path.join(ROOT, "data", "skeletal", "skeleton-geometry.json")
CENSUS_JSON = os.path.join(ROOT, "tools", "census.json")

FAILURES = []
NOTES = []


def check(ok, label, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(label)


def note(msg):
    print(f"[NOTE] {msg}")
    NOTES.append(msg)


def read_tsv(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        rows = [ln.rstrip("\n").split("\t") for ln in f if ln.strip()]
    return rows[1:]


def obj_head_and_stats(path):
    """Independent recount: header fields + streamed v/f counts + geom hash."""
    info = {}
    v = f = 0
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for line in fh:
            if line.startswith(b"#"):
                m = re.match(rb"#\s*(File ID|Concept ID)\s*:\s*(\S+)", line)
                if m:
                    info[m.group(1).decode()] = m.group(2).decode()
            elif line[:2] == b"v ":
                v += 1
                h.update(line)
            elif line[:2] == b"f ":
                f += 1
                h.update(line)
    return info, v, f, h.hexdigest()


def descendants(children, root):
    seen, stack = set(), list(children.get(root, []))
    while stack:
        c = stack.pop()
        if c not in seen:
            seen.add(c)
            stack.extend(children.get(c, []))
    return seen


def main():
    src = open(SKELETON_JS, encoding="utf-8").read()
    bones = json.loads(src[src.index("{"):src.rindex("}") + 1])["bones"]
    bone_ids = [b["id"] for b in bones]
    bone_by_id = {b["id"]: b for b in bones}
    mapping = json.load(open(MAP_JSON))
    geometry = json.load(open(GEO_JSON))
    census = json.load(open(CENSUS_JSON))
    maps = {r["record_id"]: r for r in mapping["mappings"]}
    geos = {r["record_id"]: r for r in geometry["records"]}

    print("== (a) coverage ==")
    check(set(maps) == set(bone_ids) and len(maps) == 206,
          "mapping covers exactly the 206 skeletal records",
          f"mapping rows={len(maps)}, dataset records={len(bone_ids)}")
    check(set(geos) == set(bone_ids) and len(geos) == 206,
          "geometry covers exactly the 206 skeletal records")

    print("== (b) existence ==")
    missing = []
    referenced = {}  # path -> (tree, fj)
    for r in geometry["records"]:
        for tree in ("isa_meshes", "partof_meshes"):
            for mm in r[tree]:
                p = os.path.join(ROOT, mm["path"])
                if not os.path.isfile(p):
                    missing.append(mm["path"])
                referenced[mm["path"]] = (tree, mm["fj"])
    check(not missing, "every referenced mesh file exists on disk",
          f"{len(referenced)} distinct paths referenced" +
          (f"; missing: {missing}" if missing else ""))

    print("== (c) census consistency ==")
    isa_rows = read_tsv(os.path.join(SRC, "isa_parts_list_e.txt"))
    po_rows = read_tsv(os.path.join(SRC, "partof_parts_list_e.txt"))
    isa_names = {r[0]: r[2] for r in isa_rows}
    po_names = {r[0]: r[2] for r in po_rows}
    isa_elem, po_elem = {}, {}
    for r in read_tsv(os.path.join(SRC, "isa_element_parts.txt")):
        isa_elem.setdefault(r[0], set()).add(r[2])
    for r in read_tsv(os.path.join(SRC, "partof_element_parts.txt")):
        po_elem.setdefault(r[0], set()).add(r[2])
    isa_children, po_children = {}, {}
    for r in read_tsv(os.path.join(SRC, "isa_inclusion_relation_list.txt")):
        isa_children.setdefault(r[0], []).append(r[2])
    for r in read_tsv(os.path.join(SRC, "partof_inclusion_relation_list.txt")):
        po_children.setdefault(r[0], []).append(r[2])
    n_isa_files = len([x for x in os.listdir(os.path.join(ROOT, "work", "bp3d", "isa_BP3D_4.0_obj_99")) if x.endswith(".obj")])
    n_po_files = len([x for x in os.listdir(os.path.join(ROOT, "work", "bp3d", "partof_BP3D_4.0_obj_99")) if x.endswith(".obj")])
    bp = census["bodyparts3d"]
    check(len(isa_names) == bp["isa_concepts_listed"] == 2905,
          "ISA concept count matches Milestone-1 census", f"{len(isa_names)}")
    check(n_isa_files == bp["isa_mesh_files"] == 2234,
          "ISA mesh file count matches census", f"{n_isa_files}")
    check(n_po_files == bp["partof_mesh_files"] == 1258,
          "PART-OF mesh file count matches census", f"{n_po_files}")

    bad_comp, bad_counts, bad_header = [], [], []
    stats = {}
    for path in referenced:
        stats[path] = obj_head_and_stats(os.path.join(ROOT, path))
    subtree_cache = {}
    for rid, grow in geos.items():
        mrow = maps[rid]
        cid = mrow["fma_id"]
        if cid is None:
            if grow["isa_meshes"] or grow["partof_meshes"]:
                bad_comp.append((rid, "NOT-FOUND record has meshes"))
            continue
        exp_isa = sorted(isa_elem.get(cid, [])) if cid in isa_names else []
        exp_po = sorted(po_elem.get(cid, []))
        got_isa = sorted(mm["fj"] for mm in grow["isa_meshes"])
        got_po = sorted(mm["fj"] for mm in grow["partof_meshes"])
        if exp_isa != got_isa or exp_po != got_po:
            bad_comp.append((rid, f"isa {got_isa} vs table {exp_isa}; partof {got_po} vs table {exp_po}"))
        # totals and per-file counts
        for tree, meshes in (("isa", grow["isa_meshes"]), ("partof", grow["partof_meshes"])):
            t = grow["totals"][tree]
            if (t["files"] != len(meshes) or
                    t["vertices"] != sum(mm["vertices"] for mm in meshes) or
                    t["faces"] != sum(mm["faces"] for mm in meshes)):
                bad_counts.append((rid, f"{tree} totals inconsistent"))
            children = isa_children if tree == "isa" else po_children
            if cid not in subtree_cache.setdefault(tree, {}):
                subtree_cache[tree][cid] = descendants(children, cid) | {cid}
            for mm in meshes:
                info, v, f, _ = stats[os.path.join(ROOT, mm["path"])] if False else stats[mm["path"]]
                if v != mm["vertices"] or f != mm["faces"]:
                    bad_counts.append((rid, f"{mm['fj']} stored {mm['vertices']}/{mm['faces']} recounted {v}/{f}"))
                if info.get("File ID") != mm["fj"]:
                    bad_header.append((rid, f"{mm['fj']} header File ID {info.get('File ID')}"))
                hc = info.get("Concept ID")
                if hc not in subtree_cache[tree][cid]:
                    bad_header.append((rid, f"{mm['fj']} header Concept ID {hc} not in subtree of {cid}"))
    check(not bad_comp, "every record's mesh lists equal the tables' element composition",
          f"{len(bad_comp)} mismatches" + (f": {bad_comp[:3]}" if bad_comp else ""))
    check(not bad_counts, "all stored vertex/face counts equal independent recounts",
          f"{len(bad_counts)} mismatches" + (f": {bad_counts[:3]}" if bad_counts else ""))
    check(not bad_header, "every referenced mesh's OBJ header agrees (File ID; Concept ID in subtree)",
          f"{len(bad_header)} mismatches" + (f": {bad_header[:3]}" if bad_header else ""))

    print("== (d) anatomy spot rules ==")
    ORD = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth",
           7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh", 12: "twelfth"}
    ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
    FINGER = {1: "thumb", 2: "index finger", 3: "middle finger", 4: "ring finger", 5: "little finger"}
    TOE = {1: "big toe", 2: "second toe", 3: "third toe", 4: "fourth toe", 5: "little toe"}
    violations = {k: [] for k in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8")}

    # R7 first: the NOT-FOUND set must be exactly the provably-absent seven,
    # and the absence must re-verify against the raw tables.
    expected_nf = {"malleus_right", "incus_right", "stapes_right",
                   "malleus_left", "incus_left", "stapes_left", "coccyx"}
    actual_nf = {rid for rid, r in maps.items() if r["mapping_kind"] == "NOT-FOUND"}
    if actual_nf != expected_nf:
        violations["R7"].append(f"NOT-FOUND set {sorted(actual_nf)} != expected {sorted(expected_nf)}")
    all_names = list(isa_names.values()) + list(po_names.values())
    for stem in ("malleus", "incus", "stapes", "coccyx"):
        hits = [n for n in all_names if stem in n.lower()]
        if hits:
            violations["R7"].append(f"stem '{stem}' unexpectedly present: {hits}")
    LIMB_WORDS = ("femur", "humerus", "tibia", "fibula", "radius", "ulna", "rib",
                  "vertebra", "metacarpal", "metatarsal", "phalanx", "scapula",
                  "clavicle", "patella", "calcaneus", "talus", "sternum")

    for rid, r in maps.items():
        if r["mapping_kind"] == "NOT-FOUND":
            continue
        bone = bone_by_id[rid]
        name = (r["concept_name"] or "").lower()
        sub = bone.get("subgroup")
        # R1: ribs map to rib concepts
        if sub == "ribs" and "rib" not in name:
            violations["R1"].append(rid)
        # R2: vertebrae map to vertebra/atlas/axis/sacrum concepts
        if sub == "vertebrae" and not any(w in name for w in ("vertebra", "atlas", "axis", "sacrum")):
            violations["R2"].append(rid)
        # R3: skull records never map to limb/trunk bone concepts
        if sub in ("cranium", "facial") and any(w in name for w in LIMB_WORDS):
            violations["R3"].append(rid)
        # R4: side coherence — a sided record's concept name carries its side,
        # unless the kind explicitly records the side on an un-sided class.
        if bone["side"] in ("right", "left"):
            if r["mapping_kind"] == "class+side":
                if r["side_recorded"] != bone["side"]:
                    violations["R4"].append(rid)
            elif bone["side"] not in name:
                violations["R4"].append(rid)
        # R5: hand phalanges -> finger/thumb names; foot phalanges -> toe names
        if "phalanx" in bone["name"].lower():
            if bone["region"] == "upper limb" and not ("finger" in name or "thumb" in name):
                violations["R5"].append(rid)
            if bone["region"] == "lower limb" and "toe" not in name:
                violations["R5"].append(rid)
        # R6: metacarpal/metatarsal stems preserved
        if bone["name"].startswith("Metacarpal") and "metacarpal" not in name:
            violations["R6"].append(rid)
        if bone["name"].startswith("Metatarsal") and "metatarsal" not in name:
            violations["R6"].append(rid)
        # R8: level/digit coherence for ribs, vertebrae, metapodials, phalanges
        m = re.match(r"Rib (\d+)", bone["name"])
        if m and ORD[int(m.group(1))] not in name:
            violations["R8"].append(rid)
        m = re.match(r"vert_([CTL])(\d+)$", rid)
        if m and m.group(1) in "TL" and ORD[int(m.group(2))] not in name:
            violations["R8"].append(rid)
        m = re.match(r"Meta(carpal|tarsal) ([IV]+)$", re.sub(r"\s*\((right|left)\)", "", bone["name"]))
        if m and ORD[ROMAN[m.group(2)]] not in name:
            violations["R8"].append(rid)
        m = re.match(r"(?:Proximal|Middle|Distal) phalanx ([IV]+)", bone["name"])
        if m:
            table = FINGER if bone["region"] == "upper limb" else TOE
            if table[ROMAN[m.group(1)]] not in name:
                violations["R8"].append(rid)
    labels = {
        "R1": "ribs map to rib concepts",
        "R2": "vertebrae map to vertebra/atlas/axis/sacrum concepts",
        "R3": "skull records never map to limb/trunk concepts",
        "R4": "side coherence (concept name carries the record's side)",
        "R5": "hand phalanges -> finger/thumb, foot phalanges -> toe concepts",
        "R6": "metacarpal/metatarsal stems preserved",
        "R7": "NOT-FOUND set is exactly the provably-absent seven",
        "R8": "level/digit coherence (ordinals and digit names match the record)",
    }
    for k in sorted(labels):
        check(not violations[k], f"{k}: {labels[k]}",
              f"violations: {violations[k][:6]}" if violations[k] else "0 violations")

    print("== (e) anomalies (non-fatal) ==")
    for rid, grow in geos.items():
        seen = {}
        for tree in ("isa_meshes", "partof_meshes"):
            for mm in grow[tree]:
                digest = stats[mm["path"]][3]
                key = (tree, digest)
                if key in seen:
                    note(f"{rid}: {mm['fj']} duplicates the geometry of {seen[key]} "
                         f"within the {tree} composition (identical v/f content)")
                else:
                    seen[key] = mm["fj"]

    from collections import Counter
    dist = Counter(r["mapping_kind"] for r in maps.values())
    print("== summary ==")
    print("mapping distribution (recounted):", dict(dist))
    print("stored meta distribution matches:",
          mapping["meta"]["distribution"] == dict(dist))
    check(mapping["meta"]["distribution"] == dict(dist),
          "meta distribution in fma-mapping.json matches recount")
    print(f"FAILURES: {len(FAILURES)}; NOTES: {len(NOTES)}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
