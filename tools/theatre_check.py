#!/usr/bin/env python3
"""ANATOMICA Milestone 17 checker — independent validation of the theatre.

Recomputes, from the data files alone (never from the Rust code):
  1. procedure census (phases / steps / microsteps / required set)
  2. every structure-register entry: 'record' entries resolve to a
     real record id inside the named Body Model data file; 'absence'
     entries carry a substantive note (and, where named, the file
     documenting the absence / resolution)
  3. every microstep target is registered, every instrument exists,
     every microstep carries >= 1 source that exists in parameters
  4. gate reachability: each Critical View criterion is demonstrated
     by a microstep in a phase at or before the division phase
  5. every decision point offers a bailout choice (design/05)
  6. variant definitions: prevalence stated, structures registered,
     shipped trace present
  7. scoring arithmetic in every emitted debrief JSON, recomputed
     from the debrief's own components; verdict/fail consistency;
     engine loss vs event-integral cross-check agreement
  8. trace-specific expectations (the class III injury in trace-02,
     the 67-microstep required set in trace-04, the bailout in 05)
  9. parameter discipline: cited/calibrated parameters name a source
     that exists; verify-flagged parameters are counted and listed

Usage: python3 tools/theatre_check.py [--debriefs DIR]
Regenerate debriefs with:
  (cd theatre && cargo run --release -- run-all)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEATRE = os.path.join(ROOT, "theatre")

failures = []
checks = 0


def ok(cond, label, detail=""):
    global checks
    checks += 1
    if cond:
        print(f"  PASS {label}")
    else:
        print(f"  FAIL {label} {detail}")
        failures.append(label)


def load(path):
    with open(path) as f:
        return json.load(f)


def collect_ids(node, acc):
    if isinstance(node, dict):
        rid = node.get("id") or node.get("record_id")
        if isinstance(rid, str):
            acc.add(rid)
        for v in node.values():
            collect_ids(v, acc)
    elif isinstance(node, list):
        for v in node:
            collect_ids(v, acc)
    return acc


def main():
    debriefs_dir = os.path.join(THEATRE, "debriefs")
    if "--debriefs" in sys.argv:
        debriefs_dir = sys.argv[sys.argv.index("--debriefs") + 1]

    proc = load(os.path.join(THEATRE, "procedures", "proc.lap-cholecystectomy.json"))["procedure"]
    params = load(os.path.join(THEATRE, "parameters.json"))
    instruments = load(os.path.join(THEATRE, "instruments.json"))
    source_ids = {s["id"] for s in params["sources"]}
    instrument_ids = {i["id"] for i in instruments["instruments"]}

    print("== 1. census ==")
    phases = proc["phases"]
    steps = [s for p in phases for s in p["steps"]]
    micros = [m for s in steps for m in s["microsteps"]]
    required = [m for m in micros if m["required"]]
    print(f"  phases {len(phases)}, steps {len(steps)}, microsteps {len(micros)}, required(standard) {len(required)}")
    ok(len(phases) == 9, "9 phases")
    ok(len({m['id'] for m in micros}) == len(micros), "microstep ids unique")
    ok(len({s['id'] for s in steps}) == len(steps), "step ids unique")

    print("== 2. structure register resolution ==")
    register = {s["id"]: s for s in proc["structures"]}
    file_ids = {}
    for s in proc["structures"]:
        if s["kind"] == "record":
            path = os.path.join(ROOT, s["resolves_to"])
            ok(os.path.exists(path), f"{s['id']}: data file exists", s["resolves_to"])
            if s["resolves_to"] not in file_ids:
                file_ids[s["resolves_to"]] = collect_ids(load(path), set())
            ok(s["id"] in file_ids[s["resolves_to"]],
               f"{s['id']}: record id present in {s['resolves_to']}")
        else:
            ok(len(s["note"]) > 80, f"{s['id']}: absence note is substantive ({len(s['note'])} chars)")
            if s.get("resolves_to"):
                ok(os.path.exists(os.path.join(ROOT, s["resolves_to"])),
                   f"{s['id']}: documented-absence file exists")
    # the two famous absences must be genuine: the ids must NOT exist
    # as records anywhere in the cardiovascular/digestive modules
    cv_ids = set()
    for fn in ["cardiovascular.json", "cv-inventory.json"]:
        cv_ids |= collect_ids(load(os.path.join(ROOT, "data", "cardiovascular", fn)), set())
    dg_ids = set()
    for fn in ["digestive.json", "digestive-inventory.json"]:
        dg_ids |= collect_ids(load(os.path.join(ROOT, "data", "digestive", fn)), set())
    ok(not any("cystic" in i and "artery" in i for i in cv_ids | dg_ids),
       "cystic artery genuinely absent from the Body Model data (absence note is honest)")
    ok(not any(i.endswith("common-bile-duct") or i == "duct.common-bile" for i in dg_ids),
       "common bile duct genuinely absent from the digestive data (absence note is honest)")

    print("== 3. microstep references ==")
    bad_targets = [f"{m['id']}->{t}" for m in micros for t in m.get("targets", []) if t not in register]
    ok(not bad_targets, "every microstep target is registered", "; ".join(bad_targets[:5]))
    bad_inst = [f"{m['id']}->{i}" for m in micros for i in m.get("instruments", []) if i not in instrument_ids]
    ok(not bad_inst, "every microstep instrument exists", "; ".join(bad_inst[:5]))
    bad_src = [m["id"] for m in micros if not m.get("sources")]
    ok(not bad_src, "every microstep carries at least one source", "; ".join(bad_src[:5]))
    bad_src2 = [f"{m['id']}->{s}" for m in micros for s in m.get("sources", []) if s not in source_ids]
    ok(not bad_src2, "every cited source id exists in parameters.json", "; ".join(bad_src2[:5]))
    ok(all(i.get("function") for i in instruments["instruments"]), "every instrument states a function")

    print("== 4. gate reachability ==")
    phase_index = {p["id"]: n for n, p in enumerate(phases)}
    demon = {}
    for p in phases:
        for s in p["steps"]:
            for m in s["microsteps"]:
                if m.get("demonstrates"):
                    demon[m["demonstrates"]] = phase_index[p["id"]]
    div_phase = min(phase_index[pid] for pid in
                    (next(p["id"] for p in phases for s in p["steps"] if s["id"] == sid)
                     for sid in ["step.6.1", "step.6.2"]))
    for g in proc["safety_gates"]:
        if g["kind"] != "safety_gate":
            continue
        for c in g["criteria"]:
            ok(c["id"] in demon, f"criterion {c['id']} is demonstrated by a microstep")
            if c["id"] in demon:
                ok(demon[c["id"]] <= div_phase,
                   f"criterion {c['id']} demonstrable no later than the division phase")

    print("== 5. decision points carry bailouts ==")
    for dp in proc["decision_points"]:
        has = any(any(k in c["id"] for k in ("subtotal", "convert", "abort")) for c in dp["choices"])
        ok(has, f"{dp['id']} offers a bailout choice")

    print("== 6. variants ==")
    for v in proc["variants"]:
        ok(bool(v.get("prevalence")), f"{v['id']}: prevalence stated")
        ok(all(s in register for s in v.get("structure_additions", [])),
           f"{v['id']}: added structures registered")
        ok(os.path.exists(os.path.join(ROOT, v["trace"])), f"{v['id']}: shipped trace exists")

    print("== 7/8. debrief arithmetic, recomputed independently ==")
    err_ids = {e["id"] for e in proc["errors"]}
    names = sorted(fn for fn in os.listdir(debriefs_dir) if fn.endswith(".debrief.json"))
    ok(len(names) == 5, f"five debriefs emitted (found {len(names)})")
    by_trace = {}
    for fn in names:
        d = load(os.path.join(debriefs_dir, fn))
        by_trace[d["trace_id"]] = d
        c = d["checklist"]
        ok(c["completed"] + len(c["missing"]) == c["required"],
           f"{d['trace_id']}: checklist counts reconcile")
        ok(abs(c["pct"] - 100.0 * c["completed"] / c["required"]) < 0.05,
           f"{d['trace_id']}: checklist pct recomputes")
        sg = d["safety_gate"]
        ok(sg["points"] == sg["criteria_before_first_clipdiv"] + (1 if sg["pause_before_first_clip"] else 0),
           f"{d['trace_id']}: safety points recompute")
        pr = d["process"]
        ok(pr["points"] == sum([pr["sign_in"], pr["time_out"], pr["sign_out"],
                                pr["prophylaxis_in_window"], pr["planning_complete"]]),
           f"{d['trace_id']}: process points recompute")
        ph = d["physiology"]
        ok(ph["points"] == ph["time_points"] + ph["nadir_points"] + ph["loss_points"],
           f"{d['trace_id']}: physiology points recompute")
        tol = max(1.0, 0.05 * ph["blood_loss_crosscheck_ml"])
        ok(abs(ph["blood_loss_ml"] - ph["blood_loss_crosscheck_ml"]) <= tol,
           f"{d['trace_id']}: engine loss vs event integral agree ({ph['blood_loss_ml']:.1f} vs {ph['blood_loss_crosscheck_ml']:.1f} mL)")
        if d["management"] is not None:
            mg = d["management"]
            ok(mg["points"] == mg["recognised"] + mg["control"] + mg["escalation"] + mg["plan"],
               f"{d['trace_id']}: management points recompute")
        ok((d["verdict"] == "FAIL") == (d["failed_at_s"] is not None),
           f"{d['trace_id']}: verdict/fail-time consistency")
        if d["verdict"] == "FAIL":
            ok(any(e["id"] in ("err.divide-unidentified", "err.missed-variant") for e in d["errors"]),
               f"{d['trace_id']}: FAIL is carried by a critical-fail error")
        ok(all(e["id"] in err_ids for e in d["errors"]),
           f"{d['trace_id']}: every emitted error id is defined in the procedure")
        ok(d["validity_label"] == "formative-only", f"{d['trace_id']}: formative-only label carried")
        ok(abs(d["engine_conservation_error_ml"]) < 0.01,
           f"{d['trace_id']}: engine volume conservation ({d['engine_conservation_error_ml']:.1e} mL)")

    t2 = by_trace.get("trace-02-divide-before-cvs", {})
    bdi = [c for c in t2.get("complications", []) if c["kind"] == "bile-duct-injury"]
    ok(len(bdi) == 1 and bdi[0]["stewart_way_class"] == "III"
       and bdi[0]["resolved_structure"] == "duct.common-bile",
       "trace-02: the injury is a Stewart-Way class III transection of the common bile duct")
    ok(t2.get("failed_at_s") == 1920.0, "trace-02: fails at the division (t=1920s)")
    ok(t2.get("management", {}).get("points") == 5,
       "trace-02: exemplary management (5/5) does not rescue the verdict")
    t1 = by_trace.get("trace-01-clean", {})
    ok(t1.get("checklist", {}).get("pct") == 100.0 and t1.get("safety_gate", {}).get("points") == 4,
       "trace-01: full checklist and full gate score")
    t4 = by_trace.get("trace-04-variant-double-cystic", {})
    ok(t4.get("checklist", {}).get("required") == 67,
       "trace-04: variant configuration requires 67 microsteps")
    t5 = by_trace.get("trace-05-bailout-subtotal", {})
    ok(t5.get("verdict") == "PASS"
       and any(x["id"] == "dp2" and x["choice"] == "subtotal-fenestrating" for x in t5.get("decisions", [])),
       "trace-05: bailout taken at dp2 and the attempt passes")

    print("== 9. parameter discipline ==")
    verify = []
    for p in params["parameters"]:
        if p["status"] in ("cited", "calibrated"):
            ok(p.get("source") in source_ids, f"parameter {p['key']}: source exists")
        elif p["status"] == "verify":
            verify.append(p["key"])
        else:
            ok(False, f"parameter {p['key']}: status '{p['status']}' is not cited/calibrated/verify")
    print(f"  verify-flagged parameters ({len(verify)}): {', '.join(verify)}")
    ok(proc["review"]["recorded_reviewers"] == [] and "UNMET" in proc["review"]["status"],
       "expert-review gate honestly recorded UNMET (no reviewers fabricated)")

    print(f"\ntheatre_check: {checks} checks, {len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
