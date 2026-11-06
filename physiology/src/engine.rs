//! Deterministic lumped-parameter cardiovascular core.
//!
//! Architecture per design/04 (Pulse-derived circuit analog): eight volume
//! compartments — LV, systemic arteries, systemic capillaries, systemic
//! veins, RV, pulmonary arteries, pulmonary capillaries, pulmonary veins —
//! with the two ventricles as time-varying-elastance chambers after the
//! published model in parameters.json source S1:
//!
//!   diastolic:  Pd(V)  = A * (exp(K*(V - Vu)) - 1)
//!   systolic:   Ps(V,Q) = E * (V - Vd) * (1 - KR*Q) * v(t)
//!   chamber:    P = Pd * (1 - v(t)) + Ps,   v(t) = sin^2(pi * tau / tv)
//!   valves:     Bernoulli law deltaP = B * Q^2 (+ a small, flagged linear
//!               regularisation and any series segment resistance), one-way.
//!   vessels:    P = (V - Vu) / C,  Q = deltaP / R.
//!
//! Determinism contract (design/04): fixed 20 ms tick, integer tick
//! counter, fixed-order RK4 integration at a fixed substep, no wall clock,
//! no randomness anywhere. Same initial state + same event stream gives a
//! bit-identical trace hash on every run.
//!
//! Milestone 18 adds the two compensatory mechanisms v0 omitted:
//! baroreflex venomotor recruitment (the reflex's third effector — a
//! first-order shift of venous unstressed into stressed volume at the
//! cited capacity and time constant, parameters.json S13) and
//! transcapillary refill (a lumped Starling flow driven by the deficit
//! of low-passed mean capillary pressure below its own resting value,
//! bounded by a cited interstitial reserve, S14/S15). Both are extra
//! ODE states in the same RK4 integration and are folded into the
//! trace hash like every other state.
//!
//! Milestone 21 adds the reflex's fourth effector, the one Milestone
//! 18 named as the binding omission at −1,500 mL: baroreflex
//! contractility (inotropy). A single multiplier state scales both
//! ventricles' maximal elastance (S1's E), driven by the same MAP
//! error signal, first-order at the cited heart-effector time
//! constant (S13, tau_h = 3 s) toward a target spanning the cited
//! ±20% elastance swing (S13 eq. S25 with Tables S1/S7: both
//! ventricles' targets pass through their resting elastances at
//! resting sympathetic activity and swing the identical fraction).
//! Same integration and trace-hash discipline as every other state.
//!
//! Milestone 24 adds no state and no mechanism. It makes the
//! circuit's Guyton venous-return formulation explicit and
//! measurable: the systemic stressed volume and mean systemic
//! filling pressure (MSFP = stressed volume / systemic compliance)
//! and the whole-circuit mean circulatory filling pressure (MCFP,
//! by the stop-flow equilibration construction) are computed
//! functions of state; a right-atrial-pressure proxy (the
//! flow-weighted mean RV pressure during tricuspid inflow — this
//! model has no atrium compartment) is accumulated per beat; and
//! the resistance to venous return is available both empirically,
//! (MSFP − RAP)/CO, and by the series-circuit compliance weighting.
//! At the resting operating point the two agree, which is the
//! formulation's verification: the lumped circuit already IS a
//! Guyton system, and venous return needs no new machinery. The
//! Milestone 21 −1,500 mL question is answered on the scenario side
//! instead (see cases.rs, the haemorrhage course runner, and
//! MILESTONE-24.md).

use crate::params::Params;

pub const TICK_SECONDS: f64 = 0.02;

// Volume vector indices.
pub const LV: usize = 0;
pub const SA: usize = 1;
pub const SC: usize = 2;
pub const SV: usize = 3;
pub const RV: usize = 4;
pub const PA: usize = 5;
pub const PC: usize = 6;
pub const PV: usize = 7;

/// Physical/numerical constants resolved once from the parameter file.
#[derive(Debug, Clone)]
pub struct Model {
    pub substep: f64,
    pub hr0: f64,
    pub tv0: f64,
    pub tv_exp: f64,
    pub b_av_valve: f64,       // Bernoulli coefficient, 7 cm^2 AV valves
    pub b_semilunar_valve: f64, // Bernoulli coefficient, 5 cm^2 semilunar valves
    pub valve_reg_r: f64,
    // vessels: (compliance, unstressed volume, outflow resistance)
    pub sa: (f64, f64, f64),
    pub sc: (f64, f64, f64),
    pub sv: (f64, f64, f64),
    pub pa: (f64, f64, f64),
    pub pc: (f64, f64, f64),
    pub pv: (f64, f64, f64),
    // ventricles
    pub lv: Ventricle,
    pub rv: Ventricle,
    // baroreflex (all gains VERIFY-flagged engineering placeholders)
    pub reflex_tau: f64,
    pub reflex_gain_hr: f64,
    pub reflex_gain_r: f64,
    pub reflex_hr_bounds: [f64; 2],
    pub reflex_r_bounds: [f64; 2],
    // venomotor recruitment (Milestone 18): capacity and time constant
    // cited (S13, published baroreflex model); gain VERIFY-flagged.
    pub veno_capacity_ml: f64,
    pub veno_tau: f64,
    pub veno_gain: f64,
    // transcapillary refill (Milestone 18): conductance calibrated
    // within a band derived from S14/S15 human data; reserve cited.
    pub refill_k: f64,
    pub refill_reserve_ml: f64,
    // contractility / inotropy (Milestone 21): time constant and the
    // +/- swing fraction of maximal elastance cited (S13, eq. S25,
    // Tables S1/S7); gain VERIFY-flagged like the other effector gains.
    pub ino_tau: f64,
    pub ino_swing: f64,
    pub ino_gain: f64,
}

#[derive(Debug, Clone, Copy)]
pub struct Ventricle {
    pub a: f64,
    pub k: f64,
    pub vu_d: f64,
    pub e: f64,
    pub vd: f64,
    pub kr: f64,
}

fn bernoulli_b(rho_kg_m3: f64, area_cm2: f64) -> f64 {
    // deltaP[mmHg] = B * Q[mL/s]^2, from deltaP = rho/(2 A^2) * Q^2 (SI),
    // Q_SI = Q_mL * 1e-6 m^3/s, 1 mmHg = 133.322 Pa.
    let a_m2 = area_cm2 * 1e-4;
    rho_kg_m3 * 1e-12 / (2.0 * a_m2 * a_m2 * 133.322)
}

impl Model {
    pub fn from_params(p: &Params) -> Model {
        let rho = p.f64("blood_density_kg_m3");
        Model {
            substep: p.f64("substep_seconds"),
            hr0: p.f64("heart_rate_baseline_bpm"),
            tv0: p.f64("ventricular_systole_seconds_at_1s_cycle"),
            tv_exp: p.f64("systole_duration_hr_exponent"),
            b_av_valve: bernoulli_b(rho, p.f64("valve_area_av_cm2")),
            b_semilunar_valve: bernoulli_b(rho, p.f64("valve_area_semilunar_cm2")),
            valve_reg_r: p.f64("valve_regularization_r"),
            sa: (
                p.f64("c_systemic_arteries"),
                p.f64("vu_systemic_arteries"),
                p.f64("r_systemic_arteries"),
            ),
            sc: (
                p.f64("c_systemic_capillaries"),
                p.f64("vu_systemic_capillaries"),
                p.f64("r_systemic_capillaries"),
            ),
            sv: (
                p.f64("c_systemic_veins"),
                p.f64("vu_systemic_veins"),
                p.f64("r_systemic_veins"),
            ),
            pa: (
                p.f64("c_pulmonary_arteries"),
                p.f64("vu_pulmonary_arteries"),
                p.f64("r_pulmonary_arteries"),
            ),
            pc: (
                p.f64("c_pulmonary_capillaries"),
                p.f64("vu_pulmonary_capillaries"),
                p.f64("r_pulmonary_capillaries"),
            ),
            pv: (
                p.f64("c_pulmonary_veins"),
                p.f64("vu_pulmonary_veins"),
                p.f64("r_pulmonary_veins"),
            ),
            lv: Ventricle {
                a: p.f64("lv_diastolic_a"),
                k: p.f64("lv_diastolic_k"),
                vu_d: p.f64("lv_diastolic_vu"),
                e: p.f64("lv_emax"),
                vd: p.f64("lv_vd"),
                kr: p.f64("lv_kr"),
            },
            rv: Ventricle {
                a: p.f64("rv_diastolic_a"),
                k: p.f64("rv_diastolic_k"),
                vu_d: p.f64("rv_diastolic_vu"),
                e: p.f64("rv_emax"),
                vd: p.f64("rv_vd"),
                kr: p.f64("rv_kr"),
            },
            reflex_tau: p.f64("reflex_tau_seconds"),
            reflex_gain_hr: p.f64("reflex_gain_hr"),
            reflex_gain_r: p.f64("reflex_gain_resistance"),
            reflex_hr_bounds: p.bounds("reflex_hr_mult_bounds"),
            reflex_r_bounds: p.bounds("reflex_r_mult_bounds"),
            veno_capacity_ml: p.f64("venomotor_capacity_ml"),
            veno_tau: p.f64("venomotor_tau_seconds"),
            veno_gain: p.f64("venomotor_gain"),
            refill_k: p.f64("refill_conductance_ml_s_mmhg"),
            refill_reserve_ml: p.f64("refill_reserve_ml"),
            ino_tau: p.f64("contractility_tau_seconds"),
            ino_swing: p.f64("contractility_swing_fraction"),
            ino_gain: p.f64("contractility_gain"),
        }
    }
}

#[derive(Debug, Clone, Copy, Default)]
pub struct Pressures {
    pub lv: f64,
    pub sa: f64,
    pub sc: f64,
    pub sv: f64,
    pub rv: f64,
    pub pa: f64,
    pub pc: f64,
    pub pv: f64,
}

#[derive(Debug, Clone, Copy, Default)]
pub struct Flows {
    pub aortic_valve: f64,
    pub mitral_valve: f64,
    pub tricuspid_valve: f64,
    pub pulmonary_valve: f64,
    pub systemic_arterial: f64,
    pub systemic_peripheral: f64,
    pub pulmonary_arterial: f64,
    pub pulmonary_capillary: f64,
}

/// One completed cardiac cycle's measured outputs.
#[derive(Debug, Clone)]
pub struct BeatRecord {
    pub index: u64,
    pub duration_s: f64,
    pub hr_bpm: f64,
    pub sbp: f64,
    pub dbp: f64,
    pub map: f64,
    pub pulse_pressure: f64,
    pub sv_lv_ml: f64,
    pub sv_rv_ml: f64,
    pub co_l_min: f64,
    pub cvp: f64,
    /// Right-atrial-pressure proxy (Milestone 24): the flow-weighted
    /// mean RV pressure during tricuspid inflow over the beat — the
    /// pressure against which the systemic veins drain in this
    /// atrium-less model. NOT the venous reservoir pressure (that is
    /// `cvp`, upstream of the venous outflow resistance and the
    /// tricuspid valve).
    pub rap: f64,
    /// Flow-weighted moments of tricuspid inflow over the beat
    /// (Milestone 24): fill_q2_mean = ∫q²dt/∫qdt (mL/s) and
    /// fill_q3_mean = ∫q³dt/∫qdt ((mL/s)²). Because inflow is
    /// confined to diastole, these exceed the mean flow and its
    /// square; they are what the venous outflow segment's effective
    /// resistance must be evaluated at (see
    /// resistance_to_venous_return_formula).
    pub fill_q2_mean: f64,
    pub fill_q3_mean: f64,
    pub pa_systolic: f64,
    pub pa_diastolic: f64,
    pub pa_mean: f64,
    pub pv_mean: f64,
}

#[derive(Debug, Clone)]
pub enum Event {
    /// Set the external volume flow into/out of the systemic venous
    /// compartment (mL/s; negative removes volume — haemorrhage).
    SetExtFlow { rate_ml_s: f64, label: String },
}

#[derive(Debug, Clone)]
pub struct LogEntry {
    pub tick: u64,
    pub text: String,
}

#[derive(Debug, Clone, Default)]
struct BeatAcc {
    time: f64,
    sa_int: f64,
    pa_int: f64,
    sv_int: f64,
    pv_int: f64,
    q_av_int: f64,
    q_pvv_int: f64,
    // Milestone 24 RAP proxy accumulators: time integrals of
    // (tricuspid flow x RV pressure), of tricuspid flow, and of its
    // second and third powers (the pulsatile-resistance moments).
    rv_fill_pq: f64,
    rv_fill_q: f64,
    rv_fill_q2: f64,
    rv_fill_q3: f64,
    sa_max: f64,
    sa_min: f64,
    pa_max: f64,
    pa_min: f64,
}

#[derive(Debug, Clone)]
pub struct Engine {
    pub model: Model,
    pub tick: u64,
    v: [f64; 8],
    map_lp: f64,
    /// Low-passed mean systemic capillary pressure (the refill sensor;
    /// same sensing lag as the baroreflex MAP channel).
    cap_lp: f64,
    /// Capillary-pressure reference captured when the reflex engages
    /// (the model's own resting capillary pressure — the refill
    /// mechanism's zero, like the MAP setpoint).
    cap_ref: Option<f64>,
    /// Recruited venous volume (mL): the amount by which sympathetic
    /// venoconstriction has currently reduced the systemic venous
    /// unstressed volume (negative = dilation below resting tone).
    veno_ml: f64,
    /// Net cumulative transcapillary transfer into the circulation
    /// (mL): positive = interstitial-to-plasma refill, negative =
    /// net escape. The interstitium is not a compartment; this state
    /// is the integral of the refill flow and an external inflow for
    /// volume accounting, like the external-flow integral.
    refill_ml: f64,
    /// Contractility multiplier (Milestone 21): the baroreflex
    /// inotropy state — a dimensionless scale on both ventricles'
    /// maximal elastance. 1.0 at the resting operating point; the
    /// reflex drives it within 1 +/- the cited swing fraction (S13).
    ino_mult: f64,
    tau: f64,
    ext_flow_ml_s: f64,
    ext_integral_ml: f64,
    total_volume_0: f64,
    setpoint_map: Option<f64>,
    events: Vec<(u64, Event)>,
    pub log: Vec<LogEntry>,
    acc: BeatAcc,
    pub beats: Vec<BeatRecord>,
    hash: u64,
}

const FNV_OFFSET: u64 = 0xcbf29ce484222325;
const FNV_PRIME: u64 = 0x100000001b3;

fn fnv_fold(hash: u64, bytes: &[u8]) -> u64 {
    let mut h = hash;
    for &b in bytes {
        h ^= b as u64;
        h = h.wrapping_mul(FNV_PRIME);
    }
    h
}

fn activation(tau: f64, period: f64, tv: f64) -> f64 {
    let t = tau % period;
    if t <= 0.0 || t >= tv {
        0.0
    } else {
        let s = (std::f64::consts::PI * t / tv).sin();
        s * s
    }
}

/// One-way valve flow under the Bernoulli law with a linear series term:
/// solves B*Q^2 + lin*Q = dp for Q >= 0; zero when dp <= 0.
fn valve_flow(dp: f64, b: f64, lin: f64) -> f64 {
    if dp <= 0.0 {
        0.0
    } else {
        (-lin + (lin * lin + 4.0 * b * dp).sqrt()) / (2.0 * b)
    }
}

struct Eval {
    pressures: Pressures,
    flows: Flows,
    derivs: [f64; 8],
    d_map_lp: f64,
    d_cap_lp: f64,
    d_veno: f64,
    d_refill: f64,
    d_ino: f64,
}

impl Engine {
    pub fn new(params: &Params) -> Engine {
        let model = Model::from_params(params);
        let tbv = params.f64("total_blood_volume_ml");
        // Initial conditions only (the closed loop's steady state is set by
        // total volume + parameters, not by the initial distribution):
        // vessels start at Vu + C * (rough target pressure), ventricles at
        // plausible end-diastolic volumes, and the systemic venous
        // reservoir absorbs the remainder so the total is exact.
        let v_sa = model.sa.1 + model.sa.0 * 95.0;
        let v_sc = model.sc.1 + model.sc.0 * 30.0;
        let v_pa = model.pa.1 + model.pa.0 * 15.0;
        let v_pc = model.pc.1 + model.pc.0 * 10.0;
        let v_pv = model.pv.1 + model.pv.0 * 8.0;
        let v_lv = 120.0;
        let v_rv = 110.0;
        let v_sv = tbv - (v_lv + v_sa + v_sc + v_pa + v_pc + v_pv + v_rv);
        let v = [v_lv, v_sa, v_sc, v_sv, v_rv, v_pa, v_pc, v_pv];
        let cap_lp0 = (v_sc - model.sc.1) / model.sc.0;
        Engine {
            model,
            tick: 0,
            v,
            map_lp: 90.0,
            cap_lp: cap_lp0,
            cap_ref: None,
            veno_ml: 0.0,
            refill_ml: 0.0,
            ino_mult: 1.0,
            tau: 0.0,
            ext_flow_ml_s: 0.0,
            ext_integral_ml: 0.0,
            total_volume_0: v.iter().sum(),
            setpoint_map: None,
            events: Vec::new(),
            log: Vec::new(),
            acc: BeatAcc {
                sa_max: f64::MIN,
                sa_min: f64::MAX,
                pa_max: f64::MIN,
                pa_min: f64::MAX,
                ..Default::default()
            },
            beats: Vec::new(),
            hash: FNV_OFFSET,
        }
    }

    /// Baroreflex: returns (heart rate bpm, peripheral-resistance
    /// multiplier, venomotor recruitment target in mL, contractility
    /// multiplier target) for a given sensed (low-passed) MAP. With
    /// no setpoint the reflex is off — used for the undisturbed
    /// settle, whose measured MAP then becomes the setpoint (the
    /// model's own operating point).
    fn reflex(&self, map_lp: f64) -> (f64, f64, f64, f64) {
        match self.setpoint_map {
            None => (self.model.hr0, 1.0, 0.0, 1.0),
            Some(sp) => {
                let err = (sp - map_lp) / sp;
                let hr_mult = (1.0 + self.model.reflex_gain_hr * err)
                    .clamp(self.model.reflex_hr_bounds[0], self.model.reflex_hr_bounds[1]);
                let r_mult = (1.0 + self.model.reflex_gain_r * err)
                    .clamp(self.model.reflex_r_bounds[0], self.model.reflex_r_bounds[1]);
                // Venomotor target: the cited swing capacity (S13)
                // scaled by the same error signal through the flagged
                // gain, saturating at +/- the full swing.
                let veno_target = self.model.veno_capacity_ml
                    * (self.model.veno_gain * err).clamp(-1.0, 1.0);
                // Contractility target (Milestone 21): the cited
                // +/- swing fraction of maximal elastance (S13)
                // scaled by the same error signal through the flagged
                // gain, saturating at the full swing either way.
                let ino_target = 1.0
                    + self.model.ino_swing * (self.model.ino_gain * err).clamp(-1.0, 1.0);
                (self.model.hr0 * hr_mult, r_mult, veno_target, ino_target)
            }
        }
    }

    pub fn set_reflex_setpoint(&mut self, map: f64) {
        self.setpoint_map = Some(map);
        // The refill mechanism's zero is captured at the same moment:
        // the model's own resting mean capillary pressure.
        self.cap_ref = Some(self.cap_lp);
        self.log.push(LogEntry {
            tick: self.tick,
            text: format!("baroreflex engaged, setpoint MAP = {map:.2} mmHg (model's own resting operating point)"),
        });
    }

    /// Schedule an event at an absolute tick (design/04: inputs are events
    /// on ticks).
    pub fn apply(&mut self, at_tick: u64, event: Event) {
        self.events.push((at_tick, event));
        self.events.sort_by_key(|(t, _)| *t);
    }

    #[allow(clippy::too_many_arguments)]
    fn evaluate(
        &self,
        v: &[f64; 8],
        map_lp: f64,
        cap_lp: f64,
        veno: f64,
        refill: f64,
        ino: f64,
        tau: f64,
        period: f64,
        tv: f64,
    ) -> Eval {
        let m = &self.model;
        let (_, r_mult, veno_target, ino_target) = self.reflex(map_lp);
        let p_sa = (v[SA] - m.sa.1) / m.sa.0;
        let p_sc = (v[SC] - m.sc.1) / m.sc.0;
        // Venomotor recruitment acts on the venous unstressed volume:
        // recruited volume is stressed volume (S13's mechanism).
        let p_sv = (v[SV] - (m.sv.1 - veno)) / m.sv.0;
        let p_pa = (v[PA] - m.pa.1) / m.pa.0;
        let p_pc = (v[PC] - m.pc.1) / m.pc.0;
        let p_pv = (v[PV] - m.pv.1) / m.pv.0;
        let act = activation(tau, period, tv);

        // Ventricle + semilunar valve, solved jointly: chamber pressure
        // depends on ejection flow through the KR term, and valve flow on
        // the pressure gradient (quadratic in Q — closed form).
        let ventricle = |vent: &Ventricle, vol: f64, p_down: f64, b: f64| -> (f64, f64) {
            let pd = vent.a * ((vent.k * (vol - vent.vu_d)).exp() - 1.0);
            // Contractility (Milestone 21): the inotropy state scales
            // the maximal elastance — the systolic span only; the
            // diastolic curve is not an elastance-maximum property.
            let sys_span = vent.e * ino * (vol - vent.vd);
            let base = pd * (1.0 - act) + sys_span * act;
            let alpha = sys_span * act * vent.kr;
            let q = valve_flow(base - p_down, b, m.valve_reg_r + alpha.max(0.0));
            (base - alpha * q, q)
        };
        let (p_lv, q_av) = ventricle(&m.lv, v[LV], p_sa, m.b_semilunar_valve);
        let (p_rv, q_pvv) = ventricle(&m.rv, v[RV], p_pa, m.b_semilunar_valve);

        // AV valves: upstream segment resistance in series with the valve.
        let q_mv = valve_flow(p_pv - p_lv, m.b_av_valve, m.valve_reg_r + m.pv.2);
        let q_tv = valve_flow(p_sv - p_rv, m.b_av_valve, m.valve_reg_r + m.sv.2);

        let q_sa = (p_sa - p_sc) / m.sa.2;
        let q_sc = (p_sc - p_sv) / (m.sc.2 * r_mult);
        let q_pa = (p_pa - p_pc) / m.pa.2;
        let q_pc = (p_pc - p_pv) / m.pc.2;

        // Transcapillary refill (Milestone 18): lumped Starling form —
        // net flow proportional to the deficit of mean capillary
        // pressure below its own resting reference, bounded by the
        // interstitial reserve in both directions (refill / escape).
        // Zero before the reflex engages (no reference captured).
        let q_refill = match self.cap_ref {
            None => 0.0,
            Some(r) => {
                let q = m.refill_k * (r - cap_lp);
                if (refill >= m.refill_reserve_ml && q > 0.0)
                    || (refill <= -m.refill_reserve_ml && q < 0.0)
                {
                    0.0
                } else {
                    q
                }
            }
        };
        // Venomotor recruitment: first-order approach to the reflex
        // target at the cited effector time constant (S13, tau_v).
        let d_veno = (veno_target - veno) / m.veno_tau;
        // Contractility: first-order approach to the reflex target
        // at the cited heart-effector time constant (S13, tau_h) —
        // the same form as S13's own elastance ODE (S25).
        let d_ino = (ino_target - ino) / m.ino_tau;

        let derivs = [
            q_mv - q_av,
            q_av - q_sa,
            q_sa - q_sc,
            q_sc - q_tv + self.ext_flow_ml_s + q_refill,
            q_tv - q_pvv,
            q_pvv - q_pa,
            q_pa - q_pc,
            q_pc - q_mv,
        ];
        Eval {
            pressures: Pressures {
                lv: p_lv,
                sa: p_sa,
                sc: p_sc,
                sv: p_sv,
                rv: p_rv,
                pa: p_pa,
                pc: p_pc,
                pv: p_pv,
            },
            flows: Flows {
                aortic_valve: q_av,
                mitral_valve: q_mv,
                tricuspid_valve: q_tv,
                pulmonary_valve: q_pvv,
                systemic_arterial: q_sa,
                systemic_peripheral: q_sc,
                pulmonary_arterial: q_pa,
                pulmonary_capillary: q_pc,
            },
            derivs,
            d_map_lp: (p_sa - map_lp) / m.reflex_tau,
            d_cap_lp: (p_sc - cap_lp) / m.reflex_tau,
            d_veno,
            d_refill: q_refill,
            d_ino,
        }
    }

    fn substep(&mut self, h: f64) {
        let (hr, _, _, _) = self.reflex(self.map_lp);
        let period = 60.0 / hr;
        let tv = self.model.tv0 * period.powf(self.model.tv_exp);
        // RK4 over (volumes, map_lp, cap_lp, veno, refill, ino); cycle
        // position tau advances in real time and stage taus are
        // tau + frac*h.
        let stage_frac = [0.0, 0.5, 0.5, 1.0];
        let weights = [1.0 / 6.0, 2.0 / 6.0, 2.0 / 6.0, 1.0 / 6.0];
        let mut k_v: [[f64; 8]; 4] = [[0.0; 8]; 4];
        let mut k_m: [f64; 4] = [0.0; 4];
        let mut k_c: [f64; 4] = [0.0; 4];
        let mut k_vn: [f64; 4] = [0.0; 4];
        let mut k_rf: [f64; 4] = [0.0; 4];
        let mut k_in: [f64; 4] = [0.0; 4];
        let mut acc_d_sa = 0.0;
        let mut acc_d_pa = 0.0;
        let mut acc_d_sv = 0.0;
        let mut acc_d_pv = 0.0;
        let mut acc_d_qav = 0.0;
        let mut acc_d_qpvv = 0.0;
        let mut acc_d_rvfill_pq = 0.0;
        let mut acc_d_rvfill_q = 0.0;
        let mut acc_d_rvfill_q2 = 0.0;
        let mut acc_d_rvfill_q3 = 0.0;
        // Stage value of a scalar state under this integrator's staging
        // (previous stage's derivative, half or full step).
        let stage = |base: f64, k_prev: f64, s: usize| -> f64 {
            if s == 0 {
                base
            } else {
                base + k_prev * h * if s == 3 { 1.0 } else { 0.5 }
            }
        };
        for s in 0..4 {
            let mut vs = self.v;
            if s > 0 {
                for i in 0..8 {
                    vs[i] += k_v[s - 1][i] * h * if s == 3 { 1.0 } else { 0.5 };
                }
            }
            let map_s = stage(self.map_lp, k_m[s.saturating_sub(1)], s);
            let cap_s = stage(self.cap_lp, k_c[s.saturating_sub(1)], s);
            let veno_s = stage(self.veno_ml, k_vn[s.saturating_sub(1)], s);
            let refill_s = stage(self.refill_ml, k_rf[s.saturating_sub(1)], s);
            let ino_s = stage(self.ino_mult, k_in[s.saturating_sub(1)], s);
            let tau_s = self.tau + stage_frac[s] * h;
            let ev = self.evaluate(&vs, map_s, cap_s, veno_s, refill_s, ino_s, tau_s, period, tv);
            k_v[s] = ev.derivs;
            k_m[s] = ev.d_map_lp;
            k_c[s] = ev.d_cap_lp;
            k_vn[s] = ev.d_veno;
            k_rf[s] = ev.d_refill;
            k_in[s] = ev.d_ino;
            let w = weights[s];
            acc_d_sa += w * ev.pressures.sa;
            acc_d_pa += w * ev.pressures.pa;
            acc_d_sv += w * ev.pressures.sv;
            acc_d_pv += w * ev.pressures.pv;
            acc_d_qav += w * ev.flows.aortic_valve;
            acc_d_qpvv += w * ev.flows.pulmonary_valve;
            acc_d_rvfill_pq += w * ev.flows.tricuspid_valve * ev.pressures.rv;
            acc_d_rvfill_q += w * ev.flows.tricuspid_valve;
            acc_d_rvfill_q2 += w * ev.flows.tricuspid_valve * ev.flows.tricuspid_valve;
            acc_d_rvfill_q3 +=
                w * ev.flows.tricuspid_valve * ev.flows.tricuspid_valve * ev.flows.tricuspid_valve;
            self.acc.sa_max = self.acc.sa_max.max(ev.pressures.sa);
            self.acc.sa_min = self.acc.sa_min.min(ev.pressures.sa);
            self.acc.pa_max = self.acc.pa_max.max(ev.pressures.pa);
            self.acc.pa_min = self.acc.pa_min.min(ev.pressures.pa);
        }
        for i in 0..8 {
            self.v[i] += h * (k_v[0][i] + 2.0 * k_v[1][i] + 2.0 * k_v[2][i] + k_v[3][i]) / 6.0;
        }
        let rk4 = |k: [f64; 4]| h * (k[0] + 2.0 * k[1] + 2.0 * k[2] + k[3]) / 6.0;
        self.map_lp += rk4(k_m);
        self.cap_lp += rk4(k_c);
        self.veno_ml += rk4(k_vn);
        self.refill_ml += rk4(k_rf);
        self.ino_mult += rk4(k_in);
        self.ext_integral_ml += self.ext_flow_ml_s * h;
        // Beat accumulators (RK-weighted stage means x h).
        self.acc.time += h;
        self.acc.sa_int += acc_d_sa * h;
        self.acc.pa_int += acc_d_pa * h;
        self.acc.sv_int += acc_d_sv * h;
        self.acc.pv_int += acc_d_pv * h;
        self.acc.q_av_int += acc_d_qav * h;
        self.acc.q_pvv_int += acc_d_qpvv * h;
        self.acc.rv_fill_pq += acc_d_rvfill_pq * h;
        self.acc.rv_fill_q += acc_d_rvfill_q * h;
        self.acc.rv_fill_q2 += acc_d_rvfill_q2 * h;
        self.acc.rv_fill_q3 += acc_d_rvfill_q3 * h;
        // Cycle position / beat boundary.
        self.tau += h;
        if self.tau >= period {
            self.tau -= period;
            self.close_beat();
        }
    }

    fn close_beat(&mut self) {
        let a = &self.acc;
        if a.time <= 0.0 {
            return;
        }
        let hr = 60.0 / a.time;
        let rec = BeatRecord {
            index: self.beats.len() as u64,
            duration_s: a.time,
            hr_bpm: hr,
            sbp: a.sa_max,
            dbp: a.sa_min,
            map: a.sa_int / a.time,
            pulse_pressure: a.sa_max - a.sa_min,
            sv_lv_ml: a.q_av_int,
            sv_rv_ml: a.q_pvv_int,
            co_l_min: a.q_av_int * hr / 1000.0,
            cvp: a.sv_int / a.time,
            rap: if a.rv_fill_q > 0.0 {
                a.rv_fill_pq / a.rv_fill_q
            } else {
                0.0
            },
            fill_q2_mean: if a.rv_fill_q > 0.0 {
                a.rv_fill_q2 / a.rv_fill_q
            } else {
                0.0
            },
            fill_q3_mean: if a.rv_fill_q > 0.0 {
                a.rv_fill_q3 / a.rv_fill_q
            } else {
                0.0
            },
            pa_systolic: a.pa_max,
            pa_diastolic: a.pa_min,
            pa_mean: a.pa_int / a.time,
            pv_mean: a.pv_int / a.time,
        };
        self.beats.push(rec);
        self.acc = BeatAcc {
            sa_max: f64::MIN,
            sa_min: f64::MAX,
            pa_max: f64::MIN,
            pa_min: f64::MAX,
            ..Default::default()
        };
    }

    /// Advance one 20 ms tick (design/04 interface).
    pub fn tick(&mut self) {
        // Events land on tick boundaries, before integration.
        let due: Vec<Event> = {
            let mut due = Vec::new();
            self.events.retain(|(t, e)| {
                if *t == self.tick {
                    due.push(e.clone());
                    false
                } else {
                    true
                }
            });
            due
        };
        for e in due {
            match e {
                Event::SetExtFlow { rate_ml_s, label } => {
                    self.ext_flow_ml_s = rate_ml_s;
                    self.log.push(LogEntry {
                        tick: self.tick,
                        text: format!("{label}: external volume flow set to {rate_ml_s:.3} mL/s"),
                    });
                }
            }
        }
        let n = (TICK_SECONDS / self.model.substep).round() as usize;
        for _ in 0..n {
            self.substep(self.model.substep);
        }
        self.tick += 1;
        // Trace hash fold (per tick, fixed order).
        let mut h = fnv_fold(self.hash, &self.tick.to_le_bytes());
        for x in self.v.iter() {
            h = fnv_fold(h, &x.to_bits().to_le_bytes());
        }
        h = fnv_fold(h, &self.tau.to_bits().to_le_bytes());
        h = fnv_fold(h, &self.map_lp.to_bits().to_le_bytes());
        h = fnv_fold(h, &self.cap_lp.to_bits().to_le_bytes());
        h = fnv_fold(h, &self.veno_ml.to_bits().to_le_bytes());
        h = fnv_fold(h, &self.refill_ml.to_bits().to_le_bytes());
        h = fnv_fold(h, &self.ino_mult.to_bits().to_le_bytes());
        self.hash = h;
    }

    pub fn tick_n(&mut self, n: u64) {
        for _ in 0..n {
            self.tick();
        }
    }

    pub fn hash(&self) -> u64 {
        self.hash
    }

    pub fn snapshot(&self) -> Engine {
        self.clone()
    }

    pub fn restore(&mut self, snap: Engine) {
        *self = snap;
    }

    pub fn volumes(&self) -> [f64; 8] {
        self.v
    }

    pub fn total_volume_ml(&self) -> f64 {
        // Conserved quantity: compartment sum minus BOTH external
        // inflows — the event channel (ext_integral_ml) and the
        // transcapillary refill state (Milestone 18), which is an
        // inflow from the unmodelled interstitium.
        self.v.iter().sum::<f64>() - self.ext_integral_ml - self.refill_ml
    }

    /// Net cumulative transcapillary transfer into the circulation
    /// (mL, Milestone 18): positive = refill, negative = net escape.
    pub fn net_refill_ml(&self) -> f64 {
        self.refill_ml
    }

    /// Currently recruited venous volume (mL, Milestone 18):
    /// positive = unstressed volume shifted into stressed volume.
    pub fn recruited_ml(&self) -> f64 {
        self.veno_ml
    }

    /// Current contractility multiplier (Milestone 21): the scale
    /// the baroreflex inotropy state applies to both ventricles'
    /// maximal elastance. 1.0 = the resting operating point.
    pub fn contractility_multiplier(&self) -> f64 {
        self.ino_mult
    }

    // ---- Guyton venous-return formulation (Milestone 24) ----
    //
    // Pure functions of the current state; nothing here feeds back
    // into the integration, the event stream, or the trace hash.

    /// Systemic vascular compliance (mL/mmHg): the three systemic
    /// vessel compartments (arteries, capillaries, veins). The
    /// ventricles are the pump, not capacitance, in Guyton's
    /// systemic formulation.
    pub fn systemic_compliance_ml_mmhg(&self) -> f64 {
        self.model.sa.0 + self.model.sc.0 + self.model.sv.0
    }

    /// Systemic stressed volume (mL): volume above the unstressed
    /// volumes in the systemic vascular tree, with the venous
    /// unstressed volume reduced by the currently recruited volume
    /// (the Milestone 18 venomotor state), exactly as in evaluate().
    pub fn systemic_stressed_volume_ml(&self) -> f64 {
        let m = &self.model;
        (self.v[SA] - m.sa.1)
            + (self.v[SC] - m.sc.1)
            + (self.v[SV] - (m.sv.1 - self.veno_ml))
    }

    /// Mean systemic filling pressure (mmHg): the pressure the
    /// systemic circuit equilibrates to at zero flow —
    /// stressed volume / compliance (Guyton; parameters.json S17).
    pub fn mean_systemic_filling_pressure(&self) -> f64 {
        self.systemic_stressed_volume_ml() / self.systemic_compliance_ml_mmhg()
    }

    /// Mean circulatory filling pressure (mmHg): the whole-circuit
    /// analogue, by the stop-flow equilibration construction Guyton
    /// used experimentally (arrest the pump, equilibrate pressures;
    /// S17/S21): the single pressure at which the observed total
    /// volume distributes over all six vascular compliances plus
    /// both ventricles' diastolic pressure-volume curves
    /// (Pd = A*(exp(K*(V-Vu)) - 1), inverted). Solved by bisection;
    /// deterministic (fixed iteration count).
    pub fn mean_circulatory_filling_pressure(&self) -> f64 {
        let m = &self.model;
        let vasc: [(f64, f64); 6] = [
            m.sa,
            m.sc,
            (m.sv.0, m.sv.1 - self.veno_ml, m.sv.2),
            m.pa,
            m.pc,
            m.pv,
        ]
        .map(|t| (t.0, t.1));
        let v_tot: f64 = self.v.iter().sum();
        let vol_at = |p: f64| -> f64 {
            let mut s: f64 = vasc.iter().map(|(c, vu)| vu + c * p).sum();
            for vent in [&m.lv, &m.rv] {
                if p <= -vent.a {
                    return f64::NEG_INFINITY;
                }
                s += vent.vu_d + (1.0 + p / vent.a).ln() / vent.k;
            }
            s
        };
        let (mut lo, mut hi) = (-1.99f64, 60.0f64);
        for _ in 0..200 {
            let mid = 0.5 * (lo + hi);
            if vol_at(mid) < v_tot {
                lo = mid;
            } else {
                hi = mid;
            }
        }
        0.5 * (lo + hi)
    }

    /// Resistance to venous return by the series-circuit compliance
    /// weighting (mmHg*s/mL): RVR = sum_k R_k * (compliance upstream
    /// of R_k) / C_sys over the systemic circuit. Computed at
    /// BASELINE resistances (reflex multiplier 1.0): the reflex's
    /// resistance state is not exposed, so this is the circuit's
    /// structural RVR; the operative empirical value is
    /// (MSFP - RAP) / CO from the beat record.
    ///
    /// The venous outflow segment (systemic veins -> tricuspid
    /// valve -> RV) needs one correction Guyton's steady-flow
    /// derivation does not: its flow is intermittent (diastole
    /// only), so its mean pressure gradient is NOT its resistance
    /// law evaluated at mean flow. Instantaneously the segment
    /// obeys dp = B*q^2 + lin*q; the flow-weighted mean gradient
    /// the circuit actually works against is
    /// B*<q^3>/<q> + lin*<q^2>/<q> over the beat (the moments on
    /// BeatRecord), and the segment's effective resistance at the
    /// beat's mean flow is that gradient divided by the mean flow.
    /// Evaluated from the last completed beat; None before the
    /// first beat closes.
    pub fn resistance_to_venous_return_formula(&self) -> Option<f64> {
        let m = &self.model;
        let b = self.beats.last()?;
        let q_mean = b.sv_rv_ml / b.duration_s;
        if q_mean <= 0.0 {
            return None;
        }
        let lin = m.valve_reg_r + m.sv.2;
        let grad_fw = m.b_av_valve * b.fill_q3_mean + lin * b.fill_q2_mean;
        let r_seg = grad_fw / q_mean;
        let c_sys = self.systemic_compliance_ml_mmhg();
        Some((m.sa.2 * m.sa.0 + m.sc.2 * (m.sa.0 + m.sc.0) + r_seg * c_sys) / c_sys)
    }

    pub fn volume_conservation_error_ml(&self) -> f64 {
        (self.total_volume_ml() - self.total_volume_0).abs()
    }

    /// design/04 query interface: value, unit, and the event-level causal
    /// chain (v0 provenance: the applied-event log with magnitudes — see
    /// MILESTONE-8.md for what this does and does not yet explain).
    pub fn query(&self, variable: &str) -> Option<(f64, &'static str)> {
        let b = self.beats.last()?;
        let (val, unit) = match variable {
            "heart_rate" => (b.hr_bpm, "beats/min"),
            "systolic_bp" => (b.sbp, "mmHg"),
            "diastolic_bp" => (b.dbp, "mmHg"),
            "mean_arterial_pressure" => (b.map, "mmHg"),
            "pulse_pressure" => (b.pulse_pressure, "mmHg"),
            "cardiac_output" => (b.co_l_min, "L/min"),
            "stroke_volume_lv" => (b.sv_lv_ml, "mL/beat"),
            "central_venous_pressure" => (b.cvp, "mmHg"),
            "pa_systolic" => (b.pa_systolic, "mmHg"),
            "pa_diastolic" => (b.pa_diastolic, "mmHg"),
            "pa_mean" => (b.pa_mean, "mmHg"),
            "pcwp_proxy_mean_pv_pressure" => (b.pv_mean, "mmHg"),
            // Milestone 18 mechanism states (instantaneous state, not
            // beat-window statistics like the outputs above).
            "net_transcapillary_refill" => (self.refill_ml, "mL"),
            "recruited_venous_volume" => (self.veno_ml, "mL"),
            // Milestone 21 mechanism state (instantaneous).
            "contractility_multiplier" => (self.ino_mult, "ratio"),
            // Milestone 24 Guyton formulation. The beat-level RAP
            // proxy is a beat statistic like the outputs above; the
            // filling pressures and stressed volume are instantaneous
            // functions of state, like the mechanism states.
            "right_atrial_pressure_proxy" => (b.rap, "mmHg"),
            "mean_systemic_filling_pressure" => (self.mean_systemic_filling_pressure(), "mmHg"),
            "mean_circulatory_filling_pressure" => {
                (self.mean_circulatory_filling_pressure(), "mmHg")
            }
            "systemic_stressed_volume" => (self.systemic_stressed_volume_ml(), "mL"),
            _ => return None,
        };
        Some((val, unit))
    }

    pub fn causal_chain(&self) -> Vec<String> {
        self.log
            .iter()
            .map(|e| format!("tick {} (t = {:.2} s): {}", e.tick, e.tick as f64 * TICK_SECONDS, e.text))
            .collect()
    }
}
