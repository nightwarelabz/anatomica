#!/usr/bin/env python3
"""zanatomy_register.py — derive (or refute) a Z-Anatomy → Anatomography
registration from shared landmark structures, with measured residuals.

Milestone 34, bar 2. Method, deliberately conservative:

- Landmarks are individual bones whose identity is certain in both
  sources (named identically in the Z-Anatomy template and in the
  BodyParts3D 4.0 concept tables the project resolved at Milestone 2).
- A similarity transform (Umeyama: uniform scale + rotation +
  translation) is fitted on the TRAIN landmarks' vertex centroids
  only — all of them axial (skull, vertebral column, sacrum, pelvis),
  where the two models' poses agree by construction.
- The transform is then judged on HELD-OUT landmarks it never saw
  (limb and girdle bones): centroid residuals, and full surface
  residuals (each held-out bone's Z-Anatomy vertices, transformed,
  measured against the BodyParts3D mesh of the same bone).
- No hand adjustment anywhere: if the numbers fail the stated
  threshold, the derivation fails, and this tool says so.

Inputs: an extractor output directory (tools/zanatomy_extract.py)
with one .npy of world-space vertices ( metres, Blender frame ) per
landmark, and the project's Milestone 2 geometry resolution for the
BodyParts3D side (millimetres, BP3D source frame).

  python3 tools/zanatomy_register.py EXTRACT_DIR skeleton-geometry.json \
      PROJECT_ROOT report.json
"""
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

# ZA object name -> BP3D concept name (identity certain in both)
TRAIN = {
    "Frontal bone": "frontal bone",
    "Parietal bone.r": "right parietal bone",
    "Parietal bone.l": "left parietal bone",
    "Occipital bone": "occipital bone",
    "Temporal bone.r": "right temporal bone",
    "Temporal bone.l": "left temporal bone",
    "Mandible": "mandible",
    "Sphenoid bone": "sphenoid bone",
    "Atlas (C1)": "atlas",
    "Axis (C2)": "axis",
    "Vertebra C4": "fourth cervical vertebra",
    "Vertebra T6": "sixth thoracic vertebra",
    "Vertebra L3": "third lumbar vertebra",
    "Sacrum": "sacrum",
    "Hip bone.r": "right hip bone",
    "Hip bone.l": "left hip bone",
}
HELD_OUT = {
    "Femur.r": "right femur",
    "Femur.l": "left femur",
    "Humerus.r": "right humerus",
    "Humerus.l": "left humerus",
    "Tibia.r": "right tibia",
    "Fibula.r": "right fibula",
    "Radius.r": "right radius",
    "Ulna.r": "right ulna",
    "Scapula.r": "right scapula",
    "Clavicle.r": "right clavicle",
    "Calcaneus.r": "right calcaneus",
    "Calcaneus.l": "left calcaneus",
    "Patella.r": "right patella",
    "First rib.r": "right first rib",
}

# Stated pass threshold (report §method): held-out centroid RMS and
# surface statistics, in millimetres. Justification: the nerves this
# registration would carry are 1-5 mm structures running against bone;
# the BP3D 99% meshes' own facet scale on large bones is ~1-3 mm, so a
# registration whose held-out surface mean is <= 1 mm and p95 <= 3 mm
# is at/below the resolution of the data it would be combined with.
THRESH = {"centroid_rms_mm": 2.0, "surface_mean_mm": 1.0, "surface_p95_mm": 3.0}


def load_obj_verts(path):
    vs = []
    with open(path) as fh:
        for line in fh:
            if line.startswith("v "):
                p = line.split()
                vs.append((float(p[1]), float(p[2]), float(p[3])))
    return np.array(vs, dtype=np.float64)


def bp3d_verts(record, root):
    files = record.get("isa_meshes") or record.get("partof_meshes") or []
    arrs = [load_obj_verts(os.path.join(root, m["path"])) for m in files]
    return np.concatenate(arrs) if arrs else np.empty((0, 3))


def umeyama(src, dst):
    """Similarity transform mapping src -> dst (least squares)."""
    n = len(src)
    ms, md = src.mean(0), dst.mean(0)
    cs, cd = src - ms, dst - md
    cov = (cd.T @ cs) / n
    U, D, Vt = np.linalg.svd(cov)
    S = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        S[2, 2] = -1
    R = U @ S @ Vt
    var = (cs ** 2).sum() / n
    scale = float((D * np.diag(S)).sum() / var)
    t = md - scale * (R @ ms)
    return scale, R, t


def apply(pts, scale, R, t):
    return scale * (pts @ R.T) + t


def surface_stats(za_pts_mm, bp_pts, rng):
    """Distance from transformed ZA vertices to the BP3D point set."""
    tree = cKDTree(bp_pts)
    sample = za_pts_mm
    if len(sample) > 20000:
        sample = sample[rng.choice(len(sample), 20000, replace=False)]
    d, _ = tree.query(sample, workers=4)
    return {"n": int(len(d)), "mean": float(d.mean()),
            "median": float(np.median(d)), "p95": float(np.percentile(d, 95)),
            "max": float(d.max())}


def main():
    extract_dir, geo_path, root, out_path = sys.argv[1:5]
    geo = json.load(open(geo_path))
    by_concept = {r["concept_name"].lower(): r for r in geo["records"]
                  if r.get("concept_name")}
    rng = np.random.default_rng(34)

    def za(name):
        fn = os.path.join(extract_dir, name.replace("/", "_").replace(" ", "_") + ".npy")
        return np.load(fn)

    def bp(name):
        return bp3d_verts(by_concept[name], root)

    pairs = {}
    for group, table in (("train", TRAIN), ("held_out", HELD_OUT)):
        for za_name, bp_name in table.items():
            pairs[za_name] = {"group": group, "bp3d_concept": bp_name,
                              "za_centroid": za(za_name).mean(0),
                              "bp_centroid": bp(bp_name).mean(0)}
    src = np.array([pairs[k]["za_centroid"] for k in TRAIN])
    dst = np.array([pairs[k]["bp_centroid"] for k in TRAIN])
    scale, R, t = umeyama(src, dst)

    report = {"scale_za_to_bp3d": scale,
              "rotation": [[float(x) for x in row] for row in R],
              "translation_mm": [float(x) for x in t],
              "threshold": THRESH, "landmarks": {}}
    for name, p in pairs.items():
        pred = apply(p["za_centroid"][None, :], scale, R, t)[0]
        resid = float(np.linalg.norm(pred - p["bp_centroid"]))
        entry = {"group": p["group"], "bp3d_concept": p["bp3d_concept"],
                 "centroid_residual_mm": resid}
        report["landmarks"][name] = entry
    train_rms = float(np.sqrt(np.mean(
        [report["landmarks"][k]["centroid_residual_mm"] ** 2 for k in TRAIN])))
    held = [k for k in HELD_OUT if k in pairs]
    held_rms = float(np.sqrt(np.mean(
        [report["landmarks"][k]["centroid_residual_mm"] ** 2 for k in held])))
    report["train_centroid_rms_mm"] = train_rms
    report["held_out_centroid_rms_mm"] = held_rms

    surf_means, surf_p95s = [], []
    for name in held:
        za_mm = apply(za(name), scale, R, t)
        stats = surface_stats(za_mm, bp(pairs[name]["bp3d_concept"]), rng)
        report["landmarks"][name]["surface"] = stats
        surf_means.append(stats["mean"])
        surf_p95s.append(stats["p95"])
    # two train bones get surface stats too, as a same-mesh sanity floor
    for name in ("Frontal bone", "Sacrum"):
        za_mm = apply(za(name), scale, R, t)
        report["landmarks"][name]["surface"] = surface_stats(
            za_mm, bp(pairs[name]["bp3d_concept"]), rng)
    report["held_out_surface_mean_of_means_mm"] = float(np.mean(surf_means))
    report["held_out_surface_worst_p95_mm"] = float(np.max(surf_p95s))
    report["verdict"] = {
        "centroid_rms_pass": held_rms <= THRESH["centroid_rms_mm"],
        "surface_mean_pass": report["held_out_surface_mean_of_means_mm"] <= THRESH["surface_mean_mm"],
        "surface_p95_pass": report["held_out_surface_worst_p95_mm"] <= THRESH["surface_p95_mm"],
    }
    report["verdict"]["registration_clears"] = all(report["verdict"].values())
    with open(out_path, "w") as fh:
        json.dump(report, fh, indent=1)
    print(json.dumps({k: report[k] for k in
                      ("scale_za_to_bp3d", "train_centroid_rms_mm",
                       "held_out_centroid_rms_mm",
                       "held_out_surface_mean_of_means_mm",
                       "held_out_surface_worst_p95_mm", "verdict")}, indent=1))
    print("rotation:\n", np.round(R, 4), "\ntranslation(mm):", np.round(t, 2))


def _robust_trim(pts):
    if len(pts) < 50:
        return pts
    lo = np.percentile(pts, 0.1, axis=0)
    hi = np.percentile(pts, 99.9, axis=0)
    pad = 0.1 * (hi - lo)
    keep = np.all((pts >= lo - pad) & (pts <= hi + pad), axis=1)
    return pts[keep] if keep.sum() >= 50 else pts


def _umeyama_fixed(src, dst, fixed_scale):
    n = len(src)
    ms, md = src.mean(0), dst.mean(0)
    cs, cd = src - ms, dst - md
    cov = (cd.T @ cs) / n
    U, D, Vt = np.linalg.svd(cov)
    S = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        S[2, 2] = -1
    R = U @ S @ Vt
    return fixed_scale, R, md - fixed_scale * (R @ ms)


def _icp(za, bp, init, rng, fixed_scale=None, iters=60):
    tree = cKDTree(bp)
    work = za
    if len(work) > 4000:
        work = work[rng.choice(len(work), 4000, replace=False)]
    s, R, t = init
    if fixed_scale is not None:
        s = fixed_scale
        t = bp.mean(0) - s * (R @ work.mean(0))
    pts = apply(work, s, R, t)
    prev = np.inf
    for _ in range(iters):
        d, idx = tree.query(pts, workers=4)
        if fixed_scale is not None:
            s, R, t = _umeyama_fixed(work, bp[idx], s)
        else:
            s, R, t = umeyama(work, bp[idx])
        pts = apply(work, s, R, t)
        if abs(prev - d.mean()) < 1e-5:
            break
        prev = d.mean()
    return s, R, t


def _eval(za_eval, bp, s, R, t, rng):
    moved = apply(za_eval, s, R, t)
    return surface_stats(moved, bp, rng)


def icp_main():
    """Per-landmark ICP: the per-part registration route, measured.

      python3 tools/zanatomy_register.py icp EXTRACT_DIR \
          skeleton-geometry.json PROJECT_ROOT GLOBAL_REPORT PAIR_SCALE OUT

    For every landmark bone: a free-scale ICP and a fixed-scale ICP
    (scale = the model-pair scale from the correspondence audit),
    each ALSO in split-half form — fit on a random half of the
    Z-Anatomy vertices, residuals measured on the held-out half — so
    the numbers state how a per-part registration (the Milestone 3
    pattern) would generalise, bone by bone.
    """
    _, _mode, extract_dir, geo_path, root, global_path, pair_scale, out_path = \
        sys.argv
    pair_scale = float(pair_scale)
    geo = json.load(open(geo_path))
    by_concept = {r["concept_name"].lower(): r for r in geo["records"]
                  if r.get("concept_name")}
    glob_rep = json.load(open(global_path))
    init = (glob_rep["scale_za_to_bp3d"], np.array(glob_rep["rotation"]),
            np.array(glob_rep["translation_mm"]))
    rng = np.random.default_rng(34)

    def za(name):
        fn = os.path.join(extract_dir,
                          name.replace("/", "_").replace(" ", "_") + ".npy")
        arr = np.load(fn)
        arr = arr[np.abs(arr).max(1) < 2] if len(arr) else arr
        return _robust_trim(arr)

    out = {"pair_scale": pair_scale, "bones": {}}
    for group, table in (("train", TRAIN), ("held_out", HELD_OUT)):
        for za_name, bp_name in table.items():
            z, b = za(za_name), bp3d_verts(by_concept[bp_name], root)
            entry = {"group": group, "bp3d_concept": bp_name,
                     "za_verts": int(len(z)), "bp_verts": int(len(b))}
            perm = rng.permutation(len(z))
            half = len(z) // 2
            zA, zB = z[perm[:half]], z[perm[half:]]
            for label, fixed in (("free", None), ("fixed", pair_scale)):
                s, R, t = _icp(z, b, init, rng, fixed_scale=fixed)
                entry[label] = {"scale": float(s),
                                "full": _eval(z, b, s, R, t, rng)}
                sh, Rh, th = _icp(zA, b, init, rng, fixed_scale=fixed)
                entry[label + "_splithalf"] = {
                    "scale": float(sh), "held_half": _eval(zB, b, sh, Rh, th, rng)}
            out["bones"][za_name] = entry
            f = entry["fixed_splithalf"]["held_half"]
            print(f"{za_name:18s} fixed split-half held: mean {f['mean']:.3f} "
                  f"median {f['median']:.3f} p95 {f['p95']:.3f} "
                  f"(free scale {entry['free']['scale']:.1f})")
    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "icp":
        icp_main()
    else:
        main()
