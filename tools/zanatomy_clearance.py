#!/usr/bin/env python3
"""zanatomy_clearance.py — combine the two Milestone 34 bars into the
final per-object clearance list.

Inputs: the provenance table (tools/zanatomy_correspond.py), the
template census, the nervous extractor output, and the Milestone 33
inventory (the 286 FMA records that carry no geometry).

Bar 2 has exactly two measured outcomes to combine with:
- the GLOBAL similarity (tools/zanatomy_register.py) FAILED its
  held-out thresholds — it clears nothing;
- the BRAIN-ASSEMBLY similarity (pooled over the 27 individually
  measured BP3D brain objects in the correspondence run) PASSED a
  split-half held-out check (fit 14 objects, tested 13: residual
  mean 0.27 mm, p95 0.50 mm) — it clears objects that belong to that
  assembly, operationalised here as: centroid inside the matched
  brain objects' centroid bounding box expanded by 50 mm (the
  matched objects span the cranial cavity; their largest diameter
  is 125 mm, so a 50 mm margin covers member extents without
  reaching the neck). Per-object ICP fits clear the BP3D-derived
  objects individually, wherever they sit.

Tiers:
  A  clears both bars — BP3D-derived, measured per object
     (redundant for intake: the project already holds this exact
     geometry from BodyParts3D itself).
  B  clears both bars — Z-Anatomy-original (or course-consistent
     curve), attributable, inside the validated assembly region.
  C  bar 1 only — attributable, but no validated transform covers
     its location; intake would need a further derivation.
  D  clears neither — NOT separable on provenance.

The tool also reports, per tier, how many of the 286 geometry-absent
FMA records a tier's objects correspond to (name match, sided).

  python3 tools/zanatomy_clearance.py PROVENANCE_JSON CENSUS_JSON \
      INVENTORY_JSON EXTRACT_DIR... OUT_JSON
"""
import json
import os
import re
import sys

import numpy as np

ROMAN = re.compile(r"\s*\((I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\)\s*$")
REGION_MARGIN_MM = 50.0


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def main():
    prov_path, census_path, inv_path = sys.argv[1:4]
    out_path = sys.argv[-1]
    extract_dirs = sys.argv[4:-1]
    prov = json.load(open(prov_path))
    census = json.load(open(census_path))
    inv = json.load(open(inv_path))
    asm = prov["brain_assembly_transform"]
    s_a = asm["scale"]
    R_a = np.array(asm["rotation"])
    t_a = np.array(asm["translation_mm"])
    rows = {r["object"]: r for r in prov["objects"]}

    mesh_files, curve_data = {}, {}
    for d in extract_dirs:
        rep = json.load(open(os.path.join(d, "extract_report.json")))
        for name, e in rep.items():
            if e.get("file"):
                mesh_files[name] = os.path.join(d, e["file"])
            if e.get("splines"):
                curve_data[name] = e

    def centroid_bp(name, row):
        if row["type"] == "MESH" and name in mesh_files:
            za = np.load(mesh_files[name])
            za = za[np.abs(za).max(1) < 2] if len(za) else za
            if not len(za):
                return None
            c = np.median(za, axis=0)
        elif row["type"] == "CURVE" and name in curve_data:
            pts = np.concatenate([np.array(sp["points"])
                                  for sp in curve_data[name]["splines"]])
            c = pts.mean(0)
        else:
            return None
        return s_a * (R_a @ c) + t_a

    matched = [n for n, r in rows.items()
               if r["origin"] == "bp3d-derived-measured"]
    cents = {n: centroid_bp(n, rows[n]) for n in matched}
    cents = {n: c for n, c in cents.items() if c is not None}
    box_lo = np.min(np.array(list(cents.values())), axis=0) - REGION_MARGIN_MM
    box_hi = np.max(np.array(list(cents.values())), axis=0) + REGION_MARGIN_MM

    tiers = {"A": [], "B": [], "C": [], "D": []}
    for name, r in sorted(rows.items()):
        if r["kind"] != "object":
            continue
        if r["verdict"] == "NOT separable":
            tiers["D"].append(name)
        elif r["origin"].startswith("bp3d-derived"):
            tiers["A"].append(name)
        else:
            c = centroid_bp(name, r)
            inside = c is not None and bool(
                np.all(c >= box_lo) and np.all(c <= box_hi))
            r["assembly_frame_centroid_mm"] = \
                None if c is None else [round(float(x), 1) for x in c]
            r["in_assembly_region"] = inside
            tiers["B" if inside else "C"].append(name)

    # ---- correspondence to the 286 geometry-absent FMA records
    absent = [r for r in inv["records"] if r.get("geometry") == "absent"]
    by_name = {}
    for r in absent:
        by_name.setdefault(norm(r["name"]), r["record_id"])
    fma_hits = {}
    for tier, names in tiers.items():
        hits = []
        for n in names:
            r = rows[n]
            base = ROMAN.sub("", r["base"])
            cands = []
            if r.get("side"):
                cands.append(norm(f"{r['side']} {base}"))
            cands.append(norm(base))
            hit = next((by_name[c] for c in cands if c in by_name), None)
            if hit:
                hits.append({"object": n, "fma_record": hit})
        fma_hits[tier] = hits

    out = {"region_box_bp3d_mm": {"lo": [round(float(x), 1) for x in box_lo],
                                  "hi": [round(float(x), 1) for x in box_hi]},
           "region_margin_mm": REGION_MARGIN_MM,
           "assembly_held_out": asm.get("held_out"),
           "tier_counts": {k: len(v) for k, v in tiers.items()},
           "tiers": tiers,
           "fma_absent_records": len(absent),
           "fma_coverage_by_tier": {k: len(v) for k, v in fma_hits.items()},
           "fma_hits": fma_hits}
    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=1)
    print("tiers:", out["tier_counts"])
    print("FMA geometry-absent records:", len(absent),
          "| covered by tier:", out["fma_coverage_by_tier"])
    print("tier B objects:")
    for n in tiers["B"]:
        print("   ", n, "|", rows[n]["origin"], "|", rows[n]["type"])


if __name__ == "__main__":
    main()
