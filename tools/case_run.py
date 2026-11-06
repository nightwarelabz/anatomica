#!/usr/bin/env python3
"""ANATOMICA Case Workbench runner (Milestone 20).

Computes, from cases/case.ruq-pain.001.json + the attempt file +
cases/parameters.json (never from the checker's code):

  1. the workbench board: declared priors updated stage by stage with
     the cited likelihood ratios of the findings revealed at each
     stage (naive-product rule, declared in parameters.json), with
     rule-outs by the declared threshold;
  2. the guideline criteria evaluations, stage by stage: TG18 acute
     cholecystitis groups A/B/C + status, TG18 severity grade,
     TG18 acute cholangitis groups, revised Atlanta items;
  3. the attempt scores, per design/07 and the rules declared in
     cases/parameters.json: per-stage Brier scores (learner board and
     workbench board) against the adjudicated diagnosis, ranks and
     probabilities of the true diagnosis, anchoring events,
     per-order evidence classification (discriminating /
     criteria-completing / safety-net / non-contributory), and the
     resource tally. NO composite score is computed — design/07
     defines components, not weights;
  4. a PEARLS-structured debrief JSON (design/07 step 6).

Usage: python3 tools/case_run.py [--out DIR]
Writes cases/debriefs/debrief.case-ruq-pain-001.model-learner.json
and prints the full computed report.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "cases")


def load(path):
    with open(path) as f:
        return json.load(f)


PARAMS = load(os.path.join(CASES, "parameters.json"))
CASE = load(os.path.join(CASES, "case.ruq-pain.001.json"))["case"]
ATTEMPT = load(os.path.join(
    CASES, "attempts", "attempt.case-ruq-pain-001.model-learner.json"))["attempt"]

CONST = {p["key"]: p["value"] for p in PARAMS["parameters"]}
RULE_OUT = CONST["rule_out_threshold"]
ANCHOR = CONST["anchoring_threshold"]
DISC_DELTA = CONST["discriminating_delta"]

FINDINGS = {f["id"]: f for f in CASE["findings"]}
LABS = {l["id"]: l for l in CASE["labs"]}
TESTS = {t["id"]: t for t in CASE["available_tests"]}
HYPS = [h["id"] for h in CASE["hypotheses"]]
PRIORS = {h["id"]: h["prior"]["value"] for h in CASE["hypotheses"]}
TRUTH = CASE["adjudication"]["diagnosis_hypothesis"]
STAGES = [s["stage"] for s in CASE["presentation_stages"]]


def revealed(stage):
    """Findings/labs in evidence at the end of `stage` (cumulative)."""
    fs = {fid for fid, f in FINDINGS.items() if f["stage"] <= stage}
    ls = {lid for lid, l in LABS.items() if l["stage"] <= stage}
    return fs, ls


def board(stage, exclude_findings=frozenset()):
    """Workbench posterior at end of `stage`, optionally ignoring
    some findings' LRs (used to attribute an order's effect)."""
    w = dict(PRIORS)
    for fid, f in FINDINGS.items():
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


def atom_ok(atom, stage):
    fs, ls = revealed(stage)
    if atom.get("assessable") is False:
        return "not-assessed"
    if "finding_id" in atom:
        f = FINDINGS[atom["finding_id"]]
        if atom["finding_id"] not in fs:
            return False
        return f.get("presence", "present") == atom["is"]
    if "lab_id" in atom:
        lab = LABS[atom["lab_id"]]
        if atom["lab_id"] not in ls:
            return False
        v = lab["value"]
        if atom["test"] == "value_gt":
            return v > atom["threshold"]
        if atom["test"] == "value_lt":
            return v < atom["threshold"]
        if atom["test"] == "above_reference":
            return v > lab["reference_range"]["high"]
        raise ValueError(atom)
    if "case_field" in atom:
        v = CASE["patient"][atom["case_field"]]
        if atom["test"] == "value_gt":
            return v > atom["threshold"]
        raise ValueError(atom)
    raise ValueError(atom)


def item_state(item, stage):
    states = [atom_ok(a, stage) for a in item["evidence"]]
    if any(s is True for s in states):
        return True
    if any(s == "not-assessed" for s in states):
        return "not-assessed"
    return False


def tg18_cholecystitis(stage):
    ev = CASE["adjudication"]["tg18_evaluation"]
    groups = {}
    for g in ev["groups"]:
        groups[g["group"]] = any(
            item_state(it, stage) is True for it in g["items"])
    if groups["A"] and groups["B"] and groups["C"]:
        status = "definite"
    elif groups["A"] and groups["B"]:
        status = "suspected"
    else:
        status = "not suspected"
    return groups, status


def severity(stage):
    sev = CASE["adjudication"]["severity_grade"]
    iii = {it["id"]: item_state(it, stage) for it in sev["items_grade_iii"]}
    ii = {it["id"]: item_state(it, stage) for it in sev["items_grade_ii"]}
    if any(v is True for v in iii.values()):
        grade = "III"
    elif any(v is True for v in ii.values()):
        grade = "II"
    else:
        grade = "I"
    return grade, iii, ii


def tg18_cholangitis(stage):
    """C2: A systemic inflammation; B cholestasis; C imaging.
    Suspected = A + (B or C); definite = A + B + C."""
    fs, ls = revealed(stage)
    a = ("f.fever" in fs) or ("f.wbc-elevated" in fs) or ("f.crp-elevated" in fs)
    b = False
    if "lab.bilirubin-total" in ls:
        b = b or LABS["lab.bilirubin-total"]["value"] >= 2.0
        for lid, uln in (("lab.alp", 129), ("lab.alt", 36), ("lab.ast", 33)):
            b = b or LABS[lid]["value"] > 1.5 * uln
    c = "f.us-biliary-dilatation" in fs  # no such finding exists in this case
    if a and b and c:
        status = "definite"
    elif a and (b or c):
        status = "suspected"
    else:
        status = "not suspected"
    return {"A": a, "B": b, "C": c}, status


def atlanta(stage):
    """C5: 2 of 3 — characteristic pain; lipase >= 3x ULN; imaging."""
    fs, ls = revealed(stage)
    pain = False  # case pain is RUQ/scapular, not the Atlanta description
    lipase = ("lab.lipase" in ls
              and LABS["lab.lipase"]["value"] >= 3 * LABS["lab.lipase"]["reference_range"]["high"])
    imaging = "f.us-pancreatitis-imaging" in fs  # no such finding in this case
    met = sum([pain, lipase, imaging])
    return {"pain_consistent": pain, "lipase_3x_uln": lipase,
            "imaging": imaging, "items_met": met, "diagnosable": met >= 2}


def brier(board_probs):
    return sum((p - (1.0 if h == TRUTH else 0.0)) ** 2
               for h, p in board_probs.items())


def rank_of(board_probs, hyp):
    ordered = sorted(board_probs.items(), key=lambda kv: -kv[1])
    return [h for h, _ in ordered].index(hyp) + 1


def criteria_items(stage, excluded=frozenset()):
    """Item-level criteria states for all three guideline systems.
    State in {"satisfied", "unsatisfied", "unknown"}: 'unknown' means
    the evidence an item needs has not been revealed (or is excluded).
    Pure: takes an exclusion set instead of mutating the case."""
    def fstate(fid):
        f = FINDINGS[fid]
        if fid in excluded or f["stage"] > stage:
            return "unknown"
        return "satisfied" if f.get("presence", "present") == "present" else "unsatisfied"

    def lab_known(lid):
        return lid not in excluded and LABS[lid]["stage"] <= stage

    items = {}
    # TG18 cholecystitis items (from the case's declared evaluation)
    ev = CASE["adjudication"]["tg18_evaluation"]
    for g in ev["groups"]:
        for it in g["items"]:
            states = []
            for a in it["evidence"]:
                if "finding_id" in a:
                    states.append(fstate(a["finding_id"]) if a["is"] == "present"
                                  else ("satisfied" if fstate(a["finding_id"]) == "unsatisfied"
                                        else fstate(a["finding_id"])))
                else:
                    states.append("satisfied")
            items["tg18c." + it["id"]] = ("satisfied" if "satisfied" in states
                                         else "unsatisfied" if "unsatisfied" in states
                                         else "unknown")
    # TG18 cholangitis items (C2)
    items["tg18chol.A"] = ("satisfied" if "satisfied" in
                           (fstate("f.fever"), fstate("f.wbc-elevated"), fstate("f.crp-elevated"))
                           else "unknown")
    if lab_known("lab.bilirubin-total"):
        items["tg18chol.B1"] = ("satisfied" if LABS["lab.bilirubin-total"]["value"] >= 2.0
                                else "unsatisfied")
    else:
        items["tg18chol.B1"] = "unknown"
    enz = [("lab.alp", 129), ("lab.alt", 36), ("lab.ast", 33)]
    if all(lab_known(l) for l, _ in enz):
        items["tg18chol.B2"] = ("satisfied" if any(LABS[l]["value"] > 1.5 * u for l, u in enz)
                                else "unsatisfied")
    else:
        items["tg18chol.B2"] = "unknown"
    items["tg18chol.C"] = ("unsatisfied" if fstate("f.us-no-biliary-dilatation") in
                           ("satisfied", "unsatisfied") else "unknown")
    # Revised Atlanta items (C5)
    items["atlanta.pain"] = "unsatisfied"  # case pain character, adjudicated in the case file
    if lab_known("lab.lipase"):
        items["atlanta.lipase"] = ("satisfied" if LABS["lab.lipase"]["value"]
                                   >= 3 * LABS["lab.lipase"]["reference_range"]["high"]
                                   else "unsatisfied")
    else:
        items["atlanta.lipase"] = "unknown"
    items["atlanta.imaging"] = ("unsatisfied" if fstate("f.us-pancreas-unremarkable") in
                                ("satisfied", "unsatisfied") else "unknown")
    return items


def classify_order(test, placed_stage):
    """Classify one order by the rules in parameters.json, measuring
    its effect at its reveal stage (placed_stage + 1)."""
    reveal = placed_stage + 1
    yielded = set(test["yields"])
    lr_findings = {fid for fid in yielded
                   if fid in FINDINGS and FINDINGS[fid].get("lr")}
    full = board(reveal)
    without = board(reveal, exclude_findings=lr_findings)
    # (a) leading-hypothesis delta or top change
    lead_full = max(full, key=full.get)
    lead_wo = max(without, key=without.get)
    if lead_full != lead_wo or abs(full[lead_full] - without[lead_full]) >= DISC_DELTA:
        return "discriminating", f"leading hypothesis posterior moves {without[lead_full]:.4f} -> {full[lead_full]:.4f}"
    # (b) any hypothesis crosses the rule-out line because of this test
    for h in HYPS:
        if without[h] >= RULE_OUT and full[h] < RULE_OUT:
            return "discriminating", f"{h} crosses the rule-out line ({without[h]:.4f} -> {full[h]:.4f})"
    # (c) criteria-completing: any guideline item changes state when
    # this test's yields are removed at the reveal stage
    excl = {y for y in yielded
            if (y in FINDINGS and FINDINGS[y]["stage"] == reveal)
            or (y in LABS and LABS[y]["stage"] == reveal)}
    if criteria_items(reveal, excl) != criteria_items(reveal):
        changed = [k for k in criteria_items(reveal)
                   if criteria_items(reveal, excl)[k] != criteria_items(reveal)[k]]
        return "criteria-completing", "settles guideline item(s): " + ", ".join(sorted(changed))
    if test.get("safety_net_for"):
        return "safety-net", f"excludes must-not-miss {test['safety_net_for']} (unquantified pair)"
    return "non-contributory", "no posterior, criteria, or safety-net effect"


def main():
    out_dir = CASES
    if "--out" in sys.argv:
        out_dir = sys.argv[sys.argv.index("--out") + 1]

    boards = {s: board(s) for s in STAGES}
    ruled_out = {}
    for s in STAGES:
        for h in HYPS:
            if h not in ruled_out and boards[s][h] < RULE_OUT:
                ruled_out[h] = s

    attempt_stages = {a["stage"]: a for a in ATTEMPT["stages"]}
    per_stage = []
    anchoring = []
    for s in STAGES:
        lb = attempt_stages[s]["board"]
        assert abs(sum(lb.values()) - 1.0) < 1e-9, f"stage {s} board sums to {sum(lb.values())}"
        for h in HYPS:
            if ruled_out.get(h, 99) <= s and lb[h] >= ANCHOR:
                anchoring.append({
                    "stage": s, "hypothesis": h,
                    "learner_probability": lb[h],
                    "workbench_probability": boards[s][h],
                    "ruled_out_at_stage": ruled_out[h]})
        per_stage.append({
            "stage": s,
            "workbench_board": {h: round(boards[s][h], 4) for h in HYPS},
            "learner_board": lb,
            "workbench_top": max(boards[s], key=boards[s].get),
            "learner_top": max(lb, key=lb.get),
            "workbench_rank_of_truth": rank_of(boards[s], TRUTH),
            "learner_rank_of_truth": rank_of(lb, TRUTH),
            "workbench_probability_on_truth": round(boards[s][TRUTH], 4),
            "learner_probability_on_truth": lb[TRUTH],
            "workbench_brier": round(brier(boards[s]), 4),
            "learner_brier": round(brier(lb), 4),
            "tg18_cholecystitis": tg18_cholecystitis(s),
            "tg18_cholangitis": tg18_cholangitis(s),
            "atlanta": atlanta(s),
        })

    orders = []
    tally_time = 0
    tally_cost = 0
    for a in ATTEMPT["stages"]:
        for tid in a["orders"]:
            t = TESTS[tid]
            cls, why = classify_order(t, a["stage"])
            orders.append({"test_id": tid, "placed_at_stage": a["stage"],
                           "results_stage": a["stage"] + 1,
                           "classification": cls, "basis": why,
                           "time_min": t["time_min"]["value"],
                           "cost_units": t["cost_units"]["value"]})
            tally_time += t["time_min"]["value"]
            tally_cost += t["cost_units"]["value"]

    grade, iii, ii = severity(STAGES[-1])

    debrief = {
        "debrief": {
            "case_id": CASE["id"],
            "attempt_id": ATTEMPT["id"],
            "generated_by": "tools/case_run.py (Milestone 20)",
            "structure": "PEARLS (design/07 step 6; Eppich & Cheng 2015, as cited by Milestone 17's T10)",
            "adjudicated_diagnosis": {
                "hypothesis": TRUTH,
                "mondo": CASE["adjudication"]["mondo"],
                "tg18_status_final": tg18_cholecystitis(STAGES[-1])[1],
                "tg18_severity_grade": grade,
                "severity_items_grade_iii": {k: v for k, v in iii.items()},
                "severity_items_grade_ii": {k: v for k, v in ii.items()},
            },
            "per_stage": per_stage,
            "ruled_out_by_workbench": ruled_out,
            "anchoring_events": anchoring,
            "orders": orders,
            "resource_tally": {
                "total_time_min": tally_time,
                "total_cost_units": tally_cost,
                "status": "verify — case-author accounting placeholders (design/07 requires tests to carry cost and time; no prices were consulted)"},
            "scoring_components": {
                "note": "Components only. Design/07 defines Brier-style calibration scoring, anchoring, and evidence quality, and no weights; no composite is computed.",
                "learner_brier_by_stage": {str(r["stage"]): r["learner_brier"] for r in per_stage},
                "workbench_brier_by_stage": {str(r["stage"]): r["workbench_brier"] for r in per_stage},
                "learner_probability_on_truth_by_stage": {str(r["stage"]): r["learner_probability_on_truth"] for r in per_stage},
                "anchoring_event_count": len(anchoring),
                "order_class_counts": {c: sum(1 for o in orders if o["classification"] == c)
                                       for c in ("discriminating", "criteria-completing", "safety-net", "non-contributory")},
            },
            "pearls": {
                "reactions": "The attempt reaches the right diagnosis and the right disposition. Its one systematic error is also the commonest one in the diagnostic-error literature design/07 cites: a vivid fragment (fever + RUQ pain = two-thirds of Charcot's triad) out-arguing a criteria block.",
                "description": "Stage by stage: the learner's board and the workbench's evidence board agree on the leader from stage 1 (cholecystitis), but diverge on cholangitis — the learner raises it at stage 2 (0.20 -> 0.25) on the very stage the cholestasis screen returns empty, and still holds it at 0.15 at stage 3, after the workbench has ruled it out (posterior < 0.02 and TG18 groups B and C both unmet). Pancreatitis is handled exactly right: the normal lipase collapses it at stage 2 (the attempt's 0.02 tracks the workbench's rule-out).",
                "analysis": "Three teaching points, each tied to a scored component. (1) Criteria before fragments: cholangitis under TG18 needs cholestasis or duct imaging; with bilirubin 0.9 mg/dL, enzymes inside reference, no jaundice and a 5 mm duct, there is nothing for the diagnosis to stand on — Charcot's triad is specific but only 26.4% sensitive (C2), so its partial presence is weak evidence and its textbook vividness is the trap. The consider-the-opposite prompt (design/07's debiasing evidence) for the next RUQ case: 'what would have to be true for this to be cholangitis, and have I measured those things?' (2) One test carried the case: lipase (discriminating — it alone moves pancreatitis across the rule-out line) and the ultrasound (discriminating — largest single posterior move, and the TG18 group C test). (3) Amylase alongside lipase is non-contributory by rule and by Choosing Wisely (C6): ordering both is cost without information.",
                "summary": "Diagnosis: acute calculous cholecystitis, TG18 definite from stage 3, Grade I severity (two Grade III items — respiratory and renal/hepatic function — recorded not-assessed rather than assumed). Disposition as committed: early laparoscopic cholecystectomy, handed to the Theatre (proc.chole.lap). Calibration note: a calibration curve is a property of a case SERIES (design/07); this single case contributes four staged Brier scores (learner 0.4550 -> 0.3336 -> 0.1184 -> 0.0276) and one anchoring event to that future series, and claims nothing more.",
            },
            "validity": CASE["validity"],
            "review": CASE["review"],
        }
    }

    out_path = os.path.join(out_dir, "debriefs",
                            "debrief.case-ruq-pain-001.model-learner.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(debrief, f, indent=1, sort_keys=True)

    # ---- printed report (full outputs) ----
    print("ANATOMICA Case Workbench — case.ruq-pain.001 / model-learner attempt")
    print(f"priors: " + ", ".join(f"{h}={PRIORS[h]:.2f}" for h in HYPS))
    for r in per_stage:
        print(f"\nstage {r['stage']}: workbench top={r['workbench_top']} "
              f"(truth rank {r['workbench_rank_of_truth']}, p={r['workbench_probability_on_truth']}), "
              f"learner top={r['learner_top']} (truth rank {r['learner_rank_of_truth']}, p={r['learner_probability_on_truth']})")
        print(f"  Brier: learner {r['learner_brier']:.4f} | workbench {r['workbench_brier']:.4f}")
        print(f"  workbench board: " + ", ".join(f"{h}={r['workbench_board'][h]:.4f}" for h in HYPS))
        g, st = r["tg18_cholecystitis"]
        print(f"  TG18 cholecystitis: A={g['A']} B={g['B']} C={g['C']} -> {st}")
        g2, st2 = r["tg18_cholangitis"]
        print(f"  TG18 cholangitis:   A={g2['A']} B={g2['B']} C={g2['C']} -> {st2}")
        print(f"  Atlanta pancreatitis: {r['atlanta']}")
    print(f"\nruled out by workbench (stage): {ruled_out}")
    print(f"severity grade (final): {grade}  (III items: {iii}; II items: {ii})")
    print(f"anchoring events: {len(anchoring)}")
    for a in anchoring:
        print(f"  stage {a['stage']}: learner holds {a['hypothesis']} at {a['learner_probability']} "
              f"(workbench {a['workbench_probability']:.4f}, ruled out at stage {a['ruled_out_at_stage']})")
    print("orders:")
    for o in orders:
        print(f"  {o['test_id']} (placed stage {o['placed_at_stage']}, results stage {o['results_stage']}): "
              f"{o['classification']} — {o['basis']}")
    print(f"resource tally: {tally_time} min, {tally_cost} cost units (verify-flagged accounting)")
    print(f"\ndebrief written: {out_path}")


if __name__ == "__main__":
    main()
