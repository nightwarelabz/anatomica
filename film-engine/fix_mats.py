import bpy, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import scene as S
bpy.ops.wm.open_mainfile(filepath=S.BLEND)
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    if bsdf is None:
        continue
    if m.name == 'mat_muscle':
        bsdf.inputs['Base Color'].default_value = (0.34, 0.05, 0.045, 1)
        bsdf.inputs['Roughness'].default_value = 0.5
        print('muscle mat ->', m.name)
    if m.name == 'mat_bone':
        bsdf.inputs['Base Color'].default_value = (0.78, 0.71, 0.57, 1)
        print('bone mat ->', m.name)
bpy.ops.wm.save_as_mainfile(filepath=S.BLEND)
print('MATS SAVED')
