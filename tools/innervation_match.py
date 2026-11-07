#!/usr/bin/env python3
"""Milestone 35: innervation-link match worksheet.

Decomposes each of the muscle module's distinct innervation
phrases into named-nerve components by stated mechanical rules,
and for each component lists the exact-correspondence candidates
among the FMA-sourced nervous inventory records (Milestone 33):

  R1  the name equals an un-sided inventory record's name;
  R2  the name equals the preferred name of an FMA class that has
      inventory records — targets are all records of the class;
  R3  the name equals an FMA-listed synonym (fma:synonym) of such
      a class — targets are all records of the class;
  R4  collective: the name is the class name pluralised under the
      closed mapping {nerve->nerves, ramus->rami} (articles
      dropped) — targets are the class's records, or, when the
      class itself has none, the records of its direct OWL child
      classes whose names are level specialisations of it (the
      child's name ends with the class name: 'First intercostal
      nerve' under 'Intercostal nerve'; 'Subcostal nerve' does
      not qualify and is never swept in).

No fuzzy matching anywhere: every bridge is a string equality
against a name one of the two sources itself lists. This tool
PROPOSES; tools/innervation_decide.py decides and
tools/innervation_pass.py applies.

Output: work/innervation/worksheet.json
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
MUSCLES = os.path.join(PROJECT, "data/muscular/muscles.json")
INV = os.path.join(PROJECT, "data/nervous/nervous-inventory.json")
FMA_CLASSES = os.path.join(PROJECT, "work/fma/fma-classes.json")
OUT = os.path.join(PROJECT, "work/innervation/worksheet.json")


def norm_name(s):
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\bthe\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def plural_form(class_name):
    toks = class_name.lower().split(" ")
    out = [{"nerve": "nerves", "ramus": "rami"}.get(t, t)
           for t in toks]
    return " ".join(out)


def decompose(phrase):
    """Phrase -> [{segment, name, role, qualifier}]. Mechanical:
    ';' separates components; a leading 'territory:' prefix is a
    qualifier; '(may also receive a branch from the X)' and
    ', with contributions from the X' yield contributory
    components; 'A component of the B' names B with qualifier A
    component; other trailing parentheticals are qualifiers;
    'A and B <stem> nerves' expands to the two named nerves."""
    comps = []

    def add(name, role, qualifier, segment):
        comps.append({"segment": segment,
                      "name": norm_name(name), "role": role,
                      "qualifier": qualifier})

    for seg in phrase.split(";"):
        seg = seg.strip()
        original = seg
        m = re.match(r"^[^:()]{1,40}:\s*(.+)$", seg)
        territory = None
        if m:
            territory = seg[:seg.index(":")].strip()
            seg = m.group(1).strip()
        m = re.search(r"\(may also receive a branch from the "
                      r"(.+?)\)\s*$", seg)
        if m:
            add(m.group(1), "contributory",
                "branch (phrase: may also receive)", original)
            seg = seg[:m.start()].strip()
        m = re.search(r",\s*with contributions from the (.+)$", seg)
        if m:
            add(m.group(1), "contributory", "contributions",
                original)
            seg = seg[:m.start()].strip()
        quals = []
        if territory:
            quals.append(territory)
        m = re.match(r"^(.+?) component of the (.+)$",
                     re.sub(r"\s*\(.*?\)\s*$", "", seg))
        if m:
            pm = re.search(r"\((.*?)\)\s*$", seg)
            if pm:
                quals.append(pm.group(1))
            quals.append(f"{m.group(1)} component")
            add(m.group(2), "primary", "; ".join(quals), original)
            continue
        pm = re.search(r"\((.*?)\)\s*$", seg)
        if pm:
            quals.append(pm.group(1))
            seg = seg[:pm.start()].strip()
        else:
            # inline parenthetical before the class word:
            # 'deep fibular (peroneal) nerve'
            im = re.match(r"^(.+?)\s*\((.*?)\)\s+(nerve|nerves|"
                          r"ramus|rami|plexus|ganglion)$", seg)
            if im:
                quals.append(im.group(2))
                seg = f"{im.group(1)} {im.group(3)}"
        m = re.match(r"^(.+?) and (.+?) (\w+) nerves$", seg)
        if m:
            add(f"{m.group(1)} {m.group(3)} nerve", "primary",
                "; ".join(quals) or None, original)
            add(f"{m.group(2)} {m.group(3)} nerve", "primary",
                "; ".join(quals) or None, original)
            continue
        add(seg, "primary", "; ".join(quals) or None, original)
    return comps


def main():
    mus = json.load(open(MUSCLES))
    mrecs = mus["records"] if isinstance(mus, dict) else mus
    phrases = sorted({r["innervation"]["nerve"] for r in mrecs
                      if r.get("innervation")
                      and r["innervation"].get("nerve")})
    inv = json.load(open(INV))
    classes = json.load(open(FMA_CLASSES))

    def class_fid_of(r):
        if r.get("class_concept_id"):
            return r["class_concept_id"][3:]
        cid = r["concept_ids"][0][3:]
        if r.get("side"):
            want = re.sub(r"^(Left|Right) ", "", r["name"])
            for p in classes.get(cid, {}).get("parents", []):
                if classes.get(p, {}).get("name") == want:
                    return p
        return cid

    fma_recs = [r for r in inv["records"]
                if r.get("source") == "fma-5.1.0"]
    by_class = {}
    rec_class = {}
    for r in fma_recs:
        cf = class_fid_of(r)
        rec_class[r["record_id"]] = cf
        by_class.setdefault(cf, []).append(r["record_id"])
    for v in by_class.values():
        v.sort()
    class_name = {cf: classes.get(cf, {}).get("name")
                  for cf in by_class}
    by_class_name = {}
    for cf, nm in class_name.items():
        if nm:
            by_class_name.setdefault(norm_name(nm), []).append(cf)
    by_synonym = {}
    for cf in by_class:
        for s in classes.get(cf, {}).get("synonyms", []):
            by_synonym.setdefault(norm_name(s), []).append(cf)
    unsided_by_name = {norm_name(r["name"]): r["record_id"]
                       for r in fma_recs if not r.get("side")}
    # OWL-wide probes (any class, intaken or not)
    owl_by_name, owl_by_syn = {}, {}
    for cid, info in classes.items():
        if info.get("name"):
            owl_by_name.setdefault(norm_name(info["name"]),
                                   []).append(cid)
        for s in info.get("synonyms", []):
            owl_by_syn.setdefault(norm_name(s), []).append(cid)
    children = {}
    for cid, info in classes.items():
        for p in info.get("parents", []):
            children.setdefault(p, []).append(cid)
    by_plural = {}
    for cid, info in classes.items():
        if info.get("name"):
            by_plural.setdefault(plural_form(info["name"]),
                                 []).append(cid)

    RESTRICT_TOKENS = {"cervical", "thoracic", "lumbar", "sacral",
                       "upper", "lower"}

    def candidates(name):
        out = []
        if name in unsided_by_name:
            out.append({"rule": "R1", "class_fmaid": None,
                        "class_name": None,
                        "record_ids": [unsided_by_name[name]]})
        for cf in by_class_name.get(name, []):
            out.append({"rule": "R2", "class_fmaid": "FMA" + cf,
                        "class_name": class_name[cf],
                        "record_ids": by_class[cf]})
        for cf in by_synonym.get(name, []):
            out.append({"rule": "R3", "class_fmaid": "FMA" + cf,
                        "class_name": class_name[cf],
                        "record_ids": by_class[cf]})
        for cid in by_plural.get(name, []):
            info = classes[cid]
            direct = by_class.get(cid, [])
            if direct:
                out.append({"rule": "R4", "class_fmaid": "FMA" + cid,
                            "class_name": info["name"],
                            "record_ids": direct,
                            "r4_form": "class records"})
            else:
                lvl = []
                for kid in children.get(cid, []):
                    kn = classes.get(kid, {}).get("name")
                    if kn and kn.lower().endswith(
                            info["name"].lower()):
                        lvl += by_class.get(kid, [])
                if lvl:
                    out.append({"rule": "R4",
                                "class_fmaid": "FMA" + cid,
                                "class_name": info["name"],
                                "record_ids": sorted(lvl),
                                "r4_form": "level-class records"})
        return out

    def near_miss(name):
        """Strip restriction tokens; if the stripped plural name
        resolves R4-style, report the generic class it hits."""
        toks = [t for t in name.split(" ")
                if t not in RESTRICT_TOKENS
                and not re.fullmatch(r"[a-z]\d+-[a-z]\d+|[a-z]\d+",
                                     t)]
        stripped = " ".join(toks)
        if stripped == name:
            return None
        for c in candidates(stripped):
            if c["rule"] == "R4":
                return {"stripped_name": stripped,
                        "class_fmaid": c["class_fmaid"],
                        "class_name": c["class_name"],
                        "record_ids": c["record_ids"]}
        return None

    worksheet = []
    for p in phrases:
        comps = []
        for c in decompose(p):
            entry = dict(c)
            entry["candidates"] = candidates(c["name"])
            entry["near_miss"] = near_miss(c["name"])
            entry["owl_probe"] = {
                "class_by_name": owl_by_name.get(c["name"], []),
                "class_by_synonym":
                    owl_by_syn.get(c["name"], []),
            }
            comps.append(entry)
        worksheet.append({"phrase": p, "components": comps})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(worksheet, open(OUT, "w"), indent=1)
    n_comp = sum(len(w["components"]) for w in worksheet)
    print(f"worksheet: {len(worksheet)} phrases, {n_comp} "
          f"components -> {OUT}")
    for w in worksheet:
        for c in w["components"]:
            tag = ",".join(sorted({x["rule"]
                                   for x in c["candidates"]})) \
                or "NONE"
            print(f"  [{tag}] {c['name']} ({c['role']})"
                  f"  <- {w['phrase'][:60]}")


if __name__ == "__main__":
    sys.exit(main())
