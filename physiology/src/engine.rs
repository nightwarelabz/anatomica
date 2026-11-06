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
        Engine {
            model,
            tick: 0,
            v,
            map_lp: 90.0,
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
    /// multiplier) for a given sensed (low-passed) MAP. With no setpoint
    /// the reflex is off — used for the undisturbed settle, whose measured
    /// MAP then becomes the setpoint (the model's own operating point).
    fn reflex(&self, map_lp: f64) -> (f64, f64) {
        match self.setpoint_map {
            None => (self.model.hr0, 1.0),
            Some(sp) => {
                let err = (sp - map_lp) / sp;
                let hr_mult = (1.0 + self.model.reflex_gain_hr * err)
                    .clamp(self.model.reflex_hr_bounds[0], self.model.reflex_hr_bounds[1]);
                let r_mult = (1.0 + self.model.reflex_gain_r * err)
                    .clamp(self.model.reflex_r_bounds[0], self.model.reflex_r_bounds[1]);
                (self.model.hr0 * hr_mult, r_mult)
            }
        }
    }

    pub fn set_reflex_setpoint(&mut self, map: f64) {
        self.setpoint_map = Some(map);
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

    fn evaluate(&self, v: &[f64; 8], map_lp: f64, tau: f64, period: f64, tv: f64) -> Eval {
        let m = &self.model;
        let (_, r_mult) = self.reflex(map_lp);
        let p_sa = (v[SA] - m.sa.1) / m.sa.0;
        let p_sc = (v[SC] - m.sc.1) / m.sc.0;
        let p_sv = (v[SV] - m.sv.1) / m.sv.0;
        let p_pa = (v[PA] - m.pa.1) / m.pa.0;
        let p_pc = (v[PC] - m.pc.1) / m.pc.0;
        let p_pv = (v[PV] - m.pv.1) / m.pv.0;
        let act = activation(tau, period, tv);

        // Ventricle + semilunar valve, solved jointly: chamber pressure
        // depends on ejection flow through the KR term, and valve flow on
        // the pressure gradient (quadratic in Q — closed form).
        let ventricle = |vent: &Ventricle, vol: f64, p_down: f64, b: f64| -> (f64, f64) {
            let pd = vent.a * ((vent.k * (vol - vent.vu_d)).exp() - 1.0);
            let sys_span = vent.e * (vol - vent.vd);
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

        let derivs = [
            q_mv - q_av,
            q_av - q_sa,
            q_sa - q_sc,
            q_sc - q_tv + self.ext_flow_ml_s,
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
        }
    }

    fn substep(&mut self, h: f64) {
        let (hr, _) = self.reflex(self.map_lp);
        let period = 60.0 / hr;
        let tv = self.model.tv0 * period.powf(self.model.tv_exp);
        // RK4 over (volumes, map_lp); cycle position tau advances in real
        // time and stage taus are tau + frac*h.
        let stage_frac = [0.0, 0.5, 0.5, 1.0];
        let weights = [1.0 / 6.0, 2.0 / 6.0, 2.0 / 6.0, 1.0 / 6.0];
        let mut k_v: [[f64; 8]; 4] = [[0.0; 8]; 4];
        let mut k_m: [f64; 4] = [0.0; 4];
        let mut acc_d_sa = 0.0;
        let mut acc_d_pa = 0.0;
        let mut acc_d_sv = 0.0;
        let mut acc_d_pv = 0.0;
        let mut acc_d_qav = 0.0;
        let mut acc_d_qpvv = 0.0;
        for s in 0..4 {
            let mut vs = self.v;
            if s > 0 {
                for i in 0..8 {
                    vs[i] += k_v[s - 1][i] * h * if s == 3 { 1.0 } else { 0.5 };
                }
            }
            let map_s = if s == 0 {
                self.map_lp
            } else {
                self.map_lp + k_m[s - 1] * h * if s == 3 { 1.0 } else { 0.5 }
            };
            let tau_s = self.tau + stage_frac[s] * h;
            let ev = self.evaluate(&vs, map_s, tau_s, period, tv);
            k_v[s] = ev.derivs;
            k_m[s] = ev.d_map_lp;
            let w = weights[s];
            acc_d_sa += w * ev.pressures.sa;
            acc_d_pa += w * ev.pressures.pa;
            acc_d_sv += w * ev.pressures.sv;
            acc_d_pv += w * ev.pressures.pv;
            acc_d_qav += w * ev.flows.aortic_valve;
            acc_d_qpvv += w * ev.flows.pulmonary_valve;
            self.acc.sa_max = self.acc.sa_max.max(ev.pressures.sa);
            self.acc.sa_min = self.acc.sa_min.min(ev.pressures.sa);
            self.acc.pa_max = self.acc.pa_max.max(ev.pressures.pa);
            self.acc.pa_min = self.acc.pa_min.min(ev.pressures.pa);
        }
        for i in 0..8 {
            self.v[i] += h * (k_v[0][i] + 2.0 * k_v[1][i] + 2.0 * k_v[2][i] + k_v[3][i]) / 6.0;
        }
        self.map_lp += h * (k_m[0] + 2.0 * k_m[1] + 2.0 * k_m[2] + k_m[3]) / 6.0;
        self.ext_integral_ml += self.ext_flow_ml_s * h;
        // Beat accumulators (RK-weighted stage means x h).
        self.acc.time += h;
        self.acc.sa_int += acc_d_sa * h;
        self.acc.pa_int += acc_d_pa * h;
        self.acc.sv_int += acc_d_sv * h;
        self.acc.pv_int += acc_d_pv * h;
        self.acc.q_av_int += acc_d_qav * h;
        self.acc.q_pvv_int += acc_d_qpvv * h;
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
        self.v.iter().sum::<f64>() - self.ext_integral_ml
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
