#!/usr/bin/env python3
"""ANATOMICA Milestone 23: TA2 name-pass discipline assertions.

Shared by every clinical tranche checker (the tranche checker
passes its own check/ok function as `emit`). The assertions are
re-derived from the shipped data files, the vendored TA2 table
(data/sources/ta2-2.07/ta2-terms.json) and the accounting artifact
(data/ta2-name-pass.json) — never from the pass's own working
files:

  T1  a record with a non-null ta_name carries an integer ta_code
      present in the TA2 table whose Latin term (trimmed; the one
      served string with trailing whitespace is TA2 4366) equals
      ta_name exactly, cites "TA2" in sources["ta_name"], and
      carries no ta_name verify entry.
  T2  a record with a null ta_name carries no ta_code and exactly
      one ta_name verify entry, dated and naming TA2, stating
      whether it is ambiguous or not found.
  T3  the tranche's resolved / ambiguous / not-found counts and
      record sets reconcile with data/ta2-name-pass.json, including
      each resolved record's ta_code.
  T4  the tranche meta carries the TA2 source-register entry and a
      ta2_pass block whose counts match the file.
"""

import json
import os

PROJECT = "/home/hatch/workspace/anatomica-project"
PASS_DATE = "2026-11-06"


def _load(rel):
    with open(os.path.join(PROJECT, rel), encoding="utf-8") as f:
        return json.load(f)


def run(system, clinical_rel, emit):
    doc = _load(clinical_rel)
    terms = {t["ta_id"]: t for t in
             _load("data/sources/ta2-2.07/ta2-terms.json")["terms"]}
    artifact = _load("data/ta2-name-pass.json")
    records = doc["records"]
    rid = lambda r: r.get("id") or r.get("record_id")

    bad_resolved, bad_null = [], []
    resolved, ambiguous, not_found = {}, set(), set()
    for r in records:
        v_ta = [v for v in r.get("verify", [])
                if v.startswith("ta_name")]
        if r.get("ta_name") is not None:
            resolved[rid(r)] = r.get("ta_code")
            ok = (isinstance(r.get("ta_code"), int)
                  and r["ta_code"] in terms
                  and terms[r["ta_code"]]["latin"].strip()
                  == r["ta_name"]
                  and r.get("sources", {}).get("ta_name")
                  in (["TA2"], "TA2")
                  and not v_ta)
            if not ok:
                bad_resolved.append(rid(r))
        else:
            ok = ("ta_code" not in r and len(v_ta) == 1
                  and "TA2" in v_ta[0] and PASS_DATE in v_ta[0]
                  and ("ambiguous in TA2" in v_ta[0]
                       or "not found in TA2" in v_ta[0]))
            if not ok:
                bad_null.append(rid(r))
            elif "ambiguous in TA2" in v_ta[0]:
                ambiguous.add(rid(r))
            else:
                not_found.add(rid(r))
    emit(not bad_resolved,
         f"TA2 discipline [{system}]: all {len(resolved)} resolved "
         f"ta_name values equal the TA2 table entry for their "
         f"ta_code, cite TA2, and carry no ta_name verify flag"
         + (f" — FAILING: {bad_resolved}" if bad_resolved else ""))
    emit(not bad_null,
         f"TA2 discipline [{system}]: all {len(ambiguous) + len(not_found)} "
         f"null ta_name records carry exactly one dated TA2 verify "
         f"entry (ambiguous or not found) and no ta_code"
         + (f" — FAILING: {bad_null}" if bad_null else ""))

    a_sys = artifact["systems"][system]
    emit(a_sys["records"] == len(records)
         and a_sys["resolved"] == len(resolved)
         and a_sys["ambiguous"] == len(ambiguous)
         and a_sys["not_found"] == len(not_found),
         f"TA2 accounting [{system}]: counts reconcile with "
         f"data/ta2-name-pass.json ({len(records)} records: "
         f"{len(resolved)} resolved, {len(ambiguous)} ambiguous, "
         f"{len(not_found)} not found)")
    a_res = {e["record_id"]: e["ta_id"] for e in artifact["resolved"]
             if e["system"] == system}
    a_amb = {e["record_id"] for e in artifact["ambiguous"]
             if e["system"] == system}
    a_nf = {e["record_id"] for e in artifact["not_found"]
            if e["system"] == system}
    emit(a_res == resolved and a_amb == ambiguous
         and a_nf == not_found,
         f"TA2 accounting [{system}]: artifact record sets and "
         f"ta_code values match the tranche file exactly")
    meta = doc["meta"]
    register = meta.get("sources") or meta.get("sources_bibliography") or {}
    tp = meta.get("ta2_pass", {})
    emit("TA2" in register and tp.get("resolved") == len(resolved)
         and tp.get("ambiguous") == len(ambiguous)
         and tp.get("not_found") == len(not_found),
         f"TA2 provenance [{system}]: meta carries the TA2 source "
         f"register entry and a ta2_pass block matching the file")
