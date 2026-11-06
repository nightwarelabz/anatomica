import bpy, os, sys
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import scene as S
bpy.ops.wm.open_mainfile(filepath=S.BLEND)
os.makedirs('work', exist_ok=True)
for name in S.GROUPS:
    o = bpy.data.objects.get(name)
    if o is None:
        continue
    me = o.data
    n = len(me.vertices)
    verts = np.empty(n * 3, dtype=np.float64)
    me.vertices.foreach_get('co', verts)
    verts = verts.reshape(n, 3)
    npf = len(me.polygons)
    starts = np.empty(npf, dtype=np.int64)
    totals = np.empty(npf, dtype=np.int64)
    me.polygons.foreach_get('loop_start', starts)
    me.polygons.foreach_get('loop_total', totals)
    loops = np.empty(len(me.loops), dtype=np.int64)
    me.loops.foreach_get('vertex_index', loops)
    np.savez_compressed(f'work/{name}.npz', verts=verts, starts=starts,
                        totals=totals, loops=loops)
    print('DUMPED', name, n, 'verts', npf, 'polys', flush=True)
print('DUMP DONE', flush=True)
