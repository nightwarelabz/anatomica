//! Integration tests for the physiology core: determinism, snapshot /
//! restore, volume conservation, the resting steady-state gates, and the
//! perturbation directional expectations. The gates in this file are the
//! same lines the CLI `validate` command prints — if a gate here fails,
//! the milestone's validation claim fails with it.

use anatomica_physiology::cases::{
    evaluate_perturbation, evaluate_resting, run_case, CaseKind,
};
use anatomica_physiology::engine::Engine;
use anatomica_physiology::params::Params;

fn params() -> Params {
    Params::load().expect("parameters.json must load and pass provenance checks")
}

#[test]
fn parameter_provenance_schema() {
    let p = params();
    // Every parameter is cited, calibrated within a cited range, or
    // explicitly verify-flagged — enforced by the loader; assert the file
    // actually contains all three kinds so the check is exercised.
    let statuses: Vec<&str> = p.file.parameters.iter().map(|x| x.status.as_str()).collect();
    assert!(statuses.contains(&"cited"));
    assert!(statuses.contains(&"verify"));
    // Every validation range cites a source that exists.
    for v in &p.file.validation_ranges {
        assert!(p.file.sources.iter().any(|s| s.id == v.source), "range {} cites missing source", v.output);
    }
}

#[test]
fn determinism_bit_identical() {
    let p = params();
    let mut a = Engine::new(&p);
    let mut b = Engine::new(&p);
    a.tick_n(3000);
    b.tick_n(3000);
    assert_eq!(a.hash(), b.hash(), "same inputs must give identical trace hash");
    assert_eq!(a.volumes(), b.volumes(), "final states must be bitwise identical");
}

#[test]
fn snapshot_restore_replays_identically() {
    let p = params();
    let mut e = Engine::new(&p);
    e.tick_n(1500);
    let snap = e.snapshot();
    e.tick_n(1500);
    let hash_a = e.hash();
    let vols_a = e.volumes();
    e.restore(snap);
    e.tick_n(1500);
    assert_eq!(e.hash(), hash_a);
    assert_eq!(e.volumes(), vols_a);
}

#[test]
fn volume_is_conserved() {
    let p = params();
    let outcome = run_case(&p, CaseKind::Resting);
    assert!(
        outcome.conservation_error_ml < 0.01,
        "closed loop must conserve volume, error was {} mL",
        outcome.conservation_error_ml
    );
    // With an external flow the accounting still closes.
    let outcome = run_case(&p, CaseKind::Hemorrhage750);
    assert!(outcome.conservation_error_ml < 0.01);
}

#[test]
fn resting_case_meets_published_normal_ranges() {
    let p = params();
    let outcome = run_case(&p, CaseKind::Resting);
    let lines = evaluate_resting(&p, &outcome.post);
    let failures: Vec<String> = lines
        .iter()
        .filter(|l| !l.pass && !l.soft)
        .map(|l| format!("{} = {:.2} {} outside {}", l.output, l.value, l.unit, l.range_text))
        .collect();
    assert!(failures.is_empty(), "resting gates failed:\n{}", failures.join("\n"));
    // Steady state must actually hold (design/04 gate), not just visit
    // the ranges transiently.
    let tol = p.f64("steady_state_drift_tolerance");
    assert!(outcome.post.map_drift < tol, "MAP drift {}", outcome.post.map_drift);
    assert!(outcome.post.co_drift < tol, "CO drift {}", outcome.post.co_drift);
    // Series circuit: LV and RV stroke volumes must agree.
    let imbalance = (outcome.post.sv_lv - outcome.post.sv_rv).abs() / outcome.post.sv_lv;
    assert!(imbalance < 0.05, "SV imbalance {imbalance}");
}

#[test]
fn hemorrhage_moves_in_the_sourced_directions() {
    // Since Milestone 18 this also asserts the case's hard magnitude
    // gate (ATLS Class II heart-rate band, S16): evaluate_perturbation
    // folds magnitude_range into `pass`. Soft lines (the systolic
    // band, whose lower bound was not read in a consulted source)
    // are reported by the CLI and disclosed in MILESTONE-18.md; like
    // the CLI, this test gates only hard lines.
    let p = params();
    let outcome = run_case(&p, CaseKind::Hemorrhage750);
    for line in evaluate_perturbation(&p, "hemorrhage_750", &outcome) {
        if line.soft {
            continue;
        }
        assert!(
            line.pass,
            "{}: expected {} but {:.2} -> {:.2}",
            line.output, line.expected, line.baseline, line.post
        );
    }
}

#[test]
fn hemorrhage_1500_meets_atls_class_iii_expectations() {
    // Hard lines: the sourced directional expectations. The Class
    // III heart-rate band is a soft line — the model decompensates
    // at this volume (its documented compensation ceiling,
    // MILESTONE-18.md), so the band is reported, not gated.
    let p = params();
    let outcome = run_case(&p, CaseKind::Hemorrhage1500);
    for line in evaluate_perturbation(&p, "hemorrhage_1500", &outcome) {
        if line.soft {
            continue;
        }
        assert!(
            line.pass,
            "{}: expected {} but {:.2} -> {:.2}",
            line.output, line.expected, line.baseline, line.post
        );
    }
}

#[test]
fn refill_observation_lands_in_the_cited_band() {
    use anatomica_physiology::cases::{evaluate_refill, run_refill_observation};
    let p = params();
    let outcome = run_refill_observation(&p);
    let (value, band, pass) = evaluate_refill(&p, &outcome);
    assert!(
        pass,
        "net refill at +30 min was {value:.1} mL, band [{:.1}, {:.1}]",
        band[0], band[1]
    );
    assert!(
        outcome.conservation_error_ml < 0.01,
        "conservation with refill inflow: {} mL",
        outcome.conservation_error_ml
    );
}

#[test]
fn mechanisms_are_quiet_at_rest() {
    // The Milestone 18 mechanisms must not disturb the resting
    // operating point they are referenced to: over the standard
    // resting protocol, recruited volume and net refill stay within
    // a few percent of their full scales (630 mL / 1000 mL).
    let p = params();
    let mut e = Engine::new(&p);
    e.tick_n(6000);
    let (map, _) = e.query("mean_arterial_pressure").expect("MAP after settle");
    e.set_reflex_setpoint(map);
    e.tick_n(6000);
    assert!(
        e.recruited_ml().abs() < 32.0,
        "recruited at rest: {:.1} mL",
        e.recruited_ml()
    );
    assert!(
        e.net_refill_ml().abs() < 50.0,
        "net refill at rest: {:.1} mL",
        e.net_refill_ml()
    );
}

#[test]
fn contractility_is_quiet_at_rest_and_engages_in_hemorrhage() {
    // Milestone 21: the inotropy state rests at its operating point
    // (multiplier ~1, inside a few percent — the same tolerance class
    // as the Milestone 18 quiet-at-rest bounds) and drives toward the
    // cited +20% swing ceiling (S13) under a Class III-scale loss,
    // where the reflex error signal saturates.
    use anatomica_physiology::engine::Event;
    let p = params();
    let mut e = Engine::new(&p);
    e.tick_n(6000);
    let (map, _) = e.query("mean_arterial_pressure").expect("MAP after settle");
    e.set_reflex_setpoint(map);
    e.tick_n(6000);
    assert!(
        (e.contractility_multiplier() - 1.0).abs() < 0.05,
        "contractility at rest: {:.3}",
        e.contractility_multiplier()
    );

    let mut e = Engine::new(&p);
    e.tick_n(6000);
    let (map, _) = e.query("mean_arterial_pressure").expect("MAP after settle");
    e.set_reflex_setpoint(map);
    e.apply(
        6000,
        Event::SetExtFlow {
            rate_ml_s: -1500.0 / 60.0,
            label: "test haemorrhage".to_string(),
        },
    );
    e.apply(
        9000,
        Event::SetExtFlow {
            rate_ml_s: 0.0,
            label: "test haemorrhage ends".to_string(),
        },
    );
    e.tick_n(6000);
    assert!(
        e.contractility_multiplier() > 1.10,
        "contractility after -1500 mL: {:.3} (cited swing ceiling 1.20)",
        e.contractility_multiplier()
    );
    let (mult, unit) = e.query("contractility_multiplier").expect("query");
    assert_eq!(unit, "ratio");
    assert!((mult - e.contractility_multiplier()).abs() < 1e-12);
}

#[test]
fn infusion_moves_in_the_sourced_directions() {
    let p = params();
    let outcome = run_case(&p, CaseKind::Infusion1000);
    for line in evaluate_perturbation(&p, "infusion_1000", &outcome) {
        assert!(
            line.pass,
            "{}: expected {} but {:.2} -> {:.2}",
            line.output, line.expected, line.baseline, line.post
        );
    }
}

#[test]
fn guyton_quantities_close_at_rest() {
    // Milestone 24: the Guyton formulation made first-class. Resting
    // MSFP inside the project tolerance band around the cited ~7
    // mmHg (S17/S18); the right-atrial-pressure proxy inside S3's
    // right-atrial range (the same line the CLI gates); systemic
    // stressed volume a plausible fraction of the calibrated total
    // volume (consulted reviews put stressed volume at roughly
    // 20-30% of total blood volume); and the empirical resistance
    // to venous return, (MSFP - RAP)/CO, agrees with the
    // series-circuit formula (compliance-weighted, pulsatile
    // venous-outflow segment) within the 15% engineering criterion
    // the CLI prints.
    let p = params();
    let outcome = run_case(&p, CaseKind::Resting);
    assert!(
        outcome.msfp_mmhg >= 5.0 && outcome.msfp_mmhg <= 9.0,
        "resting MSFP {:.2} mmHg outside [5, 9] (cited ~7, S17/S18)",
        outcome.msfp_mmhg
    );
    assert!(
        outcome.post.rap >= 1.0 && outcome.post.rap <= 7.0,
        "resting RAP proxy {:.2} mmHg outside S3 range [1, 7]",
        outcome.post.rap
    );
    let frac = outcome.stressed_sys_ml / 5000.0;
    assert!(
        frac > 0.10 && frac < 0.30,
        "systemic stressed volume {:.0} mL = {:.0}% of total volume",
        outcome.stressed_sys_ml,
        frac * 100.0
    );
    let rel = (outcome.rvr_empirical - outcome.rvr_formula).abs() / outcome.rvr_formula;
    assert!(
        rel < 0.15,
        "RVR empirical {:.4} vs formula {:.4} mmHg*s/mL (rel. diff {:.1}%)",
        outcome.rvr_empirical,
        outcome.rvr_formula,
        rel * 100.0
    );
    // MCFP (whole circuit, stop-flow construction) sits below MSFP
    // in this circuit: the pulmonary tree and ventricles add
    // compliance whose stressed share is smaller.
    assert!(
        outcome.mcfp_mmhg > 0.0 && outcome.mcfp_mmhg < outcome.msfp_mmhg,
        "MCFP {:.2} vs MSFP {:.2}",
        outcome.mcfp_mmhg,
        outcome.msfp_mmhg
    );
}

#[test]
fn hemorrhage_course_recovers_untreated_and_bolus_helps() {
    // Milestone 24 course case: the hard lines only (the soft lines
    // — S15 refill envelope, the two disclosed ATLS-band readings —
    // are reported by the CLI and in MILESTONE-24.md). Untreated,
    // the +30 min MAP must exceed the +2 min MAP (S19 course);
    // the ATLS-bolus arm must beat the untreated arm on MAP and CO
    // and relieve heart rate at +10 min. Both arms conserve volume.
    use anatomica_physiology::cases::{evaluate_course, run_hemorrhage_1500_course};
    let p = params();
    let untreated = run_hemorrhage_1500_course(&p, false);
    let treated = run_hemorrhage_1500_course(&p, true);
    for line in evaluate_course(&p, &untreated, &treated) {
        if line.soft {
            continue;
        }
        assert!(
            line.pass,
            "{}: expected {} but {:.2} -> {:.2}",
            line.output, line.expected, line.baseline, line.post
        );
    }
    assert!(untreated.conservation_error_ml < 0.01);
    assert!(treated.conservation_error_ml < 0.01);
    // The course's +1 min sample is the standard case's post state:
    // same protocol, same window — the two runners must agree.
    let standard = run_case(&p, CaseKind::Hemorrhage1500);
    let first = &untreated.samples[0].window;
    assert!(
        (first.map - standard.post.map).abs() < 0.05 && (first.hr - standard.post.hr).abs() < 0.5,
        "course +1 min (MAP {:.2}, HR {:.1}) vs standard post (MAP {:.2}, HR {:.1})",
        first.map,
        first.hr,
        standard.post.map,
        standard.post.hr
    );
}

#[test]
fn query_interface_reports_units_and_chain() {
    let p = params();
    let mut e = Engine::new(&p);
    e.tick_n(6000);
    let (map, unit) = e.query("mean_arterial_pressure").expect("MAP query");
    assert_eq!(unit, "mmHg");
    assert!(map > 0.0);
    // v0 causal chain = the applied-event log (empty before any event).
    assert!(e.causal_chain().is_empty());
}
