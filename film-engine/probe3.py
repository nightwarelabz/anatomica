import bpy, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import scene as S
# widen the skin envelope so every ZA system stays inside it
bpy.ops.wm.open_mainfile(filepath=S.BLEND)
o = bpy.data.objects.get('skin')
for v in o.data.vertices:
    v.co.x *= 1.18
    v.co.y *= 1.22
o.data.update()
bpy.ops.wm.save_as_mainfile(filepath=S.BLEND)
print('SKIN ENVELOPE widened')
# fresh muscular import: find objects hanging below z=0
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(
    filepath=os.path.expanduser('~/workspace/anatlas/za/public/models/'
                                 'muscular.glb'))
bad = []
for ob in bpy.data.objects:
    if ob.type != 'MESH':
        continue
    zs = [v.co.z for v in ob.data.vertices]
    if zs and min(zs) < -0.05:
        bad.append((ob.name, round(min(zs), 3), round(max(zs), 3),
                    len(ob.data.vertices)))
for b in sorted(bad, key=lambda t: t[1]):
    print('LOW MUSCLE:', b)
print('low muscle objects:', len(bad))
