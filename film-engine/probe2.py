import bpy, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import scene as S
bpy.ops.wm.open_mainfile(filepath=S.BLEND)
for name in ('skin', 'bone', 'muscle'):
    o = bpy.data.objects.get(name)
    vs = o.data.vertices
    xs = [v.co.x for v in vs]; ys = [v.co.y for v in vs]; zs = [v.co.z for v in vs]
    print(name, 'local bbox x', round(min(xs),3), round(max(xs),3),
          'y', round(min(ys),3), round(max(ys),3),
          'z', round(min(zs),3), round(max(zs),3),
          'loc', tuple(round(c,3) for c in o.location))
    if name == 'skin':
        bad = [v.co for v in vs if not (-0.30 < v.co.x < 0.30 and
               -0.25 < v.co.y < 0.25 and -0.05 < v.co.z < 1.80)]
        print('skin out-of-envelope verts:', len(bad), 'of', len(vs))
        for c in bad[:8]:
            print('   bad vert', tuple(round(q,3) for q in c))
