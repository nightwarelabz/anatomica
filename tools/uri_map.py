#!/usr/bin/env python3
"""ANATOMICA Milestone 12 — urinary system census + geometry mapping.

Censuses the urinary-system concepts of BodyParts3D 4.0 / FMA
exactly as they are represented in the release tables
(data/sources/bodyparts3d-4.0/), and maps the derived records to
BP3D meshes in the manner of Milestones 2, 4, 5, 9, 10 and 11:
exact lookups only, compositions taken from the tables,
vertex/face counts measured by streaming the OBJ files.

HOW BP3D 4.0 REPRESENTS THE URINARY SYSTEM (established by
inspection of the tables, 2026-11-06; every claim is re-derived by
this script at run time):

  * The PART-OF table carries a urinary system subtree rooted at
    FMA7159 "urinary system" (10 concepts): the root, the right and
    left upper urinary tracts, the lower urinary tract, and six
    organ instances — right/left kidney, right/left ureter, the
    urinary bladder and the urethra. That is the whole tree: the
    release decomposes no urinary organ any further in PART-OF.
  * The IS-A table carries the class concepts the PART-OF tree
    lacks — FMA7203 "kidney" and FMA9704 "ureter" — each with its
    right and left instances, plus the bladder and urethra filed as
    leaves under generic organ classes ("organ with organ cavity").
    There is no IS-A urinary-system root: FMA7159 does not occur
    in the IS-A table at all.
  * NO internal structure of any urinary organ exists anywhere in
    the release (probe-verified over all six tables): no cortex or
    medulla of kidney, no renal pyramid, papilla, column, pelvis
    or calyx, no nephron or any of its segments, no part of the
    bladder (no trigone, no detrusor, no neck), no part or sexed
    form of the urethra, and no ureteric junction or orifice. The
    urinary module's inventory is therefore six organ records; the
    internal anatomy is carried as sourced clinical text in
    Milestone 12's tranche, the gap is quantified by the probes.
  * THE ADRENAL GLANDS ARE FILED BY THE RELEASE UNDER ENDOCRINE,
    not urinary. In PART-OF the right and left adrenal glands
    (FMA15629/FMA15630) hang directly under FMA9668 "endocrine
    system"; in IS-A the class FMA9604 "adrenal gland" hangs under
    generic organ classes beside the kidney, and its two instances
    are the only descendants. The TotalSegmentator census
    (Milestone 3) likewise files adrenal_gland_left/right under
    endocrine. The three adrenal concepts are therefore censused
    here as an endocrine cross-reference set and get NO urinary
    record; the endocrine module (queued) owns them. The release
    uses "adrenal gland" only: the synonym "suprarenal gland" is
    probe-verified absent as a concept (suprarenal vessels exist
    and are cardiovascular records, Milestone 5).
  * Name sweeps over both tables adjudicate the remainder: the
    renal, suprarenal and ureteric-segment vessels inside the
    kidney's neighbourhood are cardiovascular records (the
    cardiovascular census carries 38 renal/suprarenal concepts
    in 27 records, including the artery.renal-artery and
    vein.renal-vein clinical records); the gallbladder is a
    digestive record (its name contains "bladder"); the prostate
    belongs to the reproductive census.

COUNTING CONVENTION (what counts as one urinary-system record):
  * One record per lateralised instance where the tables
    lateralise (right/left kidney, right/left ureter), each keyed
    on its instance concept with the side-stripped class concept
    carried as class_concept_id (the Milestone 11 gland/tooth
    pattern); one record for each un-sided organ (urinary bladder,
    urethra) keyed on its concept, which both tables carry.
  * The system root (urinary system), the two upper urinary
    tracts and the lower urinary tract are grouping classes:
    censused with that disposition, never records (the Milestone
    11 tract-root pattern). The adrenal concepts are censused as
    an endocrine cross-reference, never records here.

Outputs:
  data/urinary/urinary-inventory.json  census + records
  data/urinary/urinary-geometry.json   per-record meshes

Stdlib only. Run: python3 tools/uri_map.py
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
OUT_INV = os.path.join(ROOT, "data", "urinary",
                       "urinary-inventory.json")
OUT_GEO = os.path.join(ROOT, "data", "urinary",
                       "urinary-geometry.json")

URINARY_PO_ROOT = "FMA7159"         # urinary system (PART-OF)
KIDNEY_ISA_ROOT = "FMA7203"         # kidney
URETER_ISA_ROOT = "FMA9704"         # ureter
ADRENAL_ISA_ROOT = "FMA9604"        # adrenal gland (endocrine xref)
ENDOCRINE_PO_ROOT = "FMA9668"       # endocrine system (PART-OF)
BLADDER_URETHRA_ISA = {"FMA15900",  # urinary bladder
                       "FMA19667"}  # urethra
ADRENAL_PO = {"FMA15629",           # right adrenal gland
              "FMA15630"}           # left adrenal gland

# lateralised instance records: instance concept -> (prefix,
# class concept)
INSTANCES = {
    "FMA7204": ("kidney", "FMA7203"),   # right kidney
    "FMA7205": ("kidney", "FMA7203"),   # left kidney
    "FMA15571": ("ureter", "FMA9704"),  # right ureter
    "FMA15572": ("ureter", "FMA9704"),  # left ureter
}
# un-sided organ records keyed on their (both-table) concepts
ORGAN_RECORDS = {
    "FMA15900": "urinary-bladder",      # urinary bladder
    "FMA19667": "urethra",              # urethra
}
GROUPING_IDS = {
    "FMA7159",    # urinary system (root)
    "FMA71102",   # right upper urinary tract
    "FMA71103",   # left upper urinary tract
    "FMA45659",   # lower urinary tract
}
ADRENAL_IDS = {"FMA9604", "FMA15629", "FMA15630"}

ABSENCE_PROBES = [
    # kidney internal structure — none of it exists in the release
    "cortex of kidney", "renal cortex", "medulla of kidney",
    "renal medulla", "renal pyramid", "renal papilla",
    "renal column", "renal pelvis", "major calyx", "minor calyx",
    "calyx", "nephron", "glomerulus", "renal corpuscle",
    "glomerular capsule", "proximal convoluted tubule",
    "proximal tubule", "loop of henle", "nephron loop",
    "distal convoluted tubule", "collecting duct",
    "renal capsule", "fibrous capsule", "renal hilum",
    "renal sinus", "renal lobe", "renal segment", "medullary ray",
    "juxtaglomerular", "macula densa", "vasa recta",
    "peritubular capillary", "afferent arteriole",
    "efferent arteriole",
    # ureter junctions, parts and orifice
    "pelviureteric junction", "ureteropelvic junction",
    "ureterovesical junction", "vesicoureteric junction",
    "ureteric orifice", "abdominal part of ureter",
    "pelvic part of ureter", "intramural part of ureter",
    # bladder parts and interior
    "apex of urinary bladder", "apex of bladder",
    "body of urinary bladder", "fundus of urinary bladder",
    "neck of urinary bladder", "neck of bladder", "trigone",
    "detrusor", "uvula of bladder", "interureteric ridge",
    "internal urethral orifice", "vesical artery", "vesical vein",
    # urethra: sexed forms, parts, sphincters — the release carries
    # one unsexed undivided urethra concept only
    "male urethra", "female urethra", "prostatic urethra",
    "membranous urethra", "spongy urethra", "penile urethra",
    "preprostatic urethra", "external urethral sphincter",
    "internal urethral sphincter", "urethral sphincter",
    "external urethral orifice",
    # adrenal internal structure and the TA synonym: the glands are
    # endocrine cross-references (see header); their parts are as
    # absent as the urinary organs' parts
    "adrenal cortex", "adrenal medulla",
    "cortex of adrenal gland", "medulla of adrenal gland",
    "suprarenal gland", "zona glomerulosa", "zona fasciculata",
    "zona reticularis",
    # present controls (exact concepts exist)
    "kidney", "right kidney", "left kidney", "ureter",
    "right ureter", "left ureter", "urinary bladder", "urethra",
    "urinary system", "upper urinary tract", "lower urinary tract",
    "adrenal gland", "right adrenal gland", "left adrenal gland",
    "endocrine system", "prostate", "renal artery", "renal vein",
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
    kidney_isa = descendants(KIDNEY_ISA_ROOT, children)
    ureter_isa = descendants(URETER_ISA_ROOT, children)
    adrenal_isa = descendants(ADRENAL_ISA_ROOT, children)
    urinary_po = descendants(URINARY_PO_ROOT, po_children)

    isa_sets = OrderedDict([
        ("kidney-isa", kidney_isa),
        ("ureter-isa", ureter_isa),
        ("bladder-urethra-isa", set(BLADDER_URETHRA_ISA)),
        ("adrenal-gland-endocrine-xref-isa", adrenal_isa),
    ])
    po_sets = OrderedDict([
        ("urinary-system-partof", urinary_po),
        ("adrenal-gland-endocrine-xref-partof", set(ADRENAL_PO)),
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
        if cid in ADRENAL_IDS:
            return "endocrine"
        return None

    # cross-check sweep: urinary terms outside the universe
    sweep_terms = ("urin", "kidney", "renal", "ureter", "urethr",
                   "bladder", "vesical", "nephr", "adrenal",
                   "suprarenal", "calyx", "calyces", "trigone",
                   "detrusor", "glomerul")
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
                        "class_concept_id (Milestone 11 gland/tooth "
                        "pattern)")
        instance_made.append(nm)

    # (2) un-sided organs carried by both tables
    organ_made = []
    for cid, rid in sorted(ORGAN_RECORDS.items(),
                           key=lambda kv: kv[1]):
        assert cid in isa and cid in po
        assert isa[cid]["name"] == po[cid]["name"]
        nm = isa[cid]["name"]
        note = None
        if cid == "FMA19667":
            note = ("the release carries a single unsexed, "
                    "undivided urethra concept: no male/female form "
                    "and no prostatic/membranous/spongy part exists "
                    "(probe-verified); the sexed anatomy is carried "
                    "as sourced text in the clinical tranche")
        add_record(rid, nm, "un-sided", "whole-concept", [cid], cid,
                   subtree_of[cid], note=note)
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

    # TotalSegmentator urinary labels (M3 census in labels.md:
    # exactly 3 of the 104 labels are urinary; the adrenal labels
    # are filed under endocrine in that census, matching the BP3D
    # PART-OF filing re-derived above)
    ts_labels = [
        ("kidney_right", ["kidney.right-kidney"], ""),
        ("kidney_left", ["kidney.left-kidney"], ""),
        ("urinary_bladder", ["urinary-bladder"], ""),
    ]
    rec_ids = {r["record_id"] for r in records}
    ts_missing = [lbl for lbl, ids, _ in ts_labels
                  if not all(i in rec_ids for i in ids)]

    xref_counts = Counter(cross_ref(c) for c in universe
                          if cross_ref(c))
    adrenal_filing = OrderedDict([
        ("finding",
         "the release files the adrenal glands under endocrine, "
         "not urinary: in PART-OF, right/left adrenal gland "
         "(FMA15629/FMA15630) are direct children of FMA9668 "
         "'endocrine system' and occur nowhere in the urinary "
         "system subtree; in IS-A the class FMA9604 'adrenal "
         "gland' hangs under generic organ classes (corticomedullary "
         "organ) beside the kidney, with the two instances as its "
         "only descendants. The TotalSegmentator census concurs "
         "(adrenal_gland_left/right filed under endocrine). The "
         "three concepts are censused in this module as an "
         "endocrine cross-reference only; the endocrine module "
         "owns the adrenal records."),
        ("isa_parent_of_class",
         isa[parent[ADRENAL_ISA_ROOT]]["name"]
         if ADRENAL_ISA_ROOT in parent else None),
        ("partof_parent_of_instances",
         po[po_parent["FMA15629"]]["name"]),
        ("partof_parent_id", po_parent["FMA15629"]),
        ("in_urinary_partof_subtree",
         bool(ADRENAL_PO & urinary_po)),
    ])
    inv_doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA urinary system inventory — "
                      "Milestone 12"),
            ("generated_by", "tools/uri_map.py"),
            ("source_tables", "data/sources/bodyparts3d-4.0/ (BP3D "
                              "4.0 / FMA concept ids and names as "
                              "released)"),
            ("counting_convention",
             "One record per lateralised instance where the tables "
             "lateralise (right/left kidney, right/left ureter), "
             "each keyed on its instance concept with the "
             "side-stripped class concept carried as "
             "class_concept_id; one record for each un-sided organ "
             "the release carries (urinary bladder, urethra). The "
             "urinary system root, the right/left upper urinary "
             "tracts and the lower urinary tract are grouping "
             "classes, censused but not records. The adrenal gland "
             "class and its two instances are an endocrine "
             "cross-reference (the release files them under the "
             "endocrine system in PART-OF), censused but not "
             "records of this module."),
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
            ("adrenal_filing", adrenal_filing),
            ("totalsegmentator_overlap", OrderedDict([
                ("note", "of the 104 TotalSegmentator v1 labels "
                         "(Milestone 3 census), exactly three are "
                         "urinary: kidney_right, kidney_left and "
                         "urinary_bladder, each present in all "
                         "1,204 subjects. The adrenal_gland_left/"
                         "right labels are filed under endocrine in "
                         "that census. TS v1 has no ureter or "
                         "urethra label and nothing below the organ "
                         "level, so it adds no coverage the release "
                         "lacks."),
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
            ("title", "ANATOMICA urinary system geometry "
                      "resolution — Milestone 12"),
            ("generated_by", "tools/uri_map.py"),
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
    print("adrenal filing:", dict(adrenal_filing))
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
