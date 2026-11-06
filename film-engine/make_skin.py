import bpy, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import scene as S
bpy.ops.wm.open_mainfile(filepath=S.BLEND)
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
print('REMESH START', flush=True)
bpy.ops.object.voxel_remesh()
print('REMESH DONE verts', len(dup.data.vertices), flush=True)
# slight inflate along normals so the skin clears the muscle surface
me = dup.data
me.update()
for v in me.vertices:
    n = v.normal
    v.co = (v.co.x + n.x * 0.003, v.co.y + n.y * 0.003,
            v.co.z + n.z * 0.003)
for p in me.polygons:
    p.use_smooth = True
mat = bpy.data.materials.get('mat_skin')
dup.data.materials.clear()
dup.data.materials.append(mat)
old = bpy.data.objects.get('skin')
bpy.data.objects.remove(old, do_unlink=True)
dup.name = 'skin'
bpy.ops.wm.save_as_mainfile(filepath=S.BLEND)
print('SKIN REPLACED verts', len(dup.data.vertices), flush=True)
