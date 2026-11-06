import bpy, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import scene as S
bpy.ops.wm.open_mainfile(filepath=S.BLEND)
m = bpy.data.materials.get('mat_lung')
b = m.node_tree.nodes['Principled BSDF']
b.inputs['Base Color'].default_value = (0.55, 0.30, 0.28, 1)
bpy.ops.wm.save_as_mainfile(filepath=S.BLEND)
print('LUNG SAVED')
