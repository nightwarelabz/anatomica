#!/usr/bin/env python3
"""Milestone 38: apply the TA2 name pass to the FMA-sourced
integumentary records (53, Milestone 38 intake) and extend it
over the reproductive inventory's Milestone 38 male records
(76), whose file then carries the pass over all 133 FMA
records. Sibling of tools/ta2_pass_fma37.py (Milestone 37),
system-parameterized: `ta2_pass_fma38.py integumentary|
reproductive`. Field positions follow the sibling:
reproductive records carry sex_line after subtree;
integumentary records carry line in the same position.

Decisions: integumentary from tools/ta2_decide_fma38.py
(work/ta2/fma38-integumentary-decisions.json); reproductive
from the Milestone 37 decisions
(work/ta2/fma-reproductive-decisions.json) merged with the
Milestone 38 decisions
(work/ta2/fma38-reproductive-decisions.json) — the merge is
asserted disjoint and complete over the file's 133 FMA
records, and the 57 Milestone 37 records' outcomes are
rewritten from their unchanged decisions, so they come out
byte-identical. This tool writes only:

  * on each FMA record (source == "fma-5.1.0"): ta_name /
    ta_code / sources on resolution, or ta_name = null plus one
    dated ta_name verify entry on an ambiguous / not-found
    outcome. Every FMA field (verbatim name, FMAIDs, IS-A path,
    source, geometry, note) is carried through untouched; the
    BP3D-sourced records in the same file are not modified.
  * the inventory meta's ta2_pass block (milestone M38);
  * the fma_inventory_<system> section of
    data/ta2-name-pass.json (the Milestone 23 clinical
    accounting and the Milestone 35/36/37 sections are
    untouched; the reproductive section is rewritten over all
    133 records with the Milestone 38 subset recorded in its
    extension_38 block; the extension is recorded under the
    artifact meta's extension_38 key).

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
    "integumentary": {"records": 53, "bp3d": 6},
    "reproductive": {"records": 133, "bp3d": 13},
}
DECISION_FILES = {
    "integumentary": ["fma38-integumentary-decisions.json"],
    "reproductive": ["fma-reproductive-decisions.json",
                     "fma38-reproductive-decisions.json"],
}
M38_FILES = {"integumentary": "fma38-integumentary-decisions.json",
             "reproductive": "fma38-reproductive-decisions.json"}
EXTENSION_38 = (
    "Milestone 38 (2026-11-06) extended this artifact with the "
    "fma_inventory_integumentary section (the TA2 name pass "
    "over the 53 FMA-sourced integumentary inventory records "
    "intaken at Milestone 38) and rewrote the "
    "fma_inventory_reproductive section over all 133 FMA "
    "records of that inventory (the 57 Milestone 37 records, "
    "outcomes unchanged, plus the 76 Milestone 38 male "
    "records), under the same rule against the same table. "
    "The clinical accounting and the Milestone 35/36/37 "
    "sections are unchanged.")


def is_flag(entry):
    return isinstance(entry, str) and entry.startswith("ta_name:")


def main():
    system = sys.argv[1]
    assert system in SYSTEMS, system
    inv_path = os.path.join(PROJECT, "data", system,
                            f"{system}-inventory.json")
    section = f"fma_inventory_{system}"
    inv = json.load(open(inv_path))
    decisions = {}
    for fn in DECISION_FILES[system]:
        part = json.load(open(os.path.join(PROJECT, "work/ta2",
                                           fn)))
        assert not (set(part) & set(decisions)), fn
        decisions.update(part)
    m38_ids = set(json.load(open(os.path.join(
        PROJECT, "work/ta2", M38_FILES[system]))))
    terms = {t["ta_id"]: t for t in json.load(open(TA2))["terms"]}
    fma_records = [r for r in inv["records"]
                   if r.get("source") == "fma-5.1.0"]
    assert len(fma_records) == SYSTEMS[system]["records"], \
        len(fma_records)
    assert {r["record_id"] for r in fma_records} == set(decisions)

    art_resolved, art_ambiguous, art_not_found = [], [], []
    ext_resolved, ext_ambiguous, ext_not_found = [], [], []
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
            entry = {
                "record_id": r["record_id"], "name": r["name"],
                "ta_id": d["ta_id"], "ta_name": latin,
                "ta_english": t["english"], "basis": d["basis"],
                "note": note}
            art_resolved.append(entry)
            if r["record_id"] in m38_ids:
                ext_resolved.append(entry)
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
                if r["record_id"] in m38_ids:
                    ext_ambiguous.append(entry)
            else:
                entry["probes"] = d["probes"]
                art_not_found.append(entry)
                if r["record_id"] in m38_ids:
                    ext_not_found.append(entry)
        for k in ("side", "representation", "class_concept_id",
                  "concept_ids", "subtree"):
            new[k] = r[k]
        if "sex_line" in r:
            new["sex_line"] = r["sex_line"]
        if "line" in r:
            new["line"] = r["line"]
        for k in ("group_path", "source"):
            new[k] = r[k]
        if d["status"] == "resolved":
            new["sources"] = {"ta_name": ["TA2"]}
        for k in ("geometry",):
            new[k] = r[k]
        new["verify"] = verify
        new["note"] = r["note"]
        out_records.append(new)
    inv["records"] = out_records
    if system == "integumentary":
        scope = ("the 53 FMA-sourced records of this inventory "
                 "(Milestone 38 intake); the 6 BP3D-sourced "
                 "records are untouched by this pass")
        method = ("tools/ta2_match_fma38.py (candidates) -> "
                  "tools/ta2_decide_fma38.py (curated decisions) "
                  "-> tools/ta2_pass_fma38.py (this application)")
    else:
        scope = ("all 133 FMA-sourced records of this inventory "
                 "(57 Milestone 37 female intake + 76 Milestone "
                 "38 male intake); the 13 BP3D-sourced records "
                 "are untouched by this pass")
        method = ("Milestone 37 records: "
                  "tools/ta2_match_fma37.py -> "
                  "tools/ta2_decide_fma37.py; Milestone 38 "
                  "records: tools/ta2_match_fma38.py -> "
                  "tools/ta2_decide_fma38.py; applied by "
                  "tools/ta2_pass_fma38.py (this application)")
    inv["meta"]["ta2_pass"] = {
        "milestone": "M38", "date": DATE,
        "scope": scope,
        "source": "Terminologia Anatomica, 2nd edition (TA2), "
                  "FIPAT 2019, TA version 2.07, as published in "
                  "TA2Viewer; extracted table: "
                  "data/sources/ta2-2.07/ta2-terms.json",
        "method": method,
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
        "milestone": "M38" if system == "integumentary"
                     else "M37+M38",
        "date": DATE,
        "records": SYSTEMS[system]["records"],
        "resolved": art_resolved,
        "ambiguous": art_ambiguous,
        "not_found": art_not_found,
        "served_string_anomalies": anomalies,
    }
    if system == "reproductive":
        art[section]["extension_38"] = {
            "milestone": "M38", "date": DATE,
            "records_added": len(m38_ids),
            "resolved": ext_resolved,
            "ambiguous": ext_ambiguous,
            "not_found": ext_not_found,
        }
    art["meta"]["extension_38"] = EXTENSION_38
    with open(ART, "w") as fh:
        json.dump(art, fh, indent=1)
        fh.write("\n")
    print(f"pass applied [{system}]: {len(art_resolved)} resolved, "
          f"{len(art_ambiguous)} ambiguous, "
          f"{len(art_not_found)} not found; "
          f"{len(anomalies)} served-string anomalies")


if __name__ == "__main__":
    sys.exit(main())
