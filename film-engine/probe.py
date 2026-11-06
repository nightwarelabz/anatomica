import bpy, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import scene as S
import math
bpy.ops.wm.open_mainfile(filepath=S.BLEND)
patient = bpy.data.objects.new('PATIENT', None)
bpy.context.collection.objects.link(patient)
groups = {}
for k in S.GROUPS:
    o = bpy.data.objects.get(k)
    if o:
        o.parent = patient
        groups[k] = o
S.build_room(0.81)
dr = S.build_drape(patient)
patient.rotation_euler = (-math.pi / 2, 0, 0)
patient.location = (0, -0.83, 0.81 + 0.135)
bpy.context.view_layer.update()
mw = patient.matrix_world
bone = groups['bone']
import mathutils
tops = {}
for v in bone.data.vertices:
    w = mw @ v.co
    key = round(w.y / 0.2) * 0.2
    if abs(w.x) < 0.06:
        tops[key] = max(tops.get(key, 0), w.z)
print('BONE top z by world-y (|x|<0.06):')
for k in sorted(tops):
    print('  y', k, 'top', round(tops[k], 3))
dv = {}
for v in dr.data.vertices:
    key = round(v.co.y / 0.2) * 0.2
    if abs(v.co.x) < 0.04:
        dv[key] = max(dv.get(key, 0), v.co.z)
print('DRAPE ridge z by world-y:')
for k in sorted(dv):
    print('  y', k, 'z', round(dv[k], 3))
