#!/usr/bin/env python3
"""ANATOMICA provenance ledger builder.

Inventories adopted data files with source, license, and SHA-256 into a
ledger (JSON + human-readable summary). Provenance is a build gate:
a geometry file may be referenced by the geometry registry only if it has
a ledger entry with a determined, compatible license.

Usage:
    provenance.py --root DIR --source NAME --license SPDX \
        [--license-evidence PATH] [--version-str RELEASE] \
        [--out ledger.json] [--summary ledger-summary.md] \
        [--merge EXISTING_LEDGER.json] [--allow-unknown]

With --merge, entries for files already present (same path+sha256) keep
their recorded structure_id; new/changed files are added afresh.

Exit status: 0 if every inventoried file has a determined license,
1 otherwise (unless --allow-unknown). Stdlib only.
"""
import argparse
import hashlib
import json
import os
import struct
import sys
from datetime import datetime, timezone

MESH_FORMATS = {".obj", ".stl", ".ply", ".glb", ".gltf", ".fbx", ".dae"}


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def obj_stats(path):
    v = f = 0
    with open(path, "rb") as fh:
        for line in fh:
            if line.startswith(b"v "):
                v += 1
            elif line.startswith(b"f "):
                f += 1
    return {"vertices": v, "faces": f}


def stl_stats(path):
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        head = fh.read(84)
    if len(head) == 84 and not head[:5] == b"solid":
        (n,) = struct.unpack("<I", head[80:84])
        if 84 + 50 * n == size:
            return {"triangles": n}
    return {"triangles": None, "note": "ascii or nonstandard STL; count not parsed"}


def glb_stats(path):
    with open(path, "rb") as fh:
        data = fh.read(20)
        if len(data) < 20 or data[:4] != b"glTF":
            return {"error": "not a GLB"}
        (clen,) = struct.unpack("<I", data[12:16])
        fh.seek(20)
        js = json.loads(fh.read(clen))
    names = [n.get("name") for n in js.get("nodes", []) if n.get("name")]
    return {
        "meshes": len(js.get("meshes", [])),
        "nodes": len(js.get("nodes", [])),
        "named_nodes": names,
    }


def file_stats(path, ext):
    try:
        if ext == ".obj":
            return obj_stats(path)
        if ext == ".stl":
            return stl_stats(path)
        if ext == ".glb":
            return glb_stats(path)
    except Exception as e:  # parse failure is data, not a crash
        return {"error": f"{type(e).__name__}: {e}"}
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--license", default="UNKNOWN")
    ap.add_argument("--license-evidence", default=None)
    ap.add_argument("--version-str", default=None)
    ap.add_argument("--out", default="ledger.json")
    ap.add_argument("--summary", default=None)
    ap.add_argument("--merge", default=None)
    ap.add_argument("--allow-unknown", action="store_true")
    args = ap.parse_args()

    prior = {}
    if args.merge and os.path.exists(args.merge):
        with open(args.merge) as f:
            for e in json.load(f).get("entries", []):
                prior[(e["path"], e["sha256"])] = e

    entries = []
    for dirpath, _dirs, files in os.walk(args.root):
        for name in sorted(files):
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, args.root)
            ext = os.path.splitext(name)[1].lower()
            digest = sha256_of(path)
            old = prior.get((rel, digest))
            entries.append({
                "path": rel,
                "bytes": os.path.getsize(path),
                "sha256": digest,
                "format": ext.lstrip(".") or "none",
                "source": args.source,
                "source_version": args.version_str,
                "license": args.license,
                "license_evidence": args.license_evidence,
                "stats": file_stats(path, ext) if ext in MESH_FORMATS else {},
                "structure_id": old.get("structure_id") if old else None,
            })
    entries.sort(key=lambda e: e["path"])

    ledger = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "root": os.path.abspath(args.root),
        "entries": entries,
    }
    with open(args.out, "w") as f:
        json.dump(ledger, f, indent=1, sort_keys=True)

    unknown = [e for e in entries if e["license"] == "UNKNOWN"]
    total_bytes = sum(e["bytes"] for e in entries)
    if args.summary:
        by_fmt, by_lic = {}, {}
        for e in entries:
            by_fmt[e["format"]] = by_fmt.get(e["format"], 0) + 1
            by_lic[e["license"]] = by_lic.get(e["license"], 0) + 1
        lines = [
            f"# Provenance ledger summary — {args.source}",
            "",
            f"- Files: {len(entries)}",
            f"- Total bytes: {total_bytes:,}",
            f"- By format: {json.dumps(by_fmt, sort_keys=True)}",
            f"- By license: {json.dumps(by_lic, sort_keys=True)}",
        ]
        if unknown:
            lines += ["", "## UNKNOWN license (gate failures)", ""]
            lines += [f"- {e['path']}" for e in unknown]
        with open(args.summary, "w") as f:
            f.write("\n".join(lines) + "\n")

    print(f"files={len(entries)} bytes={total_bytes} unknown_license={len(unknown)}")
    if unknown and not args.allow_unknown:
        print("GATE FAIL: files with UNKNOWN license present", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
