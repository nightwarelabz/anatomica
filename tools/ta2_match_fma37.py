#!/usr/bin/env python3
"""ANATOMICA Milestone 37: TA2 match worksheet builder for the
FMA-sourced urinary (67) and reproductive (57) inventory records
(Milestone 37 intake).

Sibling of tools/ta2_match_fma36.py (Milestone 36), system-
parameterized: `ta2_match_fma37.py urinary|reproductive`. Same
discipline and candidate machinery (STRONG / SYN / REL / CORE
provenance, class-word core keys, the FMA class's own Latin
equivalents as keys); the class-word vocabularies gain the new
systems' class nouns (tubule, calyx, pelvis, capsule, corpuscle,
sphincter, tube in English; ren, ureter, urethra, vesica,
uterus, ovarium, tuba, vagina, cervix, calix, pelvis, tubulus,
glomerulus, corpusculum, fornix, hymen, labium in Latin). The
FMA Latin-equivalent extraction counts owl:Class nesting depth
(the Milestone 36 repair).

This tool PROPOSES; it never writes inventory data. Proposals
land in work/ta2/fma-<system>-worksheet.json. Decisions are
curated by tools/ta2_decide_fma37.py and applied by
tools/ta2_pass_fma37.py.
"""

import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

PROJECT = "/home/hatch/workspace/anatomica-project"
TA2 = os.path.join(PROJECT, "data/sources/ta2-2.07/ta2-terms.json")

CLASS_WORDS_EN = ["muscles", "muscle", "arteries", "artery", "veins",
                  "vein", "nerves", "nerve", "duct", "gland", "bone",
                  "joint", "ligament", "nodes", "node", "vessel",
                  "vessels", "canal", "plexus", "ganglion", "cartilage",
                  "trunk", "tonsil", "lobe", "isthmus", "follicle",
                  "medulla", "cortex", "capillary", "pulp", "marrow",
                  "body", "lobule", "trabecula", "islet", "islets",
                  "ducts", "trunks", "tubule", "calyx", "pelvis",
                  "capsule", "corpuscle", "sphincter", "tube",
                  "junction", "crest", "orifice", "fornix"]
CLASS_WORDS_LA = ["musculus", "musculi", "arteria", "vena", "nervus",
                  "nervi", "ductus", "glandula", "articulatio",
                  "ligamentum", "cartilago", "plexus", "ganglion",
                  "truncus", "tonsilla", "lobus", "isthmus",
                  "folliculus", "medulla", "cortex", "corpus",
                  "insula", "paraganglion", "nodus", "nodi", "vas",
                  "cisterna", "trabecula", "lobulus", "pulpa",
                  "ren", "ureter", "urethra", "vesica", "uterus",
                  "ovarium", "tuba", "vagina", "cervix", "calix",
                  "pelvis", "tubulus", "glomerulus",
                  "corpusculum", "fornix", "hymen", "labium",
                  "clitoris", "vestibulum", "ampulla", "fundus",
                  "collum", "portio"]


def norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("æ", "ae").replace("œ", "oe")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("ae", "e").replace("oe", "e")
    return s


def core_keys(key):
    out = set()
    words = key.split(" ")
    if not words:
        return out
    if words[-1] in CLASS_WORDS_EN or words[-1] in CLASS_WORDS_LA:
        out.add(" ".join(words[:-1]))
    if words[0] in CLASS_WORDS_EN or words[0] in CLASS_WORDS_LA:
        out.add(" ".join(words[1:]))
    return {k for k in out if k}


def class_name_of(r):
    """The record's FMA class name: for a sided record, the
    un-sided namesake class (group_path parent where recorded,
    else the side-stripped name); for an un-sided record, its
    own name."""
    if not r.get("side"):
        return r["name"]
    gp = r.get("group_path") or []
    if len(gp) >= 2 and isinstance(gp[-2], str):
        return gp[-2]
    name = r["name"]
    for pre in ("Left ", "Right "):
        if name.startswith(pre):
            return name[len(pre):]
    return name


def load_fma_latin():
    """{FMAID: [non-English equivalents]} from fma.owl — the
    FMA's own Latin naming apparatus for each class, used as
    match keys. Block boundaries count owl:Class nesting depth
    (net of self-closing references): the Milestone 36 repair —
    a block must not end at a nested restriction's close."""
    import zipfile
    owl = os.path.join(PROJECT, "work/fma/fma.owl")
    if not os.path.exists(owl):
        os.makedirs(os.path.dirname(owl), exist_ok=True)
        with zipfile.ZipFile(os.path.join(
                PROJECT, "data/sources/fma-5.1.0/fma.zip")) as zf:
            zf.extract("fma.owl", os.path.dirname(owl))

    def net(line):
        opens = len(re.findall(r"<owl:Class(?=[\s>])", line))
        selfclosed = len(re.findall(r"<owl:Class[^>]*/>", line))
        return opens - selfclosed - line.count("</owl:Class>")

    latin = {}
    block = []
    depth = 0
    with open(owl, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if depth == 0:
                if "<owl:Class rdf:about=" not in line:
                    continue
                block = [line]
                depth = net(line)
            else:
                block.append(line)
                depth += net(line)
            if depth == 0 and block:
                text = "".join(block)
                block = []
                m = re.search(r'fma/fma(\d+)"', text)
                if m:
                    eqs = re.findall(
                        r"<fma:non-English_equivalent>([^<]+)"
                        r"</fma:non-English_equivalent>", text)
                    if eqs:
                        latin[m.group(1)] = eqs
    return latin


def main():
    system = sys.argv[1]
    assert system in ("urinary", "reproductive"), system
    inv_path = os.path.join(PROJECT, "data", system,
                            f"{system}-inventory.json")
    out_path = os.path.join(PROJECT, "work/ta2",
                            f"fma-{system}-worksheet.json")
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

    inv = json.load(open(inv_path))
    fma_latin = load_fma_latin()
    worksheet = []
    for r in inv["records"]:
        if r.get("source") != "fma-5.1.0":
            continue
        cname = class_name_of(r)
        keys = {norm(r["name"]), norm(cname)}
        if r.get("side"):
            stripped = re.sub(r"^(left|right)\s+", "",
                              norm(r["name"]))
            keys.add(stripped)
        cfid = (r.get("class_concept_id") or "")[3:]
        for eq in fma_latin.get(cfid, []):
            keys.add(norm(eq))
        expanded = set(keys)
        for k in keys:
            expanded |= core_keys(k)
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
        t_only = [c for c in cand_list if not c["level"].startswith("H")]
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
            "record_id": r["record_id"], "name": r["name"],
            "class_name": cname, "side": r.get("side"),
            "class_concept_id": r.get("class_concept_id"),
            "concept_id": (r.get("concept_ids") or [None])[0],
            "subtree": r.get("subtree"),
            "auto": auto, "candidates": cand_list,
        })
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(worksheet, f, ensure_ascii=False, indent=1)
    from collections import Counter
    print(Counter(w["auto"] for w in worksheet))
    print(f"worksheet: {len(worksheet)} records -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
