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
//! same section standalone). Milestone 47 adds the respiratory
//! resting lines to the resting table (eight ranges), a respiratory
//! section (the four respiratory arms, evaluated against their
//! parameters.json cases; the haemorrhage arm also asserts the
//! circulation trace hash's identity with the standard run and the
//! M18 HR gate on its own window), and `run respiratory`.
//! Milestone 51 adds the resting coupling-zero line, the coupled
//! shunt evaluation, and the two A/B arms (pure shunt with the
//! hypoxic drive disabled; haemorrhage with the metabolic
//! feedback armed, cross-asserted against the unarmed arm).
//! Milestone 52 adds the resting Bohr-anchor line (the effective
//! P50 at rest must be the resting P50), the Bohr evaluation of
//! the hypoventilation arm, and the Bohr A/B section: the
//! hypoventilation arm with the shift disabled, and the
//! hyperventilation (alkalosis) arm in shift-live and
//! shift-disabled forms, cross-asserted at identical states.
//! Milestone 53 adds the resting compensation-zero line (the
//! renal compensation state and its target at the resting
//! readout must be exactly zero) and the chronic A/B section:
//! the hypoventilation protocol held for five simulated days and
//! the hyperventilation protocol held for three, each in
//! compensation-live and compensation-disabled forms,
//! cross-asserted at identical PaCO2 and circulation state.
//! Milestone 58 adds the resting calcium-axis lines (through the
//! resting validation ranges: ionized/total/corrected calcium
//! and PTH, all cited normals) and the calcium section: the
//! PTH-loss arm against its disabled-axis twin (frozen readouts
//! exactly, circulation hash identical at the shared horizon),
//! the calcium-infusion arm, and the chronic vitamin-D arm —
//! each gated on the independent solver's frozen bands.

use anatomica_physiology::cases::{
    evaluate_calcium, evaluate_course, evaluate_hormones, evaluate_perturbation, evaluate_refill,
    evaluate_respiratory, evaluate_resting, run_calcium_set, run_case, run_course_arm,
    run_hormone_set, run_long_rest, run_refill_observation, run_respiratory_case, CaseKind,
    CourseArm, CourseOutcome, CourseSet, HormoneArmOutcome, LongRestOutcome, RespCaseKind,
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

    let mut hemorrhage_750_hash: Option<u64> = None;
    for (kind, id, title) in [
        (CaseKind::Hemorrhage750, "hemorrhage_750", "HAEMORRHAGE -750 mL"),
        (CaseKind::Infusion1000, "infusion_1000", "VOLUME INFUSION +1000 mL"),
        (CaseKind::Hemorrhage1500, "hemorrhage_1500", "HAEMORRHAGE -1500 mL"),
    ] {
        println!("\n=== {title} — directional + magnitude expectations ===");
        let outcome = run_case(params, kind);
        if id == "hemorrhage_750" {
            // Kept for the Milestone 47 haemorrhage arm's
            // circulation-hash identity assertion below.
            hemorrhage_750_hash = Some(outcome.trace_hash);
        }
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

    // ---------------------------------------------------------------
    // Milestone 47: the respiratory module. Its resting gates are
    // the eight respiratory ranges in the resting table above (read
    // from the resting outcome's respiratory readout). Below: the
    // reported-only extraction line, the four respiratory arms, and
    // — for the haemorrhage arm — the circulation-hash identity with
    // the standard haemorrhage run above and the Milestone 18 hard
    // gate evaluated on this run's own standard window.
    // ---------------------------------------------------------------
    println!("\n=== RESPIRATORY MODULE (Milestone 47) ===");
    let mut resp_outcomes: Vec<(anatomica_physiology::cases::RespCaseKind, anatomica_physiology::cases::RespOutcome)> = Vec::new();
    {
        let r = &resting.resp_post;
        println!(
            "  resting detail: PAO2 {:.1} mmHg  A-a {:.1} mmHg  CvO2 {:.2} mL/dL  Hb {:.2} g/dL  HCO3 {:.2} mEq/L  RR {:.1} /min",
            r.alveolar_po2, r.aa_gradient, r.cvo2, r.hemoglobin, r.bicarbonate, r.resp_rate
        );
        // Milestone 51: the couplings at the resting equilibrium —
        // the hypoxic drive term must be numerically zero (it is
        // zero by construction at the captured operating point;
        // the residual is the sensor's beat noise, asserted here
        // against a 0.05 L/min bound, two orders below any gate).
        let drive_ok = resting.resp_post.hypoxic_drive.abs() < 0.05;
        if !drive_ok {
            ok = false;
        }
        println!(
            "  Milestone 51 couplings at rest: sensed PaO2 {:.2} mmHg  hypoxic drive term {:.4} L/min (criterion < 0.05 — zero at the operating point) {}",
            r.sensed_pao2,
            r.hypoxic_drive,
            if drive_ok { "PASS" } else { "FAIL" }
        );
        println!(
            "  resting oxygen extraction ratio = {:.3}   (reported: consulted bands S56 0.20-0.30 and S61 0.22-0.32; the engine's cardiac output rests at the low end of its band, so the ratio rests at the cited bands' upper region by the Fick identity — MILESTONE-47.md)",
            r.o2er
        );
        // Milestone 52: the Bohr anchor at the resting equilibrium —
        // the effective P50 at the resting readout must be the
        // resting P50 (the anchored multiplier is exactly 1 at the
        // resting pH by construction; the residual is whatever
        // microscopic state drift the resting protocol carries,
        // asserted here two orders below any gate's sensitivity).
        let p50_rest = params.f64("hill_p50_mmhg");
        let anchor_ok = (r.p50_eff - p50_rest).abs() < 0.01;
        if !anchor_ok {
            ok = false;
        }
        println!(
            "  Milestone 52 Bohr anchor at rest: effective P50 {:.4} mmHg vs resting P50 {:.2} mmHg at pH {:.4} (criterion |delta| < 0.01 — exactly 1.0x at the resting pH by construction) {}",
            r.p50_eff,
            p50_rest,
            r.ph,
            if anchor_ok { "PASS" } else { "FAIL" }
        );
        // Milestone 53: the renal compensation state at the resting
        // equilibrium — the state and its target must both be
        // numerically zero (the state is initialised at 0.0 and its
        // target at the resting PaCO2 is 0.0 by construction; the
        // residual is whatever microscopic PaCO2 drift the resting
        // protocol carries through the target's 0.3-per-mmHg slope,
        // asserted here far below any gate's sensitivity).
        let comp_ok = r.hco3_comp.abs() < 0.01;
        if !comp_ok {
            ok = false;
        }
        println!(
            "  Milestone 53 renal compensation at rest: state {:+.4} mEq/L (criterion |state| < 0.01 — zero at the resting equilibrium by construction) {}",
            r.hco3_comp,
            if comp_ok { "PASS" } else { "FAIL" }
        );
    }
    for (kind, id, title) in [
        (RespCaseKind::Hypoventilation, "hypoventilation_halved", "HYPOVENTILATION — RATE HELD AT 6 /min"),
        (RespCaseKind::Shunt, "shunt_20pct", "SHUNT — VENOUS ADMIXTURE 0.20"),
        (RespCaseKind::Metabolic, "metabolic_doubled", "METABOLIC RATE DOUBLED"),
        (RespCaseKind::HemorrhageResp, "hemorrhage_750_respiratory", "HAEMORRHAGE -750 mL, MODULE LIVE"),
    ] {
        println!("\n=== RESPIRATORY ARM: {title} ===");
        let outcome = run_respiratory_case(params, kind);
        for line in evaluate_respiratory(params, id, &outcome) {
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
        // Milestone 51: the drive-live shunt is evaluated against
        // its coupled case as well as its legacy case.
        if kind == RespCaseKind::Shunt {
            for line in evaluate_respiratory(params, "shunt_hypoxic_coupled", &outcome) {
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
                    "  [coupled] {:<21} {:>9.2} -> {:>9.2}  (delta {:+.2})  expected {:<8}{} [{}] {}",
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
        }
        // Milestone 52: the hypoventilation arm is evaluated
        // against its Bohr case as well as its legacy case — the
        // acidotic state is where the shift is largest.
        if kind == RespCaseKind::Hypoventilation {
            for line in evaluate_respiratory(params, "hypoventilation_bohr", &outcome) {
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
                    "  [bohr] {:<24} {:>9.2} -> {:>9.2}  (delta {:+.2})  expected {:<8}{} [{}] {}",
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
        }
        println!(
            "  post readout: PaCO2 {:.1} mmHg  PaO2 {:.1}  pH {:.3}  SaO2 {:.3}  CaO2 {:.2} mL/dL  DO2 {:.0} mL/min  VE {:.2} L/min  VA {:.2} L/min  P50eff {:.2} mmHg",
            outcome.post.paco2,
            outcome.post.pao2,
            outcome.post.ph,
            outcome.post.sao2,
            outcome.post.cao2,
            outcome.post.do2,
            outcome.post.minute_ventilation,
            outcome.post.alveolar_ventilation,
            outcome.post.p50_eff
        );
        println!(
            "  circulation trace hash at the standard endpoint (tick 12000): {:#018x}   respiratory trace hash: {:#018x}",
            outcome.hash_at_standard_end, outcome.resp_hash
        );
        if kind == RespCaseKind::HemorrhageResp {
            let std = hemorrhage_750_hash.expect("hemorrhage_750 ran above");
            let same = outcome.hash_at_standard_end == std;
            if !same {
                ok = false;
            }
            println!(
                "  circulation hash identity with the standard haemorrhage_750 run: {}",
                if same { "HOLDS" } else { "BROKEN" }
            );
            let hr_ok = (100.0..=120.0).contains(&outcome.window_post.hr);
            if !hr_ok {
                ok = false;
            }
            println!(
                "  standard-window HR {:.1} in the ATLS Class II band [100, 120] (the M18 gate, on the module-live run): {}",
                outcome.window_post.hr,
                if hr_ok { "PASS" } else { "FAIL" }
            );
        }
        println!("  causal chain (event log):");
        for entry in &outcome.causal_chain {
            println!("    {entry}");
        }
        resp_outcomes.push((kind, outcome));
    }

    // ---------------------------------------------------------------
    // Milestone 51: the coupled A/B arms. The pure shunt (drive
    // disabled) must reproduce the Milestone 47 picture on the
    // legacy case; the feedback-armed haemorrhage must beat the
    // unarmed arm on delivery and heart rate at the same mark (the
    // cited compensatory direction, S70/S71) while its own
    // standard-window heart rate stays inside the Milestone 18
    // ATLS Class II band.
    // ---------------------------------------------------------------
    println!("\n=== RESPIRATORY ARM: SHUNT — HYPOXIC DRIVE DISABLED (PURE, M47 PICTURE) ===");
    let pure = run_respiratory_case(params, RespCaseKind::ShuntPure);
    for line in evaluate_respiratory(params, "shunt_20pct", &pure) {
        if !line.pass && !line.soft {
            ok = false;
        }
        let verdict = if line.pass { "PASS" } else { "FAIL" };
        println!(
            "  {:<28} {:>9.2} -> {:>9.2}  (delta {:+.2})  expected {:<8} [{}] {}",
            line.output, line.baseline, line.post, line.delta, line.expected, line.source, verdict
        );
    }
    println!(
        "  post readout: PaCO2 {:.1} mmHg  PaO2 {:.1}  VE {:.2} L/min  hypoxic drive {:.3} L/min (disabled)",
        pure.post.paco2, pure.post.pao2, pure.post.minute_ventilation, pure.post.hypoxic_drive
    );
    if let Some((_, coupled)) = resp_outcomes.iter().find(|(k, _)| *k == RespCaseKind::Shunt) {
        println!(
            "  A/B at +30 min: PaCO2 pure {:.2} -> coupled {:.2} mmHg (drive buys CO2 elimination); VE pure {:.2} -> coupled {:.2} L/min; PaO2 pure {:.1} -> coupled {:.1} mmHg (oxygenation unrepaired at fixed admixture)",
            pure.post.paco2, coupled.post.paco2, pure.post.minute_ventilation,
            coupled.post.minute_ventilation, pure.post.pao2, coupled.post.pao2
        );
    }

    println!("\n=== RESPIRATORY ARM: HAEMORRHAGE -750 mL, METABOLIC FEEDBACK ARMED (Milestone 51) ===");
    let armed = run_respiratory_case(params, RespCaseKind::HemorrhageFeedback);
    for line in evaluate_respiratory(params, "hemorrhage_750_metabolic_feedback", &armed) {
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
            line.output, line.baseline, line.post, line.delta, line.expected, band, line.source,
            verdict
        );
    }
    println!(
        "  post readout: PaCO2 {:.1} mmHg  PaO2 {:.1}  DO2 {:.0} mL/min  final-window HR {:.1} /min  standard-window HR {:.1} /min",
        armed.post.paco2, armed.post.pao2, armed.post.do2, armed.final_window.hr, armed.window_post.hr
    );
    if let Some((_, unarmed)) = resp_outcomes
        .iter()
        .find(|(k, _)| *k == RespCaseKind::HemorrhageResp)
    {
        let do2_ok = armed.post.do2 > unarmed.post.do2;
        let hr_ok = armed.final_window.hr > unarmed.final_window.hr;
        if !do2_ok || !hr_ok {
            ok = false;
        }
        println!(
            "  cross-run vs the unarmed arm at +30 min: DO2 {:.0} -> {:.0} mL/min (must rise) {}; final-window HR {:.1} -> {:.1} /min (must rise) {}",
            unarmed.post.do2,
            armed.post.do2,
            if do2_ok { "PASS" } else { "FAIL" },
            unarmed.final_window.hr,
            armed.final_window.hr,
            if hr_ok { "PASS" } else { "FAIL" }
        );
        let std_hr_ok = (100.0..=120.0).contains(&armed.window_post.hr);
        if !std_hr_ok {
            ok = false;
        }
        println!(
            "  armed standard-window HR {:.1} in the ATLS Class II band [100, 120] (the M18 gate, feedback live): {}",
            armed.window_post.hr,
            if std_hr_ok { "PASS" } else { "FAIL" }
        );
    }
    println!("  causal chain (event log):");
    for entry in &armed.causal_chain {
        println!("    {entry}");
    }

    // ---------------------------------------------------------------
    // Milestone 52: the Bohr A/B arms. The hypoventilation protocol
    // run with the shift disabled must reproduce the Milestone 47
    // fixed-curve readouts at the IDENTICAL state (the override
    // suspends every path by which the shift could touch the CO2
    // store, so PaCO2, pH and both trace hashes are asserted
    // identical across the pair), and the live-vs-disabled content
    // and saturation deltas must land on the amounts the cited
    // Bohr relation computes at that state. The hyperventilation
    // (alkalosis) pair carries the same assertions in the left-
    // shift direction.
    // ---------------------------------------------------------------
    println!("\n=== RESPIRATORY ARM: HYPOVENTILATION — BOHR SHIFT DISABLED (FIXED CURVE, M47 PICTURE) ===");
    let hypo_pure = run_respiratory_case(params, RespCaseKind::HypoventilationPure);
    for line in evaluate_respiratory(params, "hypoventilation_bohr_pure", &hypo_pure) {
        if !line.pass && !line.soft {
            ok = false;
        }
        let verdict = if line.pass { "PASS" } else { "FAIL" };
        println!(
            "  {:<28} {:>9.2} -> {:>9.2}  (delta {:+.2})  expected {:<8} [{}] {}",
            line.output, line.baseline, line.post, line.delta, line.expected, line.source, verdict
        );
    }
    for line in evaluate_respiratory(params, "hypoventilation_halved", &hypo_pure) {
        if !line.pass && !line.soft {
            ok = false;
        }
        let verdict = if line.pass { "PASS" } else { "FAIL" };
        println!(
            "  [legacy] {:<21} {:>9.2} -> {:>9.2}  (delta {:+.2})  expected {:<8} [{}] {}",
            line.output, line.baseline, line.post, line.delta, line.expected, line.source, verdict
        );
    }
    println!(
        "  post readout: PaCO2 {:.1} mmHg  PaO2 {:.1}  pH {:.3}  SaO2 {:.3}  CaO2 {:.2} mL/dL  DO2 {:.0} mL/min  P50eff {:.2} mmHg (shift disabled)",
        hypo_pure.post.paco2, hypo_pure.post.pao2, hypo_pure.post.ph, hypo_pure.post.sao2,
        hypo_pure.post.cao2, hypo_pure.post.do2, hypo_pure.post.p50_eff
    );
    if let Some((_, live)) = resp_outcomes
        .iter()
        .find(|(k, _)| *k == RespCaseKind::Hypoventilation)
    {
        let state_ok = (live.post.paco2 - hypo_pure.post.paco2).abs() < 1e-9
            && (live.post.ph - hypo_pure.post.ph).abs() < 1e-9
            && live.resp_hash == hypo_pure.resp_hash
            && live.hash_at_standard_end == hypo_pure.hash_at_standard_end;
        if !state_ok {
            ok = false;
        }
        println!(
            "  A/B state identity: PaCO2 {:.4} vs {:.4} mmHg, resp hash {:#018x} vs {:#018x}, circulation hash identical: {}",
            live.post.paco2,
            hypo_pure.post.paco2,
            live.resp_hash,
            hypo_pure.resp_hash,
            if state_ok { "HOLDS" } else { "BROKEN" }
        );
        let d_cao2 = hypo_pure.post.cao2 - live.post.cao2;
        let d_sao2 = hypo_pure.post.sao2 - live.post.sao2;
        let d_do2 = hypo_pure.post.do2 - live.post.do2;
        let deltas_ok = (1.5..=2.8).contains(&d_cao2)
            && (0.07..=0.14).contains(&d_sao2)
            && (60.0..=120.0).contains(&d_do2);
        if !deltas_ok {
            ok = false;
        }
        println!(
            "  A/B shift deltas at the identical state (right shift, acidosis): CaO2 falls {:.2} mL/dL (computed ~2.1, band [1.5, 2.8]) {}; SaO2 falls {:.3} (computed ~0.104, band [0.07, 0.14]) {}; DO2 falls {:.0} mL/min (computed ~88, band [60, 120]) {}",
            d_cao2,
            if (1.5..=2.8).contains(&d_cao2) { "PASS" } else { "FAIL" },
            d_sao2,
            if (0.07..=0.14).contains(&d_sao2) { "PASS" } else { "FAIL" },
            d_do2,
            if (60.0..=120.0).contains(&d_do2) { "PASS" } else { "FAIL" }
        );
    }

    println!("\n=== RESPIRATORY ARM: HYPERVENTILATION — RATE HELD AT 24 /min (ALKALOSIS, BOHR LIVE) ===");
    let hyper = run_respiratory_case(params, RespCaseKind::Hyperventilation);
    for line in evaluate_respiratory(params, "hyperventilation_alkalosis", &hyper) {
        if !line.pass && !line.soft {
            ok = false;
        }
        let band = match line.magnitude_range {
            Some([lo, hi]) => format!("  band [{lo:.1} .. {hi:.1}]"),
            None => String::new(),
        };
        let verdict = if line.pass { "PASS" } else { "FAIL" };
        println!(
            "  {:<28} {:>9.2} -> {:>9.2}  (delta {:+.2})  expected {:<8}{} [{}] {}",
            line.output, line.baseline, line.post, line.delta, line.expected, band, line.source,
            verdict
        );
    }
    println!(
        "  post readout: PaCO2 {:.1} mmHg  PaO2 {:.1}  pH {:.3}  SaO2 {:.3}  CaO2 {:.2} mL/dL  DO2 {:.0} mL/min  P50eff {:.2} mmHg",
        hyper.post.paco2, hyper.post.pao2, hyper.post.ph, hyper.post.sao2, hyper.post.cao2,
        hyper.post.do2, hyper.post.p50_eff
    );

    println!("\n=== RESPIRATORY ARM: HYPERVENTILATION — BOHR SHIFT DISABLED (FIXED CURVE) ===");
    let hyper_pure = run_respiratory_case(params, RespCaseKind::HyperventilationPure);
    for line in evaluate_respiratory(params, "hyperventilation_bohr_pure", &hyper_pure) {
        if !line.pass && !line.soft {
            ok = false;
        }
        let verdict = if line.pass { "PASS" } else { "FAIL" };
        println!(
            "  {:<28} {:>9.2} -> {:>9.2}  (delta {:+.2})  expected {:<8} [{}] {}",
            line.output, line.baseline, line.post, line.delta, line.expected, line.source, verdict
        );
    }
    println!(
        "  post readout: PaCO2 {:.1} mmHg  PaO2 {:.1}  pH {:.3}  SaO2 {:.3}  CaO2 {:.2} mL/dL  DO2 {:.0} mL/min  P50eff {:.2} mmHg (shift disabled)",
        hyper_pure.post.paco2, hyper_pure.post.pao2, hyper_pure.post.ph, hyper_pure.post.sao2,
        hyper_pure.post.cao2, hyper_pure.post.do2, hyper_pure.post.p50_eff
    );
    {
        let state_ok = (hyper.post.paco2 - hyper_pure.post.paco2).abs() < 1e-9
            && (hyper.post.ph - hyper_pure.post.ph).abs() < 1e-9
            && hyper.resp_hash == hyper_pure.resp_hash
            && hyper.hash_at_standard_end == hyper_pure.hash_at_standard_end;
        if !state_ok {
            ok = false;
        }
        println!(
            "  A/B state identity: PaCO2 {:.4} vs {:.4} mmHg, resp hash {:#018x} vs {:#018x}, circulation hash identical: {}",
            hyper.post.paco2,
            hyper_pure.post.paco2,
            hyper.resp_hash,
            hyper_pure.resp_hash,
            if state_ok { "HOLDS" } else { "BROKEN" }
        );
        let d_cao2 = hyper.post.cao2 - hyper_pure.post.cao2;
        let d_sao2 = hyper.post.sao2 - hyper_pure.post.sao2;
        let d_pao2 = hyper_pure.post.pao2 - hyper.post.pao2;
        let deltas_ok = (0.05..=0.30).contains(&d_cao2)
            && (0.004..=0.013).contains(&d_sao2)
            && (3.0..=10.0).contains(&d_pao2);
        if !deltas_ok {
            ok = false;
        }
        println!(
            "  A/B shift deltas at the identical state (left shift, alkalosis): CaO2 rises {:.2} mL/dL (computed ~0.14, band [0.05, 0.30]) {}; SaO2 rises {:.3} (computed ~0.008, band [0.004, 0.013]) {}; PaO2 at the arm's content FALLS {:.1} mmHg (computed ~6.8, band [3, 10] — the same content sits at a lower PO2 on the left-shifted curve) {}",
            d_cao2,
            if (0.05..=0.30).contains(&d_cao2) { "PASS" } else { "FAIL" },
            d_sao2,
            if (0.004..=0.013).contains(&d_sao2) { "PASS" } else { "FAIL" },
            d_pao2,
            if (3.0..=10.0).contains(&d_pao2) { "PASS" } else { "FAIL" }
        );
    }
    println!("  causal chain (event log):");
    for entry in &hyper.causal_chain {
        println!("    {entry}");
    }

    // ---------------------------------------------------------------
    // Milestone 53: the chronic (renal) compensation arms. The
    // hypoventilation protocol held for five simulated days and
    // the hyperventilation protocol held for three (the long-
    // course precedent: the run continues past the standard
    // endpoint to the arm's mark), each in compensation-live and
    // compensation-disabled forms. Across each pair the PaCO2 and
    // the circulation at the standard endpoint must be identical
    // (the state is respiratory-side only and the override holds
    // the rate: nothing in the state can move either); the
    // respiratory hashes must DIFFER (the state folds into that
    // chain — the one hash that is supposed to move); and the
    // live-vs-disabled bicarbonate and pH deltas must land on the
    // amounts the independent solver computes (work/m53/
    // predict.py). The Bohr anchor is asserted unmoved by
    // construction in the test suite (Model::ph_rest is a
    // construction constant; the compensated pH moves, the anchor
    // does not).
    // ---------------------------------------------------------------
    println!("\n=== RESPIRATORY ARM: SUSTAINED HYPOVENTILATION — FIVE DAYS, RENAL COMPENSATION LIVE (M53) ===");
    let chronic_hypo = run_respiratory_case(params, RespCaseKind::ChronicHypoventilation);
    for line in evaluate_respiratory(params, "chronic_hypoventilation_compensated", &chronic_hypo) {
        if !line.pass && !line.soft {
            ok = false;
        }
        let band = match line.magnitude_range {
            Some([lo, hi]) => format!("  band [{lo:.1} .. {hi:.1}]"),
            None => String::new(),
        };
        let verdict = if line.pass { "PASS" } else { "FAIL" };
        println!(
            "  {:<28} {:>9.2} -> {:>9.2}  (delta {:+.2})  expected {:<8}{} [{}] {}",
            line.output, line.baseline, line.post, line.delta, line.expected, band, line.source,
            verdict
        );
    }
    println!(
        "  post readout (+5 d): PaCO2 {:.1} mmHg  PaO2 {:.1}  pH {:.3}  HCO3 total {:.2} (acute {:.2} + renal {:+.2}) mEq/L  SaO2 {:.3}  CaO2 {:.2} mL/dL  DO2 {:.0} mL/min  P50eff {:.2} mmHg",
        chronic_hypo.post.paco2, chronic_hypo.post.pao2, chronic_hypo.post.ph,
        chronic_hypo.post.bicarbonate, chronic_hypo.post.bicarbonate - chronic_hypo.post.hco3_comp,
        chronic_hypo.post.hco3_comp, chronic_hypo.post.sao2, chronic_hypo.post.cao2,
        chronic_hypo.post.do2, chronic_hypo.post.p50_eff
    );
    println!(
        "  circulation trace hash at the standard endpoint (tick 12000): {:#018x}   respiratory trace hash: {:#018x}",
        chronic_hypo.hash_at_standard_end, chronic_hypo.resp_hash
    );

    println!("\n=== RESPIRATORY ARM: SUSTAINED HYPOVENTILATION — FIVE DAYS, RENAL COMPENSATION DISABLED (ACUTE-ONLY, M53) ===");
    let chronic_hypo_pure = run_respiratory_case(params, RespCaseKind::ChronicHypoventilationPure);
    for line in evaluate_respiratory(params, "chronic_hypoventilation_uncompensated", &chronic_hypo_pure) {
        if !line.pass && !line.soft {
            ok = false;
        }
        let verdict = if line.pass { "PASS" } else { "FAIL" };
        println!(
            "  {:<28} {:>9.2} -> {:>9.2}  (delta {:+.2})  expected {:<8} [{}] {}",
            line.output, line.baseline, line.post, line.delta, line.expected, line.source, verdict
        );
    }
    println!(
        "  post readout (+5 d): PaCO2 {:.1} mmHg  PaO2 {:.1}  pH {:.3}  HCO3 total {:.2} (renal {:+.2}) mEq/L  P50eff {:.2} mmHg (compensation disabled)",
        chronic_hypo_pure.post.paco2, chronic_hypo_pure.post.pao2, chronic_hypo_pure.post.ph,
        chronic_hypo_pure.post.bicarbonate, chronic_hypo_pure.post.hco3_comp,
        chronic_hypo_pure.post.p50_eff
    );
    {
        let state_ok = (chronic_hypo.post.paco2 - chronic_hypo_pure.post.paco2).abs() < 1e-9
            && chronic_hypo.hash_at_standard_end == chronic_hypo_pure.hash_at_standard_end
            && chronic_hypo_pure.post.hco3_comp == 0.0
            && chronic_hypo.resp_hash != chronic_hypo_pure.resp_hash;
        if !state_ok {
            ok = false;
        }
        println!(
            "  A/B state identity: PaCO2 {:.4} vs {:.4} mmHg, circulation hash at tick 12000 identical, disabled state exactly 0.0, resp hashes differ (the state folds there): {}",
            chronic_hypo.post.paco2,
            chronic_hypo_pure.post.paco2,
            if state_ok { "HOLDS" } else { "BROKEN" }
        );
        let d_hco3 = chronic_hypo.post.bicarbonate - chronic_hypo_pure.post.bicarbonate;
        let d_ph = chronic_hypo.post.ph - chronic_hypo_pure.post.ph;
        let d_p50 = chronic_hypo_pure.post.p50_eff - chronic_hypo.post.p50_eff;
        let deltas_ok = (10.5..=14.0).contains(&d_hco3)
            && (0.12..=0.19).contains(&d_ph)
            && (4.0..=7.0).contains(&d_p50);
        if !deltas_ok {
            ok = false;
        }
        println!(
            "  A/B compensation deltas at +5 d (acidosis): bicarbonate {:+.2} mEq/L (computed +12.24, band [10.5, 14.0]) {}; pH {:+.3} (computed +0.157, band [0.12, 0.19]) {}; P50eff falls {:.2} mmHg as the pH recovers (computed ~5.5, band [4.0, 7.0]) {}",
            d_hco3,
            if (10.5..=14.0).contains(&d_hco3) { "PASS" } else { "FAIL" },
            d_ph,
            if (0.12..=0.19).contains(&d_ph) { "PASS" } else { "FAIL" },
            d_p50,
            if (4.0..=7.0).contains(&d_p50) { "PASS" } else { "FAIL" }
        );
    }

    println!("\n=== RESPIRATORY ARM: SUSTAINED HYPERVENTILATION — THREE DAYS, RENAL COMPENSATION LIVE (M53) ===");
    let chronic_hyper = run_respiratory_case(params, RespCaseKind::ChronicHyperventilation);
    for line in evaluate_respiratory(params, "chronic_hyperventilation_compensated", &chronic_hyper) {
        if !line.pass && !line.soft {
            ok = false;
        }
        let band = match line.magnitude_range {
            Some([lo, hi]) => format!("  band [{lo:.1} .. {hi:.1}]"),
            None => String::new(),
        };
        let verdict = if line.pass { "PASS" } else { "FAIL" };
        println!(
            "  {:<28} {:>9.2} -> {:>9.2}  (delta {:+.2})  expected {:<8}{} [{}] {}",
            line.output, line.baseline, line.post, line.delta, line.expected, band, line.source,
            verdict
        );
    }
    println!(
        "  post readout (+3 d): PaCO2 {:.1} mmHg  PaO2 {:.1}  pH {:.3}  HCO3 total {:.2} (acute {:.2} + renal {:+.2}) mEq/L  SaO2 {:.3}  CaO2 {:.2} mL/dL  DO2 {:.0} mL/min  P50eff {:.2} mmHg",
        chronic_hyper.post.paco2, chronic_hyper.post.pao2, chronic_hyper.post.ph,
        chronic_hyper.post.bicarbonate, chronic_hyper.post.bicarbonate - chronic_hyper.post.hco3_comp,
        chronic_hyper.post.hco3_comp, chronic_hyper.post.sao2, chronic_hyper.post.cao2,
        chronic_hyper.post.do2, chronic_hyper.post.p50_eff
    );
    println!(
        "  circulation trace hash at the standard endpoint (tick 12000): {:#018x}   respiratory trace hash: {:#018x}",
        chronic_hyper.hash_at_standard_end, chronic_hyper.resp_hash
    );

    println!("\n=== RESPIRATORY ARM: SUSTAINED HYPERVENTILATION — THREE DAYS, RENAL COMPENSATION DISABLED (ACUTE-ONLY, M53) ===");
    let chronic_hyper_pure = run_respiratory_case(params, RespCaseKind::ChronicHyperventilationPure);
    for line in evaluate_respiratory(params, "chronic_hyperventilation_uncompensated", &chronic_hyper_pure) {
        if !line.pass && !line.soft {
            ok = false;
        }
        let verdict = if line.pass { "PASS" } else { "FAIL" };
        println!(
            "  {:<28} {:>9.2} -> {:>9.2}  (delta {:+.2})  expected {:<8} [{}] {}",
            line.output, line.baseline, line.post, line.delta, line.expected, line.source, verdict
        );
    }
    println!(
        "  post readout (+3 d): PaCO2 {:.1} mmHg  PaO2 {:.1}  pH {:.3}  HCO3 total {:.2} (renal {:+.2}) mEq/L  P50eff {:.2} mmHg (compensation disabled)",
        chronic_hyper_pure.post.paco2, chronic_hyper_pure.post.pao2, chronic_hyper_pure.post.ph,
        chronic_hyper_pure.post.bicarbonate, chronic_hyper_pure.post.hco3_comp,
        chronic_hyper_pure.post.p50_eff
    );
    {
        let state_ok = (chronic_hyper.post.paco2 - chronic_hyper_pure.post.paco2).abs() < 1e-9
            && chronic_hyper.hash_at_standard_end == chronic_hyper_pure.hash_at_standard_end
            && chronic_hyper_pure.post.hco3_comp == 0.0
            && chronic_hyper.resp_hash != chronic_hyper_pure.resp_hash;
        if !state_ok {
            ok = false;
        }
        println!(
            "  A/B state identity: PaCO2 {:.4} vs {:.4} mmHg, circulation hash at tick 12000 identical, disabled state exactly 0.0, resp hashes differ (the state folds there): {}",
            chronic_hyper.post.paco2,
            chronic_hyper_pure.post.paco2,
            if state_ok { "HOLDS" } else { "BROKEN" }
        );
        let d_hco3 = chronic_hyper_pure.post.bicarbonate - chronic_hyper.post.bicarbonate;
        let d_ph = chronic_hyper_pure.post.ph - chronic_hyper.post.ph;
        let d_p50 = chronic_hyper.post.p50_eff - chronic_hyper_pure.post.p50_eff;
        let deltas_ok = (4.8..=7.0).contains(&d_hco3)
            && (0.12..=0.19).contains(&d_ph)
            && (2.8..=4.8).contains(&d_p50);
        if !deltas_ok {
            ok = false;
        }
        println!(
            "  A/B compensation deltas at +3 d (alkalosis): bicarbonate falls {:.2} mEq/L with compensation (computed 5.86, band [4.8, 7.0]) {}; pH falls {:.3} (computed 0.152, band [0.12, 0.19]) {}; P50eff rises {:.2} mmHg as the pH recovers (computed ~3.8, band [2.8, 4.8]) {}",
            d_hco3,
            if (4.8..=7.0).contains(&d_hco3) { "PASS" } else { "FAIL" },
            d_ph,
            if (0.12..=0.19).contains(&d_ph) { "PASS" } else { "FAIL" },
            d_p50,
            if (2.8..=4.8).contains(&d_p50) { "PASS" } else { "FAIL" }
        );
    }
    println!("  causal chain (event log):");
    for entry in &chronic_hyper.causal_chain {
        println!("    {entry}");
    }

    // ---------------------------------------------------------------
    // Milestone 58: the calcium–PTH axis arms. Three perturbation
    // cases gate on the independent solver's frozen bands
    // (work/m58/predict.py, computed from parameters.json
    // constants before the engine ran): PTH loss after
    // thyroidectomy (the Case #8 picture — secretion capacity
    // 0.09, the remnant her measured POD2 PTH implies),
    // calcium-gluconate infusion, and chronic vitamin-D
    // deficiency. The PTH-loss arm runs against its disabled-axis
    // twin at the identical horizon: the twin's five STATES must
    // sit bit-exactly on the resting equilibrium at every mark
    // (frozen derivatives — its concentration readouts still
    // move with the circulation's volume drift, which the A/B
    // line prints), the two circulation trace hashes must be
    // IDENTICAL (the axis never enters a circulation derivative),
    // and the respiratory hashes must DIFFER (the axis states
    // fold there — the one hash family that is supposed to move).
    // ---------------------------------------------------------------
    println!("\n=== CALCIUM–PTH AXIS (Milestone 58) ===");
    let calcium = run_calcium_set(params);
    {
        let r = &calcium.pth_loss.resting;
        println!(
            "  resting axis at engagement: ionized {:.4} mmol/L  total {:.3}  corrected {:.3}  PTH {:.2} pg/mL  urine Ca {:.2} mmol/day  bone/form/vitD states {:.3}/{:.3}/{:.3}",
            r.ionized_calcium, r.total_calcium, r.corrected_calcium, r.pth,
            r.urine_calcium_mmol_day, r.bone_resorption_state, r.bone_formation_state,
            r.vitamin_d_state
        );
    }
    for (arm, title) in [
        (&calcium.pth_loss, "PTH LOSS — secretion capacity 9% (post-thyroidectomy)"),
        (&calcium.pth_loss_pure, "PTH LOSS — axis DISABLED (A/B control)"),
        (&calcium.infusion, "CALCIUM INFUSION — 4.5 mmol over 20 min"),
        (&calcium.vitamin_d, "VITAMIN D DEFICIENCY — effect target scale 0.40"),
    ] {
        println!("  {title}:");
        for s in &arm.samples {
            println!(
                "    +{:>7.0} min: ionized {:.4} mmol/L  total {:.3}  corrected {:.3}  PTH {:6.2} pg/mL  bone {:.3}  form {:.3}  vitD {:.3}  urine Ca {:.2} mmol/day",
                s.minutes, s.ionized_calcium, s.total_calcium, s.corrected_calcium, s.pth,
                s.bone_resorption_state, s.bone_formation_state, s.vitamin_d_state,
                s.urine_calcium_mmol_day
            );
        }
        println!(
            "    circulation trace hash: {:#018x}   respiratory trace hash: {:#018x}   conservation error: {:.2e} mL",
            arm.trace_hash, arm.resp_hash, arm.conservation_error_ml
        );
    }
    for line in evaluate_calcium(params, &calcium) {
        if !line.pass && !line.soft {
            ok = false;
        }
        let band = match line.magnitude_range {
            Some([lo, hi]) => format!("  band [{lo:.2} .. {hi:.2}]"),
            None => String::new(),
        };
        let verdict = if line.pass { "PASS" } else { "FAIL" };
        println!(
            "  {:<52} {:>8.3} -> {:>8.3}  (delta {:+.3})  expected {:<8}{} [{}] {}",
            line.output, line.baseline, line.post, line.delta, line.expected, band, line.source,
            verdict
        );
    }
    {
        let pure = &calcium.pth_loss_pure;
        // The STATES are bit-frozen (content, PTH, the three
        // effect states — zero derivatives integrate to exactly
        // zero). The concentration READOUTS are not asserted
        // frozen: ionized calcium is the content over the live
        // extracellular volume, and the circulation's volume
        // drifts ~0.2% over a protocol day, carrying the
        // concentration with it — the drift is printed, not
        // hidden.
        let frozen = pure.samples.iter().all(|s| {
            s.content_mmol == pure.resting.content_mmol
                && s.pth == pure.resting.pth
                && s.bone_resorption_state == pure.resting.bone_resorption_state
                && s.bone_formation_state == pure.resting.bone_formation_state
                && s.vitamin_d_state == pure.resting.vitamin_d_state
        });
        let circ_ok = calcium.pth_loss.trace_hash == pure.trace_hash;
        let resp_ok = calcium.pth_loss.resp_hash != pure.resp_hash;
        if !(frozen && circ_ok && resp_ok) {
            ok = false;
        }
        let drift = pure
            .samples
            .last()
            .map(|s| s.ionized_calcium - pure.resting.ionized_calcium)
            .unwrap_or(0.0);
        println!(
            "  A/B axis identity: disabled-axis states frozen exactly at rest at every mark: {}; circulation trace hash identical to the live arm at +72 h: {}; respiratory hashes differ (the axis folds there): {}; disabled-arm ionized readout drift {:+.4} mmol/L over 72 h (extracellular-volume drift on a frozen content state)",
            if frozen { "HOLDS" } else { "BROKEN" },
            if circ_ok { "HOLDS" } else { "BROKEN" },
            if resp_ok { "HOLDS" } else { "BROKEN" },
            drift
        );
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
        Some("run") if args.get(2).map(|s| s.as_str()) == Some("respiratory") => {
            let resting = run_case(&params, CaseKind::Resting);
            let r = &resting.resp_post;
            println!(
                "resting: PaCO2 {:.1} mmHg  PAO2 {:.1}  PaO2 {:.1}  pH {:.3}  SaO2 {:.3}  CaO2 {:.2} mL/dL  CvO2 {:.2}  DO2 {:.0} mL/min  O2ER {:.3}  VE {:.2} L/min  VA {:.2} L/min  RR {:.1} /min  VO2 {:.0}  VCO2 {:.0}  Hb {:.2} g/dL  HCO3 {:.2} mEq/L  A-a {:.1} mmHg",
                r.paco2, r.alveolar_po2, r.pao2, r.ph, r.sao2, r.cao2, r.cvo2, r.do2, r.o2er,
                r.minute_ventilation, r.alveolar_ventilation, r.resp_rate, r.vo2, r.vco2,
                r.hemoglobin, r.bicarbonate, r.aa_gradient
            );
            for (kind, title) in [
                (RespCaseKind::Hypoventilation, "HYPOVENTILATION — rate held 6 /min, Bohr shift LIVE (M52)"),
                (RespCaseKind::HypoventilationPure, "HYPOVENTILATION — rate held 6 /min, Bohr shift DISABLED (M47 picture)"),
                (RespCaseKind::Hyperventilation, "HYPERVENTILATION — rate held 24 /min, Bohr shift LIVE (M52)"),
                (RespCaseKind::HyperventilationPure, "HYPERVENTILATION — rate held 24 /min, Bohr shift DISABLED"),
                (RespCaseKind::Shunt, "SHUNT — admixture 0.20, hypoxic drive LIVE (M51)"),
                (RespCaseKind::ShuntPure, "SHUNT — admixture 0.20, hypoxic drive DISABLED (M47 picture)"),
                (RespCaseKind::Metabolic, "METABOLIC DOUBLED"),
                (RespCaseKind::HemorrhageResp, "HAEMORRHAGE -750 mL, module live"),
                (RespCaseKind::HemorrhageFeedback, "HAEMORRHAGE -750 mL, metabolic feedback ARMED (M51)"),
                // Milestone 53's chronic arms are NOT listed here:
                // their multi-day horizons (five and three
                // simulated days) would push this standalone
                // listing past the case workbench's 900 s re-run
                // timeout (tools/case_check.py re-runs this
                // command for case #6). They run in `validate`,
                // whose chronic section gates them.
            ] {
                let outcome = run_respiratory_case(&params, kind);
                let (b, p) = (&outcome.baseline, &outcome.post);
                println!("\n{title}:");
                println!(
                    "  PaCO2 {:.1} -> {:.1} mmHg   PaO2 {:.1} -> {:.1}   pH {:.3} -> {:.3}   CaO2 {:.2} -> {:.2} mL/dL   DO2 {:.0} -> {:.0} mL/min",
                    b.paco2, p.paco2, b.pao2, p.pao2, b.ph, p.ph, b.cao2, p.cao2, b.do2, p.do2
                );
                println!(
                    "  VE {:.2} -> {:.2} L/min   VA {:.2} -> {:.2}   RR {:.1} -> {:.1} /min   A-a {:.1} -> {:.1} mmHg   SaO2 {:.3} -> {:.3}   P50eff {:.2} -> {:.2} mmHg",
                    b.minute_ventilation, p.minute_ventilation, b.alveolar_ventilation,
                    p.alveolar_ventilation, b.resp_rate, p.resp_rate, b.aa_gradient, p.aa_gradient,
                    b.sao2, p.sao2, b.p50_eff, p.p50_eff
                );
                println!(
                    "  HCO3 {:.2} -> {:.2} mEq/L (renal compensation {:+.2} mEq/L at the mark, M53)",
                    b.bicarbonate, p.bicarbonate, p.hco3_comp
                );
                println!(
                    "  circulation hash @ tick 12000: {:#018x}   resp hash: {:#018x}   conservation error: {:.2e} mL",
                    outcome.hash_at_standard_end, outcome.resp_hash, outcome.conservation_error_ml
                );
                for entry in &outcome.causal_chain {
                    println!("  {entry}");
                }
            }
            ExitCode::SUCCESS
        }
        Some("run") if args.get(2).map(|s| s.as_str()) == Some("calcium") => {
            // Milestone 58: the calcium arms standalone. Like the
            // respiratory listing, but the arms' horizons run to
            // simulated days (the PTH-loss and vitamin-D arms), so
            // this listing is slow by design; nothing re-runs it
            // under a timeout (the case workbench re-runs
            // `run respiratory`, not this command).
            let set = run_calcium_set(&params);
            for (arm, title) in [
                (&set.pth_loss, "PTH LOSS — secretion capacity 9% (post-thyroidectomy)"),
                (&set.pth_loss_pure, "PTH LOSS — axis DISABLED (A/B control)"),
                (&set.infusion, "CALCIUM INFUSION — 4.5 mmol over 20 min"),
                (&set.vitamin_d, "VITAMIN D DEFICIENCY — effect target scale 0.40"),
            ] {
                println!("\n{title}:");
                let r = &arm.resting;
                println!(
                    "  rest: ionized {:.4} mmol/L  total {:.3}  corrected {:.3}  PTH {:.2} pg/mL",
                    r.ionized_calcium, r.total_calcium, r.corrected_calcium, r.pth
                );
                for s in &arm.samples {
                    println!(
                        "  +{:>7.0} min: ionized {:.4} mmol/L  total {:.3}  corrected {:.3}  PTH {:6.2} pg/mL  bone {:.3}  form {:.3}  vitD {:.3}  urine Ca {:.2} mmol/day",
                        s.minutes, s.ionized_calcium, s.total_calcium, s.corrected_calcium,
                        s.pth, s.bone_resorption_state, s.bone_formation_state, s.vitamin_d_state,
                        s.urine_calcium_mmol_day
                    );
                }
                println!(
                    "  circulation trace hash: {:#018x}   respiratory trace hash: {:#018x}",
                    arm.trace_hash, arm.resp_hash
                );
            }
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
                    eprintln!("usage: run resting|hemorrhage|infusion|hemorrhage1500|refill|course|longrest|hormones|respiratory");
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
            eprintln!("usage: anatomica-physiology validate | run resting|hemorrhage|infusion|hemorrhage1500|refill|course|longrest|hormones|respiratory|calcium | determinism");
            ExitCode::FAILURE
        }
    }
}
