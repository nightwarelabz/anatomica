#!/usr/bin/env python3
"""ANATOMICA Milestone 5 — cardiovascular system census + geometry mapping.

Censuses the cardiovascular concepts of BodyParts3D 4.0 / FMA exactly as
they are represented in the release tables (data/sources/bodyparts3d-4.0/),
and maps the derived records to BP3D meshes in the manner of Milestones
2 and 4: exact lookups only, compositions taken from the tables,
vertex/face counts measured by streaming the OBJ files.

HOW BP3D 4.0 REPRESENTS THE CARDIOVASCULAR SYSTEM (established by
inspection of the tables, 2026-11-06; every claim is re-derived by this
script at run time):

  * Arteries live in the IS-A subtree rooted at FMA86187 "segment of
    arterial tree organ" (701 concepts). The subtree rooted at FMA50720
    "artery" (618) is a proper subset of it; the remaining 83 are the
    segment/trunk line ("segment of aorta", the coronary trunks, ...),
    which hangs beside "artery" under the same parent.
  * Veins live in the IS-A subtree rooted at FMA86188 "segment of venous
    tree organ" (324 concepts; the FMA50723 "vein" subtree, 291, is a
    proper subset — the coronary sinus travels with the venous trunk
    line). The two subtrees are disjoint, and their union is the whole
    of FMA50722 "region of vascular tree organ" minus the root itself.
    There is no lymphatic-tree concept in the release (probed).
  * The heart organ concept FMA7088 "heart" exists ONLY in the PART-OF
    table. Its PART-OF subtree reaches the left side of the heart and
    the fibrous skeleton (39 concepts); the right side of the heart
    (FMA7165) hangs in the PART-OF inclusion tree under "systemic
    venous system", so the heart-part census takes the union of both
    PART-OF subtrees. Chambers and valves (right atrium FMA7096, left
    ventricle FMA7101, mitral valve FMA7235, ...) are PART-OF concepts;
    several also occur in the IS-A table as wall/cavity concepts.
  * Heart parts in the IS-A table (valve cusps and leaflets, chamber
    walls and cavities, papillary muscles) hang under generic part
    roots, not under the vessel trees: FMA67598 "leaf of cardiac
    valve", FMA7232 "cusp of cardiac valve", FMA13256 "wall of cardiac
    chamber", FMA9464 "cavity of cardiac chamber", FMA268955 "region
    of papillary muscle", FMA86212 "region of wall of heart". A name
    sweep for cardiac terms outside the vessel trees (with the
    neuraxis/brain-ventricle names explicitly excluded) is run as a
    cross-check and any concept it adds beyond the roots' union is
    reported by name.
  * The aorta as a whole (FMA3734) is likewise PART-OF-only; its
    segments (ascending / arch / descending / abdominal) are IS-A
    concepts in the arterial universe.
  * Cardiac septa, the pericardium, the conduction system (sinoatrial
    node, atrioventricular node, bundle of His, Purkinje fibres) and
    the chordae tendineae occur in NEITHER table (stem probes in meta);
    they are gaps, recorded as such — no concepts, no records, no
    geometry. The papillary muscles, which Milestone 4 left to this
    module, are IS-A concepts under FMA268955 and are records here.

COUNTING CONVENTION (what counts as one cardiovascular record):
  * One record per lateralised instance where the tables lateralise
    (right/left as separate records, mirroring the skeletal and
    muscular modules); the class is the clinical key, not a record.
  * One record for an un-sided class concept the tables model jointly
    (e.g. ascending aorta, superior vena cava).
  * A class with branch-class children but no lateralised instances
    (e.g. trunk of left coronary artery) is one un-sided record; the
    disposition is reported in meta.
  * A lateralised concept whose side-stripped class does not exist in
    the release (single-sided by definition — e.g. the anterior
    interventricular branch of the LEFT coronary artery) is one record
    keyed on the concept itself.
  * The heart and the aorta are records keyed on their PART-OF organ
    concepts (representation "partof-organ"); the named chambers,
    valves and fibrous skeleton are records keyed on their PART-OF
    concepts (representation "partof-concept"); the specific valve
    cusps/leaflets and papillary muscles of the IS-A heart-part set
    are records (representation "whole-concept").
  * Structural roots, tree classes, families, subdivisions, segments
    and set concepts are NOT records; walls, cavities and regions of
    the heart are concepts, not records (the chamber records keyed on
    PART-OF concepts carry them as related concepts).

Outputs:
  data/cardiovascular/cv-inventory.json  concept census + derived records
  data/cardiovascular/cv-geometry.json   per-record resolved mesh lists
                                         with measured vertex/face counts

Stdlib only. Run: python3 tools/cv_map.py
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
OUT_INV = os.path.join(ROOT, "data", "cardiovascular", "cv-inventory.json")
OUT_GEO = os.path.join(ROOT, "data", "cardiovascular", "cv-geometry.json")

ARTERIAL_ROOT = "FMA86187"   # segment of arterial tree organ
VENOUS_ROOT = "FMA86188"     # segment of venous tree organ
ARTERY_CLASS_ROOT = "FMA50720"
VEIN_CLASS_ROOT = "FMA50723"
HEART_PO_ROOT = "FMA7088"    # heart (PART-OF table only)
HEART_RIGHT_PO_ROOT = "FMA7165"  # right side of heart (PART-OF)
AORTA_PO_ROOT = "FMA3734"    # aorta (PART-OF table only)

HEART_ISA_ROOTS = [
    "FMA67598",  # leaf of cardiac valve
    "FMA7232",   # cusp of cardiac valve
    "FMA13256",  # wall of cardiac chamber
    "FMA9464",   # cavity of cardiac chamber
    "FMA268955",  # region of papillary muscle
    "FMA86212",  # region of wall of heart
]
# Generic heart-part class concepts: documented as concepts, not records.
HEART_GENERICS = {
    "leaf of cardiac valve", "cusp of cardiac valve",
    "wall of cardiac chamber", "cavity of cardiac chamber",
    "region of papillary muscle", "region of wall of heart",
    "wall of atrium", "wall of ventricle",
    "cavity of atrium", "cavity of ventricle",
    "cusp of aortic valve", "cusp of pulmonary valve",
    "leaflet of tricuspid valve", "leaflet of mitral valve",
}
# PART-OF heart concepts that become records (chambers, valves, fibrous
# skeleton). Everything else in the heart PART-OF subtrees (walls,
# myocardial zones, inflow/outflow parts, sides of heart) is a concept.
HEART_PO_RECORDS = {
    "FMA7096": "right atrium",
    "FMA7097": "left atrium",
    "FMA7098": "right ventricle",
    "FMA7101": "left ventricle",
    "FMA7234": "tricuspid valve",
    "FMA7235": "mitral valve",
    "FMA7236": "aortic valve",
    "FMA7246": "pulmonary valve",
    "FMA9496": "fibrous skeleton of heart",
}

# Major cardiovascular structures probed for absence (gap analysis).
# A probe is evidence only about that name; hits are counted over all
# six release tables.
ABSENCE_PROBES = [
    "sinoatrial", "sinus node", "atrioventricular node", "bundle of his",
    "purkinje", "pericardium", "interatrial septum",
    "interventricular septum", "chordae", "ductus arteriosus",
    "foramen ovale", "ligamentum arteriosum", "thoracic duct",
    "ophthalmic artery", "basilar artery", "cerebral arterial circle",
    "anterior cerebral artery", "middle cerebral artery",
    "posterior cerebral artery", "anterior communicating artery",
    "posterior communicating artery", "internal thoracic artery",
    "superior epigastric artery", "inferior epigastric artery",
    "obturator artery", "superior gluteal artery", "ovarian artery",
    "uterine artery", "hepatic artery", "cystic artery",
    "gastroduodenal artery", "splenic artery", "left gastric artery",
    "ileocolic artery", "middle colic artery", "superior rectal artery",
    "hemiazygos", "azygos vein", "basilic vein", "cephalic vein",
    "median cubital vein", "external jugular vein",
    "internal jugular vein", "hepatic vein", "testicular vein",
    "superficial palmar arch", "deep palmar arch", "dorsalis pedis",
    "plantar arch", "profunda femoris", "deep femoral artery",
    "thoracoacromial artery", "subscapular artery",
    "profunda brachii", "lingual artery", "facial artery",
    "occipital artery", "superior thyroid artery",
    "thyrocervical trunk", "umbilical artery", "median sacral artery",
    "great saphenous vein", "small saphenous vein", "femoral vein",
    "popliteal vein", "coronary sinus", "pulmonary vein",
    "brachiocephalic vein", "subclavian vein", "renal vein",
    "splenic vein", "superior mesenteric vein", "inferior epigastric vein",
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
    return isa, po, isa_elem, po_elem, children, parent, po_children, po_parent


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


SIDE_PREFIX = re.compile(r"^(right|left)\s+")
SIDE_INFIX = re.compile(r"\bof (right|left)\s+")


def side_of(name):
    m = SIDE_PREFIX.match(name)
    if m:
        return m.group(1)
    m = SIDE_INFIX.search(name)
    if m:
        return m.group(1)
    return None


def base_form(name):
    """Strip lateralisation so an instance can be compared to its class."""
    n = SIDE_PREFIX.sub("", name)
    n = SIDE_INFIX.sub("of ", n)
    return n


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    (isa, po, isa_elem, po_elem, children, parent,
     po_children, po_parent) = load_tables()

    arterial = set(descendants(ARTERIAL_ROOT, children))
    venous = set(descendants(VENOUS_ROOT, children))
    assert not (arterial & venous), "vessel subtrees must be disjoint"

    # ---- heart IS-A set: roots' union, cross-checked by a name sweep ---
    heart_isa = set()
    for r in HEART_ISA_ROOTS:
        heart_isa |= set(descendants(r, children))
    sweep_terms = ("cardiac", "heart", "atrium", "atrial", "mitral",
                   "tricuspid", "papillary")
    sweep_exclude = ("neuraxis", "telencephalon", "lateral ventricle",
                     "third ventricle", "fourth ventricle",
                     "ventricular system", "interventricular foramen",
                     "circumventricular")
    sweep = set()
    for cid, v in isa.items():
        n = v["name"]
        if cid in arterial or cid in venous:
            continue
        if any(t in n for t in sweep_terms) and \
                not any(x in n for x in sweep_exclude):
            sweep.add(cid)
    sweep_only = sorted(sweep - heart_isa)
    heart_isa |= sweep

    # ---- heart PART-OF set ----------------------------------------------
    heart_po = set(descendants(HEART_PO_ROOT, po_children))
    heart_po |= set(descendants(HEART_RIGHT_PO_ROOT, po_children))
    heart_po |= {HEART_PO_ROOT, HEART_RIGHT_PO_ROOT, AORTA_PO_ROOT}
    heart_po_only = {c for c in heart_po if c not in isa}

    subtree_of = {}
    for cid in arterial:
        subtree_of[cid] = "arterial"
    for cid in venous:
        subtree_of[cid] = "venous"
    for cid in heart_isa:
        subtree_of[cid] = "heart-isa"
    for cid in heart_po:
        subtree_of.setdefault(cid, "heart-partof")

    def chain_names(cid, par, tab):
        out, cur = [], cid
        while cur in par:
            cur = par[cur]
            out.append(tab[cur]["name"])
        return out

    # ---- roles for vessel concepts ---------------------------------------
    STRUCT_ROOTS = {ARTERIAL_ROOT, VENOUS_ROOT, ARTERY_CLASS_ROOT,
                    VEIN_CLASS_ROOT}
    roles = {}

    def classify_universe(universe):
        for cid in universe:
            name = isa[cid]["name"]
            if cid in STRUCT_ROOTS:
                roles[cid] = "structural-root"
            elif name.startswith("subdivision of"):
                roles[cid] = "subdivision"
            elif name.startswith("segment of"):
                roles[cid] = "segment"
            elif name.startswith("zone of"):
                roles[cid] = "zone"
            elif " part of " in name or name.startswith("subsegmental"):
                roles[cid] = "part"
            elif name.startswith("set of"):
                roles[cid] = "set-instance" if side_of(name) else "set-class"
            elif side_of(name):
                roles[cid] = "instance"
            else:
                roles[cid] = "class-candidate"
        for cid in universe:
            if roles[cid] != "class-candidate":
                continue
            sub = [c for c in children.get(cid, []) if c in universe]
            foreign = [c for c in sub
                       if not (roles.get(c) in ("instance", "subdivision",
                                                "segment", "zone", "part",
                                                "set-class",
                                                "set-instance") and
                               (roles.get(c) != "instance" or
                                base_form(isa[c]["name"]) ==
                                base_form(isa[cid]["name"])))]
            roles[cid] = "family" if foreign else "class"

    classify_universe(arterial)
    classify_universe(venous)

    name2id = {}
    for cid in arterial | venous:
        name2id.setdefault(isa[cid]["name"], cid)

    # ---- vessel records ---------------------------------------------------
    records = []
    used_instances = set()
    instance_grouping = {"direct": 0, "deep": 0, "standalone": 0}
    family_records = []   # families recorded as un-sided vessels

    def add_record(rid, name, side, representation, concept_ids,
                   class_id, subtree, note=None):
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

    def vessel_rid(name, subtree):
        return ("artery." if subtree == "arterial" else "vein.") + slug(name)

    # Families that are generic tree/part/branch classes — never records
    # even when they pass the specific-name test in (b).
    GENERIC_FAMILIES = {
        "systemic artery", "systemic vein", "pulmonary vein",
        "coronary artery", "cardiac vein", "temporal artery",
        "lobar artery", "pancreatic artery",
    }

    def specific_family(name):
        """A family concept that is nevertheless one specific named
        vessel (e.g. posterior intercostal artery, whose children are
        its numbered branch classes) rather than a generic branch,
        trunk, tributary or part class."""
        if not (name.endswith(" artery") or name.endswith(" vein")):
            return False
        if name in GENERIC_FAMILIES:
            return False
        if name.startswith(("branch of", "tributary of", "trunk of",
                            "segmental", "subsegmental", "zone of",
                            "variant")):
            return False
        if " part of " in name:
            return False
        return True

    for universe, subtree in ((arterial, "arterial"), (venous, "venous")):
        # (a) classes AND families with lateralised instances -> one
        # record per instance; the grouping is by side-stripped name,
        # so instances filed under a subdivision of the class still
        # group to it. (In this release the great-vein and pulmonary
        # classes classify as families because their children also
        # include named branch classes; their instances still belong
        # to them.)
        for cid in sorted(universe):
            if roles[cid] not in ("class", "family"):
                continue
            cname = isa[cid]["name"]
            insts = [c for c in universe
                     if roles.get(c) == "instance" and
                     base_form(isa[c]["name"]) == base_form(cname)]
            if insts:
                for ic in sorted(insts, key=lambda c: isa[c]["name"]):
                    iname = isa[ic]["name"]
                    add_record(vessel_rid(iname, subtree), iname,
                               side_of(iname), "whole-concept", [ic], cid,
                               subtree)
                    used_instances.add(ic)
                    instance_grouping["direct" if parent.get(ic) == cid
                                      else "deep"] += 1
            elif roles[cid] == "class":
                add_record(vessel_rid(cname, subtree), cname, "un-sided",
                           "whole-concept-unsided", [cid], cid, subtree)
            elif specific_family(cname):
                add_record(vessel_rid(cname, subtree), cname, "un-sided",
                           "whole-concept-unsided", [cid], cid, subtree,
                           note="class has branch-class children but no "
                                "lateralised instances in the release; "
                                "recorded as a single un-sided vessel")
                family_records.append(cname)
        # (c) standalone instances: lateralised concepts whose
        # side-stripped class does not exist in the release.
        for cid in sorted(universe):
            if roles.get(cid) != "instance" or cid in used_instances:
                continue
            iname = isa[cid]["name"]
            if base_form(iname) in name2id:
                continue  # grouped under its class in (a) — defensive
            add_record(vessel_rid(iname, subtree), iname, side_of(iname),
                       "whole-concept", [cid], cid, subtree,
                       note="lateralised concept whose side-stripped class "
                            "does not exist in the release; single-sided "
                            "by definition (a branch of a lateralised "
                            "parent vessel)")
            used_instances.add(cid)
            instance_grouping["standalone"] += 1

    orphan_instances = [isa[c]["name"]
                        for u in (arterial, venous) for c in u
                        if roles.get(c) == "instance" and
                        c not in used_instances]

    # ---- heart records -----------------------------------------------------
    heart_organ = add_record(
        "heart", "heart", "un-sided", "partof-organ", [HEART_PO_ROOT],
        HEART_PO_ROOT, "heart-partof",
        note="the heart organ concept exists only in the PART-OF table "
             "of BP3D 4.0; geometry is its PART-OF composition")
    add_record("artery.aorta", "aorta", "un-sided", "partof-organ",
               [AORTA_PO_ROOT], AORTA_PO_ROOT, "heart-partof",
               note="the aorta as a whole exists only in the PART-OF "
                    "table; its segments are IS-A records of the "
                    "arterial universe")
    for cid, nm in sorted(HEART_PO_RECORDS.items(),
                          key=lambda kv: kv[1]):
        add_record("heart." + slug(nm), nm, "un-sided", "partof-concept",
                   [cid], cid, "heart-partof")
    heart_isa_records = []
    for cid in sorted(heart_isa):
        name = isa[cid]["name"]
        if name in HEART_GENERICS:
            continue
        if name.startswith(("wall of", "cavity of", "region of")):
            continue
        if " head of " in name:
            continue
        add_record("heart." + slug(name), name, "un-sided",
                   "whole-concept", [cid], cid, "heart-isa")
        heart_isa_records.append(name)

    # group paths
    for rec in records:
        c0 = rec["concept_ids"][0]
        if rec["subtree"] == "heart-partof":
            rec["group_path"] = list(reversed(
                chain_names(c0, po_parent, po))) \
                if c0 in po else list(reversed(chain_names(c0, parent, isa)))
        else:
            rec["group_path"] = list(reversed(chain_names(c0, parent, isa)))

    # ---- concept census rows ----------------------------------------------
    concepts = []
    for cid in sorted(subtree_of):
        in_isa = cid in isa
        tab = isa if in_isa else po
        concepts.append(OrderedDict([
            ("fma_id", cid),
            ("name", tab[cid]["name"]),
            ("representation_id", tab[cid]["repr"]),
            ("table", "isa" if in_isa else "partof"),
            ("also_in_partof", cid in po),
            ("subtree", subtree_of[cid]),
            ("role", roles.get(cid, "heart-part" if not in_isa or
                               subtree_of[cid].startswith("heart") else None)),
            ("parent_id", parent.get(cid) if in_isa else po_parent.get(cid)),
            ("parent_name", (isa[parent[cid]]["name"] if in_isa and
                             cid in parent else
                             po[po_parent[cid]]["name"] if not in_isa and
                             cid in po_parent else None)),
            ("isa_mesh_files", len(isa_elem.get(cid, ()))),
            ("partof_mesh_files", len(po_elem.get(cid, ()))),
        ]))

    # ---- absence probes -----------------------------------------------------
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

    role_counts = Counter(roles[c] for u in (arterial, venous) for c in u)
    repr_counts = Counter(r["representation"] for r in records)

    # TotalSegmentator cardiovascular labels (13) and their mapping onto
    # this module — censused in Milestone 3 from labels.json/labels.md.
    ts_labels = [
        ("aorta", ["artery.aorta"],
         "the TS aorta label is the whole aorta; the inventory keys it "
         "on the PART-OF organ record (segments are separate records)"),
        ("inferior_vena_cava", ["vein.inferior-vena-cava"],
         "single un-sided vein record"),
        ("portal_vein_and_splenic_vein",
         ["vein.right-portal-vein", "vein.left-portal-vein",
          "vein.splenic-vein"],
         "one TS label spanning the portal vein (recorded in the "
         "inventory as its right and left lateralised instances — "
         "the class itself is not a record) and the splenic vein"),
        ("pulmonary_artery",
         ["artery.right-pulmonary-artery", "artery.left-pulmonary-artery"],
         "the TS label covers the trunk and both branches; the "
         "inventory records the lateralised instances of the class"),
        ("iliac_artery_left", ["artery.left-common-iliac-artery"],
         "on CT the labelled iliac artery is the common iliac trunk "
         "continuing as external iliac; keyed to the common iliac "
         "record — approximate correspondence, flagged"),
        ("iliac_artery_right", ["artery.right-common-iliac-artery"],
         "as left"),
        ("iliac_vena_left", ["vein.left-common-iliac-vein"],
         "keyed to the common iliac vein record — approximate "
         "correspondence, flagged"),
        ("iliac_vena_right", ["vein.right-common-iliac-vein"],
         "as left"),
        ("heart_atrium_left", ["heart.left-atrium"], "PART-OF record"),
        ("heart_atrium_right", ["heart.right-atrium"], "PART-OF record"),
        ("heart_ventricle_left", ["heart.left-ventricle"],
         "PART-OF record"),
        ("heart_ventricle_right", ["heart.right-ventricle"],
         "PART-OF record"),
        ("heart_myocardium", ["heart"],
         "the TS myocardium label is the heart wall mass; the "
         "inventory carries myocardium only as PART-OF part concepts "
         "of the ventricle walls, so the label keys to the heart "
         "organ record — flagged"),
    ]
    rec_ids = {r["record_id"] for r in records}
    ts_missing = [lbl for lbl, ids, _ in ts_labels
                  if not all(i in rec_ids for i in ids)]

    inv_doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA cardiovascular system inventory — "
                      "Milestone 5"),
            ("generated_by", "tools/cv_map.py"),
            ("source_tables", "data/sources/bodyparts3d-4.0/ (BP3D 4.0 / "
                              "FMA concept ids and names as released)"),
            ("counting_convention",
             "Vessels: one record per lateralised instance where the "
             "tables lateralise (right/left as separate records, "
             "mirroring the skeletal and muscular modules); one record "
             "for an un-sided class concept modelled jointly; a class "
             "with branch-class children but no lateralised instances "
             "is one un-sided record; a lateralised concept whose "
             "side-stripped class does not exist in the release is one "
             "record keyed on the concept itself (single-sided by "
             "definition). Structural roots, tree classes, families, "
             "subdivisions, segments and set concepts are not records. "
             "Heart: the organ and the aorta are records keyed on "
             "their PART-OF-only organ concepts; named chambers, valves "
             "and the fibrous skeleton are records keyed on PART-OF "
             "concepts; specific valve cusps/leaflets and papillary "
             "muscles are records keyed on IS-A concepts; walls, "
             "cavities, regions and generic part classes are concepts, "
             "not records."),
            ("concept_universe", OrderedDict([
                ("total", len(subtree_of)),
                ("arterial_subtree", len(arterial)),
                ("venous_subtree", len(venous)),
                ("heart_isa", len(heart_isa)),
                ("heart_partof_concepts", len(heart_po)),
                ("heart_partof_only_concepts", len(heart_po_only)),
                ("vessel_roles", dict(role_counts)),
                ("heart_name_sweep_additions", sweep_only),
                ("heart_sweep_note",
                 "concepts added by the cardiac name sweep beyond the "
                 "six heart-part roots' descendant union, with "
                 "neuraxis/brain-ventricle names excluded by rule"),
            ])),
            ("record_count", len(records)),
            ("record_representations", dict(repr_counts)),
            ("instance_grouping", instance_grouping),
            ("family_records_unilateral", family_records),
            ("orphan_instances", orphan_instances),
            ("heart_isa_records", heart_isa_records),
            ("totalsegmentator_overlap", OrderedDict([
                ("note", "the 13 cardiovascular labels of the "
                         "TotalSegmentator v1 label set (Milestone 3 "
                         "census), each mapped to inventory records; "
                         "approximate correspondences are flagged in "
                         "the per-label notes"),
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

    # ---- geometry -----------------------------------------------------------
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
        mn = [min(m["bbox"]["min"][i] for m in meshes) for i in range(3)]
        mx = [max(m["bbox"]["max"][i] for m in meshes) for i in range(3)]
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
            ("title", "ANATOMICA cardiovascular geometry resolution — "
                      "Milestone 5"),
            ("generated_by", "tools/cv_map.py"),
            ("paths", "mesh paths are relative to the project root; "
                      "meshes are the extracted BP3D 4.0 working copies "
                      "under work/bp3d/ (sources in data/sources/ stay "
                      "byte-identical)"),
            ("units", "source coordinates are millimetres (OBJ "
                      "headers; verified in Milestone 2)"),
            ("counting", "vertices = lines starting 'v ', faces = "
                         "lines starting 'f ', counted by streaming "
                         "each file; bbox measured from the same "
                         "vertex stream"),
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

    print("arterial concepts:", len(arterial), "| venous:", len(venous),
          "| heart-isa:", len(heart_isa), "| heart-partof:", len(heart_po),
          "(po-only:", len(heart_po_only), ")")
    print("vessel roles:", dict(role_counts))
    print("records:", len(records), dict(repr_counts))
    print("instance grouping:", instance_grouping)
    print("family records (un-sided):", family_records)
    print("orphan instances:", orphan_instances)
    print("heart isa records:", heart_isa_records)
    print("name sweep additions:", sweep_only)
    print("TS labels without records:", ts_missing)
    print("geometry coverage: %d/%d records have meshes"
          % (covered, len(records)))
    print("absent probes:", absent)
    print(f"wrote {OUT_INV}")
    print(f"wrote {OUT_GEO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
