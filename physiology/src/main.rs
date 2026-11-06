//! CLI: `anatomica-physiology validate | run <case> | determinism`
//!
//! `validate` runs the resting case against every published normal range
//! in parameters.json (one PASS/FAIL line per output), then the two
//! perturbation sanity cases against their sourced directional
//! expectations. Exit status is 0 only if every hard-gated line passes.

use anatomica_physiology::cases::{
    evaluate_perturbation, evaluate_resting, run_case, CaseKind, WindowStats,
};
use anatomica_physiology::params::Params;
use std::process::ExitCode;

fn print_window(label: &str, s: &WindowStats) {
    println!(
        "{label}: beats={} HR={:.1} bpm  BP={:.1}/{:.1} mmHg  MAP={:.1}  PP={:.1} ({:.0}% of sys)  \
         CO={:.2} L/min  SVlv={:.1} mL  SVrv={:.1} mL  CVP={:.2} mmHg  PA={:.1}/{:.1} mean {:.1}  \
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

    for (kind, id, title) in [
        (CaseKind::Hemorrhage750, "hemorrhage_750", "HAEMORRHAGE -750 mL"),
        (CaseKind::Infusion1000, "infusion_1000", "VOLUME INFUSION +1000 mL"),
    ] {
        println!("\n=== {title} — directional expectations ===");
        let outcome = run_case(params, kind);
        print_window("baseline", &outcome.baseline);
        print_window("post    ", &outcome.post);
        for line in evaluate_perturbation(params, id, &outcome) {
            if !line.pass {
                ok = false;
            }
            println!(
                "  {:<28} {:>9.2} -> {:>9.2}  (delta {:+.2})  expected {:<8} [{}] {}",
                line.output,
                line.baseline,
                line.post,
                line.delta,
                line.expected,
                line.source,
                if line.pass { "PASS" } else { "FAIL" }
            );
        }
        println!("  trace hash: {:#018x}", outcome.trace_hash);
        println!("  causal chain (event log):");
        for entry in &outcome.causal_chain {
            println!("    {entry}");
        }
    }
    println!("\nVALIDATION: {}", if ok { "ALL HARD GATES PASS" } else { "FAILURES PRESENT" });
    ok
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
        Some("run") => {
            let kind = match args.get(2).map(|s| s.as_str()) {
                Some("resting") => CaseKind::Resting,
                Some("hemorrhage") => CaseKind::Hemorrhage750,
                Some("infusion") => CaseKind::Infusion1000,
                _ => {
                    eprintln!("usage: run resting|hemorrhage|infusion");
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
            eprintln!("usage: anatomica-physiology validate | run resting|hemorrhage|infusion | determinism");
            ExitCode::FAILURE
        }
    }
}
