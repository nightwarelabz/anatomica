import bpy, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import scene as S
bpy.ops.wm.open_mainfile(filepath=S.BLEND)
o = bpy.data.objects.get('skin')
for v in o.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    v.co = (x, z, -y)
o.data.update()
bpy.ops.wm.save_as_mainfile(filepath=S.BLEND)
xs = [v.co.x for v in o.data.vertices]
ys = [v.co.y for v in o.data.vertices]
zs = [v.co.z for v in o.data.vertices]
print('SKIN FIXED bbox x', round(min(xs),3), round(max(xs),3),
      'y', round(min(ys),3), round(max(ys),3),
      'z', round(min(zs),3), round(max(zs),3))
b = bpy.data.objects.get('bone')
wide = [v.co for v in b.data.vertices if abs(v.co.x) > 0.26]
if wide:
    wz = [c.z for c in wide]
    print('bone verts beyond skin width:', len(wide),
          'their z range', round(min(wz),3), round(max(wz),3))
