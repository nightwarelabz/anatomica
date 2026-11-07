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
    let lines = evaluate_resting(&p, &outcome);
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
    // Milestone 26: evaluation runs over the four-arm set (the
    // whole-blood MAP advantage is the one new hard line).
    use anatomica_physiology::cases::{
        evaluate_course, run_course_arm, run_hemorrhage_1500_course, CourseArm, CourseSet,
    };
    let p = params();
    let untreated = run_hemorrhage_1500_course(&p, false);
    let treated = run_hemorrhage_1500_course(&p, true);
    let set = CourseSet {
        untreated: run_course_arm(&p, CourseArm::Untreated),
        crystalloid: run_course_arm(&p, CourseArm::Crystalloid),
        whole_blood: run_course_arm(&p, CourseArm::WholeBlood),
        components: run_course_arm(&p, CourseArm::Components),
    };
    for line in evaluate_course(&p, &set) {
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
    assert!(set.whole_blood.conservation_error_ml < 0.01);
    assert!(set.components.conservation_error_ml < 0.01);
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

// ---- Milestone 25: interstitial reservoir + renal excretion ----

#[test]
fn renal_and_intake_balance_at_rest_over_an_hour() {
    use anatomica_physiology::cases::run_long_rest;
    let p = params();
    let out = run_long_rest(&p);
    // The resting steady state is a true steady state over an
    // engaged hour: post-transient drift inside the project
    // tolerance, equilibrium urine output inside its cited band
    // (S24), and the boundary fluxes nearly cancel.
    let tol = p.f64("steady_state_drift_tolerance");
    let map_drift = (out.last_window.map - out.mid_window.map).abs() / out.mid_window.map;
    let co_drift = (out.last_window.co - out.mid_window.co).abs() / out.mid_window.co;
    assert!(
        map_drift < tol && co_drift < tol,
        "post-transient drift MAP {:.3}% CO {:.3}%",
        map_drift * 100.0,
        co_drift * 100.0
    );
    assert!(
        (0.7..=1.4).contains(&out.final_uo_ml_min),
        "equilibrium urine output {:.2} mL/min outside the cited band",
        out.final_uo_ml_min
    );
    assert!(
        (out.urine_engaged_hour_ml - out.intake_engaged_hour_ml).abs() < 15.0,
        "engaged-hour boundary imbalance: urine {:.1} vs intake {:.1} mL",
        out.urine_engaged_hour_ml,
        out.intake_engaged_hour_ml
    );
    assert!(out.conservation_error_ml < 0.01);
}

#[test]
fn interstitial_reservoir_identity_and_pressure_feedback() {
    use anatomica_physiology::engine::Event;
    let p = params();
    let mut e = Engine::new(&p);
    e.tick_n(6000);
    let isf0 = e.interstitial_volume_ml();
    assert!((isf0 - 11000.0).abs() < 1e-9, "reservoir starts at its cited capacity");
    e.set_reflex_setpoint(72.91);
    e.apply(
        6000,
        Event::SetExtFlow { rate_ml_s: -750.0 / 60.0, label: "bleed".to_string() },
    );
    e.apply(
        9000,
        Event::SetExtFlow { rate_ml_s: 0.0, label: "bleed end".to_string() },
    );
    e.tick_n(90_000); // 30 min past bleed end
    // Identity: the reservoir's content, the refill state, and
    // the intracellular lump are exact mirrors at all times.
    // MILESTONE 30 AMENDMENT: the reservoir now also exchanges
    // with the intracellular lump (the protein-free refill
    // dilutes the ECF, so water moves into the cells) — the
    // M26 two-term identity gains the ICF term, and the assertion
    // stays exact at 1e-9. Measured here: the cells gain ~1.4 mL
    // over the 30 min after the -750 mL bleed, which is exactly
    // the gap the M26 form reports.
    assert!(
        (e.interstitial_volume_ml() + e.net_refill_ml()
            + (e.icf_volume_ml() - 28_000.0) - isf0).abs() < 1e-9,
        "V_isf + refill + dICF != V_isf0: {:.6} + {:.6} + {:.6} vs {:.1}",
        e.interstitial_volume_ml(),
        e.net_refill_ml(),
        e.icf_volume_ml() - 28_000.0,
        isf0
    );
    // Refill drew the reservoir down, so its pressure deviation is
    // negative — the feedback that brakes the flow.
    assert!(e.net_refill_ml() > 0.0);
    assert!(e.interstitial_pressure_deviation_mmhg() < 0.0);
    assert!(e.interstitial_volume_ml() > 0.0, "reservoir never empties in shipped scenarios");
}

// ---- Milestone 26: oncotic state + blood products ----

#[test]
fn oncotic_states_are_quiet_at_rest() {
    // The protein fluxes (leak, lymph return, synthesis, catabolism)
    // cancel at the operating point by construction, so over the
    // standard engaged resting protocol the concentrations and
    // oncotic pressures stay at their cited resting values and the
    // hematocrit does not move (nothing perturbs the red-cell state;
    // urine removes protein-free water from a 2,750 mL plasma pool
    // at ~1 mL/min balanced by intake, so the concentration effect
    // is second-order and inside the tolerance asserted).
    let p = params();
    let mut e = Engine::new(&p);
    e.tick_n(6000);
    let (map, _) = e.query("mean_arterial_pressure").expect("MAP after settle");
    e.set_reflex_setpoint(map);
    e.tick_n(6000);
    let (cp, ci) = e.protein_concentrations_g_ml();
    assert!((cp - 0.073).abs() < 0.002, "plasma protein at rest: {:.4} g/mL", cp);
    assert!((ci - 0.030).abs() < 0.002, "ISF protein at rest: {:.4} g/mL", ci);
    assert!(
        (e.plasma_oncotic_mmhg() - 26.98).abs() < 0.75,
        "plasma oncotic at rest: {:.2} mmHg (Nitta at the cited concentration; S29's table value is 28.0)",
        e.plasma_oncotic_mmhg()
    );
    assert!(
        (e.isf_oncotic_mmhg() - 7.87).abs() < 0.5,
        "ISF oncotic at rest: {:.2} mmHg (S29: 8)",
        e.isf_oncotic_mmhg()
    );
    assert!(
        (e.hematocrit() - 0.45).abs() < 0.005,
        "hematocrit at rest: {:.4}",
        e.hematocrit()
    );
}

#[test]
fn product_channel_identity_and_bookkeeping() {
    // Reflex OFF: urine is held equal to intake and refill is zero,
    // so the volume identity closes exactly around the product
    // integral. One unit of whole blood must add exactly its volume
    // to the boundary accounting, its red cells to the red-cell
    // state, and land the hematocrit on the bookkeeping value.
    use anatomica_physiology::engine::Event;
    let p = params();
    let mut e = Engine::new(&p);
    e.tick_n(600);
    let (vol, hct, prot) = e.model.product_spec("whole_blood").expect("wb spec");
    let v0 = e.total_volume_ml();
    let rbc0 = e.rbc_volume_ml();
    e.apply(
        600,
        Event::SetProductFlow {
            rate_ml_s: vol / 60.0,
            hematocrit: hct,
            protein_g_per_ml: prot,
            label: "test whole blood".to_string(),
        },
    );
    e.apply(
        3600,
        Event::SetProductFlow {
            rate_ml_s: 0.0,
            hematocrit: hct,
            protein_g_per_ml: prot,
            label: "test whole blood ends".to_string(),
        },
    );
    e.tick_n(3600);
    assert!(
        (e.cumulative_product_ml() - vol).abs() < 1e-6,
        "product integral {:.4} vs unit volume {:.1}",
        e.cumulative_product_ml(),
        vol
    );
    assert!(
        (e.total_volume_ml() - v0).abs() < 1e-6,
        "volume identity with product inflow: drift {:e} mL",
        e.total_volume_ml() - v0
    );
    assert!(
        (e.rbc_volume_ml() - (rbc0 + vol * hct)).abs() < 1e-6,
        "red-cell bookkeeping: {:.4} vs {:.4}",
        e.rbc_volume_ml(),
        rbc0 + vol * hct
    );
    let expected_hct = (rbc0 + vol * hct) / (5000.0 + vol);
    assert!(
        (e.hematocrit() - expected_hct).abs() < 1e-9,
        "hematocrit {:.6} vs bookkeeping {:.6}",
        e.hematocrit(),
        expected_hct
    );
}

#[test]
fn crystalloid_dilutes_oncotic_pressure_and_prbc_restores_hematocrit() {
    use anatomica_physiology::engine::Event;
    let p = params();
    // Crystalloid (reflex off, so no refill confound): 1,000 mL of
    // protein-free volume dilutes the plasma pool 2,750 -> ~3,750 mL;
    // protein mass is conserved to within the slow fluxes' drift
    // over two minutes, and the oncotic pressure falls on the Nitta
    // relation.
    let mut e = Engine::new(&p);
    e.tick_n(600);
    let pi0 = e.plasma_oncotic_mmhg();
    e.apply(
        600,
        Event::SetExtFlow { rate_ml_s: 1000.0 / 60.0, label: "test crystalloid".to_string() },
    );
    e.apply(
        3600,
        Event::SetExtFlow { rate_ml_s: 0.0, label: "test crystalloid ends".to_string() },
    );
    e.tick_n(3300);
    let (cp, _) = e.protein_concentrations_g_ml();
    assert!(
        cp > 0.048 && cp < 0.058,
        "diluted plasma protein {:.4} g/mL (bookkeeping ~0.0535)",
        cp
    );
    assert!(
        e.plasma_oncotic_mmhg() < pi0 - 6.0,
        "oncotic pressure must fall materially: {:.1} -> {:.1} mmHg",
        pi0,
        e.plasma_oncotic_mmhg()
    );
    assert!(
        (e.hematocrit() - 2250.0 / 6000.0).abs() < 0.002,
        "diluted hematocrit {:.4} (bookkeeping 0.375)",
        e.hematocrit()
    );

    // PRBC: 2 units (600 mL at hematocrit 0.60) into the resting
    // circulation land the hematocrit on its bookkeeping value —
    // the in-model counterpart of S34's per-unit rule, which is
    // stated at volume equilibrium and is cross-read in
    // MILESTONE-26.md rather than gated here.
    let mut e = Engine::new(&p);
    e.tick_n(600);
    let (vol, hct, prot) = e.model.product_spec("prbc").expect("prbc spec");
    e.apply(
        600,
        Event::SetProductFlow {
            rate_ml_s: 2.0 * vol / 60.0,
            hematocrit: hct,
            protein_g_per_ml: prot,
            label: "test PRBC".to_string(),
        },
    );
    e.apply(
        3600,
        Event::SetProductFlow {
            rate_ml_s: 0.0,
            hematocrit: hct,
            protein_g_per_ml: prot,
            label: "test PRBC ends".to_string(),
        },
    );
    e.tick_n(3300);
    let expected = (2250.0 + 2.0 * vol * hct) / (5000.0 + 2.0 * vol);
    assert!(
        (e.hematocrit() - expected).abs() < 0.002,
        "post-PRBC hematocrit {:.4} vs bookkeeping {:.4}",
        e.hematocrit(),
        expected
    );
}

#[test]
fn hormonal_states_quiet_at_rest() {
    // Milestone 30: the hormonal axes must not disturb the resting
    // operating point they are referenced to — the equilibrium
    // construction puts every hormonal derivative at zero there.
    // Over the standard resting protocol the states stay within a
    // small tolerance of their constructed resting values (the
    // residual is the sensed-MAP micro-oscillation coupling,
    // orders below any gate tolerance).
    let p = params();
    let mut e = Engine::new(&p);
    e.tick_n(6000);
    let (map, _) = e.query("mean_arterial_pressure").expect("MAP after settle");
    e.set_reflex_setpoint(map);
    e.tick_n(6000);
    assert!(
        (e.adh_pg_ml() - 1.75).abs() < 0.05,
        "ADH at rest: {:.3} pg/mL (constructed 1.75)",
        e.adh_pg_ml()
    );
    assert!(
        (e.aldosterone_state() - 1.0).abs() < 0.05,
        "aldosterone state at rest: {:.3} (normalised 1.0)",
        e.aldosterone_state()
    );
    assert!(
        (e.plasma_sodium_mmol_l() - 138.0).abs() < 0.5,
        "plasma sodium at rest: {:.2} mmol/L (constructed 138)",
        e.plasma_sodium_mmol_l()
    );
    assert!(
        (e.plasma_osmolality_mosm_kg() - 286.0).abs() < 1.0,
        "plasma osmolality at rest: {:.2} mOsm/kg (constructed 286)",
        e.plasma_osmolality_mosm_kg()
    );
    assert!(
        (e.urine_sodium_rate_mmol_min() - 0.111).abs() < 0.01,
        "urine sodium rate at rest: {:.4} mmol/min (baseline 0.111)",
        e.urine_sodium_rate_mmol_min()
    );
}

#[test]
fn osmolality_and_sodium_identities_at_rest() {
    // Milestone 30 construction identities on a fresh engine:
    // ECF = plasma + interstitial = 13,750 mL; TBW = 41,750 mL;
    // [Na] = 138 by construction; osmolality = 2 x 138 + 10 = 286
    // (inside the cited 275-295 band, S47); the resting urine
    // osmolality readout reproduces S39's ~600 and the urine
    // sodium concentration S48's spot range.
    let p = params();
    let e = Engine::new(&p);
    assert!((e.ecf_volume_ml() - 13_750.0).abs() < 1e-6, "ECF {:.1}", e.ecf_volume_ml());
    assert!(
        (e.total_body_water_ml() - 41_750.0).abs() < 1e-6,
        "TBW {:.1}",
        e.total_body_water_ml()
    );
    assert!((e.plasma_sodium_mmol_l() - 138.0).abs() < 1e-9);
    assert!((e.plasma_osmolality_mosm_kg() - 286.0).abs() < 1e-9);
    assert!(
        (e.urine_osmolality_mosm_kg() - 600.0).abs() < 5.0,
        "resting urine osmolality {:.1} mOsm/kg (S39 ~600)",
        e.urine_osmolality_mosm_kg()
    );
    assert!(
        (40.0..=220.0).contains(&e.urine_sodium_conc_mmol_l()),
        "resting urine sodium {:.1} mmol/L (S48 spot range 40-220)",
        e.urine_sodium_conc_mmol_l()
    );
}

#[test]
fn water_load_produces_cited_diuresis() {
    // Milestone 30, arm A: a 1 L solute-free water load suppresses
    // ADH along S37's regression and produces the water diuresis
    // S39 describes (~6x urine flow within 45 min, urine osmolarity
    // falling toward ~100) — the same lines the CLI prints.
    use anatomica_physiology::cases::{run_water_control, run_water_load};
    let p = params();
    let load = run_water_load(&p);
    let control = run_water_control(&p);
    let at = |o: &anatomica_physiology::cases::HormoneArmOutcome, m: f64| {
        o.samples.iter().find(|s| (s.minutes - m).abs() < 1e-9).unwrap().clone()
    };
    assert!(
        at(&load, 45.0).adh_pg_ml < load.resting_adh_pg_ml,
        "ADH at +45 min {:.2} should be suppressed below resting {:.2}",
        at(&load, 45.0).adh_pg_ml,
        load.resting_adh_pg_ml
    );
    // Peak interval flow ratio over the resting baseline flow.
    let rest = p.f64("baseline_urine_output_ml_min");
    let mut peak = 0.0f64;
    let mut peak_uosm = 0.0f64;
    for w in load.samples.windows(2) {
        let rate = (w[1].urine_ml - w[0].urine_ml) / (w[1].minutes - w[0].minutes);
        if rate / rest > peak {
            peak = rate / rest;
            peak_uosm = w[1].urine_osmolality_mosm_kg;
        }
    }
    assert!(
        (3.0..=12.0).contains(&peak),
        "peak urine flow ratio {peak:.2}x (S39 ~6x)"
    );
    assert!(
        (50.0..=250.0).contains(&peak_uosm),
        "urine osmolality at peak flow {peak_uosm:.0} mOsm/kg (S39 falls to ~100)"
    );
    let excess = load.samples.last().unwrap().urine_ml - control.samples.last().unwrap().urine_ml;
    assert!(excess > 400.0, "excess urine at +4 h {excess:.0} mL of the 1,000 mL load");
    assert!(load.conservation_error_ml < 0.01, "water arm conservation {:.2e}", load.conservation_error_ml);
}

#[test]
fn sodium_load_suppresses_aldosterone_and_restores_balance() {
    // Milestone 30, arm B: a fivefold sodium load suppresses the
    // aldosterone state (S43/S40) and, on the slow timescale,
    // restores sodium balance (S45's principle) at a small pressure
    // cost (S44's regime) — the same lines the CLI prints.
    use anatomica_physiology::cases::run_sodium_load;
    let p = params();
    let arm = run_sodium_load(&p);
    let at = |m: f64| arm.samples.iter().find(|s| (s.minutes - m).abs() < 1e-9).unwrap().clone();
    let late = at(1440.0);
    assert!(late.aldo_state < 0.8, "aldosterone at 24 h {:.2} (suppressed)", late.aldo_state);
    let final_hour_rate = (late.urine_na_mmol - at(1380.0).urine_na_mmol) / 60.0;
    let ratio = final_hour_rate / (5.0 * p.f64("sodium_intake_mmol_min"));
    assert!(
        (0.8..=1.25).contains(&ratio),
        "final-hour sodium excretion / intake ratio {ratio:.2}"
    );
    let rise = late.window.map - arm.baseline_window.map;
    assert!(
        (0.0..=15.0).contains(&rise),
        "MAP rise at 24 h {rise:+.1} mmHg (S44 regime)"
    );
    assert!(arm.conservation_error_ml < 0.01);
}

#[test]
fn hemorrhage_removes_sodium_at_plasma_concentration() {
    // Milestone 30 bookkeeping: blood lost through the event
    // channel removes sodium at the plasma concentration over the
    // plasma fraction — a 500 mL bleed at hematocrit ~0.45 removes
    // about (1 - 0.45) x 500 mL x 138 mmol/L = ~38 mmol (urine and
    // intake roughly cancel over the window; band is loose).
    use anatomica_physiology::engine::Event;
    let p = params();
    let mut e = Engine::new(&p);
    e.tick_n(6000);
    let (map, _) = e.query("mean_arterial_pressure").expect("MAP after settle");
    e.set_reflex_setpoint(map);
    let na0 = e.sodium_content_mmol();
    e.apply(
        6000,
        Event::SetExtFlow {
            rate_ml_s: -500.0 / 60.0,
            label: "test haemorrhage 500 mL".to_string(),
        },
    );
    e.apply(
        9000,
        Event::SetExtFlow {
            rate_ml_s: 0.0,
            label: "test haemorrhage ends".to_string(),
        },
    );
    e.tick_n(3000);
    let removed = na0 - e.sodium_content_mmol();
    assert!(
        (28.0..=46.0).contains(&removed),
        "sodium removed by a 500 mL bleed: {removed:.1} mmol (expect ~38)"
    );
}

#[test]
fn urine_output_follows_the_renal_curve_directionally() {
    let p = params();
    let rest = run_case(&p, CaseKind::Resting);
    let bleed = run_case(&p, CaseKind::Hemorrhage1500);
    let load = run_case(&p, CaseKind::Infusion1000);
    assert!(
        (0.7..=1.4).contains(&rest.post.urine_ml_min),
        "resting urine {:.2} mL/min",
        rest.post.urine_ml_min
    );
    assert!(
        bleed.post.urine_ml_min < rest.post.urine_ml_min,
        "haemorrhage urine {:.2} should fall below resting {:.2}",
        bleed.post.urine_ml_min,
        rest.post.urine_ml_min
    );
    assert!(
        load.post.urine_ml_min > rest.post.urine_ml_min,
        "infusion urine {:.2} should rise above resting {:.2}",
        load.post.urine_ml_min,
        rest.post.urine_ml_min
    );
}


// ---------------------------------------------------------------------
// Milestone 47: the respiratory module. The pinned resting baseline
// must not move (cases #1/#3 record this hash), the respiratory
// states must be deterministic in their own chain, and a lumped
// shunt must widen the A-a gradient without moving PaCO2.
// ---------------------------------------------------------------------

#[test]
fn resting_trace_hash_pinned_with_respiratory_module() {
    use anatomica_physiology::cases::CaseKind;
    let p = params();
    let rest = run_case(&p, CaseKind::Resting);
    assert_eq!(
        rest.trace_hash, 0x6369b10e9a71c872,
        "the resting circulation trace hash is pinned by the case workbench \
         (cases #1/#3); the respiratory module is one-way coupled and must \
         not move it"
    );
}

#[test]
fn respiratory_states_deterministic_and_resting() {
    use anatomica_physiology::engine::Event;
    let p = params();
    let mut a = Engine::new(&p);
    let mut b = Engine::new(&p);
    for e in [&mut a, &mut b] {
        e.tick_n(6000);
        e.set_reflex_setpoint(72.91);
        e.apply(
            6000,
            Event::SetVenousAdmixture {
                fraction: 0.20,
                label: "test shunt".to_string(),
            },
        );
        e.tick_n(3000);
    }
    assert_eq!(a.resp_hash(), b.resp_hash(), "respiratory states must be deterministic");
    assert_eq!(a.hash(), b.hash(), "circulation states must be deterministic");
    // The shunt widens the A-a gradient and lowers PaO2 at the same
    // cardiac output, while PaCO2 stays at the chemoreflex point.
    let co = 4.2;
    let mut rest = Engine::new(&p);
    rest.tick_n(6000);
    assert!(
        a.aa_gradient_mmhg(co) > rest.aa_gradient_mmhg(co) + 20.0,
        "shunt A-a {:.1} vs resting {:.1}",
        a.aa_gradient_mmhg(co),
        rest.aa_gradient_mmhg(co)
    );
    assert!(a.arterial_po2_mmhg(co) < rest.arterial_po2_mmhg(co));
    assert!(
        (a.paco2_mmhg() - rest.paco2_mmhg()).abs() < 1.0,
        "PaCO2 must hold under a pure shunt: {:.1} vs {:.1}",
        a.paco2_mmhg(),
        rest.paco2_mmhg()
    );
}

// ---------------------------------------------------------------------
// Milestone 51: the two-way couplings. The hypoxic drive is zero at
// the resting operating point and, live in the shunt arm, lowers
// PaCO2 against the drive-disabled A/B arm by the coupled
// equilibrium's amount; the metabolic feedback, ARMED at rest, must
// still reproduce the pinned circulation hash (its term is exactly
// zero inside its deadband), and armed in the haemorrhage arm it
// must raise heart rate and oxygen delivery against the unarmed
// arm at the same mark (the cited compensatory direction, S70/S71).
// ---------------------------------------------------------------------

#[test]
fn hypoxic_drive_zero_at_rest_and_coupled_shunt_lowers_paco2() {
    use anatomica_physiology::cases::{run_respiratory_case, RespCaseKind};
    let p = params();
    // At rest the term is zero at the operating point (residual is
    // sensor beat noise, asserted two orders below any gate).
    let rest = run_case(&p, CaseKind::Resting);
    assert!(
        rest.resp_post.hypoxic_drive.abs() < 0.05,
        "hypoxic drive at rest: {:.4} L/min",
        rest.resp_post.hypoxic_drive
    );
    assert!(
        (rest.resp_post.paco2 - 41.095).abs() < 0.05,
        "resting PaCO2 with the drive live: {:.3} (M47 value 41.095)",
        rest.resp_post.paco2
    );
    // A/B in the shunt arm: pure (drive disabled) reproduces the
    // Milestone 47 normocapnia; coupled (drive live) settles below
    // it, inside the computed-equilibrium band of the coupled case.
    let pure = run_respiratory_case(&p, RespCaseKind::ShuntPure);
    let coupled = run_respiratory_case(&p, RespCaseKind::Shunt);
    assert!(
        (pure.post.paco2 - 41.095).abs() < 0.1,
        "pure shunt PaCO2 {:.2} (M47: 41.10)",
        pure.post.paco2
    );
    assert_eq!(pure.post.hypoxic_drive, 0.0);
    assert!(
        coupled.post.paco2 < pure.post.paco2 - 0.3,
        "coupled PaCO2 {:.2} must fall below pure {:.2}",
        coupled.post.paco2,
        pure.post.paco2
    );
    assert!(
        (38.5..=42.0).contains(&coupled.post.paco2),
        "coupled PaCO2 {:.2} outside the computed band [38.5, 42.0]",
        coupled.post.paco2
    );
    assert!(
        coupled.post.minute_ventilation > pure.post.minute_ventilation,
        "coupled VE {:.2} must exceed pure {:.2}",
        coupled.post.minute_ventilation,
        pure.post.minute_ventilation
    );
    assert!(coupled.post.hypoxic_drive > 0.5, "drive term at the mark: {:.2} L/min", coupled.post.hypoxic_drive);
}

#[test]
fn metabolic_feedback_armed_at_rest_keeps_pinned_hash() {
    use anatomica_physiology::cases::window_stats;
    use anatomica_physiology::engine::Event;
    let p = params();
    let mut e = Engine::new(&p);
    e.tick_n(4500);
    let b0 = e.beats.len();
    e.tick_n(1500);
    let b1 = e.beats.len();
    let baseline = window_stats(&e.beats[b0..b1]);
    e.set_reflex_setpoint(baseline.map);
    e.apply(
        6000,
        Event::SetOxygenFeedback {
            armed: true,
            label: "test arming".to_string(),
        },
    );
    e.tick_n(6000);
    assert_eq!(
        e.hash(),
        0x6369b10e9a71c872,
        "armed at rest, the feedback's term is exactly zero inside its \
         deadband, so the pinned resting hash must not move"
    );
    assert_eq!(e.oxygen_feedback_multiplier(), 1.0);
}

// ---------------------------------------------------------------------
// Milestone 52: the Bohr shift. The anchored construction must be
// exactly the Milestone 47 curve at the resting pH; the loading
// side and the bisection inversion must use the SAME effective
// P50 (a mismatched inversion is detectable and excluded); and
// the two override arms (hypoventilation acidosis,
// hyperventilation alkalosis) must reproduce, live vs disabled at
// identical states, the deltas the cited Bohr relation (S72)
// computes — the shift trades loading for unloading and changes
// delivery only through the content term.
// ---------------------------------------------------------------------

#[test]
fn bohr_anchor_is_exact_at_the_resting_ph() {
    use anatomica_physiology::engine::bohr_p50_effective_mmhg;
    let p = params();
    let e = Engine::new(&p);
    // A fresh engine sits exactly on the constructed resting
    // state: its pH is the anchor pH bit-for-bit, and the
    // effective P50 there is the resting P50 bit-for-bit.
    assert_eq!(e.arterial_ph(), e.model.ph_rest);
    assert_eq!(bohr_p50_effective_mmhg(e.model.ph_rest, &e.model), e.model.hill_p50_mmhg);
    assert_eq!(e.effective_p50_mmhg(), e.model.hill_p50_mmhg);
    // Direction and magnitude off the anchor (S72: -0.48 per pH):
    // -0.23 pH (the hypoventilation arm's acidosis) raises P50 by
    // 10^(0.48 x 0.23) = x1.29; +0.22 raises affinity (x0.78).
    let acid = bohr_p50_effective_mmhg(e.model.ph_rest - 0.23, &e.model);
    assert!((acid / e.model.hill_p50_mmhg - 1.29).abs() < 0.01, "acidotic P50 {acid:.2}");
    let alk = bohr_p50_effective_mmhg(e.model.ph_rest + 0.22, &e.model);
    assert!((alk / e.model.hill_p50_mmhg - 0.785).abs() < 0.01, "alkalotic P50 {alk:.2}");
    // The resting protocol's readout carries the anchor: the
    // M47 resting oxygen readouts are bit-identical at print
    // precision with the shift live.
    let rest = run_case(&p, CaseKind::Resting);
    assert!((rest.resp_post.p50_eff - e.model.hill_p50_mmhg).abs() < 0.01);
    assert_eq!(format!("{:.2}", rest.resp_post.pao2), "91.24");
    assert_eq!(format!("{:.3}", rest.resp_post.sao2), "0.965");
    assert_eq!(format!("{:.2}", rest.resp_post.cao2), "19.66");
    assert_eq!(format!("{:.0}", rest.resp_post.do2), "828");
    assert_eq!(rest.trace_hash, 0x6369b10e9a71c872);
}

#[test]
fn bohr_loading_and_inversion_use_the_same_effective_p50() {
    use anatomica_physiology::engine::{
        o2_content_ml_dl, o2_content_ml_dl_at_ph, po2_from_content_ml_dl,
        po2_from_content_ml_dl_at_ph,
    };
    let p = params();
    let e = Engine::new(&p);
    let m = &e.model;
    let hb = 14.985;
    for ph in [7.16, 7.3893, 7.61] {
        for pao2 in [40.0, 52.2, 100.5, 125.1] {
            let c = o2_content_ml_dl_at_ph(pao2, hb, ph, m);
            let back = po2_from_content_ml_dl_at_ph(c, hb, ph, m);
            assert!(
                (back - pao2).abs() < 1e-6,
                "consistent inversion at pH {ph}: content at {pao2} inverts to {back}"
            );
            if (ph - m.ph_rest).abs() > 0.1 {
                // The inconsistent pairing (shifted content read
                // on the unshifted curve, or the reverse) is off
                // by millimetres of mercury — the test can tell
                // the two apart, so the identity above is a real
                // consistency proof, not a tautology.
                let wrong = po2_from_content_ml_dl(c, hb, m);
                assert!(
                    (wrong - pao2).abs() > 1.0,
                    "mismatched inversion at pH {ph} should be detectable: {wrong} vs {pao2}"
                );
                let c_un = o2_content_ml_dl(pao2, hb, m);
                assert!((c - c_un).abs() > 0.05, "shift must move content at pH {ph}");
            }
        }
    }
}

#[test]
fn bohr_shift_hypoventilation_ab_at_identical_state() {
    use anatomica_physiology::cases::{run_respiratory_case, RespCaseKind};
    let p = params();
    let live = run_respiratory_case(&p, RespCaseKind::Hypoventilation);
    let pure = run_respiratory_case(&p, RespCaseKind::HypoventilationPure);
    // Identical states: the override suspends every path by which
    // the shift could reach the CO2 store.
    assert_eq!(live.post.paco2, pure.post.paco2);
    assert_eq!(live.post.ph, pure.post.ph);
    assert_eq!(live.resp_hash, pure.resp_hash);
    assert_eq!(live.hash_at_standard_end, pure.hash_at_standard_end);
    // The disabled arm is the Milestone 47 picture (measured then:
    // PaO2 50.85, SaO2 0.852, CaO2 17.30) and sits exactly on the
    // resting P50.
    assert_eq!(pure.post.p50_eff, pure.baseline.p50_eff);
    assert!((pure.post.p50_eff - 26.6).abs() < 1e-12);
    assert!((pure.post.pao2 - 50.85).abs() < 0.15, "pure PaO2 {:.2}", pure.post.pao2);
    // The live arm is right-shifted by the computed amount.
    assert!(
        (33.5..=35.0).contains(&live.post.p50_eff),
        "live P50eff {:.2} (computed ~34.3)",
        live.post.p50_eff
    );
    let d_cao2 = pure.post.cao2 - live.post.cao2;
    let d_sao2 = pure.post.sao2 - live.post.sao2;
    let d_do2 = pure.post.do2 - live.post.do2;
    assert!((1.5..=2.8).contains(&d_cao2), "dCaO2 {d_cao2:.2} (computed ~2.1)");
    assert!((0.07..=0.14).contains(&d_sao2), "dSaO2 {d_sao2:.3} (computed ~0.104)");
    assert!((60.0..=120.0).contains(&d_do2), "dDO2 {d_do2:.0} (computed ~88)");
    // Delivery moves only through content: the two runs share
    // their final-window cardiac output bit-for-bit, so the DO2
    // delta is the content delta times that shared flow.
    assert_eq!(live.final_window.co, pure.final_window.co);
    assert!((d_do2 - d_cao2 * live.final_window.co * 10.0).abs() < 1e-6);
}

#[test]
fn bohr_shift_hyperventilation_ab_at_identical_state() {
    use anatomica_physiology::cases::{run_respiratory_case, RespCaseKind};
    let p = params();
    let live = run_respiratory_case(&p, RespCaseKind::Hyperventilation);
    let pure = run_respiratory_case(&p, RespCaseKind::HyperventilationPure);
    assert_eq!(live.post.paco2, pure.post.paco2);
    assert_eq!(live.post.ph, pure.post.ph);
    assert_eq!(live.resp_hash, pure.resp_hash);
    assert_eq!(live.hash_at_standard_end, pure.hash_at_standard_end);
    // Alkalosis at the computed steady state (S51/S66).
    assert!((19.0..=22.0).contains(&live.post.paco2), "PaCO2 {:.2}", live.post.paco2);
    assert!((7.55..=7.66).contains(&live.post.ph), "pH {:.3}", live.post.ph);
    // Left shift by the computed amount.
    assert!(
        (20.3..=21.5).contains(&live.post.p50_eff),
        "live P50eff {:.2} (computed ~20.9)",
        live.post.p50_eff
    );
    assert_eq!(pure.post.p50_eff, 26.6);
    let d_cao2 = live.post.cao2 - pure.post.cao2;
    let d_sao2 = live.post.sao2 - pure.post.sao2;
    let d_pao2 = pure.post.pao2 - live.post.pao2;
    assert!((0.05..=0.30).contains(&d_cao2), "dCaO2 {d_cao2:.2} (computed ~0.14)");
    assert!((0.004..=0.013).contains(&d_sao2), "dSaO2 {d_sao2:.3} (computed ~0.008)");
    assert!(
        (3.0..=10.0).contains(&d_pao2),
        "dPaO2 {d_pao2:.1} (computed ~6.8: the same content at a lower PO2)"
    );
}

// ---------------------------------------------------------------------
// Milestone 53: chronic (renal) acid–base compensation. The state
// must be exactly zero at the resting equilibrium (state, target
// and derivative), the chronic target must be the direction-
// specific cited relations' difference from the acute totals
// (S73 Rules 2/4 against S66 Rules 1/3), the Bohr anchor must not
// drift when compensation moves the pH in a sustained arm, the
// acute hypoventilation window must move only by the computed
// few-percent approach, and the multi-day picture must match the
// independent solver (work/m53/predict.py). The full five-day /
// three-day arms are gated in the validator against their
// parameters.json cases; the tests run the one-day horizon.
// ---------------------------------------------------------------------

#[test]
fn chronic_compensation_is_exactly_zero_at_rest() {
    use anatomica_physiology::engine::{
        chronic_bicarbonate_meq_l_at, renal_comp_target_meq_l_at,
    };
    let p = params();
    let e = Engine::new(&p);
    let m = &e.model;
    // State, target and total at the resting equilibrium.
    assert_eq!(e.renal_compensation_meq_l(), 0.0);
    assert_eq!(e.renal_comp_target_meq_l(), 0.0);
    assert_eq!(renal_comp_target_meq_l_at(m.paco2_rest_mmhg, m), 0.0);
    assert_eq!(e.bicarbonate_meq_l(), m.hco3_0_meq_l);
    assert_eq!(e.bicarbonate_acute_meq_l(), m.hco3_0_meq_l);
    // The chronic totals are the direction-specific relations
    // (S73): +0.4 per mmHg in acidosis, -0.5 per mmHg in
    // alkalosis, about the model's own operating point.
    let rest = m.paco2_rest_mmhg;
    assert!((chronic_bicarbonate_meq_l_at(rest + 40.0, m) - (24.0 + 16.0)).abs() < 1e-9);
    assert!((chronic_bicarbonate_meq_l_at(rest - 20.0, m) - (24.0 - 10.0)).abs() < 1e-9);
    // The renal target is chronic-minus-acute per direction:
    // (0.4-0.1) x d in acidosis, (0.5-0.2) x d in alkalosis — the
    // same 0.3 increment derived from the source's four rules,
    // not a symmetric rule imposed on the totals.
    assert!((renal_comp_target_meq_l_at(rest + 40.0, m) - 12.0).abs() < 1e-9);
    assert!((renal_comp_target_meq_l_at(rest - 20.0, m) + 6.0).abs() < 1e-9);
    // The resting protocol's readout carries the zero, and the
    // pinned resting hash holds with the state live.
    let rest_run = run_case(&p, CaseKind::Resting);
    assert_eq!(rest_run.resp_post.hco3_comp, 0.0);
    assert_eq!(rest_run.trace_hash, 0x6369b10e9a71c872);
}

#[test]
fn chronic_compensation_one_day_and_anchor_holds() {
    use anatomica_physiology::engine::Event;
    let p = params();
    let mut live = Engine::new(&p);
    live.apply(0, Event::SetVentilationOverride {
        rate_per_min: Some(6.0),
        label: "test: sustained hypoventilation, compensation live".to_string(),
    });
    let mut pure = Engine::new(&p);
    pure.apply(0, Event::SetChronicCompensation {
        enabled: false,
        label: "test: compensation disabled".to_string(),
    });
    pure.apply(0, Event::SetVentilationOverride {
        rate_per_min: Some(6.0),
        label: "test: sustained hypoventilation, compensation disabled".to_string(),
    });
    // One simulated day (tick = 0.02 s).
    live.tick_n(4_320_000);
    pure.tick_n(4_320_000);
    // The state cannot touch the CO2 store or the circulation:
    // PaCO2 and the circulation hash are identical across the pair.
    assert_eq!(live.paco2_mmhg(), pure.paco2_mmhg());
    assert_eq!(live.hash(), pure.hash());
    // The disabled state is exactly zero and its pH is the acute
    // picture (independent solver: PaCO2 82.19, pH 7.157).
    assert_eq!(pure.renal_compensation_meq_l(), 0.0);
    assert!((pure.arterial_ph() - 7.157).abs() < 0.01, "pure pH {:.3}", pure.arterial_ph());
    // At one day the live state has made 63% of its approach to
    // the +12.33 target (solver: +7.73, pH 7.262, P50eff 30.6).
    let comp = live.renal_compensation_meq_l();
    assert!((7.0..=8.5).contains(&comp), "renal comp at +1 d: {comp:.2} (computed +7.73)");
    assert!((live.renal_comp_target_meq_l() - 12.33).abs() < 0.1);
    assert!(
        (7.23..=7.29).contains(&live.arterial_ph()),
        "compensated pH at +1 d: {:.3} (computed 7.262)",
        live.arterial_ph()
    );
    assert!(
        (29.5..=31.7).contains(&live.effective_p50_mmhg()),
        "P50eff at +1 d: {:.2} (computed 30.6 — the Bohr right shift partly unwound)",
        live.effective_p50_mmhg()
    );
    // THE ANCHOR DOES NOT DRIFT: Model::ph_rest is the captured
    // construction constant — identical in both engines, and a
    // fresh engine's pH still equals it bit-for-bit even though
    // the compensated arm's pH has moved 0.105 toward it.
    let fresh = Engine::new(&p);
    assert_eq!(live.model.ph_rest, fresh.model.ph_rest);
    assert_eq!(pure.model.ph_rest, fresh.model.ph_rest);
    assert_eq!(fresh.arterial_ph(), fresh.model.ph_rest);
    assert!((live.arterial_ph() - live.model.ph_rest).abs() > 0.05);
    assert_eq!(
        anatomica_physiology::engine::arterial_ph_total_at(
            live.model.paco2_rest_mmhg, 0.0, &live.model),
        live.model.ph_rest,
        "at zero compensation the total-pH function is the anchor value bit-for-bit"
    );
}

#[test]
fn chronic_compensation_acute_window_moves_only_by_the_computed_amount() {
    use anatomica_physiology::cases::{run_respiratory_case, RespCaseKind};
    let p = params();
    // The acute hypoventilation arm (+75 min): the solver computes
    // the state at +0.46 mEq/L there (3.8% of its target), moving
    // pH from 7.160 to 7.167 and P50eff from 34.3 to 34.0 — inside
    // every pre-M53 band the arm is gated on (MILESTONE-53.md
    // accounts the movement line by line).
    let hypo = run_respiratory_case(&p, RespCaseKind::Hypoventilation);
    assert!(
        (0.30..=0.65).contains(&hypo.post.hco3_comp),
        "renal comp at +75 min: {:.3} (computed +0.464)",
        hypo.post.hco3_comp
    );
    assert!(
        (7.15..=7.18).contains(&hypo.post.ph),
        "pH at +75 min: {:.3} (pre-M53 7.160, computed with compensation 7.167)",
        hypo.post.ph
    );
    assert!(
        (33.5..=35.0).contains(&hypo.post.p50_eff),
        "P50eff at +75 min: {:.2} (the Milestone 52 band; computed 34.0)",
        hypo.post.p50_eff
    );
    // The acute hyperventilation arm (+30 min): computed state
    // -0.10, pH 7.606 against the pre-M53 7.609.
    let hyper = run_respiratory_case(&p, RespCaseKind::Hyperventilation);
    assert!(
        (-0.20..=-0.03).contains(&hyper.post.hco3_comp),
        "renal comp at +30 min: {:.3} (computed -0.102)",
        hyper.post.hco3_comp
    );
    assert!(
        (7.59..=7.62).contains(&hyper.post.ph),
        "pH at +30 min: {:.3} (pre-M53 7.609, computed with compensation 7.606)",
        hyper.post.ph
    );
}

#[test]
fn metabolic_feedback_raises_hr_and_do2_in_hemorrhage() {
    use anatomica_physiology::cases::{run_respiratory_case, RespCaseKind};
    let p = params();
    let unarmed = run_respiratory_case(&p, RespCaseKind::HemorrhageResp);
    let armed = run_respiratory_case(&p, RespCaseKind::HemorrhageFeedback);
    assert!(
        armed.post.do2 > unarmed.post.do2,
        "armed DO2 {:.0} must exceed unarmed {:.0} mL/min at +30 min",
        armed.post.do2,
        unarmed.post.do2
    );
    assert!(
        armed.final_window.hr > unarmed.final_window.hr,
        "armed HR {:.1} must exceed unarmed {:.1} /min at +30 min",
        armed.final_window.hr,
        unarmed.final_window.hr
    );
    assert!(
        (100.0..=120.0).contains(&armed.window_post.hr),
        "armed standard-window HR {:.1} must stay in the M18 Class II band",
        armed.window_post.hr
    );
}
