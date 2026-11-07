#!/usr/bin/env python3
"""ANATOMICA Milestone 40 — cross-system inventory<->geometry
attribution sweep (read-only).

The Milestone 40 regression gate, generalised. For every
record in every system's inventory, the BP3D 4.0 element
tables (the ground truth for concept->mesh attribution)
imply an expected FJ set per tree. The shipped geometry must
agree with that derivation under the partition rule:

  * BP3D-partition records: shipped FJ set == derivation.
  * FMA-partition records (source "fma-5.1.0"): shipped set
    is empty (concept-only records); the derivation over
    their concepts must also be empty, except for collisions
    adjudicated in ADJUDICATED below — an FMA concept that
    BP3D in fact carries. A collision is not an error to
    silence: it means a concept-only record names a concept
    a cleared geometry source carries, and it must be
    adjudicated explicitly (as the deferent-duct pair was at
    Milestone 40) before this sweep passes again.

The skeletal module predates the inventory schema: its
geometry records are keyed by a single fma_id and carry no
FMA partition, so the derivation runs over that one concept
per record.

Exit 0 iff every system is consistent. Run:
python3 tools/attribution_sweep.py
"""

import glob
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources", "bodyparts3d-4.0")

# Adjudicated at Milestone 40 (see MILESTONE-40.md): BP3D
# carries the deferent duct under the FMA preferred name,
# which Milestone 14's Latin-keyed probes never matched;
# Milestone 38 intaken the pair as concept-only FMA records
# and they stay concept-only until a geometry-intake
# decision re-files them.
ADJUDICATED = {
    "repro.left-deferent-duct": {"isa": {"FJ3135"},
                                 "partof": set()},
    "repro.right-deferent-duct": {"isa": {"FJ3140"},
                                  "partof": set()},
}

SYSTEMS = ["muscular", "cardiovascular", "nervous",
           "respiratory", "digestive", "urinary", "lymphatic",
           "endocrine", "reproductive", "integumentary"]


def load_elem(fn):
    d = defaultdict(set)
    with open(os.path.join(SRC, fn), encoding="utf-8",
              errors="replace") as fh:
        lines = fh.read().splitlines()
    for ln in lines[1:]:
        p = ln.split("\t")
        if len(p) >= 3:
            d[p[0]].add(p[2])
    return d


def main():
    isa_elem = load_elem("isa_element_parts.txt")
    po_elem = load_elem("partof_element_parts.txt")
    trees = (("isa", isa_elem, "isa_meshes"),
             ("partof", po_elem, "partof_meshes"))
    failures = 0

    def derivation(concepts):
        out = {}
        for tree, elem, _key in trees:
            s = set()
            for c in concepts:
                s |= elem.get(c, set())
            out[tree] = s
        return out

    for system in SYSTEMS:
        inv_p = glob.glob(os.path.join(
            ROOT, "data", system, "*inventory*.json"))[0]
        geo_p = glob.glob(os.path.join(
            ROOT, "data", system, "*geometry*.json"))[0]
        inv = json.load(open(inv_p))
        geo = json.load(open(geo_p))
        grec = {r["record_id"]: r for r in geo["records"]}
        bad, coll = [], []
        for r in inv["records"]:
            rid = r["record_id"]
            g = grec.get(rid)
            if g is None:
                bad.append((rid, "no geometry entry"))
                continue
            deriv = derivation(r.get("concept_ids", []))
            shipped = {t: {m["fj"] for m in g.get(k, [])}
                       for t, _e, k in trees}
            if r.get("source") == "fma-5.1.0":
                if shipped["isa"] or shipped["partof"]:
                    bad.append((rid, "FMA record carries "
                                     "meshes"))
                if deriv["isa"] or deriv["partof"]:
                    if ADJUDICATED.get(rid) == deriv:
                        coll.append((rid, "adjudicated"))
                    else:
                        coll.append((rid, "UNADJUDICATED"))
            elif shipped != deriv:
                bad.append((rid, "shipped != derivation"))
        status = "OK" if not bad and \
            all(c[1] == "adjudicated" for c in coll) else "FAIL"
        if status == "FAIL":
            failures += 1
        print(f"{system}: {len(inv['records'])} records, "
              f"drift={bad[:3]} collisions={coll} -> {status}")

    # Skeletal: pre-inventory schema, keyed by fma_id, no
    # FMA partition.
    geo = json.load(open(os.path.join(
        ROOT, "data", "skeletal", "skeleton-geometry.json")))
    bad = []
    for r in geo["records"]:
        deriv = derivation([r["fma_id"]])
        shipped = {t: {m["fj"] for m in r[k]}
                   for t, _e, k in trees}
        if shipped != deriv:
            bad.append(r["record_id"])
    status = "OK" if not bad else "FAIL"
    if bad:
        failures += 1
    print(f"skeletal: {len(geo['records'])} records "
          f"(fma_id-keyed), drift={bad[:3]} -> {status}")

    print("SWEEP:", "ALL SYSTEMS CONSISTENT" if not failures
          else f"{failures} SYSTEM(S) INCONSISTENT")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
