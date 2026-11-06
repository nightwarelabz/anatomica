//! CLI: `anatomica-physiology validate | run <case> | determinism`
//!
//! `validate` runs the resting case against every published normal range
//! in parameters.json (one PASS/FAIL line per output), then the
//! perturbation cases against their sourced directional expectations
//! and (Milestone 18) magnitude gates, then the 30-minute transcapillary
//! refill observation against its cited band, then (Milestone 24) the
//! Guyton venous-return formulation checks and the −1,500 mL
//! haemorrhage course (untreated vs ATLS-bolus arms). Exit status is 0
//! only if every hard-gated line passes.

use anatomica_physiology::cases::{
    evaluate_course, evaluate_perturbation, evaluate_refill, evaluate_resting,
    run_case, run_hemorrhage_1500_course, run_refill_observation, CaseKind, CourseOutcome,
    WindowStats,
};
use anatomica_physiology::params::Params;
use std::process::ExitCode;

fn print_window(label: &str, s: &WindowStats) {
    println!(
        "{label}: beats={} HR={:.1} bpm  BP={:.1}/{:.1} mmHg  MAP={:.1}  PP={:.1} ({:.0}% of sys)  \
         CO={:.2} L/min  SVlv={:.1} mL  SVrv={:.1} mL  CVP={:.2} mmHg  RAPproxy={:.2} mmHg  PA={:.1}/{:.1} mean {:.1}  \
         PVmean={:.2} mmHg  drift MAP={:.3}% CO={:.3}%",
        s.beats,
        s.hr,
        s.sbp,
        s.dbp,
        s.map,
        s.pulse_pressure,
        s.pp_fraction * 100.0,
        s.co,
        s.sv_lv,
        s.sv_rv,
        s.cvp,
        s.rap,
        s.pa_systolic,
        s.pa_diastolic,
        s.pa_mean,
        s.pv_mean,
        s.map_drift * 100.0,
        s.co_drift * 100.0,
    );
}

fn validate(params: &Params) -> bool {
    let mut ok = true;
    println!("=== RESTING CASE — steady state vs published normal ranges ===");
    let resting = run_case(params, CaseKind::Resting);
    print_window("baseline (reflex off, ticks 4500-6000)", &resting.baseline);
    print_window("post     (reflex on,  ticks 10500-12000)", &resting.post);
    for line in evaluate_resting(params, &resting.post) {
        let verdict = if line.pass {
            if line.soft { "SOFT-PASS" } else { "PASS" }
        } else if line.soft {
            "SOFT-FAIL (disclosed, not gating)"
        } else {
            "FAIL"
        };
        if !line.pass && !line.soft {
            ok = false;
        }
        println!(
            "  {:<34} {:>9.2} {:<12} range {:<14} [{}] {}",
            line.output, line.value, line.unit, line.range_text, line.source, verdict
        );
    }
    // Engineering consistency lines (labelled as such — not physiology).
    let tol = params.f64("steady_state_drift_tolerance");
    let drift_ok = resting.post.map_drift < tol && resting.post.co_drift < tol;
    if !drift_ok {
        ok = false;
    }
    println!(
        "  {:<34} MAP {:.3}% / CO {:.3}%   criterion < {:.1}%   [engineering threshold, parameters.json] {}",
        "steady-state drift (window halves)",
        resting.post.map_drift * 100.0,
        resting.post.co_drift * 100.0,
        tol * 100.0,
        if drift_ok { "PASS" } else { "FAIL" }
    );
    let sv_balance = (resting.post.sv_lv - resting.post.sv_rv).abs() / resting.post.sv_lv;
    let sv_ok = sv_balance < 0.05;
    if !sv_ok {
        ok = false;
    }
    println!(
        "  {:<34} LV {:.1} vs RV {:.1} mL   criterion < 5%   [series-circuit identity] {}",
        "stroke-volume balance",
        resting.post.sv_lv,
        resting.post.sv_rv,
        if sv_ok { "PASS" } else { "FAIL" }
    );
    let cons_ok = resting.conservation_error_ml < 0.01;
    if !cons_ok {
        ok = false;
    }
    println!(
        "  {:<34} {:.2e} mL   criterion < 0.01 mL   [closed-loop identity] {}",
        "volume conservation error",
        resting.conservation_error_ml,
        if cons_ok { "PASS" } else { "FAIL" }
    );
    println!("  trace hash (resting protocol): {:#018x}", resting.trace_hash);
    // Milestone 24: the Guyton venous-return formulation, checked at
    // the resting operating point. MSFP gate band is a disclosed
    // project tolerance around the cited ~7 mmHg (S17/S18); the RVR
    // agreement is an engineering identity check (the formulation
    // verified against the circuit's own structure), labelled as such.
    let msfp_ok = resting.msfp_mmhg >= 5.0 && resting.msfp_mmhg <= 9.0;
    if !msfp_ok {
        ok = false;
    }
    println!(
        "  {:<34} {:>9.2} mmHg   cited ~7 [S17/S18]; project tolerance band [5 .. 9] {}",
        "mean systemic filling pressure",
        resting.msfp_mmhg,
        if msfp_ok { "PASS" } else { "FAIL" }
    );
    println!(
        "  {:<34} {:>9.2} mmHg   (stop-flow equilibration over the whole circuit; reported, S17/S21)",
        "mean circulatory filling pressure",
        resting.mcfp_mmhg
    );
    println!(
        "  {:<34} {:>9.1} mL   systemic vascular tree, above unstressed volumes (reported)",
        "systemic stressed volume",
        resting.stressed_sys_ml
    );
    let rvr_rel = (resting.rvr_empirical - resting.rvr_formula).abs() / resting.rvr_formula;
    let rvr_ok = rvr_rel < 0.15;
    if !rvr_ok {
        ok = false;
    }
    println!(
        "  {:<34} empirical {:.4} vs formula {:.4} mmHg*s/mL ({:.3} vs {:.3} mmHg*min/L), rel. diff {:.1}%   criterion < 15%   [engineering identity, MILESTONE-24] {}",
        "resistance to venous return",
        resting.rvr_empirical,
        resting.rvr_formula,
        resting.rvr_empirical * 1000.0 / 60.0,
        resting.rvr_formula * 1000.0 / 60.0,
        rvr_rel * 100.0,
        if rvr_ok { "PASS" } else { "FAIL" }
    );

    for (kind, id, title) in [
        (CaseKind::Hemorrhage750, "hemorrhage_750", "HAEMORRHAGE -750 mL"),
        (CaseKind::Infusion1000, "infusion_1000", "VOLUME INFUSION +1000 mL"),
        (CaseKind::Hemorrhage1500, "hemorrhage_1500", "HAEMORRHAGE -1500 mL"),
    ] {
        println!("\n=== {title} — directional + magnitude expectations ===");
        let outcome = run_case(params, kind);
        print_window("baseline", &outcome.baseline);
        print_window("post    ", &outcome.post);
        for line in evaluate_perturbation(params, id, &outcome) {
            if !line.pass && !line.soft {
                ok = false;
            }
            let band = match line.magnitude_range {
                Some([lo, hi]) => format!("  band [{lo:.1} .. {hi:.1}]"),
                None => String::new(),
            };
            let verdict = if line.pass {
                "PASS"
            } else if line.soft {
                "SOFT-FAIL (disclosed, not gating)"
            } else {
                "FAIL"
            };
            println!(
                "  {:<28} {:>9.2} -> {:>9.2}  (delta {:+.2})  expected {:<8}{} [{}] {}",
                line.output,
                line.baseline,
                line.post,
                line.delta,
                line.expected,
                band,
                line.source,
                verdict
            );
        }
        println!("  trace hash: {:#018x}", outcome.trace_hash);
        println!(
            "  Guyton end state: stressed {:.1} mL  MSFP {:.2} mmHg  MCFP {:.2} mmHg  RVR empirical {:.4} mmHg*s/mL (reported)",
            outcome.stressed_sys_ml, outcome.msfp_mmhg, outcome.mcfp_mmhg, outcome.rvr_empirical
        );
        println!("  causal chain (event log):");
        for entry in &outcome.causal_chain {
            println!("    {entry}");
        }
    }

    println!("\n=== TRANSCAPILLARY REFILL OBSERVATION — 750 mL loss, 30 min horizon ===");
    let refill = run_refill_observation(params);
    for (m, rf, vn) in &refill.samples {
        println!(
            "  +{:>4.0} min after bleed end: net refill {:7.1} mL ({:4.1}% of loss), recruited {:6.1} mL",
            m,
            rf,
            rf / 750.0 * 100.0,
            vn
        );
    }
    print_window("final window (last 30 s)", &refill.final_window);
    let (value, band, pass) = evaluate_refill(params, &refill);
    if !pass {
        ok = false;
    }
    println!(
        "  {:<34} {:>9.1} mL   band [{:.1} .. {:.1}] mL (15-35% of loss; cited point ~25%, S15) {}",
        "net refill at +30 min",
        value,
        band[0],
        band[1],
        if pass { "PASS" } else { "FAIL" }
    );
    let cons_ok = refill.conservation_error_ml < 0.01;
    if !cons_ok {
        ok = false;
    }
    println!(
        "  {:<34} {:.2e} mL   criterion < 0.01 mL   [closed-loop identity incl. refill inflow] {}",
        "volume conservation error",
        refill.conservation_error_ml,
        if cons_ok { "PASS" } else { "FAIL" }
    );
    println!("  trace hash: {:#018x}", refill.trace_hash);

    println!("\n=== HAEMORRHAGE -1500 mL COURSE — 60 min, untreated vs ATLS bolus (Milestone 24) ===");
    let untreated = run_hemorrhage_1500_course(params, false);
    let treated = run_hemorrhage_1500_course(params, true);
    print_course("untreated", &untreated);
    print_course("treated (+1000 mL crystalloid bolus from bleed end)", &treated);
    for line in evaluate_course(params, &untreated, &treated) {
        if !line.pass && !line.soft {
            ok = false;
        }
        let band = match line.magnitude_range {
            Some([lo, hi]) => format!("  band [{lo:.1} .. {hi:.1}]"),
            None => String::new(),
        };
        let verdict = if line.pass {
            "PASS"
        } else if line.soft {
            "SOFT-FAIL (disclosed, not gating)"
        } else {
            "FAIL"
        };
        println!(
            "  {:<34} {:>9.2} -> {:>9.2}  expected {:<8}{} [{}] {}",
            line.output, line.baseline, line.post, line.expected, band,
            if line.source.len() > 60 { &line.source[..60] } else { &line.source },
            verdict
        );
    }
    for (label, arm) in [("untreated", &untreated), ("treated", &treated)] {
        let cons_ok = arm.conservation_error_ml < 0.01;
        if !cons_ok {
            ok = false;
        }
        println!(
            "  {:<34} {:.2e} mL   criterion < 0.01 mL   [closed-loop identity] {} ({})",
            "volume conservation error",
            arm.conservation_error_ml,
            if cons_ok { "PASS" } else { "FAIL" },
            label
        );
        println!("  trace hash ({label}): {:#018x}", arm.trace_hash);
    }

    println!("\nVALIDATION: {}", if ok { "ALL HARD GATES PASS" } else { "FAILURES PRESENT" });
    ok
}

fn print_course(label: &str, arm: &CourseOutcome) {
    println!("  course arm: {label}");
    for s in &arm.samples {
        println!(
            "    +{:>4.0} min: HR {:6.1}  MAP {:6.1}  CO {:5.2}  SV {:5.1}  CVP {:5.2}  RAP {:.2} | stressed {:6.1} mL  MSFP {:5.2}  MCFP {:5.2} | recruited {:6.1}  refill {:6.1}  ino x{:.2}",
            s.minutes_after_bleed_end,
            s.window.hr,
            s.window.map,
            s.window.co,
            s.window.sv_lv,
            s.window.cvp,
            s.window.rap,
            s.stressed_sys_ml,
            s.msfp_mmhg,
            s.mcfp_mmhg,
            s.recruited_ml,
            s.refill_ml,
            s.contractility,
        );
    }
}

fn main() -> ExitCode {
    let params = match Params::load() {
        Ok(p) => p,
        Err(e) => {
            eprintln!("parameter error: {e}");
            return ExitCode::FAILURE;
        }
    };
    let args: Vec<String> = std::env::args().collect();
    match args.get(1).map(|s| s.as_str()) {
        Some("validate") => {
            if validate(&params) {
                ExitCode::SUCCESS
            } else {
                ExitCode::FAILURE
            }
        }
        Some("run") if args.get(2).map(|s| s.as_str()) == Some("course") => {
            let untreated = run_hemorrhage_1500_course(&params, false);
            let treated = run_hemorrhage_1500_course(&params, true);
            print_course("untreated", &untreated);
            print_course("treated (+1000 mL crystalloid bolus from bleed end)", &treated);
            for line in evaluate_course(&params, &untreated, &treated) {
                println!(
                    "  {:<34} {:>9.2} -> {:>9.2}  expected {:<8} {}",
                    line.output,
                    line.baseline,
                    line.post,
                    line.expected,
                    if line.pass {
                        "PASS"
                    } else if line.soft {
                        "SOFT-FAIL (disclosed, not gating)"
                    } else {
                        "FAIL"
                    }
                );
            }
            println!("untreated trace hash: {:#018x}", untreated.trace_hash);
            println!("treated   trace hash: {:#018x}", treated.trace_hash);
            ExitCode::SUCCESS
        }
        Some("run") if args.get(2).map(|s| s.as_str()) == Some("refill") => {
            let outcome = run_refill_observation(&params);
            for (m, rf, vn) in &outcome.samples {
                println!(
                    "+{:>4.0} min: net refill {:7.1} mL ({:4.1}% of 750 mL loss), recruited {:6.1} mL",
                    m,
                    rf,
                    rf / 750.0 * 100.0,
                    vn
                );
            }
            print_window("final window", &outcome.final_window);
            println!("trace hash: {:#018x}", outcome.trace_hash);
            println!("volume conservation error: {:.2e} mL", outcome.conservation_error_ml);
            ExitCode::SUCCESS
        }
        Some("run") => {
            let kind = match args.get(2).map(|s| s.as_str()) {
                Some("resting") => CaseKind::Resting,
                Some("hemorrhage") => CaseKind::Hemorrhage750,
                Some("infusion") => CaseKind::Infusion1000,
                Some("hemorrhage1500") => CaseKind::Hemorrhage1500,
                _ => {
                    eprintln!("usage: run resting|hemorrhage|infusion|hemorrhage1500|refill|course");
                    return ExitCode::FAILURE;
                }
            };
            let outcome = run_case(&params, kind);
            print_window("baseline", &outcome.baseline);
            print_window("post    ", &outcome.post);
            println!("trace hash: {:#018x}", outcome.trace_hash);
            println!("volume conservation error: {:.2e} mL", outcome.conservation_error_ml);
            for entry in &outcome.causal_chain {
                println!("  {entry}");
            }
            ExitCode::SUCCESS
        }
        Some("determinism") => {
            let a = run_case(&params, CaseKind::Resting);
            let b = run_case(&params, CaseKind::Resting);
            println!("run A trace hash: {:#018x}", a.trace_hash);
            println!("run B trace hash: {:#018x}", b.trace_hash);
            if a.trace_hash == b.trace_hash {
                println!("DETERMINISM: IDENTICAL");
                ExitCode::SUCCESS
            } else {
                println!("DETERMINISM: MISMATCH");
                ExitCode::FAILURE
            }
        }
        _ => {
            eprintln!("usage: anatomica-physiology validate | run resting|hemorrhage|infusion|hemorrhage1500|refill|course | determinism");
            ExitCode::FAILURE
        }
    }
}
