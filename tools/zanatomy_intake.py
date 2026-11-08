#!/usr/bin/env python3
"""zanatomy_intake.py — Milestone 63 geometry intake.

Executes the 2026-11-08 geometry ruling on the Milestone 34 audit:

  * Tier B intake: the 236 Z-Anatomy objects the audit cleared on
    both bars are extracted from the upstream template (full
    geometry by tools/zanatomy_extract_full.py), placed into the
    BodyParts3D frame by the audit's brain-assembly similarity
    transform (scale 1030.957191; split-half held-out mean
    0.274 mm — re-derived and re-verified at Milestone 63 against
    a fresh run of the audit's own tools, bit-identical), written
    as OBJ meshes under data/sources/z-anatomy-derived/obj/
    (curves become tubes at the template's own bevel radius), and
    recorded in that directory's intake-manifest.json with a
    per-object provenance chain. The 19 objects the audit mapped
    to geometry-absent FMA records are attached to those records
    (data/nervous/nervous-geometry.json + nervous-inventory.json).
    Tier C objects are NOT intaken (gated on a derivation that
    does not yet exist); Tier D objects are NOT intaken (provenance
    inseparable). No other object is intaken under any reading.

  * Deferent-duct claim: repro.left-deferent-duct /
    repro.right-deferent-duct are re-filed as geometry-carrying
    records over the BodyParts3D 4.0 meshes FJ3135 / FJ3140 — the
    claim the Milestone 40 adjudication pinned for exactly this
    decision.

Every mesh statistic written into a geometry entry is measured by
streaming the OBJ file it names, never computed in memory. All
JSON edits are load/modify/dump with the files' own serialization
(indent=1), so untouched records stay byte-identical.

Usage:
  python3 tools/zanatomy_intake.py EXTRACT_FULL_DIR AUDIT_EXTRACT_DIR
(EXTRACT_FULL_DIR: tools/zanatomy_extract_full.py output for the
Tier B objects; AUDIT_EXTRACT_DIR: tools/zanatomy_extract.py output
for the nervous collection — used for the assembly-member surface
re-verification recorded in the manifest.)
"""
import hashlib
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
M34_PROV = os.path.join(ROOT, "milestones", "MILESTONE-34-provenance.json")
M34_CLEAR = os.path.join(ROOT, "milestones", "MILESTONE-34-clearance.json")
DERIVED = os.path.join(ROOT, "data", "sources", "z-anatomy-derived")
OBJ_DIR = os.path.join(DERIVED, "obj")
UPSTREAM_ZIP_SHA256 = \
    "e029688545627bd0214b269e1063143abb580aad72b2c2445d6d8a9a0d9da736"
RADIAL_SEGS = 8
BEZIER_PER_SEG = 16

# Excluded at intake despite the Tier B listing — the standing
# rule is that Bar-1 ambiguity is never resolved in intake's
# favour. 'Cochlear nerve.l' is a curve whose elimination origin
# cannot exclude the one alternative source that matters: it
# sits in the Dundee inner-ear named region (CC BY-NC-SA), and
# its un-sided mesh namesake ('Cochlear nerve') is adjudicated
# to that region in Tier D. For the cranial-nerve-region curves
# the same logical gap is harmless (the Dundee cranial
# inclusion is CC BY 4.0 — compatible under either attribution,
# and the attribution is recorded alongside); here the
# alternative attribution is license-incompatible, so the
# object is excluded and the exclusion reported (Milestone 63
# dossier). It maps to no Body Model record; nothing else in
# the intake depends on it.
EXCLUDED = {
    "Cochlear nerve.l":
        "Bar-1 ambiguous on re-examination: elimination origin "
        "cannot exclude the Dundee inner-ear source (CC BY-NC-SA "
        "named region; the un-sided 'Cochlear nerve' mesh is "
        "Tier D under that attribution). Excluded rather than "
        "resolved in intake's favour.",
}


def safe(name):
    return name.replace("/", "_").replace(" ", "_")


def stream_stats(path):
    """(vertices, faces, bbox) measured from an OBJ file on disk."""
    v = f = 0
    mn = [float("inf")] * 3
    mx = [float("-inf")] * 3
    with open(path) as fh:
        for line in fh:
            if line.startswith("v "):
                p = line.split()
                v += 1
                for i in range(3):
                    x = float(p[i + 1])
                    if x < mn[i]:
                        mn[i] = x
                    if x > mx[i]:
                        mx[i] = x
            elif line.startswith("f "):
                f += 1
    return v, f, {"min": mn, "max": mx}


def write_obj(path, verts, tris):
    with open(path, "w") as fh:
        fh.write("# ANATOMICA Milestone 63 — Z-Anatomy Tier B derived "
                 "geometry (CC BY-SA 4.0); see ../intake-manifest.json\n")
        for p in verts:
            fh.write(f"v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n")
        for a, b, c in tris:
            fh.write(f"f {a + 1} {b + 1} {c + 1}\n")


# ------------------------------------------------------------ curves
def bezier_polyline(spline):
    pts = np.array(spline["points"])
    if spline["type"] != "BEZIER" or len(pts) < 2:
        return pts, np.array(spline["radius"] or [1.0] * len(pts))
    hl = np.array(spline["handle_left"])
    hr = np.array(spline["handle_right"])
    rad = np.array(spline["radius"])
    out, out_r = [], []
    nseg = len(pts) if spline.get("use_cyclic_u") else len(pts) - 1
    for i in range(nseg):
        j = (i + 1) % len(pts)
        p0, p1, p2, p3 = pts[i], hr[i], hl[j], pts[j]
        steps = BEZIER_PER_SEG if i < nseg - 1 or \
            spline.get("use_cyclic_u") else BEZIER_PER_SEG + 1
        for k in range(steps):
            u = k / BEZIER_PER_SEG
            out.append(((1 - u) ** 3) * p0 + 3 * ((1 - u) ** 2) * u * p1
                       + 3 * (1 - u) * u * u * p2 + (u ** 3) * p3)
            out_r.append(rad[i] * (1 - u) + rad[j] * u)
    if not spline.get("use_cyclic_u"):
        out.append(pts[-1])
        out_r.append(rad[-1])
    return np.array(out), np.array(out_r)


def tube_mesh(pts_mm, radii_mm, cyclic=False):
    """Tube around a polyline: parallel-transport frames, RADIAL_SEGS
    sides, end caps (open if cyclic). Returns (verts, tris)."""
    keep = [0]
    for i in range(1, len(pts_mm)):
        if np.linalg.norm(pts_mm[i] - pts_mm[keep[-1]]) > 1e-6:
            keep.append(i)
    P = pts_mm[keep]
    R = radii_mm[keep]
    n = len(P)
    if n < 2:
        raise ValueError("degenerate spline (fewer than 2 distinct points)")
    T = np.zeros((n, 3))
    T[0] = P[1] - P[0]
    T[-1] = P[-1] - P[-2]
    for i in range(1, n - 1):
        T[i] = P[i + 1] - P[i - 1]
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    axis = np.eye(3)[np.argmin(np.abs(T[0]))]
    N = axis - (axis @ T[0]) * T[0]
    N /= np.linalg.norm(N)
    verts, tris = [], []
    for i in range(n):
        if i:
            v = T[i] - T[i - 1]
            nv = np.linalg.norm(v)
            if nv > 1e-12:
                v /= nv
                N = N - 2 * (N @ v) * v          # double reflection
                N = N - (N @ T[i]) * T[i]
                N /= np.linalg.norm(N)
        B = np.cross(T[i], N)
        base = len(verts)
        for k in range(RADIAL_SEGS):
            th = 2 * np.pi * k / RADIAL_SEGS
            d = np.cos(th) * N + np.sin(th) * B
            verts.append(P[i] + R[i] * d)
        if i:
            p0 = base - RADIAL_SEGS
            for k in range(RADIAL_SEGS):
                k2 = (k + 1) % RADIAL_SEGS
                tris.append((p0 + k, p0 + k2, base + k2))
                tris.append((p0 + k, base + k2, base + k))
    if cyclic:
        p0, base = (n - 1) * RADIAL_SEGS, 0
        for k in range(RADIAL_SEGS):
            k2 = (k + 1) % RADIAL_SEGS
            tris.append((p0 + k, p0 + k2, base + k2))
            tris.append((p0 + k, base + k2, base + k))
    else:
        c0 = len(verts)
        verts.append(P[0])
        c1 = len(verts)
        verts.append(P[-1])
        last = (n - 1) * RADIAL_SEGS
        for k in range(RADIAL_SEGS):
            k2 = (k + 1) % RADIAL_SEGS
            tris.append((c0, k2, k))
            tris.append((c1, last + k, last + k2))
    return verts, tris


# ------------------------------------------------------------ chains
def provenance_chain(row):
    name, typ = row["object"], row["type"]
    origin = row["origin"]
    head = (f"Z-Anatomy template object '{name}' ({typ}), from "
            f"Z-Anatomy/Models-of-human-anatomy Startup.blend "
            f"(upstream archive SHA-256 {UPSTREAM_ZIP_SHA256}); "
            f"extracted in-session (Milestone 63). ")
    if origin == "za-original-by-elimination":
        if row.get("named_region") and \
                "cranial-nerve" in row["named_region"]:
            return head + (
                "Provenance (Milestone 34 bar 1, re-verified "
                "Milestone 63): attributed to Z-Anatomy itself "
                "(the template's listed contributions: integrating "
                "missing structures; nerves and vessels converted "
                "to curves — every curve in the template carries "
                "this attribution under the audit's uniform curve "
                "rule). The object also sits in the upstream-named "
                "'Cranial Nerves and Foramina' inclusion "
                "(University of Dundee, CC BY 4.0), which cannot "
                "be isolated object-by-object from Z-Anatomy's "
                "own curve work; it is attributed to Z-Anatomy as "
                "distributed, with the Dundee attribution "
                "recorded here alongside (Milestone 34 §2) — the "
                "attribution is intake-compatible under either "
                "source. License: CC BY-SA 4.0, the "
                "distribution's headline license (upstream "
                "License.txt); share-alike applies to this "
                "derived file.")
        return head + (
            "Provenance (Milestone 34 bar 1, re-verified Milestone "
            "63): no BodyParts3D mesh-bearing concept of this name "
            "exists in any Body Model geometry resolution, and the "
            "object sits in no named third-party inclusion region; "
            "attributed to Z-Anatomy itself (the template's listed "
            "contributions: integrating missing structures; nerves "
            "and vessels converted to curves). License: CC BY-SA "
            "4.0, the distribution's headline license (upstream "
            "License.txt); share-alike applies to this derived file.")
    if origin in ("za-curve-course-consistent",
                  "za-curve-course-unresolved"):
        cc = row["curve_course"]
        named = (" The object also sits in the upstream-named "
                 "'Cranial Nerves and Foramina' inclusion "
                 "(University of Dundee, CC BY 4.0), which cannot be "
                 "isolated object-by-object from Z-Anatomy's own "
                 "curve work; it is attributed to Z-Anatomy as "
                 "distributed, with the Dundee attribution recorded "
                 "here alongside (Milestone 34 §2).")
        if origin == "za-curve-course-consistent":
            return head + (
                f"Provenance (Milestone 34 bar 1, re-verified "
                f"Milestone 63): nerve curve whose course is "
                f"measured consistent with BodyParts3D's "
                f"'{row['bp3d_concept']}' mesh under the "
                f"brain-assembly transform (median "
                f"{cc['median_dist_mm']:.2f} mm, p95 "
                f"{cc['p95_dist_mm']:.2f} mm). License: CC BY-SA "
                f"4.0 (Z-Anatomy as distributed)." + named)
        return head + (
            f"Provenance (Milestone 34 bar 1, re-verified Milestone "
            f"63): nerve curve whose course does NOT correspond to "
            f"BodyParts3D's '{row['bp3d_concept']}' mesh (median "
            f"{cc['median_dist_mm']:.2f} mm under the brain-assembly "
            f"transform) — the deviation is flagged on this entry, "
            f"not resolved; the attribution is unchanged. License: "
            f"CC BY-SA 4.0 (Z-Anatomy as distributed)." + named)
    return head + f"Provenance origin (Milestone 34): {origin}."


def main():
    full_dir, audit_dir = sys.argv[1], sys.argv[2]
    prov = json.load(open(M34_PROV))
    clear = json.load(open(M34_CLEAR))
    asm = prov["brain_assembly_transform"]
    s_a = asm["scale"]
    R_a = np.array(asm["rotation"])
    t_a = np.array(asm["translation_mm"])
    rows = {o["object"]: o for o in prov["objects"]}
    tier_b = clear["tiers"]["B"]
    hits = {h["object"]: h["fma_record"] for h in clear["fma_hits"]["B"]}
    box = clear["region_box_bp3d_mm"]
    margin = clear.get("region_margin_mm", 0.0)
    box_lo = np.array(box["lo"]) - margin
    box_hi = np.array(box["hi"]) + margin
    full_rep = json.load(open(os.path.join(full_dir,
                                           "extract_full_report.json")))

    def place(p):
        return s_a * (np.asarray(p, dtype=np.float64) @ R_a.T) + t_a

    os.makedirs(OBJ_DIR, exist_ok=True)
    entries, exclusions = [], []
    for name in tier_b:
        row = rows[name]
        if name in EXCLUDED:
            exclusions.append({
                "object": name, "tier": "B", "type": row["type"],
                "origin": row["origin"],
                "named_region": row.get("named_region"),
                "reason": EXCLUDED[name]})
            stale = os.path.join(OBJ_DIR, safe(name) + ".obj")
            if os.path.exists(stale):
                os.remove(stale)
            continue
        e = full_rep[name]
        entry = {"object": name, "type": row["type"], "tier": "B",
                 "origin": row["origin"], "verdict": row["verdict"],
                 "provenance_chain": provenance_chain(row),
                 "fma_record": hits.get(name),
                 "attached": name in hits,
                 "curve_course_mm": row.get("curve_course"),
                 "flags": []}
        if name.startswith("Trochlear nerve"):
            entry["flags"].append(
                "trochlear course discrepancy (Milestone 34 §2): "
                "this curve deviates from BodyParts3D's trochlear "
                "course (median 5.4 mm); the flag is carried on "
                "records nerve.left-trochlear-nerve / "
                "nerve.right-trochlear-nerve — those records' "
                "BodyParts3D geometry is unchanged")
        if name.startswith("Ophthalmic nerve"):
            entry["flags"].append(
                "ophthalmic course non-correspondence (Milestone "
                "34 §2): this curve does not correspond to "
                "BodyParts3D's ophthalmic course (median 53 mm); "
                "intaken unattached, flagged, not resolved")
        data = json.load(open(os.path.join(full_dir, e["file"])))
        if row["type"] == "MESH":
            verts = place(np.array(data["verts"]))
            tris = [tuple(t) for t in data["tris"]]
            centroid_src = np.median(np.array(data["verts"]), axis=0)
        else:
            all_v, all_t = [], []
            for sp in data["splines"]:
                line, rad = bezier_polyline(sp)
                pts_mm = place(line)
                radii = rad * data["bevel_depth"] * \
                    data["world_scale"] * s_a
                v, t = tube_mesh(pts_mm, radii,
                                 cyclic=bool(sp.get("use_cyclic_u")))
                off = len(all_v)
                all_v.extend(v)
                all_t.extend((a + off, b + off, c + off)
                             for a, b, c in t)
            verts, tris = all_v, all_t
            src_pts = np.concatenate(
                [np.array(sp["points"]) for sp in data["splines"]])
            centroid_src = src_pts.mean(0)
        fn = safe(name) + ".obj"
        path = os.path.join(OBJ_DIR, fn)
        write_obj(path, verts, tris)
        v, f, bb = stream_stats(path)
        cent = place(centroid_src)
        entry.update({
            "file": f"obj/{fn}", "fj": f"ZA-{safe(name)}",
            "vertices": v, "faces": f, "bbox_bp3d_mm": bb,
            "centroid_bp3d_mm": [round(float(x), 2) for x in cent],
            "in_assembly_region": bool(np.all(cent >= box_lo)
                                       and np.all(cent <= box_hi)),
            "sha256": hashlib.sha256(open(path, "rb").read()).hexdigest()})
        if row["type"] == "CURVE" and \
                abs(data["bevel_depth"] - 0.0005) > 1e-9:
            entry["flags"].append(
                f"template bevel depth {data['bevel_depth']:.4f} "
                f"(tube radius "
                f"{data['bevel_depth'] * data['world_scale'] * s_a:.3f} "
                "mm) — the Tier B set's only non-0.0005 bevel")
        entries.append(entry)

    # ---- assembly-member surface re-verification: the 27 measured
    # brain objects placed by the single shared transform, measured
    # against their BodyParts3D meshes (independent of the audit's
    # pooled-point fit statistics).
    import glob as _glob
    concept_meshes = {}
    for gj in _glob.glob(os.path.join(ROOT, "data", "*", "*-geometry.json")):
        g = json.load(open(gj))
        for r in g["records"]:
            files = (r.get("isa_meshes") or []) + (r.get("partof_meshes") or [])
            for nm in (r.get("concept_names") or [r.get("concept_name")]):
                if nm and files:
                    concept_meshes.setdefault(nm.lower(), []).extend(
                        os.path.join(ROOT, m["path"]) for m in files)

    def load_obj_verts(p):
        vs = []
        with open(p) as fh:
            for line in fh:
                if line.startswith("v "):
                    q = line.split()
                    vs.append((float(q[1]), float(q[2]), float(q[3])))
        return np.array(vs)

    rep = json.load(open(os.path.join(audit_dir, "extract_report.json")))
    member_check = []
    for name, row in sorted(rows.items()):
        if row.get("origin") != "bp3d-derived-measured":
            continue
        za = np.load(os.path.join(audit_dir, rep[name]["file"]))
        za = za[np.abs(za).max(1) < 2] if len(za) else za
        if len(za) > 4000:
            za = za[np.random.default_rng(63).choice(
                len(za), 4000, replace=False)]
        bp = np.concatenate([load_obj_verts(p)
                             for p in concept_meshes[row["bp3d_concept"]]])
        d, _ = cKDTree(bp).query(place(za), workers=4)
        member_check.append({
            "object": name, "bp3d_concept": row["bp3d_concept"],
            "surface_mean_mm": round(float(d.mean()), 3),
            "surface_p95_mm": round(float(np.percentile(d, 95)), 3)})

    manifest = {
        "title": "ANATOMICA Z-Anatomy Tier B intake manifest — Milestone 63",
        "ruling": "2026-11-08 geometry ruling: Tier B intake proceeds; "
                  "Tier C gated (no validated derivation); Tier D "
                  "excluded permanently. No Tier C or Tier D object "
                  "appears in this manifest.",
        "upstream": {
            "repository": "Z-Anatomy/Models-of-human-anatomy",
            "archive_sha256": UPSTREAM_ZIP_SHA256,
            "template": "Z-Anatomy/Startup.blend (Blender 3.5 format)",
            "license_headline": "CC BY-SA 4.0",
            "note": "Z-Anatomy as a whole distribution is not a "
                    "product source; only the 236 objects the "
                    "Milestone 34 audit cleared on both bars are "
                    "intaken, each under the provenance chain "
                    "recorded on its entry."},
        "transform": {
            "kind": "similarity (Umeyama), Z-Anatomy template units "
                    "to BodyParts3D millimetres",
            "scale": s_a, "rotation": asm["rotation"],
            "translation_mm": asm["translation_mm"],
            "pooled_points": asm["points"],
            "pooled_residual_mean_mm": asm["residual_mean_mm"],
            "pooled_residual_p95_mm": asm["residual_p95_mm"],
            "held_out": asm["held_out"],
            "reverified_milestone_63": "fresh run of the audit's own "
                "tools (zanatomy_blend census, zanatomy_extract, "
                "zanatomy_correspond, zanatomy_clearance) reproduced "
                "the landed transform bit-identically (scale, "
                "rotation and translation delta 0.0), the held-out "
                "statistics identically, and all 842 per-object "
                "verdicts/origins and all four tier lists with zero "
                "differences"},
        "assembly_member_surface_check": member_check,
        "tube_construction": "curve objects are rendered as tubes at "
            "the template's own bevel radius (bevel_depth x curve "
            "world scale x transform scale); 8 radial segments, "
            "parallel-transport frames, capped ends; Bezier splines "
            "sampled 16 steps per segment",
        "region_test": "in_assembly_region is the audit's own "
            "criterion (tools/zanatomy_clearance.py): centroid "
            "inside the matched brain objects' centroid bounding "
            "box expanded by region_margin_mm (50 mm)",
        "objects": entries,
        "exclusions": exclusions,
    }
    with open(os.path.join(DERIVED, "intake-manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    attached = [e for e in entries if e["attached"]]
    print(f"Tier B objects written: {len(entries)} "
          f"({sum(1 for e in entries if e['type'] == 'MESH')} meshes, "
          f"{sum(1 for e in entries if e['type'] == 'CURVE')} curves); "
          f"attached to records: {len(attached)}")
    surf = [m["surface_mean_mm"] for m in member_check]
    print(f"assembly members re-placed by the shared transform: "
          f"{len(member_check)} objects, surface mean "
          f"{min(surf):.3f}..{max(surf):.3f} mm")
    return entries


def dump_house(path, doc):
    with open(path, "w") as fh:
        fh.write(json.dumps(doc, indent=1, ensure_ascii=False))


def refile_nervous(entries):
    inv_p = os.path.join(ROOT, "data", "nervous", "nervous-inventory.json")
    geo_p = os.path.join(ROOT, "data", "nervous", "nervous-geometry.json")
    inv, geo = json.load(open(inv_p)), json.load(open(geo_p))
    inv_by = {r["record_id"]: r for r in inv["records"]}
    geo_by = {r["record_id"]: r for r in geo["records"]}
    transitioned = 0
    for e in entries:
        if not e["attached"]:
            continue
        rid = e["fma_record"]
        g = geo_by[rid]
        want = [{
            "fj": e["fj"],
            "path": "data/sources/z-anatomy-derived/" + e["file"],
            "vertices": e["vertices"], "faces": e["faces"],
            "bbox": e["bbox_bp3d_mm"]}]
        if g["isa_meshes"] or g["partof_meshes"]:
            assert g["isa_meshes"] == want and not g["partof_meshes"], \
                rid  # already applied by an earlier run: must match
        else:
            transitioned += 1
        g["isa_meshes"] = want
        g["totals"] = {
            "isa": {"files": 1, "vertices": e["vertices"],
                    "faces": e["faces"]},
            "partof": {"files": 0, "vertices": 0, "faces": 0},
            "combined_files": 1}
        g["bbox_isa"] = e["bbox_bp3d_mm"]
        g["geometry_status"] = (
            "derived — Z-Anatomy Tier B intake (Milestone 63): "
            f"geometry derived from the Z-Anatomy template object "
            f"'{e['object']}' ({e['type'].lower()}), placed by the "
            "Milestone 34 brain-assembly similarity transform "
            "(scale 1030.957; split-half held-out mean 0.274 mm, "
            "re-verified at Milestone 63); source license CC BY-SA "
            "4.0 (Z-Anatomy); provenance per object in "
            "data/sources/z-anatomy-derived/intake-manifest.json")
        r = inv_by[rid]
        assert r["geometry"] in ("absent", "zanatomy-derived"), rid
        r["geometry"] = "zanatomy-derived"
        r["verify"][0] = (
            "geometry: derived — Z-Anatomy Tier B intake "
            f"(Milestone 63): object '{e['object']}' placed by the "
            "Milestone 34 brain-assembly transform (held-out mean "
            "0.27 mm); license CC BY-SA 4.0; see "
            "data/sources/z-anatomy-derived/intake-manifest.json")
    cov = geo["meta"]["coverage"]
    cov["records_with_meshes"] = sum(
        1 for g in geo["records"] if g["isa_meshes"] or g["partof_meshes"])
    cov["records_without_meshes"] = cov["records"] - \
        cov["records_with_meshes"]
    inv["meta"]["fma_extension"]["geometry_absent"] -= transitioned
    note = (
        "geometry note (Milestone 63): the Z-Anatomy template's "
        "trochlear nerve curve for this side deviates from this "
        "record's BodyParts3D course (median 5.4 mm, Milestone 34 "
        "course test) — the discrepancy is flagged, not resolved: "
        "this record's geometry remains its BodyParts3D mesh, and "
        "the Z-Anatomy curve is intaken unattached in the Milestone "
        "63 Tier B set with the flag carried in "
        "data/sources/z-anatomy-derived/intake-manifest.json")
    for rid in ("nerve.left-trochlear-nerve",
                "nerve.right-trochlear-nerve"):
        assert inv_by[rid].get("note") in (None, note), rid
        inv_by[rid]["note"] = note
    dump_house(inv_p, inv)
    dump_house(geo_p, geo)
    print(f"nervous re-filed: coverage now "
          f"{cov['records_with_meshes']} with / "
          f"{cov['records_without_meshes']} without; trochlear "
          f"records flagged")


PAIR = {"repro.left-deferent-duct": ("FJ3135", 863, 1110),
        "repro.right-deferent-duct": ("FJ3140", 787, 944)}


def refile_deferent():
    inv_p = os.path.join(ROOT, "data", "reproductive",
                         "reproductive-inventory.json")
    geo_p = os.path.join(ROOT, "data", "reproductive",
                         "reproductive-geometry.json")
    inv, geo = json.load(open(inv_p)), json.load(open(geo_p))
    inv_by = {r["record_id"]: r for r in inv["records"]}
    geo_by = {r["record_id"]: r for r in geo["records"]}
    transitioned = 0
    for rid, (fj, ev, ef) in PAIR.items():
        rel = f"work/bp3d/isa_BP3D_4.0_obj_99/{fj}.obj"
        v, f, bb = stream_stats(os.path.join(ROOT, rel))
        assert (v, f) == (ev, ef), (rid, v, f)
        g = geo_by[rid]
        want = [{"fj": fj, "path": rel, "vertices": v,
                 "faces": f, "bbox": bb}]
        if g["isa_meshes"] or g["partof_meshes"]:
            assert g["isa_meshes"] == want and not g["partof_meshes"], \
                rid  # already applied by an earlier run: must match
        else:
            transitioned += 1
        g["isa_meshes"] = want
        g["totals"] = {"isa": {"files": 1, "vertices": v, "faces": f},
                       "partof": {"files": 0, "vertices": 0, "faces": 0},
                       "combined_files": 1}
        g["bbox_isa"] = bb
        g["geometry_status"] = (
            f"claimed — BodyParts3D 4.0 carries this concept under "
            f"the preferred name 'deferent duct' ({fj}); mesh "
            f"claimed at Milestone 63 under the Milestone 40 "
            f"adjudication and the 2026-11-08 geometry ruling")
        r = inv_by[rid]
        assert r["geometry"] in ("absent", "bp3d-claimed"), rid
        r["geometry"] = "bp3d-claimed"
        r["verify"][0] = (
            f"geometry: claimed — BodyParts3D 4.0 mesh {fj} claimed "
            f"at Milestone 63 (Milestone 40 adjudication): BP3D "
            f"carries this FMA concept under the preferred name "
            f"'deferent duct'")
    cov = geo["meta"]["coverage"]
    with_mesh = [g for g in geo["records"]
                 if g["isa_meshes"] or g["partof_meshes"]]
    cov["records_with_meshes"] = len(with_mesh)
    cov["records_without_meshes"] = cov["records"] - len(with_mesh)
    from collections import Counter
    per_line = Counter(g["sex_line"] for g in with_mesh)
    for line, d in cov["by_sex_line"].items():
        d["records_with_meshes"] = per_line.get(line, 0)
    meshes = [m for g in geo["records"]
              for m in g["isa_meshes"] + g["partof_meshes"]]
    cov["union_bbox_all_records"] = {
        "min": [min(m["bbox"]["min"][i] for m in meshes)
                for i in range(3)],
        "max": [max(m["bbox"]["max"][i] for m in meshes)
                for i in range(3)]}
    inv["meta"]["fma_extension_38"]["geometry_absent"] -= transitioned
    dump_house(inv_p, inv)
    dump_house(geo_p, geo)
    print(f"reproductive re-filed: pair claimed; coverage now "
          f"{cov['records_with_meshes']} with / "
          f"{cov['records_without_meshes']} without")


if __name__ == "__main__":
    _entries = main()
    refile_nervous(_entries)
    refile_deferent()
