#!/usr/bin/env python3
"""ANATOMICA Milestone 23: TA2 match worksheet builder.

Generates match candidates for every clinical record (361) against
the extracted TA2 2.07 table (data/sources/ta2-2.07/ta2-terms.json).
This tool PROPOSES; it never writes tranche data. Proposals land in
work/ta2/worksheet.json and a per-system digest is printed for human
review. Final decisions are curated in work/ta2/decisions.json and
applied by tools/ta2_pass.py.

Matching is lookup-only: a candidate exists only because a TA2 term
(or its listed synonym / related term) actually carries the string.
Normalisation is symmetric (case, punctuation, diacritics, ae/oe
folding) and is used for KEYS ONLY — the entered ta_name is always
the exact Latin string from the TA2 table.

Candidate provenance tags:
  STRONG  record key == TA2 preferred English or Latin term
  SYN     record key == a TA2-listed English/Latin synonym
  REL     record key == a TA2-listed related term (weaker: TA2 calls
          it related, not equivalent — always individually reviewed)
  CORE    match only after stripping a class word (muscle / artery /
          musculus / arteria / ...) from one side
Levels starting 'H' in TA2 are hierarchy headings; a heading can
still be the structure itself (e.g. 3932 cor), so headings are
flagged, not excluded.
"""

import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

PROJECT = "/home/hatch/workspace/anatomica-project"
TA2 = os.path.join(PROJECT, "data/sources/ta2-2.07/ta2-terms.json")
OUT = os.path.join(PROJECT, "work/ta2/worksheet.json")

TRANCHES = {
    "cardiovascular": "data/cardiovascular/cardiovascular.json",
    "digestive": "data/digestive/digestive.json",
    "endocrine": "data/endocrine/endocrine.json",
    "integumentary": "data/integumentary/integumentary.json",
    "lymphatic": "data/lymphatic/lymphatic.json",
    "muscular": "data/muscular/muscles.json",
    "nervous": "data/nervous/nervous.json",
    "reproductive": "data/reproductive/reproductive.json",
    "respiratory": "data/respiratory/respiratory.json",
    "urinary": "data/urinary/urinary.json",
}
INVENTORIES = [
    "data/cardiovascular/cv-inventory.json",
    "data/digestive/digestive-inventory.json",
    "data/endocrine/endocrine-inventory.json",
    "data/integumentary/integumentary-inventory.json",
    "data/lymphatic/lymphatic-inventory.json",
    "data/muscular/muscle-inventory.json",
    "data/nervous/nervous-inventory.json",
    "data/reproductive/reproductive-inventory.json",
    "data/respiratory/respiratory-inventory.json",
    "data/urinary/urinary-inventory.json",
    "data/skeletal/fma-mapping.json",
]

CLASS_WORDS_EN = ["muscles", "muscle", "arteries", "artery", "veins",
                  "vein", "nerves", "nerve", "duct", "gland", "bone",
                  "joint", "ligament", "nodes", "node", "vessel",
                  "vessels", "canal", "plexus", "ganglion", "cartilage"]
CLASS_WORDS_LA = ["musculus", "musculi", "arteria", "vena", "nervus",
                  "nervi", "ductus", "glandula", "articulatio",
                  "ligamentum", "cartilago", "plexus", "ganglion"]


def norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("æ", "ae").replace("œ", "oe")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # symmetric ae/oe folding (coeliac~celiac, oesophagus~esophagus)
    s = s.replace("ae", "e").replace("oe", "e")
    return s


def core_keys(key):
    """Derived weaker keys: strip one leading/trailing class word."""
    out = set()
    words = key.split(" ")
    if not words:
        return out
    if words[-1] in CLASS_WORDS_EN or words[-1] in CLASS_WORDS_LA:
        out.add(" ".join(words[:-1]))
    if words[0] in CLASS_WORDS_EN or words[0] in CLASS_WORDS_LA:
        out.add(" ".join(words[1:]))
    return {k for k in out if k}


def main():
    ta2 = json.load(open(TA2))["terms"]
    by_id = {t["ta_id"]: t for t in ta2}

    def chapter(tid):
        cur = by_id.get(tid)
        seen = []
        while cur:
            seen.append(cur)
            cur = by_id.get(cur["parent"]) if cur["parent"] else None
        for t in seen:
            if t["level"] in ("H2", "H1"):
                return t["ta_id"], t["latin"]
        return (seen[-1]["ta_id"], seen[-1]["latin"]) if seen else (None, None)

    # indexes: key -> {ta_id: via}
    idx = defaultdict(dict)

    def add(key, tid, via):
        if not key:
            return
        prev = idx[key].get(tid)
        rank = {"STRONG": 0, "SYN": 1, "REL": 2, "CORE": 3}
        if prev is None or rank[via] < rank[prev]:
            idx[key][tid] = via

    for t in ta2:
        tid = t["ta_id"]
        strong = [norm(t["english"]), norm(t["latin"])]
        syn = [norm(x) for x in t["english_synonyms"]] + \
              [norm(x) for x in t["latin_synonyms"]]
        rel = [norm(x) for x in t["related_terms"]]
        for k in strong:
            add(k, tid, "STRONG")
        for k in syn:
            add(k, tid, "SYN")
        for k in rel:
            add(k, tid, "REL")
        for k in strong + syn + rel:
            for ck in core_keys(k):
                add(ck, tid, "CORE")

    # FMA class-name corroboration via inventory records
    inv_by_id = {}
    for rel in INVENTORIES:
        p = os.path.join(PROJECT, rel)
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        concepts = {c["fma_id"]: c["name"] for c in d.get("concepts", [])}
        for r in d.get("records", []):
            rid = r.get("record_id") or r.get("id")
            if rid:
                inv_by_id[rid] = {
                    "name": r.get("name"),
                    "class_concept_id": r.get("class_concept_id"),
                    "class_name": concepts.get(r.get("class_concept_id")),
                }

    worksheet = []
    for system, rel in TRANCHES.items():
        d = json.load(open(os.path.join(PROJECT, rel)))
        for r in d["records"]:
            rid = r.get("id") or r.get("record_id")
            name = r["name"]
            rtype = r.get("type") or r.get("kind") or ""
            geo_ids = r.get("geometry_record_ids") or \
                (r.get("geometry") or {}).get("inventory_record_ids") or []
            fma_names = []
            for g in geo_ids:
                inv = inv_by_id.get(g)
                if inv:
                    for v in (inv["class_name"], inv["name"]):
                        if v and v not in fma_names:
                            fma_names.append(v)
            # record-side keys
            base = re.sub(r"\([^)]*\)", "", name)  # drop "(CN I)" etc.
            keys = {norm(base), norm(name)}
            m = re.match(r"^(left|right)\s+(.*)$", norm(base))
            side = None
            if m:
                side = m.group(1)
                keys.add(m.group(2))
            expanded = set(keys)
            for k in keys:
                expanded |= core_keys(k)
            # class word from the record's own type
            tw = norm(str(rtype)).replace("_", " ").split(" ")
            for w in tw:
                if w in CLASS_WORDS_EN:
                    for k in list(keys):
                        expanded.add(k + " " + w)
            cands = {}
            for k in expanded:
                if not k:
                    continue
                for tid, via in idx.get(k, {}).items():
                    prev = cands.get(tid)
                    rank = {"STRONG": 0, "SYN": 1, "REL": 2, "CORE": 3}
                    if prev is None or rank[via] < rank[prev["via"]]:
                        t = by_id[tid]
                        ch_id, ch_la = chapter(tid)
                        cands[tid] = {
                            "ta_id": tid, "latin": t["latin"],
                            "english": t["english"], "level": t["level"],
                            "via": via, "chapter_id": ch_id,
                            "chapter": ch_la, "key": k,
                        }
            cand_list = sorted(cands.values(),
                               key=lambda c: (c["via"] != "STRONG",
                                              c["via"] != "SYN",
                                              c["via"] != "REL",
                                              c["ta_id"]))
            t_only = [c for c in cand_list
                      if not c["level"].startswith("H")]
            if len(t_only) == 1 and t_only[0]["via"] == "STRONG" \
                    and len(cand_list) == 1:
                auto = "unique-strong"
            elif not cand_list:
                auto = "none"
            elif len(cand_list) == 1:
                auto = "unique-weak"
            else:
                auto = "multi"
            worksheet.append({
                "system": system, "record_id": rid, "name": name,
                "type": str(rtype), "side": side,
                "fma_names": fma_names[:4],
                "auto": auto, "candidates": cand_list,
            })
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(worksheet, f, ensure_ascii=False, indent=1)
    from collections import Counter
    print(Counter(w["auto"] for w in worksheet))
    print(f"worksheet: {len(worksheet)} records -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
