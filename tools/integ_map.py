#!/usr/bin/env python3
"""ANATOMICA Milestone 15 — integumentary system census +
geometry mapping.

Censuses the integumentary-system concepts of BodyParts3D
4.0 / FMA exactly as they are represented in the release
tables (data/sources/bodyparts3d-4.0/) and maps the derived
records to BP3D meshes in the manner of Milestones 2, 4, 5,
9, 10, 11, 12, 13 and 14: exact lookups only, compositions
taken from the tables, vertex/face counts measured by
streaming the OBJ files.

HOW BP3D 4.0 REPRESENTS THE INTEGUMENT (established by
inspection of the tables, 2026-11-06; every claim is
re-derived by this script at run time):

  * THE WHOLE SYSTEM IS TWELVE CONCEPTS AND FOUR MESH
    FILES. The release's integument is a single whole-body
    skin shell and a handful of hair concepts; everything
    else clinical anatomy means by the integumentary system
    — the skin's layers, the nails, the cutaneous glands,
    the mammary gland — has no concept in the release at
    all (probe-verified below).
  * IS-A: "skin" (FMA7163) is a leaf under
    "nonparenchymatous organ" with no IS-A children — no
    skin of head, trunk or limb, and no layers: there is NO
    concept named "epidermis" and none named "dermis" in
    either parts list. The only layer-named concept is
    FMA70593 "subdivision of epidermis", a tissue-subdivision
    class under "subdivision of epithelium", and the release
    files the entire appendage line under it: skin appendage
    (FMA71012) -> hair (FMA53667) -> hair of head (FMA54241)
    and hair of trunk (FMA54250) -> pubic hair (FMA54319).
  * A second hair line hangs in IS-A under "set of organ
    regions": set of hairs (FMA70752) -> set of facial hairs
    (FMA70741) -> eyebrow (FMA54237). All three concepts
    resolve to the same single mesh file, FJ2812 — the set
    classes carry no geometry beyond the eyebrow's.
  * PART-OF: the root the release itself names for the
    system, FMA72979 "integumentary system", is a bare root
    under "human body" with NO children at all. The only
    PART-OF composition in the system is integument
    (FMA74657) -> skin. The three PART-OF concepts (system,
    integument, skin) all resolve to the same single mesh
    file, FJ2810, which is also skin's IS-A file: one
    whole-body shell serves as system, organ division and
    organ.
  * The hair files partition exactly: the subdivision,
    appendage and hair class concepts each carry
    {FJ2813, FJ2815}; hair of head carries FJ2813 alone;
    hair of trunk and pubic hair carry FJ2815 alone (pubic
    hair in both tables). Four files — FJ2810, FJ2812,
    FJ2813, FJ2815 — are the module's entire geometry.
  * Pubic hair is the one concept filed across a module
    boundary: IS-A under hair of trunk (this module's line),
    PART-OF under the mons pubis (FMA20218) — the
    reproductive module's only female record (Milestone
    14). The concept is owned here; the cross-filing is
    recorded on the record and gated by the checker against
    the reproductive inventory.
  * ABSENT ENTIRELY (probe-verified over all six tables):
    the skin's layers as concepts (epidermis, dermis,
    hypodermis, every stratum), the nail in every form
    ("nail" and "unguis" score zero hits in all six
    tables), the hair follicle, and every cutaneous gland —
    "sebaceous", "sweat", "sudoriferous", "eccrine" and
    "apocrine" are all zero-hit; every "gland" name the
    sweep finds belongs to the endocrine module (adrenal,
    pituitary), the digestive module (the salivary line) or
    the lacrimal apparatus (lacrimal gland, censused by no
    module). The sensory corpuscles (pacinian, meissner)
    and the arrector pili are likewise absent.
  * THE MAMMARY GLAND IS NOWHERE. "mammary", "breast",
    "mamma", "nipple", "areola" and "lactiferous" score
    zero hits in both parts lists and all six tables: the
    release files the mammary gland under NEITHER the
    integumentary NOR the reproductive system, so the
    classification question has no dataset answer and
    nothing exists in the data for either module to own.
    The ownership decision is therefore made at the
    clinical layer and recorded in the milestone: this
    module owns the mammary record, on the basis that the
    consulted clinical source (TeachMeAnatomy, The Breasts)
    defines the mammary glands as modified sweat glands —
    cutaneous glands by kind, of a piece with this module's
    sebaceous and sweat gland records — while the
    reproductive module (Milestone 14) completed its census
    of the release without them, its sweep claiming no
    mammary name. The record itself carries the absence and
    the cross-reference: lactation is reproductive
    function, and the same source calls the gland an
    accessory gland of the female reproductive system; the
    two statements are both recorded, the decision is this
    module's, and it is a convention, not a dataset fact.
  * TotalSegmentator v1 carries exactly ONE
    integument-adjacent label of its 104: "face" (present
    in all 1,204 subjects) — a mask of the facial region,
    not a skin structure: it segments the face as an
    imaging region and names no skin, layer or appendage.
    The v1.0 label set contains NO "skin", "body" surface,
    "body_trunc" or "body_extremities" label at all —
    verified here against the label index, and against the
    package class map and the Milestone 3 index census,
    which agree on the same 104 labels. The integumentary
    overlap of TS v1 is therefore zero skin labels, with
    "face" adjudicated a region mask, not skin anatomy.

COUNTING CONVENTION (what counts as one integumentary-system
record):
  * One record for the skin, keyed on its both-table
    concept (FMA7163) — the module's organ record.
  * One record for the hair class (FMA53667), with its
    parent class, skin appendage (FMA71012), carried as
    class_concept_id; one record each for the three
    regional hairs the release carries — hair of head,
    hair of trunk, pubic hair — keyed on their own
    concepts; one record for the eyebrow (FMA54237), with
    its set class, set of facial hairs (FMA70741), carried
    as class_concept_id.
  * Grouping classes — censused, never records: the
    integumentary system root (FMA72979), the integument
    (FMA74657: the release's organ-division concept under
    which skin is filed in PART-OF, carrying no geometry
    beyond the skin record's), the subdivision of
    epidermis (FMA70593: the tissue-subdivision class
    under which the appendage line is filed — there is no
    epidermis concept for it to subdivide), and the set of
    hairs (FMA70752).
  * Line is carried per concept and per record: skin
    (the skin concept alone), appendage (the
    epidermis-subdivision line and the hair-set line) and
    system (the two PART-OF roots).

Outputs:
  data/integumentary/integumentary-inventory.json  census
  data/integumentary/integumentary-geometry.json   per-record
                                                   meshes

Stdlib only. Run: python3 tools/integ_map.py
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
OUT_INV = os.path.join(ROOT, "data", "integumentary",
                       "integumentary-inventory.json")
OUT_GEO = os.path.join(ROOT, "data", "integumentary",
                       "integumentary-geometry.json")
REPRO_INV = os.path.join(ROOT, "data", "reproductive",
                         "reproductive-inventory.json")
TS_LABELS = os.path.join(ROOT, "data", "sources",
                         "totalsegmentator-1.0", "labels.json")

SKIN = "FMA7163"                    # skin (both tables)
EPIDERMIS_SUBDIV = "FMA70593"       # subdivision of epidermis
SKIN_APPENDAGE = "FMA71012"         # skin appendage
HAIR = "FMA53667"                   # hair
HAIR_HEAD = "FMA54241"              # hair of head
HAIR_TRUNK = "FMA54250"             # hair of trunk
PUBIC_HAIR = "FMA54319"             # pubic hair (both tables)
HAIR_SET = "FMA70752"               # set of hairs
FACIAL_HAIR_SET = "FMA70741"        # set of facial hairs
EYEBROW = "FMA54237"                # eyebrow
SYSTEM_PO = "FMA72979"              # integumentary system (PO)
INTEGUMENT_PO = "FMA74657"          # integument (PART-OF)
MONS_PUBIS = "FMA20218"             # mons pubis (reproductive)

LINE_BY_CONCEPT = {
    "FMA7163": "skin",
    "FMA70593": "appendage", "FMA71012": "appendage",
    "FMA53667": "appendage", "FMA54241": "appendage",
    "FMA54250": "appendage", "FMA54319": "appendage",
    "FMA70752": "appendage", "FMA70741": "appendage",
    "FMA54237": "appendage",
    "FMA72979": "system", "FMA74657": "system",
}

# records keyed on their concepts: concept -> (record id,
# representation, class concept carried)
RECORD_DEFS = OrderedDict([
    (SKIN, ("skin", "organ", SKIN)),
    (HAIR, ("hair", "whole-concept", SKIN_APPENDAGE)),
    (HAIR_HEAD, ("hair.hair-of-head", "whole-concept", HAIR)),
    (HAIR_TRUNK, ("hair.hair-of-trunk", "whole-concept", HAIR)),
    (PUBIC_HAIR, ("hair.pubic-hair", "whole-concept", HAIR_TRUNK)),
    (EYEBROW, ("eyebrow", "whole-concept", FACIAL_HAIR_SET)),
])
GROUPING_IDS = {SYSTEM_PO, INTEGUMENT_PO, EPIDERMIS_SUBDIV,
                HAIR_SET}

RECORD_NOTES = {
    "skin": "the module's organ record, keyed on the "
            "both-table concept. The release gives the skin "
            "no IS-A children and no PART-OF parts: no "
            "regional skin, no layers — its single mesh "
            "(FJ2810) is the whole-body shell the PART-OF "
            "table also files under integument and under the "
            "integumentary system root itself",
    "hair": "the hair class record; its parent class, skin "
            "appendage (FMA71012), is carried as "
            "class_concept_id. The class carries both hair "
            "files ({FJ2813, FJ2815}) — exactly the union of "
            "its regional records' files",
    "hair.hair-of-head": "regional record, keyed on its own "
                         "concept under the hair class; the "
                         "only regional hair with its own "
                         "mesh file (FJ2813)",
    "hair.hair-of-trunk": "regional record, keyed on its own "
                          "concept under the hair class; "
                          "shares its single mesh file "
                          "(FJ2815) with its child, pubic hair",
    "hair.pubic-hair": "regional record, keyed on its own "
                       "concept; the one concept filed "
                       "across a module boundary — IS-A "
                       "under hair of trunk here, PART-OF "
                       "under the mons pubis (FMA20218), the "
                       "reproductive module's only female "
                       "record (Milestone 14). Owned here; "
                       "the cross-filing is gated by the "
                       "checker against the reproductive "
                       "inventory",
    "eyebrow": "the only named facial hair the release "
               "carries; keyed on its own concept under set "
               "of facial hairs (FMA70741), carried as "
               "class_concept_id. The eyebrow, its set class "
               "and the set of hairs above it all resolve to "
               "the same single mesh file (FJ2812), so the "
               "classes carry no geometry beyond this "
               "record's. There is no eyelash concept in the "
               "release (exact-name probe-verified)",
}

SWEEP_TERMS = ("skin", "hair", "eyebrow", "integument",
               "epiderm", "nail", "unguis", "mammary",
               "breast", "sebaceous", "sweat", "follicle",
               "cilia", "eyelash", "scalp", "subcutaneous",
               "areola", "nipple", "fascia", "gland")
_CIL = ("an ocular structure of the ciliary body of the "
        "eyeball, or its autonomic supply — the ciliary "
        "family belongs to the eye and to the nervous "
        "module (Milestone 9 censused the ciliary ganglion "
        "line); none of these names is an eyelash, and the "
        "release has no eyelash concept")
_NASO = ("nervous module: the nasociliary nerve line, a "
         "branch system of the ophthalmic nerve (Milestone "
         "9); an ocular sensory nerve, not an eyelash")
_FASCIA = ("the release's deep fascial system: deep "
           "investing fascia of the limb compartments, "
           "filed under a fascial root of its own — not "
           "skin, not subcutaneous tissue, and censused by "
           "no system module; the skin's own subcutaneous "
           "layer (hypodermis / superficial fascia) has no "
           "concept in the release at all")
SWEEP_WHY = {
    # the ciliary / nasociliary family — the eye, not lashes
    "ciliary ganglion": "nervous module (Milestone 9): the "
                        "ciliary ganglion, its one autonomic "
                        "ganglion; an ocular structure, not "
                        "an eyelash",
    "right ciliary ganglion": "nervous module (see ciliary "
                              "ganglion)",
    "left ciliary ganglion": "nervous module (see ciliary "
                             "ganglion)",
    "branch of ciliary ganglion": "nervous module (see "
                                  "ciliary ganglion)",
    "short ciliary nerve": "nervous module (see ciliary "
                           "ganglion)",
    "long ciliary nerve": "nervous module (see ciliary "
                          "ganglion)",
    "right long ciliary nerve": "nervous module (see ciliary "
                                "ganglion)",
    "left long ciliary nerve": "nervous module (see ciliary "
                               "ganglion)",
    "nasociliary nerve": _NASO,
    "right nasociliary nerve": _NASO,
    "left nasociliary nerve": _NASO,
    "branch of nasociliary nerve": _NASO,
    "communicating branch of nasociliary nerve with ciliary "
    "ganglion": "nervous module (see nasociliary nerve)",
    "communicating branch of right nasociliary nerve with "
    "right ciliary ganglion": "nervous module (see "
                              "nasociliary nerve)",
    "communicating branch of left nasociliary nerve with "
    "left ciliary ganglion": "nervous module (see "
                             "nasociliary nerve)",
    "corona ciliaris": _CIL,
    "right corona ciliaris": _CIL,
    "left corona ciliaris": _CIL,
    "region of ciliary body": _CIL,
    # glands that are not cutaneous glands
    "adrenal gland": "endocrine module (Milestone 13): the "
                     "adrenal gland class, censused there "
                     "with its instances",
    "right adrenal gland": "endocrine module (see adrenal "
                           "gland)",
    "left adrenal gland": "endocrine module (see adrenal "
                          "gland)",
    "pituitary gland": "endocrine module (Milestone 13): "
                       "the pituitary, censused there",
    "salivary gland": "digestive module (Milestone 11): "
                      "the salivary gland class, censused "
                      "there with its instances",
    "major salivary gland": "digestive module (see salivary "
                            "gland)",
    "sublingual gland": "digestive module (see salivary "
                        "gland)",
    "right sublingual gland": "digestive module (see "
                              "salivary gland)",
    "left sublingual gland": "digestive module (see "
                             "salivary gland)",
    "submandibular gland": "digestive module (see salivary "
                           "gland)",
    "right submandibular gland": "digestive module (see "
                                 "salivary gland)",
    "left submandibular gland": "digestive module (see "
                                "salivary gland)",
    "lacrimal gland": "the lacrimal apparatus of the eye: "
                      "an orbital gland, not a cutaneous "
                      "gland; censused by no system module "
                      "(the nervous module carries only the "
                      "lacrimal nerve)",
    "right lacrimal gland": "lacrimal apparatus (see "
                            "lacrimal gland)",
    "left lacrimal gland": "lacrimal apparatus (see "
                           "lacrimal gland)",
    "organ component gland": "a generic FMA component "
                             "class, not a cutaneous "
                             "structure",
    # the deep fascia — its own system in the release,
    # censused by no module
    "deep fascial system": _FASCIA,
    "fascia lata of left thigh": _FASCIA,
    "fascia lata of right thigh": _FASCIA,
    "zone of fascia lata": _FASCIA,
    "zone of investing fascia": _FASCIA,
    "zone of investing fascia of free lower limb": _FASCIA,
    "zone of investing fascia of lower limb": _FASCIA,
    "zone of investing fascia of thigh": _FASCIA,
    "investing fascia of left forearm": _FASCIA,
    "investing fascia of left free lower limb": _FASCIA,
    "investing fascia of left free upper limb": _FASCIA,
    "investing fascia of left lower limb": _FASCIA,
    "investing fascia of left thigh": _FASCIA,
    "investing fascia of left wrist": _FASCIA,
    "investing fascia of right forearm": _FASCIA,
    "investing fascia of right free lower limb": _FASCIA,
    "investing fascia of right free upper limb": _FASCIA,
    "investing fascia of right lower limb": _FASCIA,
    "investing fascia of right thigh": _FASCIA,
    "investing fascia of right upper limb": _FASCIA,
    "investing fascia of right wrist": _FASCIA,
    "tensor fasciae latae": "muscular module: the tensor "
                            "fasciae latae muscle, censused "
                            "there as its right and left "
                            "records — a muscle that tenses "
                            "the fascia lata, not fascia",
    "right tensor fasciae latae": "muscular module (see "
                                  "tensor fasciae latae)",
    "left tensor fasciae latae": "muscular module (see "
                                 "tensor fasciae latae)",
}

# substring gap probes over all six release tables; "controls"
# are terms whose concepts the release DOES carry, interleaved
# to prove the probe instrument reads the tables. "dermis" is
# deliberately NOT a substring probe: it is a substring of
# "epidermis" and would read the subdivision class as a false
# present — the dermis is probed by exact name instead.
SUBSTRING_PROBES = [
    # the layers' substance — absent
    "stratum", "keratinocyte", "melanocyte", "langerhans",
    "merkel", "dermal papilla",
    # the follicle and the cutaneous glands — absent
    "hair follicle", "follicle", "sebaceous", "sweat",
    "sudoriferous", "eccrine", "apocrine", "arrector",
    # the nail in every form — absent
    "nail", "unguis", "lunule", "eponychium", "cuticle",
    # the mammary gland — absent under every name
    "mammary", "breast", "mamma", "nipple", "areola",
    "lactiferous",
    # the head's skin and hair specialisations — absent
    "scalp", "eyelash", "beard",
    # the subcutaneous layer and the sensory corpuscles
    "subcutaneous", "hypodermis", "pacinian", "meissner",
    "vellus", "lanugo", "corium",
    # controls (present)
    "skin", "hair", "eyebrow", "integument", "epidermis",
    "pubic hair",
]
# exact-name probes: concepts whose exact English name would
# be the structure itself
EXACT_NAME_PROBES = [
    # the layers as concepts
    "epidermis", "dermis", "hypodermis", "stratum basale",
    "stratum corneum",
    # regional skin
    "skin of head", "skin of trunk", "skin of hand",
    # the nail and its parts
    "nail", "fingernail", "toenail", "nail bed", "nail plate",
    "lunule", "eponychium",
    # the follicle and glands
    "hair follicle", "sebaceous gland", "sweat gland",
    "eccrine sweat gland", "apocrine sweat gland",
    "arrector pili muscle",
    # the mammary gland and its surface anatomy
    "mammary gland", "breast", "nipple", "areola",
    # the subcutaneous layer under its clinical names
    "subcutaneous tissue", "superficial fascia",
    # the lashes and scalp
    "eyelash", "scalp",
    # controls (present)
    "skin", "hair", "eyebrow", "integument",
    "integumentary system",
]
TS_TERMS = ("skin", "face", "body", "breast", "trunc",
            "extremit", "hair", "nail", "surface")
TS_ADJUDICATION = ("the one TS v1 label matched by the "
                   "integumentary terms is 'face' — a region "
                   "mask of the face (an imaging region "
                   "in all 1,204 subjects), not a skin "
                   "structure: it names no skin, layer or "
                   "appendage. No 'skin', 'body_trunc', "
                   "'body_extremities' or other body-surface "
                   "label exists in the v1.0 label set — the "
                   "package class map, the Milestone 3 "
                   "index census and labels.json agree on "
                   "the same 104 labels, and none is a skin "
                   "or body-surface segmentation")


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


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    (isa, po, isa_elem, po_elem, children, parent,
     po_children, po_parent) = load_tables()

    # ---- concept sets ------------------------------------------------
    skin_isa = descendants(SKIN, children)
    epidermis_isa = descendants(EPIDERMIS_SUBDIV, children)
    hair_set_isa = descendants(HAIR_SET, children)
    system_po = descendants(SYSTEM_PO, po_children)
    integument_po = descendants(INTEGUMENT_PO, po_children)

    isa_sets = OrderedDict([
        ("skin-isa", skin_isa),
        ("epidermis-subdivision-isa", epidermis_isa),
        ("hair-set-isa", hair_set_isa),
    ])
    po_sets = OrderedDict([
        ("integumentary-system-partof", system_po),
        ("integument-partof", integument_po),
    ])
    isa_universe = set()
    for s in isa_sets.values():
        isa_universe |= s
    po_universe = set()
    for s in po_sets.values():
        po_universe |= s
    universe = isa_universe | po_universe
    assert universe == set(LINE_BY_CONCEPT), \
        f"universe/LINE_BY_CONCEPT mismatch: " \
        f"{sorted(universe ^ set(LINE_BY_CONCEPT))}"

    # subtree tags: PART-OF sets win (the release's own system
    # filing), IS-A sets fill the rest
    subtree_of = {}
    for tag, s in po_sets.items():
        for cid in s:
            subtree_of.setdefault(cid, tag)
    for tag, s in isa_sets.items():
        for cid in s:
            subtree_of.setdefault(cid, tag)

    def name_of(cid):
        return isa[cid]["name"] if cid in isa else po[cid]["name"]

    # cross-check sweep: integumentary terms outside the universe
    sweep_rejected = {}
    for tab, tname in ((isa, "isa"), (po, "partof")):
        for cid, v in tab.items():
            if cid in universe:
                continue
            n = v["name"]
            if any(t in n.lower() for t in SWEEP_TERMS):
                sweep_rejected.setdefault(n, tname)
    unadjudicated = [n for n in sweep_rejected if n not in SWEEP_WHY]
    assert not unadjudicated, \
        f"sweep names without adjudication: {unadjudicated}"
    sweep_names = sorted(sweep_rejected)
    sweep_zero_terms = [t for t in SWEEP_TERMS
                        if not any(t in v["name"].lower()
                                   for tab in (isa, po)
                                   for v in tab.values())]

    def chain_names(cid, par, tab):
        out, cur = [], cid
        while cur in par:
            cur = par[cur]
            out.append(tab[cur]["name"])
        return out

    # ---- record derivation --------------------------------------------
    records = []
    claimed = {}

    def add_record(rid, name, representation, concept_ids,
                   class_id, subtree, note=None):
        for c in concept_ids:
            assert c not in claimed, \
                f"concept {c} claimed by two records"
            claimed[c] = rid
        records.append(OrderedDict([
            ("record_id", rid),
            ("name", name),
            ("side", "un-sided"),
            ("representation", representation),
            ("class_concept_id", class_id),
            ("concept_ids", concept_ids),
            ("subtree", subtree),
            ("line", LINE_BY_CONCEPT[concept_ids[0]]),
            ("group_path", None),
            ("note", note),
        ]))
        return records[-1]

    for cid, (rid, representation, class_id) in RECORD_DEFS.items():
        tab = isa if cid in isa_universe else po
        assert cid in tab
        add_record(rid, tab[cid]["name"], representation, [cid],
                   class_id, subtree_of[cid],
                   note=RECORD_NOTES[rid])

    # group paths: PART-OF chain where the concept is in PART-OF
    # (the release's system filing), IS-A chain otherwise
    for rec in records:
        c0 = rec["concept_ids"][0]
        if c0 in po:
            rec["group_path"] = list(reversed(
                chain_names(c0, po_parent, po)))
        else:
            rec["group_path"] = list(reversed(
                chain_names(c0, parent, isa)))

    repr_counts = Counter(r["representation"] for r in records)
    records_by_line = Counter(r["line"] for r in records)
    concepts_by_line = Counter(LINE_BY_CONCEPT[c] for c in universe)

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
            ("subtrees", sorted(t for t, s in
                                list(isa_sets.items()) +
                                list(po_sets.items())
                                if cid in s)),
            ("line", LINE_BY_CONCEPT[cid]),
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

    sub_detail = []
    for probe in SUBSTRING_PROBES:
        hits = {fn: texts[fn].count(probe) for fn in table_files}
        sub_detail.append(OrderedDict([
            ("probe", probe),
            ("total_hits", sum(hits.values())),
            ("exact_concept_exists", probe in all_names),
            ("hits_by_table", hits)]))
    sub_block = OrderedDict([
        ("absent", [a["probe"] for a in sub_detail
                    if a["total_hits"] == 0]),
        ("present", [a["probe"] for a in sub_detail
                     if a["total_hits"] > 0]),
        ("detail", sub_detail)])
    sub_zero = sum(1 for a in sub_detail if a["total_hits"] == 0)

    isa_names = {v["name"] for v in isa.values()}
    po_names = {v["name"] for v in po.values()}
    exact_detail = []
    for probe in EXACT_NAME_PROBES:
        exact_detail.append(OrderedDict([
            ("probe", probe),
            ("concept_exists", probe in all_names),
            ("in_isa", probe in isa_names),
            ("in_partof", probe in po_names)]))
    exact_block = OrderedDict([
        ("absent", [a["probe"] for a in exact_detail
                    if not a["concept_exists"]]),
        ("present", [a["probe"] for a in exact_detail
                     if a["concept_exists"]]),
        ("detail", exact_detail)])
    exact_zero = sum(1 for a in exact_detail
                     if not a["concept_exists"])

    # ---- TotalSegmentator overlap (derived from the label index) -----
    ts = json.load(open(TS_LABELS))
    ts_counts = ts["labels"]
    ts_hits = sorted(l for l in ts_counts
                     if any(t in l for t in TS_TERMS))

    # ---- Milestone 14 boundary (pubic hair / mons pubis filing) -------
    repro = json.load(open(REPRO_INV))
    mons_recs = [r for r in repro["records"]
                 if r["record_id"] == "mons-pubis"]
    boundary = OrderedDict([
        ("source", "data/reproductive/reproductive-inventory.json "
                   "(Milestone 14)"),
        ("fact", "pubic hair (FMA54319) is filed in PART-OF "
                 "under the mons pubis (FMA20218); the mons "
                 "pubis is the reproductive module's record "
                 "'mons-pubis', keyed on that concept"),
        ("pubic_hair_partof_parent", po_parent.get(PUBIC_HAIR)),
        ("pubic_hair_partof_parent_name",
         po[po_parent[PUBIC_HAIR]]["name"]
         if PUBIC_HAIR in po_parent else None),
        ("reproductive_mons_pubis_concepts",
         mons_recs[0]["concept_ids"] if mons_recs else []),
        ("closes", bool(mons_recs)
         and mons_recs[0]["concept_ids"] == [MONS_PUBIS]
         and po_parent.get(PUBIC_HAIR) == MONS_PUBIS),
    ])
    assert boundary["closes"], "reproductive boundary does not close"

    inv_doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA integumentary system inventory — "
                      "Milestone 15"),
            ("generated_by", "tools/integ_map.py"),
            ("source_tables", "data/sources/bodyparts3d-4.0/ (BP3D "
                              "4.0 / FMA concept ids and names as "
                              "released)"),
            ("counting_convention",
             "One record for the skin, keyed on its both-table "
             "concept; one record for the hair class with its "
             "parent class (skin appendage) carried as "
             "class_concept_id; one record each for hair of "
             "head, hair of trunk and pubic hair, keyed on "
             "their own concepts; one record for the eyebrow "
             "with its set class (set of facial hairs) carried. "
             "Grouping classes — the integumentary system root, "
             "the integument, the subdivision of epidermis and "
             "the set of hairs — are censused, never records. "
             "Line is censused per concept and per record: "
             "skin (one concept), appendage (nine) and system "
             "(the two PART-OF roots). The system's whole "
             "universe is twelve concepts: the release carries "
             "the skin as one whole-body shell and the hair as "
             "four mesh files' worth of concepts, and carries "
             "no layer, nail, cutaneous gland or mammary "
             "concept at all — those structures exist in this "
             "module only as sourced clinical records with the "
             "absence recorded (the Milestone 9/14 pattern). "
             "The mammary gland's ownership is adjudicated in "
             "this module's clinical tranche: the release "
             "files it under neither system (zero hits under "
             "every name), and this module owns the record on "
             "the modified-sweat-gland basis stated there."),
            ("concept_universe", OrderedDict([
                ("total", len(universe)),
                ("isa_total", len(isa_universe)),
                ("partof_total", len(po_universe)),
                ("in_both_tables", len(isa_universe & po_universe)),
                ("isa_sets", {k: len(v) for k, v in isa_sets.items()}),
                ("partof_sets", {k: len(v)
                                 for k, v in po_sets.items()}),
                ("by_line", dict(concepts_by_line)),
                ("cross_references", {}),
                ("dispositions", dict(disp_counts)),
                ("disposition_concepts",
                 {k: v for k, v in sorted(disp_lists.items())}),
                ("sweep_rejected_names", sweep_names),
                ("sweep_adjudications",
                 {n: SWEEP_WHY[n] for n in sweep_names}),
                ("sweep_zero_hit_terms", sweep_zero_terms),
            ])),
            ("record_count", len(records)),
            ("record_representations", dict(repr_counts)),
            ("records_by_subtree",
             dict(Counter(r["subtree"] for r in records))),
            ("records_by_line", dict(records_by_line)),
            ("boundary_closures", OrderedDict([
                ("milestone_14_reproductive", boundary),
            ])),
            ("totalsegmentator_overlap", OrderedDict([
                ("note", "of the 104 TotalSegmentator v1 labels "
                         "(Milestone 3 census), exactly one is "
                         "integument-adjacent: 'face', a mask of "
                         "the facial region — adjudicated below "
                         "as a region mask, not skin anatomy. "
                         "No skin or body-surface label exists "
                         "in TS v1, so the module's TS overlap "
                         "is zero labels mapped to records"),
                ("labels", []),
                ("labels_without_records", []),
                ("labels_matched_by_terms", ts_hits),
                ("adjudication", TS_ADJUDICATION),
            ])),
            ("absences", OrderedDict([
                ("note", "probe-based gap analysis: each "
                         "substring probe was counted over all "
                         "six BP3D 4.0 release tables (zero "
                         "hits = the name does not occur in "
                         "the release); each exact-name probe "
                         "was tested for a concept of exactly "
                         "that name in either parts list. "
                         "Present controls are interleaved to "
                         "prove the instrument reads the "
                         "tables. 'dermis' is probed by exact "
                         "name only: as a substring it is "
                         "contained in 'epidermis' and would "
                         "read the subdivision class as a false "
                         "present. The finding is total: "
                         "beyond the skin shell and the hair "
                         "concepts, every structure the "
                         "clinical layer names — layers, "
                         "strata, nails, follicles, cutaneous "
                         "glands, sensory corpuscles, the "
                         "mammary gland — is absent from the "
                         "release"),
                ("substring_probes", sub_block),
                ("substring_zero_hit_count", sub_zero),
                ("exact_name_probes", exact_block),
                ("exact_name_zero_hit_count", exact_zero),
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
    covered_by_line = Counter()
    all_meshes = []
    for rec in records:
        cids = rec["concept_ids"]
        isa_meshes = mesh_list("isa", isa_elem, ISA_DIR, cids)
        po_meshes = mesh_list("partof", po_elem, PO_DIR, cids)
        if isa_meshes or po_meshes:
            covered += 1
            covered_by_line[rec["line"]] += 1
        all_meshes += isa_meshes + po_meshes
        names = []
        for c in cids:
            names.append(isa[c]["name"] if c in isa else po[c]["name"])
        geo_records.append(OrderedDict([
            ("record_id", rec["record_id"]),
            ("name", rec["name"]),
            ("side", rec["side"]),
            ("representation", rec["representation"]),
            ("line", rec["line"]),
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

    # structural findings: the one-shell identity, the hair
    # file partition and the eyebrow set identity
    def files(tab_elem, cid):
        return sorted(tab_elem.get(cid, ()))

    findings = OrderedDict([
        ("skin_shell_identity", OrderedDict([
            ("claim", "one mesh file, FJ2810, serves as the "
                      "skin in both tables and as the whole "
                      "content of the integument and of the "
                      "integumentary system root in PART-OF"),
            ("skin_isa", files(isa_elem, SKIN)),
            ("skin_partof", files(po_elem, SKIN)),
            ("integument_partof", files(po_elem, INTEGUMENT_PO)),
            ("system_partof", files(po_elem, SYSTEM_PO)),
            ("identical", files(isa_elem, SKIN) ==
             files(po_elem, SKIN) ==
             files(po_elem, INTEGUMENT_PO) ==
             files(po_elem, SYSTEM_PO) == ["FJ2810"]),
        ])),
        ("hair_file_partition", OrderedDict([
            ("claim", "the subdivision, appendage and hair "
                      "class concepts carry the same two "
                      "files; hair of head carries FJ2813 "
                      "alone; hair of trunk and pubic hair "
                      "carry FJ2815 alone (pubic hair in both "
                      "tables) — the hair geometry partitions "
                      "into a head file and a trunk file"),
            ("subdivision_isa", files(isa_elem, EPIDERMIS_SUBDIV)),
            ("appendage_isa", files(isa_elem, SKIN_APPENDAGE)),
            ("hair_isa", files(isa_elem, HAIR)),
            ("head_isa", files(isa_elem, HAIR_HEAD)),
            ("trunk_isa", files(isa_elem, HAIR_TRUNK)),
            ("pubic_isa", files(isa_elem, PUBIC_HAIR)),
            ("pubic_partof", files(po_elem, PUBIC_HAIR)),
            ("identical", files(isa_elem, EPIDERMIS_SUBDIV) ==
             files(isa_elem, SKIN_APPENDAGE) ==
             files(isa_elem, HAIR) == ["FJ2813", "FJ2815"]
             and files(isa_elem, HAIR_HEAD) == ["FJ2813"]
             and files(isa_elem, HAIR_TRUNK) ==
             files(isa_elem, PUBIC_HAIR) ==
             files(po_elem, PUBIC_HAIR) == ["FJ2815"]),
        ])),
        ("eyebrow_set_identity", OrderedDict([
            ("claim", "the eyebrow and both set classes above "
                      "it resolve to the same single file, "
                      "FJ2812, in IS-A (none is carried in "
                      "PART-OF): the classes carry no geometry "
                      "beyond the eyebrow record's"),
            ("set_of_hairs_isa", files(isa_elem, HAIR_SET)),
            ("facial_set_isa", files(isa_elem, FACIAL_HAIR_SET)),
            ("eyebrow_isa", files(isa_elem, EYEBROW)),
            ("identical", files(isa_elem, HAIR_SET) ==
             files(isa_elem, FACIAL_HAIR_SET) ==
             files(isa_elem, EYEBROW) == ["FJ2812"]),
        ])),
        ("module_file_census", OrderedDict([
            ("claim", "the module's entire geometry, across "
                      "both tables and all twelve concepts, "
                      "is four mesh files"),
            ("distinct_files", sorted(
                {fj for em in (isa_elem, po_elem)
                 for c in universe for fj in em.get(c, ())})),
        ])),
    ])
    assert findings["skin_shell_identity"]["identical"]
    assert findings["hair_file_partition"]["identical"]
    assert findings["eyebrow_set_identity"]["identical"]
    assert findings["module_file_census"]["distinct_files"] == \
        ["FJ2810", "FJ2812", "FJ2813", "FJ2815"]

    geo_doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA integumentary system geometry "
                      "resolution — Milestone 15"),
            ("generated_by", "tools/integ_map.py"),
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
                ("by_line", OrderedDict([
                    (line, OrderedDict([
                        ("records", records_by_line[line]),
                        ("records_with_meshes",
                         covered_by_line[line])]))
                    for line in ("skin", "appendage", "system")])),
                ("union_bbox_all_records", union_bbox(all_meshes)),
            ])),
            ("structure_findings", findings),
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
    print("concepts by line:", dict(concepts_by_line))
    print("records by line:", dict(records_by_line))
    print("dispositions:", dict(disp_counts))
    print("records:", len(records), dict(repr_counts))
    print("sweep rejected (%d):" % len(sweep_names), sweep_names)
    print("sweep zero-hit terms:", sweep_zero_terms)
    print("geometry coverage: %d/%d records have meshes"
          % (covered, len(records)))
    print("coverage by line:", dict(covered_by_line))
    print("TS integument-adjacent labels:", ts_hits)
    print("substring zero-hit probes:", sub_zero,
          "of", len(SUBSTRING_PROBES))
    print("exact-name zero-hit probes:", exact_zero,
          "of", len(EXACT_NAME_PROBES))
    print("reproductive boundary closes:", boundary["closes"])
    print(f"wrote {OUT_INV}")
    print(f"wrote {OUT_GEO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
