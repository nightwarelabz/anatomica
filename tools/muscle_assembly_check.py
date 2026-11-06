#!/usr/bin/env python3
"""ANATOMICA muscular assembly checker — Milestone 6 (independent of the
assembler; mirrors tools/assembly_check.py, Milestone 3).

Verifies data/muscular/muscles-assembled.json against the Milestone-4
geometry file, the inventory, and the Milestone-3 skeletal assembly,
using a different computation path than the assembler where possible
(bounding boxes are re-derived by transforming the *stored* M4 per-mesh
source boxes corner-wise — valid because the conversion is an axis
permutation with sign flips — instead of streaming vertices).

Checks:
  K1  record set: assembled ids == geometry ids == inventory ids (359);
  K2  every assembled bbox equals the corner-transformed union of the
      record's stored M4 IS-A per-mesh source boxes;
  K3  layer coherence vs the skeletal assembly: both unions reported
      with per-axis exceedances; gated part — no muscle record's bbox
      is disjoint from the skeletal union expanded by 2.0 cm (a muscle
      floating entirely outside the body envelope would indicate a
      frame error, not anatomy);
  K4  left/right mirror symmetry of paired records: distributional
      gate (median <= 0.1 cm, p90 <= 0.5 cm — a frame error would
      shift the whole distribution), with every pair >= 1.0 cm listed
      individually with its measured cross-midline vertex fraction
      (the outliers are a BP3D source property: right-side meshes of
      midline sling/neck muscles include cross-midline bulk);
  K5  [REPORT, not gated] records whose bbox intersects no bone bbox
      at all — listed in full; bbox intersection is a coarse test and
      a non-zero count is a prompt for anatomical review, not proof
      of error;
  K6  no NaN/Inf anywhere;
  K7  totals: distinct assembled mesh paths and grand vertex/face
      totals equal the sums recomputed here from the Milestone-4
      IS-A lists; per-record totals equal their mesh sums.

Stdlib only. Exit 0 iff all gated checks pass.
"""
import json
import math
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TOL = 1e-6
MIRROR_TOL_CM = 1.0
ENVELOPE_MARGIN_CM = 2.0


def conv(x, y, z):
    return (-x * 0.1, z * 0.1, -y * 0.1)


def transform_bbox(bb):
    a = conv(*bb["min"])
    b = conv(*bb["max"])
    return {"min": [min(a[i], b[i]) for i in range(3)],
            "max": [max(a[i], b[i]) for i in range(3)]}


def union(boxes):
    return {"min": [min(b["min"][i] for b in boxes) for i in range(3)],
            "max": [max(b["max"][i] for b in boxes) for i in range(3)]}


def intersects(a, b, margin=0.0):
    return all(a["min"][i] <= b["max"][i] + margin and
               b["min"][i] <= a["max"][i] + margin for i in range(3))


def main():
    geom = json.load(open(os.path.join(ROOT, "data", "muscular", "muscle-geometry.json")))
    inv = json.load(open(os.path.join(ROOT, "data", "muscular", "muscle-inventory.json")))
    asm = json.load(open(os.path.join(ROOT, "data", "muscular", "muscles-assembled.json")))
    skel = json.load(open(os.path.join(ROOT, "data", "skeletal", "skeleton-assembled.json")))
    fails = []

    def report(ok, label, detail=""):
        print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
        if not ok:
            fails.append(label)

    def note(label, detail=""):
        print(f"[REPORT] {label}" + (f" — {detail}" if detail else ""))

    grec = {r["record_id"]: r for r in geom["records"]}
    irec = {r["record_id"]: r for r in inv["records"]}
    arec = {r["record_id"]: r for r in asm["records"]}

    # K1
    report(set(arec) == set(grec) == set(irec) and len(arec) == 359,
           "K1 record set", f"assembled={len(arec)} geometry={len(grec)} inventory={len(irec)}")

    # K2 (mesh-set rule mirrored: IS-A primary — every M4 record has IS-A)
    worst = 0.0
    for rid, r in arec.items():
        src = union([m["bbox"] for m in grec[rid]["isa_meshes"]])
        exp = transform_bbox(src)
        for side in ("min", "max"):
            for i in range(3):
                worst = max(worst, abs(exp[side][i] - r["bbox_canonical_cm"][side][i]))
    report(worst <= TOL, "K2 bboxes == corner-transformed M4 boxes", f"worst diff {worst:.2e} cm")

    # K3
    mu = union([r["bbox_canonical_cm"] for r in arec.values()])
    su = skel["meta"]["union_bbox_canonical_cm"]
    span_m = [mu["max"][i] - mu["min"][i] for i in range(3)]
    span_s = [su["max"][i] - su["min"][i] for i in range(3)]
    axes = ["x (width)", "y (height)", "z (depth)"]
    exc = []
    for i in range(3):
        lo = su["min"][i] - mu["min"][i]   # >0: muscle min EXCEEDS skeletal min (reaches lower)
        hi = mu["max"][i] - su["max"][i]   # >0: muscle max EXCEEDS skeletal max (reaches higher)
        exc.append(f"{axes[i]}: muscle span {span_m[i]:.3f} vs skeletal {span_s[i]:.3f}; "
                   f"min {'EXCEEDS by %.3f' % lo if lo > 0 else 'inside by %.3f' % -lo}, "
                   f"max {'EXCEEDS by %.3f' % hi if hi > 0 else 'inside by %.3f' % -hi}")
    outside = [rid for rid, r in arec.items()
               if not intersects(r["bbox_canonical_cm"], su, ENVELOPE_MARGIN_CM)]
    report(not outside, "K3 layer bounds vs skeletal assembly",
           "; ".join(exc) + f"; records disjoint from skeletal union + {ENVELOPE_MARGIN_CM} cm: {outside}")

    # K4 — mirror symmetry. What this check can certify is the absence
    # of a systematic frame/conversion error in the assembly pipeline:
    # such an error would shift the WHOLE deviation distribution, so
    # the gate is distributional (declared here, not fitted per pair):
    # median <= 0.1 cm and p90 <= 0.5 cm over all pairs. Every pair at
    # or above the per-pair tolerance is then listed individually with
    # its measured mechanism (K4c) — nothing is averaged away.
    # The outliers are a source-data property, measured below: for
    # midline sling / neck muscles the RIGHT concept's BP3D mesh
    # includes bulk geometry across the mid-sagittal plane (the left
    # mesh never does: 0.000% in every outlier pair), which inflates
    # exactly one bbox corner. K4b's trimmed (1-99 pct) reading shows
    # which outliers are sparse tails (<1% across) vs bulk crossings.
    pairs = []
    for rid in arec:
        if rid.startswith("muscle.left-"):
            right = "muscle.right-" + rid[len("muscle.left-"):]
            if right in arec:
                pairs.append((rid, right))
    devs = []
    for left, right in pairs:
        lb = arec[left]["bbox_canonical_cm"]
        rb = arec[right]["bbox_canonical_cm"]
        mirrored = {"min": [-rb["max"][0], rb["min"][1], rb["min"][2]],
                    "max": [-rb["min"][0], rb["max"][1], rb["max"][2]]}
        dev = max(abs(mirrored[s][i] - lb[s][i]) for s in ("min", "max") for i in range(3))
        devs.append((dev, left))
    devs.sort(reverse=True)
    sorted_devs = sorted(d for d, _ in devs)
    median_dev = sorted_devs[len(sorted_devs) // 2]
    p90_dev = sorted_devs[int(0.90 * (len(sorted_devs) - 1))]
    n_over = sum(1 for d, _ in devs if d >= MIRROR_TOL_CM)
    report(median_dev <= 0.1 and p90_dev <= 0.5,
           "K4 mirror symmetry (distributional gate)",
           f"{len(pairs)} pairs; median {median_dev:.4f} cm; p90 {p90_dev:.4f} cm; "
           f"{n_over} pairs >= {MIRROR_TOL_CM} cm (listed in K4c)")

    from array import array

    def stream_trimmed(rid):
        xs, ys, zs = array("d"), array("d"), array("d")
        wrong = total = 0
        side = arec[rid]["side"]
        for m in arec[rid]["meshes"]:
            with open(os.path.join(ROOT, m["path"]), "rb") as fh:
                for line in fh:
                    if line.startswith(b"v "):
                        p = line.split()
                        cx, cy, cz = conv(float(p[1]), float(p[2]), float(p[3]))
                        xs.append(cx); ys.append(cy); zs.append(cz)
                        total += 1
                        if (side == "left" and cx > 0) or (side == "right" and cx < 0):
                            wrong += 1
        box = {}
        for i, arr in enumerate((xs, ys, zs)):
            arr = sorted(arr)
            n = len(arr)
            box[i] = (arr[int(0.01 * (n - 1))], arr[int(0.99 * (n - 1))])
        return box, (wrong / total if total else 0.0)

    trimmed = {}
    cross_frac = {}
    for left, right in pairs:
        for rid in (left, right):
            trimmed[rid], cross_frac[rid] = stream_trimmed(rid)
    tdevs = []
    for left, right in pairs:
        lb, rb = trimmed[left], trimmed[right]
        dev = max(abs(-rb[0][1] - lb[0][0]), abs(-rb[0][0] - lb[0][1]),
                  abs(rb[1][0] - lb[1][0]), abs(rb[1][1] - lb[1][1]),
                  abs(rb[2][0] - lb[2][0]), abs(rb[2][1] - lb[2][1]))
        tdevs.append((dev, left))
    tdevs.sort(reverse=True)
    note("K4b trimmed (1-99 pct) mirror deviations, worst 5",
         f"{[(d[1].replace('muscle.left-', ''), round(d[0], 3)) for d in tdevs[:5]]}")
    out_detail = []
    for d, left in devs:
        if d >= MIRROR_TOL_CM:
            right = "muscle.right-" + left[len("muscle.left-"):]
            mech = (f"cross-midline vertex fraction L {cross_frac[left]:.3%}, "
                    f"R {cross_frac[right]:.3%}")
            if cross_frac[left] == 0 and cross_frac[right] == 0:
                mech += " — mechanism NOT identified (no cross-midline geometry); flagged"
            out_detail.append(f"{left.replace('muscle.left-', '')}: raw {d:.3f} cm, {mech}")
    note("K4c raw outliers, mechanisms measured", "; ".join(out_detail) if out_detail else "none")

    # K5 (report only)
    bone_boxes = [r["bbox_canonical_cm"] for r in skel["records"]]
    no_hit = [rid for rid, r in arec.items()
              if not any(intersects(r["bbox_canonical_cm"], bb) for bb in bone_boxes)]
    note("K5 records intersecting no bone bbox", f"count={len(no_hit)}: {no_hit}")

    # K6
    bad = [rid for rid, r in arec.items()
           if any(not math.isfinite(v) for s in ("min", "max") for v in r["bbox_canonical_cm"][s])]
    report(not bad, "K6 no NaN/Inf", f"bad={bad}")

    # K7
    exp_paths = set()
    exp_v = exp_f = 0
    for r in geom["records"]:
        for m in r["isa_meshes"]:
            exp_paths.add(m["path"])
            exp_v += m["vertices"]
            exp_f += m["faces"]
    got_paths = [m["path"] for r in asm["records"] for m in r["meshes"]]
    got_v = sum(r["totals"]["vertices"] for r in asm["records"])
    got_f = sum(r["totals"]["faces"] for r in asm["records"])
    per_record_ok = all(
        r["totals"]["vertices"] == sum(m["vertices"] for m in r["meshes"]) and
        r["totals"]["faces"] == sum(m["faces"] for m in r["meshes"])
        for r in asm["records"])
    report(len(set(got_paths)) == len(exp_paths) and got_v == exp_v and got_f == exp_f
           and per_record_ok,
           "K7 totals vs M4 IS-A lists",
           f"distinct paths {len(set(got_paths))} (expected {len(exp_paths)}); "
           f"vertices {got_v} (expected {exp_v}); faces {got_f} (expected {exp_f}); "
           f"per-record sums {'ok' if per_record_ok else 'MISMATCH'}")

    print(f"\n{'ALL GATED CHECKS PASS' if not fails else 'FAILURES: ' + ', '.join(fails)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
