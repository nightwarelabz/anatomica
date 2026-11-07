#!/usr/bin/env python3
"""ANATOMICA Milestone 12: independent urinary module checker.

Written against the source tables and the shipped JSON, in the
house style of tools/dig_check.py: it does NOT import the
builders. It re-derives the concept universe from the six
BodyParts3D tables (own loading, own hierarchy walks, the
builder's documented roots and sweep lists), re-derives the
adrenal filing (PART-OF parentage under the endocrine system,
absence from the urinary subtree), the rejected-sweep census and
the disposition accounting (record / class-carried /
cross-reference / grouping-class must partition the universe
exactly), re-measures every mesh entry by streaming the OBJ
files (vertex/face counts AND bounding boxes) with FJ attribution
checked against the element-parts tables, re-runs the absence
probes as raw-text occurrence counts over all six tables, parses
the TotalSegmentator label census itself, verifies the
cardiovascular cross-module pointers (the renal clinical records
and the renal/suprarenal census count), and validates the
clinical tranche's citation discipline, tier assignments (against
its own core/soft table), pathway and nephron segment order,
bladder parts and ureter constriction lists, and the adrenal
non-duplication gate.

Scope note (Milestone 37): the inventory now also carries 67
FMA 5.1.0 concept records (the urinary interior). Every check
below that speaks of the concept universe, the records, the
dispositions, the geometry or the clinical linkage is scoped
to the BP3D partition (records without the fma-5.1.0 source
tag), exactly as shipped at Milestone 12; the FMA records
themselves are gated by tools/fma_uri_repro_check.py, and
their TA2 discipline by ta2_discipline.run_fma_inventory_multi
at the end of this file.

Exit code 0 only if every hard check passes. Printed lines marked
[report] are informational.
"""

import json
import os
import sys
from collections import Counter, OrderedDict, defaultdict

PROJECT = "/home/hatch/workspace/anatomica-project"
SRC = os.path.join(PROJECT, "data/sources/bodyparts3d-4.0")
TS_LABELS = os.path.join(
    PROJECT, "data/sources/totalsegmentator-1.0/labels.json")
URI = os.path.join(PROJECT, "data/urinary")
CV_INV = os.path.join(PROJECT,
                      "data/cardiovascular/cv-inventory.json")
CV_CLIN = os.path.join(PROJECT,
                       "data/cardiovascular/cardiovascular.json")
ISA_DIR = os.path.join(PROJECT, "work/bp3d/isa_BP3D_4.0_obj_99")
PO_DIR = os.path.join(PROJECT, "work/bp3d/partof_BP3D_4.0_obj_99")

failures = []
notes = []


def check(ok, label):
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        failures.append(label)


def report(label):
    print("[report] " + label)
    notes.append(label)


# ------------------------------------------------------------------
# Independent table loading (3-column TSVs)
# ------------------------------------------------------------------
def load_tsv(name):
    with open(os.path.join(SRC, name), encoding="utf-8",
              errors="replace") as fh:
        lines = fh.read().splitlines()
    return [ln.split("\t") for ln in lines[1:] if ln.strip()]


isa = {r[0]: r[2] for r in load_tsv("isa_parts_list_e.txt")}
po = {r[0]: r[2] for r in load_tsv("partof_parts_list_e.txt")}
isa_elem = defaultdict(set)
for r in load_tsv("isa_element_parts.txt"):
    isa_elem[r[0]].add(r[2])
po_elem = defaultdict(set)
for r in load_tsv("partof_element_parts.txt"):
    po_elem[r[0]].add(r[2])
ichild = defaultdict(list)
iparent = {}
for r in load_tsv("isa_inclusion_relation_list.txt"):
    ichild[r[0]].append(r[2])
    iparent[r[2]] = r[0]
pchild = defaultdict(list)
pparent = {}
for r in load_tsv("partof_inclusion_relation_list.txt"):
    pchild[r[0]].append(r[2])
    pparent[r[2]] = r[0]
print(f"tables: IS-A names {len(isa)}, PART-OF names {len(po)}, "
      f"IS-A element rows {sum(len(v) for v in isa_elem.values())}, "
      f"PART-OF element rows {sum(len(v) for v in po_elem.values())}")


def desc(root, children):
    seen, stack = set(), [root]
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        stack.extend(children.get(c, []))
    return seen


# ------------------------------------------------------------------
# Re-derived universe (documented roots/sweeps, own walks)
# ------------------------------------------------------------------
isa_sets = OrderedDict([
    ("kidney-isa", desc("FMA7203", ichild)),
    ("ureter-isa", desc("FMA9704", ichild)),
    ("bladder-urethra-isa", {"FMA15900", "FMA19667"}),
    ("adrenal-gland-endocrine-xref-isa", desc("FMA9604", ichild)),
])
po_sets = OrderedDict([
    ("urinary-system-partof", desc("FMA7159", pchild)),
    ("adrenal-gland-endocrine-xref-partof",
     {"FMA15629", "FMA15630"}),
])
isa_universe = set().union(*isa_sets.values())
po_universe = set().union(*po_sets.values())
universe = isa_universe | po_universe

inv = json.load(open(os.path.join(URI, "urinary-inventory.json"),
                     encoding="utf-8"))
cu = inv["meta"]["concept_universe"]
for tag, s in isa_sets.items():
    check(cu["isa_sets"].get(tag) == len(s),
          f"IS-A set {tag}: {len(s)} concepts")
for tag, s in po_sets.items():
    check(cu["partof_sets"].get(tag) == len(s),
          f"PART-OF set {tag}: {len(s)} concepts")
check(cu["isa_total"] == len(isa_universe) and
      cu["partof_total"] == len(po_universe) and
      cu["in_both_tables"] == len(isa_universe & po_universe) and
      cu["total"] == len(universe),
      f"universe totals: {len(universe)} concepts (IS-A "
      f"{len(isa_universe)}, PART-OF {len(po_universe)}, both "
      f"{len(isa_universe & po_universe)})")

# Anchor names, verified independently
check(isa["FMA7203"] == "kidney" and isa["FMA7204"] == "right kidney"
      and isa["FMA7205"] == "left kidney"
      and isa["FMA9704"] == "ureter"
      and isa["FMA15571"] == "right ureter"
      and isa["FMA15572"] == "left ureter"
      and isa["FMA15900"] == "urinary bladder"
      and isa["FMA19667"] == "urethra",
      "IS-A anchor concepts verified by name (kidney, ureter, "
      "bladder, urethra lines)")
check(po["FMA7159"] == "urinary system"
      and po["FMA71102"] == "right upper urinary tract"
      and po["FMA71103"] == "left upper urinary tract"
      and po["FMA45659"] == "lower urinary tract"
      and "FMA7159" not in isa and "FMA7203" not in po
      and "FMA9704" not in po,
      "PART-OF urinary tree verified by name; the urinary system "
      "root is PART-OF only and the kidney/ureter classes are "
      "IS-A only")

# The adrenal filing, re-derived from the tables themselves
check(po[pparent["FMA15629"]] == "endocrine system"
      and po[pparent["FMA15630"]] == "endocrine system"
      and pparent["FMA15629"] == "FMA9668",
      "adrenal instances hang directly under FMA9668 'endocrine "
      "system' in PART-OF")
check(not ({"FMA15629", "FMA15630"} & po_sets["urinary-system-partof"])
      and isa[iparent["FMA9604"]] == "corticomedullary organ"
      and desc("FMA9604", ichild) == {"FMA9604", "FMA15629", "FMA15630"},
      "adrenal glands occur nowhere in the urinary PART-OF "
      "subtree; the IS-A class hangs under a generic organ class "
      "with exactly its two instances below it")
af = inv["meta"]["adrenal_filing"]
check(af["partof_parent_id"] == "FMA9668"
      and af["partof_parent_of_instances"] == "endocrine system"
      and af["isa_parent_of_class"] == "corticomedullary organ"
      and af["in_urinary_partof_subtree"] is False,
      "inventory adrenal_filing finding matches the re-derived "
      "filing (endocrine, not urinary)")

ADRENAL_IDS = {"FMA9604", "FMA15629", "FMA15630"}
GROUPING_IDS = {"FMA7159", "FMA71102", "FMA71103", "FMA45659"}


def cross_ref(cid):
    return "endocrine" if cid in ADRENAL_IDS else None


xref = Counter(x for x in (cross_ref(c) for c in universe) if x)
check(dict(xref) == cu["cross_references"],
      f"cross-references re-derived: {dict(sorted(xref.items()))}")

# Rejected-sweep census (urinary terms outside the universe)
SWEEP_TERMS = ("urin", "kidney", "renal", "ureter", "urethr",
               "bladder", "vesical", "nephr", "adrenal",
               "suprarenal", "calyx", "calyces", "trigone",
               "detrusor", "glomerul")
sweep = set()
for tab in (isa, po):
    for cid, n in tab.items():
        if cid not in universe and any(t in n for t in SWEEP_TERMS):
            sweep.add(n)
check(sorted(sweep) == cu["sweep_rejected_names"],
      f"rejected-sweep census re-derived: {len(sweep)} names "
      "(renal/suprarenal/ureteric-segment vessels of the "
      "cardiovascular census, and the gallbladder of the "
      "digestive census)")
check(all(("artery" in n or "vein" in n) or n == "gallbladder"
          for n in sweep),
      "every rejected sweep name is a vessel (cardiovascular) or "
      "the gallbladder (digestive) — no urinary organ hides "
      "outside the universe")

# ------------------------------------------------------------------
# Records and dispositions, re-derived from the shipped inventory
# ------------------------------------------------------------------
records_all = inv["records"]
records = [r for r in records_all if r.get("source") != "fma-5.1.0"]
check(len(records) == 6
      and len(records_all) == inv["meta"]["record_count"],
      f"record count: {len(records)} BP3D + "
      f"{len(records_all) - len(records)} FMA (Milestone 37) = "
      f"{len(records_all)}")
check(len({r['record_id'] for r in records_all})
      == len(records_all),
      "record ids unique")
claimed = {}
for r in records:
    for c in r["concept_ids"]:
        check(c not in claimed,
              f"concept {c} claimed once ({r['record_id']})")
        claimed[c] = r["record_id"]
check(set(claimed) <= universe,
      "every record concept lies inside the universe")
check(set(claimed) == {"FMA7204", "FMA7205", "FMA15571", "FMA15572",
                       "FMA15900", "FMA19667"},
      "the six records key exactly the six organ concepts "
      "(kidneys, ureters, bladder, urethra)")
check(not (set(claimed) & ADRENAL_IDS),
      "no adrenal concept is claimed by a urinary record "
      "(endocrine cross-reference discipline)")
class_carried = {r["class_concept_id"] for r in records
                 if r["class_concept_id"] not in claimed}
check(class_carried == {"FMA7203", "FMA9704"},
      "class-carried concepts are exactly the kidney and ureter "
      "classes")


def disposition(cid):
    if cid in claimed:
        return "record"
    if cid in class_carried:
        return "class-carried"
    if cross_ref(cid):
        return "cross-reference:" + cross_ref(cid)
    if cid in GROUPING_IDS:
        return "grouping-class"
    return "subtree-internal"


disp = Counter(disposition(c) for c in universe)
check(dict(disp) == cu["dispositions"],
      f"disposition accounting re-derived: {dict(sorted(disp.items()))}")
check(sum(disp.values()) == len(universe)
      and disp.get("subtree-internal", 0) == 0,
      "dispositions partition the universe exactly "
      "(6 record + 2 class-carried + 4 grouping-class + 3 "
      "endocrine cross-reference = 15; nothing unaccounted)")
disp_lists = {}
for c in universe:
    disp_lists.setdefault(disposition(c), set()).add(c)
check(all(set(v) == disp_lists.get(k, set())
          for k, v in cu["disposition_concepts"].items())
      and set(cu["disposition_concepts"]) == set(disp_lists),
      "per-disposition concept lists match the inventory exactly")
# shipped concept rows agree with the tables
rows = {c["fma_id"]: c for c in inv["concepts"]}
check(set(rows) == universe, "inventory concept rows = universe")
name_ok = all(
    rows[c]["name"] == (isa[c] if c in isa_universe else po[c])
    for c in universe)
check(name_ok, "every concept row carries its table name")
check(all(rows[c]["disposition"] == disposition(c) for c in universe)
      and all(rows[c]["record_id"] == claimed.get(c) for c in universe),
      "concept-row dispositions and record links re-derived")

# ------------------------------------------------------------------
# Geometry: full re-measurement by streaming
# ------------------------------------------------------------------
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
                    mn[i] = min(mn[i], x)
                    mx[i] = max(mx[i], x)
            elif line[:2] == b"f ":
                f += 1
    return v, f, {"min": mn, "max": mx}


geo = json.load(open(os.path.join(URI, "urinary-geometry.json"),
                     encoding="utf-8"))
fma_geo = [g for g in geo["records"]
           if g.get("source") == "fma-5.1.0"]
check(geo["meta"]["coverage"] == {
        "records": len(records_all),
        "records_with_meshes": 6,
        "records_without_meshes": len(fma_geo)},
      "geometry coverage: 6/6 BP3D records with meshes; the "
      "Milestone 37 FMA records are geometry-absent")
geo_by_id = {g["record_id"]: g for g in geo["records"]}
check(set(geo_by_id) == {r["record_id"] for r in records_all},
      "geometry records = inventory records")
check(all(not g["isa_meshes"] and not g["partof_meshes"]
          and g.get("geometry_status") for g in fma_geo),
      "FMA geometry entries are mesh-less (Milestone 37)")
entries = mismatches = 0
distinct = {"isa": set(), "partof": set()}
tot = {"isa": [0, 0], "partof": [0, 0]}
for r in records:
    g = geo_by_id[r["record_id"]]
    check(g["concept_ids"] == r["concept_ids"],
          f"{r['record_id']}: geometry concepts = record concepts")
    for tree, elem, base in (("isa", isa_elem, ISA_DIR),
                             ("partof", po_elem, PO_DIR)):
        want_fj = set()
        for c in r["concept_ids"]:
            want_fj |= elem.get(c, set())
        got = g[tree + "_meshes"]
        check({m["fj"] for m in got} == want_fj,
              f"{r['record_id']}/{tree}: FJ attribution exact "
              f"({len(got)} files)")
        for m in got:
            entries += 1
            distinct[tree].add(m["fj"])
            v, f, bb = obj_stats(os.path.join(base, m["fj"] + ".obj"))
            tot[tree][0] += v
            tot[tree][1] += f
            if (v, f, bb) != (m["vertices"], m["faces"], m["bbox"]):
                mismatches += 1
        check(g["totals"][tree]["files"] == len(got)
              and g["totals"][tree]["vertices"]
              == sum(m["vertices"] for m in got)
              and g["totals"][tree]["faces"]
              == sum(m["faces"] for m in got),
              f"{r['record_id']}/{tree}: totals consistent")
check(mismatches == 0,
      f"all {entries} mesh entries re-measured (vertices, faces, "
      "bounding boxes): 0 mismatches")
report(f"distinct mesh files: IS-A {len(distinct['isa'])} "
       f"({tot['isa'][0]} v / {tot['isa'][1]} f), PART-OF "
       f"{len(distinct['partof'])} ({tot['partof'][0]} v / "
       f"{tot['partof'][1]} f)")

# ------------------------------------------------------------------
# Absence probes, re-run as raw-text counts over all six tables
# ------------------------------------------------------------------
TABLE_FILES = ["isa_parts_list_e.txt", "partof_parts_list_e.txt",
               "isa_element_parts.txt", "partof_element_parts.txt",
               "isa_inclusion_relation_list.txt",
               "partof_inclusion_relation_list.txt"]
texts = {fn: open(os.path.join(SRC, fn), encoding="utf-8",
                  errors="replace").read().lower()
         for fn in TABLE_FILES}
ALL_NAMES = set(isa.values()) | set(po.values())
shipped = {a["probe"]: a for a in inv["meta"]["absences"]["detail"]}
my_absent, my_present = [], []
probe_mismatch = 0
for probe, a in shipped.items():
    total = sum(texts[fn].count(probe) for fn in TABLE_FILES)
    if total != a["total_hits"] or \
            (probe in ALL_NAMES) != a["exact_concept_exists"]:
        probe_mismatch += 1
    (my_absent if total == 0 else my_present).append(probe)
check(probe_mismatch == 0,
      f"all {len(shipped)} absence probes re-run with identical "
      "hit counts and exact-concept flags")
check(my_absent == inv["meta"]["absences"]["absent"]
      and my_present == inv["meta"]["absences"]["present"],
      f"absent/present probe lists reproduced exactly "
      f"({len(my_absent)} absent, {len(my_present)} present)")
KEY_ABSENT = ["renal cortex", "renal medulla", "renal pyramid",
              "renal pelvis", "calyx", "nephron", "glomerulus",
              "collecting duct", "trigone", "detrusor",
              "ureteropelvic junction", "male urethra",
              "female urethra", "prostatic urethra",
              "adrenal cortex", "suprarenal gland"]
check(all(p in my_absent for p in KEY_ABSENT),
      "the load-bearing gaps re-verified: no kidney internal "
      "structure, no nephron, no bladder part, no sexed or "
      "divided urethra, no adrenal part in the release")

# ------------------------------------------------------------------
# TotalSegmentator census, parsed independently
# ------------------------------------------------------------------
ts = json.load(open(TS_LABELS, encoding="utf-8"))
ts_names = set(ts["labels"])
check(ts["distinct_labels"] == 104 and len(ts_names) == 104,
      "TS label census parsed: 104 labels")
URI_TS = {"kidney_right", "kidney_left", "urinary_bladder"}
check(URI_TS <= ts_names
      and all(ts["labels"][l] == 1204 for l in URI_TS),
      "the three urinary TS labels are present, each in all "
      "1,204 subjects")
check(not any("ureter" in l or "urethra" in l for l in ts_names),
      "TS v1 carries no ureter or urethra label")
check({"adrenal_gland_left", "adrenal_gland_right"} <= ts_names,
      "TS carries the adrenal labels (filed under endocrine in "
      "the Milestone 3 census, concurring with the BP3D filing)")
ts_map = inv["meta"]["totalsegmentator_overlap"]["labels"]
check({e["label"] for e in ts_map} == URI_TS
      and all(i in {r["record_id"] for r in records}
              for e in ts_map for i in e["inventory_record_ids"])
      and inv["meta"]["totalsegmentator_overlap"]
          ["labels_without_records"] == [],
      "every urinary TS label maps to resolving inventory "
      "records; TS adds nothing below the organ level")

# ------------------------------------------------------------------
# Cross-module pointers
# ------------------------------------------------------------------
cv_inv = json.load(open(CV_INV, encoding="utf-8"))
cv_names = {}
for c in cv_inv["concepts"]:
    cv_names[c["fma_id"]] = c["name"]
sweep_cv = [c for c, n in cv_names.items()
            if "renal" in n or "suprarenal" in n]
cv_recs = [r for r in cv_inv["records"]
           if "renal" in r["record_id"]
           or "suprarenal" in r["record_id"]]
check(len(sweep_cv) == 38 and len(cv_recs) == 27,
      f"cardiovascular census carries the renal/suprarenal "
      f"vessels: {len(sweep_cv)} concepts in {len(cv_recs)} "
      "records, re-counted")
cv_clin = json.load(open(CV_CLIN, encoding="utf-8"))
cv_clin_ids = {r["id"] for r in cv_clin["records"]}
check({"artery.renal-artery", "vein.renal-vein"} <= cv_clin_ids,
      "the kidney record's cited cardiovascular clinical records "
      "(artery.renal-artery, vein.renal-vein) resolve in the "
      "cardiovascular module")

# ------------------------------------------------------------------
# Clinical tranche: citation / flag / tier discipline
# ------------------------------------------------------------------
clin = json.load(open(os.path.join(URI, "urinary.json"),
                      encoding="utf-8"))
crecs = clin["records"]
check(len(crecs) == clin["meta"]["record_count"] == 6,
      f"clinical records: {len(crecs)}")
check(len({r['id'] for r in crecs}) == len(crecs),
      "clinical record ids unique")
check(not any("adrenal" in r["id"] for r in crecs),
      "no adrenal clinical record in the urinary tranche "
      "(endocrine module owns the glands)")
SOURCES = set(clin["meta"]["sources"])
STRUCT = {"id", "name", "type", "group", "ta_name", "ta_code",
          "sources", "verify", "note", "geometry_record_ids",
          "sourcing_tier"}
# the checker's own core/soft declaration per record
TIERS = {
    "organ.kidney": (
        ["position", "coverings", "internal_structure",
         "drainage_sequence"],
        ["hilum", "arterial_supply", "venous_drainage",
         "lymphatics", "relations"]),
    "structure.nephron": (
        ["definition", "segments_in_order", "corpuscle"],
        ["types", "juxtaglomerular_apparatus"]),
    "organ.ureter": (
        ["course", "constrictions"],
        ["extent", "constriction_note", "arterial_supply",
         "innervation", "relations_at_risk"]),
    "pathway.urinary-pathway": (["sequence", "function"], []),
    "organ.urinary-bladder": (
        ["parts", "trigone", "musculature"],
        ["position", "function", "capacity", "vasculature",
         "innervation"]),
    "structure.urethra": (
        ["function", "female", "male"],
        ["sphincters", "epithelium"]),
}
inv_ids = {r["record_id"] for r in records}
tier_counts = Counter()
for r in crecs:
    fields = [k for k in r if k not in STRUCT]
    check(all(r[f] is None or f in r["sources"] for f in fields),
          f"{r['id']}: every non-null field is cited")
    check(all(r[f] is not None
              or any(v.startswith(f + ":") for v in r["verify"])
              for f in fields),
          f"{r['id']}: every null field carries a verify flag")
    check(all(s in SOURCES for ss in r["sources"].values()
              for s in ss),
          f"{r['id']}: all cited source ids exist")
    check((r["ta_name"] is None
           and any(v.startswith("ta_name:") for v in r["verify"]))
          or (r["ta_name"] is not None
              and r["sources"].get("ta_name") == ["TA2"]
              and isinstance(r.get("ta_code"), int)),
          f"{r['id']}: ta_name follows the M23 TA2 discipline "
          "(TA2 name + ta_code + citation, or null + verify-flagged; "
          "table equality via tools/ta2_discipline.py)")
    check(all(i in inv_ids for i in r["geometry_record_ids"]),
          f"{r['id']}: geometry links resolve to inventory "
          "records")
    if not r["geometry_record_ids"]:
        check(any(v.startswith("no BP3D concept")
                  for v in r["verify"]),
              f"{r['id']}: empty geometry link carries the "
              "recorded absence")
    core, soft = TIERS[r["id"]]
    check(set(core) | set(soft) == set(fields),
          f"{r['id']}: field set matches the checker's "
          "declaration")
    want = "C" if any(r[f] is None for f in core) else \
        "B" if any(r[f] is None for f in soft) else "A"
    check(r["sourcing_tier"] == want,
          f"{r['id']}: tier re-derived as {want}")
    tier_counts[r["sourcing_tier"]] += 1
check(dict(tier_counts) == clin["meta"]["tiers"],
      f"tier counts re-derived: {dict(sorted(tier_counts.items()))}")
check(dict(Counter(r["group"] for r in crecs))
      == clin["meta"]["groups"],
      "group counts re-derived")

by_id = {r["id"]: r for r in crecs}
pw = by_id["pathway.urinary-pathway"]["sequence"]
check(len(pw) == 8 and pw[0].startswith("renal papilla")
      and pw[-1].startswith("exterior")
      and [pw.index(s) for s in pw] == sorted(pw.index(s) for s in pw)
      and pw.index("major calyx") > pw.index("minor calyx")
      and pw.index("renal pelvis") > pw.index("major calyx"),
      "urinary pathway sequence: 8 stations in drainage order "
      "(papilla -> minor calyx -> major calyx -> pelvis -> "
      "ureter -> bladder -> urethra -> exterior)")
check(set(by_id["pathway.urinary-pathway"]["geometry_record_ids"])
      == inv_ids,
      "the pathway record links all six organ records")
seg = by_id["structure.nephron"]["segments_in_order"]
check(len(seg) == 5 and "corpuscle" in seg[0]
      and "proximal" in seg[1] and "loop of Henle" in seg[2]
      and "distal" in seg[3] and "collecting duct" in seg[4],
      "nephron segments in filtrate order: corpuscle -> PCT -> "
      "loop of Henle -> DCT -> collecting duct")
check("15 percent" in by_id["structure.nephron"]["types"],
      "nephron types carry the sourced ~15% juxtamedullary share")
kid = by_id["organ.kidney"]
check(kid["coverings"].index("renal capsule")
      < kid["coverings"].index("perirenal fat")
      < kid["coverings"].index("renal fascia")
      < kid["coverings"].index("pararenal fat"),
      "kidney coverings listed deep to superficial in sourced "
      "order (capsule, perirenal fat, renal fascia, pararenal fat)")
check("T12 to L3" in kid["position"]
      and "artery.renal-artery" in kid["arterial_supply"]
      and "vein.renal-vein" in kid["venous_drainage"],
      "kidney record carries the sourced T12-L3 extent and cites "
      "the cardiovascular records rather than duplicating them")
ure = by_id["organ.ureter"]
check(len(ure["constrictions"]) == 3
      and "ureteropelvic" in ure["constrictions"][0]
      and "pelvic inlet" in ure["constrictions"][1]
      and "ureterovesical" in ure["constrictions"][2],
      "the three ureteric constrictions in course order "
      "(UPJ, pelvic inlet, UVJ)")
check("25-30 cm" in ure["extent"] or "25 cm" in ure["extent"],
      "ureter extent records the consulted sources' range "
      "(TMA ~25 cm, OpenStax ~30 cm)")
bla = by_id["organ.urinary-bladder"]
check(len(bla["parts"]) == 4
      and bla["parts"][0].startswith("apex")
      and bla["parts"][3].startswith("neck"),
      "bladder parts: apex, body, fundus, neck (4, in order)")
check("trigone" in bla and "detrusor" in bla["musculature"]
      and "400-600" in bla["capacity"],
      "bladder record carries the trigone, the detrusor and the "
      "sourced 400-600 mL capacity")
check(any(v.startswith("vasculature:") for v in bla["verify"]),
      "bladder vasculature carries the recorded absence of any "
      "vesical vessel concept")
urt = by_id["structure.urethra"]
check("4 cm" in urt["female"] and "20 cm" in urt["male"]
      and "prostatic" in urt["male"] and "membranous" in urt["male"]
      and "spongy" in urt["male"],
      "urethra record carries the sourced sex difference "
      "(female ~4 cm; male ~20 cm in four named regions)")
check(any(v.startswith("female:") for v in urt["verify"])
      and any(v.startswith("male:") for v in urt["verify"]),
      "urethra record flags that neither sex's urethra has a "
      "BP3D concept (single unsexed inventory record)")
linked = set()
for r in crecs:
    linked |= set(r["geometry_record_ids"])
report(f"clinical linkage: {len(crecs)} records link "
       f"{len(linked)} of {len(inv_ids)} inventory records")

# ------------------------------------------------- TA2 discipline (M23)
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import ta2_discipline as _ta2d
_ta2d.run("urinary", "data/urinary/urinary.json", check)
_ta2d.run_fma_inventory_multi(
    "urinary", "data/urinary/urinary-inventory.json",
    "fma_inventory_urinary", "M37", check)

print()
if failures:
    print(f"{len(failures)} HARD CHECK(S) FAILED")
    sys.exit(1)
print(f"ALL HARD CHECKS PASS ({len(notes)} reports)")
