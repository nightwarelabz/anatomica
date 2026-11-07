#!/usr/bin/env python3
"""ANATOMICA Milestone 14 — independent checker for the
reproductive module.

Shares NO code with tools/repro_map.py or
tools/build_repro_records.py. Re-derives, from the six BP3D
4.0 release tables: (1) the concept universe per sex line (the
testis, epididymis and seminal-vesicle IS-A lines, the
prostate and erectile IS-A singletons, the glans-zone line,
the perineal-muscle IS-A line, the genital and perineum
PART-OF lines and the mons pubis), its records and
dispositions, the sweep adjudications and the per-line absence
probes; (2) the concept->mesh attribution (FJ numbers) and
every recorded vertex/face count and bounding box, by
re-reading the OBJ files, plus the two structural identities —
the glans and its zone concept resolving to the same mesh
file, and the perineum pair carrying exactly the muscular
module's external-anal-sphincter file set; (3) the
TotalSegmentator overlap, from the M3 label index (exactly
zero reproductive labels); (4) the Milestone 13 boundary
closure — the endocrine module's reproductive cross-reference
set must be exactly this module's testis census; (5) the
clinical tranche's citation/flag/tier discipline against this
checker's own core/soft field table, plus content gates: the
male pathway's station order, the female pathway's station
order, the male pathway's gland order, the urethra
cross-reference resolving to the urinary module's records
(and the urethra concept NOT claimed here), the ovary
record's absence discipline (no geometry, absence recorded,
and no ovarian vessel record existing in the cardiovascular
module for its supply to point at), the testis and penis
records' named cardiovascular records all resolving, the
prostate's zones in McNeal order, the perineum record's
sphincter pointer resolving to the muscular module, and the
female line's geometry census — exactly one female clinical
record links geometry, the mons pubis, at tier C.

Scope note (Milestone 37): the inventory now also carries 57
FMA 5.1.0 concept records (the female reproductive tract).
Milestone 38 adds 76 more (the male remainder; 133 FMA
records in the file altogether).
Every check below that speaks of the concept universe, the
records or the dispositions is scoped to the BP3D partition
(records without the fma-5.1.0 source tag), exactly as shipped
at Milestone 14. The geometry section's set-equality and
correspondence checks span all records; its re-measurement —
the concept->mesh derivation from the BP3D element tables —
is likewise scoped to the BP3D partition (the derivation is
that partition's defining rule, as in tools/uri_check.py),
and the FMA entries are asserted mesh-less in the same
section. Milestone 40: the section also carries the
collision gate — the element-table derivation over
FMA-partition concepts must be empty except for the
adjudicated deferent-duct pair (see MILESTONE-40.md).
The FMA records themselves are
gated by tools/fma_uri_repro_check.py, and their TA2
discipline by ta2_discipline.run_fma_inventory_multi at the
end of this file.

Run: python3 tools/repro_check.py   (exit 0 = all checks pass)
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
INV_P = os.path.join(ROOT, "data", "reproductive",
                     "reproductive-inventory.json")
GEO_P = os.path.join(ROOT, "data", "reproductive",
                     "reproductive-geometry.json")
CLIN_P = os.path.join(ROOT, "data", "reproductive",
                      "reproductive.json")
ENDO_INV = os.path.join(ROOT, "data", "endocrine",
                        "endocrine-inventory.json")
URI_INV = os.path.join(ROOT, "data", "urinary",
                       "urinary-inventory.json")
URI_CLIN = os.path.join(ROOT, "data", "urinary", "urinary.json")
CV_INV = os.path.join(ROOT, "data", "cardiovascular",
                      "cv-inventory.json")
MUSC_INV = os.path.join(ROOT, "data", "muscular",
                        "muscle-inventory.json")
MUSC_GEO = os.path.join(ROOT, "data", "muscular",
                        "muscle-geometry.json")
TS_LABELS = os.path.join(ROOT, "data", "sources",
                         "totalsegmentator-1.0", "labels.json")

TESTIS = "FMA7210"
EPIDIDYMIS = "FMA18255"
SV = "FMA19386"
PROSTATE = "FMA9600"
CAVERNOSUM = "FMA19618"
SPONGIOSUM = "FMA19617"
GLANS_ZONE = "FMA20247"
GLANS = "FMA18247"
PERINEAL_MUSCLE = "FMA9623"
GENITAL = "FMA7160"
PERINEUM = "FMA9579"
ANAL_PART = "FMA20347"
MONS = "FMA20218"
EAS = "FMA21930"
URETHRA = "FMA19667"
TESTIS_SET = {"FMA7210", "FMA7211", "FMA7212"}
EPIDIDYMIS_SET = {"FMA18255", "FMA18256", "FMA18257"}
SV_SET = {"FMA19386", "FMA19387", "FMA19388"}
GLANS_SET = {"FMA20247", "FMA18247"}
PERINEAL_MUSCLE_SET = {"FMA9623", "FMA19728", "FMA21930"}
GENITAL_SET = {"FMA7160", "FMA9600"}
PERINEUM_SET = {"FMA9579", "FMA20347", "FMA21930"}
CLASS_CARRIED = {"FMA7210", "FMA18255", "FMA19386", "FMA20247"}
XREF = {"FMA9623": "muscular", "FMA19728": "muscular",
        "FMA21930": "muscular"}
GROUPING = {"FMA7160"}
SEX = {}
for _c in TESTIS_SET | EPIDIDYMIS_SET | SV_SET | GLANS_SET | \
        {PROSTATE, CAVERNOSUM, SPONGIOSUM}:
    SEX[_c] = "male"
SEX[MONS] = "female"
for _c in GENITAL_SET | PERINEUM_SET | PERINEAL_MUSCLE_SET:
    SEX.setdefault(_c, "shared")
SEX[PROSTATE] = "male"
SWEEP_TERMS = ("genital", "testis", "testicle", "epididym",
               "seminal", "prostate", "penis", "penile", "uterus",
               "uterine", "vagina", "vulva", "ovary", "ovarian",
               "cervix", "perineum", "perineal", "scrotum",
               "clitoris", "labia", "labium", "mons pubis",
               "spermatic", "ductus deferens", "vas deferens",
               "ejaculat", "bulbourethral", "hymen", "glans",
               "cavernosum", "spongiosum", "prepuce", "dartos",
               "fornix", "gonad", "urethra")
TS_TERMS = ("prostate", "seminal", "testis", "ovary", "uterus",
            "uterine", "vagina", "penis", "scrotum", "spermatic",
            "epididym", "perine", "cervix", "vulva", "gonad")
PERINEAL_FILES = {"FJ1450", "FJ1450M", "FJ2543", "FJ2548"}

CORE = {
    "pathway.male-reproductive-pathway":
        ["description", "stations", "urethra_relationship"],
    "organ.testis": ["description", "parts", "function"],
    "structure.epididymis": ["description", "parts", "function"],
    "duct.ductus-deferens": ["description", "course", "function"],
    "gland.seminal-vesicles": ["description", "function"],
    "gland.prostate": ["description", "parts", "function"],
    "gland.bulbourethral-glands": ["description", "function"],
    "organ.penis": ["description", "parts", "function"],
    "pathway.female-reproductive-pathway":
        ["description", "stations", "function"],
    "organ.ovary": ["description", "parts", "function"],
    "duct.uterine-tube": ["description", "parts", "function"],
    "organ.uterus": ["description", "parts", "function"],
    "organ.vagina": ["description", "parts", "function"],
    "structure.vulva": ["description", "parts", "function"],
    "structure.mons-pubis": ["description", "parts", "function"],
    "region.perineum": ["description", "boundaries", "parts",
                        "function"],
}
SOFT = {
    "pathway.male-reproductive-pathway":
        ["glands_in_order", "semen_composition", "clinical_note"],
    "organ.testis": ["dimension", "arterial_supply",
                     "venous_drainage", "lymphatic_drainage",
                     "innervation", "relations"],
    "structure.epididymis": ["dimension", "relations",
                             "arterial_supply"],
    "duct.ductus-deferens": ["parts", "clinical_note"],
    "gland.seminal-vesicles": ["relations", "arterial_supply"],
    "gland.prostate": ["relations", "arterial_supply",
                       "venous_drainage", "innervation",
                       "lymphatic_drainage"],
    "gland.bulbourethral-glands": ["position"],
    "organ.penis": ["arterial_supply", "venous_drainage",
                    "innervation"],
    "pathway.female-reproductive-pathway": ["dataset_note"],
    "organ.ovary": ["dimension", "ligaments", "arterial_supply",
                    "venous_drainage", "lymphatic_drainage",
                    "innervation"],
    "duct.uterine-tube": ["regional_subdivisions"],
    "organ.uterus": ["wall_layers", "dimension", "position",
                     "ligaments", "arterial_supply",
                     "venous_drainage", "lymphatic_drainage",
                     "innervation"],
    "organ.vagina": ["dimension", "arterial_supply",
                     "innervation"],
    "structure.vulva": ["arterial_supply"],
    "structure.mons-pubis": ["relations"],
    "region.perineum": ["dataset_note"],
}
RECORD_SEX = {
    "pathway.male-reproductive-pathway": "male",
    "organ.testis": "male", "structure.epididymis": "male",
    "duct.ductus-deferens": "male",
    "gland.seminal-vesicles": "male", "gland.prostate": "male",
    "gland.bulbourethral-glands": "male", "organ.penis": "male",
    "pathway.female-reproductive-pathway": "female",
    "organ.ovary": "female", "duct.uterine-tube": "female",
    "organ.uterus": "female", "organ.vagina": "female",
    "structure.vulva": "female", "structure.mons-pubis": "female",
    "region.perineum": "shared",
}
BASE_KEYS = {"id", "name", "type", "group", "sex_line",
             "ta_name", "sources", "verify", "note",
             "geometry_record_ids", "sourcing_tier"}
ABSENCE_MARK = "no BP3D 4.0 concept exists"
PATHWAY_MARK = "the pathway record links no geometry itself"

checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    return ok


def read_tsv(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        rows = [ln.rstrip("\n").split("\t") for ln in f if ln.strip()]
    return rows[1:]


def descendants(root, kids):
    seen, stack = set(), [root]
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        stack.extend(kids.get(c, []))
    return seen


def measure(path):
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
                    mn[i] = min(mn[i], x)
                    mx[i] = max(mx[i], x)
            elif line[:2] == b"f ":
                f += 1
    return v, f, {"min": mn, "max": mx}


def main():
    isa_rows = read_tsv(os.path.join(SRC, "isa_parts_list_e.txt"))
    po_rows = read_tsv(os.path.join(SRC, "partof_parts_list_e.txt"))
    isa = {r[0]: {"repr": r[1], "name": r[2]} for r in isa_rows}
    po = {r[0]: {"repr": r[1], "name": r[2]} for r in po_rows}
    isa_elem, po_elem = {}, {}
    for r in read_tsv(os.path.join(SRC, "isa_element_parts.txt")):
        isa_elem.setdefault(r[0], set()).add(r[2])
    for r in read_tsv(os.path.join(SRC, "partof_element_parts.txt")):
        po_elem.setdefault(r[0], set()).add(r[2])
    isa_kids, isa_par = {}, {}
    for r in read_tsv(os.path.join(
            SRC, "isa_inclusion_relation_list.txt")):
        isa_kids.setdefault(r[0], []).append(r[2])
        isa_par[r[2]] = r[0]
    po_kids, po_par = {}, {}
    for r in read_tsv(os.path.join(
            SRC, "partof_inclusion_relation_list.txt")):
        po_kids.setdefault(r[0], []).append(r[2])
        po_par[r[2]] = r[0]

    inv = json.load(open(INV_P))
    geo = json.load(open(GEO_P))
    clin = json.load(open(CLIN_P))
    meta = inv["meta"]
    cu = meta["concept_universe"]

    # ---------- universe re-derivation ----------
    testis_isa = descendants(TESTIS, isa_kids)
    epididymis_isa = descendants(EPIDIDYMIS, isa_kids)
    sv_isa = descendants(SV, isa_kids)
    glans_isa = descendants(GLANS_ZONE, isa_kids)
    pm_isa = descendants(PERINEAL_MUSCLE, isa_kids)
    genital_po = descendants(GENITAL, po_kids)
    perineum_po = descendants(PERINEUM, po_kids)
    check("testis IS-A line is class + right + left instances",
          testis_isa == TESTIS_SET, f"{sorted(testis_isa)}")
    check("epididymis IS-A line is class + 2 instances",
          epididymis_isa == EPIDIDYMIS_SET)
    check("seminal vesicle IS-A line is class + 2 instances",
          sv_isa == SV_SET)
    check("glans-zone IS-A line is the zone + the glans, and the "
          "glans' IS-A parent is the zone",
          glans_isa == GLANS_SET and isa_par[GLANS] == GLANS_ZONE)
    check("perineal muscle IS-A line is class + superficial + "
          "external anal sphincter",
          pm_isa == PERINEAL_MUSCLE_SET)
    check("genital PART-OF line is exactly the root + prostate",
          genital_po == GENITAL_SET, f"{sorted(genital_po)}")
    check("perineum PART-OF line is perineum + anal part + "
          "external anal sphincter",
          perineum_po == PERINEUM_SET, f"{sorted(perineum_po)}")
    exp_isa = testis_isa | epididymis_isa | sv_isa | {PROSTATE} | \
        {CAVERNOSUM} | {SPONGIOSUM} | glans_isa | pm_isa
    exp_po = genital_po | perineum_po | {MONS}
    exp_universe = exp_isa | exp_po
    check("concept universe re-derived (21 concepts)",
          {c["fma_id"] for c in inv["concepts"]} == exp_universe
          and len(exp_universe) == 21,
          f"{len(exp_universe)} concepts")
    check("universe counts match meta",
          cu["total"] == len(exp_universe)
          and cu["isa_total"] == len(exp_isa)
          and cu["partof_total"] == len(exp_po)
          and cu["in_both_tables"] == len(exp_isa & exp_po))
    check("sex-line census re-derived: 14 male, 1 female, "
          "6 shared concepts",
          Counter(SEX[c] for c in exp_universe) ==
          Counter({"male": 14, "female": 1, "shared": 6})
          and cu["by_sex_line"] ==
          dict(Counter(SEX[c] for c in exp_universe)),
          f"{dict(Counter(SEX[c] for c in exp_universe))}")
    check("the female line of the release is exactly one "
          "concept — the mons pubis — and no concept name in "
          "either list contains 'ovary', 'uterus' or 'vagina'",
          {c for c in exp_universe if SEX[c] == "female"} ==
          {MONS}
          and not any(t in v["name"] for v in
                      list(isa.values()) + list(po.values())
                      for t in ("ovary", "uterus", "vagina")))
    check("no concept is named 'penis' (the organ exists only "
          "as its erectile parts)",
          "penis" not in {v["name"] for v in isa.values()} |
          {v["name"] for v in po.values()})
    isa_sets = {"testis-isa": testis_isa,
                "epididymis-isa": epididymis_isa,
                "seminal-vesicle-isa": sv_isa,
                "prostate-isa": {PROSTATE},
                "corpus-cavernosum-isa": {CAVERNOSUM},
                "corpus-spongiosum-isa": {SPONGIOSUM},
                "glans-zone-isa": glans_isa,
                "perineal-muscle-isa": pm_isa}
    po_sets = {"genital-system-partof": genital_po,
               "perineum-partof": perineum_po,
               "mons-pubis-partof": {MONS}}
    sub_expect = {}
    for tag, s in po_sets.items():
        for c in s:
            sub_expect.setdefault(c, tag)
    for tag, s in isa_sets.items():
        for c in s:
            sub_expect.setdefault(c, tag)
    bad = [c["fma_id"] for c in inv["concepts"]
           if c["subtree"] != sub_expect[c["fma_id"]]
           or c["sex_line"] != SEX[c["fma_id"]]
           or set(c["subtrees"]) !=
           {t for t, s in list(isa_sets.items()) +
            list(po_sets.items()) if c["fma_id"] in s}]
    check("concept subtree tags, sex lines and subtree sets "
          "match re-derived sets", not bad, f"bad={bad}")

    # ---------- records re-derivation ----------
    exp_records = {
        "testis.right-testis": ("right testis", "right",
                                "whole-concept", ["FMA7211"],
                                TESTIS, "testis-isa", "male"),
        "testis.left-testis": ("left testis", "left",
                               "whole-concept", ["FMA7212"],
                               TESTIS, "testis-isa", "male"),
        "epididymis.right-epididymis": (
            "right epididymis", "right", "whole-concept",
            ["FMA18256"], EPIDIDYMIS, "epididymis-isa", "male"),
        "epididymis.left-epididymis": (
            "left epididymis", "left", "whole-concept",
            ["FMA18257"], EPIDIDYMIS, "epididymis-isa", "male"),
        "seminal-vesicle.right-seminal-vesicle": (
            "right seminal vesicle", "right", "whole-concept",
            ["FMA19387"], SV, "seminal-vesicle-isa", "male"),
        "seminal-vesicle.left-seminal-vesicle": (
            "left seminal vesicle", "left", "whole-concept",
            ["FMA19388"], SV, "seminal-vesicle-isa", "male"),
        "prostate": ("prostate", "un-sided", "whole-concept",
                     [PROSTATE], PROSTATE,
                     "genital-system-partof", "male"),
        "corpus-cavernosum-of-penis": (
            "corpus cavernosum of penis", "un-sided",
            "whole-concept", [CAVERNOSUM], CAVERNOSUM,
            "corpus-cavernosum-isa", "male"),
        "corpus-spongiosum-of-penis": (
            "corpus spongiosum of penis", "un-sided",
            "whole-concept", [SPONGIOSUM], SPONGIOSUM,
            "corpus-spongiosum-isa", "male"),
        "glans-penis": ("glans penis", "un-sided",
                        "whole-concept", [GLANS], GLANS_ZONE,
                        "glans-zone-isa", "male"),
        "mons-pubis": ("mons pubis", "un-sided", "organ",
                       [MONS], MONS, "mons-pubis-partof",
                       "female"),
        "perineum": ("perineum", "un-sided", "organ",
                     [PERINEUM], PERINEUM, "perineum-partof",
                     "shared"),
        "perineum.anal-part-of-perineum": (
            "anal part of perineum", "un-sided", "partof-concept",
            [ANAL_PART], ANAL_PART, "perineum-partof", "shared"),
    }
    got_records = {r["record_id"]: r for r in inv["records"]
                   if r.get("source") != "fma-5.1.0"}
    check("record id set matches derivation (13 records)",
          set(got_records) == set(exp_records),
          f"{sorted(got_records)}")
    bad = []
    for rid, (nm, side, rep, cids, cc, sub, sex) in \
            exp_records.items():
        r = got_records.get(rid)
        if r is None:
            bad.append(rid)
            continue
        if (r["name"], r["side"], r["representation"],
                r["concept_ids"], r["class_concept_id"],
                r["subtree"], r["sex_line"]) != \
                (nm, side, rep, cids, cc, sub, sex):
            bad.append(rid)
    check("record fields match derivation", not bad, f"bad={bad}")
    check("meta record count, representations and sex-line "
          "counts match (totals over all records; the BP3D "
          "partition's counters equal the derivation)",
          meta["record_count"] == len(inv["records"])
          and meta["record_representations"] ==
          dict(Counter(r["representation"]
                       for r in inv["records"]))
          and meta["records_by_sex_line"] ==
          dict(Counter(r["sex_line"] for r in inv["records"]))
          and dict(Counter(r["representation"]
                           for r in got_records.values())) ==
          dict(Counter(v[2] for v in exp_records.values()))
          and dict(Counter(r["sex_line"]
                           for r in got_records.values())) ==
          dict(Counter(v[6] for v in exp_records.values())))

    # dispositions
    claimed = {}
    for rid, r in got_records.items():
        for c in r["concept_ids"]:
            claimed[c] = rid
    carried = {r["class_concept_id"] for r in got_records.values()
               if r["class_concept_id"]
               and r["class_concept_id"] not in claimed}

    def exp_disp(c):
        if c in claimed:
            return "record"
        if c in carried:
            return "class-carried"
        if c in XREF:
            return "cross-reference:" + XREF[c]
        if c in GROUPING:
            return "grouping-class"
        return "subtree-internal"
    bad = [c["fma_id"] for c in inv["concepts"]
           if c["disposition"] != exp_disp(c["fma_id"])
           or c["record_id"] != claimed.get(c["fma_id"])
           or c["cross_reference"] != XREF.get(c["fma_id"])]
    check("concept dispositions, record and cross-reference "
          "pointers match", not bad, f"bad={bad}")
    check("dispositions partition the universe (13 record, "
          "4 class-carried, 1 grouping, 3 muscular "
          "cross-references, 0 internal)",
          Counter(exp_disp(c) for c in exp_universe) ==
          Counter(c["disposition"] for c in inv["concepts"])
          and sum(cu["dispositions"].values()) == len(exp_universe)
          and carried == CLASS_CARRIED
          and {c for c in exp_universe
               if exp_disp(c) == "grouping-class"} == GROUPING
          and not any(exp_disp(c) == "subtree-internal"
                      for c in exp_universe))

    # concept-row consistency
    bad = []
    for c in inv["concepts"]:
        cid = c["fma_id"]
        tab = isa if c["table"] == "isa" else po
        par = isa_par if c["table"] == "isa" else po_par
        if tab[cid]["name"] != c["name"] or \
                tab[cid]["repr"] != c["representation_id"]:
            bad.append((cid, "name/repr"))
        if c["also_in_isa"] != (cid in isa) or \
                c["also_in_partof"] != (cid in po):
            bad.append((cid, "also_in"))
        if c["isa_mesh_files"] != len(isa_elem.get(cid, ())) or \
                c["partof_mesh_files"] != len(po_elem.get(cid, ())):
            bad.append((cid, "mesh counts"))
        pid = par.get(cid)
        if c["parent_id"] != pid or (pid is not None and
                                     c["parent_name"] !=
                                     tab[pid]["name"]):
            bad.append((cid, "parent"))
    check("concept rows consistent with the tables", not bad,
          f"bad={bad[:5]}")

    # ---------- Milestone 13 boundary closure ----------
    endo = json.load(open(ENDO_INV))
    endo_xref = set(endo["meta"]["concept_universe"]
                    ["disposition_concepts"]
                    ["cross-reference:reproductive"])
    check("M13 boundary closure: the endocrine module's "
          "reproductive cross-reference set is exactly this "
          "module's testis census (class + both instances)",
          endo_xref == testis_isa == TESTIS_SET
          and meta["boundary_closures"]
          ["milestone_13_endocrine"]["equal"] is True,
          f"endocrine={sorted(endo_xref)} testis="
          f"{sorted(testis_isa)}")
    check("the urethra is NOT in this module's universe "
          "(urinary module's record, cross-referenced only)",
          URETHRA not in exp_universe
          and not any(c["fma_id"] == URETHRA
                      for c in inv["concepts"]))

    # ---------- sweep re-derivation ----------
    exp_rej = set()
    for tab in (isa, po):
        for cid, v in tab.items():
            if cid not in exp_universe and \
                    any(t in v["name"] for t in SWEEP_TERMS):
                exp_rej.add(v["name"])
    check("sweep rejected names match re-derivation (13 names)",
          set(cu["sweep_rejected_names"]) == exp_rej
          and len(exp_rej) == 13, f"{sorted(exp_rej)}")
    check("every sweep name carries an adjudication, and the "
          "adjudications name the expected owners",
          set(cu["sweep_adjudications"]) == exp_rej
          and "nervous" in cu["sweep_adjudications"]
          ["fornix of forebrain"]
          and "cardiovascular" in cu["sweep_adjudications"]
          ["deep dorsal vein of penis"]
          and "urinary" in cu["sweep_adjudications"]["urethra"])
    check("the sweep's five fornix names are all cerebral — "
          "there is no vaginal fornix concept",
          {n for n in exp_rej if "fornix" in n} ==
          {"fornix of forebrain",
           "commissure of fornix of forebrain",
           "fornix of neuraxis", "left fornix of forebrain",
           "right fornix of forebrain"})

    # ---------- absence probes re-run ----------
    table_files = ["isa_parts_list_e.txt", "partof_parts_list_e.txt",
                   "isa_element_parts.txt",
                   "partof_element_parts.txt",
                   "isa_inclusion_relation_list.txt",
                   "partof_inclusion_relation_list.txt"]
    texts = {fn: open(os.path.join(SRC, fn), encoding="utf-8",
                      errors="replace").read().lower()
             for fn in table_files}
    all_names = {v["name"] for v in isa.values()} | \
        {v["name"] for v in po.values()}
    abs_meta = meta["absences"]
    bad = []
    zero_re = {}
    for line in ("male", "female", "shared"):
        blk = abs_meta["substring_probes"][line]
        detail = {a["probe"]: a for a in blk["detail"]}
        for probe, a in detail.items():
            hits = {fn: texts[fn].count(probe)
                    for fn in table_files}
            if a["hits_by_table"] != hits or \
                    a["total_hits"] != sum(hits.values()) or \
                    a["exact_concept_exists"] != (probe in all_names):
                bad.append((line, probe))
        zero_re[line] = sum(1 for a in detail.values()
                            if a["total_hits"] == 0)
        if blk["absent"] != [p for p, a in detail.items()
                             if a["total_hits"] == 0] or \
                blk["present"] != [p for p, a in detail.items()
                                   if a["total_hits"] > 0]:
            bad.append((line, "absent/present lists"))
    check("substring probe counts re-run identically, per line",
          not bad, f"bad={bad[:5]}")
    check("substring zero-hit counts per line match meta "
          "(male 17, female 25, shared 5)",
          zero_re == {"male": 17, "female": 25, "shared": 5}
          and abs_meta["substring_zero_hit_counts"] == zero_re,
          f"{zero_re}")
    det = {line: {a["probe"]: a for a in
                  abs_meta["substring_probes"][line]["detail"]}
           for line in abs_meta["substring_probes"]}
    check("headline absences are probe-verified zero, per line: "
          "the whole male duct system, and the entire female "
          "tract",
          all(det["male"][p]["total_hits"] == 0 for p in
              ("ductus deferens", "vas deferens", "spermatic",
               "ejaculat", "bulbourethral", "scrotum",
               "seminiferous", "tunica", "prepuce"))
          and all(det["female"][p]["total_hits"] == 0 for p in
                  ("ovary", "ovarian", "uterus", "uterine",
                   "vagina", "vaginal", "cervix", "vulva",
                   "clitoris", "labia", "hymen", "endometrium",
                   "myometrium", "fallopian", "fimbria"))
          and all(det["shared"][p]["total_hits"] == 0 for p in
                  ("perineal body", "perineal membrane",
                   "ischioanal")))
    check("probe controls are present, per line (the instrument "
          "reads the tables)",
          all(det["male"][p]["total_hits"] > 0 for p in
              ("testis", "epididymis", "prostate",
               "seminal vesicle"))
          and det["female"]["mons pubis"]["total_hits"] > 0
          and all(det["shared"][p]["total_hits"] > 0 for p in
                  ("perineum", "genital system")))
    bad = []
    exact_zero_re = {}
    for line in ("male", "female", "shared"):
        blk = abs_meta["exact_name_probes"][line]
        for a in blk["detail"]:
            if a["concept_exists"] != (a["probe"] in all_names) or \
                    a["in_isa"] != (a["probe"] in
                                    {v["name"] for v in
                                     isa.values()}) or \
                    a["in_partof"] != (a["probe"] in
                                       {v["name"] for v in
                                        po.values()}):
                bad.append((line, a["probe"]))
        exact_zero_re[line] = sum(1 for a in blk["detail"]
                                  if not a["concept_exists"])
    check("exact-name probes re-derived identically, per line",
          not bad, f"bad={bad[:5]}")
    check("exact-name zero-hit counts per line match meta "
          "(male 7/7, female 22/22, shared 4/4 — every probed "
          "organ name is absent)",
          exact_zero_re == {"male": 7, "female": 22, "shared": 4}
          and abs_meta["exact_name_zero_hit_counts"] ==
          exact_zero_re, f"{exact_zero_re}")

    # ---------- geometry re-measurement ----------
    inv_rec = {r["record_id"]: r for r in inv["records"]}
    geo_rec = {r["record_id"]: r for r in geo["records"]}
    check("geometry record set equals inventory record set",
          set(geo_rec) == set(inv_rec))
    bad, entries = [], 0
    tot = Counter()
    all_meshes = []
    fma_mesh_bad = []
    collisions = {}
    for rid, gr in geo_rec.items():
        if gr["concept_ids"] != inv_rec[rid]["concept_ids"] or \
                gr["sex_line"] != inv_rec[rid]["sex_line"]:
            bad.append((rid, "concept ids / sex line"))
        if inv_rec[rid].get("source") == "fma-5.1.0":
            # FMA partition: concept-only records (Milestones
            # 37/38). Their geometry entries are governed by
            # the mesh-less rule, not by the BP3D element-table
            # derivation — the derivation is the BP3D
            # partition's defining rule (cf. the partition
            # scoping of tools/uri_check.py). The derivation
            # over their concepts is still computed, to feed
            # the Milestone 40 collision gate below.
            tt = gr.get("totals") or {}
            if gr["isa_meshes"] or gr["partof_meshes"] or \
                    gr.get("bbox_isa") is not None or \
                    gr.get("bbox_partof") is not None or \
                    (tt.get("isa") or {}).get("files") or \
                    (tt.get("partof") or {}).get("files"):
                fma_mesh_bad.append(rid)
            deriv = {"isa": set(), "partof": set()}
            for tree, elem in (("isa", isa_elem),
                               ("partof", po_elem)):
                for c in gr["concept_ids"]:
                    deriv[tree] |= elem.get(c, set())
            if deriv["isa"] or deriv["partof"]:
                collisions[rid] = deriv
            continue
        for tree, key, elem, d in (
                ("isa", "isa_meshes", isa_elem, ISA_DIR),
                ("partof", "partof_meshes", po_elem, PO_DIR)):
            exp_fj = set()
            for c in gr["concept_ids"]:
                exp_fj |= elem.get(c, set())
            if {m["fj"] for m in gr[key]} != exp_fj:
                bad.append((rid, tree + " fj set"))
            tv = tf = 0
            for m in gr[key]:
                entries += 1
                all_meshes.append(m)
                v, f, bb = measure(os.path.join(ROOT, m["path"]))
                if (v, f) != (m["vertices"], m["faces"]) or \
                        bb != m["bbox"]:
                    bad.append((rid, m["fj"]))
                tv += v
                tf += f
            t = gr["totals"][tree]
            if (t["files"], t["vertices"], t["faces"]) != \
                    (len(gr[key]), tv, tf):
                bad.append((rid, tree + " totals"))
            tot[tree + "_v"] += tv
            tot[tree + "_f"] += tf
            bbk = "bbox_" + tree
            if gr[key]:
                mn = [min(m["bbox"]["min"][i] for m in gr[key])
                      for i in range(3)]
                mx = [max(m["bbox"]["max"][i] for m in gr[key])
                      for i in range(3)]
                if gr[bbk] != {"min": mn, "max": mx}:
                    bad.append((rid, bbk))
            elif gr[bbk] is not None:
                bad.append((rid, bbk + " not null"))
    check(f"all geometry entries re-measured ({entries} entries)",
          not bad, f"bad={bad[:6]}")
    # Milestone 40 adjudication: FMA19235/FMA19236 ARE carried
    # by BP3D 4.0 — under the FMA preferred name "deferent
    # duct", which Milestone 14's Latin-keyed probes and sweep
    # terms ("ductus deferens" / "vas deferens") never matched,
    # so the line was recorded absent and Milestone 38 intaken
    # the pair as concept-only FMA records. The records stay
    # concept-only — upgrading them to geometry-carrying
    # records is a geometry-intake decision (the Milestone 34
    # line), not a checker repair. The pair's claimable meshes
    # are pinned here so that any change to this collision
    # set — a newly BP3D-carried FMA concept, a changed file
    # set, or a deliberate re-filing of the pair — fails
    # loudly instead of drifting. See MILESTONE-40.md.
    ADJUDICATED_COLLISIONS = {
        "repro.left-deferent-duct":
            {"isa": {"FJ3135"}, "partof": set()},
        "repro.right-deferent-duct":
            {"isa": {"FJ3140"}, "partof": set()},
    }
    check("attribution consistency across all records "
          "(Milestone 40 gate): the FMA partition is "
          "mesh-less, and the BP3D element-table derivation "
          "over FMA-partition concepts is empty except the "
          "adjudicated deferent-duct pair (FJ3135 / FJ3140)",
          not fma_mesh_bad
          and collisions == ADJUDICATED_COLLISIONS,
          f"mesh_bad={fma_mesh_bad[:3]} "
          f"collisions={collisions}")
    cov = geo["meta"]["coverage"]
    check("geometry coverage meta matches (13/13; male 10/10, "
          "female 1/1, shared 2/2)",
          cov["records_with_meshes"] == 13
          and cov["by_sex_line"]["male"]["records_with_meshes"] == 10
          and cov["by_sex_line"]["female"]
          ["records_with_meshes"] == 1
          and cov["by_sex_line"]["shared"]
          ["records_with_meshes"] == 2)
    if all_meshes:
        mn = [min(m["bbox"]["min"][i] for m in all_meshes)
              for i in range(3)]
        mx = [max(m["bbox"]["max"][i] for m in all_meshes)
              for i in range(3)]
        check("union bbox over all records matches meta",
              cov["union_bbox_all_records"] ==
              {"min": mn, "max": mx})
    fj_owner = {}
    for rid, gr in geo_rec.items():
        for key in ("isa_meshes", "partof_meshes"):
            for m in gr[key]:
                fj_owner.setdefault((key, m["fj"]), set()).add(rid)
    shared_slots = {k: v for k, v in fj_owner.items() if len(v) > 1}
    check("FJ attribution: every mesh file belongs to exactly "
          "one record per table, except the four perineal files "
          "shared by the perineum and its anal part in PART-OF",
          set(shared_slots) ==
          {("partof_meshes", fj) for fj in PERINEAL_FILES}
          and all(v == {"perineum",
                        "perineum.anal-part-of-perineum"}
                  for v in shared_slots.values()),
          f"shared={shared_slots}")
    # structural identities, re-derived from the element tables
    glans_files = {t: (isa_elem if t == "isa" else po_elem)
                   .get(GLANS, set()) for t in ("isa", "partof")}
    zone_files = {t: (isa_elem if t == "isa" else po_elem)
                  .get(GLANS_ZONE, set()) for t in ("isa", "partof")}
    check("glans/zone identity re-derived: the glans and its "
          "zone concept resolve to the same single mesh file in "
          "the IS-A table (FJ3134; neither concept is carried "
          "in PART-OF)",
          glans_files == zone_files ==
          {"isa": {"FJ3134"}, "partof": set()})
    musc_geo = json.load(open(MUSC_GEO))
    eas_rec = [r for r in musc_geo["records"]
               if r["record_id"] ==
               "muscle.external-anal-sphincter"][0]
    eas_files = {t: {m["fj"] for m in eas_rec[t + "_meshes"]}
                 for t in ("isa", "partof")}
    check("perineum identity re-derived: perineum and anal part "
          "PART-OF files == the muscular module's external anal "
          "sphincter file set, in both of its tables",
          po_elem.get(PERINEUM, set()) == PERINEAL_FILES
          and po_elem.get(ANAL_PART, set()) == PERINEAL_FILES
          and eas_files == {"isa": PERINEAL_FILES,
                            "partof": PERINEAL_FILES})
    find = geo["meta"]["structure_findings"]
    check("geometry structure_findings match the re-derived "
          "identities",
          find["glans_zone_shared_mesh"]["identical"] is True
          and find["perineum_mesh_identity"]
          ["identical_to_muscular_record"] is True
          and set(find["perineum_mesh_identity"]
                  ["combined_file_set"]) == PERINEAL_FILES)

    # ---------- TotalSegmentator overlap ----------
    ts = json.load(open(TS_LABELS))
    ts_counts = ts["labels"]
    ts_hits = sorted(l for l in ts_counts
                     if any(t in l for t in TS_TERMS))
    check("TS v1 carries exactly zero reproductive labels "
          "(of its 104)",
          ts_hits == [] and len(ts_counts) == 104,
          f"hits={ts_hits} labels={len(ts_counts)}")
    check("inventory TS overlap matches (empty, with the census "
          "recorded)",
          meta["totalsegmentator_overlap"]["labels"] == []
          and meta["totalsegmentator_overlap"]
          ["labels_without_records"] == []
          and meta["totalsegmentator_overlap"]
          ["labels_matched_by_terms"] == [])

    # ---------- clinical tranche ----------
    recs = clin["records"]
    by_id = {r["id"]: r for r in recs}
    check("clinical record count and ids match this checker "
          "(16 records)",
          clin["meta"]["record_count"] == len(CORE) == 16
          and set(by_id) == set(CORE), f"{sorted(by_id)}")
    check("clinical meta sources are exactly S1-S10 + TA2 (M23)",
          set(clin["meta"]["sources"]) ==
          {f"S{i}" for i in range(1, 11)} | {"TA2"})
    bad = []
    tier_count = Counter()
    tier_group = {}
    tier_sex = {}
    for rid, r in by_id.items():
        core, soft = CORE[rid], SOFT[rid]
        if set(r.keys()) - {"ta_code"} != BASE_KEYS | set(core) | set(soft):
            bad.append((rid, "key set"))
        if r["sex_line"] != RECORD_SEX[rid]:
            bad.append((rid, "sex line"))
        if r["ta_name"] is not None:
            # M23 discipline: TA2 name + integer ta_code + TA2
            # citation (table equality via tools/ta2_discipline.py)
            if r["sources"].get("ta_name") != ["TA2"] or \
                    not isinstance(r.get("ta_code"), int):
                bad.append((rid, "ta_name discipline"))
        elif not any("ta_name" in v for v in r["verify"]):
            bad.append((rid, "ta_name discipline"))
        exp_tier = "A"
        for fname in core + soft:
            if r[fname] is None:
                if not any(fname in v for v in r["verify"]):
                    bad.append((rid, fname + " null unflagged"))
                exp_tier = "C" if fname in core else \
                    ("B" if exp_tier == "A" else exp_tier)
            else:
                if fname not in r["sources"]:
                    bad.append((rid, fname + " valued uncited"))
                for s in r["sources"].get(fname, []):
                    if s not in clin["meta"]["sources"]:
                        bad.append((rid, fname + " bad source " + s))
        if r["sourcing_tier"] != exp_tier:
            bad.append((rid, "tier %s != %s"
                        % (r["sourcing_tier"], exp_tier)))
        tier_count[r["sourcing_tier"]] += 1
        tier_group.setdefault(r["group"], Counter())[
            r["sourcing_tier"]] += 1
        tier_sex.setdefault(r["sex_line"], Counter())[
            r["sourcing_tier"]] += 1
        for g in r["geometry_record_ids"]:
            if g not in inv_rec:
                bad.append((rid, "dangling geometry link " + g))
    check("clinical citation/flag/tier discipline (own core/soft "
          "table)", not bad, f"bad={bad[:8]}")
    check("clinical tier counts match meta (overall, by group, "
          "by sex line)",
          dict(tier_count) == clin["meta"]["tiers"]
          and {g: dict(c) for g, c in tier_group.items()} ==
          clin["meta"]["tiers_by_group"]
          and {s: dict(c) for s, c in tier_sex.items()} ==
          clin["meta"]["tiers_by_sex_line"],
          f"{dict(tier_count)}")
    bad = []
    for rid, r in by_id.items():
        if not r["geometry_record_ids"] and \
                not any(ABSENCE_MARK in v or PATHWAY_MARK in v
                        for v in r["verify"]):
            bad.append((rid, "empty links without absence/pathway "
                             "entry"))
    check("empty geometry links carry the absence or pathway "
          "entry", not bad, f"bad={bad}")
    exp_links = {
        "organ.testis": {"testis.right-testis",
                         "testis.left-testis"},
        "structure.epididymis": {"epididymis.right-epididymis",
                                 "epididymis.left-epididymis"},
        "gland.seminal-vesicles":
            {"seminal-vesicle.right-seminal-vesicle",
             "seminal-vesicle.left-seminal-vesicle"},
        "gland.prostate": {"prostate"},
        "organ.penis": {"corpus-cavernosum-of-penis",
                        "corpus-spongiosum-of-penis",
                        "glans-penis"},
        "structure.mons-pubis": {"mons-pubis"},
        "region.perineum": {"perineum",
                            "perineum.anal-part-of-perineum"},
    }
    bad = [rid for rid, r in by_id.items()
           if set(r["geometry_record_ids"]) !=
           exp_links.get(rid, set())]
    check("geometry links are exactly the expected sets (7 "
          "records linked, 9 unlinked)", not bad, f"bad={bad}")

    # ---------- content gates ----------
    mp = by_id["pathway.male-reproductive-pathway"]
    stations = " | ".join(mp["stations"]).lower()
    seq = ["seminiferous", "straight tubules", "rete testis",
           "efferent", "epididymis", "ductus deferens",
           "ejaculatory duct", "prostatic urethra",
           "membranous urethra", "spongy"]
    pos = [stations.find(w) for w in seq]
    check("male pathway stations in sourced anatomical order "
          "(seminiferous -> straight -> rete -> efferent -> "
          "epididymis -> ductus -> ejaculatory -> prostatic -> "
          "membranous -> spongy)",
          all(x >= 0 for x in pos) and pos == sorted(pos),
          f"positions={pos}")
    glands = mp["glands_in_order"].lower()
    gpos = [glands.find(w) for w in
            ("seminal vesicles", "prostate", "bulbourethral")]
    check("male pathway glands join in order (seminal vesicles "
          "-> prostate -> bulbourethral)",
          all(x >= 0 for x in gpos) and gpos == sorted(gpos),
          f"positions={gpos}")
    fp = by_id["pathway.female-reproductive-pathway"]
    fst = " | ".join(fp["stations"]).lower()
    fseq = ["ovary", "uterine tube", "uterus", "cervix", "vagina"]
    fpos = [fst.find(w) for w in fseq]
    check("female pathway stations in sourced anatomical order "
          "(ovary -> uterine tube -> uterus -> cervix -> vagina)",
          all(x >= 0 for x in fpos) and fpos == sorted(fpos),
          f"positions={fpos}")
    uri_inv = json.load(open(URI_INV))
    uri_clin_ids = {r["id"] for r in
                    json.load(open(URI_CLIN))["records"]}
    check("urethra cross-reference resolves: the male pathway "
          "names the urinary module's structure.urethra, whose "
          "inventory record 'urethra' is keyed FMA19667 — and "
          "this module duplicates neither",
          "structure.urethra" in mp["urethra_relationship"]
          and "structure.urethra" in uri_clin_ids
          and any(r["record_id"] == "urethra"
                  and r["concept_ids"] == [URETHRA]
                  for r in uri_inv["records"])
          and "structure.urethra" not in by_id)
    cv_ids = {r["record_id"] for r in
              json.load(open(CV_INV))["records"]}
    tes = by_id["organ.testis"]
    named = set(re.findall(r"(?:artery|vein)\.[a-z0-9-]+",
                           tes["arterial_supply"] + " " +
                           tes["venous_drainage"]))
    check("testis record's named cardiovascular records all "
          "resolve (both testicular arteries and veins)",
          named == {"artery.right-testicular-artery",
                    "artery.left-testicular-artery",
                    "vein.right-testicular-vein",
                    "vein.left-testicular-vein"}
          and named <= cv_ids, f"named={sorted(named)}")
    pen = by_id["organ.penis"]
    pnamed = set(re.findall(r"(?:artery|vein)\.[a-z0-9-]+",
                            pen["arterial_supply"] + " " +
                            pen["venous_drainage"]))
    check("penis record's named cardiovascular records all "
          "resolve (2 dorsal arteries, 3 dorsal veins)",
          pnamed == {"artery.right-dorsal-artery-of-penis",
                     "artery.left-dorsal-artery-of-penis",
                     "vein.deep-dorsal-vein-of-penis",
                     "vein.right-superficial-dorsal-vein-of-penis",
                     "vein.left-superficial-dorsal-vein-of-penis"}
          and pnamed <= cv_ids, f"named={sorted(pnamed)}")
    ov = by_id["organ.ovary"]
    check("ovary record's absence discipline: no geometry, the "
          "absence recorded on the record itself, the ovarian "
          "arteries sourced — and no ovarian vessel record "
          "exists in the cardiovascular module to point at",
          ov["geometry_record_ids"] == []
          and any(ABSENCE_MARK in v for v in ov["verify"])
          and "ovarian arteries" in ov["arterial_supply"]
          and not any("ovarian" in r["record_id"]
                      for r in json.load(open(CV_INV))["records"]))
    pro = by_id["gland.prostate"]["parts"].lower()
    zpos = [pro.find(w) for w in
            ("central zone", "transitional", "peripheral")]
    check("prostate zones in McNeal order inside the parts "
          "field (central < transitional < peripheral)",
          all(x >= 0 for x in zpos) and zpos == sorted(zpos),
          f"positions={zpos}")
    check("testis parts carry the seminiferous tubules and the "
          "lobule count of the consulted source",
          "seminiferous" in tes["parts"]
          and "300 to 400" in tes["parts"])
    musc_inv = json.load(open(MUSC_INV))
    per = by_id["region.perineum"]
    check("perineum record's sphincter pointer resolves to the "
          "muscular module's inventory record",
          "muscle.external-anal-sphincter" in per["dataset_note"]
          and any(r["record_id"] ==
                  "muscle.external-anal-sphincter"
                  for r in musc_inv["records"]))
    fem_linked = {rid for rid, r in by_id.items()
                  if r["sex_line"] == "female"
                  and r["geometry_record_ids"]}
    male_linked = {rid for rid, r in by_id.items()
                   if r["sex_line"] == "male"
                   and r["geometry_record_ids"]}
    check("female geometry census: exactly one female clinical "
          "record links geometry (the mons pubis), against five "
          "male organ records",
          fem_linked == {"structure.mons-pubis"}
          and by_id["structure.mons-pubis"]
          ["geometry_record_ids"] == ["mons-pubis"]
          and male_linked == {"organ.testis",
                              "structure.epididymis",
                              "gland.seminal-vesicles",
                              "gland.prostate", "organ.penis"},
          f"female={fem_linked} male={male_linked}")
    check("the mons pubis record is the tranche's one tier C "
          "(its core parts and function fields flagged null), "
          "and overall tiers are A7 B8 C1",
          by_id["structure.mons-pubis"]["sourcing_tier"] == "C"
          and by_id["structure.mons-pubis"]["parts"] is None
          and by_id["structure.mons-pubis"]["function"] is None
          and dict(tier_count) == {"A": 7, "B": 8, "C": 1},
          f"tiers={dict(tier_count)}")

    # TA2 discipline (M23)
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    import ta2_discipline as _ta2d
    _ta2d.run("reproductive", "data/reproductive/reproductive.json", lambda ok_, label: check(label, ok_))
    _ta2d.run_fma_inventory_multi("reproductive", "data/reproductive/reproductive-inventory.json", "fma_inventory_reproductive", "M38", lambda ok_, label: check(label, ok_))

    npass = sum(1 for _, ok, _ in checks if ok)
    print(f"repro_check: {npass}/{len(checks)} checks passed")
    for name, ok, detail in checks:
        print(("PASS " if ok else "FAIL ") + name +
              ((" — " + detail) if detail and not ok else ""))
    print(f"  universe {len(exp_universe)} concepts (male 14 / "
          f"female 1 / shared 6) / {len(exp_records)} records / "
          f"geometry totals: IS-A {tot['isa_v']} v "
          f"{tot['isa_f']} f, PART-OF {tot['partof_v']} v "
          f"{tot['partof_f']} f / clinical {len(recs)} records "
          f"tiers {dict(tier_count)}")
    return 0 if npass == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
