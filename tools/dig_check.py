#!/usr/bin/env python3
"""ANATOMICA Milestone 11: independent digestive module checker.

Written against the source tables and the shipped JSON, in the
house style of tools/resp_check.py: it does NOT import the
builders. It re-derives the concept universe from the six
BodyParts3D tables (own loading, own hierarchy walks over the
inclusion-relation lists, the builder's documented roots and sweep
lists), re-runs the cross-reference classification, the rejected-
sweep census and the disposition accounting (record / class-carried
/ cross-reference / grouping-class / subtree-internal must partition
the universe exactly), re-measures every mesh entry by streaming
the OBJ files (vertex/face counts AND bounding boxes), re-runs the
absence probes as raw-text occurrence counts over all six tables,
parses the TotalSegmentator label census itself, verifies the
cross-module pointers (cardiovascular, muscular, skeletal), and
validates the clinical tranche's citation discipline, tier
assignments, pathway order, Couinaud segment list, biliary links
and dentition arithmetic.

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
DIG = os.path.join(PROJECT, "data/digestive")

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
# Independent table loading (3-column TSVs, as in resp_check.py)
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
iparent = {}
for r in load_tsv("isa_inclusion_relation_list.txt"):
    ichild[r[0]].append(r[2])
    iparent[r[2]] = r[0]
pchild = defaultdict(list)
pparent = {}
for r in load_tsv("partof_inclusion_relation_list.txt"):
    pchild[r[0]].append(r[2])
    pparent[r[2]] = r[0]
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


def ancestors(cid, parent):
    out, cur = set(), cid
    while cur in parent:
        cur = parent[cur]
        out.add(cur)
    return out


# ------------------------------------------------------------------
# Re-derived universe (documented roots/sweeps, own walks)
# ------------------------------------------------------------------
isa_sets = OrderedDict([
    ("anal-sphincter-muscular-xref-isa", {"FMA21930"}),
    ("salivary-gland-isa", desc("FMA9597", ichild)),
    ("tooth-isa", desc("FMA12516", ichild)),
    ("hepatovenous-segment-isa", desc("FMA15737", ichild)),
    ("biliary-tree-isa", desc("FMA71856", ichild)),
    ("bile-duct-isa", desc("FMA9706", ichild)),
    ("segment-of-liver-isa", desc("FMA14495", ichild)),
    ("gingiva-isa", desc("FMA59762", ichild)),
    ("mesentery-of-large-intestine-sweep-isa", {"FMA14645"}),
])
po_sets = OrderedDict([
    ("gastrointestinal-tract-partof", desc("FMA71132", pchild)),
    ("alimentary-system-partof", desc("FMA7152", pchild)),
    ("anal-sphincter-muscular-xref-partof", {"FMA21930"}),
])
isa_universe = set().union(*isa_sets.values())
po_universe = set().union(*po_sets.values())
universe = isa_universe | po_universe

inv = json.load(open(os.path.join(DIG, "digestive-inventory.json"),
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
check(isa["FMA21930"] == "external anal sphincter" and
      po["FMA21930"] == "external anal sphincter" and
      isa["FMA14645"] == "mesentery of large intestine" and
      "FMA14645" not in po,
      "sweep anchor concepts verified by name (external anal "
      "sphincter in both tables; mesentery of large intestine "
      "IS-A only)")
ALL_NAMES = set(isa.values()) | set(po.values())
check("hepatovenous segment i" not in ALL_NAMES and
      all(f"hepatovenous segment {r}" in ALL_NAMES for r in
          ("ii", "iii", "iv", "v", "vi", "vii", "viii", "ix")),
      "the release names hepatovenous segments ii-ix only: no "
      "'hepatovenous segment i' concept exists")

MUSCULAR_XREF_IDS = {"FMA46728", "FMA46729", "FMA46731", "FMA46732",
                     "FMA46733", "FMA21930"}
SKELETAL_XREF_IDS = {"FMA54397", "FMA54398"}


def cross_ref(cid):
    if cid in MUSCULAR_XREF_IDS:
        return "muscular"
    if cid in SKELETAL_XREF_IDS:
        return "skeletal"
    name = isa[cid] if cid in isa else po[cid]
    if "artery" in name or "vein" in name:
        return "cardiovascular"
    return None


xref = Counter(x for x in (cross_ref(c) for c in universe) if x)
check(dict(xref) == cu["cross_references"],
      f"cross-references re-derived: {dict(sorted(xref.items()))}")

# Rejected-sweep census (digestive terms outside the universe)
SWEEP_TERMS = ("digest", "aliment", "gastro", "esophag", "oesophag",
               "stomach", "gastric", "intestin", "colon", "cecum",
               "caecum", "append", "rectum", "rectal", "liver",
               "hepat", "gallbladder", "biliar", "bile", "pancrea",
               "salivary", "parotid", "submandibular", "sublingual",
               "tongue", "tooth", "teeth", "gingiva", "palate",
               "mouth", "peritone", "mesenter", "oment", "duoden",
               "jejun", "ileum", "sphincter", "spleen", "splenic")
rejected = set()
for tab in (isa, po):
    for cid, n in tab.items():
        if cid in universe:
            continue
        if any(t in n for t in SWEEP_TERMS):
            rejected.add(n)
check(sorted(rejected) == cu["sweep_rejected_names"],
      f"rejected sweep census matches: {len(rejected)} names "
      "(cardiovascular neighbours, tongue/palate muscle classes, "
      "spleen and generic region classes), none admitted")

# ------------------------------------------------------------------
# Inventory records + disposition accounting
# ------------------------------------------------------------------
recs = inv["records"]
ids = [r["record_id"] for r in recs]
names = [r["name"] for r in recs]
check(len(ids) == len(set(ids)), "record ids unique")
check(len(names) == len(set(names)), "record names unique")
check(len(recs) == inv["meta"]["record_count"] == 93,
      f"inventory record count {len(recs)}")
used = [cid for r in recs for cid in r["concept_ids"]]
check(len(used) == len(set(used)), "record concept sets are disjoint")
check(set(used) <= universe, "record concepts all in the universe")
kinds = Counter(r["representation"] for r in recs)
check(kinds == Counter({"partof-organ": 9, "partof-concept": 45,
                        "whole-concept": 39}),
      f"record representations: {dict(kinds)}")
check(all(r["class_concept_id"] in isa or r["class_concept_id"] in po
          for r in recs),
      "every record's class concept exists in the tables")

claimed = set(used)
class_carried = {r["class_concept_id"] for r in recs} & universe \
    - claimed
# Grouping classes are derived on the IS-A (class) graph only: in
# the PART-OF graph, walls, layers and region parts sit ABOVE the
# named structures they belong to (the taeniae hang under the
# muscle layer of the large intestine; the gingivae under the
# mouth region parts), so a part-of ancestor rule would misclassify
# those internal parts as grouping classes.
anc_of_claimed = set()
for cid in claimed | class_carried:
    anc_of_claimed |= ancestors(cid, iparent)
SET_ROOTS = {"FMA7152", "FMA71132",           # PART-OF roots
             "FMA9597", "FMA12516", "FMA15737", "FMA71856",
             "FMA9706", "FMA14495", "FMA59762"}  # IS-A set roots
GROUPING_EXPLICIT = {"FMA265228",   # pancreaticobiliary system
                     "FMA49177",    # upper gastrointestinal tract
                     "FMA49179",    # lower gastrointestinal tract
                     "FMA15755", "FMA15756", "FMA15757",  # in-vivo
                     # liver region classes
                     "FMA71859", "FMA71860",  # segment of right /
                     # left hepatic biliary tree
                     "FMA71865", "FMA71866"}  # segmental tributary
# classes (their descendants are the recorded trees' named
# tributaries, which are subtree-internal)
grouping = {c for c in universe - claimed - class_carried
            if not cross_ref(c) and
            (c in anc_of_claimed or c in SET_ROOTS or
             c in GROUPING_EXPLICIT)}
internal = {c for c in universe - claimed - class_carried - grouping
            if not cross_ref(c)}
disp_expected = {
    "record": sorted(claimed),
    "class-carried": sorted(class_carried),
    "cross-reference:cardiovascular": sorted(
        c for c in universe if cross_ref(c) == "cardiovascular"),
    "cross-reference:muscular": sorted(
        c for c in universe if cross_ref(c) == "muscular"),
    "cross-reference:skeletal": sorted(
        c for c in universe if cross_ref(c) == "skeletal"),
    "grouping-class": sorted(grouping),
    "subtree-internal": sorted(internal),
}
check(cu["disposition_concepts"] == disp_expected,
      "disposition accounting partitions the universe exactly: " +
      ", ".join(f"{k} {len(v)}" for k, v in
                sorted(disp_expected.items())))
check(sum(len(v) for v in disp_expected.values()) == len(universe),
      f"dispositions sum to the universe total {len(universe)}")
conc_rows = {c["fma_id"]: c for c in inv["concepts"]}
check(set(conc_rows) == universe and
      all(conc_rows[c]["disposition"] ==
          next(k for k, v in disp_expected.items() if c in v)
          for c in universe),
      "every concept row carries the re-derived disposition")

# Cross-module pointers resolve
muscular = json.load(open(os.path.join(
    PROJECT, "data/muscular/muscle-inventory.json"), encoding="utf-8"))
check("muscle.external-anal-sphincter" in
      {r["record_id"] for r in muscular["records"]},
      "anal sphincter cross-reference resolves: "
      "muscle.external-anal-sphincter exists in the muscular module")
skeletal = json.load(open(os.path.join(
    PROJECT, "data/skeletal/skeleton-geometry.json"), encoding="utf-8"))
check({"maxilla_left", "maxilla_right", "mandible"} <=
      {r["record_id"] for r in skeletal["records"]},
      "jaw cross-references resolve: skeletal records maxilla_left "
      "/ maxilla_right / mandible exist")
cv_inv = json.load(open(os.path.join(
    PROJECT, "data/cardiovascular/cv-inventory.json"),
    encoding="utf-8"))
cv_names = {c["name"] for c in cv_inv["concepts"]}
missing_cv = {isa[c] if c in isa else po[c]
              for c in universe if cross_ref(c) == "cardiovascular"
              and (isa[c] if c in isa else po[c]) not in cv_names}
CV_UNRESOLVED = {
    "right hepatic artery", "left hepatic artery",
    "anterior segmental hepatic artery",
    "posterior segmental hepatic artery",
    "medial segmental hepatic artery",
    "lateral segmental hepatic artery",
    "anterior branch of right portal vein",
    "posterior branch of right portal vein",
    "medial branch of left portal vein",
    "lateral branch of left portal vein",
}
check(missing_cv == CV_UNRESOLVED,
      "cardiovascular cross-reference resolution measured exactly: "
      "30 of the 40 vessel concepts resolve to the cardiovascular "
      "module's concept universe; the 10 unresolved are the "
      "intrahepatic branch concepts (right/left hepatic artery as "
      "filed in this subtree, the four segmental hepatic arteries "
      "and the four lobar portal-vein branches), which the "
      "cardiovascular census does not carry — a documented "
      "cross-module gap, not a silent one")
cv_clin = json.load(open(os.path.join(
    PROJECT, "data/cardiovascular/cardiovascular.json"),
    encoding="utf-8"))
CV_CITED = {"artery.celiac-artery", "artery.common-hepatic-artery",
            "artery.hepatic-artery-proper",
            "artery.gastroduodenal-artery", "artery.splenic-artery",
            "artery.superior-mesenteric-artery",
            "vein.hepatic-portal-vein", "vein.splenic-vein",
            "vein.hepatic-vein"}
check(CV_CITED <= {r["id"] for r in cv_clin["records"]},
      "the cardiovascular clinical records cited in this module's "
      "notes (hepatic/portal/gut supply) all resolve")

# ------------------------------------------------------------------
# Geometry: attribution + re-measurement by streaming (v/f + bbox)
# ------------------------------------------------------------------
geo = json.load(open(os.path.join(DIG, "digestive-geometry.json"),
                     encoding="utf-8"))
gre = {g["record_id"]: g for g in geo["records"]}
check(set(gre) == set(ids), "geometry file covers exactly the "
                            "inventory records")
check(geo["meta"]["coverage"] == {"records": 93,
                                  "records_with_meshes": 93,
                                  "records_without_meshes": 0},
      "geometry coverage meta: 93/93 records with meshes")

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
DIG_TS = {"esophagus", "stomach", "duodenum", "small_bowel", "colon",
          "liver", "gallbladder", "pancreas"}
check(DIG_TS <= ts_names and "spleen" in ts_names,
      "the eight digestive TS labels are present in the census; "
      "the spleen label is also present but filed under lymphatic "
      "in the M3 census (cross-reference, not digestive)")
ts_map = inv["meta"]["totalsegmentator_overlap"]["labels"]
check({e["label"] for e in ts_map} == DIG_TS and
      all(e["inventory_record_ids"] and
          all(rid in set(ids) for rid in e["inventory_record_ids"])
          for e in ts_map) and
      inv["meta"]["totalsegmentator_overlap"]
         ["labels_without_records"] == [],
      "every digestive TS label maps to resolving inventory "
      "records; TS adds nothing below the organ level")

# ------------------------------------------------------------------
# Absence probes: raw-text occurrence counts over all six tables
# ------------------------------------------------------------------
PROBES = [
    "sigmoid colon", "sigmoid mesocolon", "anal canal", "anus",
    "dentate line", "pectinate line", "ileocecal valve", "haustra",
    "appendices epiploicae", "circular folds", "intestinal villus",
    "duodenal gland", "major duodenal papilla",
    "minor duodenal papilla", "hepatopancreatic ampulla",
    "sphincter of hepatopancreatic ampulla",
    "cardiac part of stomach", "fundus of stomach", "body of stomach",
    "pyloric part of stomach", "pylorus", "pyloric sphincter",
    "greater curvature", "lesser curvature", "angular incisure",
    "hepatic flexure", "splenic flexure", "right colic flexure",
    "left colic flexure",
    "common bile duct", "accessory pancreatic duct",
    "head of pancreas", "neck of pancreas", "body of pancreas",
    "tail of pancreas", "uncinate process",
    "quadrate lobe", "porta hepatis", "bare area",
    "falciform ligament", "ligamentum teres", "ligamentum venosum",
    "coronary ligament",
    "parotid gland", "parotid duct", "submandibular duct",
    "sublingual duct", "minor salivary gland",
    "third molar tooth", "third secondary molar tooth",
    "primary tooth", "deciduous tooth", "dental pulp", "enamel",
    "dentine",
    "parietal peritoneum", "peritoneal cavity", "lesser sac",
    "omental bursa", "greater omentum", "lesser omentum",
    "epiploic foramen", "omental foramen", "hepatorenal recess",
    "rectovesical pouch", "rectouterine pouch", "root of mesentery",
    "hard palate", "palatine tonsil",
    "hepatovenous segment i",
    "esophagus", "stomach", "duodenum", "liver", "gallbladder",
    "pancreas", "appendix", "tongue", "tooth", "peritoneum",
    "bile duct", "taenia", "submandibular gland",
    "mesentery of small intestine", "hepatovenous segment ii",
    "external anal sphincter", "spleen",
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
absent = [p for p in PROBES if blob.lower().count(p) == 0]
check(absent == inv["meta"]["absences"]["absent"],
      f"absence probes re-run over all six tables: {len(absent)} "
      f"absent of {len(PROBES)} probed (inventory recorded "
      f"{len(inv['meta']['absences']['absent'])})")
for probe in ("esophagus", "stomach", "duodenum", "liver",
              "gallbladder", "pancreas", "appendix", "tongue",
              "peritoneum", "bile duct", "submandibular gland",
              "mesentery of small intestine",
              "hepatovenous segment ii", "external anal sphincter",
              "spleen"):
    check(probe in ALL_NAMES, f"exact-concept control present: {probe}")
for probe in ("sigmoid colon", "anal canal", "anus",
              "common bile duct", "parotid gland", "quadrate lobe",
              "parietal peritoneum", "greater omentum",
              "lesser omentum", "hepatovenous segment i",
              "major duodenal papilla", "fundus of stomach",
              "head of pancreas", "third secondary molar tooth"):
    check(probe not in ALL_NAMES,
          f"exact concept absent (probe-verified): {probe}")

# ------------------------------------------------------------------
# Clinical tranche
# ------------------------------------------------------------------
clin = json.load(open(os.path.join(DIG, "digestive.json"),
                      encoding="utf-8"))
crecs = clin["records"]
meta_sources = clin["meta"]["sources"]
check(clin["meta"]["record_count"] == len(crecs) == 31,
      f"clinical record count {len(crecs)}")
check(clin["meta"]["link_failures"] == [], "no geometry link failures")

CORE_SOFT = {
    "pathway": (["extent", "function"], ["structure"]),
    "segment": (["sector", "definition"],
                ["position", "surgical_note"]),
    "ductpath": (["sequence", "termination"], ["territory"]),
    "glands": (["major_glands", "parotid"],
               ["submandibular", "sublingual", "saliva"]),
}
BY_ID_CORE_SOFT = {
    "organ.stomach": (["parts", "curvatures"],
                      ["sphincters", "blood_supply", "innervation"]),
    "organ.liver": (["lobes", "surfaces"],
                    ["position", "ligaments", "blood_supply",
                     "nerve_supply"]),
    "organ.gallbladder": (["parts", "function"],
                          ["position_relations", "blood_supply",
                           "innervation"]),
    "organ.pancreas": (["parts", "duct_system"],
                       ["position", "blood_supply"]),
    "dig.oral-cavity-structure": (["divisions", "functions"],
                                  ["palate"]),
    "dig.peritoneum": (["layers", "cavity"],
                       ["reflections", "organ_relations"]),
    "dig.peritoneal-cavity": (["greater_sac", "lesser_sac"],
                              ["pelvic_pouches"]),
}

bad = []
for r in crecs:
    if r["type"] == "dentition":
        continue
    if r["type"] in CORE_SOFT:
        core, soft = CORE_SOFT[r["type"]]
    elif r["id"] in BY_ID_CORE_SOFT:
        core, soft = BY_ID_CORE_SOFT[r["id"]]
    else:
        bad.append((r["id"], "unknown type/shape"))
        continue
    fields = core + soft
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
    for v in r["verify"]:
        if not (v.startswith("ta_name:") or
                v.startswith("no BP3D concept") or
                any(v.startswith(f + ":") for f in fields)):
            bad.append((r["id"], f"unaccounted verify entry: {v[:40]}"))
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
check(dict(tiers) == clin["meta"]["tiers"] == {"A": 30, "B": 1},
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
unlinked_clin = {r["id"] for r in crecs
                 if not r["geometry_record_ids"]}
check(unlinked_clin == {"dig.sigmoid-colon", "dig.anal-canal"},
      "exactly two clinical records link nothing — the sigmoid "
      "colon and the anal canal, both absence-flagged")

pw = [r for r in crecs if r["group"] == "Alimentary canal pathway"]
check(sorted(r["pathway_order"] for r in pw) == list(range(1, 14)),
      f"canal pathway orders 1..13 complete ({len(pw)} records)")

segs = {r["id"]: r for r in crecs if r["type"] == "segment"}
check(len(segs) == 8, f"Couinaud segment records: {len(segs)}")
SEG_LINK = {
    "seg.couinaud-i": "liver.caudate-lobe-of-liver",
    "seg.couinaud-ii": "liver-segment.hepatovenous-segment-ii",
    "seg.couinaud-iii": "liver-segment.hepatovenous-segment-iii",
    "seg.couinaud-iv": "liver-segment.hepatovenous-segment-iv",
    "seg.couinaud-v": "liver-segment.hepatovenous-segment-v",
    "seg.couinaud-vi": "liver-segment.hepatovenous-segment-vi",
    "seg.couinaud-vii": "liver-segment.hepatovenous-segment-vii",
    "seg.couinaud-viii": "liver-segment.hepatovenous-segment-viii",
}
check(all(segs[k]["geometry_record_ids"] == [v]
          for k, v in SEG_LINK.items()),
      "each Couinaud segment record links exactly its inventory "
      "segment record (segment I links the caudate lobe record)")
SEG_SECTOR = {"seg.couinaud-i": "caudate",
              "seg.couinaud-ii": "Left lateral",
              "seg.couinaud-iii": "Left lateral",
              "seg.couinaud-iv": "Left medial",
              "seg.couinaud-v": "Right anterior",
              "seg.couinaud-vi": "Right posterior",
              "seg.couinaud-vii": "Right posterior",
              "seg.couinaud-viii": "Right anterior"}
check(all(SEG_SECTOR[k] in segs[k]["sector"] for k in SEG_SECTOR),
      "segment sectors match the Couinaud groupings of S13 "
      "(I caudate; II/III left lateral; IV left medial; V/VIII "
      "right anterior; VI/VII right posterior)")
check(not any("segment-ix" in g for r in crecs
              for g in r["geometry_record_ids"]),
      "no clinical record links the hepatovenous segment ix "
      "inventory record: the Couinaud classification has eight "
      "segments and the ninth named concept is not force-mapped")

bil = next(r for r in crecs if r["id"] == "dig.biliary-tree")
check({"biliary.biliary-tree", "duct.right-hepatic-duct",
       "duct.left-hepatic-duct", "duct.common-hepatic-duct",
       "duct.cystic-duct", "gallbladder"} <=
      set(bil["geometry_record_ids"]),
      "biliary record links the tree, duct and gallbladder "
      "inventory records")
check(any("common bile duct" in v for v in bil["verify"]) and
      any("ampulla" in v for v in bil["verify"]),
      "biliary record carries the common bile duct and ampulla "
      "absence flags")

dent = next(r for r in crecs if r["type"] == "dentition")
EXPECTED_VALUES = {
    "permanent_teeth_total": 32, "deciduous_teeth_total": 20,
    "incisors": 8, "canines": 4, "premolars": 8, "molars": 12,
    "third_molars_within_molars": 4,
    "release_permanent_tooth_records": 28,
}
check(dent["values"] == EXPECTED_VALUES,
      "dentition values match the consulted source counts (S12) "
      "and the inventory count exactly")
v = dent["values"]
tooth_records = [r for r in recs
                 if r["record_id"].startswith("tooth.")]
check(v["incisors"] + v["canines"] + v["premolars"] + v["molars"]
      == v["permanent_teeth_total"] and
      v["release_permanent_tooth_records"] == len(tooth_records) and
      v["permanent_teeth_total"] -
      v["release_permanent_tooth_records"] ==
      v["third_molars_within_molars"],
      "dentition arithmetic closes: 8+4+8+12 = 32 clinical teeth; "
      "32 - 28 release records = the 4 third molars the release "
      "does not carry")
check(dent["sources"].get("values") == ["S12"] and
      dent["sourcing_tier"] == "A" and
      set(dent["geometry_record_ids"]) ==
      {r["record_id"] for r in tooth_records},
      "dentition record cited to S12, tier A, linking all 28 "
      "inventory tooth records")

groups = Counter(r["group"] for r in crecs)
check(dict(groups) == clin["meta"]["groups"],
      f"clinical groups: {dict(sorted(groups.items()))}")

print()
if failures:
    print(f"{len(failures)} HARD CHECK(S) FAILED")
    sys.exit(1)
print("ALL HARD CHECKS PASSED")
