#!/usr/bin/env python3
"""ANATOMICA Milestone 4 — independent checker for the muscular module.

Deliberately shares NO code with tools/muscle_map.py or
tools/build_muscle_records.py: it re-reads the raw BodyParts3D 4.0
release tables and the OBJ files on disk and re-derives every claim.

Checks:
  T1  muscle concept universe re-censused from the IS-A inclusion
      table (four subtrees), compared with the inventory meta;
  T2  every concept id referenced by the inventory exists in the
      release tables and inside the re-censused universe; no concept
      is claimed by two inventory records (exact partition);
  G1  every mesh path in muscle-geometry.json exists on disk;
  G2  vertex/face counts re-measured by streaming every distinct OBJ
      file, compared per file and in total with the geometry file;
  C1  every non-null clinical field in muscles.json carries a
      per-field source citation that resolves to the bibliography;
  C2  every null clinical field carries an explicit verify flag;
  C3  innervation nerve names resolve against concept names in the
      release tables, or are reported as flagged findings;
  X1  no duplicate record ids in any of the three module files;
  X2  cross-file linkage: geometry ids == inventory ids; clinical
      geometry links reference real inventory records.

Run:  python3 tools/muscle_check.py        (exit 1 on any FAIL)
"""

import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources", "bodyparts3d-4.0")
FAILURES = []
INFOS = []

def ok(cond, label, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label +
          ((" — " + detail) if detail else ""))
    if not cond:
        FAILURES.append(label)

def info(msg):
    print("INFO  " + msg)
    INFOS.append(msg)

def read_tsv(path):
    with open(path, encoding="utf-8") as f:
        rows = [ln.rstrip("\n").split("\t") for ln in f if ln.strip()]
    return rows[0], rows[1:]

# ---------------------------------------------------------------- tables
_, isa_parts = read_tsv(os.path.join(SRC, "isa_parts_list_e.txt"))
_, po_parts = read_tsv(os.path.join(SRC, "partof_parts_list_e.txt"))
_, incl = read_tsv(os.path.join(SRC, "isa_inclusion_relation_list.txt"))

concept_name = {}
for cid, _rep, name in isa_parts + po_parts:
    concept_name.setdefault(cid, name)
children = defaultdict(list)
for pid, _pn, cid, _cn in incl:
    children[pid].append(cid)

def subtree(root_id):
    seen, stack = set(), [root_id]
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        stack.extend(children.get(c, []))
    return seen

name_to_id = {}
for cid, nm in concept_name.items():
    name_to_id.setdefault(nm, cid)

ROOTS = {
    "muscle_organ_subtree": "FMA5022",
    "zone_subtree": "FMA10474",
    "head_subtree": "FMA85453",
    "musculature_set_subtree": name_to_id.get("musculature"),
}
subs = {k: subtree(v) for k, v in ROOTS.items() if v}
universe = set().union(*subs.values())
overlap = len(universe) != sum(len(s) for s in subs.values())

inv = json.load(open(os.path.join(ROOT, "data/muscular/muscle-inventory.json")))
meta_u = inv["meta"]["concept_universe"]
ok(not overlap, "T1a the four muscle subtrees are disjoint")
ok(len(universe) == meta_u["total"],
   "T1b concept universe re-censused from the inclusion table",
   f"checker={len(universe)} inventory_meta={meta_u['total']}")
for k in ("muscle_organ_subtree", "zone_subtree", "head_subtree"):
    ok(len(subs[k]) == meta_u[k], f"T1c subtree size: {k}",
       f"checker={len(subs[k])} inventory_meta={meta_u[k]}")
info(f"musculature set subtree re-censused at {len(subs['musculature_set_subtree'])} concepts")

# ---------------------------------------------------------------- inventory
claimed = {}
bad_ids = []
for r in inv["records"]:
    for cid in r["concept_ids"]:
        if cid not in concept_name or cid not in universe:
            bad_ids.append((r["record_id"], cid))
        if cid in claimed:
            bad_ids.append((r["record_id"], cid + " (also in " +
                            claimed[cid] + ")"))
        claimed[cid] = r["record_id"]
    for cid in [r.get("class_concept_id")] + r.get("zone_concept_ids", []):
        if cid and (cid not in concept_name or cid not in universe):
            bad_ids.append((r["record_id"], cid))
ok(not bad_ids, "T2 inventory concept ids exist in the tables, lie in "
                "the universe, and partition it without overlap",
   f"violations={bad_ids[:5]}" if bad_ids else
   f"{len(claimed)} instance concepts claimed by "
   f"{len(inv['records'])} records")
ok(len(inv["records"]) == inv["meta"]["record_count"],
   "T2b inventory record count matches its meta",
   f"records={len(inv['records'])}")

# ---------------------------------------------------------------- geometry
geo = json.load(open(os.path.join(ROOT, "data/muscular/muscle-geometry.json")))
recount = {}
missing = []
for g in geo["records"]:
    for kind in ("isa_meshes", "partof_meshes"):
        for m in g[kind]:
            p = os.path.join(ROOT, m["path"])
            if not os.path.exists(p):
                missing.append(m["path"])
                continue
            if m["path"] not in recount:
                v = f = 0
                with open(p, encoding="utf-8", errors="replace") as fh:
                    for ln in fh:
                        if ln.startswith("v "):
                            v += 1
                        elif ln.startswith("f "):
                            f += 1
                recount[m["path"]] = (v, f)
            if recount[m["path"]] != (m["vertices"], m["faces"]):
                missing.append(m["path"] + " (count mismatch)")
ok(not missing, "G1/G2 every geometry mesh exists on disk and its "
                "vertex/face counts re-measure exactly",
   f"violations={missing[:5]}" if missing else
   f"{len(recount)} distinct OBJ files re-counted")
tot_v = sum(v for v, _ in recount.values())
tot_f = sum(f for _, f in recount.values())
cov = geo["meta"]["coverage"]
isa_paths = {m["path"] for g in geo["records"] for m in g["isa_meshes"]}
isa_v = sum(recount[p][0] for p in isa_paths)
isa_f = sum(recount[p][1] for p in isa_paths)
ok(cov["records"] == len(geo["records"]) and
   cov["records_with_meshes"] == len(geo["records"]) and
   cov["records_without_meshes"] == 0,
   "G2b coverage meta consistent: every inventory record has meshes",
   f"{cov['records_with_meshes']}/{cov['records']} records with meshes")
info(f"G2c checker-measured IS-A totals: {len(isa_paths)} distinct "
     f"files, {isa_v} vertices, {isa_f} faces (IS-A + PART-OF paths "
     f"together: {len(recount)} files, {tot_v} vertices, {tot_f} "
     f"faces)")

# ---------------------------------------------------------------- clinical
clin = json.load(open(os.path.join(ROOT, "data/muscular/muscles.json")))
bib = set(clin["meta"]["sources_bibliography"])
inv_ids = {r["record_id"] for r in inv["records"]}
problems = []
for r in clin["records"]:
    vals = {"origin": r["origin"], "insertion": r["insertion"],
            "actions": r["actions"],
            "innervation.nerve": r["innervation"]["nerve"],
            "innervation.root_values": r["innervation"]["root_values"],
            "arterial_supply": r["arterial_supply"],
            "ta_name": r["ta_name"]}
    vfields = {v.split(":")[0].strip() for v in r["verify"]}
    for field, val in vals.items():
        present = val not in (None, [], "")
        if present:
            src = r["sources"].get(field)
            if not src:
                problems.append(f"{r['record_id']}: {field} has a value "
                                "but no source citation")
            elif src not in bib:
                problems.append(f"{r['record_id']}: {field} cites "
                                f"unknown source key {src}")
        else:
            covered = field in vfields or (
                field.startswith("innervation.") and
                "innervation" in vfields)
            if not covered:
                problems.append(f"{r['record_id']}: {field} is null "
                                "without a verify flag")
    if r["geometry"] is not None:
        for rid in r["geometry"]["inventory_record_ids"]:
            if rid not in inv_ids:
                problems.append(f"{r['record_id']}: geometry link to "
                                f"unknown inventory record {rid}")
ok(not problems, "C1/C2/X2 clinical fields: values cited, nulls "
                 "verify-flagged, geometry links valid",
   f"violations={problems[:6]}" if problems else
   f"{len(clin['records'])} records checked")

# innervation resolution against table concept names
names_lc = {n.lower() for n in concept_name.values()}
unresolved = []
resolved = 0
for r in clin["records"]:
    nerve = r["innervation"]["nerve"]
    if not nerve:
        continue
    cands = [c.strip() for c in re.split(r"[;,]", nerve) if c.strip()]
    for c in cands:
        c_clean = re.sub(r"\(.*?\)", "", c).strip().lower()
        c_clean = re.sub(r"\s+L\d.*$", "", c_clean)
        hit = (c_clean in names_lc or
               any(n == c_clean or n.endswith(" " + c_clean)
                   for n in names_lc))
        if hit:
            resolved += 1
        else:
            unresolved.append((r["record_id"], c))
info(f"C3 innervation phrases resolved against table concept names: "
     f"{resolved}; unresolved phrases: {len(unresolved)}")
from collections import Counter
phrase_counts = Counter(c for _rid, c in unresolved)
nerve_concepts = sorted(n for n in concept_name.values()
                        if "nerve" in n.lower())
info(f"C3 the release tables carry only {len(nerve_concepts)} "
     f"nerve-named concepts (mostly cranial nerves and nerve trunks); "
     f"the peripheral nerves named in the clinical records are not "
     f"concepts in BodyParts3D 4.0, so C3 resolution is reported, "
     f"not gated. Distinct unresolved phrases: "
     f"{len(phrase_counts)}")
for phrase, n in phrase_counts.most_common():
    info(f"C3 unresolved phrase x{n}: '{phrase}'")

# ---------------------------------------------------------------- ids
for label, data in (("inventory", inv), ("geometry", geo),
                    ("clinical", clin)):
    ids = [r["record_id"] for r in data["records"]]
    ok(len(ids) == len(set(ids)), f"X1 no duplicate record ids in "
                                  f"{label}", f"{len(ids)} records")
ok({g["record_id"] for g in geo["records"]} == inv_ids,
   "X2b geometry record ids == inventory record ids")

print()
print(f"SUMMARY: {len(FAILURES)} failures, {len(INFOS)} info lines")
if FAILURES:
    print("FAILED CHECKS:", FAILURES)
    sys.exit(1)
print("ALL HARD CHECKS PASS")
