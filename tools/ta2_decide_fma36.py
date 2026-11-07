#!/usr/bin/env python3
"""Milestone 36 curation: turn the FMA-36 worksheets into
decisions. Sibling of tools/ta2_decide_fma.py, system-
parameterized: `ta2_decide_fma36.py lymphatic|endocrine`.

Mechanical rules first (the Milestone 23 discipline, unchanged):
a record resolves only when TA2's own naming apparatus (preferred
term, listed synonym, or listed related term) names a term for a
structure identical to the record's, corroborated by structure
class, with no competing in-class term.

  M1  a sole STRONG candidate whose structure class is compatible
      with the record's class resolves (basis from the winning
      key's provenance in the term's apparatus);
  M2  among several candidates, a sole in-class STRONG candidate
      resolves;
  M3  a sole weak candidate (synonym / related-term bridge) whose
      structure class is compatible resolves with that basis;
  M4  a record the matcher left with NO candidate is not found:
      its probes are its own names, absent from TA2's naming
      apparatus by the matcher's construction and re-asserted
      here against the whole table.

Everything else is a hand decision below, each with its reason —
the same override discipline as tools/ta2_decide_fma.py. The
dominant lymphatic pattern: TA2 names node groups as regional
plural collective terms ('nodi occipitales', 'nodi axillares',
...) where the FMA carries a class per group; where the regional
name corresponds exactly, the record resolves to the collective
term (basis 'collective-term', the Milestone 35 pattern); where
TA2 divides the FMA's group or the FMA's group spans two TA2
terms, the record is ambiguous with those candidates. The script
fails loudly on any record no rule and no override covers.

Output: work/ta2/fma-<system>-decisions.json
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
TA2 = os.path.join(PROJECT, "data/sources/ta2-2.07/ta2-terms.json")
EXPECTED = {"lymphatic": 131, "endocrine": 14}

sys.path.insert(0, HERE)
from ta2_match_fma36 import norm, class_name_of, load_fma_latin  # noqa: E402


def cand_class(latin):
    la = (latin or "").lower()
    for pre, cls in (("nodi", "node"), ("nodus", "node"),
                     ("ductus", "duct"), ("truncus", "trunk"),
                     ("trunci", "trunk"), ("vasa", "vessel"),
                     ("vas", "vessel"), ("glandulae", "gland"),
                     ("glandula", "gland"), ("tonsilla", "tonsil"),
                     ("medulla", "medulla"), ("cortex", "cortex"),
                     ("pulpa", "pulp"), ("lobuli", "lobule"),
                     ("lobulus", "lobule"), ("lobus", "lobe"),
                     ("isthmus", "isthmus"), ("insulae", "islet"),
                     ("insula", "islet"), ("cisterna", "cisterna"),
                     ("trabeculae", "trabecula"),
                     ("trabecula", "trabecula"),
                     ("paraganglia", "paraganglion"),
                     ("plexus", "plexus"), ("lympha", "fluid")):
        if la.startswith(pre):
            return cls
    return "other"


def record_class(class_name):
    n = class_name.lower()
    if "lymph node" in n:
        return "node"
    if "lymphatic trunk" in n:
        return "trunk"
    if "cisterna" in n:
        return "cisterna"
    if "duct" in n:
        return "duct"
    if "capillary" in n or "lymphatic vessel" in n:
        return "vessel"
    if "tonsil" in n:
        return "tonsil"
    if "marrow" in n:
        return "medulla"
    if "pulp" in n:
        return "pulp"
    if "trabecula" in n:
        return "trabecula"
    if "lobule" in n:
        return "lobule"
    if "cortex" in n:
        return "cortex"
    if "medulla" in n:
        return "medulla"
    if "isthmus" in n:
        return "isthmus"
    if "lobe" in n and "thyroid" in n:
        return "lobe"
    if "thyroid gland" in n or "parathyroid" in n:
        return "gland"
    if "islet" in n:
        return "islet"
    if "paraganglion" in n:
        return "paraganglion"
    if "carotid body" in n:
        return "body"
    if "aggregated lymphoid follicle" in n:
        return "follicle"
    return "other"


def basis_of(term, record, fma_latin):
    """Basis from the record's own keys' provenance in the term's
    naming apparatus (Milestone 23 basis vocabulary), recomputed
    deterministically — copied from tools/ta2_decide_fma.py,
    importing the sibling matcher's norm/class_name_of."""
    name_keys = {norm(record["name"]), norm(class_name_of(record))}
    if record.get("side"):
        name_keys.add(re.sub(r"^(left|right)\s+", "",
                             norm(record["name"])))
    cfid = (record.get("class_concept_id") or "")[3:]
    latin_keys = {norm(eq) for eq in fma_latin.get(cfid, [])}
    base = name_keys | latin_keys
    if norm(term["latin"]) in base:
        return "latin-term" if term["english"] is None \
            else "preferred"
    if term["english"] and norm(term["english"]) in base:
        return "preferred"
    esyn = [norm(s) for s in term["english_synonyms"]]
    lsyn = [norm(s) for s in term["latin_synonyms"]]
    if any(k in esyn for k in name_keys):
        return "synonym"
    if any(k in lsyn for k in base):
        return "latin-synonym"
    if any(k in esyn for k in base):
        return "synonym"
    if any(k in [norm(s) for s in term["related_terms"]]
           for k in base):
        return "related-term"
    return "class-word-form"


def _res(ta_id, basis, reason):
    return {"status": "resolved", "ta_id": ta_id, "basis": basis,
            "reason": reason}


def _amb(cands, reason):
    return {"status": "ambiguous", "candidates": cands,
            "reason": reason}


def _nf(probes, reason):
    return {"status": "not_found", "probes": probes,
            "reason": reason}


def _coll(ta_id, latin, cname):
    return _res(ta_id, "collective-term",
                f"TA2 names this group only as the regional plural "
                f"collective term {ta_id} {latin}; the FMA class "
                f"'{cname}' is that group's generic.")


CLASS_OVERRIDES = {}

# -- node groups: TA2 regional collective terms, exact regional
#    correspondence (class-level; sided records take their
#    class's term per the Milestone 23 sidedness rule) -----------
_COLL_MAP = [
    ("Occipital lymph node", 5199, "nodi occipitales"),
    ("Mastoid lymph node", 5200, "nodi mastoidei"),
    ("Superficial parotid lymph node", 5201,
     "nodi parotidei superficiales"),
    ("Deep parotid lymph node", 5202, "nodi parotidei profundi"),
    ("Facial lymph node", 5206, "nodi faciales"),
    ("Submandibular lymph node", 5214, "nodi submandibulares"),
    ("Submental lymph node", 5213, "nodi submentales"),
    ("Anterior cervical lymph node", 5215,
     "nodi cervicales anteriores"),
    ("Lateral cervical lymph node", 5223,
     "nodi cervicales laterales"),
    ("Supraclavicular lymph node", 5233, "nodi supraclaviculares"),
    ("Retropharyngeal lymph node", 5234, "nodi retropharyngei"),
    ("Prelaryngeal lymph node", 5219, "nodi prelaryngei"),
    ("Pretracheal lymph node", 5221, "nodi pretracheales"),
    ("Axillary lymph node", 5236, "nodi axillares"),
    ("Apical axillary lymph node", 5237, "nodi axillares apicales"),
    ("Central axillary lymph node", 5238,
     "nodi axillares centrales"),
    ("Lateral axillary lymph node", 5239,
     "nodi axillares laterales"),
    ("Subscapular lymph node", 5240, "nodi axillares posteriores"),
    ("Brachial lymph node", 5244, "nodi brachiales"),
    ("Supratrochlear lymph node", 5246, "nodi supratrochleares"),
    ("Cubital lymph node", 5245, "nodi cubitales"),
    ("Tracheobronchial lymph node", 5261,
     "nodi tracheobronchiales"),
    ("Superior tracheobronchial lymph node", 5262,
     "nodi tracheobronchiales superiores"),
    ("Inferior tracheobronchial lymph node", 5263,
     "nodi tracheobronchiales inferiores"),
    ("Bronchopulmonary lymph node", 5266,
     "nodi bronchopulmonales"),
    ("Intercostal lymph node", 5251, "nodi intercostales"),
    ("Superior diaphragmatic lymph node", 5253,
     "nodi phrenici superiores"),
    ("Celiac lymph node", 5282, "nodi coeliaci"),
    ("Hepatic lymph node", 5299, "nodi hepatici"),
    ("Splenic lymph node", 5295, "nodi splenici"),
    ("Pancreatic lymph node", 5292, "nodi pancreatici"),
    ("Pancreaticoduodenal lymph node", 5296,
     "nodi pancreaticoduodenales"),
    ("Superior mesenteric lymph node", 5302,
     "nodi mesenterici superiores"),
    ("Inferior mesenteric lymph node", 5312,
     "nodi mesenterici inferiores"),
    ("Ileocolic lymph node", 5305, "nodi ileocolici"),
    ("Appendicular lymph node", 5308, "nodi appendiculares"),
    ("Lateral aortic lymph node", 5271, "nodi aortici laterales"),
    ("Common iliac lymph node", 5319, "nodi iliaci communes"),
    ("External iliac lymph node", 5325, "nodi iliaci externi"),
    ("Internal iliac lymph node", 5334, "nodi iliaci interni"),
    ("Gluteal lymph node", 5335, "nodi glutei"),
    ("Inguinal lymph node", 5348, "nodi inguinales"),
    ("Superficial inguinal lymph node", 5349,
     "nodi inguinales superficiales"),
    ("Deep inguinal lymph node", 5353, "nodi inguinales profundi"),
    ("Popliteal lymph node", 5357, "nodi poplitei"),
    ("Superficial popliteal lymph node", 5358,
     "nodi poplitei superficiales"),
    ("Deep popliteal lymph node", 5359, "nodi poplitei profundi"),
]
for _cname, _tid, _latin in _COLL_MAP:
    CLASS_OVERRIDES[_cname] = _coll(_tid, _latin, _cname)
# the subscapular correspondence is by position, stated in full
CLASS_OVERRIDES["Subscapular lymph node"] = _res(
    5240, "collective-term",
    "TA2 names the posterior axillary nodes 5240 nodi axillares "
    "posteriores; the subscapular group IS the posterior axillary "
    "group (the intake record carries the same note), and TA2 "
    "carries no 'subscapular' node term.")
# the superior phrenic nodes ARE TA2's superior diaphragmatic
# term — the FMA carries both group names, TA2 one term
CLASS_OVERRIDES["Superior phrenic lymph node"] = _res(
    5253, "collective-term",
    "TA2 names the superior diaphragmatic nodes 5253 nodi "
    "phrenici superiores; 'phrenic' and 'diaphragmatic' name the "
    "same group (the FMA carries both classes), and both "
    "records take the one term.")
# the esophageal nodes: TA2's juxta-oesophageal term, no English
CLASS_OVERRIDES["Esophageal lymph node"] = _res(
    5264, "latin-term",
    "TA2 names the esophageal nodes 5264 nodi juxtaoesophagei "
    "(no English equivalent served); no other TA2 term names "
    "them.")

# -- node groups TA2 divides, or that span two TA2 terms ---------
CLASS_OVERRIDES["Parotid lymph node"] = _amb(
    [5201, 5202],
    "TA2 divides the parotid nodes into the superficial set "
    "(5201 nodi parotidei superficiales) and the deep set (5202 "
    "nodi parotidei profundi, the intraglandular nodes 5205 "
    "named within that territory); the FMA class is the whole "
    "group, and no single TA2 term names it.")
CLASS_OVERRIDES["Deep lateral cervical lymph node"] = _amb(
    [5225, 5229],
    "TA2 divides the deep lateral cervical nodes into superior "
    "(5225) and inferior (5229) sets; the FMA class is the whole "
    "group, and no single TA2 term names it.")
CLASS_OVERRIDES["Paratracheal lymph node"] = _amb(
    [5222, 5260],
    "TA2 names the paratracheal nodes twice by region — 5222 "
    "nodi paratracheales colli and 5260 nodi paratracheales "
    "thoracis; the FMA class is the one chain along the trachea, "
    "and neither term alone names it.")
CLASS_OVERRIDES["Diaphragmatic lymph node"] = _amb(
    [5253, 5279],
    "TA2 names the diaphragmatic nodes as the superior set "
    "(5253 nodi phrenici superiores, thoracic) and the inferior "
    "set (5279 nodi phrenici inferiores, abdominal); the FMA "
    "class is undivided.")
CLASS_OVERRIDES["Mesenteric lymph node"] = _amb(
    [5302, 5312],
    "TA2 names the mesenteric nodes only in their superior "
    "(5302) and inferior (5312) divisions; the FMA class is the "
    "undivided group.")
CLASS_OVERRIDES["Sacral lymph node"] = _amb(
    [5324, 5338],
    "TA2 names the sacral nodes as the median set (5324 nodi "
    "sacrales mediani) and the lateral set (5338 nodi sacrales "
    "laterales); the FMA class is undivided.")
CLASS_OVERRIDES["Parathyroid gland"] = _amb(
    [3871, 3872],
    "TA2 names the parathyroid glands only in their superior "
    "(3871 glandula parathyroidea superior) and inferior (3872) "
    "division; the FMA class is the undivided gland, and no "
    "single TA2 term names it (the accessory gland 3873 is a "
    "variant, not the class).")
CLASS_OVERRIDES["Aggregated lymphoid follicle of small "
                "intestine"] = _amb(
    [2960, 2978],
    "TA2 names the aggregated lymphoid nodules only by organ — "
    "2960 noduli lymphoidei aggregati ilei (the Peyer's patches "
    "proper) and 2978 ... appendicis vermiformis; the FMA class "
    "is the small-intestine aggregate generally (its ileal "
    "specialisation FMA72027 corresponds to 2960), broader than "
    "either term.")

# -- the generic lymphatic vessel --------------------------------
CLASS_OVERRIDES["Lymphatic vessel"] = _res(
    3915, "collective-term",
    "TA2 names the lymphatic vessels only collectively, as the "
    "part heading 3915 vasa lymphatica (its children are the "
    "capillary 3918 and the plexus 3930); the FMA class is that "
    "category's generic. The capillary record resolves to 3918 "
    "mechanically.")

# -- tonsils: TA2 names each twice (digestive and lymphoid
#    chapters, identical Latin); this module is the lymphatic
#    module, so the lymphoid-chapter term is entered -------------
for _cname, _tid, _twin in [
        ("Palatine tonsil", 5181, 2853),
        ("Pharyngeal tonsil", 5186, 2865),
        ("Lingual tonsil", 5179, 2830),
        ("Tubal tonsil", 5189, 2872)]:
    CLASS_OVERRIDES[_cname] = _res(
        _tid, "preferred",
        f"TA2 names this tonsil twice under the identical Latin "
        f"'tonsilla' term — {_twin} in the digestive chapter and "
        f"{_tid} in the lymphoid chapter; these are lymphatic "
        f"records (Waldeyer's ring as lymphoid tissue), so the "
        f"lymphoid-chapter term {_tid} is entered.")

# -- interiors the matcher missed on name form --------------------
CLASS_OVERRIDES["Red pulp of spleen"] = _res(
    5175, "preferred",
    "FMA orders the name 'Red pulp of spleen'; TA2 names the "
    "same tissue 5175 pulpa rubra splenis (English 'red pulp') "
    "under 5174 pulpa splenis, which the pulp record takes.")
CLASS_OVERRIDES["White pulp of spleen"] = _res(
    5176, "preferred",
    "FMA orders the name 'White pulp of spleen'; TA2 names the "
    "same tissue 5176 pulpa alba splenis (English 'white pulp') "
    "under 5174 pulpa splenis, which the pulp record takes.")
CLASS_OVERRIDES["Lobule of thymus"] = _res(
    5154, "collective-term",
    "TA2 names the thymic lobules as the plural term 5154 lobuli "
    "thymi (under 5153 lobus thymi, the lobe — a different "
    "record's neighbour, not this one); the FMA class is the "
    "lobule generic.")
CLASS_OVERRIDES["Trabecula of spleen"] = _res(
    5173, "collective-term",
    "TA2 names the splenic trabeculae as the collective term "
    "5173 trabeculae splenis (English 'splenic trabeculae'); "
    "the FMA class is the trabecula generic.")

# -- not-found with specific reasons ------------------------------
CLASS_OVERRIDES["Tonsil"] = _nf(
    ["Tonsil", "tonsilla"],
    "TA2 names no generic tonsil: only the four named tonsils "
    "(palatina, pharyngea, lingualis, tubaria — each recorded) "
    "and the unrelated tonsilla cerebelli; the FMA's generic "
    "class has no TA2 counterpart.")
CLASS_OVERRIDES["Anterior mediastinal lymph node group"] = _nf(
    ["Anterior mediastinal lymph node group",
     "nodi mediastinales anteriores"],
    "TA2 folds the anterior mediastinal nodes into the "
    "brachiocephalic (5255) and pericardial (5258, 5259) terms "
    "under the mediastinal heading; no term names the anterior "
    "mediastinal group as such.")
CLASS_OVERRIDES["Posterior mediastinal lymph node"] = _nf(
    ["Posterior mediastinal lymph node",
     "nodi mediastinales posteriores"],
    "TA2 names no posterior mediastinal group; the posterior "
    "mediastinal territory is carried by the juxta-oesophageal "
    "(5264) and prevertebral (5252) terms, neither of which is "
    "this group.")
CLASS_OVERRIDES["Superior mediastinal lymph node"] = _nf(
    ["Superior mediastinal lymph node"],
    "TA2 carries no superior mediastinal node term; the "
    "superior mediastinal territory is inside the mediastinal "
    "heading 5254, which the mediastinal record takes.")
CLASS_OVERRIDES["Common hepatic lymph node"] = _nf(
    ["Common hepatic lymph node"],
    "TA2 names the hepatic nodes undivided (5299 nodi hepatici, "
    "which the hepatic record takes); no common hepatic term "
    "exists in its apparatus.")

# -- endocrine hand decisions --------------------------------------
CLASS_OVERRIDES["Pyramidal lobe of thyroid gland"] = _res(
    3867, "preferred",
    "TA2 names the pyramidal lobe 3867 lobus pyramidalis under "
    "the thyroid gland; the FMA class name carries the organ "
    "qualifier TA2 leaves to the chapter.")
CLASS_OVERRIDES["Pancreatic islet"] = _res(
    3128, "collective-term",
    "TA2 names the pancreatic islets only as the collective "
    "plural term 3128 insulae pancreaticae; the FMA class is "
    "that tissue's generic. The worksheet's other candidates "
    "are the pancreas's duct, veins, nodes and plexus — "
    "different structures (class mismatch).")
CLASS_OVERRIDES["Paraganglion"] = _res(
    3885, "collective-term",
    "TA2 names the paraganglia only as the collective heading "
    "term 3885 paraganglia, its named instances entered "
    "individually (the carotid body at 3886); the FMA class is "
    "the generic.")
CLASS_OVERRIDES["Carotid body"] = _res(
    3886, "preferred",
    "TA2 names the carotid body 3886 glomus caroticum (the "
    "FMA's own listed synonym for the class is 'Carotid "
    "glomus'); the structure is identical, the class word "
    "differs (glomus, not corpus).")

RECORD_OVERRIDES = {}
# -- sided records whose TA2 terms are themselves sided ----------
RECORD_OVERRIDES["lymph.left-gastric-lymph-node"] = _res(
    5284, "preferred",
    "TA2 names the gastric nodes sided: 5284 nodi gastrici "
    "sinistri for the left record.")
RECORD_OVERRIDES["lymph.right-gastric-lymph-node"] = _res(
    5283, "preferred",
    "TA2 names the gastric nodes sided: 5283 nodi gastrici "
    "dextri for the right record.")
RECORD_OVERRIDES["lymph.left-colic-lymph-node"] = _res(
    5314, "preferred",
    "TA2 names the colic nodes sided: 5314 nodi colici sinistri "
    "for the left record (the middle colic nodes 5311 are "
    "named within the superior mesenteric set, not this class).")
RECORD_OVERRIDES["lymph.right-colic-lymph-node"] = _res(
    5310, "preferred",
    "TA2 names the colic nodes sided: 5310 nodi colici dextri "
    "for the right record (the middle colic nodes 5311 are "
    "named within the superior mesenteric set, not this class).")
RECORD_OVERRIDES["lymph.left-lumbar-lymph-node-group"] = _res(
    5270, "preferred",
    "TA2 names the lumbar nodes sided: 5270 nodi lumbales "
    "sinistri for the left record.")
RECORD_OVERRIDES["lymph.right-lumbar-lymph-node-group"] = _res(
    5275, "preferred",
    "TA2 names the lumbar nodes sided: 5275 nodi lumbales "
    "dextri for the right record.")


def main():
    system = sys.argv[1]
    assert system in EXPECTED, system
    ws_path = os.path.join(PROJECT, "work/ta2",
                           f"fma-{system}-worksheet.json")
    inv_path = os.path.join(PROJECT, "data", system,
                            f"{system}-inventory.json")
    out_path = os.path.join(PROJECT, "work/ta2",
                            f"fma-{system}-decisions.json")
    ws = json.load(open(ws_path))
    terms = {t["ta_id"]: t for t in
             json.load(open(TA2))["terms"]}
    records = {r["record_id"]: r for r in
               json.load(open(inv_path))["records"]}
    fma_latin = load_fma_latin()
    apparatus = set()
    for t in terms.values():
        for s in [t["latin"], t["english"]] + t["latin_synonyms"] \
                + t["english_synonyms"] + t["related_terms"]:
            if s:
                apparatus.add(norm(s))

    decisions = {}
    unresolved = []
    for w in ws:
        rid, cname = w["record_id"], w["class_name"]
        ov = RECORD_OVERRIDES.get(rid) or CLASS_OVERRIDES.get(cname)
        if ov is not None:
            d = dict(ov)
            d["record_id"] = rid
            if d["status"] == "not_found":
                for p in d["probes"]:
                    assert norm(p) not in apparatus, (rid, p)
            decisions[rid] = d
            continue
        cands = w["candidates"]
        if not cands:
            # M4: no candidate anywhere in TA2's apparatus
            probes = sorted({w["name"], cname})
            for p in probes:
                assert norm(p) not in apparatus, (rid, p)
            decisions[rid] = {
                "record_id": rid, "status": "not_found",
                "probes": probes,
                "reason": f"TA2 names no term for the FMA class "
                          f"'{cname}': the record's names return "
                          f"no hit anywhere in the table's naming "
                          f"apparatus (preferred terms, synonyms, "
                          f"related terms)."}
            continue
        rc = record_class(cname)
        strong = [c for c in cands if c["via"] == "STRONG"]
        inclass = [c for c in strong
                   if cand_class(c["latin"]) == rc]
        pick = None
        if len(strong) == 1 and (cand_class(
                strong[0]["latin"]) == rc or rc == "other"):
            pick = strong[0]
        elif len(inclass) == 1:
            pick = inclass[0]
        elif len(cands) == 1 and cand_class(
                cands[0]["latin"]) in (rc, "other"):
            pick = cands[0]
        if pick is None:
            unresolved.append((rid, cname, w["auto"],
                               [(c["ta_id"], c["via"])
                                for c in cands]))
            continue
        t = terms[pick["ta_id"]]
        decisions[rid] = {
            "record_id": rid, "status": "resolved",
            "ta_id": pick["ta_id"],
            "basis": basis_of(t, records[rid], fma_latin),
            "reason": f"mechanical: {w['auto']}, sole in-class "
                      f"{pick['via']} candidate via key "
                      f"'{pick['key']}'"}

    if unresolved:
        print("UNRESOLVED BY RULES+OVERRIDES:")
        for u in unresolved:
            print("  ", u)
        sys.exit(1)
    assert len(decisions) == len(ws) == EXPECTED[system], \
        (len(decisions), len(ws))
    json.dump(decisions, open(out_path, "w"), indent=1)
    from collections import Counter
    print(Counter(d["status"] for d in decisions.values()))
    print(Counter(d.get("basis") for d in decisions.values()
                  if d["status"] == "resolved"))
    print("decisions:", len(decisions), "->", out_path)


if __name__ == "__main__":
    main()
