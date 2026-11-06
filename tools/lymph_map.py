#!/usr/bin/env python3
"""ANATOMICA Milestone 13 — lymphatic system census + geometry
mapping.

Censuses the lymphatic-system concepts of BodyParts3D 4.0 / FMA
exactly as they are represented in the release tables
(data/sources/bodyparts3d-4.0/), and maps the derived records to
BP3D meshes in the manner of Milestones 2, 4, 5, 9, 10, 11 and
12: exact lookups only, compositions taken from the tables,
vertex/face counts measured by streaming the OBJ files.

HOW BP3D 4.0 REPRESENTS THE LYMPHATIC SYSTEM (established by
inspection of the tables, 2026-11-06; every claim is re-derived
by this script at run time):

  * THE WORD "lymph" DOES NOT OCCUR IN THE RELEASE. Neither
    parts list contains a single name with the substring "lymph":
    there is no lymphatic system root in either table, no lymph
    node, no lymphatic vessel, trunk or duct, no tonsil, no
    lymphoid tissue concept of any kind. The thoracic duct —
    probe-verified absent by Milestone 5 against the same tables
    — is re-verified here. The entire conducting and filtering
    apparatus of the system is missing as data.
  * What the release does carry, it files elsewhere. The SPLEEN
    (FMA7196) exists in IS-A only, as a leaf under the generic
    class "corticomedullary organ"; it occurs nowhere in the
    PART-OF table. The THYMUS exists as an organ only in PART-OF
    (FMA9607), where it hangs under "content of anterior
    mediastinum" — not under any lymphatic root, there being
    none — with its two lobes (FMA71194/FMA71195) as its only
    parts; the IS-A table carries the lobe line only (class
    FMA71193 "lobe of thymus" with the two instances), and no
    thymus organ concept at all.
  * Bone marrow — the other primary lymphoid organ — is as
    absent as the nodes: "marrow" scores zero hits in both parts
    lists. Peyer's patches, the adenoid and every other MALT
    structure are likewise absent. The vermiform appendix
    (FMA14542 "appendix") exists, but it is a digestive record
    (Milestone 11); it is adjudicated in the sweep below, not
    claimed here.
  * Name sweeps over both tables adjudicate the remainder: the
    only names outside the universe that touch the system are
    the splenic vessels (cardiovascular records, Milestone 5:
    artery.splenic-artery and vein.splenic-vein clinical
    records) and the appendix (digestive).

COUNTING CONVENTION (what counts as one lymphatic-system
record):
  * One record for the spleen, keyed on its IS-A concept — the
    release carries it nowhere else.
  * One record for the thymus as an organ, keyed on its PART-OF
    concept (the Milestone 9 partof-organ pattern: the brain and
    spinal cord are keyed the same way, on the table that
    carries the organ).
  * One record per lateralised thymus lobe, keyed on its
    instance concept with the side-stripped class concept
    carried as class_concept_id (the Milestone 12 instance
    pattern). The lobes are parts of the thymus in PART-OF and
    instances of the lobe class in IS-A; both tables carry them.

Outputs:
  data/lymphatic/lymphatic-inventory.json  census + records
  data/lymphatic/lymphatic-geometry.json   per-record meshes

Stdlib only. Run: python3 tools/lymph_map.py
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
OUT_INV = os.path.join(ROOT, "data", "lymphatic",
                       "lymphatic-inventory.json")
OUT_GEO = os.path.join(ROOT, "data", "lymphatic",
                       "lymphatic-geometry.json")

SPLEEN_ISA = "FMA7196"              # spleen (IS-A only)
THYMUS_LOBE_ISA = "FMA71193"        # lobe of thymus (IS-A line)
THYMUS_PO = "FMA9607"               # thymus (PART-OF organ)

# lateralised lobe records: instance concept -> (prefix, class)
INSTANCES = {
    "FMA71194": ("thymus-lobe", "FMA71193"),  # right lobe of thymus
    "FMA71195": ("thymus-lobe", "FMA71193"),  # left lobe of thymus
}

ABSENCE_PROBES = [
    # the conducting system — none of it exists in the release
    "lymph", "lymphatic system", "lymph node", "lymphatic vessel",
    "lymphatic trunk", "lymphatic duct", "thoracic duct",
    "right lymphatic duct", "cisterna chyli", "lymphatic capillary",
    "lymph vessel", "lymphoid", "lymphatic follicle",
    "aggregated lymphatic follicle", "solitary lymphatic follicle",
    "superficial lymphatic", "deep lymphatic",
    # named node groups — none exists
    "cervical lymph node", "axillary lymph node",
    "inguinal lymph node", "mesenteric lymph node",
    "bronchopulmonary lymph node", "pancreaticosplenic",
    "coeliac lymph node", "lumbar lymph node",
    # tonsils and MALT — none exists
    "tonsil", "palatine tonsil", "pharyngeal tonsil",
    "lingual tonsil", "adenoid", "peyer",
    "mucosa-associated lymphoid tissue",
    # bone marrow — the other primary lymphoid organ
    "marrow", "bone marrow", "red bone marrow",
    "yellow bone marrow",
    # spleen interior — the organ exists, its parts do not
    "splenic pulp", "red pulp", "white pulp", "splenic hilum",
    "trabecula of spleen",
    # thymus interior — lobes exist, lobules and zones do not
    "lobule of thymus", "cortex of thymus", "medulla of thymus",
    # present controls (exact concepts exist)
    "spleen", "thymus", "lobe of thymus", "right lobe of thymus",
    "left lobe of thymus", "splenic artery", "splenic vein",
    "appendix",
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
    spleen_isa = descendants(SPLEEN_ISA, children)
    thymus_lobe_isa = descendants(THYMUS_LOBE_ISA, children)
    thymus_po = descendants(THYMUS_PO, po_children)

    isa_sets = OrderedDict([
        ("spleen-isa", spleen_isa),
        ("thymus-lobe-isa", thymus_lobe_isa),
    ])
    po_sets = OrderedDict([
        ("thymus-partof", thymus_po),
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

    # cross-check sweep: lymphatic terms outside the universe
    sweep_terms = ("lymph", "spleen", "splenic", "thymus", "thymic",
                   "tonsil", "marrow", "peyer")
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

    # (1) the spleen: an IS-A-only whole organ
    add_record("spleen", isa[SPLEEN_ISA]["name"], "un-sided",
               "whole-concept", [SPLEEN_ISA], SPLEEN_ISA,
               subtree_of[SPLEEN_ISA],
               note="the release carries the spleen in IS-A only, "
                    "as a leaf under the generic class "
                    "'corticomedullary organ'; it occurs nowhere "
                    "in the PART-OF table, and no part of it "
                    "(pulp, hilum, trabecula) exists as a concept "
                    "(probe-verified)")
    # (2) the thymus: a PART-OF-only organ
    add_record("thymus", po[THYMUS_PO]["name"], "un-sided",
               "partof-organ", [THYMUS_PO], None,
               subtree_of[THYMUS_PO],
               note="the release carries the thymus as an organ "
                    "in PART-OF only, filed under 'content of "
                    "anterior mediastinum'; the IS-A table carries "
                    "no thymus organ concept, only the lobe line "
                    "below")
    # (3) lateralised lobe instances (class carried)
    instance_made = []
    for cid, (prefix, class_id) in sorted(
            INSTANCES.items(), key=lambda kv: isa[kv[0]]["name"]):
        assert cid in isa and class_id in isa
        nm = isa[cid]["name"]
        add_record(prefix + "." + slug(nm), nm, side_of(nm),
                   "whole-concept", [cid], class_id, subtree_of[cid],
                   note="lateralised instance; the side-stripped "
                        "class concept is carried as "
                        "class_concept_id (Milestone 12 pattern). "
                        "The instance is a part of the thymus in "
                        "PART-OF and an instance of the lobe class "
                        "in IS-A")
        instance_made.append(nm)

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
            ("cross_reference", None),
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

    # TotalSegmentator lymphatic labels (M3 census in labels.md:
    # exactly 1 of the 104 labels is lymphatic — spleen; there is
    # no thymus, node, vessel or duct label)
    ts_labels = [
        ("spleen", ["spleen"], ""),
    ]
    rec_ids = {r["record_id"] for r in records}
    ts_missing = [lbl for lbl, ids, _ in ts_labels
                  if not all(i in rec_ids for i in ids)]

    inv_doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA lymphatic system inventory — "
                      "Milestone 13"),
            ("generated_by", "tools/lymph_map.py"),
            ("source_tables", "data/sources/bodyparts3d-4.0/ (BP3D "
                              "4.0 / FMA concept ids and names as "
                              "released)"),
            ("counting_convention",
             "One record for the spleen, keyed on its IS-A "
             "concept — the only table that carries it. One "
             "record for the thymus as an organ, keyed on its "
             "PART-OF concept (the Milestone 9 partof-organ "
             "pattern). One record per lateralised thymus lobe, "
             "keyed on its instance concept with the side-stripped "
             "class concept carried as class_concept_id (the "
             "Milestone 12 instance pattern). There is no "
             "lymphatic system root in the release to census as a "
             "grouping class: the string 'lymph' occurs in no "
             "concept name in either table."),
            ("concept_universe", OrderedDict([
                ("total", len(universe)),
                ("isa_total", len(isa_universe)),
                ("partof_total", len(po_universe)),
                ("in_both_tables", len(isa_universe & po_universe)),
                ("isa_sets", {k: len(v) for k, v in isa_sets.items()}),
                ("partof_sets", {k: len(v)
                                 for k, v in po_sets.items()}),
                ("cross_references", {}),
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
            ("totalsegmentator_overlap", OrderedDict([
                ("note", "of the 104 TotalSegmentator v1 labels "
                         "(Milestone 3 census), exactly one is "
                         "lymphatic: spleen, present in all 1,204 "
                         "subjects. TS v1 has no thymus label and "
                         "no node, vessel, trunk or duct label, so "
                         "it adds no coverage the release lacks."),
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
            ("title", "ANATOMICA lymphatic system geometry "
                      "resolution — Milestone 13"),
            ("generated_by", "tools/lymph_map.py"),
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
    print("dispositions:", dict(disp_counts))
    print("records:", len(records), dict(repr_counts))
    print("instance records:", instance_made)
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
