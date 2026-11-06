#!/usr/bin/env python3
"""ANATOMICA assembly checker — Milestone 3 (independent of the assembler).

Verifies data/skeletal/skeleton-assembled.json against the Milestone-2
geometry file and the measured constants in tools/register_sketch.md,
using a different computation path than the assembler where possible
(bounding boxes are re-derived by transforming the *stored* M2 source
boxes corner-wise — valid because the conversion is an axis permutation
with sign flips — instead of streaming vertices).

Checks:
  C1  exactly the 199 geometry-bearing records are present;
  C2  every assembled bbox equals the corner-transformed M2 source bbox;
  C3  whole-body bounds: height equals the measured source z-span
      (1706.75 mm = 170.675 cm; register_sketch union), width/depth the
      measured x/y spans (647.85 / 254.05 mm);
  C4  left/right mirror symmetry of paired records (bbox mirrored across
      x=0 vs the opposite record's bbox; worst deviation reported,
      declared tolerance 1.0 cm);
  C5  vertical sanity: frontal bone entirely above both calcanei;
      the records owning the global y-min / y-max are a toe bone and a
      skull bone respectively;
  C6  no NaN/Inf anywhere;
  C7  hyoid de-duplication took effect (assembled vertices = one copy).

Stdlib only. Exit 0 iff all checks pass.
"""
import json
import math
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TOL = 1e-6
MIRROR_TOL_CM = 1.0


def conv(x, y, z):
    return (-x * 0.1, z * 0.1, -y * 0.1)


def transform_bbox(bb):
    a = conv(*bb["min"])
    b = conv(*bb["max"])
    return {"min": [min(a[i], b[i]) for i in range(3)],
            "max": [max(a[i], b[i]) for i in range(3)]}


def main():
    geom = json.load(open(os.path.join(ROOT, "data", "skeletal", "skeleton-geometry.json")))
    asm = json.load(open(os.path.join(ROOT, "data", "skeletal", "skeleton-assembled.json")))
    fails = []

    def report(ok, label, detail=""):
        print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
        if not ok:
            fails.append(label)

    grec = {r["record_id"]: r for r in geom["records"]}
    arec = {r["record_id"]: r for r in asm["records"]}
    with_geom = {rid for rid, r in grec.items() if r["isa_meshes"] or r["partof_meshes"]}

    # C1
    report(set(arec) == with_geom and len(arec) == 199,
           "C1 record set", f"assembled={len(arec)} geometry-bearing={len(with_geom)}")

    # C2
    worst = 0.0
    for rid, r in arec.items():
        g = grec[rid]
        src = g["bbox_isa"] if r["source_tree"] == "isa" else g["bbox_partof"]
        exp = transform_bbox(src)
        for side in ("min", "max"):
            for i in range(3):
                worst = max(worst, abs(exp[side][i] - r["bbox_canonical_cm"][side][i]))
    report(worst <= TOL, "C2 bboxes == corner-transformed M2 boxes", f"worst diff {worst:.2e} cm")

    # C3
    umin = [min(r["bbox_canonical_cm"]["min"][i] for r in arec.values()) for i in range(3)]
    umax = [max(r["bbox_canonical_cm"]["max"][i] for r in arec.values()) for i in range(3)]
    span = [umax[i] - umin[i] for i in range(3)]
    exp_span = [64.785, 170.675, 25.405]  # register_sketch union spans, mm x 0.1
    ok = all(abs(span[i] - exp_span[i]) < 0.01 for i in range(3))
    report(ok, "C3 whole-body bounds",
           f"width(x)={span[0]:.3f} cm, height(y)={span[1]:.3f} cm, depth(z)={span[2]:.3f} cm "
           f"(expected {exp_span}); union min={['%.3f' % v for v in umin]} max={['%.3f' % v for v in umax]}")

    # C4
    pairs = []
    for rid in arec:
        if rid.endswith("_right"):
            left = rid[:-len("_right")] + "_left"
            if left in arec:
                pairs.append((left, rid))
    worst_pair, worst_dev = None, 0.0
    devs = []
    for left, right in pairs:
        lb = arec[left]["bbox_canonical_cm"]
        rb = arec[right]["bbox_canonical_cm"]
        mirrored = {"min": [-rb["max"][0], rb["min"][1], rb["min"][2]],
                    "max": [-rb["min"][0], rb["max"][1], rb["max"][2]]}
        dev = max(abs(mirrored[s][i] - lb[s][i]) for s in ("min", "max") for i in range(3))
        devs.append((dev, left, right))
        if dev > worst_dev:
            worst_dev, worst_pair = dev, (left, right)
    devs.sort(reverse=True)
    report(worst_dev < MIRROR_TOL_CM, "C4 mirror symmetry",
           f"{len(pairs)} pairs; worst {worst_pair} dev {worst_dev:.4f} cm; "
           f"next: {[(d[1][:-5], round(d[0], 4)) for d in devs[1:4]]}")

    # C5
    fr = arec["frontal"]["bbox_canonical_cm"]
    ok = True
    detail = f"frontal y [{fr['min'][1]:.2f}, {fr['max'][1]:.2f}]"
    for cid in ("calcaneus_right", "calcaneus_left"):
        cb = arec[cid]["bbox_canonical_cm"]
        detail += f"; {cid} y [{cb['min'][1]:.2f}, {cb['max'][1]:.2f}]"
        ok = ok and fr["min"][1] > cb["max"][1]
    ymin_owner = min(arec, key=lambda r: arec[r]["bbox_canonical_cm"]["min"][1])
    ymax_owner = max(arec, key=lambda r: arec[r]["bbox_canonical_cm"]["max"][1])
    detail += f"; global y-min owner {ymin_owner}, y-max owner {ymax_owner}"
    ok = ok and ("toe" in ymin_owner or "phalanx" in ymin_owner) and ymax_owner in (
        "parietal_right", "parietal_left", "frontal")
    report(ok, "C5 vertical sanity (skull top, feet bottom)", detail)

    # C6
    bad = [rid for rid, r in arec.items()
           if any(not math.isfinite(v) for s in ("min", "max") for v in r["bbox_canonical_cm"][s])]
    report(not bad, "C6 no NaN/Inf", f"bad={bad}")

    # C7
    hy = arec["hyoid"]
    report(hy["totals"]["vertices"] * 2 == grec["hyoid"]["totals"]["isa"]["vertices"]
           and hy["totals"]["files"] == 1,
           "C7 hyoid de-duplicated",
           f"assembled {hy['totals']['vertices']} v / {hy['totals']['files']} file vs M2 isa "
           f"{grec['hyoid']['totals']['isa']['vertices']} v / {grec['hyoid']['totals']['isa']['files']} files")

    print(f"\n{'ALL CHECKS PASS' if not fails else 'FAILURES: ' + ', '.join(fails)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
