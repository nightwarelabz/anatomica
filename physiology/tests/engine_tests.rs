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
