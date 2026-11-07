#!/usr/bin/env python3
"""Milestone 35: innervation-link decisions.

Applies the resolution rules to the worksheet
(tools/innervation_match.py) deterministically:

  D1  a component with candidates resolves to them (rule
      precedence R1 > R2 > R3 > R4; multiple candidate entries
      must agree on the target record set — disagreement fails
      the run for curation, it is never silently picked);
  D2  a component whose name restricts a generic class to a
      region/level subset (the worksheet's near-miss fired) does
      NOT link to the generic class's record — the absence
      stands, with the near-miss named in the reason;
  D3  a component with no candidates whose name is an FMA class
      (preferred name or listed synonym, full-OWL probe) that
      Milestone 33 did not intake is absent — the class exists,
      the record does not;
  D4  a component with no candidates and no FMA class is absent.

Also recomputes the BEFORE census under Milestone 9/33 semantics
(the old nerve_check C8 full-phrase equality) for the artifact's
before/after accounting.

Output: work/innervation/decisions.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
WS = os.path.join(PROJECT, "work/innervation/worksheet.json")
OUT = os.path.join(PROJECT, "work/innervation/decisions.json")
RULE_ORDER = ["R1", "R2", "R3", "R4"]

# Documented reason overrides (the mechanical D4 text would lose
# a near-miss worth naming; the outcome is unchanged — absent).
REASON_OVERRIDES = {
    "anterior interosseous branch of median nerve": (
        "the phrase's name matches neither the preferred name "
        "nor any listed synonym of the evidently intended class "
        "FMA44822 'Anterior interosseous nerve' (the median "
        "nerve's anterior interosseous branch under its shorter "
        "FMA name), and that class was not intaken at Milestone "
        "33 in any case; no inventory record exists to link."),
    "recurrent branch of median nerve": (
        "no FMA 5.1.0 class carries this name as a preferred "
        "name or a listed synonym (full-OWL probe over preferred "
        "names and synonyms); no inventory record exists to "
        "link."),
}


def main():
    ws = json.load(open(WS))
    classes = json.load(open(os.path.join(
        PROJECT, "work/fma/fma-classes.json")))

    # BEFORE census, Milestone 9/33 semantics (old C8): full-phrase
    # equality against clinical names and inventory names
    cli = json.load(open(os.path.join(
        PROJECT, "data/nervous/nervous.json")))["records"]
    inv = json.load(open(os.path.join(
        PROJECT, "data/nervous/nervous-inventory.json")))["records"]
    cli_names = {r["name"].lower() for r in cli}
    cli_names |= {r["name"].split(" (")[0].lower() for r in cli}
    inv_names = {r["name"].lower() for r in inv}
    phrases = [w["phrase"] for w in ws]
    before = {
        "phrases": len(phrases),
        "to_clinical": sorted(p for p in phrases
                              if p.lower() in cli_names),
        "to_inventory": sorted(p for p in phrases
                               if p.lower() in inv_names),
    }

    out_phrases = []
    comp_counts = {"resolved": 0, "restricted": 0, "absent": 0}
    for w in ws:
        comps = []
        union = set()
        for c in w["components"]:
            d = {"segment": c["segment"], "name": c["name"],
                 "role": c["role"], "qualifier": c["qualifier"]}
            cands = c["candidates"]
            if cands:
                sets = {tuple(sorted(x["record_ids"]))
                        for x in cands}
                assert len(sets) == 1, (w["phrase"], c["name"],
                                        cands)
                best = min(cands, key=lambda x: RULE_ORDER.index(
                    x["rule"]))
                d.update({
                    "status": "resolved", "rule": best["rule"],
                    "class_fmaid": best.get("class_fmaid"),
                    "class_name": best.get("class_name"),
                    "record_ids": sorted(sets.pop()),
                    "reason": None})
                union |= set(d["record_ids"])
                comp_counts["resolved"] += 1
            elif c["near_miss"]:
                nm = c["near_miss"]
                d.update({
                    "status": "restricted", "rule": None,
                    "class_fmaid": None, "class_name": None,
                    "record_ids": [],
                    "reason": (
                        f"the name restricts the generic class "
                        f"{nm['class_fmaid']} '{nm['class_name']}' "
                        f"to a region/level subset; the generic "
                        f"class's record "
                        f"{', '.join(nm['record_ids'])} denotes "
                        f"the unrestricted class, so no link is "
                        f"made, and the named subset has no "
                        f"inventory record.")})
                comp_counts["restricted"] += 1
            else:
                probe = c["owl_probe"]
                if c["name"] in REASON_OVERRIDES:
                    reason = REASON_OVERRIDES[c["name"]]
                elif probe["class_by_name"]:
                    cid = probe["class_by_name"][0]
                    reason = (
                        f"FMA class FMA{cid} "
                        f"'{classes[cid]['name']}' exists in "
                        f"FMA 5.1.0 but was not among the classes "
                        f"intaken at Milestone 33 (frozen target "
                        f"list); no inventory record exists to "
                        f"link.")
                elif probe["class_by_synonym"]:
                    cid = probe["class_by_synonym"][0]
                    reason = (
                        f"the name is an FMA-listed synonym of "
                        f"FMA{cid} '{classes[cid]['name']}', "
                        f"which was not intaken at Milestone 33; "
                        f"no inventory record exists to link.")
                else:
                    reason = (
                        "no FMA 5.1.0 class carries this name "
                        "as a preferred name or a listed synonym "
                        "(full-OWL probe); no inventory record "
                        "exists to link.")
                d.update({"status": "absent", "rule": None,
                          "class_fmaid": None, "class_name": None,
                          "record_ids": [], "reason": reason})
                comp_counts["absent"] += 1
            comps.append(d)
        n_res = sum(1 for c in comps if c["status"] == "resolved")
        status = "resolved" if n_res == len(comps) else \
            "partial" if n_res else "unresolved"
        out_phrases.append({"phrase": w["phrase"], "status": status,
                            "components": comps,
                            "record_ids": sorted(union)})
    linked = sorted({rid for p in out_phrases
                     for rid in p["record_ids"]})
    after = {
        "phrases": len(out_phrases),
        "phrases_fully_resolved":
            sum(1 for p in out_phrases if p["status"] == "resolved"),
        "phrases_partially_resolved":
            sum(1 for p in out_phrases if p["status"] == "partial"),
        "phrases_unresolved":
            sum(1 for p in out_phrases
                if p["status"] == "unresolved"),
        "components": sum(comp_counts.values()),
        "components_resolved": comp_counts["resolved"],
        "components_restricted": comp_counts["restricted"],
        "components_absent": comp_counts["absent"],
        "distinct_inventory_records_linked": len(linked),
    }
    json.dump({"before": before, "after": after,
               "phrases": out_phrases}, open(OUT, "w"), indent=1)
    print("before:", before["phrases"], "phrases;",
          len(before["to_clinical"]), "to clinical;",
          len(before["to_inventory"]), "to inventory")
    print("after:", json.dumps(after))
    print("decisions ->", OUT)


if __name__ == "__main__":
    sys.exit(main())
