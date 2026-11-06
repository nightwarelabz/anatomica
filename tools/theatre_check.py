#!/usr/bin/env python3
"""ANATOMICA theatre checker (Milestones 17 + 28) — independent
validation of the theatre module's two procedures.

Recomputes, from the data files alone (never from the Rust code):
  1. procedure census (phases / steps / microsteps / required set)
  2. every structure-register entry: 'record' entries resolve to a
     real record id inside the named Body Model data file; 'absence'
     entries carry a substantive note (and, where named, the file
     documenting the absence / resolution)
  3. every microstep target is registered, every instrument exists,
     every microstep carries >= 1 source that exists in parameters
  4. gate reachability: each safety-gate criterion is demonstrated
     by a microstep in a phase at or before the phase of the steps
     the gate unlocks (the division phase)
  5. every decision point offers a bailout choice (design/05)
  6. variant definitions: prevalence stated, structures registered,
     shipped trace present
  7. scoring arithmetic in every emitted debrief JSON, recomputed
     from the debrief's own components; verdict/fail consistency;
     engine loss vs event-integral cross-check agreement
  8. trace-specific expectations for both procedures (the Stewart-Way
     class III injury in chole trace-02, the 67-microstep required
     set in trace-04, the bailout in 05; the cecal injury in appy
     trace-08, the configuration required sets in 06/07/09/10)
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


PROCEDURES = [
    ("proc.lap-cholecystectomy.json", 9),
    ("proc.lap-appendectomy.json", 9),
]


def check_procedure(proc, expected_phases, params, instrument_ids, source_ids, debriefs_by_proc):
    pid = proc["id"]
    print(f"\n##### {pid} #####")
    phases = proc["phases"]
    steps = [s for p in phases for s in p["steps"]]
    micros = [m for s in steps for m in s["microsteps"]]
    required = [m for m in micros if m["required"]]

    print("== 1. census ==")
    print(f"  phases {len(phases)}, steps {len(steps)}, microsteps {len(micros)}, required(standard) {len(required)}")
    ok(len(phases) == expected_phases, f"{pid}: {expected_phases} phases")
    ok(len({m['id'] for m in micros}) == len(micros), f"{pid}: microstep ids unique")
    ok(len({s['id'] for s in steps}) == len(steps), f"{pid}: step ids unique")

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

    print("== 3. microstep references ==")
    bad_targets = [f"{m['id']}->{t}" for m in micros for t in m.get("targets", []) if t not in register]
    ok(not bad_targets, f"{pid}: every microstep target is registered", "; ".join(bad_targets[:5]))
    bad_inst = [f"{m['id']}->{i}" for m in micros for i in m.get("instruments", []) if i not in instrument_ids]
    ok(not bad_inst, f"{pid}: every microstep instrument exists", "; ".join(bad_inst[:5]))
    bad_src = [m["id"] for m in micros if not m.get("sources")]
    ok(not bad_src, f"{pid}: every microstep carries at least one source", "; ".join(bad_src[:5]))
    bad_src2 = [f"{m['id']}->{s}" for m in micros for s in m.get("sources", []) if s not in source_ids]
    ok(not bad_src2, f"{pid}: every cited source id exists in parameters.json", "; ".join(bad_src2[:5]))

    print("== 4. gate reachability ==")
    phase_index = {p["id"]: n for n, p in enumerate(phases)}
    step_phase = {s["id"]: phase_index[p["id"]] for p in phases for s in p["steps"]}
    demon = {}
    for p in phases:
        for s in p["steps"]:
            for m in s["microsteps"]:
                if m.get("demonstrates"):
                    demon[m["demonstrates"]] = phase_index[p["id"]]
    for g in proc["safety_gates"]:
        if g["kind"] != "safety_gate":
            continue
        unlock_phases = [step_phase[sid] for sid in g.get("unlocks", []) if sid in step_phase]
        div_phase = min(unlock_phases) if unlock_phases else None
        for c in g["criteria"]:
            ok(c["id"] in demon, f"{pid}: criterion {c['id']} is demonstrated by a microstep")
            if c["id"] in demon and div_phase is not None:
                ok(demon[c["id"]] <= div_phase,
                   f"{pid}: criterion {c['id']} demonstrable no later than the division phase")

    print("== 5. decision points carry bailouts ==")
    for dp in proc["decision_points"]:
        has = any(any(k in c["id"] for k in ("subtotal", "convert", "abort", "return-theatre")) for c in dp["choices"])
        ok(has, f"{pid}: {dp['id']} offers a bailout choice")

    print("== 6. variants ==")
    for v in proc["variants"]:
        ok(bool(v.get("prevalence")), f"{pid}: {v['id']}: prevalence stated")
        ok(all(s in register for s in v.get("structure_additions", [])),
           f"{pid}: {v['id']}: added structures registered")
        ok(os.path.exists(os.path.join(ROOT, v["trace"])), f"{pid}: {v['id']}: shipped trace exists")

    print("== 7. debrief arithmetic, recomputed independently ==")
    err_severity = {e["id"]: e["severity"] for e in proc["errors"]}
    names = debriefs_by_proc.get(pid, [])
    for fn, d in names:
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
            ok(any(err_severity.get(e["id"]) == "critical-fail" for e in d["errors"]),
               f"{d['trace_id']}: FAIL is carried by a critical-fail error")
        ok(all(e["id"] in err_severity for e in d["errors"]),
           f"{d['trace_id']}: every emitted error id is defined in the procedure")
        ok(d["validity_label"] == "formative-only", f"{d['trace_id']}: formative-only label carried")
        ok(abs(d["engine_conservation_error_ml"]) < 0.01,
           f"{d['trace_id']}: engine volume conservation ({d['engine_conservation_error_ml']:.1e} mL)")

    ok(proc["review"]["recorded_reviewers"] == [] and "UNMET" in proc["review"]["status"],
       f"{pid}: expert-review gate honestly recorded UNMET (no reviewers fabricated)")
    return {d["trace_id"]: d for _, d in names}


def main():
    debriefs_dir = os.path.join(THEATRE, "debriefs")
    if "--debriefs" in sys.argv:
        debriefs_dir = sys.argv[sys.argv.index("--debriefs") + 1]

    params = load(os.path.join(THEATRE, "parameters.json"))
    instruments = load(os.path.join(THEATRE, "instruments.json"))
    source_ids = {s["id"] for s in params["sources"]}
    instrument_ids = {i["id"] for i in instruments["instruments"]}
    ok(all(i.get("function") for i in instruments["instruments"]), "every instrument states a function")

    # Group the emitted debriefs by the procedure they ran against.
    debriefs_by_proc = {}
    all_names = sorted(fn for fn in os.listdir(debriefs_dir) if fn.endswith(".debrief.json"))
    for fn in all_names:
        d = load(os.path.join(debriefs_dir, fn))
        debriefs_by_proc.setdefault(d["procedure_id"], []).append((fn, d))
    ok(len(all_names) == 10, f"ten debriefs emitted, five per procedure (found {len(all_names)})")

    by_trace = {}
    for fname, expected_phases in PROCEDURES:
        proc = load(os.path.join(THEATRE, "procedures", fname))["procedure"]
        by_trace.update(check_procedure(proc, expected_phases, params, instrument_ids, source_ids, debriefs_by_proc))

    print("\n== 8. trace-specific expectations ==")
    # -- cholecystectomy (Milestone 17, unchanged) --
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

    # -- appendicectomy (Milestone 28) --
    # The register's honest asymmetry: the appendiceal artery exists
    # as an inventory record but has no clinical record.
    cv_clinical = collect_ids(load(os.path.join(ROOT, "data", "cardiovascular", "cardiovascular.json")), set())
    ok("artery.appendicular-artery" in cv_ids and "artery.appendicular-artery" not in cv_clinical,
       "appendiceal artery is inventory-only (register note is honest)")
    ok("canal.appendix" in dg_ids and "canal.cecum" in dg_ids and "dig.cecum-appendix" in dg_ids,
       "appendix/cecum records genuinely present in the digestive data")

    t6 = by_trace.get("trace-06-appy-clean", {})
    ok(t6.get("checklist", {}).get("pct") == 100.0 and t6.get("safety_gate", {}).get("points") == 4,
       "trace-06: full checklist and full gate score")
    ok(t6.get("checklist", {}).get("required") == 37,
       "trace-06: closure decision brings the required set to 37")
    ok(t6.get("errors") == [], "trace-06: the clean attempt carries no errors")
    t7 = by_trace.get("trace-07-appy-variant-retrocecal", {})
    ok(t7.get("checklist", {}).get("required") == 39 and t7.get("verdict") == "PASS",
       "trace-07: retrocecal configuration requires 39 and the mobilized attempt passes")
    t8 = by_trace.get("trace-08-appy-divide-unidentified", {})
    ci = [c for c in t8.get("complications", []) if c["kind"] == "cecal-injury"]
    ok(len(ci) == 1 and ci[0]["resolved_structure"] == "canal.cecum",
       "trace-08: the injury is a cecal injury, resolved onto canal.cecum")
    ok(t8.get("failed_at_s") == 1740.0, "trace-08: fails at the division (t=1740s)")
    ok(t8.get("management", {}).get("points") == 5,
       "trace-08: exemplary management (5/5) does not rescue the verdict")
    t9 = by_trace.get("trace-09-appy-perforated", {})
    ok(t9.get("checklist", {}).get("required") == 39 and t9.get("checklist", {}).get("pct") == 100.0,
       "trace-09: perforated configuration requires 39 (suction + antibiotic course) at 100%")
    ok(t9.get("errors") == [], "trace-09: the guideline-concordant perforated attempt carries no errors")
    t10 = by_trace.get("trace-10-appy-variant-pelvic", {})
    ok(t10.get("checklist", {}).get("required") == 38 and t10.get("verdict") == "PASS",
       "trace-10: pelvic configuration requires 38 and passes")

    print("\n== 9. parameter discipline ==")
    verify = []
    for p in params["parameters"]:
        if p["status"] in ("cited", "calibrated"):
            ok(p.get("source") in source_ids, f"parameter {p['key']}: source exists")
        elif p["status"] == "verify":
            verify.append(p["key"])
        else:
            ok(False, f"parameter {p['key']}: status '{p['status']}' is not cited/calibrated/verify")
    print(f"  verify-flagged parameters ({len(verify)}): {', '.join(verify)}")

    print(f"\ntheatre_check: {checks} checks, {len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
