import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
# union bbox of ALL anatomy (from measured group bboxes), +1 cm margin
BOX = (-0.345, 0.345, -0.19, 0.145, -0.005, 1.715)
GROUPS = ['skin', 'bone', 'cartilage', 'muscle', 'artery', 'vein',
          'heart', 'nerve', 'brain', 'lung', 'liver', 'organ']
for name in GROUPS:
    d = np.load(f'work/{name}.npz')
    verts, starts, totals, loops = d['verts'], d['starts'], d['totals'], d['loops']
    n = len(verts)
    face_of_loop = np.repeat(np.arange(len(starts)), totals)
    idx = np.arange(len(loops))
    last_loop = np.repeat(starts + totals - 1, totals)
    first_loop = np.repeat(starts, totals)
    nxt = loops[np.where(idx == last_loop, first_loop, idx + 1)]
    rows = np.concatenate([loops, nxt])
    cols = np.concatenate([nxt, loops])
    g = csr_matrix((np.ones(len(rows), dtype=np.int8), (rows, cols)),
                   shape=(n, n))
    ncomp, labels = connected_components(g, directed=False)
    sizes = np.bincount(labels)
    kill_vert = np.zeros(n, dtype=bool)
    nk = 0
    cents = []
    for c in range(ncomp):
        if sizes[c] < 3000:
            sel = labels == c
            cen = verts[sel].mean(axis=0)
            outside = not (BOX[0] <= cen[0] <= BOX[1] and
                           BOX[2] <= cen[1] <= BOX[3] and
                           BOX[4] <= cen[2] <= BOX[5])
            if outside:
                kill_vert[sel] = True
                nk += 1
                cents.append((int(sizes[c]), tuple(np.round(cen, 3))))
    face_kill = np.bincount(face_of_loop[kill_vert[loops]],
                            minlength=len(starts)) > 0
    keep_faces = np.where(~face_kill)[0]
    print(f'{name}: kill comps {nk}, kill verts {int(kill_vert.sum())}, '
          f'keep faces {len(keep_faces)}/{len(starts)}', flush=True)
    for s, cen in cents[:6]:
        print(f'    stray size {s} at {cen}', flush=True)
    np.savez_compressed(f'work/{name}_keep.npz', keep_faces=keep_faces)
print('ISLANDS3 DONE')
