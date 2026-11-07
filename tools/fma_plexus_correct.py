#!/usr/bin/env python3
"""ANATOMICA Milestone 37: plexus label re-verification and
correction.

Re-derives the name fields of the somatic plexus classes —
FMA5906 'Brachial nerve plexus', FMA5907 'Lumbosacral nerve
plexus', FMA5908 'Lumbar nerve plexus', and their six sided
children — under the depth-aware OWL parse (the Milestone 36
repair), cross-checked against an independent ElementTree XML
parse of the same file.

Milestone 35 (§1) recorded, from Milestone 33's import, that
the three un-sided classes "carry an rdfs:label but no
fma:preferred_name, which is why the importer missed them".
Milestone 36 §5.1 flagged that reading as a probable
naive-parser artifact. It was: under both correct parses all
three classes carry fma:preferred_name identical to their
labels. The Milestone 33 records keyed on the sided children
were created anyway (the children's own names parsed), but
their class_concept_id was left null and their group_path
carries a null at the un-sided class's position.

This tool corrects exactly those two name-provenance fields on
exactly those six records:

  * class_concept_id: null -> the un-sided class (FMA5906 /
    FMA5907 / FMA5908), derived from the sided class's IS-A
    parentage in the OWL;
  * group_path: the null entry -> the class's preferred name.
    The corrected path is re-derived by BFS over the
    depth-aware parse and asserted equal to the recorded path
    with the null slot filled — no other path element changes.

Record identity is re-verified after the correction: names,
concept FMAIDs, TA2 names/codes (against the
data/ta2-name-pass.json fma_inventory section) and every other
field are asserted unchanged. The full evidence — both parses'
name fields for all nine classes, before/after values, and
the dated correction note — is written to the
plexus_reverification section of data/fma-intake-37.json.

Idempotent: an already-corrected inventory is detected and
reported, with the artifact section refreshed.

Usage: fma_plexus_correct.py
Stdlib only.
"""
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
ART_PATH = os.path.join(ROOT, "data", "fma-intake-37.json")
TA2_ART = os.path.join(ROOT, "data", "ta2-name-pass.json")
DATE = "2026-11-06"

# un-sided class -> (expected preferred name, [sided record ids])
PLEXUS = {
    "5906": ("Brachial nerve plexus",
             ["nerve.left-brachial-nerve-plexus",
              "nerve.right-brachial-nerve-plexus"]),
    "5907": ("Lumbosacral nerve plexus",
             ["nerve.left-lumbosacral-nerve-plexus",
              "nerve.right-lumbosacral-nerve-plexus"]),
    "5908": ("Lumbar nerve plexus",
             ["nerve.left-lumbar-nerve-plexus",
              "nerve.right-lumbar-nerve-plexus"]),
}

CORRECTION_NOTE = (
    "Correction (2026-11-06, Milestone 37): Milestone 35 §1 "
    "recorded the un-sided plexus classes FMA5906/5907/5908 as "
    "carrying an rdfs:label but no fma:preferred_name. That "
    "reading was an artifact of the naive OWL block parser "
    "(the defect class proven at Milestone 36 §5.1): under the "
    "depth-aware parse, and independently under an ElementTree "
    "XML parse, all three classes carry fma:preferred_name "
    "identical to their labels. The six sided records' "
    "class_concept_id (null since the Milestone 33 import) "
    "and group_path (one null entry at the class position) "
    "are corrected to the derived values. Record names, "
    "concept FMAIDs, TA2 names and codes, and all other "
    "fields are unchanged and re-verified; the Milestone 35 "
    "TA2 outcomes for these records (6395 / 6517 / 6516, the "
    "un-sided classes' terms) stand.")


def parse_owl_xml(path):
    """ElementTree iterparse: {fid: (preferred_name, label)}."""
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
            if about:
                names[about.rsplit("fma", 1)[-1]] = (
                    pn.text if pn is not None else None,
                    lb.text if lb is not None else None)
            el.clear()
    return names


def main():
    classes = parse_owl(OWL)
    owl_xml = parse_owl_xml(OWL)

    # --- name-field evidence for the nine classes, both parses.
    # The sided classes are anchored on the records' own concept
    # FMAIDs (identity), then their names and parentage are
    # verified against the OWL.
    _inv_pre = json.load(open(NERV_INV))
    _rec_pre = {r["record_id"]: r for r in _inv_pre["records"]}
    evidence = []
    sided_of = {}  # record_id -> (class fid, sided fid)
    for cfid, (expected, rids) in PLEXUS.items():
        rx = classes[cfid]
        xm = owl_xml[cfid]
        assert rx["name"] == xm[0] and rx["label"] == xm[1], cfid
        evidence.append({
            "fmaid": f"FMA{cfid}", "role": "un-sided class",
            "preferred_name": rx["name"], "label": rx["label"],
            "parses_agree": True})
        assert rx["name"] == expected, (cfid, rx["name"])
        for rid in rids:
            side = "left" if ".left-" in rid else "right"
            child = _rec_pre[rid]["concept_ids"][0][3:]
            cx = owl_xml[child]
            assert classes[child]["name"] == cx[0], child
            assert classes[child]["name"].lower() == \
                f"{side} {expected}".lower(), child
            assert cfid in classes[child]["parents"], child
            evidence.append({
                "fmaid": f"FMA{child}", "role": f"sided class ({side})",
                "preferred_name": classes[child]["name"],
                "label": classes[child]["label"],
                "is_a_parent": f"FMA{cfid}", "parses_agree": True})
            sided_of[rid] = (cfid, child)
    print("name fields re-derived: FMA5906/5907/5908 all carry "
          "fma:preferred_name (both parses agree) — the "
          "Milestone 35 'label-only' note does not stand")

    # --- adjacent observation (reported, NOT corrected: outside
    # the named scope): the two oculomotor records carry the
    # same artifact
    oculo_parents = {}
    for sfid in ("50879", "50880"):
        for p in classes[sfid]["parents"]:
            oculo_parents[f"FMA{p}"] = classes[p]["name"]
    print(f"  adjacent: oculomotor sided classes' IS-A parents: "
          f"{oculo_parents}")

    # --- apply the correction
    inv = json.load(open(NERV_INV))
    by_id = {r["record_id"]: r for r in inv["records"]}
    ta2_art = json.load(open(TA2_ART))["fma_inventory"]
    ta2_by_id = {e["record_id"]: e for e in ta2_art["resolved"]}

    record_notes = []
    changed = 0
    for rid, (cfid, child) in sided_of.items():
        r = by_id[rid]
        assert r["concept_ids"] == [f"FMA{child}"], rid
        before = {"class_concept_id": r["class_concept_id"],
                  "group_path": list(r["group_path"])}
        derived_path = group_path(child, classes)
        filled = [classes[cfid]["name"] if x is None else x
                  for x in before["group_path"]]
        assert derived_path == filled, (rid, derived_path, filled)
        after = {"class_concept_id": f"FMA{cfid}",
                 "group_path": derived_path}
        identity = {
            "name": r["name"], "concept_ids": r["concept_ids"],
            "ta_name": r.get("ta_name"), "ta_code": r.get("ta_code"),
        }
        art_entry = ta2_by_id[rid]
        assert art_entry["ta_id"] == r["ta_code"] and \
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
    print(f"  corrected records: {changed} (6 expected on first "
          f"run, 0 on re-run)")

    # --- re-verify from disk: only the two fields changed
    inv2 = json.load(open(NERV_INV))
    pre = json.load(open(os.path.join(
        ROOT, "work", "m37", "pre-nervous-inventory.json")))
    diffs = []
    pre_by = {r["record_id"]: r for r in pre["records"]}
    for r in inv2["records"]:
        p = pre_by[r["record_id"]]
        if r != p:
            keys = [k for k in set(r) | set(p)
                    if r.get(k) != p.get(k)]
            diffs.append((r["record_id"], keys))
    assert all(set(k) <= {"class_concept_id", "group_path"}
               for _rid, k in diffs), diffs
    assert {d[0] for d in diffs} <= set(sided_of), diffs
    print(f"  nervous inventory diff vs pre-M37 snapshot: "
          f"{len(diffs)} records, fields {sorted({k for _, ks in diffs for k in ks})}")

    # --- write the artifact section
    art = json.load(open(ART_PATH))
    art["plexus_reverification"] = {
        "date": DATE,
        "question": "Milestone 35 §1 recorded FMA5906/5907/5908 "
                    "as carrying rdfs:label but no "
                    "fma:preferred_name (a Milestone 33 import "
                    "reading); Milestone 36 §5.1 flagged the "
                    "reading as a probable naive-parser artifact",
        "verdict": "the note does not stand — all three classes "
                   "carry fma:preferred_name identical to their "
                   "labels, under both the depth-aware parse and "
                   "an independent XML parse",
        "classes": evidence,
        "correction": CORRECTION_NOTE,
        "records_corrected": record_notes,
        "applied_by": "tools/fma_plexus_correct.py",
        "records_changed_this_run": changed,
        "adjacent_observation_not_corrected": (
            "nerve.left-oculomotor-nerve and "
            "nerve.right-oculomotor-nerve carry the same "
            "Milestone 33 artifact (class_concept_id null, one "
            "null group_path entry at the un-sided class "
            f"position; parents under the depth-aware parse: "
            f"{oculo_parents}). They are outside this "
            "milestone's named scope (the six plexus classes) "
            "and are NOT corrected here; named for a future "
            "ruling."),
    }
    with open(ART_PATH, "w") as f:
        json.dump(art, f, indent=1)
    print(f"  artifact section -> {ART_PATH} "
          f"(plexus_reverification)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
