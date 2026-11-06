#!/usr/bin/env python3
"""ANATOMICA Case Workbench runner (Milestone 20 machinery, generalised
at Milestone 22 to every case in cases/).

For each case file (cases/case.*.json) and its model-learner attempt,
computes — from the case file + cases/parameters.json alone:

  1. the workbench board: declared priors updated stage by stage with
     the cited likelihood ratios of the findings revealed at each
     stage (naive-product rule, declared in parameters.json), with
     rule-outs by the declared threshold;
  2. the guideline criteria evaluations, stage by stage, from the
     case's DECLARED criteria blocks (no criteria logic lives in this
     file): "grouped" blocks (TG18-style groups + status rules),
     "k_of_n" blocks (revised Atlanta-style), and "classification"
     blocks (Strasberg-Bismuth-style decision rules over named
     inputs), and "score" blocks (Milestone 29: published clinical
     scores — flat or tiered weighted items summed into declared
     bands, with unmeasured items recorded not-assessed), plus the
     TG18 severity grade where a case declares one;
  3. the attempt scores, per design/07 and the rules declared in
     cases/parameters.json: per-stage Brier scores (learner board and
     workbench board) against the adjudicated diagnosis, ranks and
     probabilities of the true diagnosis, anchoring events,
     per-order evidence classification (discriminating /
     criteria-completing / safety-net / non-contributory), and the
     resource tally. NO composite score is computed — design/07
     defines components, not weights;
  4. a PEARLS-structured debrief JSON (design/07 step 6), whose
     prose is carried in the attempt file (debrief_text), not here.

Usage: python3 tools/case_run.py [--case CASE_ID] [--out DIR]
Without --case, every case with an attempt is run.
Debriefs are written to cases/debriefs/.
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "cases")


def load(path):
    with open(path) as f:
        return json.load(f)


PARAMS = load(os.path.join(CASES, "parameters.json"))
CONST = {p["key"]: p["value"] for p in PARAMS["parameters"]}
RULE_OUT = CONST["rule_out_threshold"]
ANCHOR = CONST["anchoring_threshold"]
DISC_DELTA = CONST["discriminating_delta"]


class CaseRun:
    def __init__(self, case, attempt):
        self.case = case
        self.attempt = attempt
        self.findings = {f["id"]: f for f in case["findings"]}
        self.labs = {l["id"]: l for l in case["labs"]}
        self.tests = {t["id"]: t for t in case["available_tests"]}
        self.measurements = {m["id"]: m for m in case.get("measurements", [])}
        self.hyps = [h["id"] for h in case["hypotheses"]]
        self.priors = {h["id"]: h["prior"]["value"] for h in case["hypotheses"]}
        self.truth = case["adjudication"]["diagnosis_hypothesis"]
        self.stages = [s["stage"] for s in case["presentation_stages"]]
        self.blocks = self._blocks()

    # ---------- criteria blocks (all declared in the case file) ----
    def _blocks(self):
        blocks = []
        ev = self.case["adjudication"].get("tg18_evaluation")
        if ev:  # Milestone 20 form: the TG18 cholecystitis block
            blocks.append({
                "id": "tg18_cholecystitis", "kind": "grouped",
                "groups": ev["groups"], "status_rules": ev["status_rules"],
                "default_status": ev["default_status"]})
        blocks.extend(self.case.get("criteria_blocks", []))
        return blocks

    # ---------- atoms ----------------------------------------------
    def _ref_stage(self, atom):
        if "finding_id" in atom:
            return self.findings[atom["finding_id"]]["stage"]
        if "lab_id" in atom:
            return self.labs[atom["lab_id"]]["stage"]
        if "measurement_id" in atom:
            return self.measurements[atom["measurement_id"]]["stage"]
        return None

    def _atom_excluded(self, atom, excl):
        for key in ("finding_id", "lab_id", "measurement_id"):
            if key in atom and atom[key] in excl:
                return True
        if "measurement_id" in atom:
            src = self.measurements[atom["measurement_id"]].get("finding_id")
            if src in excl:
                return True
        return False

    def atom(self, atom, stage, excl=frozenset(), three=False):
        """Evaluate one evidence atom.
        three=False: True / False / "not-assessed" (unrevealed = False).
        three=True: "satisfied" / "unsatisfied" / "unknown"."""
        if atom.get("assessable") is False:
            return "not-assessed" if not three else "unknown"
        if "constant" in atom:
            v = bool(atom["constant"])
            return v if not three else ("satisfied" if v else "unsatisfied")
        if self._atom_excluded(atom, excl):
            return "unknown" if three else False
        if self._ref_stage(atom) is not None and self._ref_stage(atom) > stage:
            return "unknown" if three else False
        if "finding_id" in atom:
            f = self.findings[atom["finding_id"]]
            v = f.get("presence", "present") == atom["is"]
        elif "lab_id" in atom:
            lab = self.labs[atom["lab_id"]]
            v = lab["value"]
            t = atom["test"]
            if t == "value_gt":
                v = v > atom["threshold"]
            elif t == "value_lt":
                v = v < atom["threshold"]
            elif t == "value_gte":
                v = v >= atom["threshold"]
            elif t == "value_lte":
                v = v <= atom["threshold"]
            elif t == "above_reference":
                v = v > lab["reference_range"]["high"]
            elif t == "value_gt_uln_multiple":
                v = v > atom["factor"] * lab["reference_range"]["high"]
            elif t == "value_gte_uln_multiple":
                v = v >= atom["factor"] * lab["reference_range"]["high"]
            else:
                raise ValueError(atom)
        elif "measurement_id" in atom:
            v = self.measurements[atom["measurement_id"]]["value"]
            t = atom["test"]
            if t == "value_gt":
                v = v > atom["threshold"]
            elif t == "value_lt":
                v = v < atom["threshold"]
            elif t == "value_gte":
                v = v >= atom["threshold"]
            elif t == "value_lte":
                v = v <= atom["threshold"]
            else:
                raise ValueError(atom)
        elif "case_field" in atom:
            v = self.case["patient"][atom["case_field"]]
            if atom["test"] == "value_gt":
                v = v > atom["threshold"]
            elif atom["test"] == "value_lt":
                v = v < atom["threshold"]
            else:
                raise ValueError(atom)
        else:
            raise ValueError(atom)
        return v if not three else ("satisfied" if v else "unsatisfied")

    def item_bool(self, item, stage):
        states = [self.atom(a, stage) for a in item["evidence"]]
        if any(s is True for s in states):
            return True
        if any(s == "not-assessed" for s in states):
            return "not-assessed"
        return False

    def item_three(self, item, stage, excl=frozenset()):
        states = [self.atom(a, stage, excl, three=True) for a in item["evidence"]]
        if "satisfied" in states:
            return "satisfied"
        if all(s == "unsatisfied" for s in states):
            return "unsatisfied"
        return "unknown"

    # ---------- block evaluation ------------------------------------
    def eval_block(self, block, stage):
        kind = block["kind"]
        if kind == "grouped":
            groups = {}
            for g in block["groups"]:
                groups[g["group"]] = any(
                    self.item_bool(it, stage) is True for it in g["items"])
            status = block["default_status"]
            for rule in block["status_rules"]:
                req = rule.get("require", {})
                anyof = rule.get("require_any", {})
                if all(groups[g] == want for g, want in req.items()) and (
                        not anyof or any(groups[g] == want for g, want in anyof.items())):
                    status = rule["status"]
                    break
            return {"groups": groups, "status": status}
        if kind == "k_of_n":
            items = {it["id"]: self.item_bool(it, stage) is True
                     for it in block["items"]}
            met = sum(1 for v in items.values() if v)
            return {"items": items, "items_met": met,
                    "diagnosable": met >= block["k"]}
        if kind == "classification":
            inputs = {}
            for inp in block["inputs"]:
                states = [self.atom(a, stage, three=True) for a in inp["atoms"]]
                if "satisfied" in states:
                    inputs[inp["id"]] = True
                elif all(s == "unsatisfied" for s in states):
                    inputs[inp["id"]] = False
                else:
                    inputs[inp["id"]] = "unknown"
            for i, rule in enumerate(block["rules"]):
                vals = [(inputs[k], want) for k, want in rule["when"].items()]
                if all(v == want for v, want in vals):
                    return {"status": "classified", "result": rule["result"],
                            "rule_index": i, "inputs": inputs}
            return {"status": block.get("pending_label", "not yet classifiable"),
                    "result": None, "rule_index": None, "inputs": inputs}
        if kind == "score":
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
        raise ValueError(kind)

    def score_item(self, item, stage, excl=frozenset()):
        """Three-valued state + awarded points for one score item
        (Milestone 29). Flat item: `points` for its evidence. Tiered
        item: tiers declared highest-first; the first tier whose
        evidence is satisfied wins its points. An item is unsatisfied
        only if every tier is unsatisfied; otherwise unknown."""
        tiers = item["tiers"] if "tiers" in item else [
            {"points": item["points"], "evidence": item["evidence"]}]
        states = []
        for t in tiers:
            vals = [self.atom(a, stage, excl, three=True)
                    for a in t["evidence"]]
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

    def criteria_items(self, stage, excl=frozenset()):
        """Three-valued states of every criteria input, for order
        classification: grouped/k_of_n items and classification inputs."""
        out = {}
        for block in self.blocks:
            if block["kind"] in ("grouped", "k_of_n"):
                groups = block["groups"] if block["kind"] == "grouped" else [
                    {"items": block["items"]}]
                for g in groups:
                    for it in g["items"]:
                        out[f"{block['id']}.{it['id']}"] = self.item_three(
                            it, stage, excl)
            elif block["kind"] == "classification":
                for inp in block["inputs"]:
                    item = {"evidence": inp["atoms"]}
                    out[f"{block['id']}.{inp['id']}"] = self.item_three(
                        item, stage, excl)
            elif block["kind"] == "score":
                for it in block["items"]:
                    r = self.score_item(it, stage, excl)
                    out[f"{block['id']}.{it['id']}"] = (
                        f"satisfied:{r['points']}"
                        if r["state"] == "satisfied" else r["state"])
        return out

    def severity(self, stage):
        sev = self.case["adjudication"]["severity_grade"]
        iii = {it["id"]: self.item_bool(it, stage) for it in sev["items_grade_iii"]}
        ii = {it["id"]: self.item_bool(it, stage) for it in sev["items_grade_ii"]}
        if any(v is True for v in iii.values()):
            grade = "III"
        elif any(v is True for v in ii.values()):
            grade = "II"
        else:
            grade = "I"
        return grade, iii, ii

    # ---------- the board -------------------------------------------
    def board(self, stage, exclude_findings=frozenset()):
        w = dict(self.priors)
        for fid, f in self.findings.items():
            if f["stage"] > stage or fid in exclude_findings:
                continue
            lr = f.get("lr")
            if not lr:
                continue
            h = lr["for_hypothesis"]
            if "lr_plus" in lr:
                w[h] *= lr["lr_plus"]
            if "lr_minus" in lr:
                w[h] *= lr["lr_minus"]
        total = sum(w.values())
        return {h: v / total for h, v in w.items()}

    def brier(self, probs):
        return sum((p - (1.0 if h == self.truth else 0.0)) ** 2
                   for h, p in probs.items())

    @staticmethod
    def rank_of(probs, hyp):
        ordered = sorted(probs.items(), key=lambda kv: -kv[1])
        return [h for h, _ in ordered].index(hyp) + 1

    # ---------- order classification ---------------------------------
    def classify_order(self, test, placed_stage):
        reveal = placed_stage + 1
        yielded = set(test["yields"])
        lr_findings = {fid for fid in yielded
                       if fid in self.findings and self.findings[fid].get("lr")}
        full = self.board(reveal)
        without = self.board(reveal, exclude_findings=lr_findings)
        lead_full = max(full, key=full.get)
        lead_wo = max(without, key=without.get)
        if lead_full != lead_wo or abs(full[lead_full] - without[lead_full]) >= DISC_DELTA:
            return "discriminating", (
                f"leading hypothesis posterior moves "
                f"{without[lead_full]:.4f} -> {full[lead_full]:.4f}")
        for h in self.hyps:
            if without[h] >= RULE_OUT and full[h] < RULE_OUT:
                return "discriminating", (
                    f"{h} crosses the rule-out line "
                    f"({without[h]:.4f} -> {full[h]:.4f})")
        excl = {y for y in yielded
                if (y in self.findings and self.findings[y]["stage"] == reveal)
                or (y in self.labs and self.labs[y]["stage"] == reveal)
                or (y in self.measurements
                    and self.measurements[y]["stage"] == reveal)}
        if self.criteria_items(reveal, excl) != self.criteria_items(reveal):
            changed = [k for k in self.criteria_items(reveal)
                       if self.criteria_items(reveal, excl)[k]
                       != self.criteria_items(reveal)[k]]
            return "criteria-completing", (
                "settles guideline item(s): " + ", ".join(sorted(changed)))
        if test.get("safety_net_for"):
            return "safety-net", (
                f"excludes must-not-miss {test['safety_net_for']} (unquantified pair)")
        return "non-contributory", "no posterior, criteria, or safety-net effect"

    # ---------- shaping for the debrief -------------------------------
    def _shape(self, block, result):
        """Debrief shape per block; the Milestone 20 legacy shapes are
        kept for the blocks case 1 shipped with."""
        if block["kind"] == "grouped":
            if block["id"] in ("tg18_cholecystitis", "tg18_cholangitis"):
                return [result["groups"], result["status"]]
            return result
        if block["kind"] == "k_of_n":
            if block["id"] == "atlanta":
                out = dict(result["items"])
                out["items_met"] = result["items_met"]
                out["diagnosable"] = result["diagnosable"]
                return out
            return result
        return result

    # ---------- main --------------------------------------------------
    def run(self, out_dir):
        case, attempt = self.case, self.attempt
        boards = {s: self.board(s) for s in self.stages}
        ruled_out = {}
        for s in self.stages:
            for h in self.hyps:
                if h not in ruled_out and boards[s][h] < RULE_OUT:
                    ruled_out[h] = s

        attempt_stages = {a["stage"]: a for a in attempt["stages"]}
        per_stage = []
        anchoring = []
        for s in self.stages:
            lb = attempt_stages[s]["board"]
            assert abs(sum(lb.values()) - 1.0) < 1e-9, \
                f"stage {s} board sums to {sum(lb.values())}"
            for h in self.hyps:
                if ruled_out.get(h, 99) <= s and lb[h] >= ANCHOR:
                    anchoring.append({
                        "stage": s, "hypothesis": h,
                        "learner_probability": lb[h],
                        "workbench_probability": boards[s][h],
                        "ruled_out_at_stage": ruled_out[h]})
            criteria = {}
            row = {"stage": s}
            for block in self.blocks:
                res = self.eval_block(block, s)
                criteria[block["id"]] = res
                row[block["id"]] = self._shape(block, res)
            row.update({
                "workbench_board": {h: round(boards[s][h], 4) for h in self.hyps},
                "learner_board": lb,
                "workbench_top": max(boards[s], key=boards[s].get),
                "learner_top": max(lb, key=lb.get),
                "workbench_rank_of_truth": self.rank_of(boards[s], self.truth),
                "learner_rank_of_truth": self.rank_of(lb, self.truth),
                "workbench_probability_on_truth": round(boards[s][self.truth], 4),
                "learner_probability_on_truth": lb[self.truth],
                "workbench_brier": round(self.brier(boards[s]), 4),
                "learner_brier": round(self.brier(lb), 4),
                "criteria": criteria,
            })
            per_stage.append(row)

        orders = []
        tally_time = tally_cost = 0
        for a in attempt["stages"]:
            for tid in a["orders"]:
                t = self.tests[tid]
                cls, why = self.classify_order(t, a["stage"])
                orders.append({"test_id": tid, "placed_at_stage": a["stage"],
                               "results_stage": a["stage"] + 1,
                               "classification": cls, "basis": why,
                               "time_min": t["time_min"]["value"],
                               "cost_units": t["cost_units"]["value"]})
                tally_time += t["time_min"]["value"]
                tally_cost += t["cost_units"]["value"]

        final = self.stages[-1]
        criteria_final = {b["id"]: self.eval_block(b, final) for b in self.blocks}
        adj = {"hypothesis": self.truth,
               "mondo": case["adjudication"].get("mondo"),
               "criteria_final": criteria_final}
        if "classification" in case["adjudication"]:
            adj["classification"] = case["adjudication"]["classification"]
        if "tg18_cholecystitis" in criteria_final:
            adj["tg18_status_final"] = criteria_final["tg18_cholecystitis"]["status"]
        if "severity_grade" in case["adjudication"]:
            grade, iii, ii = self.severity(final)
            adj["tg18_severity_grade"] = grade
            adj["severity_items_grade_iii"] = iii
            adj["severity_items_grade_ii"] = ii

        text = attempt.get("debrief_text", {})
        debrief = {"debrief": {
            "case_id": case["id"],
            "attempt_id": attempt["id"],
            "generated_by": "tools/case_run.py (Milestone 20 machinery, "
                            "generalised at Milestone 22)",
            "structure": "PEARLS (design/07 step 6; Eppich & Cheng 2015, "
                         "as cited by Milestone 17's T10)",
            "adjudicated_diagnosis": adj,
            "per_stage": per_stage,
            "ruled_out_by_workbench": ruled_out,
            "anchoring_events": anchoring,
            "orders": orders,
            "resource_tally": {
                "total_time_min": tally_time,
                "total_cost_units": tally_cost,
                "status": "verify — case-author accounting placeholders "
                          "(design/07 requires tests to carry cost and time; "
                          "no prices were consulted)"},
            "scoring_components": {
                "note": "Components only. Design/07 defines Brier-style "
                        "calibration scoring, anchoring, and evidence quality, "
                        "and no weights; no composite is computed.",
                "learner_brier_by_stage": {str(r["stage"]): r["learner_brier"]
                                           for r in per_stage},
                "workbench_brier_by_stage": {str(r["stage"]): r["workbench_brier"]
                                             for r in per_stage},
                "learner_probability_on_truth_by_stage": {
                    str(r["stage"]): r["learner_probability_on_truth"]
                    for r in per_stage},
                "anchoring_event_count": len(anchoring),
                "order_class_counts": {
                    c: sum(1 for o in orders if o["classification"] == c)
                    for c in ("discriminating", "criteria-completing",
                              "safety-net", "non-contributory")},
            },
            "pearls": {
                "reactions": text.get("reactions", ""),
                "description": text.get("description", ""),
                "analysis": text.get("analysis", ""),
                "summary": text.get("summary", ""),
            },
            "validity": case["validity"],
            "review": case["review"],
        }}

        slug = case["id"].replace(".", "-")
        out_path = os.path.join(out_dir, "debriefs", f"debrief.{slug}.model-learner.json")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(debrief, f, indent=1, sort_keys=True)

        print(f"\nANATOMICA Case Workbench — {case['id']} / {attempt['id']}")
        print("priors: " + ", ".join(f"{h}={self.priors[h]:.2f}" for h in self.hyps))
        for r in per_stage:
            print(f"\nstage {r['stage']}: workbench top={r['workbench_top']} "
                  f"(truth rank {r['workbench_rank_of_truth']}, "
                  f"p={r['workbench_probability_on_truth']}), learner "
                  f"top={r['learner_top']} (truth rank "
                  f"{r['learner_rank_of_truth']}, p={r['learner_probability_on_truth']})")
            print(f"  Brier: learner {r['learner_brier']:.4f} | "
                  f"workbench {r['workbench_brier']:.4f}")
            print("  workbench board: " + ", ".join(
                f"{h}={r['workbench_board'][h]:.4f}" for h in self.hyps))
            for bid, res in r["criteria"].items():
                if "status" in res and "groups" in res:
                    print(f"  {bid}: {res['groups']} -> {res['status']}")
                elif "items_met" in res:
                    print(f"  {bid}: {res['items']} -> {res['items_met']} met, "
                          f"diagnosable={res['diagnosable']}")
                elif "result" in res:
                    print(f"  {bid}: {res['status']}"
                          + (f" -> {res['result']}" if res["result"] else ""))
                elif "total" in res:
                    print(f"  {bid}: {res['total']}/{res['max_total']} -> "
                          f"{res['status']}"
                          + (f" (partial; not assessed: "
                             f"{', '.join(res['not_assessed'])})"
                             if res["partial"] else ""))
        print(f"\nruled out by workbench (stage): {ruled_out}")
        if "severity_grade" in case["adjudication"]:
            grade, iii, ii = self.severity(final)
            print(f"severity grade (final): {grade}  (III: {iii}; II: {ii})")
        print(f"anchoring events: {len(anchoring)}")
        for a in anchoring:
            print(f"  stage {a['stage']}: learner holds {a['hypothesis']} at "
                  f"{a['learner_probability']} (workbench "
                  f"{a['workbench_probability']:.4f}, ruled out at stage "
                  f"{a['ruled_out_at_stage']})")
        print("orders:")
        for o in orders:
            print(f"  {o['test_id']} (placed stage {o['placed_at_stage']}, "
                  f"results stage {o['results_stage']}): "
                  f"{o['classification']} — {o['basis']}")
        print(f"resource tally: {tally_time} min, {tally_cost} cost units "
              f"(verify-flagged accounting)")
        print(f"debrief written: {out_path}")
        return out_path


def main():
    out_dir = CASES
    only = None
    if "--out" in sys.argv:
        out_dir = sys.argv[sys.argv.index("--out") + 1]
    if "--case" in sys.argv:
        only = sys.argv[sys.argv.index("--case") + 1]
    attempts = {}
    for p in glob.glob(os.path.join(CASES, "attempts", "*.json")):
        a = load(p)["attempt"]
        attempts.setdefault(a["case_id"], []).append(a)
    ran = 0
    for p in sorted(glob.glob(os.path.join(CASES, "case.*.json"))):
        case = load(p)["case"]
        if only and case["id"] != only:
            continue
        for attempt in attempts.get(case["id"], []):
            CaseRun(case, attempt).run(out_dir)
            ran += 1
    print(f"\n{ran} case attempt(s) run")


if __name__ == "__main__":
    main()
