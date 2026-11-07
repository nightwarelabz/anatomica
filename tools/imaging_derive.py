#!/usr/bin/env python3
"""ANATOMICA imaging derivation — Milestone 19 (Imaging v1).

Derives a synthetic, DICOM-structured CT series + web-shell slice data
from ONE TotalSegmentator v1.0 subject already held locally (M3
intake). The subject's segmentation label map is crosswalked to Body
Model record ids using ONLY mappings established by earlier
milestones:

  - skeletal labels: the label->record rules of Milestone 3, read back
    from data/sources/totalsegmentator-1.0/labels.json
    (skeletal_overlap) and re-asserted against tools/ts_census.py;
  - non-skeletal labels: the `totalsegmentator_overlap` blocks
    adjudicated into the per-system inventory files by Milestones
    5 and 9-15;
  - every other label stays a source label, flagged unmapped. The
    muscular tranche (M4) recorded no overlap block and Milestone 3
    deliberately mapped `face` to no record, so those 11 labels are
    unmapped here; same-name records, where they exist, are listed
    as *unadjudicated candidates* only — the viewer never opens a
    record from a candidate.

Pixel data: the subject's own CT intensities (Hounsfield units as
stored: int32, scl_slope 1, scl_inter 0). The ONLY alteration before
output is (a) an int32->int16 conversion, asserted lossless for this
subject (every stored value inside int16 range), and (b) the burned-in
SYNTHETIC watermark glyphs in the top-left corner of every slice
(design/06 watermarking rule), applied AFTER all HU statistics are
computed from the unaltered values. No intensity remapping, no
resampling: geometry (1.5 mm isotropic spacing, dimensions) is the
source's, re-expressed in DICOM LPS coordinates.

Orientation: NIfTI voxel order (i,j,k) = (+x RAS right, +y anterior,
+z superior). The stored order used by BOTH the DICOM files and the
web bins flips both in-plane axes (c = nx-1-i, r = ny-1-j), which
yields the standard DICOM axial display (ImageOrientationPatient
[1,0,0, 0,1,0]: patient left on screen right, anterior up) and a
canvas that matches a DICOM viewer's rendering.

Outputs:
  data/imaging/<subject>/dicom/*.dcm        DICOM PS3.10 file set
  data/imaging/<subject>/series.json        derivation manifest
  data/imaging/<subject>/crosswalk.json     label->record accounting
  web/data/imaging.json                     web-shell manifest — combined
                                            (Milestone 32): shared meta +
                                            one block per derived subject;
                                            deriving a subject merges its
                                            block in, preserving the others
  web/data/imaging/<subject>/hu-XXXX.bin    int16 HU per slice
  web/data/imaging/<subject>/lbl-XXXX.bin   uint8 label index/slice

Dependency note: earlier ANATOMICA tools are stdlib-only; this one
uses numpy (1.26.4, present in the environment) because the pipeline
streams ~3 GB of voxel data. Everything else is stdlib.
"""
import colorsys
import csv
import gzip
import hashlib
import io
import json
import os
import struct
import sys
import uuid
from datetime import datetime, timezone

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TS_DIR = os.path.join(ROOT, "data", "sources", "totalsegmentator-1.0")
SUBJECT = sys.argv[1] if len(sys.argv) > 1 else "s0778"
# Milestone label for THIS derivation (argv 2). Defaults preserve the
# Milestone 19 derivation of s0778 exactly; Milestone 32 derives the
# second subject with "Milestone 32".
MILESTONE = sys.argv[2] if len(sys.argv) > 2 else "Milestone 19"
MTAG = "M" + MILESTONE.split()[-1]
SUBJ_DIR = os.path.join(TS_DIR, "subset", "Totalsegmentator_dataset", SUBJECT)
# Why this subject was chosen, recorded in its series.json. Subjects
# are picked by the Milestone 19 rule — most non-empty label masks of
# the locally held subjects (M19), then of the remaining ones (M32).
SELECTION_REASONS = {
    "s0778": ("most complete of the 10 locally held subjects: "
              "98 of 104 label masks non-empty (next best 95); "
              "thorax-abdomen-pelvis coverage, 646.5 mm z-extent"),
    "s1090": ("second subject (Milestone 32), chosen by the Milestone 19 "
              "rule applied to the nine remaining locally held subjects: "
              "most non-empty label masks, 95 of 104 (next best remaining "
              "subject s0480 with 71); thorax-abdomen-pelvis coverage, "
              "658.5 mm z-extent. Full ranking table in MILESTONE-32.md"),
}
WATERMARK_VALUE = 3071  # 12-bit maximum; white under every shipped preset

# 5x7 bitmap font (rows top->bottom, 5 bits each) for "SYNTHETIC".
FONT = {
    "S": ["01110", "10001", "10000", "01110", "00001", "10001", "01110"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
}
WM_TEXT = "SYNTHETIC"
WM_ORIGIN = (6, 6)  # (row, col) in stored orientation


def watermark_offsets():
    offs = []
    for ci, ch in enumerate(WM_TEXT):
        for gr, row in enumerate(FONT[ch]):
            for gc, bit in enumerate(row):
                if bit == "1":
                    offs.append([WM_ORIGIN[0] + gr, WM_ORIGIN[1] + ci * 6 + gc])
    return offs


# ---------------------------------------------------------------- NIfTI ----
def read_nifti(path):
    """Minimal NIfTI-1 reader (gzip or plain). Returns (array[z,y,x],
    header dict). Asserts the axis-aligned sform these files carry."""
    raw = gzip.open(path, "rb").read() if path.endswith(".gz") else open(path, "rb").read()
    assert struct.unpack("<i", raw[0:4])[0] == 348, path
    dim = struct.unpack("<8h", raw[40:56])
    nd, nx, ny, nz = dim[0], dim[1], dim[2], dim[3]
    assert nd == 3, (path, dim)
    datatype = struct.unpack("<h", raw[70:72])[0]
    voxoff = int(struct.unpack("<f", raw[108:112])[0])
    slope = struct.unpack("<f", raw[112:116])[0]
    inter = struct.unpack("<f", raw[116:120])[0]
    srow = [struct.unpack("<4f", raw[280 + 16 * i:296 + 16 * i]) for i in range(3)]
    typ = {2: np.uint8, 4: np.int16, 8: np.int32, 16: np.float32}[datatype]
    a = np.frombuffer(raw, dtype=typ, count=nx * ny * nz, offset=voxoff)
    a = a.reshape((nz, ny, nx))
    if slope not in (0.0, 1.0) or inter != 0.0:
        a = a.astype(np.float32) * (slope or 1.0) + inter
    hdr = {"dim": (nx, ny, nz), "srow": srow, "slope": slope, "inter": inter,
           "datatype": datatype}
    return a, hdr


def affine_of(hdr):
    """Voxel (i,j,k) -> RAS mm, asserting a diagonal sform."""
    (sx, _, _, ox), (_, sy, _, oy), (_, _, sz, oz) = [
        (r[0], r[1], r[2], r[3]) for r in hdr["srow"]]
    flat = [hdr["srow"][0][1], hdr["srow"][0][2], hdr["srow"][1][0],
            hdr["srow"][1][2], hdr["srow"][2][0], hdr["srow"][2][1]]
    assert all(v == 0.0 for v in flat), "non-diagonal sform not supported"
    assert sx > 0 and sy > 0 and sz > 0, "negative axis step not supported"
    return (sx, sy, sz), (ox, oy, oz)


# ------------------------------------------------------------- crosswalk ----
def build_crosswalk(records_by_key):
    census = json.load(open(os.path.join(TS_DIR, "labels.json")))
    labels = sorted(census["labels"])
    skel = dict(census["skeletal_overlap"])
    # re-assert the M3 rules reproduce the stored overlap exactly
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from ts_census import skeletal_record, SYSTEM_GROUPS
    for lab in labels:
        r = skeletal_record(lab)
        assert (r is None and lab not in skel) or skel.get(lab) == r, lab
    blocks = {}

    def find(o):
        if isinstance(o, dict):
            if "totalsegmentator_overlap" in o:
                yield o["totalsegmentator_overlap"]
            for v in o.values():
                yield from find(v)
        elif isinstance(o, list):
            for v in o:
                yield from find(v)

    import glob
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "*", "*-inventory.json"))):
        for blk in find(json.load(open(f))):
            for e in blk.get("labels", []):
                assert e["label"] not in blocks and e["label"] not in skel, e["label"]
                blocks[e["label"]] = {
                    "record_ids": e["inventory_record_ids"],
                    "note": e.get("note") or "",
                    "source": os.path.relpath(f, ROOT),
                }
    group_of = {}
    for g, members in SYSTEM_GROUPS.items():
        for m in members:
            group_of[m] = g
    # unadjudicated candidates: literal, auditable; never viewer-actionable
    CANDIDATES = {
        "autochthon_left": ([], "group label for the intrinsic back muscles; the Body Model carries no single autochthon record"),
        "autochthon_right": ([], "group label for the intrinsic back muscles; the Body Model carries no single autochthon record"),
        "gluteus_maximus_left": (["muscle.left-gluteus-maximus"], "same-name record exists; the muscular tranche (M4) recorded no TS overlap adjudication"),
        "gluteus_maximus_right": (["muscle.right-gluteus-maximus"], "same-name record exists; the muscular tranche (M4) recorded no TS overlap adjudication"),
        "gluteus_medius_left": (["muscle.left-gluteus-medius"], "same-name record exists; the muscular tranche (M4) recorded no TS overlap adjudication"),
        "gluteus_medius_right": (["muscle.right-gluteus-medius"], "same-name record exists; the muscular tranche (M4) recorded no TS overlap adjudication"),
        "gluteus_minimus_left": (["muscle.left-gluteus-minimus"], "same-name record exists; the muscular tranche (M4) recorded no TS overlap adjudication"),
        "gluteus_minimus_right": (["muscle.right-gluteus-minimus"], "same-name record exists; the muscular tranche (M4) recorded no TS overlap adjudication"),
        "iliopsoas_left": (["muscle.left-psoas-major", "muscle.left-iliacus"], "composite label (psoas major + iliacus); no single iliopsoas record; M4 recorded no adjudication"),
        "iliopsoas_right": (["muscle.right-psoas-major", "muscle.right-iliacus"], "composite label (psoas major + iliacus); no single iliopsoas record; M4 recorded no adjudication"),
        "face": ([], "soft-tissue region label; the M3 census deliberately maps it to no record and M15 records TS overlap 0 for integumentary"),
    }
    out = []
    for idx, lab in enumerate(labels, start=1):
        if lab in skel:
            e = {"index": idx, "label": lab, "system_group": "skeletal",
                 "mapping_status": "mapped", "record_ids": [skel[lab]],
                 "mapping_note": "", "mapping_source": "data/sources/totalsegmentator-1.0/labels.json (Milestone 3 census rules, tools/ts_census.py)"}
        elif lab in blocks:
            b = blocks[lab]
            e = {"index": idx, "label": lab, "system_group": group_of.get(lab, ""),
                 "mapping_status": "mapped", "record_ids": b["record_ids"],
                 "mapping_note": b["note"], "mapping_source": b["source"] + " (totalsegmentator_overlap block)"}
        else:
            cand, reason = CANDIDATES[lab]
            e = {"index": idx, "label": lab, "system_group": group_of.get(lab, ""),
                 "mapping_status": "unmapped", "record_ids": [],
                 "mapping_note": reason, "mapping_source": "",
                 "candidate_record_ids": cand}
        out.append(e)
    return out


# ----------------------------------------------------------------- DICOM ----
# PS3.5 maximum lengths (characters, per component) for the string VRs
# this writer emits. _el REFUSES a non-conforming value: the Milestone
# 45 toolkit pass found a 67-character LO SeriesDescription (limit 64)
# in all 870 instances of both series, emitted unchecked by the
# pre-gate writer; Milestone 46 added this gate so the writer can
# never emit an over-length string element again.
_VR_MAX = {"AE": 16, "AS": 4, "CS": 16, "DA": 8, "DS": 16, "DT": 26,
           "IS": 12, "LO": 64, "LT": 10240, "PN": 64, "SH": 16,
           "ST": 1024, "TM": 16, "UI": 64}


def _el(tag, vr, value):
    g, e = tag
    if vr in _VR_MAX and isinstance(value, (bytes, bytearray)):
        text = bytes(value).decode("ascii")
        for comp in text.split("\\"):
            semantic = comp.rstrip(" \x00")  # strip the even-length pad
            assert len(semantic) <= _VR_MAX[vr], (
                f"element ({g:04X},{e:04X}) VR {vr}: value component "
                f"{semantic!r} is {len(semantic)} characters, over the "
                f"PS3.5 maximum {_VR_MAX[vr]} — refusing to emit")
    if vr in ("OB", "OW", "OF", "SQ", "UC", "UR", "UT", "UN"):
        return struct.pack("<HH", g, e) + vr.encode("ascii") + b"\x00\x00" \
            + struct.pack("<I", len(value)) + value
    return struct.pack("<HH", g, e) + vr.encode("ascii") \
        + struct.pack("<H", len(value)) + value


def _ui(s):
    b = s.encode("ascii")
    return b + (b"\x00" if len(b) % 2 else b"")


def _txt(s, pad=b" "):
    b = s.encode("ascii")
    return b + (pad if len(b) % 2 else b"")


def _ds(x):
    s = f"{x:.6f}".rstrip("0").rstrip(".")
    return _txt(s if s else "0")


def _is(n):
    return _txt(str(int(n)))


def write_dicom(path, pixels_i16, meta, k):
    """One CT image instance, Explicit VR Little Endian, PS3.10 file."""
    sop_uid = f"{meta['instance_root']}.{k + 1}"
    els = []
    els.append(_el((0x0008, 0x0008), "CS", _txt("DERIVED\\SECONDARY")))
    els.append(_el((0x0008, 0x0016), "UI", _ui("1.2.840.10008.5.1.4.1.1.2")))
    els.append(_el((0x0008, 0x0018), "UI", _ui(sop_uid)))
    els.append(_el((0x0008, 0x0020), "DA", _txt(meta["date"])))
    els.append(_el((0x0008, 0x0021), "DA", _txt(meta["date"])))
    els.append(_el((0x0008, 0x0030), "TM", _txt(meta["time"])))
    els.append(_el((0x0008, 0x0031), "TM", _txt(meta["time"])))
    els.append(_el((0x0008, 0x0050), "SH", _txt("")))
    els.append(_el((0x0008, 0x0060), "CS", _txt("CT")))
    els.append(_el((0x0008, 0x0070), "LO", _txt("ANATOMICA (educational model)")))
    els.append(_el((0x0008, 0x0080), "LO", _txt("ANATOMICA project")))
    els.append(_el((0x0008, 0x1030), "LO", _txt(meta["study_desc"])))
    els.append(_el((0x0008, 0x103E), "LO", _txt(meta["series_desc"])))
    els.append(_el((0x0010, 0x0010), "PN", _txt("ANATOMICA^SYNTHETIC")))
    els.append(_el((0x0010, 0x0020), "LO", _txt(meta["patient_id"])))
    els.append(_el((0x0010, 0x0040), "CS", _txt(meta["sex"])))
    els.append(_el((0x0010, 0x1010), "AS", _txt(meta["age"])))
    els.append(_el((0x0018, 0x0050), "DS", _ds(meta["spacing"][2])))
    els.append(_el((0x0018, 0x0088), "DS", _ds(meta["spacing"][2])))
    els.append(_el((0x0020, 0x000D), "UI", _ui(meta["study_uid"])))
    els.append(_el((0x0020, 0x000E), "UI", _ui(meta["series_uid"])))
    els.append(_el((0x0020, 0x0010), "SH", _txt(meta["study_id"])))
    els.append(_el((0x0020, 0x0011), "IS", _is(1)))
    els.append(_el((0x0020, 0x0013), "IS", _is(k + 1)))
    ipp = [meta["ipp0"][0], meta["ipp0"][1], meta["ipp0"][2] + k * meta["spacing"][2]]
    els.append(_el((0x0020, 0x0032), "DS", b"\\".join(_ds(v).rstrip() for v in ipp)))
    els.append(_el((0x0020, 0x0037), "DS", b"\\".join(_ds(v).rstrip() for v in meta["iop"])))
    els.append(_el((0x0020, 0x0052), "UI", _ui(meta["for_uid"])))
    els.append(_el((0x0020, 0x1041), "DS", _ds(ipp[2])))
    els.append(_el((0x0028, 0x0002), "US", struct.pack("<H", 1)))
    els.append(_el((0x0028, 0x0004), "CS", _txt("MONOCHROME2")))
    els.append(_el((0x0028, 0x0010), "US", struct.pack("<H", meta["rows"])))
    els.append(_el((0x0028, 0x0011), "US", struct.pack("<H", meta["cols"])))
    els.append(_el((0x0028, 0x0030), "DS", b"\\".join(_ds(v).rstrip() for v in (meta["spacing"][0], meta["spacing"][1]))))
    els.append(_el((0x0028, 0x0100), "US", struct.pack("<H", 16)))
    els.append(_el((0x0028, 0x0101), "US", struct.pack("<H", 16)))
    els.append(_el((0x0028, 0x0102), "US", struct.pack("<H", 15)))
    els.append(_el((0x0028, 0x0103), "US", struct.pack("<H", 1)))
    els.append(_el((0x0028, 0x0301), "CS", _txt("YES")))
    els.append(_el((0x0028, 0x1050), "DS", _ds(50)))
    els.append(_el((0x0028, 0x1051), "DS", _ds(350)))
    els.append(_el((0x0028, 0x1052), "DS", _ds(0)))
    els.append(_el((0x0028, 0x1053), "DS", _ds(1)))
    els.append(_el((0x0020, 0x4000), "LT", _txt(meta["comment"])))
    els.append(_el((0x7FE0, 0x0010), "OW", pixels_i16.astype("<i2").tobytes()))
    dataset = b"".join(els)
    meta_els = b"".join([
        _el((0x0002, 0x0001), "OB", b"\x00\x01"),
        _el((0x0002, 0x0002), "UI", _ui("1.2.840.10008.5.1.4.1.1.2")),
        _el((0x0002, 0x0003), "UI", _ui(sop_uid)),
        _el((0x0002, 0x0010), "UI", _ui("1.2.840.10008.1.2.1")),
        _el((0x0002, 0x0012), "UI", _ui(meta["impl_uid"])),
        _el((0x0002, 0x0013), "SH", _txt(meta["impl_name"])),
    ])
    group_len = struct.pack("<I", len(meta_els))
    with open(path, "wb") as f:
        f.write(b"\x00" * 128 + b"DICM")
        f.write(_el((0x0002, 0x0000), "UL", group_len))
        f.write(meta_els)
        f.write(dataset)


# ------------------------------------------------------------------- main ---
def main():
    census = json.load(open(os.path.join(TS_DIR, "labels.json")))
    label_names = sorted(census["labels"])
    assert len(label_names) == 104
    records_doc = json.load(open(os.path.join(ROOT, "web", "data", "records.json")))
    records = records_doc["records"]
    rec_by_id = {r["id"]: r for r in records}

    with open(os.path.join(SUBJ_DIR, "..", "meta.csv"), encoding="utf-8-sig") as f:
        meta_rows = {r["image_id"]: r for r in csv.DictReader(f, delimiter=";")}
    subj_meta = meta_rows[SUBJECT]

    ct, ct_hdr = read_nifti(os.path.join(SUBJ_DIR, "ct.nii.gz"))
    (sx, sy, sz), (ox, oy, oz) = affine_of(ct_hdr)
    nx, ny, nz = ct_hdr["dim"]
    spacing = (sx, sy, sz)
    print(f"subject {SUBJECT}: dims {ct_hdr['dim']} spacing {spacing} "
          f"CT stored range [{ct.min()}, {ct.max()}] dtype {ct.dtype}")

    # ---- masks: counts, then priority painting (smallest mask wins) ----
    masks = {}
    counts = {}
    for lab in label_names:
        a, h = read_nifti(os.path.join(SUBJ_DIR, "segmentations", lab + ".nii.gz"))
        assert h["dim"] == ct_hdr["dim"] and h["srow"] == ct_hdr["srow"], lab
        masks[lab] = a
        counts[lab] = int((a > 0).sum())
    claims = np.zeros(ct.shape, dtype=np.uint16)
    for lab in label_names:
        claims += (masks[lab] > 0)
    contested = int((claims >= 2).sum())
    total_claims = int(claims.sum())
    print(f"mask voxels total {total_claims}; contested (>=2 masks) {contested}")

    index_of = {lab: i + 1 for i, lab in enumerate(label_names)}
    label_vol = np.zeros(ct.shape, dtype=np.uint8)  # NIfTI orientation
    for lab in sorted(label_names, key=lambda l: (counts[l], index_of[l])):
        m = (masks[lab] > 0) & (label_vol == 0)
        label_vol[m] = index_of[lab]
    assigned = {lab: int((label_vol == index_of[lab]).sum()) for lab in label_names}
    del masks, claims

    # ---- HU statistics per label, BEFORE any watermark ----------------
    hu_i16_range_ok = int(ct.min()) >= -32768 and int(ct.max()) <= 32767
    print(f"int32->int16 conversion lossless for this subject: {hu_i16_range_ok}")
    assert hu_i16_range_ok
    stats = {}
    for lab in label_names:
        sel = label_vol == index_of[lab]
        n = int(sel.sum())
        if not n:
            stats[lab] = None
            continue
        v = ct[sel].astype(np.float64)
        stats[lab] = {
            "voxels": n,
            "mean": round(float(v.mean()), 2),
            "median": round(float(np.median(v)), 2),
            "p5": round(float(np.percentile(v, 5)), 2),
            "p95": round(float(np.percentile(v, 95)), 2),
            "min": int(v.min()), "max": int(v.max()),
        }

    # ---- flip to stored orientation (both in-plane axes) --------------
    ct_s = np.ascontiguousarray(ct[:, ::-1, ::-1]).astype(np.int16)
    lab_s = np.ascontiguousarray(label_vol[:, ::-1, ::-1])
    del ct, label_vol
    # per-label bbox/centroid in DICOM LPS mm, stored orientation:
    # stored voxel (c,r,k) centre LPS = ipp0 + (c*sx, r*sy, k*sz)
    ras_corner = (ox + (nx - 1) * sx, oy + (ny - 1) * sy, oz)
    ipp0 = (-ras_corner[0], -ras_corner[1], ras_corner[2])
    geom = {}
    for lab in label_names:
        idx = index_of[lab]
        if not assigned[lab]:
            geom[lab] = None
            continue
        zz, rr, cc = np.nonzero(lab_s == idx)
        cen = [float(ipp0[0] + cc.mean() * sx), float(ipp0[1] + rr.mean() * sy),
               float(ipp0[2] + zz.mean() * sz)]
        bb = [[float(ipp0[0] + cc.min() * sx), float(ipp0[1] + rr.min() * sy),
               float(ipp0[2] + zz.min() * sz)],
              [float(ipp0[0] + cc.max() * sx), float(ipp0[1] + rr.max() * sy),
               float(ipp0[2] + zz.max() * sz)]]
        geom[lab] = {"centroid_lps_mm": [round(v, 2) for v in cen],
                     "bbox_lps_mm": [[round(v, 2) for v in row] for row in bb]}

    # ---- watermark (after stats): burn glyphs into a copy -------------
    offs = watermark_offsets()
    ct_wm = ct_s.copy()
    glyph_voxels = 0
    for k in range(nz):
        for (r, c) in offs:
            ct_wm[k, r, c] = WATERMARK_VALUE
        glyph_voxels += len(offs)
    print(f"watermark: {len(offs)} glyph voxels/slice x {nz} slices = {glyph_voxels}")

    # ---- crosswalk -----------------------------------------------------
    crosswalk = build_crosswalk(rec_by_id)
    for e in crosswalk:
        lab = e["label"]
        e["present_in_subject"] = assigned[lab] > 0
        e["voxels"] = assigned[lab]
        e["hu"] = stats[lab]
        e["geometry_lps"] = geom[lab]
        e["records"] = [{"id": rid, "name": rec_by_id[rid]["name"],
                         "layer": rec_by_id[rid]["layer"]}
                        for rid in e["record_ids"]]
        assert all(rid in rec_by_id for rid in e["record_ids"]), lab
        assert all(cid in rec_by_id for cid in e.get("candidate_record_ids", [])), lab
        hue = (e["index"] * 137.508) % 360.0
        rgb = colorsys.hls_to_rgb(hue / 360.0, 0.55, 0.62)
        e["color_rgb"] = [round(c * 255) for c in rgb]
    mapped = [e for e in crosswalk if e["mapping_status"] == "mapped"]
    unmapped = [e for e in crosswalk if e["mapping_status"] == "unmapped"]
    reach_present = sorted({rid for e in mapped if e["present_in_subject"]
                            for rid in e["record_ids"]})
    reach_all = sorted({rid for e in mapped for rid in e["record_ids"]})
    totals = {
        "labels_in_source_set": len(crosswalk),
        "labels_mapped": len(mapped),
        "labels_unmapped": len(unmapped),
        "labels_present_in_subject": sum(1 for e in crosswalk if e["present_in_subject"]),
        "labels_absent_in_subject": sum(1 for e in crosswalk if not e["present_in_subject"]),
        "mapped_and_present": sum(1 for e in mapped if e["present_in_subject"]),
        "mapped_and_absent": sum(1 for e in mapped if not e["present_in_subject"]),
        "unmapped_and_present": sum(1 for e in unmapped if e["present_in_subject"]),
        "unmapped_and_absent": sum(1 for e in unmapped if not e["present_in_subject"]),
        "records_reachable_from_present_labels": len(reach_present),
        "records_reachable_from_all_mapped_labels": len(reach_all),
        "contested_voxels": contested,
        "mask_voxel_claims_total": total_claims,
        "labelled_voxels_total": int(sum(assigned.values())),
    }
    print(json.dumps(totals, indent=1))

    # ---- UIDs / shared meta -------------------------------------------
    now = datetime.now(timezone.utc)
    uid = lambda: "2.25." + str(uuid.uuid4().int)  # noqa: E731
    dmeta = {
        "date": now.strftime("%Y%m%d"), "time": now.strftime("%H%M%S"),
        "study_uid": uid(), "series_uid": uid(), "for_uid": uid(),
        "instance_root": uid(), "impl_uid": uid(),
        "study_id": "ANATOMICA-" + MTAG, "impl_name": "ANATOMICA_" + MTAG,
        "study_desc": "SYNTHETIC - educational model - ANATOMICA derived CT study",
        # Milestone 46: shortened from "...educational model - derived
        # from..." (67 chars) — VR LO caps at 64 (Milestone 45 defect).
        "series_desc": "SYNTHETIC - derived from TotalSegmentator " + SUBJECT,
        "patient_id": "ANATOMICA-SYNTH-" + SUBJECT[1:],
        "sex": (subj_meta["gender"] or "").upper()[:1],
        "age": f"{int(subj_meta['age']):03d}Y",
        "spacing": spacing, "rows": ny, "cols": nx, "ipp0": ipp0,
        "iop": [1, 0, 0, 0, 1, 0],
        "comment": ("SYNTHETIC - educational model. Derived by ANATOMICA " + MILESTONE +
                    " from TotalSegmentator dataset v1.0 subject " + SUBJECT +
                    " (CC BY 4.0, Zenodo 6802614). Pixel values are the source "
                    "subject's CT intensities; identifiers are synthetic. "
                    "Not patient data of any ANATOMICA user; not for clinical use."),
    }

    out_base = os.path.join(ROOT, "data", "imaging", SUBJECT)
    dicom_dir = os.path.join(out_base, "dicom")
    os.makedirs(dicom_dir, exist_ok=True)
    web_dir = os.path.join(ROOT, "web", "data", "imaging", SUBJECT)
    os.makedirs(web_dir, exist_ok=True)

    dicom_index = []
    for k in range(nz):
        name = f"{SUBJECT}-ct-synth-{k + 1:04d}.dcm"
        path = os.path.join(dicom_dir, name)
        write_dicom(path, ct_wm[k], dmeta, k)
        dicom_index.append({
            "instance_number": k + 1, "file": "dicom/" + name,
            "sop_instance_uid": f"{dmeta['instance_root']}.{k + 1}",
            "sha256": hashlib.sha256(open(path, "rb").read()).hexdigest(),
            "bytes": os.path.getsize(path),
        })
        ct_wm[k].astype("<i2").tofile(os.path.join(web_dir, f"hu-{k:04d}.bin"))
        lab_s[k].astype(np.uint8).tofile(os.path.join(web_dir, f"lbl-{k:04d}.bin"))
    print(f"wrote {nz} DICOM instances + {nz} web slice pairs")

    series = {
        "title": f"ANATOMICA Imaging v1 — synthetic derived CT series ({SUBJECT})",
        "milestone": MILESTONE,
        "synthetic": True,
        "derived_at_utc": now.isoformat(),
        "derivation_tool": "tools/imaging_derive.py",
        "subject": {
            "id": SUBJECT,
            "dataset": "TotalSegmentator dataset v1.0 (Zenodo 6802614), CC BY 4.0",
            "meta_csv_row": subj_meta,
            "intake": "Milestone 3 subset (CRC-verified at intake)",
            "selection_reason": SELECTION_REASONS.get(
                SUBJECT,
                "selected by the Milestone 19 rule (most non-empty label "
                "masks among the locally held subjects); see the deriving "
                "milestone document for the ranking table"),
        },
        "provenance_note": ("The atlas Body Model is a DIFFERENT individual "
                            "(BodyParts3D subject). This series and the atlas share "
                            "structure identity (record ids) only — no spatial "
                            "co-registration between the two subjects is claimed."),
        "pixel_route": {
            "source": "subject ct.nii.gz, int32, scl_slope 1.0, scl_inter 0.0 (HU as stored)",
            "conversion": "int32 -> int16, asserted lossless (all values within int16 range)",
            "stored_range_hu": [int(ct_s.min()), int(ct_s.max())],
            "remapping": "none",
            "watermark": ("'SYNTHETIC' 5x7 glyphs burned at value "
                          f"{WATERMARK_VALUE} HU, rows {WM_ORIGIN[0]}..{WM_ORIGIN[0] + 6}, "
                          f"cols {WM_ORIGIN[1]}..{WM_ORIGIN[1] + 52} of every slice "
                          "(stored orientation), applied AFTER HU statistics; "
                          f"{len(offs)} voxels per slice, {glyph_voxels} total"),
            "watermark_offsets_row_col": offs,
            "watermark_metadata": ("DICOM BurnedInAnnotation (0028,0301) = YES; "
                                   "ImageType DERIVED\\SECONDARY; SYNTHETIC stated in "
                                   "StudyDescription, SeriesDescription and ImageComments"),
        },
        "geometry": {
            "dims_voxels": {"cols": nx, "rows": ny, "slices": nz},
            "spacing_mm": list(spacing),
            "nifti_srow": ct_hdr["srow"],
            "stored_orientation": ("stored[c,r,k] = nifti[nx-1-c, ny-1-r, k] "
                                   "(both in-plane axes flipped)"),
            "image_orientation_patient": [1, 0, 0, 0, 1, 0],
            "ipp_first_slice_lps_mm": [round(v, 6) for v in ipp0],
            "frame_of_reference_uid": dmeta["for_uid"],
        },
        "dicom": {
            "study_instance_uid": dmeta["study_uid"],
            "series_instance_uid": dmeta["series_uid"],
            "sop_class_uid": "1.2.840.10008.5.1.4.1.1.2",
            "transfer_syntax": "1.2.840.10008.1.2.1 (Explicit VR Little Endian)",
            "instances": dicom_index,
        },
        "label_assignment_rule": ("per-voxel: among masks claiming a voxel, the "
                                  "smallest mask (fewest voxels; ties by label index) "
                                  "wins; contested voxels counted, not hidden"),
        "crosswalk_totals": totals,
    }
    with open(os.path.join(out_base, "series.json"), "w") as f:
        json.dump(series, f, indent=1, sort_keys=True)
    with open(os.path.join(out_base, "crosswalk.json"), "w") as f:
        json.dump({"subject": SUBJECT, "totals": totals, "labels": crosswalk},
                  f, indent=1, sort_keys=True)

    presets = [
        {"id": "soft-tissue", "label": "Soft tissue", "window_width": 350, "window_level": 50},
        {"id": "lung", "label": "Lung", "window_width": 1600, "window_level": -600},
        {"id": "bone", "label": "Bone", "window_width": 2000, "window_level": 500},
    ]
    preset_sources = [
        "Stepwards, 'Fundamentals Of Computed Tomography Studies: Windowing' (stepwards.com/?page_id=21646) — soft tissue W350/L50, lung W1600/L-600, bone W2000/L500; consulted 2026-11-06",
        "FireVoxel documentation, 'Grayscale Window' (firevoxel.org/docs/html/userguide/grayscale.html) — lung L-600/W1600, bone L500/W2000, soft tissue L50 (W400 variant noted); consulted 2026-11-06",
    ]
    hu_table_sources = [
        "design/06-imaging.md per-structure ranges (water 0, air -1000, fat -120..-90, liver 40-60, cortical bone +500..+1900)",
        "research/round-02-medical-fields/fronts/05-imaging-science §5.1 HU table (Wikipedia Hounsfield scale, cross-checked against radiology texts)",
    ]
    # Per-subject block of the web manifest. The label->record mapping
    # fields inside "labels" are label-level (identical for every
    # subject — the crosswalk is built once, above); presence, voxel
    # counts, HU statistics and geometry are this subject's accounting.
    subj_block = {
        "meta": {
            "title": series["title"],
            "banner": ("SYNTHETIC — educational model · derived from TotalSegmentator "
                       f"subject {SUBJECT} (CC BY 4.0) · not patient data"),
            "subject": series["subject"],
            "pixel_route": series["pixel_route"],
        },
        "geometry": series["geometry"],
        "files": {"hu": f"imaging/{SUBJECT}/hu-{{slice:04d}}.bin",
                  "labels": f"imaging/{SUBJECT}/lbl-{{slice:04d}}.bin",
                  "hu_bytes_per_slice": nx * ny * 2, "label_bytes_per_slice": nx * ny},
        "crosswalk_totals": totals,
        "labels": [{k: e[k] for k in ("index", "label", "system_group", "mapping_status",
                                      "record_ids", "records", "mapping_note",
                                      "candidate_record_ids", "present_in_subject",
                                      "voxels", "hu", "geometry_lps", "color_rgb")
                    if k in e} for e in crosswalk],
    }
    # web/data/imaging.json is the COMBINED manifest (Milestone 32):
    # shared meta (presets + their citations, HU table sources, the
    # provenance note) plus one block per derived subject. Deriving a
    # new subject merges its block in and preserves the others; a
    # Milestone 19/31 flat single-subject manifest is folded in as
    # that subject's block, its data copied verbatim (the earlier
    # subject is NOT re-derived).
    man_path = os.path.join(ROOT, "web", "data", "imaging.json")
    combined = None
    if os.path.exists(man_path):
        prev = json.load(open(man_path))
        if "subjects" in prev:
            combined = prev
        elif "labels" in prev:
            old_id = prev["meta"]["subject"]["id"]
            combined = {
                "meta": {
                    "title": "ANATOMICA Imaging — synthetic derived CT series",
                    "synthetic": True,
                    "provenance_note": prev["meta"]["provenance_note"],
                    "presets": prev["meta"]["presets"],
                    "preset_sources": prev["meta"]["preset_sources"],
                    "hu_table_sources": prev["meta"]["hu_table_sources"],
                },
                "default_subject": old_id,
                "subjects": {old_id: {
                    "meta": {k: prev["meta"][k] for k in
                             ("title", "banner", "subject", "pixel_route")},
                    "geometry": prev["geometry"], "files": prev["files"],
                    "crosswalk_totals": prev["crosswalk_totals"],
                    "labels": prev["labels"],
                }},
            }
    if combined is None:
        combined = {
            "meta": {
                "title": "ANATOMICA Imaging — synthetic derived CT series",
                "synthetic": True,
                "provenance_note": series["provenance_note"],
                "presets": presets, "preset_sources": preset_sources,
                "hu_table_sources": hu_table_sources,
            },
            "default_subject": SUBJECT,
            "subjects": {},
        }
    combined["subjects"][SUBJECT] = subj_block
    combined["meta"]["manifest_milestone"] = MILESTONE
    with open(man_path, "w") as f:
        json.dump(combined, f, indent=1, sort_keys=True)
    print("manifests written")


if __name__ == "__main__":
    sys.exit(main())
