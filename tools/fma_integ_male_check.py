#!/usr/bin/env python3
"""ANATOMICA integumentary + male reproductive FMA extension
checker, and the oculomotor correction gate — Milestone 38.

Independent of tools/fma_integ_male_map.py and
tools/fma_oculomotor_correct.py: the OWL is re-parsed here
with an XML parser (the builders used streaming regex), the
license evidence is re-hashed against the provenance ledger,
every Milestone 38 record is re-verified against the ontology
and against every other inventory of the Body Model, and the
oculomotor correction is re-derived from the OWL, the shipped
files and the pre-Milestone-38 snapshots. Shares no code with
the builders or the corrector.

Checks:
  L1  data/sources/fma-5.1.0/LICENSE hash == ledger pin, and
      the text is the CC BY 4.0 instrument.
  L2  fma.zip hash == ledger pin.
  C0  the BP3D partitions are intact (integumentary 6,
      reproductive 13).
  F1  every Milestone 38 record's concept FMAID exists in
      fma.owl with the identical preferred name.
  F2  side consistency in BOTH of the FMA's naming patterns
      (prefix 'Left deferent duct'; suffix 'Seminiferous
      tubule of left testis'): a sided record's name carries
      its side, and class_concept_id, where set, is the
      record's own class or the un-sided namesake class.
  F3  group_path ends at the record's own name and carries no
      null entry; the fraction whose path reaches the
      'Anatomical entity' root is reported.
  B1  no Milestone 38 FMAID appears in ANY other inventory
      record of the Body Model.
  B2  the eight accounted exclusions are real: FMA7163 (skin),
      FMA53667 (hair) and FMA54237 (eyebrow) are owned by the
      integumentary module's BP3D records; FMA7210/7211/7212
      (testis), FMA18255/18256/18257 (epididymis),
      FMA19386/19387/19388 (seminal vesicle), FMA9600
      (prostate) and FMA18247 (glans penis) by the
      reproductive module's. And the bulbourethral evidence:
      no OWL class carries the preferred name 'Bulbourethral
      gland', and no record was created from its duct classes
      (FMA20091 and sided children).
  G1  inventory <-> geometry correspondence for Milestone 38
      records: one geometry entry each, zero meshes,
      geometry_status set, bounding boxes null, sex_line
      (reproductive) / line (integumentary) agreement.
  G2  every Milestone 38 record carries the two Milestone 38
      geometry-absent verify flags and the fma-5.1.0 source
      tag.
  C1  census arithmetic: meta record_count, representations,
      extension blocks, sex-line / line counts and geometry
      coverage recompute from the records themselves.
  A1  the intake accounting (data/fma-intake-38.json,
      §systems) reconciles: per-system before/after/added
      counts, the resolved targets' record sets equal the
      inventories' Milestone 38 sets, every absence probe
      reports zero preferred-name hits.
  O1  the oculomotor classes' name fields under the XML
      parse: FMA50864 carries fma:preferred_name identical to
      its label ('Oculomotor nerve'), and the sided classes
      FMA50879/FMA50880 carry theirs.
  O2  the correction is exact: both records now carry
      class_concept_id FMA50864 and a group_path equal to the
      artifact's recorded after-values — the recorded before
      path with its single null slot filled by the class's
      preferred name, nothing else moved.
  O3  record identity after correction: the two records'
      names, concept FMAIDs, TA2 names and codes equal the
      artifact's identity values and the
      data/ta2-name-pass.json fma_inventory section (6187).
  O4  the Milestone 37 plexus corrections are still intact:
      the six records carry FMA5906/5907/5908 and null-free
      group paths ending in their own names.
  S1  sweep completeness, by construction: enumerating every
      null class_concept_id and every null group_path entry
      across all FMA-sourced records of the frozen
      pre-Milestone-38 snapshots (work/m38/pre-inventories/)
      yields exactly the two oculomotor records; the same
      enumeration over the current inventories yields none,
      over 684 FMA-sourced records Body-Model-wide.

Usage: fma_integ_male_check.py. Exit 0 iff all gated checks pass.
Stdlib only.
"""
import glob as globmod
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources", "fma-5.1.0")
OWL = os.path.join(ROOT, "work", "fma", "fma.owl")
LEDGER = json.load(open(os.path.join(SRC, "ledger.json")))
SOURCE_TAG = "fma-5.1.0"
VERIFY_FLAGS = [
    "geometry: absent — the FMA is an ontology and carries no mesh "
    "data; this record is concept-only until a geometry source clears "
    "the project's license and registration bars (Milestone 38)",
    "clinical: no clinical tranche has been authored for FMA-sourced "
    "records; no clinical values are entered",
]
SYSTEMS = {
    "integumentary": 6,
    "reproductive": 13,
}
PLEXUS_AFTER = {
    "nerve.left-brachial-nerve-plexus": "FMA5906",
    "nerve.right-brachial-nerve-plexus": "FMA5906",
    "nerve.left-lumbosacral-nerve-plexus": "FMA5907",
    "nerve.right-lumbosacral-nerve-plexus": "FMA5907",
    "nerve.left-lumbar-nerve-plexus": "FMA5908",
    "nerve.right-lumbar-nerve-plexus": "FMA5908",
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
        ROOT, "data", "fma-intake-38.json")))
    m38_ids = {}
    for system in SYSTEMS:
        sec = accounting["systems"][system]
        m38_ids[system] = {rid for t in sec["targets"]
                           if t["verdict"] == "resolved"
                           for rid in t["records"]}

    for system, bp3d_expected in SYSTEMS.items():
        inv = inventories[system]
        geo = json.load(open(os.path.join(
            ROOT, "data", system, f"{system}-geometry.json")))
        ext_all = [r for r in inv["records"]
                    if r.get("source") == SOURCE_TAG]
        ext = [r for r in ext_all
               if r["record_id"] in m38_ids[system]]
        assert len(ext) == len(m38_ids[system])
        bp3d = [r for r in inv["records"]
                if r.get("source") != SOURCE_TAG]
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
                    bad.append((r["record_id"],
                                "class concept mismatch"))
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
                if other == system and r["record_id"] in m38_ids[system]:
                    continue  # this system's own Milestone 38 set
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
            elif system == "integumentary" and \
                    g.get("line") != r.get("line"):
                gbad.append((r["record_id"], "line"))
        check(not gbad, f"G1 geometry correspondence [{system}] "
                        f"(all mesh-less)", f"{gbad[:3]}")
        vbad = [r["record_id"] for r in ext
                if r.get("geometry") != "absent"
                or r.get("verify", [])[:2] != VERIFY_FLAGS
                or any(not e.startswith("ta_name:")
                       for e in r.get("verify", [])[2:])]
        check(not vbad, f"G2 verify flags carried [{system}]",
              f"{vbad[:3]}")

        sec = accounting["systems"][system]
        meta = inv["meta"]
        ok = meta["record_count"] == len(inv["records"]) \
            and meta["record_representations"].get("fma-concept") \
            == len(ext_all) \
            and len(inv["records"]) == sec["records_after"] \
            and len(ext_all) == sec["prior_fma_records"] + len(ext)
        if system == "integumentary":
            ok = ok and meta["fma_extension"]["records_added"] \
                == len(ext) \
                and meta["records_by_line"] == dict(Counter(
                    r["line"] for r in inv["records"]))
        else:
            ok = ok and meta["fma_extension"]["records_added"] \
                == sec["prior_fma_records"] \
                and meta["fma_extension_38"]["records_added"] \
                == len(ext) \
                and meta["records_by_sex_line"] == dict(Counter(
                    r["sex_line"] for r in inv["records"]))
        check(ok, f"C1 census arithmetic [{system}]",
              f"{len(inv['records'])} total = {len(bp3d)} + "
              f"{len(ext_all)} FMA ({len(ext)} of them M38)")
        cov = geo["meta"]["coverage"]
        ok = cov["records"] == len(geo["records"]) \
            and cov["records_without_meshes"] == len(ext_all)
        lines = {}
        key = "by_line" if system == "integumentary" \
            else "by_sex_line"
        field = "line" if system == "integumentary" else "sex_line"
        for g in geo["records"]:
            e = lines.setdefault(
                g[field], {"records": 0, "records_with_meshes": 0})
            e["records"] += 1
            if g["isa_meshes"] or g["partof_meshes"]:
                e["records_with_meshes"] += 1
        # the integumentary coverage carries a legacy "system"
        # row (0 records) beside the two record lines
        extra = {k: v for k, v in cov[key].items() if k not in lines}
        ok = ok and all(cov[key][k] == v for k, v in lines.items()) \
            and all(v == {"records": 0, "records_with_meshes": 0}
                    for v in extra.values())
        check(ok, f"C1 geometry coverage arithmetic [{system}]",
              f"{cov['records']} entries, "
              f"{cov['records_without_meshes']} mesh-less")

        resolved_ids = sorted(rid for t in sec["targets"]
                              if t["verdict"] == "resolved"
                              for rid in t["records"])
        probes_ok = all(p["preferred_name_hits"] == 0
                        for p in sec["absence_probes"])
        check(sec["records_before"] == len(bp3d) + len(ext_all) - len(ext)
              and sec["records_after"] == len(inv["records"])
              and sec["records_added"] == len(ext)
              and resolved_ids == sorted(r["record_id"] for r in ext)
              and probes_ok,
              f"A1 accounting reconciles [{system}]",
              f"{sec['records_before']} -> {sec['records_after']}")

    # B2 — the eight accounted exclusions, re-derived
    integ = {r["record_id"]: r
             for r in inventories["integumentary"]["records"]}
    rep = {r["record_id"]: r
           for r in inventories["reproductive"]["records"]}
    excl = {(s, t["target"])
            for s in SYSTEMS
            for t in accounting["systems"][s]["targets"]
            if t["verdict"] == "excluded"}
    owned = set()
    for r in list(integ.values()) + list(rep.values()):
        if r.get("source") != SOURCE_TAG:
            owned.update(r.get("concept_ids") or [])
            if r.get("class_concept_id"):
                owned.add(r["class_concept_id"])
    bulb_names = [fid for fid, (pn, _lb) in owl.items()
                  if pn == "Bulbourethral gland"]
    duct_records = [r["record_id"]
                    for inv in inventories.values()
                    for r in inv["records"]
                    if "FMA20091" in (r.get("concept_ids") or [])
                    or r.get("class_concept_id") == "FMA20091"]
    check(integ["skin"]["concept_ids"] == ["FMA7163"]
          and integ["hair"]["concept_ids"] == ["FMA53667"]
          and integ["eyebrow"]["concept_ids"] == ["FMA54237"]
          and {"FMA7210", "FMA7211", "FMA7212",
               "FMA18255", "FMA18256", "FMA18257",
               "FMA19386", "FMA19387", "FMA19388",
               "FMA9600", "FMA18247"} <= owned
          and excl == {("integumentary", "Skin"),
                       ("integumentary", "Hair"),
                       ("integumentary", "Eyebrow"),
                       ("reproductive", "Testis"),
                       ("reproductive", "Epididymis"),
                       ("reproductive", "Seminal vesicle"),
                       ("reproductive", "Prostate"),
                       ("reproductive", "Glans penis")}
          and not bulb_names and not duct_records,
          "B2 the eight accounted exclusions are real (skin, "
          "hair, eyebrow, testis, epididymis, seminal vesicle, "
          "prostate, glans already owned); no bulbourethral "
          "gland class exists in the OWL and no record was "
          "created from its duct classes",
          f"bulb_classes={bulb_names} duct_records={duct_records}")

    # ---- oculomotor correction ---------------------------------
    occ_sec = accounting["oculomotor_correction"]
    nerv = {r["record_id"]: r
            for r in inventories["nervous"]["records"]}
    ta2sec = json.load(open(os.path.join(
        ROOT, "data", "ta2-name-pass.json")))["fma_inventory"]
    ta2_by_id = {e["record_id"]: e for e in ta2sec["resolved"]}

    obad = []
    pn, lb = owl.get("50864", (None, None))
    if pn != "Oculomotor nerve" or lb != "Oculomotor nerve":
        obad.append(("FMA50864", pn, lb))
    for fid, rname in (("50879", "Right oculomotor nerve"),
                       ("50880", "Left oculomotor nerve")):
        if owl.get(fid, (None, None))[0] != rname:
            obad.append((fid, owl.get(fid)))
    ev = {e["fmaid"]: e for e in occ_sec.get("classes", [])}
    e50864 = ev.get("FMA50864") or {}
    if e50864.get("preferred_name") != "Oculomotor nerve" \
            or e50864.get("label") != "Oculomotor nerve":
        obad.append(("artifact evidence", e50864))
    check(not obad and len(ev) == 3,
          "O1 oculomotor classes carry preferred_name (XML "
          "parse): FMA50864 + the two sided classes",
          f"{obad[:3]}")

    cbad = []
    corr = {c["record_id"]: c
            for c in occ_sec.get("records_corrected", [])}
    for rid in ("nerve.left-oculomotor-nerve",
                "nerve.right-oculomotor-nerve"):
        r = nerv[rid]
        c = corr.get(rid) or {}
        before = c.get("group_path_before") or []
        filled = ["Oculomotor nerve" if x is None else x
                  for x in before]
        if r["class_concept_id"] != "FMA50864" \
                or c.get("class_concept_id_after") != "FMA50864" \
                or c.get("class_concept_id_before") is not None \
                or before.count(None) != 1 \
                or r["group_path"] != filled \
                or c.get("group_path_after") != r["group_path"]:
            cbad.append(rid)
    check(not cbad and len(corr) == 2,
          "O2 oculomotor correction exact (class id + the "
          "single null path slot, nothing else moved)",
          f"{cbad}")

    ibad = []
    for rid in corr:
        r = nerv[rid]
        ident = corr[rid].get("identity_reverified") or {}
        if ident.get("name") != r["name"] \
                or ident.get("concept_ids") != r["concept_ids"] \
                or ident.get("ta_name") != r.get("ta_name") \
                or ident.get("ta_code") != r.get("ta_code") \
                or r.get("ta_code") != 6187 \
                or ta2_by_id[rid]["ta_id"] != 6187 \
                or ta2_by_id[rid]["ta_name"] != r["ta_name"]:
            ibad.append(rid)
    check(not ibad,
          "O3 oculomotor record identity re-verified (FMAIDs, "
          "TA2 outcome 6187 unchanged)", f"{ibad}")

    pbad = [rid for rid, cfid in PLEXUS_AFTER.items()
            if nerv[rid]["class_concept_id"] != cfid
            or None in (nerv[rid]["group_path"] or [])
            or nerv[rid]["group_path"][-1] != nerv[rid]["name"]]
    check(not pbad,
          "O4 the Milestone 37 plexus corrections are still "
          "intact (six records)", f"{pbad}")

    pre_nulls = set()
    for path in sorted(globmod.glob(os.path.join(
            ROOT, "work", "m38", "pre-inventories",
            "*-inventory.json"))):
        pre = json.load(open(path))
        for r in pre["records"]:
            if r.get("source") == SOURCE_TAG and (
                    r.get("class_concept_id") is None
                    or None in (r.get("group_path") or [])):
                pre_nulls.add(r["record_id"])
    now_nulls = set()
    total_fma = 0
    for inv in inventories.values():
        for r in inv["records"]:
            if r.get("source") == SOURCE_TAG:
                total_fma += 1
                if r.get("class_concept_id") is None \
                        or None in (r.get("group_path") or []):
                    now_nulls.add(r["record_id"])
    check(pre_nulls == {"nerve.left-oculomotor-nerve",
                        "nerve.right-oculomotor-nerve"}
          and now_nulls == set() and total_fma == 684,
          "S1 sweep complete by construction: the pre-M38 "
          "snapshots held exactly two artifact carriers; none "
          "survives anywhere (684 FMA records enumerated)",
          f"pre={sorted(pre_nulls)} now={sorted(now_nulls)} "
          f"total={total_fma}")

    print(f"\n{'ALL CHECKS PASS' if not FAILS else 'FAILURES: ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
