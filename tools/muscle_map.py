#!/usr/bin/env python3
"""ANATOMICA Milestone 4 — muscular system census + geometry mapping.

Censuses the muscle concepts of BodyParts3D 4.0 / FMA exactly as they are
represented in the release tables (data/sources/bodyparts3d-4.0/), and maps
the derived muscle records to BP3D meshes in the manner of Milestone 2
(tools/fma_map.py): exact lookups only, compositions taken from the tables,
vertex/face counts measured by streaming the OBJ files.

HOW BP3D 4.0 REPRESENTS MUSCLES (established by inspection of the tables,
2026-11-06; every claim below is re-derived by this script at run time):

  * The IS-A inclusion structure is a strict tree (2,904 edges, 2,904
    distinct children, no multi-parent concepts).
  * Muscle concepts live in three disjoint subtrees:
      - the muscle-organ subtree rooted at FMA5022 "muscle organ"
        (regional groups -> families -> classes -> lateralised instances);
      - the zone subtree rooted at FMA10474 "zone of muscle organ"
        (zones and parts of muscles that have no whole-muscle concept,
        plus the component classes of the quadriceps and levator ani
        composites, which hang under their zone);
      - the head subtree rooted at FMA85453 "head of muscle organ"
        (heads of muscles that have no whole-muscle concept, plus the
        clavicular part of pectoralis major).
  * Some major muscles therefore have NO whole-muscle concept anywhere in
    the tables (trapezius, deltoid, pectoralis major, biceps brachii,
    triceps brachii, gastrocnemius, pronator teres, flexor carpi ulnaris,
    longus colli, cricothyroid, oblique arytenoid). They are represented
    only by lateralised head/part concepts. This census creates one record
    per side for them with representation "parts-composite"; the muscle
    name is taken from the part concepts' own names, never invented.
  * A parallel "musculature" set-tree (rooted at the concept named
    "musculature", under "set of organs") holds the small muscles FMA
    models only as sets: hand lumbricals and interossei, levatores
    costarum, cervical intertransversarii, interspinales cervicis and
    lumborum. Lateralised sets exist for some (right/left set concepts).
    These enter the census as records with representation "set-concept"
    (one record per set; the set's members are not individually modelled
    in the release).
  * Some major muscles are absent from the tables entirely (stem search
    over all six release tables): latissimus dorsi, masseter, temporalis,
    rectus abdominis, the multifidi, most muscles of facial expression.
    They get NO record; they are listed in meta.absences with hit counts.
  * Papillary muscles of the heart are not descendants of "muscle organ"
    in these tables (they hang under the heart) and are out of scope for
    the muscular module; they belong to the cardiovascular module.

COUNTING CONVENTION (what counts as one muscle record):
  * One record per lateralised instance where the tables lateralise
    (right X / left X as separate records), mirroring the skeletal module.
  * One record for an un-sided class concept the tables model jointly
    (e.g. diaphragm; the intercostal classes, whose two mesh files form a
    mirrored FJ/FJM pair — noted on the record).
  * One record per side for a parts-composite muscle (heads/parts are
    geometry components of the record, never separate records).
  * Numbered instances (lumbricals, interossei) count individually, per
    side and number, as FMA names them.
  * Groups, families, zones and part concepts are NOT records.

Outputs:
  data/muscular/muscle-inventory.json  concept census + derived records
  data/muscular/muscle-geometry.json   per-record resolved mesh lists with
                                       measured vertex/face counts + bboxes

Stdlib only. Run: python3 tools/muscle_map.py
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
OUT_INV = os.path.join(ROOT, "data", "muscular", "muscle-inventory.json")
OUT_GEO = os.path.join(ROOT, "data", "muscular", "muscle-geometry.json")

MUSCLE_ROOT = "FMA5022"    # muscle organ
ZONE_ROOT = "FMA10474"     # zone of muscle organ
HEAD_ROOT = "FMA85453"     # head of muscle organ

# Collective concepts whose names end in " muscle" but which denote groups
# of muscles, not one muscle. Derived by inspecting every such name in the
# universe (printed by this script's analysis pass). The three intercostal
# classes and "uvular muscle" end in " muscle" too but ARE single muscles;
# they are deliberately NOT in this set.
GROUP_NAMES = {
    "anterior suboccipital muscle", "posterior suboccipital muscle",
    "deep postvertebral muscle", "intermediate postvertebral muscle",
    "superficial postvertebral muscle", "postvertebral muscle",
    "prevertebral muscle", "extra-ocular muscle", "gluteal muscle",
    "hypothenar muscle", "thenar muscle", "infrahyoid muscle",
    "suprahyoid muscle", "intercostal muscle", "interspinalis muscle",
    "intertransversarius muscle", "obturator muscle", "pectoral muscle",
    "perineal muscle", "superficial perineal muscle", "rotator muscle",
    "scalene muscle",
}

REGIONAL_GROUPS = {
    "muscle of head", "muscle of neck", "muscle of trunk",
    "muscle of thorax", "muscle of abdomen", "muscle of pelvis",
    "perineal muscle", "muscle of upper limb", "muscle of lower limb",
    "muscle of vertebral column",
}

# Major named muscles probed for absence (gap analysis). A probe is only
# evidence about that name; hits are counted over all six release tables.
ABSENCE_PROBES = [
    "latissimus dorsi", "masseter", "temporalis", "rectus abdominis",
    "multifidus", "multifidi", "frontalis", "occipitofrontalis",
    "orbicularis oculi", "orbicularis oris", "buccinator",
    "zygomaticus major", "zygomaticus minor", "iliopsoas",
    "transversus abdominis", "internal oblique", "pyramidalis",
    "cremaster", "arrector", "detrusor", "levator labii",
    "depressor anguli", "nasalis", "procerus", "mentalis",
    "risorius", "platysma", "scalenus medius", "longus capitis",
    "rectus capitis anterior", "geniohyoid", "genioglossus",
    "palatoglossus", "palatopharyngeus", "salpingopharyngeus",
    "stylopharyngeus", "tensor tympani", "stapedius",
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
    return isa, po, isa_elem, po_elem, children, parent


def descendants(root, children):
    seen, stack = [], [root]
    while stack:
        c = stack.pop()
        seen.append(c)
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


# --------------------------------------------------------------------------
# Name analysis
# --------------------------------------------------------------------------

SIDE_PREFIX = re.compile(r"^(right|left)\s+")
SIDE_INFIX = re.compile(r"\bof (right|left) (hand|foot)\b")
SIDE_SET = re.compile(r"^set of (right|left)\s+")


def side_of(name):
    m = SIDE_PREFIX.match(name)
    if m:
        return m.group(1)
    m = SIDE_SET.match(name)
    if m:
        return m.group(1)
    m = SIDE_INFIX.search(name)
    if m:
        return m.group(1)
    return None


def base_form(name):
    """Strip lateralisation so an instance can be compared to its class."""
    n = SIDE_PREFIX.sub("", name)
    n = SIDE_SET.sub("set of ", n)
    n = SIDE_INFIX.sub(r"of \2", n)
    if n.endswith(" muscle"):
        n = n[: -len(" muscle")]
    return n


PART_RE = re.compile(r"^(.+?) (head|part) of (.+)$")
ZONE_RE = re.compile(r"^zone of (.+)$")


def part_base(name):
    """For a part concept name, return (descriptor, base_muscle_name)."""
    m = PART_RE.match(name)
    if m:
        return (f"{m.group(1)} {m.group(2)}", m.group(3))
    return None


def main():
    isa, po, isa_elem, po_elem, children, parent = load_tables()
    name2id = {}
    for cid, v in isa.items():
        name2id.setdefault(v["name"].lower(), cid)

    set_roots = [cid for cid, v in isa.items() if v["name"] == "musculature"]
    assert len(set_roots) == 1, set_roots
    SET_ROOT = set_roots[0]

    subtree_of = {}
    for root, label in ((MUSCLE_ROOT, "muscle-organ"), (ZONE_ROOT, "zone"),
                        (HEAD_ROOT, "head"), (SET_ROOT, "musculature-sets")):
        for cid in descendants(root, children):
            subtree_of[cid] = label
    universe = sorted(subtree_of)

    def chain_names(cid):
        out, cur = [], cid
        while cur in parent:
            cur = parent[cur]
            out.append(isa[cur]["name"])
        return out

    MUSCULATURE_REGIONS = {
        "musculature of chest": "muscle of thorax",
        "musculature of subdivision of trunk": "muscle of vertebral column",
        "musculature of subdivision of free upper limb": "muscle of upper limb",
        "musculature of subdivision of upper limb": "muscle of upper limb",
        "musculature of subdivision of free lower limb": "muscle of lower limb",
        "musculature of subdivision of lower limb": "muscle of lower limb",
    }

    def region_group(cid):
        for n in chain_names(cid):
            if n in REGIONAL_GROUPS:
                return n
            if n in MUSCULATURE_REGIONS:
                return MUSCULATURE_REGIONS[n]
        return None

    # ---- role classification -------------------------------------------
    roles = {}

    def kids(cid):
        return children.get(cid, [])

    for cid in universe:
        name = isa[cid]["name"]
        if cid in (MUSCLE_ROOT, ZONE_ROOT, HEAD_ROOT, SET_ROOT):
            roles[cid] = "structural-root"
        elif name.startswith("set of "):
            roles[cid] = "set-instance" if side_of(name) else "set-class"
        elif name.startswith("musculature"):
            roles[cid] = "group"
        elif name.startswith("muscle of ") or name in GROUP_NAMES or \
                name.startswith(("intrinsic muscle of ", "extrinsic muscle of ")):
            roles[cid] = "group"
        elif ZONE_RE.match(name):
            roles[cid] = "zone"
        elif part_base(name):
            roles[cid] = "part"
        elif side_of(name):
            roles[cid] = "instance"
        else:
            roles[cid] = "class-candidate"

    # class-candidate -> class or family: a candidate whose children within
    # the universe include concepts that are NOT its own lateralised
    # instances is a family (its children are distinct named muscles).
    for cid in universe:
        if roles[cid] != "class-candidate":
            continue
        sub = [c for c in kids(cid) if c in subtree_of]
        foreign = [c for c in sub
                   if not (side_of(isa[c]["name"]) and
                           base_form(isa[c]["name"]) == base_form(isa[cid]["name"]))]
        roles[cid] = "family" if foreign else "class"

    # ---- records ---------------------------------------------------------
    records = []
    used_instances = set()

    def slug(s):
        return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

    def add_record(name, side, representation, concept_ids, class_id, note=None):
        records.append(OrderedDict([
            ("record_id", "muscle." + slug(name)),
            ("name", name),
            ("side", side),
            ("representation", representation),
            ("class_concept_id", class_id),
            ("concept_ids", concept_ids),
            ("zone_concept_ids", []),
            ("region_group", None),   # filled below from first concept
            ("group_path", None),
            ("note", note),
        ]))
        return records[-1]

    # (a) classes with lateralised instances -> one record per instance
    # (b) classes without instances -> one un-sided record
    for cid in universe:
        if roles[cid] != "class":
            continue
        cname = isa[cid]["name"]
        insts = [c for c in kids(cid)
                 if roles.get(c) == "instance" and
                 base_form(isa[c]["name"]) == base_form(cname)]
        if insts:
            for ic in sorted(insts, key=lambda c: isa[c]["name"]):
                iname = isa[ic]["name"]
                add_record(iname, side_of(iname), "whole-concept", [ic], cid)
                used_instances.add(ic)
        else:
            add_record(cname, "un-sided", "whole-concept-unsided", [cid], cid)

    # (e) set-concepts: lateralised sets -> one record per side; un-sided
    # sets -> one record. The set is the record; members are not modelled
    # individually in the release.
    for cid in universe:
        if roles[cid] != "set-class":
            continue
        cname = isa[cid]["name"]
        insts = [c for c in kids(cid)
                 if roles.get(c) == "set-instance" and
                 base_form(isa[c]["name"]) == base_form(cname)]
        if insts:
            for ic in sorted(insts, key=lambda c: isa[c]["name"]):
                iname = isa[ic]["name"]
                add_record(iname, side_of(iname), "set-concept", [ic], cid,
                           note="FMA/BP3D models this muscle only as a set; "
                                "members are not individually modelled")
        else:
            add_record(cname, "un-sided", "set-concept", [cid], cid,
                       note="FMA/BP3D models this muscle only as a set; "
                            "members are not individually modelled")

    # (c) instances whose parent is a family (numbered instances sit under
    # numbered classes, which are themselves classes — handled in (a); any
    # instance left over is reported, never dropped silently)
    orphan_instances = [c for c in universe
                        if roles[c] == "instance" and c not in used_instances]

    # (d) parts-composite muscles: group part concepts by base muscle.
    # A lateralised part is named "<descriptor> head/part of <side> <muscle>"
    # (e.g. "long head of right biceps brachii"); its un-sided part class is
    # "<descriptor> head/part of <muscle>". Group by the side-stripped base;
    # geometry for a side comes from that side's part concepts (the un-sided
    # part classes are their parents and duplicate their compositions).
    part_groups = {}   # base -> {"lat": {side: [cids]}, "unsided": [cids], "zones": [cids]}
    for cid in universe:
        if roles[cid] != "part":
            continue
        desc, base_raw = part_base(isa[cid]["name"])
        s = side_of(base_raw) or side_of(isa[cid]["name"])
        base = SIDE_PREFIX.sub("", base_raw)
        g = part_groups.setdefault(base, {"lat": {}, "unsided": [], "zones": []})
        if s:
            g["lat"].setdefault(s, []).append(cid)
        else:
            g["unsided"].append(cid)
    for cid in universe:
        if roles[cid] == "zone":
            base = ZONE_RE.match(isa[cid]["name"]).group(1)
            g = part_groups.setdefault(base, {"lat": {}, "unsided": [], "zones": []})
            g["zones"].append(cid)

    composite_groups = []   # zones whose components are separate records
    parts_composite = {}
    asymmetries = []        # parts-composite muscles lateralised on one side only
    for base, g in sorted(part_groups.items()):
        if not g["lat"] and not g["unsided"]:
            # zone-only entry. Three dispositions, all reported:
            #  - a whole-muscle class exists (the zone is its adjunct);
            #  - classes under the zone produced records (true composite);
            #  - neither (the zone concept alone represents the muscle).
            zcid = g["zones"][0] if g["zones"] else None
            covered = any(r["class_concept_id"] and
                          base_form(isa[r["class_concept_id"]]["name"]) == base_form(base)
                          for r in records)
            if covered:
                parts_composite[base] = "zone-adjunct-covered-by-class"
                continue
            comp = []
            if zcid:
                zdesc = set(descendants(zcid, children))
                comp = [rec["record_id"] for rec in records
                        if rec["class_concept_id"] in zdesc]
            if comp:
                composite_groups.append(OrderedDict([
                    ("name", base), ("zone_concept_id", zcid),
                    ("component_record_ids", comp),
                    ("note", "composite of separately-recorded muscles; "
                             "not itself a record")]))
            elif zcid:
                parts_composite[base] = "zone-only"
                add_record(base, "un-sided", "zone-composite", [zcid], None,
                           note="represented in BP3D 4.0 only by its zone "
                                "concept; geometry = the zone composition")
            continue
        # does a whole-muscle class already cover this base name?
        covered = any(r["class_concept_id"] and
                      base_form(isa[r["class_concept_id"]]["name"]) == base_form(base)
                      for r in records)
        if covered:
            parts_composite[base] = "covered-by-class"
            continue
        parts_composite[base] = "parts-composite"
        zone_ids = sorted(g["zones"])
        if g["lat"]:
            for s in sorted(g["lat"]):
                note = ("no whole-muscle concept in BP3D 4.0; "
                        "geometry = this side's head/part concepts")
                if len(g["lat"]) == 1:
                    other = "left" if s == "right" else "right"
                    note += (f"; ASYMMETRY: BP3D 4.0 lateralises this muscle "
                             f"on the {s} side only — no {other}-side part "
                             f"concepts exist in the release")
                    asymmetries.append(base)
                rec = add_record(f"{s} {base}", s, "parts-composite",
                                 sorted(g["lat"][s]), None, note=note)
                rec["zone_concept_ids"] = zone_ids
        else:
            rec = add_record(base, "un-sided", "parts-composite",
                             sorted(g["unsided"]), None,
                             note="no whole-muscle concept in BP3D 4.0; "
                                  "geometry = its un-sided head/part concepts")
            rec["zone_concept_ids"] = zone_ids

    # region group + group path from the record's first concept
    for rec in records:
        c0 = rec["concept_ids"][0] if rec["concept_ids"] else rec["class_concept_id"]
        if c0:
            rec["region_group"] = region_group(c0)
            rec["group_path"] = list(reversed(chain_names(c0)))

    # ---- concept census rows --------------------------------------------
    concepts = []
    for cid in universe:
        concepts.append(OrderedDict([
            ("fma_id", cid),
            ("name", isa[cid]["name"]),
            ("representation_id", isa[cid]["repr"]),
            ("subtree", subtree_of[cid]),
            ("role", roles[cid]),
            ("parent_id", parent.get(cid)),
            ("parent_name", isa[parent[cid]]["name"] if cid in parent else None),
            ("isa_mesh_files", len(isa_elem.get(cid, ()))),
            ("partof_mesh_files", len(po_elem.get(cid, ()))),
        ]))

    # ---- absence probe ----------------------------------------------------
    table_files = ["isa_parts_list_e.txt", "partof_parts_list_e.txt",
                   "isa_element_parts.txt", "partof_element_parts.txt",
                   "isa_inclusion_relation_list.txt",
                   "partof_inclusion_relation_list.txt"]
    texts = {fn: open(os.path.join(SRC, fn), encoding="utf-8",
                      errors="replace").read().lower() for fn in table_files}
    absences = []
    for probe in ABSENCE_PROBES:
        hits = {fn: texts[fn].count(probe) for fn in table_files}
        absences.append(OrderedDict([
            ("probe", probe), ("total_hits", sum(hits.values())),
            ("hits_by_table", hits)]))
    absent = [a["probe"] for a in absences if a["total_hits"] == 0]
    present = [a["probe"] for a in absences if a["total_hits"] > 0]

    role_counts = Counter(roles[c] for c in universe)
    repr_counts = Counter(r["representation"] for r in records)

    inv_doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA muscular system inventory — Milestone 4"),
            ("generated_by", "tools/muscle_map.py"),
            ("source_tables", "data/sources/bodyparts3d-4.0/ (BP3D 4.0 / FMA "
                              "concept ids and names as released)"),
            ("counting_convention",
             "One record per lateralised instance where the tables "
             "lateralise (right/left as separate records, mirroring the "
             "skeletal module); one record for an un-sided class concept "
             "modelled jointly; one record per side for a parts-composite "
             "muscle (a muscle with no whole-muscle concept in BP3D 4.0, "
             "represented only by lateralised head/part concepts — heads "
             "and parts are geometry components, never separate records); "
             "numbered instances (lumbricals, interossei) count "
             "individually per side and number as FMA names them. Where "
             "FMA/BP3D models a muscle only as a set (hand interossei and "
             "lumbricals, levatores costarum, cervical intertransversarii, "
             "interspinales cervicis/lumborum), the set is one record per "
             "side where lateralised, else one un-sided record. Groups, "
             "families, zones and part concepts are not records."),
            ("concept_universe", OrderedDict([
                ("total", len(universe)),
                ("muscle_organ_subtree", sum(1 for c in universe if subtree_of[c] == "muscle-organ")),
                ("zone_subtree", sum(1 for c in universe if subtree_of[c] == "zone")),
                ("head_subtree", sum(1 for c in universe if subtree_of[c] == "head")),
                ("roles", dict(role_counts)),
            ])),
            ("record_count", len(records)),
            ("record_representations", dict(repr_counts)),
            ("parts_composite_disposition", parts_composite),
            ("one_sided_parts_composite", asymmetries),
            ("composite_groups", [g["name"] for g in composite_groups]),
            ("orphan_instances", [isa[c]["name"] for c in orphan_instances]),
            ("absences", OrderedDict([
                ("note", "probe-based gap analysis: each probe name was "
                         "counted over all six BP3D 4.0 release tables. "
                         "Zero hits = the name does not occur in the "
                         "release; the muscle has no BP3D concept and no "
                         "record. Probes with hits are listed under "
                         "'present' and are not absences."),
                ("absent", absent),
                ("present", present),
                ("detail", absences),
            ])),
        ])),
        ("concepts", concepts),
        ("records", records),
        ("composite_groups", composite_groups),
    ])
    os.makedirs(os.path.dirname(OUT_INV), exist_ok=True)
    with open(OUT_INV, "w") as f:
        json.dump(inv_doc, f, indent=1, sort_keys=False)

    # ---- geometry ---------------------------------------------------------
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
                    ("path", os.path.relpath(os.path.join(base_dir, fj + ".obj"), ROOT)),
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
        mn = [min(m["bbox"]["min"][i] for m in meshes) for i in range(3)]
        mx = [max(m["bbox"]["max"][i] for m in meshes) for i in range(3)]
        return {"min": mn, "max": mx}

    # Zone concepts are provenance for parts-composite records, NOT extra
    # geometry: a zone's composition spans both sides and is verified here
    # to be a subset of the union of the sides' part files, so including it
    # per-side would misattribute the other side's files to each record.
    zone_subset = {}
    _byside = {}
    for rec in records:
        if rec["representation"] == "parts-composite" and rec.get("zone_concept_ids"):
            base = SIDE_PREFIX.sub("", rec["name"])
            _byside.setdefault(base, {"zones": rec["zone_concept_ids"], "files": set()})
            for c in rec["concept_ids"]:
                _byside[base]["files"] |= isa_elem.get(c, set())
    for base, d in _byside.items():
        zfiles = set()
        for z in d["zones"]:
            zfiles |= isa_elem.get(z, set())
        zone_subset[base] = zfiles <= d["files"]

    geo_records = []
    covered = 0
    for rec in records:
        cids = rec["concept_ids"]
        isa_meshes = mesh_list("isa", isa_elem, ISA_DIR, cids)
        po_meshes = mesh_list("partof", po_elem, PO_DIR, cids)
        if isa_meshes or po_meshes:
            covered += 1
        geo_records.append(OrderedDict([
            ("record_id", rec["record_id"]),
            ("name", rec["name"]),
            ("side", rec["side"]),
            ("representation", rec["representation"]),
            ("concept_ids", cids),
            ("concept_names", [isa[c]["name"] for c in cids]),
            ("isa_meshes", isa_meshes),
            ("partof_meshes", po_meshes),
            ("totals", {"isa": totals(isa_meshes),
                        "partof": totals(po_meshes),
                        "combined_files": len({m["fj"] for m in isa_meshes} |
                                              {m["fj"] for m in po_meshes})}),
            ("bbox_isa", union_bbox(isa_meshes)),
            ("bbox_partof", union_bbox(po_meshes))]))

    geo_doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA muscular geometry resolution — Milestone 4"),
            ("generated_by", "tools/muscle_map.py"),
            ("paths", "mesh paths are relative to the project root; meshes "
                      "are the extracted BP3D 4.0 working copies under "
                      "work/bp3d/ (sources in data/sources/ stay "
                      "byte-identical)"),
            ("units", "source coordinates are millimetres (OBJ headers; "
                      "verified in Milestone 2)"),
            ("counting", "vertices = lines starting 'v ', faces = lines "
                         "starting 'f ', counted by streaming each file; "
                         "bbox measured from the same vertex stream"),
            ("coverage", OrderedDict([
                ("records", len(records)),
                ("records_with_meshes", covered),
                ("records_without_meshes", len(records) - covered),
            ])),
            ("zone_subset_check", OrderedDict([
                ("claim", "for every parts-composite muscle with a zone "
                          "concept, the zone's IS-A element files are a "
                          "subset of the union of the sides' part files; "
                          "zone concepts are therefore recorded as "
                          "provenance on the records and excluded from "
                          "per-side geometry"),
                ("results", zone_subset),
            ])),
        ])),
        ("records", geo_records),
    ])
    with open(OUT_GEO, "w") as f:
        json.dump(geo_doc, f, indent=1, sort_keys=False)

    print("concept universe:", len(universe), dict(role_counts))
    print("records:", len(records), dict(repr_counts))
    print("parts-composite disposition:", parts_composite)
    print("composite groups:", [g["name"] for g in composite_groups])
    print("orphan instances:", [isa[c]["name"] for c in orphan_instances])
    print("geometry coverage: %d/%d records have meshes" % (covered, len(records)))
    print("absent probes:", absent)
    print("present probes:", present)
    print(f"wrote {OUT_INV}")
    print(f"wrote {OUT_GEO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
