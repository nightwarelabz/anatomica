import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
import os
CORE = (-0.30, 0.30, -0.19, 0.17, 0.03, 1.72)
GROUPS = ['skin', 'bone', 'cartilage', 'muscle', 'artery', 'vein',
          'heart', 'nerve', 'brain', 'lung', 'liver', 'organ']
for name in GROUPS:
    d = np.load(f'work/{name}.npz')
    verts, starts, totals, loops = d['verts'], d['starts'], d['totals'], d['loops']
    n = len(verts)
    # polygon edges: consecutive loop pairs (incl. wrap)
    face_of_loop = np.repeat(np.arange(len(starts)), totals)
    nxt = loops.copy()
    # next vertex within each polygon
    idx = np.arange(len(loops))
    last_loop = np.repeat(starts + totals - 1, totals)
    first_loop = np.repeat(starts, totals)
    nxt_pos = np.where(idx == last_loop, first_loop, idx + 1)
    nxt = loops[nxt_pos]
    rows = np.concatenate([loops, nxt])
    cols = np.concatenate([nxt, loops])
    g = csr_matrix((np.ones(len(rows), dtype=np.int8), (rows, cols)),
                   shape=(n, n))
    ncomp, labels = connected_components(g, directed=False)
    sizes = np.bincount(labels)
    kill_comp = np.zeros(ncomp, dtype=bool)
    for c in range(ncomp):
        if sizes[c] < 3000:
            cen = verts[labels == c].mean(axis=0)
            inside = (CORE[0] <= cen[0] <= CORE[1] and
                      CORE[2] <= cen[1] <= CORE[3] and
                      CORE[4] <= cen[2] <= CORE[5])
            if not inside:
                kill_comp[c] = True
    kill_vert = kill_comp[labels]
    face_kill = np.bincount(face_of_loop[kill_vert[loops]],
                            minlength=len(starts)) > 0
    keep_faces = np.where(~face_kill)[0]
    print(f'{name}: comps {ncomp}, kill comps {int(kill_comp.sum())}, '
          f'kill verts {int(kill_vert.sum())}, keep faces '
          f'{len(keep_faces)}/{len(starts)}', flush=True)
    np.savez_compressed(f'work/{name}_keep.npz', keep_faces=keep_faces)
print('ISLANDS DONE')
