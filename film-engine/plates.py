"""ANATOMICA v5 - multi-pass plate rendering (Blender Python).

Renders one plate per call: a single anatomy group (or the room base)
from a locked camera, transparent background for group plates, so the
film can be composited in post with true-3D plates (layer fades,
sweep wipes, heart pulse, breathing - all as plate animation).
  blender -b --python plates.py -- <camera> <group> <out.png> [res] [samples]
camera: main | surg ; group: base|skin|bone|muscle|vessels|heart|
        nerve|brain|lung|organliver|drape_anat
"""
import bpy
import math
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import scene as S

GROUPMAP = {
    'skin': ('skin',),
    'bone': ('bone', 'cartilage'),
    'muscle': ('muscle',),
    'vessels': ('artery', 'vein'),
    'heart': ('heart',),
    'nerve': ('nerve',),
    'brain': ('brain',),
    'lung': ('lung',),
    'organliver': ('organ', 'liver'),
}


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    cam_name, group, out = argv[0], argv[1], argv[2]
    res = int(argv[3]) if len(argv) > 3 else 2560
    samples = int(argv[4]) if len(argv) > 4 else 32
    bpy.ops.wm.open_mainfile(filepath=S.BLEND)
    patient = bpy.data.objects.new('PATIENT', None)
    bpy.context.collection.objects.link(patient)
    groups = {}
    for k in S.GROUPS:
        o = bpy.data.objects.get(k)
        if o:
            o.parent = patient
            groups[k] = o
    table_top = 0.81
    S.build_room(table_top)
    drape = S.build_drape(patient)
    S.add_lights()
    patient.rotation_euler = (-math.pi / 2, 0, 0)
    patient.location = (0, -0.83, table_top + 0.135)
    w = bpy.context.scene.world
    if w is None:
        w = bpy.data.worlds.new('World')
        bpy.context.scene.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = \
        (0.004, 0.007, 0.014, 1)
    # visibility for this plate
    want = GROUPMAP.get(group, ())
    for k, o in groups.items():
        o.hide_render = k not in want
    room_objs = ('floor', 'table', 'table_col', 'table_base', 'pad')
    for name in room_objs:
        o = bpy.data.objects.get(name)
        if o:
            o.hide_render = group != 'base'
    drape.hide_render = group not in ('base', 'drapeonly')
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    bpy.context.scene.camera = cam
    if cam_name == 'main':
        cam.location = (1.55, -2.6, 2.05)
        S.aim(cam, (0, 0.02, 0.9))
        cam.data.lens = 44
    else:
        for lname, e in (('key', 170), ('fill', 40), ('rim', 150),
                         ('surg_spot', 900)):
            lo = bpy.data.objects.get(lname)
            if lo:
                lo.data.energy = e
        cam.location = (0.12, 0.38, 1.78)
        S.aim(cam, (0, 0.47, 0.86))
        cam.data.lens = 44
        from mathutils import Quaternion
        q = cam.rotation_quaternion
        cam.rotation_quaternion = q @ Quaternion((0, 0, 1), -0.45)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.eevee.taa_render_samples = samples
    sc.eevee.shadow_cube_size = '1024'
    sc.eevee.shadow_cascade_size = '1024'
    sc.render.resolution_x = res
    sc.render.resolution_y = int(res * 9 / 16)
    sc.render.film_transparent = group != 'base'
    if group == 'drapeonly':
        sc.render.film_transparent = True
    sc.view_settings.view_transform = 'AgX'
    if cam_name == 'surg':
        sc.view_settings.exposure = -0.3
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.filepath = os.path.abspath(out)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print('PLATE', cam_name, group, 'TIME', round(time.time() - t0, 1),
          '->', out)


if __name__ == '__main__':
    main()
