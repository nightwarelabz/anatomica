#!/usr/bin/env python3
"""ANATOMICA Milestone 39 — independent checker for the major-nerve
clinical tranche (data/nervous/major-nerves.json). Shares no code
with tools/build_major_nerve_records.py: the frozen target set, the
field discipline and the tier rule are re-declared here, and every
expectation is re-derived from the shipped files.

Gates:
  N1  the tranche holds exactly the frozen set of 40 major_nerve
      records (12 cranial nerves, 6 brachial-plexus trunks/cords,
      9 upper-limb nerves, 13 lower-limb nerves), ids unique.
  N2  citation discipline: every non-null content field carries a
      sources entry naming sources from the file's own register;
      every null field carries a verify entry for that field; the
      sources map holds no other keys than the non-null fields plus
      ta_name when a TA name is present.
  N3  tier re-derivation: core = root_values, motor_distribution,
      sensory_distribution; soft = course, clinical_testing;
      A = all five sourced, B = core sourced with a soft field null,
      C = any core field null. The shipped sourcing_tier must equal
      the re-derived tier for every record.
  N4  link integrity: every record's geometry_record_ids is
      non-empty, duplicate-free, and every id resolves to a record
      of data/nervous/nervous-inventory.json.
  N5  TA discipline: each record's ta_name/ta_code equal the
      outcome carried by its linked inventory records — the
      Milestone 35 TA2 fields of the FMA records (all linked
      records must agree), or, for records linking BodyParts3D
      inventory records (which carry no TA fields), the Milestone
      23 outcome on the corresponding Milestone 9 clinical record.
  N6  both-ways innervation consistency: for every resolved
      component of data/innervation-link-pass.json (Milestone 35),
      if any of its inventory record ids is linked by a record of
      this tranche, all of them are linked by that same record —
      the muscle module's innervation links and this tranche's
      links name the same inventory records for the same nerves.
  N7  census: nervous clinical records total 92 (52 Milestone 9 +
      40 here); the clinical tranche across all systems totals 401.

Exit code 0 only if every hard check passes.
"""

import json
import os
import sys
from collections import Counter

PROJECT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def load(rel):
    with open(os.path.join(PROJECT, rel)) as fh:
        return json.load(fh)


MAJOR = load("data/nervous/major-nerves.json")
INV = {r["record_id"]: r
       for r in load("data/nervous/nervous-inventory.json")["records"]}
M9 = {r["id"]: r for r in load("data/nervous/nervous.json")["records"]}
PASS = load("data/innervation-link-pass.json")

failures = []


def check(ok, label, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}"
          + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(label)


CORE = ("root_values", "motor_distribution", "sensory_distribution")
SOFT = ("course", "clinical_testing")
FIELDS = CORE[:1] + ("course",) + CORE[1:] + SOFT[1:]

FROZEN = {
    "major.cn-01-olfactory", "major.cn-02-optic",
    "major.cn-03-oculomotor", "major.cn-04-trochlear",
    "major.cn-05-trigeminal", "major.cn-06-abducens",
    "major.cn-07-facial", "major.cn-08-vestibulocochlear",
    "major.cn-09-glossopharyngeal", "major.cn-10-vagus",
    "major.cn-11-accessory", "major.cn-12-hypoglossal",
    "major.superior-trunk", "major.middle-trunk",
    "major.inferior-trunk", "major.lateral-cord",
    "major.posterior-cord", "major.medial-cord",
    "major.suprascapular", "major.long-thoracic",
    "major.musculocutaneous", "major.axillary", "major.radial",
    "major.median", "major.ulnar", "major.medial-cutaneous-arm",
    "major.medial-cutaneous-forearm",
    "major.femoral", "major.obturator",
    "major.lateral-femoral-cutaneous", "major.saphenous",
    "major.superior-gluteal", "major.inferior-gluteal",
    "major.sciatic", "major.tibial", "major.common-fibular",
    "major.superficial-fibular", "major.deep-fibular",
    "major.sural", "major.pudendal",
}

# Records linking BodyParts3D inventory records (no TA fields of
# their own): the Milestone 9 clinical record whose Milestone 23
# TA2 outcome the tranche record must carry.
BP3D_TA_PARENT = {
    "major.cn-02-optic": "nerve.cn-02-optic",
    "major.cn-04-trochlear": "nerve.cn-04-trochlear",
}

records = MAJOR["records"]
by_id = {r["id"]: r for r in records}

# ---------------------------------------------------------------- N1
check(len(records) == 40 and set(by_id) == FROZEN
      and len(by_id) == len(records)
      and all(r["type"] == "major_nerve" for r in records),
      "N1 frozen set: exactly the 40 declared major_nerve records",
      f"{len(records)} records; groups "
      f"{dict(Counter(r['group'] for r in records))}")

# ---------------------------------------------------------------- N2
register = set(MAJOR["meta"]["sources"])
cit_bad, flag_bad = [], []
for r in records:
    expected_keys = {f for f in FIELDS if r[f] is not None}
    if r["ta_name"] is not None:
        expected_keys.add("ta_name")
    if set(r["sources"]) != expected_keys:
        cit_bad.append(f"{r['id']}: sources keys "
                       f"{sorted(set(r['sources']) ^ expected_keys)}")
    for f, srcs in r["sources"].items():
        if not srcs or not set(srcs) <= register:
            cit_bad.append(f"{r['id']}:{f} cites unregistered source")
    flagged = {v.split(":", 1)[0] for v in r["verify"]}
    null_fields = {f for f in FIELDS if r[f] is None}
    if flagged != null_fields:
        flag_bad.append(f"{r['id']}: flagged {sorted(flagged)} vs "
                        f"null {sorted(null_fields)}")
    if r["ta_name"] is None or r["ta_code"] is None:
        flag_bad.append(f"{r['id']}: TA name/code missing")
check(not cit_bad, "N2 every non-null field cited from the register",
      "; ".join(cit_bad[:4]))
check(not flag_bad, "N2 every null field verify-flagged, no others",
      "; ".join(flag_bad[:4]))

# ---------------------------------------------------------------- N3
def derive(r):
    if any(r[f] is None for f in CORE):
        return "C"
    if any(r[f] is None for f in SOFT):
        return "B"
    return "A"


tier_bad = [r["id"] for r in records
            if r["sourcing_tier"] != derive(r)]
check(not tier_bad, "N3 sourcing_tier == re-derived tier (core/soft)",
      f"tiers {dict(Counter(derive(r) for r in records))}"
      + (f"; mismatches: {tier_bad}" if tier_bad else ""))

# ---------------------------------------------------------------- N4
link_bad, n_links = [], 0
for r in records:
    g = r["geometry_record_ids"]
    n_links += len(g)
    if not g or len(set(g)) != len(g):
        link_bad.append(f"{r['id']}: empty or duplicated links")
    for rid in g:
        if rid not in INV:
            link_bad.append(f"{r['id']}: unresolved link {rid}")
check(not link_bad, "N4 all geometry_record_ids resolve to the "
      "nervous inventory", f"{n_links} links over "
      f"{len({x for r in records for x in r['geometry_record_ids']})} "
      f"distinct inventory records"
      + (f"; {link_bad[:3]}" if link_bad else ""))

# ---------------------------------------------------------------- N5
ta_bad = []
for r in records:
    linked = [INV[rid] for rid in r["geometry_record_ids"]]
    fma_tas = {(x.get("ta_code"), x.get("ta_name")) for x in linked
               if x.get("source") == "fma-5.1.0"}
    if fma_tas:
        if len(fma_tas) != 1:
            ta_bad.append(f"{r['id']}: linked FMA records disagree "
                          f"on TA {fma_tas}")
        elif (r["ta_code"], r["ta_name"]) != next(iter(fma_tas)):
            ta_bad.append(f"{r['id']}: TA {(r['ta_code'], r['ta_name'])}"
                          f" != inventory {next(iter(fma_tas))}")
    else:
        parent = BP3D_TA_PARENT.get(r["id"])
        if parent is None:
            ta_bad.append(f"{r['id']}: no FMA TA and no declared "
                          f"BodyParts3D TA parent")
        else:
            exp = (M9[parent]["ta_code"], M9[parent]["ta_name"])
            if (r["ta_code"], r["ta_name"]) != exp:
                ta_bad.append(f"{r['id']}: TA {(r['ta_code'], r['ta_name'])}"
                              f" != Milestone 9/23 {exp}")
    if r["sources"].get("ta_name") != ["TA2"]:
        ta_bad.append(f"{r['id']}: ta_name not cited to TA2")
check(not ta_bad, "N5 TA name/code follow the linked inventory "
      "records (M35) or the M9/M23 outcome (BodyParts3D links)",
      "; ".join(ta_bad[:4]))

# ---------------------------------------------------------------- N6
owner = {}
for r in records:
    for rid in r["geometry_record_ids"]:
        owner[rid] = r["id"]
both_bad, corroborated = [], set()
for phrase in PASS["phrases"]:
    for comp in phrase["components"]:
        if comp["status"] != "resolved":
            continue
        ids = comp["record_ids"]
        owners = {owner.get(i) for i in ids} - {None}
        if not owners:
            continue
        if len(owners) != 1:
            both_bad.append(f"component '{comp['name']}': split "
                            f"across {owners}")
        elif any(owner.get(i) != next(iter(owners)) for i in ids):
            both_bad.append(f"component '{comp['name']}': only "
                            f"partially linked by {owners}")
        else:
            corroborated.add(next(iter(owners)))
check(not both_bad, "N6 innervation-pass components and tranche "
      "links name the same inventory records",
      f"{len(corroborated)} tranche records corroborated by muscle "
      f"innervation links"
      + (f"; {both_bad[:3]}" if both_bad else ""))

# ---------------------------------------------------------------- N7
CLIN_FILES = [
    "data/muscular/muscles.json",
    "data/cardiovascular/cardiovascular.json",
    "data/nervous/nervous.json",
    "data/nervous/major-nerves.json",
    "data/respiratory/respiratory.json",
    "data/digestive/digestive.json",
    "data/urinary/urinary.json",
    "data/lymphatic/lymphatic.json",
    "data/endocrine/endocrine.json",
    "data/reproductive/reproductive.json",
    "data/integumentary/integumentary.json",
]
total = sum(len(load(f)["records"]) for f in CLIN_FILES)
nervous_total = len(M9) + len(records)
check(nervous_total == 92 and total == 401,
      "N7 census: nervous clinical 92; all-system clinical tranche "
      "401", f"nervous {nervous_total}, total {total}")

print(f"\n{'ALL CHECKS PASS' if not failures else 'FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
