#!/usr/bin/env python3
"""ANATOMICA theatre checker (Milestones 17 + 28 + 42 + 44 + 49 + 56 + 62) —
independent validation of the theatre module's seven procedures.

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
  8. trace-specific expectations for the seven procedures (the Stewart-Way
     class III injury in chole trace-02, the 67-microstep required
     set in trace-04, the bailout in 05; the cecal injury in appy
     trace-08, the configuration required sets in 06/07/09/10; the
     median nerve injury in carpal trace-12, the variant required
     sets in 13/14, the incomplete release in 15; the ulnar injuries
     and configuration sets in 16-20; the vascular injury in hernia
     trace-22, the variant required sets in 23/24, the unconfirmed
     peritoneal closure in 25; the recurrent laryngeal nerve injury
     in thyroid trace-27, the variant and scenario required sets in
     28/29, the computed hypocalcemia in 30, and the absence
     discipline the thyroid gate resolutions rely on; the
     perforation in endoscopy trace-32, the scored misclassification
     and monotherapy rebleedings in 33/34, the Dieulafoy variant
     sets in 35/36, the computed aspiration in 37, and the absence
     discipline the endoscopy gate resolutions rely on)
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
    ("proc.carpal-release.json", 9),
    ("proc.ulnar-decompression.json", 9),
    ("proc.lap-inguinal-hernia.json", 9),
    ("proc.thyroidectomy.total.json", 9),
    ("proc.upper-gi-endoscopy.json", 9),
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
    # First demonstration wins: a criterion demonstrated on both
    # sides of a bilateral procedure (Milestone 56: the thyroidectomy
    # accounts are made per side, right in phase.3 and left in
    # phase.5) is reachable from its FIRST demonstration; recording
    # the last would read the left side's phase as the criterion's
    # phase and fail a gate whose first gated division is phase.4.
    # For the five earlier procedures each criterion is demonstrated
    # exactly once, so first-wins changes nothing there.
    demon = {}
    for p in phases:
        for s in p["steps"]:
            for m in s["microsteps"]:
                if m.get("demonstrates") and m["demonstrates"] not in demon:
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
    ok(len(all_names) == 37, f"thirty-seven debriefs emitted across seven procedures (found {len(all_names)})")

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

    # -- carpal tunnel release (Milestone 42) --
    # The register's absences, probed against the Body Model data:
    # the ligament divided, the branch the gate protects, the arch,
    # the persistent artery and Guyon's canal have no records.
    import glob as _glob
    all_data_ids = set()
    for path in _glob.glob(os.path.join(ROOT, "data", "*", "*.json")):
        all_data_ids |= collect_ids(load(path), set())
    ok(not any("transverse-carpal" in i or "retinaculum" in i for i in all_data_ids),
       "transverse carpal ligament genuinely absent from the Body Model data (absence note is honest)")
    ok(not any("recurrent" in i and "branch" in i for i in all_data_ids),
       "recurrent branch of the median nerve genuinely absent (the M35/M39/M41 honesty claim)")
    ok(not any("palmar-cutaneous" in i for i in all_data_ids),
       "palmar cutaneous branch genuinely absent from the Body Model data")
    ok(not any("palmar-arch" in i or "persistent-median" in i for i in all_data_ids),
       "superficial palmar arch and persistent median artery genuinely absent")
    ok(not any("guyon" in i or "kaplan" in i for i in all_data_ids),
       "Guyon's canal and Kaplan's line carry no records (landmark/absence register is honest)")
    ok("major.median" in all_data_ids and "major.ulnar" in all_data_ids,
       "median and ulnar nerve clinical records genuinely present (M39)")

    t11 = by_trace.get("trace-11-carpal-clean", {})
    ok(t11.get("checklist", {}).get("pct") == 100.0 and t11.get("safety_gate", {}).get("points") == 4,
       "trace-11: full checklist and full gate score")
    ok(t11.get("process", {}).get("points") == 4,
       "trace-11: process 4/5 — no prophylaxis exists for this operation (T26, T28), the ceiling is by design")
    ok(t11.get("errors") == [], "trace-11: the clean attempt carries no errors")
    t12 = by_trace.get("trace-12-carpal-divide-before-id", {})
    ni = [c for c in t12.get("complications", []) if c["kind"] == "median-nerve-injury"]
    ok(len(ni) == 1 and ni[0]["resolved_structure"] == "major.median",
       "trace-12: the injury is a median nerve injury, resolved onto major.median")
    ok(t12.get("failed_at_s") == 1020.0, "trace-12: fails at the division (t=1020s)")
    ok(t12.get("management", {}).get("points") == 5,
       "trace-12: exemplary management (5/5) does not rescue the verdict")
    ok(len(t12.get("complications", [])) == 1,
       "trace-12: the failed attempt declares the injury only (no incomplete-release noise)")
    t13 = by_trace.get("trace-13-carpal-variant-transligamentous", {})
    ok(t13.get("checklist", {}).get("required") == 30 and t13.get("checklist", {}).get("pct") == 100.0
       and t13.get("verdict") == "PASS",
       "trace-13: transligamentous configuration requires 30 at 100% and passes")
    t14 = by_trace.get("trace-14-carpal-variant-persistent-median-artery", {})
    ok(t14.get("checklist", {}).get("required") == 30 and t14.get("verdict") == "PASS",
       "trace-14: persistent-median-artery configuration requires 30 and passes")
    t15 = by_trace.get("trace-15-carpal-incomplete-release", {})
    inc = [c for c in t15.get("complications", []) if c["kind"] == "incomplete-release"]
    ok(len(inc) == 1 and inc[0]["resolved_structure"] == "ligament.transverse-carpal",
       "trace-15: the unconfirmed release computes persistent symptoms on the ligament")
    ok(t15.get("checklist", {}).get("missing") == ["m6.2"]
       and any(e["id"] == "err.incomplete-release" for e in t15.get("errors", [])),
       "trace-15: the only omission is the completeness confirmation, and it is scored")
    ok(t15.get("verdict") == "PASS" and t15.get("management", {}).get("points") == 5,
       "trace-15: a postoperative consequence, managed at dp4 — not a failed attempt")

    # -- ulnar nerve decompression (Milestone 44) --
    # The register's absences, probed against the Body Model data
    # (all_data_ids was collected for the carpal block above): the
    # divided fascial structures have no records; the two nerves
    # the gate protects, the flexor carpi ulnaris and the humerus
    # genuinely do.
    ok(not any("osborne" in i or "struthers" in i for i in all_data_ids),
       "Osborne's ligament and the arcade of Struthers genuinely absent from the Body Model data (absence notes are honest)")
    ok(not any("aponeurosis" in i for i in all_data_ids),
       "no aponeurosis record exists in the Body Model data (the FCU and flexor-pronator absence notes are honest)")
    ok(not any("intermuscular" in i for i in all_data_ids)
       and sorted(i for i in all_data_ids if "septum" in i)
           == ["nose.nasal-septum", "repro.left-septum-of-testis", "repro.right-septum-of-testis"],
       "no medial intermuscular septum record exists — the only septum records are the nasal septum and the testis septa")
    ok("nerve.medial-cutaneous-nerve-of-forearm" in all_data_ids,
       "the medial antebrachial cutaneous nerve genuinely present as an M33 inventory record (the gate's crit2 protects a real record)")
    ok("muscle.flexor-carpi-ulnaris" in all_data_ids and "humerus_right" in all_data_ids,
       "flexor carpi ulnaris and the right humerus genuinely present (register records resolve)")

    t16 = by_trace.get("trace-16-ulnar-clean", {})
    ok(t16.get("checklist", {}).get("pct") == 100.0 and t16.get("safety_gate", {}).get("points") == 4,
       "trace-16: full checklist and full gate score")
    ok(t16.get("process", {}).get("points") == 4,
       "trace-16: process 4/5 — no prophylaxis exists for this operation (T33), the ceiling is by design")
    ok(t16.get("errors") == [], "trace-16: the clean attempt carries no errors")
    t17 = by_trace.get("trace-17-ulnar-divide-before-id", {})
    ni = [c for c in t17.get("complications", []) if c["kind"] == "ulnar-nerve-injury"]
    ok(len(ni) == 1 and ni[0]["resolved_structure"] == "major.ulnar",
       "trace-17: the injury is an ulnar nerve injury, resolved onto major.ulnar")
    ok(t17.get("failed_at_s") == 1140.0, "trace-17: fails at the division (t=1140s)")
    ok(t17.get("management", {}).get("points") == 5,
       "trace-17: exemplary management (5/5) does not rescue the verdict")
    ok(len(t17.get("complications", [])) == 1,
       "trace-17: the failed attempt declares the injury only (no scoring-time noise)")
    t18 = by_trace.get("trace-18-ulnar-variant-subluxating", {})
    ok(t18.get("checklist", {}).get("required") == 33 and t18.get("checklist", {}).get("pct") == 100.0
       and t18.get("verdict") == "PASS",
       "trace-18: transposition configuration requires 33 (dp5 drops m6.2, inserts m6.3-m6.6) at 100% and passes")
    ok(t18.get("complications") == [],
       "trace-18: a transposed unstable nerve computes no instability consequence")
    t19 = by_trace.get("trace-19-ulnar-subluxation-unaddressed", {})
    inst = [c for c in t19.get("complications", []) if c["kind"] == "nerve-instability"]
    ok(len(inst) == 1 and inst[0]["resolved_structure"] == "major.ulnar",
       "trace-19: the unaddressed instability computes onto major.ulnar")
    ok(any(e["id"] == "err.subluxation-unaddressed" for e in t19.get("errors", []))
       and t19.get("verdict") == "PASS" and t19.get("management", {}).get("points") == 5,
       "trace-19: scored as the configuration error, a postoperative consequence managed at dp4 — not a failed attempt")
    t20 = by_trace.get("trace-20-ulnar-incomplete-release", {})
    inc = [c for c in t20.get("complications", []) if c["kind"] == "incomplete-release"]
    ok(len(inc) == 1 and inc[0]["resolved_structure"] == "ligament.cubital-tunnel-retinaculum",
       "trace-20: the unconfirmed release computes persistent symptoms on the retinaculum")
    ok(t20.get("checklist", {}).get("missing") == ["m5.4"]
       and any(e["id"] == "err.incomplete-release" for e in t20.get("errors", [])),
       "trace-20: the only omission is the completeness confirmation, and it is scored")
    ok(t20.get("verdict") == "PASS" and t20.get("management", {}).get("points") == 5,
       "trace-20: a postoperative consequence, managed at dp4 — not a failed attempt")

    # -- inguinal hernia repair (Milestone 49) --
    # The register's absences, probed against the Body Model data
    # (all_data_ids was collected for the carpal block above): the
    # two triangles, the orifice, Cooper's ligament, the sac, the
    # transversalis fascia, the inguinal canal and the corona
    # mortis have no records; the vessels, nerves, cord and duct
    # the gate protects genuinely do.
    ok(not any("triangle" in i for i in all_data_ids),
       "no triangle record exists in the Body Model data (the doom/pain region absence notes are honest)")
    ok(not any("transversalis" in i or "myopectineal" in i or "pectineal" in i
               or "cooper" in i or "hernia" in i for i in all_data_ids),
       "transversalis fascia, myopectineal orifice, Cooper's ligament and hernia sac genuinely absent")
    ok("canal.inguinal" not in all_data_ids,
       "the inguinal canal genuinely absent from the Body Model data (absence note is honest)")
    ok(not any(i.startswith("artery.") and "obturator" in i for i in all_data_ids)
       and not any("corona" in i and "mortis" in i for i in all_data_ids),
       "no obturator artery and no corona mortis record exists (the corona absence is doubly honest)")
    ok("repro.right-deferent-duct" in all_data_ids
       and "artery.right-external-iliac-artery" in all_data_ids
       and "nerve.genitofemoral" in all_data_ids
       and "major.lateral-femoral-cutaneous" in all_data_ids,
       "deferent duct, external iliac artery and the pain-territory nerves genuinely present (register records resolve)")

    t21 = by_trace.get("trace-21-hernia-clean", {})
    ok(t21.get("checklist", {}).get("pct") == 100.0 and t21.get("safety_gate", {}).get("points") == 4,
       "trace-21: full checklist and full gate score")
    ok(t21.get("process", {}).get("points") == 4,
       "trace-21: process 4/5 — no prophylaxis exists for this operation (T36, T37), the ceiling is by design")
    ok(t21.get("errors") == [], "trace-21: the clean attempt carries no errors")
    t22 = by_trace.get("trace-22-hernia-fixate-before-account", {})
    vi = [c for c in t22.get("complications", []) if c["kind"] == "vascular-injury"]
    ok(len(vi) == 1 and vi[0]["resolved_structure"] == "artery.right-external-iliac-artery",
       "trace-22: the injury is a vascular injury, resolved onto the external iliac artery")
    ok(t22.get("failed_at_s") == 1200.0, "trace-22: fails at the fixation (t=1200s)")
    ok(t22.get("management", {}).get("points") == 5,
       "trace-22: exemplary management (5/5) does not rescue the verdict")
    hem = [c for c in t22.get("complications", []) if c["kind"] == "hemorrhage"]
    ok(len(hem) == 1 and abs(hem[0].get("loss_ml", 0) - 1500.0) < 5.0,
       "trace-22: the haemorrhage is 300 s at the 5.0 mL/s placeholder rate (1500 mL)")
    t23 = by_trace.get("trace-23-hernia-variant-corona-mortis", {})
    ok(t23.get("checklist", {}).get("required") == 34 and t23.get("checklist", {}).get("pct") == 100.0
       and t23.get("verdict") == "PASS",
       "trace-23: corona configuration requires 34 (survey protection added) at 100% and passes")
    t24 = by_trace.get("trace-24-hernia-variant-sliding", {})
    ok(t24.get("checklist", {}).get("required") == 34 and t24.get("checklist", {}).get("pct") == 100.0
       and t24.get("verdict") == "PASS",
       "trace-24: sliding configuration requires 34 (sliding survey added) at 100% and passes")
    t25 = by_trace.get("trace-25-hernia-incomplete-closure", {})
    ad = [c for c in t25.get("complications", []) if c["kind"] == "bowel-adhesion"]
    ok(len(ad) == 1 and ad[0]["resolved_structure"] == "peritoneum.peritoneum",
       "trace-25: the unconfirmed closure computes bowel adhesion on the peritoneum")
    ok(t25.get("checklist", {}).get("missing") == ["m7.2"]
       and any(e["id"] == "err.incomplete-peritoneal-closure" for e in t25.get("errors", [])),
       "trace-25: the only omission is the closure confirmation, and it is scored")
    ok(t25.get("verdict") == "PASS" and t25.get("management", {}).get("points") == 5,
       "trace-25: a postoperative consequence, managed at dp6 — not a failed attempt")

    # -- total thyroidectomy (Milestone 56) --
    # The register's absences, probed against the Body Model data:
    # neither the recurrent laryngeal nerve nor the external branch
    # of the superior laryngeal nerve has a record anywhere in the
    # inventory (the M39 major-nerve tranche covers the vagus trunk,
    # not its laryngeal branches), and neither do the superior
    # thyroid artery, the ligament of Berry or the middle thyroid
    # vein — the gate's injuries resolve onto documented absences,
    # never onto invented records. The gland, its lobes, the
    # parathyroids, the inferior thyroid arteries and the vagus
    # nerves the gate protects genuinely do have records.
    ok(not any("recurrent-laryngeal" in i for i in all_data_ids),
       "no recurrent laryngeal nerve record exists in the Body Model data (the absence notes are honest)")
    ok(not any("external-laryngeal" in i or "superior-laryngeal" in i for i in all_data_ids),
       "no external branch / superior laryngeal nerve record exists in the Body Model data")
    ok(not any("superior-thyroid" in i for i in all_data_ids),
       "no superior thyroid artery record exists in the Body Model data")
    ok(not any("berry" in i or "middle-thyroid" in i for i in all_data_ids),
       "no ligament of Berry and no middle thyroid vein record exists in the Body Model data")
    ok("gland.thyroid-gland" in all_data_ids
       and "gland.parathyroid-glands" in all_data_ids
       and "endo.right-lobe-of-thyroid-gland" in all_data_ids
       and "endo.left-inferior-parathyroid-gland" in all_data_ids
       and "artery.right-inferior-thyroid-artery" in all_data_ids
       and "artery.left-inferior-thyroid-artery" in all_data_ids
       and "nerve.right-vagus-nerve" in all_data_ids
       and "major.cn-10-vagus" in all_data_ids,
       "thyroid, parathyroids, inferior thyroid arteries and vagus nerves genuinely present (register records resolve)")

    t26 = by_trace.get("trace-26-thyroid-clean", {})
    ok(t26.get("checklist", {}).get("pct") == 100.0 and t26.get("checklist", {}).get("required") == 43
       and t26.get("safety_gate", {}).get("points") == 4,
       "trace-26: full checklist (43 required) and full gate score")
    ok(t26.get("process", {}).get("points") == 4,
       "trace-26: process 4/5 — postoperative antibiotics are not indicated for this operation (T44), the ceiling is by design")
    ok(t26.get("errors") == [] and t26.get("complications") == [],
       "trace-26: the clean attempt carries no errors and computes no complications")
    t27 = by_trace.get("trace-27-thyroid-divide-before-id", {})
    ri = [c for c in t27.get("complications", []) if c["kind"] == "recurrent-laryngeal-nerve-injury"]
    ok(len(ri) == 1 and ri[0]["resolved_structure"] == "nerve.right-recurrent-laryngeal-nerve",
       "trace-27: the division resolves onto the unaccounted right recurrent laryngeal nerve (a documented absence)")
    ok(t27.get("failed_at_s") == 1380.0, "trace-27: fails at the inferior pedicle division (t=1380s)")
    ok(t27.get("management", {}).get("points") == 5 and len(t27.get("complications", [])) == 1,
       "trace-27: exemplary management (5/5) does not rescue the verdict, and the failed attempt declares the injury only")
    t28 = by_trace.get("trace-28-thyroid-variant-branching", {})
    ok(t28.get("checklist", {}).get("required") == 44 and t28.get("checklist", {}).get("pct") == 100.0
       and t28.get("verdict") == "PASS" and t28.get("errors") == [],
       "trace-28: branching configuration requires 44 (branch survey added) at 100% and passes clean")
    t29 = by_trace.get("trace-29-thyroid-parathyroid-devascularized", {})
    ok(t29.get("checklist", {}).get("required") == 44 and t29.get("checklist", {}).get("pct") == 100.0
       and t29.get("verdict") == "PASS" and t29.get("errors") == [],
       "trace-29: devascularised configuration requires 44 (autotransplant inserted) at 100% and passes clean")
    ok(not any(c["kind"] == "hypocalcemia" for c in t29.get("complications", [])),
       "trace-29: an autotransplanted devascularised gland computes no hypocalcemia")
    t30 = by_trace.get("trace-30-thyroid-parathyroid-unaccounted", {})
    hc = [c for c in t30.get("complications", []) if c["kind"] == "hypocalcemia"]
    ok(len(hc) == 1 and hc[0]["resolved_structure"] == "gland.parathyroid-glands",
       "trace-30: the unaccounted side computes hypocalcemia on the parathyroid glands at scoring")
    ok(t30.get("checklist", {}).get("missing") == ["m3.2"]
       and any(e["id"] == "err.parathyroid-unaccounted" for e in t30.get("errors", [])),
       "trace-30: the only omission is the right parathyroid account, and it is scored")
    ok(t30.get("verdict") == "PASS" and t30.get("management", {}).get("points") == 5,
       "trace-30: a postoperative consequence, managed at dp6 — not a failed attempt")

    # -- upper GI endoscopy (Milestone 62) --
    # The register's absences, probed against the Body Model data
    # (all_data_ids was collected for the carpal block above): no
    # ulcer, Dieulafoy, Mallory-Weiss or varices record exists
    # anywhere — the gate's lesions are endoscopic findings, not
    # records — while the organs, the duodenal lumen, the
    # gastroduodenal artery and the trachea its consequences
    # resolve onto genuinely do.
    ok(not any("ulcer" in i.lower() or "dieulafoy" in i.lower()
               or "mallory" in i.lower() or "varic" in i.lower() for i in all_data_ids),
       "no ulcer, Dieulafoy, Mallory-Weiss or varices record exists in the Body Model data (the absence notes are honest)")
    ok("dig.oesophagus" in all_data_ids and "dig.stomach" in all_data_ids
       and "dig.duodenum" in all_data_ids and "canal.duodenum" in all_data_ids
       and "artery.gastroduodenal-artery" in all_data_ids
       and "airway.trachea" in all_data_ids,
       "oesophagus, stomach, duodenum, gastroduodenal artery and trachea genuinely present (register records resolve)")

    t31 = by_trace.get("trace-31-endo-clean", {})
    ok(t31.get("checklist", {}).get("pct") == 100.0 and t31.get("checklist", {}).get("required") == 27
       and t31.get("safety_gate", {}).get("points") == 4,
       "trace-31: full checklist (27 required) and full gate score")
    ok(t31.get("process", {}).get("points") == 4,
       "trace-31: process 4/5 — no prophylaxis act exists in this procedure's consulted pathway (T49, T50), the ceiling is by design")
    ok(t31.get("errors") == [] and t31.get("complications") == [],
       "trace-31: the clean attempt carries no errors and computes no complications")
    t32 = by_trace.get("trace-32-endo-treat-before-classification", {})
    pf = [c for c in t32.get("complications", []) if c["kind"] == "perforation"]
    ok(len(pf) == 1 and pf[0]["resolved_structure"] == "canal.duodenum",
       "trace-32: the blind therapy computes a perforation on the duodenum (a documented record)")
    ok(t32.get("failed_at_s") == 1080.0, "trace-32: fails at the clip (t=1080s)")
    ok(t32.get("verdict") == "FAIL" and t32.get("management", {}).get("points") == 5,
       "trace-32: exemplary management (5/5) does not rescue the verdict")
    ok(t32.get("checklist", {}).get("missing") == ["m3.2", "m4.1", "m4.2"],
       "trace-32: the omissions are exactly the classification and the pause pair")
    t33 = by_trace.get("trace-33-endo-misclassification", {})
    rb = [c for c in t33.get("complications", []) if c["kind"] == "rebleeding"]
    ok(len(rb) == 1 and rb[0]["resolved_structure"] == "lesion.peptic-ulcer",
       "trace-33: the untreated true IIa computes rebleeding on the lesion")
    ok(any(e["id"] == "err.misclassification" for e in t33.get("errors", []))
       and any(e["id"] == "err.high-risk-untreated" for e in t33.get("errors", [])),
       "trace-33: the wrong declaration and the untreated truth are both scored")
    ok(t33.get("verdict") == "PASS" and t33.get("management", {}).get("points") == 5,
       "trace-33: a post-procedure consequence, managed at dp4 — not a failed attempt")
    t34 = by_trace.get("trace-34-endo-epinephrine-monotherapy", {})
    rb = [c for c in t34.get("complications", []) if c["kind"] == "rebleeding"]
    ok(len(rb) == 1 and any(e["id"] == "err.epinephrine-monotherapy" for e in t34.get("errors", [])),
       "trace-34: epinephrine alone on a high-risk lesion computes rebleeding")
    ok(t34.get("verdict") == "PASS" and t34.get("management", {}).get("points") == 5,
       "trace-34: scored as the prohibited configuration, managed at dp4 — not a failed attempt")
    t35 = by_trace.get("trace-35-endo-dieulafoy", {})
    ok(t35.get("checklist", {}).get("required") == 28 and t35.get("checklist", {}).get("pct") == 100.0
       and t35.get("verdict") == "PASS" and t35.get("errors") == [],
       "trace-35: Dieulafoy configuration requires 28 (artery search added) at 100% and passes clean")
    t36 = by_trace.get("trace-36-endo-dieulafoy-missed", {})
    hem = [c for c in t36.get("complications", []) if c["kind"] == "hemorrhage"]
    ok(len(hem) == 1 and hem[0]["resolved_structure"] == "lesion.dieulafoy"
       and abs(hem[0].get("loss_ml", 0) - 1500.0) < 5.0,
       "trace-36: the missed lesion's haemorrhage is 300 s at the 5.0 mL/s placeholder rate (1500 mL)")
    ok(t36.get("failed_at_s") == 1380.0 and t36.get("verdict") == "FAIL",
       "trace-36: fails at the completion survey (t=1380s)")
    ok(t36.get("checklist", {}).get("missing") == ["m3.3"]
       and t36.get("management", {}).get("points") == 5,
       "trace-36: the only omission is the artery search; exemplary management does not rescue the verdict")
    t37 = by_trace.get("trace-37-endo-airway-unprotected", {})
    asp = [c for c in t37.get("complications", []) if c["kind"] == "aspiration"]
    ok(len(asp) == 1 and asp[0]["resolved_structure"] == "airway.trachea",
       "trace-37: sedation over the unprotected airway computes aspiration on the trachea")
    ok(t37.get("checklist", {}).get("required") == 28 and t37.get("checklist", {}).get("pct") == 100.0
       and any(e["id"] == "err.unprotected-airway" for e in t37.get("errors", [])),
       "trace-37: the hematemesis configuration requires 28 (airway protection inserted) — performed late, at 100%, with the error standing")
    ok(t37.get("verdict") == "PASS" and t37.get("management", {}).get("points") == 5,
       "trace-37: a computed adverse event, recognised and managed — not a failed attempt")

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
