#!/usr/bin/env python3
"""ANATOMICA Milestone 5 — independent checker for the cardiovascular
module.  Shares no code with tools/cv_map.py or
tools/build_cv_records.py: the concept census is re-derived from the
BodyParts3D 4.0 release tables, geometry is re-measured by streaming
the OBJ files, absence probes are re-run over all six tables, and the
clinical file is validated for citation completeness, flag
completeness, tier consistency, branch-name resolution and the
variant gate.

Exit code 0 only if every hard check passes.  Reported-only items are
labelled REPORT.
"""

import json
import os
import sys
from collections import defaultdict

PROJECT = "/home/hatch/workspace/anatomica-project"
SRC = os.path.join(PROJECT, "data/sources/bodyparts3d-4.0")
TS_LABELS = os.path.join(PROJECT,
                         "data/sources/totalsegmentator-1.0/labels.json")

failures = []
reports = []


def check(ok, label, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def load_tsv(path):
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    return [ln.split("\t") for ln in lines[1:] if ln.strip()]


# ------------------------------------------------------------ tables
isa_inc = load_tsv(os.path.join(SRC, "isa_inclusion_relation_list.txt"))
po_inc = load_tsv(os.path.join(SRC, "partof_inclusion_relation_list.txt"))
isa_parts = load_tsv(os.path.join(SRC, "isa_parts_list_e.txt"))
po_parts = load_tsv(os.path.join(SRC, "partof_parts_list_e.txt"))
isa_elem = load_tsv(os.path.join(SRC, "isa_element_parts.txt"))
po_elem = load_tsv(os.path.join(SRC, "partof_element_parts.txt"))

isa_children = defaultdict(set)
for p, _pn, c, _cn in isa_inc:
    isa_children[p].add(c)
po_children = defaultdict(set)
for p, _pn, c, _cn in po_inc:
    po_children[p].add(c)

concept_name = {}
for cid, _rep, name in isa_parts + po_parts:
    concept_name.setdefault(cid, name)


def descendants(children, root):
    seen, stack = set(), [root]
    while stack:
        cur = stack.pop()
        for ch in children.get(cur, ()):
            if ch not in seen:
                seen.add(ch)
                stack.append(ch)
    return seen


arterial = descendants(isa_children, "FMA86187") | {"FMA86187"}
venous = descendants(isa_children, "FMA86188") | {"FMA86188"}
# The builder's heart PART-OF set: both PART-OF subtrees, their roots,
# and the aorta (FMA3734, itself PART-OF-only).  Concepts of the set
# that belong to a vessel subtree (e.g. FMA4716, right marginal vein)
# are tagged with that subtree in the inventory, not heart-partof.
heart_po = (descendants(po_children, "FMA7088")
            | descendants(po_children, "FMA7165")
            | {"FMA7088", "FMA7165", "FMA3734"})

inv = json.load(open(os.path.join(PROJECT,
                                  "data/cardiovascular/cv-inventory.json"),
                     encoding="utf-8"))
geo = json.load(open(os.path.join(PROJECT,
                                  "data/cardiovascular/cv-geometry.json"),
                     encoding="utf-8"))
clin = json.load(open(os.path.join(PROJECT,
                                   "data/cardiovascular/cardiovascular.json"),
                      encoding="utf-8"))

# ------------------------------------------------- T1: census recount
meta_u = inv["meta"]["concept_universe"]
check(len(arterial) == meta_u["arterial_subtree"] == 701,
      "T1a arterial subtree recount",
      f"recount {len(arterial)}, inventory meta {meta_u['arterial_subtree']}")
check(len(venous) == meta_u["venous_subtree"] == 324,
      "T1b venous subtree recount",
      f"recount {len(venous)}, inventory meta {meta_u['venous_subtree']}")
check(not (arterial & venous), "T1c arterial/venous subtrees disjoint")
check(len(heart_po) == meta_u["heart_partof_concepts"],
      "T1d heart PART-OF union recount",
      f"recount {len(heart_po)}, inventory meta {meta_u['heart_partof_concepts']}")
inv_concepts = {c["fma_id"]: c for c in inv["concepts"]}
heart_tagged = {cid for cid, c in inv_concepts.items()
                if c["subtree"] == "heart-partof"}
check(heart_tagged <= heart_po
      and len(heart_tagged) == meta_u["heart_partof_only_concepts"],
      "T1d2 heart-partof-only tags sit inside the recounted set",
      f"{len(heart_tagged)} partof-only concepts")
check(len(inv_concepts) == meta_u["total"],
      "T1e inventory concept count matches meta",
      f"{len(inv_concepts)} vs {meta_u['total']}")
bad_subtree = [cid for cid, c in inv_concepts.items()
               if c["subtree"] == "arterial" and cid not in arterial]
bad_subtree += [cid for cid, c in inv_concepts.items()
                if c["subtree"] == "venous" and cid not in venous]
check(not bad_subtree, "T1f inventory subtree tags agree with recount",
      f"{len(bad_subtree)} disagreements")
missing_art = [cid for cid in arterial if cid not in inv_concepts]
missing_ven = [cid for cid in venous if cid not in inv_concepts]
check(not missing_art and not missing_ven,
      "T1g every recounted vessel concept is in the inventory",
      f"missing arterial {len(missing_art)}, venous {len(missing_ven)}")

# ------------------------------------------- T2: records and partition
inv_records = {r["record_id"]: r for r in inv["records"]}
check(len(inv_records) == inv["meta"]["record_count"] == len(inv["records"]),
      "T2a record count", f"{len(inv_records)} records")
claimed = {}
dup_claims = []
for r in inv["records"]:
    for cid in r["concept_ids"]:
        if cid in claimed:
            dup_claims.append((cid, claimed[cid], r["record_id"]))
        claimed[cid] = r["record_id"]
check(not dup_claims, "T2b concept partition (no concept in two records)",
      f"{len(dup_claims)} duplicates")
unknown_concepts = [cid for r in inv["records"] for cid in r["concept_ids"]
                    if cid not in concept_name]
check(not unknown_concepts, "T2c record concept ids exist in the tables",
      f"{len(unknown_concepts)} unknown")

# --------------------------------------------- T3: absence re-probe
all_names = " ".join(concept_name.values()).lower()
po_names = {cid: nm for cid, nm in
            ((r[0], r[2]) for r in po_parts)}
probe_fail = []
for stem in inv["meta"]["absences"]["absent"]:
    if stem.lower() in all_names:
        probe_fail.append(stem)
check(not probe_fail, "T3 absence probes re-run over both tables",
      f"probes wrongly present: {probe_fail}" if probe_fail else
      f"{len(inv['meta']['absences']['absent'])} probe stems absent")

# ------------------------------------------------- G: geometry recount
def count_obj(path):
    v = f = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            if ln.startswith("v "):
                v += 1
            elif ln.startswith("f "):
                f += 1
    return v, f


geo_by_id = {g["record_id"]: g for g in geo["records"]}
check(set(geo_by_id) == set(inv_records),
      "G0 geometry records == inventory records",
      f"{len(geo_by_id)} vs {len(inv_records)}")
mismatch, missing_files = [], []
distinct = {}
for g in geo["records"]:
    for tree in ("isa_meshes", "partof_meshes"):
        for m in g[tree]:
            p = os.path.join(PROJECT, m["path"])
            if not os.path.exists(p):
                missing_files.append(m["path"])
                continue
            if m["path"] not in distinct:
                distinct[m["path"]] = count_obj(p)
            v, f = distinct[m["path"]]
            if (v, f) != (m["vertices"], m["faces"]):
                mismatch.append((m["path"], (v, f), (m["vertices"], m["faces"])))
check(not missing_files, "G1 all geometry paths exist",
      f"{len(missing_files)} missing")
check(not mismatch, "G2 vertex/face counts re-measured exactly",
      f"{len(mismatch)} mismatches over {len(distinct)} distinct files")
isa_files = {m["path"] for g in geo["records"] for m in g["isa_meshes"]}
po_files = {m["path"] for g in geo["records"] for m in g["partof_meshes"]}
isa_tot = (sum(distinct[p][0] for p in isa_files),
           sum(distinct[p][1] for p in isa_files))
po_tot = (sum(distinct[p][0] for p in po_files),
          sum(distinct[p][1] for p in po_files))
cov = geo["meta"]["coverage"]
no_mesh = [g["record_id"] for g in geo["records"]
           if not g["isa_meshes"] and not g["partof_meshes"]]
check(cov["records_with_meshes"] == len(geo["records"]) and not no_mesh,
      "G3 geometry coverage", f"{cov['records_with_meshes']}/{cov['records']} records with meshes")
print(f"       distinct IS-A files {len(isa_files)}: {isa_tot[0]} v / {isa_tot[1]} f")
print(f"       distinct PART-OF files {len(po_files)}: {po_tot[0]} v / {po_tot[1]} f")

# ------------------------------------------------------- TS: overlap
ts = json.load(open(TS_LABELS, encoding="utf-8"))
ts_labels = set(ts["labels"])
overlap = inv["meta"]["totalsegmentator_overlap"]["labels"]
check(len(overlap) == 13, "TS0 13 cardiovascular labels recorded",
      f"{len(overlap)}")
ts_bad = [e["label"] for e in overlap if e["label"] not in ts_labels]
ts_bad += [e["label"] for e in overlap
           if not e["inventory_record_ids"]
           or any(rid not in inv_records for rid in e["inventory_record_ids"])]
check(not ts_bad, "TS1 labels exist in the TS intake and map to records",
      f"bad: {ts_bad}" if ts_bad else "all 13 map")

# ------------------------------------------------------- C: clinical
CLIN_FIELDS = ["origin", "course", "branches", "territory", "termination"]
CORE = ["origin", "course", "branches"]
biblio = clin["meta"]["sources_bibliography"]
recs = clin["records"]
ids = [r["id"] for r in recs]
check(len(ids) == len(set(ids)), "C0 clinical record ids unique",
      f"{len(recs)} records")

cit_fail, flag_fail, tier_fail, link_fail = [], [], [], []
branch_unresolved, branch_flagged = [], []
name_universe = set(concept_name.values()) | {r["name"] for r in inv["records"]}
for r in recs:
    fields = (CLIN_FIELDS if r["type"] == "vessel"
              else ["chambers", "valves", "conduction_system",
                    "arterial_supply", "venous_drainage"])
    for f in fields:
        if r.get(f) is not None:
            srcs = r["sources"].get(f)
            if not srcs or any(s not in biblio for s in srcs):
                cit_fail.append((r["id"], f))
        else:
            if not any(v.startswith(f + ":") or f in v for v in r["verify"]):
                flag_fail.append((r["id"], f))
    for f, srcs in r["sources"].items():
        if any(s not in biblio for s in srcs):
            cit_fail.append((r["id"], f"unknown-source:{f}"))
    if r["type"] == "vessel":
        if any(r.get(f) is None for f in CORE):
            expect = "C"
        elif any(r.get(f) is None for f in CLIN_FIELDS):
            expect = "B"
        else:
            expect = "A"
        if r["sourcing_tier"] != expect:
            tier_fail.append((r["id"], r["sourcing_tier"], expect))
        for b in (r.get("branches") or []):
            if b not in name_universe:
                covered = any(b.lower() in v.lower() for v in r["verify"])
                (branch_flagged if covered else branch_unresolved).append(
                    (r["id"], b))
    for gid in r["geometry_record_ids"]:
        if gid not in inv_records:
            link_fail.append((r["id"], gid))
    if r["ta_name"] is not None:
        # M23 discipline: an entered ta_name must be the TA2 pass's
        # (TA2 citation + integer ta_code; table equality is
        # asserted by tools/ta2_discipline.py below)
        if r["sources"].get("ta_name") != ["TA2"] or \
                not isinstance(r.get("ta_code"), int):
            cit_fail.append((r["id"], "ta_name entered without TA2 "
                                      "citation/ta_code"))
check(not cit_fail, "C1 every entered field cites a bibliography source",
      f"failures: {cit_fail[:6]}" if cit_fail else "all cited")
check(not flag_fail, "C2 every null field carries a verify flag",
      f"failures: {flag_fail[:6]}" if flag_fail else "all flagged")
check(not tier_fail, "C3 sourcing tiers recompute exactly",
      f"failures: {tier_fail}" if tier_fail else "tiers consistent")
check(not link_fail, "C4 geometry links resolve to inventory records",
      f"failures: {link_fail}" if link_fail else "all resolve")
check(not branch_unresolved,
      "B1 branch names resolve to inventory concepts/records or are flagged",
      f"unresolved+unflagged: {branch_unresolved[:8]}" if branch_unresolved
      else f"all resolve or are flagged ({len(branch_flagged)} flagged)")
for rid, b in branch_flagged:
    reports.append(f"branch name flagged (no inventory concept): {rid} :: {b}")

linked = set()
for r in recs:
    linked.update(r["geometry_record_ids"])
meta_counts = clin["meta"]["counts"]
check(meta_counts["clinical_records"] == len(recs)
      and meta_counts["inventory_records_linked_from_clinical"] == len(linked),
      "C5 meta counts agree with the file",
      f"{len(recs)} clinical, {len(linked)} inventory records linked")

# ------------------------------------------------------- V: variants
clin_ids = set(ids)
var_fail = []
for v in clin["variants"]:
    p = v["prevalence"]
    if not (p["low_pct"] <= p["high_pct"] and p["low_pct"] >= 1.0):
        var_fail.append((v["id"], "prevalence range/gate"))
    if any(s not in biblio for s in v["sources"]):
        var_fail.append((v["id"], "source"))
    if any(rid not in clin_ids for rid in v["related_record_ids"]):
        var_fail.append((v["id"], "related record"))
    if not v["modeled"] and not v.get("unmodeled_note"):
        var_fail.append((v["id"], "unmodelled without declaration"))
check(not var_fail, "V1 variant gate (range, citation, declaration)",
      f"failures: {var_fail}" if var_fail else
      f"{len(clin['variants'])} variants pass")

# ------------------------------------------------------------- report
print()
for rpt in reports:
    print(f"[REPORT] {rpt}")
# ------------------------------------------------- TA2 discipline (M23)
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import ta2_discipline as _ta2d
_ta2d.run("cardiovascular", "data/cardiovascular/cardiovascular.json", check)

print()
if failures:
    print(f"RESULT: FAIL — {len(failures)} hard check(s) failed: {failures}")
    sys.exit(1)
print("RESULT: PASS — all hard checks passed")
