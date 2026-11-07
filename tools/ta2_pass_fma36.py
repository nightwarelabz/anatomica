#!/usr/bin/env python3
"""Milestone 36: apply the TA2 name pass to the FMA-sourced
lymphatic (131) and endocrine (14) inventory records (Milestone
36 intake). Sibling of tools/ta2_pass_fma.py (Milestone 35),
system-parameterized: `ta2_pass_fma36.py lymphatic|endocrine`.

Decisions come from tools/ta2_decide_fma36.py
(work/ta2/fma-<system>-decisions.json); this tool writes only:

  * on each FMA record (source == "fma-5.1.0"): ta_name /
    ta_code / sources on resolution, or ta_name = null plus one
    dated ta_name verify entry on an ambiguous / not-found
    outcome. Every FMA field (verbatim name, FMAIDs, IS-A path,
    source, geometry, note) is carried through untouched; the
    BP3D-sourced records in the same file are not modified.
  * the inventory meta's ta2_pass block (milestone M36);
  * the fma_inventory_<system> section of
    data/ta2-name-pass.json (the Milestone 23 clinical
    accounting and the Milestone 35 fma_inventory section are
    untouched; the extension is recorded under the artifact
    meta's extension_36 key).

Idempotent: ta_name verify entries and prior pass fields are
stripped and rewritten from the decisions on every run.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
TA2 = os.path.join(PROJECT, "data/sources/ta2-2.07/ta2-terms.json")
ART = os.path.join(PROJECT, "data/ta2-name-pass.json")
DATE = "2026-11-06"
FLAG = ("ta_name: {kind} in TA2 (FIPAT 2nd ed., version 2.07) "
        f"consulted {DATE} — {{reason}}")
SYSTEMS = {
    "lymphatic": {"records": 131, "bp3d": 4},
    "endocrine": {"records": 14, "bp3d": 3},
}
EXTENSION_36 = (
    "Milestone 36 (2026-11-06) extended this artifact with the "
    "fma_inventory_lymphatic and fma_inventory_endocrine "
    "sections: the TA2 name pass over the 145 FMA-sourced "
    "lymphatic and endocrine inventory records intaken at "
    "Milestone 36, under the same rule against the same table. "
    "The clinical accounting and the Milestone 35 fma_inventory "
    "section are unchanged.")


def is_flag(entry):
    return isinstance(entry, str) and entry.startswith("ta_name:")


def main():
    system = sys.argv[1]
    assert system in SYSTEMS, system
    inv_path = os.path.join(PROJECT, "data", system,
                            f"{system}-inventory.json")
    dec_path = os.path.join(PROJECT, "work/ta2",
                            f"fma-{system}-decisions.json")
    section = f"fma_inventory_{system}"
    inv = json.load(open(inv_path))
    decisions = json.load(open(dec_path))
    terms = {t["ta_id"]: t for t in json.load(open(TA2))["terms"]}
    fma_records = [r for r in inv["records"]
                   if r.get("source") == "fma-5.1.0"]
    assert len(fma_records) == SYSTEMS[system]["records"], \
        len(fma_records)
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
        "milestone": "M36", "date": DATE,
        "scope": f"the {SYSTEMS[system]['records']} FMA-sourced "
                 f"records of this inventory (Milestone 36 "
                 f"intake); the {SYSTEMS[system]['bp3d']} "
                 f"BP3D-sourced records are untouched by this pass",
        "source": "Terminologia Anatomica, 2nd edition (TA2), "
                  "FIPAT 2019, TA version 2.07, as published in "
                  "TA2Viewer; extracted table: "
                  "data/sources/ta2-2.07/ta2-terms.json",
        "method": "tools/ta2_match_fma36.py (candidates) -> "
                  "tools/ta2_decide_fma36.py (curated decisions) "
                  "-> tools/ta2_pass_fma36.py (this application)",
        "artifact": f"data/ta2-name-pass.json ({section})",
        "resolved": len(art_resolved),
        "ambiguous": len(art_ambiguous),
        "not_found": len(art_not_found),
    }
    with open(inv_path, "w") as fh:
        json.dump(inv, fh, indent=1)

    art = json.load(open(ART))
    art[section] = {
        "file": f"data/{system}/{system}-inventory.json",
        "milestone": "M36", "date": DATE,
        "records": SYSTEMS[system]["records"],
        "resolved": art_resolved,
        "ambiguous": art_ambiguous,
        "not_found": art_not_found,
        "served_string_anomalies": anomalies,
    }
    art["meta"]["extension_36"] = EXTENSION_36
    with open(ART, "w") as fh:
        json.dump(art, fh, indent=1)
        fh.write("\n")
    print(f"pass applied [{system}]: {len(art_resolved)} resolved, "
          f"{len(art_ambiguous)} ambiguous, "
          f"{len(art_not_found)} not found; "
          f"{len(anomalies)} served-string anomalies")


if __name__ == "__main__":
    sys.exit(main())
