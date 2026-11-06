import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
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
    big = sizes >= 3000
    kill_vert = np.zeros(n, dtype=bool)
    if big.any() and (~big).any():
        tree = cKDTree(verts[big[labels]])
        small_idx = np.where(~big[labels])[0]
        # chunked distance queries to bound memory
        far = np.zeros(len(small_idx), dtype=bool)
        for s in range(0, len(small_idx), 200000):
            chunk = small_idx[s:s + 200000]
            dist, _ = tree.query(verts[chunk], k=1, workers=4)
            far[s:s + len(chunk)] = dist > 0.05
        kill_vert[small_idx[far]] = True
    face_kill = np.bincount(face_of_loop[kill_vert[loops]],
                            minlength=len(starts)) > 0
    keep_faces = np.where(~face_kill)[0]
    print(f'{name}: comps {ncomp}, kill verts {int(kill_vert.sum())}, '
          f'keep faces {len(keep_faces)}/{len(starts)}', flush=True)
    np.savez_compressed(f'work/{name}_keep.npz', keep_faces=keep_faces)
print('ISLANDS2 DONE')
