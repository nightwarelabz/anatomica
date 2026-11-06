"""ANATOMICA v5 - patient assembly (Blender Python).

Builds the patient from the Z-Anatomy GLB set (native model space -
the peripheral nervous system is registered by construction, which
fixes the v4 cross-model nerve errors) plus the BodyParts3D skin
warped into the same frame (anatlas/skin_za.obj). Meshes are joined
into film groups and given clinical materials. Run inside Blender:
  blender -b --python patient.py -- <out.blend>
Anatomy: Z-Anatomy (CC BY-SA 4.0) + BodyParts3D (DBCLS, CC BY 4.0).
Local only; nothing published without Chase's approval.
"""
import bpy
import math
import os
import sys

ZA = os.path.expanduser('~/workspace/anatlas/za/public/models')
SKIN_OBJ = os.path.expanduser('~/workspace/anatlas/skin_za.obj')

BRAIN_KEYS = ('cerebr', 'cerebellum', 'ventricle', 'capsule', 'thalam',
              'hypothal', 'hippocamp', 'amygdala', 'caudate', 'putamen',
              'globus', 'claustrum', 'corpus callosum', 'fornix', 'pineal',
              'pituitary', 'brain', 'midbrain', 'pons', 'medulla', 'insula',
              'cingulate', 'lobe', 'gyrus', 'sulcus', 'white matter',
              'gray matter', 'grey matter', 'lemniscus', 'nucleus',
              'olive', 'pyramid of medulla', 'tract')


def classify(system, name):
    n = name.lower()
    if system == 'skeletal':
        return 'bone'
    if system == 'joints':
        return 'cartilage'
    if system == 'muscular':
        if any(k in n for k in ('fascia', 'aponeurosis', 'septum')):
            return None
        return 'muscle'
    if system == 'cardiovascular':
        if any(k in n for k in ('atrium', 'ventricle', 'papillary',
                                'coronary', 'myocard', 'aortic valve',
                                'mitral', 'tricuspid', 'pulmonary valve',
                                'chordae', 'heart')):
            return 'heart'
        if any(k in n for k in ('vein', 'vena', 'venous', 'sinus',
                                'jugular', 'saphenous', 'cephalic',
                                'basilic', 'azygos', 'caval', 'portal')):
            return 'vein'
        return 'artery'
    if system == 'nervous':
        if any(k in n for k in BRAIN_KEYS):
            return 'brain'
        return 'nerve'
    if system == 'visceral':
        if any(k in n for k in ('lung', 'bronch', 'trachea', 'pleura')):
            return 'lung'
        if any(k in n for k in ('liver', 'hepatic', 'gallbladder',
                                'bile', 'cystic duct')):
            return 'liver'
        return 'organ'
    return None


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_system(system):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(
        filepath=os.path.join(ZA, system + '.glb'),
        import_pack_images=False)
    new = [o for o in bpy.data.objects if o not in before]
    groups = {}
    for o in new:
        if o.type != 'MESH':
            continue
        g = classify(system, o.name)
        if g is None:
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        groups.setdefault(g, []).append(o)
        o.name = f'{g}__{o.name}'
    return groups


def join_group(objects, name):
    if not objects:
        return None
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1:
        bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = name
    # bake ALL transforms (incl. location) so the group sits at the
    # origin with world-space geometry - the film rig poses it exactly
    bpy.ops.object.transform_apply(location=True, rotation=True,
                                   scale=True)
    return joined


MAT_DEFS = {
    # name: (base rgb, roughness, metallic, emission rgb, emission str,
    #        subsurface)
    'skin':      ((0.72, 0.52, 0.42), 0.55, 0.0, (0, 0, 0), 0.0, 0.35),
    'bone':      ((0.87, 0.82, 0.70), 0.5, 0.0, (0, 0, 0), 0.0, 0.08),
    'cartilage': ((0.62, 0.70, 0.78), 0.4, 0.0, (0, 0, 0), 0.0, 0.15),
    'muscle':    ((0.48, 0.10, 0.09), 0.42, 0.0, (0, 0, 0), 0.0, 0.25),
    'artery':    ((0.75, 0.10, 0.08), 0.3, 0.0, (0.35, 0.02, 0.01), 0.25, 0.1),
    'vein':      ((0.16, 0.28, 0.62), 0.3, 0.0, (0.01, 0.03, 0.2), 0.25, 0.1),
    'heart':     ((0.62, 0.12, 0.11), 0.32, 0.0, (0.4, 0.03, 0.02), 0.3, 0.2),
    'nerve':     ((0.92, 0.68, 0.18), 0.35, 0.0, (0.55, 0.36, 0.03), 0.55, 0.0),
    'brain':     ((0.80, 0.66, 0.58), 0.5, 0.0, (0, 0, 0), 0.0, 0.3),
    'lung':      ((0.72, 0.42, 0.40), 0.5, 0.0, (0, 0, 0), 0.0, 0.3),
    'liver':     ((0.42, 0.13, 0.12), 0.38, 0.0, (0, 0, 0), 0.0, 0.25),
    'organ':     ((0.66, 0.50, 0.38), 0.5, 0.0, (0, 0, 0), 0.0, 0.25),
}


def make_material(key):
    mat = bpy.data.materials.new('mat_' + key)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    rgb, rough, metal, erg, estr, subs = MAT_DEFS[key]
    bsdf.inputs['Base Color'].default_value = (*rgb, 1.0)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if subs > 0:
        try:
            bsdf.inputs['Subsurface Weight'].default_value = subs
            bsdf.inputs['Subsurface Radius'].default_value = (0.6, 0.25, 0.15)
        except KeyError:
            pass
    if estr > 0:
        try:
            bsdf.inputs['Emission Color'].default_value = (*erg, 1.0)
            bsdf.inputs['Emission Strength'].default_value = estr
        except KeyError:
            pass
    try:
        mat.surface_render_method = 'DITHERED'
    except Exception:
        try:
            mat.blend_method = 'BLEND'
        except Exception:
            pass
    return mat


def set_alpha(mat, a):
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Alpha'].default_value = a


def build_patient():
    reset_scene()
    all_groups = {}
    for system in ('skeletal', 'joints', 'muscular', 'cardiovascular',
                   'nervous', 'visceral'):
        g = import_system(system)
        for k, objs in g.items():
            all_groups.setdefault(k, []).extend(objs)
        print('imported', system, {k: len(v) for k, v in g.items()})
    # skin (BodyParts3D warped into ZA frame; OBJ axis -> Blender frame)
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=SKIN_OBJ)
    for o in bpy.data.objects:
        if o not in before and o.type == 'MESH':
            me = o.data
            for v in me.vertices:
                x, y, z = v.co.x, v.co.y, v.co.z
                v.co = (x, -z, y)
            o.name = 'skin'
            all_groups['skin'] = [o]
    patient = {}
    for key in ('skin', 'bone', 'cartilage', 'muscle', 'artery', 'vein',
                'heart', 'nerve', 'brain', 'lung', 'liver', 'organ'):
        objs = all_groups.get(key, [])
        if not objs:
            print('WARNING: empty group', key)
            continue
        joined = join_group(objs, key)
        mat = make_material(key)
        joined.data.materials.clear()
        joined.data.materials.append(mat)
        patient[key] = joined
        print('group', key, 'verts',
              sum(len(o.data.vertices) for o in [joined]))
    return patient


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    build_patient()
    if argv:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(argv[0]))
    print('PATIENT BUILT')
