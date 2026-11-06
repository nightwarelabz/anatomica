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
//!
//! Milestone 25 closes the two volume-side omissions Milestone 24
//! named. (1) The interstitium becomes a finite reservoir: the
//! refill state IS its net transfer integral, so the interstitial
//! volume is V_isf = interstitial_volume_ml − refill_ml by identity
//! (cited capacity, S25), and the Starling driver gains the
//! reservoir's pressure feedback — dP_isf = −refill_ml / C_isf with
//! C_isf a single lumped compliance calibrated inside the band of
//! the fitted experimental pressure–volume relation (S26) — which
//! brakes refill as the reservoir depletes and escape as it fills,
//! replacing the Milestone 18 hard reserve bound (the flow now
//! stops only at the reservoir's physical floor). Infused
//! crystalloid therefore redistributes on the pathway's own time
//! course instead of staying intravascular. (2) A lumped renal
//! function curve in the Guyton tradition (S23): urine output is a
//! piecewise-linear multiple of the baseline output U0 (S24),
//! driven by the sensed MAP relative to the captured operating
//! point through the chapter's cited anchors (zero output 50 mmHg
//! below the normal pressure, ~3x at +50 mmHg, 6–8x at +100 mmHg),
//! leaving the systemic venous compartment; a constant lumped
//! intake equal to U0 (the source's equilibrium construction)
//! enters it. This is a renal FUNCTION curve, not nephron
//! modelling — the Body Model has no nephron either. Before the
//! reflex engages, urine output is held exactly equal to intake so
//! the settle is undisturbed; afterwards the curve acts, and volume
//! loads are actually excreted over the course horizon. Both new
//! states (cumulative urine, cumulative intake) are RK4-integrated
//! and folded into the trace hash like every other state; the
//! hormonal axes that steepen the chronic curve (S23) and
//! lymphatic return as a separate dynamic remain unmodelled —
//! named in MILESTONE-25.md's caveat ledger.
//!
//! Milestone 26 closes the omission Milestone 25's ledger named as
//! binding on the volume side: oncotic/protein handling. Three lumped
//! states join the RK4 integration and the trace hash: red-cell volume
//! (mL), plasma protein mass (g) and interstitial protein mass (g).
//! Protein concentrations are derived (mass over plasma volume —
//! total blood volume minus red-cell volume — and over the
//! interstitial reservoir volume), and oncotic pressures follow from
//! them through Nitta et al.'s corrected Landis-Pappenheimer relation
//! (S33) at a fixed albumin fraction (S29's table). The Starling
//! driver gains the oncotic term in its textbook form,
//! sigma x ((pi_c - pi_i) - its own resting value), with sigma cited
//! (S30); protein crosses with the Starling flow under a disclosed
//! upstream convention (inflow limb unsieved at the interstitial
//! concentration, outflow limb sieved at (1 - sigma) x plasma
//! concentration), leaks from plasma at a rate proportional to its
//! concentration, and returns via the lymph at a rate proportional
//! to the interstitial concentration — the pair exactly balanced at
//! the operating point at the cited resting lymph protein-return
//! flux (S32). Albumin synthesis (S31) enters the plasma pool against
//! a first-order catabolic sink calibrated to cancel it at rest.
//! Blood products enter through a second, composition-carrying event
//! channel (Event::SetProductFlow): whole blood, packed red cells
//! and plasma with cited unit volumes, hematocrits and protein
//! concentrations (S29/S34/S35). Hematocrit is TRACKED-BUT-INERT,
//! stated plainly: it feeds the plasma-volume identity and the
//! product/dilution bookkeeping only — no viscosity coupling is
//! modelled, because no sourced lumped viscosity law was consulted
//! and inventing one is refused. Lymphatic VOLUME return remains
//! subsumed in the net Starling pathway (Milestone 25 ledger stands);
//! what Milestone 26 adds is the lymphatic PROTEIN flux riding on it.
//!
//! Milestone 30 closes the caveat Milestones 24–26 carried — the
//! hormonal volume axes. Four lumped states join the RK4 integration
//! and the trace hash: the extracellular sodium content (mmol), the
//! intracellular water volume (mL), the plasma AVP/ADH concentration
//! (pg/mL), and a normalised aldosterone EFFECT state (1.0 at rest);
//! a fifth boundary state, cumulative urinary sodium, is integrated
//! alongside cumulative urine. Plasma sodium is the sodium content
//! over the extracellular volume (plasma + interstitial); calculated
//! plasma osmolality is 2[Na] + the constant non-sodium term of the
//! Dorwart–Chalmers formula (S47) — glucose and urea are not states,
//! disclosed. The intracellular lump holds a fixed solute content
//! and exchanges water with the interstitium on the osmolality
//! difference alone, so it is an osmotic buffer (its volume change
//! is part of the interstitial volume identity, exactly as refill
//! is). ADH follows the classic osmolality regression (S37) plus a
//! volume/pressure limb (S38), with a lumped secretion–clearance
//! time constant (S36/S38); it acts on the renal curve through
//! the AVP–urine-osmolality response curve (S39 anchors, S49):
//! urine flow is the acute pressure multiple times the urinary
//! osmole excretion rate over the curve at the current AVP — at
//! the resting osmole rate exactly the curve-ratio
//! water-permeability multiplier, and exactly the baseline flow at
//! the operating point, so the resting trajectories are
//! undisturbed. Urine osmolality is then an honest readout: total
//! urinary osmole rate (sodium salts plus a constant
//! urea-dominated term, derived from S39's resting value) over
//! urine flow — ADH moves water at nearly constant solute
//! excretion, which is S39's own mechanism. Aldosterone is the slow
//! limb by construction: its effect state approaches its target
//! (renal perfusion deficit and plasma-sodium excess; renin and
//! angiotensin are subsumed, disclosed) at the genomic timescale of
//! the human infusion data (S41/S42 — peak effect 2–4 h), and it
//! acts by shifting a CHRONIC pressure–natriuresis curve (S23/S43):
//! sodium excretion reuses the acute curve's shape with its
//! pressure axis compressed (the chronic steepening S23 describes)
//! and shifted by the aldosterone state (Guyton's curve-shift
//! formulation). Water excretion deliberately stays on the
//! Milestone 25 acute curve — the asymmetry is named in
//! MILESTONE-30.md. Intake becomes an event-settable pair of rates
//! (Event::SetIntake); at their defaults the equilibrium
//! construction holds exactly as before.

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
    // interstitial reservoir (Milestone 25): finite capacity cited
    // (S25); compliance calibrated inside the fitted-curve band (S26).
    pub isf_volume_ml: f64,
    pub isf_compliance_ml_mmhg: f64,
    // lumped renal function curve (Milestone 25): baseline output
    // and intake in mL/s (parameters carry mL/min); curve anchors
    // cited (S23).
    pub urine0_ml_s: f64,
    pub intake_ml_s: f64,
    pub renal_zero_offset_mmhg: f64,
    pub renal_mult_50: f64,
    pub renal_mult_100: f64,
    // oncotic state (Milestone 26): resting protein concentrations
    // (S29), hematocrit, reflection coefficient (S30), Nitta
    // coefficients (S33), lymph protein return / synthesis /
    // catabolism (S32/S31), and the blood products' compositions
    // (S34/S35) as (unit volume mL, hematocrit, protein g/mL).
    pub protein_cp0_g_ml: f64,
    pub protein_ci0_g_ml: f64,
    pub hematocrit_resting: f64,
    pub sigma_protein: f64,
    pub nitta_alb: [f64; 3],
    pub nitta_glob: [f64; 3],
    pub albumin_fraction: f64,
    pub lymph_protein_g_s: f64,
    pub albumin_synthesis_g_s: f64,
    pub protein_catabolic_frac_s: f64,
    pub product_wb: (f64, f64, f64),
    pub product_prbc: (f64, f64, f64),
    pub product_plasma: (f64, f64, f64),
    // hormonal volume axes (Milestone 30): the sodium/osmolality
    // construction (S46/S47/S48), the intracellular osmotic buffer
    // (S36/S46), the ADH axis (S37/S38 thresholds, slope, volume
    // limb; S36/S38 time constants; S39/S49 urine-osmolality
    // response), sodium balance (S45), the crystalloid sodium
    // convention (S50), and the aldosterone limb (S41/S42 effect
    // timescale; S43 mechanism; gains VERIFY-flagged like the reflex
    // gains; S23 chronic-curve steepening and curve shift).
    pub na_resting_mmol_l: f64,
    pub osm_non_sodium_mosm_kg: f64,
    pub icf_volume_ml: f64,
    pub icf_k_ml_s_mosm: f64,
    pub adh_threshold_mosm_kg: f64,
    pub adh_slope_pg_ml_mosm: f64,
    pub adh_vol_threshold: f64,
    pub adh_vol_full: f64,
    pub adh_vol_max_pg_ml: f64,
    pub adh_tau_s: f64,
    pub uosm_min_mosm_kg: f64,
    pub uosm_max_mosm_kg: f64,
    pub uosm_half_pg_ml: f64,
    pub una0_mmol_s: f64,
    pub na_intake0_mmol_s: f64,
    pub urine_non_na_osm_mosm_s: f64,
    pub crystalloid_na_mmol_l: f64,
    pub aldo_tau_s: f64,
    pub aldo_gain_perf: f64,
    pub aldo_gain_na: f64,
    pub aldo_floor: f64,
    pub aldo_ceiling: f64,
    pub aldo_shift_mmhg_per_unit: f64,
    pub renal_chronic_steep: f64,
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

/// Read a 3-element coefficient array parameter (Milestone 26: the
/// Nitta relation's polynomials).
fn coef3(p: &Params, name: &str) -> [f64; 3] {
    let v = &p.parameter(name).value;
    let a = v
        .as_array()
        .unwrap_or_else(|| panic!("parameter '{name}' is not a coefficient array"));
    assert!(a.len() == 3, "coefficient array '{name}' must have exactly 3 elements");
    [
        a[0].as_f64().unwrap(),
        a[1].as_f64().unwrap(),
        a[2].as_f64().unwrap(),
    ]
}

/// Colloid osmotic (oncotic) pressure from a total protein
/// concentration (Milestone 26): Nitta et al.'s corrected
/// Landis-Pappenheimer relation (parameters.json S33), concentrations
/// in g/dL, result in mmHg, the albumin fraction held at the resting
/// plasma composition (S29) — the lumped states track total protein
/// only, so the relation is applied at fixed composition in both
/// pools (disclosed in MILESTONE-26.md).
pub fn oncotic_pressure_mmhg(c_g_per_dl: f64, m: &Model) -> f64 {
    if c_g_per_dl <= 0.0 {
        return 0.0;
    }
    let c = c_g_per_dl;
    let alb = m.albumin_fraction
        * (m.nitta_alb[0] * c + m.nitta_alb[1] * c * c + m.nitta_alb[2] * c * c * c);
    let glob = (1.0 - m.albumin_fraction)
        * (m.nitta_glob[0] * c + m.nitta_glob[1] * c * c + m.nitta_glob[2] * c * c * c);
    alb + glob
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
            isf_volume_ml: p.f64("interstitial_volume_ml"),
            isf_compliance_ml_mmhg: p.f64("interstitial_compliance_ml_mmhg"),
            urine0_ml_s: p.f64("baseline_urine_output_ml_min") / 60.0,
            intake_ml_s: p.f64("fluid_intake_ml_min") / 60.0,
            renal_zero_offset_mmhg: p.f64("renal_pressure_zero_offset_mmhg"),
            renal_mult_50: p.f64("renal_multiple_at_plus_50_mmhg"),
            renal_mult_100: p.f64("renal_multiple_at_plus_100_mmhg"),
            protein_cp0_g_ml: p.f64("plasma_protein_concentration_g_ml"),
            protein_ci0_g_ml: p.f64("isf_protein_concentration_g_ml"),
            hematocrit_resting: p.f64("hematocrit_resting"),
            sigma_protein: p.f64("starling_reflection_coefficient_protein"),
            nitta_alb: coef3(p, "oncotic_albumin_coefficients"),
            nitta_glob: coef3(p, "oncotic_globulin_coefficients"),
            albumin_fraction: p.f64("plasma_albumin_fraction"),
            lymph_protein_g_s: p.f64("lymph_protein_return_g_s"),
            albumin_synthesis_g_s: p.f64("albumin_synthesis_g_s"),
            protein_catabolic_frac_s: p.f64("protein_catabolic_fraction_s"),
            product_wb: (
                p.f64("product_whole_blood_volume_ml"),
                p.f64("product_whole_blood_hematocrit"),
                p.f64("product_whole_blood_protein_g_ml"),
            ),
            product_prbc: (
                p.f64("product_prbc_volume_ml"),
                p.f64("product_prbc_hematocrit"),
                p.f64("product_prbc_protein_g_ml"),
            ),
            product_plasma: (
                p.f64("product_plasma_volume_ml"),
                p.f64("product_plasma_hematocrit"),
                p.f64("product_plasma_protein_g_ml"),
            ),
            na_resting_mmol_l: p.f64("plasma_sodium_resting_mmol_l"),
            osm_non_sodium_mosm_kg: p.f64("osmolality_non_sodium_mosm_kg"),
            icf_volume_ml: p.f64("icf_volume_ml"),
            icf_k_ml_s_mosm: p.f64("icf_exchange_conductance_ml_s_mosm"),
            adh_threshold_mosm_kg: p.f64("adh_osmotic_threshold_mosm_kg"),
            adh_slope_pg_ml_mosm: p.f64("adh_osmotic_slope_pg_ml_per_mosm"),
            adh_vol_threshold: p.f64("adh_volume_threshold_fraction"),
            adh_vol_full: p.f64("adh_volume_full_fraction"),
            adh_vol_max_pg_ml: p.f64("adh_volume_max_pg_ml"),
            adh_tau_s: p.f64("adh_tau_seconds"),
            uosm_min_mosm_kg: p.f64("adh_uosm_min_mosm_kg"),
            uosm_max_mosm_kg: p.f64("adh_uosm_max_mosm_kg"),
            uosm_half_pg_ml: p.f64("adh_uosm_half_pg_ml"),
            una0_mmol_s: p.f64("baseline_sodium_excretion_mmol_min") / 60.0,
            na_intake0_mmol_s: p.f64("sodium_intake_mmol_min") / 60.0,
            urine_non_na_osm_mosm_s: p.f64("urine_non_sodium_osmole_rate_mosm_min") / 60.0,
            crystalloid_na_mmol_l: p.f64("crystalloid_sodium_mmol_l"),
            aldo_tau_s: p.f64("aldosterone_tau_seconds"),
            aldo_gain_perf: p.f64("aldosterone_perfusion_gain"),
            aldo_gain_na: p.f64("aldosterone_sodium_gain"),
            aldo_floor: p.f64("aldosterone_target_floor"),
            aldo_ceiling: p.f64("aldosterone_target_ceiling"),
            aldo_shift_mmhg_per_unit: p.f64("renal_curve_shift_per_aldosterone_mmhg"),
            renal_chronic_steep: p.f64("renal_chronic_steepening"),
        }
    }

    /// Resting calculated plasma osmolality (mOsm/kg) implied by the
    /// construction parameters (Milestone 30): 2[Na] + the constant
    /// non-sodium term (S47). The sodium state is initialised so the
    /// resting operating point sits exactly on this value — the
    /// disclosed equilibrium construction.
    pub fn resting_osmolality_mosm_kg(&self) -> f64 {
        2.0 * self.na_resting_mmol_l + self.osm_non_sodium_mosm_kg
    }

    /// Resting plasma AVP (pg/mL) implied by the construction
    /// (Milestone 30): the S37 regression at the resting osmolality.
    pub fn resting_adh_pg_ml(&self) -> f64 {
        self.adh_slope_pg_ml_mosm
            * (self.resting_osmolality_mosm_kg() - self.adh_threshold_mosm_kg).max(0.0)
    }

    /// A blood product's composition by scenario key (Milestone 26):
    /// (unit volume mL, hematocrit, protein g/mL) from
    /// parameters.json under the usual sourcing discipline.
    pub fn product_spec(&self, key: &str) -> Option<(f64, f64, f64)> {
        match key {
            "whole_blood" => Some(self.product_wb),
            "prbc" => Some(self.product_prbc),
            "plasma" => Some(self.product_plasma),
            _ => None,
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
    /// Set the blood-product inflow (Milestone 26): a second,
    /// composition-carrying channel into the systemic venous
    /// compartment. Unlike the crystalloid/event channel, the stream
    /// brings red-cell volume and plasma protein at the product's own
    /// concentrations (parameters.json product_* parameters, S34/S35).
    /// A rate of 0 stops the product. One product flow at a time —
    /// the channel carries one composition.
    SetProductFlow {
        rate_ml_s: f64,
        hematocrit: f64,
        protein_g_per_ml: f64,
        label: String,
    },
    /// Set the lumped intake rates (Milestone 30): water (mL/min)
    /// and sodium (mmol/min) entering the systemic venous
    /// compartment — the behavioural side of fluid balance, exposed
    /// as a scenario input (thirst is behaviour, not a reflex this
    /// engine models; see MILESTONE-30.md). The rates are absolute,
    /// not deltas; the defaults are the parameters.json baseline
    /// intake values, at which the equilibrium construction holds.
    /// The theatre scenarios never fire this event.
    SetIntake {
        water_ml_min: f64,
        sodium_mmol_min: f64,
        label: String,
    },
    /// Set the solute-free water inflow (mL/s; Milestone 30): a
    /// dedicated channel carrying water with NO sodium, protein or
    /// red cells — the intravenous pure-water load (a
    /// dextrose-water-equivalent input after glucose metabolism).
    /// It exists because the event channel is a crystalloid channel
    /// and carries sodium at the crystalloid concentration: a water
    /// load through it would be an isotonic load and could not test
    /// the osmolality axis at all (measured and recorded in
    /// MILESTONE-30.md). A rate of 0 stops the flow.
    SetWaterFlow { rate_ml_s: f64, label: String },
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
    /// net escape. This state is the integral of the refill flow and
    /// an external inflow for volume accounting, like the
    /// external-flow integral. Milestone 25: the interstitium is now
    /// a finite reservoir whose volume is this state's mirror —
    /// V_isf = interstitial_volume_ml - refill_ml by identity — and
    /// whose pressure feedback brakes the flow (see evaluate()).
    refill_ml: f64,
    /// Cumulative urine output (mL, Milestone 25): the integral of
    /// the lumped renal function curve's flow out of the systemic
    /// venous compartment.
    urine_ml: f64,
    /// Cumulative fluid intake (mL, Milestone 25): the integral of
    /// the constant lumped intake into the systemic venous
    /// compartment.
    intake_ml: f64,
    /// Contractility multiplier (Milestone 21): the baroreflex
    /// inotropy state — a dimensionless scale on both ventricles'
    /// maximal elastance. 1.0 at the resting operating point; the
    /// reflex drives it within 1 +/- the cited swing fraction (S13).
    ino_mult: f64,
    /// Red-cell volume (mL, Milestone 26): the formed-element part of
    /// the blood volume. Plasma volume is derived as total blood
    /// volume minus this state, and hematocrit as their ratio.
    /// TRACKED-BUT-INERT: it feeds the plasma-volume identity and the
    /// product/dilution bookkeeping only — no viscosity coupling.
    rbc_ml: f64,
    /// Plasma protein mass (g, Milestone 26): the lumped oncotic
    /// state of the vascular pool. Its concentration (mass over the
    /// derived plasma volume) sets the plasma oncotic pressure.
    protein_plasma_g: f64,
    /// Interstitial protein mass (g, Milestone 26): the lumped
    /// oncotic state of the interstitial reservoir (Milestone 25);
    /// its concentration sets the interstitial oncotic pressure.
    protein_isf_g: f64,
    /// Oncotic reference captured when the reflex engages (Milestone
    /// 26): (plasma, interstitial) oncotic pressures at the model's
    /// own resting operating point — the Starling oncotic term's
    /// zero, exactly as cap_ref is the pressure term's zero.
    oncotic_ref: Option<(f64, f64)>,
    /// The active blood-product flow (Milestone 26): rate (mL/s) and
    /// the product's composition, set by Event::SetProductFlow.
    product_flow_ml_s: f64,
    product_hematocrit: f64,
    product_protein_g_ml: f64,
    /// Cumulative product volume infused (mL, Milestone 26): the
    /// product channel's boundary integral, carried in the volume
    /// identity like the event channel's.
    product_integral_ml: f64,
    /// Extracellular sodium content (mmol, Milestone 30): the
    /// osmotic lump. Plasma sodium concentration is this content
    /// over the extracellular volume (plasma + interstitial); the
    /// state is the ECF's effective (osmotically active) sodium —
    /// bone and skin non-osmotic stores are not part of it,
    /// disclosed in MILESTONE-30.md.
    na_mmol: f64,
    /// Intracellular water volume (mL, Milestone 30): the osmotic
    /// buffer lump. Its solute content is fixed at the resting
    /// osmolality (see icf_solute_mosm); it exchanges water with
    /// the interstitium on the osmolality difference only.
    icf_ml: f64,
    /// Plasma AVP/ADH concentration (pg/mL, Milestone 30).
    adh_pg_ml: f64,
    /// Aldosterone EFFECT state (Milestone 30): normalised so 1.0
    /// is the resting operating point. Renin and angiotensin are
    /// subsumed into this limb's target (disclosed); the state is
    /// the slow genomic effector of S41/S42, not the hormone's
    /// plasma concentration.
    aldo_state: f64,
    /// Cumulative urinary sodium (mmol, Milestone 30): the integral
    /// of the chronic curve's sodium excretion — a boundary state
    /// like cumulative urine, RK4-integrated and hash-folded.
    urine_na_mmol: f64,
    /// Cumulative sodium intake (mmol, Milestone 30): the intake
    /// channel's boundary integral — exact, like the product
    /// integral (its rate is piecewise constant, set by events), and
    /// not hash-folded, like the product integral.
    intake_na_mmol: f64,
    /// The intracellular lump's fixed solute content (mOsm,
    /// Milestone 30): resting osmolality x resting ICF volume,
    /// fixed at construction — the lump buffers water, it does not
    /// gain or lose solute.
    icf_solute_mosm: f64,
    /// The resting extracellular sodium content (mmol, Milestone
    /// 30): the aldosterone target's expansion reference — the
    /// sodium-content error (state over this reference) is the
    /// lump's volume-expansion signal to the RAAS limb (see
    /// evaluate()).
    na_content_rest_mmol: f64,
    /// Current lumped intake rates (Milestone 30): water (mL/s) and
    /// sodium (mmol/s) into the systemic venous compartment.
    /// Initialised to the parameters.json baselines; Event::
    /// SetIntake replaces them.
    intake_rate_ml_s: f64,
    intake_na_rate_mmol_s: f64,
    /// The solute-free water channel (Milestone 30): current rate
    /// (mL/s) and its boundary integral (mL), carried in the volume
    /// identity like the other channels' integrals (exact, not
    /// hash-folded — event-determined).
    water_flow_ml_s: f64,
    water_integral_ml: f64,
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
    d_urine: f64,
    // Milestone 26 oncotic-state derivatives (g/s, mL/s).
    d_rbc: f64,
    d_prot_p: f64,
    d_prot_i: f64,
    // Milestone 30 hormonal-axis derivatives: sodium content
    // (mmol/s), intracellular water (mL/s), plasma AVP
    // (pg/mL per s), aldosterone effect state (1/s), and the
    // urinary sodium boundary rate (mmol/s).
    d_na: f64,
    d_icf: f64,
    d_adh: f64,
    d_aldo: f64,
    d_una: f64,
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
        // Milestone 26 oncotic initial conditions: red-cell volume
        // at the resting hematocrit of the total blood volume, and
        // protein masses at the cited resting concentrations over
        // the derived resting plasma volume and the interstitial
        // reservoir volume. At these values the protein fluxes
        // (leak, lymph return, synthesis, catabolism) cancel
        // exactly, so the settle is undisturbed.
        let rbc0 = model.hematocrit_resting * tbv;
        let protein_plasma0 = model.protein_cp0_g_ml * (tbv - rbc0);
        let protein_isf0 = model.protein_ci0_g_ml * model.isf_volume_ml;
        // Milestone 30 hormonal initial conditions, by the disclosed
        // equilibrium construction: the sodium state starts at the
        // resting concentration over the resting extracellular
        // volume (plasma + interstitial), the ICF lump at its cited
        // volume holding solute at the resting osmolality, AVP at
        // the S37 regression's value at that osmolality, the
        // aldosterone effect state at its normalised 1.0, and the
        // intake rates at their parameter baselines (sodium intake
        // equal to baseline excretion). Every hormonal derivative
        // therefore vanishes at the resting operating point and the
        // settle is undisturbed, as with the M25/M26 constructions.
        let ecf0_ml = (tbv - rbc0) + model.isf_volume_ml;
        let na0_mmol = model.na_resting_mmol_l * ecf0_ml / 1000.0;
        let icf_solute_mosm = model.resting_osmolality_mosm_kg() * model.icf_volume_ml / 1000.0;
        let adh0 = model.resting_adh_pg_ml();
        let icf0_ml = model.icf_volume_ml;
        let intake0_ml_s = model.intake_ml_s;
        let na_intake0_mmol_s = model.na_intake0_mmol_s;
        Engine {
            model,
            tick: 0,
            v,
            map_lp: 90.0,
            cap_lp: cap_lp0,
            cap_ref: None,
            veno_ml: 0.0,
            refill_ml: 0.0,
            urine_ml: 0.0,
            intake_ml: 0.0,
            ino_mult: 1.0,
            rbc_ml: rbc0,
            protein_plasma_g: protein_plasma0,
            protein_isf_g: protein_isf0,
            oncotic_ref: None,
            product_flow_ml_s: 0.0,
            product_hematocrit: 0.0,
            product_protein_g_ml: 0.0,
            product_integral_ml: 0.0,
            na_mmol: na0_mmol,
            icf_ml: icf0_ml,
            adh_pg_ml: adh0,
            aldo_state: 1.0,
            urine_na_mmol: 0.0,
            intake_na_mmol: 0.0,
            icf_solute_mosm,
            na_content_rest_mmol: na0_mmol,
            intake_rate_ml_s: intake0_ml_s,
            intake_na_rate_mmol_s: na_intake0_mmol_s,
            water_flow_ml_s: 0.0,
            water_integral_ml: 0.0,
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
        // Milestone 26: the Starling oncotic term's zero is captured
        // at the same moment — the model's own resting oncotic
        // pressures. The protein states are exactly at their initial
        // values here (their fluxes cancel at the operating point
        // and nothing has perturbed them), so the captured values
        // are the cited resting oncotic pressures by construction.
        let (cp, ci) = self.protein_concentrations_g_ml();
        self.oncotic_ref = Some((
            oncotic_pressure_mmhg(cp * 100.0, &self.model),
            oncotic_pressure_mmhg(ci * 100.0, &self.model),
        ));
        self.log.push(LogEntry {
            tick: self.tick,
            text: format!("baroreflex engaged, setpoint MAP = {map:.2} mmHg (model's own resting operating point)"),
        });
    }

    /// The renal function curve's SHAPE (Milestone 25, Guyton
    /// tradition, parameters.json S23): a piecewise-linear multiple
    /// of a baseline output, driven by a pressure offset d from the
    /// operating point through the source chapter's cited anchors —
    /// output essentially zero at d = -renal_zero_offset, 1x at the
    /// operating point, renal_mult_50 x at +50 mmHg, renal_mult_100
    /// x at +100 mmHg; above +100 the last segment's slope continues
    /// (extrapolation, disclosed in the parameter's note). Milestone
    /// 30 factors the shape out of the water curve: sodium excretion
    /// reuses it on a compressed, aldosterone-shifted pressure axis
    /// (the chronic curve — see urine_sodium_rate_mmol_s).
    fn renal_mult(&self, d: f64) -> f64 {
        let m = &self.model;
        if d <= -m.renal_zero_offset_mmhg {
            0.0
        } else if d < 0.0 {
            1.0 + d / m.renal_zero_offset_mmhg
        } else if d <= 50.0 {
            1.0 + d * (m.renal_mult_50 - 1.0) / 50.0
        } else if d <= 100.0 {
            m.renal_mult_50 + (d - 50.0) * (m.renal_mult_100 - m.renal_mult_50) / 50.0
        } else {
            m.renal_mult_100 + (d - 100.0) * (m.renal_mult_100 - m.renal_mult_50) / 50.0
        }
    }

    /// The AVP–urine-osmolality response curve (Milestone 30):
    /// urine osmolality (mOsm/kg) as a saturating function of the
    /// plasma AVP concentration, between the cited floor (50, S39)
    /// and ceiling (1,200, S39), half-maximal at the calibrated
    /// adh_uosm_half_pg_ml — calibrated so the curve passes through
    /// S39's resting ~600 mOsm/kg at the resting AVP and is
    /// near-maximal by 5–6 pg/mL (S38/S49). A Hill form with
    /// exponent 2; the exponent is an engineering choice, disclosed
    /// in the parameter's note.
    fn adh_uosm_curve(&self, adh: f64) -> f64 {
        let m = &self.model;
        let a2 = adh * adh;
        let h2 = m.uosm_half_pg_ml * m.uosm_half_pg_ml;
        m.uosm_min_mosm_kg + (m.uosm_max_mosm_kg - m.uosm_min_mosm_kg) * a2 / (a2 + h2)
    }

    /// Total urinary osmole excretion rate (mOsm/s, Milestone 30):
    /// sodium salts at twice the sodium excretion rate (Na+ with
    /// its accompanying anions) plus the constant non-sodium
    /// (urea-dominated) osmole rate. S39's mechanism — ADH changes
    /// water excretion at nearly constant solute excretion — is
    /// what the urine-osmolality readout and the flow law below are
    /// built on.
    fn urine_osmole_rate_mosm_s(&self, u_na_mmol_s: f64) -> f64 {
        2.0 * u_na_mmol_s + self.model.urine_non_na_osm_mosm_s
    }

    /// Urine WATER output flow (mL/s): the Milestone 25 acute renal
    /// function curve's pressure multiple, applied to the flow the
    /// current solute load implies at the current AVP —
    /// osmole excretion rate over the AVP–urine-osmolality response
    /// curve. At the resting osmole rate this reduces exactly to
    /// the curve-ratio water-permeability multiplier (response
    /// curve at the resting AVP over the curve at the current AVP),
    /// and at the operating point the flow is exactly the baseline
    /// U0 — the resting trajectories are undisturbed by
    /// construction. Formulating the flow on the osmole rate (not
    /// on U0 alone) is what keeps the urine-osmolality readout
    /// inside the kidney's concentrating ceiling when the solute
    /// load itself moves (measured in MILESTONE-30.md: with the
    /// multiplier applied to U0 alone, a sodium load drove the
    /// readout through the cited 1,200 mOsm/kg ceiling). Before
    /// the reflex engages there is no operating point: output is
    /// held exactly equal to the current intake rate so the
    /// reflex-off settle is undisturbed (the source's equilibrium
    /// construction — at the equilibrium point, output equals
    /// intake by definition).
    fn renal_urine_rate_ml_s(&self, map_lp: f64, adh: f64, u_na_mmol_s: f64) -> f64 {
        match self.setpoint_map {
            None => self.intake_rate_ml_s,
            Some(sp) => {
                self.renal_mult(map_lp - sp) * self.urine_osmole_rate_mosm_s(u_na_mmol_s)
                    / self.adh_uosm_curve(adh)
                    * 1000.0
            }
        }
    }

    /// Urine SODIUM excretion rate (mmol/s, Milestone 30): the
    /// CHRONIC pressure–natriuresis relation — the shared curve
    /// shape with its pressure axis compressed by the cited chronic
    /// steepening (S23: chronically, a few mmHg doubles output,
    /// against ~25 mmHg acutely) and shifted along the pressure
    /// axis by the aldosterone effect state (Guyton's curve-shift
    /// formulation; S23/S43): a raised aldosterone state shifts the
    /// relation to higher pressures (retention), a suppressed state
    /// to lower (natriuresis at small pressure cost). Before the
    /// reflex engages, excretion is held exactly equal to the
    /// current sodium intake rate (the equilibrium construction, as
    /// for water).
    fn urine_sodium_rate_mmol_s(&self, map_lp: f64, aldo: f64) -> f64 {
        let m = &self.model;
        match self.setpoint_map {
            None => self.intake_na_rate_mmol_s,
            Some(sp) => {
                let shift = m.aldo_shift_mmhg_per_unit * (aldo - 1.0);
                let d_eff = (map_lp - sp) - shift;
                m.una0_mmol_s * self.renal_mult(m.renal_chronic_steep * d_eff)
            }
        }
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
        rbc: f64,
        prot_p: f64,
        prot_i: f64,
        na: f64,
        icf: f64,
        adh: f64,
        aldo: f64,
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

        // Milestone 26 oncotic state at this stage: concentrations
        // from the stage protein masses over the stage plasma volume
        // (blood volume minus red-cell volume) and the stage
        // interstitial reservoir volume; oncotic pressures through
        // the Nitta relation (S33). Hematocrit is the stage ratio —
        // tracked-but-inert: it enters only this bookkeeping (the
        // plasma-volume identity and the fluxes below), never a
        // resistance or an elastance.
        let v_blood_s: f64 = v.iter().sum();
        let hct_s = if v_blood_s > 0.0 {
            (rbc / v_blood_s).clamp(0.0, 0.95)
        } else {
            0.0
        };
        let v_plasma_s = (v_blood_s - rbc).max(1.0);
        let cp_s = prot_p / v_plasma_s; // g/mL
        // Milestone 30: the interstitial volume identity gains the
        // intracellular exchange — V_isf = V_isf0 − refill +
        // (V_icf0 − V_icf): water the cells release joins the
        // interstitium, water they take up leaves it.
        let v_isf_s = (m.isf_volume_ml - refill + (m.icf_volume_ml - icf)).max(1.0);
        let ci_s = prot_i / v_isf_s; // g/mL
        let pi_c_s = oncotic_pressure_mmhg(cp_s * 100.0, m);
        let pi_i_s = oncotic_pressure_mmhg(ci_s * 100.0, m);

        // Transcapillary refill (Milestone 18): lumped Starling form —
        // net flow proportional to the deficit of mean capillary
        // pressure below its own resting reference. Zero before the
        // reflex engages (no reference captured).
        // Milestone 25: the driver gains the interstitial reservoir's
        // pressure feedback. The reservoir's pressure deviation from
        // its operating point is dP_isf = -refill / C_isf (depleting
        // it lowers its pressure, filling it raises it), and it
        // enters the Starling balance against the capillary term:
        //   Q = k * [ (Pcap_ref - Pcap_lp) - refill / C_isf ].
        // The Milestone 18 hard reserve bound is retired: the flow
        // now stops only at the reservoir's physical floor (refill
        // cannot exceed the interstitial volume itself).
        // Milestone 26: the driver gains the oncotic term in its
        // textbook Starling form, sigma x the deviation of the
        // transcapillary oncotic difference from its own resting
        // value (both references captured at engagement, like
        // cap_ref):
        //   Q = k * [ (Pcap_ref - Pcap_lp) - refill / C_isf
        //             + sigma * ((pi_c - pi_i) - (pi_c_ref - pi_i_ref)) ].
        // Dilution (crystalloid, or refill of protein-poor fluid)
        // lowers pi_c and so brakes refill / drives escape;
        // protein-carrying inputs restore it. Before Milestone 26
        // the driver was pressure-deficit only; the missing term is
        // why the Milestone 25 crystalloid retention (0.49) sat
        // above the volunteer figure it was read against (S27).
        let q_refill = match self.cap_ref {
            None => 0.0,
            Some(r) => {
                let (pi_c_ref, pi_i_ref) = self.oncotic_ref.unwrap_or((pi_c_s, pi_i_s));
                // Milestone 30: the interstitial pressure term is
                // the reservoir's NET volume deviation over its
                // compliance — refill plus the intracellular
                // exchange — which reduces to Milestone 25's
                // -refill / C_isf when the ICF lump is at rest.
                let q = m.refill_k
                    * ((r - cap_lp)
                        + (-refill + (m.icf_volume_ml - icf)) / m.isf_compliance_ml_mmhg
                        + m.sigma_protein * ((pi_c_s - pi_i_s) - (pi_c_ref - pi_i_ref)));
                if refill >= m.isf_volume_ml && q > 0.0 {
                    0.0
                } else {
                    q
                }
            }
        };
        // Milestone 26 protein and red-cell fluxes (per second).
        // Haemorrhage (the event channel's outflow limb) removes
        // whole blood at the stage composition: red cells at the
        // stage hematocrit, protein at the stage plasma
        // concentration over the plasma fraction. The event channel's
        // inflow limb is crystalloid: no cells, no protein. The
        // product channel adds both at the product's composition.
        // Starling protein flux uses the upstream convention,
        // disclosed: on the inflow limb (refill, ISF -> plasma) the
        // incoming fluid carries the interstitial concentration
        // unsieved; on the outflow limb (escape, plasma -> ISF) it
        // carries the sieved plasma concentration (1 - sigma) x cp.
        // The transcapillary leak and the lymphatic return are the
        // slow protein circulation of S29/S32: leak out of plasma at
        // the resting return flux scaled by the plasma concentration
        // ratio, lymph return into plasma at the same flux scaled
        // by the interstitial concentration ratio — exactly balanced
        // at the operating point. Synthesis (S31) enters plasma;
        // the lumped catabolic sink (S31's clearances) leaves it
        // first-order in the plasma mass, calibrated to cancel
        // synthesis at rest.
        let bleed_rate = (-self.ext_flow_ml_s).max(0.0);
        let starling_protein = if q_refill >= 0.0 {
            q_refill * ci_s
        } else {
            q_refill * (1.0 - m.sigma_protein) * cp_s
        };
        let leak = m.lymph_protein_g_s * (cp_s / m.protein_cp0_g_ml);
        let lymph_return = m.lymph_protein_g_s * (ci_s / m.protein_ci0_g_ml);
        let d_rbc = -bleed_rate * hct_s + self.product_flow_ml_s * self.product_hematocrit;
        let d_prot_p = -bleed_rate * (1.0 - hct_s) * cp_s
            + self.product_flow_ml_s * self.product_protein_g_ml
            + starling_protein
            - leak
            + lymph_return
            + m.albumin_synthesis_g_s
            - m.protein_catabolic_frac_s * prot_p;
        let d_prot_i = -starling_protein + leak - lymph_return;
        // Milestone 30 hormonal axes at this stage. Plasma sodium
        // is the sodium state over the stage extracellular volume
        // (plasma + interstitial); calculated osmolality follows
        // S47's formula with its constant non-sodium term. The ICF
        // lump's osmolality is its fixed solute content over its
        // stage volume, and water crosses the cell membrane toward
        // the higher osmolality at the calibrated conductance.
        let v_ecf_s = v_plasma_s + v_isf_s;
        let na_conc_s = na * 1000.0 / v_ecf_s; // mmol/L
        let osm_s = 2.0 * na_conc_s + m.osm_non_sodium_mosm_kg; // mOsm/kg
        let osm_icf_s = self.icf_solute_mosm / (icf.max(1.0) / 1000.0);
        let d_icf = m.icf_k_ml_s_mosm * (osm_icf_s - osm_s);
        // ADH target: the osmotic limb is S37's regression at the
        // stage osmolality; the volume limb (S38) adds on the MAP
        // deficit against the set-point — zero below the cited 8%
        // threshold, full-scale at the cited 25% deficit where AVP
        // reaches 20-30x normal. AVP's own V1 vasoconstrictor
        // action is NOT an effector here (disclosed). The state
        // approaches the target at the lumped secretion-clearance
        // time constant (S36/S38).
        let osm_part = m.adh_slope_pg_ml_mosm * (osm_s - m.adh_threshold_mosm_kg).max(0.0);
        let vol_part = match self.setpoint_map {
            None => 0.0,
            Some(sp) => {
                let deficit = ((sp - map_lp) / sp).max(0.0);
                if deficit <= m.adh_vol_threshold {
                    0.0
                } else {
                    m.adh_vol_max_pg_ml
                        * ((deficit - m.adh_vol_threshold)
                            / (m.adh_vol_full - m.adh_vol_threshold))
                            .clamp(0.0, 1.0)
                }
            }
        };
        let d_adh = (osm_part + vol_part - adh) / m.adh_tau_s;
        // Aldosterone target: renal perfusion deficit raises it,
        // sodium-content excess suppresses it (S43's mechanism;
        // gains VERIFY-flagged), bounded by the flagged floor and
        // ceiling. The sodium input is the CONTENT error, not the
        // concentration error — measured reason (MILESTONE-30.md):
        // water follows sodium, so under an isotonic load the
        // concentration error saturates at under 1% while the
        // content error reaches +21%; a concentration input cannot
        // express the cited suppression. The content error is the
        // lump's expansion signal (the integrated renin pathway's
        // inputs — perfusion, macula-densa delivery, atrial
        // stretch — all track the expanded state, not the clamped
        // concentration). The EFFECT state approaches the target
        // at the genomic timescale (S41/S42) — hours, deliberately
        // the slowest limb in the engine.
        let perf_err = match self.setpoint_map {
            None => 0.0,
            Some(sp) => (sp - map_lp) / sp,
        };
        let na_err = (na - self.na_content_rest_mmol) / self.na_content_rest_mmol;
        let aldo_target = (1.0 + m.aldo_gain_perf * perf_err - m.aldo_gain_na * na_err)
            .clamp(m.aldo_floor, m.aldo_ceiling);
        let d_aldo = (aldo_target - aldo) / m.aldo_tau_s;
        // Renal excretion: water on the acute curve times the ADH
        // multiplier; sodium on the chronic, aldosterone-shifted
        // curve. Both leave the systemic venous compartment (the
        // sodium leaves the sodium state, not a volume).
        let u_na = self.urine_sodium_rate_mmol_s(map_lp, aldo);
        let q_urine = self.renal_urine_rate_ml_s(map_lp, adh, u_na);
        // Sodium balance at this stage (mmol/s): intake in; urinary
        // excretion out; the event channel's inflow carries sodium
        // at the crystalloid concentration (S50), its outflow limb
        // (haemorrhage) removes sodium at the stage plasma
        // concentration over the plasma fraction; the product
        // channel returns sodium at the resting plasma concentration
        // over the product's plasma fraction. Starling and ICF
        // transfers are internal to the ECF and carry no net sodium
        // flux in this lump (the ISF and plasma share one
        // concentration by construction).
        let inflow_rate = self.ext_flow_ml_s.max(0.0);
        let d_na = self.intake_na_rate_mmol_s - u_na
            + inflow_rate * m.crystalloid_na_mmol_l / 1000.0
            + self.product_flow_ml_s * (1.0 - self.product_hematocrit)
                * m.na_resting_mmol_l
                / 1000.0
            - bleed_rate * (1.0 - hct_s) * na_conc_s / 1000.0;
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
            q_sc - q_tv + self.ext_flow_ml_s + self.product_flow_ml_s + self.water_flow_ml_s
                + q_refill + self.intake_rate_ml_s - q_urine,
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
            d_urine: q_urine,
            d_rbc,
            d_prot_p,
            d_prot_i,
            d_na,
            d_icf,
            d_adh,
            d_aldo,
            d_una: u_na,
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
        let mut k_ur: [f64; 4] = [0.0; 4];
        let mut k_rb: [f64; 4] = [0.0; 4];
        let mut k_pp: [f64; 4] = [0.0; 4];
        let mut k_pi: [f64; 4] = [0.0; 4];
        let mut k_na: [f64; 4] = [0.0; 4];
        let mut k_ic: [f64; 4] = [0.0; 4];
        let mut k_ad: [f64; 4] = [0.0; 4];
        let mut k_al: [f64; 4] = [0.0; 4];
        let mut k_un: [f64; 4] = [0.0; 4];
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
            let rbc_s = stage(self.rbc_ml, k_rb[s.saturating_sub(1)], s);
            let pp_s = stage(self.protein_plasma_g, k_pp[s.saturating_sub(1)], s);
            let pi_s = stage(self.protein_isf_g, k_pi[s.saturating_sub(1)], s);
            let na_s = stage(self.na_mmol, k_na[s.saturating_sub(1)], s);
            let icf_s = stage(self.icf_ml, k_ic[s.saturating_sub(1)], s);
            let adh_s = stage(self.adh_pg_ml, k_ad[s.saturating_sub(1)], s);
            let aldo_s = stage(self.aldo_state, k_al[s.saturating_sub(1)], s);
            let tau_s = self.tau + stage_frac[s] * h;
            let ev = self.evaluate(
                &vs, map_s, cap_s, veno_s, refill_s, ino_s, rbc_s, pp_s, pi_s, na_s, icf_s, adh_s,
                aldo_s, tau_s, period, tv,
            );
            k_v[s] = ev.derivs;
            k_m[s] = ev.d_map_lp;
            k_c[s] = ev.d_cap_lp;
            k_vn[s] = ev.d_veno;
            k_rf[s] = ev.d_refill;
            k_in[s] = ev.d_ino;
            k_ur[s] = ev.d_urine;
            k_rb[s] = ev.d_rbc;
            k_pp[s] = ev.d_prot_p;
            k_pi[s] = ev.d_prot_i;
            k_na[s] = ev.d_na;
            k_ic[s] = ev.d_icf;
            k_ad[s] = ev.d_adh;
            k_al[s] = ev.d_aldo;
            k_un[s] = ev.d_una;
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
        // Milestone 25 boundary states: urine is RK4-integrated like
        // every other state; intake is a constant rate, integrated
        // exactly.
        self.urine_ml += rk4(k_ur);
        self.intake_ml += self.intake_rate_ml_s * h;
        self.ext_integral_ml += self.ext_flow_ml_s * h;
        // Milestone 26 oncotic states: RK4-integrated like every
        // other state; the product boundary integral is exact (its
        // rate is piecewise constant, set by events). The mass
        // floors are numeric guards only — the fluxes cannot drive
        // either mass negative at these rates and step sizes, and
        // the guard keeps a pathological stage value from doing so.
        self.rbc_ml = (self.rbc_ml + rk4(k_rb)).max(0.0);
        self.protein_plasma_g = (self.protein_plasma_g + rk4(k_pp)).max(0.0);
        self.protein_isf_g = (self.protein_isf_g + rk4(k_pi)).max(0.0);
        self.product_integral_ml += self.product_flow_ml_s * h;
        // Milestone 30 hormonal states: RK4-integrated like every
        // other state, with the same class of numeric floor guards
        // as the protein masses (the fluxes cannot drive any of
        // them negative at these rates and step sizes; the ICF
        // floor keeps the osmolality ratio defined). The sodium
        // intake boundary integral is exact (piecewise-constant
        // rate), like the product integral.
        self.na_mmol = (self.na_mmol + rk4(k_na)).max(0.0);
        self.icf_ml = (self.icf_ml + rk4(k_ic)).max(1.0);
        self.adh_pg_ml = (self.adh_pg_ml + rk4(k_ad)).max(0.0);
        self.aldo_state = (self.aldo_state + rk4(k_al)).max(0.0);
        self.urine_na_mmol += rk4(k_un);
        self.intake_na_mmol += self.intake_na_rate_mmol_s * h;
        self.water_integral_ml += self.water_flow_ml_s * h;
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
                Event::SetProductFlow {
                    rate_ml_s,
                    hematocrit,
                    protein_g_per_ml,
                    label,
                } => {
                    self.product_flow_ml_s = rate_ml_s;
                    self.product_hematocrit = hematocrit;
                    self.product_protein_g_ml = protein_g_per_ml;
                    self.log.push(LogEntry {
                        tick: self.tick,
                        text: format!(
                            "{label}: product flow set to {rate_ml_s:.3} mL/s (hematocrit {hematocrit:.2}, protein {protein_g_per_ml:.4} g/mL)"
                        ),
                    });
                }
                Event::SetWaterFlow { rate_ml_s, label } => {
                    self.water_flow_ml_s = rate_ml_s;
                    self.log.push(LogEntry {
                        tick: self.tick,
                        text: format!(
                            "{label}: solute-free water flow set to {rate_ml_s:.3} mL/s"
                        ),
                    });
                }
                Event::SetIntake {
                    water_ml_min,
                    sodium_mmol_min,
                    label,
                } => {
                    self.intake_rate_ml_s = water_ml_min / 60.0;
                    self.intake_na_rate_mmol_s = sodium_mmol_min / 60.0;
                    self.log.push(LogEntry {
                        tick: self.tick,
                        text: format!(
                            "{label}: intake set to {water_ml_min:.3} mL/min water, {sodium_mmol_min:.4} mmol/min sodium"
                        ),
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
        // Milestone 25: the renal/intake boundary states join the
        // fold (after ino_mult; the fold order is part of the trace
        // format, so all Milestone 25 hashes differ from Milestone
        // 24's even where trajectories agree).
        h = fnv_fold(h, &self.urine_ml.to_bits().to_le_bytes());
        h = fnv_fold(h, &self.intake_ml.to_bits().to_le_bytes());
        // Milestone 26: the oncotic states join the fold (after
        // intake; the fold order is part of the trace format, so all
        // Milestone 26 hashes differ from Milestone 25's even where
        // trajectories agree). The product boundary integral is not
        // folded, like the event channel's integral — it is
        // event-determined.
        h = fnv_fold(h, &self.rbc_ml.to_bits().to_le_bytes());
        h = fnv_fold(h, &self.protein_plasma_g.to_bits().to_le_bytes());
        h = fnv_fold(h, &self.protein_isf_g.to_bits().to_le_bytes());
        // Milestone 30: the hormonal states join the fold (after
        // the oncotic states; the fold order is part of the trace
        // format, so all Milestone 30 hashes differ from Milestone
        // 26's even where trajectories agree). The sodium intake
        // boundary integral is not folded, like the product
        // integral — it is event-determined.
        h = fnv_fold(h, &self.na_mmol.to_bits().to_le_bytes());
        h = fnv_fold(h, &self.icf_ml.to_bits().to_le_bytes());
        h = fnv_fold(h, &self.adh_pg_ml.to_bits().to_le_bytes());
        h = fnv_fold(h, &self.aldo_state.to_bits().to_le_bytes());
        h = fnv_fold(h, &self.urine_na_mmol.to_bits().to_le_bytes());
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
        // Conserved quantity: compartment sum minus ALL boundary
        // inflows plus the boundary outflow — the event channel
        // (ext_integral_ml), the transcapillary refill state
        // (Milestone 18; an inflow from the interstitial reservoir),
        // and, Milestone 25, the lumped fluid intake (inflow) and
        // cumulative urine (outflow). Milestone 26 adds the product
        // channel's boundary integral (an inflow). Milestone 30
        // adds the solute-free water channel's boundary integral
        // (an inflow). At t = 0 every
        // boundary integral is zero, so the identity starts exact.
        self.v.iter().sum::<f64>() - self.ext_integral_ml - self.product_integral_ml
            - self.water_integral_ml
            - self.refill_ml - self.intake_ml
            + self.urine_ml
    }

    /// Net cumulative transcapillary transfer into the circulation
    /// (mL, Milestone 18): positive = refill, negative = net escape.
    pub fn net_refill_ml(&self) -> f64 {
        self.refill_ml
    }

    /// Cumulative urine output (mL, Milestone 25).
    pub fn cumulative_urine_ml(&self) -> f64 {
        self.urine_ml
    }

    /// Cumulative fluid intake (mL, Milestone 25).
    pub fn cumulative_intake_ml(&self) -> f64 {
        self.intake_ml
    }

    /// Cumulative blood-product volume infused (mL, Milestone 26).
    pub fn cumulative_product_ml(&self) -> f64 {
        self.product_integral_ml
    }

    /// Red-cell volume (mL, Milestone 26).
    pub fn rbc_volume_ml(&self) -> f64 {
        self.rbc_ml
    }

    /// Hematocrit (Milestone 26): red-cell volume over total blood
    /// volume. TRACKED-BUT-INERT — reported and used by the
    /// plasma-volume identity; it drives no resistance or elastance.
    pub fn hematocrit(&self) -> f64 {
        let vb: f64 = self.v.iter().sum();
        if vb > 0.0 {
            self.rbc_ml / vb
        } else {
            0.0
        }
    }

    /// Plasma volume (mL, Milestone 26): total blood volume minus
    /// red-cell volume — the identity hematocrit feeds. No F-cell
    /// (whole-body vs large-vessel hematocrit) correction is
    /// applied; the lumped circulation has one hematocrit.
    pub fn plasma_volume_ml(&self) -> f64 {
        self.v.iter().sum::<f64>() - self.rbc_ml
    }

    /// Protein concentrations (plasma, interstitial) in g/mL
    /// (Milestone 26): the protein masses over the derived plasma
    /// volume and the interstitial reservoir volume (Milestone 25).
    pub fn protein_concentrations_g_ml(&self) -> (f64, f64) {
        let vp = self.plasma_volume_ml().max(1.0);
        let visf = self.interstitial_volume_ml().max(1.0);
        (
            self.protein_plasma_g / vp,
            self.protein_isf_g / visf,
        )
    }

    /// Plasma oncotic pressure (mmHg, Milestone 26): the Nitta
    /// relation (S33) at the current plasma protein concentration.
    pub fn plasma_oncotic_mmhg(&self) -> f64 {
        oncotic_pressure_mmhg(self.protein_concentrations_g_ml().0 * 100.0, &self.model)
    }

    /// Interstitial oncotic pressure (mmHg, Milestone 26): the same
    /// relation at the interstitial concentration.
    pub fn isf_oncotic_mmhg(&self) -> f64 {
        oncotic_pressure_mmhg(self.protein_concentrations_g_ml().1 * 100.0, &self.model)
    }

    /// Instantaneous urine output rate (mL/min, Milestone 25): the
    /// lumped renal function curve evaluated at the current sensed
    /// MAP, times the Milestone 30 ADH water-permeability
    /// multiplier at the current AVP state. Before the reflex
    /// engages this equals the intake rate by the equilibrium
    /// construction.
    pub fn urine_rate_ml_min(&self) -> f64 {
        let u_na = self.urine_sodium_rate_mmol_s(self.map_lp, self.aldo_state);
        self.renal_urine_rate_ml_s(self.map_lp, self.adh_pg_ml, u_na) * 60.0
    }

    /// Interstitial fluid volume (mL, Milestone 25): the finite
    /// reservoir's current content, by the identity
    /// V_isf = interstitial_volume_ml - refill_ml. Milestone 30:
    /// the identity gains the intracellular exchange — water the
    /// ICF lump releases joins the reservoir, water it takes up
    /// leaves it: V_isf = V_isf0 - refill + (V_icf0 - V_icf).
    pub fn interstitial_volume_ml(&self) -> f64 {
        self.model.isf_volume_ml - self.refill_ml
            + (self.model.icf_volume_ml - self.icf_ml)
    }

    /// Interstitial pressure deviation from the operating point
    /// (mmHg, Milestone 25): the reservoir's net volume deviation
    /// over its compliance, dP_isf = (V_isf - V_isf0) / C_isf —
    /// Milestone 30: the deviation includes the intracellular
    /// exchange, reducing to Milestone 25's -refill_ml / C_isf when
    /// the ICF lump is at rest. The absolute interstitial pressure
    /// is not a state (the engine's pressures are self-referenced
    /// like the refill driver itself); the deviation is the
    /// quantity that enters the Starling balance.
    pub fn interstitial_pressure_deviation_mmhg(&self) -> f64 {
        (self.interstitial_volume_ml() - self.model.isf_volume_ml)
            / self.model.isf_compliance_ml_mmhg
    }

    // ---- Hormonal volume axes (Milestone 30) ----
    //
    // Readouts of the sodium/osmolality lump and the two axes.
    // Nothing here feeds back into the integration.

    /// Extracellular fluid volume (mL): plasma volume plus the
    /// interstitial reservoir's current volume.
    pub fn ecf_volume_ml(&self) -> f64 {
        self.plasma_volume_ml() + self.interstitial_volume_ml()
    }

    /// Total body water (mL): extracellular volume plus the
    /// intracellular lump.
    pub fn total_body_water_ml(&self) -> f64 {
        self.ecf_volume_ml() + self.icf_ml
    }

    /// Extracellular sodium content (mmol): the osmotic lump state.
    pub fn sodium_content_mmol(&self) -> f64 {
        self.na_mmol
    }

    /// Plasma sodium concentration (mmol/L): the sodium state over
    /// the extracellular volume (the lump's one concentration —
    /// plasma and interstitium share it by construction).
    pub fn plasma_sodium_mmol_l(&self) -> f64 {
        self.na_mmol * 1000.0 / self.ecf_volume_ml().max(1.0)
    }

    /// Calculated plasma osmolality (mOsm/kg): 2[Na] + the constant
    /// non-sodium term of S47's formula.
    pub fn plasma_osmolality_mosm_kg(&self) -> f64 {
        2.0 * self.plasma_sodium_mmol_l() + self.model.osm_non_sodium_mosm_kg
    }

    /// Intracellular water volume (mL): the osmotic buffer lump.
    pub fn icf_volume_ml(&self) -> f64 {
        self.icf_ml
    }

    /// Plasma AVP/ADH concentration (pg/mL).
    pub fn adh_pg_ml(&self) -> f64 {
        self.adh_pg_ml
    }

    /// Aldosterone effect state (normalised; 1.0 at rest).
    pub fn aldosterone_state(&self) -> f64 {
        self.aldo_state
    }

    /// Instantaneous urine sodium excretion rate (mmol/min): the
    /// chronic, aldosterone-shifted curve at the current sensed MAP
    /// and aldosterone state. Before the reflex engages this equals
    /// the sodium intake rate by the equilibrium construction.
    pub fn urine_sodium_rate_mmol_min(&self) -> f64 {
        self.urine_sodium_rate_mmol_s(self.map_lp, self.aldo_state) * 60.0
    }

    /// Urine sodium concentration (mmol/L): the excretion rate over
    /// the urine flow. At negligible flow there is no urine to
    /// measure; NaN is returned rather than a fabricated value.
    pub fn urine_sodium_conc_mmol_l(&self) -> f64 {
        let flow = self.urine_rate_ml_min();
        if flow > 1e-9 {
            self.urine_sodium_rate_mmol_min() / flow * 1000.0
        } else {
            f64::NAN
        }
    }

    /// Urine osmolality readout (mOsm/kg): the total urinary
    /// osmole excretion rate over the urine flow. Honest because
    /// ADH moves water at nearly constant solute excretion (S39's
    /// mechanism): the readout is high exactly when the flow is
    /// low against a steady solute load, and the flow law's
    /// construction keeps it at the response curve's value
    /// whenever the pressure multiple is 1. In OLIGURIA
    /// (< 0.5 mL/min) the ratio is NOT reported: as filtration
    /// collapses the constant-solute-load assumption fails (a real
    /// kidney's solute excretion falls with its filtration, and no
    /// collecting duct exceeds the concentrating ceiling), so the
    /// ratio would fabricate values above the cited 1,200 mOsm/kg
    /// ceiling — measured in MILESTONE-30.md (2,156 mOsm/kg at
    /// +2 min of the haemorrhage course). Instead the kidney's
    /// concentrating STATE is reported: the AVP–urine-osmolality
    /// response curve at the current AVP, which is the
    /// concentration the next urine formed would carry. Every
    /// gated use of this readout sits at flows above the
    /// threshold, where the ratio definition applies.
    pub fn urine_osmolality_mosm_kg(&self) -> f64 {
        let flow_ml_min = self.urine_rate_ml_min();
        if flow_ml_min > 0.5 {
            let osm_rate_mosm_min =
                self.urine_osmole_rate_mosm_s(self.urine_sodium_rate_mmol_min() / 60.0) * 60.0;
            osm_rate_mosm_min / (flow_ml_min / 1000.0)
        } else {
            self.adh_uosm_curve(self.adh_pg_ml)
        }
    }

    /// Cumulative urinary sodium (mmol).
    pub fn cumulative_urine_sodium_mmol(&self) -> f64 {
        self.urine_na_mmol
    }

    /// Cumulative sodium intake (mmol).
    pub fn cumulative_sodium_intake_mmol(&self) -> f64 {
        self.intake_na_mmol
    }

    /// Cumulative solute-free water infused (mL, Milestone 30).
    pub fn cumulative_water_ml(&self) -> f64 {
        self.water_integral_ml
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
            // Milestone 25 volume-side states (instantaneous, like
            // the mechanism states above).
            "urine_output" => (self.urine_rate_ml_min(), "mL/min"),
            "cumulative_urine" => (self.urine_ml, "mL"),
            "cumulative_intake" => (self.intake_ml, "mL"),
            "interstitial_volume" => (self.interstitial_volume_ml(), "mL"),
            "interstitial_pressure_deviation" => {
                (self.interstitial_pressure_deviation_mmhg(), "mmHg")
            }
            // Milestone 26 oncotic states (instantaneous, like the
            // mechanism states above).
            "hematocrit" => (self.hematocrit(), "fraction"),
            "rbc_volume" => (self.rbc_ml, "mL"),
            "plasma_protein" => (self.protein_concentrations_g_ml().0 * 100.0, "g/dL"),
            "isf_protein" => (self.protein_concentrations_g_ml().1 * 100.0, "g/dL"),
            "plasma_oncotic_pressure" => (self.plasma_oncotic_mmhg(), "mmHg"),
            "isf_oncotic_pressure" => (self.isf_oncotic_mmhg(), "mmHg"),
            "cumulative_product" => (self.product_integral_ml, "mL"),
            // Milestone 30 hormonal axes (instantaneous, like the
            // mechanism states above).
            "plasma_sodium" => (self.plasma_sodium_mmol_l(), "mmol/L"),
            "plasma_osmolality" => (self.plasma_osmolality_mosm_kg(), "mOsm/kg"),
            "plasma_adh" => (self.adh_pg_ml, "pg/mL"),
            "aldosterone_state" => (self.aldo_state, "ratio"),
            "urine_osmolality" => (self.urine_osmolality_mosm_kg(), "mOsm/kg"),
            "urine_sodium_rate" => (self.urine_sodium_rate_mmol_min(), "mmol/min"),
            "urine_sodium_concentration" => (self.urine_sodium_conc_mmol_l(), "mmol/L"),
            "ecf_volume" => (self.ecf_volume_ml(), "mL"),
            "icf_volume" => (self.icf_ml, "mL"),
            "total_body_water" => (self.total_body_water_ml(), "mL"),
            "cumulative_urine_sodium" => (self.urine_na_mmol, "mmol"),
            "cumulative_sodium_intake" => (self.intake_na_mmol, "mmol"),
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
