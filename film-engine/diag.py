import bpy, os, sys, time
argv = sys.argv[sys.argv.index('--') + 1:]
mode = argv[0]
bpy.ops.wm.open_mainfile(filepath=os.path.expanduser('~/workspace/anatomica/blender/patient.blend'))
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.eevee.taa_render_samples = 1
sc.render.resolution_x = 160
sc.render.resolution_y = 90
sc.render.filepath = '/tmp/diag.png'
bpy.ops.object.camera_add(location=(0.4, -3.4, 1.7))
cam = bpy.context.active_object
import mathutils
cam.rotation_euler = mathutils.Vector((0, 0.05, 0.85)).__class__ and (1.25, 0, 0.1)
sc.camera = cam
bpy.ops.object.light_add(type='AREA', location=(1.6, -1.4, 3.2))
bpy.context.active_object.data.energy = 900
vis = {'bone', 'skin'}
if mode in ('L2', 'L3'):
    vis = None
for o in bpy.data.objects:
    if o.type == 'MESH':
        o.hide_render = False if (vis is None or o.name in vis) else True
if mode in ('L1', 'L2', 'L3'):
    sc.eevee.shadow_cube_size = '512'
    sc.eevee.shadow_cascade_size = '512'
else:
    for o in bpy.data.objects:
        if o.type == 'LIGHT':
            o.data.use_shadow = False
if mode == 'L3':
    sc.render.resolution_x = 640
    sc.render.resolution_y = 360
    sc.eevee.taa_render_samples = 8
t0 = time.time()
bpy.ops.render.render(write_still=True)
print('DIAG', mode, 'TIME', round(time.time() - t0, 1))
