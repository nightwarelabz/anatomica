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
     score — Milestone 29, severity) recompute from the declared blocks; anchoring events
     and order classifications recompute; resource tally recomputes;
  6. governance: synthetic, review gate UNMET (never fabricated),
     validity dual-sourced-draft, and NO composite score key anywhere.

Plus per-case profile sections: case 1 (lab arithmetic, the imaging
voxel recount, the physiology engine re-run, the Theatre handoff, the
FHIR export), case 2 (lab arithmetic, the classification
arithmetic, the WSES timing band, the anchoring headline, and the
LOOP verification: the trace-02 Theatre debrief is re-read, its
SHA-256 recomputed, and every matched field compared field-by-field
against the file's actual contents), and case 3 (Milestone 29: both
scores' arithmetic stage by stage, the ectopic rule-out timing, the
colon-label recount and the recorded absence of an appendix label,
the physiology link's identity with case 1's engine state, and the
appendicectomy handoff with its branch consistency).

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
        if block["kind"] == "score":
            items = {}
            total = 0
            not_assessed = []
            for it in block["items"]:
                r = self.score_item(it, stage)
                items[it["id"]] = r
                total += r["points"]
                if r["state"] == "unknown":
                    not_assessed.append(it["id"])
            status = block["default_status"]
            for band in block["bands"]:
                if band["min"] <= total <= band["max"]:
                    status = band["status"]
                    break
            return {"items": items, "total": total,
                    "max_total": block["max_total"],
                    "not_assessed": not_assessed,
                    "partial": bool(not_assessed), "status": status}
        raise ValueError(block["kind"])

    def score_item(self, item, stage, excl=frozenset()):
        """Independent re-implementation of the runner's score item
        (Milestone 29): tiers highest-first, first satisfied tier wins;
        unsatisfied only if every tier is unsatisfied; else unknown."""
        tiers = item["tiers"] if "tiers" in item else [
            {"points": item["points"], "evidence": item["evidence"]}]
        states = []
        for t in tiers:
            vals = [self.atom3(a, stage, excl) for a in t["evidence"]]
            if "satisfied" in vals:
                states.append("satisfied")
            elif vals and all(v == "unsatisfied" for v in vals):
                states.append("unsatisfied")
            else:
                states.append("unknown")
        for t, s in zip(tiers, states):
            if s == "satisfied":
                return {"state": "satisfied", "points": t["points"]}
        if states and all(s == "unsatisfied" for s in states):
            return {"state": "unsatisfied", "points": 0}
        return {"state": "unknown", "points": 0}

    def crit_items(self, stage, excl=frozenset()):
        out = {}
        for b in self.blocks:
            if b["kind"] == "grouped":
                its = [i for g in b["groups"] for i in g["items"]]
            elif b["kind"] == "k_of_n":
                its = b["items"]
            elif b["kind"] == "score":
                for i in b["items"]:
                    r = self.score_item(i, stage, excl)
                    out[f"{b['id']}.{i['id']}"] = (
                        f"satisfied:{r['points']}"
                        if r["state"] == "satisfied" else r["state"])
                continue
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
        elif b["kind"] == "score":
            its = []
            for i in b["items"]:
                atoms = list(i.get("evidence", []))
                for t in i.get("tiers", []):
                    atoms += list(t.get("evidence", []))
                its.append({"id": i["id"], "evidence": atoms})
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


# =====================================================================
# Case 3 profile (Milestone 29): score arithmetic, the disagreement,
# the anchoring headline, the imaging absence, physiology, handoff
# =====================================================================
def profile_case3(case, ctx, boards, attempt):
    print(f"\n=== {case['id']} profile: scores / anchoring / imaging / "
          f"physiology / theatre ===")
    labs, meas = ctx.labs, ctx.meas
    ok(10.0 <= labs["lab.wbc"]["value"] < 15.0,
       "case3: WBC 12.4 in the AIR band 10.0-14.9 and above the Alvarado line 10.0")
    ok(75 < labs["lab.neutrophils-pct"]["value"] < 85,
       "case3: neutrophils 78% above the Alvarado shift line (75) and inside the AIR band 70-84")
    ok(10 <= labs["lab.crp"]["value"] < 50,
       "case3: CRP 26 mg/L inside the AIR band 10-49")
    t = meas["meas.temperature-c"]["value"]
    ok(t >= 37.3 and t < 38.5,
       "case3: temperature 37.6 C meets the Alvarado line (37.3) and misses the AIR line (38.5) — the divergence datum")
    ok(meas["meas.rebound-grade"]["value"] == 1,
       "case3: rebound grade 1 (light) — Alvarado 1 point, AIR 1 of 3")

    alv = [b for b in ctx.blocks if b["id"] == "alvarado"][0]
    air = [b for b in ctx.blocks if b["id"] == "air"][0]
    a1, a4 = ctx.block_eval(alv, 1), ctx.block_eval(alv, 4)
    r1, r4 = ctx.block_eval(air, 1), ctx.block_eval(air, 4)
    ok(a1["total"] == 7 and a1["not_assessed"] == ["leukocytosis", "shift"]
       and a1["partial"] is True,
       f"case3: Alvarado stage-1 partial = 7, not-assessed {a1['not_assessed']}")
    ok(a4["total"] == 10 and a4["status"] == "very probable"
       and a4["partial"] is False,
       "case3: Alvarado final = 10/10 'very probable'")
    ok(r1["total"] == 3 and r1["not_assessed"] == ["pmn", "wbc", "crp"]
       and r1["partial"] is True,
       f"case3: AIR stage-1 partial = 3, not-assessed {r1['not_assessed']}")
    ok(r4["total"] == 6 and r4["status"] == "intermediate probability"
       and r4["partial"] is False,
       "case3: AIR final = 6/12 'intermediate probability'")
    cmp_ = case["adjudication"]["score_comparison"]
    ok(cmp_["alvarado_final"]["total"] == a4["total"]
       and cmp_["alvarado_final"]["status"] == a4["status"]
       and cmp_["air_final"]["total"] == r4["total"]
       and cmp_["air_final"]["status"] == r4["status"],
       "case3: adjudication's stated score comparison matches the computed scores")

    ok(boards[1]["hyp.ectopic-pregnancy"] >= RULE_OUT
       and boards[2]["hyp.ectopic-pregnancy"] < RULE_OUT,
       "case3: ectopic pregnancy live at stage 1, ruled out at stage 2 by the negative hCG")
    ok(boards[4]["hyp.acute-appendicitis"] > 0.96,
       "case3: workbench appendicitis posterior > 0.96 after CT")

    # ---- imaging link: recount + the recorded absence ---------------
    import numpy as np
    bindir = os.path.join(ROOT, "web", "data", "imaging", "s0778")
    counts = []
    for i in range(431):
        arr = np.fromfile(os.path.join(bindir, f"lbl-{i:04d}.bin"), dtype=np.uint8)
        counts.append(int((arr == 9).sum()))
    present = [i for i, cn in enumerate(counts) if cn > 0]
    link = case["imaging_link"]
    m = link["measures"]
    ok([present[0], present[-1]] == m["slice_files_0based"] == [45, 248],
       f"case3: colon slices recounted {present[0]}..{present[-1]} (0-based files)")
    ok(len(present) == m["slices_with_label"] == 204,
       "case3: 204 slices carry the colon label")
    ok(sum(counts) == 324670
       == link["label"]["hu_statistics_from_crosswalk"]["voxels"],
       "case3: total colon voxels recounted: 324,670")
    mx = max(range(431), key=lambda i: counts[i])
    ok(mx == m["max_cross_section"]["file_index_0based"] == 186
       and counts[mx] == m["max_cross_section"]["voxels"] == 4722,
       f"case3: max colon cross-section recounted: file {mx}, {counts[mx]} voxels")
    ok(abs(324670 * 3.375 / 1000 - 1095.76) < 0.01,
       "case3: volume arithmetic 324,670 x 3.375 mm3 = 1095.76 mL")
    cw = load(os.path.join(ROOT, "data", "imaging", "s0778", "crosswalk.json"))
    ok(all(l["label"] != "appendix" for l in cw["labels"]),
       "case3: NO appendix label exists in the shipped s0778 label set (recorded absence)")
    colon = next(l for l in cw["labels"] if l["label"] == "colon")
    ok(colon["record_ids"] == ["large-intestine"] and colon["index"] == 9
       and link["label"]["record_id"] == "large-intestine",
       "case3: crosswalk maps label 9 (colon) to record 'large-intestine'")
    hu = link["label"]["hu_statistics_from_crosswalk"]
    ok(all(colon["hu"][k] == hu[k] for k in ("mean", "median", "p5", "p95", "min", "max")),
       "case3: case HU statistics equal crosswalk values")
    ok("does NOT show" in link["honesty_block"],
       "case3: imaging honesty block states what the series does not show")
    ok("canal.appendix" in INVS,
       "case3: the Body Model HAS an appendix record (canal.appendix) — the asymmetry is real")
    dig = load(os.path.join(ROOT, "data", "digestive", "digestive.json"))
    ok(any((r.get("id") or r.get("record_id")) == "dig.cecum-appendix"
           for r in dig["records"]),
       "case3: compound clinical record dig.cecum-appendix exists")

    # ---- physiology link: same engine state as case 1 ---------------
    c1 = load(os.path.join(CASES, "case.ruq-pain.001.json"))["case"]
    ok(case["physiology_link"]["trace_hash"]
       == c1["physiology_link"]["trace_hash"] == "0x6369b10e9a71c872",
       "case3: physiology link records the current engine trace hash (case 1's profile re-runs the engine itself)")
    ok(case["physiology_link"]["baseline_recorded_outputs"]
       == c1["physiology_link"]["baseline_recorded_outputs"],
       "case3: baseline outputs identical to case 1's recorded baseline (same engine state)")

    # ---- theatre handoff ---------------------------------------------
    appy = load(os.path.join(
        ROOT, "theatre", "procedures", "proc.lap-appendectomy.json"))["procedure"]
    ok(appy["id"] == case["management"]["handoff"]["procedure_id"]
       == "proc.appy.lap",
       "case3: handoff procedure id matches the theatre file (proc.appy.lap)")
    reg = {s["id"]: s for s in appy["structures"]}
    ok(reg["canal.appendix"]["kind"] == "record"
       and reg["canal.appendix"]["resolves_to"]
       == "data/digestive/digestive-inventory.json",
       "case3: theatre register resolves canal.appendix")
    req = sum(1 for ph in appy["phases"] for st in ph["steps"]
              for ms in st["microsteps"] if ms.get("required"))
    ok(req == 36, f"case3: standard configuration requires {req} microsteps (36)")
    ok(case["management"]["handoff"]["procedure_configuration"] == "standard"
       and "standard position" in ctx.findings["f.ct-appendicitis"]["text"]
       and "perforation" in ctx.findings["f.ct-uncomplicated"]["text"],
       "case3: branch consistency — standard position + recorded no-perforation findings behind the standard configuration")
    commit = attempt["stages"][-1]["commit"]
    ok(commit["diagnosis_hypothesis"] == case["adjudication"]["diagnosis_hypothesis"]
       and "proc.appy.lap" in commit["management"],
       "case3: attempt commit matches adjudication and names the handoff procedure")


def profile_case4(case, ctx, boards, attempt):
    print(f"\n=== {case['id']} profile: CTS-6 / anchoring / imaging "
          f"absence / links / theatre handoff (M42) ===")
    labs = ctx.labs
    ok(labs["lab.hba1c"]["value"] == 6.8 and 6.5 <= 6.8 < 7.0,
       "case4: HbA1c 6.8% at/above the C29 diabetes threshold (6.5%) and "
       "below the 7% goal C29 states — consistent with known diabetes, "
       "settles nothing about neuropathy")

    cts6 = [b for b in ctx.blocks if b["id"] == "cts6"][0]
    e1 = ctx.block_eval(cts6, 1)
    e2 = ctx.block_eval(cts6, 2)
    e4 = ctx.block_eval(cts6, 4)
    ok(e1["total"] == 7.5 and e1["partial"] is True
       and e1["not_assessed"] == ["thenar_atrophy_or_weakness", "phalen",
                                  "two_point_discrimination_loss", "tinel"],
       f"case4: CTS-6 stage-1 partial = 7.5, not-assessed {e1['not_assessed']}")
    ok(e2["total"] == 16.5 and e2["partial"] is False
       and e2["status"].startswith("positive"),
       "case4: CTS-6 complete at stage 2 = 16.5/26, positive band")
    ok(e4["total"] == 16.5 and e4["status"] == e2["status"],
       "case4: CTS-6 unchanged by stages 3-4 (it is an examination instrument)")
    cmp_ = case["adjudication"]["score_comparison"]
    ok(cmp_["cts6_final"]["total"] == e4["total"]
       and cmp_["cts6_final"]["status"] == e4["status"]
       and cmp_["cts6_stage1_partial"]["total"] == e1["total"],
       "case4: adjudication's stated CTS-6 comparison matches the computed scores")

    ok([round(boards[s]["hyp.carpal-tunnel-syndrome"], 4) for s in (1, 2, 3, 4)]
       == [0.7778, 0.6364, 0.9114, 0.9943],
       "case4: workbench CTS trajectory 0.7778 -> 0.6364 (the LR- dip) "
       "-> 0.9114 -> 0.9943")
    ok(boards[3]["hyp.cervical-radiculopathy"] >= RULE_OUT
       and boards[4]["hyp.cervical-radiculopathy"] < RULE_OUT,
       "case4: cervical radiculopathy live at stage 3 (0.0234), ruled out "
       "only at stage 4 by the electrodiagnostic protocol")
    ok(all(boards[3][h] < RULE_OUT and boards[2][h] >= RULE_OUT for h in
           ("hyp.pronator-syndrome", "hyp.diabetic-polyneuropathy",
            "hyp.brachial-plexopathy")),
       "case4: pronator / polyneuropathy / plexopathy first ruled out at "
       "stage 3 (the ultrasound stage)")
    ruled = {}
    for s in (1, 2, 3, 4):
        for h, p in boards[s].items():
            if p < RULE_OUT and h not in ruled:
                ruled[h] = s
    events = []
    for st in attempt["stages"]:
        s = st["stage"]
        for h, lp in st["board"].items():
            if lp >= ANCHOR and h in ruled and ruled[h] <= s:
                events.append((s, h))
    ok(events == [(4, "hyp.cervical-radiculopathy")],
       f"case4: exactly one anchoring event, recomputed: {events}")
    ok(attempt["stages"][3]["board"]["hyp.cervical-radiculopathy"] == 0.15,
       "case4: the anchored residue is 0.15 at stage 4")

    # ---- imaging: the recorded absence, re-verified ------------------
    ok("imaging_link" not in case and "imaging_assessment" in case,
       "case4: no imaging_link declared — the assessment block records "
       "why none can be")
    label_sets = {}
    for sid in ("s0778", "s1090"):
        cw = load(os.path.join(ROOT, "data", "imaging", sid, "crosswalk.json"))
        names = sorted(l["label"] for l in cw["labels"])
        label_sets[sid] = names
        ok(len(names) == 104,
           f"case4: {sid} label set recounted at 104 labels")
        ok(not any(any(w in n for w in
                       ("nerve", "median", "carpal", "wrist", "hand"))
                   for n in names),
           f"case4: {sid} label set contains no nerve / median / carpal / "
           "wrist / hand label")
        ser = load(os.path.join(ROOT, "data", "imaging", sid, "series.json"))
        ok(ser["subject"]["meta_csv_row"]["study_type"]
           == "ct thorax-abdomen-pelvis",
           f"case4: {sid} is a thorax-abdomen-pelvis study — the wrist is "
           "outside the imaged volume")
    ok(label_sets["s0778"] == label_sets["s1090"],
       "case4: the two subjects' label sets are identical")

    # ---- links: median nerve records + the M35 honesty claim ---------
    ok("nerve.right-median-nerve" in INVS and "nerve.left-median-nerve" in INVS,
       "case4: Body Model inventory holds both median nerve records (M33)")
    mn = load(os.path.join(ROOT, "data", "nervous", "major-nerves.json"))
    med = next(r for r in mn["records"] if r["id"] == "major.median")
    ok(sorted(med["geometry_record_ids"]) ==
       ["nerve.left-median-nerve", "nerve.right-median-nerve"],
       "case4: M39 record major.median links exactly the two inventory nerves")
    mus = load(os.path.join(ROOT, "data", "muscular", "muscles.json"))
    ok(any(r.get("record_id") == "muscle.abductor-pollicis-brevis"
           for r in mus["records"]),
       "case4: thenar muscle record muscle.abductor-pollicis-brevis exists")
    pas = load(os.path.join(ROOT, "data", "innervation-link-pass.json"))
    phrase = next(p for p in pas["phrases"]
                  if p["phrase"] == "recurrent branch of the median nerve")
    ok(phrase["status"] == "unresolved"
       and phrase["components"][0]["status"] == "absent",
       "case4: M35 pass indeed leaves the recurrent branch unresolved / "
       "absent — the case's thenar link honesty claim is true")

    # ---- no physiology link; the Milestone 42 theatre handoff --------
    ok("physiology_link" not in case
       and case["ground_truth"]["engine_state"].startswith("No physiology link"),
       "case4: no physiology link declared (case-2 precedent), gap stated")
    proc_ids = set()
    for p in glob.glob(os.path.join(ROOT, "theatre", "procedures", "*.json")):
        proc_ids.add(load(p)["procedure"]["id"])
    ok(proc_ids == {"proc.chole.lap", "proc.appy.lap", "proc.carpal-release",
                    "proc.ulnar-decompression", "proc.lap-inguinal-hernia"},
       f"case4: the Theatre holds exactly {sorted(proc_ids)} — the carpal "
       "tunnel release authored at Milestone 42 is the handoff target (the "
       "ulnar decompression joined it at Milestone 44; the inguinal hernia "
       "repair joined at Milestone 49 — set assertion updated in the "
       "Milestone 44 maintenance pattern, the handoff itself unchanged)")
    ho = case["management"]["handoff"]
    ok(ho["procedure_id"] == "proc.carpal-release"
       and ho["module"] == "theatre" and ho["from_case_stage"] == 4
       and ho["procedure_configuration"] == "standard",
       "case4: handoff names proc.carpal-release, standard (open) "
       "configuration, from stage 4")
    ctp = load(os.path.join(
        ROOT, "theatre", "procedures", "proc.carpal-release.json"))["procedure"]
    ok(ctp["id"] == ho["procedure_id"],
       "case4: handoff procedure id matches the theatre file "
       "(proc.carpal-release)")
    reg = {s["id"]: s for s in ctp["structures"]}
    ok(reg["major.median"]["kind"] == "record"
       and reg["major.median"]["resolves_to"]
       == "data/nervous/major-nerves.json",
       "case4: theatre register resolves major.median — the case's own "
       "clinical link is the procedure's decompressed structure")
    ok(reg["nerve.recurrent-branch-median"]["kind"] == "absence",
       "case4: the register carries the recurrent branch as an absence — "
       "the M35 honesty claim, inherited by the procedure's safety gate")
    ok("proc.carpal-release" in case["management"]["theatre_link_verified"]
       and "Milestone 42" in case["management"]["theatre_note"],
       "case4: management carries the link-verification note and the "
       "dated record of the handoff's arrival")

    # ---- ontology discipline ------------------------------------------
    hyps = {h["id"]: h for h in case["hypotheses"]}
    ok(hyps["hyp.carpal-tunnel-syndrome"]["mondo"] == "MONDO:0007275"
       and case["ground_truth"]["mondo"] == "MONDO:0007275",
       "case4: diagnosis coded MONDO:0007275 on hypothesis and ground truth")
    ok(hyps["hyp.pronator-syndrome"]["mondo"] is None
       and "MONDO:0003598" in hyps["hyp.pronator-syndrome"]["mondo_note"],
       "case4: pronator syndrome unclassed, with the near-miss class named "
       "and refused in its note")
    ok(hyps["hyp.cervical-radiculopathy"]["mondo"] == "MONDO:0002959"
       and "mondo_note" in hyps["hyp.cervical-radiculopathy"],
       "case4: cervical hypothesis coded to the generic radiculopathy class "
       "with the absence of a cervical-specific class stated")
    ok(hyps["hyp.diabetic-polyneuropathy"]["mondo"] == "MONDO:0001583"
       and hyps["hyp.brachial-plexopathy"]["mondo"] == "MONDO:0006683",
       "case4: polyneuropathy / plexopathy Mondo ids as verified (C10 addendum)")

    # ---- debrief: classifications + tally ------------------------------
    slug = case["id"].replace(".", "-")
    deb = load(os.path.join(
        CASES, "debriefs", f"debrief.{slug}.model-learner.json"))["debrief"]
    cls = {o["test_id"]: o["classification"] for o in deb["orders"]}
    ok(cls == {"test.hand-exam-battery": "discriminating",
               "test.hba1c": "safety-net",
               "test.wrist-ultrasound": "discriminating",
               "test.cervical-mri": "non-contributory",
               "test.ncs-emg": "discriminating"},
       f"case4: order classifications {cls}")
    ok(deb["resource_tally"]["total_time_min"] == 170
       and deb["resource_tally"]["total_cost_units"] == 21,
       "case4: resource tally 170 min / 21 units")
    ok(deb["ruled_out_by_workbench"] ==
       {"hyp.pronator-syndrome": 3, "hyp.diabetic-polyneuropathy": 3,
        "hyp.brachial-plexopathy": 3, "hyp.cervical-radiculopathy": 4,
        "hyp.other-unspecified": 4},
       "case4: rule-out stages as designed (neck and residual last, at 4)")
    commit = attempt["stages"][-1]["commit"]
    ok(commit["diagnosis_hypothesis"]
       == case["adjudication"]["diagnosis_hypothesis"]
       and "carpal tunnel release" in commit["management"]
       and "proc.carpal-release" in commit["management"],
       "case4: attempt commit matches adjudication and names the theatre "
       "procedure the handoff targets (Milestone 42)")


# =====================================================================
# Case 5 profile (Milestone 43): McGowan block / branch anatomy /
# anchoring / imaging absence / links / theatre handoff (M44)
# =====================================================================
def profile_case5(case, ctx, boards, attempt):
    print(f"\n=== {case['id']} profile: McGowan / trajectory / anchoring / "
          f"imaging absence / links / theatre handoff (M44) ===")
    ok(len(case["findings"]) == 30 and len(case["labs"]) == 0
       and len(case.get("measurements", [])) == 5
       and len(case["available_tests"]) == 4,
       "case5: 30 findings, 0 labs, 5 measurements, 4 orderable tests")

    # ---- LR discipline: exactly three, all computed, all sourced ----
    lrs = {f["id"]: f["lr"] for f in case["findings"] if f.get("lr")}
    ok(set(lrs) == {"f.tinel-elbow", "f.elbow-us-csa-enlarged",
                    "f.edx-across-elbow-slowing"},
       f"case5: exactly three findings carry a board LR {sorted(lrs)}")
    ok(lrs["f.tinel-elbow"]["lr_plus"] == 35.0
       and lrs["f.tinel-elbow"]["source"] == "C33"
       and lrs["f.tinel-elbow"]["status"] == "computed",
       "case5: Tinel LR+ 35.0 computed from the C33 pair (0.70 / 0.02), "
       "spectrum caveat carried in its note")
    ok(abs(lrs["f.elbow-us-csa-enlarged"]["lr_plus"] - 9.4444) < 1e-9
       and lrs["f.elbow-us-csa-enlarged"]["source"] == "C32",
       "case5: elbow ultrasound LR+ 9.4444 computed from the C32 pooled pair")
    ok(lrs["f.edx-across-elbow-slowing"]["lr_plus"] == 7.4
       and lrs["f.edx-across-elbow-slowing"]["source"] == "C31",
       "case5: EDX LR+ 7.4 computed at the C31 parameter's least "
       "favourable supported combination (a disclosed floor)")
    ok(ctx.findings["f.dorsal-ulnar-sensory-loss"].get("lr") is None
       and ctx.findings["f.pressure-flexion-positive"].get("lr") is None,
       "case5: the decisive dorsal-branch finding and the combined "
       "pressure-flexion test carry NO LR — no consulted source quantifies "
       "the one, and the other's specificity is unstated in its source")

    # ---- McGowan block: pending at 1, grade II from 2 ----------------
    ok("classification" not in case["adjudication"],
       "case5: no adjudication 'classification' key — the McGowan block "
       "is a criteria block, not a Strasberg-style classification")
    mg = [b for b in ctx.blocks if b["id"] == "mcgowan"][0]
    e1 = ctx.block_eval(mg, 1)
    ok(e1["status"] != "classified" and e1["result"] is None
       and e1["inputs"]["motor_weakness"] == "unknown",
       "case5: McGowan not yet classifiable at stage 1 (motor "
       "examination unrevealed — the grade is not a history product)")
    for s in (2, 3, 4):
        ev = ctx.block_eval(mg, s)
        ok(ev["status"] == "classified"
           and ev["result"]["mcgowan_grade"] == "II"
           and ev["result"]["grade_label"] == "intermediate",
           f"case5: McGowan grade II (intermediate) at stage {s}")
    ok(ctx.findings["f.interosseous-paralysis"]["presence"] == "absent",
       "case5: the grade-III boundary is an examined absence (no "
       "interosseous paralysis on record), not missing data")
    cmp_ = case["adjudication"]["criteria_comparison"]
    ok(cmp_["mcgowan_final"]["grade"] == "II"
       and cmp_["mcgowan_stage1"]["grade"] is None,
       "case5: adjudication's stated McGowan comparison matches the "
       "computed block (II final, unclassifiable at stage 1)")

    # ---- trajectory + rule-out structure ------------------------------
    ok([round(boards[s]["hyp.ulnar-neuropathy-elbow"], 4)
        for s in (1, 2, 3, 4)] == [0.22, 0.908, 0.9894, 0.9986],
       "case5: workbench elbow trajectory 0.22 -> 0.9080 (Tinel) "
       "-> 0.9894 (elbow US) -> 0.9986 (EDX floor)")
    ok(boards[2]["hyp.ulnar-neuropathy-wrist"] >= RULE_OUT
       and boards[3]["hyp.ulnar-neuropathy-wrist"] < RULE_OUT,
       "case5: the wrist hypothesis survives stage 2 (0.0212 — the "
       "Tinel weight cannot retire it) and is ruled out at stage 3")
    ok(all(boards[2][h] < RULE_OUT and boards[1][h] >= RULE_OUT for h in
           ("hyp.c8-radiculopathy", "hyp.lower-trunk-plexopathy",
            "hyp.neurogenic-thoracic-outlet")),
       "case5: C8 / plexopathy / thoracic outlet first ruled out at "
       "stage 2")
    ok(boards[3]["hyp.other-unspecified"] < RULE_OUT
       and boards[2]["hyp.other-unspecified"] >= RULE_OUT,
       "case5: the residual retires at stage 3, arithmetically")

    # ---- anchoring: exactly one, self-installed, at stage 3 -----------
    ruled = {}
    for s in (1, 2, 3, 4):
        for h, p in boards[s].items():
            if p < RULE_OUT and h not in ruled:
                ruled[h] = s
    events = []
    for st in attempt["stages"]:
        s = st["stage"]
        for h, lp in st["board"].items():
            if lp >= ANCHOR and h in ruled and ruled[h] <= s:
                events.append((s, h))
    ok(events == [(3, "hyp.ulnar-neuropathy-wrist")],
       f"case5: exactly one anchoring event, recomputed: {events}")
    ok(attempt["stages"][2]["board"]["hyp.ulnar-neuropathy-wrist"] == 0.16
       and attempt["stages"][0]["board"]["hyp.ulnar-neuropathy-wrist"]
       == 0.34,
       "case5: the anchor's arc — wrist led the learner's board at "
       "stage 1 (0.34, the cycling frame) and was still held at 0.16 "
       "at stage 3, after the dorsal finding excluded it at stage 2")

    # ---- EDX / ultrasound internal consistency ------------------------
    meas = ctx.meas
    ok(meas["meas.ae-be-motor-cv"]["value"] < 50
       and meas["meas.be-w-motor-cv"]["value"]
       - meas["meas.ae-be-motor-cv"]["value"] > 10
       and meas["meas.cmap-amplitude-drop-pct"]["value"] > 20,
       "case5: the patient's EDX numbers meet the C31 focal criteria "
       "they are weighed with (38 < 50 m/s; 18 > 10 m/s slower; 28% > 20%)")
    ok(meas["meas.elbow-ulnar-csa"]["value"] >= 10
       and meas["meas.elbow-ulnar-csa"]["value"]
       > meas["meas.wrist-ulnar-csa"]["value"],
       "case5: elbow CSA 14 mm2 above the C32 cutoff and above the "
       "same patient's wrist CSA (5 mm2) — enlargement at the elbow")

    # ---- imaging: the recorded absence, re-verified -------------------
    ok("imaging_link" not in case and "imaging_assessment" in case,
       "case5: no imaging_link declared — the assessment block records "
       "why none can be")
    label_sets = {}
    for sid in ("s0778", "s1090"):
        cw = load(os.path.join(ROOT, "data", "imaging", sid, "crosswalk.json"))
        names = sorted(l["label"] for l in cw["labels"])
        label_sets[sid] = names
        ok(len(names) == 104, f"case5: {sid} label set recounted at 104")
        ok(not any(any(w in n for w in ("nerve", "ulnar", "elbow"))
                   for n in names),
           f"case5: {sid} label set contains no nerve / ulnar / elbow label")
        ser = load(os.path.join(ROOT, "data", "imaging", sid, "series.json"))
        ok(ser["subject"]["meta_csv_row"]["study_type"]
           == "ct thorax-abdomen-pelvis",
           f"case5: {sid} is a thorax-abdomen-pelvis study — neither the "
           "elbow nor the wrist is in the imaged volume")
    ok(label_sets["s0778"] == label_sets["s1090"],
       "case5: the two subjects' label sets are identical")

    # ---- links: ulnar records + the M35 honesty claims -----------------
    ok("nerve.right-ulnar-nerve" in INVS and "nerve.left-ulnar-nerve" in INVS,
       "case5: Body Model inventory holds both ulnar nerve records (M33)")
    mn = load(os.path.join(ROOT, "data", "nervous", "major-nerves.json"))
    uln = next(r for r in mn["records"] if r["id"] == "major.ulnar")
    ok(sorted(uln["geometry_record_ids"]) ==
       ["nerve.left-ulnar-nerve", "nerve.right-ulnar-nerve"],
       "case5: M39 record major.ulnar links exactly the two inventory nerves")
    ok("dorsal cutaneous branch is spared" in uln["clinical_testing"]
       and "Guyon" in uln["course"],
       "case5: major.ulnar states the wrist pattern the case's dorsal "
       "finding contradicts (dorsal branch spared in wrist lesions)")
    mus = load(os.path.join(ROOT, "data", "muscular", "muscles.json"))
    fcu = next(r for r in mus["records"]
               if (r.get("record_id") or r.get("id"))
               == "muscle.flexor-carpi-ulnaris")
    ok(sorted(fcu["innervation"]["nerve_record_ids"]) ==
       ["nerve.left-ulnar-nerve", "nerve.right-ulnar-nerve"],
       "case5: flexor carpi ulnaris carries M35 nerve_record_ids for "
       "both ulnar nerves (its phrase resolves)")
    pas = load(os.path.join(ROOT, "data", "innervation-link-pass.json"))
    deep = next(p for p in pas["phrases"]
                if p["phrase"] == "deep branch of the ulnar nerve")
    ok(deep["status"] == "unresolved"
       and deep["components"][0]["status"] == "absent",
       "case5: M35 pass leaves the deep branch of the ulnar nerve "
       "unresolved / absent — the intrinsic findings' honesty claim is true")

    # ---- no physiology link; the Milestone 44 theatre handoff --------
    ok("physiology_link" not in case
       and case["ground_truth"]["engine_state"].startswith(
           "No physiology link"),
       "case5: no physiology link declared (case-2 precedent), gap stated")
    proc_ids = set()
    for p in glob.glob(os.path.join(ROOT, "theatre", "procedures", "*.json")):
        proc_ids.add(load(p)["procedure"]["id"])
    ok(proc_ids == {"proc.chole.lap", "proc.appy.lap", "proc.carpal-release",
                    "proc.ulnar-decompression", "proc.lap-inguinal-hernia"},
       f"case5: the Theatre holds exactly {sorted(proc_ids)} — the ulnar "
       "decompression authored at Milestone 44 is the handoff target (the "
       "inguinal hernia repair joined at Milestone 49 — set assertion "
       "updated in the Milestone 44 maintenance pattern, the handoff "
       "itself unchanged)")
    ho = case["management"]["handoff"]
    ok(ho["procedure_id"] == "proc.ulnar-decompression"
       and ho["module"] == "theatre" and ho["from_case_stage"] == 4
       and ho["procedure_configuration"] == "standard",
       "case5: handoff names proc.ulnar-decompression, standard "
       "(in-situ) configuration, from stage 4")
    udp = load(os.path.join(
        ROOT, "theatre", "procedures", "proc.ulnar-decompression.json"))["procedure"]
    ok(udp["id"] == ho["procedure_id"],
       "case5: handoff procedure id matches the theatre file "
       "(proc.ulnar-decompression)")
    reg = {s["id"]: s for s in udp["structures"]}
    ok(reg["major.ulnar"]["kind"] == "record"
       and reg["major.ulnar"]["resolves_to"]
       == "data/nervous/major-nerves.json",
       "case5: theatre register resolves major.ulnar — the case's own "
       "clinical link is the procedure's decompressed structure")
    ok(reg["nerve.medial-cutaneous-nerve-of-forearm"]["kind"] == "record"
       and reg["nerve.medial-cutaneous-nerve-of-forearm"]["resolves_to"]
       == "data/nervous/nervous-inventory.json",
       "case5: theatre register resolves the medial antebrachial "
       "cutaneous nerve — the gate's second protected structure is a "
       "real Body Model record")
    ok("proc.ulnar-decompression" in case["management"]["theatre_link_verified"]
       and "Milestone 44" in case["management"]["theatre_note"],
       "case5: management carries the link-verification note and the "
       "dated record of the handoff's arrival")

    # ---- ontology discipline -------------------------------------------
    hyps = {h["id"]: h for h in case["hypotheses"]}
    ok(hyps["hyp.ulnar-neuropathy-elbow"]["mondo"] == "MONDO:0043982"
       and case["ground_truth"]["mondo"] == "MONDO:0043982",
       "case5: diagnosis coded MONDO:0043982 (cubital tunnel syndrome) "
       "on hypothesis and ground truth")
    ok(hyps["hyp.ulnar-neuropathy-wrist"]["mondo"] == "MONDO:0007006"
       and "MONDO:0007006" in hyps["hyp.ulnar-neuropathy-wrist"]["mondo_note"]
       and "No Guyon" in hyps["hyp.ulnar-neuropathy-wrist"]["mondo_note"],
       "case5: wrist hypothesis coded to the generic ulnar neuropathy "
       "class with the absent Guyon-specific class stated, not fabricated")
    ok(hyps["hyp.neurogenic-thoracic-outlet"]["mondo"] == "MONDO:0015061"
       and hyps["hyp.c8-radiculopathy"]["mondo"] == "MONDO:0002959"
       and "mondo_note" in hyps["hyp.c8-radiculopathy"]
       and hyps["hyp.lower-trunk-plexopathy"]["mondo"] == "MONDO:0006683"
       and hyps["hyp.other-unspecified"]["mondo"] is None
       and hyps["hyp.other-unspecified"].get("mondo_note"),
       "case5: NTOS / generic-radiculopathy / plexopathy / residual "
       "Mondo coding as verified in the C10 Milestone 43 addendum")

    # ---- debrief: classifications + tally -------------------------------
    slug = case["id"].replace(".", "-")
    deb = load(os.path.join(
        CASES, "debriefs", f"debrief.{slug}.model-learner.json"))["debrief"]
    cls = {o["test_id"]: o["classification"] for o in deb["orders"]}
    ok(cls == {"test.targeted-exam-battery": "discriminating",
               "test.wrist-ultrasound": "non-contributory",
               "test.elbow-ultrasound": "discriminating",
               "test.edx-ulnar-protocol": "safety-net"},
       f"case5: order classifications {cls}")
    ok(deb["resource_tally"]["total_time_min"] == 125
       and deb["resource_tally"]["total_cost_units"] == 14,
       "case5: resource tally 125 min / 14 units")
    ok(deb["ruled_out_by_workbench"] ==
       {"hyp.c8-radiculopathy": 2, "hyp.lower-trunk-plexopathy": 2,
        "hyp.neurogenic-thoracic-outlet": 2,
        "hyp.ulnar-neuropathy-wrist": 3, "hyp.other-unspecified": 3},
       "case5: rule-out stages as designed (proximal rivals at 2, the "
       "anchored wrist and the residual at 3)")
    commit = attempt["stages"][-1]["commit"]
    ok(commit["diagnosis_hypothesis"]
       == case["adjudication"]["diagnosis_hypothesis"]
       and "proc.ulnar-decompression" in commit["management"],
       "case5: attempt commit matches adjudication and names the theatre "
       "procedure the handoff targets (Milestone 44)")


def profile_case6(case, ctx, boards, attempt):
    print(f"\n=== {case['id']} profile: Wells / PERC / CURB-65 / A-a "
          f"arithmetic / ESC class / trajectory / anchoring / physiology "
          f"+ imaging links / no theatre handoff (M48) ===")
    ok(len(case["findings"]) == 37 and len(case["labs"]) == 10
       and len(case.get("measurements", [])) == 10
       and len(case["available_tests"]) == 10,
       "case6: 37 findings, 10 labs, 10 measurements, 10 orderable tests")

    # ---- LR discipline: exactly four, all computed, all sourced ----
    lrs = {f["id"]: f["lr"] for f in case["findings"] if f.get("lr")}
    ok(set(lrs) == {"f.bnp-elevated", "f.ddimer-positive",
                    "f.ctpa-pe-positive", "f.lus-no-blines"},
       f"case6: exactly four findings carry a board LR {sorted(lrs)}")
    ok(lrs["f.bnp-elevated"]["lr_plus"] == 3.75
       and lrs["f.bnp-elevated"]["source"] == "C36"
       and lrs["f.bnp-elevated"]["status"] == "computed",
       "case6: BNP LR+ 3.75 computed from the C36 pair (0.90 / 0.24)")
    ok(abs(lrs["f.ddimer-positive"]["lr_plus"] - 1.6441) < 1e-9
       and lrs["f.ddimer-positive"]["source"] == "C39"
       and "lr_minus" not in lrs["f.ddimer-positive"],
       "case6: D-dimer LR+ 1.6441 computed from the C39 pooled pair "
       "(0.97 / 0.59), and deliberately NO lr_minus — in a "
       "post-surgical patient a below-cutoff result was never going "
       "to be allowed to exclude, so no exclusion weight is registered")
    ok(lrs["f.ctpa-pe-positive"]["lr_plus"] == 20.75
       and lrs["f.ctpa-pe-positive"]["source"] == "C40",
       "case6: CTPA LR+ 20.75 computed from the conservative PIOPED II "
       "pair (0.83 / 0.04), not the larger pooled pair in C39")
    ok(abs(lrs["f.lus-no-blines"]["lr_minus"] - 0.1176) < 1e-9
       and lrs["f.lus-no-blines"]["source"] == "C43",
       "case6: absent-B-lines LR- 0.1176 computed from the C43 pooled "
       "pair (0.104 / 0.884); the review's published pooled 0.13 is "
       "recorded in the derivation")
    ok(ctx.findings["f.troponin-elevated"].get("lr") is None,
       "case6: the troponin finding carries NO LR — myocardial injury "
       "is not infarction, and no consulted source quantifies it for "
       "either hypothesis in this differential")

    # ---- the five blocks, stage by stage ------------------------------
    ok("classification" not in case["adjudication"],
       "case6: no adjudication 'classification' key — the blocks are "
       "criteria blocks (case-5 discipline)")
    blocks = {b["id"]: b for b in ctx.blocks}
    w = ctx.block_eval(blocks["wells_score"], 1)
    ok(w["total"] == 3.0 and w["partial"]
       and w["not_assessed"] == ["dvt_signs"]
       and w["status"] == "PE unlikely (two-tier)",
       "case6: Wells at stage 1 is a PARTIAL 3.0 (PE unlikely) with "
       "the DVT-signs item not yet assessed — the calves unmeasured")
    w2 = ctx.block_eval(blocks["wells_score"], 2)
    ok(w2["total"] == 6.0 and not w2["partial"]
       and w2["status"] == "PE likely (two-tier)",
       "case6: Wells completes at 6.0 (PE likely) at stage 2 — "
       "DVT signs 3 + tachycardia 1.5 + surgery 1.5")
    ok(all(i["id"] != "pe_is_top_diagnosis"
           for i in blocks["wells_score"]["items"]),
       "case6: the Wells clinician-judgment item is NOT a block item "
       "— a self-scored item cannot be both evidence and verdict; "
       "its exclusion and sensitivity are stated in the block note")
    p1 = ctx.block_eval(blocks["perc_rule"], 1)
    p2 = ctx.block_eval(blocks["perc_rule"], 2)
    ok(p1["total"] == 4 and p1["partial"]
       and p1["not_assessed"] == ["unilateral_leg_swelling"]
       and p2["total"] == 5 and not p2["partial"]
       and p2["status"].startswith("PERC positive"),
       "case6: PERC counts 4 (partial) at stage 1 and 5 complete at "
       "stage 2 — positive either way, and its < 15% gestalt "
       "precondition is stated unmet in the block note")
    c1 = ctx.block_eval(blocks["curb65"], 1)
    c2 = ctx.block_eval(blocks["curb65"], 2)
    ok(c1["total"] == 1 and c1["partial"]
       and c1["not_assessed"] == ["urea_over_7"]
       and c2["total"] == 1 and not c2["partial"]
       and "low severity band" in c2["status"],
       "case6: CURB-65 totals 1 (the age item alone) from stage 2 — "
       "a severity statement about a pneumonia this patient does "
       "not have, recorded as such")
    aa1 = ctx.block_eval(blocks["aa_assessment"], 1)
    ok(aa1["status"] != "classified" and aa1["result"] is None,
       "case6: the gas classification is pending at stage 1 — it is "
       "not a history product")
    for s in (2, 3, 4):
        ev = ctx.block_eval(blocks["aa_assessment"], s)
        ok(ev["status"] == "classified"
           and ev["result"]["pattern"] == "ventilation/perfusion mismatch",
           f"case6: A-a classification is V/Q mismatch at stage {s}")
    for s in (1, 2):
        ev = ctx.block_eval(blocks["esc_pe_risk"], s)
        ok(ev["status"] != "classified" and ev["result"] is None
           and ev["inputs"]["rv_dysfunction"] == "unknown",
           f"case6: ESC risk class pending at stage {s} — the RV "
           "input is unmeasured until the CTPA, by design")
    for s in (3, 4):
        ev = ctx.block_eval(blocks["esc_pe_risk"], s)
        ok(ev["status"] == "classified"
           and ev["result"]["esc_category"] == "intermediate-high",
           f"case6: ESC class intermediate-high at stage {s} "
           "(stable, sPESI >= 1 via HR 112, RV/LV 1.1, troponin 34)")
    cmp_ = case["adjudication"]["criteria_comparison"]
    ok(cmp_["wells_final"]["total"] == 6.0
       and cmp_["wells_stage1"]["total"] == 3.0
       and cmp_["perc_final"]["total"] == 5
       and cmp_["curb65_final"]["total"] == 1
       and cmp_["aa_final"]["pattern"] == "ventilation/perfusion mismatch"
       and cmp_["esc_risk_final"]["category"] == "intermediate-high",
       "case6: adjudication's stated criteria comparison matches the "
       "computed blocks at every stage")

    # ---- the A-a arithmetic, verified from the case's own numbers ----
    import math as _math
    pao2 = ctx.labs["lab.pao2"]["value"]
    paco2 = ctx.labs["lab.paco2"]["value"]
    ph = ctx.labs["lab.ph"]["value"]
    hco3 = ctx.labs["lab.hco3"]["value"]
    pao2_alv = 0.21 * (760 - 47) - paco2 * (0.21 + (1 - 0.21) / 0.8)
    aa = pao2_alv - pao2
    ok(abs(aa - ctx.meas["meas.aa-gradient"]["value"]) < 0.15,
       f"case6: the engine's alveolar gas equation on the case's own "
       f"gas gives A-a {aa:.1f} mmHg, matching the recorded "
       "measurement (51.8) — PAO2 113.8 at PaCO2 30, FiO2 0.21")
    ok(abs(6.1 + _math.log10(hco3 / (0.03 * paco2)) - ph) < 0.01,
       "case6: the authored gas is Henderson-Hasselbalch consistent "
       "(HCO3 22, PaCO2 30 -> pH 7.49)")
    ok(abs((2.5 + 0.21 * 71) - 17.41) < 0.01
       and ctx.meas["meas.aa-gradient"]["value"] > 17.41,
       "case6: the age-expected gradient (Mellemgaard, C46) is 17.41 "
       "mmHg at 71 and the patient's 51.8 exceeds it threefold")
    ok(case["physiology_link"]["respiratory_recorded_outputs"]
       ["aa_gradient_mmhg"] < ctx.meas["meas.aa-gradient"]["value"],
       "case6: the engine's resting gradient (9.3 mmHg) is the "
       "yardstick the patient's 51.8 is read against")

    # ---- trajectory + rule-out structure ------------------------------
    ok([round(boards[s]["hyp.pulmonary-embolism"], 4)
        for s in (1, 2, 3, 4)] == [0.36, 0.379, 0.9554, 0.9554],
       "case6: workbench PE trajectory 0.36 -> 0.3790 (the BNP stage: "
       "HF rises to 0.2881 and PE still leads) -> 0.9554 (CTPA) ")
    ok(round(boards[2]["hyp.heart-failure"], 4) == 0.2881
       and round(boards[1]["hyp.heart-failure"], 4) == 0.12,
       "case6: the stage-2 BNP effect is in the machinery itself — "
       "the workbench's HF posterior more than doubles (0.12 -> "
       "0.2881) on the honestly weighed LR+ 3.75")
    ok(boards[2]["hyp.asthma-exacerbation"] < RULE_OUT
       and boards[1]["hyp.asthma-exacerbation"] >= RULE_OUT,
       "case6: asthma is the first retirement (stage 2, by "
       "renormalisation alone — no finding addresses it)")
    ok(all(boards[3][h] < RULE_OUT and boards[2][h] >= RULE_OUT for h in
           ("hyp.heart-failure", "hyp.pneumonia", "hyp.pneumothorax",
            "hyp.acute-coronary-syndrome", "hyp.copd-exacerbation",
            "hyp.other-unspecified")),
       "case6: every remaining rival is ruled out at stage 3, when "
       "the CTPA weight lands")

    # ---- anchoring: exactly one, result-installed, at stage 3 ---------
    ruled = {}
    for s in (1, 2, 3, 4):
        for h, p in boards[s].items():
            if p < RULE_OUT and h not in ruled:
                ruled[h] = s
    events = []
    for st in attempt["stages"]:
        s = st["stage"]
        for h, lp in st["board"].items():
            if lp >= ANCHOR and h in ruled and ruled[h] <= s:
                events.append((s, h))
    ok(events == [(3, "hyp.heart-failure")],
       f"case6: exactly one anchoring event, recomputed: {events}")
    lb = {st["stage"]: st["board"] for st in attempt["stages"]}
    ok(lb[1]["hyp.heart-failure"] == 0.20
       and lb[2]["hyp.heart-failure"] == 0.42
       and lb[3]["hyp.heart-failure"] == 0.16,
       "case6: the anchor's arc — HF second at stage 1 (0.20), "
       "installed as the lead at stage 2 by the BNP result (0.42), "
       "still held at 0.16 at stage 3 after the CTPA and the "
       "learner's own B-line-negative ultrasound")

    # ---- physiology link: hash + both readouts re-run ------------------
    link = case["physiology_link"]
    c1 = load(os.path.join(CASES, "case.ruq-pain.001.json"))["case"]
    ok(link["trace_hash"] == c1["physiology_link"]["trace_hash"]
       == "0x6369b10e9a71c872",
       "case6: physiology link records the same pinned circulation "
       "trace hash as cases 1 and 3 — the M47 respiratory module did "
       "not move the circulation chain")
    ok(link["baseline_recorded_outputs"]
       == c1["physiology_link"]["baseline_recorded_outputs"],
       "case6: recorded circulation baseline outputs identical to "
       "case 1's link")
    resp = link["respiratory_recorded_outputs"]
    ok(len(resp) == 17,
       "case6: the link records the full 17-value respiratory "
       "resting readout (the resting protocol prints no resp hash; "
       "the state is pinned by its readout, as the link states)")
    import re as _re
    try:
        env = dict(os.environ)
        env["PATH"] = os.path.expanduser("~/.cargo/bin") + ":" + env["PATH"]
        r = subprocess.run(["cargo", "run", "--release", "--quiet", "--",
                            "run", "respiratory"],
                           cwd=os.path.join(ROOT, "physiology"),
                           capture_output=True, text=True, timeout=900,
                           env=env)
        m = _re.search(
            r"resting: PaCO2 ([\d.]+) mmHg  PAO2 ([\d.]+)  PaO2 ([\d.]+)  "
            r"pH ([\d.]+)  SaO2 ([\d.]+)  CaO2 ([\d.]+) mL/dL  "
            r"CvO2 ([\d.]+)  DO2 ([\d.]+) mL/min  O2ER ([\d.]+)  "
            r"VE ([\d.]+) L/min  VA ([\d.]+) L/min  RR ([\d.]+) /min  "
            r"VO2 ([\d.]+)  VCO2 ([\d.]+)  Hb ([\d.]+) g/dL  "
            r"HCO3 ([\d.]+) mEq/L  A-a ([\d.]+) mmHg", r.stdout)
        keys = ["pa_co2_mmhg", "alveolar_po2_mmhg", "pa_o2_mmhg", "ph",
                "sa_o2", "ca_o2_ml_dl", "cv_o2_ml_dl", "do2_ml_min",
                "o2er", "ve_l_min", "va_l_min", "rr_per_min",
                "vo2_ml_min", "vco2_ml_min", "hb_g_dl", "hco3_meq_l",
                "aa_gradient_mmhg"]
        tol = {"ph": 0.0006, "sa_o2": 0.0006, "o2er": 0.0006,
               "ca_o2_ml_dl": 0.0051, "cv_o2_ml_dl": 0.0051,
               "ve_l_min": 0.0051, "va_l_min": 0.0051,
               "hb_g_dl": 0.0051, "hco3_meq_l": 0.0051,
               "do2_ml_min": 0.51, "vo2_ml_min": 0.51,
               "vco2_ml_min": 0.51}
        got = ({k: float(g) for k, g in zip(keys, m.groups())}
               if m else {})
        ok(m is not None and all(
            abs(got[k] - resp[k]) < tol.get(k, 0.051) for k in keys),
           f"case6: engine respiratory resting readout reproduces "
           f"all 17 recorded values ({got.get('pa_o2_mmhg', 'none')})")
    except Exception as e:  # pragma: no cover
        ok(False, f"case6: respiratory engine re-run failed: {e}")
    ok("no thromboembolic state" in link["gap_statement"]
       or "thrombus" in link["gap_statement"],
       "case6: the link's gap statement is explicit — the engine "
       "has no thromboembolic state and the patient's gases are "
       "authored case data, not simulation")

    # ---- imaging link: localisation only, recounted --------------------
    il = case["imaging_link"]
    ok(il["label"]["record_id"] in INVS
       and all(r in INVS for r in il["label"]["record_ids"]),
       "case6: imaging link's pulmonary artery records are Body "
       "Model records (both lateralised instances carried)")
    cw = load(os.path.join(ROOT, "data", "imaging", "s0778",
                           "crosswalk.json"))
    lab48 = next(l for l in cw["labels"] if l["index"] == 48)
    ok(lab48["label"] == "pulmonary_artery"
       and lab48["voxels"] == il["label"]["hu_statistics_from_crosswalk"]["voxels"]
       == 23547
       and sorted(r["id"] for r in lab48["records"])
       == sorted(il["label"]["record_ids"]),
       "case6: crosswalk label 48 is pulmonary_artery, 23,547 "
       "voxels, mapped to exactly the two records the link carries")
    hu = il["label"]["hu_statistics_from_crosswalk"]
    ok(all(lab48["hu"][k] == hu[k]
           for k in ("mean", "median", "p5", "p95", "min", "max")),
       "case6: case HU statistics equal crosswalk values")
    ok(lab48["geometry_lps"]["bbox_lps_mm"] == il["measures"]["bbox_lps_mm"],
       "case6: link bbox equals the crosswalk geometry")
    # recount the label from the shipped web bins
    counts = {}
    bdir = os.path.join(ROOT, "web", "data", "imaging", "s0778")
    for fn in sorted(os.listdir(bdir)):
        if fn.startswith("lbl-"):
            idx = int(fn[4:8])
            with open(os.path.join(bdir, fn), "rb") as fh:
                counts[idx] = fh.read().count(48)
    hit = {i: n for i, n in counts.items() if n}
    ok(min(hit) == il["measures"]["slice_files_0based"][0]
       and max(hit) == il["measures"]["slice_files_0based"][1]
       and len(hit) == il["measures"]["slices_with_label"] == 42
       and sum(hit.values()) == 23547
       and hit[il["measures"]["max_cross_section"]["file_index_0based"]]
       == il["measures"]["max_cross_section"]["voxels"] == 1278,
       "case6: label-48 recount from the shipped bins reproduces "
       "the link (files 302-343, 42 slices, 23,547 voxels, max "
       "file 327 at 1,278)")
    series = load(os.path.join(ROOT, "data", "imaging", "s0778",
                               "series.json"))
    z0 = series["geometry"]["ipp_first_slice_lps_mm"][2]
    ok(abs((z0 + 302 * 1.5) - il["measures"]["z_range_lps_mm"][0]) < 0.01
       and abs((z0 + 343 * 1.5) - il["measures"]["z_range_lps_mm"][1])
       < 0.01,
       "case6: slice z-arithmetic reproduces the link's z range")
    ok(abs(23547 * 3.375 / 1000 - 79.47) < 0.01,
       "case6: volume arithmetic (23,547 x 3.375 mm3 = 79.47 mL)")
    for sid in ("s0778", "s1090"):
        cwx = load(os.path.join(ROOT, "data", "imaging", sid,
                                "crosswalk.json"))
        names = sorted(l["label"] for l in cwx["labels"])
        ok(len(names) == 104, f"case6: {sid} label set recounted at 104")
        ok(not any(any(wd in n for wd in
                       ("embol", "consolid", "pleura", "effusion"))
                   for n in names),
           f"case6: {sid} label set contains NO embolus, "
           "consolidation, pleura or effusion label — the series "
           "cannot show this case's pathology, as the link states")
        ok("pulmonary_artery" in names
           and sum(1 for n in names if n.startswith("lung_")) == 5,
           f"case6: {sid} DOES carry pulmonary_artery and all five "
           "lung lobes — the lungs are in the field; the embolus "
           "is not a label")
    ok("conflated" in il["honesty_block"] and "NOT s0778" in il["honesty_block"],
       "case6: imaging honesty block present (three individuals, "
       "never conflated)")

    # ---- no theatre handoff, stated -------------------------------------
    ok("handoff" not in case["management"],
       "case6: management carries NO handoff key — PE management "
       "here is medical, and no Theatre procedure treats it")
    proc_ids = set()
    for p in glob.glob(os.path.join(ROOT, "theatre", "procedures", "*.json")):
        proc_ids.add(load(p)["procedure"]["id"])
    ok(proc_ids == {"proc.chole.lap", "proc.appy.lap",
                    "proc.carpal-release", "proc.ulnar-decompression",
                    "proc.lap-inguinal-hernia"},
       f"case6: the Theatre still holds exactly its five procedures "
       f"{sorted(proc_ids)} — none is an embolectomy (the inguinal hernia "
       "repair joined at Milestone 49 — set assertion updated in the "
       "Milestone 44 maintenance pattern; the no-handoff fact this "
       "assertion guards is unchanged)")
    ok("no Theatre handoff exists" in case["management"]["theatre_note"],
       "case6: the absence of a handoff is stated in the case, per "
       "the module's discipline, not left silent")

    # ---- ontology discipline --------------------------------------------
    hyps = {h["id"]: h for h in case["hypotheses"]}
    ok(hyps["hyp.pulmonary-embolism"]["mondo"] == "MONDO:0005279"
       and case["ground_truth"]["mondo"] == "MONDO:0005279"
       and case["adjudication"]["mondo"] == "MONDO:0005279",
       "case6: diagnosis coded MONDO:0005279 (pulmonary embolism) "
       "on hypothesis, adjudication and ground truth")
    ok(hyps["hyp.heart-failure"]["mondo"] == "MONDO:0005252"
       and "acute heart failure" in
       hyps["hyp.heart-failure"]["mondo_note"],
       "case6: heart failure coded to the generic MONDO:0005252 — "
       "the OLS search for an acute class returned only non-human "
       "classes, and the note says so rather than fabricating one")
    ok(hyps["hyp.pneumonia"]["mondo"] == "MONDO:0005249"
       and "community-acquired" in hyps["hyp.pneumonia"]["mondo_note"],
       "case6: pneumonia coded to MONDO:0005249 — no "
       "community-acquired class exists in Mondo (numFound 0), "
       "recorded in the note")
    ok(hyps["hyp.pneumothorax"]["mondo"] == "MONDO:0002076"
       and hyps["hyp.acute-coronary-syndrome"]["mondo"] == "MONDO:0005542"
       and hyps["hyp.copd-exacerbation"]["mondo"] == "MONDO:0005002"
       and hyps["hyp.asthma-exacerbation"]["mondo"] == "MONDO:0004979"
       and hyps["hyp.other-unspecified"]["mondo"] is None
       and hyps["hyp.other-unspecified"].get("mondo_note"),
       "case6: pneumothorax / ACS / COPD / asthma / residual Mondo "
       "coding as verified in the C10 Milestone 48 addendum")

    # ---- debrief: classifications + tally --------------------------------
    slug = case["id"].replace(".", "-")
    deb = load(os.path.join(
        CASES, "debriefs", f"debrief.{slug}.model-learner.json"))["debrief"]
    cls = {o["test_id"]: o["classification"] for o in deb["orders"]}
    ok(cls == {"test.ecg": "safety-net",
               "test.troponin": "criteria-completing",
               "test.abg": "criteria-completing",
               "test.bnp": "discriminating",
               "test.d-dimer": "discriminating",
               "test.bloods": "criteria-completing",
               "test.chest-xray": "criteria-completing",
               "test.exam-battery": "criteria-completing",
               "test.ctpa": "discriminating",
               "test.lung-ultrasound": "discriminating"},
       f"case6: order classifications {cls} — the BNP is "
       "discriminating in the WRONG direction (it moves the lead "
       "away from the truth), and the troponin ordered as a "
       "safety-net lands criteria-completing via the ESC block")
    ok(deb["resource_tally"]["total_time_min"] == 215
       and deb["resource_tally"]["total_cost_units"] == 27,
       "case6: resource tally 215 min / 27 units")
    ok(deb["ruled_out_by_workbench"] ==
       {"hyp.asthma-exacerbation": 2, "hyp.heart-failure": 3,
        "hyp.pneumonia": 3, "hyp.pneumothorax": 3,
        "hyp.acute-coronary-syndrome": 3, "hyp.copd-exacerbation": 3,
        "hyp.other-unspecified": 3},
       "case6: rule-out stages as designed (asthma at 2, all other "
       "rivals at 3)")
    commit = attempt["stages"][-1]["commit"]
    ok(commit["diagnosis_hypothesis"]
       == case["adjudication"]["diagnosis_hypothesis"]
       and "no Theatre handoff" in commit["management"],
       "case6: attempt commit matches adjudication and states the "
       "absent Theatre handoff")


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
    if "case.appendicitis.003" in profiles:
        c, ctx, boards = profiles["case.appendicitis.003"]
        profile_case3(c, ctx, boards, attempts["case.appendicitis.003"])
    if "case.carpal-tunnel.004" in profiles:
        c, ctx, boards = profiles["case.carpal-tunnel.004"]
        profile_case4(c, ctx, boards, attempts["case.carpal-tunnel.004"])
    if "case.ulnar-neuropathy.005" in profiles:
        c, ctx, boards = profiles["case.ulnar-neuropathy.005"]
        profile_case5(c, ctx, boards, attempts["case.ulnar-neuropathy.005"])
    if "case.acute-dyspnea.006" in profiles:
        c, ctx, boards = profiles["case.acute-dyspnea.006"]
        profile_case6(c, ctx, boards, attempts["case.acute-dyspnea.006"])

    print(f"\n{'ALL CHECKS PASS' if FAIL == 0 else 'FAILURES PRESENT'}: "
          f"{PASS} passed, {FAIL} failed")
    for n in NOTES:
        print(f"  note: {n}")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
