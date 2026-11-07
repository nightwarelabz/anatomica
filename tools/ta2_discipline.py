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

Milestone 35 extends the same discipline to the 286 FMA-sourced
nervous inventory records (data/nervous/nervous-inventory.json,
source == "fma-5.1.0") via run_fma_inventory: F1/F2 are T1/T2 over
that record set, F3 reconciles against the artifact's
fma_inventory section, F4 checks the inventory meta's ta2_pass
block, and F5 asserts the pass's scope — the 133 BP3D-sourced
records in the same file carry no ta_name/ta_code keys at all.

Milestone 36 extends it again to the FMA-sourced lymphatic (131)
and endocrine (14) inventory records via run_fma_inventory_multi,
the same F1–F5 parameterized by system, inventory file, artifact
section and milestone — no new assertion machinery.
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


def run_fma_inventory(emit):
    doc = _load("data/nervous/nervous-inventory.json")
    terms = {t["ta_id"]: t for t in
             _load("data/sources/ta2-2.07/ta2-terms.json")["terms"]}
    artifact = _load("data/ta2-name-pass.json")
    fma = [r for r in doc["records"] if r.get("source") == "fma-5.1.0"]
    bp3d = [r for r in doc["records"] if r.get("source") != "fma-5.1.0"]

    bad_resolved, bad_null = [], []
    resolved, ambiguous, not_found = {}, set(), set()
    for r in fma:
        v_ta = [v for v in r.get("verify", [])
                if v.startswith("ta_name")]
        if r.get("ta_name") is not None:
            resolved[r["record_id"]] = r.get("ta_code")
            ok = (isinstance(r.get("ta_code"), int)
                  and r["ta_code"] in terms
                  and terms[r["ta_code"]]["latin"].strip()
                  == r["ta_name"]
                  and r.get("sources", {}).get("ta_name") == ["TA2"]
                  and not v_ta)
            if not ok:
                bad_resolved.append(r["record_id"])
        else:
            ok = ("ta_code" not in r and len(v_ta) == 1
                  and "TA2" in v_ta[0] and PASS_DATE in v_ta[0]
                  and ("ambiguous in TA2" in v_ta[0]
                       or "not found in TA2" in v_ta[0]))
            if not ok:
                bad_null.append(r["record_id"])
            elif "ambiguous in TA2" in v_ta[0]:
                ambiguous.add(r["record_id"])
            else:
                not_found.add(r["record_id"])
    emit(not bad_resolved,
         f"TA2 discipline [fma-inventory]: all {len(resolved)} "
         f"resolved ta_name values equal the TA2 table entry for "
         f"their ta_code, cite TA2, and carry no ta_name verify flag"
         + (f" — FAILING: {bad_resolved}" if bad_resolved else ""))
    emit(not bad_null,
         f"TA2 discipline [fma-inventory]: all "
         f"{len(ambiguous) + len(not_found)} null ta_name records "
         f"carry exactly one dated TA2 verify entry (ambiguous or "
         f"not found) and no ta_code"
         + (f" — FAILING: {bad_null}" if bad_null else ""))

    sec = artifact.get("fma_inventory", {})
    a_res = {e["record_id"]: e["ta_id"] for e in sec.get("resolved", [])}
    a_amb = {e["record_id"] for e in sec.get("ambiguous", [])}
    a_nf = {e["record_id"] for e in sec.get("not_found", [])}
    emit(sec.get("records") == len(fma)
         and sec.get("file") == "data/nervous/nervous-inventory.json"
         and a_res == resolved and a_amb == ambiguous
         and a_nf == not_found,
         f"TA2 accounting [fma-inventory]: artifact fma_inventory "
         f"record sets and ta_code values match the inventory file "
         f"exactly ({len(fma)} records: {len(resolved)} resolved, "
         f"{len(ambiguous)} ambiguous, {len(not_found)} not found)")
    tp = doc["meta"].get("ta2_pass", {})
    emit(tp.get("milestone") == "M35"
         and tp.get("resolved") == len(resolved)
         and tp.get("ambiguous") == len(ambiguous)
         and tp.get("not_found") == len(not_found)
         and "TA2" in tp.get("source", ""),
         f"TA2 provenance [fma-inventory]: inventory meta carries "
         f"the M35 ta2_pass block matching the file")
    touched = [r["record_id"] for r in bp3d
               if "ta_name" in r or "ta_code" in r]
    emit(not touched,
         f"TA2 scope [fma-inventory]: the {len(bp3d)} BP3D-sourced "
         f"records in the same file carry no ta_name/ta_code — "
         f"the pass touched FMA records only"
         + (f" — FAILING: {touched}" if touched else ""))


def run_fma_inventory_multi(system, inventory_rel, section_key,
                            milestone, emit):
    """Milestone 36: run_fma_inventory generalized — the same
    F1–F5 assertions over another system's FMA-sourced inventory
    records, reconciling against the artifact section
    `section_key` and the inventory meta's ta2_pass block at
    `milestone`. No new assertion machinery."""
    doc = _load(inventory_rel)
    terms = {t["ta_id"]: t for t in
             _load("data/sources/ta2-2.07/ta2-terms.json")["terms"]}
    artifact = _load("data/ta2-name-pass.json")
    fma = [r for r in doc["records"] if r.get("source") == "fma-5.1.0"]
    bp3d = [r for r in doc["records"] if r.get("source") != "fma-5.1.0"]
    label = f"fma-inventory-{system}"

    bad_resolved, bad_null = [], []
    resolved, ambiguous, not_found = {}, set(), set()
    for r in fma:
        v_ta = [v for v in r.get("verify", [])
                if v.startswith("ta_name")]
        if r.get("ta_name") is not None:
            resolved[r["record_id"]] = r.get("ta_code")
            ok = (isinstance(r.get("ta_code"), int)
                  and r["ta_code"] in terms
                  and terms[r["ta_code"]]["latin"].strip()
                  == r["ta_name"]
                  and r.get("sources", {}).get("ta_name") == ["TA2"]
                  and not v_ta)
            if not ok:
                bad_resolved.append(r["record_id"])
        else:
            ok = ("ta_code" not in r and len(v_ta) == 1
                  and "TA2" in v_ta[0] and PASS_DATE in v_ta[0]
                  and ("ambiguous in TA2" in v_ta[0]
                       or "not found in TA2" in v_ta[0]))
            if not ok:
                bad_null.append(r["record_id"])
            elif "ambiguous in TA2" in v_ta[0]:
                ambiguous.add(r["record_id"])
            else:
                not_found.add(r["record_id"])
    emit(not bad_resolved,
         f"TA2 discipline [{label}]: all {len(resolved)} "
         f"resolved ta_name values equal the TA2 table entry for "
         f"their ta_code, cite TA2, and carry no ta_name verify flag"
         + (f" — FAILING: {bad_resolved}" if bad_resolved else ""))
    emit(not bad_null,
         f"TA2 discipline [{label}]: all "
         f"{len(ambiguous) + len(not_found)} null ta_name records "
         f"carry exactly one dated TA2 verify entry (ambiguous or "
         f"not found) and no ta_code"
         + (f" — FAILING: {bad_null}" if bad_null else ""))

    sec = artifact.get(section_key, {})
    a_res = {e["record_id"]: e["ta_id"] for e in sec.get("resolved", [])}
    a_amb = {e["record_id"] for e in sec.get("ambiguous", [])}
    a_nf = {e["record_id"] for e in sec.get("not_found", [])}
    emit(sec.get("records") == len(fma)
         and sec.get("file") == inventory_rel
         and a_res == resolved and a_amb == ambiguous
         and a_nf == not_found,
         f"TA2 accounting [{label}]: artifact {section_key} "
         f"record sets and ta_code values match the inventory file "
         f"exactly ({len(fma)} records: {len(resolved)} resolved, "
         f"{len(ambiguous)} ambiguous, {len(not_found)} not found)")
    tp = doc["meta"].get("ta2_pass", {})
    emit(tp.get("milestone") == milestone
         and tp.get("resolved") == len(resolved)
         and tp.get("ambiguous") == len(ambiguous)
         and tp.get("not_found") == len(not_found)
         and "TA2" in tp.get("source", ""),
         f"TA2 provenance [{label}]: inventory meta carries "
         f"the {milestone} ta2_pass block matching the file")
    touched = [r["record_id"] for r in bp3d
               if "ta_name" in r or "ta_code" in r]
    emit(not touched,
         f"TA2 scope [{label}]: the {len(bp3d)} BP3D-sourced "
         f"records in the same file carry no ta_name/ta_code — "
         f"the pass touched FMA records only"
         + (f" — FAILING: {touched}" if touched else ""))
