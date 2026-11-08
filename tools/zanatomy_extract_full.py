#!/usr/bin/env python3
"""zanatomy_extract_full.py — Blender-side FULL geometry extractor
for the Milestone 63 Tier B intake.

Companion to tools/zanatomy_extract.py (Milestone 34), which reads
out world-space vertices and curve splines for the provenance audit.
Intake needs faces: for each named MESH object this tool additionally
reads the datablock's loop triangles (calc_loop_triangles — the same
raw datablock, no modifier evaluation, exactly the audit's load
pattern), and writes one JSON per object:

  <sanitized name>.full.json:
    {"type": "MESH", "matrix_world": [[...]x4], "det_negative": bool,
     "verts": [[x, y, z], ...]        (world space, template units)
     "tris":  [[i, j, k], ...]}       (winding corrected: if the
                                       world matrix determinant is
                                       negative — the template's
                                       mirrored left copies — each
                                       triangle's order is reversed
                                       so world-space orientation is
                                       outward-consistent)
    {"type": "CURVE", "matrix_world": ..., "world_scale": float,
     "bevel_depth": float, "bevel_resolution": int,
     "resolution_u": int,
     "splines": [ ... same shape as tools/zanatomy_extract.py ... ]}

  blender -b --factory-startup --python \
      tools/zanatomy_extract_full.py -- Startup.blend OUTDIR NAMES.json
"""
import bpy
import json
import os
import sys

import numpy as np


def spline_entry(s, mw):
    if s.type == "BEZIER":
        pts = np.array([[list(bp.co), list(bp.handle_left),
                         list(bp.handle_right)]
                        for bp in s.bezier_points])
        pts_w = pts @ mw[:3, :3].T + mw[:3, 3]
        return {"type": "BEZIER",
                "points": pts_w[:, 0].tolist(),
                "handle_left": pts_w[:, 1].tolist(),
                "handle_right": pts_w[:, 2].tolist(),
                "radius": [float(bp.radius) for bp in s.bezier_points],
                "use_cyclic_u": bool(s.use_cyclic_u)}
    pts = np.array([list(p.co[:3]) for p in s.points])
    pts_w = pts @ mw[:3, :3].T + mw[:3, 3]
    return {"type": s.type,
            "points": pts_w.tolist(),
            "radius": [float(p.radius) for p in s.points],
            "use_cyclic_u": bool(s.use_cyclic_u)}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    src, outdir, names_path = argv[0], argv[1], argv[2]
    with open(names_path) as fh:
        names = json.load(fh)
    os.makedirs(outdir, exist_ok=True)
    with bpy.data.libraries.load(src, link=False) as (data_from, data_to):
        want = [n for n in names if n in data_from.objects]
        data_to.objects = want
    loaded = {o.name: o for o in data_to.objects}
    frontier = list(loaded.values())
    seen = set(loaded)
    while frontier:
        nxt = []
        for o in frontier:
            p = o.parent
            if p is not None and p.name not in seen:
                seen.add(p.name)
                nxt.append(p)
        if nxt:
            with bpy.data.libraries.load(src, link=False) as (df, dt):
                dt.objects = [o.name for o in nxt if o.name in df.objects]
            for o in dt.objects:
                loaded[o.name] = o
        frontier = nxt
    coll = bpy.context.scene.collection
    for o in loaded.values():
        if o.name not in coll.objects:
            try:
                coll.objects.link(o)
            except RuntimeError:
                pass
    bpy.context.view_layer.update()
    report = {}
    for name in names:
        o = loaded.get(name)
        if o is None:
            report[name] = {"error": "not in file"}
            continue
        mw = np.array(o.matrix_world)
        det_neg = bool(np.linalg.det(mw[:3, :3]) < 0)
        safe = name.replace("/", "_").replace(" ", "_")
        entry = {"type": o.type,
                 "matrix_world": [[float(x) for x in row] for row in mw],
                 "det_negative": det_neg}
        if o.type == "MESH":
            me = o.data
            verts = np.empty(len(me.vertices) * 3)
            me.vertices.foreach_get("co", verts)
            verts = verts.reshape(-1, 3)
            world = verts @ mw[:3, :3].T + mw[:3, 3]
            me.calc_loop_triangles()
            tris = np.empty(len(me.loop_triangles) * 3, dtype=np.int64)
            me.loop_triangles.foreach_get("vertices", tris)
            tris = tris.reshape(-1, 3)
            if det_neg:
                tris = tris[:, ::-1]
            entry["verts"] = int(len(world))
            entry["tris"] = int(len(tris))
            with open(os.path.join(outdir, safe + ".full.json"), "w") as fh:
                json.dump({"verts": world.tolist(),
                           "tris": tris.tolist()}, fh)
            entry["file"] = safe + ".full.json"
        elif o.type == "CURVE":
            cu = o.data
            entry["bevel_depth"] = float(cu.bevel_depth)
            entry["bevel_resolution"] = int(cu.bevel_resolution)
            entry["resolution_u"] = int(cu.resolution_u)
            # mean singular scale of the world matrix (bevel radius
            # lives in curve-local units; the world tube radius is
            # bevel_depth x this factor)
            sv = np.linalg.svd(mw[:3, :3], compute_uv=False)
            entry["world_scale"] = float(sv.mean())
            entry["splines"] = [spline_entry(s, mw) for s in cu.splines]
            with open(os.path.join(outdir, safe + ".full.json"), "w") as fh:
                json.dump({"splines": entry["splines"],
                           "bevel_depth": entry["bevel_depth"],
                           "world_scale": entry["world_scale"]}, fh)
            entry["file"] = safe + ".full.json"
        report[name] = entry
    with open(os.path.join(outdir, "extract_full_report.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    print("extracted full:", len(report))


if __name__ == "__main__":
    main()
