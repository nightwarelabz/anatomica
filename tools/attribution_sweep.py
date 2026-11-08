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
    Milestone 63 (2026-11-08 geometry ruling) resolved both
    standing adjudications by intake:
      - the deferent-duct pair is CLAIMED: shipped must now
        EQUAL the pinned derivation exactly;
      - the 19 nervous records in ZA_CLAIMED gained derived
        Z-Anatomy Tier B geometry (not a BP3D derivation —
        the element-table derivation over their concepts is
        empty and must stay empty): shipped must equal the
        pinned derived set exactly.
    Any other FMA record carrying meshes, or any unpinned
    derivation, fails the sweep.

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
# Milestone 38 intaken the pair as concept-only FMA records.
# CLAIMED at Milestone 63 (2026-11-08 geometry ruling): the
# pair now carries geometry, and this pin is the required
# shipped state — shipped must equal the derivation below
# exactly, in both trees.
ADJUDICATED = {
    "repro.left-deferent-duct": {"isa": {"FJ3135"},
                                 "partof": set()},
    "repro.right-deferent-duct": {"isa": {"FJ3140"},
                                  "partof": set()},
}

# Milestone 63 Tier B intake (see MILESTONE-63.md and
# data/sources/z-anatomy-derived/intake-manifest.json): these
# 19 nervous FMA records carry derived Z-Anatomy geometry
# (ZA-* ids), placed by the Milestone 34 brain-assembly
# transform — not BP3D meshes, so the element-table derivation
# over their concepts is empty and must stay empty; shipped
# must equal the pinned derived set exactly. No other FMA
# record in any system may carry meshes.
ZA_CLAIMED = {
    "nerve.left-abducens-nerve":
        {"isa": {"ZA-Abducens_nerve_(VI).l"}, "partof": set()},
    "nerve.right-abducens-nerve":
        {"isa": {"ZA-Abducens_nerve_(VI).r"}, "partof": set()},
    "nerve.left-facial-nerve":
        {"isa": {"ZA-Facial_nerve_(VII).l"}, "partof": set()},
    "nerve.right-facial-nerve":
        {"isa": {"ZA-Facial_nerve_(VII).r"}, "partof": set()},
    "nerve.falx-cerebri":
        {"isa": {"ZA-Falx_cerebri"}, "partof": set()},
    "nerve.left-glossopharyngeal-nerve":
        {"isa": {"ZA-Glossopharyngeal_nerve_(IX).l"},
         "partof": set()},
    "nerve.right-glossopharyngeal-nerve":
        {"isa": {"ZA-Glossopharyngeal_nerve_(IX).r"},
         "partof": set()},
    "nerve.left-hypoglossal-nerve":
        {"isa": {"ZA-Hypoglossal_nerve_(XII).l"}, "partof": set()},
    "nerve.right-hypoglossal-nerve":
        {"isa": {"ZA-Hypoglossal_nerve_(XII).r"}, "partof": set()},
    "nerve.left-maxillary-nerve":
        {"isa": {"ZA-Maxillary_nerve.l"}, "partof": set()},
    "nerve.right-maxillary-nerve":
        {"isa": {"ZA-Maxillary_nerve.r"}, "partof": set()},
    "nerve.left-oculomotor-nerve":
        {"isa": {"ZA-Oculomotor_nerve_(III).l"}, "partof": set()},
    "nerve.right-oculomotor-nerve":
        {"isa": {"ZA-Oculomotor_nerve_(III).r"}, "partof": set()},
    "nerve.left-olfactory-nerve":
        {"isa": {"ZA-Olfactory_nerve_(I).l"}, "partof": set()},
    "nerve.right-olfactory-nerve":
        {"isa": {"ZA-Olfactory_nerve_(I).r"}, "partof": set()},
    "nerve.left-trigeminal-nerve":
        {"isa": {"ZA-Trigeminal_nerve_(V).l"}, "partof": set()},
    "nerve.right-trigeminal-nerve":
        {"isa": {"ZA-Trigeminal_nerve_(V).r"}, "partof": set()},
    "nerve.left-vestibulocochlear-nerve":
        {"isa": {"ZA-Vestibulocochlear_nerve_(VIII).l"},
         "partof": set()},
    "nerve.right-vestibulocochlear-nerve":
        {"isa": {"ZA-Vestibulocochlear_nerve_(VIII).r"},
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
                if rid in ADJUDICATED:
                    # Milestone 63 claim: shipped must equal
                    # the pinned derivation exactly.
                    if shipped == ADJUDICATED[rid] \
                            and deriv == ADJUDICATED[rid]:
                        coll.append((rid, "adjudicated-claimed"))
                    else:
                        coll.append((rid, "UNADJUDICATED"))
                elif rid in ZA_CLAIMED:
                    # Milestone 63 Tier B: shipped must equal
                    # the pinned derived set; the BP3D
                    # derivation must stay empty.
                    if shipped == ZA_CLAIMED[rid] \
                            and not deriv["isa"] \
                            and not deriv["partof"]:
                        coll.append((rid, "adjudicated-tier-b"))
                    else:
                        coll.append((rid, "UNADJUDICATED"))
                else:
                    if shipped["isa"] or shipped["partof"]:
                        bad.append((rid, "FMA record carries "
                                         "meshes"))
                    if deriv["isa"] or deriv["partof"]:
                        coll.append((rid, "UNADJUDICATED"))
            elif shipped != deriv:
                bad.append((rid, "shipped != derivation"))
        status = "OK" if not bad and \
            all(c[1] in ("adjudicated", "adjudicated-claimed",
                         "adjudicated-tier-b")
                for c in coll) else "FAIL"
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
