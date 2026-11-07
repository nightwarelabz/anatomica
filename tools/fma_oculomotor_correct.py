#!/usr/bin/env python3
"""ANATOMICA Milestone 38: oculomotor name-provenance
correction + the whole-intake artifact sweep.

Milestone 37 §5 corrected the six somatic plexus records and
named the adjacent observation it did NOT correct: the two
oculomotor records (nerve.left-oculomotor-nerve,
nerve.right-oculomotor-nerve) carry the same Milestone 33
naive-parser artifact — class_concept_id null and one null
group_path entry — although their IS-A parent FMA50864
'Oculomotor nerve' carries a preferred name under the
depth-aware parse. Milestone 38 is the ruling: correct them
with the identical pattern (tools/fma_plexus_correct.py is
the template), and sweep the WHOLE FMA intake for any other
record carrying the artifact.

Correction applied to exactly the two oculomotor records:

  * class_concept_id: null -> FMA50864, derived from the
    sided classes' IS-A parentage in the OWL;
  * group_path: the null entry -> 'Oculomotor nerve'. The
    corrected path is re-derived by BFS over the depth-aware
    parse and asserted equal to the recorded path with the
    null slot filled — no other path element changes.

Record identity is re-verified after the correction: names,
concept FMAIDs, TA2 names/codes (6187 nervus oculomotorius,
against the data/ta2-name-pass.json fma_inventory section)
and every other field are asserted unchanged against the
pre-Milestone 38 snapshot (work/m38/pre-inventories/).

The sweep is complete by construction: it enumerates, over
the pre-Milestone 38 snapshots of ALL eleven inventories,
every FMA-sourced record whose class_concept_id is null or
whose group_path carries a null entry, and re-derives each
hit against the OWL under both parses (depth-aware regex
and ElementTree XML). The enumeration finds exactly the two
oculomotor records; every other FMA-sourced record of the
555-record intake (Milestones 33/36/37) is null-free, so
after this correction the artifact survives nowhere in the
intake. The full evidence is written to the
oculomotor_correction section of data/fma-intake-38.json.

Idempotent: an already-corrected inventory is detected and
reported, with the artifact section refreshed.

Usage: fma_oculomotor_correct.py
Stdlib only.
"""
import glob as globmod
import html
import json
import os
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fma_uri_repro_map import parse_owl, group_path  # noqa: E402

OWL = os.path.join(ROOT, "work", "fma", "fma.owl")
NERV_INV = os.path.join(ROOT, "data", "nervous",
                        "nervous-inventory.json")
PRE_DIR = os.path.join(ROOT, "work", "m38", "pre-inventories")
ART_PATH = os.path.join(ROOT, "data", "fma-intake-38.json")
TA2_ART = os.path.join(ROOT, "data", "ta2-name-pass.json")
SOURCE_TAG = "fma-5.1.0"
DATE = "2026-11-06"

CLASS_FID = "50864"
CLASS_NAME = "Oculomotor nerve"
RECORDS = ["nerve.left-oculomotor-nerve",
           "nerve.right-oculomotor-nerve"]

CORRECTION_NOTE = (
    "Correction (2026-11-06, Milestone 38): the two "
    "oculomotor records carried the Milestone 33 naive-parser "
    "artifact named at Milestone 37 §5 — class_concept_id "
    "null and one null group_path entry at the un-sided class "
    "position — although the parent class FMA50864 "
    "'Oculomotor nerve' carries a fma:preferred_name. Under "
    "the depth-aware parse, and independently under an "
    "ElementTree XML parse, FMA50864 carries "
    "fma:preferred_name identical to its rdfs:label. The "
    "records' class_concept_id and group_path null slot are "
    "corrected to the derived values, exactly as the six "
    "plexus records were corrected at Milestone 37. A sweep "
    "of all 555 FMA-sourced records (every inventory, frozen "
    "pre-Milestone 38 snapshots) finds these two records are "
    "the only remaining carriers of the artifact; after this "
    "correction it survives nowhere in the intake. Record "
    "names, concept FMAIDs, TA2 names and codes (6187), and "
    "all other fields are unchanged and re-verified.")


def parse_owl_xml(path):
    """ElementTree iterparse: {fid: (preferred_name, label,
    parents)} — names entity-decoded by the XML parser."""
    ns = {"owl": "http://www.w3.org/2002/07/owl#",
          "fma": "http://purl.org/sig/ont/fma/",
          "rdfs": "http://www.w3.org/2000/01/rdf-schema#"}
    names = {}
    for _ev, el in ET.iterparse(path, events=("end",)):
        if el.tag == f"{{{ns['owl']}}}Class":
            about = el.get(
                "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about")
            pn = el.find("fma:preferred_name", ns)
            lb = el.find("rdfs:label", ns)
            parents = [x.get(
                "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
                "resource").rsplit("fma", 1)[-1]
                for x in el.findall("rdfs:subClassOf", ns)
                if x.get("{http://www.w3.org/1999/02/22-rdf-syntax"
                         "-ns#}resource")]
            if about:
                names[about.rsplit("fma", 1)[-1]] = (
                    pn.text if pn is not None else None,
                    lb.text if lb is not None else None,
                    parents)
            el.clear()
    return names


def sweep_snapshots():
    """Enumerate the artifact over the frozen pre-M38
    snapshots of every inventory: [(system, record_id,
    null_class_id, null_path_slots)]."""
    hits = []
    total = 0
    for path in sorted(globmod.glob(
            os.path.join(PRE_DIR, "*-inventory.json"))):
        system = os.path.basename(path)[:-len("-inventory.json")]
        doc = json.load(open(path))
        for r in doc.get("records", []):
            if r.get("source") != SOURCE_TAG:
                continue
            total += 1
            slots = [i for i, x in enumerate(r.get("group_path")
                                             or []) if x is None]
            if r.get("class_concept_id") is None or slots:
                hits.append({
                    "system": system, "record_id": r["record_id"],
                    "class_concept_id_null":
                        r.get("class_concept_id") is None,
                    "null_group_path_slots": slots})
    return hits, total


def main():
    classes = parse_owl(OWL)
    owl_xml = parse_owl_xml(OWL)

    # --- the sweep, over the frozen before-state ------------
    hits, total = sweep_snapshots()
    assert total == 555, total
    assert [h["record_id"] for h in hits] == RECORDS, hits
    print(f"sweep: {total} FMA-sourced records enumerated over "
          f"the pre-M38 snapshots of all inventories; artifact "
          f"carriers: {[h['record_id'] for h in hits]}")

    # --- name-field evidence for FMA50864 and the two sided
    # classes, both parses -----------------------------------
    inv_pre = json.load(open(os.path.join(
        PRE_DIR, "nervous-inventory.json")))
    rec_pre = {r["record_id"]: r for r in inv_pre["records"]}
    evidence = []
    rx = classes[CLASS_FID]
    xm = owl_xml[CLASS_FID]
    assert html.unescape(rx["name"] or "") == xm[0] \
        and html.unescape(rx["label"] or "") == xm[1]
    assert xm[0] == CLASS_NAME and xm[1] == CLASS_NAME
    evidence.append({
        "fmaid": f"FMA{CLASS_FID}", "role": "un-sided class",
        "preferred_name": xm[0], "label": xm[1],
        "parses_agree": True})
    sided_of = {}
    for rid in RECORDS:
        side = "left" if ".left-" in rid else "right"
        child = rec_pre[rid]["concept_ids"][0][3:]
        cx = owl_xml[child]
        assert html.unescape(classes[child]["name"] or "") \
            == cx[0], child
        assert cx[0].lower() == f"{side} {CLASS_NAME}".lower(), \
            child
        assert CLASS_FID in cx[2], (child, cx[2])
        assert CLASS_FID in classes[child]["parents"], child
        evidence.append({
            "fmaid": f"FMA{child}", "role": f"sided class ({side})",
            "preferred_name": cx[0], "label": cx[1],
            "is_a_parent": f"FMA{CLASS_FID}", "parses_agree": True})
        sided_of[rid] = child
    print(f"name fields re-derived: FMA{CLASS_FID} carries "
          f"fma:preferred_name '{CLASS_NAME}' (both parses "
          f"agree) — the Milestone 33 null was a parser "
          f"artifact")

    # --- apply the correction -------------------------------
    inv = json.load(open(NERV_INV))
    by_id = {r["record_id"]: r for r in inv["records"]}
    ta2_art = json.load(open(TA2_ART))["fma_inventory"]
    ta2_by_id = {e["record_id"]: e for e in ta2_art["resolved"]}

    record_notes = []
    changed = 0
    for rid, child in sided_of.items():
        r = by_id[rid]
        assert r["concept_ids"] == [f"FMA{child}"], rid
        before = {"class_concept_id": r["class_concept_id"],
                  "group_path": list(r["group_path"])}
        derived_path = group_path(child, classes)
        derived_path = [html.unescape(x) if isinstance(x, str)
                        else x for x in derived_path]
        filled = [CLASS_NAME if x is None else x
                  for x in before["group_path"]]
        assert derived_path == filled, (rid, derived_path, filled)
        after = {"class_concept_id": f"FMA{CLASS_FID}",
                 "group_path": derived_path}
        identity = {
            "name": r["name"], "concept_ids": r["concept_ids"],
            "ta_name": r.get("ta_name"), "ta_code": r.get("ta_code"),
        }
        art_entry = ta2_by_id[rid]
        assert art_entry["ta_id"] == r["ta_code"] == 6187 and \
            art_entry["ta_name"] == r["ta_name"], rid
        if before != after:
            r["class_concept_id"] = after["class_concept_id"]
            r["group_path"] = after["group_path"]
            changed += 1
        record_notes.append({
            "record_id": rid, "concept_id": f"FMA{child}",
            "class_concept_id_before": before["class_concept_id"],
            "class_concept_id_after": after["class_concept_id"],
            "group_path_before": before["group_path"],
            "group_path_after": after["group_path"],
            "identity_reverified": identity})
    if changed:
        with open(NERV_INV, "w") as f:
            json.dump(inv, f, indent=1)
    print(f"  corrected records: {changed} (2 expected on first "
          f"run, 0 on re-run)")

    # --- re-verify from disk: only the two fields changed ---
    inv2 = json.load(open(NERV_INV))
    diffs = []
    pre_by = {r["record_id"]: r for r in inv_pre["records"]}
    for r in inv2["records"]:
        p = pre_by[r["record_id"]]
        if r != p:
            keys = [k for k in set(r) | set(p)
                    if r.get(k) != p.get(k)]
            diffs.append((r["record_id"], keys))
    assert all(set(k) <= {"class_concept_id", "group_path"}
               for _rid, k in diffs), diffs
    assert {d[0] for d in diffs} <= set(RECORDS), diffs
    print(f"  nervous inventory diff vs pre-M38 snapshot: "
          f"{len(diffs)} records, fields "
          f"{sorted({k for _, ks in diffs for k in ks})}")

    # --- after-state: the artifact survives nowhere ---------
    survivors = []
    now_total = 0
    for path in sorted(globmod.glob(os.path.join(
            ROOT, "data", "*", "*-inventory.json"))):
        doc = json.load(open(path))
        for r in doc.get("records", []):
            if r.get("source") != SOURCE_TAG:
                continue
            now_total += 1
            if r.get("class_concept_id") is None or \
                    None in (r.get("group_path") or []):
                survivors.append(r["record_id"])
    assert survivors == [], survivors
    print(f"  after-state sweep: {now_total} FMA-sourced "
          f"records, artifact survivors: 0")

    # --- write the artifact section -------------------------
    art = {}
    if os.path.exists(ART_PATH):
        art = json.load(open(ART_PATH))
    art["oculomotor_correction"] = {
        "date": DATE,
        "question": "Milestone 37 §5 named the same Milestone "
                    "33 naive-parser artifact on "
                    "nerve.left/right-oculomotor-nerve "
                    "(class_concept_id null, one null "
                    "group_path entry) and deferred it for a "
                    "ruling; Milestone 38 is that ruling",
        "verdict": "corrected — FMA50864 'Oculomotor nerve' "
                   "carries fma:preferred_name identical to "
                   "its label under both the depth-aware parse "
                   "and an independent XML parse; the null was "
                   "a parser artifact, as with the plexus "
                   "classes at Milestone 37",
        "classes": evidence,
        "correction": CORRECTION_NOTE,
        "records_corrected": record_notes,
        "applied_by": "tools/fma_oculomotor_correct.py",
        "records_changed_this_run": changed,
        "sweep": {
            "scope": "every FMA-sourced record of the intake "
                     "(Milestones 33/36/37) in the frozen "
                     "pre-Milestone 38 snapshots of all eleven "
                     "inventories",
            "records_enumerated": total,
            "carriers_found": hits,
            "after_state": "0 records in any inventory carry "
                           "a null class_concept_id or a null "
                           "group_path entry",
        },
    }
    with open(ART_PATH, "w") as f:
        json.dump(art, f, indent=1)
    print(f"  artifact section -> {ART_PATH} "
          f"(oculomotor_correction)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
