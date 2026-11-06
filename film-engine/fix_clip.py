import bpy, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import scene as S
bpy.ops.wm.open_mainfile(filepath=S.BLEND)
BOX = (-0.37, 0.37, -0.21, 0.21, -0.02, 1.76)
for name in S.GROUPS:
    o = bpy.data.objects.get(name)
    if o is None:
        continue
    vs = o.data.vertices
    xs = [v.co.x for v in vs]; ys = [v.co.y for v in vs]
    zs = [v.co.z for v in vs]
    bad = sum(1 for v in vs
              if not (BOX[0] <= v.co.x <= BOX[1] and
                      BOX[2] <= v.co.y <= BOX[3] and
                      BOX[4] <= v.co.z <= BOX[5]))
    print(name, 'bbox x', round(min(xs), 3), round(max(xs), 3),
          'y', round(min(ys), 3), round(max(ys), 3),
          'z', round(min(zs), 3), round(max(zs), 3),
          'OUT', bad, '/', len(vs))
    if bad:
        kill = [v.index for v in vs
                if not (BOX[0] <= v.co.x <= BOX[1] and
                        BOX[2] <= v.co.y <= BOX[3] and
                        BOX[4] <= v.co.z <= BOX[5])]
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        for i in kill:
            vs[i].select = True
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.delete(type='VERT')
        bpy.ops.object.mode_set(mode='OBJECT')
        o.select_set(False)
        print('   clipped', len(kill))
bpy.ops.wm.save_as_mainfile(filepath=S.BLEND)
print('CLIP SAVED')
