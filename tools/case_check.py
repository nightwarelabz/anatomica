#!/usr/bin/env python3
"""ANATOMICA Case Workbench checker (Milestone 20; parameterised at
Milestone 22 to validate EVERY case in cases/, not one).

Independently re-derives — without importing the runner — and for each
case checks:

  1. parameter discipline: every LR maps to a derivation in
     cases/parameters.json whose arithmetic reproduces it; priors are
     declared (calibrated ones inside their cited range), sum to 1,
     and are flagged unless a consulted source carries them;
  2. ontology discipline: Mondo ids resolve to the C10 register
     entries actually verified via EBI OLS (or are null WITH an
     explanatory note — never invented), HPO ids to the C11 register;
  3. reference resolution: every record a case points at exists —
     body-model structures, discriminators, labs, findings,
     measurements, criteria atoms, classification inputs and rules;
  4. stage discipline: findings/labs revealed at declared stages,
     orders placed legally, yield stages = placed + 1, every menu
     yield producible by ordering;
  5. scoring recomputation: priors + LRs reproduce every workbench
     board; learner boards reproduce every Brier score, rank and
     probability; criteria statuses (grouped, k_of_n, classification,
     severity) recompute from the declared blocks; anchoring events
     and order classifications recompute; resource tally recomputes;
  6. governance: synthetic, review gate UNMET (never fabricated),
     validity dual-sourced-draft, and NO composite score key anywhere.

Plus per-case profile sections: case 1 (lab arithmetic, the imaging
voxel recount, the physiology engine re-run, the Theatre handoff, the
FHIR export) and case 2 (lab arithmetic, the classification
arithmetic, the WSES timing band, the anchoring headline, and the
LOOP verification: the trace-02 Theatre debrief is re-read, its
SHA-256 recomputed, and every matched field compared field-by-field
against the file's actual contents).

Usage: python3 tools/case_check.py
"""
import glob
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "cases")
PASS = 0
FAIL = 0
NOTES = []


def ok(cond, label, note=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL: {label}")
    if note:
        NOTES.append(note)
    return cond


def load(path):
    with open(path) as f:
        return json.load(f)


PARAMS = load(os.path.join(CASES, "parameters.json"))
SOURCES = {s["id"]: s for s in PARAMS["sources"]}
CONST = {p["key"]: p["value"] for p in PARAMS["parameters"]}
RULE_OUT = CONST["rule_out_threshold"]
ANCHOR = CONST["anchoring_threshold"]
DISC_DELTA = CONST["discriminating_delta"]
DERIV = {(d["finding"], d["target_hypothesis"]): d
         for d in PARAMS["lr_derivations"]}

# ---- inventory + theatre registers (for body-model references) -----
INVS = {}
for inv_path in sorted(glob.glob(os.path.join(ROOT, "data", "*", "*.json"))):
    try:
        inv = load(inv_path)
    except Exception:
        continue
    if isinstance(inv, dict) and isinstance(inv.get("records"), list):
        module = os.path.basename(os.path.dirname(inv_path))
        for r in inv["records"]:
            if isinstance(r, dict) and (r.get("id") or r.get("record_id")):
                INVS.setdefault(r.get("id") or r.get("record_id"),
                                []).append(module)
PROC_FILE = load(os.path.join(
    ROOT, "theatre", "procedures", "proc.lap-cholecystectomy.json"))["procedure"]
STRUCT_IDS = {s["id"] for s in PROC_FILE["structures"]}
PROC_IDS = {PROC_FILE["id"]}


# ---- independent atom / criteria machinery (fresh implementation) --
class Ctx:
    def __init__(self, case):
        self.case = case
        self.findings = {f["id"]: f for f in case["findings"]}
        self.labs = {l["id"]: l for l in case["labs"]}
        self.meas = {m["id"]: m for m in case.get("measurements", [])}
        blocks = []
        ev = case["adjudication"].get("tg18_evaluation")
        if ev:
            blocks.append({"id": "tg18_cholecystitis", "kind": "grouped",
                           "groups": ev["groups"],
                           "status_rules": ev["status_rules"],
                           "default_status": ev["default_status"]})
        blocks.extend(case.get("criteria_blocks", []))
        self.blocks = blocks

    def _stage_of(self, atom):
        if "finding_id" in atom:
            return self.findings[atom["finding_id"]]["stage"]
        if "lab_id" in atom:
            return self.labs[atom["lab_id"]]["stage"]
        if "measurement_id" in atom:
            return self.meas[atom["measurement_id"]]["stage"]
        return 0

    def _test(self, value, atom, high=None):
        t = atom["test"]
        if t == "value_gt":
            return value > atom["threshold"]
        if t == "value_lt":
            return value < atom["threshold"]
        if t == "value_gte":
            return value >= atom["threshold"]
        if t == "value_lte":
            return value <= atom["threshold"]
        if t == "above_reference":
            return value > high
        if t == "value_gt_uln_multiple":
            return value > atom["factor"] * high
        if t == "value_gte_uln_multiple":
            return value >= atom["factor"] * high
        raise ValueError(atom)

    def atom3(self, atom, stage, excl=frozenset()):
        if atom.get("assessable") is False:
            return "unknown"
        if "constant" in atom:
            return "satisfied" if atom["constant"] else "unsatisfied"
        refs = [atom[k] for k in ("finding_id", "lab_id", "measurement_id")
                if k in atom]
        if refs and refs[0] in excl:
            return "unknown"
        if "measurement_id" in atom:
            src = self.meas[atom["measurement_id"]].get("finding_id")
            if src in excl:
                return "unknown"
        if self._stage_of(atom) > stage:
            return "unknown"
        if "finding_id" in atom:
            hit = self.findings[atom["finding_id"]].get(
                "presence", "present") == atom["is"]
        elif "lab_id" in atom:
            lab = self.labs[atom["lab_id"]]
            rr = lab.get("reference_range") or {}
            hit = self._test(lab["value"], atom, rr.get("high"))
        elif "measurement_id" in atom:
            hit = self._test(self.meas[atom["measurement_id"]]["value"], atom)
        elif "case_field" in atom:
            hit = self._test(self.case["patient"][atom["case_field"]], atom)
        else:
            raise ValueError(atom)
        return "satisfied" if hit else "unsatisfied"

    def atomb(self, atom, stage):
        if atom.get("assessable") is False:
            return "not-assessed"
        r = self.atom3(atom, stage)
        if r == "unknown":
            return False
        return r == "satisfied"

    def itemb(self, item, stage):
        vals = [self.atomb(a, stage) for a in item["evidence"]]
        if any(v is True for v in vals):
            return True
        if any(v == "not-assessed" for v in vals):
            return "not-assessed"
        return False

    def item3(self, item, stage, excl=frozenset()):
        vals = [self.atom3(a, stage, excl) for a in item["evidence"]]
        if "satisfied" in vals:
            return "satisfied"
        if vals and all(v == "unsatisfied" for v in vals):
            return "unsatisfied"
        return "unknown"

    def block_eval(self, block, stage):
        if block["kind"] == "grouped":
            groups = {g["group"]: any(self.itemb(i, stage) is True
                                       for i in g["items"])
                      for g in block["groups"]}
            status = block["default_status"]
            for rule in block["status_rules"]:
                req = rule.get("require", {})
                anyof = rule.get("require_any", {})
                if all(groups[g] == w for g, w in req.items()) and (
                        not anyof or any(groups[g] == w for g, w in anyof.items())):
                    status = rule["status"]
                    break
            return {"groups": groups, "status": status}
        if block["kind"] == "k_of_n":
            items = {i["id"]: self.itemb(i, stage) is True
                     for i in block["items"]}
            met = sum(items.values())
            return {"items": items, "items_met": met,
                    "diagnosable": met >= block["k"]}
        if block["kind"] == "classification":
            inputs = {}
            for inp in block["inputs"]:
                st = [self.atom3(a, stage) for a in inp["atoms"]]
                inputs[inp["id"]] = (True if "satisfied" in st else
                                     False if st and all(
                                         s == "unsatisfied" for s in st)
                                     else "unknown")
            for idx, rule in enumerate(block["rules"]):
                if all(inputs[k] == w for k, w in rule["when"].items()):
                    return {"status": "classified", "result": rule["result"],
                            "rule_index": idx, "inputs": inputs}
            return {"status": block.get("pending_label",
                                        "not yet classifiable"),
                    "result": None, "rule_index": None, "inputs": inputs}
        raise ValueError(block["kind"])

    def crit_items(self, stage, excl=frozenset()):
        out = {}
        for b in self.blocks:
            if b["kind"] == "grouped":
                its = [i for g in b["groups"] for i in g["items"]]
            elif b["kind"] == "k_of_n":
                its = b["items"]
            else:
                its = [{"id": inp["id"], "evidence": inp["atoms"]}
                       for inp in b["inputs"]]
            for i in its:
                out[f"{b['id']}.{i['id']}"] = self.item3(i, stage, excl)
        return out

    def classify(self, test, placed, boards):
        reveal = placed + 1
        y = set(test["yields"])
        lr_y = {f for f in y if f in self.findings
                and self.findings[f].get("lr")}
        full = boards(reveal)
        wo = boards(reveal, lr_y)
        lf, lw = max(full, key=full.get), max(wo, key=wo.get)
        if lf != lw or abs(full[lf] - wo[lf]) >= DISC_DELTA:
            return "discriminating"
        if any(wo[h] >= RULE_OUT and full[h] < RULE_OUT for h in full):
            return "discriminating"
        excl = {i for i in y
                if (i in self.findings and self.findings[i]["stage"] == reveal)
                or (i in self.labs and self.labs[i]["stage"] == reveal)
                or (i in self.meas and self.meas[i]["stage"] == reveal)}
        if self.crit_items(reveal, excl) != self.crit_items(reveal):
            return "criteria-completing"
        if test.get("safety_net_for"):
            return "safety-net"
        return "non-contributory"


def check_case(case_path, attempt, debrief):
    case = load(case_path)["case"]
    cid = case["id"]
    print(f"\n=== {cid} ===")
    ctx = Ctx(case)
    hyps = {h["id"]: h for h in case["hypotheses"]}
    findings = ctx.findings
    labs = ctx.labs
    tests = {t["id"]: t for t in case["available_tests"]}
    stages = [s["stage"] for s in case["presentation_stages"]]
    truth = case["adjudication"]["diagnosis_hypothesis"]

    # ---- 1. parameters, priors, LRs -------------------------------
    print("[1] parameter discipline")
    psum = sum(h["prior"]["value"] for h in case["hypotheses"])
    ok(abs(psum - 1.0) < 1e-9, f"{cid}: priors sum to {psum:.6f}")
    for h in case["hypotheses"]:
        p = h["prior"]
        ok(p["status"] in ("calibrated", "verify"), f"{cid}: prior status {h['id']}")
        if p["status"] == "verify":
            ok("flag" in p["note"].lower(),
               f"{cid}: verify prior is flagged in its note {h['id']}")
        if p.get("range"):
            ok(p["range"][0] <= p["value"] <= p["range"][1],
               f"{cid}: calibrated prior inside its cited range {h['id']}")
        if p.get("source"):
            ok(p["source"] in SOURCES, f"{cid}: prior source exists {h['id']}")
    for f in case["findings"]:
        lr = f.get("lr")
        if not lr:
            continue
        ok(lr["status"] in ("cited", "computed"),
           f"{cid}: LR status declared {f['id']}")
        if lr["status"] == "cited":
            ok("source" in lr and lr["source"] in SOURCES,
               f"{cid}: cited LR names its source {f['id']}")
            ok("sens" not in lr and "spec" not in lr,
               f"{cid}: cited LR carries no invented sens/spec {f['id']}")
        d = DERIV.get((f["id"], lr["for_hypothesis"]))
        ok(d is not None, f"{cid}: LR derivation registered {f['id']}")
        if d:
            ok(d["status"] == lr["status"],
               f"{cid}: derivation status agrees with finding {f['id']}")
            import re as _re
            prose_numbers = [float(x) for x in
                             _re.findall(r"\d+\.\d+", d["derivation"])]
            for k in ("lr_plus", "lr_minus"):
                if k in lr:
                    ok(abs(d[k] - lr[k]) < 1e-9,
                       f"{cid}: {k} for {f['id']} matches derivation "
                       f"({lr[k]} vs {d[k]})")
                    if d["status"] == "computed":
                        ok(any(abs(n - lr[k]) < 1e-3 for n in prose_numbers),
                           f"{cid}: {k} value appears in the worked arithmetic "
                           f"of the derivation {f['id']}")

    # ---- 2. ontology ----------------------------------------------
    print("[2] ontology discipline")
    c10 = SOURCES["C10"]["consulted"]
    c11 = SOURCES["C11"]["consulted"]
    for h in case["hypotheses"]:
        m = h.get("mondo")
        if m is None:
            ok(h.get("mondo_note"), f"{cid}: null Mondo is explained {h['id']}")
        else:
            ok(m in c10, f"{cid}: Mondo id verified in-session (C10) {h['id']} {m}")
    gt_m = case["ground_truth"].get("mondo")
    ok(gt_m == case["adjudication"].get("mondo") == hyps[truth].get("mondo"),
       f"{cid}: ground truth / adjudication / hypothesis Mondo agree")
    for hp in case["ground_truth"].get("hpo", []):
        ok(hp in c11, f"{cid}: HPO verified in-session (C11) {hp}")
    for entry in case["ground_truth"].get("hpo_absent", []):
        hp = entry if isinstance(entry, str) else entry["hpo"]
        ok(hp in c11, f"{cid}: absent-finding HPO verified (C11) {hp}")

    # ---- 3. references --------------------------------------------
    print("[3] reference resolution")
    if "imaging_link" in case:
        rid = case["imaging_link"]["label"]["record_id"]
        ok(rid in INVS, f"{cid}: imaging-link body record exists {rid}")
    for d in case.get("discriminators", []):
        ok(d["hypothesis"] in hyps, f"{cid}: discriminator hypothesis {d['id']}")
        ok(d["settled_by"] in findings or d["settled_by"] in labs,
           f"{cid}: discriminator settled_by resolves {d['id']}")
    for l in case["labs"]:
        if l.get("linked_test"):
            ok(l["linked_test"] in tests, f"{cid}: lab linked_test {l['id']}")
    for f in case["findings"]:
        if f.get("source_lab"):
            ok(f["source_lab"] in labs, f"{cid}: finding source_lab {f['id']}")
    menu_yields = set()
    for t in case["available_tests"]:
        for y in t["yields"]:
            menu_yields.add(y)
            ok(y in findings or y in labs or y in ctx.meas,
               f"{cid}: test yield resolves {t['id']} -> {y}")
        if t.get("safety_net_for"):
            ok(t["safety_net_for"] in hyps, f"{cid}: safety_net_for {t['id']}")
    for f in case["findings"]:
        for chain_id in f.get("evidence_chain", []):
            ok(chain_id in findings, f"{cid}: evidence_chain {f['id']} -> {chain_id}")
    for m in case.get("measurements", []):
        if m.get("finding_id"):
            ok(m["finding_id"] in findings, f"{cid}: measurement source {m['id']}")
    atom_refs = []
    for b in ctx.blocks:
        if b["kind"] == "grouped":
            its = [i for g in b["groups"] for i in g["items"]]
        elif b["kind"] == "k_of_n":
            its = b["items"]
        else:
            its = [{"id": inp["id"], "evidence": inp["atoms"]}
                   for inp in b["inputs"]]
            input_ids = {inp["id"] for inp in b["inputs"]}
            for rule in b["rules"]:
                ok(all(k in input_ids for k in rule["when"]),
                   f"{cid}: classification rule references declared inputs {b['id']}")
        atom_refs.extend(its)
    if "severity_grade" in case["adjudication"]:
        sev = case["adjudication"]["severity_grade"]
        atom_refs.extend(sev["items_grade_ii"] + sev["items_grade_iii"])
    for item in atom_refs:
        for a in item["evidence"]:
            for k in ("finding_id", "lab_id", "measurement_id"):
                if k in a:
                    pool = {"finding_id": findings, "lab_id": labs,
                            "measurement_id": ctx.meas}[k]
                    ok(a[k] in pool, f"{cid}: criteria atom resolves {a[k]}")
    ok(truth in hyps, f"{cid}: adjudicated diagnosis is a declared hypothesis")
    if "final_stage" in case["management"]:
        ok(case["management"]["final_stage"] in stages,
           f"{cid}: management final stage declared")

    # ---- 4. stage discipline ---------------------------------------
    print("[4] stage discipline")
    for f in case["findings"]:
        ok(f["stage"] in stages, f"{cid}: finding stage valid {f['id']}")
    for l in case["labs"]:
        ok(l["stage"] in stages, f"{cid}: lab stage valid {l['id']}")
    producible = {x["id"] for x in case["findings"]} | {x["id"] for x in case["labs"]}
    starter = {x["id"] for x in case["findings"] + case["labs"] if x["stage"] == 1}
    ok(producible - starter <= menu_yields,
       f"{cid}: every post-stage-1 finding/lab is producible by some order")
    att_stages = {a["stage"]: a for a in attempt["stages"]}
    for a in attempt["stages"]:
        ok(a["stage"] in stages, f"{cid}: attempt stage valid {a['stage']}")
        ok(set(a["board"]) == set(hyps), f"{cid}: board covers all hypotheses s{a['stage']}")
        ok(abs(sum(a["board"].values()) - 1.0) < 1e-9,
           f"{cid}: learner board sums to 1 at stage {a['stage']}")
        for tid in a["orders"]:
            ok(tid in tests, f"{cid}: ordered test exists {tid}")
            ok(tests[tid]["available_from_stage"] <= a["stage"],
               f"{cid}: order placed legally {tid} at stage {a['stage']}")
            for y in tests[tid]["yields"]:
                if y in findings:
                    ok(findings[y]["stage"] == a["stage"] + 1,
                       f"{cid}: yield stage = placed+1 {tid} -> {y}")
                elif y in labs:
                    ok(labs[y]["stage"] == a["stage"] + 1,
                       f"{cid}: yield stage = placed+1 {tid} -> {y}")
                elif y in ctx.meas:
                    ok(ctx.meas[y]["stage"] == a["stage"] + 1,
                       f"{cid}: yield stage = placed+1 {tid} -> {y}")

    # ---- 5. scoring recomputation ----------------------------------
    print("[5] scoring recomputation")
    priors = {h["id"]: h["prior"]["value"] for h in case["hypotheses"]}

    def board_at(stage, exclude=frozenset()):
        w = dict(priors)
        for f in case["findings"]:
            if f["stage"] <= stage and f["id"] not in exclude and f.get("lr"):
                lr = f["lr"]
                if "lr_plus" in lr:
                    w[lr["for_hypothesis"]] *= lr["lr_plus"]
                if "lr_minus" in lr:
                    w[lr["for_hypothesis"]] *= lr["lr_minus"]
        tot = sum(w.values())
        return {h: v / tot for h, v in w.items()}

    boards = {s: board_at(s) for s in stages}
    ruled = {}
    for s in stages:
        for h in hyps:
            if h not in ruled and boards[s][h] < RULE_OUT:
                ruled[h] = s
    d = debrief["debrief"]
    ok(d["ruled_out_by_workbench"] == ruled, f"{cid}: rule-out stages recompute")
    anchor_expect = []
    for s in stages:
        lb = att_stages[s]["board"]
        for h in hyps:
            if ruled.get(h, 99) <= s and lb[h] >= ANCHOR:
                anchor_expect.append((s, h))
    got_anchor = [(a["stage"], a["hypothesis"]) for a in d["anchoring_events"]]
    ok(got_anchor == anchor_expect,
       f"{cid}: anchoring events recompute {got_anchor}")
    for row in d["per_stage"]:
        s = row["stage"]
        wb = boards[s]
        ok(all(abs(row["workbench_board"][h] - round(wb[h], 4)) < 1e-9
               for h in hyps), f"{cid}: workbench board stage {s}")
        lb = att_stages[s]["board"]
        bl = sum((p - (1 if h == truth else 0)) ** 2 for h, p in lb.items())
        bw = sum((p - (1 if h == truth else 0)) ** 2 for h, p in wb.items())
        ok(abs(row["learner_brier"] - round(bl, 4)) < 1e-9,
           f"{cid}: learner Brier stage {s}")
        ok(abs(row["workbench_brier"] - round(bw, 4)) < 1e-9,
           f"{cid}: workbench Brier stage {s}")
        rank_l = 1 + sum(1 for h in hyps if lb[h] > lb[truth])
        rank_w = 1 + sum(1 for h in hyps if wb[h] > wb[truth])
        ok(row["learner_rank_of_truth"] == rank_l, f"{cid}: learner rank stage {s}")
        ok(row["workbench_rank_of_truth"] == rank_w, f"{cid}: workbench rank stage {s}")
        for b in ctx.blocks:
            ev = ctx.block_eval(b, s)
            got = row["criteria"][b["id"]]
            ok(got == ev, f"{cid}: criteria {b['id']} stage {s} recompute")
    adj = d["adjudicated_diagnosis"]
    ok(adj["hypothesis"] == truth, f"{cid}: debrief adjudication = case adjudication")
    if "classification" in case["adjudication"]:
        fin = ctx.block_eval(
            [b for b in ctx.blocks if b["kind"] == "classification"][0],
            stages[-1])
        want = case["adjudication"]["classification"]
        ok(fin["status"] == "classified"
           and fin["result"]["strasberg"] == want["strasberg"]
           and fin["result"]["bismuth"] == want["bismuth"],
           f"{cid}: classification final recompute")
    if "severity_grade" in case["adjudication"]:
        sev = case["adjudication"]["severity_grade"]
        iii = {i["id"]: ctx.itemb(i, stages[-1]) for i in sev["items_grade_iii"]}
        ii = {i["id"]: ctx.itemb(i, stages[-1]) for i in sev["items_grade_ii"]}
        grade = ("III" if any(v is True for v in iii.values())
                 else "II" if any(v is True for v in ii.values()) else "I")
        ok(adj["tg18_severity_grade"] == grade,
           f"{cid}: severity grade recompute = {grade}")
    tally_t = tally_c = 0
    class_expect = {}
    for a in attempt["stages"]:
        for tid in a["orders"]:
            t = tests[tid]
            class_expect[tid] = ctx.classify(t, a["stage"], board_at)
            tally_t += t["time_min"]["value"]
            tally_c += t["cost_units"]["value"]
    for o in d["orders"]:
        ok(o["classification"] == class_expect[o["test_id"]],
           f"{cid}: order classification {o['test_id']} = {class_expect[o['test_id']]}")
    ok(d["resource_tally"]["total_time_min"] == tally_t
       and d["resource_tally"]["total_cost_units"] == tally_c,
       f"{cid}: resource tally recompute {tally_t} min / {tally_c} units")

    # ---- 6. governance ----------------------------------------------
    print("[6] governance")
    ok(case["synthetic"] is True, f"{cid}: synthetic case")
    ok(case["review"]["status"].startswith("UNMET")
       and case["review"]["recorded_reviewers"] == [],
       f"{cid}: review gate UNMET with an empty reviewer list (not fabricated)")
    ok(case["validity"]["content"] == "dual-sourced-draft",
       f"{cid}: validity dual-sourced-draft")
    ok(d["review"]["status"].startswith("UNMET"), f"{cid}: debrief review UNMET")

    def find_composite(o, where="case"):
        if isinstance(o, dict):
            for k, v in o.items():
                ok("composite" not in k.lower(),
                   f"{cid}: no composite score key at {where}.{k}")
                find_composite(v, f"{where}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                find_composite(v, f"{where}[{i}]")
    find_composite(case)
    find_composite(debrief)
    return case, ctx, boards


# =====================================================================
# Case 1 profile (Milestone 20 sections, preserved)
# =====================================================================
def profile_case1(case, ctx, attempt):
    print(f"\n=== {case['id']} profile: labs / severity items / imaging / "
          f"physiology / theatre / FHIR ===")
    labs = ctx.labs
    ok(labs["lab.lipase"]["value"] < 3 * labs["lab.lipase"]["reference_range"]["high"],
       "case1: lipase 95 < 3x ULN 480 (Atlanta enzyme item false)")
    ok(labs["lab.crp"]["value"] >= 10, "case1: CRP 86 >= TG18 B-2 threshold 10 mg/L")
    bl = labs["lab.bilirubin-total"]
    ok(bl["value"] <= bl["reference_range"]["high"],
       "case1: bilirubin 0.9 inside cited range (TG18 B-5 unmet, as adjudicated)")
    trop = ctx.findings["f.troponin-negative"]
    ok(trop.get("lr") is None and trop["stage"] == 2,
       "case1: troponin is an unquantified finding (safety-net pair, no LR invented)")

    sev = case["adjudication"]["severity_grade"]
    final = case["presentation_stages"][-1]["stage"]
    for it in sev["items_grade_ii"] + sev["items_grade_iii"]:
        ok(ctx.itemb(it, final) == it["satisfied"],
           f"case1: severity item {it['id']} declared state matches recomputation")
    g3 = [ctx.itemb(i, final) for i in sev["items_grade_iii"]]
    ok(sum(1 for v in g3 if v == "not-assessed") == 3,
       "case1: exactly three Grade III items not-assessed (respiratory, renal, hepatic)")
    ok(sev["grade"] == "I", "case1: case file severity grade is I")

    # ---- imaging link: recount from the shipped web bins ----------
    import numpy as np
    bindir = os.path.join(ROOT, "web", "data", "imaging", "s0778")
    counts = []
    for i in range(431):
        arr = np.fromfile(os.path.join(bindir, f"lbl-{i:04d}.bin"), dtype=np.uint8)
        counts.append(int((arr == 15).sum()))
    present = [i for i, c in enumerate(counts) if c > 0]
    link = case["imaging_link"]
    ok([present[0], present[-1]] == link["measures"]["slice_files_0based"],
       f"case1: gallbladder slices recounted {present[0]}..{present[-1]} (0-based files)")
    ok(len(present) == link["measures"]["slices_with_label"] == 24,
       "case1: 24 slices carry the gallbladder label")
    ok(sum(counts) == 2720 == link["label"]["hu_statistics_from_crosswalk"]["voxels"],
       "case1: total gallbladder voxels recounted: 2,720")
    mx = max(range(431), key=lambda i: counts[i])
    ok(mx == link["measures"]["max_cross_section"]["file_index_0based"]
       and counts[mx] == link["measures"]["max_cross_section"]["voxels"] == 186,
       f"case1: max cross-section recounted: file {mx}, {counts[mx]} voxels")
    ok(abs(2720 * 3.375 / 1000 - 9.18) < 1e-9,
       "case1: volume arithmetic 2,720 x 3.375 mm3 = 9.18 mL")
    cw = load(os.path.join(ROOT, "data", "imaging", "s0778", "crosswalk.json"))
    gb = next(l for l in cw["labels"] if l["label"] == "gallbladder")
    ok(gb["record_ids"] == ["gallbladder"] and gb["index"] == 15,
       "case1: crosswalk maps label 15 (gallbladder) to record 'gallbladder'")
    hu = link["label"]["hu_statistics_from_crosswalk"]
    ok(all(gb["hu"][k] == hu[k] for k in ("mean", "median", "p5", "p95", "min", "max")),
       "case1: case HU statistics equal crosswalk values")
    series = load(os.path.join(ROOT, "data", "imaging", "s0778", "series.json"))
    z0 = series["geometry"]["ipp_first_slice_lps_mm"][2]
    ok(abs((z0 + 195 * 1.5) - link["measures"]["z_range_lps_mm"][0]) < 0.01
       and abs((z0 + 218 * 1.5) - link["measures"]["z_range_lps_mm"][1]) < 0.01,
       "case1: slice z-arithmetic reproduces the crosswalk bbox")
    ok("does not show" in link["honesty_block"] or "NOT" in link["honesty_block"],
       "case1: imaging honesty block present")

    # ---- physiology link: engine re-run (cargo) --------------------
    import re as _re
    try:
        env = dict(os.environ)
        env["PATH"] = os.path.expanduser("~/.cargo/bin") + ":" + env["PATH"]
        r = subprocess.run(["cargo", "run", "--release", "--quiet", "--",
                            "run", "resting"],
                           cwd=os.path.join(ROOT, "physiology"),
                           capture_output=True, text=True, timeout=900, env=env)
        m = _re.search(r"trace hash: (0x[0-9a-f]+)", r.stdout)
        ok(m is not None and m.group(1) == case["physiology_link"]["trace_hash"],
           f"case1: engine trace hash reproduces ({m.group(1) if m else 'none'})")
        post = _re.search(
            r"post\s+: beats=\d+ HR=([\d.]+) bpm  BP=([\d.]+)/([\d.]+) mmHg  "
            r"MAP=([\d.]+).*?CO=([\d.]+) L/min  SVlv=([\d.]+) mL.*?"
            r"CVP=([\d.]+) mmHg", r.stdout)
        exp = case["physiology_link"]["baseline_recorded_outputs"]
        got = {"heart_rate_per_min": float(post.group(1)),
               "systolic_bp_mmhg": float(post.group(2)),
               "diastolic_bp_mmhg": float(post.group(3)),
               "map_mmhg": float(post.group(4)),
               "cardiac_output_l_min": float(post.group(5)),
               "stroke_volume_lv_ml": float(post.group(6)),
               "cvp_mmhg": float(post.group(7))}
        ok(all(abs(got[k] - exp[k]) < 0.051 for k in exp),
           f"case1: engine resting outputs match the recorded baseline ({got})")
    except Exception as e:  # pragma: no cover
        ok(False, f"case1: physiology engine re-run failed: {e}")

    # ---- theatre handoff -------------------------------------------
    ok(PROC_FILE["id"] == case["management"]["handoff"]["procedure_id"]
       == "proc.chole.lap",
       "case1: handoff procedure id matches the theatre file")
    reg = {s["id"]: s for s in PROC_FILE["structures"]}
    ok(reg["organ.gallbladder"]["kind"] == "record"
       and reg["organ.gallbladder"]["resolves_to"] == "data/digestive/digestive.json",
       "case1: theatre register resolves organ.gallbladder")
    commit = attempt["stages"][-1]["commit"]
    ok(commit["diagnosis_hypothesis"] == case["adjudication"]["diagnosis_hypothesis"]
       and "proc.chole.lap" in commit["management"],
       "case1: attempt commit matches adjudication and names the handoff procedure")

    # ---- FHIR export -------------------------------------------------
    def all_systems(o, acc):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "system" and isinstance(v, str):
                    acc.add(v)
                all_systems(v, acc)
        elif isinstance(o, list):
            for v in o:
                all_systems(v, acc)
        return acc
    bundle_doc = load(os.path.join(CASES, "fhir", "case.ruq-pain.001.bundle.json"))
    systems = all_systems(bundle_doc, set())
    ok(not any("snomed" in s.lower() or "loinc" in s.lower() for s in systems),
       f"case1: no SNOMED CT / LOINC among the bundle's coding systems ({sorted(systems)})")
    bundle = bundle_doc["bundle"]
    res = {e["resource"]["id"]: e["resource"] for e in bundle["entry"]}
    cond = next(r for r in res.values() if r["resourceType"] == "Condition")
    ok(cond["code"]["coding"][0]["code"] == case["ground_truth"]["mondo"],
       "case1: FHIR Condition code == ground-truth Mondo")
    obs = {r["code"]["coding"][0]["code"]: r for r in res.values()
           if r["resourceType"] == "Observation"}
    for lab in case["labs"]:
        code = lab["id"].split(".", 1)[1]
        o = obs.get(code)
        ok(o is not None
           and abs(o["valueQuantity"]["value"] - lab["value"]) < 1e-9
           and o["valueQuantity"]["unit"] == lab["unit"],
           f"case1: FHIR Observation {code} == case lab value and unit")


# =====================================================================
# Case 2 profile (Milestone 22): labs, classification, timing, LOOP
# =====================================================================
def profile_case2(case, ctx, boards):
    print(f"\n=== {case['id']} profile: labs / classification / timing / THE LOOP ===")
    labs = ctx.labs
    bil = labs["lab.bilirubin-total"]
    ok(bil["value"] >= 2.0 and bil["value"] > bil["reference_range"]["high"],
       "case2: bilirubin 6.8 >= TG18 B-1 threshold 2.0 and above cited range")
    for lid, fold in (("lab.alp", 4.0), ("lab.alt", 2.7), ("lab.ast", 2.7)):
        l = labs[lid]
        f = l["value"] / l["reference_range"]["high"]
        ok(l["value"] > 1.5 * l["reference_range"]["high"] and abs(f - fold) < 0.15,
           f"case2: {lid} {l['value']} = {f:.2f}x ULN (TG18 B-2 >1.5x met)")
    ok(labs["lab.wbc"]["value"] <= 10.0, "case2: WBC 8.9 <= 10.0 (TG18 A-2 unmet)")
    ok(labs["lab.crp"]["value"] < 10, "case2: CRP 8 < 10 (TG18 A-2 unmet)")
    chol = [b for b in ctx.blocks if b["id"] == "tg18_cholangitis"][0]
    for s in (1, 2, 3, 4):
        ev = ctx.block_eval(chol, s)
        ok(ev["status"] == "not suspected",
           f"case2: TG18 cholangitis not suspected at stage {s} (A unmet, mechanically)")
    ev4 = ctx.block_eval(chol, 4)
    ok(ev4["groups"] == {"A": False, "B": True, "C": True},
       "case2: cholangitis groups at final stage = A false, B true, C true")

    cls_block = [b for b in ctx.blocks if b["kind"] == "classification"][0]
    meas = ctx.meas["meas.stump-below-confluence-mm"]
    want = case["adjudication"]["classification"]
    ok(meas["value"] == want["stump_mm"] == 25,
       "case2: stump measurement == adjudication stump (25 mm)")
    ok(meas["value"] >= 20 and meas["value"] >= 1,
       "case2: E1 arithmetic — stump >= 20 mm true, >= 1 mm true, < 20 mm false")
    for s in (1, 2, 3):
        ok(ctx.block_eval(cls_block, s)["status"] != "classified",
           f"case2: classification pending at stage {s} (level evidence unrevealed)")
    fin = ctx.block_eval(cls_block, 4)
    ok(fin["result"]["strasberg"] == "E1" and fin["result"]["bismuth"] == "I",
       "case2: classification fires E1 / Bismuth I at stage 4")

    day = case["patient"]["postoperative_day"]
    band = ("le_72h" if day <= 3 else "72h_to_3wk" if day <= 21 else "late")
    ok(case["management"]["wses_timing_band"]["band"] == band == "72h_to_3wk",
       f"case2: WSES timing band recomputes from postoperative_day {day} -> {band}")
    ok("hepaticojejunostomy" in case["management"]["definitive_pathway"],
       "case2: definitive pathway names Roux-en-Y hepaticojejunostomy (C14 4.2/7.4)")

    # ---- THE LOOP: verify against the shipped Theatre debrief -----
    link = case["theatre_link"]
    tpath = os.path.join(ROOT, link["debrief_file"])
    raw = open(tpath, "rb").read()
    digest = hashlib.sha256(raw).hexdigest()
    ok(digest == link["debrief_sha256"],
       f"case2 LOOP: trace-02 debrief SHA-256 recomputes ({digest[:16]}...)")
    td = json.loads(raw)
    mf = link["matched_fields"]
    ok(td["verdict"] == mf["verdict"] == "FAIL", "case2 LOOP: verdict FAIL")
    ok(td["failed_at_s"] == mf["failed_at_s"] == 1920.0,
       "case2 LOOP: failed_at_s 1920.0")
    ok(mf["fail_reason_contains"] in td["fail_reason"],
       "case2 LOOP: fail_reason names err.divide-unidentified")
    ok(td["checklist"]["completed"] == mf["checklist_completed"] == 32
       and td["checklist"]["required"] == mf["checklist_required"] == 64,
       "case2 LOOP: checklist 32/64")
    ok(td["safety_gate"]["points"] == mf["safety_gate_points"] == 0,
       "case2 LOOP: safety gate 0 points")
    ok(td["management"]["points"] == mf["management_points"] == 5
       and td["management"]["max"] == mf["management_max"] == 5,
       "case2 LOOP: management 5/5")
    bdi = [c for c in td["complications"] if c["kind"] == "bile-duct-injury"]
    ok(len(bdi) == 1, "case2 LOOP: exactly one bile-duct-injury complication")
    if bdi:
        b = bdi[0]
        m = mf["complication_bdi"]
        ok(b["stewart_way_class"] == m["stewart_way_class"] == "III"
           and b["resolved_structure"] == m["resolved_structure"]
           and b["t_onset_s"] == m["t_onset_s"] == 1920.0
           and b["recognised"] == m["recognised"] is True,
           "case2 LOOP: BDI = Stewart-Way III, duct.common-bile, t=1920s, recognised")
    clip = [c for c in td["complications"]
            if c["kind"] == "clip-on-common-bile-duct"]
    ok(len(clip) == 1 and clip[0]["stewart_way_class"] == "I (mechanism)"
       and clip[0]["t_onset_s"] == 1860.0,
       "case2 LOOP: clip complication = class I mechanism at t=1860s")
    dp4 = [x for x in td["decisions"] if x["id"] == "dp4"]
    ok(len(dp4) == 1 and dp4[0]["choice"] == "drain-refer"
       and dp4[0]["t_s"] == 2220.0,
       "case2 LOOP: dp4 = drain-refer at t=2220s")
    ok(any(ev["text"].startswith("m7.6:") for ev in td["event_log"]),
       "case2 LOOP: drain microstep m7.6 present in the event log")
    ok(td["trace_id"] == case["theatre_link"]["trace_id"],
       "case2 LOOP: trace id matches")
    print(f"  loop evidence: trace {td['trace_id']}, verdict {td['verdict']}, "
          f"failed_at_s {td['failed_at_s']}, checklist "
          f"{td['checklist']['completed']}/{td['checklist']['required']}, "
          f"management {td['management']['points']}/{td['management']['max']}, "
          f"BDI class {bdi[0]['stewart_way_class'] if bdi else '?'}")


def main():
    attempts = {}
    for p in glob.glob(os.path.join(CASES, "attempts", "*.json")):
        a = load(p)["attempt"]
        attempts[a["case_id"]] = a
    print("ANATOMICA case checker (Milestone 20 machinery, parameterised "
          "at Milestone 22)")
    print(f"parameters: {len(PARAMS['parameters'])} cited, "
          f"{len(PARAMS['lr_derivations'])} LR derivations; sources "
          f"{', '.join(sorted(SOURCES))}")
    print(f"shared registers: {len(INVS)} body-model records, "
          f"{len(STRUCT_IDS)} theatre structures")
    profiles = {}
    for p in sorted(glob.glob(os.path.join(CASES, "case.*.json"))):
        case = load(p)["case"]
        slug = case["id"].replace(".", "-")
        debrief = load(os.path.join(
            CASES, "debriefs", f"debrief.{slug}.model-learner.json"))
        profiles[case["id"]] = check_case(p, attempts[case["id"]], debrief)
    if "case.ruq-pain.001" in profiles:
        c, ctx, _ = profiles["case.ruq-pain.001"]
        profile_case1(c, ctx, attempts["case.ruq-pain.001"])
    if "case.post-op-jaundice.002" in profiles:
        c, ctx, boards = profiles["case.post-op-jaundice.002"]
        profile_case2(c, ctx, boards)

    print(f"\n{'ALL CHECKS PASS' if FAIL == 0 else 'FAILURES PRESENT'}: "
          f"{PASS} passed, {FAIL} failed")
    for n in NOTES:
        print(f"  note: {n}")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
