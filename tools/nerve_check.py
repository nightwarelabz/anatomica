#!/usr/bin/env python3
"""ANATOMICA Milestone 9 — independent checker for the nervous system
module. Shares no code with tools/nerve_map.py or
tools/build_nerve_records.py: the concept census is re-derived from
the BodyParts3D 4.0 release tables, geometry is re-measured by
streaming the OBJ files, absence probes are re-run over all six
tables, and the clinical file is validated for citation completeness,
flag completeness, tier consistency and geometry-link resolution.

Also gated (Milestone 35): the innervation-link re-pointing — the
muscle module's innervation.nerve_record_ids links are re-derived
here from the rules stated in data/innervation-link-pass.json
(decomposition + exact-correspondence rules R1–R4 against the
FMA-sourced inventory, the OWL re-parsed from the vendored
FMA 5.1.0 package), and the shipped links must equal the
re-derivation exactly.

Exit code 0 only if every hard check passes.
"""

import json
import os
import sys
from collections import Counter, defaultdict

PROJECT = "/home/hatch/workspace/anatomica-project"
SRC = os.path.join(PROJECT, "data/sources/bodyparts3d-4.0")
TS_LABELS = os.path.join(PROJECT,
                         "data/sources/totalsegmentator-1.0/labels.json")
INV = json.load(open(os.path.join(PROJECT,
                                  "data/nervous/nervous-inventory.json")))
GEO = json.load(open(os.path.join(PROJECT,
                                  "data/nervous/nervous-geometry.json")))
CLI = json.load(open(os.path.join(PROJECT,
                                  "data/nervous/nervous.json")))

failures = []
reports = []


def check(ok, label, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}"
          + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def report(label, detail=""):
    print(f"[REPORT] {label}" + (f" — {detail}" if detail else ""))
    reports.append(label)


def load_tsv(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    return [ln.split("\t") for ln in lines[1:] if ln.strip()]


# ------------------------------------------------------------- tables
isa_rows = load_tsv(os.path.join(SRC, "isa_parts_list_e.txt"))
po_rows = load_tsv(os.path.join(SRC, "partof_parts_list_e.txt"))
isa = {r[0]: r[2] for r in isa_rows}
po = {r[0]: r[2] for r in po_rows}
isa_elem = defaultdict(set)
for r in load_tsv(os.path.join(SRC, "isa_element_parts.txt")):
    isa_elem[r[0]].add(r[2])
po_elem = defaultdict(set)
for r in load_tsv(os.path.join(SRC, "partof_element_parts.txt")):
    po_elem[r[0]].add(r[2])
ichild = defaultdict(list)
for r in load_tsv(os.path.join(SRC, "isa_inclusion_relation_list.txt")):
    ichild[r[0]].append(r[2])
pchild = defaultdict(list)
for r in load_tsv(os.path.join(SRC,
                               "partof_inclusion_relation_list.txt")):
    pchild[r[0]].append(r[2])


def desc(root, children):
    seen, stack = set(), [root]
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        stack.extend(children.get(c, []))
    return seen


# ------------------------------------------------- N: census re-derived
neural_tree = desc("FMA11195", ichild)
cranial_line = desc("FMA5865", ichild)
neuraxis_roots = [c for c, n in isa.items() if "neuraxis" in n]
neuraxis_isa = set()
for r in neuraxis_roots:
    neuraxis_isa |= desc(r, ichild)
subdivision = set()
for r in ("FMA45638", "FMA65551", "FMA65539"):
    subdivision |= desc(r, ichild)
dura = set()
for r in ("FMA266054", "FMA71235"):
    dura |= desc(r, ichild)
dura.add("FMA83966")
dura |= desc("FMA83966", ichild)
sweep = set()
for c in ("FMA62493", "FMA72713", "FMA72714", "FMA242193"):
    sweep.add(c)
    sweep |= desc(c, ichild)
isa_universe = (neural_tree | cranial_line | neuraxis_isa |
                subdivision | dura | sweep)
po_universe = desc("FMA7157", pchild) | desc("FMA79876", pchild)
universe = isa_universe | po_universe

meta_u = INV["meta"]["concept_universe"]
check(len(neural_tree) == meta_u["neural_tree_isa"] == 62,
      "N1 neural tree census", f"{len(neural_tree)}")
check(len(cranial_line) == meta_u["cranial_nerve_line_isa"] == 4,
      "N2 cranial nerve line census", f"{len(cranial_line)}")
check(len(neuraxis_isa) == meta_u["neuraxis_isa"] == 170,
      "N3 neuraxis IS-A census", f"{len(neuraxis_isa)}")
check(len(subdivision) == meta_u["subdivision_isa"]
      and len(dura) == meta_u["dura_isa"]
      and len(sweep) == meta_u["sweep_additions_isa"],
      "N4 subdivision/dura/sweep censuses",
      f"{len(subdivision)}/{len(dura)}/{len(sweep)}")
check(len(po_universe) == meta_u["nervous_system_partof"]
      + meta_u["brainstem_partof_extra"] == 91,
      "N5 PART-OF census", f"{len(po_universe)}")
inv_concepts = {c["fma_id"] for c in INV["concepts"]}
check(inv_concepts == universe and len(inv_concepts)
      == meta_u["total"] == 286,
      "N6 concept universe agreement",
      f"inventory {len(inv_concepts)} vs re-derived {len(universe)}")
nerve_named = {c for c, n in isa.items() if "nerve" in n}
check(len(nerve_named) == 55 and nerve_named <= universe,
      "N7 nerve-named concepts (Milestone 4 finding C3 quantified)",
      f"{len(nerve_named)} nerve-named, all inside the universe")
names_ok = all(
    (isa.get(c["fma_id"]) or po.get(c["fma_id"])) == c["name"]
    for c in INV["concepts"])
check(names_ok, "N8 concept names match the release tables")

# ------------------------------------------------- P: record partition
recs = INV["records"]
claimed = [c for r in recs for c in r["concept_ids"]]
check(len(claimed) == len(set(claimed)),
      "P1 no concept claimed by two records", f"{len(claimed)} claims")
check(all(c in universe for r in recs if r.get("source") != "fma-5.1.0"
          for c in r["concept_ids"]),
      "P2 every BP3D record concept is in the universe")
# Milestone 33: FMA-extension records (source == "fma-5.1.0") key on
# FMA 5.1.0 concepts outside the BP3D universe by design; they are
# gated by tools/fma_nerve_check.py. P1 above still spans all
# records, so no concept may be claimed twice across both sources.
check(len({r['record_id'] for r in recs}) == len(recs)
      == INV["meta"]["record_count"],
      "P3 record ids unique and count matches meta",
      f"{len(recs)} records")
by_id = {r["record_id"]: r for r in recs}
conc_rec = {}
for r in recs:
    for c in r["concept_ids"]:
        conc_rec[c] = r["record_id"]
check(all(c["record_id"] == conc_rec.get(c["fma_id"])
          for c in INV["concepts"]),
      "P4 concept rows carry the same record assignment")

# ------------------------------------------------- G: geometry re-measured
def stream_stats(path):
    v = f = 0
    with open(path, "rb") as fh:
        for line in fh:
            if line[:2] == b"v ":
                v += 1
            elif line[:2] == b"f ":
                f += 1
    return v, f


geo_recs = GEO["records"]
check([g["record_id"] for g in geo_recs]
      == [r["record_id"] for r in recs],
      "G1 geometry records align with inventory records")
bad = []
distinct = {"isa": {}, "partof": {}}
for g in geo_recs:
    for tree, key in (("isa", "isa_meshes"), ("partof", "partof_meshes")):
        for m in g[key]:
            p = os.path.join(PROJECT, m["path"])
            if not os.path.exists(p):
                bad.append((g["record_id"], m["path"], "missing"))
                continue
            v, f = stream_stats(p)
            if (v, f) != (m["vertices"], m["faces"]):
                bad.append((g["record_id"], m["path"],
                            f"{v}/{f} != {m['vertices']}/{m['faces']}"))
            distinct[tree][m["fj"]] = (v, f)
check(not bad, "G2 every mesh path exists and re-measures exactly",
      f"{sum(len(g[k]) for g in geo_recs for k in ('isa_meshes', 'partof_meshes'))} mesh entries"
      + (f"; first bad: {bad[:3]}" if bad else ""))
cov = GEO["meta"]["coverage"]
n_with = sum(1 for g in geo_recs if g["isa_meshes"] or g["partof_meshes"])
check(cov["records"] == len(recs)
      and cov["records_with_meshes"] == n_with,
      "G3 coverage statement re-derived",
      f"{n_with}/{len(recs)} records with meshes")
for tree in ("isa", "partof"):
    tv = sum(v for v, _ in distinct[tree].values())
    tf = sum(f for _, f in distinct[tree].values())
    report(f"G4 distinct {tree} mesh files re-measured",
           f"{len(distinct[tree])} files, {tv} vertices, {tf} faces")


# ------------------------------------------------- A: absence probes
table_files = ["isa_parts_list_e.txt", "partof_parts_list_e.txt",
               "isa_element_parts.txt", "partof_element_parts.txt",
               "isa_inclusion_relation_list.txt",
               "partof_inclusion_relation_list.txt"]
texts = {fn: open(os.path.join(SRC, fn), encoding="utf-8",
                  errors="replace").read().lower()
         for fn in table_files}
all_names = set(isa.values()) | set(po.values())
det = INV["meta"]["absences"]["detail"]
probe_bad = []
for d in det:
    total = sum(texts[fn].count(d["probe"]) for fn in table_files)
    if total != d["total_hits"]:
        probe_bad.append((d["probe"], total, d["total_hits"]))
    if (d["probe"] in all_names) != d["exact_concept_exists"]:
        probe_bad.append((d["probe"], "exact-flag mismatch"))
check(not probe_bad, "A1 absence probes re-run over all six tables",
      f"{len(det)} probes, {len(INV['meta']['absences']['absent'])} "
      f"with zero hits"
      + (f"; bad: {probe_bad[:3]}" if probe_bad else ""))

# ------------------------------------------------- T: TotalSegmentator
lab = json.load(open(TS_LABELS))
neural_labels = [k for k in lab["labels"]
                 if any(t in k for t in ("brain", "spinal", "cord",
                                         "nerve", "ganglion"))]
check(neural_labels == ["brain"],
      "T1 TS v1 neural-adjacent labels re-censused",
      f"{neural_labels}")
ts_meta = INV["meta"]["totalsegmentator_overlap"]
check(all(i in by_id for e in ts_meta["labels"]
          for i in e["inventory_record_ids"])
      and ts_meta["labels_without_records"] == [],
      "T2 TS brain label maps to an inventory record")

# ------------------------------------------------- C: clinical tranche
bib = CLI["meta"]["sources"]
crecs = CLI["records"]
check(len({r['id'] for r in crecs}) == len(crecs)
      == CLI["meta"]["record_count"],
      "C1 clinical record ids unique", f"{len(crecs)} records")

FIELDS = {
    "nerve": (["root_values", "branches", "motor_territory",
               "sensory_territory"],
              ["root_values", "motor_territory", "sensory_territory"],
              ["branches"]),
    "cranial_nerve": (["modality", "function", "exit_foramen",
                       "branches"],
                      ["modality", "function", "exit_foramen"],
                      ["branches"]),
    "central_structure": (["function", "connections"], ["function"],
                          ["connections"]),
    "organ": (None, None, None),   # hand-built; fields checked ad hoc
}
cit_bad, flag_bad, tier_bad = [], [], []
for r in crecs:
    if r["ta_name"] is not None:
        # M23 discipline: entered ta_name must cite TA2 (table
        # equality asserted by tools/ta2_discipline.py below)
        if r["sources"].get("ta_name") != ["TA2"]:
            cit_bad.append((r["id"], "ta_name",
                            "TA2 name without TA2 citation"))
    elif not any(v.startswith("ta_name:") for v in r["verify"]):
        flag_bad.append((r["id"], "ta_name"))
    fields, core, soft = FIELDS[r["type"]]
    if fields is None:
        fields = [k for k in r["sources"]]
        core, soft = fields, []
    for f in fields:
        if r.get(f) is not None:
            if f not in r["sources"] or not r["sources"][f]:
                cit_bad.append((r["id"], f, "value without citation"))
            elif any(s not in bib for s in r["sources"][f]):
                cit_bad.append((r["id"], f, "citation not in bibliography"))
        else:
            if not any(v.startswith(f + ":") for v in r["verify"]):
                flag_bad.append((r["id"], f))
    if any(r.get(f) is None for f in core):
        tier = "C"
    elif any(r.get(f) is None for f in soft):
        tier = "B"
    else:
        tier = "A"
    if tier != r["sourcing_tier"]:
        tier_bad.append((r["id"], tier, r["sourcing_tier"]))
check(not cit_bad, "C2 every entered field cites a bibliography source",
      f"bad: {cit_bad[:4]}" if cit_bad else "all cited")
check(not flag_bad, "C3 every null field carries a verify flag",
      f"bad: {flag_bad[:4]}" if flag_bad else "all flagged")
check(not tier_bad, "C4 sourcing tiers recompute exactly",
      f"bad: {tier_bad[:4]}" if tier_bad else
      f"{dict(Counter(r['sourcing_tier'] for r in crecs))}")
link_bad = []
for r in crecs:
    for i in r["geometry_record_ids"]:
        if i not in by_id:
            link_bad.append((r["id"], i))
    if not r["geometry_record_ids"]:
        if not any("no BP3D concept" in v or "no concept" in v
                   or "no geometry" in v for v in r["verify"]) \
                and "no concept" not in (r["note"] or "") \
                and "no BP3D concept" not in (r["note"] or ""):
            link_bad.append((r["id"], "empty link without absence note"))
check(not link_bad, "C5 geometry links resolve; empty links are "
      "explained by a recorded absence",
      f"bad: {link_bad[:4]}" if link_bad else
      f"{sum(1 for r in crecs if r['geometry_record_ids'])} of "
      f"{len(crecs)} records linked")
check(CLI["meta"]["link_failures"] == [],
      "C6 builder reported no link failures")
linked_inv = {i for r in crecs for i in r["geometry_record_ids"]}
report("C7 inventory linkage",
       f"clinical records link {len(linked_inv)} of {len(recs)} "
       f"inventory records; {len(recs) - len(linked_inv)} inventory "
       f"records are inventory-only in v1")

# -------------------------------------- Milestone 35: innervation links
# Independent re-derivation of the re-pointing. The decomposition
# and the R1–R4 exact-correspondence rules are re-implemented here
# from the rule text in data/innervation-link-pass.json; the OWL
# is re-parsed from the vendored FMA 5.1.0 extraction. No code is
# shared with tools/innervation_match.py / innervation_decide.py /
# innervation_pass.py.
import re as _re
import zipfile as _zipfile

mus = json.load(open(os.path.join(PROJECT,
                                  "data/muscular/muscles.json")))
mrecs = mus["records"] if isinstance(mus, dict) else mus
link_art = json.load(open(os.path.join(
    PROJECT, "data/innervation-link-pass.json")))

_owl_path = os.path.join(PROJECT, "work/fma/fma.owl")
if not os.path.exists(_owl_path):
    os.makedirs(os.path.dirname(_owl_path), exist_ok=True)
    with _zipfile.ZipFile(os.path.join(
            PROJECT, "data/sources/fma-5.1.0/fma.zip")) as _zf:
        _zf.extract("fma.owl", os.path.dirname(_owl_path))
_owl = {}
_cur, _buf = None, []
with open(_owl_path, encoding="utf-8", errors="replace") as _fh:
    for _line in _fh:
        _m = _re.search(r'<owl:Class rdf:about='
                        r'"http://purl\.org/sig/ont/fma/fma(\d+)"',
                        _line)
        if _m:
            _cur, _buf = _m.group(1), [_line]
            continue
        if _cur is not None:
            _buf.append(_line)
            if "</owl:Class>" in _line:
                _text = "".join(_buf)
                _nm = _re.search(r"<fma:preferred_name>([^<]+)"
                                 r"</fma:preferred_name>", _text) \
                    or _re.search(r"<rdfs:label[^>]*>([^<]+)"
                                  r"</rdfs:label>", _text)
                _owl[_cur] = {
                    "name": _nm.group(1) if _nm else None,
                    "synonyms": _re.findall(
                        r"<fma:synonym>([^<]+)</fma:synonym>",
                        _text),
                    "parents": _re.findall(
                        r'<rdfs:subClassOf rdf:resource='
                        r'"http://purl\.org/sig/ont/fma/fma(\d+)"/>',
                        _text)}
                _cur, _buf = None, []


def _c8_norm(s):
    s = _re.sub(r"\s+", " ", s.lower().strip())
    s = _re.sub(r"\bthe\b", "", s)
    return _re.sub(r"\s+", " ", s).strip()


def _c8_decompose(phrase):
    comps = []
    for seg in phrase.split(";"):
        seg = seg.strip()
        m = _re.match(r"^[^:()]{1,40}:\s*(.+)$", seg)
        if m:
            seg = m.group(1).strip()
        m = _re.search(r"\(may also receive a branch from the "
                       r"(.+?)\)\s*$", seg)
        if m:
            comps.append((_c8_norm(m.group(1)), "contributory"))
            seg = seg[:m.start()].strip()
        m = _re.search(r",\s*with contributions from the (.+)$",
                       seg)
        if m:
            comps.append((_c8_norm(m.group(1)), "contributory"))
            seg = seg[:m.start()].strip()
        core = _re.sub(r"\s*\(.*?\)\s*$", "", seg)
        m = _re.match(r"^(.+?) component of the (.+)$", core)
        if m:
            comps.append((_c8_norm(m.group(2)), "primary"))
            continue
        seg = core
        im = _re.match(r"^(.+?)\s*\((.*?)\)\s+(nerve|nerves|ramus|"
                       r"rami|plexus|ganglion)$", seg)
        if im:
            seg = f"{im.group(1)} {im.group(3)}"
        m = _re.match(r"^(.+?) and (.+?) (\w+) nerves$", seg)
        if m:
            comps.append((_c8_norm(f"{m.group(1)} {m.group(3)} "
                                    f"nerve"), "primary"))
            comps.append((_c8_norm(f"{m.group(2)} {m.group(3)} "
                                    f"nerve"), "primary"))
            continue
        comps.append((_c8_norm(seg), "primary"))
    return comps


_fma_recs = [r for r in recs if r.get("source") == "fma-5.1.0"]


def _c8_class_fid(r):
    if r.get("class_concept_id"):
        return r["class_concept_id"][3:]
    cid = r["concept_ids"][0][3:]
    if r.get("side"):
        want = _re.sub(r"^(Left|Right) ", "", r["name"])
        for p in _owl.get(cid, {}).get("parents", []):
            if _owl.get(p, {}).get("name") == want:
                return p
    return cid


_by_class, _class_name = {}, {}
for _r in _fma_recs:
    _cf = _c8_class_fid(_r)
    _by_class.setdefault(_cf, []).append(_r["record_id"])
    _class_name[_cf] = _owl.get(_cf, {}).get("name")
for _v in _by_class.values():
    _v.sort()
_by_cname, _by_syn, _by_plural, _children = {}, {}, {}, {}
for _cf, _nm in _class_name.items():
    if _nm:
        _by_cname.setdefault(_c8_norm(_nm), []).append(_cf)
        for _s in _owl.get(_cf, {}).get("synonyms", []):
            _by_syn.setdefault(_c8_norm(_s), []).append(_cf)
for _cid, _info in _owl.items():
    if _info.get("name"):
        _pl = " ".join({"nerve": "nerves", "ramus": "rami"}.get(
            t, t) for t in _info["name"].lower().split(" "))
        _by_plural.setdefault(_pl, []).append(_cid)
    for _p in _info.get("parents", []):
        _children.setdefault(_p, []).append(_cid)
_unsided = {_c8_norm(r["name"]): r["record_id"]
            for r in _fma_recs if not r.get("side")}
_RESTRICT = {"cervical", "thoracic", "lumbar", "sacral", "upper",
            "lower"}


def _c8_resolve(name):
    """-> (status, record_ids): resolved / restricted / absent."""
    hits = []
    if name in _unsided:
        hits.append([_unsided[name]])
    for cf in _by_cname.get(name, []):
        hits.append(_by_class[cf])
    for cf in _by_syn.get(name, []):
        hits.append(_by_class[cf])
    for cid in _by_plural.get(name, []):
        if _by_class.get(cid):
            hits.append(_by_class[cid])
        else:
            lvl = []
            for kid in _children.get(cid, []):
                kn = _owl.get(kid, {}).get("name")
                if kn and kn.lower().endswith(
                        _owl[cid]["name"].lower()):
                    lvl += _by_class.get(kid, [])
            if lvl:
                hits.append(sorted(lvl))
    if hits:
        assert all(h == hits[0] for h in hits), name
        return "resolved", hits[0]
    toks = [t for t in name.split(" ") if t not in _RESTRICT
            and not _re.fullmatch(r"[a-z]\d+-[a-z]\d+|[a-z]\d+", t)]
    stripped = " ".join(toks)
    if stripped != name:
        st, _ = _c8_resolve(stripped)
        if st == "resolved":
            return "restricted", []
    return "absent", []


_c8_phrases = {}
for _p in sorted({r["innervation"]["nerve"] for r in mrecs
                  if r.get("innervation")
                  and r["innervation"].get("nerve")}):
    _comps = []
    _union = set()
    for _nm, _role in _c8_decompose(_p):
        _st, _ids = _c8_resolve(_nm)
        _comps.append((_nm, _role, _st, _ids))
        _union |= set(_ids)
    _c8_phrases[_p] = (_comps, sorted(_union))

# C8a: shipped links equal the re-derivation, record by record
_bad_link = []
for _r in mrecs:
    _inn = _r.get("innervation") or {}
    _phrase = _inn.get("nerve")
    if _phrase:
        if _inn.get("nerve_record_ids") != _c8_phrases[_phrase][1]:
            _bad_link.append(_r["record_id"])
    elif "nerve_record_ids" in _inn:
        _bad_link.append(_r["record_id"])
check(not _bad_link,
      "C8a innervation links: every muscle record's "
      "nerve_record_ids equals the independent R1–R4 "
      "re-derivation for its phrase"
      + (f" — FAILING: {_bad_link}" if _bad_link else ""))

# C8b: the artifact's accounting equals the re-derivation
_art_phrases = {p["phrase"]: p for p in link_art["phrases"]}
_c8_counts = {
    "phrases": len(_c8_phrases),
    "phrases_fully_resolved": sum(
        1 for c, _ in _c8_phrases.values()
        if all(x[2] == "resolved" for x in c)),
    "phrases_partially_resolved": sum(
        1 for c, _ in _c8_phrases.values()
        if any(x[2] == "resolved" for x in c)
        and not all(x[2] == "resolved" for x in c)),
    "phrases_unresolved": sum(
        1 for c, _ in _c8_phrases.values()
        if not any(x[2] == "resolved" for x in c)),
    "components": sum(len(c) for c, _ in _c8_phrases.values()),
    "components_resolved": sum(
        1 for c, _ in _c8_phrases.values() for x in c
        if x[2] == "resolved"),
    "components_restricted": sum(
        1 for c, _ in _c8_phrases.values() for x in c
        if x[2] == "restricted"),
    "components_absent": sum(
        1 for c, _ in _c8_phrases.values() for x in c
        if x[2] == "absent"),
    "distinct_inventory_records_linked": len(
        {i for _, u in _c8_phrases.values() for i in u}),
}
_art_bad = []
if set(_art_phrases) != set(_c8_phrases):
    _art_bad.append("phrase sets differ")
for _p, (_comps, _union) in _c8_phrases.items():
    _ap = _art_phrases.get(_p)
    if _ap is None:
        continue
    if _ap["record_ids"] != _union:
        _art_bad.append(f"{_p}: union")
    _ac = {(c["name"], c["role"]): c for c in _ap["components"]}
    for _nm, _role, _st, _ids in _comps:
        _a = _ac.get((_nm, _role))
        if _a is None or _a["status"] != _st \
                or _a["record_ids"] != _ids:
            _art_bad.append(f"{_p}: {_nm}")
if link_art["after"] != _c8_counts:
    _art_bad.append("after census")
check(not _art_bad,
      "C8b innervation accounting: data/innervation-link-pass.json "
      "components, statuses and census match the re-derivation"
      + (f" — FAILING: {_art_bad[:4]}" if _art_bad else ""))

# C8c: every non-resolved component carries its reason
_reason_bad = [f"{p['phrase']}: {c['name']}"
               for p in link_art["phrases"]
               for c in p["components"]
               if c["status"] != "resolved"
               and not (c.get("reason") or "").strip()]
check(not _reason_bad,
      "C8c every restricted/absent innervation component carries "
      "a specific reason in the artifact"
      + (f" — FAILING: {_reason_bad}" if _reason_bad else ""))

# C8d: clinical continuity — the old full-phrase semantics still
# resolve the same 11 phrases to this module's clinical records
cli_names = {r["name"].lower() for r in crecs}
cli_names |= {r["name"].split(" (")[0].lower() for r in crecs}
resolved_cli = sorted(p for p in _c8_phrases
                      if p.lower() in cli_names)
check(resolved_cli == link_art["before"]["to_clinical"],
      "C8d clinical continuity: the phrases resolving to sourced "
      "clinical records are unchanged (11, as Milestone 33 "
      "recorded)")
report("C8 Milestone 35 innervation re-pointing",
       f"{_c8_counts['phrases']} distinct innervation phrases; "
       f"{_c8_counts['phrases_fully_resolved']} now fully resolve "
       f"to FMA inventory records, "
       f"{_c8_counts['phrases_partially_resolved']} partially, "
       f"{_c8_counts['phrases_unresolved']} not at all "
       f"({_c8_counts['components_resolved']} of "
       f"{_c8_counts['components']} named-nerve components link, "
       f"{_c8_counts['components_restricted']} restricted to a "
       f"subset of a generic class, "
       f"{_c8_counts['components_absent']} with no intaken "
       f"record); {_c8_counts['distinct_inventory_records_linked']}"
       f" distinct inventory records linked. Before Milestone 35, "
       f"2 of the 45 phrases resolved to inventory records under "
       f"full-phrase equality.")

# ------------------------------------------------- TA2 discipline (M23)
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import ta2_discipline as _ta2d
_ta2d.run("nervous", "data/nervous/nervous.json", check)
_ta2d.run_fma_inventory(check)

print()
if failures:
    print(f"FAILED: {len(failures)} hard check(s): {failures}")
    sys.exit(1)
print(f"ALL HARD CHECKS PASS ({len(reports)} reports printed)")
