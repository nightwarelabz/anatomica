#!/usr/bin/env python3
"""ANATOMICA Milestone 10: independent respiratory module checker.

Written against the source tables and the shipped JSON, in the
house style of tools/nerve_check.py: it does NOT import the
builders. It re-derives the concept universe from the six
BodyParts3D tables (own loading, own hierarchy walks over the
inclusion-relation lists, the builder's documented roots and sweep
lists), re-runs the cross-reference classification and the
rejected-sweep census, re-measures every mesh entry by streaming
the OBJ files (vertex/face counts AND bounding boxes), re-runs the
absence probes as raw-text occurrence counts over all six tables,
parses the TotalSegmentator label census itself, and validates the
clinical tranche's citation discipline, tier assignments, pathway
order, segment list and geometry links.

Exit code 0 only if every hard check passes. Printed lines marked
[report] are informational.
"""

import json
import os
import sys
from collections import Counter, OrderedDict, defaultdict

PROJECT = "/home/hatch/workspace/anatomica-project"
SRC = os.path.join(PROJECT, "data/sources/bodyparts3d-4.0")
TS_LABELS = os.path.join(PROJECT,
                         "data/sources/totalsegmentator-1.0/labels.json")
RESP = os.path.join(PROJECT, "data/respiratory")

failures = []
notes = []


def check(ok, label):
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        failures.append(label)


def report(label):
    print("[report] " + label)
    notes.append(label)


# ------------------------------------------------------------------
# Independent table loading (3-column TSVs, as in nerve_check.py)
# ------------------------------------------------------------------
def load_tsv(name):
    with open(os.path.join(SRC, name), encoding="utf-8",
              errors="replace") as fh:
        lines = fh.read().splitlines()
    return [ln.split("\t") for ln in lines[1:] if ln.strip()]


isa = {r[0]: r[2] for r in load_tsv("isa_parts_list_e.txt")}
po = {r[0]: r[2] for r in load_tsv("partof_parts_list_e.txt")}
isa_elem = defaultdict(set)
for r in load_tsv("isa_element_parts.txt"):
    isa_elem[r[0]].add(r[2])
po_elem = defaultdict(set)
for r in load_tsv("partof_element_parts.txt"):
    po_elem[r[0]].add(r[2])
ichild = defaultdict(list)
for r in load_tsv("isa_inclusion_relation_list.txt"):
    ichild[r[0]].append(r[2])
pchild = defaultdict(list)
for r in load_tsv("partof_inclusion_relation_list.txt"):
    pchild[r[0]].append(r[2])
print(f"tables: IS-A names {len(isa)}, PART-OF names {len(po)}, "
      f"IS-A element rows {sum(len(v) for v in isa_elem.values())}, "
      f"PART-OF element rows {sum(len(v) for v in po_elem.values())}")


def desc(root, children):
    seen, stack = set(), [root]
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        stack.extend(children.get(c, []))
    return seen


# ------------------------------------------------------------------
# Re-derived universe (documented roots/sweeps, own walks)
# ------------------------------------------------------------------
tracheobronchial = desc("FMA12224", ichild)
larynx_cartilage = desc("FMA55108", ichild)
larynx_ligament = set()
for r_ in ("FMA55131", "FMA55244", "FMA55233"):
    larynx_ligament |= desc(r_, ichild)
thyrohyoid = {"FMA55132", "FMA55134", "FMA55133", "FMA55135",
              "FMA55138", "FMA55139", "FMA55140", "FMA55141"}
conus = desc("FMA55250", ichild)
pharynx_subdiv = desc("FMA54877", ichild)
raphe = {"FMA55077"}
larynx_muscle_x = (desc("FMA46562", ichild) | desc("FMA46602", ichild)
                   | desc("FMA46608", ichild))
pharynx_muscle_x = desc("FMA46619", ichild)
nasal_cartilage = desc("FMA59502", ichild)
concha_x = {"FMA54736", "FMA54737", "FMA54738"}
diaphragm_x = {"FMA13295"}

isa_sets = OrderedDict([
    ("tracheobronchial-isa", tracheobronchial),
    ("larynx-cartilage-isa", larynx_cartilage),
    ("larynx-ligament-isa", larynx_ligament),
    ("thyrohyoid-isa", thyrohyoid),
    ("conus-elasticus-isa", conus),
    ("pharynx-subdivision-isa", pharynx_subdiv),
    ("pharynx-raphe-isa", raphe),
    ("larynx-muscle-xref-isa", larynx_muscle_x),
    ("pharynx-muscle-xref-isa", pharynx_muscle_x),
    ("nasal-cartilage-isa", nasal_cartilage),
    ("concha-skeletal-xref-isa", concha_x),
    ("diaphragm-muscular-xref-isa", diaphragm_x),
])
rs_po = desc("FMA7158", pchild)
left_lung_po = desc("FMA7310", pchild)
nose_po = desc("FMA46472", pchild)
compartments_po = {"FMA85055", "FMA85056"}
airway_po = {"FMA7395"}
po_sets = OrderedDict([
    ("respiratory-system-partof", rs_po),
    ("left-lung-partof", left_lung_po),
    ("nose-partof", nose_po),
    ("pulmopleural-compartment-partof", compartments_po),
    ("airway-partof-sweep", airway_po),
])
isa_universe = set().union(*isa_sets.values())
po_universe = set().union(*po_sets.values())
universe = isa_universe | po_universe

inv = json.load(open(os.path.join(RESP, "respiratory-inventory.json"),
                     encoding="utf-8"))
cu = inv["meta"]["concept_universe"]
for tag, s in isa_sets.items():
    check(cu["isa_sets"].get(tag) == len(s),
          f"IS-A set {tag}: {len(s)} concepts")
for tag, s in po_sets.items():
    check(cu["partof_sets"].get(tag) == len(s),
          f"PART-OF set {tag}: {len(s)} concepts")
check(cu["isa_total"] == len(isa_universe) and
      cu["partof_total"] == len(po_universe) and
      cu["in_both_tables"] == len(isa_universe & po_universe) and
      cu["total"] == len(universe),
      f"universe totals: {len(universe)} concepts (IS-A "
      f"{len(isa_universe)}, PART-OF {len(po_universe)}, both "
      f"{len(isa_universe & po_universe)})")
check({isa[c] for c in concha_x} ==
      {"inferior nasal concha", "right inferior nasal concha",
       "left inferior nasal concha"},
      "concha cross-reference concepts preserved as released "
      "(inferior conchae only)")
check(isa["FMA13295"] == "diaphragm" and po["FMA7395"] ==
      "right main bronchus",
      "sweep/diaphragm anchor concepts verified by name")

# Cross-reference classification (first-tag wins, builder's rule)
subtree_of = {}
for tag, s in list(isa_sets.items()) + list(po_sets.items()):
    for cid in s:
        subtree_of.setdefault(cid, tag)


def cross_ref(cid):
    tag = subtree_of[cid]
    name = isa[cid] if cid in isa else po[cid]
    if "muscle-xref" in tag or tag == "diaphragm-muscular-xref-isa":
        return "muscular"
    if tag == "concha-skeletal-xref-isa":
        return "skeletal"
    if "artery" in name or "vein" in name:
        return "cardiovascular"
    if tag == "pulmopleural-compartment-partof":
        return "compartment (not a record in any module)"
    return None


xref = Counter(x for x in (cross_ref(c) for c in universe) if x)
check(dict(xref) == cu["cross_references"],
      f"cross-references re-derived: {dict(sorted(xref.items()))}")

# Rejected-sweep census (respiratory terms outside the universe)
SWEEP_TERMS = ("lung", "bronch", "trachea", "laryng", "pharyng",
               "pleura", "nasal", "nose", "alveol", "diaphragm",
               "concha", "glott", "epiglott", "vocal", "raphe",
               "respiratory", "sinus", "pulmon")
SWEEP_EXCLUDE = ("ventricle of heart", "papillary muscle",
                 "superior parietal lobule",
                 "inferior parietal lobule")
rejected = set()
for tab in (isa, po):
    for cid, n in tab.items():
        if cid in universe:
            continue
        if any(t in n for t in SWEEP_TERMS) and \
                not any(x in n for x in SWEEP_EXCLUDE):
            rejected.add(n)
check(sorted(rejected) == cu["sweep_rejected_names"],
      f"rejected sweep census matches: {len(rejected)} names, all "
      "cardiovascular / skeletal-nose / raphe neighbours, none "
      "admitted")

# ------------------------------------------------------------------
# Inventory records
# ------------------------------------------------------------------
recs = inv["records"]
ids = [r["record_id"] for r in recs]
names = [r["name"] for r in recs]
check(len(ids) == len(set(ids)), "record ids unique")
check(len(names) == len(set(names)), "record names unique")
check(len(recs) == inv["meta"]["record_count"] == 83,
      f"inventory record count {len(recs)}")
used = [cid for r in recs for cid in r["concept_ids"]]
check(len(used) == len(set(used)), "record concept sets are disjoint")
check(set(used) <= universe, "record concepts all in the universe")
kinds = Counter(r["representation"] for r in recs)
check(kinds == Counter({"whole-concept": 51, "partof-organ": 3,
                        "partof-concept": 29}),
      f"record representations: {dict(kinds)}")
check(all(r["class_concept_id"] in isa or r["class_concept_id"] in po
          for r in recs),
      "every record's class concept exists in the tables")
accounted = set(used) | {r["class_concept_id"] for r in recs} & universe
unrecorded = universe - accounted
internals = (rs_po | left_lung_po | nose_po | larynx_muscle_x |
             pharynx_muscle_x | compartments_po)
anchors = concha_x | diaphragm_x
grouping = {c for c in unrecorded
            if desc(c, ichild) & accounted}
check(unrecorded <= internals | anchors | grouping,
      f"unrecorded concepts all accounted: {len(unrecorded)} of "
      f"{len(universe)}")
report(f"unrecorded universe concepts: {len(unrecorded)} = "
       f"{len(unrecorded & internals)} organ-subtree internals / "
       f"muscle cross-reference lines / compartment concepts, "
       f"{len(unrecorded & anchors)} cross-module anchors whose "
       f"records live in the muscular/skeletal modules (diaphragm, "
       f"inferior nasal conchae), {len(unrecorded & grouping)} "
       f"grouping class concepts (subtree roots and intermediate "
       f"classes whose descendants are recorded)")

# Cross-module pointers resolve
muscular = json.load(open(os.path.join(
    PROJECT, "data/muscular/muscle-inventory.json"), encoding="utf-8"))
check("muscle.diaphragm" in {r["record_id"] for r in muscular["records"]},
      "diaphragm cross-reference resolves: muscle.diaphragm exists "
      "in the muscular module")
skeletal = json.load(open(os.path.join(
    PROJECT, "data/skeletal/skeleton-geometry.json"), encoding="utf-8"))
check({"concha_left", "concha_right"} <=
      {r["record_id"] for r in skeletal["records"]},
      "concha cross-reference resolves: skeletal records "
      "concha_left / concha_right exist")
cv = json.load(open(os.path.join(
    PROJECT, "data/cardiovascular/cv-inventory.json"),
    encoding="utf-8"))
check({"segmental pulmonary artery", "segmental pulmonary vein"} <=
      {c["name"] for c in cv["concepts"]},
      "lung-subtree vessel concepts resolve to the cardiovascular "
      "module's concept universe (segmental pulmonary artery/vein)")

# ------------------------------------------------------------------
# Geometry: attribution + re-measurement by streaming (v/f + bbox)
# ------------------------------------------------------------------
geo = json.load(open(os.path.join(RESP, "respiratory-geometry.json"),
                     encoding="utf-8"))
gre = {g["record_id"]: g for g in geo["records"]}
check(set(gre) == set(ids), "geometry file covers exactly the "
                            "inventory records")
check(geo["meta"]["coverage"] == {"records": 83,
                                  "records_with_meshes": 83,
                                  "records_without_meshes": 0},
      "geometry coverage meta: 83/83 records with meshes")

mismatch = 0
checked_entries = 0
distinct = {"isa": {}, "partof": {}}
for r in recs:
    g = gre[r["record_id"]]
    for table, elem, meshes in (("isa", isa_elem, g["isa_meshes"]),
                                ("partof", po_elem, g["partof_meshes"])):
        want = set()
        for cid in r["concept_ids"]:
            want |= elem.get(cid, set())
        got = {m["fj"] for m in meshes}
        if want != got:
            mismatch += 1
        tot_v = tot_f = 0
        for m in meshes:
            path = os.path.join(PROJECT, m["path"])
            v = f = 0
            mins = [float("inf")] * 3
            maxs = [float("-inf")] * 3
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.startswith("v "):
                        v += 1
                        p = line.split()
                        for i in range(3):
                            x = float(p[i + 1])
                            if x < mins[i]:
                                mins[i] = x
                            if x > maxs[i]:
                                maxs[i] = x
                    elif line.startswith("f "):
                        f += 1
            checked_entries += 1
            if v != m["vertices"] or f != m["faces"]:
                mismatch += 1
            bb = m["bbox"]
            if any(abs(mins[i] - bb["min"][i]) > 0.01 or
                   abs(maxs[i] - bb["max"][i]) > 0.01 for i in range(3)):
                mismatch += 1
            tot_v += v
            tot_f += f
            distinct[table][m["fj"]] = (v, f)
        t = g["totals"][table]
        if (t["files"], t["vertices"], t["faces"]) != \
                (len(meshes), tot_v, tot_f):
            mismatch += 1
check(mismatch == 0,
      f"geometry verified: {checked_entries} mesh entries "
      f"re-measured by streaming (counts + bounding boxes), fj "
      f"attribution exact per record and table, 0 mismatches")
for table in ("isa", "partof"):
    dv = sum(v for v, _f in distinct[table].values())
    df = sum(f for _v, f in distinct[table].values())
    report(f"distinct {table} mesh files: {len(distinct[table])} "
           f"({dv:,} v / {df:,} f)")

# ------------------------------------------------------------------
# TotalSegmentator overlap
# ------------------------------------------------------------------
ts = json.load(open(TS_LABELS, encoding="utf-8"))
ts_names = set(ts["labels"])
check(ts["distinct_labels"] == 104 and len(ts_names) == 104,
      "TS label census parsed: 104 labels")
RESP_TS = {"trachea", "lung_upper_lobe_left", "lung_lower_lobe_left",
           "lung_upper_lobe_right", "lung_middle_lobe_right",
           "lung_lower_lobe_right"}
resp_ts = {n for n in ts_names if n == "trachea" or
           n.startswith("lung_")}
check(resp_ts == RESP_TS,
      f"respiratory TS labels identified by name pattern: "
      f"{len(resp_ts)}")
ts_map = inv["meta"]["totalsegmentator_overlap"]["labels"]
check({e["label"] for e in ts_map} == RESP_TS and
      all(e["inventory_record_ids"] and
          all(rid in set(ids) for rid in e["inventory_record_ids"])
          for e in ts_map),
      "every respiratory TS label maps to resolving inventory "
      "records; TS adds nothing below lobe level")

# ------------------------------------------------------------------
# Absence probes: raw-text occurrence counts over all six tables
# ------------------------------------------------------------------
PROBES = [
    "pharynx", "larynx", "nasopharynx", "oropharynx",
    "laryngopharynx", "nasal cavity", "choana", "pleura",
    "visceral pleura", "parietal pleura", "pleural cavity",
    "costal pleura", "mediastinal pleura", "diaphragmatic pleura",
    "cervical pleura", "costodiaphragmatic recess",
    "costomediastinal recess", "pleural recess",
    "paranasal sinus", "frontal sinus", "maxillary sinus",
    "sphenoidal sinus", "sphenoid sinus", "ethmoid sinus",
    "ethmoidal sinus", "ethmoidal air cell", "auditory tube",
    "pharyngotympanic tube", "eustachian tube", "nasolacrimal duct",
    "semilunar hiatus", "ethmoidal bulla", "uncinate process",
    "agger nasi", "sphenopalatine foramen",
    "superior nasal concha", "middle nasal concha",
    "supreme nasal concha", "nasal meatus", "superior nasal meatus",
    "middle nasal meatus", "inferior nasal meatus",
    "sphenoethmoidal recess", "common nasal meatus",
    "oblique fissure", "horizontal fissure", "fissure of lung",
    "hilum of lung", "root of lung", "cardiac notch", "lingula",
    "apex of lung", "base of lung", "costal surface of lung",
    "mediastinal surface of lung", "pulmonary lobule",
    "interlobular septum", "acinus",
    "lobar bronchus", "secondary bronchus", "tertiary bronchus",
    "segmental bronchus", "subsegmental bronchus",
    "bronchus intermedius", "upper lobe bronchus",
    "middle lobe bronchus", "lower lobe bronchus",
    "lingular bronchus", "eparterial bronchus",
    "bronchiole", "respiratory bronchiole", "terminal bronchiole",
    "conducting bronchiole", "alveolar duct", "alveolar sac",
    "pulmonary alveolus", "alveolus", "respiratory membrane",
    "carina", "carina of trachea", "bifurcation of trachea",
    "tracheal cartilage", "tracheal ring", "trachealis",
    "trachealis muscle",
    "vocal fold", "vestibular fold", "vocal cord", "true vocal cord",
    "false vocal cord", "glottis", "rima glottidis",
    "laryngeal ventricle", "laryngeal cavity", "laryngeal inlet",
    "vestibule of larynx", "infraglottic cavity", "piriform recess",
    "piriform fossa", "vallecula", "aryepiglottic fold",
    "cricothyroid membrane", "quadrangular membrane",
    "conus elasticus", "thyrohyoid membrane",
    "sesamoid cartilage", "triticeal cartilage",
    "epiglottic cartilage",
    "trachea", "main bronchus", "bronchopulmonary segment",
    "arytenoid cartilage", "nasal septum", "diaphragm",
]
TABLE_FILES = ["isa_parts_list_e.txt", "partof_parts_list_e.txt",
               "isa_element_parts.txt", "partof_element_parts.txt",
               "isa_inclusion_relation_list.txt",
               "partof_inclusion_relation_list.txt"]
blob = ""
for fn in TABLE_FILES:
    with open(os.path.join(SRC, fn), encoding="utf-8",
              errors="replace") as fh:
        blob += fh.read()
absent = [p for p in PROBES if blob.count(p) == 0]
check(absent == inv["meta"]["absences"]["absent"],
      f"absence probes re-run over all six tables: {len(absent)} "
      f"absent of {len(PROBES)} probed (inventory recorded "
      f"{len(inv['meta']['absences']['absent'])})")
ALL_NAMES = set(isa.values()) | set(po.values())
for probe in ("conus elasticus", "thyrohyoid membrane", "trachea",
              "main bronchus", "arytenoid cartilage", "nasal septum",
              "diaphragm"):
    check(probe in ALL_NAMES, f"exact-concept control present: {probe}")
check("bronchopulmonary segment" not in ALL_NAMES,
      "no un-sided 'bronchopulmonary segment' concept: segments "
      "exist only as named lateralised instances (21 records)")
for probe in ("pleura", "nasal cavity", "pharynx", "larynx",
              "lobar bronchus", "bronchiole", "alveolus",
              "vocal fold", "carina"):
    check(probe not in ALL_NAMES,
          f"exact concept absent (probe-verified): {probe}")

# ------------------------------------------------------------------
# Clinical tranche
# ------------------------------------------------------------------
clin = json.load(open(os.path.join(RESP, "respiratory.json"),
                      encoding="utf-8"))
crecs = clin["records"]
meta_sources = clin["meta"]["sources"]
check(clin["meta"]["record_count"] == len(crecs) == 37,
      f"clinical record count {len(crecs)}")
check(clin["meta"]["link_failures"] == [], "no geometry link failures")

CORE_SOFT = {
    "pathway": (["extent", "function"], ["structure"]),
    "segment": (["lobe", "definition"], ["surgical_note"]),
    "membrane": (["layers", "cavity_and_fluid"],
                 ["parietal_parts", "recesses", "innervation_supply"]),
}
ORGAN_CORE_SOFT = {
    "resp.right-lung": (["lobes", "fissures"],
                        ["root_hilum", "relations", "blood_supply",
                         "nerve_supply"]),
    "resp.left-lung": (["lobes", "fissures"],
                       ["root_hilum", "relations", "blood_supply",
                        "nerve_supply"]),
    "resp.larynx": (["position", "functions", "cartilages"],
                    ["cavity_divisions", "innervation",
                     "blood_supply"]),
}
REGION_CORE_SOFT = {
    "resp.nasal-cavity-organ": (["divisions", "functions"],
                                ["conchae_meatuses", "openings",
                                 "blood_supply", "innervation"]),
    "resp.pharynx": (["extent", "parts"],
                     ["muscles", "innervation", "blood_supply"]),
}
ALL_FIELDS = {
    "pathway": ["extent", "structure", "function"],
    "segment": ["lobe", "definition", "surgical_note"],
    "membrane": ["layers", "parietal_parts", "cavity_and_fluid",
                 "recesses", "innervation_supply"],
}

bad = []
for r in crecs:
    if r["type"] == "values":
        continue
    if r["type"] in CORE_SOFT:
        core, soft = CORE_SOFT[r["type"]]
        fields = ALL_FIELDS[r["type"]]
    elif r["id"] in ORGAN_CORE_SOFT:
        core, soft = ORGAN_CORE_SOFT[r["id"]]
        fields = core + soft
    elif r["id"] in REGION_CORE_SOFT:
        core, soft = REGION_CORE_SOFT[r["id"]]
        fields = core + soft
    else:
        bad.append((r["id"], "unknown type/shape"))
        continue
    if r["ta_name"] is not None:
        bad.append((r["id"], "ta_name not null"))
    if not any(v.startswith("ta_name:") for v in r["verify"]):
        bad.append((r["id"], "ta_name verify flag missing"))
    for f in fields:
        if r[f] is None:
            if not any(v.startswith(f + ":") for v in r["verify"]):
                bad.append((r["id"], f"null field {f} unflagged"))
        else:
            if f not in r["sources"]:
                bad.append((r["id"], f"field {f} uncited"))
            else:
                for s in r["sources"][f]:
                    if s not in meta_sources:
                        bad.append((r["id"], f"unknown source {s}"))
    if not r["geometry_record_ids"] and not any(
            v.startswith("no BP3D concept") for v in r["verify"]):
        bad.append((r["id"], "empty links without recorded absence"))
    tier = ("C" if any(r[f] is None for f in core)
            else "B" if any(r[f] is None for f in soft) else "A")
    if tier != r["sourcing_tier"]:
        bad.append((r["id"], f"tier {r['sourcing_tier']} != {tier}"))
check(not bad, f"clinical citation/flag/tier discipline holds for "
               f"all records (violations: {bad[:6]})")
tiers = Counter(r["sourcing_tier"] for r in crecs)
check(dict(tiers) == clin["meta"]["tiers"],
      f"clinical tiers: {dict(sorted(tiers.items()))}")

inv_ids = set(ids)
bad_links = [(r["id"], g) for r in crecs
             for g in r["geometry_record_ids"] if g not in inv_ids]
check(not bad_links, "all clinical geometry links resolve to "
                     "inventory records")
linked_inv = {g for r in crecs for g in r["geometry_record_ids"]}
report(f"clinical records linking >=1 inventory record: "
       f"{sum(1 for r in crecs if r['geometry_record_ids'])}/"
       f"{len(crecs)}; inventory records linked: {len(linked_inv)}/"
       f"{len(recs)}; unlinked: "
       f"{sorted(set(ids) - linked_inv)}")

pw = [r for r in crecs if r["group"] == "Airway pathway"]
check(sorted(r["pathway_order"] for r in pw) == list(range(1, 14)),
      f"airway pathway orders 1..13 complete ({len(pw)} records)")
zones = {r["pathway_order"]: r["zone"] for r in pw}
check(all(zones[o] == "conducting" for o in range(1, 11)) and
      all(zones[o] == "respiratory" for o in (11, 12, 13)),
      "conducting zone orders 1-10, respiratory zone 11-13")

segs = [r for r in crecs if r["type"] == "segment"]
check(len(segs) == 18, f"bronchopulmonary segment records: {len(segs)}")
check(len([r for r in segs if "right" in r["id"]]) == 10 and
      len([r for r in segs if "left" in r["id"]]) == 8,
      "segments split right 10 / left 8 (Jackson & Huber list, S4)")
check(all(len(r["geometry_record_ids"]) >= 2 for r in segs),
      "every segment record links its segment concept record and "
      "its segmental bronchial tree record")
ap = next(r for r in segs if r["id"] == "segment.left-apicoposterior")
check(len(ap["geometry_record_ids"]) == 5,
      "left apico-posterior segment links 5 inventory records "
      "(merged segment + both constituents + both trees)")
amb = next(r for r in segs if r["id"] == "segment.left-anteromedial-basal")
check(len(amb["geometry_record_ids"]) == 4,
      "left anteromedial basal segment links 4 inventory records "
      "(both constituents + both trees)")

mech = next(r for r in crecs if r["type"] == "values")
EXPECTED = {
    "tidal_volume_ml": 500, "inspiratory_reserve_volume_ml": 3000,
    "expiratory_reserve_volume_ml": 1300, "residual_volume_ml": 1200,
    "functional_residual_capacity_ml": 2500,
    "vital_capacity_ml": 5000, "total_lung_capacity_ml": 6000,
    "minimal_volume_ml": 500, "anatomical_dead_space_ml": 150,
    "respiratory_rate_breaths_per_min": "12-15",
    "minute_respiratory_volume_ml_per_min": "6000-7500",
    "alveolar_ventilation_ml_per_min": 5250,
    "fev1_percent_of_vital_capacity": "about 80",
}
check(mech["values"] == EXPECTED,
      "mechanics values match the consulted source table exactly "
      "(S8; transcribed as printed — the source's own approximates, "
      "not arithmetically forced)")
check(mech["sources"].get("values") == ["S8"] and
      mech["sourcing_tier"] == "A",
      "mechanics values cited to S8, tier A")

groups = Counter(r["group"] for r in crecs)
check(dict(groups) == clin["meta"]["groups"],
      f"clinical groups: {dict(sorted(groups.items()))}")

print()
if failures:
    print(f"{len(failures)} HARD CHECK(S) FAILED")
    sys.exit(1)
print("ALL HARD CHECKS PASSED")
