"""ANATOMICA v5 - scene + stills (Blender Python).

Opens patient.blend, stages the examination room (dark floor, table,
surgical drape, lights), poses the patient supine, and renders one
checkpoint still: A = full-body layered view (Act III look),
B = top-down thoracic procedure field (Act IV look).
  blender -b --python scene.py -- A|B <out.png>
"""
import bpy
import math
import os
import sys

BLEND = os.path.expanduser('~/workspace/anatomica/blender/patient.blend')
GROUPS = ('skin', 'bone', 'cartilage', 'muscle', 'artery', 'vein',
          'heart', 'nerve', 'brain', 'lung', 'liver', 'organ')


def mat_of(obj):
    return obj.data.materials[0]


def set_alpha(obj, a):
    bsdf = obj.data.materials[0].node_tree.nodes['Principled BSDF']
    bsdf.inputs['Alpha'].default_value = a


def _box(name, loc, scale, mat):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(mat)
    return o


def _mat(name, rgb, rough, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m


def build_room(patient_z):
    # patient_z = pad top height (world). Table: slim slab + column.
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = 'floor'
    floor.data.materials.append(
        _mat('floor_mat', (0.004, 0.006, 0.010), 0.55))
    tmat = _mat('table_mat', (0.022, 0.03, 0.04), 0.4, 0.7)
    _box('table', (0, -0.05, patient_z - 0.045), (0.38, 0.98, 0.03), tmat)
    _box('table_col', (-0.22, 0.05, (patient_z - 0.075) / 2),
         (0.10, 0.26, (patient_z - 0.075) / 2), tmat)
    _box('table_base', (-0.22, 0.05, 0.012), (0.20, 0.42, 0.012), tmat)
    _box('pad', (0, -0.05, patient_z - 0.012), (0.34, 0.93, 0.012),
         _mat('pad_mat', (0.012, 0.016, 0.022), 0.85))


def build_drape(patient):
    """Surgical drape in WORLD space (call after posing the patient):
    a cloth mound over pelvis + legs, built as a parametric sheet that
    follows the body's top profile and falls to the pad at the sides.
    Covers the pelvis from every camera the film uses."""
    import math as _m
    pad_top = 0.81
    xs = [-0.36 + 0.72 * i / 16 for i in range(17)]
    ys = [-0.94 + 1.38 * i / 30 for i in range(31)]

    def top_h(y):
        # world-z of the body's top line along its length
        pts = [(-0.94, 0.90), (-0.83, 0.99), (-0.6, 1.01), (-0.35, 1.04),
               (-0.1, 1.10), (0.17, 1.14), (0.30, 1.12), (0.44, 0.88)]
        for (y0, h0), (y1, h1) in zip(pts, pts[1:]):
            if y0 <= y <= y1:
                t = (y - y0) / (y1 - y0)
                return h0 + (h1 - h0) * t + 0.055
        return pts[-1][1]

    def half_w(y):
        return 0.20 + 0.07 * max(0.0, min(1.0, (y + 0.5) / 0.8))

    verts = []
    for y in ys:
        h = top_h(y)
        hw = half_w(y)
        for x in xs:
            t = abs(x) / (hw + 0.10)
            prof = max(0.0, _m.cos(min(1.0, t) * _m.pi / 2)) ** 0.45
            z = pad_top + (h - pad_top) * prof
            verts.append((x, y, z))
    faces = []
    nx = len(xs)
    for j in range(len(ys) - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    me = bpy.data.meshes.new('drape_mesh')
    me.from_pydata(verts, [], faces)
    me.update()
    dr = bpy.data.objects.new('drape', me)
    bpy.context.collection.objects.link(dr)
    sol = dr.modifiers.new('sol', 'SOLIDIFY')
    sol.thickness = 0.008
    for p in me.polygons:
        p.use_smooth = True
    dr.data.materials.append(
        _mat('drape_mat', (0.004, 0.035, 0.045), 1.0))
    return dr


def add_lights():
    def area(name, loc, energy, size, color):
        bpy.ops.object.light_add(type='AREA', location=loc)
        L = bpy.context.active_object
        L.name = name
        L.data.energy = energy
        L.data.shape = 'DISK'
        L.data.size = size
        L.data.color = color
        return L
    key = area('key', (1.8, -1.2, 3.0), 620, 2.0, (1.0, 0.97, 0.92))
    aim(key, (0, 0.05, 0.85))
    fill = area('fill', (-2.4, 0.8, 1.8), 130, 2.4, (0.75, 0.85, 1.0))
    aim(fill, (0, 0.05, 0.85))
    bpy.ops.object.light_add(type='POINT', location=(0, 1.6, 2.4))
    rim = bpy.context.active_object
    rim.name = 'rim'
    rim.data.energy = 280
    rim.data.color = (0.45, 0.65, 1.0)
    bpy.ops.object.light_add(type='SPOT', location=(0, 0.35, 3.4))
    spot = bpy.context.active_object
    spot.name = 'surgical_spot'
    spot.data.energy = 1200
    spot.data.spot_size = 1.0
    spot.data.spot_blend = 0.6
    spot.data.color = (1.0, 0.98, 0.95)
    spot.rotation_euler = (0.12, 0, 0)
    return spot


def aim(obj, target):
    import mathutils
    d = mathutils.Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    which = argv[0] if argv else 'A'
    out = argv[1]
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    patient = bpy.data.objects.new('PATIENT', None)
    bpy.context.collection.objects.link(patient)
    groups = {}
    for k in GROUPS:
        o = bpy.data.objects.get(k)
        if o:
            o.parent = patient
            groups[k] = o
    table_top = 0.81
    build_room(table_top)
    build_drape(patient)
    spot = add_lights()
    # pose: supine, head toward +Y, anterior up
    patient.rotation_euler = (-math.pi / 2, 0, 0)
    patient.location = (0, -0.83, table_top + 0.135)
    # world
    w = bpy.context.scene.world
    if w is None:
        w = bpy.data.worlds.new('World')
        bpy.context.scene.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = \
        (0.004, 0.007, 0.014, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
    # camera
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    bpy.context.scene.camera = cam
    cam.data.lens = 42
    if which == 'A':
        # layered composite: translucent onion of systems
        alphas = {'skin': 0.14, 'bone': 0.9, 'cartilage': 0.7,
                  'muscle': 0.5, 'artery': 1.0, 'vein': 1.0,
                  'heart': 1.0, 'nerve': 1.0, 'brain': 1.0,
                  'lung': 0.85, 'liver': 1.0, 'organ': 0.9}
        for k, a in alphas.items():
            if k in groups:
                set_alpha(groups[k], a)
        cam.location = (0.4, -3.4, 1.7)
        aim(cam, (0, 0.05, 0.85))
        spot.data.energy = 250
    else:
        # procedure field: skin/muscle pulled back (ghost), chest open
        alphas = {'skin': 0.05, 'bone': 1.0, 'cartilage': 0.9,
                  'muscle': 0.16, 'artery': 1.0, 'vein': 1.0,
                  'heart': 1.0, 'nerve': 0.5, 'brain': 1.0,
                  'lung': 0.55, 'liver': 0.8, 'organ': 0.5}
        for k, a in alphas.items():
            if k in groups:
                set_alpha(groups[k], a)
        # chest in rig space: z ~1.32 (supine -> world y ~ +0.49)
        cam.location = (0.15, 0.35, 2.05)
        aim(cam, (0, 0.47, 0.86))
        cam.data.lens = 38
        spot.location = (0.1, 0.5, 2.6)
        spot.data.energy = 1600
    # render settings
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.eevee.taa_render_samples = 32
    sc.eevee.shadow_cube_size = '1024'
    sc.eevee.shadow_cascade_size = '1024'
    sc.render.resolution_x = 1280
    sc.render.resolution_y = 720
    sc.render.filepath = os.path.abspath(out)
    # compositor glare (bloom) for the clinical glow
    sc.use_nodes = True
    nt = sc.node_tree
    nt.nodes.clear()
    rl = nt.nodes.new('CompositorNodeRLayers')
    gl = nt.nodes.new('CompositorNodeGlare')
    gl.glare_type = 'FOG_GLOW'
    gl.quality = 'HIGH'
    gl.threshold = 0.55
    gl.size = 7
    cp = nt.nodes.new('CompositorNodeComposite')
    nt.links.new(rl.outputs['Image'], gl.inputs['Image'])
    nt.links.new(gl.outputs['Image'], cp.inputs['Image'])
    import time
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print('RENDER TIME', round(time.time() - t0, 1), 's ->', out)


if __name__ == '__main__':
    main()
