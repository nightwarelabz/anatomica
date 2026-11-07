#!/usr/bin/env python3
"""zanatomy_correspond.py — per-object provenance evidence for the
Z-Anatomy nervous-system objects (Milestone 34, bar 1).

For every object in the template's 'Nervous system & Sense organs'
collection this tool assembles the evidence that can actually be
produced, object by object:

- NAME / TYPE / SIZE from the template census (tools/zanatomy_blend.py).
- BP3D PRESENCE: whether BodyParts3D 4.0 carries a mesh-bearing
  concept of the same name (crosswalk over every system's Milestone
  geometry resolution; one explicit TA2->FMA synonym is recorded in
  SYNONYMS below, no others were needed — the matcher was audited
  against token-level candidates and the misses are anatomical, not
  lexical: BP3D has no sulci, lemnisci, fasciculi or white matter).
- GEOMETRIC CORRESPONDENCE (meshes with a BP3D counterpart), two
  tests, both iterated closest-point fits initialised from the
  global registration of tools/zanatomy_register.py:
  (A) similarity ICP, scale free. A first pass over all candidates
      estimates the model-pair scale as the median fitted scale of
      the confident fits (it comes out at 1030.1 — the Z-Anatomy
      scene unit is 1/1030.1 of a BodyParts3D millimetre, i.e. the
      figure was re-scaled to ~175 cm). A 'same geometry' verdict
      requires the fitted scale to land within +/-8% of that pair
      scale: a free-scale fit that shrinks an object into a larger
      counterpart is a containment, not an identity.
  (B) rigid ICP with the scale FIXED at the pair scale — the test
      that decides small objects, whose absolute residuals are
      sub-millimetre under almost any placement.
  Both directions are measured (forward: ZA->BP3D, reverse:
  BP3D->ZA). A sided object whose forward fit is exact but whose
  reverse fit fails is a FRAGMENT of the BP3D concept; sided pairs
  are then tested jointly (union of .l + .r against the whole
  concept). Left objects are also tested under the mirror
  hypothesis (the template mirrors right meshes to the left).
- CURVE COURSE (nerve curves with a BP3D mesh counterpart — the
  cranial nerves): spline points carried by the BRAIN-ASSEMBLY
  transform (a single similarity fitted over the point clouds of
  all measured-BP3D brain objects, pooled through their per-object
  ICP correspondences); distances to the BP3D mesh are course
  evidence, indicative not probative.
- NAMED-REGION FLAGS from the upstream License.txt inclusion list
  (Dundee inner ear CC BY-NC-SA; Dundee cranial nerves CC BY;
  UW 'Brainder'/'White matter', license unstated): applied as
  suspicion, never as proof — a measured BP3D match overrides them;
  an unmatched object inside an NC-named region is NOT separable.

Classification (per object, in the emitted table):
  origin: bp3d-derived-measured | bp3d-derived-mirror-measured |
          bp3d-derived-fragment | za-original-by-elimination |
          named-third-party-region | unresolved-*
  verdict: cleanly attributable | attributable-with-stated-evidence |
           NOT separable
Bands (mm): same = mean<=1.0, p95<=2.5, reverse_mean<=2.0 (a
p95-marginal sub-band — mean<=1.0, p95<=3.0, reverse_mean<=1.0 — is
reported as 'same' with its numbers kept visible); borderline =
mean<=2.0, p95<=5.0. Borderline never rounds into a pass.

  python3 tools/zanatomy_correspond.py CENSUS_JSON EXTRACT_DIR... \
      REGISTER_JSON PROJECT_ROOT TABLE_JSON
"""
import glob
import json
import os
import re
import sys

import numpy as np
from scipy.spatial import cKDTree

MATCH_MEAN, MATCH_P95, MATCH_REV = 1.0, 2.5, 2.0
MARG_P95, MARG_REV = 3.0, 1.0
BORD_MEAN, BORD_P95 = 2.0, 5.0
SCALE_TOL = 0.08
SYNONYMS = {"aqueduct of midbrain": "cerebral aqueduct"}
INNER_EAR = re.compile(
    r"^(cochlea|vestibule)$|semicircular canal|bony labyrinth|"
    r"membranous labyrinth|cochlear duct|utricle|saccule|"
    r"endolymphatic|scala (vestibuli|tympani)|^cochlear nerve$", re.I)
WHITE_MATTER = re.compile(r"white matter of (telencephalon|cerebrum)", re.I)
CRANIAL_NERVE = re.compile(
    r"(olfactory|optic|oculomotor|trochlear|trigeminal|abducens|facial|"
    r"vestibulocochlear|glossopharyngeal|vagus|accessory|hypoglossal)"
    r" nerve", re.I)
ROMAN = re.compile(r"\s*\((I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\)\s*$")


def norm(name):
    return re.sub(r"\s+", " ", name.strip().lower())


def split_za(name):
    n = name.strip()
    side, kind = None, "object"
    m = re.search(r"\.(l|r|j|g|t|s|i|ol|or)$", n)
    if m:
        suf = m.group(1)
        n = n[:m.start()]
        if suf == "l":
            side = "left"
        elif suf == "r":
            side = "right"
        elif suf in ("j", "i"):
            kind = "marker"
        elif suf in ("g", "t", "s"):
            kind = "label"
    return n, side, kind, (n.startswith("(") or "*" in n)


def load_obj_verts(path):
    vs = []
    with open(path) as fh:
        for line in fh:
            if line.startswith("v "):
                p = line.split()
                vs.append((float(p[1]), float(p[2]), float(p[3])))
    return np.array(vs, dtype=np.float64)


def umeyama(src, dst, fixed_scale=None):
    n = len(src)
    ms, md = src.mean(0), dst.mean(0)
    cs, cd = src - ms, dst - md
    cov = (cd.T @ cs) / n
    U, D, Vt = np.linalg.svd(cov)
    S = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        S[2, 2] = -1
    R = U @ S @ Vt
    if fixed_scale is not None:
        scale = fixed_scale
    else:
        var = (cs ** 2).sum() / n
        scale = float((D * np.diag(S)).sum() / var)
    return scale, R, md - scale * (R @ ms)


def robust_trim(pts):
    """Drop garbage vertices (the template contains isolated corrupt
    points, e.g. one vertex at z=-5.7e29 in the frontal bone): keep the
    [0.1, 99.9] percentile box per axis, expanded by 10% of its range."""
    if len(pts) < 50:
        return pts
    lo = np.percentile(pts, 0.1, axis=0)
    hi = np.percentile(pts, 99.9, axis=0)
    pad = 0.1 * (hi - lo)
    keep = np.all((pts >= lo - pad) & (pts <= hi + pad), axis=1)
    return pts[keep] if keep.sum() >= 50 else pts


def icp(za_m, bp_mm, init, rng, fixed_scale=None, iters=60):
    tree = cKDTree(bp_mm)
    za = za_m
    if len(za) > 4000:
        za = za[rng.choice(len(za), 4000, replace=False)]
    s, R, t = init
    if fixed_scale is not None:
        s = fixed_scale
        # the caller's translation belongs to a different scale; solve
        # the fixed-scale translation from the centroids instead
        t = bp_mm.mean(0) - s * (R @ za.mean(0))
    pts = s * (za @ R.T) + t
    prev = np.inf
    for _ in range(iters):
        d, idx = tree.query(pts, workers=4)
        s, R, t = umeyama(za, bp_mm[idx], fixed_scale=fixed_scale)
        pts = s * (za @ R.T) + t
        if abs(prev - d.mean()) < 1e-5:
            break
        prev = d.mean()
    full = za_m
    if len(full) > 20000:
        full = full[rng.choice(len(full), 20000, replace=False)]
    pf = s * (full @ R.T) + t
    d, _ = tree.query(pf, workers=4)
    bp_s = bp_mm
    if len(bp_s) > 20000:
        bp_s = bp_s[rng.choice(len(bp_s), 20000, replace=False)]
    dr, _ = cKDTree(pf).query(bp_s, workers=4)
    return {"scale": float(s), "mean": float(d.mean()),
            "median": float(np.median(d)), "p95": float(np.percentile(d, 95)),
            "reverse_mean": float(dr.mean()),
            "reverse_p95": float(np.percentile(dr, 95)),
            "R": R, "t": t}


def pub(stats):
    if stats is None:
        return None
    return {k: stats[k] for k in
            ("scale", "mean", "median", "p95", "reverse_mean", "reverse_p95")}


def band(st):
    if st is None:
        return None
    if st["mean"] <= MATCH_MEAN and st["p95"] <= MATCH_P95 and \
            st["reverse_mean"] <= MATCH_REV:
        return "same"
    if st["mean"] <= MATCH_MEAN and st["p95"] <= MARG_P95 and \
            st["reverse_mean"] <= MARG_REV:
        return "same-marginal-p95"
    if st["mean"] <= MATCH_MEAN and st["p95"] <= MATCH_P95:
        return "forward-only"      # fragment of the counterpart
    if st["mean"] <= BORD_MEAN and st["p95"] <= BORD_P95:
        return "borderline"
    return "different"


def bezier_samples(spline, per_seg=8):
    pts = np.array(spline["points"])
    if spline["type"] != "BEZIER" or len(pts) < 2:
        return pts
    hl = np.array(spline["handle_left"])
    hr = np.array(spline["handle_right"])
    out = []
    n = len(pts) if spline.get("use_cyclic_u") else len(pts) - 1
    for i in range(n):
        j = (i + 1) % len(pts)
        p0, p1, p2, p3 = pts[i], hr[i], hl[j], pts[j]
        for k in range(per_seg):
            u = k / per_seg
            out.append(((1 - u) ** 3) * p0 + 3 * ((1 - u) ** 2) * u * p1 +
                       3 * (1 - u) * u * u * p2 + (u ** 3) * p3)
    return np.array(out)


def main():
    census_path = sys.argv[1]
    reg_path, root, out_path = sys.argv[-3], sys.argv[-2], sys.argv[-1]
    extract_dirs = sys.argv[2:-3]
    census = json.load(open(census_path))
    reg = json.load(open(reg_path))
    init = (reg["scale_za_to_bp3d"], np.array(reg["rotation"]),
            np.array(reg["translation_mm"]))
    rng = np.random.default_rng(34)

    concept_meshes = {}
    for gj in glob.glob(os.path.join(root, "data", "*", "*-geometry.json")):
        g = json.load(open(gj))
        for r in g["records"]:
            files = (r.get("isa_meshes") or []) + (r.get("partof_meshes") or [])
            if not files:
                continue
            for nm in (r.get("concept_names") or [r.get("concept_name")]):
                if nm:
                    concept_meshes.setdefault(norm(nm), []).extend(
                        os.path.join(root, m["path"]) for m in files)
    bp_cache = {}

    def bp_verts(concept):
        if concept not in bp_cache:
            bp_cache[concept] = np.concatenate(
                [load_obj_verts(p) for p in concept_meshes[concept]])
        return bp_cache[concept]

    mesh_files, curve_data = {}, {}
    for d in extract_dirs:
        rep = json.load(open(os.path.join(d, "extract_report.json")))
        for name, e in rep.items():
            if e.get("file"):
                mesh_files[name] = os.path.join(d, e["file"])
            if e.get("splines"):
                curve_data[name] = e
    objs = {o["name"]: o for o in census["objects"]}
    nerv = set(census["collections"]
               ["Scene Collection/7: Nervous system & Sense organs"])

    def concept_for(base, side):
        b = ROMAN.sub("", base)
        cands = []
        if side:
            cands.append(norm(f"{side} {b}"))
        cands += [norm(b), norm(SYNONYMS.get(norm(b), ""))]
        return next((c for c in cands if c and c in concept_meshes), None)

    # ---------- pass 1: free-scale ICP everywhere, estimate pair scale
    work = {}
    for name in sorted(nerv):
        o = objs.get(name)
        if o is None:
            continue
        base, side, kind, variant = split_za(name)
        if kind in ("marker", "label") or o["type"] == "FONT" or \
                (o["type"] == "MESH" and (o.get("verts") or 0) <= 2):
            work[name] = {"helper": True}
            continue
        w = {"base": base, "side": side, "type": o["type"],
             "variant": variant, "concept": None}
        if o["type"] == "MESH" and name in mesh_files:
            za = np.load(mesh_files[name])
            za = za[np.abs(za).max(1) < 2] if len(za) else za
            w["za"] = robust_trim(za)
            hit = concept_for(base, side)
            w["concept"] = hit
            if hit:
                w["icpA"] = icp(za, bp_verts(hit), init, rng)
                if side == "left":
                    rc = concept_for(base, "right")
                    if rc:
                        w["icpA_mirror"] = icp(za * [-1.0, 1.0, 1.0],
                                               bp_verts(rc), init, rng)
                        w["concept_right"] = rc
        work[name] = w
    confident = [w["icpA"]["scale"] for w in work.values()
                 if w.get("icpA") and band(w["icpA"]) in ("same", "same-marginal-p95")]
    pair_scale = float(np.median(confident)) if confident else init[0]

    # ---------- pass 2: fixed-scale ICP + classification
    rows = []
    asm_src, asm_dst = [], []
    for name in sorted(nerv):
        o = objs[name]
        w = work[name]
        base, side, kind, variant = split_za(name)
        row = {"object": name, "base": base, "side": side, "type": o["type"],
               "kind": "helper" if w.get("helper") else "object",
               "variant_form": variant}
        if w.get("helper"):
            row.update({"origin": "non-anatomical-helper",
                        "verdict": "not-anatomy (excluded from clearance)"})
            rows.append(row)
            continue
        named = None
        if INNER_EAR.search(base) and "nucle" not in base.lower():
            named = "inner-ear (Dundee CC BY-NC-SA named inclusion)"
        elif WHITE_MATTER.search(base):
            named = "white-matter (UW named inclusion, license unstated)"
        elif o["type"] == "CURVE" and CRANIAL_NERVE.search(base):
            named = "cranial-nerve (Dundee CC BY named inclusion)"
        row["named_region"] = named
        row["bp3d_concept"] = w.get("concept")
        if o["type"] == "MESH" and "za" in w:
            za = w["za"]
            row["verts"] = int(len(za))
            if len(za):
                span = np.percentile(za, 99.9, axis=0) - \
                    np.percentile(za, 0.1, axis=0)
                row["diameter_mm"] = float(np.linalg.norm(span) * pair_scale)
            if w.get("concept"):
                bp = bp_verts(w["concept"])
                w["icpB"] = icp(za, bp, init, rng, fixed_scale=pair_scale)
                row["icp_free"] = pub(w["icpA"])
                row["icp_fixed"] = pub(w["icpB"])
                row["band_free"] = band(w["icpA"])
                row["band_fixed"] = band(w["icpB"])
                if w["side"] == "left" and w.get("icpA_mirror"):
                    mb = icp(za * [-1.0, 1.0, 1.0], bp_verts(w["concept_right"]),
                             init, rng, fixed_scale=pair_scale)
                    row["icp_mirror_fixed"] = pub(mb)
                    row["band_mirror_fixed"] = band(mb)
                    w["icpB_mirror"] = mb
                scale_ok = abs(w["icpA"]["scale"] - pair_scale) <= \
                    SCALE_TOL * pair_scale
                sameA = row["band_free"] in ("same", "same-marginal-p95") and scale_ok
                sameB = row["band_fixed"] in ("same", "same-marginal-p95")
                sameM = row.get("band_mirror_fixed") in ("same", "same-marginal-p95")
                frag = "forward-only" in (row["band_free"], row["band_fixed"])
                if sameA or sameB:
                    row["origin"] = "bp3d-derived-measured"
                    row["verdict"] = "cleanly attributable"
                elif sameM:
                    row["origin"] = "bp3d-derived-mirror-measured"
                    row["verdict"] = "cleanly attributable"
                elif frag:
                    row["origin"] = "bp3d-derived-fragment (pending pair-union)"
                    row["verdict"] = "pending"
                elif named:
                    row["origin"] = "named-third-party-region"
                    row["verdict"] = "NOT separable"
                elif "borderline" in (row["band_free"], row["band_fixed"]):
                    row["origin"] = "unresolved-borderline-geometry"
                    row["verdict"] = "NOT separable"
                else:
                    row["origin"] = "unresolved-different-geometry"
                    row["verdict"] = "NOT separable"
                if row["verdict"] == "cleanly attributable":
                    st = w["icpB"] if sameB else w["icpA"]
                    sub = za if len(za) <= 300 else za[rng.choice(len(za), 300, replace=False)]
                    asm_src.append(sub)
                    asm_dst.append(st["scale"] * (sub @ st["R"].T) + st["t"])
            else:
                if named:
                    row["origin"] = "named-third-party-region"
                    row["verdict"] = "NOT separable"
                else:
                    row["origin"] = "za-original-by-elimination"
                    row["verdict"] = "attributable-with-stated-evidence"
        elif o["type"] == "CURVE" and name in curve_data:
            w["curve"] = curve_data[name]
            row["origin"] = "za-original-by-elimination"
            row["verdict"] = "attributable-with-stated-evidence"
        else:
            row["origin"] = "unevaluated"
            row["verdict"] = "NOT separable"
        w["row"] = row
        rows.append(row)

    # ---------- pair-union tests: sided pairs sharing one un-sided
    # BP3D concept, where neither side is individually clean — ZA
    # frequently splits one BP3D concept into .l/.r fragments.
    by_base = {}
    for name, w in work.items():
        r = w.get("row")
        if r and r.get("bp3d_concept") and r.get("side") and "za" in w:
            by_base.setdefault((r["base"], r["bp3d_concept"]), []).append(name)
    # only pairs where at least one side is not individually clean
    by_base = {k: v for k, v in by_base.items()
               if any(work[n]["row"]["verdict"] != "cleanly attributable"
                      for n in v)}
    for (base, concept), names in by_base.items():
        sides = {work[n]["side"]: n for n in names}
        if set(sides) == {"left", "right"}:
            za_u = np.concatenate([work[sides["left"]]["za"],
                                   work[sides["right"]]["za"]])
            st = icp(za_u, bp_verts(concept), init, rng,
                     fixed_scale=pair_scale)
            ok = band(st) in ("same", "same-marginal-p95")
            for n in names:
                r = work[n]["row"]
                if r["origin"] == "named-third-party-region":
                    continue
                r["pair_union"] = pub(st)
                if ok and r["verdict"] != "cleanly attributable":
                    r["origin"] = "bp3d-derived-fragment (pair-union same)"
                    r["verdict"] = "cleanly attributable"
                elif r["origin"].startswith("bp3d-derived-fragment"):
                    r["origin"] = "unresolved-fragment"
                    r["verdict"] = "NOT separable"
        else:
            for n in names:
                r = work[n]["row"]
                if r["origin"].startswith("bp3d-derived-fragment"):
                    r["origin"] = "unresolved-fragment"
                    r["verdict"] = "NOT separable"

    # ---------- brain-assembly transform + curve course tests
    asm = None
    if asm_src:
        S = np.concatenate(asm_src)
        D = np.concatenate(asm_dst)
        s_a, R_a, t_a = umeyama(S, D)
        resid = np.linalg.norm(s_a * (S @ R_a.T) + t_a - D, axis=1)
        asm = {"scale": float(s_a), "rotation": R_a.tolist(),
               "translation_mm": t_a.tolist(),
               "points": int(len(S)), "residual_mean_mm": float(resid.mean()),
               "residual_p95_mm": float(np.percentile(resid, 95))}
        # held-out check: fit the assembly on even-indexed matched
        # objects only, measure residuals on the odd-indexed ones
        half = len(asm_src) // 2
        idx = np.arange(len(asm_src))
        fit_i = idx[idx % 2 == 0]
        test_i = idx[idx % 2 == 1]
        if len(fit_i) >= 4 and len(test_i) >= 4:
            Sf = np.concatenate([asm_src[i] for i in fit_i])
            Df = np.concatenate([asm_dst[i] for i in fit_i])
            St = np.concatenate([asm_src[i] for i in test_i])
            Dt = np.concatenate([asm_dst[i] for i in test_i])
            sh, Rh, th = umeyama(Sf, Df)
            rh = np.linalg.norm(sh * (St @ Rh.T) + th - Dt, axis=1)
            asm["held_out"] = {
                "fit_objects": int(len(fit_i)), "test_objects": int(len(test_i)),
                "scale": float(sh),
                "residual_mean_mm": float(rh.mean()),
                "residual_median_mm": float(np.median(rh)),
                "residual_p95_mm": float(np.percentile(rh, 95))}
    curve_rows = 0
    if asm:
        for name in sorted(nerv):
            w = work[name]
            row = w.get("row")
            if not row or row["type"] != "CURVE" or "curve" not in w:
                continue
            hit = concept_for(w["base"], w["side"])
            row["bp3d_concept"] = hit
            if not hit:
                continue
            e = w["curve"]
            pts = np.concatenate([bezier_samples(s) for s in e["splines"]])
            moved = asm["scale"] * (pts @ np.array(asm["rotation"]).T) + \
                np.array(asm["translation_mm"])
            dd, _ = cKDTree(bp_verts(hit)).query(moved, workers=4)
            row["curve_course"] = {
                "median_dist_mm": float(np.median(dd)),
                "p95_dist_mm": float(np.percentile(dd, 95)),
                "bevel_depth_m": e["bevel_depth"]}
            row["origin"] = "za-curve-course-consistent" \
                if row["curve_course"]["median_dist_mm"] <= 5 else \
                "za-curve-course-unresolved"
            curve_rows += 1

    with open(out_path, "w") as fh:
        json.dump({"pair_scale_za_to_bp3d": pair_scale,
                   "bands_mm": {"match_mean": MATCH_MEAN, "match_p95": MATCH_P95,
                                "match_reverse_mean": MATCH_REV,
                                "borderline_mean": BORD_MEAN,
                                "borderline_p95": BORD_P95,
                                "scale_tolerance": SCALE_TOL},
                   "brain_assembly_transform": asm,
                   "objects": rows}, fh, indent=1)
    from collections import Counter
    print("pair scale:", round(pair_scale, 2), "| assembly:", asm and
          (round(asm["scale"], 1), round(asm["residual_mean_mm"], 3),
           round(asm["residual_p95_mm"], 3)), "| curve rows:", curve_rows)
    print("objects:", len(rows))
    print(Counter(r["verdict"] for r in rows))
    print(Counter(r["origin"] for r in rows))


if __name__ == "__main__":
    main()
