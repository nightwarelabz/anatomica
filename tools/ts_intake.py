#!/usr/bin/env python3
"""ANATOMICA TotalSegmentator intake (subset via HTTP range requests).

The full Zenodo file is a single 28,404,091,806-byte zip. Measured
throughput to zenodo.org from this VM is ~0.95 MB/s, so a full download
is ~8 h — impractical in-session. This script instead:

  1. fetches the zip End-Of-Central-Directory + the full central
     directory (the archive's own file index) via range requests;
  2. derives the complete label census from that index (every entry
     name in all 1,204 subject folders — no pixel data needed);
  3. downloads a representative subset of complete subject folders
     plus meta.csv, extracting each entry from its byte range and
     verifying the CRC-32 recorded in the central directory.

Everything downloaded is written under the output dir with SHA-256
hashes printed for the SOURCE.md / provenance ledger. Stdlib only.
"""
import hashlib
import json
import os
import struct
import sys
import time
import urllib.request
import zlib

URL = "https://zenodo.org/api/records/6802614/files/Totalsegmentator_dataset.zip/content"
TOTAL_SIZE = 28404091806
ZENODO_MD5 = "f0fbb3f91d9d99f2169863545f577b30"  # published by Zenodo for the full zip
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                   "data", "sources", "totalsegmentator-1.0")
N_SUBJECTS = 10


def fetch_range(start, end, retries=4):
    """Fetch bytes [start, end] inclusive."""
    for attempt in range(retries):
        req = urllib.request.Request(URL, headers={"Range": f"bytes={start}-{end}"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
            if len(data) == end - start + 1:
                return data
            print(f"  short read {len(data)} != {end-start+1}, retry", file=sys.stderr)
        except Exception as e:
            print(f"  fetch error {e}, retry", file=sys.stderr)
        time.sleep(2 * attempt + 1)
    raise RuntimeError(f"range {start}-{end} failed after {retries} tries")


def parse_eocd(tail, tail_start):
    i = tail.rfind(b"PK\x05\x06")
    if i < 0:
        raise RuntimeError("EOCD not found")
    (disk, cd_disk, n_disk, n_total, cd_size, cd_off, _clen) = struct.unpack_from("<HHHHIIH", tail, i + 4)
    if cd_off == 0xFFFFFFFF or cd_size == 0xFFFFFFFF:
        # ZIP64: locator sits 20 bytes before the classic EOCD
        li = tail.rfind(b"PK\x06\x07")
        (z64_off,) = struct.unpack_from("<Q", tail, li + 8)
        z64 = fetch_range(z64_off, z64_off + 55)
        (n_total,) = struct.unpack_from("<Q", z64, 32)
        (cd_size,) = struct.unpack_from("<Q", z64, 40)
        (cd_off,) = struct.unpack_from("<Q", z64, 48)
    return n_total, cd_size, cd_off


def parse_cd(cd):
    entries = []
    pos = 0
    while pos < len(cd):
        if cd[pos:pos + 4] != b"PK\x01\x02":
            raise RuntimeError(f"CD entry signature missing at {pos}")
        (method,) = struct.unpack_from("<H", cd, pos + 10)
        (crc,) = struct.unpack_from("<I", cd, pos + 16)
        (csize, usize) = struct.unpack_from("<II", cd, pos + 20)
        (fnlen, extralen, comlen) = struct.unpack_from("<HHH", cd, pos + 28)
        (lho,) = struct.unpack_from("<I", cd, pos + 42)
        name = cd[pos + 46: pos + 46 + fnlen].decode("utf-8")
        extra = cd[pos + 46 + fnlen: pos + 46 + fnlen + extralen]
        # ZIP64 extra field 0x0001: usize, csize, lho in that order when 0xFFFFFFFF
        j = 0
        vals = []
        while j + 4 <= len(extra):
            (tag, sz) = struct.unpack_from("<HH", extra, j)
            if tag == 0x0001:
                vals = list(struct.unpack_from(f"<{sz // 8}Q", extra, j + 4))
            j += 4 + sz
        k = 0
        if usize == 0xFFFFFFFF:
            usize = vals[k]; k += 1
        if csize == 0xFFFFFFFF:
            csize = vals[k]; k += 1
        if lho == 0xFFFFFFFF:
            lho = vals[k]; k += 1
        entries.append({"name": name, "method": method, "crc": crc,
                        "csize": csize, "usize": usize, "lho": lho})
        pos += 46 + fnlen + extralen + comlen
    return entries


def extract(entry):
    head = fetch_range(entry["lho"], entry["lho"] + 29)
    if head[:4] != b"PK\x03\x04":
        raise RuntimeError(f"local header missing for {entry['name']}")
    (fnlen, extralen) = struct.unpack_from("<HH", head, 26)
    start = entry["lho"] + 30 + fnlen + extralen
    raw = fetch_range(start, start + entry["csize"] - 1)
    if entry["method"] == 0:
        data = raw
    elif entry["method"] == 8:
        data = zlib.decompressobj(-15).decompress(raw)
    else:
        raise RuntimeError(f"unsupported method {entry['method']}")
    if len(data) != entry["usize"]:
        raise RuntimeError(f"size mismatch {entry['name']}: {len(data)} != {entry['usize']}")
    if zlib.crc32(data) & 0xFFFFFFFF != entry["crc"]:
        raise RuntimeError(f"CRC mismatch {entry['name']}")
    return data


def main():
    out = os.path.abspath(OUT)
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    print("fetching tail (EOCD)…")
    tail_len = 1 << 20
    tail = fetch_range(TOTAL_SIZE - tail_len, TOTAL_SIZE - 1)
    n_total, cd_size, cd_off = parse_eocd(tail, TOTAL_SIZE - tail_len)
    print(f"entries={n_total} cd_size={cd_size} cd_off={cd_off}")
    print("fetching central directory…")
    cd = fetch_range(cd_off, cd_off + cd_size - 1)
    entries = parse_cd(cd)
    assert len(entries) == n_total, (len(entries), n_total)
    print(f"parsed {len(entries)} entries in {time.time()-t0:.0f}s")

    # ---- label census from the full central directory ----
    subjects = {}
    for e in entries:
        parts = e["name"].split("/")
        if len(parts) >= 3 and parts[1].startswith("s") and parts[1][1:].isdigit():
            subjects.setdefault(parts[1], []).append(e)
    label_subjects = {}
    for subj, es in subjects.items():
        for e in es:
            p = e["name"].split("/")
            if len(p) == 4 and p[2] == "segmentations" and p[3].endswith(".nii.gz"):
                label_subjects.setdefault(p[3][:-len(".nii.gz")], set()).add(subj)
    labels = {k: len(v) for k, v in sorted(label_subjects.items())}
    print(f"subjects in index: {len(subjects)}; distinct labels: {len(labels)}")

    # ---- choose representative subjects: evenly spaced ----
    ids = sorted(subjects)
    picks = [ids[round(i * (len(ids) - 1) / (N_SUBJECTS - 1))] for i in range(N_SUBJECTS)]
    print("subset subjects:", picks)

    downloaded = []
    meta_entry = next((e for e in entries if e["name"].endswith("/meta.csv")), None)
    todo = ([meta_entry] if meta_entry else []) + [e for s in picks for e in subjects[s]]
    total_bytes = 0
    for i, e in enumerate(todo):
        if e["name"].endswith("/"):
            continue
        data = extract(e)
        dest = os.path.join(out, "subset", e["name"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        h = hashlib.sha256(data).hexdigest()
        downloaded.append({"path": e["name"], "bytes": len(data), "sha256": h,
                           "crc32_ok": True})
        total_bytes += len(data)
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(todo)} files, {total_bytes/1e6:.0f} MB, {time.time()-t0:.0f}s")

    census = {
        "source_url": URL,
        "zenodo_record": 6802614,
        "full_zip_bytes": TOTAL_SIZE,
        "full_zip_md5_published": ZENODO_MD5,
        "index_entries": len(entries),
        "subjects_in_index": len(subjects),
        "distinct_labels": len(labels),
        "label_subject_counts": labels,
        "subset_subjects": picks,
        "subset_files": downloaded,
        "subset_total_bytes": total_bytes,
        "elapsed_s": round(time.time() - t0, 1),
    }
    cpath = os.path.join(out, "index-census.json")
    with open(cpath, "w") as f:
        json.dump(census, f, indent=1, sort_keys=True)
    print(f"wrote {cpath}: {len(downloaded)} files, {total_bytes:,} bytes")
    print("LABELS:", ", ".join(labels))


if __name__ == "__main__":
    sys.exit(main())
