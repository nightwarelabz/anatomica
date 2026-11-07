#!/usr/bin/env python3
"""Milestone 35: apply the innervation-link re-pointing.

Writes, for every muscle record carrying an innervation nerve
phrase, the phrase's resolved inventory targets as
innervation.nerve_record_ids (the sorted union over the phrase's
components, contributory components included — the artifact
preserves each component's role). Nothing else in the muscle
records moves: the phrase strings, root values, and every
clinical field are carried through untouched. Records without a
nerve phrase are not modified.

Also writes the accounting artifact
data/innervation-link-pass.json (per-phrase components with
rules, FMA class evidence, target record ids, and a dated reason
for every component that does not resolve) and the muscle meta's
innervation_link_pass block.

Decisions come from tools/innervation_decide.py. Idempotent.
Note: tools/build_muscle_records.py predates this pass and would
drop nerve_record_ids if re-run; this tool is the applying tool
of record for the link field.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
MUSCLES = os.path.join(PROJECT, "data/muscular/muscles.json")
DEC = os.path.join(PROJECT, "work/innervation/decisions.json")
ART = os.path.join(PROJECT, "data/innervation-link-pass.json")
DATE = "2026-11-06"

RULE_TEXT = (
    "A phrase decomposes into named-nerve components by stated "
    "mechanical rules (';' separates; 'territory:' prefixes, "
    "parentheticals other than the two contributory patterns, "
    "and 'A component of the B' are qualifiers on B; 'may also "
    "receive a branch from the X' and 'with contributions from "
    "the X' are contributory components; 'A and B <stem> nerves' "
    "expands to the two named nerves). A component links to "
    "FMA-sourced inventory records only on exact correspondence: "
    "R1 the name equals an un-sided record's name; R2 it equals "
    "the preferred name of an FMA class with records (all the "
    "class's records); R3 it equals an FMA-listed synonym of "
    "such a class; R4 it is the class name pluralised under "
    "{nerve->nerves, ramus->rami} (the class's records, or its "
    "level-specialisation child classes' records). A name that "
    "restricts a generic class to a region/level subset does "
    "not link to the generic record. No fuzzy matching.")


def main():
    mus = json.load(open(MUSCLES))
    dec = json.load(open(DEC))
    by_phrase = {p["phrase"]: p for p in dec["phrases"]}
    n_written = 0
    for r in mus["records"]:
        inn = r.get("innervation")
        if not inn or not inn.get("nerve"):
            continue
        p = by_phrase[inn["nerve"]]
        new_inn = {"nerve": inn["nerve"],
                   "root_values": inn.get("root_values"),
                   "nerve_record_ids": p["record_ids"]}
        # preserve any other innervation keys, in order, after
        for k, v in inn.items():
            if k not in new_inn:
                new_inn[k] = v
        r["innervation"] = new_inn
        n_written += 1
    mus["meta"]["innervation_link_pass"] = {
        "milestone": "M35", "date": DATE,
        "field": "innervation.nerve_record_ids",
        "method": "tools/innervation_match.py (worksheet) -> "
                  "tools/innervation_decide.py (decisions) -> "
                  "tools/innervation_pass.py (this application)",
        "artifact": "data/innervation-link-pass.json",
        "records_written": n_written,
        "phrases": dec["after"]["phrases"],
        "phrases_fully_resolved":
            dec["after"]["phrases_fully_resolved"],
        "phrases_partially_resolved":
            dec["after"]["phrases_partially_resolved"],
        "phrases_unresolved": dec["after"]["phrases_unresolved"],
        "distinct_inventory_records_linked":
            dec["after"]["distinct_inventory_records_linked"],
    }
    with open(MUSCLES, "w") as fh:
        json.dump(mus, fh, indent=1)
        fh.write("\n")

    artifact = {
        "meta": {
            "milestone": "M35", "date": DATE,
            "scope": "the muscle module's 45 distinct innervation "
                     "nerve phrases (115 records) re-pointed "
                     "against the FMA-sourced nervous inventory "
                     "records of Milestone 33",
            "method": "tools/innervation_match.py -> "
                      "tools/innervation_decide.py -> "
                      "tools/innervation_pass.py",
            "rule": RULE_TEXT,
            "before_note": "Milestone 9/33 semantics (old "
                           "nerve_check C8): a phrase resolved "
                           "only when the full phrase string "
                           "equalled a record name.",
        },
        "before": dec["before"],
        "after": dec["after"],
        "phrases": dec["phrases"],
    }
    with open(ART, "w") as fh:
        json.dump(artifact, fh, indent=1)
        fh.write("\n")
    print(f"link pass applied: {n_written} muscle records "
          f"written; artifact -> {ART}")


if __name__ == "__main__":
    sys.exit(main())
