#!/usr/bin/env python3
"""ANATOMICA Milestone 15 — independent checker for the
integumentary module.

Shares NO code with tools/integ_map.py or
tools/build_integ_records.py. Re-derives, from the six BP3D
4.0 release tables: (1) the concept universe (the skin IS-A
singleton, the subdivision-of-epidermis IS-A line, the
hair-set IS-A line, the integumentary-system and integument
PART-OF lines), its records and dispositions, the sweep
adjudications and the absence probes; (2) the concept->mesh
attribution (FJ numbers) and every recorded vertex/face
count and bounding box, by re-reading the OBJ files, plus
the three structural identities — the single FJ2810 shell
serving as skin in both tables and as the PART-OF content
of integument and system root, the hair files' head/trunk
partition, and the eyebrow and its set classes resolving to
the one file FJ2812 — and the module file census (four
files in total); (3) the TotalSegmentator overlap, from the
M3 label index (zero skin labels; the one term-matched
label, 'face', adjudicated a region mask); (4) the
Milestone 14 boundary — pubic hair's PART-OF parent must be
the mons pubis concept the reproductive module holds as its
record; (5) the clinical tranche's citation/flag/tier
discipline against this checker's own core/soft field
table, plus content gates: the skin's layer order, the
epidermis' strata order deep to superficial, the dermis'
layer order, the hair and nail part orders, the sweat
gland types in eccrine-then-apocrine order, the mammary
record's lobule count and its lymphatic percentages in
order, its ownership adjudication carrying both the
modified-sweat-gland basis and the recorded
counter-consideration, its absence discipline (no geometry,
absence on the record), and the cross-module gate — no
mammary or breast record or concept anywhere in the
reproductive module — and the two designed tier C records
(trunk hair, pubic hair) with their function fields flagged
null.

Run: python3 tools/integ_check.py   (exit 0 = all pass)
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
INV_P = os.path.join(ROOT, "data", "integumentary",
                     "integumentary-inventory.json")
GEO_P = os.path.join(ROOT, "data", "integumentary",
                     "integumentary-geometry.json")
CLIN_P = os.path.join(ROOT, "data", "integumentary",
                      "integumentary.json")
REPRO_INV = os.path.join(ROOT, "data", "reproductive",
                         "reproductive-inventory.json")
REPRO_CLIN = os.path.join(ROOT, "data", "reproductive",
                          "reproductive.json")
TS_LABELS = os.path.join(ROOT, "data", "sources",
                         "totalsegmentator-1.0", "labels.json")

SKIN = "FMA7163"
EPIDERMIS_SUBDIV = "FMA70593"
SKIN_APPENDAGE = "FMA71012"
HAIR = "FMA53667"
HAIR_HEAD = "FMA54241"
HAIR_TRUNK = "FMA54250"
PUBIC_HAIR = "FMA54319"
HAIR_SET = "FMA70752"
FACIAL_HAIR_SET = "FMA70741"
EYEBROW = "FMA54237"
SYSTEM_PO = "FMA72979"
INTEGUMENT_PO = "FMA74657"
MONS_PUBIS = "FMA20218"

SKIN_SET = {SKIN}
EPIDERMIS_SET = {EPIDERMIS_SUBDIV, SKIN_APPENDAGE, HAIR,
                 HAIR_HEAD, HAIR_TRUNK, PUBIC_HAIR}
HAIR_SET_SET = {HAIR_SET, FACIAL_HAIR_SET, EYEBROW}
SYSTEM_SET = {SYSTEM_PO}
INTEGUMENT_SET = {INTEGUMENT_PO, SKIN}
UNIVERSE = SKIN_SET | EPIDERMIS_SET | HAIR_SET_SET | \
    SYSTEM_SET | INTEGUMENT_SET
LINE = {SKIN: "skin", SYSTEM_PO: "system", INTEGUMENT_PO: "system"}
for _c in EPIDERMIS_SET | HAIR_SET_SET:
    LINE[_c] = "appendage"
GROUPING = {SYSTEM_PO, INTEGUMENT_PO, EPIDERMIS_SUBDIV, HAIR_SET}
# record id -> (concept, representation, class concept)
EXP_RECORDS = {
    "skin": (SKIN, "organ", SKIN),
    "hair": (HAIR, "whole-concept", SKIN_APPENDAGE),
    "hair.hair-of-head": (HAIR_HEAD, "whole-concept", HAIR),
    "hair.hair-of-trunk": (HAIR_TRUNK, "whole-concept", HAIR),
    "hair.pubic-hair": (PUBIC_HAIR, "whole-concept", HAIR_TRUNK),
    "eyebrow": (EYEBROW, "whole-concept", FACIAL_HAIR_SET),
}
SWEEP_TERMS = ("skin", "hair", "eyebrow", "integument",
               "epiderm", "nail", "unguis", "mammary",
               "breast", "sebaceous", "sweat", "follicle",
               "cilia", "eyelash", "scalp", "subcutaneous",
               "areola", "nipple", "fascia", "gland")
TS_TERMS = ("skin", "face", "body", "breast", "trunc",
            "extremit", "hair", "nail", "surface")
SKIN_FILES_ISA = {"FJ2810": {"skin"}}
SKIN_FILES_PO = {"FJ2810": {"skin"}, "FJ2815": {"hair.pubic-hair"}}
HAIR_FILES_ISA = {"FJ2812": {"eyebrow"},
                  "FJ2813": {"hair", "hair.hair-of-head"},
                  "FJ2815": {"hair", "hair.hair-of-trunk",
                             "hair.pubic-hair"}}

CORE = {
    "organ.skin": ["description", "layers", "function"],
    "structure.epidermis": ["description", "strata", "function"],
    "structure.dermis": ["description", "layers", "function"],
    "structure.hypodermis": ["description", "function"],
    "structure.hair": ["description", "parts", "function"],
    "structure.hair-of-head": ["description", "function"],
    "structure.hair-of-trunk": ["description", "function"],
    "structure.pubic-hair": ["description", "function"],
    "structure.eyebrow": ["description", "function"],
    "structure.nail": ["description", "parts", "function"],
    "gland.sebaceous-glands": ["description", "secretion",
                               "function"],
    "gland.sweat-glands": ["description", "types", "function"],
    "organ.mammary-gland": ["description", "parts", "function",
                            "ownership"],
}
SOFT = {
    "organ.skin": ["cells", "vascularisation", "innervation"],
    "structure.epidermis": ["cells", "forms"],
    "structure.dermis": ["contents"],
    "structure.hypodermis": ["composition"],
    "structure.hair": ["growth_cycle", "colour"],
    "structure.hair-of-head": [],
    "structure.hair-of-trunk": [],
    "structure.pubic-hair": [],
    "structure.eyebrow": [],
    "structure.nail": [],
    "gland.sebaceous-glands": ["activation"],
    "gland.sweat-glands": [],
    "organ.mammary-gland": ["relations", "arterial_supply",
                            "venous_drainage",
                            "lymphatic_drainage", "innervation"],
}
BASE_KEYS = {"id", "name", "type", "group", "ta_name",
             "sources", "verify", "note",
             "geometry_record_ids", "sourcing_tier"}
ABSENCE_MARK = "no BP3D 4.0 concept exists"

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
                    if x < mn[i]:
                        mn[i] = x
                    if x > mx[i]:
                        mx[i] = x
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
    isa_kids, po_kids = {}, {}
    isa_par, po_par = {}, {}
    for r in read_tsv(os.path.join(
            SRC, "isa_inclusion_relation_list.txt")):
        isa_kids.setdefault(r[0], []).append(r[2])
        isa_par[r[2]] = r[0]
    for r in read_tsv(os.path.join(
            SRC, "partof_inclusion_relation_list.txt")):
        po_kids.setdefault(r[0], []).append(r[2])
        po_par[r[2]] = r[0]

    inv = json.load(open(INV_P))
    geo = json.load(open(GEO_P))
    clin = json.load(open(CLIN_P))
    meta = inv["meta"]
    cu = meta["concept_universe"]

    # ---------- universe, re-derived two ways ----------
    d_skin = descendants(SKIN, isa_kids)
    d_epi = descendants(EPIDERMIS_SUBDIV, isa_kids)
    d_hset = descendants(HAIR_SET, isa_kids)
    d_sys = descendants(SYSTEM_PO, po_kids)
    d_int = descendants(INTEGUMENT_PO, po_kids)
    check("subtree derivations match the expected sets (skin "
          "IS-A singleton; epidermis-subdivision line of 6; "
          "hair-set line of 3; system root bare; integument "
          "line of 2)",
          d_skin == SKIN_SET and d_epi == EPIDERMIS_SET
          and d_hset == HAIR_SET_SET and d_sys == SYSTEM_SET
          and d_int == INTEGUMENT_SET,
          f"skin={sorted(d_skin)} epi={sorted(d_epi)} "
          f"hset={sorted(d_hset)} sys={sorted(d_sys)} "
          f"int={sorted(d_int)}")
    exp_isa = SKIN_SET | EPIDERMIS_SET | HAIR_SET_SET
    exp_po = SYSTEM_SET | INTEGUMENT_SET
    check("concept universe is exactly the expected 12 "
          "(IS-A 10, PART-OF 3, both tables 1 — the skin)",
          UNIVERSE == exp_isa | exp_po and len(UNIVERSE) == 12
          and len(exp_isa) == 10 and len(exp_po) == 3
          and exp_isa & exp_po == {SKIN})
    inv_concepts = {c["fma_id"]: c for c in inv["concepts"]}
    check("inventory concepts are exactly the universe, with "
          "matching names, tables and lines",
          set(inv_concepts) == UNIVERSE
          and cu["total"] == 12 and cu["isa_total"] == 10
          and cu["partof_total"] == 3
          and cu["in_both_tables"] == 1
          and all(inv_concepts[c]["name"] ==
                  (isa[c] if c in exp_isa else po[c])["name"]
                  for c in UNIVERSE)
          and all(inv_concepts[c]["line"] == LINE[c]
                  for c in UNIVERSE)
          and cu["by_line"] == {"skin": 1, "appendage": 9,
                                "system": 2},
          f"by_line={cu['by_line']}")
    check("inventory set counts match the derivations",
          cu["isa_sets"] == {"skin-isa": 1,
                             "epidermis-subdivision-isa": 6,
                             "hair-set-isa": 3}
          and cu["partof_sets"] ==
          {"integumentary-system-partof": 1,
           "integument-partof": 2})
    # dispositions, re-derived
    claimed = {}
    for rid, (cid, _rep, _cls) in EXP_RECORDS.items():
        claimed[cid] = rid
    class_carried = {cls for _rid, (_c, _r, cls)
                     in EXP_RECORDS.items()
                     if cls not in claimed}
    exp_disp = {}
    for c in UNIVERSE:
        if c in claimed:
            exp_disp[c] = "record"
        elif c in class_carried:
            exp_disp[c] = "class-carried"
        elif c in GROUPING:
            exp_disp[c] = "grouping-class"
        else:
            exp_disp[c] = "subtree-internal"
    check("dispositions match (6 record, 2 class-carried — "
          "skin appendage and set of facial hairs, 4 "
          "grouping-class, 0 subtree-internal)",
          all(inv_concepts[c]["disposition"] == exp_disp[c]
              for c in UNIVERSE)
          and Counter(exp_disp.values()) ==
          Counter({"record": 6, "class-carried": 2,
                   "grouping-class": 4})
          and class_carried == {SKIN_APPENDAGE, FACIAL_HAIR_SET}
          and cu["dispositions"] ==
          {"record": 6, "class-carried": 2, "grouping-class": 4},
          f"disp={Counter(exp_disp.values())}")
    inv_records = {r["record_id"]: r for r in inv["records"]}
    bp3d_records = {rid: r for rid, r in inv_records.items()
                    if r["representation"] != "fma-concept"}
    fma_records = {rid: r for rid, r in inv_records.items()
                   if r["representation"] == "fma-concept"}
    check("inventory records are exactly the expected six, "
          "with concepts, representations and carried classes "
          "(BP3D partition, scoped at Milestone 38; the 53 "
          "Milestone 38 FMA concept records beside them are "
          "gated by tools/fma_integ_male_check.py)",
          set(bp3d_records) == set(EXP_RECORDS)
          and len(fma_records) == 53
          and meta["record_count"] == 59
          and all(bp3d_records[rid]["concept_ids"] == [cid]
                  and bp3d_records[rid]["representation"] == rep
                  and bp3d_records[rid]["class_concept_id"] == cls
                  for rid, (cid, rep, cls) in EXP_RECORDS.items())
          and meta["record_representations"] ==
          {"organ": 1, "whole-concept": 5, "fma-concept": 53})
    check("per-concept mesh file counts in the inventory "
          "match the element tables",
          all(inv_concepts[c]["isa_mesh_files"] ==
              len(isa_elem.get(c, ()))
              and inv_concepts[c]["partof_mesh_files"] ==
              len(po_elem.get(c, ())) for c in UNIVERSE))

    # ---------- sweep, re-derived ----------
    rej = {}
    for tab, tn in ((isa, "isa"), (po, "partof")):
        for cid, v in tab.items():
            if cid in UNIVERSE:
                continue
            if any(t in v["name"].lower() for t in SWEEP_TERMS):
                rej.setdefault(v["name"], tn)
    check("sweep re-derived: exactly 59 rejected names, all "
          "adjudicated in the inventory, none unadjudicated",
          sorted(rej) == cu["sweep_rejected_names"]
          and len(rej) == 59
          and set(cu["sweep_adjudications"]) == set(rej),
          f"n={len(rej)}")
    zero_terms = [t for t in SWEEP_TERMS
                  if not any(t in v["name"].lower()
                             for tab in (isa, po)
                             for v in tab.values())]
    check("sweep zero-hit terms match (nail, unguis, mammary, "
          "breast, sebaceous, sweat, follicle, eyelash, scalp, "
          "subcutaneous, areola, nipple — the absence headline "
          "in twelve terms)",
          zero_terms == cu["sweep_zero_hit_terms"]
          and set(zero_terms) == {"nail", "unguis", "mammary",
                                  "breast", "sebaceous",
                                  "sweat", "follicle",
                                  "eyelash", "scalp",
                                  "subcutaneous", "areola",
                                  "nipple"},
          f"zero={zero_terms}")

    # ---------- absence probes, re-run ----------
    table_files = ["isa_parts_list_e.txt",
                   "partof_parts_list_e.txt",
                   "isa_element_parts.txt",
                   "partof_element_parts.txt",
                   "isa_inclusion_relation_list.txt",
                   "partof_inclusion_relation_list.txt"]
    texts = {fn: open(os.path.join(SRC, fn), encoding="utf-8",
                      errors="replace").read().lower()
             for fn in table_files}
    all_names = {v["name"] for v in isa.values()} | \
        {v["name"] for v in po.values()}
    ab = meta["absences"]
    bad = []
    for a in ab["substring_probes"]["detail"]:
        tot = sum(texts[fn].count(a["probe"])
                  for fn in table_files)
        if tot != a["total_hits"]:
            bad.append((a["probe"], tot, a["total_hits"]))
    check("substring probes re-run identically (41 probes, "
          "35 zero-hit — only the six controls present)",
          not bad and ab["substring_zero_hit_count"] == 35
          and ab["substring_probes"]["present"] ==
          ["skin", "hair", "eyebrow", "integument",
           "epidermis", "pubic hair"],
          f"bad={bad[:5]}")
    bad = []
    for a in ab["exact_name_probes"]["detail"]:
        if (a["probe"] in all_names) != a["concept_exists"]:
            bad.append(a["probe"])
    check("exact-name probes re-run identically (34 probes, "
          "29 zero-hit — epidermis, dermis and hypodermis "
          "among them; only the five controls exist)",
          not bad and ab["exact_name_zero_hit_count"] == 29
          and ab["exact_name_probes"]["present"] ==
          ["skin", "hair", "eyebrow", "integument",
           "integumentary system"]
          and "epidermis" in ab["exact_name_probes"]["absent"]
          and "dermis" in ab["exact_name_probes"]["absent"]
          and "mammary gland" in
          ab["exact_name_probes"]["absent"],
          f"bad={bad[:5]}")

    # ---------- Milestone 14 boundary ----------
    repro_inv = json.load(open(REPRO_INV))
    mons = [r for r in repro_inv["records"]
            if r["record_id"] == "mons-pubis"]
    check("pubic hair boundary re-derived: its PART-OF parent "
          "is FMA20218, the concept the reproductive module "
          "holds as its mons-pubis record",
          po_par.get(PUBIC_HAIR) == MONS_PUBIS
          and len(mons) == 1
          and mons[0]["concept_ids"] == [MONS_PUBIS]
          and meta["boundary_closures"]
          ["milestone_14_reproductive"]["closes"] is True)

    # ---------- geometry, re-measured ----------
    geo_rec = {r["record_id"]: r for r in geo["records"]}
    bad = []
    entries = 0
    all_meshes = []
    tot = Counter()
    for rid, gr in geo_rec.items():
        if rid not in EXP_RECORDS:
            continue  # Milestone 38 FMA entries carry no
            # meshes; gated by tools/fma_integ_male_check.py
        cid = EXP_RECORDS[rid][0]
        for tree, elem, d in (("isa", isa_elem, ISA_DIR),
                              ("partof", po_elem, PO_DIR)):
            key = tree + "_meshes"
            exp_fj = sorted(elem.get(cid, ()))
            got_fj = sorted(m["fj"] for m in gr[key])
            if exp_fj != got_fj:
                bad.append((rid, key, exp_fj, got_fj))
            for m in gr[key]:
                entries += 1
                all_meshes.append(m)
                v, f, bb = measure(os.path.join(d, m["fj"] + ".obj"))
                tot[tree + "_v"] += v
                tot[tree + "_f"] += f
                if (v, f, bb) != (m["vertices"], m["faces"],
                                  m["bbox"]):
                    bad.append((rid, m["fj"], "remeasure"))
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
    check(f"all geometry entries re-measured ({entries} "
          "entries)", not bad, f"bad={bad[:6]}")
    cov = geo["meta"]["coverage"]
    check("geometry coverage meta matches (6/59 with meshes; "
          "skin line 1/20, appendage line 5/39 — the Milestone "
          "38 FMA records are concept-only)",
          cov["records"] == 59
          and cov["records_with_meshes"] == 6
          and cov["by_line"]["skin"]["records"] == 20
          and cov["by_line"]["skin"]["records_with_meshes"] == 1
          and cov["by_line"]["appendage"]["records"] == 39
          and cov["by_line"]["appendage"]
          ["records_with_meshes"] == 5)
    if all_meshes:
        mn = [min(m["bbox"]["min"][i] for m in all_meshes)
              for i in range(3)]
        mx = [max(m["bbox"]["max"][i] for m in all_meshes)
              for i in range(3)]
        check("union bbox over all records matches meta",
              cov["union_bbox_all_records"] ==
              {"min": mn, "max": mx})
    fj_owner = {"isa": {}, "partof": {}}
    for rid, gr in geo_rec.items():
        for tree in ("isa", "partof"):
            for m in gr[tree + "_meshes"]:
                fj_owner[tree].setdefault(m["fj"], set()).add(rid)
    check("FJ attribution is exactly the designed sharing: "
          "FJ2813 shared by the hair class and hair of head, "
          "FJ2815 by the hair class, hair of trunk and pubic "
          "hair (IS-A); FJ2810 and FJ2815 single-owner in "
          "PART-OF",
          fj_owner["isa"] ==
          {**SKIN_FILES_ISA, **HAIR_FILES_ISA}
          and fj_owner["partof"] == SKIN_FILES_PO,
          f"isa={fj_owner['isa']} po={fj_owner['partof']}")
    # structural identities, re-derived from the element tables
    check("skin shell identity re-derived: skin (both "
          "tables), integument and the system root all "
          "resolve to FJ2810 alone",
          isa_elem.get(SKIN, set()) == {"FJ2810"}
          and po_elem.get(SKIN, set()) == {"FJ2810"}
          and po_elem.get(INTEGUMENT_PO, set()) == {"FJ2810"}
          and po_elem.get(SYSTEM_PO, set()) == {"FJ2810"})
    check("hair partition re-derived: subdivision, appendage "
          "and hair classes carry {FJ2813, FJ2815}; head "
          "FJ2813 alone; trunk and pubic hair FJ2815 alone "
          "(pubic hair in both tables)",
          isa_elem.get(EPIDERMIS_SUBDIV, set()) ==
          isa_elem.get(SKIN_APPENDAGE, set()) ==
          isa_elem.get(HAIR, set()) == {"FJ2813", "FJ2815"}
          and isa_elem.get(HAIR_HEAD, set()) == {"FJ2813"}
          and isa_elem.get(HAIR_TRUNK, set()) ==
          isa_elem.get(PUBIC_HAIR, set()) ==
          po_elem.get(PUBIC_HAIR, set()) == {"FJ2815"})
    check("eyebrow set identity re-derived: set of hairs, "
          "set of facial hairs and eyebrow all resolve to "
          "FJ2812 in IS-A, none carried in PART-OF",
          isa_elem.get(HAIR_SET, set()) ==
          isa_elem.get(FACIAL_HAIR_SET, set()) ==
          isa_elem.get(EYEBROW, set()) == {"FJ2812"}
          and not po_elem.get(EYEBROW)
          and EYEBROW not in po)
    distinct = {fj for em in (isa_elem, po_elem)
                for c in UNIVERSE for fj in em.get(c, ())}
    find = geo["meta"]["structure_findings"]
    check("module file census re-derived: the whole "
          "module's geometry is four mesh files, and the "
          "recorded structure findings match",
          distinct == {"FJ2810", "FJ2812", "FJ2813", "FJ2815"}
          and find["skin_shell_identity"]["identical"] is True
          and find["hair_file_partition"]["identical"] is True
          and find["eyebrow_set_identity"]["identical"] is True
          and find["module_file_census"]["distinct_files"] ==
          ["FJ2810", "FJ2812", "FJ2813", "FJ2815"],
          f"distinct={sorted(distinct)}")

    # ---------- TotalSegmentator overlap ----------
    ts = json.load(open(TS_LABELS))
    ts_counts = ts["labels"]
    ts_hits = sorted(l for l in ts_counts
                     if any(t in l for t in TS_TERMS))
    check("TS v1 integument adjudication re-derived: of its "
          "104 labels the only term match is 'face' — a "
          "region mask; no skin, body_trunc, body_extremities "
          "or other body-surface label exists",
          ts_hits == ["face"] and len(ts_counts) == 104
          and "body_trunc" not in ts_counts
          and "body_extremities" not in ts_counts
          and "skin" not in ts_counts,
          f"hits={ts_hits} labels={len(ts_counts)}")
    check("inventory TS overlap matches (no labels mapped; "
          "'face' recorded as matched-by-terms with its "
          "adjudication)",
          meta["totalsegmentator_overlap"]["labels"] == []
          and meta["totalsegmentator_overlap"]
          ["labels_without_records"] == []
          and meta["totalsegmentator_overlap"]
          ["labels_matched_by_terms"] == ["face"]
          and "region mask" in meta["totalsegmentator_overlap"]
          ["adjudication"])

    # ---------- clinical tranche ----------
    recs = clin["records"]
    by_id = {r["id"]: r for r in recs}
    check("clinical record count and ids match this checker "
          "(13 records)",
          clin["meta"]["record_count"] == len(CORE) == 13
          and set(by_id) == set(CORE), f"{sorted(by_id)}")
    check("clinical meta sources are exactly S1-S5 + TA2 (M23)",
          set(clin["meta"]["sources"]) ==
          {f"S{i}" for i in range(1, 6)} | {"TA2"})
    bad = []
    tier_count = Counter()
    tier_group = {}
    for rid, r in by_id.items():
        core, soft = CORE[rid], SOFT[rid]
        if set(r.keys()) - {"ta_code"} != BASE_KEYS | set(core) | set(soft):
            bad.append((rid, "key set"))
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
        for g in r["geometry_record_ids"]:
            if g not in inv_records:
                bad.append((rid, "dangling geometry link " + g))
    check("clinical citation/flag/tier discipline (own "
          "core/soft table)", not bad, f"bad={bad[:8]}")
    check("clinical tier counts match meta (overall and by "
          "group)",
          dict(tier_count) == clin["meta"]["tiers"]
          and {g: dict(c) for g, c in tier_group.items()} ==
          clin["meta"]["tiers_by_group"],
          f"{dict(tier_count)}")
    bad = []
    for rid, r in by_id.items():
        if not r["geometry_record_ids"] and \
                not any(ABSENCE_MARK in v for v in r["verify"]):
            bad.append((rid, "empty links without absence entry"))
    check("empty geometry links carry the absence entry",
          not bad, f"bad={bad}")
    exp_links = {
        "organ.skin": {"skin"},
        "structure.hair": {"hair"},
        "structure.hair-of-head": {"hair.hair-of-head"},
        "structure.hair-of-trunk": {"hair.hair-of-trunk"},
        "structure.pubic-hair": {"hair.pubic-hair"},
        "structure.eyebrow": {"eyebrow"},
    }
    bad = [rid for rid, r in by_id.items()
           if set(r["geometry_record_ids"]) !=
           exp_links.get(rid, set())]
    check("geometry links are exactly the expected sets (6 "
          "records linked, 7 unlinked)", not bad, f"bad={bad}")

    # ---------- content gates ----------
    sk = by_id["organ.skin"]
    lpos = [sk["layers"][i].find(w) for i, w in
            enumerate(("epidermis", "dermis", "hypodermis"))]
    check("skin layers in sourced order (epidermis -> "
          "dermis -> hypodermis)",
          len(sk["layers"]) == 3 and all(x == 0 for x in lpos)
          and sk["layers"][0].startswith("epidermis")
          and sk["layers"][1] == "dermis"
          and sk["layers"][2].startswith("hypodermis"))
    ep = by_id["structure.epidermis"]
    strata = " | ".join(ep["strata"]).lower()
    spos = [strata.find(w) for w in
            ("basale", "spinosum", "granulosum", "lucidum",
             "corneum")]
    check("epidermal strata in sourced deep-to-superficial "
          "order (basale -> spinosum -> granulosum -> "
          "lucidum -> corneum)",
          all(x >= 0 for x in spos) and spos == sorted(spos),
          f"positions={spos}")
    de = by_id["structure.dermis"]
    check("dermal layers in sourced order (papillary -> "
          "reticular)",
          de["layers"] == ["papillary layer", "reticular layer"])
    ha = by_id["structure.hair"]
    parts = " | ".join(ha["parts"]).lower()
    ppos = [parts.find(w) for w in
            ("follicle", "shaft", "root", "bulb", "matrix",
             "papilla")]
    check("hair parts carry the follicle, shaft, root, bulb, "
          "matrix and papilla in the record's stated order",
          all(x >= 0 for x in ppos) and ppos == sorted(ppos),
          f"positions={ppos}")
    na = by_id["structure.nail"]
    nparts = " | ".join(na["parts"]).lower()
    npos = [nparts.find(w) for w in
            ("nail bed", "nail root", "nail body",
             "eponychium", "lunula", "hyponychium")]
    check("nail parts in the record's stated anatomical "
          "order (bed -> root -> body -> eponychium -> "
          "lunula -> hyponychium)",
          all(x >= 0 for x in npos) and npos == sorted(npos),
          f"positions={npos}")
    sw = by_id["gland.sweat-glands"]
    check("sweat gland types in order (eccrine first, "
          "apocrine second), with their sourced distributions",
          len(sw["types"]) == 2
          and sw["types"][0].startswith("eccrine")
          and "palms" in sw["types"][0]
          and sw["types"][1].startswith("apocrine")
          and "armpits" in sw["types"][1])
    mg = by_id["organ.mammary-gland"]
    check("mammary record carries the sourced 15-20 lobules "
          "in its parts",
          any("15-20" in p and "lobule" in p.lower()
              for p in mg["parts"]))
    lym = mg["lymphatic_drainage"]
    ypos = [lym.find(w) for w in ("(75%)", "(20%)", "(5%)")]
    check("mammary lymphatic percentages in sourced order "
          "(axillary 75% -> parasternal 20% -> posterior "
          "intercostal 5%)",
          all(x >= 0 for x in ypos) and ypos == sorted(ypos),
          f"positions={ypos}")
    check("mammary ownership adjudication carries both the "
          "basis and the counter-consideration, and the "
          "absence discipline holds (no geometry, absence on "
          "the record)",
          "modified sweat glands" in mg["ownership"]
          and "accessory gland of the female reproductive "
              "system" in mg["ownership"]
          and "owned HERE" in mg["ownership"]
          and mg["geometry_record_ids"] == []
          and any(ABSENCE_MARK in v for v in mg["verify"]))
    repro_clin = json.load(open(REPRO_CLIN))
    repro_names = [c["name"].lower()
                   for c in repro_inv["concepts"]]
    check("cross-module gate: the reproductive module holds "
          "no mammary or breast record and no mammary or "
          "breast concept — the ownership question has no "
          "dataset claimant there",
          not any("mammary" in r["id"] or "breast" in r["id"]
                  for r in repro_clin["records"])
          and not any("mammary" in n or "breast" in n
                      for n in repro_names))
    check("the two designed tier C records are trunk hair "
          "and pubic hair, each with its function field "
          "flagged null; the eyebrow record is tier A; "
          "overall tiers are A11 C2",
          by_id["structure.hair-of-trunk"]["sourcing_tier"] == "C"
          and by_id["structure.hair-of-trunk"]["function"] is None
          and by_id["structure.pubic-hair"]["sourcing_tier"] == "C"
          and by_id["structure.pubic-hair"]["function"] is None
          and by_id["structure.eyebrow"]["sourcing_tier"] == "A"
          and dict(tier_count) == {"A": 11, "C": 2},
          f"tiers={dict(tier_count)}")

    # TA2 discipline (M23)
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    import ta2_discipline as _ta2d
    _ta2d.run("integumentary", "data/integumentary/integumentary.json", lambda ok_, label: check(label, ok_))

    # TA2 discipline over the Milestone 38 FMA inventory
    # records (Milestone 38 extension of the Milestone 35
    # pattern)
    _ta2d.run_fma_inventory_multi("integumentary", "data/integumentary/integumentary-inventory.json", "fma_inventory_integumentary", "M38", lambda ok_, label: check(label, ok_))

    npass = sum(1 for _, ok, _ in checks if ok)
    print(f"integ_check: {npass}/{len(checks)} checks passed")
    for name, ok, detail in checks:
        print(("PASS " if ok else "FAIL ") + name +
              ((" — " + detail) if detail and not ok else ""))
    print(f"  universe {len(UNIVERSE)} concepts (skin 1 / "
          f"appendage 9 / system 2) / {len(EXP_RECORDS)} "
          f"records / geometry totals: IS-A {tot['isa_v']} v "
          f"{tot['isa_f']} f, PART-OF {tot['partof_v']} v "
          f"{tot['partof_f']} f over {entries} entries / "
          f"clinical {len(recs)} records tiers "
          f"{dict(tier_count)}")
    return 0 if npass == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
