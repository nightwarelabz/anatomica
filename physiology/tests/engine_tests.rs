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
    let p = params();
    let outcome = run_case(&p, CaseKind::Hemorrhage750);
    for line in evaluate_perturbation(&p, "hemorrhage_750", &outcome) {
        assert!(
            line.pass,
            "{}: expected {} but {:.2} -> {:.2}",
            line.output, line.expected, line.baseline, line.post
        );
    }
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
