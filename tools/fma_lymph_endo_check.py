#!/usr/bin/env python3
"""ANATOMICA lymphatic + endocrine FMA extension checker — Milestone 36.

Independent of tools/fma_lymph_endo_map.py: the OWL is re-parsed
here with an XML parser (the builder used streaming regex), the
license evidence is re-hashed against the provenance ledger, and
every extension record is re-verified against the ontology and
against every other inventory of the Body Model. Shares no code
with the builder.

Checks:
  L1  data/sources/fma-5.1.0/LICENSE hash == ledger pin, and the
      text is the CC BY 4.0 instrument (title + Section 2 grant).
  L2  fma.zip hash == ledger pin.
  C0  the BP3D partitions are intact (lymphatic 4, endocrine 3).
  F1  every extension record's concept FMAID exists in fma.owl
      with the identical preferred name. (This check is what
      caught the builder's first OWL parser truncating FMA9603
      at its nested restriction axioms and misreading the class
      as label-only; the class carries its preferred name after
      the axioms, and the record is an ordinary preferred-name
      record.)
  F2  side consistency: a record with side left/right keys on the
      FMA's sided class of that name; an un-sided record keys on
      the un-sided class; class_concept_id, where set, is the
      record's own class or the un-sided namesake class.
  F3  group_path ends at the record's own name; the fraction whose
      path reaches the 'Anatomical entity' root is reported.
  B1  no extension FMAID appears in ANY other inventory record of
      the Body Model (all systems, BP3D-derived or Milestone 33
      FMA) — the extension adds only what the model lacks.
  B2  the one accounted exclusion is real: FMA62033 (Pineal body)
      is owned by the nervous inventory's BP3D record
      brain.pineal-body.
  G1  inventory <-> geometry correspondence for extension records:
      one geometry entry each, zero meshes, geometry_status set,
      bounding boxes null.
  G2  every extension record carries the two Milestone 36
      geometry-absent verify flags (as its first verify entries;
      any further entry is the TA2 pass's ta_name flag, gated by
      tools/ta2_discipline.py) and the fma-5.1.0 source tag.
  C1  census arithmetic: meta record_count, representations and
      coverage recompute from the records themselves.
  A1  the intake accounting (data/fma-intake-36.json) reconciles:
      per-system before/after/added counts, the resolved targets'
      record sets equal the inventories' extension sets, and every
      absence probe reports zero preferred-name hits.

Usage: fma_lymph_endo_check.py. Exit 0 iff all gated checks pass.
Stdlib only.
"""
import glob as globmod
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources", "fma-5.1.0")
OWL = os.path.join(ROOT, "work", "fma", "fma.owl")
LEDGER = json.load(open(os.path.join(SRC, "ledger.json")))
SOURCE_TAG = "fma-5.1.0"
VERIFY_FLAGS = [
    "geometry: absent — the FMA is an ontology and carries no mesh "
    "data; this record is concept-only until a geometry source clears "
    "the project's license and registration bars (Milestone 36)",
    "clinical: no clinical tranche has been authored for FMA-sourced "
    "records; no clinical values are entered",
]
SYSTEMS = {
    "lymphatic": 4,
    "endocrine": 3,
}

FAILS = []


def check(ok, label, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label} {detail}")
    if not ok:
        FAILS.append(label)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_owl_xml(path):
    """ElementTree iterparse: {fid: (preferred_name, label)}."""
    ns = {"owl": "http://www.w3.org/2002/07/owl#",
          "fma": "http://purl.org/sig/ont/fma/",
          "rdfs": "http://www.w3.org/2000/01/rdf-schema#"}
    names = {}
    for _ev, el in ET.iterparse(path, events=("end",)):
        if el.tag == f"{{{ns['owl']}}}Class":
            about = el.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about")
            pn = el.find("fma:preferred_name", ns)
            lb = el.find("rdfs:label", ns)
            if about:
                names[about.rsplit("fma", 1)[-1]] = (
                    pn.text if pn is not None else None,
                    lb.text if lb is not None else None)
            el.clear()
    return names


def main():
    pins = {e["path"]: e["sha256"] for e in LEDGER["entries"]}
    lic_path = os.path.join(SRC, "LICENSE")
    lic_text = open(lic_path, encoding="utf-8").read()
    check(sha256(lic_path) == pins["LICENSE"]
          and "Attribution 4.0 International" in lic_text
          and "reproduce and Share the Licensed Material" in lic_text,
          "L1 license evidence", "CC BY 4.0 text, hash-pinned")
    check(sha256(os.path.join(SRC, "fma.zip")) == pins["fma.zip"],
          "L2 fma.zip hash == ledger pin")

    owl = parse_owl_xml(OWL)
    print(f"  OWL classes (XML parse): {len(owl)}")

    # Global ownership: every FMAID in every inventory record.
    inventories = {}
    for path in sorted(globmod.glob(
            os.path.join(ROOT, "data", "*", "*-inventory.json"))):
        system = os.path.basename(os.path.dirname(path))
        inventories[system] = json.load(open(path))

    accounting = json.load(open(os.path.join(
        ROOT, "data", "fma-intake-36.json")))

    for system, bp3d_expected in SYSTEMS.items():
        inv = inventories[system]
        geo = json.load(open(os.path.join(
            ROOT, "data", system, f"{system}-geometry.json")))
        ext = [r for r in inv["records"] if r.get("source") == SOURCE_TAG]
        bp3d = [r for r in inv["records"] if r.get("source") != SOURCE_TAG]
        check(len(bp3d) == bp3d_expected,
              f"C0 BP3D partition intact [{system}]", f"{len(bp3d)}")

        bad = []
        root_hits = 0
        for r in ext:
            fid = r["concept_ids"][0][3:]
            pn, lb = owl.get(fid, (None, None))
            if pn != r["name"]:
                bad.append((r["record_id"], "name/FMAID mismatch"))
            if r["side"] in ("left", "right"):
                if not r["name"].lower().startswith(r["side"] + " "):
                    bad.append((r["record_id"], "side/name mismatch"))
            if r.get("class_concept_id"):
                cfid = r["class_concept_id"][3:]
                base = r["name"]
                for pre in ("Left ", "Right "):
                    if base.startswith(pre):
                        base = base[len(pre):]
                cpn = owl.get(cfid, (None, None))[0]
                # Consistent iff the class pointer is the record's
                # own class (un-sided records; includes classes
                # whose very name carries a side, e.g. FMA5832
                # 'Right lymphatic duct') or the un-sided namesake
                # of a sided record.
                if cfid != fid and (cpn or "").lower() != base.lower():
                    bad.append((r["record_id"], "class concept mismatch"))
            gp = r.get("group_path") or []
            if not gp or gp[-1] != r["name"]:
                bad.append((r["record_id"],
                            "group_path does not end at name"))
            if gp and gp[0] == "Anatomical entity":
                root_hits += 1
        check(not bad, f"F1/F2/F3 record fidelity vs OWL [{system}]",
              f"{len(ext)} records; {bad[:3]}")
        print(f"  group_path reaches 'Anatomical entity' root "
              f"[{system}]: {root_hits}/{len(ext)}")

        elsewhere = set()
        for other, oinv in inventories.items():
            for r in oinv["records"]:
                if other == system and r.get("source") == SOURCE_TAG:
                    continue  # this system's own extension
                elsewhere.update(r.get("concept_ids") or [])
                if r.get("class_concept_id"):
                    elsewhere.add(r["class_concept_id"])
        overlap = [r["record_id"] for r in ext
                   if r["concept_ids"][0] in elsewhere]
        check(not overlap, f"B1 no FMAID overlap anywhere [{system}]",
              f"{overlap[:3]}")

        geo_by_id = {g["record_id"]: g for g in geo["records"]}
        gbad = [r["record_id"] for r in ext
                if r["record_id"] not in geo_by_id
                or geo_by_id[r["record_id"]]["isa_meshes"]
                or geo_by_id[r["record_id"]]["partof_meshes"]
                or not geo_by_id[r["record_id"]].get("geometry_status")
                or geo_by_id[r["record_id"]]["bbox_isa"] is not None
                or geo_by_id[r["record_id"]]["bbox_partof"] is not None]
        check(not gbad, f"G1 geometry correspondence [{system}] "
                        f"(all mesh-less)", f"{gbad[:3]}")
        vbad = [r["record_id"] for r in ext
                if r.get("geometry") != "absent"
                or r.get("verify", [])[:2] != VERIFY_FLAGS
                or any(not e.startswith("ta_name:")
                       for e in r.get("verify", [])[2:])]
        check(not vbad, f"G2 verify flags carried [{system}]",
              f"{vbad[:3]}")

        meta = inv["meta"]
        check(meta["record_count"] == len(inv["records"])
              and meta["record_representations"].get("fma-concept")
              == len(ext)
              and meta["fma_extension"]["records_added"] == len(ext),
              f"C1 census arithmetic [{system}]",
              f"{len(inv['records'])} total = {len(bp3d)} + {len(ext)}")
        cov = geo["meta"]["coverage"]
        check(cov["records"] == len(geo["records"])
              and cov["records_without_meshes"] == len(ext),
              f"C1 geometry coverage arithmetic [{system}]", f"{cov}")

        sec = accounting["systems"][system]
        resolved_ids = sorted(rid for t in sec["targets"]
                              if t["verdict"] == "resolved"
                              for rid in t["records"])
        probes_ok = all(p["preferred_name_hits"] == 0
                        for p in sec["absence_probes"])
        check(sec["records_before"] == len(bp3d)
              and sec["records_after"] == len(inv["records"])
              and sec["records_added"] == len(ext)
              and resolved_ids == sorted(r["record_id"] for r in ext)
              and probes_ok,
              f"A1 accounting reconciles [{system}]",
              f"{sec['records_before']} -> {sec['records_after']}")

    pineal_owner = [r["record_id"]
                    for r in inventories["nervous"]["records"]
                    if "FMA62033" in (r.get("concept_ids") or [])]
    check(pineal_owner == ["brain.pineal-body"]
          and any(t["target"] == "Pineal body"
                  and t["verdict"] == "excluded"
                  for t in accounting["systems"]["endocrine"]["targets"]),
          "B2 pineal exclusion is real and accounted",
          f"owner: {pineal_owner}")

    print(f"\n{'ALL CHECKS PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
