#!/usr/bin/env python3
"""ANATOMICA Milestone 23: apply the TA2 name pass.

Applies work/ta2/decisions.json (curated by tools/ta2_decide.py
against data/sources/ta2-2.07/ta2-terms.json) to the ten clinical
tranche files:

  resolved   ta_name := the TA2 Latin term exactly as served
             (one served string, TA2 4366 'carotis communis ',
             carries a trailing space; the entered value is trimmed
             and the anomaly is recorded in the artifact), ta_code
             inserted after ta_name, sources gains "ta_name":
             ["TA2"], and the record's old ta_name verify entry is
             removed.
  ambiguous  ta_name stays null; the ta_name verify entry is
  not_found  replaced by a dated entry stating the outcome and the
             specific reason from the decision record.

Every tranche meta gains a "TA2" entry in its source register
(sources / sources_bibliography), a refreshed "ta_name_status",
and a "ta2_pass" summary block. The full accounting is written to
data/ta2-name-pass.json. The pass is idempotent: re-running it on
already-passed files reproduces the same bytes.

Exit non-zero if decisions and tranche files disagree about the
record set, or if any decision references a TA2 id not in the
source table.
"""

import json
import os
import sys
from collections import Counter, OrderedDict

PROJECT = "/home/hatch/workspace/anatomica-project"
DECISIONS = os.path.join(PROJECT, "work/ta2/decisions.json")
TA2 = os.path.join(PROJECT, "data/sources/ta2-2.07/ta2-terms.json")
ARTIFACT = os.path.join(PROJECT, "data/ta2-name-pass.json")
DATE = "2026-11-06"
SOURCE_LABEL = ("Terminologia Anatomica, 2nd edition (TA2), FIPAT "
                "2019, TA version 2.07, as published in TA2Viewer "
                "(ta2viewer.openanatomy.org); extracted table: "
                "data/sources/ta2-2.07/ta2-terms.json")

TRANCHES = OrderedDict([
    ("cardiovascular", "data/cardiovascular/cardiovascular.json"),
    ("digestive", "data/digestive/digestive.json"),
    ("endocrine", "data/endocrine/endocrine.json"),
    ("integumentary", "data/integumentary/integumentary.json"),
    ("lymphatic", "data/lymphatic/lymphatic.json"),
    ("muscular", "data/muscular/muscles.json"),
    ("nervous", "data/nervous/nervous.json"),
    ("reproductive", "data/reproductive/reproductive.json"),
    ("respiratory", "data/respiratory/respiratory.json"),
    ("urinary", "data/urinary/urinary.json"),
])


def rid_of(r):
    return r.get("id") or r.get("record_id")


def main():
    decisions = json.load(open(DECISIONS))
    ta2doc = json.load(open(TA2))
    terms = {t["ta_id"]: t for t in ta2doc["terms"]}

    artifact = {
        "meta": {
            "milestone": "M23",
            "date": DATE,
            "source": SOURCE_LABEL,
            "source_terms_sha256_note": "see data/sources/ta2-2.07/"
                                        "SOURCE.md",
            "method": "tools/ta2_match.py (candidates) -> "
                      "tools/ta2_decide.py (curated decisions) -> "
                      "tools/ta2_pass.py (this application)",
            "rule": "a record resolves only when TA2's own naming "
                    "apparatus (preferred term, listed synonym, or "
                    "listed related term) names a term for a "
                    "structure identical to the record's, with no "
                    "competing TA2 term; otherwise ambiguous "
                    "(candidates listed) or not found (probe "
                    "evidence in the decision record).",
        },
        "systems": {},
        "resolved": [],
        "ambiguous": [],
        "not_found": [],
        "served_string_anomalies": [],
    }

    seen_keys = set()
    for system, rel in TRANCHES.items():
        path = os.path.join(PROJECT, rel)
        doc = json.load(open(path))
        counts = Counter()
        for r in doc["records"]:
            rid = rid_of(r)
            key = f"{system}:{rid}"
            seen_keys.add(key)
            d = decisions.get(key)
            assert d is not None, f"no decision for {key}"
            # strip any existing ta_name verify entries (old debt
            # wording or a previous pass) before writing the new state
            r["verify"] = [v for v in r.get("verify", [])
                           if not v.startswith("ta_name")]
            if d["decision"] == "resolved":
                tid = d["ta_id"]
                assert tid in terms, f"{key}: TA2 id {tid} not in table"
                served = terms[tid]["latin"]
                entered = served.strip()
                if served != entered:
                    artifact["served_string_anomalies"].append({
                        "ta_id": tid, "served": served,
                        "entered": entered,
                        "note": "served string carries trailing "
                                "whitespace; entered value trimmed"})
                # rebuild record with ta_code right after ta_name
                new_r = {}
                for k, v in r.items():
                    if k == "ta_code":
                        continue
                    new_r[k] = v
                    if k == "ta_name":
                        new_r["ta_code"] = tid
                new_r["ta_name"] = entered
                r.clear()
                r.update(new_r)
                srcs = r.setdefault("sources", {})
                # the muscular tranche's checker treats sources
                # values as scalar keys; the other tranches use
                # lists — write each tranche's own convention
                srcs["ta_name"] = "TA2" if system == "muscular" \
                    else ["TA2"]
                counts["resolved"] += 1
                artifact["resolved"].append({
                    "system": system, "record_id": rid,
                    "name": r["name"], "ta_id": tid,
                    "ta_name": entered,
                    "ta_english": terms[tid]["english"],
                    "basis": d.get("basis"),
                    "note": d.get("note")})
            else:
                r["ta_name"] = None
                if "ta_code" in r:
                    del r["ta_code"]
                label = "ambiguous" if d["decision"] == "ambiguous" \
                    else "not found"
                r["verify"].append(
                    f"ta_name: {label} in TA2 (FIPAT 2nd ed., "
                    f"version 2.07) consulted {DATE} — {d['reason']}")
                counts[d["decision"]] += 1
                entry = {"system": system, "record_id": rid,
                         "name": r["name"], "reason": d["reason"]}
                if d["decision"] == "ambiguous":
                    entry["candidates"] = [
                        {"ta_id": cid, "latin": terms[cid]["latin"],
                         "english": terms[cid]["english"]}
                        for cid in d["candidates"]]
                    artifact["ambiguous"].append(entry)
                else:
                    entry["probes"] = d.get("probes", [])
                    artifact["not_found"].append(entry)
        total = sum(counts.values())
        artifact["systems"][system] = {
            "file": rel, "records": total,
            "resolved": counts["resolved"],
            "ambiguous": counts["ambiguous"],
            "not_found": counts["not_found"]}
        meta = doc["meta"]
        for reg_key in ("sources", "sources_bibliography"):
            if isinstance(meta.get(reg_key), dict):
                meta[reg_key]["TA2"] = SOURCE_LABEL
        meta["ta_name_status"] = (
            f"TA2 name pass applied {DATE} (Milestone 23): "
            f"{counts['resolved']} of {total} records carry a TA2 "
            f"Latin name with its TA2 id in ta_code, cited to source "
            f"register entry TA2; {counts['ambiguous']} ambiguous "
            f"and {counts['not_found']} not found in TA2 2.07, each "
            f"verify-flagged with its reason. Full accounting: "
            f"data/ta2-name-pass.json.")
        meta["ta2_pass"] = {
            "milestone": "M23", "date": DATE, "source": SOURCE_LABEL,
            "records": total, "resolved": counts["resolved"],
            "ambiguous": counts["ambiguous"],
            "not_found": counts["not_found"],
            "artifact": "data/ta2-name-pass.json"}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print(f"{system}: {total} records — {counts['resolved']} "
              f"resolved, {counts['ambiguous']} ambiguous, "
              f"{counts['not_found']} not found")
    missing = set(decisions) - seen_keys
    assert not missing, f"decisions without records: {missing}"
    assert len(seen_keys) == 361, f"record set {len(seen_keys)} != 361"
    with open(ARTIFACT, "w", encoding="utf-8") as f:
        json.dump(artifact, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"TOTAL: {len(artifact['resolved'])} resolved, "
          f"{len(artifact['ambiguous'])} ambiguous, "
          f"{len(artifact['not_found'])} not found -> {ARTIFACT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
