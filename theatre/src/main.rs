//! anatomica-theatre CLI.
//!
//!   anatomica-theatre validate
//!   anatomica-theatre run <trace.json> [--out <debrief.json>]
//!   anatomica-theatre run-all [--outdir <dir>]
//!
//! Data files (procedure, parameters, instruments) resolve relative
//! to the crate root, so the binary runs from any directory.

use anatomica_physiology::params::Params as PhysParams;
use anatomica_theatre::model::{InstrumentsFile, Procedure, TheatreParams, Trace};
use anatomica_theatre::runner::{run_attempt, Debrief};
use std::path::{Path, PathBuf};

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn load_all() -> Result<(Vec<Procedure>, TheatreParams, InstrumentsFile), String> {
    let r = root();
    // Every procedure file in procedures/ is loaded (Milestone 28:
    // the theatre now carries two procedures; traces name theirs).
    let dir = r.join("procedures");
    let mut paths: Vec<PathBuf> = std::fs::read_dir(&dir)
        .map_err(|e| format!("cannot list {}: {e}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().map(|x| x == "json").unwrap_or(false))
        .collect();
    paths.sort();
    let mut procs = Vec::new();
    for p in &paths {
        procs.push(Procedure::load(p)?);
    }
    if procs.is_empty() {
        return Err("no procedure files found".to_string());
    }
    let tparams = TheatreParams::load(&r.join("parameters.json"))?;
    let instruments = InstrumentsFile::load(&r.join("instruments.json"))?;
    Ok((procs, tparams, instruments))
}

/// The procedure a trace runs against: its named procedure, or the
/// cholecystectomy for the Milestone 17 traces that predate the field.
fn proc_for<'a>(procs: &'a [Procedure], trace: &Trace) -> Result<&'a Procedure, String> {
    let want = trace.procedure.as_deref().unwrap_or("proc.chole.lap");
    procs
        .iter()
        .find(|p| p.id == want)
        .ok_or_else(|| format!("trace {} names unknown procedure {want}", trace.id))
}

fn print_debrief(d: &Debrief) {
    println!("=== {} — {} ===", d.trace_id, d.trace_name);
    println!(
        "procedure {} | variant {} | duration {:.0} s | validity {}",
        d.procedure_id,
        d.case_variant.as_deref().unwrap_or("standard anatomy"),
        d.duration_s,
        d.validity_label
    );
    println!("VERDICT: {}", d.verdict);
    if let (Some(t), Some(r)) = (d.failed_at_s, &d.fail_reason) {
        println!("  failed at t={t:.0}s: {r}");
    }
    println!(
        "checklist: {:.1}% ({}/{}){}",
        d.checklist.pct,
        d.checklist.completed,
        d.checklist.required,
        if d.checklist.missing.is_empty() {
            String::new()
        } else {
            format!(" — missing: {}", d.checklist.missing.join(", "))
        }
    );
    println!(
        "safety gate: {}/{} (criteria before first clip/divide: {}, pre-clip pause: {})",
        d.safety_gate.points,
        d.safety_gate.max,
        d.safety_gate.criteria_before_first_clipdiv,
        d.safety_gate.pause_before_first_clip
    );
    if let Some(n) = &d.safety_gate.note {
        println!("  note: {n}");
    }
    println!(
        "process: {}/{} (sign-in {}, time-out {}, sign-out {}, prophylaxis in window {}, planning {})",
        d.process.points,
        d.process.max,
        d.process.sign_in,
        d.process.time_out,
        d.process.sign_out,
        d.process.prophylaxis_in_window,
        d.process.planning_complete
    );
    println!(
        "physiology: {}/{} (time {}, nadir {}, loss {}) — MAP baseline {:.1}, nadir {:.1} mmHg, {:.0} s below threshold, blood loss {:.0} mL (cross-check {:.0} mL), infused {:.0} mL",
        d.physiology.points,
        d.physiology.max,
        d.physiology.time_points,
        d.physiology.nadir_points,
        d.physiology.loss_points,
        d.physiology.map_baseline_mmhg,
        d.physiology.map_nadir_mmhg,
        d.physiology.seconds_below_threshold,
        d.physiology.blood_loss_ml,
        d.physiology.blood_loss_crosscheck_ml,
        d.physiology.infused_ml
    );
    match &d.management {
        Some(m) => println!(
            "management: {}/{} (recognised {}, control {}, escalation {}, plan {})",
            m.points, m.max, m.recognised, m.control, m.escalation, m.plan
        ),
        None => println!("management: n/a (no complication computed)"),
    }
    for c in &d.complications {
        println!(
            "complication: {} at t={:.0}s — {}{}{}",
            c.kind,
            c.t_onset_s,
            c.detail,
            c.stewart_way_class
                .as_ref()
                .map(|s| format!(" [Stewart-Way {s}]"))
                .unwrap_or_default(),
            c.loss_ml.map(|l| format!(" [loss {l:.0} mL]")).unwrap_or_default()
        );
    }
    for e in &d.errors {
        println!("error: {} at t={:.0}s — {}", e.id, e.t_s, e.detail);
    }
    println!(
        "engine: trace hash {}, {} beats, conservation error {:.2e} mL",
        d.engine_trace_hash, d.engine_beats, d.engine_conservation_error_ml
    );
    println!("\n-- debrief (PEARLS) --");
    println!("DESCRIPTION:");
    for l in &d.debrief.description {
        println!("  {l}");
    }
    println!("ANALYSIS — plus:");
    for l in &d.debrief.plus {
        println!("  + {l}");
    }
    println!("ANALYSIS — delta:");
    for l in &d.debrief.delta {
        println!("  - {l}");
    }
    println!("ANALYSIS — directive:");
    for l in &d.debrief.directive {
        println!("  > {l}");
    }
    println!("SUMMARY:");
    for l in &d.debrief.summary {
        println!("  {l}");
    }
}

fn run_one(
    procs: &[Procedure],
    tparams: &TheatreParams,
    phys: &PhysParams,
    trace_path: &Path,
    out: Option<&Path>,
) -> Result<Debrief, String> {
    let trace = Trace::load(trace_path)?;
    let proc = proc_for(procs, &trace)?;
    let d = run_attempt(proc, tparams, phys, &trace)?;
    print_debrief(&d);
    let expect_ok = d.verdict.to_lowercase() == trace.expect_verdict.to_lowercase();
    println!(
        "expectation: {} (trace expects {})",
        if expect_ok { "MET" } else { "NOT MET" },
        trace.expect_verdict
    );
    if let Some(out) = out {
        let json = serde_json::to_string_pretty(&d).map_err(|e| e.to_string())?;
        std::fs::write(out, json).map_err(|e| format!("cannot write {}: {e}", out.display()))?;
        println!("debrief written: {}", out.display());
    }
    if !expect_ok {
        return Err(format!("trace {} verdict {} != expected {}", trace.id, d.verdict, trace.expect_verdict));
    }
    Ok(d)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let cmd = args.get(1).map(|s| s.as_str()).unwrap_or("");
    let result: Result<(), String> = (|| {
        let (procs, tparams, instruments) = load_all()?;
        match cmd {
            "validate" => {
                let mut all_problems = 0;
                for proc in &procs {
                    let problems = proc.validate(&instruments.ids());
                    let (ph, st, mi, req) = proc.census();
                    println!(
                        "procedure {} — {ph} phases, {st} steps, {mi} microsteps ({req} required in the standard configuration)",
                        proc.id
                    );
                    println!(
                        "structures {}, gates {}, decision points {}, errors {}, variants {}",
                        proc.structures.len(),
                        proc.safety_gates.len(),
                        proc.decision_points.len(),
                        proc.errors.len(),
                        proc.variants.len()
                    );
                    if problems.is_empty() {
                        println!("validation: PASS (no internal consistency problems)");
                    } else {
                        for p in &problems {
                            println!("validation problem: {p}");
                        }
                        all_problems += problems.len();
                    }
                }
                println!(
                    "theatre parameters: {} ({} verify-flagged)",
                    tparams.file.parameters.len(),
                    tparams.file.parameters.iter().filter(|p| p.status == "verify").count()
                );
                println!("instruments: {}", instruments.instruments.len());
                if all_problems == 0 {
                    Ok(())
                } else {
                    Err(format!("validation: FAIL ({all_problems} problems)"))
                }
            }
            "run" => {
                let trace_path = args.get(2).ok_or("usage: run <trace.json> [--out <debrief.json>]")?;
                let out = if args.get(3).map(|s| s.as_str()) == Some("--out") {
                    args.get(4).map(PathBuf::from)
                } else {
                    None
                };
                let phys = PhysParams::load()?;
                run_one(&procs, &tparams, &phys, Path::new(trace_path), out.as_deref())?;
                Ok(())
            }
            "run-all" => {
                let outdir = if args.get(2).map(|s| s.as_str()) == Some("--outdir") {
                    args.get(3).map(PathBuf::from)
                } else {
                    None
                }
                .unwrap_or_else(|| root().join("debriefs"));
                std::fs::create_dir_all(&outdir).map_err(|e| e.to_string())?;
                let phys = PhysParams::load()?;
                let traces_dir = root().join("traces");
                let mut paths: Vec<PathBuf> = std::fs::read_dir(&traces_dir)
                    .map_err(|e| format!("cannot list {}: {e}", traces_dir.display()))?
                    .filter_map(|e| e.ok().map(|e| e.path()))
                    .filter(|p| p.extension().map(|x| x == "json").unwrap_or(false))
                    .collect();
                paths.sort();
                let mut failures = 0;
                for p in &paths {
                    println!("\n########################################");
                    let out = outdir.join(format!(
                        "{}.debrief.json",
                        p.file_stem().unwrap().to_string_lossy()
                    ));
                    if let Err(e) = run_one(&procs, &tparams, &phys, p, Some(&out)) {
                        println!("RUN PROBLEM: {e}");
                        failures += 1;
                    }
                }
                println!("\nrun-all complete: {} traces, {} expectation failures", paths.len(), failures);
                if failures > 0 {
                    Err(format!("{failures} trace expectation failure(s)"))
                } else {
                    Ok(())
                }
            }
            _ => Err("usage: anatomica-theatre <validate|run <trace.json> [--out f]|run-all [--outdir d]>".to_string()),
        }
    })();
    if let Err(e) = result {
        eprintln!("ERROR: {e}");
        std::process::exit(1);
    }
}
