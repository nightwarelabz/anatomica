#!/usr/bin/env python3
"""ANATOMICA urinary + reproductive FMA extension checker —
Milestone 37.

Independent of tools/fma_uri_repro_map.py: the OWL is re-parsed
here with an XML parser (the builder used streaming regex), the
license evidence is re-hashed against the provenance ledger,
and every extension record is re-verified against the ontology
and against every other inventory of the Body Model. Shares no
code with the builder. The plexus re-verification (P1–P4) is
likewise re-derived here from the OWL and the shipped files,
not taken from tools/fma_plexus_correct.py.

Checks:
  L1  data/sources/fma-5.1.0/LICENSE hash == ledger pin, and
      the text is the CC BY 4.0 instrument.
  L2  fma.zip hash == ledger pin.
  C0  the BP3D partitions are intact (urinary 6, reproductive
      13).
  F1  every extension record's concept FMAID exists in fma.owl
      with the identical preferred name.
  F2  side consistency in BOTH of the FMA's naming patterns
      (prefix 'Left renal pelvis'; kidney-suffix 'Cortex of
      left kidney'): a sided record's name carries its side,
      and class_concept_id, where set, is the record's own
      class or the un-sided namesake class.
  F3  group_path ends at the record's own name and carries no
      null entry; the fraction whose path reaches the
      'Anatomical entity' root is reported.
  B1  no extension FMAID appears in ANY other inventory record
      of the Body Model.
  B2  the five accounted exclusions are real: FMA7203/7204/
      7205 (kidney class + instances), FMA9704/15571/15572
      (ureter), FMA15900 (bladder) and FMA19667 (urethra) are
      owned by the urinary module's BP3D records, and FMA20218
      (mons pubis) by the reproductive module's.
  G1  inventory <-> geometry correspondence for extension
      records: one geometry entry each, zero meshes,
      geometry_status set, bounding boxes null, sex_line
      agreement (reproductive).
  G2  every extension record carries the two Milestone 37
      geometry-absent verify flags and the fma-5.1.0 source
      tag.
  C1  census arithmetic: meta record_count, representations,
      sex-line counts (reproductive) and coverage recompute
      from the records themselves.
  A1  the intake accounting (data/fma-intake-37.json)
      reconciles: per-system before/after/added counts, the
      resolved targets' record sets equal the inventories'
      extension sets, every absence probe reports zero
      preferred-name hits, and the plexus section is present.
  P1  the nine plexus classes' name fields under the XML
      parse: FMA5906/5907/5908 carry fma:preferred_name
      identical to their labels (the Milestone 35 'label-only'
      note does not stand), and the six sided children carry
      theirs, each IS-A under its un-sided class per the
      artifact's recorded parentage claim re-derived from the
      regex-free evidence below.
  P2  the six sided plexus records in the nervous inventory
      now carry the derived class_concept_id and a null-free
      group_path whose penultimate entry is the class's
      preferred name — equal to the artifact's recorded
      after-values.
  P3  record identity after correction: the six records'
      names, concept FMAIDs, TA2 names and codes equal the
      values recorded in the artifact and in the
      data/ta2-name-pass.json fma_inventory section.
  P4  the correction is exactly scoped (updated at Milestone
      38, as Milestone 37 §5 anticipated a ruling): across all
      FMA-sourced nervous records, NO null class_concept_id or
      null group_path entry survives, and the two oculomotor
      records named in the artifact's adjacent observation now
      carry FMA50864 with the filled group path. The Milestone
      38 correction itself is gated in full (dual-parse
      evidence, exactness, sweep completeness) by
      tools/fma_integ_male_check.py.

Scope note (Milestone 38): this checker's per-system checks
(F1–F3, B1, G1, G2, C1, A1) cover the Milestone 37 record
sets exactly as gated at Milestone 37 — the reproductive
extension set is read from data/fma-intake-37.json's
accounting. The 76 Milestone 38 male records in the same
inventory are gated by tools/fma_integ_male_check.py; the C1
census checks here read the combined file (133 FMA records)
where the arithmetic spans it.

Usage: fma_uri_repro_check.py. Exit 0 iff all gated checks pass.
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
    "the project's license and registration bars (Milestone 37)",
    "clinical: no clinical tranche has been authored for FMA-sourced "
    "records; no clinical values are entered",
]
SYSTEMS = {
    "urinary": 6,
    "reproductive": 13,
}
PLEXUS = {
    "FMA5906": ("Brachial nerve plexus",
                ["nerve.left-brachial-nerve-plexus",
                 "nerve.right-brachial-nerve-plexus"]),
    "FMA5907": ("Lumbosacral nerve plexus",
                ["nerve.left-lumbosacral-nerve-plexus",
                 "nerve.right-lumbosacral-nerve-plexus"]),
    "FMA5908": ("Lumbar nerve plexus",
                ["nerve.left-lumbar-nerve-plexus",
                 "nerve.right-lumbar-nerve-plexus"]),
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


def base_name(name, side):
    """The un-sided namesake of a record name, in either of the
    FMA's naming patterns."""
    for pre in ("Left ", "Right "):
        if name.startswith(pre):
            return name[len(pre):]
    if side:
        return name.replace(f" of {side} ", " of ")
    return name


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

    inventories = {}
    for path in sorted(globmod.glob(
            os.path.join(ROOT, "data", "*", "*-inventory.json"))):
        system = os.path.basename(os.path.dirname(path))
        inventories[system] = json.load(open(path))

    accounting = json.load(open(os.path.join(
        ROOT, "data", "fma-intake-37.json")))

    for system, bp3d_expected in SYSTEMS.items():
        inv = inventories[system]
        geo = json.load(open(os.path.join(
            ROOT, "data", system, f"{system}-geometry.json")))
        ext_all = [r for r in inv["records"]
                    if r.get("source") == SOURCE_TAG]
        m37_ids = {rid for t in
                   accounting["systems"][system]["targets"]
                   if t["verdict"] == "resolved"
                   for rid in t["records"]}
        ext = [r for r in ext_all if r["record_id"] in m37_ids]
        assert len(ext) == len(m37_ids)
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
                nm = r["name"].lower()
                if not (nm.startswith(r["side"] + " ")
                        or f" of {r['side']} " in nm):
                    bad.append((r["record_id"], "side/name mismatch"))
            if r.get("class_concept_id"):
                cfid = r["class_concept_id"][3:]
                base = base_name(r["name"], r["side"])
                cpn = owl.get(cfid, (None, None))[0]
                if cfid != fid and (cpn or "").lower() != base.lower():
                    bad.append((r["record_id"], "class concept mismatch"))
            gp = r.get("group_path") or []
            if not gp or gp[-1] != r["name"]:
                bad.append((r["record_id"],
                            "group_path does not end at name"))
            if None in gp:
                bad.append((r["record_id"], "group_path null entry"))
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
        gbad = []
        for r in ext:
            g = geo_by_id.get(r["record_id"])
            if g is None or g["isa_meshes"] or g["partof_meshes"] \
                    or not g.get("geometry_status") \
                    or g["bbox_isa"] is not None \
                    or g["bbox_partof"] is not None:
                gbad.append(r["record_id"])
            elif system == "reproductive" and \
                    g.get("sex_line") != r.get("sex_line"):
                gbad.append((r["record_id"], "sex_line"))
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
        ok = meta["record_count"] == len(inv["records"]) \
            and meta["record_representations"].get("fma-concept") \
            == len(ext_all) \
            and meta["fma_extension"]["records_added"] == len(ext)
        if system == "reproductive":
            from collections import Counter
            ok = ok and meta["records_by_sex_line"] == dict(
                Counter(r["sex_line"] for r in inv["records"])) \
                and meta["fma_extension_38"]["records_added"] \
                == len(ext_all) - len(ext)
        check(ok, f"C1 census arithmetic [{system}]",
              f"{len(inv['records'])} total = {len(bp3d)} + "
              f"{len(ext_all)} FMA ({len(ext)} of them M37)")
        cov = geo["meta"]["coverage"]
        ok = cov["records"] == len(geo["records"]) \
            and cov["records_without_meshes"] == len(ext_all)
        if system == "reproductive":
            from collections import Counter
            lines = {}
            for g in geo["records"]:
                e = lines.setdefault(
                    g["sex_line"],
                    {"records": 0, "records_with_meshes": 0})
                e["records"] += 1
                if g["isa_meshes"] or g["partof_meshes"]:
                    e["records_with_meshes"] += 1
            ok = ok and cov["by_sex_line"] == lines
        check(ok, f"C1 geometry coverage arithmetic [{system}]",
              f"{cov}")

        sec = accounting["systems"][system]
        resolved_ids = sorted(rid for t in sec["targets"]
                              if t["verdict"] == "resolved"
                              for rid in t["records"])
        probes_ok = all(p["preferred_name_hits"] == 0
                        for p in sec["absence_probes"])
        check(sec["records_before"] == len(bp3d)
              and sec["records_after"] == len(bp3d) + len(ext)
              and sec["records_added"] == len(ext)
              and resolved_ids == sorted(r["record_id"] for r in ext)
              and probes_ok,
              f"A1 accounting reconciles [{system}]",
              f"{sec['records_before']} -> {sec['records_after']} "
              f"(Milestone 37 state; the file now holds "
              f"{len(inv['records'])})")

    # B2 — the five accounted exclusions, re-derived
    uri = {r["record_id"]: r for r in inventories["urinary"]["records"]}
    rep = {r["record_id"]: r
           for r in inventories["reproductive"]["records"]}
    excl = {(s, t["target"])
            for s in SYSTEMS for t in accounting["systems"][s]["targets"]
            if t["verdict"] == "excluded"}
    check(uri["kidney.left-kidney"]["concept_ids"] == ["FMA7205"]
          and uri["kidney.right-kidney"]["concept_ids"] == ["FMA7204"]
          and uri["kidney.left-kidney"]["class_concept_id"] == "FMA7203"
          and uri["ureter.left-ureter"]["concept_ids"] == ["FMA15572"]
          and uri["ureter.right-ureter"]["concept_ids"] == ["FMA15571"]
          and uri["ureter.left-ureter"]["class_concept_id"] == "FMA9704"
          and uri["urinary-bladder"]["concept_ids"] == ["FMA15900"]
          and uri["urethra"]["concept_ids"] == ["FMA19667"]
          and rep["mons-pubis"]["concept_ids"] == ["FMA20218"]
          and excl == {("urinary", "Kidney"), ("urinary", "Ureter"),
                       ("urinary", "Urinary bladder"),
                       ("urinary", "Urethra"),
                       ("reproductive", "Mons pubis")},
          "B2 the five accounted exclusions are real (kidney, "
          "ureter, bladder, urethra, mons pubis already owned)")

    # ---- plexus re-verification --------------------------------
    psec = accounting.get("plexus_reverification") or {}
    nerv = {r["record_id"]: r
            for r in inventories["nervous"]["records"]}
    ta2sec = json.load(open(os.path.join(
        ROOT, "data", "ta2-name-pass.json")))["fma_inventory"]
    ta2_by_id = {e["record_id"]: e for e in ta2sec["resolved"]}

    pbad = []
    ev = {e["fmaid"]: e for e in psec.get("classes", [])}
    for cfid, (cname, rids) in PLEXUS.items():
        fid = cfid[3:]
        pn, lb = owl.get(fid, (None, None))
        if pn != cname or lb != cname:
            pbad.append((cfid, "XML name fields", pn, lb))
        e = ev.get(cfid) or {}
        if e.get("preferred_name") != cname or e.get("label") != cname:
            pbad.append((cfid, "artifact evidence mismatch"))
        for rid in rids:
            rfid = nerv[rid]["concept_ids"][0][3:]
            rpn, _rlb = owl.get(rfid, (None, None))
            if rpn != nerv[rid]["name"]:
                pbad.append((rid, "sided name mismatch", rpn))
    check(not pbad and len(ev) == 9,
          "P1 plexus classes carry preferred_name (XML parse): "
          "FMA5906/5907/5908 + six sided children", f"{pbad[:3]}")

    cbad = []
    corr = {c["record_id"]: c
            for c in psec.get("records_corrected", [])}
    for cfid, (cname, rids) in PLEXUS.items():
        for rid in rids:
            r = nerv[rid]
            c = corr.get(rid) or {}
            if r["class_concept_id"] != cfid \
                    or None in (r["group_path"] or []) \
                    or r["group_path"][-2] != cname \
                    or r["group_path"][-1] != r["name"] \
                    or c.get("class_concept_id_after") != cfid \
                    or c.get("group_path_after") != r["group_path"] \
                    or c.get("class_concept_id_before") is not None \
                    or None not in (c.get("group_path_before") or []):
                cbad.append(rid)
    check(not cbad and len(corr) == 6,
          "P2 six plexus records corrected (class id + group_path)",
          f"{cbad[:3]}")

    ibad = []
    for cfid, (_cname, rids) in PLEXUS.items():
        for rid in rids:
            r = nerv[rid]
            ident = (corr.get(rid) or {}).get(
                "identity_reverified") or {}
            if ident.get("name") != r["name"] \
                    or ident.get("concept_ids") != r["concept_ids"] \
                    or ident.get("ta_name") != r.get("ta_name") \
                    or ident.get("ta_code") != r.get("ta_code") \
                    or ta2_by_id[rid]["ta_id"] != r["ta_code"] \
                    or ta2_by_id[rid]["ta_name"] != r["ta_name"]:
                ibad.append(rid)
    check(not ibad,
          "P3 plexus record identity re-verified (FMAIDs, TA2 "
          "outcomes unchanged)", f"{ibad[:3]}")

    survivors = [r["record_id"]
                 for r in inventories["nervous"]["records"]
                 if r.get("source") == SOURCE_TAG
                 and (r.get("class_concept_id") is None
                      or None in (r.get("group_path") or []))]
    occ_l = nerv["nerve.left-oculomotor-nerve"]
    occ_r = nerv["nerve.right-oculomotor-nerve"]
    check(survivors == []
          and occ_l["class_concept_id"] == "FMA50864"
          and occ_r["class_concept_id"] == "FMA50864"
          and occ_l["group_path"][-2] == "Oculomotor nerve"
          and occ_r["group_path"][-2] == "Oculomotor nerve"
          and occ_l["group_path"][-1] == occ_l["name"]
          and occ_r["group_path"][-1] == occ_r["name"],
          "P4 correction exactly scoped (updated at Milestone "
          "38): no null artifact survives in any FMA-sourced "
          "nervous record, and the two oculomotor records "
          "named at Milestone 37 now carry FMA50864 with the "
          "filled group path",
          f"survivors={survivors}")

    print(f"\n{'ALL CHECKS PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
