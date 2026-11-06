import bpy, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import scene as S
bpy.ops.wm.open_mainfile(filepath=S.BLEND)
CORE = (-0.30, 0.30, -0.19, 0.17, 0.03, 1.72)
for name in S.GROUPS:
    o = bpy.data.objects.get(name)
    if o is None:
        continue
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.mode_set(mode='OBJECT')
    parts = [p for p in bpy.context.selected_objects]
    killed = 0
    keep = []
    for p in parts:
        vs = p.data.vertices
        n = len(vs)
        cx = sum(v.co.x for v in vs) / max(1, n)
        cy = sum(v.co.y for v in vs) / max(1, n)
        cz = sum(v.co.z for v in vs) / max(1, n)
        inside = (CORE[0] <= cx <= CORE[1] and CORE[2] <= cy <= CORE[3]
                  and CORE[4] <= cz <= CORE[5])
        if n < 3000 and not inside:
            killed += 1
            bpy.data.objects.remove(p, do_unlink=True)
        else:
            keep.append(p)
    if keep:
        bpy.ops.object.select_all(action='DESELECT')
        for p in keep:
            p.select_set(True)
        bpy.context.view_layer.objects.active = keep[0]
        if len(keep) > 1:
            bpy.ops.object.join()
        keep[0].name = name
    print('ISLANDS', name, 'parts', len(parts), 'killed', killed)
# deepen muscle + bone materials
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    if bsdf is None:
        continue
    if m.name.startswith('muscle'):
        bsdf.inputs['Base Color'].default_value = (0.34, 0.05, 0.045, 1)
        bsdf.inputs['Roughness'].default_value = 0.5
    if m.name.startswith('bone'):
        bsdf.inputs['Base Color'].default_value = (0.78, 0.71, 0.57, 1)
bpy.ops.wm.save_as_mainfile(filepath=S.BLEND)
print('ISLANDS+MATS SAVED')
