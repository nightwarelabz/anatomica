#!/usr/bin/env python3
"""Milestone 37 curation: turn the FMA-37 worksheets into
decisions. Sibling of tools/ta2_decide_fma36.py, system-
parameterized: `ta2_decide_fma37.py urinary|reproductive`.

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
the same override discipline as tools/ta2_decide_fma36.py. The
dominant patterns of this intake: TA2's served table carries NO
nephron-segment terms at all (glomerulus, tubules, collecting
duct, macula densa, juxtaglomerular apparatus, vasa recta are
Terminologia Histologica territory), so the nephron records are
not found in TA2 by whole families; TA2 names several FMA
singular classes as plural collectives (renal columns, major /
minor calices, fimbriae, lesser vestibular glands — the
collective-term pattern); and TA2 divides the un-sexed urethral
orifice and sphincter classes by sex, where the FMA classes are
un-sexed (ambiguous). For resolved overrides the basis is
computed from the record's own keys against the term's apparatus
(basis_of), except collective-term resolutions, whose basis is
the pattern itself. The script fails loudly on any record no
rule and no override covers.

Output: work/ta2/fma-<system>-decisions.json
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
TA2 = os.path.join(PROJECT, "data/sources/ta2-2.07/ta2-terms.json")
EXPECTED = {"urinary": 67, "reproductive": 57}

sys.path.insert(0, HERE)
from ta2_match_fma37 import norm, class_name_of, load_fma_latin  # noqa: E402


def cand_class(latin):
    la = (latin or "").lower()
    if "forni" in la:
        return "fornix"
    for pre, cls in (("cortex", "cortex"), ("medulla", "medulla"),
                     ("pyramis", "pyramid"), ("papilla", "papilla"),
                     ("pelvis", "pelvis"), ("sinus", "sinus"),
                     ("hilum", "hilum"), ("capsula", "capsule"),
                     ("fascia", "fascia"), ("lobus", "lobe"),
                     ("apex", "apex"), ("corpus", "body"),
                     ("fundus", "fundus"),
                     ("cervix vesicae", "neck"),
                     ("cervix", "cervix"), ("canalis", "canal"),
                     ("trigonum", "trigone"), ("uvula", "uvula"),
                     ("detrusor", "detrusor"),
                     ("plica", "fold"), ("ostium", "orifice"),
                     ("urethra", "urethra"), ("ovarium", "ovary"),
                     ("tuba", "tube"), ("uterus", "uterus"),
                     ("vagina", "vagina"), ("vulva", "vulva"),
                     ("clitoris", "clitoris"), ("labium", "labium"),
                     ("vestibulum", "vestibule"),
                     ("hymen", "hymen"), ("glandula", "gland"),
                     ("glandulae", "gland"),
                     ("ligamentum", "ligamentum"),
                     ("mesovarium", "mesovarium"),
                     ("mesosalpinx", "mesosalpinx"),
                     ("mesometrium", "mesometrium"),
                     ("perimetrium", "perimetrium"),
                     ("endometrium", "endometrium"),
                     ("myometrium", "myometrium"),
                     ("infundibulum", "infundibulum"),
                     ("ampulla", "ampulla"), ("isthmus", "isthmus"),
                     ("portio", "part"), ("pars", "part"),
                     ("sphincter", "sphincter"),
                     ("colliculus", "colliculus"),
                     ("crista", "crest"), ("glans", "glans")):
        if la.startswith(pre):
            return cls
    return "other"


def record_class(class_name):
    n = class_name.lower()
    for key, cls in (("vestibule", "vestibule"),
                     ("interureteric", "fold"),
                     ("cortex", "cortex"), ("medulla", "medulla"),
                     ("pyramid", "pyramid"), ("papilla", "papilla"),
                     ("renal pelvis", "pelvis"), ("sinus", "sinus"),
                     ("hilum", "hilum"), ("capsule", "capsule"),
                     ("fascia", "fascia"), ("lobe", "lobe"),
                     ("apex of", "apex"), ("body of", "body"),
                     ("fundus", "fundus"),
                     ("neck of urinary bladder", "neck"),
                     ("trigone", "trigone"), ("uvula", "uvula"),
                     ("detrusor", "detrusor"),
                     ("orifice", "orifice"),
                     ("part of", "part"),
                     ("glans", "glans"),
                     ("cervix", "cervix"),
                     ("mesovarium", "mesovarium"),
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
                     ("ligament", "ligamentum"),
                     ("gland", "gland"), ("sphincter", "sphincter"),
                     ("colliculus", "colliculus"),
                     ("uterine tube", "tube"), ("uterus", "uterus"),
                     ("ovary", "ovary"), ("urethra", "urethra"),
                     ("corpus", "body"),
                     ("body", "body")):
        if key in n:
            return cls
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
                f"TA2 names this structure only as the plural "
                f"collective term {ta_id} {latin}; the FMA class "
                f"'{cname}' is that structure's generic.")


CLASS_OVERRIDES = {}

# -- urinary: name-form bridges the matcher cannot build --------
CLASS_OVERRIDES["Cortex of kidney"] = _res(
    3368, None,
    "TA2 names the renal cortex 3368 cortex renis; the sole "
    "naming-apparatus bridge is that term (via its Latin "
    "synonym 'cortex renalis', the FMA class's own Latin "
    "equivalent). The worksheet's remaining candidates are "
    "class-word cores of other renal structures (medulla, "
    "lobe, pelvis, vessels) — class mismatch.")
CLASS_OVERRIDES["Medulla of kidney"] = _res(
    3369, None,
    "TA2 names the renal medulla 3369 medulla renis (English "
    "'renal medulla'); the FMA class's name form 'Medulla of "
    "kidney' occurs nowhere in TA2's apparatus in that order "
    "and the class carries no Latin-equivalent key for the "
    "matcher, which returned no candidate. The structure is "
    "identical and in-class (the medulla term sits beside "
    "3368 cortex renis, which the cortex records take).")
CLASS_OVERRIDES["Renal lobe"] = _res(
    3376, None,
    "TA2 names the renal lobe 3376 lobus renis (English "
    "'kidney lobe'); the matcher bridged only by a class-word "
    "core, and every other candidate is a different renal "
    "structure (cortex, medulla, pelvis, vessels, plexus).")

# -- urinary: TA2 plural collectives ------------------------------
CLASS_OVERRIDES["Renal column"] = _coll(
    3370, "columnae renales", "Renal column")
CLASS_OVERRIDES["Major calyx"] = _res(
    3385, "collective-term",
    "TA2 names the major calyces only as the plural collective "
    "term 3385 calices renales majores; the FMA class is the "
    "singular generic. (The worksheet's CORE candidates 1286 "
    "'pelvis major' and kin are bony-pelvis diameter terms — "
    "class mismatch, rejected.)")
CLASS_OVERRIDES["Minor calyx"] = _res(
    3389, "collective-term",
    "TA2 names the minor calyces only as the plural collective "
    "term 3389 calices renales minores; the FMA class is the "
    "singular generic. (The worksheet's CORE candidate 1287 "
    "'pelvis minor' is a bony-pelvis diameter term — class "
    "mismatch, rejected.)")

# -- urinary: TA2 carries no nephron terms (whole families) ------
_NEPHRON_NF = (
    "TA2's served table carries no nephron-segment terms at "
    "all — the uriniferous tubule and its parts are "
    "Terminologia Histologica territory, and no term in the "
    "table's naming apparatus names this structure.")
CLASS_OVERRIDES["Renal tubule"] = _nf(
    ["Renal tubule", "tubulus renalis"],
    _NEPHRON_NF + " The worksheet's candidates are class-word "
    "cores of other renal structures (cortex, medulla, "
    "pelvis, vessels) — class mismatch.")
CLASS_OVERRIDES["Renal corpuscle"] = _nf(
    ["Renal corpuscle", "corpusculum renis"],
    _NEPHRON_NF)

# -- urinary: the divided urethra ---------------------------------
CLASS_OVERRIDES["Pre-prostatic part of urethra"] = _res(
    3443, None,
    "TA2 names this part 3443 pars intramuralis urethrae "
    "masculinae, whose listed English synonym is "
    "'preprostatic part of urethra' and whose Latin synonyms "
    "include 'pars preprostatica urethrae'; the matcher "
    "missed on the FMA name's hyphenation ('Pre-prostatic').")
CLASS_OVERRIDES["Prostatic urethra"] = _res(
    3445, None,
    "TA2 names the prostatic urethra twice under the identical "
    "Latin 'pars prostatica urethrae' — 3445 in the urinary "
    "chapter and 3658 in the male genital chapter (under the "
    "prostate); the urethra is the urinary module's record "
    "(Milestone 12/14 boundary), so the urinary-chapter term "
    "3445 is entered (the Milestone 35 chapter-twin pattern).")
CLASS_OVERRIDES["Membranous urethra"] = _res(
    3453, None,
    "TA2 names the male membranous part 3453 pars membranacea "
    "urethrae masculinae (English 'membranous part of male "
    "urethra'); the FMA class is that segment (a child of "
    "'Segment of male urethra'). The worksheet's only "
    "candidate, 367 'os membranaceum', is a bone term — class "
    "mismatch, rejected.")
CLASS_OVERRIDES["Spongiose part of urethra"] = _res(
    3455, None,
    "TA2 names the spongy part 3455 pars spongiosa urethrae "
    "(English 'spongy urethra', synonym 'penile urethra'); "
    "the FMA class is that segment of the male urethra.")
CLASS_OVERRIDES["Urethral crest"] = _res(
    3446, None,
    "TA2 names the urethral crest sexed — 3446 crista "
    "urethralis masculina and 3430 crista urethralis "
    "feminina. The FMA class sits in the prostatic urethra: "
    "its IS-A path runs through 'Region of wall of prostatic "
    "part of urethra', beside the seminal colliculus — it is "
    "the male crest, and takes 3446.")
CLASS_OVERRIDES["External urethral sphincter"] = _amb(
    [3431, 3454],
    "TA2 names the external urethral sphincter only sexed — "
    "3431 sphincter externus urethrae femininae and 3454 "
    "sphincter externus urethrae masculinae; the FMA class is "
    "the un-sexed generic (a perineal muscle class), and "
    "neither term alone names it.")
CLASS_OVERRIDES["External urethral orifice"] = _amb(
    [3432, 3458],
    "TA2 names the external urethral orifice only sexed — "
    "3432 ostium externum urethrae femininae (named again at "
    "3557 in the female external genitalia chapter) and 3458 "
    "ostium externum urethrae masculinae; the FMA class is "
    "the un-sexed generic under 'Urethral orifice', and "
    "neither term alone names it.")

# -- reproductive --------------------------------------------------
CLASS_OVERRIDES["Ovarian ligament"] = _res(
    3834, None,
    "TA2 names the ovarian ligament 3834 ligamentum proprium "
    "ovarii; it is the sole naming-apparatus bridge (via "
    "synonym). The worksheet's remaining candidates are "
    "class-word cores of ovarian structures (medulla, cortex, "
    "vessels, plexus) — class mismatch.")
CLASS_OVERRIDES["Follicle of ovary"] = _nf(
    ["Follicle of ovary", "folliculi ovarici"],
    "TA2 names no generic ovarian follicle: only the "
    "vesicular stage (3482 folliculi ovarici vesiculosi) "
    "among the ovary's terms; the FMA class is the follicle "
    "generic, broader than the stage term. (The worksheet's "
    "only candidate, 3834 ligamentum proprium ovarii, is the "
    "ovarian ligament — class mismatch.)")
CLASS_OVERRIDES["Fimbria of uterine tube"] = _coll(
    3489, "fimbriae tubae uterinae", "Fimbria of uterine tube")
CLASS_OVERRIDES["Cavity of uterus"] = _res(
    3503, None,
    "TA2 names the uterine cavity 3503 cavitas uteri (English "
    "'uterine cavity'); the FMA class name orders the words "
    "'Cavity of uterus', which the matcher does not bridge.")
CLASS_OVERRIDES["Lesser vestibular gland"] = _coll(
    3564, "glandulae vestibulares minores",
    "Lesser vestibular gland")

RECORD_OVERRIDES = {}


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
