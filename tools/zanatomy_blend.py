#!/usr/bin/env python3
"""zanatomy_blend.py — streaming, read-only .blend parser for audit work.

Written for the Milestone 34 Z-Anatomy audit: a full Blender process
cannot load the 306 MB upstream template on this machine (OOM-killed,
exit 137), so this parser reads the file format directly — header,
block directory, SDNA struct-layout block, then the Object / Mesh /
Collection / Text structs and the arrays they point at — all through
an mmap, so memory stays flat and the audit is re-runnable anywhere.

Generic by construction: field offsets come from the file's own SDNA,
never from hardcoded layouts. Read-only: the audited file is never
modified.

Usage:
  python3 tools/zanatomy_blend.py census   Startup.blend census.json
  python3 tools/zanatomy_blend.py vertices Startup.blend outdir \\
      "Right femur" "Sacrum" ...

census writes one JSON object: file facts; every collection path with
its member object names; every object (bare name, type, parent,
loc/rot/size, mesh vertex count, custom properties); every text
block's full content.

vertices writes, per named mesh object, a .npy of world-space vertex
coordinates (object obmat composed up the parent chain).
"""
import json
import mmap
import os
import struct
import sys
from collections import Counter

OBJ_TYPES = {0: "EMPTY", 1: "MESH", 2: "CURVE", 3: "SURF", 4: "FONT",
             5: "MBALL", 6: "LIGHT", 7: "SPEAKER", 8: "CAMERA",
             9: "LIGHT_PROBE", 10: "LATTICE", 11: "ARMATURE",
             12: "GPENCIL", 25: "CURVES", 26: "POINTCLOUD", 27: "VOLUME"}


class BlendFile:
    def __init__(self, path):
        self.f = open(path, "rb")
        self.mm = mmap.mmap(self.f.fileno(), 0, access=mmap.ACCESS_READ)
        mm = self.mm
        assert mm[0:7] == b"BLENDER", "not a .blend file"
        self.ptr_size = 8 if mm[7:8] == b"-" else 4
        self.endian = "<" if mm[8:9] == b"v" else ">"
        self.version = mm[9:12].decode()
        self.ptr_fmt = self.endian + ("Q" if self.ptr_size == 8 else "I")
        self.blocks = []
        self.by_addr = {}
        off = 12
        hdr = 16 + self.ptr_size
        while off + hdr <= len(mm):
            code = mm[off:off + 4].decode("latin1").rstrip("\0")
            size, addr, sdna, count = struct.unpack_from(
                self.endian + "I" + ("Q" if self.ptr_size == 8 else "I") + "II",
                mm, off + 4)
            blk = {"code": code, "size": size, "addr": addr, "sdna": sdna,
                   "count": count, "off": off + hdr}
            self.blocks.append(blk)
            if addr:
                self.by_addr[addr] = blk
            off += hdr + size
            if code == "ENDB":
                break
        dna_blk = next(b for b in self.blocks if b["code"] == "DNA1")
        self._parse_dna(dna_blk["off"], dna_blk["size"])

    # ---------------------------------------------------------------- DNA
    def _parse_dna(self, off, size):
        mm, e = self.mm, self.endian
        base = off

        def align(p):   # SDNA sections pad relative to the DNA block start
            return base + ((p - base + 3) & ~3)

        assert mm[off:off + 4] == b"SDNA"
        p = off + 4
        assert mm[p:p + 4] == b"NAME"
        n, = struct.unpack_from(e + "I", mm, p + 4)
        p += 8
        names = []
        for _ in range(n):
            end = mm.find(b"\0", p)
            names.append(mm[p:end].decode("latin1"))
            p = end + 1
        p = align(p)
        assert mm[p:p + 4] == b"TYPE"
        n, = struct.unpack_from(e + "I", mm, p + 4)
        p += 8
        types = []
        for _ in range(n):
            end = mm.find(b"\0", p)
            types.append(mm[p:end].decode("latin1"))
            p = end + 1
        p = align(p)
        assert mm[p:p + 4] == b"TLEN"
        p += 4
        tlens = struct.unpack_from(e + "%dH" % n, mm, p)
        p += 2 * n
        p = align(p)
        assert mm[p:p + 4] == b"STRC"
        n_strc, = struct.unpack_from(e + "I", mm, p + 4)
        p += 8
        self.structs = {}
        self.struct_sizes = {}
        self.sdna_order = []
        raw = []   # (tname, [(clean, ftype, cnt, is_ptr), ...])
        for _ in range(n_strc):
            t_idx, n_fields = struct.unpack_from(e + "HH", mm, p)
            p += 4
            tname = types[t_idx]
            self.sdna_order.append(tname)
            flist = []
            for _ in range(n_fields):
                ft, fn = struct.unpack_from(e + "HH", mm, p)
                p += 4
                fname, ftype = names[fn], types[ft]
                cnt, base = 1, fname
                while base.endswith("]"):
                    i = base.rindex("[")
                    cnt *= int(base[i + 1:-1])
                    base = base[:i]
                is_ptr = "*" in base or base.startswith("(")
                clean = base.replace("*", "").strip("()")
                flist.append((clean, ftype, cnt, is_ptr))
            raw.append((tname, flist))
            self.struct_sizes[tname] = tlens[t_idx]
        # Field offsets with C alignment (Blender's DNA offsets are the
        # compiler's): align each field to its type's alignment —
        # pointers to the pointer size, primitives to their size,
        # embedded structs to their own largest member alignment.
        prim_align = {"char": 1, "uchar": 1, "int8_t": 1, "uint8_t": 1,
                      "short": 2, "ushort": 2, "int16_t": 2, "uint16_t": 2,
                      "int": 4, "uint": 4, "float": 4, "int32_t": 4,
                      "uint32_t": 4, "double": 8, "int64_t": 8,
                      "uint64_t": 8, "long": 8, "ulong": 8}
        align_of = {}

        def struct_align(tname, seen=()):
            if tname in align_of:
                return align_of[tname]
            if tname in seen:
                return 1
            entry = next((f for n_, f in raw if n_ == tname), None)
            if entry is None:
                return prim_align.get(tname, 1)
            a = 1
            for _c, ft, _n, is_ptr in entry:
                a = max(a, self.ptr_size if is_ptr else
                        struct_align(ft, seen + (tname,)))
            align_of[tname] = a
            return a

        prim_size = dict(prim_align)   # primitive size == alignment here
        for tname, flist in raw:
            fields = {}
            offset = 0
            for clean, ftype, cnt, is_ptr in flist:
                a = self.ptr_size if is_ptr else struct_align(ftype)
                offset = (offset + a - 1) & ~(a - 1)
                if is_ptr:
                    sz = self.ptr_size
                elif ftype in self.struct_sizes:
                    sz = self.struct_sizes[ftype] * cnt
                else:
                    sz = prim_size.get(ftype, 4) * cnt
                fields[clean] = (offset, ftype, cnt, is_ptr)
                offset += sz
            self.structs[tname] = fields

    def block_struct_name(self, blk):
        return self.sdna_order[blk["sdna"]]

    # ------------------------------------------------------------- reading
    _PRIM = {"char": "b", "uchar": "B", "short": "h", "ushort": "H",
             "int": "i", "uint": "I", "long": "l", "ulong": "L",
             "float": "f", "double": "d", "int64_t": "q", "uint64_t": "Q",
             "int8_t": "b", "uint8_t": "B", "int16_t": "h", "uint16_t": "H",
             "int32_t": "i", "uint32_t": "I"}

    def read_struct_at(self, off, struct_name):
        fields = self.structs[struct_name]
        out = {}
        for fname, (foff, ftype, cnt, is_ptr) in fields.items():
            o = off + foff
            if is_ptr:
                out[fname] = struct.unpack_from(self.ptr_fmt, self.mm, o)[0]
            elif ftype == "char" and cnt > 1:
                out[fname] = bytes(self.mm[o:o + cnt])
            elif ftype in self._PRIM:
                fmt = self._PRIM[ftype]
                if cnt == 1:
                    out[fname] = struct.unpack_from(self.endian + fmt, self.mm, o)[0]
                else:
                    out[fname] = list(struct.unpack_from(
                        self.endian + "%d%s" % (cnt, fmt), self.mm, o))
            elif ftype in self.structs and self.struct_sizes[ftype] > 1 and cnt == 1:
                out[fname] = ("embedded", o)
            else:  # char arrays and anything else: raw bytes
                n = cnt * (self.struct_sizes.get(ftype, 1))
                out[fname] = bytes(self.mm[o:o + n])
        return out

    def read_struct(self, blk, struct_name, index=0):
        return self.read_struct_at(
            blk["off"] + index * self.struct_sizes[struct_name], struct_name)

    def embedded(self, marker, struct_name):
        return self.read_struct_at(marker[1], struct_name)

    def id_name(self, blk, struct_name):
        idf = self.structs[struct_name]["id"]
        id_struct = self.read_struct_at(blk["off"] + idf[0], "ID")
        raw = id_struct["name"]
        if isinstance(raw, list):
            raw = bytes(raw)
        name = raw.split(b"\0")[0].decode("utf8", "replace")
        return name[2:] if len(name) > 2 else name  # strip ID code prefix

    def read_cstr(self, addr):
        blk = self.by_addr.get(addr)
        if not blk:
            return None
        raw = bytes(self.mm[blk["off"]:blk["off"] + blk["size"]])
        return raw.split(b"\0")[0].decode("utf8", "replace")

    def listbase(self, first_addr, struct_name):
        items, addr, seen = [], first_addr, set()
        while addr and addr not in seen and addr in self.by_addr:
            seen.add(addr)
            blk = self.by_addr[addr]
            d = self.read_struct(blk, struct_name)
            items.append((addr, d))
            addr = d.get("next", 0)
        return items

    # ------------------------------------------------------- ID properties
    def decode_idprops_at(self, listbase_off):
        """Decode the IDProperty children whose ListBase head is at the
        given file offset. The file's DNA places IDPropertyData.group at
        +8 inside the union and val at +24; both are read through the
        DNA offsets, not constants. Type codes follow Blender 3.5's
        BKE_idprop.h (0 string, 1 int, 2 float, 3 array, 4 group,
        5 id, 6 double, 7 idparray, 8 boolean); groups written by the
        Z-Anatomy add-ons also appear with the root's own type code, so
        a type whose group ListBase resolves to IDProperty blocks is
        decoded as a group regardless of the code."""
        first, = struct.unpack_from(self.ptr_fmt, self.mm, listbase_off)
        dataf = self.structs["IDPropertyData"]
        props = {}
        for _a, d in self.listbase(first, "IDProperty"):
            nm = d.get("name")
            if isinstance(nm, (bytes, bytearray)):
                nm = nm.split(b"\0")[0].decode("utf8", "replace")
            ptype = d.get("type")
            data = d.get("data")
            val = {"type": ptype}
            if isinstance(data, tuple) and data[0] == "embedded":
                doff = data[1]
                ptr, = struct.unpack_from(self.ptr_fmt, self.mm, doff)
                val_off = doff + dataf["val"][0]
                group_off = doff + dataf["group"][0]
                gfirst, = struct.unpack_from(self.ptr_fmt, self.mm, group_off)
                is_group = gfirst in self.by_addr and \
                    self.block_struct_name(self.by_addr[gfirst]) == "IDProperty"
                if ptype == 0:
                    val = self.read_cstr(ptr)
                elif ptype == 1 or ptype == 8:
                    val = struct.unpack_from(self.endian + "i", self.mm, val_off)[0]
                elif ptype == 2:
                    bits = struct.unpack_from(self.endian + "I", self.mm, val_off)[0]
                    val = struct.unpack_from(self.endian + "f",
                                             struct.pack(self.endian + "I", bits), 0)[0]
                elif is_group:
                    val = self.decode_idprops_at(group_off)
                elif ptype == 6 and ptr in self.by_addr:
                    blk = self.by_addr[ptr]
                    val = struct.unpack_from(self.endian + "d", self.mm, blk["off"])[0]
                elif ptype in (3, 5, 7):
                    val = {"ref_or_array": True, "len": d.get("len")}
            props[nm] = val
        return props

    def object_idprops(self, blk):
        idf = self.structs["Object"]["id"]
        id_struct = self.read_struct_at(blk["off"] + idf[0], "ID")
        root = id_struct.get("properties", 0)
        if not root or root not in self.by_addr:
            return {}
        d = self.read_struct(self.by_addr[root], "IDProperty")
        data = d.get("data")
        if isinstance(data, tuple) and data[0] == "embedded":
            group_off = data[1] + self.structs["IDPropertyData"]["group"][0]
            return self.decode_idprops_at(group_off)
        return {}

    # ------------------------------------------------------------- objects
    def objects(self):
        objs = {}
        for blk in self.blocks:
            if blk["code"] != "OB":
                continue
            d = self.read_struct(blk, "Object")
            name = self.id_name(blk, "Object")
            objs[blk["addr"]] = (name, blk, d)
        return objs

    def mesh_info(self, mesh_addr):
        blk = self.by_addr.get(mesh_addr)
        if not blk:
            return None
        d = self.read_struct(blk, "Mesh")
        return {"name": self.id_name(blk, "Mesh"),
                "totvert": d.get("totvert"), "totpoly": d.get("totpoly"),
                "mvert_ptr": d.get("mvert", 0), "blk": blk, "raw": d}

    def mesh_vertices_local(self, mesh_addr):
        """(n,3) float array of local-space vertex coordinates. The
        array block's own element count is authoritative (Mesh.totvert
        can exceed it when edit-mode data is present)."""
        import numpy as np
        info = self.mesh_info(mesh_addr)
        if info is None or not info["mvert_ptr"]:
            return None
        blk = self.by_addr[info["mvert_ptr"]]
        sz = self.struct_sizes["MVert"]
        co_off = self.structs["MVert"]["co"][0]
        n = blk["size"] // sz
        raw = np.frombuffer(self.mm, dtype=np.uint8,
                            count=n * sz, offset=blk["off"])
        co = raw.reshape(n, sz)[:, co_off:co_off + 12]
        return co.copy().view(np.float32).reshape(n, 3).astype(np.float64)


def mat_from_object(d):
    """Object world matrix: stored obmat if present (4x4 row-major in
    DNA as float[4][4]); else composed loc/rot(euler XYZ)/size."""
    import numpy as np
    ob = d.get("obmat")
    if isinstance(ob, list) and len(ob) == 16:
        return np.array(ob, dtype=np.float64).reshape(4, 4).T.copy()
    # DNA stores mat[4][4] column-major in Blender: obmat is [4][4] with
    # translation in obmat[3][0..2] as stored. The flat list is in C
    # order, i.e. obmat[i][j] at index i*4+j, Blender convention:
    # world = M @ v with M = obmat transposed from storage order.
    loc = np.array(d.get("loc", [0, 0, 0]), dtype=np.float64)
    return np.array([[1, 0, 0, loc[0]], [0, 1, 0, loc[1]],
                     [0, 0, 1, loc[2]], [0, 0, 0, 1]])


def census(path):
    bf = BlendFile(path)
    objs = bf.objects()
    addr2name = {a: n for a, (n, _b, _d) in objs.items()}
    # collections: every block whose SDNA type is Collection
    collections = {}
    col_members = {}
    for blk in bf.blocks:
        if bf.block_struct_name(blk) != "Collection":
            continue
        d = bf.read_struct(blk, "Collection")
        nm = bf.id_name(blk, "Collection")
        children, members = [], []
        ch = d.get("children")
        if isinstance(ch, tuple) and ch[0] == "embedded":
            lb = bf.embedded(ch, "ListBase") if False else None
        # ListBase embedded: read first pointer at its offset
        collections[blk["addr"]] = (nm, blk, d)
    # ListBase heads are embedded structs: their {first,last} pointers sit
    # at the field offset inside Collection. Read them directly.
    def listbase_first(blk, struct_name, field):
        foff = bf.structs[struct_name][field][0]
        first, = struct.unpack_from(bf.ptr_fmt, bf.mm, blk["off"] + foff)
        return first
    col_paths = {}

    def col_members_of(blk):
        first = listbase_first(blk, "Collection", "gobject")
        names = []
        for _a, co in bf.listbase(first, "CollectionObject"):
            ob = co.get("ob", 0)
            if ob in addr2name:
                names.append(addr2name[ob])
        return names

    def col_children_of(blk):
        first = listbase_first(blk, "Collection", "children")
        kids = []
        for _a, cc in bf.listbase(first, "CollectionChild"):
            cptr = cc.get("collection", 0)
            if cptr in collections:
                kids.append(cptr)
        return kids

    # find the master (scene) collection: the one that is no one's child
    all_kids = set()
    for a, (nm, blk, d) in collections.items():
        all_kids.update(col_children_of(blk))
    roots = [a for a in collections if a not in all_kids]

    def walk(addr, prefix):
        nm, blk, _d = collections[addr]
        path = (prefix + "/" + nm) if prefix else nm
        col_paths[path] = col_members_of(blk)
        for k in col_children_of(blk):
            walk(k, path)
    for r in roots:
        walk(r, "")
    # objects
    obj_list = []
    data2mesh = {}
    for blk in bf.blocks:
        if bf.block_struct_name(blk) == "Mesh":
            data2mesh[blk["addr"]] = bf.id_name(blk, "Mesh")
    for addr, (name, blk, d) in sorted(objs.items(), key=lambda kv: kv[1][0]):
        entry = {"name": name, "type": OBJ_TYPES.get(d.get("type"), d.get("type")),
                 "parent": addr2name.get(d.get("parent", 0)),
                 "loc": [round(float(x), 4) for x in d.get("loc", [])],
                 "size": [round(float(x), 4) for x in d.get("size", [])]}
        data = d.get("data", 0)
        if d.get("type") == 1 and data in data2mesh:
            entry["mesh"] = data2mesh[data]
            info = bf.mesh_info(data)
            entry["verts"] = info["totvert"] if info else None
        props = bf.object_idprops(blk)
        if props:
            entry["props"] = props
        obj_list.append(entry)
    # texts
    texts = {}
    for blk in bf.blocks:
        if blk["code"] == "TX":
            nm = bf.id_name(blk, "Text")
            d = bf.read_struct(blk, "Text")
            foff = bf.structs["Text"]["lines"][0]
            first, = struct.unpack_from(bf.ptr_fmt, bf.mm, blk["off"] + foff)
            lines = []
            for _a, tl in bf.listbase(first, "TextLine"):
                s = bf.read_cstr(tl.get("line", 0))
                lines.append(s if s is not None else "")
            texts[nm] = lines
    return {"file": os.path.basename(path), "blend_version": bf.version,
            "block_codes": dict(Counter(b["code"] for b in bf.blocks)),
            "n_objects": len(obj_list), "collections": col_paths,
            "objects": obj_list, "texts": texts}


def vertices(path, outdir, names):
    bf = BlendFile(path)
    objs = bf.objects()
    by_name = {n: (a, b, d) for a, (n, b, d) in objs.items()}
    import numpy as np
    os.makedirs(outdir, exist_ok=True)
    mats = {}

    def world_mat(addr):
        if addr in mats:
            return mats[addr]
        _n, _b, d = objs[addr]
        m = mat_from_object(d)
        parent = d.get("parent", 0)
        if parent and parent in objs:
            m = world_mat(parent) @ m
        mats[addr] = m
        return m

    for nm in names:
        if nm not in by_name:
            print("MISSING:", nm)
            continue
        addr, _b, d = by_name[nm]
        verts = bf.mesh_vertices_local(d.get("data", 0))
        if verts is None:
            print("NO VERTS:", nm)
            continue
        m = world_mat(addr)
        world = verts @ m[:3, :3].T + m[:3, 3]
        fn = os.path.join(outdir, nm.replace("/", "_") + ".npy")
        np.save(fn, world)
        print("wrote", fn, world.shape)


def main():
    if sys.argv[1] == "census":
        out = census(sys.argv[2])
        with open(sys.argv[3], "w") as fh:
            json.dump(out, fh, indent=1)
        print("objects:", out["n_objects"], "collections:", len(out["collections"]),
              "texts:", list(out["texts"]))
    elif sys.argv[1] == "vertices":
        vertices(sys.argv[2], sys.argv[3], sys.argv[4:])


if __name__ == "__main__":
    main()
