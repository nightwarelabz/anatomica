#!/usr/bin/env python3
"""ANATOMICA Milestone 13 — independent checker for the lymphatic
module.

Shares NO code with tools/lymph_map.py or
tools/build_lymph_records.py. Re-derives, from the six BP3D 4.0
release tables: (1) the concept universe and the geometry records
(spleen line, thymus lobe line, thymus PART-OF line),
dispositions and absence probes; (2) the concept->mesh
attribution (FJ numbers) and every recorded vertex/face count
and bounding box, by re-reading the OBJ files; (3) the
TotalSegmentator overlap, from the M3 label index; (4) the
clinical tranche's citation/flag/tier discipline against this
checker's own core/soft field table, plus content gates: the
drainage pathway's station order as the consulted source gives
it, and the spleen's splenic-artery / splenic-vein
cross-references resolving to cardiovascular clinical records.

Run: python3 tools/lymph_check.py   (exit 0 = all checks pass)
"""
import json
import os
import re
import sys
from collections import Counter, OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources", "bodyparts3d-4.0")
ISA_DIR = os.path.join(ROOT, "work", "bp3d", "isa_BP3D_4.0_obj_99")
PO_DIR = os.path.join(ROOT, "work", "bp3d", "partof_BP3D_4.0_obj_99")
INV_P = os.path.join(ROOT, "data", "lymphatic",
                     "lymphatic-inventory.json")
GEO_P = os.path.join(ROOT, "data", "lymphatic",
                     "lymphatic-geometry.json")
CLIN_P = os.path.join(ROOT, "data", "lymphatic", "lymphatic.json")
TS_LABELS = os.path.join(ROOT, "data", "sources",
                         "totalsegmentator-1.0", "labels.json")
CV_CLIN = os.path.join(ROOT, "data", "cardiovascular",
                       "cardiovascular.json")

SPLEEN = "FMA7196"
LOBE = "FMA71193"
THYMUS_PO = "FMA9607"
LOBE_INSTANCES = {"FMA71194", "FMA71195"}
SWEEP_TERMS = ("lymph", "spleen", "splenic", "thymus", "thymic",
               "tonsil", "marrow", "peyer")

CORE = {
    "organ.spleen": ["position", "internal_structure", "function"],
    "organ.thymus": ["position", "structure", "function"],
    "pathway.lymphatic-drainage": ["sequence", "function"],
    "structure.lymph-nodes": ["nodes", "tonsils"],
}
SOFT = {
    "organ.spleen": ["relations", "arterial_supply",
                     "venous_drainage", "lymphatic_drainage",
                     "innervation"],
    "organ.thymus": ["age_changes", "arterial_supply"],
    "pathway.lymphatic-drainage": ["ducts_and_territories"],
    "structure.lymph-nodes": ["malt"],
}
BASE_KEYS = {"id", "name", "type", "group", "ta_name", "sources",
             "verify", "note", "geometry_record_ids",
             "sourcing_tier"}
LYMPHATIC_NAMES = {"spleen", "thymus", "right lobe of thymus",
                   "left lobe of thymus"}

checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    return ok


def read_tsv(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        rows = [ln.rstrip("\n").split("\t") for ln in f if ln.strip()]
    return rows[1:]


def descendants(root, kids):
    seen, stack = set(), [root]
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        stack.extend(kids.get(c, []))
    return seen


def measure(path):
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


def main():
    isa_rows = read_tsv(os.path.join(SRC, "isa_parts_list_e.txt"))
    po_rows = read_tsv(os.path.join(SRC, "partof_parts_list_e.txt"))
    isa = {r[0]: {"repr": r[1], "name": r[2]} for r in isa_rows}
    po = {r[0]: {"repr": r[1], "name": r[2]} for r in po_rows}
    isa_elem, po_elem = {}, {}
    for r in read_tsv(os.path.join(SRC, "isa_element_parts.txt")):
        isa_elem.setdefault(r[0], set()).add(r[2])
    for r in read_tsv(os.path.join(SRC, "partof_element_parts.txt")):
        po_elem.setdefault(r[0], set()).add(r[2])
    isa_kids, isa_par = {}, {}
    for r in read_tsv(os.path.join(
            SRC, "isa_inclusion_relation_list.txt")):
        isa_kids.setdefault(r[0], []).append(r[2])
        isa_par[r[2]] = r[0]
    po_kids, po_par = {}, {}
    for r in read_tsv(os.path.join(
            SRC, "partof_inclusion_relation_list.txt")):
        po_kids.setdefault(r[0], []).append(r[2])
        po_par[r[2]] = r[0]

    inv = json.load(open(INV_P))
    geo = json.load(open(GEO_P))
    clin = json.load(open(CLIN_P))
    meta = inv["meta"]
    cu = meta["concept_universe"]

    # ---------- universe re-derivation ----------
    spleen_isa = descendants(SPLEEN, isa_kids)
    lobe_isa = descendants(LOBE, isa_kids)
    thymus_po = descendants(THYMUS_PO, po_kids)
    exp_isa = spleen_isa | lobe_isa
    exp_po = thymus_po
    exp_universe = exp_isa | exp_po
    check("spleen IS-A line is the spleen alone",
          spleen_isa == {SPLEEN}, f"{len(spleen_isa)} concepts")
    check("thymus lobe IS-A line is class + 2 instances",
          lobe_isa == {LOBE} | LOBE_INSTANCES,
          f"{sorted(lobe_isa)}")
    check("thymus PART-OF line is organ + 2 lobes",
          thymus_po == {THYMUS_PO} | LOBE_INSTANCES,
          f"{sorted(thymus_po)}")
    check("the string 'lymph' occurs in no concept name",
          not any("lymph" in v["name"]
                  for v in list(isa.values()) + list(po.values())))
    check("concept universe re-derived",
          {c["fma_id"] for c in inv["concepts"]} == exp_universe,
          f"{len(exp_universe)} concepts")
    check("universe counts match meta",
          cu["total"] == len(exp_universe)
          and cu["isa_total"] == len(exp_isa)
          and cu["partof_total"] == len(exp_po)
          and cu["in_both_tables"] == len(exp_isa & exp_po))
    sub_expect = {}
    for c in spleen_isa:
        sub_expect[c] = "spleen-isa"
    for c in lobe_isa:
        sub_expect[c] = "thymus-lobe-isa"
    for c in thymus_po:
        sub_expect.setdefault(c, "thymus-partof")
    bad = [c["fma_id"] for c in inv["concepts"]
           if c["subtree"] != sub_expect[c["fma_id"]]]
    check("concept subtree tags match re-derived sets", not bad,
          f"bad={bad}")

    # ---------- records re-derivation ----------
    exp_records = {
        "spleen": ("spleen", "un-sided", "whole-concept",
                   [SPLEEN], SPLEEN),
        "thymus": ("thymus", "un-sided", "partof-organ",
                   [THYMUS_PO], None),
        "thymus-lobe.right-lobe-of-thymus": (
            "right lobe of thymus", "right", "whole-concept",
            ["FMA71194"], LOBE),
        "thymus-lobe.left-lobe-of-thymus": (
            "left lobe of thymus", "left", "whole-concept",
            ["FMA71195"], LOBE),
    }
    got_records = {r["record_id"]: r for r in inv["records"]}
    check("record id set matches derivation",
          set(got_records) == set(exp_records),
          f"{sorted(got_records)}")
    bad = []
    for rid, (nm, side, rep, cids, cc) in exp_records.items():
        r = got_records.get(rid)
        if r is None:
            bad.append(rid)
            continue
        if (r["name"], r["side"], r["representation"],
                r["concept_ids"], r["class_concept_id"]) != \
                (nm, side, rep, cids, cc):
            bad.append(rid)
    check("record fields match derivation", not bad, f"bad={bad}")
    check("meta record count and representations match",
          meta["record_count"] == len(exp_records)
          and meta["record_representations"] ==
          dict(Counter(v[2] for v in exp_records.values())))

    # dispositions
    claimed = {}
    for rid, r in got_records.items():
        for c in r["concept_ids"]:
            claimed[c] = rid
    carried = {r["class_concept_id"] for r in got_records.values()
               if r["class_concept_id"]
               and r["class_concept_id"] not in claimed}

    def exp_disp(c):
        if c in claimed:
            return "record"
        if c in carried:
            return "class-carried"
        return "subtree-internal"
    bad = [c["fma_id"] for c in inv["concepts"]
           if c["disposition"] != exp_disp(c["fma_id"])
           or c["record_id"] != claimed.get(c["fma_id"])]
    check("concept dispositions and record pointers match", not bad,
          f"bad={bad}")
    check("dispositions partition the universe",
          Counter(exp_disp(c) for c in exp_universe) ==
          Counter(c["disposition"] for c in inv["concepts"])
          and sum(cu["dispositions"].values()) == len(exp_universe))
    check("lobe class is the only class-carried concept",
          carried == {LOBE}, f"{carried}")

    # concept-row consistency
    bad = []
    for c in inv["concepts"]:
        cid = c["fma_id"]
        tab = isa if c["table"] == "isa" else po
        par = isa_par if c["table"] == "isa" else po_par
        ptab = isa if c["table"] == "isa" else po
        if tab[cid]["name"] != c["name"] or \
                tab[cid]["repr"] != c["representation_id"]:
            bad.append((cid, "name/repr"))
        if c["also_in_isa"] != (cid in isa) or \
                c["also_in_partof"] != (cid in po):
            bad.append((cid, "also_in"))
        if c["isa_mesh_files"] != len(isa_elem.get(cid, ())) or \
                c["partof_mesh_files"] != len(po_elem.get(cid, ())):
            bad.append((cid, "mesh counts"))
        pid = par.get(cid)
        if c["parent_id"] != pid or (pid is not None and
                                     c["parent_name"] !=
                                     ptab[pid]["name"]):
            bad.append((cid, "parent"))
    check("concept rows consistent with the tables", not bad,
          f"bad={bad[:5]}")

    # ---------- sweep re-derivation ----------
    exp_rej = set()
    for tab in (isa, po):
        for cid, v in tab.items():
            if cid not in exp_universe and \
                    any(t in v["name"] for t in SWEEP_TERMS):
                exp_rej.add(v["name"])
    check("sweep rejected names match re-derivation",
          set(cu["sweep_rejected_names"]) == exp_rej,
          f"{sorted(exp_rej)}")
    check("every rejected name is a splenic vessel (owned by the "
          "cardiovascular module)",
          all("splenic" in n for n in exp_rej), f"{sorted(exp_rej)}")

    # ---------- absence probes re-run ----------
    table_files = ["isa_parts_list_e.txt", "partof_parts_list_e.txt",
                   "isa_element_parts.txt",
                   "partof_element_parts.txt",
                   "isa_inclusion_relation_list.txt",
                   "partof_inclusion_relation_list.txt"]
    texts = {fn: open(os.path.join(SRC, fn), encoding="utf-8",
                      errors="replace").read().lower()
             for fn in table_files}
    all_names = {v["name"] for v in isa.values()} | \
        {v["name"] for v in po.values()}
    detail = {a["probe"]: a for a in meta["absences"]["detail"]}
    bad = []
    for probe, a in detail.items():
        hits = {fn: texts[fn].count(probe) for fn in table_files}
        if a["hits_by_table"] != hits or \
                a["total_hits"] != sum(hits.values()) or \
                a["exact_concept_exists"] != (probe in all_names):
            bad.append(probe)
    check("absence probe counts re-run identically", not bad,
          f"bad={bad}")
    check("absent/present probe lists match re-run",
          meta["absences"]["absent"] ==
          [p for p, a in detail.items() if a["total_hits"] == 0]
          and meta["absences"]["present"] ==
          [p for p, a in detail.items() if a["total_hits"] > 0],
          f"{len(meta['absences']['absent'])} absent / "
          f"{len(meta['absences']['present'])} present")
    check("the conducting system is probe-verified absent "
          "(thoracic duct re-verified)",
          all(detail[p]["total_hits"] == 0 for p in
              ("lymph", "lymphatic system", "lymph node",
               "lymphatic vessel", "lymphatic trunk",
               "thoracic duct", "right lymphatic duct",
               "cisterna chyli", "tonsil", "marrow")))

    # ---------- geometry re-measurement ----------
    inv_rec = {r["record_id"]: r for r in inv["records"]}
    geo_rec = {r["record_id"]: r for r in geo["records"]}
    check("geometry record set equals inventory record set",
          set(geo_rec) == set(inv_rec))
    bad, entries = [], 0
    tot = Counter()
    for rid, gr in geo_rec.items():
        if gr["concept_ids"] != inv_rec[rid]["concept_ids"]:
            bad.append((rid, "concept ids"))
        for tree, key, elem, d in (
                ("isa", "isa_meshes", isa_elem, ISA_DIR),
                ("partof", "partof_meshes", po_elem, PO_DIR)):
            exp_fj = set()
            for c in gr["concept_ids"]:
                exp_fj |= elem.get(c, set())
            if {m["fj"] for m in gr[key]} != exp_fj:
                bad.append((rid, tree + " fj set"))
            tv = tf = 0
            for m in gr[key]:
                entries += 1
                v, f, bb = measure(os.path.join(ROOT, m["path"]))
                if (v, f) != (m["vertices"], m["faces"]) or \
                        bb != m["bbox"]:
                    bad.append((rid, m["fj"]))
                tv += v
                tf += f
            t = gr["totals"][tree]
            if (t["files"], t["vertices"], t["faces"]) != \
                    (len(gr[key]), tv, tf):
                bad.append((rid, tree + " totals"))
            tot[tree + "_v"] += tv
            tot[tree + "_f"] += tf
            bbk = "bbox_" + tree
            if gr[key]:
                mn = [min(m["bbox"]["min"][i] for m in gr[key])
                      for i in range(3)]
                mx = [max(m["bbox"]["max"][i] for m in gr[key])
                      for i in range(3)]
                if gr[bbk] != {"min": mn, "max": mx}:
                    bad.append((rid, bbk))
            elif gr[bbk] is not None:
                bad.append((rid, bbk + " not null"))
    check(f"all geometry entries re-measured ({entries} entries)",
          not bad, f"bad={bad[:6]}")
    check("geometry coverage meta matches",
          geo["meta"]["coverage"]["records_with_meshes"] ==
          sum(1 for g in geo_rec.values()
              if g["isa_meshes"] or g["partof_meshes"]))
    # FJ attribution: instance meshes belong to exactly their
    # records; organ/class compositions account for the rest
    fj_owner = {}
    for rid, gr in geo_rec.items():
        for key in ("isa_meshes", "partof_meshes"):
            for m in gr[key]:
                fj_owner.setdefault((key, m["fj"]), set()).add(rid)
    # each PART-OF lobe file is shared by exactly the thymus
    # organ record (whose element set is the union composition)
    # and its own lobe record; every IS-A file is single-owned
    lobe_of_fj = {}
    for m in geo_rec["thymus-lobe.left-lobe-of-thymus"][
            "partof_meshes"]:
        lobe_of_fj[m["fj"]] = "thymus-lobe.left-lobe-of-thymus"
    for m in geo_rec["thymus-lobe.right-lobe-of-thymus"][
            "partof_meshes"]:
        lobe_of_fj[m["fj"]] = "thymus-lobe.right-lobe-of-thymus"
    bad = []
    for key, owners in fj_owner.items():
        tree, fj = key
        if tree == "partof_meshes" and fj in lobe_of_fj:
            if owners != {"thymus", lobe_of_fj[fj]}:
                bad.append((key, owners))
        elif len(owners) != 1:
            bad.append((key, owners))
    check("FJ attribution: each PART-OF lobe file is shared "
          "exactly by the thymus organ record and its own lobe "
          "record; all other files single-owned",
          not bad, f"bad={bad}")
    check("thymus PART-OF mesh is the union of its lobes' meshes",
          {m["fj"] for m in geo_rec["thymus"]["partof_meshes"]} ==
          {m["fj"] for m in
           geo_rec["thymus-lobe.right-lobe-of-thymus"]
           ["partof_meshes"]} |
          {m["fj"] for m in
           geo_rec["thymus-lobe.left-lobe-of-thymus"]
           ["partof_meshes"]})
    check("spleen has an IS-A mesh and no PART-OF mesh",
          len(geo_rec["spleen"]["isa_meshes"]) == 1
          and not geo_rec["spleen"]["partof_meshes"])

    # ---------- TotalSegmentator overlap ----------
    ts = json.load(open(TS_LABELS))
    ts_counts = ts["labels"]
    lymph_labels = [l for l in ts_counts
                    if any(t in l for t in
                           ("spleen", "thymus", "lymph", "node"))]
    check("TS carries exactly one lymphatic label",
          lymph_labels == ["spleen"], f"{lymph_labels}")
    check("TS spleen present in all 1,204 subjects",
          ts_counts["spleen"] == ts["subjects_in_index"] == 1204)
    check("inventory TS overlap matches (spleen -> spleen record)",
          meta["totalsegmentator_overlap"]["labels"] ==
          [OrderedDict([("label", "spleen"),
                        ("inventory_record_ids", ["spleen"]),
                        ("note", "")])]
          and meta["totalsegmentator_overlap"]
          ["labels_without_records"] == [])

    # ---------- clinical tranche ----------
    recs = clin["records"]
    by_id = {r["id"]: r for r in recs}
    check("clinical record count and ids match this checker",
          clin["meta"]["record_count"] == len(CORE)
          and set(by_id) == set(CORE), f"{sorted(by_id)}")
    check("clinical meta sources are exactly S1-S3 + TA2 (M23)",
          set(clin["meta"]["sources"]) == {"S1", "S2", "S3", "TA2"})
    all_inv_names = {r["name"] for r in inv["records"]}
    bad = []
    tier_count = Counter()
    for rid, r in by_id.items():
        core, soft = CORE[rid], SOFT[rid]
        if set(r.keys()) - {"ta_code"} != BASE_KEYS | set(core) | set(soft):
            bad.append((rid, "key set"))
        if r["ta_name"] is not None:
            # M23 discipline: TA2 name + integer ta_code + TA2
            # citation (table equality via tools/ta2_discipline.py)
            if r["sources"].get("ta_name") != ["TA2"] or \
                    not isinstance(r.get("ta_code"), int):
                bad.append((rid, "ta_name discipline"))
        elif not any("ta_name" in v for v in r["verify"]):
            bad.append((rid, "ta_name discipline"))
        exp_tier = "A"
        for fname in core + soft:
            if r[fname] is None:
                if not any(fname in v for v in r["verify"]):
                    bad.append((rid, fname + " null unflagged"))
                exp_tier = "C" if fname in core else \
                    ("B" if exp_tier == "A" else exp_tier)
            else:
                if fname not in r["sources"]:
                    bad.append((rid, fname + " valued uncited"))
                for s in r["sources"].get(fname, []):
                    if s not in clin["meta"]["sources"]:
                        bad.append((rid, fname + " bad source " + s))
        if r["sourcing_tier"] != exp_tier:
            bad.append((rid, "tier %s != %s"
                        % (r["sourcing_tier"], exp_tier)))
        tier_count[r["sourcing_tier"]] += 1
        for g in r["geometry_record_ids"]:
            if g not in inv_rec:
                bad.append((rid, "dangling geometry link " + g))
    check("clinical citation/flag/tier discipline (own core/soft "
          "table)", not bad, f"bad={bad[:8]}")
    check("clinical tier counts match meta",
          dict(tier_count) == clin["meta"]["tiers"],
          f"{dict(tier_count)}")
    bad = []
    for rid, r in by_id.items():
        linked_names = set()
        for g in r["geometry_record_ids"]:
            linked_names.add(inv_rec[g]["name"])
        extra = linked_names - LYMPHATIC_NAMES
        if extra:
            bad.append((rid, f"non-lymphatic link {extra}"))
        if not r["geometry_record_ids"] and \
                not any("no BP3D 4.0 concept exists" in v
                        for v in r["verify"]):
            bad.append((rid, "empty links without absence entry"))
    check("geometry links resolve inside the lymphatic module; "
          "empty links carry the absence entry", not bad,
          f"bad={bad}")
    check("spleen and thymus records link their organs' geometry",
          by_id["organ.spleen"]["geometry_record_ids"] == ["spleen"]
          and set(by_id["organ.thymus"]["geometry_record_ids"]) ==
          {"thymus", "thymus-lobe.right-lobe-of-thymus",
           "thymus-lobe.left-lobe-of-thymus"})

    # ---------- content gates ----------
    seq_text = " ".join(by_id["pathway.lymphatic-drainage"]
                        ["sequence"]).lower()
    order = [seq_text.find(w) for w in
             ("capillaries", "vessels", "trunks", "ducts", "vein")]
    check("drainage pathway stations in the consulted order "
          "(capillaries < vessels < trunks < ducts < vein)",
          all(x >= 0 for x in order) and order == sorted(order),
          f"positions={order}")
    cv_ids = {r["id"] for r in json.load(open(CV_CLIN))["records"]}
    sp = by_id["organ.spleen"]
    check("spleen supply cross-references resolve to "
          "cardiovascular clinical records",
          "artery.splenic-artery" in sp["arterial_supply"]
          and "vein.splenic-vein" in sp["venous_drainage"]
          and {"artery.splenic-artery", "vein.splenic-vein"} <=
          cv_ids)
    check("spleen relations and thymus arterial supply are the "
          "two flagged nulls (tier B pair)",
          sp["relations"] is None
          and by_id["organ.thymus"]["arterial_supply"] is None
          and dict(tier_count) == {"A": 2, "B": 2})

    # TA2 discipline (M23)
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    import ta2_discipline as _ta2d
    _ta2d.run("lymphatic", "data/lymphatic/lymphatic.json", lambda ok_, label: check(label, ok_))

    npass = sum(1 for _, ok, _ in checks if ok)
    print(f"lymph_check: {npass}/{len(checks)} checks passed")
    for name, ok, detail in checks:
        print(("PASS " if ok else "FAIL ") + name +
              ((" — " + detail) if detail and not ok else ""))
    print(f"  universe {len(exp_universe)} concepts / "
          f"{len(exp_records)} records / geometry totals: "
          f"IS-A {tot['isa_v']} v {tot['isa_f']} f, PART-OF "
          f"{tot['partof_v']} v {tot['partof_f']} f "
          f"(entries summed per record; shared lobe-union files "
          f"counted per owning record) / clinical "
          f"{len(recs)} records tiers {dict(tier_count)}")
    return 0 if npass == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
