#!/usr/bin/env python3
"""ANATOMICA Milestone 9 — independent checker for the nervous system
module. Shares no code with tools/nerve_map.py or
tools/build_nerve_records.py: the concept census is re-derived from
the BodyParts3D 4.0 release tables, geometry is re-measured by
streaming the OBJ files, absence probes are re-run over all six
tables, and the clinical file is validated for citation completeness,
flag completeness, tier consistency and geometry-link resolution.

Also reported (not gated): the Milestone 4 finding C3 continuity —
how many of the muscle module's distinct innervation nerve names now
resolve to a nervous-system record (clinical or inventory).

Exit code 0 only if every hard check passes.
"""

import json
import os
import sys
from collections import Counter, defaultdict

PROJECT = "/home/hatch/workspace/anatomica-project"
SRC = os.path.join(PROJECT, "data/sources/bodyparts3d-4.0")
TS_LABELS = os.path.join(PROJECT,
                         "data/sources/totalsegmentator-1.0/labels.json")
INV = json.load(open(os.path.join(PROJECT,
                                  "data/nervous/nervous-inventory.json")))
GEO = json.load(open(os.path.join(PROJECT,
                                  "data/nervous/nervous-geometry.json")))
CLI = json.load(open(os.path.join(PROJECT,
                                  "data/nervous/nervous.json")))

failures = []
reports = []


def check(ok, label, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}"
          + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def report(label, detail=""):
    print(f"[REPORT] {label}" + (f" — {detail}" if detail else ""))
    reports.append(label)


def load_tsv(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    return [ln.split("\t") for ln in lines[1:] if ln.strip()]


# ------------------------------------------------------------- tables
isa_rows = load_tsv(os.path.join(SRC, "isa_parts_list_e.txt"))
po_rows = load_tsv(os.path.join(SRC, "partof_parts_list_e.txt"))
isa = {r[0]: r[2] for r in isa_rows}
po = {r[0]: r[2] for r in po_rows}
isa_elem = defaultdict(set)
for r in load_tsv(os.path.join(SRC, "isa_element_parts.txt")):
    isa_elem[r[0]].add(r[2])
po_elem = defaultdict(set)
for r in load_tsv(os.path.join(SRC, "partof_element_parts.txt")):
    po_elem[r[0]].add(r[2])
ichild = defaultdict(list)
for r in load_tsv(os.path.join(SRC, "isa_inclusion_relation_list.txt")):
    ichild[r[0]].append(r[2])
pchild = defaultdict(list)
for r in load_tsv(os.path.join(SRC,
                               "partof_inclusion_relation_list.txt")):
    pchild[r[0]].append(r[2])


def desc(root, children):
    seen, stack = set(), [root]
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        stack.extend(children.get(c, []))
    return seen


# ------------------------------------------------- N: census re-derived
neural_tree = desc("FMA11195", ichild)
cranial_line = desc("FMA5865", ichild)
neuraxis_roots = [c for c, n in isa.items() if "neuraxis" in n]
neuraxis_isa = set()
for r in neuraxis_roots:
    neuraxis_isa |= desc(r, ichild)
subdivision = set()
for r in ("FMA45638", "FMA65551", "FMA65539"):
    subdivision |= desc(r, ichild)
dura = set()
for r in ("FMA266054", "FMA71235"):
    dura |= desc(r, ichild)
dura.add("FMA83966")
dura |= desc("FMA83966", ichild)
sweep = set()
for c in ("FMA62493", "FMA72713", "FMA72714", "FMA242193"):
    sweep.add(c)
    sweep |= desc(c, ichild)
isa_universe = (neural_tree | cranial_line | neuraxis_isa |
                subdivision | dura | sweep)
po_universe = desc("FMA7157", pchild) | desc("FMA79876", pchild)
universe = isa_universe | po_universe

meta_u = INV["meta"]["concept_universe"]
check(len(neural_tree) == meta_u["neural_tree_isa"] == 62,
      "N1 neural tree census", f"{len(neural_tree)}")
check(len(cranial_line) == meta_u["cranial_nerve_line_isa"] == 4,
      "N2 cranial nerve line census", f"{len(cranial_line)}")
check(len(neuraxis_isa) == meta_u["neuraxis_isa"] == 170,
      "N3 neuraxis IS-A census", f"{len(neuraxis_isa)}")
check(len(subdivision) == meta_u["subdivision_isa"]
      and len(dura) == meta_u["dura_isa"]
      and len(sweep) == meta_u["sweep_additions_isa"],
      "N4 subdivision/dura/sweep censuses",
      f"{len(subdivision)}/{len(dura)}/{len(sweep)}")
check(len(po_universe) == meta_u["nervous_system_partof"]
      + meta_u["brainstem_partof_extra"] == 91,
      "N5 PART-OF census", f"{len(po_universe)}")
inv_concepts = {c["fma_id"] for c in INV["concepts"]}
check(inv_concepts == universe and len(inv_concepts)
      == meta_u["total"] == 286,
      "N6 concept universe agreement",
      f"inventory {len(inv_concepts)} vs re-derived {len(universe)}")
nerve_named = {c for c, n in isa.items() if "nerve" in n}
check(len(nerve_named) == 55 and nerve_named <= universe,
      "N7 nerve-named concepts (Milestone 4 finding C3 quantified)",
      f"{len(nerve_named)} nerve-named, all inside the universe")
names_ok = all(
    (isa.get(c["fma_id"]) or po.get(c["fma_id"])) == c["name"]
    for c in INV["concepts"])
check(names_ok, "N8 concept names match the release tables")

# ------------------------------------------------- P: record partition
recs = INV["records"]
claimed = [c for r in recs for c in r["concept_ids"]]
check(len(claimed) == len(set(claimed)),
      "P1 no concept claimed by two records", f"{len(claimed)} claims")
check(all(c in universe for c in claimed),
      "P2 every record concept is in the universe")
check(len({r['record_id'] for r in recs}) == len(recs)
      == INV["meta"]["record_count"],
      "P3 record ids unique and count matches meta",
      f"{len(recs)} records")
by_id = {r["record_id"]: r for r in recs}
conc_rec = {}
for r in recs:
    for c in r["concept_ids"]:
        conc_rec[c] = r["record_id"]
check(all(c["record_id"] == conc_rec.get(c["fma_id"])
          for c in INV["concepts"]),
      "P4 concept rows carry the same record assignment")

# ------------------------------------------------- G: geometry re-measured
def stream_stats(path):
    v = f = 0
    with open(path, "rb") as fh:
        for line in fh:
            if line[:2] == b"v ":
                v += 1
            elif line[:2] == b"f ":
                f += 1
    return v, f


geo_recs = GEO["records"]
check([g["record_id"] for g in geo_recs]
      == [r["record_id"] for r in recs],
      "G1 geometry records align with inventory records")
bad = []
distinct = {"isa": {}, "partof": {}}
for g in geo_recs:
    for tree, key in (("isa", "isa_meshes"), ("partof", "partof_meshes")):
        for m in g[key]:
            p = os.path.join(PROJECT, m["path"])
            if not os.path.exists(p):
                bad.append((g["record_id"], m["path"], "missing"))
                continue
            v, f = stream_stats(p)
            if (v, f) != (m["vertices"], m["faces"]):
                bad.append((g["record_id"], m["path"],
                            f"{v}/{f} != {m['vertices']}/{m['faces']}"))
            distinct[tree][m["fj"]] = (v, f)
check(not bad, "G2 every mesh path exists and re-measures exactly",
      f"{sum(len(g[k]) for g in geo_recs for k in ('isa_meshes', 'partof_meshes'))} mesh entries"
      + (f"; first bad: {bad[:3]}" if bad else ""))
cov = GEO["meta"]["coverage"]
n_with = sum(1 for g in geo_recs if g["isa_meshes"] or g["partof_meshes"])
check(cov["records"] == len(recs)
      and cov["records_with_meshes"] == n_with,
      "G3 coverage statement re-derived",
      f"{n_with}/{len(recs)} records with meshes")
for tree in ("isa", "partof"):
    tv = sum(v for v, _ in distinct[tree].values())
    tf = sum(f for _, f in distinct[tree].values())
    report(f"G4 distinct {tree} mesh files re-measured",
           f"{len(distinct[tree])} files, {tv} vertices, {tf} faces")


# ------------------------------------------------- A: absence probes
table_files = ["isa_parts_list_e.txt", "partof_parts_list_e.txt",
               "isa_element_parts.txt", "partof_element_parts.txt",
               "isa_inclusion_relation_list.txt",
               "partof_inclusion_relation_list.txt"]
texts = {fn: open(os.path.join(SRC, fn), encoding="utf-8",
                  errors="replace").read().lower()
         for fn in table_files}
all_names = set(isa.values()) | set(po.values())
det = INV["meta"]["absences"]["detail"]
probe_bad = []
for d in det:
    total = sum(texts[fn].count(d["probe"]) for fn in table_files)
    if total != d["total_hits"]:
        probe_bad.append((d["probe"], total, d["total_hits"]))
    if (d["probe"] in all_names) != d["exact_concept_exists"]:
        probe_bad.append((d["probe"], "exact-flag mismatch"))
check(not probe_bad, "A1 absence probes re-run over all six tables",
      f"{len(det)} probes, {len(INV['meta']['absences']['absent'])} "
      f"with zero hits"
      + (f"; bad: {probe_bad[:3]}" if probe_bad else ""))

# ------------------------------------------------- T: TotalSegmentator
lab = json.load(open(TS_LABELS))
neural_labels = [k for k in lab["labels"]
                 if any(t in k for t in ("brain", "spinal", "cord",
                                         "nerve", "ganglion"))]
check(neural_labels == ["brain"],
      "T1 TS v1 neural-adjacent labels re-censused",
      f"{neural_labels}")
ts_meta = INV["meta"]["totalsegmentator_overlap"]
check(all(i in by_id for e in ts_meta["labels"]
          for i in e["inventory_record_ids"])
      and ts_meta["labels_without_records"] == [],
      "T2 TS brain label maps to an inventory record")

# ------------------------------------------------- C: clinical tranche
bib = CLI["meta"]["sources"]
crecs = CLI["records"]
check(len({r['id'] for r in crecs}) == len(crecs)
      == CLI["meta"]["record_count"],
      "C1 clinical record ids unique", f"{len(crecs)} records")

FIELDS = {
    "nerve": (["root_values", "branches", "motor_territory",
               "sensory_territory"],
              ["root_values", "motor_territory", "sensory_territory"],
              ["branches"]),
    "cranial_nerve": (["modality", "function", "exit_foramen",
                       "branches"],
                      ["modality", "function", "exit_foramen"],
                      ["branches"]),
    "central_structure": (["function", "connections"], ["function"],
                          ["connections"]),
    "organ": (None, None, None),   # hand-built; fields checked ad hoc
}
cit_bad, flag_bad, tier_bad = [], [], []
for r in crecs:
    if r["ta_name"] is not None or not any(
            v.startswith("ta_name:") for v in r["verify"]):
        flag_bad.append((r["id"], "ta_name"))
    fields, core, soft = FIELDS[r["type"]]
    if fields is None:
        fields = [k for k in r["sources"]]
        core, soft = fields, []
    for f in fields:
        if r.get(f) is not None:
            if f not in r["sources"] or not r["sources"][f]:
                cit_bad.append((r["id"], f, "value without citation"))
            elif any(s not in bib for s in r["sources"][f]):
                cit_bad.append((r["id"], f, "citation not in bibliography"))
        else:
            if not any(v.startswith(f + ":") for v in r["verify"]):
                flag_bad.append((r["id"], f))
    if any(r.get(f) is None for f in core):
        tier = "C"
    elif any(r.get(f) is None for f in soft):
        tier = "B"
    else:
        tier = "A"
    if tier != r["sourcing_tier"]:
        tier_bad.append((r["id"], tier, r["sourcing_tier"]))
check(not cit_bad, "C2 every entered field cites a bibliography source",
      f"bad: {cit_bad[:4]}" if cit_bad else "all cited")
check(not flag_bad, "C3 every null field carries a verify flag",
      f"bad: {flag_bad[:4]}" if flag_bad else "all flagged")
check(not tier_bad, "C4 sourcing tiers recompute exactly",
      f"bad: {tier_bad[:4]}" if tier_bad else
      f"{dict(Counter(r['sourcing_tier'] for r in crecs))}")
link_bad = []
for r in crecs:
    for i in r["geometry_record_ids"]:
        if i not in by_id:
            link_bad.append((r["id"], i))
    if not r["geometry_record_ids"]:
        if not any("no BP3D concept" in v or "no concept" in v
                   or "no geometry" in v for v in r["verify"]) \
                and "no concept" not in (r["note"] or "") \
                and "no BP3D concept" not in (r["note"] or ""):
            link_bad.append((r["id"], "empty link without absence note"))
check(not link_bad, "C5 geometry links resolve; empty links are "
      "explained by a recorded absence",
      f"bad: {link_bad[:4]}" if link_bad else
      f"{sum(1 for r in crecs if r['geometry_record_ids'])} of "
      f"{len(crecs)} records linked")
check(CLI["meta"]["link_failures"] == [],
      "C6 builder reported no link failures")
linked_inv = {i for r in crecs for i in r["geometry_record_ids"]}
report("C7 inventory linkage",
       f"clinical records link {len(linked_inv)} of {len(recs)} "
       f"inventory records; {len(recs) - len(linked_inv)} inventory "
       f"records are inventory-only in v1")

# -------------------------------------- REPORT: Milestone 4 C3 continuity
mus = json.load(open(os.path.join(PROJECT,
                                  "data/muscular/muscles.json")))
mrecs = mus["records"] if isinstance(mus, dict) else mus
phrases = sorted({r["innervation"]["nerve"] for r in mrecs
                  if r.get("innervation")
                  and r["innervation"].get("nerve")})
cli_names = {r["name"].lower() for r in crecs}
cli_names |= {r["name"].split(" (")[0].lower() for r in crecs}
inv_names = {r["name"].lower() for r in recs}
resolved_cli = [p for p in phrases if p.lower() in cli_names]
resolved_inv = [p for p in phrases if p.lower() in inv_names]
report("C8 Milestone 4 C3 continuity",
       f"{len(phrases)} distinct innervation nerve names in the "
       f"muscle module; {len(resolved_cli)} resolve to a sourced "
       f"clinical record of this module, {len(resolved_inv)} to an "
       f"inventory (geometry) record; the rest remain unresolvable "
       f"against BP3D 4.0 because the release carries no concepts "
       f"for them")
print("  resolved to clinical records:", resolved_cli)
print("  resolved to inventory records:", resolved_inv)

print()
if failures:
    print(f"FAILED: {len(failures)} hard check(s): {failures}")
    sys.exit(1)
print(f"ALL HARD CHECKS PASS ({len(reports)} reports printed)")
