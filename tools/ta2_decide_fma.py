#!/usr/bin/env python3
"""Milestone 35 curation: turn the FMA worksheet into decisions.

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
      structure class is compatible resolves with that basis.

Everything else is a hand decision below, each with its reason —
the same override discipline as tools/ta2_decide.py. The script
fails loudly on any record no rule and no override covers.

Output: work/ta2/fma-decisions.json
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
WS = os.path.join(PROJECT, "work/ta2/fma-worksheet.json")
TA2 = os.path.join(PROJECT, "data/sources/ta2-2.07/ta2-terms.json")
INV = os.path.join(PROJECT, "data/nervous/nervous-inventory.json")
OUT = os.path.join(PROJECT, "work/ta2/fma-decisions.json")

sys.path.insert(0, HERE)
from ta2_match_fma import norm, class_name_of, load_fma_latin  # noqa: E402
# norm() is the matcher's own (it folds ae->e and oe->e, which is
# how 'plexus oesophageus' and 'plexus esophageus' meet); basis
# derivation must use the same folding or it misreads provenance.


def cand_class(latin):
    la = (latin or "").lower()
    for pre, cls in (("plexus", "plexus"), ("ganglion", "ganglion"),
                     ("nervus", "nerve"), ("nervi", "nerve"),
                     ("radix", "root"), ("ramus", "ramus"),
                     ("rami", "ramus"), ("truncus", "trunk"),
                     ("divisio", "division"),
                     ("fasciculus", "cord"), ("dura", "meninx"),
                     ("pia", "meninx"), ("arachnoidea", "meninx"),
                     ("falx", "sheet"), ("tentorium", "sheet"),
                     ("diaphragma", "sheet"), ("ligamentum", "sheet"),
                     ("cauda", "cord-part"), ("conus", "cord-part"),
                     ("intumescentia", "cord-part"),
                     ("filum", "cord-part")):
        if la.startswith(pre):
            return cls
    return "other"


def record_class(class_name):
    n = class_name.lower()
    # the brachial architecture records name the plexus as their
    # container; their own structure word comes first
    if "division of" in n:
        return "division"
    if "trunk" in n:
        return "trunk"
    if "cord of" in n:
        return "cord"
    if "plexus" in n:
        return "plexus"
    if "ganglion" in n:
        return "ganglion"
    if n.startswith("anterior root") or n.startswith("posterior root"):
        return "root"
    if "ramus of" in n:
        return "ramus"
    if "mater" in n:
        return "meninx"
    if any(w in n for w in ("falx", "tentorium", "diaphragma",
                            "ligament")):
        return "sheet"
    if any(w in n for w in ("cauda equina", "conus", "enlargement",
                            "filum")):
        return "cord-part"
    if "nerve" in n:
        return "nerve"
    return "other"


def basis_of(term, record, fma_latin):
    """Basis from the record's own keys' provenance in the term's
    naming apparatus (Milestone 23 basis vocabulary), recomputed
    deterministically: the worksheet stores only one key per term,
    and which one survives is not the provenance question. Only
    base keys count (name, class name, side-stripped name, the FMA
    class's Latin equivalents) — a resolution that rests on a
    class-word-stripped core key alone is 'class-word-form'."""
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


# ---------------------------------------------------------------------
# Hand decisions. Class-level templates apply to every record of the
# class (both sides); record-level entries win over class-level.
# ---------------------------------------------------------------------

def _res(ta_id, basis, reason):
    return {"status": "resolved", "ta_id": ta_id, "basis": basis,
            "reason": reason}


def _amb(cands, reason):
    return {"status": "ambiguous", "candidates": cands,
            "reason": reason}


ORDINAL = ["first", "second", "third", "fourth", "fifth", "sixth",
           "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth"]
LAT_ORD = ["primus", "secundus", "tertius", "quartus", "quintus",
           "sextus", "septimus", "octavus", "nonus", "decimus",
           "undecimus", "duodecimus"]

CLASS_OVERRIDES = {}

# -- per-level spinal nerves: TA2 names the spinal nerve only
#    generically; a level record is a member of that denotation,
#    not the denotation itself — the Milestone 23 ambiguous
#    pattern (candidate's denotation strictly contains the
#    record's), not a resolution and not a not-found -------------
_REGION = [("cervical", "6363 nervi cervicales"),
           ("thoracic", "6467 nervi thoracici"),
           ("lumbar", "6489 nervi lumbales"),
           ("sacral", "6507 nervi sacrales")]
for region, heading in _REGION:
    n = 8 if region == "cervical" else 12 if region == "thoracic" \
        else 5
    for i in range(n):
        cname = f"{ORDINAL[i].capitalize()} {region} nerve"
        CLASS_OVERRIDES[cname] = _amb(
            [6143],
            f"TA2 names the spinal nerve only generically (6143 "
            f"nervus spinalis) and under regional plural group "
            f"headings ({heading}, under 6362 nervi spinales); no "
            f"per-level term names the {ORDINAL[i]} {region} "
            f"nerve, and the generic term denotes every spinal "
            f"nerve, not this level's.")

# -- per-level intercostal nerves: same pattern, generic term 6472 --
for i in range(11):
    cname = f"{ORDINAL[i].capitalize()} intercostal nerve"
    CLASS_OVERRIDES[cname] = _amb(
        [6472],
        "TA2 names the intercostal nerve only generically "
        "(6472 nervus intercostalis, under 6470 rami anteriores "
        "nervorum thoracicorum); no per-level term names the "
        f"{ORDINAL[i]} intercostal nerve, and the generic term "
        "denotes every intercostal nerve, not this level's.")

# -- per-level lumbar splanchnic nerves: collective term only -------
for i in range(4):
    cname = f"{ORDINAL[i].capitalize()} lumbar splanchnic nerve"
    CLASS_OVERRIDES[cname] = _amb(
        [6635],
        "TA2 names the lumbar splanchnic nerves only as the "
        "collective set term 6635 nervi splanchnici lumbales; "
        f"no per-level term names the {ORDINAL[i]} lumbar "
        "splanchnic nerve, which is one member of that set.")

# -- brachial plexus divisions: TA2 names them, in its own order -----
_DIV = {("Superior", "anterior"): 6399, ("Superior", "posterior"): 6400,
        ("Middle", "anterior"): 6402, ("Middle", "posterior"): 6403,
        ("Inferior", "anterior"): 6405, ("Inferior", "posterior"): 6406}
_TRUNK = {"Superior": 6398, "Middle": 6401, "Inferior": 6404}
for (lvl, ap), tid in _DIV.items():
    cname = f"{lvl} {ap} division of brachial plexus"
    CLASS_OVERRIDES[cname] = _res(
        tid, "preferred",
        f"FMA orders the name '{lvl.lower()} {ap} division of "
        f"brachial plexus'; TA2 names the same division as the "
        f"{ap} division of the {lvl.lower()} trunk (term {tid}, "
        f"under trunk term {_TRUNK[lvl]}). No other TA2 term names "
        f"a per-trunk division.")

# -- collective terms: TA2 names the structure only as a set ---------
CLASS_OVERRIDES["Supraclavicular nerve"] = _res(
    6391, "collective-term",
    "TA2 names the supraclavicular nerves only as the plural set "
    "term 6391 nervi supraclaviculares (its children 6392-6394 "
    "are the medial/intermediate/lateral subsets); the FMA class "
    "is that nerve set's generic.")
CLASS_OVERRIDES["Sacral splanchnic nerve"] = _res(
    6636, "collective-term",
    "TA2 names the sacral splanchnic nerves only as the plural "
    "set term 6636 nervi splanchnici sacrales; the FMA class is "
    "that nerve set's generic.")
CLASS_OVERRIDES["Pelvic splanchnic nerve"] = _res(
    6685, "collective-term",
    "TA2 names the pelvic splanchnic nerves only as the plural "
    "set term 6685 nervi splanchnici pelvici; the FMA class is "
    "that nerve set's generic.")
CLASS_OVERRIDES["Celiac ganglion"] = _res(
    6639, "collective-term",
    "TA2 names the celiac ganglia only as the plural pair term "
    "6639 ganglia coeliaca (no English equivalent served); the "
    "FMA class is that ganglion (FMA itself lists the synonym "
    "'Coeliac ganglion').")

# -- FMA inserts 'nerve' where TA2 does not ---------------------------
CLASS_OVERRIDES["Submucosal nerve plexus"] = _res(
    6728, "preferred",
    "FMA inserts 'nerve' in the class name; TA2's 6728 plexus "
    "submucosus is the same (Meissner) plexus, paired with the "
    "myenteric plexus 6727 under the intramural plexuses in both "
    "sources.")

# -- the pharyngeal plexus: the mechanical candidate is a nerve ------
CLASS_OVERRIDES["Pharyngeal nerve plexus"] = _res(
    6338, "preferred",
    "The mechanical candidate 6223 nervus pharyngeus is the "
    "pharyngeal nerve, a different structure (class mismatch: "
    "this record is a plexus, FMA class FMA82453 'Pharyngeal "
    "nerve plexus'); TA2 names the plexus at 6338 plexus "
    "pharyngeus.")

# -- myenteric: FMA's own equivalent list also names the neighbour ---
CLASS_OVERRIDES["Myenteric nerve plexus"] = _res(
    6727, "preferred",
    "The class's FMA non-English equivalents include both "
    "'Plexus myentericus' and 'Plexus submucosus' (an FMA data "
    "quirk — the two enteric plexus classes share a parent); "
    "the record's preferred Latin equivalent and its English "
    "name are decisive for 6727 plexus myentericus.")

# -- the undivided aortic plexus --------------------------------------
CLASS_OVERRIDES["Aortic plexus"] = _amb(
    [6658, 6695],
    "TA2 names the aortic plexus only as its two regional parts "
    "(6658 plexus aorticus thoracicus, 6695 plexus aorticus "
    "abdominalis); the FMA class is the undivided plexus, and no "
    "single TA2 term names it.")

# -- the posterior cutaneous name collision ---------------------------
CLASS_OVERRIDES["Posterior cutaneous nerve"] = _amb(
    [6566],
    "Name collision, not identity: TA2 6566 nervus cutaneus "
    "posterior femoris is the posterior cutaneous nerve of "
    "thigh, a sacral-plexus branch; the FMA class (FMA77561) is "
    "a branch of the lateral branch of the posterior ramus of "
    "a spinal nerve (its IS-A path), a different structure. TA2 "
    "names posterior cutaneous branches of posterior rami only "
    "regionally and plurally (6369, 6370, 6469); no term names "
    "this class.")

RECORD_OVERRIDES = {}

# -- the six sided plexus records whose FMA class carries an
#    rdfs:label but no fma:preferred_name (Milestone 33 left
#    class_concept_id unrecorded for exactly these) ------------------
_SIDED_PLEXUS = [
    ("nerve.left-brachial-nerve-plexus", 6395, "FMA5906",
     "Brachial nerve plexus"),
    ("nerve.right-brachial-nerve-plexus", 6395, "FMA5906",
     "Brachial nerve plexus"),
    ("nerve.left-lumbar-nerve-plexus", 6517, "FMA5908",
     "Lumbar nerve plexus"),
    ("nerve.right-lumbar-nerve-plexus", 6517, "FMA5908",
     "Lumbar nerve plexus"),
    ("nerve.left-lumbosacral-nerve-plexus", 6516, "FMA5907",
     "Lumbosacral nerve plexus"),
    ("nerve.right-lumbosacral-nerve-plexus", 6516, "FMA5907",
     "Lumbosacral nerve plexus"),
]
for rid, tid, cfid, cname in _SIDED_PLEXUS:
    RECORD_OVERRIDES[rid] = _res(
        tid, "preferred",
        f"The record's OWL IS-A parent class {cfid} is the "
        f"un-sided class '{cname}' (it carries an rdfs:label but "
        f"no fma:preferred_name, which is why Milestone 33 left "
        f"class_concept_id unrecorded); TA2 names that class at "
        f"{tid}. Per the Milestone 23 sidedness rule, a sided "
        f"record takes its class's un-sided term.")

# annotations appended to mechanical resolutions
NOTE_OVERRIDES = {
    "nerve.filum-terminale": (
        "TA2 splits the filum into internum (5414, the pial part) "
        "and externum (5384, the dural part); the bare name "
        "'filum terminale' appears in 5414's related terms and in "
        "no other term's apparatus."),
}


def main():
    ws = json.load(open(WS))
    terms = {t["ta_id"]: t for t in
             json.load(open(TA2))["terms"]}
    records = {r["record_id"]: r for r in
               json.load(open(INV))["records"]}
    fma_latin = load_fma_latin()
    # probe integrity: every recorded not-found probe must return
    # no hit anywhere in the table's naming apparatus
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
        rc = record_class(cname)
        strong = [c for c in cands if c["via"] == "STRONG"]
        # in-class means the candidate's structure class IS the
        # record's — TA2's chapter-1 adjective terms (medianus,
        # radialis, ...) class as 'other' and never compete with a
        # true in-class term
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
        d = {"record_id": rid, "status": "resolved",
             "ta_id": pick["ta_id"],
             "basis": basis_of(t, records[rid], fma_latin),
             "reason": f"mechanical: {w['auto']}, sole in-class "
                       f"{pick['via']} candidate via key "
                       f"'{pick['key']}'"}
        if rid in NOTE_OVERRIDES:
            d["note"] = NOTE_OVERRIDES[rid]
        decisions[rid] = d

    if unresolved:
        print("UNRESOLVED BY RULES+OVERRIDES:")
        for u in unresolved:
            print("  ", u)
        sys.exit(1)
    assert len(decisions) == len(ws) == 286, (len(decisions),
                                              len(ws))
    json.dump(decisions, open(OUT, "w"), indent=1)
    from collections import Counter
    print(Counter(d["status"] for d in decisions.values()))
    print(Counter(d.get("basis") for d in decisions.values()
                  if d["status"] == "resolved"))
    print("decisions:", len(decisions), "->", OUT)


if __name__ == "__main__":
    main()
