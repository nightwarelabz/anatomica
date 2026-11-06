#!/usr/bin/env python3
"""ANATOMICA Milestone 23: TA2 source-table extraction.

Extracts the official Terminologia Anatomica 2 (TA2) term table from
the saved TA2Viewer web bundle (work/ta2/main.js). TA2Viewer
(ta2viewer.openanatomy.org) is the official digital version of TA2:
a joint FIPAT / Open Anatomy Project publication that "incorporates
the official digital version of the second edition of Terminologia
Anatomica (TA2) as published by FIPAT". The viewer ships the complete
terminology as one JSON payload embedded in its main JS bundle
(JSON.parse('...')); this script unescapes that JS string literal
(JS \\xHH / \\uHHHH escapes included) and parses the JSON.

Input:  work/ta2/main.js  (bundle as downloaded; SHA-256 pinned in
        data/sources/ta2-2.07/SOURCE.md — the bundle itself is NOT
        vendored into data/sources: it is third-party application
        code; only the terminology terms are extracted)
Output: data/sources/ta2-2.07/ta2-terms.json

Integrity gates (all must hold or the script exits non-zero):
  - the bundle's own metadata payload reads vocab "2.07"
    (TA version 2.07, the current errata version);
  - exactly 7,112 term objects (the published TA2 term count);
  - term ids span 1..7113 with exactly one unassigned id.
    (Observed in the served 2.07 data: 2259 is the unassigned id and
    2590 IS assigned, to "vinculum breve tendinis" — this differs
    from the secondary-source claim that 2590 is unassigned; the
    discrepancy is recorded in SOURCE.md, not corrected away.)
"""

import hashlib
import json
import os
import re
import sys

PROJECT = "/home/hatch/workspace/anatomica-project"
BUNDLE = os.path.join(PROJECT, "work/ta2/main.js")
OUT = os.path.join(PROJECT, "data/sources/ta2-2.07/ta2-terms.json")


def js_unescape_payloads(text):
    """Yield the string contents of every JSON.parse('...') call."""
    payloads = []
    for m in re.finditer(r"JSON\.parse\('", text):
        i = m.end()
        out = []
        while i < len(text):
            c = text[i]
            if c == "\\":
                nxt = text[i + 1] if i + 1 < len(text) else ""
                if nxt == "x":
                    out.append(chr(int(text[i + 2:i + 4], 16)))
                    i += 4
                elif nxt == "u":
                    out.append(chr(int(text[i + 2:i + 6], 16)))
                    i += 6
                elif nxt == "n":
                    out.append("\n"); i += 2
                elif nxt == "t":
                    out.append("\t"); i += 2
                elif nxt == "r":
                    out.append("\r"); i += 2
                elif nxt == "0":
                    out.append("\0"); i += 2
                elif nxt in ("\\", "'", '"', "/"):
                    out.append(nxt); i += 2
                else:
                    out.append("\\"); out.append(nxt); i += 2
            elif c == "'":
                payloads.append("".join(out))
                break
            else:
                out.append(c)
                i += 1
    return payloads


def main():
    raw = open(BUNDLE, "rb").read()
    bundle_sha = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8", errors="replace")
    meta = None
    terms = None
    for payload in js_unescape_payloads(text):
        try:
            obj = json.loads(payload)
        except Exception:
            continue
        if isinstance(obj, dict) and obj.get("vocab"):
            meta = obj
        if isinstance(obj, list) and obj and isinstance(obj[0], dict) \
                and "term" in obj[0]:
            terms = obj
    assert meta is not None, "viewer metadata payload not found"
    assert terms is not None, "term payload not found"
    assert meta.get("vocab") == "2.07", f"unexpected TA version {meta}"
    assert len(terms) == 7112, f"term count {len(terms)} != 7112"
    ids = sorted(t["id"] for t in terms)
    assert ids[0] == 1 and ids[-1] == 7113, "id span wrong"
    missing = sorted(set(range(1, 7114)) - set(ids))
    assert len(missing) == 1, f"unassigned ids {missing}"

    table = []
    for t in terms:
        term = t.get("term") or {}
        syn = t.get("synonyms") or {}
        table.append({
            "ta_id": t["id"],
            "latin": term.get("la"),
            "english": term.get("en"),
            "latin_synonyms": syn.get("la", []),
            "english_synonyms": syn.get("en", []),
            "related_terms": t.get("related_terms", []),
            "level": t.get("level"),
            "parent": t.get("parent"),
        })
    doc = {
        "meta": {
            "source": "Terminologia Anatomica, 2nd edition (TA2), "
                      "FIPAT 2019, as published in TA2Viewer",
            "ta_version": "2.07",
            "viewer_metadata_payload": meta,
            "extraction": "tools/ta2_extract.py from the TA2Viewer "
                          "main JS bundle (work/ta2/main.js)",
            "bundle_sha256": bundle_sha,
            "term_count": len(table),
            "unassigned_ids_observed": missing,
            "license": "Publication CC BY-ND 4.0; individual terms "
                       "in the public domain (FIPAT's own statement, "
                       "see SOURCE.md in this directory)",
        },
        "terms": table,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"OK: {len(table)} terms, ids 1..7113 (unassigned: {missing}), "
          f"TA version {meta['vocab']} -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
