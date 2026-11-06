#!/usr/bin/env python3
"""ANATOMICA nervous-system FMA extension builder — Milestone 33.

Extends the nervous inventory with concept records sourced from the
Foundational Model of Anatomy (FMA) 5.1.0 for the structures
Milestone 9 proved absent from BodyParts3D 4.0 (its 126-probe gap
analysis): cranial nerves I, VI–XII and the trigeminal divisions,
every spinal nerve level, the plexuses, the named limb and trunk
nerves, the autonomic system, the spinal cord's named parts and the
meninges.

License: the FMA 5.1.0 release package ships the full text of
CC BY 4.0 as its LICENSE file (data/sources/fma-5.1.0/, hash-pinned
in that directory's provenance ledger). Concept data (names, FMAIDs,
IS-A paths) is therefore redistributable in product data with
attribution. The FMA is an ontology: it carries NO geometry. Every
record written here is marked geometry-absent; no mesh, coordinate
or clinical value is created by this tool.

Method:
  - fma.owl is parsed by streaming class blocks (regex extraction —
    the independent checker tools/fma_nerve_check.py re-parses with
    an XML parser instead and must agree).
  - A frozen target list (below) names the concepts Milestone 9
    recorded as absent. Each target is resolved mechanically:
    lateralised records (left/right) where the FMA carries both
    sided classes, otherwise a single un-sided record keyed on the
    un-sided class. Class/aggregate concepts are not targets.
  - Any candidate whose FMAID already appears in the BodyParts3D
    inventory is excluded and reported (the extension must add only
    what the release lacks).
  - The merge is idempotent: records tagged source == "fma-5.1.0"
    are stripped and re-appended; the 133 BodyParts3D records and
    every BP3D census field are left byte-identical.

Usage: fma_nerve_map.py [--report]
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
INV_PATH = os.path.join(ROOT, "data", "nervous", "nervous-inventory.json")
GEO_PATH = os.path.join(ROOT, "data", "nervous", "nervous-geometry.json")
SOURCE_TAG = "fma-5.1.0"

ORDINALS = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth",
            "Seventh", "Eighth", "Ninth", "Tenth", "Eleventh", "Twelfth"]

# Frozen target list: (preferred-name target, subtree, note or None).
# Every name is a structure Milestone 9's gap analysis recorded as
# absent from BodyParts3D 4.0, or a named part of one.
TARGETS = []
# Cranial nerves and the trigeminal apparatus
for n in ["Olfactory nerve", "Oculomotor nerve", "Trigeminal nerve",
          "Maxillary nerve", "Mandibular nerve", "Ophthalmic nerve",
          "Trigeminal ganglion", "Abducens nerve", "Facial nerve",
          "Vestibulocochlear nerve", "Glossopharyngeal nerve",
          "Vagus nerve", "Spinal accessory nerve", "Hypoglossal nerve"]:
    TARGETS.append((n, "peripheral", None))
# Spinal nerves, every level
for region, count in [("cervical", 8), ("thoracic", 12), ("lumbar", 5),
                      ("sacral", 5)]:
    for i in range(count):
        TARGETS.append((f"{ORDINALS[i]} {region} nerve", "peripheral", None))
TARGETS.append(("Coccygeal nerve", "peripheral", None))
# Spinal nerve architecture (FMA models these as generic classes)
for n in ["Anterior root of spinal nerve", "Posterior root of spinal nerve",
          "Spinal ganglion", "Anterior ramus of spinal nerve",
          "Posterior ramus of spinal nerve"]:
    TARGETS.append((n, "peripheral",
                    "generic class in the FMA (modelled per level in the "
                    "body); recorded as the un-sided class, as released"))
# Intercostal nerves T1-T11 and the subcostal nerve (T12)
for i in range(11):
    TARGETS.append((f"{ORDINALS[i]} intercostal nerve", "peripheral", None))
TARGETS.append(("Subcostal nerve", "peripheral", None))
# Somatic plexuses
for n in ["Cervical nerve plexus", "Brachial nerve plexus",
          "Lumbar nerve plexus", "Sacral nerve plexus",
          "Lumbosacral nerve plexus", "Coccygeal nerve plexus"]:
    TARGETS.append((n, "peripheral", None))
# Brachial plexus architecture (un-sided classes in the FMA)
for n in ["Superior trunk of brachial nerve plexus",
          "Middle trunk of brachial nerve plexus",
          "Inferior trunk of brachial nerve plexus",
          "Superior anterior division of brachial plexus",
          "Middle anterior division of brachial plexus",
          "Inferior anterior division of brachial plexus",
          "Superior posterior division of brachial plexus",
          "Middle posterior division of brachial plexus",
          "Inferior posterior division of brachial plexus",
          "Lateral cord of brachial nerve plexus",
          "Posterior cord of brachial nerve plexus",
          "Medial cord of brachial nerve plexus"]:
    TARGETS.append((n, "peripheral", None))
# Named peripheral nerves (Milestone 9's probed set and the terminal
# branches a Theatre procedure or the muscle module names)
for n in ["Phrenic nerve", "Great auricular nerve",
          "Transverse cervical nerve", "Supraclavicular nerve",
          "Suprascapular nerve", "Long thoracic nerve",
          "Thoracodorsal nerve", "Lateral pectoral nerve",
          "Medial pectoral nerve", "Superior subscapular nerve",
          "Inferior subscapular nerve", "Axillary nerve",
          "Musculocutaneous nerve", "Median nerve", "Ulnar nerve",
          "Radial nerve", "Medial cutaneous nerve of arm",
          "Medial cutaneous nerve of forearm",
          "Posterior cutaneous nerve of arm",
          "Posterior cutaneous nerve of forearm",
          "Iliohypogastric nerve", "Ilioinguinal nerve",
          "Genitofemoral nerve", "Femoral nerve", "Obturator nerve",
          "Superior gluteal nerve", "Inferior gluteal nerve",
          "Sciatic nerve", "Tibial nerve", "Common fibular nerve",
          "Deep fibular nerve", "Superficial fibular nerve",
          "Pudendal nerve", "Lateral femoral cutaneous nerve",
          "Saphenous nerve", "Sural nerve", "Medial plantar nerve",
          "Lateral plantar nerve", "Anococcygeal nerve",
          "Perforating cutaneous nerve", "Nerve to piriformis",
          "Nerve to quadratus femoris"]:
    TARGETS.append((n, "peripheral", None))
TARGETS.append(("Posterior cutaneous nerve", "peripheral",
                "the FMA's preferred name for the posterior femoral "
                "cutaneous nerve (TA2: nervus cutaneus femoris posterior)"))
# Autonomic: trunks, ganglia, splanchnic nerves
for n in ["Sympathetic trunk", "Superior cervical ganglion",
          "Middle cervical ganglion", "Cervicothoracic ganglion",
          "Celiac ganglion", "Superior mesenteric ganglion",
          "Inferior mesenteric ganglion", "Greater splanchnic nerve",
          "Lesser splanchnic nerve", "Least splanchnic nerve",
          "Sacral splanchnic nerve", "Pelvic splanchnic nerve"]:
    TARGETS.append((n, "autonomic", None))
for i in range(4):
    TARGETS.append((f"{ORDINALS[i]} lumbar splanchnic nerve",
                    "autonomic", None))
TARGETS.append(("Cervicothoracic ganglion", "autonomic", None))
# Autonomic plexuses
for n in ["Cardiac nerve plexus", "Celiac nerve plexus",
          "Superior hypogastric nerve plexus",
          "Inferior hypogastric nerve plexus",
          "Superior mesenteric nerve plexus",
          "Inferior mesenteric nerve plexus", "Aortic plexus",
          "Intermesenteric nerve plexus", "Renal nerve plexus",
          "Hepatic nerve plexus", "Splenic nerve plexus",
          "Pulmonary nerve plexus", "Esophageal nerve plexus",
          "Pharyngeal nerve plexus", "Tympanic plexus",
          "Vesical nerve plexus", "Uterovaginal nerve plexus",
          "Prostatic nerve plexus", "Myenteric nerve plexus",
          "Submucosal nerve plexus", "Enteric plexus"]:
    TARGETS.append((n, "autonomic", None))
# Spinal cord named parts
for n in ["Conus medullaris", "Cauda equina", "Filum terminale",
          "Denticulate ligament", "Cervical enlargement"]:
    TARGETS.append((n, "central", None))
TARGETS.append(("Lumbar enlargement", "central",
                "the FMA's preferred name for the lumbosacral "
                "enlargement of the spinal cord"))
# Meninges
for n in ["Pia mater", "Arachnoid mater", "Cranial dura mater",
          "Spinal dura mater", "Falx cerebri", "Falx cerebelli",
          "Diaphragma sellae"]:
    TARGETS.append((n, "meningeal", None))

# De-duplicate targets preserving order (cervicothoracic listed once).
_seen = set()
TARGETS = [t for t in TARGETS if not (t[0] in _seen or _seen.add(t[0]))]

VERIFY_FLAGS = [
    "geometry: absent — the FMA is an ontology and carries no mesh "
    "data; this record is concept-only until a geometry source clears "
    "the project's license and registration bars (Milestone 33)",
    "clinical: no clinical tranche has been authored for FMA-sourced "
    "records; no clinical values are entered",
]


def slug(name):
    s = name.lower().replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def parse_owl(path):
    """Streaming regex parse of owl:Class blocks -> {fid: {name, parents}}."""
    classes = {}
    block = []
    in_class = False
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "<owl:Class rdf:about=" in line:
                in_class = True
                block = [line]
            elif in_class:
                block.append(line)
                if "</owl:Class>" in line:
                    text = "".join(block)
                    m = re.search(
                        r'owl:Class rdf:about="http://purl\.org/sig/ont/'
                        r'fma/fma(\d+)"', text)
                    if m:
                        name = re.search(
                            r"<fma:preferred_name>([^<]+)</fma:preferred_name>",
                            text)
                        parents = re.findall(
                            r'<rdfs:subClassOf rdf:resource='
                            r'"http://purl\.org/sig/ont/fma/fma(\d+)"/>', text)
                        classes[m.group(1)] = {
                            "name": name.group(1) if name else None,
                            "parents": parents}
                    in_class = False
    return classes


def group_path(fid, classes, byname):
    """BFS over named IS-A parents to FMA62955 'Anatomical entity'
    (the root of the FMA's IS-A tree and of the BodyParts3D
    group_paths); returns the ancestor chain root-first, ending at
    the class. Note: the FMA's IS-A tree does not pass through
    'Nervous system' (FMA7157), which hangs off the part hierarchy —
    recorded in MILESTONE-33.md."""
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
        return [classes[fid]["name"]]
    chain = []
    cur = found
    while cur is not None:
        chain.append(classes[cur]["name"])
        cur = prev[cur]
    return chain


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

    inv = json.load(open(INV_PATH))
    geo = json.load(open(GEO_PATH))
    bp3d_records = [r for r in inv["records"]
                    if r.get("source") != SOURCE_TAG]
    bp3d_ids = {r["record_id"] for r in bp3d_records}
    bp3d_fmaids = set()
    for r in bp3d_records:
        bp3d_fmaids.update(r.get("concept_ids") or [])
        if r.get("class_concept_id"):
            bp3d_fmaids.add(r["class_concept_id"])

    new_records = []
    excluded, unresolved = [], []
    for target, subtree, note in TARGETS:
        unsided = byname.get(target.lower(), [])
        left = byname.get(f"left {target}".lower(), [])
        right = byname.get(f"right {target}".lower(), [])
        jobs = []
        if left and right:
            jobs = [("left", left[0]), ("right", right[0])]
        elif unsided:
            jobs = [(None, unsided[0])]
        if not jobs:
            unresolved.append(target)
            continue
        class_id = f"FMA{unsided[0]}" if unsided else None
        for side, fid in jobs:
            if f"FMA{fid}" in bp3d_fmaids:
                excluded.append((target, side, fid))
                continue
            name = classes[fid]["name"]
            rid = f"nerve.{slug(name)}"
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
                "group_path": group_path(fid, classes, byname),
                "source": SOURCE_TAG,
                "geometry": "absent",
                "verify": list(VERIFY_FLAGS),
                "note": note,
            })

    print(f"targets: {len(TARGETS)}  new records: {len(new_records)}  "
          f"excluded (already in BP3D inventory): {len(excluded)}  "
          f"unresolved: {len(unresolved)}")
    for t in unresolved:
        print(f"  UNRESOLVED: {t}")
    for t, s, f in excluded:
        print(f"  EXCLUDED: {t} side={s} FMA{f} already inventoried")
    if report:
        return 0

    inv["records"] = bp3d_records + new_records
    inv["meta"]["record_count"] = len(inv["records"])
    inv["meta"]["record_representations"]["fma-concept"] = len(new_records)
    inv["meta"]["fma_extension"] = {
        "milestone": 33,
        "source": "Foundational Model of Anatomy (FMA) 5.1.0, "
                  "data/sources/fma-5.1.0/ (CC BY 4.0)",
        "records_added": len(new_records),
        "geometry_absent": len(new_records),
        "counting_convention": "one record per lateralised instance "
                               "where the FMA carries both sided "
                               "classes; one record keyed on the "
                               "un-sided class otherwise — mirroring "
                               "the Milestone 9 convention",
    }
    with open(INV_PATH, "w") as f:
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
                           "carries no mesh data (Milestone 33)",
        "isa_meshes": [],
        "partof_meshes": [],
        "totals": {"isa": {"files": 0, "vertices": 0, "faces": 0},
                   "partof": {"files": 0, "vertices": 0, "faces": 0}},
    } for r in new_records]
    geo["records"] = geo_bp3d + geo_new
    geo["meta"]["coverage"] = {
        "records": len(geo["records"]),
        "records_with_meshes": len(geo_bp3d),
        "records_without_meshes": len(geo_new),
    }
    with open(GEO_PATH, "w") as f:
        json.dump(geo, f, indent=1)
    print(f"inventory records: {len(bp3d_records)} BP3D + "
          f"{len(new_records)} FMA = {len(inv['records'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
