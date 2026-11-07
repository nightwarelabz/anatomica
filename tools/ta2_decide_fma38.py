#!/usr/bin/env python3
"""Milestone 38 curation: turn the FMA-38 worksheets into
decisions. Sibling of tools/ta2_decide_fma37.py, system-
parameterized: `ta2_decide_fma38.py integumentary|reproductive`.
The reproductive decisions cover the 76 Milestone 38 male
records only; the pass tool merges them with the Milestone
37 decisions for the file's earlier records.

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

Everything else is a hand decision below, each with its reason.
The dominant patterns of this intake: TA2's served table carries
NO epidermal stratum terms and NO epidermal cell terms at all
(the strata and the skin's cells are Terminologia Histologica
territory, as the nephron segments were at Milestone 37), and no
cutaneous corpuscle terms; TA2 names several FMA singular classes
as plural collectives (sweat glands, beard hairs, septa and
lobules of testis, straight tubules, efferent ductules); TA2
names the nail and the nail bed once, undivided, where the FMA
divides them by digit and by region (the Milestone 35 containment
pattern — ambiguous); and two name-form bridges the matcher
cannot build (the dermis layers without their 'of dermis'
qualifier; the transitional zone's adjective form; the seminal
vesicle under its TA2 name 'glandula seminalis'). For resolved
overrides the basis is computed from the record's own keys
against the term's apparatus (basis_of), except collective-term
resolutions, whose basis is the pattern itself. The script fails
loudly on any record no rule and no override covers.

Output: work/ta2/fma38-<system>-decisions.json
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
TA2 = os.path.join(PROJECT, "data/sources/ta2-2.07/ta2-terms.json")
EXPECTED = {"integumentary": 53, "reproductive": 76}

sys.path.insert(0, HERE)
from ta2_match_fma38 import norm, class_name_of, load_fma_latin  # noqa: E402

_CAND_PRE = (
    ("tela subcutanea", "hypodermis"),
    ("folliculus", "follicle"), ("stipes", "shaft"),
    ("lamina unguis", "nail-plate"), ("matrix unguis", "matrix"),
    ("radix unguis", "root"), ("lunula", "lunule"),
    ("lectulus", "nail-bed"), ("unguis", "nail"),
    ("cilia", "eyelash"), ("papilla mammaria", "nipple"),
    ("areola", "areola"), ("glandula mammaria", "mammary"),
    ("glandula sebacea", "sebaceous"),
    ("glandulae sudoriferae", "sweat"),
    ("glandula sudorifera", "sweat"),
    ("ductus deferens", "duct"), ("ductus ejaculatorius", "duct"),
    ("ductus epididymidis", "duct"), ("ductus", "duct"),
    ("rete testis", "rete"),
    ("mediastinum testis", "mediastinum-testis"),
    ("tunica", "tunica"), ("caput", "head"), ("cauda", "tail"),
    ("basis", "base"), ("zona", "zone"),
    ("funiculus", "cord"), ("scrotum", "scrotum"),
    ("fascia", "fascia"), ("cremaster", "cremaster"),
    ("musculus dartos", "dartos"),
    ("plexus pampiniformis", "pampiniform"),
    ("penis", "penis"), ("radix", "root"), ("bulbus", "bulb"),
    ("collum", "neck"), ("preputium", "prepuce"),
    ("frenulum", "frenulum"), ("corona", "corona"),
    ("epidermis", "epidermis"), ("dermis", "dermis"),
    ("pili", "hair"),
)
_CAND_BASE = (
    ("cortex", "cortex"), ("medulla", "medulla"),
    ("pyramis", "pyramid"), ("papilla", "papilla"),
    ("pelvis", "pelvis"), ("sinus", "sinus"),
    ("hilum", "hilum"), ("capsula", "capsule"),
    ("fascia", "fascia"), ("lobus", "lobe"),
    ("apex", "apex"), ("corpus", "body"),
    ("fundus", "fundus"), ("cervix vesicae", "neck"),
    ("cervix", "cervix"), ("canalis", "canal"),
    ("trigonum", "trigone"), ("uvula", "uvula"),
    ("detrusor", "detrusor"), ("plica", "fold"),
    ("ostium", "orifice"), ("urethra", "urethra"),
    ("ovarium", "ovary"), ("tuba", "tube"), ("uterus", "uterus"),
    ("vagina", "vagina"), ("vulva", "vulva"),
    ("clitoris", "clitoris"), ("labium", "labium"),
    ("vestibulum", "vestibule"), ("hymen", "hymen"),
    ("glandula", "gland"), ("glandulae", "gland"),
    ("ligamentum", "ligamentum"), ("mesovarium", "mesovarium"),
    ("mesosalpinx", "mesosalpinx"),
    ("mesometrium", "mesometrium"),
    ("perimetrium", "perimetrium"),
    ("endometrium", "endometrium"),
    ("myometrium", "myometrium"),
    ("infundibulum", "infundibulum"),
    ("ampulla", "ampulla"), ("isthmus", "isthmus"),
    ("portio", "part"), ("pars", "part"),
    ("sphincter", "sphincter"), ("colliculus", "colliculus"),
    ("crista", "crest"), ("glans", "glans"),
)


def cand_class(latin):
    la = (latin or "").lower()
    if "forni" in la:
        return "fornix"
    for pre, cls in _CAND_PRE + _CAND_BASE:
        if la.startswith(pre):
            return cls
    return "other"


_REC_PRE = (
    ("mediastinum of testis", "mediastinum-testis"),
    ("ampulla of", "ampulla"),
    ("part of deferent duct", "part"),
    ("body of nail", "nail-plate"), ("body of", "body"),
    ("septum of testis", "septum"),
    ("tunica vaginalis", "tunica"),
    ("tunica albuginea", "tunica"),
    ("rete testis", "rete"),
    ("head of", "head"), ("tail of", "tail"),
    ("base of", "base"),
    ("lobe of prostate", "lobe"), ("zone of prostate", "zone"),
    ("spermatic cord", "cord"),
    ("cremasteric muscle", "cremaster"), ("dartos", "dartos"),
    ("pampiniform", "pampiniform"),
    ("root of", "root"), ("bulb of", "bulb"),
    ("neck of", "neck"),
    ("prepuce", "prepuce"), ("frenulum", "frenulum"),
    ("corona", "corona"),
    ("hair follicle", "follicle"), ("hair shaft", "shaft"),
    ("hair root", "root"), ("hair papilla", "papilla"),
    ("hair matrix", "matrix"), ("cortex of hair", "hair-part"),
    ("cuticle of hair", "hair-part"),
    ("dermal papilla", "papilla"),
    ("nail matrix", "matrix"), ("root of nail", "root"),
    ("nail bed", "nail-bed"),
    ("nail", "nail"),
    ("mammary gland", "mammary"), ("nipple", "nipple"),
    ("areola", "areola"), ("lactiferous", "duct"),
    ("sebaceous", "sebaceous"), ("sweat gland", "sweat"),
    ("hypodermis", "hypodermis"), ("epidermis", "epidermis"),
    ("dermis", "dermis"),
    ("eyelash", "eyelash"), ("beard", "beard"),
    ("scrotum", "scrotum"), ("fascia", "fascia"),
    ("duct of epididymis", "duct"), ("duct of seminal", "duct"),
    ("deferent duct", "duct"), ("ejaculatory", "duct"),
    ("penis", "penis"),
)
_REC_BASE = (
    ("vestibule", "vestibule"), ("interureteric", "fold"),
    ("cortex", "cortex"), ("medulla", "medulla"),
    ("pyramid", "pyramid"), ("papilla", "papilla"),
    ("renal pelvis", "pelvis"), ("sinus", "sinus"),
    ("hilum", "hilum"), ("capsule", "capsule"),
    ("fascia", "fascia"), ("lobe", "lobe"),
    ("apex of", "apex"), ("body of", "body"),
    ("fundus", "fundus"), ("neck of urinary bladder", "neck"),
    ("trigone", "trigone"), ("uvula", "uvula"),
    ("detrusor", "detrusor"), ("orifice", "orifice"),
    ("part of", "part"), ("glans", "glans"),
    ("cervix", "cervix"), ("mesovarium", "mesovarium"),
    ("mesosalpinx", "mesosalpinx"),
    ("mesometrium", "mesometrium"),
    ("serosa of uterus", "perimetrium"),
    ("endometrium", "endometrium"),
    ("myometrium", "myometrium"),
    ("infundibulum", "infundibulum"),
    ("ampulla", "ampulla"), ("isthmus", "isthmus"),
    ("fornix", "fornix"), ("hymen", "hymen"),
    ("labium", "labium"), ("clitoris", "clitoris"),
    ("vulva", "vulva"), ("vagina", "vagina"),
    ("ligament", "ligamentum"), ("gland", "gland"),
    ("sphincter", "sphincter"), ("colliculus", "colliculus"),
    ("uterine tube", "tube"), ("uterus", "uterus"),
    ("ovary", "ovary"), ("urethra", "urethra"),
    ("corpus", "body"), ("body", "body"),
)


def record_class(class_name):
    n = class_name.lower()
    for key, cls in _REC_PRE + _REC_BASE:
        if key in n:
            return cls
    return "other"


def basis_of(term, record, fma_latin):
    """Basis from the record's own keys' provenance in the term's
    naming apparatus (Milestone 23 basis vocabulary),
    recomputed deterministically — copied from
    tools/ta2_decide_fma37.py."""
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
                f"TA2 names this structure only as the plural "
                f"collective term {ta_id} {latin}; the FMA class "
                f"'{cname}' is that structure's generic.")


CLASS_OVERRIDES = {}

# -- integumentary: the subcutaneous layer, named once ---------
CLASS_OVERRIDES["Superficial fascia"] = _res(
    7083, None,
    "TA2 names the subcutaneous layer once, 7083 tela "
    "subcutanea, whose listed English synonym is 'superficial "
    "fascia' — the term's own apparatus names this record's "
    "structure. The term is shared with the Hypodermis record: "
    "TA2 carries the layer under one term, and the FMA carries "
    "it under two classes. (The worksheet's other STRONG "
    "candidate, 32 'superficialis', is the general adjective "
    "term, not the layer.)")
CLASS_OVERRIDES["Body of nail"] = _res(
    7066, None,
    "TA2's nail plate term 7066 lamina unguis lists 'body of "
    "nail' as its English synonym; the FMA class is the plate "
    "under its body name. (The worksheet's STRONG candidate "
    "7065 unguis is the whole nail — class mismatch.)")
CLASS_OVERRIDES["Root of nail"] = _res(
    7076, None,
    "TA2 names the nail root 7076 radix unguis (under 7065 "
    "unguis); the worksheet bridges to it only by a class-word "
    "core. Its other CORE candidates are the roots of penis "
    "and nerve — class mismatch.")
CLASS_OVERRIDES["Lunule of nail"] = _res(
    7067, None,
    "TA2 names the lunule 7067 lunula unguis, the sole STRONG "
    "candidate; the class-word machinery cannot map 'lunula' "
    "to this record's class, so the mechanical rules leave it.")
CLASS_OVERRIDES["Papillary layer of dermis"] = _res(
    7048, None,
    "TA2 names the papillary layer 7048 stratum papillare in "
    "the dermis section — its parent chain runs through 7047 "
    "dermis — without the 'of dermis' qualifier the FMA class "
    "name carries; the matcher does not bridge the qualifier.")
CLASS_OVERRIDES["Reticular layer of dermis"] = _res(
    7050, None,
    "TA2 names the reticular layer 7050 stratum reticulare "
    "in the dermis section (parent chain through 7047 "
    "dermis), without the 'of dermis' qualifier the FMA "
    "class name carries; the matcher does not bridge the "
    "qualifier.")
CLASS_OVERRIDES["Sweat gland"] = _coll(
    7079, "glandulae sudoriferae", "Sweat gland")
CLASS_OVERRIDES["Beard"] = _coll(
    7058, "pili barbae", "Beard")

# -- integumentary: TA2 names it once, the FMA divides it ------
CLASS_OVERRIDES["Nail of finger"] = _amb(
    [7065],
    "TA2 names the nail once, undivided by digit (7065 "
    "unguis); the term's denotation strictly contains this "
    "record's (the nails of the fingers only) — the "
    "Milestone 35 containment pattern, so the term is not "
    "entered.")
CLASS_OVERRIDES["Nail of toe"] = _amb(
    [7065],
    "TA2 names the nail once, undivided by digit (7065 "
    "unguis); the term's denotation strictly contains this "
    "record's (the nails of the toes only) — the Milestone "
    "35 containment pattern, so the term is not entered.")
CLASS_OVERRIDES["Nail bed of finger"] = _amb(
    [7074],
    "TA2 names the nail bed once, undivided (7074 lectulus, "
    "under 7065 unguis); the FMA divides it by region "
    "(finger and toe generics, then per-digit classes), and "
    "the generic term's denotation strictly contains this "
    "record's — the Milestone 35 containment pattern.")
CLASS_OVERRIDES["Nail bed of toe"] = _amb(
    [7074],
    "TA2 names the nail bed once, undivided (7074 lectulus, "
    "under 7065 unguis); the FMA divides it by region "
    "(finger and toe generics, then per-digit classes), and "
    "the generic term's denotation strictly contains this "
    "record's — the Milestone 35 containment pattern.")

# -- integumentary: the epidermal strata — no terms at all -----
_STRATA_NF = (
    "TA2's served table names the epidermis whole (7046) but "
    "carries no layer term for it in any form — the strata "
    "are Terminologia Histologica territory, as the nephron "
    "segments were at Milestone 37.")
CLASS_OVERRIDES["Basal cell layer of epidermis"] = _nf(
    ["Basal cell layer of epidermis", "Stratum basale"],
    _STRATA_NF)
CLASS_OVERRIDES["Prickle cell layer of epidermis"] = _nf(
    ["Prickle cell layer of epidermis", "Stratum spinosum"],
    _STRATA_NF)
CLASS_OVERRIDES["Granular layer of epidermis"] = _nf(
    ["Granular layer of epidermis", "Stratum granulosum"],
    _STRATA_NF)
CLASS_OVERRIDES["Stratum lucidum of epidermis"] = _nf(
    ["Stratum lucidum of epidermis"], _STRATA_NF)
CLASS_OVERRIDES["Horny layer of epidermis"] = _nf(
    ["Horny layer of epidermis", "Stratum corneum"],
    _STRATA_NF)

# -- integumentary: the epidermal cells — no terms at all ------
_CELL_NF = (
    "TA2's served table names no epidermal cell terms at "
    "all — the skin's cells are Terminologia Histologica "
    "territory, as the nephron segments were at Milestone "
    "37.")
CLASS_OVERRIDES["Melanocyte"] = _nf(["Melanocyte"], _CELL_NF)
CLASS_OVERRIDES["Merkel cell"] = _nf(["Merkel cell"], _CELL_NF)
CLASS_OVERRIDES["Langerhans cell"] = _nf(
    ["Langerhans cell"], _CELL_NF)
CLASS_OVERRIDES["Keratinized cell of epidermis"] = _nf(
    ["Keratinized cell of epidermis", "Keratinocyte"],
    _CELL_NF + " The FMA itself carries no class named "
    "'Keratinocyte'; this record and the nonkeratinized cell "
    "are its keratinocyte classes.")
CLASS_OVERRIDES["Nonkeratinized cell of epidermis"] = _nf(
    ["Nonkeratinized cell of epidermis", "Keratinocyte"],
    _CELL_NF + " The FMA itself carries no class named "
    "'Keratinocyte'; this record and the keratinized cell "
    "are its keratinocyte classes.")

# -- integumentary: the cutaneous corpuscles — no terms --------
CLASS_OVERRIDES["Pacinian corpuscle"] = _nf(
    ["Pacinian corpuscle", "corpusculum lamellosum"],
    "TA2's served table names no lamellar (Pacinian) "
    "corpuscle term anywhere in its naming apparatus; the "
    "cutaneous corpuscles are Terminologia Histologica "
    "territory in the served table, as the epidermal strata "
    "are.")
CLASS_OVERRIDES["Meissner's corpuscle"] = _nf(
    ["Meissner's corpuscle", "corpusculum tactus"],
    "TA2's served table names no tactile (Meissner) "
    "corpuscle term anywhere in its naming apparatus; the "
    "worksheet's sole candidate, 6728 plexus submucosus, is "
    "a submucosal nerve plexus — class mismatch. The "
    "cutaneous corpuscles are Terminologia Histologica "
    "territory in the served table.")

# -- integumentary: the hair apparatus beyond shaft/follicle --
_HAIR_NF = (
    "TA2's hair apparatus in the served table is exactly "
    "7053 pili, 7064 folliculus pili, 7063 stipes pili, 7057 "
    "cilia and 7058 pili barbae; the worksheet's CORE "
    "candidates are the shaft and the follicle — class "
    "mismatch — and no term names this record's structure.")
CLASS_OVERRIDES["Hair root"] = _nf(["Hair root"], _HAIR_NF)
CLASS_OVERRIDES["Hair papilla"] = _nf(["Hair papilla"], _HAIR_NF)
CLASS_OVERRIDES["Hair matrix"] = _nf(["Hair matrix"], _HAIR_NF)

# -- reproductive: collectives of the testis chapter -----------
CLASS_OVERRIDES["Septum of testis"] = _coll(
    3596, "septula testis", "Septum of testis")
CLASS_OVERRIDES["Lobule of testis"] = _coll(
    3597, "lobuli testis", "Lobule of testis")
CLASS_OVERRIDES["Straight seminiferous tubule of testis"] = \
    _coll(3600, "tubuli seminiferi recti",
          "Straight seminiferous tubule of testis")
CLASS_OVERRIDES["Efferent ductule"] = _coll(
    3602, "ductuli efferentes testis", "Efferent ductule")

# -- reproductive: name-form bridges and the chapter twin ------
CLASS_OVERRIDES["Mediastinum of testis"] = _res(
    3595, None,
    "TA2 names the mediastinum of testis 3595, the sole "
    "in-class STRONG candidate; the other STRONG candidate, "
    "3333 'mediastinum', is the thoracic mediastinum — class "
    "mismatch.")
CLASS_OVERRIDES["Cremasteric muscle"] = _res(
    3617, None,
    "TA2 names the cremaster twice under the identical Latin "
    "'cremaster' — 2374 in the muscle chapter and 3617 in "
    "the male genital chapter (under 3615 funiculus "
    "spermaticus); this record is a spermatic cord content, "
    "so the genital-chapter term 3617 is entered (the "
    "Milestone 37 chapter-twin pattern).")
CLASS_OVERRIDES["Transition zone of prostate"] = _res(
    3648, None,
    "TA2 names the transitional zone 3648 zona transitionalis "
    "prostatae (English 'transitional zone of prostate'); "
    "the FMA class's name form 'Transition zone' differs in "
    "the adjective, which the matcher does not bridge.")
CLASS_OVERRIDES["Duct of seminal vesicle"] = _res(
    3635, None,
    "TA2 names the seminal vesicle 'glandula seminalis' "
    "(3631) and its duct 3635 ductus excretorius glandulae "
    "seminalis, 'excretory duct of seminal gland' — the duct "
    "that joins the ampulla of the deferent duct to form the "
    "ejaculatory duct, which is this record's structure. The "
    "name forms share no key the matcher can bridge.")

# -- reproductive: named in the chapter, absent as terms -------
CLASS_OVERRIDES["Seminiferous tubule of testis"] = _nf(
    ["Seminiferous tubule of testis", "tubuli seminiferi"],
    "TA2 names the seminiferous tubule only as its two "
    "kinds, both plural collectives — 3599 tubuli seminiferi "
    "contorti and 3600 tubuli seminiferi recti (the straight "
    "kind is taken by its own record); neither names the "
    "generic class, and no generic term exists in the table "
    "(the Milestone 37 ovarian-follicle pattern).")
CLASS_OVERRIDES["Central zone of prostate"] = _amb(
    [3647],
    "TA2 carries 'zona centralis prostatae' only as a "
    "related term of 3647 zona glandularum periurethralium "
    "prostatae — the periurethral glandular zone, a "
    "neighboring but distinct McNeal zone (the central zone "
    "surrounds the ejaculatory ducts; the periurethral "
    "glands lie within the transitional zone). The name is "
    "in the table's apparatus but is not this record's term, "
    "so it is not entered.")
CLASS_OVERRIDES["Anterior fibromuscular stroma of prostate"] = \
    _nf(["Anterior fibromuscular stroma of prostate"],
        "No term in TA2's prostate chapter names the "
        "anterior fibromuscular stroma (the chapter names "
        "the glandular part, its zones and the prostatic "
        "ducts).")
CLASS_OVERRIDES["Lobe of prostate"] = _nf(
    ["Lobe of prostate", "lobus prostatae"],
    "TA2 names only the middle lobe (3645 lobus medius "
    "prostatae) and the lateral part (3644) of the prostate; "
    "the generic lobe and its sided forms have no term. The "
    "worksheet's candidates are class-word cores of other "
    "prostate structures (commissure, capsule, fascia, "
    "veins) — class mismatch.")
_TUNICA_NF = (
    "TA2 names the tunica vaginalis whole (3584 tunica "
    "vaginalis testis); its layers are not separately named "
    "in the served table.")
CLASS_OVERRIDES["Visceral layer of tunica vaginalis of testis"] = \
    _nf(["Visceral layer of tunica vaginalis of testis"],
        _TUNICA_NF)
CLASS_OVERRIDES["Parietal layer of tunica vaginalis of testis"] = \
    _nf(["Parietal layer of tunica vaginalis of testis"],
        _TUNICA_NF)

RECORD_OVERRIDES = {}


def main():
    system = sys.argv[1]
    assert system in EXPECTED, system
    ws_path = os.path.join(PROJECT, "work/ta2",
                           f"fma38-{system}-worksheet.json")
    inv_path = os.path.join(PROJECT, "data", system,
                            f"{system}-inventory.json")
    out_path = os.path.join(PROJECT, "work/ta2",
                            f"fma38-{system}-decisions.json")
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
            if d["status"] == "resolved" and d.get("basis") is None:
                d["basis"] = basis_of(terms[d["ta_id"]],
                                      records[rid], fma_latin)
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
