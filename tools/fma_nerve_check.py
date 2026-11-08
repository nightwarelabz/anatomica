#!/usr/bin/env python3
"""ANATOMICA nervous-system FMA extension checker — Milestone 33.

Independent of tools/fma_nerve_map.py: the OWL is re-parsed here
with an XML parser (the builder used streaming regex), the license
evidence is re-hashed against the provenance ledger, and every
extension record is re-verified against the ontology and against
the BodyParts3D tables. Shares no code with the builder.

Checks:
  L1  data/sources/fma-5.1.0/LICENSE hash == ledger pin, and the
      text is the CC BY 4.0 instrument (title + Section 2 grant).
  L2  fma.zip hash == ledger pin.
  F1  every FMA-extension inventory record's concept FMAID exists in
      fma.owl with the identical preferred name.
  F2  side consistency: a record with side left/right keys on the
      FMA's sided class of that name; an un-sided record keys on the
      un-sided class; class_concept_id, where set, is the un-sided
      namesake class.
  F3  group_path ends at the record's own name; the fraction whose
      path reaches the 'Nervous system' root is reported.
  B1  no extension FMAID appears among the BodyParts3D-derived
      inventory's concept ids (the extension adds only what the
      release lacks).
  B2  [REPORT] extension names found anywhere in the BP3D 4.0
      ISA/PART-OF parts lists (concepts the release lists outside
      the nervous census — reported, not gated).
  G1  inventory <-> geometry correspondence for extension records:
      one geometry entry each; the 267 un-claimed records carry
      zero meshes; the 19 records claimed at Milestone 63 (Tier B
      Z-Anatomy intake, CLAIMED below) carry exactly their pinned
      derived mesh, re-measured from the OBJ file on disk.
  G2  every un-claimed extension record carries the
      geometry-absent verify flags and the fma-5.1.0 source tag;
      the 19 claimed records carry the Milestone 63 derived-
      geometry flag instead.
  C1  census arithmetic: meta record_count, representations and
      coverage recompute from the records themselves.
  C2  [REPORT] Milestone 4 C3 continuity, as re-pointed at
      Milestone 35: prints the census of
      data/innervation-link-pass.json (the one resolution
      semantics; re-derived and gated in nerve_check.py C8).

Usage: fma_nerve_check.py. Exit 0 iff all gated checks pass.
Stdlib only.
"""
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources", "fma-5.1.0")
OWL = os.path.join(ROOT, "work", "fma", "fma.owl")
INV = json.load(open(os.path.join(ROOT, "data", "nervous",
                                  "nervous-inventory.json")))
GEO = json.load(open(os.path.join(ROOT, "data", "nervous",
                                  "nervous-geometry.json")))
LEDGER = json.load(open(os.path.join(SRC, "ledger.json")))
SOURCE_TAG = "fma-5.1.0"

# Milestone 63 adjudication (2026-11-08 geometry ruling on the
# Milestone 34 audit): these 19 extension records — and only
# these — gained geometry, derived from the named Z-Anatomy Tier B
# template objects under data/sources/z-anatomy-derived/obj/ and
# placed by the audit's brain-assembly transform. The claim is
# pinned here: G1 requires the mesh-carrying extension set to
# equal this set exactly, each entry's fj/path to equal the
# pinned derivation from the object name, and each entry's
# counts/bbox to re-measure from the OBJ file on disk. The other
# 267 extension records remain mesh-less under the original rule.
CLAIMED = {
    "nerve.left-abducens-nerve": "Abducens nerve (VI).l",
    "nerve.right-abducens-nerve": "Abducens nerve (VI).r",
    "nerve.left-facial-nerve": "Facial nerve (VII).l",
    "nerve.right-facial-nerve": "Facial nerve (VII).r",
    "nerve.falx-cerebri": "Falx cerebri",
    "nerve.left-glossopharyngeal-nerve":
        "Glossopharyngeal nerve (IX).l",
    "nerve.right-glossopharyngeal-nerve":
        "Glossopharyngeal nerve (IX).r",
    "nerve.left-hypoglossal-nerve": "Hypoglossal nerve (XII).l",
    "nerve.right-hypoglossal-nerve": "Hypoglossal nerve (XII).r",
    "nerve.left-maxillary-nerve": "Maxillary nerve.l",
    "nerve.right-maxillary-nerve": "Maxillary nerve.r",
    "nerve.left-oculomotor-nerve": "Oculomotor nerve (III).l",
    "nerve.right-oculomotor-nerve": "Oculomotor nerve (III).r",
    "nerve.left-olfactory-nerve": "Olfactory nerve (I).l",
    "nerve.right-olfactory-nerve": "Olfactory nerve (I).r",
    "nerve.left-trigeminal-nerve": "Trigeminal nerve (V).l",
    "nerve.right-trigeminal-nerve": "Trigeminal nerve (V).r",
    "nerve.left-vestibulocochlear-nerve":
        "Vestibulocochlear nerve (VIII).l",
    "nerve.right-vestibulocochlear-nerve":
        "Vestibulocochlear nerve (VIII).r",
}


def claimed_fj(obj_name):
    return "ZA-" + obj_name.replace("/", "_").replace(" ", "_")


def claimed_path(obj_name):
    return "data/sources/z-anatomy-derived/obj/" + \
        obj_name.replace("/", "_").replace(" ", "_") + ".obj"


def measure(path):
    """(vertices, faces, bbox) streamed from an OBJ file."""
    v = f = 0
    mn = [float("inf")] * 3
    mx = [float("-inf")] * 3
    with open(path, "rb") as fh:
        for line in fh:
            if line[:2] == b"v ":
                v += 1
                p = line.split()
                for i in range(3):
                    x = float(p[1 + i])
                    mn[i] = min(mn[i], x)
                    mx[i] = max(mx[i], x)
            elif line[:2] == b"f ":
                f += 1
    return v, f, {"min": mn, "max": mx}

FAILS = []


def check(ok, label, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label} {detail}")
    if not ok:
        FAILS.append(label)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_owl_xml(path):
    """ElementTree iterparse: {fid: preferred_name}."""
    ns = {"owl": "http://www.w3.org/2002/07/owl#",
          "fma": "http://purl.org/sig/ont/fma/",
          "rdfs": "http://www.w3.org/2000/01/rdf-schema#"}
    names = {}
    for _ev, el in ET.iterparse(path, events=("end",)):
        if el.tag == f"{{{ns['owl']}}}Class":
            about = el.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about")
            pn = el.find("fma:preferred_name", ns)
            if about and pn is not None:
                names[about.rsplit("fma", 1)[-1]] = pn.text
            el.clear()
    return names


def main():
    pins = {e["path"]: e["sha256"] for e in LEDGER["entries"]}
    lic_path = os.path.join(SRC, "LICENSE")
    lic_text = open(lic_path, encoding="utf-8").read()
    check(sha256(lic_path) == pins["LICENSE"]
          and "Attribution 4.0 International" in lic_text
          and "reproduce and Share the Licensed Material" in lic_text,
          "L1 license evidence", "CC BY 4.0 text, hash-pinned")
    check(sha256(os.path.join(SRC, "fma.zip")) == pins["fma.zip"],
          "L2 fma.zip hash == ledger pin")

    owl_names = parse_owl_xml(OWL)
    print(f"  OWL classes with preferred names (XML parse): {len(owl_names)}")

    ext = [r for r in INV["records"] if r.get("source") == SOURCE_TAG]
    bp3d = [r for r in INV["records"] if r.get("source") != SOURCE_TAG]
    check(len(bp3d) == 133, "C0 BP3D partition intact", f"{len(bp3d)}")

    bad = []
    root_hits = 0
    for r in ext:
        fid = r["concept_ids"][0][3:]
        if owl_names.get(fid) != r["name"]:
            bad.append((r["record_id"], "name/FMAID mismatch"))
        if r["side"] in ("left", "right"):
            if not r["name"].lower().startswith(r["side"] + " "):
                bad.append((r["record_id"], "side/name mismatch"))
        if r.get("class_concept_id"):
            cfid = r["class_concept_id"][3:]
            base = r["name"]
            for pre in ("Left ", "Right "):
                if base.startswith(pre):
                    base = base[len(pre):]
            if owl_names.get(cfid, "").lower() != base.lower():
                bad.append((r["record_id"], "class concept mismatch"))
        gp = r.get("group_path") or []
        if not gp or gp[-1] != r["name"]:
            bad.append((r["record_id"], "group_path does not end at name"))
        if gp and gp[0] == "Anatomical entity":
            root_hits += 1
    check(not bad, "F1/F2/F3 record fidelity vs OWL",
          f"{len(ext)} records; {bad[:3]}")
    print(f"  group_path reaches 'Anatomical entity' root: "
          f"{root_hits}/{len(ext)}")

    bp3d_fmaids = set()
    for r in bp3d:
        bp3d_fmaids.update(r.get("concept_ids") or [])
        if r.get("class_concept_id"):
            bp3d_fmaids.add(r["class_concept_id"])
    overlap = [r["record_id"] for r in ext
               if r["concept_ids"][0] in bp3d_fmaids]
    check(not overlap, "B1 no FMAID overlap with BP3D inventory",
          f"{overlap[:3]}")

    parts_names = set()
    for fn in ("isa_parts_list_e.txt", "partof_parts_list_e.txt"):
        with open(os.path.join(ROOT, "data", "sources",
                               "bodyparts3d-4.0", fn),
                  encoding="utf-8", errors="replace") as f:
            next(f)
            for ln in f:
                parts = ln.rstrip("\n").split("\t")
                if len(parts) >= 3:
                    parts_names.add(parts[2].lower())
    in_parts = [r["name"] for r in ext
                if r["name"].lower() in parts_names]
    print(f"  [REPORT] B2 extension names present in BP3D parts lists: "
          f"{len(in_parts)} {in_parts[:5]}")

    geo_by_id = {g["record_id"]: g for g in GEO["records"]}
    gbad = [r["record_id"] for r in ext
            if r["record_id"] not in CLAIMED
            and (r["record_id"] not in geo_by_id
                 or geo_by_id[r["record_id"]]["isa_meshes"]
                 or geo_by_id[r["record_id"]]["partof_meshes"]
                 or not geo_by_id[r["record_id"]].get("geometry_status"))]
    carriers = {r["record_id"] for r in ext
                if r["record_id"] in geo_by_id
                and (geo_by_id[r["record_id"]]["isa_meshes"]
                     or geo_by_id[r["record_id"]]["partof_meshes"])}
    cbad = []
    if carriers != set(CLAIMED):
        cbad.append(("carrier set", sorted(carriers ^ set(CLAIMED))))
    for rid, obj in CLAIMED.items():
        g = geo_by_id.get(rid)
        if g is None:
            cbad.append((rid, "no geometry entry"))
            continue
        isa = g["isa_meshes"]
        if len(isa) != 1 or g["partof_meshes"] \
                or not g.get("geometry_status"):
            cbad.append((rid, "entry shape"))
            continue
        m = isa[0]
        if m["fj"] != claimed_fj(obj) or m["path"] != claimed_path(obj):
            cbad.append((rid, "fj/path != pinned claim"))
            continue
        v, f, bb = measure(os.path.join(ROOT, m["path"]))
        t = g["totals"]
        if (v, f) != (m["vertices"], m["faces"]) or bb != m["bbox"] \
                or g["bbox_isa"] != bb or g.get("bbox_partof") is not None \
                or t["isa"] != {"files": 1, "vertices": v, "faces": f} \
                or t["partof"] != {"files": 0, "vertices": 0,
                                   "faces": 0} \
                or t["combined_files"] != 1:
            cbad.append((rid, "re-measurement mismatch"))
    check(not gbad and not cbad,
          "G1 geometry correspondence (267 mesh-less; the 19 "
          "Milestone 63 Tier B claims pinned and re-measured)",
          f"meshless_bad={gbad[:3]} claim_bad={cbad[:3]}")
    vbad = [r["record_id"] for r in ext
            if r["record_id"] not in CLAIMED
            and (r.get("geometry") != "absent"
                 or not any(v.startswith("geometry: absent")
                            for v in r.get("verify", [])))]
    vbad += [r["record_id"] for r in ext
             if r["record_id"] in CLAIMED
             and (r.get("geometry") != "zanatomy-derived"
                  or not any(v.startswith(
                      "geometry: derived — Z-Anatomy Tier B intake "
                      "(Milestone 63)")
                      for v in r.get("verify", [])))]
    check(not vbad, "G2 verify flags carried", f"{vbad[:3]}")

    meta = INV["meta"]
    check(meta["record_count"] == len(INV["records"])
          and meta["record_representations"].get("fma-concept") == len(ext)
          and meta["fma_extension"]["records_added"] == len(ext),
          "C1 census arithmetic",
          f"{len(INV['records'])} total = {len(bp3d)} + {len(ext)}")
    cov = GEO["meta"]["coverage"]
    check(cov["records"] == len(GEO["records"])
          and cov["records_without_meshes"] == len(ext) - len(CLAIMED)
          and cov["records_with_meshes"] ==
          cov["records"] - cov["records_without_meshes"],
          "C1 geometry coverage arithmetic", f"{cov}")

    try:
        # Milestone 35: the resolution census is the one in
        # data/innervation-link-pass.json (component decomposition
        # + exact-correspondence rules R1–R4), re-derived and
        # gated in tools/nerve_check.py C8 — this report prints
        # that census, not a second naive count.
        link = json.load(open(os.path.join(
            ROOT, "data", "innervation-link-pass.json")))
        a, b = link["after"], link["before"]
        print(f"  [REPORT] C2 muscle innervation names: "
              f"{a['phrases']} distinct phrases; Milestone 35 "
              f"re-pointing: {a['phrases_fully_resolved']} fully "
              f"resolve to FMA inventory records, "
              f"{a['phrases_partially_resolved']} partially, "
              f"{a['phrases_unresolved']} not at all "
              f"({a['components_resolved']} of {a['components']} "
              f"named-nerve components link; "
              f"{a['distinct_inventory_records_linked']} distinct "
              f"inventory records linked); before: "
              f"{len(b['to_inventory'])} phrases to inventory and "
              f"{len(b['to_clinical'])} to clinical records under "
              f"full-phrase equality")
    except Exception as exc:  # report-only section
        print(f"  [REPORT] C2 skipped: {exc}")

    print(f"\n{'ALL CHECKS PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
