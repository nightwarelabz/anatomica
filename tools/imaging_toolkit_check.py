#!/usr/bin/env python3
"""ANATOMICA Milestone 45: independent DICOM toolkit validation of the
imaging series (the toolkit pass owed since Milestone 19).

This checker validates the shipped DICOM series from OUTSIDE the
project's own code. It imports NO project module: DICOM parsing is
pydicom 3.0.2, the source-volume corroboration is nibabel 5.4.2, the
rest is stdlib + numpy. tools/imaging_derive.py (the derivation under
audit) and the in-project EVLE readers behind verify_web.js W7 are
never imported or invoked; the recorded claims under test come from
each subject's series.json manifest and the milestone documents.

Per subject series (discovered under data/imaging/*/):

  1. file set: the dicom/ directory holds exactly the instances the
     manifest enumerates; every file's byte count and SHA-256 equal
     the manifest's;
  2. parse: every file is a PS3.10 file (preamble + DICM, via
     pydicom.misc.is_dicom) and dcmread() parses it unforced;
  3. file meta: Transfer Syntax is Explicit VR Little Endian; Media
     Storage SOP Class / Instance agree with the dataset;
  4. identity: SOP Class is CT Image Storage; SOP Instance UID equals
     the manifest's per instance and is unique; Study / Series /
     Frame of Reference UIDs are constant and equal the manifest's;
     Modality CT throughout; PatientID / PatientName / PatientSex /
     PatientAge match the manifest's recorded subject identity;
     StudyID and Implementation Version Name carry the deriving
     milestone's tag recorded in the manifest; Series Number 1;
     Instance Numbers are exactly 1..N in manifest order; Study and
     Series Date/Time are constant within the series;
  5. image encoding: Rows / Columns equal the recorded dims; Samples
     Per Pixel 1; Photometric Interpretation MONOCHROME2; Bits
     Allocated 16, Bits Stored 16, High Bit 15, Pixel Representation
     1 (signed); Rescale Slope 1 / Intercept 0; Pixel Spacing, Slice
     Thickness and Spacing Between Slices equal the recorded spacing;
     Image Orientation Patient equals the recorded direction and is
     orthonormal with the recorded slice normal; the Pixel Data
     element length is exactly Rows x Columns x 2 bytes (uncompressed
     int16) in every instance;
  6. geometry chain: first-slice Image Position Patient equals the
     manifest's recorded IPP (tolerance 2e-6 mm — both are 6-decimal
     roundings of the same source values); IPP x/y are constant; every
     consecutive z step equals the recorded slice spacing (1e-6 mm);
     Slice Location equals IPP z per instance; the centre span is
     (N-1) x spacing and the full extent N x spacing; the recorded
     spacing is isotropic and the per-instance spacing elements agree
     with it (the sform-derived 1.5 mm isotropic claim as expressed in
     the series);
  7. pixels, read through pydicom only: pixel_array is int16 of the
     recorded shape in every instance; the series' global min/max
     equal the manifest's recorded stored HU range; and every
     instance's pixel array equals the shipped web HU bin for that
     slice exactly (the W7 identity claim, reproduced through the
     toolkit rather than the project's reader);
  8. watermark (Milestone 19 section 4): Burned In Annotation YES,
     Image Type DERIVED\\SECONDARY, and SYNTHETIC present in Study
     Description, Series Description and Image Comments in every
     instance; in the pixels, every recorded glyph offset (123 per
     slice) holds the documented watermark value 3071 HU in every
     instance, read through pydicom;
  9. end-to-end source corroboration (nibabel): the source NIfTI is
     int32 with slope 1 / intercept 0; its global min/max equal the
     recorded stored range (the int32 range sits inside int16 — the
     conversion's losslessness anchor); its affine is diagonal with
     the recorded spacing steps and its origin reproduces the
     recorded first-slice IPP under the documented LPS relation; and
     for every slice, the set of voxels where the DICOM pixels differ
     from the flipped source slice is exactly the recorded glyph
     offset set, with the DICOM value 3071 at every differing voxel —
     i.e. the ONLY alteration between source and series is the
     watermark, at exactly the recorded positions;
 10. value-length conformance audit (PS3.5): every string element
     value (dataset + file meta, per component for multi-valued VRs)
     is measured against its VR's maximum length. Violations are
     reported as FINDINGS — printed, counted, and carried in the
     milestone dossier as standing defects — not as hard failures:
     the claims under audit (sections 1-9) are the ones Milestones
     19/32 made, and a finding here is a defect to fix in a future
     re-derivation, not a data error this pass is allowed to repair.

Exit code 0 only if every hard check (sections 1-9) passes. Printed
lines marked [report] are informational; lines marked FINDING are
the section-10 conformance defects.

Usage: python3 tools/imaging_toolkit_check.py
Requires: pydicom 3.0.2, nibabel 5.4.2, numpy (pip-installed at
Milestone 45; versions pinned in MILESTONE-45.md).
"""

import glob
import hashlib
import json
import os
import sys

import numpy as np
import pydicom
import nibabel as nib

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(PROJECT, "data", "imaging")
WEB_DIR = os.path.join(PROJECT, "web", "data", "imaging")
TS_DIR = os.path.join(PROJECT, "data", "sources",
                      "totalsegmentator-1.0", "subset",
                      "Totalsegmentator_dataset")

CT_SOP_CLASS = "1.2.840.10008.5.1.4.1.1.2"
EVLE = "1.2.840.10008.1.2.1"
WM_VALUE = 3071  # Milestone 19 section 4: glyph value, 12-bit maximum

# PS3.5 maximum lengths (characters) for the string VRs these files
# carry; multi-valued values are audited per component.
VR_MAX = {"AE": 16, "AS": 4, "CS": 16, "DA": 8, "DS": 16, "DT": 26,
          "IS": 12, "LO": 64, "LT": 10240, "PN": 64, "SH": 16,
          "ST": 1024, "TM": 16, "UI": 64, "UT": None}

failures = []
findings = []
notes = []


def check(ok, label):
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        failures.append(label)


def report(label):
    print("[report] " + label)
    notes.append(label)


def finding(label):
    print("FINDING " + label)
    findings.append(label)


def ds_floats(ds, tag):
    elem = ds[tag]
    if elem.VM > 1:
        return [float(x) for x in elem.value]
    return [float(elem.value)]


def check_subject(subj):
    print(f"\n===== subject {subj} =====")
    base = os.path.join(IMG_DIR, subj)
    man = json.load(open(os.path.join(base, "series.json")))
    geom = man["geometry"]
    dims = geom["dims_voxels"]
    nx, ny, nz = dims["cols"], dims["rows"], dims["slices"]
    spacing = [float(s) for s in geom["spacing_mm"]]
    ipp0 = [float(v) for v in geom["ipp_first_slice_lps_mm"]]
    insts = man["dicom"]["instances"]
    n = len(insts)
    check(n == nz, f"{subj}: manifest enumerates {n} instances == "
                   f"recorded slice count {nz}")
    mtag = "M" + man["milestone"].split()[-1]
    exp_study_id = "ANATOMICA-" + mtag
    exp_impl_name = "ANATOMICA_" + mtag
    subj_meta = man["subject"]["meta_csv_row"]
    exp_patient_id = "ANATOMICA-SYNTH-" + subj[1:]
    exp_sex = (subj_meta["gender"] or "").upper()[:1]
    exp_age = f"{int(subj_meta['age']):03d}Y"
    offs = [tuple(o) for o in man["pixel_route"]["watermark_offsets_row_col"]]
    off_set = set(offs)

    # ---- 1. file set vs manifest -----------------------------------
    dicom_dir = os.path.join(base, "dicom")
    on_disk = sorted(f for f in os.listdir(dicom_dir) if f.endswith(".dcm"))
    man_files = sorted(os.path.basename(i["file"]) for i in insts)
    check(on_disk == man_files,
          f"{subj}: dicom/ holds exactly the {n} manifest files")
    bad_hash = [i["file"] for i in insts
                if hashlib.sha256(open(os.path.join(base, i["file"]), "rb")
                                  .read()).hexdigest() != i["sha256"]
                or os.path.getsize(os.path.join(base, i["file"])) != i["bytes"]]
    check(not bad_hash,
          f"{subj}: SHA-256 and byte count match the manifest for all "
          f"{n} instances ({len(bad_hash)} mismatches)")

    # ---- 2-8. pydicom pass over every instance ----------------------
    bad_magic, bad_parse = [], []
    bad_ts, bad_meta_uid = [], []
    bad_sopclass, bad_sopuid, dup_uid = [], [], []
    bad_study_uid, bad_series_uid, bad_for_uid = [], [], []
    bad_modality, bad_patient, bad_studyid, bad_seriesnum = [], [], [], []
    bad_instnum, bad_datetime = [], []
    bad_dims, bad_encoding, bad_rescale, bad_spacing_el = [], [], [], []
    bad_iop, bad_pixlen = [], []
    bad_wm_meta, bad_wm_pix = [], []
    bad_shape, bad_bin = [], []
    uid_seen = set()
    dates, times = set(), set()
    ipps = []
    gmin, gmax = None, None
    vr_violations = {}

    for idx, inst in enumerate(insts):
        path = os.path.join(base, inst["file"])
        name = os.path.basename(path)
        if not pydicom.misc.is_dicom(path):
            bad_magic.append(name)
            continue
        try:
            ds = pydicom.dcmread(path)
        except Exception as exc:  # parse failure: record, keep going
            bad_parse.append(f"{name}: {exc}")
            continue
        fm = ds.file_meta
        if str(fm.TransferSyntaxUID) != EVLE:
            bad_ts.append(name)
        if (str(fm.MediaStorageSOPClassUID) != CT_SOP_CLASS
                or str(fm.MediaStorageSOPInstanceUID) != str(ds.SOPInstanceUID)):
            bad_meta_uid.append(name)
        if str(ds.SOPClassUID) != CT_SOP_CLASS:
            bad_sopclass.append(name)
        if str(ds.SOPInstanceUID) != inst["sop_instance_uid"]:
            bad_sopuid.append(name)
        if str(ds.SOPInstanceUID) in uid_seen:
            dup_uid.append(name)
        uid_seen.add(str(ds.SOPInstanceUID))
        if str(ds.StudyInstanceUID) != man["dicom"]["study_instance_uid"]:
            bad_study_uid.append(name)
        if str(ds.SeriesInstanceUID) != man["dicom"]["series_instance_uid"]:
            bad_series_uid.append(name)
        if str(ds.FrameOfReferenceUID) != geom["frame_of_reference_uid"]:
            bad_for_uid.append(name)
        if str(ds.Modality) != "CT":
            bad_modality.append(name)
        if (str(ds.PatientID) != exp_patient_id
                or str(ds.PatientName) != "ANATOMICA^SYNTHETIC"
                or str(ds.PatientSex) != exp_sex
                or str(ds.PatientAge) != exp_age):
            bad_patient.append(name)
        if (str(ds.StudyID) != exp_study_id
                or str(fm.ImplementationVersionName) != exp_impl_name):
            bad_studyid.append(name)
        if int(ds.SeriesNumber) != 1:
            bad_seriesnum.append(name)
        if int(ds.InstanceNumber) != idx + 1 \
                or int(ds.InstanceNumber) != inst["instance_number"]:
            bad_instnum.append(name)
        dates.add(str(ds.StudyDate)); dates.add(str(ds.SeriesDate))
        times.add(str(ds.StudyTime)); times.add(str(ds.SeriesTime))
        if (int(ds.Rows), int(ds.Columns)) != (ny, nx):
            bad_dims.append(name)
        if (int(ds.SamplesPerPixel) != 1
                or str(ds.PhotometricInterpretation) != "MONOCHROME2"
                or (int(ds.BitsAllocated), int(ds.BitsStored),
                    int(ds.HighBit), int(ds.PixelRepresentation))
                != (16, 16, 15, 1)):
            bad_encoding.append(name)
        if float(ds.RescaleSlope) != 1.0 or float(ds.RescaleIntercept) != 0.0:
            bad_rescale.append(name)
        if (ds_floats(ds, (0x0028, 0x0030)) != spacing[:2]
                or float(ds.SliceThickness) != spacing[2]
                or float(ds.SpacingBetweenSlices) != spacing[2]):
            bad_spacing_el.append(name)
        iop = ds_floats(ds, (0x0020, 0x0037))
        if iop != [float(v) for v in geom["image_orientation_patient"]]:
            bad_iop.append(name)
        if len(ds.PixelData) != nx * ny * 2:
            bad_pixlen.append(name)
        if (str(ds.BurnedInAnnotation) != "YES"
                or [str(x) for x in ds.ImageType] != ["DERIVED", "SECONDARY"]
                or "SYNTHETIC" not in str(ds.StudyDescription)
                or "SYNTHETIC" not in str(ds.SeriesDescription)
                or "SYNTHETIC" not in str(ds.ImageComments)):
            bad_wm_meta.append(name)
        arr = ds.pixel_array
        if arr.shape != (ny, nx) or arr.dtype != np.int16:
            bad_shape.append(name)
            continue
        lo, hi = int(arr.min()), int(arr.max())
        gmin = lo if gmin is None else min(gmin, lo)
        gmax = hi if gmax is None else max(gmax, hi)
        if any(int(arr[r, c]) != WM_VALUE for (r, c) in offs):
            bad_wm_pix.append(name)
        binpath = os.path.join(WEB_DIR, subj, f"hu-{idx:04d}.bin")
        barr = np.fromfile(binpath, dtype="<i2").reshape(ny, nx)
        if not np.array_equal(arr, barr):
            bad_bin.append(name)
        ipps.append((idx, ds_floats(ds, (0x0020, 0x0032)),
                     float(ds.SliceLocation)))
        for elem in list(ds) + list(fm):
            lim = VR_MAX.get(elem.VR)
            if lim is None or elem.VM == 0:
                continue
            vals = elem.value if elem.VM > 1 else [elem.value]
            for v in vals:
                if isinstance(v, str) and len(v) > lim:
                    key = (f"({elem.tag.group:04X},{elem.tag.element:04X})",
                           elem.VR, lim, len(v), v)
                    vr_violations.setdefault(key, []).append(
                        str(ds.SOPInstanceUID))

    check(not bad_magic, f"{subj}: all {n} files are PS3.10 "
                          f"(preamble + DICM)")
    check(not bad_parse, f"{subj}: pydicom parses all {n} instances "
                         f"unforced ({len(bad_parse)} failures)")
    for lst, label in (
            (bad_ts, "Transfer Syntax is Explicit VR Little Endian"),
            (bad_meta_uid, "file-meta SOP Class/Instance agree with dataset"),
            (bad_sopclass, "SOP Class is CT Image Storage"),
            (bad_sopuid, "SOP Instance UID equals the manifest's"),
            (dup_uid, "SOP Instance UIDs are unique"),
            (bad_study_uid, "Study Instance UID equals the manifest's"),
            (bad_series_uid, "Series Instance UID equals the manifest's"),
            (bad_for_uid, "Frame of Reference UID equals the manifest's"),
            (bad_modality, "Modality is CT"),
            (bad_patient, "patient identity matches the recorded subject "
                          f"({exp_patient_id}, {exp_sex}, {exp_age})"),
            (bad_studyid, f"StudyID / Implementation Version Name carry "
                          f"the {mtag} tag"),
            (bad_seriesnum, "Series Number is 1"),
            (bad_instnum, "Instance Numbers are 1..N in manifest order"),
            (bad_dims, f"Rows x Columns == recorded {ny} x {nx}"),
            (bad_encoding, "1 sample/pixel, MONOCHROME2, 16/16/15, signed"),
            (bad_rescale, "Rescale Slope 1 / Intercept 0"),
            (bad_spacing_el, "Pixel Spacing / Slice Thickness / Spacing "
                             "Between Slices == recorded spacing"),
            (bad_iop, "Image Orientation Patient == recorded "
                      "[1,0,0, 0,1,0]"),
            (bad_pixlen, "Pixel Data length == Rows x Columns x 2 "
                         "(uncompressed int16)"),
            (bad_wm_meta, "watermark metadata in every instance "
                          "(BurnedInAnnotation YES, ImageType "
                          "DERIVED\\SECONDARY, SYNTHETIC in Study/Series "
                          "Description and Image Comments)"),
            (bad_wm_pix, "watermark pixels: all 123 glyph offsets hold "
                         "3071 HU in every instance (pydicom)"),
            (bad_shape, "pixel_array is int16 of the recorded shape"),
            (bad_bin, "DICOM pixel array == shipped web HU bin, every "
                      "instance (pydicom)")):
        check(not lst, f"{subj}: {label} — {n - len(lst)}/{n} instances"
                       + (f"; failures: {lst[:4]}" if lst else ""))
    check(len(dates) == 1 and len(times) == 1,
          f"{subj}: Study/Series Date and Time constant across the "
          f"series ({sorted(dates)}, {sorted(times)})")
    rng = man["pixel_route"]["stored_range_hu"]
    check([gmin, gmax] == list(rng),
          f"{subj}: pydicom global pixel range [{gmin}, {gmax}] == "
          f"recorded stored range {rng}")

    # ---- 6. geometry chain ------------------------------------------
    ipps.sort()
    p0 = ipps[0][1]
    check(all(abs(p0[i] - ipp0[i]) <= 2e-6 for i in range(3)),
          f"{subj}: first-slice IPP {p0} == recorded {ipp0} (2e-6 mm)")
    xy_const = all(p[1][0] == p0[0] and p[1][1] == p0[1] for p in ipps)
    steps = [ipps[i + 1][1][2] - ipps[i][1][2] for i in range(len(ipps) - 1)]
    steps_ok = all(abs(s - spacing[2]) <= 1e-6 for s in steps)
    check(xy_const and steps_ok,
          f"{subj}: IPP x/y constant; all {len(steps)} z steps == "
          f"{spacing[2]} mm (1e-6)")
    check(all(abs(p[2] - p[1][2]) <= 1e-6 for p in ipps),
          f"{subj}: Slice Location == IPP z in every instance")
    span = ipps[-1][1][2] - ipps[0][1][2]
    check(abs(span - (n - 1) * spacing[2]) <= 1e-6
          and abs(n * spacing[2] - (span + spacing[2])) <= 1e-6,
          f"{subj}: centre span {span:.1f} mm == (N-1) x spacing; full "
          f"extent {n * spacing[2]:.1f} mm == N x spacing")
    iop = [float(v) for v in geom["image_orientation_patient"]]
    r = np.array(iop[:3]); c = np.array(iop[3:])
    normal = np.cross(r, c)
    check(abs(np.linalg.norm(r) - 1) < 1e-12
          and abs(np.linalg.norm(c) - 1) < 1e-12
          and float(np.dot(r, c)) == 0.0
          and list(normal) == [0.0, 0.0, 1.0],
          f"{subj}: IOP row/column cosines orthonormal, slice normal "
          f"{list(normal)}")
    check(spacing[0] == spacing[1] == spacing[2],
          f"{subj}: recorded spacing isotropic {spacing} (the "
          f"sform-derived claim, as expressed in the series)")

    # glyph picture from slice 0's pydicom pixels (report only)
    ds0 = pydicom.dcmread(os.path.join(base, insts[0]["file"]))
    a0 = ds0.pixel_array
    rows = sorted({r for r, _ in offs}); cols = sorted({c for _, c in offs})
    art = ["".join("#" if int(a0[r, c]) == WM_VALUE else "."
                   for c in range(min(cols), max(cols) + 1))
           for r in range(min(rows), max(rows) + 1)]
    report(f"{subj}: slice-0 glyph box read through pydicom "
           f"(rows {min(rows)}..{max(rows)}, cols {min(cols)}.."
           f"{max(cols)}, '#' = 3071 HU):")
    for line in art:
        print("        " + line)

    # ---- 10. conformance findings ------------------------------------
    for (tag, vr, lim, ln, val), uids in sorted(vr_violations.items()):
        finding(f"{subj}: {tag} VR {vr} value length {ln} exceeds the "
                f"PS3.5 maximum {lim} in {len(uids)}/{n} instances — "
                f"value: {val!r} (present in every instance; first SOP "
                f"Instance UID {uids[0]}, last {uids[-1]})")
    if not vr_violations:
        report(f"{subj}: value-length audit: no PS3.5 violations")

    # ---- 9. nibabel end-to-end corroboration --------------------------
    ct_path = os.path.join(TS_DIR, subj, "ct.nii.gz")
    img = nib.load(ct_path)
    raw = img.dataobj.get_unscaled()
    check(raw.dtype == np.int32 and raw.shape == (nx, ny, nz),
          f"{subj}: source NIfTI is int32 of shape {raw.shape} "
          f"(nibabel; recorded dims {(nx, ny, nz)})")
    slope, inter = img.header.get_slope_inter()
    check((slope is None or float(slope) == 1.0) and float(inter or 0) == 0.0,
          f"{subj}: source scaling slope {slope} / intercept {inter} "
          f"(HU as stored)")
    check([int(raw.min()), int(raw.max())] == list(rng),
          f"{subj}: source int32 range [{int(raw.min())}, "
          f"{int(raw.max())}] == recorded stored range {rng} and sits "
          f"inside int16 (conversion lossless)")
    aff = img.affine
    offdiag = max(abs(aff[i, j]) for i in range(3) for j in range(3) if i != j)
    steps_ok = all(abs(aff[i, i] - spacing[i]) <= 1e-4 for i in range(3))
    check(offdiag <= 1e-4 and steps_ok,
          f"{subj}: source affine diagonal (max off-diagonal "
          f"{offdiag:.2e}) with steps "
          f"{[round(float(aff[i, i]), 4) for i in range(3)]} == "
          f"recorded spacing")
    ox, oy, oz = (float(aff[i, 3]) for i in range(3))
    derived_ipp0 = [-(ox + (nx - 1) * spacing[0]),
                    -(oy + (ny - 1) * spacing[1]), oz]
    check(all(abs(derived_ipp0[i] - ipp0[i]) <= 2e-3 for i in range(3)),
          f"{subj}: source origin reproduces the recorded first-slice "
          f"IPP under the LPS relation: {derived_ipp0} vs {ipp0} "
          f"(2e-3 mm)")
    diff_bad, diff_counts = [], []
    natural_3071 = 0
    for idx, inst in enumerate(insts):
        ds = pydicom.dcmread(os.path.join(base, inst["file"]))
        arr = ds.pixel_array
        expect = raw[::-1, ::-1, idx].T
        diff = {(int(r), int(c)) for r, c in zip(*np.nonzero(arr != expect))}
        if diff != off_set or any(int(arr[r, c]) != WM_VALUE
                                  for (r, c) in diff):
            diff_bad.append(inst["file"])
        diff_counts.append(len(diff))
        natural_3071 += int((expect[list(zip(*off_set))[0],
                                    list(zip(*off_set))[1]] == WM_VALUE).sum()) \
            if idx == 0 else 0
    check(not diff_bad,
          f"{subj}: per-slice DICOM-vs-source difference set == the "
          f"123 glyph offsets, DICOM value 3071 at every differing "
          f"voxel, all {n} slices (nibabel x pydicom); differing-voxel "
          f"counts per slice: min {min(diff_counts)}, max "
          f"{max(diff_counts)}")
    report(f"{subj}: glyph positions whose source value was already "
           f"3071 HU on slice 0: {natural_3071} of 123 (all other glyph "
           f"voxels are source values overwritten by the watermark)")


def main():
    print("ANATOMICA imaging toolkit checker (Milestone 45) — "
          f"pydicom {pydicom.__version__}, nibabel {nib.__version__}, "
          f"numpy {np.__version__}")
    subjects = sorted(d for d in os.listdir(IMG_DIR)
                      if os.path.exists(os.path.join(IMG_DIR, d,
                                                     "series.json")))
    print(f"subjects: {', '.join(subjects)}")
    for subj in subjects:
        check_subject(subj)
    print()
    if failures:
        print(f"{len(failures)} HARD CHECK(S) FAILED")
        for f in failures:
            print(f"  FAILED: {f}")
    else:
        print("ALL HARD CHECKS PASS")
    print(f"{len(findings)} conformance finding(s) standing "
          f"(reported, not gated — see MILESTONE-45.md):")
    for f in findings:
        print(f"  FINDING: {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
