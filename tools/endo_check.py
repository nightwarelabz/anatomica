#!/usr/bin/env python3
"""ANATOMICA Milestone 13 — independent checker for the endocrine
module.

Shares NO code with tools/endo_map.py or
tools/build_endo_records.py. Re-derives, from the six BP3D 4.0
release tables: (1) the concept universe and the geometry records
(endocrine PART-OF line, adrenal IS-A line, pituitary, and the
pineal / pancreas / testis cross-reference lines), dispositions
and absence probes; (2) the concept->mesh attribution (FJ
numbers) and every recorded vertex/face count and bounding box,
by re-reading the OBJ files; (3) the TotalSegmentator overlap,
from the M3 label index; (4) the Milestone 12 boundary closure —
the urinary module's endocrine cross-reference set must be
exactly this module's adrenal census; (5) the clinical
tranche's citation/flag/tier discipline against this checker's
own core/soft field table, plus content gates: the adrenal
cortical zones in their anatomical order inside the cortex
field, the thyroid record's recurrent-laryngeal cross-reference
resolving to the nervous module's vagus record, the pineal
record's geometry pointer resolving to the nervous module's
pineal record, the islets record's host pointer resolving to
the digestive module's pancreas records, and the adrenal and
thyroid records' named cardiovascular records all resolving.

Run: python3 tools/endo_check.py   (exit 0 = all checks pass)
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
INV_P = os.path.join(ROOT, "data", "endocrine",
                     "endocrine-inventory.json")
GEO_P = os.path.join(ROOT, "data", "endocrine",
                     "endocrine-geometry.json")
CLIN_P = os.path.join(ROOT, "data", "endocrine", "endocrine.json")
URI_INV = os.path.join(ROOT, "data", "urinary",
                       "urinary-inventory.json")
NERV_INV = os.path.join(ROOT, "data", "nervous",
                        "nervous-inventory.json")
NERV_CLIN = os.path.join(ROOT, "data", "nervous", "nervous.json")
DIG_INV = os.path.join(ROOT, "data", "digestive",
                       "digestive-inventory.json")
DIG_CLIN = os.path.join(ROOT, "data", "digestive",
                        "digestive.json")
CV_INV = os.path.join(ROOT, "data", "cardiovascular",
                      "cv-inventory.json")
TS_LABELS = os.path.join(ROOT, "data", "sources",
                         "totalsegmentator-1.0", "labels.json")

ENDO_ROOT = "FMA9668"
PITUITARY = "FMA13889"
ADRENAL_CLASS = "FMA9604"
PINEAL = "FMA62033"
PANCREAS = "FMA7198"
TESTIS = "FMA7210"
ADRENAL_INSTANCES = {"FMA15629", "FMA15630"}
TESTIS_SET = {"FMA7210", "FMA7211", "FMA7212"}
XREF = {"FMA62033": "nervous", "FMA7198": "digestive",
        "FMA7210": "reproductive", "FMA7211": "reproductive",
        "FMA7212": "reproductive"}
GROUPING = {"FMA9668"}
SWEEP_TERMS = ("endocrine", "gland", "thyroid", "parathyroid",
               "pituitary", "pineal", "adrenal", "suprarenal",
               "hypophysis", "islet")

CORE = {
    "gland.pituitary-gland": ["position", "parts", "products"],
    "gland.thyroid-gland": ["position", "structure", "products"],
    "gland.parathyroid-glands": ["position", "products",
                                 "function"],
    "gland.adrenal-gland": ["position", "cortex", "medulla",
                            "products"],
    "gland.pineal-gland": ["position", "products", "function"],
    "gland.pancreatic-islets": ["definition", "cell_types",
                                "products"],
}
SOFT = {
    "gland.pituitary-gland": ["relations", "vasculature",
                              "control"],
    "gland.thyroid-gland": ["arterial_supply", "venous_drainage",
                            "nerves_at_risk",
                            "lymphatic_drainage", "control"],
    "gland.parathyroid-glands": ["cells", "relations",
                                 "arterial_supply"],
    "gland.adrenal-gland": ["relations", "arterial_supply",
                            "venous_drainage", "innervation",
                            "lymphatics"],
    "gland.pineal-gland": ["regulation"],
    "gland.pancreatic-islets": ["host_organ"],
}
BASE_KEYS = {"id", "name", "type", "group", "ta_name", "sources",
             "verify", "note", "geometry_record_ids",
             "sourcing_tier"}
ENDO_NAMES = {"pituitary gland", "right adrenal gland",
              "left adrenal gland"}
HELD_MARK = "geometry held by the nervous module"

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
    endo_po = descendants(ENDO_ROOT, po_kids)
    adrenal_isa = descendants(ADRENAL_CLASS, isa_kids)
    testis_isa = descendants(TESTIS, isa_kids)
    exp_isa = {PITUITARY} | adrenal_isa | {PINEAL} | {PANCREAS} | \
        testis_isa
    exp_po = endo_po | {PINEAL} | {PANCREAS}
    exp_universe = exp_isa | exp_po
    check("endocrine PART-OF line is root + pituitary + 2 adrenals",
          endo_po == {ENDO_ROOT, PITUITARY} | ADRENAL_INSTANCES,
          f"{sorted(endo_po)}")
    check("adrenal IS-A line is class + 2 instances",
          adrenal_isa == {ADRENAL_CLASS} | ADRENAL_INSTANCES)
    check("testis IS-A line is class + 2 instances",
          testis_isa == TESTIS_SET)
    check("no IS-A concept name contains 'endocrine', and the "
          "thyroid gland concept does not exist",
          not any("endocrine" in v["name"] for v in isa.values())
          and "thyroid gland" not in
          {v["name"] for v in isa.values()} |
          {v["name"] for v in po.values()})
    check("concept universe re-derived",
          {c["fma_id"] for c in inv["concepts"]} == exp_universe,
          f"{len(exp_universe)} concepts")
    check("universe counts match meta",
          cu["total"] == len(exp_universe)
          and cu["isa_total"] == len(exp_isa)
          and cu["partof_total"] == len(exp_po)
          and cu["in_both_tables"] == len(exp_isa & exp_po)
          and cu["cross_references"] ==
          dict(Counter(XREF[c] for c in exp_universe if c in XREF)))
    sub_expect = {}
    for c in endo_po:
        sub_expect[c] = "endocrine-system-partof"
    sub_expect[PITUITARY] = "pituitary-isa"
    for c in adrenal_isa:
        sub_expect[c] = "adrenal-gland-isa"
    sub_expect[PINEAL] = "pineal-nervous-xref-isa"
    sub_expect[PANCREAS] = "pancreas-digestive-xref"
    for c in testis_isa:
        sub_expect[c] = "testis-reproductive-xref-isa"
    bad = [c["fma_id"] for c in inv["concepts"]
           if c["subtree"] != sub_expect[c["fma_id"]]]
    check("concept subtree tags match re-derived sets", not bad,
          f"bad={bad}")

    # ---------- records re-derivation ----------
    exp_records = {
        "pituitary-gland": ("pituitary gland", "un-sided",
                            "whole-concept", [PITUITARY], PITUITARY),
        "adrenal-gland.right-adrenal-gland": (
            "right adrenal gland", "right", "whole-concept",
            ["FMA15629"], ADRENAL_CLASS),
        "adrenal-gland.left-adrenal-gland": (
            "left adrenal gland", "left", "whole-concept",
            ["FMA15630"], ADRENAL_CLASS),
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
        if c in XREF:
            return "cross-reference:" + XREF[c]
        if c in GROUPING:
            return "grouping-class"
        return "subtree-internal"
    bad = [c["fma_id"] for c in inv["concepts"]
           if c["disposition"] != exp_disp(c["fma_id"])
           or c["record_id"] != claimed.get(c["fma_id"])
           or c["cross_reference"] != XREF.get(c["fma_id"])]
    check("concept dispositions, record and cross-reference "
          "pointers match", not bad, f"bad={bad}")
    check("dispositions partition the universe",
          Counter(exp_disp(c) for c in exp_universe) ==
          Counter(c["disposition"] for c in inv["concepts"])
          and sum(cu["dispositions"].values()) == len(exp_universe))
    check("adrenal class is the only class-carried concept; the "
          "endocrine root the only grouping class",
          carried == {ADRENAL_CLASS}
          and {c for c in exp_universe
               if exp_disp(c) == "grouping-class"} == GROUPING)

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

    # ---------- Milestone 12 boundary closure ----------
    uri = json.load(open(URI_INV))
    uri_xref = {c["fma_id"] for c in uri["concepts"]
                if c["cross_reference"] == "endocrine"}
    endo_adrenal = carried | {c for rid, r in got_records.items()
                              for c in r["concept_ids"]
                              if rid.startswith("adrenal-gland.")}
    check("M12 boundary closure: the urinary module's endocrine "
          "cross-reference set is exactly this module's adrenal "
          "census (class + both instances)",
          uri_xref == endo_adrenal ==
          {ADRENAL_CLASS} | ADRENAL_INSTANCES,
          f"urinary={sorted(uri_xref)} endocrine="
          f"{sorted(endo_adrenal)}")

    # ---------- sweep re-derivation ----------
    exp_rej = set()
    for tab in (isa, po):
        for cid, v in tab.items():
            if cid not in exp_universe and \
                    any(t in v["name"] for t in SWEEP_TERMS):
                exp_rej.add(v["name"])
    check("sweep rejected names match re-derivation",
          set(cu["sweep_rejected_names"]) == exp_rej,
          f"{len(exp_rej)} names")
    check("lacrimal glands appear in the sweep with no owning "
          "module and are not claimed here",
          {"lacrimal gland", "right lacrimal gland",
           "left lacrimal gland"} <= exp_rej
          and not any("lacrimal" in c["name"]
                      for c in inv["concepts"]))
    check("salivary names in the sweep are the digestive module's "
          "concepts, not this module's",
          {"salivary gland", "major salivary gland",
           "submandibular gland", "sublingual gland"} <= exp_rej)

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
    check("thyroid, parathyroids, islets, all gland interiors and "
          "the ovary are probe-verified absent",
          all(detail[p]["total_hits"] == 0 for p in
              ("thyroid gland", "parathyroid", "pancreatic islet",
               "islet", "langerhans", "adenohypophysis",
               "neurohypophysis", "adrenal cortex",
               "adrenal medulla", "zona glomerulosa",
               "suprarenal gland", "ovary", "ovarian")))

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
    check("geometry coverage meta matches (3/3)",
          geo["meta"]["coverage"]["records_with_meshes"] == 3)
    check("both tables carry identical meshes for every record",
          all(geo_rec[r]["totals"]["isa"] ==
              geo_rec[r]["totals"]["partof"] for r in geo_rec))
    fj_owner = {}
    for rid, gr in geo_rec.items():
        for key in ("isa_meshes", "partof_meshes"):
            for m in gr[key]:
                fj_owner.setdefault((key, m["fj"]), set()).add(rid)
    check("FJ attribution: every mesh file belongs to exactly one "
          "record per table", all(len(v) == 1
                                  for v in fj_owner.values()),
          f"{len(fj_owner)} file slots")

    # ---------- TotalSegmentator overlap ----------
    ts = json.load(open(TS_LABELS))
    ts_counts = ts["labels"]
    endo_labels = [l for l in ts_counts if "adrenal" in l]
    check("TS carries exactly two endocrine labels (the adrenals)",
          sorted(endo_labels) == ["adrenal_gland_left",
                                  "adrenal_gland_right"],
          f"{endo_labels}")
    check("TS adrenal labels present in all 1,204 subjects",
          all(ts_counts[l] == ts["subjects_in_index"] == 1204
              for l in endo_labels))
    check("inventory TS overlap matches the adrenal records",
          {(l["label"], tuple(l["inventory_record_ids"]))
           for l in meta["totalsegmentator_overlap"]["labels"]} ==
          {("adrenal_gland_right",
            ("adrenal-gland.right-adrenal-gland",)),
           ("adrenal_gland_left",
            ("adrenal-gland.left-adrenal-gland",))}
          and meta["totalsegmentator_overlap"]
          ["labels_without_records"] == [])

    # ---------- clinical tranche ----------
    recs = clin["records"]
    by_id = {r["id"]: r for r in recs}
    check("clinical record count and ids match this checker",
          clin["meta"]["record_count"] == len(CORE)
          and set(by_id) == set(CORE), f"{sorted(by_id)}")
    check("clinical meta sources are exactly S1-S8 + TA2 (M23)",
          set(clin["meta"]["sources"]) ==
          {f"S{i}" for i in range(1, 9)} | {"TA2"})
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
        linked_names = {inv_rec[g]["name"]
                        for g in r["geometry_record_ids"]}
        extra = linked_names - ENDO_NAMES
        if extra:
            bad.append((rid, f"non-endocrine link {extra}"))
        if not r["geometry_record_ids"] and \
                not any("no BP3D 4.0 concept exists" in v
                        or HELD_MARK in v for v in r["verify"]):
            bad.append((rid, "empty links without absence/held "
                             "entry"))
    check("geometry links resolve inside the endocrine module; "
          "empty links carry the absence or held-by entry",
          not bad, f"bad={bad}")
    check("exactly the pituitary and adrenal records link "
          "geometry; thyroid, parathyroid and islet records link "
          "none",
          by_id["gland.pituitary-gland"]["geometry_record_ids"] ==
          ["pituitary-gland"]
          and set(by_id["gland.adrenal-gland"]
                  ["geometry_record_ids"]) ==
          {"adrenal-gland.right-adrenal-gland",
           "adrenal-gland.left-adrenal-gland"}
          and all(not by_id[r]["geometry_record_ids"] for r in
                  ("gland.thyroid-gland",
                   "gland.parathyroid-glands",
                   "gland.pancreatic-islets")))

    # ---------- content gates ----------
    cortex = by_id["gland.adrenal-gland"]["cortex"].lower()
    zones = [cortex.find(w) for w in
             ("glomerulosa", "fasciculata", "reticularis")]
    check("adrenal cortical zones in anatomical order inside the "
          "cortex field (glomerulosa < fasciculata < reticularis)",
          all(x >= 0 for x in zones) and zones == sorted(zones),
          f"positions={zones}")
    products = by_id["gland.pituitary-gland"]["products"].lower()
    hormones = ("growth hormone", "prolactin",
                "thyroid-stimulating", "adrenocorticotropic",
                "follicle-stimulating", "luteinising",
                "melanocyte-stimulating", "antidiuretic",
                "oxytocin")
    check("pituitary products carry the consulted source's full "
          "hormone list", all(h in products for h in hormones),
          f"missing={[h for h in hormones if h not in products]}")
    nerv_clin_ids = {r["id"] for r in
                     json.load(open(NERV_CLIN))["records"]}
    thy = by_id["gland.thyroid-gland"]
    check("thyroid nerves_at_risk cross-reference resolves to "
          "the nervous module's vagus record",
          "nerve.cn-10-vagus" in thy["nerves_at_risk"]
          and "nerve.cn-10-vagus" in nerv_clin_ids)
    nerv_inv = json.load(open(NERV_INV))
    pineal_rec = [r for r in nerv_inv["records"]
                  if r["record_id"] == "brain.pineal-body"]
    pin = by_id["gland.pineal-gland"]
    check("pineal record's held-by pointer resolves: nervous "
          "inventory holds brain.pineal-body keyed FMA62033",
          any(HELD_MARK in v for v in pin["verify"])
          and len(pineal_rec) == 1
          and pineal_rec[0]["concept_ids"] == [PINEAL])
    dig_inv = json.load(open(DIG_INV))
    dig_clin_ids = {r["id"] for r in
                    json.load(open(DIG_CLIN))["records"]}
    isl = by_id["gland.pancreatic-islets"]
    check("islets host-organ pointer resolves to the digestive "
          "module's pancreas records",
          "organ.pancreas" in isl["host_organ"]
          and "organ.pancreas" in dig_clin_ids
          and any(r["record_id"] == "pancreas"
                  for r in dig_inv["records"]))
    cv_ids = {r["record_id"] for r in
              json.load(open(CV_INV))["records"]}
    adr = by_id["gland.adrenal-gland"]
    named = set(re.findall(r"(?:artery|vein)\.[a-z0-9-]+",
                           adr["arterial_supply"] + " " +
                           adr["venous_drainage"]))
    thy_named = set(re.findall(r"artery\.[a-z0-9-]+",
                               " ".join(thy["verify"])))
    check("adrenal and thyroid records' named cardiovascular "
          "inventory records all resolve",
          named == {"artery.left-middle-suprarenal-artery",
                    "artery.right-middle-suprarenal-artery",
                    "artery.left-inferior-suprarenal-artery",
                    "artery.right-inferior-suprarenal-artery",
                    "vein.right-suprarenal-vein",
                    "vein.left-suprarenal-vein"}
          and thy_named == {"artery.left-inferior-thyroid-artery",
                            "artery.right-inferior-thyroid-artery"}
          and (named | thy_named) <= cv_ids,
          f"adrenal={sorted(named)} thyroid={sorted(thy_named)}")
    check("parathyroid arterial supply is the tranche's one "
          "flagged null (tier B)",
          by_id["gland.parathyroid-glands"]
          ["arterial_supply"] is None
          and dict(tier_count) == {"A": 5, "B": 1})

    # TA2 discipline (M23)
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    import ta2_discipline as _ta2d
    _ta2d.run("endocrine", "data/endocrine/endocrine.json", lambda ok_, label: check(label, ok_))

    npass = sum(1 for _, ok, _ in checks if ok)
    print(f"endo_check: {npass}/{len(checks)} checks passed")
    for name, ok, detail in checks:
        print(("PASS " if ok else "FAIL ") + name +
              ((" — " + detail) if detail and not ok else ""))
    print(f"  universe {len(exp_universe)} concepts / "
          f"{len(exp_records)} records / geometry totals: "
          f"IS-A {tot['isa_v']} v {tot['isa_f']} f, PART-OF "
          f"{tot['partof_v']} v {tot['partof_f']} f / clinical "
          f"{len(recs)} records tiers {dict(tier_count)}")
    return 0 if npass == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
