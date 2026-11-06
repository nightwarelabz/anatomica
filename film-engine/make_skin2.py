import bpy, os, sys
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import scene as S

def log(*a):
    print(*a, flush=True)

bpy.ops.wm.open_mainfile(filepath=S.BLEND)
log('STEP open')
src = bpy.data.objects.get('muscle')
dup = src.copy()
dup.data = src.data.copy()
dup.name = 'skin_new'
bpy.context.collection.objects.link(dup)
bpy.ops.object.select_all(action='DESELECT')
dup.select_set(True)
bpy.context.view_layer.objects.active = dup
dup.data.remesh_voxel_size = 0.006
dup.data.use_remesh_fix_poles = True
bpy.ops.object.voxel_remesh()
log('STEP remesh verts', len(dup.data.vertices))
me = dup.data
n = len(me.vertices)
co = np.empty(n * 3)
me.vertices.foreach_get('co', co)
no = np.empty(n * 3)
me.vertices.foreach_get('normal', no)
co = co + no * 0.003
me.vertices.foreach_set('co', co)
me.update()
log('STEP inflate')
for p in me.polygons:
    p.use_smooth = True
mat = bpy.data.materials.get('mat_skin')
dup.data.materials.clear()
dup.data.materials.append(mat)
old = bpy.data.objects.get('skin')
bpy.data.objects.remove(old, do_unlink=True)
dup.name = 'skin'
log('STEP presave')
bpy.ops.wm.save_as_mainfile(filepath=S.BLEND)
log('SKIN REPLACED verts', len(dup.data.vertices))
