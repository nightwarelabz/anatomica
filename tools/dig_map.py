#!/usr/bin/env python3
"""ANATOMICA Milestone 11 — digestive system census + geometry mapping.

Censuses the digestive-system concepts of BodyParts3D 4.0 / FMA
exactly as they are represented in the release tables
(data/sources/bodyparts3d-4.0/), and maps the derived records to BP3D
meshes in the manner of Milestones 2, 4, 5, 9 and 10: exact lookups
only, compositions taken from the tables, vertex/face counts measured
by streaming the OBJ files.

HOW BP3D 4.0 REPRESENTS THE DIGESTIVE SYSTEM (established by
inspection of the tables, 2026-11-06; every claim is re-derived by
this script at run time):

  * There is no IS-A digestive tree at all. The IS-A name search for
    a digestive/alimentary/gastrointestinal root finds nothing; the
    IS-A table files each digestive organ as a leaf under generic
    organ classes. The digestive census therefore hangs on the
    PART-OF root FMA7152 "alimentary system" (141 concepts), whose
    gastrointestinal-tract subtree (root FMA71132, 121 concepts)
    carries the canal and the accessory organs, while the remaining
    20 concepts are the mouth, tongue, palate, gingivae, the two
    submandibular glands, the jaw cross-references and the
    pancreaticobiliary grouping node.
  * Inside the PART-OF subtree, the liver carries its full
    morphological apparatus: lobes, hemilivers, sectors and seven of
    the eight hepatovenous segments (ii-viii), plus 40 portal /
    hepatic-artery / hepatic-vein concepts cross-referenced to the
    cardiovascular module by the name rule. (Measured by the
    checker: 30 of the 40 resolve to concepts in the cardiovascular
    census; the 10 intrahepatic branch concepts — the segmental
    hepatic arteries and the lobar portal-vein branches among
    them — are carried only inside this subtree.)
    The biliary apparatus is present as five tree concepts and 13
    named tributaries; the extrahepatic ducts hang in IS-A under
    FMA9706 "bile duct" (6 concepts). There is NO "common bile duct"
    concept anywhere in the release — the tree runs from the common
    hepatic duct straight to the cystic duct junction with the final
    common channel unnamed.
  * Three IS-A-only lines complete the census: the salivary-gland
    line (root FMA9597, 8 concepts — submandibular and sublingual
    glands only; the parotid gland has no concept at all), the tooth
    line (root FMA12516, 56 concepts: 28 lateralised permanent-tooth
    instances and 28 classes — seven tooth types per quadrant, so
    the third molars of the clinical 32-tooth count are absent, as
    are all primary/deciduous teeth), and the hepatovenous-segment
    line (root FMA15737 "hepatovenous subsector", 12 concepts,
    adding segment ix and three in-vivo region classes to the seven
    segments PART-OF carries). The release names its liver segments
    ii-ix: there is no "hepatovenous segment i" concept (segment i
    of the Couinaud classification corresponds to the caudate lobe,
    which the release carries as a lobe concept).
  * The mesentery of the large intestine (FMA14645) exists only in
    IS-A, outside every subtree above; it is admitted by sweep,
    mirroring the transverse mesocolon and mesoappendix records
    PART-OF carries. The external anal sphincter (FMA21930) occurs
    in both tables but hangs under the perineum in PART-OF; it is
    the muscular module's record (Milestone 4) and is censused here
    as a cross-reference sweep set in both tables. The palate
    muscles inside the PART-OF subtree (levator/tensor veli palatini,
    uvular muscle) are likewise muscular cross-references, and the
    upper/lower jaw concepts are skeletal cross-references (the
    skeletal records maxilla_left, maxilla_right and mandible).
  * Name sweeps over both tables adjudicate the remainder (122
    rejected names): the named arteries and veins of the gut and
    liver are cardiovascular records; the tongue and palate muscle
    classes and the digastric / gastrocnemius / puborectalis hits
    are muscular; the spleen and splenic vessels belong to the
    lymphatic/cardiovascular censuses; "segment of colon", "zone of
    ileum" and their kin are generic region classes, not organs.

COUNTING CONVENTION (what counts as one digestive-system record):
  * One record per lateralised instance where the tables
    lateralise; one record for an un-sided class modelled jointly.
  * The nine organs whose concepts anchor the PART-OF subtree
    (mouth, tongue, esophagus, stomach, small and large intestine,
    liver, gallbladder, pancreas) are records keyed on their PART-OF
    concepts ("partof-organ"); the canal divisions, taeniae, liver
    lobes/hemilivers/sectors/segments, biliary trees, the pancreatic
    duct, the mouth parts and the peritoneal structures that exist
    (in this role) only in PART-OF are records keyed on PART-OF
    concepts ("partof-concept"); the extrahepatic ducts, the
    salivary gland instances, hepatovenous segment ix, the mesentery
    of the large intestine and the 28 teeth are records keyed on
    IS-A concepts ("whole-concept"), each lateralised tooth and
    gland keyed on its instance with its side-stripped class carried
    as class_concept_id.
  * Portal/hepatic vessels (cardiovascular), palate muscles and the
    external anal sphincter (muscular), the jaws (skeletal), system
    and tract roots, generic segment/region classes, the in-vivo
    liver region classes, zonal parts of jejunum/ileum, organ walls,
    pancreatic parenchyma, mouth region parts and the named biliary
    tributaries are NOT digestive records; they are censused and
    tagged with their disposition.

Outputs:
  data/digestive/digestive-inventory.json  census + records
  data/digestive/digestive-geometry.json   per-record meshes

Stdlib only. Run: python3 tools/dig_map.py
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
OUT_INV = os.path.join(ROOT, "data", "digestive",
                       "digestive-inventory.json")
OUT_GEO = os.path.join(ROOT, "data", "digestive",
                       "digestive-geometry.json")

ALIMENTARY_PO_ROOT = "FMA7152"      # alimentary system (PART-OF)
GI_TRACT_PO_ROOT = "FMA71132"       # gastrointestinal tract (PART-OF)
SALIVARY_ISA_ROOT = "FMA9597"       # salivary gland
TOOTH_ISA_ROOT = "FMA12516"         # tooth
HEPSEG_ISA_ROOT = "FMA15737"        # hepatovenous subsector
BILIARY_TREE_ISA_ROOT = "FMA71856"  # segment of biliary tree
BILE_DUCT_ISA_ROOT = "FMA9706"      # bile duct
SEGMENT_LIVER_ISA_ROOT = "FMA14495"  # segment of liver
GINGIVA_ISA_ROOT = "FMA59762"       # gingiva
ANAL_SPHINCTER_XREF = "FMA21930"    # external anal sphincter (muscular)
MESENTERY_LI_SWEEP = "FMA14645"     # mesentery of large intestine
                                    # (IS-A only, admitted by sweep)

# PART-OF organ records: concept -> (record_id, side)
PO_ORGANS = {
    "FMA49184": ("mouth", "un-sided"),
    "FMA54640": ("tongue", "un-sided"),
    "FMA7131": ("esophagus", "un-sided"),
    "FMA7148": ("stomach", "un-sided"),
    "FMA7200": ("small-intestine", "un-sided"),
    "FMA7201": ("large-intestine", "un-sided"),
    "FMA7197": ("liver", "un-sided"),
    "FMA7202": ("gallbladder", "un-sided"),
    "FMA7198": ("pancreas", "un-sided"),
}
# PART-OF concept records: concept -> (record_id prefix, expected name)
PO_CONCEPTS = {
    # alimentary canal divisions
    "FMA7206": ("canal", "duodenum"),
    "FMA7207": ("canal", "jejunum"),
    "FMA7208": ("canal", "ileum"),
    "FMA14541": ("canal", "cecum"),
    "FMA14542": ("canal", "appendix"),
    "FMA14545": ("canal", "ascending colon"),
    "FMA14546": ("canal", "transverse colon"),
    "FMA14547": ("canal", "descending colon"),
    "FMA14544": ("canal", "rectum"),
    "FMA11338": ("canal", "ileocecal junction"),
    # taeniae coli
    "FMA15044": ("colon", "taenia libera"),
    "FMA15042": ("colon", "taenia mesocolica"),
    "FMA15043": ("colon", "taenia omentalis"),
    # liver lobes, hemilivers, sectors
    "FMA13362": ("liver", "right lobe of liver"),
    "FMA13363": ("liver", "left lobe of liver"),
    "FMA13365": ("liver", "caudate lobe of liver"),
    "FMA15809": ("liver", "right hemiliver"),
    "FMA15810": ("liver", "left hemiliver"),
    "FMA15748": ("liver", "anterior sector of right liver"),
    "FMA15749": ("liver", "posterior sector of right liver"),
    "FMA15750": ("liver", "anterior sector of left liver"),
    "FMA15751": ("liver", "posterior sector of left liver"),
    # hepatovenous segments ii-viii (PART-OF representations)
    "FMA15739": ("liver-segment", "hepatovenous segment ii"),
    "FMA15741": ("liver-segment", "hepatovenous segment iii"),
    "FMA15742": ("liver-segment", "hepatovenous segment iv"),
    "FMA15743": ("liver-segment", "hepatovenous segment v"),
    "FMA15744": ("liver-segment", "hepatovenous segment vi"),
    "FMA15745": ("liver-segment", "hepatovenous segment vii"),
    "FMA15746": ("liver-segment", "hepatovenous segment viii"),
    # biliary trees
    "FMA14665": ("biliary", "biliary tree"),
    "FMA71891": ("biliary", "hepatic biliary tree"),
    "FMA68016": ("biliary", "intrahepatic biliary tree"),
    "FMA71857": ("biliary", "right hepatic biliary tree"),
    "FMA71858": ("biliary", "left hepatic biliary tree"),
    # pancreatic duct (duct tree concept attached in derivation)
    "FMA10419": ("duct", "pancreatic duct"),
    # mouth parts
    "FMA55021": ("mouth", "soft palate"),
    "FMA55022": ("mouth", "uvula"),
    "FMA59763": ("mouth", "gingiva of upper jaw"),
    "FMA59764": ("mouth", "gingiva of lower jaw"),
    # peritoneum and mesenteries
    "FMA9584": ("peritoneum", "peritoneum"),
    "FMA14703": ("peritoneum", "visceral peritoneum"),
    "FMA9908": ("peritoneum", "peritoneal sac"),
    "FMA14643": ("peritoneum", "mesentery of small intestine"),
    "FMA14647": ("peritoneum", "transverse mesocolon"),
    "FMA16549": ("peritoneum", "mesoappendix"),
}
PANCREATIC_DUCT_TREE = "FMA63103"   # pancreatic duct tree (attached)
# whole-concept records keyed on IS-A concepts
ISA_CONCEPTS = {
    "FMA15747": ("liver-segment", "hepatovenous segment ix"),
    "FMA14669": ("duct", "right hepatic duct"),
    "FMA14670": ("duct", "left hepatic duct"),
    "FMA14668": ("duct", "common hepatic duct"),
    "FMA14539": ("duct", "cystic duct"),
    "FMA76903": ("duct", "left duct of caudate lobe of liver"),
    "FMA14645": ("peritoneum", "mesentery of large intestine"),
}
# salivary gland instances: concept -> class concept
GLANDS = {
    "FMA59802": "FMA55093",   # right submandibular gland
    "FMA59803": "FMA55093",   # left submandibular gland
    "FMA59804": "FMA59791",   # right sublingual gland
    "FMA59805": "FMA59791",   # left sublingual gland
}

MUSCULAR_XREF_IDS = {"FMA46728", "FMA46729",   # levator veli palatini
                     "FMA46731", "FMA46732",   # tensor veli palatini
                     "FMA46733",               # uvular muscle
                     "FMA21930"}               # external anal sphincter
SKELETAL_XREF_IDS = {"FMA54397",               # upper jaw
                     "FMA54398"}               # lower jaw
# grouping / structural classes: censused, never records
GROUPING_IDS = {
    "FMA7152",    # alimentary system (root)
    "FMA71132",   # gastrointestinal tract
    "FMA49177",   # upper gastrointestinal tract
    "FMA49179",   # lower gastrointestinal tract
    "FMA265228",  # pancreaticobiliary system
    "FMA9597",    # salivary gland
    "FMA59788",   # major salivary gland
    "FMA12516",   # tooth
    "FMA55636",   # canine tooth
    "FMA12823",   # incisor tooth
    "FMA55638",   # molar tooth
    "FMA55637",   # premolar tooth
    "FMA84203",   # secondary canine tooth
    "FMA84201",   # secondary incisor tooth
    "FMA84207",   # secondary molar tooth
    "FMA55713",   # lower secondary incisor tooth
    "FMA55721",   # lower secondary molar tooth
    "FMA55717",   # lower secondary premolar tooth
    "FMA55712",   # upper secondary incisor tooth
    "FMA55720",   # upper secondary molar tooth
    "FMA55716",   # upper secondary premolar tooth
    "FMA15737",   # hepatovenous subsector
    "FMA15755",   # region of anterior sector of right liver (in-vivo)
    "FMA15756",   # region of posterior sector of right liver (in-vivo)
    "FMA15757",   # region of anterior sector of left liver (in-vivo)
    "FMA71856",   # segment of biliary tree
    "FMA71859",   # segment of right hepatic biliary tree
    "FMA71860",   # segment of left hepatic biliary tree
    "FMA71865",   # segmental tributary of right hepatic biliary tree
    "FMA71866",   # segmental tributary of left hepatic biliary tree
    "FMA9706",    # bile duct
    "FMA14678",   # extrahepatic bile duct
    "FMA14495",   # segment of liver
    "FMA59762",   # gingiva
}

ABSENCE_PROBES = [
    # canal segments and landmarks with no concept in the release
    "sigmoid colon", "sigmoid mesocolon", "anal canal", "anus",
    "dentate line", "pectinate line", "ileocecal valve", "haustra",
    "appendices epiploicae", "circular folds", "intestinal villus",
    "duodenal gland", "major duodenal papilla",
    "minor duodenal papilla", "hepatopancreatic ampulla",
    "sphincter of hepatopancreatic ampulla",
    # stomach parts
    "cardiac part of stomach", "fundus of stomach", "body of stomach",
    "pyloric part of stomach", "pylorus", "pyloric sphincter",
    "greater curvature", "lesser curvature", "angular incisure",
    # colon flexures
    "hepatic flexure", "splenic flexure", "right colic flexure",
    "left colic flexure",
    # the missing final common channel of the biliary tree
    "common bile duct", "accessory pancreatic duct",
    # pancreas parts
    "head of pancreas", "neck of pancreas", "body of pancreas",
    "tail of pancreas", "uncinate process",
    # liver surface anatomy
    "quadrate lobe", "porta hepatis", "bare area",
    "falciform ligament", "ligamentum teres", "ligamentum venosum",
    "coronary ligament",
    # salivary glands the release does not carry
    "parotid gland", "parotid duct", "submandibular duct",
    "sublingual duct", "minor salivary gland",
    # dentition the release does not carry
    "third molar tooth", "third secondary molar tooth",
    "primary tooth", "deciduous tooth", "dental pulp", "enamel",
    "dentine",
    # peritoneal structures
    "parietal peritoneum", "peritoneal cavity", "lesser sac",
    "omental bursa", "greater omentum", "lesser omentum",
    "epiploic foramen", "omental foramen", "hepatorenal recess",
    "rectovesical pouch", "rectouterine pouch", "root of mesentery",
    # mouth structures carried by other modules' trees only
    "hard palate", "palatine tonsil",
    # named but absent as an exact concept: the release numbers its
    # hepatovenous segments ii-ix; "hepatovenous segment i" occurs
    # only as a substring of ii/iii (exact_concept_exists is the
    # operative field for this probe)
    "hepatovenous segment i",
    # present controls (exact concepts exist)
    "esophagus", "stomach", "duodenum", "liver", "gallbladder",
    "pancreas", "appendix", "tongue", "tooth", "peritoneum",
    "bile duct", "taenia", "submandibular gland",
    "mesentery of small intestine", "hepatovenous segment ii",
    "external anal sphincter", "spleen",
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

    # ---- concept sets ------------------------------------------------------
    salivary_isa = descendants(SALIVARY_ISA_ROOT, children)
    tooth_isa = descendants(TOOTH_ISA_ROOT, children)
    hepseg_isa = descendants(HEPSEG_ISA_ROOT, children)
    biliary_isa = descendants(BILIARY_TREE_ISA_ROOT, children)
    bileduct_isa = descendants(BILE_DUCT_ISA_ROOT, children)
    segliver_isa = descendants(SEGMENT_LIVER_ISA_ROOT, children)
    gingiva_isa = descendants(GINGIVA_ISA_ROOT, children)
    sphincter_x_isa = {ANAL_SPHINCTER_XREF}
    mesentery_li = {MESENTERY_LI_SWEEP}

    isa_sets = OrderedDict([
        ("anal-sphincter-muscular-xref-isa", sphincter_x_isa),
        ("salivary-gland-isa", salivary_isa),
        ("tooth-isa", tooth_isa),
        ("hepatovenous-segment-isa", hepseg_isa),
        ("biliary-tree-isa", biliary_isa),
        ("bile-duct-isa", bileduct_isa),
        ("segment-of-liver-isa", segliver_isa),
        ("gingiva-isa", gingiva_isa),
        ("mesentery-of-large-intestine-sweep-isa", mesentery_li),
    ])
    isa_universe = set()
    for s in isa_sets.values():
        isa_universe |= s

    alimentary_po = descendants(ALIMENTARY_PO_ROOT, po_children)
    gi_po = descendants(GI_TRACT_PO_ROOT, po_children)
    sphincter_x_po = {ANAL_SPHINCTER_XREF}
    po_sets = OrderedDict([
        ("gastrointestinal-tract-partof", gi_po),
        ("alimentary-system-partof", alimentary_po),
        ("anal-sphincter-muscular-xref-partof", sphincter_x_po),
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

    def name_of(cid):
        return isa[cid]["name"] if cid in isa else po[cid]["name"]

    def cross_ref(cid):
        if cid in MUSCULAR_XREF_IDS:
            return "muscular"
        if cid in SKELETAL_XREF_IDS:
            return "skeletal"
        name = name_of(cid)
        if "artery" in name or "vein" in name:
            return "cardiovascular"
        return None

    # cross-check sweeps: digestive terms outside the universe
    sweep_terms = ("digest", "aliment", "gastro", "esophag", "oesophag",
                   "stomach", "gastric", "intestin", "colon", "cecum",
                   "caecum", "append", "rectum", "rectal", "liver",
                   "hepat", "gallbladder", "biliar", "bile", "pancrea",
                   "salivary", "parotid", "submandibular", "sublingual",
                   "tongue", "tooth", "teeth", "gingiva", "palate",
                   "mouth", "peritone", "mesenter", "oment", "duoden",
                   "jejun", "ileum", "sphincter", "spleen", "splenic")
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

    # ---- record derivation --------------------------------------------------
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

    # (1) PART-OF organs
    organ_made = []
    for cid, (rid, side) in sorted(PO_ORGANS.items()):
        assert cid in po
        add_record(rid, po[cid]["name"], side, "partof-organ", [cid],
                   cid, subtree_of[cid],
                   note="organ concept anchoring the PART-OF "
                        "alimentary subtree of BP3D 4.0")
        organ_made.append(po[cid]["name"])

    # (2) PART-OF concepts
    po_made = []
    for cid, (prefix, nm) in sorted(PO_CONCEPTS.items(),
                                    key=lambda kv: kv[1][1]):
        assert cid in po and po[cid]["name"] == nm, (cid, nm)
        add_record(prefix + "." + slug(nm), nm, side_of(nm) or "un-sided",
                   "partof-concept", [cid], cid, subtree_of[cid])
        po_made.append(nm)
    # the pancreatic duct tree concept rides on the pancreatic duct
    # record (same duct system, two table representations)
    for rec in records:
        if rec["record_id"] == "duct.pancreatic-duct":
            assert PANCREATIC_DUCT_TREE not in claimed
            claimed[PANCREATIC_DUCT_TREE] = rec["record_id"]
            rec["concept_ids"].append(PANCREATIC_DUCT_TREE)
            rec["note"] = ("keyed on the PART-OF concept 'pancreatic "
                           "duct'; the 'pancreatic duct tree' concept "
                           "(FMA63103) is attached as a second concept "
                           "id — the release carries the duct and its "
                           "tree as separate concepts")

    # (3) whole-concept records keyed on IS-A concepts
    isa_made = []
    for cid, (prefix, nm) in sorted(ISA_CONCEPTS.items(),
                                    key=lambda kv: kv[1][1]):
        assert cid in isa and isa[cid]["name"] == nm, (cid, nm)
        note = None
        if cid == "FMA15747":
            note = ("IS-A only: PART-OF carries hepatovenous segments "
                    "ii-viii. The Couinaud classification has exactly "
                    "eight segments (i-viii); this ninth named segment "
                    "has no Couinaud counterpart and is recorded as "
                    "the release carries it, flagged in Milestone 11")
        if cid == MESENTERY_LI_SWEEP:
            note = ("admitted by sweep: the concept exists only in "
                    "IS-A, outside the PART-OF alimentary subtree "
                    "that carries the other mesentery records")
        add_record(prefix + "." + slug(nm), nm, side_of(nm) or "un-sided",
                   "whole-concept", [cid], cid, subtree_of[cid],
                   note=note)
        isa_made.append(nm)

    # (4) salivary gland instances (class carried)
    gland_made = []
    for cid, class_id in sorted(GLANDS.items(),
                                key=lambda kv: isa[kv[0]]["name"]):
        assert cid in isa and class_id in isa
        nm = isa[cid]["name"]
        add_record("gland." + slug(nm), nm, side_of(nm), "whole-concept",
                   [cid], class_id, subtree_of[cid])
        gland_made.append(nm)

    # (5) teeth: one record per lateralised permanent-tooth instance,
    # keyed on the instance with its side-stripped class carried
    isa_name_to_id = {v["name"]: k for k, v in isa.items()}
    tooth_made = []
    tooth_instances = sorted(
        (c for c in tooth_isa if side_of(isa[c]["name"]) is not None),
        key=lambda c: isa[c]["name"])
    for cid in tooth_instances:
        nm = isa[cid]["name"]
        class_name = base_form(nm)
        assert class_name in isa_name_to_id, class_name
        add_record("tooth." + slug(nm), nm, side_of(nm), "whole-concept",
                   [cid], isa_name_to_id[class_name], subtree_of[cid])
        tooth_made.append(nm)

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

    # ---- dispositions -------------------------------------------------------
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

    # ---- concept census rows --------------------------------------------------
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

    # ---- absence probes -------------------------------------------------------
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

    # TotalSegmentator digestive labels (M3 census in labels.md:
    # exactly 8 of the 104 labels are digestive; the spleen label is
    # filed under lymphatic in that census and is a cross-reference)
    ts_labels = [
        ("esophagus", ["esophagus"], ""),
        ("stomach", ["stomach"], ""),
        ("duodenum", ["canal.duodenum"],
         "the TS duodenum label keys to the PART-OF duodenum record"),
        ("small_bowel", ["small-intestine"],
         "one undivided TS label for jejunum and ileum together"),
        ("colon", ["large-intestine"],
         "one undivided TS colon label; BP3D splits the colon into "
         "named divisions but carries no sigmoid colon concept"),
        ("liver", ["liver"], ""),
        ("gallbladder", ["gallbladder"], ""),
        ("pancreas", ["pancreas"], ""),
    ]
    rec_ids = {r["record_id"] for r in records}
    ts_missing = [lbl for lbl, ids, _ in ts_labels
                  if not all(i in rec_ids for i in ids)]

    xref_counts = Counter(cross_ref(c) for c in universe
                          if cross_ref(c))
    inv_doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA digestive system inventory — "
                      "Milestone 11"),
            ("generated_by", "tools/dig_map.py"),
            ("source_tables", "data/sources/bodyparts3d-4.0/ (BP3D 4.0 "
                              "/ FMA concept ids and names as released)"),
            ("counting_convention",
             "One record per lateralised instance where the tables "
             "lateralise (right/left as separate records, mirroring "
             "the skeletal, muscular, cardiovascular, nervous and "
             "respiratory modules); one record for an un-sided class "
             "modelled jointly. The nine subtree organs are records "
             "keyed on their PART-OF concepts; canal divisions, "
             "taeniae, liver lobes/hemilivers/sectors/segments, "
             "biliary trees, the pancreatic duct, mouth parts and "
             "peritoneal structures are records keyed on PART-OF "
             "concepts; the extrahepatic ducts, salivary gland "
             "instances, hepatovenous segment ix, the mesentery of "
             "the large intestine and the 28 permanent teeth are "
             "records keyed on IS-A concepts. Portal and hepatic "
             "vessels (cardiovascular), palate muscles and the "
             "external anal sphincter (muscular), the jaws "
             "(skeletal), structural roots, generic classes, in-vivo "
             "region classes, zonal parts, walls, parenchyma, mouth "
             "region parts and named biliary tributaries are "
             "censused with dispositions, not recorded here."),
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
            ("partof_organ_records", organ_made),
            ("partof_concept_records", po_made),
            ("isa_concept_records", isa_made),
            ("salivary_gland_records", gland_made),
            ("tooth_records", tooth_made),
            ("totalsegmentator_overlap", OrderedDict([
                ("note", "of the 104 TotalSegmentator v1 labels "
                         "(Milestone 3 census), exactly eight are "
                         "digestive: esophagus, stomach, duodenum, "
                         "small bowel, colon, liver, gallbladder and "
                         "pancreas, each present in all 1,204 "
                         "subjects. The spleen label is filed under "
                         "lymphatic in that census and is a "
                         "cross-reference only. TS v1 has no segment, "
                         "duct, gland, tooth or peritoneum label, so "
                         "it adds no coverage below the organ level."),
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
                         "in the release. For 'hepatovenous segment "
                         "i' the operative field is "
                         "exact_concept_exists: the string occurs "
                         "only as a substring of segments ii/iii."),
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

    # ---- geometry -------------------------------------------------------------
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
            ("title", "ANATOMICA digestive system geometry "
                      "resolution — Milestone 11"),
            ("generated_by", "tools/dig_map.py"),
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
    print("dispositions:", dict(disp_counts))
    print("records:", len(records), dict(repr_counts))
    print("records by subtree:",
          dict(Counter(r["subtree"] for r in records)))
    print("organ records:", organ_made)
    print("partof concept records:", po_made)
    print("isa concept records:", isa_made)
    print("gland records:", gland_made)
    print("tooth records (%d):" % len(tooth_made), tooth_made)
    print("sweep rejected (%d):" % len(sweep_rejected), sweep_rejected)
    print("geometry coverage: %d/%d records have meshes"
          % (covered, len(records)))
    print("TS labels without records:", ts_missing)
    print("absent probes (%d):" % len(absent), absent)
    print(f"wrote {OUT_INV}")
    print(f"wrote {OUT_GEO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
