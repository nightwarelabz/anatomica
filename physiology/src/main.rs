//! CLI: `anatomica-physiology validate | run <case> | determinism`
//!
//! `validate` runs the resting case against every published normal range
//! in parameters.json (one PASS/FAIL line per output), then the
//! perturbation cases against their sourced directional expectations
//! and (Milestone 18) magnitude gates, then the 30-minute transcapillary
//! refill observation against its cited band, then (Milestone 24) the
//! Guyton venous-return formulation checks and the −1,500 mL
//! haemorrhage course (untreated vs ATLS-bolus arms). Exit status is 0
//! only if every hard-gated line passes. Milestone 25 adds the
//! urine-output resting line (gated in parameters.json), the course's
//! volume-side sample columns and bolus-retention line, and a
//! long-horizon resting run (60 engaged minutes) proving the resting
//! steady state and the equilibrium urine output now that an
//! excretory pathway is open. Milestone 26 adds the oncotic resting
//! lines (hematocrit, plasma and interstitial oncotic pressures),
//! the course's whole-blood and components arms beside the
//! crystalloid arm, and the product-arm retention/oncotic course
//! lines. Milestone 30 adds the hormonal resting lines (plasma
//! osmolality and sodium, urine osmolality, plasma ADH), the
//! course's hormonal sample columns, and a hormonal-axes section:
//! the water-load, water-deprivation and sodium-load arms plus the
//! −1,500 mL course extended to 12 h, evaluated against the
//! hormonal cases in parameters.json (`run hormones` prints the
//! same section standalone).

use anatomica_physiology::cases::{
    evaluate_course, evaluate_hormones, evaluate_perturbation, evaluate_refill, evaluate_resting,
    run_case, run_course_arm, run_hormone_set, run_long_rest, run_refill_observation, CaseKind,
    CourseArm, CourseOutcome, CourseSet, HormoneArmOutcome, LongRestOutcome, WindowStats,
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
    for line in evaluate_resting(params, &resting) {
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

    println!("\n=== HAEMORRHAGE -1500 mL COURSE — 60 min, untreated vs ATLS bolus vs blood products (Milestones 24-26) ===");
    let set = run_course_set(params);
    print_course("untreated", &set.untreated);
    print_course("treated (+1000 mL crystalloid bolus from bleed end)", &set.crystalloid);
    print_course("whole blood (2 units from bleed end)", &set.whole_blood);
    print_course("components (2 units PRBC, then 2 units plasma)", &set.components);
    for line in evaluate_course(params, &set) {
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
    for (label, arm) in [
        ("untreated", &set.untreated),
        ("treated", &set.crystalloid),
        ("whole blood", &set.whole_blood),
        ("components", &set.components),
    ] {
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

    println!("\n=== LONG-HORIZON RESTING — 60 min engaged (Milestone 25) ===");
    let long = run_long_rest(params);
    print_long_rest(params, &long, &mut ok);

    println!("\n=== HORMONAL AXES — ADH + RAAS/aldosterone scenario arms (Milestone 30) ===");
    let hormones = run_hormone_set(params);
    print_hormone_arm("water load (+1000 mL solute-free water at engagement)", &hormones.water_load);
    print_hormone_arm("water deprivation (intake zeroed at engagement)", &hormones.deprivation);
    print_hormone_arm("sodium load (sodium intake x5, water intake x3, at engagement)", &hormones.sodium_load);
    print_course("long course untreated (−1500 mL, 12 h)", &hormones.long_course.untreated);
    print_course("long course crystalloid (−1500 mL + 1 L bolus, 12 h)", &hormones.long_course.crystalloid);
    for line in evaluate_hormones(params, &hormones) {
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
            "  {:<52} {:>9.2} -> {:>9.2}  (delta {:+.2})  expected {:<8}{} [{}] {}",
            line.output,
            line.baseline,
            line.post,
            line.delta,
            line.expected,
            band,
            if line.source.len() > 60 { &line.source[..60] } else { &line.source },
            verdict
        );
    }
    for (label, arm) in [
        ("water load", &hormones.water_load),
        ("water control", &hormones.water_control),
        ("deprivation", &hormones.deprivation),
        ("sodium load", &hormones.sodium_load),
    ] {
        let cons_ok = arm.conservation_error_ml < 0.01;
        if !cons_ok {
            ok = false;
        }
        println!(
            "  {:<52} {:.2e} mL   criterion < 0.01 mL   [closed-loop identity] {} ({})",
            "volume conservation error",
            arm.conservation_error_ml,
            if cons_ok { "PASS" } else { "FAIL" },
            label
        );
        println!("  trace hash ({label}): {:#018x}", arm.trace_hash);
    }
    for (label, arm) in [
        ("long course untreated", &hormones.long_course.untreated),
        ("long course crystalloid", &hormones.long_course.crystalloid),
    ] {
        let cons_ok = arm.conservation_error_ml < 0.01;
        if !cons_ok {
            ok = false;
        }
        println!(
            "  {:<52} {:.2e} mL   criterion < 0.01 mL   [closed-loop identity] {} ({})",
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

/// One hormonal arm's mark table (Milestone 30): the axis states
/// and readouts at each mark — osmolality and sodium (the sensed
/// variables), ADH and the aldosterone effect state (the axes),
/// urine flow / sodium excretion / urine osmolality (the effects).
fn print_hormone_arm(label: &str, arm: &HormoneArmOutcome) {
    println!("  hormone arm: {label}");
    println!(
        "    resting at engagement: ADH {:.2} pg/mL  osmolality {:.1} mOsm/kg  urine osmolality {:.0} mOsm/kg",
        arm.resting_adh_pg_ml, arm.resting_osmolality_mosm_kg, arm.resting_urine_osmolality_mosm_kg
    );
    let mut prev: Option<&anatomica_physiology::cases::HormoneSample> = None;
    for s in &arm.samples {
        let interval_uo = match prev {
            Some(p) if s.minutes > p.minutes => {
                (s.urine_ml - p.urine_ml) / (s.minutes - p.minutes)
            }
            _ => f64::NAN,
        };
        println!(
            "    +{:>5.0} min: MAP {:6.1} | Osm {:6.1} mOsm/kg  Na {:6.1} mmol/L | ADH {:6.2} pg/mL  aldo x{:.2} | urine {:5.2} mL/min (interval {:5.2})  UNa {:6.3} mmol/min  Uosm {:5.0} | cum urine {:6.1} mL  cum UNa {:6.1} mmol  Na body {:7.1} mmol  ICF {:6.0} mL",
            s.minutes,
            s.window.map,
            s.osmolality_mosm_kg,
            s.sodium_mmol_l,
            s.adh_pg_ml,
            s.aldo_state,
            s.urine_rate_ml_min,
            interval_uo,
            s.urine_na_rate_mmol_min,
            s.urine_osmolality_mosm_kg,
            s.urine_ml,
            s.urine_na_mmol,
            s.na_mmol,
            s.icf_ml,
        );
        prev = Some(s);
    }
}

/// The Milestone 25 long-horizon resting section: first vs last
/// window drift under the existing steady-state tolerance, the
/// equilibrium urine output against its cited band (S24), and the
/// engaged hour's boundary balance (urine vs intake — an
/// engineering balance criterion, disclosed as such: at a true
/// equilibrium the two must nearly cancel over the hour).
fn print_long_rest(params: &Params, long: &LongRestOutcome, ok: &mut bool) {
    print_window("first window (30 s engaged)", &long.first_window);
    print_window("mid window (+30 min)", &long.mid_window);
    print_window("last window (+60 min)", &long.last_window);
    // The steady-state gate compares two POST-TRANSIENT windows
    // (+30 vs +60 min): the first window sits inside the engagement
    // transient by construction (the same reason the standard
    // protocol's post window starts 90 s after engagement), so a
    // first-vs-last comparison would gate the transient, not the
    // steady state. Both comparisons are printed; the gate is the
    // post-transient one.
    let tol = params.f64("steady_state_drift_tolerance");
    let map_drift = (long.last_window.map - long.mid_window.map).abs() / long.mid_window.map;
    let co_drift = (long.last_window.co - long.mid_window.co).abs() / long.mid_window.co;
    let drift_ok = map_drift < tol && co_drift < tol;
    if !drift_ok {
        *ok = false;
    }
    println!(
        "  {:<34} MAP {:6.3}%  CO {:6.3}%   criterion < {:.1}% [+30 -> +60 min, post-transient] {}",
        "window drift mid -> last",
        map_drift * 100.0,
        co_drift * 100.0,
        tol * 100.0,
        if drift_ok { "PASS" } else { "FAIL" }
    );
    let map_drift_fl = (long.last_window.map - long.first_window.map).abs() / long.first_window.map;
    let co_drift_fl = (long.last_window.co - long.first_window.co).abs() / long.first_window.co;
    println!(
        "  {:<34} MAP {:6.3}%  CO {:6.3}%   [reported: includes the engagement transient]",
        "window drift first -> last",
        map_drift_fl * 100.0,
        co_drift_fl * 100.0
    );
    let (ulo, uhi, usrc) = params
        .validation_range("urine_output")
        .map(|r| (r.low, r.high.unwrap_or(f64::INFINITY), r.source.clone()))
        .unwrap_or((f64::NAN, f64::NAN, String::new()));
    let uo_ok = long.final_uo_ml_min >= ulo && long.final_uo_ml_min <= uhi;
    if !uo_ok {
        *ok = false;
    }
    println!(
        "  {:<34} {:>9.2} mL/min   cited band [{:.1} .. {:.1}] mL/min ({}) — mean over the final 30 min {}",
        "equilibrium urine output",
        long.final_uo_ml_min,
        ulo,
        uhi,
        usrc,
        if uo_ok { "PASS" } else { "FAIL" }
    );
    let net = long.urine_engaged_hour_ml - long.intake_engaged_hour_ml;
    let bal_ok = net.abs() < 15.0;
    if !bal_ok {
        *ok = false;
    }
    println!(
        "  {:<34} urine {:7.1} mL vs intake {:7.1} mL over the engaged hour (net {:+6.1} mL)   criterion |net| < 15 mL [engineering balance] {}",
        "boundary balance",
        long.urine_engaged_hour_ml,
        long.intake_engaged_hour_ml,
        net,
        if bal_ok { "PASS" } else { "FAIL" }
    );
    println!(
        "  {:<34} {:.1} mL at engagement -> {:.1} mL at +60 min (net refill {:+.2} mL)",
        "interstitial volume",
        long.isf_at_engagement_ml,
        long.isf_at_end_ml,
        long.refill_at_end_ml
    );
    let cons_ok = long.conservation_error_ml < 0.01;
    if !cons_ok {
        *ok = false;
    }
    println!(
        "  {:<34} {:.2e} mL   criterion < 0.01 mL   [closed-loop identity incl. intake/urine] {}",
        "volume conservation error",
        long.conservation_error_ml,
        if cons_ok { "PASS" } else { "FAIL" }
    );
    println!("  trace hash: {:#018x}", long.trace_hash);
}

/// Run all four course arms (Milestone 26).
fn run_course_set(params: &Params) -> CourseSet {
    CourseSet {
        untreated: run_course_arm(params, CourseArm::Untreated),
        crystalloid: run_course_arm(params, CourseArm::Crystalloid),
        whole_blood: run_course_arm(params, CourseArm::WholeBlood),
        components: run_course_arm(params, CourseArm::Components),
    }
}

fn print_course(label: &str, arm: &CourseOutcome) {
    println!("  course arm: {label}");
    let mut prev: Option<&anatomica_physiology::cases::CourseSample> = None;
    for s in &arm.samples {
        // Urine rate over the interval ending at this mark (mL/min),
        // from the cumulative renal state at consecutive marks.
        let uo_rate = match prev {
            Some(p) => {
                (s.urine_ml - p.urine_ml)
                    / (s.minutes_after_bleed_end - p.minutes_after_bleed_end)
            }
            None => f64::NAN,
        };
        // Sodium excretion rate over the same interval (mmol/min,
        // Milestone 30), from the cumulative urinary sodium state.
        let una_rate = match prev {
            Some(p) => {
                (s.urine_na_mmol - p.urine_na_mmol)
                    / (s.minutes_after_bleed_end - p.minutes_after_bleed_end)
            }
            None => f64::NAN,
        };
        println!(
            "    +{:>4.0} min: HR {:6.1}  MAP {:6.1}  CO {:5.2}  SV {:5.1}  CVP {:5.2}  RAP {:.2} | stressed {:6.1} mL  MSFP {:5.2}  MCFP {:5.2} | recruited {:6.1}  refill {:6.1}  ino x{:.2} | urine {:6.1} mL (rate {:5.2}/min)  ISF {:7.1} mL  blood {:6.1} mL | Hct {:.3}  pi_c {:5.1}  pi_i {:4.1} mmHg  product {:6.1} mL | Osm {:5.1}  Na {:5.1}  ADH {:5.1}  aldo x{:.2}  Uosm {:4.0}  UNa {:5.3}/min",
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
            s.urine_ml,
            uo_rate,
            s.isf_ml,
            s.blood_volume_ml,
            s.hematocrit,
            s.plasma_oncotic_mmhg,
            s.isf_oncotic_mmhg,
            s.product_ml,
            s.osmolality_mosm_kg,
            s.sodium_mmol_l,
            s.adh_pg_ml,
            s.aldo_state,
            s.urine_osmolality_mosm_kg,
            una_rate,
        );
        prev = Some(s);
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
            let set = run_course_set(&params);
            print_course("untreated", &set.untreated);
            print_course("treated (+1000 mL crystalloid bolus from bleed end)", &set.crystalloid);
            print_course("whole blood (2 units from bleed end)", &set.whole_blood);
            print_course("components (2 units PRBC, then 2 units plasma)", &set.components);
            for line in evaluate_course(&params, &set) {
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
            println!("untreated   trace hash: {:#018x}", set.untreated.trace_hash);
            println!("treated     trace hash: {:#018x}", set.crystalloid.trace_hash);
            println!("whole blood trace hash: {:#018x}", set.whole_blood.trace_hash);
            println!("components  trace hash: {:#018x}", set.components.trace_hash);
            ExitCode::SUCCESS
        }
        Some("run") if args.get(2).map(|s| s.as_str()) == Some("hormones") => {
            let set = run_hormone_set(&params);
            print_hormone_arm(
                "water load (+1000 mL solute-free water at engagement)",
                &set.water_load,
            );
            print_hormone_arm(
                "water deprivation (intake zeroed at engagement)",
                &set.deprivation,
            );
            print_hormone_arm("sodium load (sodium intake x5, water intake x3, at engagement)", &set.sodium_load);
            print_course("long course untreated (−1500 mL, 12 h)", &set.long_course.untreated);
            print_course(
                "long course crystalloid (−1500 mL + 1 L bolus, 12 h)",
                &set.long_course.crystalloid,
            );
            for line in evaluate_hormones(&params, &set) {
                println!(
                    "  {:<52} {:>9.2} -> {:>9.2}  expected {:<8} {}",
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
            println!("water load   trace hash: {:#018x}", set.water_load.trace_hash);
            println!("water control trace hash: {:#018x}", set.water_control.trace_hash);
            println!("deprivation  trace hash: {:#018x}", set.deprivation.trace_hash);
            println!("sodium load  trace hash: {:#018x}", set.sodium_load.trace_hash);
            println!(
                "long course untreated   trace hash: {:#018x}",
                set.long_course.untreated.trace_hash
            );
            println!(
                "long course crystalloid trace hash: {:#018x}",
                set.long_course.crystalloid.trace_hash
            );
            ExitCode::SUCCESS
        }
        Some("run") if args.get(2).map(|s| s.as_str()) == Some("longrest") => {
            let long = run_long_rest(&params);
            let mut ok = true;
            print_long_rest(&params, &long, &mut ok);
            let _ = ok;
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
                    eprintln!("usage: run resting|hemorrhage|infusion|hemorrhage1500|refill|course|longrest|hormones");
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
            eprintln!("usage: anatomica-physiology validate | run resting|hemorrhage|infusion|hemorrhage1500|refill|course|longrest|hormones | determinism");
            ExitCode::FAILURE
        }
    }
}
