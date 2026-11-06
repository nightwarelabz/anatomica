#!/usr/bin/env python3
"""ANATOMICA Milestone 10 — respiratory system census + geometry mapping.

Censuses the respiratory-system concepts of BodyParts3D 4.0 / FMA
exactly as they are represented in the release tables
(data/sources/bodyparts3d-4.0/), and maps the derived records to BP3D
meshes in the manner of Milestones 2, 4, 5 and 9: exact lookups only,
compositions taken from the tables, vertex/face counts measured by
streaming the OBJ files.

HOW BP3D 4.0 REPRESENTS THE RESPIRATORY SYSTEM (established by
inspection of the tables, 2026-11-06; every claim is re-derived by
this script at run time):

  * There is no IS-A respiratory-system tree. The conducting airway
    hangs in IS-A under the generic organ-part root FMA12224
    "segment of tracheobronchial tree" (37 concepts): the trachea,
    the bronchus classes, the main bronchi and 29 segmental
    bronchial tree concepts (11 un-sided classes, 16 lateralised
    instances, the 2 un-sided lingular trees). The tree jumps from
    the main bronchi straight to the segmental bronchial trees —
    no lobar (secondary) bronchus concept exists.
  * The larynx exists only as its furniture: the laryngeal
    cartilage line (root FMA55108, 12 concepts), the ligament lines
    (FMA55131 "ligament of larynx" + the vocal ligament line FMA55244
    + the cricothyroid ligament line FMA55233, 10 concepts), the
    thyrohyoid membrane/ligament sweep set (8 concepts) and the
    epiglottis, which the release files under "subdivision of
    pharynx" (FMA54877 subtree, 3 concepts). There is no "larynx"
    concept and no laryngeal cavity, fold or ventricle concept.
  * The laryngeal and pharyngeal MUSCLES are censused here but
    their records live in the muscular module (Milestone 4): the
    muscle-of-larynx line (FMA46562, 18 concepts), the
    aryepiglotticus line (FMA46602, 3), the cricothyroid part line
    (FMA46608, 7 — the release carries no "cricothyroid" class
    concept, only its straight/oblique parts, which are exactly the
    concepts the muscular records key on) and the muscle-of-pharynx
    line (FMA46619, 20). The diaphragm (FMA13295) is likewise a
    muscular-module record, cross-referenced here.
  * In PART-OF, the "respiratory system" subtree (root FMA7158,
    92 concepts) carries the tracheobronchial tree and the RIGHT
    lung with its lobes, its 10 bronchopulmonary segments and its
    segmental pulmonary vasculature — but the LEFT lung hangs
    outside it, under "left pulmopleural compartment" (thoracic
    compartment line): its subtree (43 concepts) carries the left
    lobes, 11 left segment concepts and the left segmental vessels.
    The nose (FMA46472, 25 concepts) hangs under face/head. The
    PART-OF census is therefore the union of the three subtrees.
    The segmental arteries and veins inside the lung subtrees are
    censused and tagged as cardiovascular cross-references — their
    records live in the cardiovascular module (Milestone 5); the
    two pulmopleural compartments are censused as compartment
    concepts (the release's only pleura-adjacent structures), not
    records. There is no "pleura" concept of any kind.
  * The bronchopulmonary segments exist ONLY in PART-OF (21
    concepts: 10 right, 11 left — the left carries apicoposterior
    AND separate apical and posterior concepts). The inferior
    nasal conchae are skeletal-module bone records (FMA54736
    class, FMA54737/54738 instances); the superior and middle
    conchae have no concepts at all (they are parts of the ethmoid
    bone, skeletal record "ethmoid", FMA52740). The nasal
    cartilages hang in IS-A under FMA59502 (8 concepts) and also
    occur in the PART-OF nose subtree.
  * Name sweeps over both tables adjudicate the remainder:
    bronchial arteries and the coronary sinus are cardiovascular;
    the nasal bones are skeletal; the pharyngeal raphe (FMA55077)
    is admitted as a sweep addition and a record; the
    pterygomandibular raphe, stylohyoid ligaments and the zone of
    oblique arytenoid are reported as rejected sweep hits.

COUNTING CONVENTION (what counts as one respiratory-system record):
  * One record per lateralised instance where the tables
    lateralise; one record for an un-sided class modelled jointly;
    a lateralised concept whose side-stripped class does not exist
    is one record keyed on the concept itself (the right main
    bronchus, keyed on the IS-A "right main bronchus proper" with
    the PART-OF-only "right main bronchus" concept attached).
  * The nose and the two lungs are records keyed on their PART-OF
    organ concepts ("partof-organ"); the five lobes, the 21
    bronchopulmonary segments and the three named nose parts that
    exist only in PART-OF are records keyed on PART-OF concepts
    ("partof-concept"); airway, larynx and nasal-cartilage
    structures are records keyed on IS-A concepts
    ("whole-concept").
  * Muscles (records in the muscular module), the diaphragm,
    pulmonary segmental vessels (records in the cardiovascular
    module), the nasal conchae (records in the skeletal module),
    structural roots, tree classes, generic part classes,
    bronchial-tree aggregate/composition concepts, nose skeleton
    aggregates, wall/side/region classes and the two pulmopleural
    compartments are NOT respiratory records; they are censused
    and tagged with their cross-reference.

Outputs:
  data/respiratory/respiratory-inventory.json  census + records
  data/respiratory/respiratory-geometry.json   per-record meshes

Stdlib only. Run: python3 tools/resp_map.py
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
OUT_INV = os.path.join(ROOT, "data", "respiratory",
                       "respiratory-inventory.json")
OUT_GEO = os.path.join(ROOT, "data", "respiratory",
                       "respiratory-geometry.json")

TRACHEOBRONCHIAL_ROOT = "FMA12224"  # segment of tracheobronchial tree
LARYNX_CARTILAGE_ROOT = "FMA55108"  # laryngeal cartilage
LARYNX_LIGAMENT_ROOTS = ["FMA55131",   # ligament of larynx
                         "FMA55244",   # vocal ligament
                         "FMA55233"]   # cricothyroid ligament
PHARYNX_SUBDIV_ROOT = "FMA54877"    # subdivision of pharynx
THYROHYOID_SWEEP = ["FMA55132",   # thyrohyoid membrane
                    "FMA55134",   # left thyrohyoid membrane
                    "FMA55133",   # right thyrohyoid membrane
                    "FMA55135",   # thyrohyoid ligament
                    "FMA55138",   # median thyrohyoid ligament
                    "FMA55139",   # lateral thyrohyoid ligament
                    "FMA55140",   # right lateral thyrohyoid ligament
                    "FMA55141"]   # left lateral thyrohyoid ligament
RAPHE_SWEEP = "FMA55077"            # pharyngeal raphe
CONUS_ROOT = "FMA55250"             # conus elasticus (hangs under
                                    # "membrane organ component", not
                                    # under the ligament lines; found
                                    # by probe, admitted by sweep)
LARYNX_MUSCLE_ROOT = "FMA46562"     # muscle of larynx (muscular xref)
ARYEPIGLOTTICUS_ROOT = "FMA46602"   # aryepiglotticus (muscular xref)
CRICOTHYROID_ROOT = "FMA46608"      # zone of cricothyroid (muscular xref)
PHARYNX_MUSCLE_ROOT = "FMA46619"    # muscle of pharynx (muscular xref)
NASAL_CARTILAGE_ROOT = "FMA59502"   # nasal cartilage
CONCHA_XREF = ["FMA54736",          # inferior nasal concha (skeletal)
               "FMA54737",          # right inferior nasal concha
               "FMA54738"]          # left inferior nasal concha
DIAPHRAGM_XREF = "FMA13295"         # diaphragm (muscular xref)

RS_PO_ROOT = "FMA7158"              # respiratory system (PART-OF)
LEFT_LUNG_PO = "FMA7310"            # left lung (PART-OF, compartment line)
NOSE_PO = "FMA46472"                # nose (PART-OF, under face)
PULMOPLEURAL_PO = ["FMA85055",      # right pulmopleural compartment
                   "FMA85056"]      # left pulmopleural compartment
AIRWAY_PO_SWEEP = ["FMA7395"]      # right main bronchus (PART-OF only;
                                   # hangs outside the three subtrees,
                                   # admitted by sweep so the record's
                                   # second concept id is censused)

EPIGLOTTIS = "FMA55130"
RIGHT_MAIN_PO = "FMA7395"           # right main bronchus (PART-OF only)

# PART-OF organ records: concept -> (record_id, side)
PO_ORGANS = {
    "FMA46472": ("nose", "un-sided"),
    "FMA7309": ("right-lung", "right"),
    "FMA7310": ("left-lung", "left"),
}
# PART-OF lobe records
PO_LOBES = {
    "FMA7333": "upper lobe of right lung",
    "FMA7383": "middle lobe of lung",
    "FMA7337": "lower lobe of right lung",
    "FMA7370": "upper lobe of left lung",
    "FMA7371": "lower lobe of left lung",
}
# PART-OF bronchopulmonary segment records: concept -> side
PO_SEGMENTS = {
    "FMA7338": "right",   # right apical
    "FMA7339": "right",   # right posterior
    "FMA7359": "right",   # right anterior
    "FMA7361": "right",   # lateral (middle lobe)
    "FMA7360": "right",   # medial (middle lobe)
    "FMA7366": "right",   # right superior
    "FMA7365": "right",   # right medial basal
    "FMA7364": "right",   # right anterior basal
    "FMA7363": "right",   # right lateral basal
    "FMA7362": "right",   # right posterior basal
    "FMA7372": "left",    # apicoposterior
    "FMA7385": "left",    # left apical
    "FMA7386": "left",    # left posterior
    "FMA7373": "left",    # left anterior
    "FMA7374": "left",    # superior lingular
    "FMA7375": "left",    # inferior lingular
    "FMA7376": "left",    # left superior
    "FMA7377": "left",    # left medial basal
    "FMA7378": "left",    # left anterior basal
    "FMA7379": "left",    # left lateral basal
    "FMA7380": "left",    # left posterior basal
}
# PART-OF named nose parts (cartilages are keyed on IS-A concepts)
PO_NOSE_PARTS = {
    "FMA59515": "external nose",
    "FMA59637": "internal nose",
    "FMA54375": "nasal septum",
}

AIRWAY_GENERICS = {
    "segment of tracheobronchial tree", "segment of bronchial tree",
    "pulmonary segment of bronchial tree", "bronchus",
}
LARYNX_CARTILAGE_GENERICS = {"laryngeal cartilage"}
LIGAMENT_GENERICS = {
    "ligament of larynx", "intrinsic ligament of larynx",
    "extrinsic ligament of larynx", "cricothyroid ligament",
    "thyrohyoid ligament",
}
NASAL_CARTILAGE_GENERICS = {"nasal cartilage"}

ABSENCE_PROBES = [
    # organs / spaces with no concept of their own in the release
    "pharynx", "larynx", "nasopharynx", "oropharynx",
    "laryngopharynx", "nasal cavity", "choana", "pleura",
    "visceral pleura", "parietal pleura", "pleural cavity",
    "costal pleura", "mediastinal pleura", "diaphragmatic pleura",
    "cervical pleura", "costodiaphragmatic recess",
    "costomediastinal recess", "pleural recess",
    # paranasal sinuses and drainage structures
    "paranasal sinus", "frontal sinus", "maxillary sinus",
    "sphenoidal sinus", "sphenoid sinus", "ethmoid sinus",
    "ethmoidal sinus", "ethmoidal air cell", "auditory tube",
    "pharyngotympanic tube", "eustachian tube", "nasolacrimal duct",
    "semilunar hiatus", "ethmoidal bulla", "uncinate process",
    "agger nasi", "sphenopalatine foramen",
    # nasal conchae / meatuses beyond the inferior concha
    "superior nasal concha", "middle nasal concha",
    "supreme nasal concha", "nasal meatus", "superior nasal meatus",
    "middle nasal meatus", "inferior nasal meatus",
    "sphenoethmoidal recess", "common nasal meatus",
    # lung surface features
    "oblique fissure", "horizontal fissure", "fissure of lung",
    "hilum of lung", "root of lung", "cardiac notch", "lingula",
    "apex of lung", "base of lung", "costal surface of lung",
    "mediastinal surface of lung", "pulmonary lobule",
    "interlobular septum", "acinus",
    # bronchial generations the release skips
    "lobar bronchus", "secondary bronchus", "tertiary bronchus",
    "segmental bronchus", "subsegmental bronchus",
    "bronchus intermedius", "upper lobe bronchus",
    "middle lobe bronchus", "lower lobe bronchus",
    "lingular bronchus", "eparterial bronchus",
    # distal airway (respiratory zone)
    "bronchiole", "respiratory bronchiole", "terminal bronchiole",
    "conducting bronchiole", "alveolar duct", "alveolar sac",
    "pulmonary alveolus", "alveolus", "respiratory membrane",
    # tracheal detail
    "carina", "carina of trachea", "bifurcation of trachea",
    "tracheal cartilage", "tracheal ring", "trachealis",
    "trachealis muscle",
    # laryngeal interior and membranes
    "vocal fold", "vestibular fold", "vocal cord", "true vocal cord",
    "false vocal cord", "glottis", "rima glottidis",
    "laryngeal ventricle", "laryngeal cavity", "laryngeal inlet",
    "vestibule of larynx", "infraglottic cavity", "piriform recess",
    "piriform fossa", "vallecula", "aryepiglottic fold",
    "cricothyroid membrane", "quadrangular membrane",
    "conus elasticus", "thyrohyoid membrane",  # present: control
    "sesamoid cartilage", "triticeal cartilage",
    "epiglottic cartilage",
    # present controls (exact concepts exist)
    "trachea", "main bronchus", "bronchopulmonary segment",
    "arytenoid cartilage", "nasal septum", "diaphragm",
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
    n = SIDE_PREFIX.sub("", name)
    n = SIDE_INFIX.sub("of ", n)
    return n


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    (isa, po, isa_elem, po_elem, children, parent,
     po_children, po_parent) = load_tables()

    # ---- concept subtrees ------------------------------------------------
    tracheobronchial = descendants(TRACHEOBRONCHIAL_ROOT, children)
    larynx_cartilage = descendants(LARYNX_CARTILAGE_ROOT, children)
    larynx_ligament = set()
    for r in LARYNX_LIGAMENT_ROOTS:
        larynx_ligament |= descendants(r, children)
    thyrohyoid = set(THYROHYOID_SWEEP)
    conus = descendants(CONUS_ROOT, children)
    pharynx_subdiv = descendants(PHARYNX_SUBDIV_ROOT, children)
    raphe = {RAPHE_SWEEP}
    larynx_muscle_x = descendants(LARYNX_MUSCLE_ROOT, children) | \
        descendants(ARYEPIGLOTTICUS_ROOT, children) | \
        descendants(CRICOTHYROID_ROOT, children)
    pharynx_muscle_x = descendants(PHARYNX_MUSCLE_ROOT, children)
    nasal_cartilage = descendants(NASAL_CARTILAGE_ROOT, children)
    concha_x = set(CONCHA_XREF)
    diaphragm_x = {DIAPHRAGM_XREF}

    isa_sets = OrderedDict([
        ("tracheobronchial-isa", tracheobronchial),
        ("larynx-cartilage-isa", larynx_cartilage),
        ("larynx-ligament-isa", larynx_ligament),
        ("thyrohyoid-isa", thyrohyoid),
        ("conus-elasticus-isa", conus),
        ("pharynx-subdivision-isa", pharynx_subdiv),
        ("pharynx-raphe-isa", raphe),
        ("larynx-muscle-xref-isa", larynx_muscle_x),
        ("pharynx-muscle-xref-isa", pharynx_muscle_x),
        ("nasal-cartilage-isa", nasal_cartilage),
        ("concha-skeletal-xref-isa", concha_x),
        ("diaphragm-muscular-xref-isa", diaphragm_x),
    ])
    isa_universe = set()
    for s in isa_sets.values():
        isa_universe |= s

    rs_po = descendants(RS_PO_ROOT, po_children)
    left_lung_po = descendants(LEFT_LUNG_PO, po_children)
    nose_po = descendants(NOSE_PO, po_children)
    compartments_po = set(PULMOPLEURAL_PO)
    airway_po = set(AIRWAY_PO_SWEEP)
    po_sets = OrderedDict([
        ("respiratory-system-partof", rs_po),
        ("left-lung-partof", left_lung_po),
        ("nose-partof", nose_po),
        ("pulmopleural-compartment-partof", compartments_po),
        ("airway-partof-sweep", airway_po),
    ])
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

    def cross_ref(cid):
        tag = subtree_of[cid]
        name = (isa[cid]["name"] if cid in isa else po[cid]["name"])
        if "muscle-xref" in tag or tag == "diaphragm-muscular-xref-isa":
            return "muscular"
        if tag == "concha-skeletal-xref-isa":
            return "skeletal"
        if "artery" in name or "vein" in name:
            return "cardiovascular"
        if tag == "pulmopleural-compartment-partof":
            return "compartment (not a record in any module)"
        return None

    # cross-check sweeps: respiratory terms outside the universe
    sweep_terms = ("lung", "bronch", "trachea", "laryng", "pharyng",
                   "pleura", "nasal", "nose", "alveol", "diaphragm",
                   "concha", "glott", "epiglott", "vocal", "raphe",
                   "respiratory", "sinus", "pulmon")
    sweep_exclude = ("ventricle of heart", "papillary muscle",
                     "superior parietal lobule",
                     "inferior parietal lobule")
    sweep_rejected = {}
    for tab, tname in ((isa, "isa"), (po, "partof")):
        for cid, v in tab.items():
            if cid in universe:
                continue
            n = v["name"]
            if any(t in n for t in sweep_terms) and \
                    not any(x in n for x in sweep_exclude):
                sweep_rejected.setdefault(n, tname)
    sweep_rejected = sorted(sweep_rejected)

    def chain_names(cid, par, tab):
        out, cur = [], cid
        while cur in par:
            cur = par[cur]
            out.append(tab[cur]["name"])
        return out

    # ---- record derivation ----------------------------------------------
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

    def is_specific_isa(cid, generics):
        name = isa[cid]["name"]
        if name in generics:
            return False
        if name.startswith(("segment of", "zone of", "region of",
                            "subdivision of", "subdivisionof",
                            "wall of", "cavity of", "set of",
                            "branch of")):
            return False
        if " part of " in name:
            return False
        return True

    def group_records(cands, prefix, subtree, generics):
        by_base = {}
        for cid in cands:
            by_base.setdefault(base_form(isa[cid]["name"]), []).append(cid)
        made, used = [], set()
        for base, members in sorted(by_base.items()):
            classes = [c for c in members
                       if side_of(isa[c]["name"]) is None]
            insts = [c for c in members
                     if side_of(isa[c]["name"]) is not None]
            class_id = classes[0] if classes else None
            if insts and class_id is not None:
                for ic in sorted(insts, key=lambda c: isa[c]["name"]):
                    iname = isa[ic]["name"]
                    add_record(prefix + slug(iname), iname,
                               side_of(iname), "whole-concept", [ic],
                               class_id, subtree)
                    used.add(ic)
                    made.append(iname)
                used.add(class_id)
            elif class_id is not None:
                cname = isa[class_id]["name"]
                add_record(prefix + slug(cname), cname, "un-sided",
                           "whole-concept", [class_id], class_id,
                           subtree)
                used.add(class_id)
                made.append(cname)
            else:
                for ic in sorted(insts, key=lambda c: isa[c]["name"]):
                    iname = isa[ic]["name"]
                    add_record(prefix + slug(iname), iname,
                               side_of(iname), "whole-concept", [ic],
                               ic, subtree,
                               note="lateralised concept whose "
                                    "side-stripped class does not exist "
                                    "in the release")
                    used.add(ic)
                    made.append(iname)
        return made, used

    # (1) airway: trachea, main bronchi, segmental bronchial trees
    airway_cands = [c for c in tracheobronchial
                    if is_specific_isa(c, AIRWAY_GENERICS)]
    airway_made, airway_used = group_records(
        airway_cands, "airway.", "tracheobronchial-isa",
        AIRWAY_GENERICS)
    # the PART-OF-only "right main bronchus" concept rides on the
    # IS-A "right main bronchus proper" record (same structure, two
    # table representations)
    for rec in records:
        if rec["record_id"] == "airway.right-main-bronchus-proper":
            assert RIGHT_MAIN_PO not in claimed
            claimed[RIGHT_MAIN_PO] = rec["record_id"]
            rec["concept_ids"].append(RIGHT_MAIN_PO)
            rec["note"] = ("keyed on the IS-A concept 'right main "
                           "bronchus proper'; the PART-OF-only "
                           "concept 'right main bronchus' (FMA7395) "
                           "is attached as a second concept id — the "
                           "release names the same bronchus two ways "
                           "in the two tables")

    # (2) laryngeal cartilages
    cart_cands = [c for c in larynx_cartilage
                  if is_specific_isa(c, LARYNX_CARTILAGE_GENERICS)]
    cart_made, cart_used = group_records(
        cart_cands, "larynx.", "larynx-cartilage-isa",
        LARYNX_CARTILAGE_GENERICS)

    # (3) epiglottis (filed by the release under pharynx subdivisions)
    add_record("larynx.epiglottis", isa[EPIGLOTTIS]["name"], "un-sided",
               "whole-concept", [EPIGLOTTIS], EPIGLOTTIS,
               "pharynx-subdivision-isa",
               note="the release files the epiglottis under "
                    "'subdivision of pharynx' / 'subdivision of "
                    "laryngopharynx'; it is recorded here as the "
                    "ninth laryngeal cartilage")

    # (4) laryngeal ligaments + thyrohyoid membranes/ligaments +
    # conus elasticus
    lig_cands = [c for c in (larynx_ligament | thyrohyoid | conus)
                 if is_specific_isa(c, LIGAMENT_GENERICS)]
    lig_made, lig_used = group_records(
        lig_cands, "larynx.", "larynx-ligament-isa", LIGAMENT_GENERICS)

    # (5) nasal cartilages
    nas_cands = [c for c in nasal_cartilage
                 if is_specific_isa(c, NASAL_CARTILAGE_GENERICS)]
    nas_made, nas_used = group_records(
        nas_cands, "nose.", "nasal-cartilage-isa",
        NASAL_CARTILAGE_GENERICS)

    # (6) pharyngeal raphe (sweep addition)
    add_record("pharynx.pharyngeal-raphe", isa[RAPHE_SWEEP]["name"],
               "un-sided", "whole-concept", [RAPHE_SWEEP], RAPHE_SWEEP,
               "pharynx-raphe-isa",
               note="admitted by name sweep; the fibrous midline "
                    "band into which the pharyngeal constrictors "
                    "insert (muscular module records)")

    # (7) PART-OF organs, lobes, segments, nose parts
    po_made = []
    for cid, (rid, side) in sorted(PO_ORGANS.items()):
        assert cid in po
        add_record(rid, po[cid]["name"], side, "partof-organ", [cid],
                   cid, subtree_of[cid],
                   note="organ concept exists only in the PART-OF "
                        "table of BP3D 4.0")
        po_made.append(po[cid]["name"])
    for cid, nm in sorted(PO_LOBES.items(), key=lambda kv: kv[1]):
        assert cid in po and po[cid]["name"] == nm, (cid, nm)
        add_record("lung." + slug(nm), nm, side_of(nm),
                   "partof-concept", [cid], cid, subtree_of[cid])
        po_made.append(nm)
    for cid, side in sorted(PO_SEGMENTS.items(),
                            key=lambda kv: po[kv[0]]["name"]):
        nm = po[cid]["name"]
        add_record("segment." + slug(nm), nm, side, "partof-concept",
                   [cid], cid, subtree_of[cid])
        po_made.append(nm)
    for cid, nm in sorted(PO_NOSE_PARTS.items(), key=lambda kv: kv[1]):
        assert cid in po and po[cid]["name"] == nm, (cid, nm)
        add_record("nose." + slug(nm), nm, "un-sided", "partof-concept",
                   [cid], cid, subtree_of[cid])
        po_made.append(nm)

    # group paths
    for rec in records:
        c0 = rec["concept_ids"][0]
        if rec["representation"].startswith("partof"):
            rec["group_path"] = list(reversed(
                chain_names(c0, po_parent, po)))
        else:
            rec["group_path"] = list(reversed(
                chain_names(c0, parent, isa)))

    repr_counts = Counter(r["representation"] for r in records)

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

    # TotalSegmentator respiratory labels (M3 census in labels.md:
    # exactly 6 of the 104 labels are respiratory)
    ts_labels = [
        ("trachea", ["airway.trachea"],
         "the TS trachea label keys to the IS-A trachea record"),
        ("lung_upper_lobe_left", ["lung.upper-lobe-of-left-lung"],
         "TS segments lobes, not bronchopulmonary segments"),
        ("lung_lower_lobe_left", ["lung.lower-lobe-of-left-lung"], ""),
        ("lung_upper_lobe_right", ["lung.upper-lobe-of-right-lung"], ""),
        ("lung_middle_lobe_right", ["lung.middle-lobe-of-lung"], ""),
        ("lung_lower_lobe_right", ["lung.lower-lobe-of-right-lung"], ""),
    ]
    rec_ids = {r["record_id"] for r in records}
    ts_missing = [lbl for lbl, ids, _ in ts_labels
                  if not all(i in rec_ids for i in ids)]

    xref_counts = Counter(cross_ref(c) for c in universe
                          if cross_ref(c))
    inv_doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA respiratory system inventory — "
                      "Milestone 10"),
            ("generated_by", "tools/resp_map.py"),
            ("source_tables", "data/sources/bodyparts3d-4.0/ (BP3D 4.0 "
                              "/ FMA concept ids and names as released)"),
            ("counting_convention",
             "One record per lateralised instance where the tables "
             "lateralise (right/left as separate records, mirroring "
             "the skeletal, muscular, cardiovascular and nervous "
             "modules); one record for an un-sided class modelled "
             "jointly; a lateralised concept whose side-stripped "
             "class does not exist in the release is one record "
             "keyed on the concept itself. The nose and lungs are "
             "records keyed on their PART-OF-only organ concepts; "
             "the lobes, bronchopulmonary segments and named nose "
             "parts existing only in PART-OF are records keyed on "
             "PART-OF concepts; airway, larynx and nasal-cartilage "
             "structures are records keyed on IS-A concepts. "
             "Muscles, the diaphragm, segmental pulmonary vessels, "
             "the nasal conchae, structural roots, generic part "
             "classes, aggregate/composition concepts, wall/region "
             "classes and the pulmopleural compartments are "
             "censused with cross-references, not recorded here."),
            ("concept_universe", OrderedDict([
                ("total", len(universe)),
                ("isa_total", len(isa_universe)),
                ("partof_total", len(po_universe)),
                ("in_both_tables", len(isa_universe & po_universe)),
                ("isa_sets", {k: len(v) for k, v in isa_sets.items()}),
                ("partof_sets", {k: len(v)
                                 for k, v in po_sets.items()}),
                ("cross_references", dict(xref_counts)),
                ("sweep_rejected_names", sweep_rejected),
            ])),
            ("record_count", len(records)),
            ("record_representations", dict(repr_counts)),
            ("records_by_subtree",
             dict(Counter(r["subtree"] for r in records))),
            ("airway_records", airway_made),
            ("laryngeal_cartilage_records", cart_made),
            ("ligament_membrane_records", lig_made),
            ("nasal_cartilage_records", nas_made),
            ("partof_records", po_made),
            ("totalsegmentator_overlap", OrderedDict([
                ("note", "of the 104 TotalSegmentator v1 labels "
                         "(Milestone 3 census), exactly six are "
                         "respiratory: the trachea and the five lung "
                         "lobes. TS v1 has no bronchopulmonary "
                         "segment, bronchus, larynx, nose, pharynx "
                         "or pleura label, so it adds no coverage "
                         "below the lobe level."),
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
            ("title", "ANATOMICA respiratory system geometry "
                      "resolution — Milestone 10"),
            ("generated_by", "tools/resp_map.py"),
            ("paths", "mesh paths are relative to the project root; "
                      "meshes are the extracted BP3D 4.0 working "
                      "copies under work/bp3d/ (sources in "
                      "data/sources/ stay byte-identical)"),
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

    print("isa sets:", {k: len(v) for k, v in isa_sets.items()})
    print("po sets:", {k: len(v) for k, v in po_sets.items()})
    print("concept universe:", len(universe), "| isa:", len(isa_universe),
          "| po:", len(po_universe),
          "| both:", len(isa_universe & po_universe))
    print("cross references:", dict(xref_counts))
    print("records:", len(records), dict(repr_counts))
    print("records by subtree:",
          dict(Counter(r["subtree"] for r in records)))
    print("airway records:", airway_made)
    print("cartilage records:", cart_made)
    print("ligament/membrane records:", lig_made)
    print("nasal cartilage records:", nas_made)
    print("partof records:", po_made)
    print("sweep rejected:", sweep_rejected)
    print("geometry coverage: %d/%d records have meshes"
          % (covered, len(records)))
    print("TS labels without records:", ts_missing)
    print("absent probes (%d):" % len(absent), absent)
    print(f"wrote {OUT_INV}")
    print(f"wrote {OUT_GEO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
