#!/usr/bin/env python3
"""ANATOMICA geometry coverage census.

Counts what the adopted geometry actually contains and maps it against the
Body Model inventory targets. Every number is computed from the data files
themselves; anything that cannot be derived is reported as NOT DERIVABLE,
never estimated.

Sections:
  A. BodyParts3D 4.0 — concepts (ISA parts list), element files (meshes),
     concept<->file mapping coverage (element parts list), per-file header
     license census.
  B. Z-Anatomy GLB exports — named nodes per system file (reference only;
     NC-encumbered as distributed, see data/sources/z-anatomy-glb/SOURCE.md).
  C. Skeletal coverage — the verified 206-bone Phase-1 inventory matched by
     normalized name against BodyParts3D concept names (name-match coverage;
     geometric registration is later pipeline work and is NOT claimed here).

Usage: census.py [--out census.json] [--report census.md]
Stdlib only.
"""
import argparse
import json
import os
import re
import struct
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP3D = os.path.join(ROOT, "data", "sources", "bodyparts3d-4.0")
ZA = os.path.join(ROOT, "data", "sources", "z-anatomy-glb")
SKELETON_JS = os.path.expanduser("~/workspace/anatomica-app/data/skeleton.js")


def read_tsv(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        rows = [ln.rstrip("\n").split("\t") for ln in f if ln.strip()]
    return rows[1:]  # drop header


def norm(name):
    s = name.lower()
    s = re.sub(r"\((right|left)\)", "", s)
    s = re.sub(r"\b(right|left)\b", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def glb_node_names(path):
    with open(path, "rb") as fh:
        head = fh.read(20)
        (clen,) = struct.unpack("<I", head[12:16])
        fh.seek(20)
        doc = json.loads(fh.read(clen))
    return [n.get("name") for n in doc.get("nodes", []) if n.get("name")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "tools", "census.json"))
    ap.add_argument("--report", default=os.path.join(ROOT, "tools", "census.md"))
    args = ap.parse_args()
    R = {}

    # ---- A. BodyParts3D ----
    isa_rows = read_tsv(os.path.join(BP3D, "isa_parts_list_e.txt"))
    concepts = {r[0]: r[2] for r in isa_rows if len(r) >= 3}
    elem_rows = read_tsv(os.path.join(BP3D, "isa_element_parts.txt"))
    concept_files = {}
    for fma, _name, fj in [(r[0], r[1], r[2]) for r in elem_rows if len(r) >= 3]:
        concept_files.setdefault(fma, set()).add(fj)
    mesh_files = {}
    for zname in ("isa_BP3D_4.0_obj_99.zip", "partof_BP3D_4.0_obj_99.zip"):
        with zipfile.ZipFile(os.path.join(BP3D, zname)) as zf:
            mesh_files[zname] = {os.path.splitext(os.path.basename(n))[0]
                                 for n in zf.namelist() if n.endswith(".obj")}
    isa_meshes = mesh_files["isa_BP3D_4.0_obj_99.zip"]
    mapped_with_mesh = {c for c, fjs in concept_files.items() if fjs & isa_meshes}
    header_licenses = {}
    work = os.path.join(ROOT, "work", "bp3d", "isa_BP3D_4.0_obj_99")
    if os.path.isdir(work):
        for fn in os.listdir(work):
            with open(os.path.join(work, fn), "rb") as fh:
                for line in fh:
                    if b"license for this database" in line:
                        key = ("CC BY-SA 2.1 Japan" if b"Share Alike 2.1 Japan" in line
                               else line.decode("utf-8", "replace")[:80])
                        header_licenses[key] = header_licenses.get(key, 0) + 1
                        break
    R["bodyparts3d"] = {
        "isa_concepts_listed": len(concepts),
        "isa_mesh_files": len(isa_meshes),
        "partof_mesh_files": len(mesh_files["partof_BP3D_4.0_obj_99.zip"]),
        "concepts_with_at_least_one_mesh_file": len(mapped_with_mesh),
        "concepts_without_mesh_file": len(concepts) - len(mapped_with_mesh),
        "obj_header_license_census_isa": header_licenses,
        "current_license_page": "CC BY 4.0 (DBCLS page archived as LICENSE-PAGE.html)",
        "per_system_breakdown": "NOT DERIVABLE from the release files (no system field); not estimated",
    }

    # ---- B. Z-Anatomy GLBs ----
    za = {}
    for fn in sorted(os.listdir(ZA)):
        if fn.endswith(".glb"):
            names = glb_node_names(os.path.join(ZA, fn))
            za[fn] = {"named_nodes": len(names), "nodes_sample": names[:5]}
    R["z_anatomy_glb_reference_only"] = za

    # ---- C. Skeletal coverage vs the verified 206 ----
    src = open(SKELETON_JS, encoding="utf-8").read()
    data = json.loads(src[src.index("{"):src.rindex("}") + 1])
    bones = data["bones"]
    concept_names = {norm(v) for v in concepts.values()}
    matched, unmatched = [], []
    for b in bones:
        (matched if norm(b["name"]) in concept_names else unmatched).append(b["name"])
    za_skeletal = {norm(n) for n in glb_node_names(os.path.join(ZA, "skeletal.glb"))}
    za_matched = [b["name"] for b in bones if norm(b["name"]) in za_skeletal]
    R["skeletal_coverage"] = {
        "target_bones": len(bones),
        "counting_convention": data["meta"]["counting_convention"],
        "bp3d_name_matched": len(matched),
        "bp3d_name_unmatched": unmatched,
        "za_skeletal_glb_named_nodes": len(za_skeletal),
        "za_name_matched": len(za_matched),
        "method": "normalized-name match (side/punctuation stripped). Name coverage only; "
                  "geometric registration is separate pipeline work and is not claimed.",
    }

    with open(args.out, "w") as f:
        json.dump(R, f, indent=1, sort_keys=True)
    bp, sk = R["bodyparts3d"], R["skeletal_coverage"]
    lines = [
        "# Geometry coverage census (computed by tools/census.py)",
        "",
        "## BodyParts3D 4.0",
        f"- ISA concepts listed: {bp['isa_concepts_listed']}",
        f"- ISA mesh files (.obj): {bp['isa_mesh_files']}",
        f"- PART-OF mesh files (.obj): {bp['partof_mesh_files']}",
        f"- Concepts with >=1 mesh file: {bp['concepts_with_at_least_one_mesh_file']}",
        f"- Concepts without a mesh file: {bp['concepts_without_mesh_file']}",
        f"- OBJ header license census (ISA): {json.dumps(bp['obj_header_license_census_isa'])}",
        f"- Current DBCLS license page: {bp['current_license_page']}",
        f"- Per-system breakdown: {bp['per_system_breakdown']}",
        "",
        "## Z-Anatomy GLB exports (reference only — NC-encumbered as distributed)",
    ]
    for fn, s in za.items():
        lines.append(f"- {fn}: {s['named_nodes']} named nodes")
    lines += [
        "",
        "## Skeletal coverage vs the verified 206-bone inventory",
        f"- Target bones: {sk['target_bones']}",
        f"- BodyParts3D name-matched: {sk['bp3d_name_matched']}",
        f"- BodyParts3D name-unmatched: {len(sk['bp3d_name_unmatched'])}",
        f"- Z-Anatomy skeletal.glb name-matched: {sk['za_name_matched']} of {sk['za_skeletal_glb_named_nodes']} named nodes",
        f"- Method: {sk['method']}",
        "",
        "### Unmatched bone names (BodyParts3D)",
    ] + [f"- {n}" for n in sk["bp3d_name_unmatched"]]
    with open(args.report, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(json.dumps({k: (v if not isinstance(v, dict) else "...") for k, v in R.items()}, indent=1))
    print(f"BP3D: concepts={bp['isa_concepts_listed']} isa_meshes={bp['isa_mesh_files']} "
          f"with_mesh={bp['concepts_with_at_least_one_mesh_file']}")
    print(f"Skeletal: target={sk['target_bones']} bp3d_matched={sk['bp3d_name_matched']} "
          f"za_matched={sk['za_name_matched']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
