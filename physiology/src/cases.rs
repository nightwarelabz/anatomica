//! Case protocol and validation harness.
//!
//! Protocol for every case (deterministic, event-driven per design/04):
//!   1. Settle 120 s undisturbed, baroreflex off.
//!   2. Baseline window: beats completed during ticks 4500..6000 (30 s).
//!   3. Baroreflex engages with its setpoint = the baseline MAP (the
//!      model's own resting operating point — no external setpoint value
//!      is asserted).
//!   4. Perturbation cases apply their events at tick 6000 and run to
//!      tick 12000; the post window is beats during ticks 10500..12000.
//!      The resting case runs the same span with no events, which is what
//!      tests the design/04 "holds steady state" gate under an engaged
//!      reflex.
//!
//! Milestone 25 additions: WindowStats carries the post window's
//! mean urine output rate (from the engine's cumulative renal state
//! at the window edges — urine is a flow integral, not a beat
//! statistic); the course samples carry the volume-side states at
//! each mark (cumulative urine and intake, interstitial volume,
//! total blood volume) and the course gains the bolus-retention
//! quantity; and a long-horizon resting runner (run_long_rest)
//! proves the resting steady state over a full engaged hour now
//! that an excretory pathway is open.
//!
//! Milestone 30 additions: the resting evaluation gains the
//! hormonal resting lines (plasma osmolality, plasma sodium, urine
//! osmolality, plasma ADH — end-of-run engine states on
//! CaseOutcome, like the Milestone 26 oncotic lines); WindowStats
//! carries the post window's mean sodium excretion rate; the
//! course samples carry the hormonal states at each mark and the
//! course runner takes an explicit mark schedule; and four
//! hormonal scenario arms (water load with a paired no-load
//! control, water deprivation, sodium load, and the −1,500 mL
//! course extended to 12 h) run under a dedicated evaluator
//! (evaluate_hormones) against the cases parameters.json declares
//! for them — each axis exercised in its own regime and on its own
//! timescale.

use crate::engine::{BeatRecord, Engine, Event};
use crate::params::Params;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CaseKind {
    Resting,
    Hemorrhage750,
    Infusion1000,
    Hemorrhage1500,
}

#[derive(Debug, Clone)]
pub struct WindowStats {
    pub beats: usize,
    pub hr: f64,
    pub sbp: f64,
    pub dbp: f64,
    pub map: f64,
    pub pulse_pressure: f64,
    pub pp_fraction: f64,
    pub co: f64,
    pub sv_lv: f64,
    pub sv_rv: f64,
    pub cvp: f64,
    /// Mean right-atrial-pressure proxy over the window (Milestone
    /// 24; see engine::BeatRecord::rap).
    pub rap: f64,
    /// Mean urine output rate over the window (mL/min, Milestone
    /// 25). Not derivable from beats: run_case fills the post window
    /// from the engine's cumulative urine state at the window edges;
    /// window_stats leaves it 0.0 elsewhere.
    pub urine_ml_min: f64,
    /// Mean urine sodium excretion rate over the window (mmol/min,
    /// Milestone 30). Same construction as urine_ml_min, from the
    /// engine's cumulative urinary sodium state at the window edges.
    pub urine_na_ml_min: f64,
    pub pa_systolic: f64,
    pub pa_diastolic: f64,
    pub pa_mean: f64,
    pub pv_mean: f64,
    pub map_drift: f64,
    pub co_drift: f64,
}

fn mean(xs: &[f64]) -> f64 {
    xs.iter().sum::<f64>() / xs.len() as f64
}

fn drift(xs: &[f64]) -> f64 {
    if xs.len() < 4 {
        return 0.0;
    }
    let half = xs.len() / 2;
    let m1 = mean(&xs[..half]);
    let m2 = mean(&xs[half..]);
    let m = mean(xs);
    if m == 0.0 {
        0.0
    } else {
        (m2 - m1).abs() / m
    }
}

pub fn window_stats(beats: &[BeatRecord]) -> WindowStats {
    let get = |f: &dyn Fn(&BeatRecord) -> f64| beats.iter().map(f).collect::<Vec<_>>();
    let maps = get(&|b| b.map);
    let cos = get(&|b| b.co_l_min);
    let sbp = mean(&get(&|b| b.sbp));
    let pp = mean(&get(&|b| b.pulse_pressure));
    WindowStats {
        beats: beats.len(),
        hr: mean(&get(&|b| b.hr_bpm)),
        sbp,
        dbp: mean(&get(&|b| b.dbp)),
        map: mean(&maps),
        pulse_pressure: pp,
        pp_fraction: if sbp > 0.0 { pp / sbp } else { 0.0 },
        co: mean(&cos),
        sv_lv: mean(&get(&|b| b.sv_lv_ml)),
        sv_rv: mean(&get(&|b| b.sv_rv_ml)),
        cvp: mean(&get(&|b| b.cvp)),
        rap: mean(&get(&|b| b.rap)),
        urine_ml_min: 0.0,
        urine_na_ml_min: 0.0,
        pa_systolic: mean(&get(&|b| b.pa_systolic)),
        pa_diastolic: mean(&get(&|b| b.pa_diastolic)),
        pa_mean: mean(&get(&|b| b.pa_mean)),
        pv_mean: mean(&get(&|b| b.pv_mean)),
        map_drift: drift(&maps),
        co_drift: drift(&cos),
    }
}

#[derive(Debug, Clone)]
pub struct CaseOutcome {
    pub kind: CaseKind,
    pub baseline: WindowStats,
    pub post: WindowStats,
    pub trace_hash: u64,
    pub conservation_error_ml: f64,
    pub total_beats: usize,
    pub causal_chain: Vec<String>,
    /// Guyton formulation at the end of the run (Milestone 24):
    /// systemic stressed volume (mL), mean systemic filling
    /// pressure (mmHg), whole-circuit mean circulatory filling
    /// pressure (mmHg) — computed functions of the final state.
    pub stressed_sys_ml: f64,
    pub msfp_mmhg: f64,
    pub mcfp_mmhg: f64,
    /// Resistance to venous return (mmHg*s/mL) at the post window:
    /// empirical, (MSFP_end − RAP_window) / CO_window, and the
    /// series-circuit formula at baseline resistances (engine).
    pub rvr_empirical: f64,
    pub rvr_formula: f64,
    /// Oncotic state at the end of the run (Milestone 26):
    /// hematocrit, plasma and interstitial oncotic pressures —
    /// instantaneous engine states, gated by evaluate_resting
    /// against the resting validation ranges in parameters.json.
    pub hematocrit_end: f64,
    pub plasma_oncotic_end: f64,
    pub isf_oncotic_end: f64,
    /// Hormonal state at the end of the run (Milestone 30):
    /// calculated plasma osmolality (mOsm/kg), plasma sodium
    /// (mmol/L), plasma AVP (pg/mL) and the urine osmolality
    /// readout (mOsm/kg) — instantaneous engine states, gated by
    /// evaluate_resting against the resting validation ranges in
    /// parameters.json, like the oncotic lines.
    pub osmolality_end: f64,
    pub sodium_end: f64,
    pub adh_end: f64,
    pub urine_osm_end: f64,
}

pub fn run_case(params: &Params, kind: CaseKind) -> CaseOutcome {
    let mut e = Engine::new(params);
    // Phase 1+2: settle, baseline window = beats in ticks 4500..6000.
    e.tick_n(4500);
    let b0 = e.beats.len();
    e.tick_n(1500);
    let b1 = e.beats.len();
    let baseline = window_stats(&e.beats[b0..b1]);
    // Phase 3: reflex on, setpoint = own resting MAP.
    e.set_reflex_setpoint(baseline.map);
    // Phase 4: perturbation events on ticks, run to tick 12000.
    match kind {
        CaseKind::Resting => {}
        CaseKind::Hemorrhage750 => {
            e.apply(
                6000,
                Event::SetExtFlow {
                    rate_ml_s: -750.0 / 60.0,
                    label: "haemorrhage 750 mL over 60 s begins".to_string(),
                },
            );
            e.apply(
                9000,
                Event::SetExtFlow {
                    rate_ml_s: 0.0,
                    label: "haemorrhage ends (750 mL removed)".to_string(),
                },
            );
        }
        CaseKind::Infusion1000 => {
            e.apply(
                6000,
                Event::SetExtFlow {
                    rate_ml_s: 1000.0 / 60.0,
                    label: "volume infusion 1000 mL over 60 s begins".to_string(),
                },
            );
            e.apply(
                9000,
                Event::SetExtFlow {
                    rate_ml_s: 0.0,
                    label: "infusion ends (1000 mL added)".to_string(),
                },
            );
        }
        CaseKind::Hemorrhage1500 => {
            e.apply(
                6000,
                Event::SetExtFlow {
                    rate_ml_s: -1500.0 / 60.0,
                    label: "haemorrhage 1500 mL over 60 s begins".to_string(),
                },
            );
            e.apply(
                9000,
                Event::SetExtFlow {
                    rate_ml_s: 0.0,
                    label: "haemorrhage ends (1500 mL removed)".to_string(),
                },
            );
        }
    }
    e.tick_n(4500);
    // Milestone 25: urine output over the post window, from the
    // cumulative renal state at the window edges (ticks 10500 and
    // 12000 — the window is 30 s, so the rate is twice the delta).
    let urine_a = e.cumulative_urine_ml();
    let una_a = e.cumulative_urine_sodium_mmol();
    let b2 = e.beats.len();
    e.tick_n(1500);
    let b3 = e.beats.len();
    let urine_b = e.cumulative_urine_ml();
    let una_b = e.cumulative_urine_sodium_mmol();
    let mut post = window_stats(&e.beats[b2..b3]);
    post.urine_ml_min = (urine_b - urine_a) * 2.0;
    post.urine_na_ml_min = (una_b - una_a) * 2.0;
    let q_post = post.co * 1000.0 / 60.0;
    let rvr_empirical = (e.mean_systemic_filling_pressure() - post.rap) / q_post;
    let rvr_formula = e.resistance_to_venous_return_formula().unwrap_or(f64::NAN);
    CaseOutcome {
        kind,
        baseline,
        post,
        trace_hash: e.hash(),
        conservation_error_ml: e.volume_conservation_error_ml(),
        total_beats: e.beats.len(),
        causal_chain: e.causal_chain(),
        stressed_sys_ml: e.systemic_stressed_volume_ml(),
        msfp_mmhg: e.mean_systemic_filling_pressure(),
        mcfp_mmhg: e.mean_circulatory_filling_pressure(),
        rvr_empirical,
        rvr_formula,
        hematocrit_end: e.hematocrit(),
        plasma_oncotic_end: e.plasma_oncotic_mmhg(),
        isf_oncotic_end: e.isf_oncotic_mmhg(),
        osmolality_end: e.plasma_osmolality_mosm_kg(),
        sodium_end: e.plasma_sodium_mmol_l(),
        adh_end: e.adh_pg_ml(),
        urine_osm_end: e.urine_osmolality_mosm_kg(),
    }
}

/// One line of the resting validation table.
#[derive(Debug, Clone)]
pub struct ValidationLine {
    pub output: String,
    pub value: f64,
    pub unit: String,
    pub range_text: String,
    pub source: String,
    pub soft: bool,
    pub pass: bool,
}

fn stat_for(stats: &WindowStats, output: &str) -> f64 {
    match output {
        "heart_rate" => stats.hr,
        "systolic_bp" => stats.sbp,
        "diastolic_bp" => stats.dbp,
        "mean_arterial_pressure" => stats.map,
        "pulse_pressure" => stats.pulse_pressure,
        "pulse_pressure_fraction" => stats.pp_fraction,
        "cardiac_output" => stats.co,
        "stroke_volume_lv" => stats.sv_lv,
        "central_venous_pressure" => stats.cvp,
        "right_atrial_pressure_proxy" => stats.rap,
        "urine_output" => stats.urine_ml_min,
        "urine_sodium_rate" => stats.urine_na_ml_min,
        "pa_systolic" => stats.pa_systolic,
        "pa_diastolic" => stats.pa_diastolic,
        "pa_mean" => stats.pa_mean,
        "pcwp_proxy_mean_pv_pressure" => stats.pv_mean,
        _ => f64::NAN,
    }
}

/// The two blood-pressure lines whose lower bounds were not read in a
/// consulted source this session (see parameters.json notes): reported
/// and disclosed, but a miss does not fail the build.
const SOFT_OUTPUTS: [&str; 2] = ["systolic_bp", "diastolic_bp"];

pub fn evaluate_resting(params: &Params, outcome: &CaseOutcome) -> Vec<ValidationLine> {
    let stats = &outcome.post;
    let mut lines = Vec::new();
    for r in &params.file.validation_ranges {
        // Milestone 26: the oncotic resting lines read the engine's
        // end-of-run state (CaseOutcome), not a beat-window
        // statistic; everything else reads the post window as
        // before.
        let value = match r.output.as_str() {
            "hematocrit" => outcome.hematocrit_end,
            "plasma_oncotic_pressure" => outcome.plasma_oncotic_end,
            "isf_oncotic_pressure" => outcome.isf_oncotic_end,
            "plasma_osmolality" => outcome.osmolality_end,
            "plasma_sodium" => outcome.sodium_end,
            "plasma_adh" => outcome.adh_end,
            "urine_osmolality" => outcome.urine_osm_end,
            _ => stat_for(stats, &r.output),
        };
        let pass = value >= r.low && r.high.map(|h| value <= h).unwrap_or(true);
        let range_text = match r.high {
            Some(h) => format!("{} .. {}", r.low, h),
            None => format!(">= {}", r.low),
        };
        lines.push(ValidationLine {
            output: r.output.clone(),
            value,
            unit: r.unit.clone(),
            range_text,
            source: r.source.clone(),
            soft: SOFT_OUTPUTS.contains(&r.output.as_str()),
            pass,
        });
    }
    lines
}

#[derive(Debug, Clone)]
pub struct PerturbationLine {
    pub output: String,
    pub baseline: f64,
    pub post: f64,
    pub delta: f64,
    pub expected: String,
    /// The published band from parameters.json, when this expectation
    /// carries a Milestone 18 magnitude gate.
    pub magnitude_range: Option<[f64; 2]>,
    /// Soft lines are reported and disclosed but do not fail
    /// validation (see params::Expectation::soft).
    pub soft: bool,
    pub source: String,
    pub pass: bool,
}

pub fn evaluate_perturbation(
    params: &Params,
    case_id: &str,
    outcome: &CaseOutcome,
) -> Vec<PerturbationLine> {
    let case = params
        .perturbation_case(case_id)
        .unwrap_or_else(|| panic!("perturbation case '{case_id}' missing from parameters.json"));
    case.expectations
        .iter()
        .map(|x| {
            let b = stat_for(&outcome.baseline, &x.output);
            let p = stat_for(&outcome.post, &x.output);
            let direction_pass = match x.direction.as_str() {
                "rises" => p > b,
                "falls" => p < b,
                "narrows" => p < b,
                // "in_range": no directional requirement; the band
                // check below is the whole expectation.
                "in_range" => true,
                _ => false,
            };
            let range_pass = match x.magnitude_range {
                Some([lo, hi]) => p >= lo && p <= hi,
                None => true,
            };
            PerturbationLine {
                output: x.output.clone(),
                baseline: b,
                post: p,
                delta: p - b,
                expected: x.direction.clone(),
                magnitude_range: x.magnitude_range,
                soft: x.soft,
                source: x.source.clone(),
                pass: direction_pass && range_pass,
            }
        })
        .collect()
}

/// The Milestone 18 long-horizon refill observation: the standard
/// settle/baseline/engage protocol, a 750 mL haemorrhage over 60 s,
/// then 30 minutes of undisturbed simulated time after the bleed
/// ends. Samples the mechanism states as the trajectory unfolds.
#[derive(Debug, Clone)]
pub struct RefillOutcome {
    /// (minutes after bleed end, net refill mL, recruited mL)
    pub samples: Vec<(f64, f64, f64)>,
    pub refill_30min_ml: f64,
    pub refill_fraction_of_loss: f64,
    /// Post-observation window (last 30 s) haemodynamics.
    pub final_window: WindowStats,
    pub trace_hash: u64,
    pub conservation_error_ml: f64,
}

pub fn run_refill_observation(params: &Params) -> RefillOutcome {
    let mut e = Engine::new(params);
    e.tick_n(4500);
    let b0 = e.beats.len();
    e.tick_n(1500);
    let b1 = e.beats.len();
    let baseline = window_stats(&e.beats[b0..b1]);
    e.set_reflex_setpoint(baseline.map);
    e.apply(
        6000,
        Event::SetExtFlow {
            rate_ml_s: -750.0 / 60.0,
            label: "haemorrhage 750 mL over 60 s begins".to_string(),
        },
    );
    e.apply(
        9000,
        Event::SetExtFlow {
            rate_ml_s: 0.0,
            label: "haemorrhage ends (750 mL removed)".to_string(),
        },
    );
    // Bleed ends at tick 9000 (t = 180 s). Sample at +1, +5, +10,
    // +20, +30 min after the bleed ends.
    let marks_min = [1.0, 5.0, 10.0, 20.0, 30.0];
    let mut samples = Vec::new();
    let mut target_tick = 9000u64;
    for m in marks_min {
        let t = 9000 + (m * 60.0 / crate::engine::TICK_SECONDS) as u64;
        e.tick_n(t - target_tick);
        target_tick = t;
        samples.push((m, e.net_refill_ml(), e.recruited_ml()));
    }
    let refill_30min_ml = samples.last().map(|s| s.1).unwrap_or(0.0);
    // Final window: beats of the last 30 s of the run.
    let n = e.beats.len();
    let from = n.saturating_sub(31);
    let final_window = window_stats(&e.beats[from..n.max(from)]);
    RefillOutcome {
        samples,
        refill_30min_ml,
        refill_fraction_of_loss: refill_30min_ml / 750.0,
        final_window,
        trace_hash: e.hash(),
        conservation_error_ml: e.volume_conservation_error_ml(),
    }
}

/// Milestone 24: the −1,500 mL haemorrhage COURSE — the standard
/// settle/baseline/engage protocol and the 60-second bleed of
/// `hemorrhage_1500`, then an hour of simulated course, sampled at
/// marks after the bleed ends. Two arms: untreated, and treated
/// with the ATLS initial fluid bolus (1,000 mL crystalloid over
/// 60 s beginning when the bleed ends — the scenario-input side;
/// parameters.json S20). The standard case protocol's post window
/// (30–60 s after the bleed ends) samples the transient nadir of a
/// 60-second bleed; this runner exists because the ATLS classes
/// and the textbook haemorrhage course are stated on presentation
/// timescales, not at the nadir (MILESTONE-24.md).
///
/// Milestone 26: two product arms join the course (whole blood,
/// components — see CourseArm), the samples carry the oncotic
/// states, and evaluation runs over the four-arm CourseSet.
#[derive(Debug, Clone)]
pub struct CourseSample {
    pub minutes_after_bleed_end: f64,
    /// Haemodynamics over the 30 s ending at the mark.
    pub window: WindowStats,
    pub stressed_sys_ml: f64,
    pub msfp_mmhg: f64,
    pub mcfp_mmhg: f64,
    pub recruited_ml: f64,
    pub refill_ml: f64,
    pub contractility: f64,
    /// Milestone 25 volume-side states at the mark: cumulative
    /// urine output and intake since run start (mL), the
    /// interstitial reservoir's current volume (mL), and the total
    /// intravascular volume (compartment sum, mL) — the last is
    /// what the treated arm's bolus retention is measured on.
    pub urine_ml: f64,
    pub intake_ml: f64,
    pub isf_ml: f64,
    pub blood_volume_ml: f64,
    /// Milestone 26 oncotic states at the mark: hematocrit
    /// (tracked-but-inert), plasma and interstitial oncotic
    /// pressures (mmHg), and the cumulative product volume (mL).
    pub hematocrit: f64,
    pub plasma_oncotic_mmhg: f64,
    pub isf_oncotic_mmhg: f64,
    pub product_ml: f64,
    /// Milestone 30 hormonal states at the mark: calculated plasma
    /// osmolality (mOsm/kg), plasma sodium (mmol/L), plasma AVP
    /// (pg/mL), the aldosterone effect state (normalised), the
    /// urine osmolality readout (mOsm/kg), and the cumulative
    /// urinary sodium (mmol) — the last is what the interval sodium
    /// excretion rates are differenced from.
    pub osmolality_mosm_kg: f64,
    pub sodium_mmol_l: f64,
    pub adh_pg_ml: f64,
    pub aldo_state: f64,
    pub urine_osmolality_mosm_kg: f64,
    pub urine_na_mmol: f64,
}

/// The course arms (Milestone 26 generalises Milestone 24's two):
/// untreated; the ATLS crystalloid bolus; whole blood (2 units);
/// and components (2 units PRBC then 2 units plasma, sequentially
/// at the same nominal rate). All product arms start when the bleed
/// ends, like the bolus.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CourseArm {
    Untreated,
    Crystalloid,
    WholeBlood,
    Components,
}

#[derive(Debug, Clone)]
pub struct CourseOutcome {
    pub arm: CourseArm,
    pub samples: Vec<CourseSample>,
    pub trace_hash: u64,
    pub conservation_error_ml: f64,
}

/// The four arms' outcomes, evaluated together (Milestone 26).
#[derive(Debug, Clone)]
pub struct CourseSet {
    pub untreated: CourseOutcome,
    pub crystalloid: CourseOutcome,
    pub whole_blood: CourseOutcome,
    pub components: CourseOutcome,
}

/// Total input volume of an arm (mL), from parameters.json — the
/// retention metrics' denominators.
pub fn course_input_volume_ml(params: &Params, arm: CourseArm) -> f64 {
    match arm {
        CourseArm::Untreated => 0.0,
        CourseArm::Crystalloid => 1000.0,
        CourseArm::WholeBlood => 2.0 * params.f64("product_whole_blood_volume_ml"),
        CourseArm::Components => {
            2.0 * params.f64("product_prbc_volume_ml")
                + 2.0 * params.f64("product_plasma_volume_ml")
        }
    }
}

pub fn run_hemorrhage_1500_course(params: &Params, treated: bool) -> CourseOutcome {
    run_course_arm(
        params,
        if treated {
            CourseArm::Crystalloid
        } else {
            CourseArm::Untreated
        },
    )
}

pub fn run_course_arm(params: &Params, arm: CourseArm) -> CourseOutcome {
    run_course_arm_marks(params, arm, &[1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0])
}

/// The course runner with an explicit mark schedule (Milestone
/// 30): the standard course uses the marks above; the long-horizon
/// hormonal course reuses the identical protocol, arms and event
/// schedule with marks out to 12 h.
pub fn run_course_arm_marks(params: &Params, arm: CourseArm, marks_min: &[f64]) -> CourseOutcome {
    let mut e = Engine::new(params);
    e.tick_n(4500);
    let b0 = e.beats.len();
    e.tick_n(1500);
    let b1 = e.beats.len();
    let baseline = window_stats(&e.beats[b0..b1]);
    e.set_reflex_setpoint(baseline.map);
    e.apply(
        6000,
        Event::SetExtFlow {
            rate_ml_s: -1500.0 / 60.0,
            label: "haemorrhage 1500 mL over 60 s begins".to_string(),
        },
    );
    e.apply(
        9000,
        Event::SetExtFlow {
            rate_ml_s: 0.0,
            label: "haemorrhage ends (1500 mL removed)".to_string(),
        },
    );
    // Arm inputs, applied after the bleed events so at tick 9000
    // the bleed end (0.0) is processed before the input start.
    match arm {
        CourseArm::Untreated => {}
        CourseArm::Crystalloid => {
            e.apply(
                9000,
                Event::SetExtFlow {
                    rate_ml_s: 1000.0 / 60.0,
                    label: "ATLS initial bolus: 1000 mL crystalloid over 60 s begins".to_string(),
                },
            );
            e.apply(
                12000,
                Event::SetExtFlow {
                    rate_ml_s: 0.0,
                    label: "bolus ends (1000 mL given)".to_string(),
                },
            );
        }
        CourseArm::WholeBlood => {
            // 2 units over 60 s from the bleed end — the same window
            // as the crystalloid bolus, so the arms differ in
            // composition, not in schedule. Volume 1,026 mL (the
            // units' quantisation, product_whole_blood_volume_ml).
            let (vol, hct, prot) = e
                .model
                .product_spec("whole_blood")
                .expect("whole_blood product spec");
            let total = 2.0 * vol;
            e.apply(
                9000,
                Event::SetProductFlow {
                    rate_ml_s: total / 60.0,
                    hematocrit: hct,
                    protein_g_per_ml: prot,
                    label: format!("whole blood: 2 units ({total:.0} mL) over 60 s begins"),
                },
            );
            e.apply(
                12000,
                Event::SetProductFlow {
                    rate_ml_s: 0.0,
                    hematocrit: hct,
                    protein_g_per_ml: prot,
                    label: "whole blood ends (2 units given)".to_string(),
                },
            );
        }
        CourseArm::Components => {
            // 2 units PRBC then 2 units plasma, sequentially at the
            // crystalloid bolus's nominal rate (1000 mL / 60 s): the
            // PRBC segment runs 36 s (600 mL), the plasma segment
            // 27 s (450 mL) — components practice gives red cells
            // first, plasma after (the 1:1 component pairing of the
            // unit counts is the scenario's stated simplification;
            // no platelets or cryoprecipitate — the engine has no
            // coagulation state and claims none).
            let rate = 1000.0 / 60.0;
            let (pvol, phct, pprot) = e.model.product_spec("prbc").expect("prbc product spec");
            let (fvol, fhct, fprot) = e.model.product_spec("plasma").expect("plasma product spec");
            let prbc_total = 2.0 * pvol;
            let plasma_total = 2.0 * fvol;
            let prbc_ticks = (prbc_total / rate / crate::engine::TICK_SECONDS).round() as u64;
            let plasma_ticks = (plasma_total / rate / crate::engine::TICK_SECONDS).round() as u64;
            e.apply(
                9000,
                Event::SetProductFlow {
                    rate_ml_s: rate,
                    hematocrit: phct,
                    protein_g_per_ml: pprot,
                    label: format!("components: PRBC 2 units ({prbc_total:.0} mL) begins"),
                },
            );
            e.apply(
                9000 + prbc_ticks,
                Event::SetProductFlow {
                    rate_ml_s: rate,
                    hematocrit: fhct,
                    protein_g_per_ml: fprot,
                    label: format!("components: plasma 2 units ({plasma_total:.0} mL) begins"),
                },
            );
            e.apply(
                9000 + prbc_ticks + plasma_ticks,
                Event::SetProductFlow {
                    rate_ml_s: 0.0,
                    hematocrit: fhct,
                    protein_g_per_ml: fprot,
                    label: "components end (2 units PRBC + 2 units plasma given)".to_string(),
                },
            );
        }
    }
    // Cumulative beat end-times (beats tile simulated time), for
    // exact 30 s windows ending at each mark.
    let mut beat_ends: Vec<f64> = Vec::new();
    let mut t_acc = 0.0;
    let mut seen = 0usize;
    let sync_beats = |e: &Engine, beat_ends: &mut Vec<f64>, t_acc: &mut f64, seen: &mut usize| {
        while *seen < e.beats.len() {
            *t_acc += e.beats[*seen].duration_s;
            beat_ends.push(*t_acc);
            *seen += 1;
        }
    };
    sync_beats(&e, &mut beat_ends, &mut t_acc, &mut seen);
    let mut samples = Vec::new();
    let mut target_tick = 6000u64;
    for &m in marks_min {
        let t = 9000 + (m * 60.0 / crate::engine::TICK_SECONDS) as u64;
        e.tick_n(t - target_tick);
        target_tick = t;
        sync_beats(&e, &mut beat_ends, &mut t_acc, &mut seen);
        let t_end = t as f64 * crate::engine::TICK_SECONDS;
        let lo = beat_ends.partition_point(|&x| x <= t_end - 30.0);
        let hi = beat_ends.partition_point(|&x| x <= t_end);
        let window = window_stats(&e.beats[lo..hi.max(lo)]);
        samples.push(CourseSample {
            minutes_after_bleed_end: m,
            window,
            stressed_sys_ml: e.systemic_stressed_volume_ml(),
            msfp_mmhg: e.mean_systemic_filling_pressure(),
            mcfp_mmhg: e.mean_circulatory_filling_pressure(),
            recruited_ml: e.recruited_ml(),
            refill_ml: e.net_refill_ml(),
            contractility: e.contractility_multiplier(),
            urine_ml: e.cumulative_urine_ml(),
            intake_ml: e.cumulative_intake_ml(),
            isf_ml: e.interstitial_volume_ml(),
            blood_volume_ml: e.volumes().iter().sum(),
            hematocrit: e.hematocrit(),
            plasma_oncotic_mmhg: e.plasma_oncotic_mmhg(),
            isf_oncotic_mmhg: e.isf_oncotic_mmhg(),
            product_ml: e.cumulative_product_ml(),
            osmolality_mosm_kg: e.plasma_osmolality_mosm_kg(),
            sodium_mmol_l: e.plasma_sodium_mmol_l(),
            adh_pg_ml: e.adh_pg_ml(),
            aldo_state: e.aldosterone_state(),
            urine_osmolality_mosm_kg: e.urine_osmolality_mosm_kg(),
            urine_na_mmol: e.cumulative_urine_sodium_mmol(),
        });
    }
    CourseOutcome {
        arm,
        samples,
        trace_hash: e.hash(),
        conservation_error_ml: e.volume_conservation_error_ml(),
    }
}

#[derive(Debug, Clone)]
pub struct CourseLine {
    pub output: String,
    pub baseline: f64,
    pub post: f64,
    pub expected: String,
    pub magnitude_range: Option<[f64; 2]>,
    pub soft: bool,
    pub source: String,
    pub pass: bool,
}

fn course_at<'a>(outcome: &'a CourseOutcome, minutes: f64) -> &'a CourseSample {
    outcome
        .samples
        .iter()
        .find(|s| (s.minutes_after_bleed_end - minutes).abs() < 1e-9)
        .unwrap_or_else(|| panic!("course sample at {minutes} min missing"))
}

/// (baseline, post) pair for a course expectation output, from the
/// four arms (Milestone 26; "treated" in the Milestone 24/25 output
/// names is the crystalloid arm). For `in_range` lines
/// baseline == post == the value.
fn course_quantity(params: &Params, set: &CourseSet, output: &str) -> (f64, f64) {
    let untreated = &set.untreated;
    let treated = &set.crystalloid;
    match output {
        "map_recovery_untreated" => (
            course_at(untreated, 2.0).window.map,
            course_at(untreated, 30.0).window.map,
        ),
        "treated_map_advantage_10min" => (
            course_at(untreated, 10.0).window.map,
            course_at(treated, 10.0).window.map,
        ),
        "treated_co_advantage_10min" => (
            course_at(untreated, 10.0).window.co,
            course_at(treated, 10.0).window.co,
        ),
        "treated_hr_relief_10min" => (
            course_at(untreated, 10.0).window.hr,
            course_at(treated, 10.0).window.hr,
        ),
        "net_refill_ml_at_60min_untreated" => {
            let v = course_at(untreated, 60.0).refill_ml;
            (v, v)
        }
        "hr_untreated_30min" => {
            let v = course_at(untreated, 30.0).window.hr;
            (v, v)
        }
        "hr_treated_10min" => {
            let v = course_at(treated, 10.0).window.hr;
            (v, v)
        }
        // Milestone 25: how much of the 1,000 mL bolus is still
        // intravascular at +60 min, measured as the treated arm's
        // blood-volume advantage over the untreated arm (the
        // difference construction nets out the shared haemorrhage,
        // recruitment and intake).
        "bolus_retention_60min" => {
            let v = (course_at(treated, 60.0).blood_volume_ml
                - course_at(untreated, 60.0).blood_volume_ml)
                / 1000.0;
            (v, v)
        }
        // Milestone 26: the product arms on the same constructions.
        "wb_map_advantage_10min" => (
            course_at(untreated, 10.0).window.map,
            course_at(&set.whole_blood, 10.0).window.map,
        ),
        "wb_retention_60min" => {
            let v = (course_at(&set.whole_blood, 60.0).blood_volume_ml
                - course_at(untreated, 60.0).blood_volume_ml)
                / course_input_volume_ml(params, CourseArm::WholeBlood);
            (v, v)
        }
        "comp_retention_60min" => {
            let v = (course_at(&set.components, 60.0).blood_volume_ml
                - course_at(untreated, 60.0).blood_volume_ml)
                / course_input_volume_ml(params, CourseArm::Components);
            (v, v)
        }
        "wb_hematocrit_60min" => {
            let v = course_at(&set.whole_blood, 60.0).hematocrit;
            (v, v)
        }
        "wb_plasma_oncotic_60min" => {
            let v = course_at(&set.whole_blood, 60.0).plasma_oncotic_mmhg;
            (v, v)
        }
        "treated_plasma_oncotic_60min" => {
            let v = course_at(treated, 60.0).plasma_oncotic_mmhg;
            (v, v)
        }
        _ => panic!("unknown course output '{output}'"),
    }
}

/// Evaluate the course expectations in parameters.json (case
/// `hemorrhage_1500_course`) against the four arms.
pub fn evaluate_course(params: &Params, set: &CourseSet) -> Vec<CourseLine> {
    let case = params
        .perturbation_case("hemorrhage_1500_course")
        .expect("hemorrhage_1500_course case missing from parameters.json");
    case.expectations
        .iter()
        .map(|x| {
            let (b, p) = course_quantity(params, set, &x.output);
            let direction_pass = match x.direction.as_str() {
                "rises" => p > b,
                "falls" => p < b,
                "in_range" => true,
                _ => false,
            };
            let range_pass = match x.magnitude_range {
                Some([lo, hi]) => p >= lo && p <= hi,
                None => true,
            };
            CourseLine {
                output: x.output.clone(),
                baseline: b,
                post: p,
                expected: x.direction.clone(),
                magnitude_range: x.magnitude_range,
                soft: x.soft,
                source: x.source.clone(),
                pass: direction_pass && range_pass,
            }
        })
        .collect()
}

/// Evaluate the refill observation against the magnitude band in
/// parameters.json (case `refill_observation_750`). Returns
/// (measured mL, band, pass).
pub fn evaluate_refill(params: &Params, outcome: &RefillOutcome) -> (f64, [f64; 2], bool) {
    let case = params
        .perturbation_case("refill_observation_750")
        .expect("refill_observation_750 case missing from parameters.json");
    let exp = case
        .expectations
        .iter()
        .find(|x| x.output == "net_refill_ml_at_30min")
        .expect("net_refill_ml_at_30min expectation missing");
    let band = exp
        .magnitude_range
        .expect("refill expectation must carry a magnitude_range");
    let v = outcome.refill_30min_ml;
    (v, band, v >= band[0] && v <= band[1])
}

/// Milestone 25: the long-horizon resting run — the standard
/// settle/baseline/engage protocol, then a full hour of undisturbed
/// simulated time with the reflexes, the renal curve and intake all
/// active. Milestone 24's resting evidence was a 30-second window;
/// with an excretory pathway open, a slow drift (urine running
/// persistently above or below intake, the reservoir creeping)
/// would be invisible at that horizon. This runner proves the
/// resting state is a true steady state over an hour and measures
/// the equilibrium urine output against its cited band (S24).
#[derive(Debug, Clone)]
pub struct LongRestOutcome {
    /// Haemodynamics over the first 30 s after engagement (contains
    /// the engagement transient; reported, not gated).
    pub first_window: WindowStats,
    /// Haemodynamics over the 30 s ending at +30 min.
    pub mid_window: WindowStats,
    /// Haemodynamics over the last 30 s of the hour.
    pub last_window: WindowStats,
    /// Boundary totals over the engaged hour (engagement to +60 min).
    pub urine_engaged_hour_ml: f64,
    pub intake_engaged_hour_ml: f64,
    /// Mean urine output over the final 30 minutes (mL/min).
    pub final_uo_ml_min: f64,
    pub isf_at_engagement_ml: f64,
    pub isf_at_end_ml: f64,
    pub refill_at_end_ml: f64,
    pub trace_hash: u64,
    pub conservation_error_ml: f64,
}

pub fn run_long_rest(params: &Params) -> LongRestOutcome {
    let mut e = Engine::new(params);
    e.tick_n(4500);
    let b0 = e.beats.len();
    e.tick_n(1500);
    let b1 = e.beats.len();
    let baseline = window_stats(&e.beats[b0..b1]);
    e.set_reflex_setpoint(baseline.map);
    // Engagement is at tick 6000. Everything below is counted from
    // there: first window ticks 6000..7500, the +30 min mark is tick
    // 96000, the hour ends at tick 186000.
    let urine_engage = e.cumulative_urine_ml();
    let intake_engage = e.cumulative_intake_ml();
    let isf_at_engagement_ml = e.interstitial_volume_ml();
    let b2 = e.beats.len();
    e.tick_n(1500);
    let b3 = e.beats.len();
    let first_window = window_stats(&e.beats[b2..b3]);
    e.tick_n(87_000);
    let bm0 = e.beats.len();
    e.tick_n(1500);
    let bm1 = e.beats.len();
    let mid_window = window_stats(&e.beats[bm0..bm1]);
    let urine_30min = e.cumulative_urine_ml();
    e.tick_n(88_500);
    let b4 = e.beats.len();
    e.tick_n(1500);
    let b5 = e.beats.len();
    let last_window = window_stats(&e.beats[b4..b5]);
    let urine_end = e.cumulative_urine_ml();
    let intake_end = e.cumulative_intake_ml();
    LongRestOutcome {
        first_window,
        mid_window,
        last_window,
        urine_engaged_hour_ml: urine_end - urine_engage,
        intake_engaged_hour_ml: intake_end - intake_engage,
        final_uo_ml_min: (urine_end - urine_30min) / 30.0,
        isf_at_engagement_ml,
        isf_at_end_ml: e.interstitial_volume_ml(),
        refill_at_end_ml: e.net_refill_ml(),
        trace_hash: e.hash(),
        conservation_error_ml: e.volume_conservation_error_ml(),
    }
}

// ---------------------------------------------------------------------
// Milestone 30: the hormonal scenario arms. Each axis is exercised
// in its own regime, on its own timescale: ADH against a water load
// and against deprivation (minutes to hours), aldosterone against
// a sodium load (hours — its cited effect timescale), and both
// together on the −1,500 mL course extended to 12 h. All four arms
// use the standard settle/baseline/engage protocol; the
// intervention lands at engagement (tick 6000) through the event
// channels, and marks are sampled on 30 s windows like the course.

#[derive(Debug, Clone)]
pub struct HormoneSample {
    /// Minutes after the arm's mark origin (the load's end for the
    /// water-load arms, engagement for the others).
    pub minutes: f64,
    /// Haemodynamics over the 30 s ending at the mark.
    pub window: WindowStats,
    pub osmolality_mosm_kg: f64,
    pub sodium_mmol_l: f64,
    pub adh_pg_ml: f64,
    pub aldo_state: f64,
    pub urine_osmolality_mosm_kg: f64,
    /// Instantaneous rates at the mark (the sensed MAP is
    /// low-passed, so these are smooth, not beat statistics).
    pub urine_rate_ml_min: f64,
    pub urine_na_rate_mmol_min: f64,
    /// Boundary integrals and lump states at the mark.
    pub urine_ml: f64,
    pub urine_na_mmol: f64,
    pub na_mmol: f64,
    pub icf_ml: f64,
    pub isf_ml: f64,
    pub blood_volume_ml: f64,
}

#[derive(Debug, Clone)]
pub struct HormoneArmOutcome {
    pub baseline_window: WindowStats,
    /// The hormonal operating point at engagement (the states sit
    /// exactly on the constructed resting values there).
    pub resting_adh_pg_ml: f64,
    pub resting_osmolality_mosm_kg: f64,
    pub resting_urine_osmolality_mosm_kg: f64,
    pub na_at_engagement_mmol: f64,
    pub samples: Vec<HormoneSample>,
    pub trace_hash: u64,
    pub conservation_error_ml: f64,
}

/// The standard protocol's first three phases, shared by the
/// hormonal arms: settle, baseline window, engage at the model's
/// own resting MAP. Returns the engine at tick 6000, engaged.
fn engaged_engine(params: &Params) -> (Engine, WindowStats) {
    let mut e = Engine::new(params);
    e.tick_n(4500);
    let b0 = e.beats.len();
    e.tick_n(1500);
    let b1 = e.beats.len();
    let baseline = window_stats(&e.beats[b0..b1]);
    e.set_reflex_setpoint(baseline.map);
    (e, baseline)
}

/// Beat-window sampler on cumulative beat end-times (the course
/// runner's construction): exact 30 s windows ending at each mark.
struct MarkSampler {
    beat_ends: Vec<f64>,
    t_acc: f64,
    seen: usize,
}

impl MarkSampler {
    fn new(e: &Engine) -> MarkSampler {
        let mut s = MarkSampler {
            beat_ends: Vec::new(),
            t_acc: 0.0,
            seen: 0,
        };
        s.sync(e);
        s
    }

    fn sync(&mut self, e: &Engine) {
        while self.seen < e.beats.len() {
            self.t_acc += e.beats[self.seen].duration_s;
            self.beat_ends.push(self.t_acc);
            self.seen += 1;
        }
    }

    fn sample(&mut self, e: &Engine, minutes: f64, t_end_s: f64) -> HormoneSample {
        self.sync(e);
        let lo = self.beat_ends.partition_point(|&x| x <= t_end_s - 30.0);
        let hi = self.beat_ends.partition_point(|&x| x <= t_end_s);
        HormoneSample {
            minutes,
            window: window_stats(&e.beats[lo..hi.max(lo)]),
            osmolality_mosm_kg: e.plasma_osmolality_mosm_kg(),
            sodium_mmol_l: e.plasma_sodium_mmol_l(),
            adh_pg_ml: e.adh_pg_ml(),
            aldo_state: e.aldosterone_state(),
            urine_osmolality_mosm_kg: e.urine_osmolality_mosm_kg(),
            urine_rate_ml_min: e.urine_rate_ml_min(),
            urine_na_rate_mmol_min: e.urine_sodium_rate_mmol_min(),
            urine_ml: e.cumulative_urine_ml(),
            urine_na_mmol: e.cumulative_urine_sodium_mmol(),
            na_mmol: e.sodium_content_mmol(),
            icf_ml: e.icf_volume_ml(),
            isf_ml: e.interstitial_volume_ml(),
            blood_volume_ml: e.volumes().iter().sum(),
        }
    }
}

fn run_hormone_arm(
    params: &Params,
    apply_events: &dyn Fn(&mut Engine),
    mark_origin_tick: u64,
    marks_min: &[f64],
) -> HormoneArmOutcome {
    let (mut e, baseline_window) = engaged_engine(params);
    let resting_adh_pg_ml = e.adh_pg_ml();
    let resting_osmolality_mosm_kg = e.plasma_osmolality_mosm_kg();
    let resting_urine_osmolality_mosm_kg = e.urine_osmolality_mosm_kg();
    let na_at_engagement_mmol = e.sodium_content_mmol();
    apply_events(&mut e);
    let mut sampler = MarkSampler::new(&e);
    let mut samples = Vec::new();
    let mut target_tick = 6000u64;
    for &m in marks_min {
        let t = mark_origin_tick + (m * 60.0 / crate::engine::TICK_SECONDS) as u64;
        e.tick_n(t - target_tick);
        target_tick = t;
        samples.push(sampler.sample(&e, m, t as f64 * crate::engine::TICK_SECONDS));
    }
    HormoneArmOutcome {
        baseline_window,
        resting_adh_pg_ml,
        resting_osmolality_mosm_kg,
        resting_urine_osmolality_mosm_kg,
        na_at_engagement_mmol,
        samples,
        trace_hash: e.hash(),
        conservation_error_ml: e.volume_conservation_error_ml(),
    }
}

/// Water load: 1,000 mL of solute-free water over 60 s from
/// engagement, through the dedicated water channel (an intravenous
/// pure-water load — the crystalloid event channel carries sodium
/// and cannot express it; the oral route's absorption lag is not
/// modelled, disclosed in MILESTONE-30.md). Marks are minutes
/// after the load ends.
pub fn run_water_load(params: &Params) -> HormoneArmOutcome {
    run_hormone_arm(
        params,
        &|e: &mut Engine| {
            e.apply(
                6000,
                Event::SetWaterFlow {
                    rate_ml_s: 1000.0 / 60.0,
                    label: "water load: 1000 mL solute-free water over 60 s begins".to_string(),
                },
            );
            e.apply(
                9000,
                Event::SetWaterFlow {
                    rate_ml_s: 0.0,
                    label: "water load ends (1000 mL added)".to_string(),
                },
            );
        },
        9000,
        &[0.0, 15.0, 30.0, 45.0, 60.0, 120.0, 180.0, 240.0],
    )
}

/// The water load's paired control: the identical protocol with no
/// load, so the excess-urine difference nets out everything the two
/// runs share.
pub fn run_water_control(params: &Params) -> HormoneArmOutcome {
    run_hormone_arm(params, &|_| {}, 9000, &[0.0, 15.0, 30.0, 45.0, 60.0, 120.0, 180.0, 240.0])
}

/// Water deprivation: intake (water and sodium together) set to
/// zero at engagement, 12 h. The engine carries no insensible
/// losses, so urine is the only water exit — the bound that
/// defines this arm (MILESTONE-30.md).
pub fn run_water_deprivation(params: &Params) -> HormoneArmOutcome {
    run_hormone_arm(
        params,
        &|e: &mut Engine| {
            e.apply(
                6000,
                Event::SetIntake {
                    water_ml_min: 0.0,
                    sodium_mmol_min: 0.0,
                    label: "water deprivation: intake set to zero".to_string(),
                },
            );
        },
        6000,
        &[60.0, 180.0, 360.0, 540.0, 660.0, 720.0],
    )
}

/// Sodium load: sodium intake raised fivefold at engagement, with
/// water intake raised threefold in parallel, 24 h. The parallel
/// water rise follows the cited protocol (S44: Guyton's
/// salt-loading experiments raised salt AND water intake together,
/// water freely available) and is measured, not cosmetic: with
/// water intake held at baseline, the same 5x sodium load drives
/// the model onto a hypernatraemic branch ([Na+] 147 mmol/L,
/// osmolality 304, ADH 8 pg/mL at 24 h, sodium balance only 0.66)
/// because the engine has no thirst — intake is behavioural and
/// the fixed-water arm is the thirst caveat demonstrated
/// (MILESTONE-30.md). The RAAS/aldosterone regime: the axis's own
/// timescale is hours, and the coupled water/sodium
/// re-equilibration is slower still — at 12 h the arm had reached
/// only ~60% of sodium balance, which is why the arm runs a full
/// day.
pub fn run_sodium_load(params: &Params) -> HormoneArmOutcome {
    let water_in = 3.0 * params.f64("fluid_intake_ml_min");
    let na_in = 5.0 * params.f64("sodium_intake_mmol_min");
    run_hormone_arm(
        params,
        &|e: &mut Engine| {
            e.apply(
                6000,
                Event::SetIntake {
                    water_ml_min: water_in,
                    sodium_mmol_min: na_in,
                    label: "sodium load: sodium intake x5, water intake x3".to_string(),
                },
            );
        },
        6000,
        &[60.0, 180.0, 360.0, 540.0, 720.0, 1080.0, 1380.0, 1440.0],
    )
}

/// The −1,500 mL course extended to 12 h (untreated and
/// crystalloid arms), on the standard course protocol.
#[derive(Debug, Clone)]
pub struct LongCourseSet {
    pub untreated: CourseOutcome,
    pub crystalloid: CourseOutcome,
}

pub fn run_long_course(params: &Params) -> LongCourseSet {
    let marks = [
        1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0, 240.0, 360.0, 540.0, 720.0,
    ];
    LongCourseSet {
        untreated: run_course_arm_marks(params, CourseArm::Untreated, &marks),
        crystalloid: run_course_arm_marks(params, CourseArm::Crystalloid, &marks),
    }
}

/// All four hormonal arms plus the long course, evaluated together.
#[derive(Debug, Clone)]
pub struct HormoneSet {
    pub water_load: HormoneArmOutcome,
    pub water_control: HormoneArmOutcome,
    pub deprivation: HormoneArmOutcome,
    pub sodium_load: HormoneArmOutcome,
    pub long_course: LongCourseSet,
}

pub fn run_hormone_set(params: &Params) -> HormoneSet {
    HormoneSet {
        water_load: run_water_load(params),
        water_control: run_water_control(params),
        deprivation: run_water_deprivation(params),
        sodium_load: run_sodium_load(params),
        long_course: run_long_course(params),
    }
}

fn hormone_at<'a>(outcome: &'a HormoneArmOutcome, minutes: f64) -> &'a HormoneSample {
    outcome
        .samples
        .iter()
        .find(|s| (s.minutes - minutes).abs() < 1e-9)
        .unwrap_or_else(|| panic!("hormone sample at {minutes} min missing"))
}

/// Peak interval urine-flow ratio of the water-load arm: the
/// highest mean urine flow over the mark-to-mark intervals after
/// the load, over the resting baseline flow; and the mark at which
/// that interval ends (its urine osmolality is the paired readout).
fn water_peak_flow(params: &Params, set: &HormoneSet) -> (f64, f64) {
    let samples = &set.water_load.samples;
    let rest = params.f64("baseline_urine_output_ml_min");
    let mut best = (0.0f64, 0.0f64);
    for w in samples.windows(2) {
        let rate = (w[1].urine_ml - w[0].urine_ml) / (w[1].minutes - w[0].minutes);
        if rate / rest > best.0 {
            best = (rate / rest, w[1].minutes);
        }
    }
    best
}

/// (baseline, post) pair for a hormonal expectation output, in the
/// course_quantity pattern: directional lines pair the resting
/// value with the arm's value; `in_range` lines carry the measured
/// quantity twice.
fn hormone_quantity(params: &Params, set: &HormoneSet, output: &str) -> (f64, f64) {
    match output {
        // --- water load ---
        "plasma_osmolality_nadir" => {
            let v = set
                .water_load
                .samples
                .iter()
                .map(|s| s.osmolality_mosm_kg)
                .fold(f64::INFINITY, f64::min);
            (v, v)
        }
        "adh_at_45min" => (
            set.water_load.resting_adh_pg_ml,
            hormone_at(&set.water_load, 45.0).adh_pg_ml,
        ),
        "urine_flow_peak_ratio" => {
            let v = water_peak_flow(params, set).0;
            (v, v)
        }
        "urine_osmolality_at_peak_flow" => {
            let end_min = water_peak_flow(params, set).1;
            let v = hormone_at(&set.water_load, end_min).urine_osmolality_mosm_kg;
            (v, v)
        }
        "excess_urine_4h_ml" => {
            let v = set.water_load.samples.last().unwrap().urine_ml
                - set.water_control.samples.last().unwrap().urine_ml;
            (v, v)
        }
        // --- water deprivation ---
        "adh_late" => (
            set.deprivation.resting_adh_pg_ml,
            hormone_at(&set.deprivation, 720.0).adh_pg_ml,
        ),
        "urine_flow_late" => {
            let v = (hormone_at(&set.deprivation, 720.0).urine_ml
                - hormone_at(&set.deprivation, 660.0).urine_ml)
                / 60.0;
            (params.f64("baseline_urine_output_ml_min"), v)
        }
        "urine_osmolality_late" => (
            set.deprivation.resting_urine_osmolality_mosm_kg,
            hormone_at(&set.deprivation, 720.0).urine_osmolality_mosm_kg,
        ),
        "plasma_osmolality_late" => {
            let v = hormone_at(&set.deprivation, 720.0).osmolality_mosm_kg;
            (v, v)
        }
        // --- sodium load (24 h arm; "late" = the final hour) ---
        "aldosterone_late" => (1.0, hormone_at(&set.sodium_load, 1440.0).aldo_state),
        "urine_sodium_balance_late" => {
            let rate = (hormone_at(&set.sodium_load, 1440.0).urine_na_mmol
                - hormone_at(&set.sodium_load, 1380.0).urine_na_mmol)
                / 60.0;
            let v = rate / (5.0 * params.f64("sodium_intake_mmol_min"));
            (v, v)
        }
        "map_rise_late" => {
            let v = hormone_at(&set.sodium_load, 1440.0).window.map
                - set.sodium_load.baseline_window.map;
            (v, v)
        }
        "sodium_retained_mmol" => {
            let v = hormone_at(&set.sodium_load, 1440.0).na_mmol
                - set.sodium_load.na_at_engagement_mmol;
            (v, v)
        }
        // --- long course ---
        "untreated_adh_60min" => (
            Engine::new(params).adh_pg_ml(),
            course_at(&set.long_course.untreated, 60.0).adh_pg_ml,
        ),
        "untreated_aldo_6h" => (
            1.0,
            course_at(&set.long_course.untreated, 360.0).aldo_state,
        ),
        "untreated_urine_sodium_6h" => {
            let v = (course_at(&set.long_course.untreated, 360.0).urine_na_mmol
                - course_at(&set.long_course.untreated, 240.0).urine_na_mmol)
                / 120.0;
            (params.f64("baseline_sodium_excretion_mmol_min"), v)
        }
        "untreated_map_recovery_long" => (
            course_at(&set.long_course.untreated, 60.0).window.map,
            course_at(&set.long_course.untreated, 720.0).window.map,
        ),
        "treated_map_advantage_6h" => (
            course_at(&set.long_course.untreated, 360.0).window.map,
            course_at(&set.long_course.crystalloid, 360.0).window.map,
        ),
        _ => panic!("unknown hormone output '{output}'"),
    }
}

/// Evaluate the four hormonal cases in parameters.json against the
/// arm outcomes. Lines are prefixed with their case id so the four
/// cases can share one table.
pub fn evaluate_hormones(params: &Params, set: &HormoneSet) -> Vec<PerturbationLine> {
    let mut lines = Vec::new();
    for case_id in [
        "water_load_1000",
        "water_deprivation_12h",
        "sodium_load_5x",
        "hemorrhage_1500_course_long",
    ] {
        let case = params
            .perturbation_case(case_id)
            .unwrap_or_else(|| panic!("perturbation case '{case_id}' missing from parameters.json"));
        for x in &case.expectations {
            let (b, p) = hormone_quantity(params, set, &x.output);
            let direction_pass = match x.direction.as_str() {
                "rises" => p > b,
                "falls" => p < b,
                "in_range" => true,
                _ => false,
            };
            let range_pass = match x.magnitude_range {
                Some([lo, hi]) => p >= lo && p <= hi,
                None => true,
            };
            lines.push(PerturbationLine {
                output: format!("{case_id}::{}", x.output),
                baseline: b,
                post: p,
                delta: p - b,
                expected: x.direction.clone(),
                magnitude_range: x.magnitude_range,
                soft: x.soft,
                source: x.source.clone(),
                pass: direction_pass && range_pass,
            });
        }
    }
    lines
}

