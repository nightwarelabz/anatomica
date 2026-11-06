#!/usr/bin/env python3
"""ANATOMICA Milestone 14 — reproductive system census + geometry
mapping.

Censuses the reproductive-system concepts of BodyParts3D 4.0 /
FMA exactly as they are represented in the release tables
(data/sources/bodyparts3d-4.0/), male and female lines
separately, and maps the derived records to BP3D meshes in the
manner of Milestones 2, 4, 5, 9, 10, 11, 12 and 13: exact
lookups only, compositions taken from the tables, vertex/face
counts measured by streaming the OBJ files.

HOW BP3D 4.0 REPRESENTS THE REPRODUCTIVE SYSTEM (established
by inspection of the tables, 2026-11-06; every claim is
re-derived by this script at run time):

  * The PART-OF table's own genital tree is vestigial: the
    subtree under FMA7160 "genital system" has exactly two
    members — the root and the prostate (FMA9600). No other
    reproductive organ is filed under the system the release
    itself names genital.
  * The male line lives in IS-A as three class lines with
    lateralised instances — testis (FMA7210, instances
    FMA7211/FMA7212), epididymis (FMA18255, FMA18256/FMA18257)
    and seminal vesicle (FMA19386, FMA19387/FMA19388) — plus
    IS-A leaves for the erectile tissues: corpus cavernosum of
    penis (FMA19618), corpus spongiosum of penis (FMA19617)
    and the glans penis (FMA18247), whose IS-A parent is its
    own zone concept, FMA20247 "zone of corpus spongiosum of
    penis". THE PENIS ITSELF HAS NO CONCEPT: no concept is
    named "penis" (exact-name probe-verified); the organ exists
    in the release only as its erectile parts and as the
    vessels the cardiovascular module carries (dorsal artery
    and dorsal veins of penis).
  * THE DUCT SYSTEM DOES NOT EXIST. The ductus (vas) deferens,
    the ejaculatory duct and the spermatic cord score zero
    name hits in both parts lists; the epididymis is the only
    duct the release carries, and the bulbourethral glands are
    absent too. The male pathway is therefore discontinuous in
    the data at exactly the segment a vasectomy interrupts.
  * THE FEMALE LINE IS ESSENTIALLY ABSENT — the milestone's
    headline. "ovary", "ovarian", "uterus", "uterine",
    "vagina", "vulva", "clitoris", "labia", "hymen",
    "endometrium", "myometrium" and "fallopian" all score
    zero hits in both parts lists (the zero-hit sweep Milestone
    13 recorded for the ovary at the endocrine boundary is
    re-derived here and extends to the whole tract). The ONE
    female-named concept in either table is the mons pubis
    (FMA20218), carried in PART-OF only and filed by the
    release under the pelvis (FMA9578) — not under any genital
    root, there being no female genital tree to file it under.
    Against the male line's fourteen concepts, the female line
    has one.
  * The perineum is shared ground: PART-OF roots it under the
    trunk (FMA7181) with one child, the anal part of perineum
    (FMA20347), and IS-A carries a perineal muscle line
    (FMA9623, FMA19728, FMA21930) that belongs to the muscular
    module — the external anal sphincter (FMA21930) is the
    muscular module's record muscle.external-anal-sphincter
    and is censused here as a cross-reference, never
    duplicated. The perineum and its anal part carry the SAME
    four mesh files in PART-OF — {FJ1450, FJ1450M, FJ2543,
    FJ2548} — which are exactly the files the muscular
    module's sphincter record carries (in both tables). The
    release draws the perineum as its sphincter and nothing
    else (identity gated by tools/repro_check.py).
  * The urethra (FMA19667) is NOT in this universe: the
    urinary module (Milestone 12) holds it as its single
    unsexed record, and this module cross-references it rather
    than duplicating it — the male pathway record states the
    relationship (the urethra is the shared terminal segment
    of both systems), and the checker gates the pointer.
  * TotalSegmentator v1 has NO reproductive label at all:
    none of the 104 labels names a reproductive structure (no
    prostate, no seminal_vesicle, nothing) — the overlap is
    exactly zero, censused from the label index.
  * The Milestone 13 boundary closes by construction: the
    endocrine module censused exactly the testis line
    {FMA7210, FMA7211, FMA7212} as its reproductive
    cross-reference; this module's testis census is that same
    set, the class carried on the two instance records
    (equality gated by the checker against the endocrine
    inventory file itself).

COUNTING CONVENTION (what counts as one reproductive-system
record):
  * One record per lateralised instance (right/left testis,
    epididymis, seminal vesicle), keyed on its instance
    concept with the side-stripped class concept carried as
    class_concept_id (the Milestone 11/12/13 instance pattern).
  * One record for the prostate, keyed on its both-table
    concept; one record each for the corpus cavernosum, the
    corpus spongiosum and the glans penis, keyed on their IS-A
    concepts (the glans carries its zone concept as
    class_concept_id); one record for the mons pubis, keyed on
    its PART-OF-only concept; one record for the perineum and
    one for its anal part, keyed on their PART-OF concepts.
  * The genital system root (FMA7160) is a grouping class:
    censused, never a record. The perineal muscle concepts are
    cross-references to the muscular module: censused, never
    records here. Sex line is carried per concept and per
    record: male (the testis, epididymis, seminal-vesicle,
    prostate, erectile and glans concepts), female (the mons
    pubis alone) and shared (the genital root and the perineal
    concepts).

Outputs:
  data/reproductive/reproductive-inventory.json  census
  data/reproductive/reproductive-geometry.json   per-record
                                                 meshes

Stdlib only. Run: python3 tools/repro_map.py
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
OUT_INV = os.path.join(ROOT, "data", "reproductive",
                       "reproductive-inventory.json")
OUT_GEO = os.path.join(ROOT, "data", "reproductive",
                       "reproductive-geometry.json")
ENDO_INV = os.path.join(ROOT, "data", "endocrine",
                        "endocrine-inventory.json")
MUSC_GEO = os.path.join(ROOT, "data", "muscular",
                        "muscle-geometry.json")
TS_LABELS = os.path.join(ROOT, "data", "sources",
                         "totalsegmentator-1.0", "labels.json")

TESTIS_ISA_ROOT = "FMA7210"         # testis (IS-A line)
EPIDIDYMIS_ISA_ROOT = "FMA18255"    # epididymis (IS-A line)
SV_ISA_ROOT = "FMA19386"            # seminal vesicle (IS-A line)
PROSTATE = "FMA9600"                # prostate (both tables)
CAVERNOSUM = "FMA19618"             # corpus cavernosum of penis
SPONGIOSUM = "FMA19617"             # corpus spongiosum of penis
GLANS_ZONE_ROOT = "FMA20247"        # zone of corpus spongiosum
GLANS = "FMA18247"                  # glans penis
PERINEAL_MUSCLE_ROOT = "FMA9623"    # perineal muscle (IS-A)
GENITAL_PO_ROOT = "FMA7160"         # genital system (PART-OF)
PERINEUM_PO_ROOT = "FMA9579"        # perineum (PART-OF)
MONS_PUBIS = "FMA20218"             # mons pubis (PART-OF only)
EAS = "FMA21930"                    # external anal sphincter

SEX_BY_CONCEPT = {
    "FMA7210": "male", "FMA7211": "male", "FMA7212": "male",
    "FMA18255": "male", "FMA18256": "male", "FMA18257": "male",
    "FMA19386": "male", "FMA19387": "male", "FMA19388": "male",
    "FMA9600": "male", "FMA19618": "male", "FMA19617": "male",
    "FMA20247": "male", "FMA18247": "male",
    "FMA20218": "female",
    "FMA7160": "shared", "FMA9579": "shared", "FMA20347": "shared",
    "FMA9623": "shared", "FMA19728": "shared", "FMA21930": "shared",
}

# lateralised instance records: instance concept -> (prefix,
# class concept)
INSTANCES = {
    "FMA7211": ("testis", "FMA7210"),            # right testis
    "FMA7212": ("testis", "FMA7210"),            # left testis
    "FMA18256": ("epididymis", "FMA18255"),      # right epididymis
    "FMA18257": ("epididymis", "FMA18255"),      # left epididymis
    "FMA19387": ("seminal-vesicle", "FMA19386"),  # right SV
    "FMA19388": ("seminal-vesicle", "FMA19386"),  # left SV
}
# un-sided records keyed on their concepts
PROSTATE_RECORD = {PROSTATE: "prostate"}
ISA_LEAF_RECORDS = {
    CAVERNOSUM: ("corpus-cavernosum-of-penis", CAVERNOSUM),
    SPONGIOSUM: ("corpus-spongiosum-of-penis", SPONGIOSUM),
    GLANS: ("glans-penis", GLANS_ZONE_ROOT),
}
PARTOF_RECORDS = {
    "FMA9579": ("perineum", "organ"),
    "FMA20347": ("perineum.anal-part-of-perineum",
                 "partof-concept"),
    MONS_PUBIS: ("mons-pubis", "organ"),
}
GROUPING_IDS = {GENITAL_PO_ROOT}
XREF_IDS = {
    "FMA9623": "muscular",        # perineal muscle (class)
    "FMA19728": "muscular",       # superficial perineal muscle
    EAS: "muscular",              # external anal sphincter
}

RECORD_NOTES = {
    "testis": "lateralised instance; the side-stripped class "
              "concept is carried as class_concept_id. "
              "Milestone 13 censused this line as the endocrine "
              "module's reproductive cross-reference; these "
              "records close that boundary",
    "epididymis": "lateralised instance; the side-stripped "
                  "class concept is carried as class_concept_id",
    "seminal-vesicle": "lateralised instance; the side-stripped "
                       "class concept is carried as "
                       "class_concept_id",
    "prostate": "the only member the release files under its "
                "own genital system in PART-OF, and a singleton "
                "under 'organ with cavitated organ parts' in "
                "IS-A; keyed on the both-table concept",
    "corpus-cavernosum-of-penis":
                "IS-A leaf. The penis itself has no concept in "
                "the release (exact-name probe-verified); the "
                "organ exists in the data only as its erectile "
                "parts here and its vessels in the cardiovascular "
                "module",
    "corpus-spongiosum-of-penis":
                "IS-A leaf; see corpus-cavernosum-of-penis",
    "glans-penis": "IS-A child of FMA20247 'zone of corpus "
                   "spongiosum of penis', carried as "
                   "class_concept_id; the zone and the glans "
                   "resolve to the same single mesh file "
                   "(FJ3134, IS-A table — neither concept is "
                   "carried in PART-OF), so the class carries no "
                   "geometry beyond this record's",
    "perineum": "PART-OF organ record: the release roots the "
                "perineum under the trunk. It carries the same "
                "four PART-OF mesh files as its anal part — "
                "exactly the perineal-muscle file set the "
                "muscular module carries for the external anal "
                "sphincter — so the release draws the perineum "
                "as its sphincter and nothing else (identity "
                "gated by the checker)",
    "perineum.anal-part-of-perineum":
                "PART-OF child of the perineum; the release "
                "gives it the same mesh files as its parent",
    "mons-pubis": "the only female-named concept in either "
                  "parts list; the release files it in PART-OF "
                  "under the pelvis, not under any genital root "
                  "— there is no female genital tree in the "
                  "release to file it under",
}

SWEEP_TERMS = ("genital", "testis", "testicle", "epididym",
               "seminal", "prostate", "penis", "penile", "uterus",
               "uterine", "vagina", "vulva", "ovary", "ovarian",
               "cervix", "perineum", "perineal", "scrotum",
               "clitoris", "labia", "labium", "mons pubis",
               "spermatic", "ductus deferens", "vas deferens",
               "ejaculat", "bulbourethral", "hymen", "glans",
               "cavernosum", "spongiosum", "prepuce", "dartos",
               "fornix", "gonad", "urethra")
SWEEP_WHY = {
    "fornix of forebrain": "nervous module: a cerebral fornix, "
                           "not a vaginal fornix — the vaginal "
                           "fornix has no concept in the release",
    "commissure of fornix of forebrain": "nervous module (see "
                                         "fornix of forebrain)",
    "fornix of neuraxis": "nervous module (see fornix of "
                          "forebrain)",
    "left fornix of forebrain": "nervous module (see fornix of "
                                "forebrain)",
    "right fornix of forebrain": "nervous module (see fornix of "
                                 "forebrain)",
    "dorsal artery of penis": "cardiovascular module class "
                              "concept, carried there as "
                              "artery.right-dorsal-artery-of-penis "
                              "and "
                              "artery.left-dorsal-artery-of-penis",
    "right dorsal artery of penis": "cardiovascular module "
                                    "record "
                                    "artery.right-dorsal-artery-"
                                    "of-penis",
    "left dorsal artery of penis": "cardiovascular module record "
                                   "artery.left-dorsal-artery-"
                                   "of-penis",
    "deep dorsal vein of penis": "cardiovascular module record "
                                 "vein.deep-dorsal-vein-of-penis",
    "superficial dorsal vein of penis": "cardiovascular module "
                                        "class concept, carried "
                                        "there as the right and "
                                        "left superficial dorsal "
                                        "vein records",
    "right superficial dorsal vein of penis":
        "cardiovascular module record "
        "vein.right-superficial-dorsal-vein-of-penis",
    "left superficial dorsal vein of penis":
        "cardiovascular module record "
        "vein.left-superficial-dorsal-vein-of-penis",
    "urethra": "urinary module record 'urethra' (FMA19667): the "
               "release's single unsexed urethra concept, held "
               "by Milestone 12; cross-referenced by this "
               "module's male pathway record, never duplicated",
}

# substring gap probes, per sex line; "controls" are terms whose
# concepts the release DOES carry, interleaved to prove the
# probe instrument reads the tables
SUBSTRING_PROBES = OrderedDict([
    ("male", [
        # the duct system — wholly absent
        "ductus deferens", "vas deferens", "spermatic",
        "ejaculat", "ampulla of ductus deferens",
        # the scrotum and the testis coverings/interior — absent
        "scrotum", "tunica", "dartos", "cremaster",
        "seminiferous", "rete testis", "testicle",
        # the remaining accessory gland — absent
        "bulbourethral", "cowper",
        # penile skin structures — absent
        "prepuce", "foreskin",
        # the gonad word itself — the release says testis/ovary
        # only, and only the testis exists
        "gonad",
        # controls (present)
        "testis", "epididymis", "prostate", "seminal vesicle",
    ]),
    ("female", [
        # the gonad and its structures — wholly absent
        "ovary", "ovarian", "corpus luteum", "oocyte",
        "mesovarium",
        # the tract — wholly absent
        "uterus", "uterine", "fallopian", "fimbria", "cervix",
        "vagina", "vaginal",
        # the uterine wall — wholly absent
        "endometrium", "myometrium", "perimetrium",
        # the ligaments — wholly absent
        "broad ligament", "mesosalpinx", "mesometrium",
        # the external genitalia — absent except the mons pubis
        "vulva", "clitoris", "labia", "labium", "hymen",
        "bartholin", "skene",
        # controls (present)
        "mons pubis",
    ]),
    ("shared", [
        # perineal structures the clinical layer names — the
        # release carries none of them as concepts
        "perineal body", "perineal membrane", "ischioanal",
        "perineal pouch", "sphincter urethrae",
        # controls (present)
        "perineum", "genital system",
    ]),
])
# exact-name probes: concepts whose exact English name would be
# the organ itself
EXACT_NAME_PROBES = OrderedDict([
    ("male", ["penis", "ductus deferens", "ejaculatory duct",
              "bulbourethral gland", "spermatic cord",
              "tunica albuginea", "scrotum"]),
    ("female", ["ovary", "uterus", "vagina", "clitoris",
                "uterine tube", "fallopian tube", "cervix",
                "cervix of uterus", "vulva", "labium majus",
                "labium minus", "hymen", "endometrium",
                "myometrium", "broad ligament",
                "broad ligament of uterus",
                "round ligament of uterus", "mesovarium",
                "ovarian follicle", "corpus luteum",
                "greater vestibular gland",
                "vestibule of vagina"]),
    ("shared", ["perineal body", "perineal membrane",
                "urogenital triangle", "anal triangle"]),
])
TS_TERMS = ("prostate", "seminal", "testis", "ovary", "uterus",
            "uterine", "vagina", "penis", "scrotum", "spermatic",
            "epididym", "perine", "cervix", "vulva", "gonad")


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
    testis_isa = descendants(TESTIS_ISA_ROOT, children)
    epididymis_isa = descendants(EPIDIDYMIS_ISA_ROOT, children)
    sv_isa = descendants(SV_ISA_ROOT, children)
    glans_isa = descendants(GLANS_ZONE_ROOT, children)
    perineal_muscle_isa = descendants(PERINEAL_MUSCLE_ROOT,
                                      children)
    genital_po = descendants(GENITAL_PO_ROOT, po_children)
    perineum_po = descendants(PERINEUM_PO_ROOT, po_children)

    isa_sets = OrderedDict([
        ("testis-isa", testis_isa),
        ("epididymis-isa", epididymis_isa),
        ("seminal-vesicle-isa", sv_isa),
        ("prostate-isa", {PROSTATE}),
        ("corpus-cavernosum-isa", {CAVERNOSUM}),
        ("corpus-spongiosum-isa", {SPONGIOSUM}),
        ("glans-zone-isa", glans_isa),
        ("perineal-muscle-isa", perineal_muscle_isa),
    ])
    po_sets = OrderedDict([
        ("genital-system-partof", genital_po),
        ("perineum-partof", perineum_po),
        ("mons-pubis-partof", {MONS_PUBIS}),
    ])
    isa_universe = set()
    for s in isa_sets.values():
        isa_universe |= s
    po_universe = set()
    for s in po_sets.values():
        po_universe |= s
    universe = isa_universe | po_universe
    assert universe == set(SEX_BY_CONCEPT), \
        f"universe/SEX_BY_CONCEPT mismatch: " \
        f"{sorted(universe ^ set(SEX_BY_CONCEPT))}"

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

    def cross_ref(cid):
        return XREF_IDS.get(cid)

    # cross-check sweep: reproductive terms outside the universe
    sweep_rejected = {}
    for tab, tname in ((isa, "isa"), (po, "partof")):
        for cid, v in tab.items():
            if cid in universe:
                continue
            n = v["name"]
            if any(t in n for t in SWEEP_TERMS):
                sweep_rejected.setdefault(n, tname)
    unadjudicated = [n for n in sweep_rejected if n not in SWEEP_WHY]
    assert not unadjudicated, \
        f"sweep names without adjudication: {unadjudicated}"
    sweep_names = sorted(sweep_rejected)

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
            ("sex_line", SEX_BY_CONCEPT[concept_ids[0]]),
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
                   "whole-concept", [cid], class_id,
                   subtree_of[cid], note=RECORD_NOTES[prefix])
        instance_made.append(nm)

    # (2) the prostate — the genital tree's only member
    for cid, rid in sorted(PROSTATE_RECORD.items(),
                           key=lambda kv: kv[1]):
        assert cid in isa and cid in po
        assert isa[cid]["name"] == po[cid]["name"]
        add_record(rid, isa[cid]["name"], "un-sided",
                   "whole-concept", [cid], cid, subtree_of[cid],
                   note=RECORD_NOTES[rid])
    # (3) IS-A leaf records (erectile tissues and the glans)
    for cid, (rid, class_id) in sorted(ISA_LEAF_RECORDS.items(),
                                       key=lambda kv: kv[1][0]):
        assert cid in isa
        add_record(rid, isa[cid]["name"], "un-sided",
                   "whole-concept", [cid], class_id,
                   subtree_of[cid], note=RECORD_NOTES[rid])
    # (4) PART-OF records (perineum, its anal part, mons pubis)
    for cid, (rid, representation) in sorted(
            PARTOF_RECORDS.items(), key=lambda kv: kv[1][0]):
        assert cid in po
        add_record(rid, po[cid]["name"], "un-sided", representation,
                   [cid], cid, subtree_of[cid],
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
    records_by_sex = Counter(r["sex_line"] for r in records)
    concepts_by_sex = Counter(SEX_BY_CONCEPT[c] for c in universe)

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
            ("subtrees", sorted(t for t, s in
                                list(isa_sets.items()) +
                                list(po_sets.items())
                                if cid in s)),
            ("sex_line", SEX_BY_CONCEPT[cid]),
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

    sub_block = OrderedDict()
    sub_zero = {}
    for line, probes in SUBSTRING_PROBES.items():
        detail = []
        for probe in probes:
            hits = {fn: texts[fn].count(probe) for fn in table_files}
            detail.append(OrderedDict([
                ("probe", probe),
                ("total_hits", sum(hits.values())),
                ("exact_concept_exists", probe in all_names),
                ("hits_by_table", hits)]))
        sub_block[line] = OrderedDict([
            ("absent", [a["probe"] for a in detail
                        if a["total_hits"] == 0]),
            ("present", [a["probe"] for a in detail
                         if a["total_hits"] > 0]),
            ("detail", detail)])
        sub_zero[line] = sum(1 for a in detail
                             if a["total_hits"] == 0)
    exact_block = OrderedDict()
    exact_zero = {}
    isa_names = {v["name"] for v in isa.values()}
    po_names = {v["name"] for v in po.values()}
    for line, probes in EXACT_NAME_PROBES.items():
        detail = []
        for probe in probes:
            detail.append(OrderedDict([
                ("probe", probe),
                ("concept_exists", probe in all_names),
                ("in_isa", probe in isa_names),
                ("in_partof", probe in po_names)]))
        exact_block[line] = OrderedDict([
            ("absent", [a["probe"] for a in detail
                        if not a["concept_exists"]]),
            ("present", [a["probe"] for a in detail
                         if a["concept_exists"]]),
            ("detail", detail)])
        exact_zero[line] = sum(1 for a in detail
                               if not a["concept_exists"])

    # ---- TotalSegmentator overlap (derived from the label index) -----
    ts = json.load(open(TS_LABELS))
    ts_counts = ts["labels"]
    ts_hits = sorted(l for l in ts_counts
                     if any(t in l for t in TS_TERMS))

    # ---- Milestone 13 boundary (endocrine -> reproductive) -----------
    endo = json.load(open(ENDO_INV))
    endo_xref = set(endo["meta"]["concept_universe"]
                    ["disposition_concepts"]
                    ["cross-reference:reproductive"])
    boundary = OrderedDict([
        ("source", "data/endocrine/endocrine-inventory.json "
                   "(Milestone 13)"),
        ("endocrine_cross_reference_reproductive",
         sorted(endo_xref)),
        ("this_module_testis_census", sorted(testis_isa)),
        ("equal", endo_xref == testis_isa),
    ])
    assert boundary["equal"], "endocrine boundary does not close"

    xref_counts = Counter(cross_ref(c) for c in universe
                          if cross_ref(c))
    inv_doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA reproductive system inventory — "
                      "Milestone 14"),
            ("generated_by", "tools/repro_map.py"),
            ("source_tables", "data/sources/bodyparts3d-4.0/ (BP3D "
                              "4.0 / FMA concept ids and names as "
                              "released)"),
            ("counting_convention",
             "One record per lateralised instance (right/left "
             "testis, epididymis, seminal vesicle), keyed on its "
             "instance concept with the side-stripped class "
             "concept carried as class_concept_id; one record "
             "for the prostate, keyed on its both-table concept; "
             "one record each for the corpus cavernosum, the "
             "corpus spongiosum and the glans penis, keyed on "
             "their IS-A concepts (the glans carries its zone "
             "concept as class_concept_id); one record for the "
             "mons pubis, keyed on its PART-OF-only concept; one "
             "record for the perineum and one for its anal part, "
             "keyed on their PART-OF concepts. The genital "
             "system root is a grouping class, censused but not "
             "a record. The perineal muscle concepts are "
             "cross-references to the muscular module, censused "
             "but never records here. Sex line is censused per "
             "concept and per record: the female line of the "
             "release is exactly one concept (the mons pubis) "
             "against fourteen male concepts — every internal "
             "female organ is absent from the release entirely "
             "and exists in this module only as sourced clinical "
             "records with the absence recorded (the Milestone 9 "
             "pattern). The urethra is not in this universe: it "
             "is the urinary module's single unsexed record "
             "(Milestone 12), cross-referenced, never "
             "duplicated."),
            ("concept_universe", OrderedDict([
                ("total", len(universe)),
                ("isa_total", len(isa_universe)),
                ("partof_total", len(po_universe)),
                ("in_both_tables", len(isa_universe & po_universe)),
                ("isa_sets", {k: len(v) for k, v in isa_sets.items()}),
                ("partof_sets", {k: len(v)
                                 for k, v in po_sets.items()}),
                ("by_sex_line", dict(concepts_by_sex)),
                ("cross_references", dict(xref_counts)),
                ("dispositions", dict(disp_counts)),
                ("disposition_concepts",
                 {k: v for k, v in sorted(disp_lists.items())}),
                ("sweep_rejected_names", sweep_names),
                ("sweep_adjudications",
                 {n: SWEEP_WHY[n] for n in sweep_names}),
            ])),
            ("record_count", len(records)),
            ("record_representations", dict(repr_counts)),
            ("records_by_subtree",
             dict(Counter(r["subtree"] for r in records))),
            ("records_by_sex_line", dict(records_by_sex)),
            ("instance_records", instance_made),
            ("boundary_closures", OrderedDict([
                ("milestone_13_endocrine", boundary),
            ])),
            ("totalsegmentator_overlap", OrderedDict([
                ("note", "of the 104 TotalSegmentator v1 labels "
                         "(Milestone 3 census), NONE names a "
                         "reproductive structure — there is no "
                         "prostate, seminal_vesicle, testis, "
                         "ovary, uterus or any other reproductive "
                         "label in the index; the overlap of this "
                         "module with TS v1 is exactly zero, "
                         "derived here from the label index by "
                         "term match and re-derived by the "
                         "checker"),
                ("labels", []),
                ("labels_without_records", []),
                ("labels_matched_by_terms", ts_hits),
            ])),
            ("absences", OrderedDict([
                ("note", "probe-based gap analysis, per sex "
                         "line: each substring probe was counted "
                         "over all six BP3D 4.0 release tables "
                         "(zero hits = the name does not occur in "
                         "the release); each exact-name probe was "
                         "tested for a concept of exactly that "
                         "name in either parts list. Present "
                         "controls are interleaved in each line to "
                         "prove the instrument reads the tables. "
                         "The asymmetry is the finding: the male "
                         "line's probes find the gonad, its duct's "
                         "first segment, two of three accessory "
                         "glands and the erectile tissues present "
                         "and the duct system absent; the female "
                         "line's probes find nothing but the "
                         "control — the entire internal female "
                         "tract is absent from the release"),
                ("substring_probes", sub_block),
                ("substring_zero_hit_counts", sub_zero),
                ("exact_name_probes", exact_block),
                ("exact_name_zero_hit_counts", exact_zero),
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
    covered_by_sex = Counter()
    all_meshes = []
    for rec in records:
        cids = rec["concept_ids"]
        isa_meshes = mesh_list("isa", isa_elem, ISA_DIR, cids)
        po_meshes = mesh_list("partof", po_elem, PO_DIR, cids)
        if isa_meshes or po_meshes:
            covered += 1
            covered_by_sex[rec["sex_line"]] += 1
        all_meshes += isa_meshes + po_meshes
        names = []
        for c in cids:
            names.append(isa[c]["name"] if c in isa else po[c]["name"])
        geo_records.append(OrderedDict([
            ("record_id", rec["record_id"]),
            ("name", rec["name"]),
            ("side", rec["side"]),
            ("representation", rec["representation"]),
            ("sex_line", rec["sex_line"]),
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

    # structural findings: the glans/zone shared file and the
    # perineum = perineal-muscle file identity
    glans_files = {t: sorted(isa_elem.get(GLANS, ())
                             if t == "isa" else
                             po_elem.get(GLANS, ()))
                   for t in ("isa", "partof")}
    zone_files = {t: sorted(isa_elem.get(GLANS_ZONE_ROOT, ())
                            if t == "isa" else
                            po_elem.get(GLANS_ZONE_ROOT, ()))
                  for t in ("isa", "partof")}
    perineum_files = {
        t: sorted((isa_elem if t == "isa" else po_elem)
                  .get(PERINEUM_PO_ROOT, set()) |
                  (isa_elem if t == "isa" else po_elem)
                  .get("FMA20347", set()))
        for t in ("isa", "partof")}
    anal_part_files = {
        t: sorted((isa_elem if t == "isa" else po_elem)
                  .get("FMA20347", set()))
        for t in ("isa", "partof")}
    musc = json.load(open(MUSC_GEO))
    eas_rec = [r for r in musc["records"]
               if r["record_id"] ==
               "muscle.external-anal-sphincter"][0]
    eas_files = {t: sorted(m["fj"] for m in eas_rec[t + "_meshes"])
                 for t in ("isa", "partof")}
    perineum_combined = sorted(set(perineum_files["isa"]) |
                               set(perineum_files["partof"]))
    eas_combined = sorted(set(eas_files["isa"]) |
                          set(eas_files["partof"]))
    findings = OrderedDict([
        ("glans_zone_shared_mesh", OrderedDict([
            ("glans_concept", GLANS),
            ("zone_concept", GLANS_ZONE_ROOT),
            ("glans_files", glans_files),
            ("zone_files", zone_files),
            ("identical", glans_files == zone_files),
        ])),
        ("perineum_mesh_identity", OrderedDict([
            ("perineum_concepts", [PERINEUM_PO_ROOT, "FMA20347"]),
            ("perineum_concept_files",
             {t: sorted((isa_elem if t == "isa" else po_elem)
                        .get(PERINEUM_PO_ROOT, set()))
              for t in ("isa", "partof")}),
            ("anal_part_files", anal_part_files),
            ("perineum_files", perineum_files),
            ("muscular_record", OrderedDict([
                ("record_id", "muscle.external-anal-sphincter"),
                ("concept_id", EAS),
                ("files", eas_files)])),
            ("combined_file_set", perineum_combined),
            ("identical_to_muscular_record",
             perineum_combined == eas_combined
             and anal_part_files["partof"] ==
             eas_files["partof"]),
        ])),
    ])
    assert findings["glans_zone_shared_mesh"]["identical"]
    assert findings["perineum_mesh_identity"][
        "identical_to_muscular_record"]

    geo_doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA reproductive system geometry "
                      "resolution — Milestone 14"),
            ("generated_by", "tools/repro_map.py"),
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
                ("by_sex_line", OrderedDict([
                    (line, OrderedDict([
                        ("records", records_by_sex[line]),
                        ("records_with_meshes",
                         covered_by_sex[line])]))
                    for line in ("male", "female", "shared")])),
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
    print("concepts by sex line:", dict(concepts_by_sex))
    print("records by sex line:", dict(records_by_sex))
    print("cross references:", dict(xref_counts))
    print("dispositions:", dict(disp_counts))
    print("records:", len(records), dict(repr_counts))
    print("instance records:", instance_made)
    print("sweep rejected (%d):" % len(sweep_names), sweep_names)
    print("geometry coverage: %d/%d records have meshes"
          % (covered, len(records)))
    print("coverage by sex line:", dict(covered_by_sex))
    print("TS reproductive labels:", ts_hits)
    print("substring zero-hit probes:", sub_zero)
    print("exact-name zero-hit probes:", exact_zero)
    print("endocrine boundary closes:", boundary["equal"])
    print(f"wrote {OUT_INV}")
    print(f"wrote {OUT_GEO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
