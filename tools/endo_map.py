#!/usr/bin/env python3
"""ANATOMICA Milestone 13 — endocrine system census + geometry
mapping.

Censuses the endocrine-system concepts of BodyParts3D 4.0 / FMA
exactly as they are represented in the release tables
(data/sources/bodyparts3d-4.0/), and maps the derived records to
BP3D meshes in the manner of Milestones 2, 4, 5, 9, 10, 11 and
12: exact lookups only, compositions taken from the tables,
vertex/face counts measured by streaming the OBJ files.

HOW BP3D 4.0 REPRESENTS THE ENDOCRINE SYSTEM (established by
inspection of the tables, 2026-11-06; every claim is re-derived
by this script at run time):

  * The PART-OF table carries an endocrine system subtree
    rooted at FMA9668 "endocrine system" — and it has exactly
    three members below the root: the pituitary gland (FMA13889)
    and the right and left adrenal glands (FMA15629/FMA15630).
    Nothing else is filed under the system the release itself
    names endocrine.
  * The IS-A table carries the class concepts the PART-OF tree
    lacks: FMA9604 "adrenal gland" (with exactly its two
    instances below it) and the pituitary gland again — each
    gland hanging under a generic organ class (the adrenal under
    "corticomedullary organ", the pituitary under "lobular
    organ"), never under an endocrine class: no IS-A concept
    name contains the word "endocrine" at all.
  * THE THYROID GLAND DOES NOT EXIST IN THE RELEASE. Neither
    parts list contains the name "thyroid gland", nor any lobe,
    isthmus, follicle or parafollicular concept: every "thyroid"
    name in the tables is the thyroid cartilage (skeletal), the
    inferior thyroid arteries (cardiovascular) or the
    sternothyroid and cricothyroid muscles (muscular) — the
    gland between them is simply not there. THE PARATHYROID
    GLANDS ARE AS ABSENT: "parathyroid" scores zero hits in
    both parts lists. The two glands thyroid surgery most
    endangers — and the recurrent laryngeal nerve relation that
    makes them load-bearing — have no data here at all; the
    clinical tranche carries them as sourced text with the
    absence recorded, in the Milestone 9 pattern.
  * The remaining named glands are owned by other modules and
    are censused here as cross-references, never duplicated:
    the PINEAL BODY (FMA62033) is filed by the release under the
    epithalamus, inside the nervous system tree, and is the
    nervous module's record brain.pineal-body (Milestone 9); the
    PANCREAS (FMA7198) is the digestive module's record
    (Milestone 11), and its endocrine tissue — the pancreatic
    islets — has no concept anywhere in the release ("islet"
    and "langerhans" score zero hits in both parts lists); the
    TESTIS line (class FMA7210 with its two instances, IS-A
    only) belongs to the reproductive module, queued next. The
    OVARY does not exist in the release at all — "ovary" and
    "ovarian" score zero hits in both parts lists — a gap the
    reproductive module inherits and this census records at the
    boundary.
  * NO endocrine gland has any interior in the release: no
    adenohypophysis or neurohypophysis, no adrenal cortex or
    medulla, no zona of the cortex, no part of any gland
    (probe-verified over all six tables). The glands the release
    does carry are undivided volumes, as the urinary organs were
    in Milestone 12.
  * The adrenal boundary with Milestone 12 closes by
    construction: the urinary module censused exactly three
    adrenal concepts (FMA9604, FMA15629, FMA15630) as an
    endocrine cross-reference and made no records; this module
    keys its adrenal records on those same three concepts, the
    class carried on the two instance records.

COUNTING CONVENTION (what counts as one endocrine-system
record):
  * One record for the pituitary gland, keyed on FMA13889,
    which both tables carry.
  * One record per adrenal gland instance (right/left), keyed
    on its instance concept with the side-stripped class concept
    FMA9604 carried as class_concept_id (the Milestone 12
    instance pattern).
  * The endocrine system root (FMA9668) is a grouping class:
    censused, never a record. The pineal body, the pancreas and
    the testis line are cross-references to the nervous,
    digestive and reproductive modules respectively: censused,
    never records here.

Outputs:
  data/endocrine/endocrine-inventory.json  census + records
  data/endocrine/endocrine-geometry.json   per-record meshes

Stdlib only. Run: python3 tools/endo_map.py
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
OUT_INV = os.path.join(ROOT, "data", "endocrine",
                       "endocrine-inventory.json")
OUT_GEO = os.path.join(ROOT, "data", "endocrine",
                       "endocrine-geometry.json")

ENDOCRINE_PO_ROOT = "FMA9668"       # endocrine system (PART-OF)
PITUITARY = "FMA13889"              # pituitary gland (both tables)
ADRENAL_ISA_ROOT = "FMA9604"        # adrenal gland (IS-A line)
PINEAL_XREF = "FMA62033"            # pineal body — nervous record
PANCREAS_XREF = "FMA7198"           # pancreas — digestive record
TESTIS_ISA_ROOT = "FMA7210"         # testis — reproductive (queued)

# lateralised instance records: instance concept -> (prefix,
# class concept)
INSTANCES = {
    "FMA15629": ("adrenal-gland", "FMA9604"),  # right adrenal gland
    "FMA15630": ("adrenal-gland", "FMA9604"),  # left adrenal gland
}
# un-sided organ records keyed on their (both-table) concepts
ORGAN_RECORDS = {
    "FMA13889": "pituitary-gland",      # pituitary gland
}
GROUPING_IDS = {
    "FMA9668",    # endocrine system (root)
}
XREF_IDS = {
    "FMA62033": "nervous",        # pineal body -> brain.pineal-body
    "FMA7198": "digestive",       # pancreas -> digestive record
    "FMA7210": "reproductive",    # testis class (module queued)
    "FMA7211": "reproductive",    # right testis
    "FMA7212": "reproductive",    # left testis
}

ABSENCE_PROBES = [
    # the thyroid gland — the release's largest endocrine absence
    "thyroid gland", "lobe of thyroid gland",
    "isthmus of thyroid gland", "thyroid follicle",
    "parafollicular", "pyramidal lobe",
    # the parathyroid glands — wholly absent
    "parathyroid", "parathyroid gland", "superior parathyroid",
    "inferior parathyroid", "chief cell",
    # the pancreatic islets — the endocrine pancreas has no concept
    "pancreatic islet", "islet", "langerhans",
    "endocrine pancreas",
    # interiors of the glands that do exist — none exists
    "adenohypophysis", "neurohypophysis",
    "anterior lobe of pituitary gland",
    "posterior lobe of pituitary gland", "pars distalis",
    "pars nervosa", "pars intermedia", "infundibulum",
    "adrenal cortex", "adrenal medulla",
    "cortex of adrenal gland", "medulla of adrenal gland",
    "zona glomerulosa", "zona fasciculata", "zona reticularis",
    "suprarenal gland", "chromaffin",
    # generic endocrine classes — none exists
    "endocrine gland", "endocrine system",
    # the gonad boundary: testis exists (reproductive), ovary not
    "ovary", "ovarian", "ovarian follicle", "corpus luteum",
    "seminiferous", "leydig", "pinealocyte", "pineal gland",
    # present controls (exact concepts exist)
    "pituitary gland", "pineal body", "adrenal gland",
    "right adrenal gland", "left adrenal gland", "pancreas",
    "testis", "right testis", "left testis", "hypothalamus",
]


def read_tsv(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        rows = [ln.rstrip("\n").split("\t") for ln in f if ln.strip()]
    return rows[1:]


def load_tables():
    isa_rows = read_tsv(os.path.join(SRC, "isa_parts_list_e.txt"))
    po_rows = read_tsv(os.path.join(SRC, "partof_parts_list_e.txt"))
    isa = {r[0]: {"repr": r[1], "name": r[2]} for r in isa_rows}
    po = {r[0]: {"repr": r[1], "name": r[2]} for r in po_rows}
    isa_elem, po_elem = {}, {}
    for r in read_tsv(os.path.join(SRC, "isa_element_parts.txt")):
        isa_elem.setdefault(r[0], set()).add(r[2])
    for r in read_tsv(os.path.join(SRC, "partof_element_parts.txt")):
        po_elem.setdefault(r[0], set()).add(r[2])
    children, parent = {}, {}
    for r in read_tsv(os.path.join(SRC, "isa_inclusion_relation_list.txt")):
        children.setdefault(r[0], []).append(r[2])
        parent[r[2]] = r[0]
    po_children, po_parent = {}, {}
    for r in read_tsv(os.path.join(SRC, "partof_inclusion_relation_list.txt")):
        po_children.setdefault(r[0], []).append(r[2])
        po_parent[r[2]] = r[0]
    return isa, po, isa_elem, po_elem, children, parent, \
        po_children, po_parent


def descendants(root, children):
    seen, stack = set(), [root]
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        stack.extend(children.get(c, []))
    return seen


def obj_stats(path):
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
                    if x < mn[i]:
                        mn[i] = x
                    if x > mx[i]:
                        mx[i] = x
            elif line[:2] == b"f ":
                f += 1
    return {"vertices": v, "faces": f, "bbox": {"min": mn, "max": mx}}


SIDE_PREFIX = re.compile(r"^(right|left)\s+")


def side_of(name):
    m = SIDE_PREFIX.match(name)
    return m.group(1) if m else None


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    (isa, po, isa_elem, po_elem, children, parent,
     po_children, po_parent) = load_tables()

    # ---- concept sets ------------------------------------------------
    endocrine_po = descendants(ENDOCRINE_PO_ROOT, po_children)
    adrenal_isa = descendants(ADRENAL_ISA_ROOT, children)
    testis_isa = descendants(TESTIS_ISA_ROOT, children)

    isa_sets = OrderedDict([
        ("pituitary-isa", {PITUITARY}),
        ("adrenal-gland-isa", adrenal_isa),
        ("pineal-nervous-xref-isa", {PINEAL_XREF}),
        ("pancreas-digestive-xref", {PANCREAS_XREF}),
        ("testis-reproductive-xref-isa", testis_isa),
    ])
    po_sets = OrderedDict([
        ("endocrine-system-partof", endocrine_po),
        ("pineal-nervous-xref-partof", {PINEAL_XREF}),
        ("pancreas-digestive-xref-partof", {PANCREAS_XREF}),
    ])
    isa_universe = set()
    for s in isa_sets.values():
        isa_universe |= s
    po_universe = set()
    for s in po_sets.values():
        po_universe |= s
    universe = isa_universe | po_universe

    subtree_of = {}
    for tag, s in isa_sets.items():
        for cid in s:
            subtree_of.setdefault(cid, tag)
    for tag, s in po_sets.items():
        for cid in s:
            subtree_of.setdefault(cid, tag)

    def name_of(cid):
        return isa[cid]["name"] if cid in isa else po[cid]["name"]

    def cross_ref(cid):
        return XREF_IDS.get(cid)

    # cross-check sweep: endocrine terms outside the universe
    sweep_terms = ("endocrine", "gland", "thyroid", "parathyroid",
                   "pituitary", "pineal", "adrenal", "suprarenal",
                   "hypophysis", "islet")
    sweep_rejected = {}
    for tab, tname in ((isa, "isa"), (po, "partof")):
        for cid, v in tab.items():
            if cid in universe:
                continue
            n = v["name"]
            if any(t in n for t in sweep_terms):
                sweep_rejected.setdefault(n, tname)
    sweep_rejected = sorted(sweep_rejected)

    def chain_names(cid, par, tab):
        out, cur = [], cid
        while cur in par:
            cur = par[cur]
            out.append(tab[cur]["name"])
        return out

    # ---- record derivation --------------------------------------------
    records = []
    claimed = {}

    def add_record(rid, name, side, representation, concept_ids,
                   class_id, subtree, note=None):
        for c in concept_ids:
            assert c not in claimed, \
                f"concept {c} claimed by two records"
            claimed[c] = rid
        records.append(OrderedDict([
            ("record_id", rid),
            ("name", name),
            ("side", side),
            ("representation", representation),
            ("class_concept_id", class_id),
            ("concept_ids", concept_ids),
            ("subtree", subtree),
            ("group_path", None),
            ("note", note),
        ]))
        return records[-1]

    # (1) lateralised instances (class carried)
    instance_made = []
    for cid, (prefix, class_id) in sorted(
            INSTANCES.items(), key=lambda kv: isa[kv[0]]["name"]):
        assert cid in isa and class_id in isa
        nm = isa[cid]["name"]
        add_record(prefix + "." + slug(nm), nm, side_of(nm),
                   "whole-concept", [cid], class_id, subtree_of[cid],
                   note="lateralised instance; the side-stripped "
                        "class concept is carried as "
                        "class_concept_id. The instance is a direct "
                        "member of the endocrine system in PART-OF "
                        "and an instance of the adrenal class in "
                        "IS-A; Milestone 12 censused this concept as "
                        "an endocrine cross-reference, and this "
                        "record closes that boundary")
        instance_made.append(nm)

    # (2) un-sided organs carried by both tables
    organ_made = []
    for cid, rid in sorted(ORGAN_RECORDS.items(),
                           key=lambda kv: kv[1]):
        assert cid in isa and cid in po
        assert isa[cid]["name"] == po[cid]["name"]
        nm = isa[cid]["name"]
        add_record(rid, nm, "un-sided", "whole-concept", [cid], cid,
                   subtree_of[cid],
                   note="the gland is a leaf in both tables: no "
                        "adenohypophysis, neurohypophysis or other "
                        "part exists as a concept (probe-verified); "
                        "its two-part structure is carried as "
                        "sourced text in the clinical tranche")
        organ_made.append(nm)

    # group paths
    for rec in records:
        c0 = rec["concept_ids"][0]
        if c0 in po:
            rec["group_path"] = list(reversed(
                chain_names(c0, po_parent, po)))
        else:
            rec["group_path"] = list(reversed(
                chain_names(c0, parent, isa)))

    repr_counts = Counter(r["representation"] for r in records)

    # ---- dispositions ---------------------------------------------------
    class_carried = set()
    for rec in records:
        cc = rec["class_concept_id"]
        if cc is not None and cc not in claimed:
            class_carried.add(cc)

    def disposition(cid):
        if cid in claimed:
            return "record"
        if cid in class_carried:
            return "class-carried"
        xr = cross_ref(cid)
        if xr:
            return "cross-reference:" + xr
        if cid in GROUPING_IDS:
            return "grouping-class"
        return "subtree-internal"

    disp_counts = Counter(disposition(c) for c in universe)
    disp_lists = {}
    for c in sorted(universe):
        disp_lists.setdefault(disposition(c), []).append(c)

    # ---- concept census rows ----------------------------------------------
    concepts = []
    for cid in sorted(universe):
        in_isa = cid in isa_universe
        tab = isa if in_isa else po
        concepts.append(OrderedDict([
            ("fma_id", cid),
            ("name", tab[cid]["name"]),
            ("representation_id", tab[cid]["repr"]),
            ("table", "isa" if in_isa else "partof"),
            ("also_in_partof", cid in po),
            ("also_in_isa", cid in isa),
            ("subtree", subtree_of[cid]),
            ("cross_reference", cross_ref(cid)),
            ("disposition", disposition(cid)),
            ("record_id", claimed.get(cid)),
            ("parent_id", parent.get(cid) if in_isa
             else po_parent.get(cid)),
            ("parent_name", (isa[parent[cid]]["name"]
                             if in_isa and cid in parent
                             else po[po_parent[cid]]["name"]
                             if not in_isa and cid in po_parent
                             else None)),
            ("isa_mesh_files", len(isa_elem.get(cid, ()))),
            ("partof_mesh_files", len(po_elem.get(cid, ()))),
        ]))

    # ---- absence probes -----------------------------------------------------
    table_files = ["isa_parts_list_e.txt", "partof_parts_list_e.txt",
                   "isa_element_parts.txt", "partof_element_parts.txt",
                   "isa_inclusion_relation_list.txt",
                   "partof_inclusion_relation_list.txt"]
    texts = {fn: open(os.path.join(SRC, fn), encoding="utf-8",
                      errors="replace").read().lower()
             for fn in table_files}
    all_names = {v["name"] for v in isa.values()} | \
        {v["name"] for v in po.values()}
    absences = []
    for probe in ABSENCE_PROBES:
        hits = {fn: texts[fn].count(probe) for fn in table_files}
        absences.append(OrderedDict([
            ("probe", probe), ("total_hits", sum(hits.values())),
            ("exact_concept_exists", probe in all_names),
            ("hits_by_table", hits)]))
    absent = [a["probe"] for a in absences if a["total_hits"] == 0]
    present = [a["probe"] for a in absences if a["total_hits"] > 0]

    # TotalSegmentator endocrine labels (M3 census in labels.md:
    # exactly 2 of the 104 labels are endocrine — the adrenal
    # glands; there is no pituitary, pineal, thyroid or
    # parathyroid label, and the pancreas label belongs to the
    # digestive census)
    ts_labels = [
        ("adrenal_gland_right", ["adrenal-gland.right-adrenal-gland"], ""),
        ("adrenal_gland_left", ["adrenal-gland.left-adrenal-gland"], ""),
    ]
    rec_ids = {r["record_id"] for r in records}
    ts_missing = [lbl for lbl, ids, _ in ts_labels
                  if not all(i in rec_ids for i in ids)]

    xref_counts = Counter(cross_ref(c) for c in universe
                          if cross_ref(c))
    inv_doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA endocrine system inventory — "
                      "Milestone 13"),
            ("generated_by", "tools/endo_map.py"),
            ("source_tables", "data/sources/bodyparts3d-4.0/ (BP3D "
                              "4.0 / FMA concept ids and names as "
                              "released)"),
            ("counting_convention",
             "One record for the pituitary gland, keyed on its "
             "both-table concept; one record per adrenal gland "
             "instance, keyed on its instance concept with the "
             "side-stripped class concept carried as "
             "class_concept_id. The endocrine system root is a "
             "grouping class, censused but not a record. The "
             "pineal body (nervous module's record), the pancreas "
             "(digestive module's record) and the testis line "
             "(reproductive module, queued) are cross-references, "
             "censused but never records here. The thyroid and "
             "parathyroid glands and the pancreatic islets have "
             "no concept in the release at all and so have no "
             "inventory row; they exist only as sourced clinical "
             "records with the absence recorded (the Milestone 9 "
             "pattern)."),
            ("concept_universe", OrderedDict([
                ("total", len(universe)),
                ("isa_total", len(isa_universe)),
                ("partof_total", len(po_universe)),
                ("in_both_tables", len(isa_universe & po_universe)),
                ("isa_sets", {k: len(v) for k, v in isa_sets.items()}),
                ("partof_sets", {k: len(v)
                                 for k, v in po_sets.items()}),
                ("cross_references", dict(xref_counts)),
                ("dispositions", dict(disp_counts)),
                ("disposition_concepts",
                 {k: v for k, v in sorted(disp_lists.items())}),
                ("sweep_rejected_names", sweep_rejected),
            ])),
            ("record_count", len(records)),
            ("record_representations", dict(repr_counts)),
            ("records_by_subtree",
             dict(Counter(r["subtree"] for r in records))),
            ("instance_records", instance_made),
            ("organ_records", organ_made),
            ("totalsegmentator_overlap", OrderedDict([
                ("note", "of the 104 TotalSegmentator v1 labels "
                         "(Milestone 3 census), exactly two are "
                         "endocrine: adrenal_gland_right and "
                         "adrenal_gland_left, each present in all "
                         "1,204 subjects. TS v1 has no pituitary, "
                         "pineal, thyroid or parathyroid label; the "
                         "pancreas label maps to the digestive "
                         "module's record, cross-referenced here."),
                ("labels", [OrderedDict([("label", l),
                                         ("inventory_record_ids", ids),
                                         ("note", n)])
                            for l, ids, n in ts_labels]),
                ("labels_without_records", ts_missing),
            ])),
            ("absences", OrderedDict([
                ("note", "probe-based gap analysis: each probe name "
                         "was counted over all six BP3D 4.0 release "
                         "tables. Zero hits = the name does not occur "
                         "in the release."),
                ("absent", absent),
                ("present", present),
                ("detail", absences),
            ])),
        ])),
        ("concepts", concepts),
        ("records", records),
    ])
    os.makedirs(os.path.dirname(OUT_INV), exist_ok=True)
    with open(OUT_INV, "w") as f:
        json.dump(inv_doc, f, indent=1, sort_keys=False)

    # ---- geometry ------------------------------------------------------
    stats_cache = {}

    def stats_for(tree, fj):
        key = (tree, fj)
        if key not in stats_cache:
            d = ISA_DIR if tree == "isa" else PO_DIR
            stats_cache[key] = obj_stats(os.path.join(d, fj + ".obj"))
        return stats_cache[key]

    def mesh_list(tree_name, elem_map, base_dir, cids):
        out = []
        seen = set()
        for cid in cids:
            for fj in sorted(elem_map.get(cid, [])):
                if (tree_name, fj) in seen:
                    continue
                seen.add((tree_name, fj))
                st = stats_for(tree_name, fj)
                out.append(OrderedDict([
                    ("fj", fj),
                    ("path", os.path.relpath(
                        os.path.join(base_dir, fj + ".obj"), ROOT)),
                    ("vertices", st["vertices"]),
                    ("faces", st["faces"]),
                    ("bbox", st["bbox"])]))
        return out

    def totals(meshes):
        return {"files": len(meshes),
                "vertices": sum(m["vertices"] for m in meshes),
                "faces": sum(m["faces"] for m in meshes)}

    def union_bbox(meshes):
        if not meshes:
            return None
        mn = [min(m["bbox"]["min"][i] for m in meshes)
              for i in range(3)]
        mx = [max(m["bbox"]["max"][i] for m in meshes)
              for i in range(3)]
        return {"min": mn, "max": mx}

    geo_records = []
    covered = 0
    for rec in records:
        cids = rec["concept_ids"]
        isa_meshes = mesh_list("isa", isa_elem, ISA_DIR, cids)
        po_meshes = mesh_list("partof", po_elem, PO_DIR, cids)
        if isa_meshes or po_meshes:
            covered += 1
        names = []
        for c in cids:
            names.append(isa[c]["name"] if c in isa else po[c]["name"])
        geo_records.append(OrderedDict([
            ("record_id", rec["record_id"]),
            ("name", rec["name"]),
            ("side", rec["side"]),
            ("representation", rec["representation"]),
            ("concept_ids", cids),
            ("concept_names", names),
            ("isa_meshes", isa_meshes),
            ("partof_meshes", po_meshes),
            ("totals", {"isa": totals(isa_meshes),
                        "partof": totals(po_meshes),
                        "combined_files": len(
                            {m["fj"] for m in isa_meshes} |
                            {m["fj"] for m in po_meshes})}),
            ("bbox_isa", union_bbox(isa_meshes)),
            ("bbox_partof", union_bbox(po_meshes))]))

    geo_doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA endocrine system geometry "
                      "resolution — Milestone 13"),
            ("generated_by", "tools/endo_map.py"),
            ("paths", "mesh paths are relative to the project "
                      "root; meshes are the extracted BP3D 4.0 "
                      "working copies under work/bp3d/ (sources in "
                      "data/sources/ stay byte-identical)"),
            ("units", "source coordinates are millimetres (OBJ "
                      "headers; verified in Milestone 2)"),
            ("counting", "vertices = lines starting 'v ', faces = "
                         "lines starting 'f ', counted by "
                         "streaming each file; bbox measured from "
                         "the same vertex stream"),
            ("coverage", OrderedDict([
                ("records", len(records)),
                ("records_with_meshes", covered),
                ("records_without_meshes", len(records) - covered),
            ])),
        ])),
        ("records", geo_records),
    ])
    with open(OUT_GEO, "w") as f:
        json.dump(geo_doc, f, indent=1, sort_keys=False)

    print("isa sets:", {k: len(v) for k, v in isa_sets.items()})
    print("po sets:", {k: len(v) for k, v in po_sets.items()})
    print("concept universe:", len(universe), "| isa:", len(isa_universe),
          "| po:", len(po_universe),
          "| both:", len(isa_universe & po_universe))
    print("cross references:", dict(xref_counts))
    print("dispositions:", dict(disp_counts))
    print("records:", len(records), dict(repr_counts))
    print("instance records:", instance_made)
    print("organ records:", organ_made)
    print("sweep rejected (%d):" % len(sweep_rejected), sweep_rejected)
    print("geometry coverage: %d/%d records have meshes"
          % (covered, len(records)))
    print("TS labels without records:", ts_missing)
    print("absent probes (%d):" % len(absent), absent)
    print("present probes (%d):" % len(present), present)
    print(f"wrote {OUT_INV}")
    print(f"wrote {OUT_GEO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
