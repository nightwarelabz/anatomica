#!/usr/bin/env python3
"""ANATOMICA lymphatic + endocrine FMA extension builder — Milestone 36.

Extends the lymphatic and endocrine inventories with concept records
sourced from the Foundational Model of Anatomy (FMA) 5.1.0, for the
structures Milestone 13 proved absent from BodyParts3D 4.0 (its
52-probe gap analyses: the entire lymphatic conducting system,
every named node group, the tonsils and MALT, bone marrow, the
spleen/thymus interiors; the thyroid and parathyroid glands entire,
the endocrine pancreas, the paraganglia).

Sibling of tools/fma_nerve_map.py (Milestone 33), same discipline:

  - License: the FMA 5.1.0 release package ships the full text of
    CC BY 4.0 as its LICENSE file (data/sources/fma-5.1.0/,
    hash-pinned in that directory's provenance ledger at
    Milestone 33). The FMA is an ontology: it carries NO geometry.
    Every record written here is marked geometry-absent; no mesh,
    coordinate or clinical value is created by this tool.
  - A frozen target list per system (below) names the absent
    structures. Each target is resolved mechanically against
    fma.owl: lateralised records (left/right) where the FMA
    carries both sided classes, otherwise a single un-sided
    record keyed on the un-sided class.
  - Exclusion: any candidate whose FMAID already appears in ANY
    BodyParts3D-derived inventory record of the Body Model (any
    system), or in the Milestone 33 FMA intake, is excluded and
    reported with its owner — the extension adds only what the
    model lacks, and never double-owns a concept. (One target is
    expected to fire this rule: 'Pineal body', FMA62033, the
    nervous module's record.)
  - The OWL parser counts owl:Class nesting depth (net of
    self-closing class references): an element whose restriction
    axioms embed nested class expressions must not be truncated
    at the first nested close (FMA9603's fma:preferred_name sits
    after ~55 restriction axioms; a naive block parse reads
    that class as label-only — the independent checker, parsing
    with ElementTree, caught exactly this during the Milestone
    36 build; the fixed parser agrees with the XML parse on
    preferred names: 103,687 classes carry one).
  - The merge is idempotent: records tagged source ==
    "fma-5.1.0" in these two inventories are stripped and
    re-appended; every BP3D record and census field is left
    byte-identical in parsed form.
  - The per-system intake accounting is written to
    data/fma-intake-36.json (targets, verdicts, probe evidence,
    census deltas), in the pattern of
    data/innervation-link-pass.json.

Usage: fma_lymph_endo_map.py [--report]
Stdlib only.
"""
import json
import os
import re
import sys
import zipfile
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources", "fma-5.1.0")
WORK_OWL = os.path.join(ROOT, "work", "fma", "fma.owl")
ART_PATH = os.path.join(ROOT, "data", "fma-intake-36.json")
SOURCE_TAG = "fma-5.1.0"
DATE = "2026-11-06"

GENERIC_NOTE = ("generic class in the FMA; recorded as the un-sided "
                "class, as released")
GROUP_NOTE = ("the FMA names this aggregate only as a group class; "
              "recorded as released")
VERIFY_FLAGS = [
    "geometry: absent — the FMA is an ontology and carries no mesh "
    "data; this record is concept-only until a geometry source clears "
    "the project's license and registration bars (Milestone 36)",
    "clinical: no clinical tranche has been authored for FMA-sourced "
    "records; no clinical values are entered",
]

# ---------------------------------------------------------------------
# Frozen target lists: (preferred-name target, subtree, note or None).
# Every name was verified present in fma.owl by probe before freezing
# (Milestone 36 build record). pin= marks the label-only class.
# ---------------------------------------------------------------------

LYMPH_TARGETS = []
# Conducting system (Milestone 13: absent entire)
for n in ["Lymphatic vessel", "Lymphatic capillary"]:
    LYMPH_TARGETS.append((n, "conducting", GENERIC_NOTE))
for n in ["Thoracic duct", "Cisterna chyli",
          "Jugular lymphatic trunk", "Subclavian lymphatic trunk",
          "Bronchomediastinal lymphatic trunk",
          "Lumbar lymphatic trunk", "Intestinal lymphatic trunk"]:
    LYMPH_TARGETS.append((n, "conducting", None))
LYMPH_TARGETS.append(("Right lymphatic duct", "conducting",
                      "the FMA's class is intrinsically the "
                      "right-sided duct — no left counterpart and "
                      "no separate un-sided class exists; recorded "
                      "as the un-sided job on the class as "
                      "released, its name carrying the side"))
LYMPH_TARGETS.append(("Lymph node", "conducting", GENERIC_NOTE))
# Node groups — head and neck
for n in ["Occipital lymph node", "Mastoid lymph node",
          "Parotid lymph node", "Superficial parotid lymph node",
          "Deep parotid lymph node", "Facial lymph node",
          "Submandibular lymph node", "Submental lymph node",
          "Anterior cervical lymph node", "Lateral cervical lymph node",
          "Deep lateral cervical lymph node",
          "Supraclavicular lymph node", "Retropharyngeal lymph node",
          "Prelaryngeal lymph node", "Pretracheal lymph node",
          "Jugulodigastric lymph node"]:
    LYMPH_TARGETS.append((n, "nodes-head-neck", None))
# Node groups — axillary and upper limb
LYMPH_TARGETS.append(("Axillary lymph node", "nodes-upper-limb",
                      "the FMA carries the sided forms of this "
                      "aggregate only as group classes (Left/Right "
                      "axillary lymph node group); the un-sided class "
                      "is recorded, per the counting convention"))
LYMPH_TARGETS.append(("Pectoral axillary lymph node group",
                      "nodes-upper-limb", GROUP_NOTE))
LYMPH_TARGETS.append(("Subscapular lymph node", "nodes-upper-limb",
                      "the FMA's class for the subscapular (posterior "
                      "axillary) node group"))
for n in ["Apical axillary lymph node", "Central axillary lymph node",
          "Lateral axillary lymph node", "Brachial lymph node",
          "Supratrochlear lymph node", "Cubital lymph node"]:
    LYMPH_TARGETS.append((n, "nodes-upper-limb", None))
# Node groups — thorax
for n in ["Paratracheal lymph node", "Tracheobronchial lymph node",
          "Superior tracheobronchial lymph node",
          "Inferior tracheobronchial lymph node",
          "Bronchopulmonary lymph node", "Intercostal lymph node",
          "Diaphragmatic lymph node", "Superior diaphragmatic lymph node",
          "Superior phrenic lymph node", "Superior mediastinal lymph node",
          "Posterior mediastinal lymph node", "Mediastinal lymph node",
          "Esophageal lymph node"]:
    LYMPH_TARGETS.append((n, "nodes-thoracic", None))
LYMPH_TARGETS.append(("Anterior mediastinal lymph node group",
                      "nodes-thoracic", GROUP_NOTE))
# Node groups — abdomen
for n in ["Celiac lymph node", "Gastric lymph node", "Hepatic lymph node",
          "Common hepatic lymph node", "Splenic lymph node",
          "Pancreatic lymph node", "Pancreaticoduodenal lymph node",
          "Cystic lymph node", "Superior mesenteric lymph node",
          "Inferior mesenteric lymph node", "Mesenteric lymph node",
          "Colic lymph node", "Ileocolic lymph node",
          "Appendicular lymph node", "Lateral aortic lymph node"]:
    LYMPH_TARGETS.append((n, "nodes-abdominal", None))
LYMPH_TARGETS.append(("Lumbar lymph node group", "nodes-abdominal",
                      GROUP_NOTE))
# Node groups — pelvis and lower limb
for n in ["Common iliac lymph node", "External iliac lymph node",
          "Internal iliac lymph node", "Sacral lymph node",
          "Gluteal lymph node", "Inguinal lymph node",
          "Superficial inguinal lymph node", "Deep inguinal lymph node",
          "Popliteal lymph node", "Superficial popliteal lymph node",
          "Deep popliteal lymph node"]:
    LYMPH_TARGETS.append((n, "nodes-pelvic-lower-limb", None))
# Tonsils and MALT (Milestone 13: absent entire)
LYMPH_TARGETS.append(("Tonsil", "tonsils-malt", GENERIC_NOTE))
for n in ["Palatine tonsil", "Pharyngeal tonsil", "Lingual tonsil",
          "Tubal tonsil"]:
    LYMPH_TARGETS.append((n, "tonsils-malt", None))
LYMPH_TARGETS.append((
    "Aggregated lymphoid follicle of small intestine", "tonsils-malt",
    "the FMA's class for the aggregated lymphoid follicles of the "
    "small intestine (Peyer's patches); the FMA also carries a "
    "regional ileal class (FMA72027), not separately recorded — "
    "the census granularity is the named aggregate"))
# Bone marrow (Milestone 13 gap analysis: the other primary
# lymphoid organ, absent entire; owned by this module there)
LYMPH_TARGETS.append(("Bone marrow", "marrow",
                      "the primary lymphoid organ of Milestone 13's "
                      "gap analysis, which recorded its absence "
                      "under this module"))
for n in ["Red bone marrow", "Yellow bone marrow"]:
    LYMPH_TARGETS.append((n, "marrow", None))
# Interiors of the two organs the release carries (Milestone 13)
for n in ["Splenic pulp", "Red pulp of spleen", "White pulp of spleen",
          "Trabecula of spleen"]:
    LYMPH_TARGETS.append((n, "interiors-spleen", None))
for n in ["Lobule of thymus", "Cortex of thymus", "Medulla of thymus"]:
    LYMPH_TARGETS.append((n, "interiors-thymus", None))

ENDO_TARGETS = []
# The thyroid gland, entire (Milestone 13)
ENDO_TARGETS.append(("Thyroid gland", "thyroid", None))
for n in ["Lobe of thyroid gland", "Isthmus of thyroid gland",
          "Pyramidal lobe of thyroid gland"]:
    ENDO_TARGETS.append((n, "thyroid", None))
# The parathyroid glands, entire (Milestone 13)
ENDO_TARGETS.append(("Parathyroid gland", "parathyroid", GENERIC_NOTE))
for n in ["Superior parathyroid gland", "Inferior parathyroid gland"]:
    ENDO_TARGETS.append((n, "parathyroid", None))
# The pineal: expected to be EXCLUDED — FMA62033 is the nervous
# module's BodyParts3D record (brain.pineal-body); the target is
# frozen here so the exclusion fires mechanically and is accounted.
ENDO_TARGETS.append(("Pineal body", "pineal",
                     "the FMA's preferred name for the pineal "
                     "gland (its listed synonym); targeted so the "
                     "cross-module exclusion is mechanical"))
# The endocrine pancreas: the islet concept. The pancreas organ
# record is the digestive module's (FMA7198, Milestone 11/13
# boundary); this record is the endocrine content only, mirroring
# the Milestone 13 clinical boundary (gland.pancreatic-islets).
ENDO_TARGETS.append(("Pancreatic islet", "islets",
                     "host organ is the digestive module's "
                     "pancreas record (FMA7198); this concept "
                     "record carries the endocrine content only — "
                     "the Milestone 13 boundary"))
# Paraganglia (FMA carries the generic class and the carotid body;
# the aortic body and jugulotympanic paraganglion have no class
# under the probed names — see absence probes)
ENDO_TARGETS.append(("Paraganglion", "paraganglia", GENERIC_NOTE))
ENDO_TARGETS.append(("Carotid body", "paraganglia", None))

SYSTEMS = {
    "lymphatic": {
        "inventory": "data/lymphatic/lymphatic-inventory.json",
        "geometry": "data/lymphatic/lymphatic-geometry.json",
        "prefix": "lymph",
        "targets": LYMPH_TARGETS,
    },
    "endocrine": {
        "inventory": "data/endocrine/endocrine-inventory.json",
        "geometry": "data/endocrine/endocrine-geometry.json",
        "prefix": "endo",
        "targets": ENDO_TARGETS,
    },
}

# Absence probes: names with NO class in the FMA under the probed
# preferred name or its Left/Right forms — computed, not asserted,
# and written into the accounting artifact as evidence.
ABSENCE_PROBES = {
    "lymphatic": [
        "Superficial cervical lymph node", "Deep cervical lymph node",
        "Pancreaticosplenic lymph node", "Splenic hilum",
        "Thymic corpuscle", "Intestinal trunk", "Lymphatic trunk",
        "Peyer patch", "Aggregated lymphoid nodule",
    ],
    "endocrine": [
        "Endocrine pancreas", "Islet of Langerhans", "Aortic body",
        "Glomus jugulare", "Jugulotympanic paraganglion",
        "Parafollicular cell", "Pineal gland",
    ],
}

# Census-named structures that EXIST in the FMA but are not targets
# of this intake, with the reason (recorded, not silent).
DEFERRED = {
    "lymphatic": [
        {"names": "per-level intercostal lymph nodes (First–Eleventh "
                  "intercostal lymph node classes) and the segmental "
                  "bronchopulmonary chain classes",
         "reason": "below the frozen list's granularity: Milestone "
                   "13's absence census names node groups and "
                   "chains, not per-level or per-segment nodes; "
                   "the generic Intercostal lymph node and "
                   "Bronchopulmonary lymph node classes are "
                   "recorded"},
        {"names": "'Set of …' aggregate classes throughout the "
                  "lymph node space",
         "reason": "set/aggregate classes are not records, per "
                   "the Milestone 9/33 convention"},
    ],
    "endocrine": [
        {"names": "Adenohypophysis (FMA74627), Neurohypophysis "
                  "(FMA74628)",
         "reason": "interiors of the pituitary, an organ already "
                   "holding a record; gland interiors of recorded "
                   "organs are a separate named follow-on class, "
                   "not part of this whole-gland absence intake"},
        {"names": "Adrenal cortex (FMA15632), Adrenal medulla "
                  "(FMA15633), Zona glomerulosa (FMA69225) / "
                  "fasciculata (FMA69234) / reticularis (FMA69236) "
                  "of adrenal gland",
         "reason": "interiors of the adrenals, organs already "
                   "holding records; same follow-on class as the "
                   "pituitary interiors"},
        {"names": "Thyroid follicle (FMA68805)",
         "reason": "histological unit, below record granularity "
                   "(the Milestone 9 segment-class convention); "
                   "the gland and its gross parts are recorded"},
        {"names": "Accessory thyroid gland (FMA55533), Accessory "
                  "parathyroid gland (FMA55567)",
         "reason": "accessory/ectopic variants, not named in "
                   "Milestone 13's absence census; variants are "
                   "modelled as variants, not census records"},
    ],
}


def slug(name):
    s = name.lower().replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def parse_owl(path):
    """Streaming regex parse of owl:Class blocks ->
    {fid: {name, label, parents}} (name = fma:preferred_name,
    label = rdfs:label; either may be None). Block boundaries
    count owl:Class nesting depth: restriction axioms embed
    nested class expressions, and a block must not end at a
    nested close (FMA9603's preferred_name sits after its
    restriction axioms)."""
    def net(line):
        opens = len(re.findall(r"<owl:Class(?=[\s>])", line))
        selfclosed = len(re.findall(r"<owl:Class[^>]*/>", line))
        return opens - selfclosed - line.count("</owl:Class>")

    classes = {}
    block = []
    depth = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if depth == 0 and "<owl:Class rdf:about=" in line:
                block = [line]
                depth = net(line)
                if depth > 0:
                    continue
            elif depth:
                block.append(line)
                depth += net(line)
                if depth > 0:
                    continue
            else:
                continue
            if block:
                text = "".join(block)
                block = []
                m = re.search(
                    r'owl:Class rdf:about="http://purl\.org/sig/ont/'
                    r'fma/fma(\d+)"', text)
                if m:
                    name = re.search(
                        r"<fma:preferred_name>([^<]+)"
                        r"</fma:preferred_name>", text)
                    label = re.search(
                        r"<rdfs:label[^>]*>([^<]+)</rdfs:label>",
                        text)
                    parents = re.findall(
                        r'<rdfs:subClassOf rdf:resource='
                        r'"http://purl\.org/sig/ont/fma/fma(\d+)"/>',
                        text)
                    classes[m.group(1)] = {
                        "name": name.group(1) if name else None,
                        "label": label.group(1) if label else None,
                        "parents": parents}
    return classes


def display_name(fid, classes):
    c = classes.get(fid) or {}
    return c.get("name") or c.get("label")


def group_path(fid, classes):
    """BFS over named IS-A parents to FMA62955 'Anatomical entity';
    ancestor names are preferred names, falling back to rdfs:label
    for the classes that carry no preferred name."""
    target = "62955"
    from collections import deque
    prev = {fid: None}
    queue = deque([fid])
    found = None
    while queue:
        cur = queue.popleft()
        if cur == target:
            found = cur
            break
        for p in classes.get(cur, {}).get("parents", []):
            if p not in prev and p in classes:
                prev[p] = cur
                queue.append(p)
    if found is None:
        return [display_name(fid, classes)]
    chain = []
    cur = found
    while cur is not None:
        chain.append(display_name(cur, classes))
        cur = prev[cur]
    return chain


def global_exclusions():
    """fid -> [owners] over every BodyParts3D-derived inventory
    record of the Body Model, plus the Milestone 33 FMA intake
    (the nervous inventory's tagged records). This builder's OWN
    records — the tagged records of the two inventories it
    rebuilds — never exclude: they are stripped and re-derived
    on every run, which is what makes the builder idempotent.
    (The first build run proved the point by omission: with its
    own output on disk, a naive sweep excluded every target
    against itself and the inventories collapsed to their BP3D
    partitions; the independent checker failed the run and the
    fixed builder restored them.)"""
    import glob as globmod
    owners = defaultdict(list)
    own_files = {os.path.join(ROOT, cfg["inventory"])
                 for cfg in SYSTEMS.values()}
    for path in sorted(globmod.glob(
            os.path.join(ROOT, "data", "*", "*-inventory.json"))):
        doc = json.load(open(path))
        system = os.path.basename(os.path.dirname(path))
        for r in doc.get("records", []):
            if r.get("source") == SOURCE_TAG and path in own_files:
                continue  # this run's own records: rebuilt below
            ids = list(r.get("concept_ids") or [])
            if r.get("class_concept_id"):
                ids.append(r["class_concept_id"])
            for cid in ids:
                if r.get("source") == SOURCE_TAG:
                    owners[cid].append(
                        f"fma-intake:{system}:{r['record_id']}")
                else:
                    owners[cid].append(
                        f"bp3d:{system}:{r['record_id']}")
    return owners


def build_system(system, cfg, classes, byname, owners, report):
    inv = json.load(open(os.path.join(ROOT, cfg["inventory"])))
    geo = json.load(open(os.path.join(ROOT, cfg["geometry"])))
    bp3d_records = [r for r in inv["records"]
                    if r.get("source") != SOURCE_TAG]
    bp3d_ids = {r["record_id"] for r in bp3d_records}

    new_records = []
    entries = []
    for target, subtree, note in cfg["targets"]:
        unsided = byname.get(target.lower(), [])
        left = byname.get(f"left {target}".lower(), [])
        right = byname.get(f"right {target}".lower(), [])
        jobs = []
        if left and right:
            jobs = [("left", left[0]), ("right", right[0])]
        elif unsided:
            jobs = [(None, unsided[0])]
        if not jobs:
            entries.append({"target": target, "subtree": subtree,
                            "verdict": "not-in-fma",
                            "evidence": "no class carries this "
                                        "preferred name or its "
                                        "Left/Right forms in fma.owl",
                            "records": []})
            continue
        class_id = f"FMA{unsided[0]}" if unsided else None
        rec_ids = []
        excluded_hit = []
        for side, fid in jobs:
            owner = owners.get(f"FMA{fid}")
            if owner:
                excluded_hit.append((side, fid, owner))
                continue
            name = display_name(fid, classes)
            assert name is not None, (target, fid)
            rid = f"{cfg['prefix']}.{slug(name)}"
            assert rid not in bp3d_ids, f"record id collision: {rid}"
            assert all(x["record_id"] != rid for x in new_records), rid
            new_records.append({
                "record_id": rid,
                "name": name,
                "side": side,
                "representation": "fma-concept",
                "class_concept_id": class_id,
                "concept_ids": [f"FMA{fid}"],
                "subtree": subtree,
                "group_path": group_path(fid, classes),
                "source": SOURCE_TAG,
                "geometry": "absent",
                "verify": list(VERIFY_FLAGS),
                "note": note,
            })
            rec_ids.append(rid)
        if excluded_hit and not rec_ids:
            entries.append({
                "target": target, "subtree": subtree,
                "verdict": "excluded",
                "evidence": "; ".join(
                    f"FMA{fid} already inventoried ({', '.join(own)})"
                    for _s, fid, own in excluded_hit),
                "records": []})
        else:
            assert not excluded_hit, (target, excluded_hit)
            entries.append({
                "target": target, "subtree": subtree,
                "verdict": "resolved",
                "records": rec_ids,
                "fmaids": [r["concept_ids"][0] for r in new_records
                           if r["record_id"] in rec_ids],
                "sided": sum(1 for r in new_records
                             if r["record_id"] in rec_ids
                             and r["side"] is not None)})
    unresolved = [e for e in entries if e["verdict"] == "not-in-fma"]
    print(f"[{system}] targets: {len(cfg['targets'])}  new records: "
          f"{len(new_records)}  excluded: "
          f"{sum(1 for e in entries if e['verdict'] == 'excluded')}  "
          f"not-in-fma: {len(unresolved)}")
    for e in entries:
        if e["verdict"] != "resolved":
            print(f"  {e['verdict'].upper()}: {e['target']} — "
                  f"{e['evidence']}")
    if report:
        return None

    inv["records"] = bp3d_records + new_records
    inv["meta"]["record_count"] = len(inv["records"])
    reps = {}
    for r in inv["records"]:
        reps[r["representation"]] = reps.get(r["representation"], 0) + 1
    inv["meta"]["record_representations"] = reps
    by_sub = {}
    for r in inv["records"]:
        by_sub[r["subtree"]] = by_sub.get(r["subtree"], 0) + 1
    inv["meta"]["records_by_subtree"] = by_sub
    inv["meta"]["fma_extension"] = {
        "milestone": 36,
        "source": "Foundational Model of Anatomy (FMA) 5.1.0, "
                  "data/sources/fma-5.1.0/ (CC BY 4.0)",
        "records_added": len(new_records),
        "geometry_absent": len(new_records),
        "counting_convention": "one record per lateralised instance "
                               "where the FMA carries both sided "
                               "classes; one record keyed on the "
                               "un-sided class otherwise — mirroring "
                               "the Milestone 33 convention",
        "accounting": "data/fma-intake-36.json",
    }
    with open(os.path.join(ROOT, cfg["inventory"]), "w") as f:
        json.dump(inv, f, indent=1)

    geo_bp3d = [r for r in geo["records"]
                if r.get("source") != SOURCE_TAG]
    geo_new = [{
        "record_id": r["record_id"],
        "name": r["name"],
        "side": r["side"],
        "representation": "fma-concept",
        "concept_ids": r["concept_ids"],
        "concept_names": [r["name"]],
        "source": SOURCE_TAG,
        "geometry_status": "absent — FMA concept record; the FMA "
                           "carries no mesh data (Milestone 36)",
        "isa_meshes": [],
        "partof_meshes": [],
        "totals": {"isa": {"files": 0, "vertices": 0, "faces": 0},
                   "partof": {"files": 0, "vertices": 0, "faces": 0},
                   "combined_files": 0},
        "bbox_isa": None,
        "bbox_partof": None,
    } for r in new_records]
    geo["records"] = geo_bp3d + geo_new
    geo["meta"]["coverage"] = {
        "records": len(geo["records"]),
        "records_with_meshes": len(geo_bp3d),
        "records_without_meshes": len(geo_new),
    }
    with open(os.path.join(ROOT, cfg["geometry"]), "w") as f:
        json.dump(geo, f, indent=1)
    print(f"[{system}] inventory records: {len(bp3d_records)} BP3D + "
          f"{len(new_records)} FMA = {len(inv['records'])}")
    return {
        "records_before": len(bp3d_records),
        "records_after": len(inv["records"]),
        "records_added": len(new_records),
        "targets": entries,
    }


def main():
    report = "--report" in sys.argv
    if not os.path.exists(WORK_OWL):
        os.makedirs(os.path.dirname(WORK_OWL), exist_ok=True)
        with zipfile.ZipFile(os.path.join(SRC, "fma.zip")) as zf:
            zf.extract("fma.owl", os.path.dirname(WORK_OWL))
    classes = parse_owl(WORK_OWL)
    byname = defaultdict(list)
    for fid, c in classes.items():
        if c["name"]:
            byname[c["name"].lower()].append(fid)
    owners = global_exclusions()

    artifact = {
        "meta": {
            "milestone": "M36", "date": DATE,
            "scope": "FMA 5.1.0 concept intake #2: the lymphatic "
                     "system and the endocrine glands — the "
                     "structures Milestone 13 proved absent from "
                     "BodyParts3D 4.0",
            "method": "tools/fma_lymph_endo_map.py (frozen targets, "
                      "mechanical resolution) — checked by "
                      "tools/fma_lymph_endo_check.py (independent)",
            "rule": "lateralised records where the FMA carries "
                    "both sided classes, one un-sided record "
                    "otherwise; any FMAID already inventoried "
                    "anywhere in the Body Model (BP3D-derived or "
                    "Milestone 33 FMA) is excluded and accounted "
                    "with its owner",
            "source": "Foundational Model of Anatomy (FMA) 5.1.0, "
                      "data/sources/fma-5.1.0/ (CC BY 4.0)",
        },
        "systems": {},
    }
    for system, cfg in SYSTEMS.items():
        result = build_system(system, cfg, classes, byname, owners,
                              report)
        probes = []
        for p in ABSENCE_PROBES[system]:
            hits = (byname.get(p.lower(), [])
                    + byname.get(f"left {p}".lower(), [])
                    + byname.get(f"right {p}".lower(), []))
            probes.append({"probe": p,
                           "preferred_name_hits": len(hits)})
        if result is not None:
            result["absence_probes"] = probes
            result["deferred"] = DEFERRED[system]
            artifact["systems"][system] = result
    if not report:
        with open(ART_PATH, "w") as f:
            json.dump(artifact, f, indent=1)
        print(f"accounting -> {ART_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
