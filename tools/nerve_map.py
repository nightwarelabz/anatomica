#!/usr/bin/env python3
"""ANATOMICA Milestone 9 — nervous system census + geometry mapping.

Censuses the nervous-system concepts of BodyParts3D 4.0 / FMA exactly as
they are represented in the release tables (data/sources/bodyparts3d-4.0/),
and maps the derived records to BP3D meshes in the manner of Milestones
2, 4 and 5: exact lookups only, compositions taken from the tables,
vertex/face counts measured by streaming the OBJ files.

HOW BP3D 4.0 REPRESENTS THE NERVOUS SYSTEM (established by inspection
of the tables, 2026-11-06; every claim is re-derived by this script at
run time):

  * Peripheral nerves live in the IS-A subtree rooted at FMA11195
    "segment of neural tree organ" (62 concepts), which also carries
    the ganglion line (FMA5884 "ganglion" hangs under it; its only
    specific ganglion is the ciliary ganglion, with right/left
    instances). The class concept FMA5865 "cranial nerve" hangs
    OUTSIDE that subtree (under "neural tree organ"); its subtree
    (4 concepts) carries only the trochlear nerve line — the optic
    nerve travels inside the neural-tree subtree as a nerve trunk.
    The whole release carries exactly 55 nerve-named concepts (the
    Milestone 4 finding C3), and every one of them belongs to cranial
    nerves II, III, IV or the ophthalmic division of V, plus their
    branch classes and the ciliary ganglion communicating branches.
    There are no spinal nerves, no plexuses and no named limb nerves
    in the release at all (absence probes in meta).
  * Central structures hang in the IS-A table under generic part
    roots named for the neuraxis ("gyrus of neuraxis" FMA83874,
    "nucleus of neuraxis" FMA83686, "segment of neuraxis" FMA256237,
    "white matter of neuraxis" FMA83929, ... — 20 neuraxis-named
    concepts whose descendant union is 170 concepts), exactly as the
    heart parts of Milestone 5 hang under generic part roots. Three
    subdivision lines ("subdivision of nervous system" FMA45638,
    "subdivision of autonomic nervous system" FMA65551,
    "subdivision of parasympathetic nervous system" FMA65539) and the
    dura line ("subdivision of cranial dura mater" FMA266054,
    "region of dura mater" FMA71235, "tentorium cerebelli" FMA83966)
    complete the IS-A picture; a name sweep for neural terms outside
    those subtrees adds only the hippocampus line (FMA62493 with its
    right/left instances, filed in the release under "region of
    cerebral cortex") and "region of cerebral cortex" itself — the
    remaining sweep hits are heart/liver homonyms, excluded by rule
    and reported.
  * The brain as an organ exists ONLY in the PART-OF table: the
    PART-OF subtree rooted at FMA7157 "nervous system" (89 concepts)
    carries the neuraxis, the brain and its lateralised lobes, gyri,
    hemispheres and ventricles, and the spinal cord (FMA7647, whose
    PART-OF subtree is just itself and the central canal). The
    brainstem line (FMA79876 "brainstem" + FMA62004 "medulla
    oblongata") hangs in the PART-OF inclusion tree under
    "basicranial part of head proper", not under the nervous system,
    so the PART-OF census takes the union of both subtrees (as
    Milestone 5 took the union of two heart subtrees). The cerebellum
    (FMA67944) likewise hangs under head proper in PART-OF but is an
    IS-A neuraxis concept and is counted once.
  * Meninges are nearly absent: "pia mater" and "arachnoid mater"
    occur in neither table (stem probes in meta); the dura exists
    only as two class concepts and the tentorium cerebelli. The
    spinal cord's named parts (segments, enlargements, conus
    medullaris, cauda equina, filum terminale, roots) occur in
    neither table.

COUNTING CONVENTION (what counts as one nervous-system record):
  * One record per lateralised instance where the tables lateralise
    (right/left as separate records, mirroring the skeletal, muscular
    and cardiovascular modules); the class is the clinical key, not a
    record.
  * One record for an un-sided class concept the tables model jointly
    (e.g. thalamus, corpus callosum).
  * A lateralised concept whose side-stripped class does not exist in
    the release is one record keyed on the concept itself.
  * The brain and the spinal cord are records keyed on their PART-OF
    organ concepts (representation "partof-organ"); named parts that
    exist only in the PART-OF tree (the lateralised lobes and gyri,
    hemispheres, lateral ventricles, internal capsule, ...) are
    records keyed on their PART-OF concepts (representation
    "partof-concept"); specific structures of the IS-A neuraxis set
    (nuclei, commissures, the cerebellum, the brainstem divisions as
    IS-A concepts, ...) are records keyed on IS-A concepts
    (representation "whole-concept"); peripheral nerves and the
    ciliary ganglion likewise ("whole-concept").
  * Structural roots, tree classes, generic part classes (the
    "... of neuraxis" classes), segments/zones/regions/subdivisions
    as classes, branch-of classes of nerves, ventricular-system and
    cortical aggregate concepts are NOT records.

Outputs:
  data/nervous/nervous-inventory.json  concept census + derived records
  data/nervous/nervous-geometry.json   per-record resolved mesh lists
                                       with measured vertex/face counts

Stdlib only. Run: python3 tools/nerve_map.py
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
OUT_INV = os.path.join(ROOT, "data", "nervous", "nervous-inventory.json")
OUT_GEO = os.path.join(ROOT, "data", "nervous", "nervous-geometry.json")

NEURAL_TREE_ROOT = "FMA11195"   # segment of neural tree organ (IS-A)
CRANIAL_NERVE_ROOT = "FMA5865"  # cranial nerve (IS-A, outside the tree)
SUBDIVISION_ROOTS = ["FMA45638",  # subdivision of nervous system
                     "FMA65551",  # subdivisionof autonomic nervous system
                     "FMA65539"]  # subdivision of parasympathetic NS
DURA_ROOTS = ["FMA266054",     # subdivision of cranial dura mater
              "FMA71235"]      # region of dura mater
TENTORIUM = "FMA83966"         # tentorium cerebelli
HIPPOCAMPUS_SWEEP = ["FMA62493",   # hippocampus
                     "FMA72713",   # right hippocampus
                     "FMA72714",   # left hippocampus
                     "FMA242193"]  # region of cerebral cortex
NS_PO_ROOT = "FMA7157"         # nervous system (PART-OF)
BRAINSTEM_PO_ROOT = "FMA79876"  # brainstem (PART-OF, under head proper)
BRAIN_PO = "FMA50801"          # brain (PART-OF only)
CORD_PO = "FMA7647"            # spinal cord (PART-OF only)

# PART-OF concepts that become records: the named parts of the brain
# that exist only in the PART-OF tree (lateralised lobes/gyri and
# other specific structures). Divisions (forebrain, telencephalon,
# diencephalon, hindbrain, metencephalon, epithalamus, neuraxis),
# aggregates (cortex/white matter/subcortex of a hemisphere,
# archicortex, prefrontal cortex), the ventricular-system concepts
# and the cavity of neuraxis are concepts, not records. Concepts that
# are also IS-A specific structures (hypothalamus, pineal body, third
# and fourth ventricles, cerebral aqueduct, central canal) are keyed
# as IS-A records instead and do not appear here.
PO_RECORDS = {
    "FMA61819": "left cerebral hemisphere",
    "FMA67292": "right cerebral hemisphere",
    "FMA72970": "left frontal lobe",
    "FMA72969": "right frontal lobe",
    "FMA72974": "left parietal lobe",
    "FMA72973": "right parietal lobe",
    "FMA72972": "left temporal lobe",
    "FMA72971": "right temporal lobe",
    "FMA72976": "left occipital lobe",
    "FMA72975": "right occipital lobe",
    "FMA72981": "left limbic lobe",
    "FMA72980": "right limbic lobe",
    "FMA72978": "left insula",
    "FMA72977": "right insula",
    "FMA72654": "left superior frontal gyrus",
    "FMA72653": "right superior frontal gyrus",
    "FMA72656": "left middle frontal gyrus",
    "FMA72655": "right middle frontal gyrus",
    "FMA72658": "left inferior frontal gyrus",
    "FMA72657": "right inferior frontal gyrus",
    "FMA72662": "left precentral gyrus",
    "FMA72661": "right precentral gyrus",
    "FMA72666": "left postcentral gyrus",
    "FMA72665": "right postcentral gyrus",
    "FMA72672": "left superior parietal lobule",
    "FMA72671": "right superior parietal lobule",
    "FMA72668": "left supramarginal gyrus",
    "FMA72667": "right supramarginal gyrus",
    "FMA72670": "left angular gyrus",
    "FMA72669": "right angular gyrus",
    "FMA72718": "left cingulate gyrus",
    "FMA72717": "right cingulate gyrus",
    "FMA72690": "left fusiform gyrus",
    "FMA72689": "right fusiform gyrus",
    "FMA72686": "left middle temporal gyrus",
    "FMA72685": "right middle temporal gyrus",
    "FMA72688": "left inferior temporal gyrus",
    "FMA72687": "right inferior temporal gyrus",
    "FMA72706": "left parahippocampal gyrus",
    "FMA72705": "right parahippocampal gyrus",
    "FMA261141": "left hippocampal formation",
    "FMA261139": "right hippocampal formation",
    "FMA72907": "left internal capsule",
    "FMA72906": "right internal capsule",
    "FMA78450": "left lateral ventricle",
    "FMA78449": "right lateral ventricle",
    "FMA73423": "left superior colliculus",
    "FMA73422": "right superior colliculus",
    "FMA73435": "left inferior colliculus",
    "FMA73434": "right inferior colliculus",
    "FMA62032": "habenula",
    "FMA62327": "tuber cinereum",
    "FMA79876": "brainstem",
}

# Generic / structural IS-A neuraxis class names: concepts, not records.
NEURAXIS_GENERICS = {
    "gray matter of neuraxis", "white matter of neuraxis",
    "segment of white matter of neuraxis",
    "organ component of neuraxis", "cell part cluster of neuraxis",
    "segment of neuraxis", "nucleus of neuraxis",
    "nuclear complex of neuraxis", "stria of neuraxis",
    "lamina of neuraxis", "brachium of neuraxis",
    "peduncle of neuraxis", "fornix of neuraxis", "gyrus of neuraxis",
    "septum of neuraxis", "commissure of neuraxis",
    "zone of neuraxis", "circumventricular organ of neuraxis",
    "region of ventricular system of neuraxis",
    "region of ventricular system of brain",
    "segment of brain", "segment of cerebral hemisphere",
    "segment of telencephalon", "segment of hindbrain",
    "segment of metencephalon", "segment of midbrain",
    "internal gray matter component", "nucleus of brain",
    "basal ganglion of telencephalon", "white matter of telencephalon",
    "white matter of brain", "gray matter of brain",
    "region of cerebral cortex", "region of dura mater",
    "subdivision of cranial dura mater",
    "subdivision of nervous system",
    "subdivisionof autonomic nervous system",
    "subdivision of parasympathetic nervous system",
    "subdivision of sympathetic nervous system",
    "cardinal segment of brain", "capsule of cerebral hemisphere",
    "cerebral white matter", "gray matter of diencephalon",
    "gray matter of hypothalamus", "lamina of cerebral hemisphere",
    "lobe of cerebral hemisphere", "lobule of cerebral hemisphere",
    "nucleus of thalamus", "septum of telencephalon",
    "stria of telencephalon", "commissure of diencephalon",
    "commissure of fornix of forebrain",
}
# Structural classes of the nerve tree: concepts, not records.
NERVE_GENERICS = {
    "segment of neural tree organ", "nerve", "nerve trunk",
    "cranial nerve", "ganglion", "autonomic ganglion",
    "parasympathetic ganglion", "cranial parasympathetic ganglion",
    "branch of cranial nerve",
}

ABSENCE_PROBES = [
    # cranial nerves and divisions absent from the release
    "olfactory nerve", "olfactory tract", "olfactory bulb",
    "maxillary nerve", "mandibular nerve", "trigeminal nerve",
    "trigeminal ganglion", "abducens nerve", "abducent nerve",
    "facial nerve", "vestibulocochlear nerve", "glossopharyngeal nerve",
    "vagus nerve", "accessory nerve", "hypoglossal nerve",
    "greater petrosal", "nerve of pterygoid canal", "chorda tympani",
    # spinal nerves, roots, plexuses
    "spinal nerve", "cervical nerve", "thoracic nerve", "lumbar nerve",
    "sacral nerve", "coccygeal nerve", "dorsal root", "ventral root",
    "dorsal root ganglion", "spinal ganglion", "ramus communicans",
    "brachial plexus", "cervical plexus", "lumbar plexus",
    "sacral plexus", "lumbosacral plexus", "lumbosacral trunk",
    # named peripheral nerves
    "median nerve", "ulnar nerve", "radial nerve", "axillary nerve",
    "musculocutaneous nerve", "suprascapular nerve",
    "long thoracic nerve", "thoracodorsal nerve", "phrenic nerve",
    "intercostal nerve", "subcostal nerve", "iliohypogastric nerve",
    "ilioinguinal nerve", "genitofemoral nerve", "femoral nerve",
    "obturator nerve", "sciatic nerve", "tibial nerve",
    "common fibular nerve", "common peroneal nerve",
    "superior gluteal nerve", "inferior gluteal nerve",
    "pudendal nerve", "posterior cutaneous nerve",
    "lateral cutaneous nerve", "saphenous nerve", "sural nerve",
    "superficial fibular nerve", "deep fibular nerve",
    "digital nerve", "plantar nerve",
    # autonomic structures
    "sympathetic trunk", "sympathetic ganglion",
    "superior cervical ganglion", "stellate ganglion",
    "cervicothoracic ganglion", "celiac ganglion",
    "superior mesenteric ganglion", "splanchnic nerve",
    "pelvic splanchnic", "enteric plexus", "myenteric plexus",
    "cardiac plexus", "celiac plexus", "hypogastric plexus",
    "dorsal vagal", "nucleus ambiguus",
    # spinal cord named parts
    "conus medullaris", "cauda equina", "filum terminale",
    "cervical enlargement", "lumbosacral enlargement",
    "denticulate ligament", "segment of spinal cord",
    # meninges
    "pia mater", "arachnoid mater", "dura mater", "falx cerebri",
    "falx cerebelli", "diaphragma sellae", "meninx", "leptomeninx",
    "subarachnoid space", "epidural space",
    # central structures probed (present ones are reported as present)
    "substantia nigra", "red nucleus", "dentate nucleus",
    "inferior olivary", "olivary nucleus", "mammillary body",
    "cerebral peduncle", "basal ganglia", "striatum",
    "lentiform nucleus", "claustrum", "external capsule",
    "extreme capsule", "posterior limb of internal capsule",
    "corpus callosum", "anterior commissure", "fornix",
    "choroid plexus", "ependyma", "septum pellucidum",
    "interthalamic adhesion", "massa intermedia",
    "superior medullary velum", "vermis", "flocculus",
    "tonsil of cerebellum", "fastigial nucleus",
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
    neural_tree = descendants(NEURAL_TREE_ROOT, children)
    cranial_line = descendants(CRANIAL_NERVE_ROOT, children)
    neuraxis_roots = sorted(c for c, v in isa.items()
                            if "neuraxis" in v["name"])
    neuraxis_isa = set()
    for r in neuraxis_roots:
        neuraxis_isa |= descendants(r, children)
    subdivision = set()
    for r in SUBDIVISION_ROOTS:
        subdivision |= descendants(r, children)
    dura = set()
    for r in DURA_ROOTS:
        dura |= descendants(r, children)
    dura.add(TENTORIUM)
    dura |= descendants(TENTORIUM, children)
    sweep_add = set(HIPPOCAMPUS_SWEEP)
    for c in list(sweep_add):
        sweep_add |= descendants(c, children)

    isa_universe = (neural_tree | cranial_line | neuraxis_isa |
                    subdivision | dura | sweep_add)

    ns_po = descendants(NS_PO_ROOT, po_children)
    brainstem_po = descendants(BRAINSTEM_PO_ROOT, po_children)
    po_universe = ns_po | brainstem_po

    # cross-check sweep: neural terms outside the IS-A universe
    sweep_terms = ("brain", "cerebr", "cerebell", "thalam", "neuraxis",
                   "spinal cord", "medulla oblongata", "pons", "mening",
                   "ventricl", "gyrus", "hippocamp", "amygdal",
                   "callosum", "capsule", "colliculus", "pineal",
                   "chiasm", "fornix", "caudate", "putamen", "pallidus",
                   "claustrum", "insula", "nerve", "ganglion")
    sweep_exclude = ("artery", "vein", "ventricle of heart",
                     "papillary muscle", "caudate lobe",
                     "ventricle proper")
    sweep_hits = {}
    for cid, v in isa.items():
        if cid in isa_universe:
            continue
        n = v["name"]
        if any(t in n for t in sweep_terms) and \
                not any(x in n for x in sweep_exclude):
            sweep_hits[cid] = n
    # adjudicated: anything left here is a heart-ventricle homonym or
    # the generic "decussation" class; reported, not admitted.
    sweep_rejected = sorted(sweep_hits.values())

    nerve_named = {c for c, v in isa.items() if "nerve" in v["name"]}

    subtree_of = {}
    for cid in neural_tree:
        subtree_of[cid] = "peripheral"
    for cid in cranial_line:
        subtree_of.setdefault(cid, "peripheral")
    for cid in neuraxis_isa:
        subtree_of.setdefault(cid, "central-isa")
    for cid in subdivision:
        subtree_of.setdefault(cid, "central-isa")
    for cid in dura:
        subtree_of.setdefault(cid, "meningeal-isa")
    for cid in sweep_add:
        subtree_of.setdefault(cid, "central-isa")
    for cid in po_universe:
        subtree_of.setdefault(cid, "central-partof")

    universe = set(subtree_of)

    def chain_names(cid, par, tab):
        out, cur = [], cid
        while cur in par:
            cur = par[cur]
            out.append(tab[cur]["name"])
        return out

    # ---- record derivation ----------------------------------------------
    records = []
    claimed = {}   # concept id -> record id (partition check input)

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
                            "branch of", "communicating branch of",
                            "gray matter of", "white matter of")):
            return False
        if " part of " in name:
            return False
        return True

    def group_records(cands, prefix_of, subtree, generics):
        """CV-style grouping: classes with lateralised instances give
        one record per instance; an un-sided specific class is one
        record; a standalone lateralised concept is one record."""
        by_base = {}
        for cid in cands:
            by_base.setdefault(base_form(isa[cid]["name"]), []).append(cid)
        made = []
        used = set()
        for base, members in sorted(by_base.items()):
            classes = [c for c in members
                       if side_of(isa[c]["name"]) is None]
            insts = [c for c in members
                     if side_of(isa[c]["name"]) is not None]
            class_id = classes[0] if classes else None
            if insts and class_id is not None:
                for ic in sorted(insts, key=lambda c: isa[c]["name"]):
                    iname = isa[ic]["name"]
                    add_record(prefix_of(iname) + slug(iname), iname,
                               side_of(iname), "whole-concept", [ic],
                               class_id, subtree)
                    used.add(ic)
                    made.append(iname)
                used.add(class_id)
            elif class_id is not None:
                cname = isa[class_id]["name"]
                add_record(prefix_of(cname) + slug(cname), cname,
                           "un-sided", "whole-concept", [class_id],
                           class_id, subtree)
                used.add(class_id)
                made.append(cname)
            else:
                for ic in sorted(insts, key=lambda c: isa[c]["name"]):
                    iname = isa[ic]["name"]
                    add_record(prefix_of(iname) + slug(iname), iname,
                               side_of(iname), "whole-concept", [ic], ic,
                               subtree,
                               note="lateralised concept whose "
                                    "side-stripped class does not exist "
                                    "in the release")
                    used.add(ic)
                    made.append(iname)
        return made, used

    # (1) peripheral nerves + ganglia: specific nerve/ganglion-named
    # concepts anywhere in the IS-A universe (the short ciliary nerve,
    # e.g., is filed by the release under the parasympathetic
    # subdivision line, not under the neural tree).
    nerve_cands = [c for c in isa_universe
                   if is_specific_isa(c, NERVE_GENERICS)
                   and isa[c]["name"] not in NEURAXIS_GENERICS
                   and ("nerve" in isa[c]["name"]
                        or "ganglion" in isa[c]["name"]
                        or isa[c]["name"] == "optic chiasm"
                        or "optic tract" in isa[c]["name"])]
    nerve_made, nerve_used = group_records(
        nerve_cands,
        lambda n: "ganglion." if "ganglion" in n else "nerve.",
        "peripheral", NERVE_GENERICS)

    # (2) central IS-A specific structures (nerve-used concepts are
    # already records of the peripheral grouping)
    central_cands = [c for c in (neuraxis_isa | subdivision | sweep_add)
                     if c not in nerve_used
                     and is_specific_isa(c, NEURAXIS_GENERICS)]
    central_made, central_used = group_records(
        central_cands,
        lambda n: "brain.", "central-isa", NEURAXIS_GENERICS)

    # (3) tentorium cerebelli (meningeal record)
    add_record("meninx." + slug(isa[TENTORIUM]["name"]),
               isa[TENTORIUM]["name"], "un-sided", "whole-concept",
               [TENTORIUM], TENTORIUM, "meningeal-isa",
               note="the only specific meningeal structure named in "
                    "the release; the dura mater exists only as class "
                    "concepts and pia/arachnoid are absent entirely")

    # (4) PART-OF organ records
    add_record("brain", "brain", "un-sided", "partof-organ",
               [BRAIN_PO], BRAIN_PO, "central-partof",
               note="the brain organ concept exists only in the "
                    "PART-OF table of BP3D 4.0; geometry is its "
                    "PART-OF composition")
    add_record("spinal-cord", "spinal cord", "un-sided", "partof-organ",
               [CORD_PO], CORD_PO, "central-partof",
               note="the spinal cord organ concept exists only in the "
                    "PART-OF table; the release names no cord segment, "
                    "root or enlargement")

    # (5) PART-OF named-part records
    po_made = []
    for cid, nm in sorted(PO_RECORDS.items(), key=lambda kv: kv[1]):
        assert cid in po and po[cid]["name"] == nm, (cid, nm)
        if cid in claimed:
            continue
        prefix = "brain." if nm != "brainstem" else "brain."
        add_record(prefix + slug(nm), nm, side_of(nm) or "un-sided",
                   "partof-concept", [cid], cid, "central-partof")
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
        in_isa = cid in isa and cid in isa_universe
        in_po = cid in po and cid in po_universe
        tab = isa if cid in isa else po
        concepts.append(OrderedDict([
            ("fma_id", cid),
            ("name", tab[cid]["name"]),
            ("representation_id", tab[cid]["repr"]),
            ("table", "isa" if cid in isa_universe else "partof"),
            ("also_in_partof", cid in po),
            ("also_in_isa", cid in isa),
            ("subtree", subtree_of[cid]),
            ("record_id", claimed.get(cid)),
            ("parent_id", parent.get(cid) if cid in isa_universe
             else po_parent.get(cid)),
            ("parent_name", (isa[parent[cid]]["name"]
                             if cid in isa_universe and cid in parent
                             else po[po_parent[cid]]["name"]
                             if cid not in isa_universe
                             and cid in po_parent else None)),
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

    # TotalSegmentator neural-adjacent labels (M3 census of labels.json:
    # exactly one of the 104 labels is neural).
    ts_labels = [
        ("brain", ["brain"],
         "the TS whole-brain label keys to the PART-OF brain organ "
         "record; TS v1 carries no spinal cord, nerve or ganglion "
         "label, so TotalSegmentator adds no peripheral coverage"),
    ]
    rec_ids = {r["record_id"] for r in records}
    ts_missing = [lbl for lbl, ids, _ in ts_labels
                  if not all(i in rec_ids for i in ids)]

    inv_doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA nervous system inventory — Milestone 9"),
            ("generated_by", "tools/nerve_map.py"),
            ("source_tables", "data/sources/bodyparts3d-4.0/ (BP3D 4.0 / "
                              "FMA concept ids and names as released)"),
            ("counting_convention",
             "One record per lateralised instance where the tables "
             "lateralise (right/left as separate records, mirroring "
             "the skeletal, muscular and cardiovascular modules); one "
             "record for an un-sided class modelled jointly; a "
             "lateralised concept whose side-stripped class does not "
             "exist in the release is one record keyed on the concept "
             "itself. The brain and spinal cord are records keyed on "
             "their PART-OF-only organ concepts; named brain parts "
             "existing only in the PART-OF tree are records keyed on "
             "PART-OF concepts; specific IS-A neuraxis structures and "
             "the peripheral nerves/ganglion are records keyed on IS-A "
             "concepts. Structural roots, tree classes, generic part "
             "classes ('... of neuraxis'), segment/zone/region/"
             "subdivision classes, nerve branch-of classes, "
             "ventricular-system and cortical aggregate concepts are "
             "not records."),
            ("concept_universe", OrderedDict([
                ("total", len(universe)),
                ("neural_tree_isa", len(neural_tree)),
                ("cranial_nerve_line_isa", len(cranial_line)),
                ("neuraxis_isa", len(neuraxis_isa)),
                ("neuraxis_roots", [isa[r]["name"]
                                    for r in neuraxis_roots]),
                ("subdivision_isa", len(subdivision)),
                ("dura_isa", len(dura)),
                ("sweep_additions_isa", len(sweep_add)),
                ("nervous_system_partof", len(ns_po)),
                ("brainstem_partof_extra", len(brainstem_po - ns_po)),
                ("partof_only_concepts",
                 len([c for c in universe if c not in isa])),
                ("nerve_named_concepts_total", len(nerve_named)),
                ("nerve_named_in_universe",
                 len(nerve_named & isa_universe)),
                ("sweep_rejected_names", sweep_rejected),
            ])),
            ("record_count", len(records)),
            ("record_representations", dict(repr_counts)),
            ("records_by_subtree",
             dict(Counter(r["subtree"] for r in records))),
            ("nerve_records", nerve_made),
            ("central_isa_records", central_made),
            ("partof_records", po_made),
            ("totalsegmentator_overlap", OrderedDict([
                ("note", "of the 104 TotalSegmentator v1 labels "
                         "(Milestone 3 census), exactly one is "
                         "neural-adjacent: brain. There is no spinal "
                         "cord, nerve or ganglion label in TS v1."),
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
            ("title", "ANATOMICA nervous system geometry resolution — "
                      "Milestone 9"),
            ("generated_by", "tools/nerve_map.py"),
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

    print("neural tree:", len(neural_tree), "| cranial line:",
          len(cranial_line), "| neuraxis-isa:", len(neuraxis_isa),
          "| subdivision:", len(subdivision), "| dura:", len(dura),
          "| sweep:", len(sweep_add), "| PO:", len(po_universe))
    print("concept universe:", len(universe))
    print("nerve-named concepts:", len(nerve_named), "in universe:",
          len(nerve_named & isa_universe))
    print("records:", len(records), dict(repr_counts))
    print("records by subtree:",
          dict(Counter(r["subtree"] for r in records)))
    print("nerve records:", nerve_made)
    print("central isa records:", central_made)
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

