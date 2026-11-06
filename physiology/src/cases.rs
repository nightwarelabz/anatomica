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
    let b2 = e.beats.len();
    e.tick_n(1500);
    let b3 = e.beats.len();
    let post = window_stats(&e.beats[b2..b3]);
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

pub fn evaluate_resting(params: &Params, stats: &WindowStats) -> Vec<ValidationLine> {
    let mut lines = Vec::new();
    for r in &params.file.validation_ranges {
        let value = stat_for(stats, &r.output);
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
}

#[derive(Debug, Clone)]
pub struct CourseOutcome {
    pub treated: bool,
    pub samples: Vec<CourseSample>,
    pub trace_hash: u64,
    pub conservation_error_ml: f64,
}

pub fn run_hemorrhage_1500_course(params: &Params, treated: bool) -> CourseOutcome {
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
    if treated {
        // Applied after the bleed events, so at tick 9000 the bleed
        // end (0.0) is processed before the bolus start.
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
    let marks_min = [1.0f64, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0];
    let mut samples = Vec::new();
    let mut target_tick = 6000u64;
    for m in marks_min {
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
        });
    }
    CourseOutcome {
        treated,
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
/// two arms. For `in_range` lines baseline == post == the value.
fn course_quantity(untreated: &CourseOutcome, treated: &CourseOutcome, output: &str) -> (f64, f64) {
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
        _ => panic!("unknown course output '{output}'"),
    }
}

/// Evaluate the course expectations in parameters.json (case
/// `hemorrhage_1500_course`) against the two arms.
pub fn evaluate_course(
    params: &Params,
    untreated: &CourseOutcome,
    treated: &CourseOutcome,
) -> Vec<CourseLine> {
    let case = params
        .perturbation_case("hemorrhage_1500_course")
        .expect("hemorrhage_1500_course case missing from parameters.json");
    case.expectations
        .iter()
        .map(|x| {
            let (b, p) = course_quantity(untreated, treated, &x.output);
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
