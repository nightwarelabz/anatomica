#!/usr/bin/env python3
"""ANATOMICA TotalSegmentator label census — Milestone 3.

Re-derives the dataset's label set from the Zenodo archive's own central
directory (every file name in all subject folders; no pixel data),
cross-checks it against the label list published in the TotalSegmentator
code package (totalsegmentator/map_to_binary.py, map "total_v1",
Apache-2.0), and computes the overlap with the ANATOMICA Body Model's
206 skeletal records using the explicit label->record rules below.

Outputs (into data/sources/totalsegmentator-1.0/):
  labels.json — per-label subject counts + package agreement + mapping
  labels.md   — human-readable census

Stdlib only. Network: two range fetches against Zenodo (EOCD + CD).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ts_intake import fetch_range, parse_eocd, parse_cd, TOTAL_SIZE  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRCDIR = os.path.join(ROOT, "data", "sources", "totalsegmentator-1.0")

# --- explicit TS label -> skeletal record-id rules (auditable) ---
def skeletal_record(label):
    if label.startswith("vertebrae_"):
        return "vert_" + label.split("_", 1)[1]              # vertebrae_T6 -> vert_T6
    if label.startswith("rib_left_"):
        return "rib" + label.rsplit("_", 1)[1] + "_left"     # rib_left_3 -> rib3_left
    if label.startswith("rib_right_"):
        return "rib" + label.rsplit("_", 1)[1] + "_right"
    direct = {
        "femur_left": "femur_left", "femur_right": "femur_right",
        "humerus_left": "humerus_left", "humerus_right": "humerus_right",
        "scapula_left": "scapula_left", "scapula_right": "scapula_right",
        "hip_left": "hip_left", "hip_right": "hip_right",
        "sacrum": "sacrum",
        "clavicula_left": "clavicle_left", "clavicula_right": "clavicle_right",
    }
    return direct.get(label)

# non-skeletal labels grouped by Body Model system (curated, stated here)
SYSTEM_GROUPS = {
    "cardiovascular": ["aorta", "inferior_vena_cava", "portal_vein_and_splenic_vein",
                       "pulmonary_artery", "iliac_artery_left", "iliac_artery_right",
                       "iliac_vena_left", "iliac_vena_right", "heart_myocardium",
                       "heart_atrium_left", "heart_atrium_right",
                       "heart_ventricle_left", "heart_ventricle_right"],
    "respiratory": ["trachea", "lung_upper_lobe_left", "lung_lower_lobe_left",
                    "lung_upper_lobe_right", "lung_middle_lobe_right", "lung_lower_lobe_right"],
    "digestive": ["esophagus", "stomach", "duodenum", "small_bowel", "colon",
                  "liver", "gallbladder", "pancreas"],
    "urinary": ["kidney_left", "kidney_right", "urinary_bladder"],
    "lymphatic": ["spleen"],
    "endocrine": ["adrenal_gland_left", "adrenal_gland_right"],
    "nervous": ["brain"],
    "muscular": ["autochthon_left", "autochthon_right",
                 "gluteus_maximus_left", "gluteus_maximus_right",
                 "gluteus_medius_left", "gluteus_medius_right",
                 "gluteus_minimus_left", "gluteus_minimus_right",
                 "iliopsoas_left", "iliopsoas_right"],
    "integumentary/other": ["face"],
}


def main():
    tail = fetch_range(TOTAL_SIZE - (1 << 20), TOTAL_SIZE - 1)
    n_total, cd_size, cd_off = parse_eocd(tail, 0)
    entries = parse_cd(fetch_range(cd_off, cd_off + cd_size - 1))

    subjects = {}
    label_subjects = {}
    for e in entries:
        p = e["name"].split("/")
        if len(p) >= 2 and p[1].startswith("s") and p[1][1:].isdigit():
            subjects.setdefault(p[1], 0)
            subjects[p[1]] += 1
            if len(p) == 4 and p[2] == "segmentations" and p[3].endswith(".nii.gz"):
                label_subjects.setdefault(p[3][:-7], set()).add(p[1])
    labels = {k: len(v) for k, v in sorted(label_subjects.items())}
    n_subj = len(subjects)

    with open(os.path.join(ROOT, "tools", "ts_package_class_map_v1.json")) as f:
        pkg = json.load(f)
    pkg_set, idx_set = set(pkg), set(labels)

    mapping = json.load(open(os.path.join(ROOT, "data", "skeletal", "fma-mapping.json")))
    record_ids = {r["record_id"] for r in mapping["mappings"]}
    overlap = {}
    for lab in labels:
        rid = skeletal_record(lab)
        if rid:
            assert rid in record_ids, (lab, rid)
            overlap[lab] = rid

    out = {
        "dataset": "TotalSegmentator dataset v1.0 (Zenodo 6802614)",
        "subjects_in_index": n_subj,
        "index_entries": n_total,
        "distinct_labels": len(labels),
        "labels": labels,
        "package_map_labels": len(pkg),
        "index_vs_package": {
            "only_in_index": sorted(idx_set - pkg_set),
            "only_in_package": sorted(pkg_set - idx_set),
        },
        "skeletal_overlap": overlap,
        "skeletal_records_covered": len(set(overlap.values())),
        "system_groups_non_skeletal": SYSTEM_GROUPS,
    }
    with open(os.path.join(SRCDIR, "labels.json"), "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)

    grouped = {}
    for lab in labels:
        for sysname, members in SYSTEM_GROUPS.items():
            if lab in members:
                grouped[lab] = sysname
    lines = [
        "# TotalSegmentator v1 label census (Milestone 3)",
        "",
        f"- Subjects in archive index: {n_subj}; index entries: {n_total}.",
        f"- Distinct segmentation labels: {len(labels)} (dataset title claims 104).",
        f"- Package class map (total_v1): {len(pkg)} labels; "
        f"index-only: {sorted(idx_set - pkg_set) or 'none'}; "
        f"package-only: {sorted(pkg_set - idx_set) or 'none'}.",
        f"- Labels present in all {n_subj} subjects: "
        f"{sum(1 for v in labels.values() if v == n_subj)}; "
        f"min subject count: {min(labels.values())} ({min(labels, key=labels.get)}).",
        "",
        "## Skeletal overlap with the 206-record Body Model",
        "",
        f"{len(overlap)} TS labels map onto {len(set(overlap.values()))} skeletal records:",
        "",
    ]
    for lab in sorted(overlap):
        lines.append(f"- `{lab}` -> `{overlap[lab]}` (present in {labels[lab]}/{n_subj} subjects)")
    lines += [
        "",
        "Notable absences for the skeletal module: no sternum label (v1; "
        "sternum exists only in the v2 label set), no tibia/fibula/patella, "
        "no hand or foot bones, no individual skull bones (`face` is a "
        "soft-tissue label and is NOT mapped to any bone record), no "
        "ossicles, no coccyx.",
        "",
        "## Non-skeletal labels by Body Model system",
        "",
    ]
    for sysname, members in SYSTEM_GROUPS.items():
        present = [m for m in members if m in labels]
        lines.append(f"- **{sysname}** ({len(present)}): " + ", ".join(f"`{m}`" for m in present))
    ungrouped = [lab for lab in labels if lab not in overlap and lab not in grouped]
    lines += ["", f"Ungrouped labels: {ungrouped or 'none'}", "",
              "## Full label list with subject counts", ""]
    for lab, cnt in labels.items():
        lines.append(f"- `{lab}`: {cnt}")
    with open(os.path.join(SRCDIR, "labels.md"), "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"subjects={n_subj} labels={len(labels)} pkg={len(pkg)} "
          f"idx-only={sorted(idx_set - pkg_set)} pkg-only={sorted(pkg_set - idx_set)}")
    print(f"skeletal overlap: {len(overlap)} labels -> {len(set(overlap.values()))} records")
    print(f"labels in all subjects: {sum(1 for v in labels.values() if v == n_subj)}; "
          f"min count {min(labels.values())} ({min(labels, key=labels.get)})")
    print(f"ungrouped: {ungrouped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
