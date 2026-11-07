#!/usr/bin/env python3
"""zanatomy_extract.py — Blender-side geometry extractor for the audit.

Run WITH Blender (a full scene load of the 306 MB Z-Anatomy template
is OOM-killed on this machine, so this script starts from an empty
scene and pulls only the named datablocks — plus their parent chains —
through bpy.data.libraries.load, links them, updates the view layer
once, and reads out world-space geometry):

  blender -b --factory-startup --python tools/zanatomy_extract.py -- \
      Startup.blend OUTDIR NAME [NAME ...]

Per object it writes OUTDIR/<sanitized name>.json with the world
matrix and, for meshes, a sibling .npy of world-space vertices; for
curves, the spline control points (world space), spline types,
bevel depth and resolution — a curve's tube is derivable from those.

The companion parser tools/zanatomy_blend.py supplies names/parents
(headless, no Blender); this extractor trusts Blender itself for
transform semantics (parenting, parentinv, mirroring) — the two were
cross-validated against the distributor's GLB exports in Milestone 34.
"""
import bpy
import json
import os
import sys

import numpy as np


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    src, outdir, names = argv[0], argv[1], argv[2:]
    if len(names) == 1 and names[0].endswith(".json") and os.path.exists(names[0]):
        with open(names[0]) as fh:
            names = json.load(fh)
    os.makedirs(outdir, exist_ok=True)
    with bpy.data.libraries.load(src, link=False) as (data_from, data_to):
        want = [n for n in names if n in data_from.objects]
        data_to.objects = want
    loaded = {o.name: o for o in data_to.objects}
    # pull in ancestor chains so matrix_world composes correctly
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
        entry = {"type": o.type,
                 "matrix_world": [[float(x) for x in row] for row in mw],
                 "parent": o.parent.name if o.parent else None}
        safe = name.replace("/", "_").replace(" ", "_")
        if o.type == "MESH":
            verts = np.empty(len(o.data.vertices) * 3)
            o.data.vertices.foreach_get("co", verts)
            verts = verts.reshape(-1, 3)
            world = verts @ mw[:3, :3].T + mw[:3, 3]
            np.save(os.path.join(outdir, safe + ".npy"), world)
            entry["verts"] = int(len(world))
            entry["file"] = safe + ".npy"
        elif o.type == "CURVE":
            cu = o.data
            entry["bevel_depth"] = float(cu.bevel_depth)
            entry["bevel_resolution"] = int(cu.bevel_resolution)
            entry["resolution_u"] = int(cu.resolution_u)
            splines = []
            for s in cu.splines:
                if s.type == "BEZIER":
                    pts = np.array([[list(bp.co), list(bp.handle_left),
                                     list(bp.handle_right)]
                                    for bp in s.bezier_points])
                    pts_w = pts @ mw[:3, :3].T + mw[:3, 3]
                    splines.append({"type": "BEZIER",
                                    "points": pts_w[:, 0].tolist(),
                                    "handle_left": pts_w[:, 1].tolist(),
                                    "handle_right": pts_w[:, 2].tolist(),
                                    "radius": [float(bp.radius)
                                               for bp in s.bezier_points],
                                    "use_cyclic_u": bool(s.use_cyclic_u)})
                else:
                    pts = np.array([list(p.co[:3]) for p in s.points])
                    pts_w = pts @ mw[:3, :3].T + mw[:3, 3]
                    splines.append({"type": s.type,
                                    "points": pts_w.tolist(),
                                    "radius": [float(p.radius)
                                               for p in s.points],
                                    "use_cyclic_u": bool(s.use_cyclic_u)})
            entry["splines"] = splines
        report[name] = entry
    with open(os.path.join(outdir, "extract_report.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    print("extracted:", len(report))


if __name__ == "__main__":
    main()
