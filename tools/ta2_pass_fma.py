#!/usr/bin/env python3
"""Milestone 35: apply the TA2 name pass to the 286 FMA-sourced
nervous inventory records (Milestone 33 intake).

Sibling of tools/ta2_pass.py (Milestone 23, clinical tranches) and
the applying tool of record for the inventory pass. Decisions come
from tools/ta2_decide_fma.py (work/ta2/fma-decisions.json); this
tool writes only:

  * on each FMA record (source == "fma-5.1.0"): ta_name / ta_code /
    sources on resolution, or ta_name = null plus one dated
    ta_name verify entry on an ambiguous / not-found outcome.
    Every FMA field (verbatim name, FMAIDs, IS-A path, source,
    geometry, note) is carried through untouched; the 133
    BP3D-sourced records in the same file are not modified.
  * the inventory meta's ta2_pass block;
  * the fma_inventory section of data/ta2-name-pass.json (the
    Milestone 23 artifact's clinical accounting is untouched).

Idempotent: ta_name verify entries and prior pass fields are
stripped and rewritten from the decisions on every run.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
INV = os.path.join(PROJECT, "data/nervous/nervous-inventory.json")
DEC = os.path.join(PROJECT, "work/ta2/fma-decisions.json")
TA2 = os.path.join(PROJECT, "data/sources/ta2-2.07/ta2-terms.json")
ART = os.path.join(PROJECT, "data/ta2-name-pass.json")
DATE = "2026-11-06"
FLAG = ("ta_name: {kind} in TA2 (FIPAT 2nd ed., version 2.07) "
        f"consulted {DATE} — {{reason}}")


def is_flag(entry):
    return isinstance(entry, str) and entry.startswith("ta_name:")


def main():
    inv = json.load(open(INV))
    decisions = json.load(open(DEC))
    terms = {t["ta_id"]: t for t in json.load(open(TA2))["terms"]}
    fma_records = [r for r in inv["records"]
                   if r.get("source") == "fma-5.1.0"]
    assert len(fma_records) == 286, len(fma_records)
    assert {r["record_id"] for r in fma_records} == set(decisions)

    art_resolved, art_ambiguous, art_not_found = [], [], []
    anomalies = []
    out_records = []
    for r in inv["records"]:
        if r.get("source") != "fma-5.1.0":
            out_records.append(r)
            continue
        d = decisions[r["record_id"]]
        verify = [e for e in r.get("verify", []) if not is_flag(e)]
        new = {"record_id": r["record_id"], "name": r["name"]}
        if d["status"] == "resolved":
            t = terms[d["ta_id"]]
            latin = t["latin"]
            if latin != latin.strip():
                anomalies.append({
                    "ta_id": d["ta_id"], "served": latin,
                    "entered": latin.strip(),
                    "note": "TA2 serves this term's Latin with "
                            "trailing whitespace; entered trimmed, "
                            "as Milestone 23 entered 4366."})
                latin = latin.strip()
            new["ta_name"] = latin
            new["ta_code"] = d["ta_id"]
            note = d.get("note")
            if note is None and not d.get("reason", "").startswith(
                    "mechanical:"):
                note = d.get("reason")
            art_resolved.append({
                "record_id": r["record_id"], "name": r["name"],
                "ta_id": d["ta_id"], "ta_name": latin,
                "ta_english": t["english"], "basis": d["basis"],
                "note": note})
        else:
            new["ta_name"] = None
            kind = "ambiguous" if d["status"] == "ambiguous" \
                else "not found"
            verify = verify + [FLAG.format(kind=kind,
                                           reason=d["reason"])]
            entry = {"record_id": r["record_id"], "name": r["name"],
                     "reason": d["reason"]}
            if d["status"] == "ambiguous":
                entry["candidates"] = [
                    {"ta_id": tid, "latin": terms[tid]["latin"],
                     "english": terms[tid]["english"]}
                    for tid in d["candidates"]]
                art_ambiguous.append(entry)
            else:
                entry["probes"] = d["probes"]
                art_not_found.append(entry)
        for k in ("side", "representation", "class_concept_id",
                  "concept_ids", "subtree", "group_path", "source"):
            new[k] = r[k]
        if d["status"] == "resolved":
            new["sources"] = {"ta_name": ["TA2"]}
        for k in ("geometry",):
            new[k] = r[k]
        new["verify"] = verify
        new["note"] = r["note"]
        out_records.append(new)
    inv["records"] = out_records
    inv["meta"]["ta2_pass"] = {
        "milestone": "M35", "date": DATE,
        "scope": "the 286 FMA-sourced records of this inventory "
                 "(Milestone 33 intake); the 133 BP3D-sourced "
                 "records are untouched by this pass",
        "source": "Terminologia Anatomica, 2nd edition (TA2), "
                  "FIPAT 2019, TA version 2.07, as published in "
                  "TA2Viewer; extracted table: "
                  "data/sources/ta2-2.07/ta2-terms.json",
        "method": "tools/ta2_match_fma.py (candidates) -> "
                  "tools/ta2_decide_fma.py (curated decisions) -> "
                  "tools/ta2_pass_fma.py (this application)",
        "artifact": "data/ta2-name-pass.json (fma_inventory)",
        "resolved": len(art_resolved),
        "ambiguous": len(art_ambiguous),
        "not_found": len(art_not_found),
    }
    with open(INV, "w") as fh:
        json.dump(inv, fh, indent=1)

    art = json.load(open(ART))
    art["fma_inventory"] = {
        "file": "data/nervous/nervous-inventory.json",
        "milestone": "M35", "date": DATE,
        "records": 286,
        "resolved": art_resolved,
        "ambiguous": art_ambiguous,
        "not_found": art_not_found,
        "served_string_anomalies": anomalies,
    }
    art["meta"]["extension"] = (
        "Milestone 35 (2026-11-06) extended this artifact with "
        "the fma_inventory section: the TA2 name pass over the "
        "286 FMA-sourced nervous inventory records intaken at "
        "Milestone 33, under the same rule against the same "
        "table. The clinical accounting above is unchanged.")
    with open(ART, "w") as fh:
        json.dump(art, fh, indent=1)
        fh.write("\n")
    print(f"pass applied: {len(art_resolved)} resolved, "
          f"{len(art_ambiguous)} ambiguous, "
          f"{len(art_not_found)} not found; "
          f"{len(anomalies)} served-string anomalies")


if __name__ == "__main__":
    sys.exit(main())
