//! The attempt runner: executes a scripted trace against the
//! procedure model and the physiology engine, evaluates every safety
//! gate, computes complications from attempt state, and emits a
//! scored debrief (PEARLS structure, T10).
//!
//! State the model tracks — because the injury literature says the
//! injury lives here, not in hand movements (T1: 97% perceptual):
//!   - which structures have been *identified*
//!   - which Critical View criteria have been *demonstrated*, and when
//!   - which structures carry clips, and whether the clip state was
//!     established before or after identification
//!   - which structures have been divided
//!
//! A divide action is resolved against that state. Dividing the
//! presumed cystic duct before the Critical View resolves to the
//! common bile duct (Stewart-Way class III, 61% of the Way series);
//! dividing the cystic artery in the replaced-RHA variant case
//! without having identified the variant vessel resolves to the
//! replaced artery. Both are attempt-failing by the procedure's
//! master rule, and any resulting haemorrhage is computed by the
//! physiology engine from the bleed rate (a verify-flagged theatre
//! parameter) and the simulated time to control — the trace script
//! never states a blood loss.

use crate::model::{Action, Procedure, TheatreParams, Trace};
use anatomica_physiology::engine::{Engine, Event, TICK_SECONDS};
use anatomica_physiology::params::Params as PhysParams;
use serde::Serialize;
use std::collections::{HashMap, HashSet};

const SETTLE_TICKS: u64 = 6000;
const TAIL_TICKS: u64 = 6000; // 120 s of observation after the last action
const CRITICAL: [&str; 3] = ["duct.cystic-duct", "artery.cystic", "artery.cystic-branch-2"];

// ---------------------------------------------------------------------------
// Debrief (serialised; the independent checker recomputes its arithmetic)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize)]
pub struct LogLine {
    pub t_s: f64,
    pub kind: String,
    pub text: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ErrorEvent {
    pub t_s: f64,
    pub id: String,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct Complication {
    pub kind: String,
    pub t_onset_s: f64,
    pub detail: String,
    pub resolved_structure: Option<String>,
    pub stewart_way_class: Option<String>,
    pub recognised: bool,
    pub controlled_s: Option<f64>,
    pub loss_ml: Option<f64>,
}

#[derive(Debug, Clone, Serialize)]
pub struct DecisionMade {
    pub t_s: f64,
    pub id: String,
    pub choice: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ChecklistScore {
    pub completed: usize,
    pub required: usize,
    pub pct: f64,
    pub missing: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct SafetyScore {
    pub criteria_before_first_clipdiv: usize,
    pub pause_before_first_clip: bool,
    pub points: usize,
    pub max: usize,
    pub note: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ProcessScore {
    pub points: usize,
    pub max: usize,
    pub sign_in: bool,
    pub time_out: bool,
    pub sign_out: bool,
    pub prophylaxis_in_window: bool,
    pub planning_complete: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct PhysiologyScore {
    pub points: usize,
    pub max: usize,
    pub time_points: usize,
    pub nadir_points: usize,
    pub loss_points: usize,
    pub map_nadir_mmhg: f64,
    pub map_baseline_mmhg: f64,
    pub seconds_below_threshold: f64,
    pub blood_loss_ml: f64,
    pub blood_loss_crosscheck_ml: f64,
    pub infused_ml: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct ManagementScore {
    pub points: usize,
    pub max: usize,
    pub recognised: usize,
    pub control: usize,
    pub escalation: usize,
    pub plan: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct Pearls {
    pub description: Vec<String>,
    pub plus: Vec<String>,
    pub delta: Vec<String>,
    pub directive: Vec<String>,
    pub summary: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct Debrief {
    pub trace_id: String,
    pub trace_name: String,
    pub procedure_id: String,
    pub case_variant: Option<String>,
    pub verdict: String,
    pub failed_at_s: Option<f64>,
    pub fail_reason: Option<String>,
    pub validity_label: String,
    pub duration_s: f64,
    pub checklist: ChecklistScore,
    pub safety_gate: SafetyScore,
    pub process: ProcessScore,
    pub physiology: PhysiologyScore,
    pub management: Option<ManagementScore>,
    pub errors: Vec<ErrorEvent>,
    pub complications: Vec<Complication>,
    pub decisions: Vec<DecisionMade>,
    pub engine_trace_hash: String,
    pub engine_beats: usize,
    pub engine_conservation_error_ml: f64,
    pub debrief: Pearls,
    pub event_log: Vec<LogLine>,
}

// ---------------------------------------------------------------------------
// Runner state
// ---------------------------------------------------------------------------

struct Bleed {
    source: String,
    rate_ml_s: f64,
    t_start: f64,
    t_end: Option<f64>,
    complication_idx: usize,
}

struct Attempt<'a> {
    proc: &'a Procedure,
    params: &'a TheatreParams,
    variant: Option<String>,
    engine: Engine,
    beats_at_start: usize,
    volume_at_start: f64,
    // procedure state
    performed: HashMap<String, f64>,
    criteria: HashMap<String, f64>,
    identified: HashSet<String>,
    clipped: HashSet<String>,
    divided: HashSet<String>,
    misclip_cbd: Option<f64>,
    required: HashSet<String>,
    // outcomes
    errors: Vec<ErrorEvent>,
    complications: Vec<Complication>,
    decisions: Vec<DecisionMade>,
    failed: Option<(f64, String)>,
    // process state
    prophylaxis_t: Option<f64>,
    incision_t: Option<f64>,
    pause_t: Option<f64>,
    checklist_done: HashSet<String>,
    first_clipdiv_t: Option<f64>,
    // management state
    help_calls: Vec<String>,
    recognised_kinds: HashSet<String>,
    drain_placed: bool,
    bailout_chosen: bool,
    // flows
    bleeds: Vec<Bleed>,
    flow_sources: Vec<(String, f64)>, // (label, rate) — engine has ONE ext-flow channel; we net
    pending_infusion_stops: Vec<(u64, String)>,
    infused_ml: f64,
    log: Vec<LogLine>,
}

impl<'a> Attempt<'a> {
    fn log(&mut self, t_s: f64, kind: &str, text: String) {
        self.log.push(LogLine { t_s, kind: kind.to_string(), text });
    }

    fn error(&mut self, t_s: f64, id: &str, detail: String) {
        self.errors.push(ErrorEvent { t_s, id: id.to_string(), detail: detail.clone() });
        self.log(t_s, "error", format!("{id}: {detail}"));
    }

    fn fail(&mut self, t_s: f64, reason: String) {
        if self.failed.is_none() {
            self.log(t_s, "fail", reason.clone());
            self.failed = Some((t_s, reason));
        }
    }

    fn cvs_at(&self, t_s: f64) -> bool {
        ["crit1", "crit2", "crit3"]
            .iter()
            .all(|c| self.criteria.get(*c).map(|t| *t <= t_s).unwrap_or(false))
    }

    fn crit_count_at(&self, t_s: f64) -> usize {
        ["crit1", "crit2", "crit3"]
            .iter()
            .filter(|c| self.criteria.get(**c).map(|t| *t <= t_s).unwrap_or(false))
            .count()
    }

    // -- flow bookkeeping ---------------------------------------------------

    fn apply_net_flow(&mut self) {
        let net: f64 = self.flow_sources.iter().map(|(_, r)| *r).sum();
        let label = self
            .flow_sources
            .iter()
            .map(|(l, _)| l.clone())
            .collect::<Vec<_>>()
            .join(" + ");
        let tick = self.engine.tick;
        self.engine.apply(
            tick,
            Event::SetExtFlow {
                rate_ml_s: net,
                label: if label.is_empty() { "theatre: no active flow".into() } else { format!("theatre: {label}") },
            },
        );
    }

    fn start_flow(&mut self, label: &str, rate_ml_s: f64) {
        self.flow_sources.push((label.to_string(), rate_ml_s));
        self.apply_net_flow();
    }

    fn stop_flow(&mut self, label: &str) {
        self.flow_sources.retain(|(l, _)| l != label);
        self.apply_net_flow();
    }

    fn advance_to(&mut self, t_s: f64) {
        let target = SETTLE_TICKS + (t_s / TICK_SECONDS).round() as u64;
        loop {
            // fire infusion stops scheduled exactly at this tick
            let due: Vec<String> = self
                .pending_infusion_stops
                .iter()
                .filter(|(t, _)| *t == self.engine.tick)
                .map(|(_, l)| l.clone())
                .collect();
            if !due.is_empty() {
                self.pending_infusion_stops.retain(|(t, _)| *t != self.engine.tick);
                for label in due {
                    self.stop_flow(&label);
                }
            }
            if self.engine.tick >= target {
                break;
            }
            self.engine.tick();
        }
    }

    fn start_bleed(&mut self, t_s: f64, source: &str, rate_ml_s: f64, detail: String) -> usize {
        let idx = self.complications.len();
        self.complications.push(Complication {
            kind: "hemorrhage".to_string(),
            t_onset_s: t_s,
            detail,
            resolved_structure: Some(source.to_string()),
            stewart_way_class: None,
            recognised: false,
            controlled_s: None,
            loss_ml: None,
        });
        self.bleeds.push(Bleed {
            source: source.to_string(),
            rate_ml_s,
            t_start: t_s,
            t_end: None,
            complication_idx: idx,
        });
        self.start_flow(&format!("bleed:{source}"), -rate_ml_s);
        idx
    }

    fn stop_bleed(&mut self, t_s: f64, source: &str, how: &str) {
        let mut hit = false;
        for i in 0..self.bleeds.len() {
            if self.bleeds[i].source == source && self.bleeds[i].t_end.is_none() {
                self.bleeds[i].t_end = Some(t_s);
                let ci = self.bleeds[i].complication_idx;
                self.complications[ci].controlled_s = Some(t_s);
                self.complications[ci].recognised = true;
                hit = true;
            }
        }
        if hit {
            self.recognised_kinds.insert("hemorrhage".to_string());
            self.log(t_s, "control", format!("haemorrhage from {source} controlled ({how})"));
        }
        if self.flow_sources.iter().any(|(l, _)| l == &format!("bleed:{source}")) {
            self.stop_flow(&format!("bleed:{source}"));
        }
    }

    // -- actions --------------------------------------------------------------

    fn do_microstep(&mut self, t_s: f64, id: &str) {
        let m = match self.proc.microstep(id) {
            Some(m) => m.clone(),
            None => {
                self.log(t_s, "warn", format!("trace references unknown microstep {id}"));
                return;
            }
        };
        if self.performed.contains_key(id) {
            self.log(t_s, "note", format!("microstep {id} repeated; counted once"));
            return;
        }
        self.performed.insert(id.to_string(), t_s);
        self.log(t_s, "step", format!("{id}: {}", m.label));

        if id == "m1.1" && self.incision_t.is_none() {
            self.incision_t = Some(t_s);
        }
        match m.fulfills.as_deref() {
            Some("prophylaxis") => {
                if self.prophylaxis_t.is_none() {
                    self.prophylaxis_t = Some(t_s);
                }
            }
            Some("preclip-pause") => {
                if self.pause_t.is_none() {
                    self.pause_t = Some(t_s);
                }
            }
            Some(who) if who.starts_with("who.") => {
                self.checklist_done.insert(who.to_string());
            }
            _ => {}
        }
        if let Some(c) = &m.demonstrates {
            self.criteria.insert(c.clone(), t_s);
            if self.cvs_at(t_s) {
                self.log(t_s, "gate", "Critical View of Safety achieved: all three criteria demonstrated".into());
            }
        }
        if id == "m7.6" || id == "m6b.6" {
            self.drain_placed = true;
        }

        let target = m.targets.first().cloned().unwrap_or_default();
        match m.verb.as_str() {
            "clip" if CRITICAL.contains(&target.as_str()) => {
                self.on_clip(t_s, &m, &target);
            }
            "divide" if CRITICAL.contains(&target.as_str()) => {
                self.on_divide(t_s, &m, &target);
            }
            _ => {}
        }

        // Liver-bed dissection with an uncontrolled second arterial
        // branch still attached (double-cystic variant): computed
        // haemorrhage from the branch until it is clipped.
        if id == "m7.1" && self.variant_active("variant.double-cystic") {
            let branch_open = !self.divided.contains("artery.cystic-branch-2")
                && !self.clipped.contains("artery.cystic-branch-2");
            let already_bled = self.bleeds.iter().any(|b| b.source == "artery.cystic-branch-2");
            if branch_open && !already_bled {
                self.error(
                    t_s,
                    "err.uncontrolled-branch",
                    "liver-bed dissection begun with the second cystic artery branch uncontrolled".into(),
                );
                let rate = self.params.get("bleed_rate_uncontrolled_branch_ml_s");
                self.start_bleed(
                    t_s,
                    "artery.cystic-branch-2",
                    rate,
                    format!("haemorrhage from the uncontrolled second cystic artery branch (rate {rate} mL/s — verify-flagged engineering parameter)"),
                );
            }
        }
    }

    fn variant_active(&self, id: &str) -> bool {
        self.variant.as_deref() == Some(id)
    }

    fn on_clip(&mut self, t_s: f64, m: &crate::model::Microstep, target: &str) {
        if self.first_clipdiv_t.is_none() {
            self.first_clipdiv_t = Some(t_s);
        }
        if !self.cvs_at(t_s) {
            self.error(
                t_s,
                "err.clip-unidentified",
                format!(
                    "clip applied to presumed {} before the Critical View of Safety was demonstrated ({} of 3 criteria met)",
                    target,
                    self.crit_count_at(t_s)
                ),
            );
            if target == "duct.cystic-duct" && self.misclip_cbd.is_none() {
                self.misclip_cbd = Some(t_s);
                self.complications.push(Complication {
                    kind: "clip-on-common-bile-duct".to_string(),
                    t_onset_s: t_s,
                    detail: "clip placed on the common bile duct, which traction has tented into the cystic duct line (Stewart-Way class I mechanism)".into(),
                    resolved_structure: Some("duct.common-bile".to_string()),
                    stewart_way_class: Some("I (mechanism)".to_string()),
                    recognised: false,
                    controlled_s: None,
                    loss_ml: None,
                });
                self.log(t_s, "complication", "the clipped structure is the common bile duct (class I mechanism state)".into());
            }
        } else {
            self.clipped.insert(target.to_string());
            self.log(t_s, "clip", format!("{} clipped with the Critical View demonstrated", m.id));
        }
        if target == "artery.cystic-branch-2" {
            self.clipped.insert(target.to_string());
            // clipping the branch also stops a branch bleed
            if self.bleeds.iter().any(|b| b.source == target && b.t_end.is_none()) {
                self.stop_bleed(t_s, target, "branch clipped");
            }
        }
    }

    fn on_divide(&mut self, t_s: f64, m: &crate::model::Microstep, target: &str) {
        if self.first_clipdiv_t.is_none() {
            self.first_clipdiv_t = Some(t_s);
        }
        let variant_rha = self.variant_active("variant.replaced-rha");

        // Variant resolution first: in the replaced-RHA field, the
        // artery presented for division is the variant vessel unless
        // it has been explicitly identified and excluded.
        if target == "artery.cystic" && variant_rha && !self.identified.contains("artery.replaced-rha") {
            self.error(
                t_s,
                "err.missed-variant",
                "cystic artery divided in a replaced-right-hepatic-artery field without identifying the variant vessel".into(),
            );
            let rate = self.params.get("bleed_rate_replaced_rha_ml_s");
            self.start_bleed(
                t_s,
                "artery.replaced-rha",
                rate,
                format!("the divided artery is the replaced right hepatic artery (rate {rate} mL/s — verify-flagged engineering parameter)"),
            );
            self.divided.insert("artery.replaced-rha".to_string());
            self.fail(
                t_s,
                "an unidentified critical structure — the replaced right hepatic artery — was divided (err.missed-variant)".into(),
            );
            return;
        }

        if !self.cvs_at(t_s) {
            // The master rule: dividing an unidentified critical
            // structure fails the attempt, whatever else is true.
            self.error(
                t_s,
                "err.divide-unidentified",
                format!(
                    "{} divided before the Critical View of Safety was demonstrated ({} of 3 criteria met)",
                    target,
                    self.crit_count_at(t_s)
                ),
            );
            if target == "duct.cystic-duct" {
                self.complications.push(Complication {
                    kind: "bile-duct-injury".to_string(),
                    t_onset_s: t_s,
                    detail: "the structure divided as the cystic duct is the common bile duct, tented into the line of the cystic duct by infundibular traction — the classic visual perceptual illusion (97% of injuries in the Way series are perceptual, 3% technical)".into(),
                    resolved_structure: Some("duct.common-bile".to_string()),
                    stewart_way_class: Some("III".to_string()),
                    recognised: false,
                    controlled_s: None,
                    loss_ml: None,
                });
                self.log(t_s, "complication", "bile duct injury: common bile duct transected (Stewart-Way class III)".into());
            } else {
                let rate = self.params.get("bleed_rate_cystic_artery_ml_s");
                self.start_bleed(
                    t_s,
                    target,
                    rate,
                    format!("unidentified artery in the hepatocystic triangle divided (rate {rate} mL/s — verify-flagged engineering parameter)"),
                );
            }
            self.divided.insert(target.to_string());
            self.fail(
                t_s,
                format!("an unidentified critical structure ({target}) was divided before the Critical View of Safety (err.divide-unidentified)"),
            );
            return;
        }

        // Critical View demonstrated: division resolves as intended,
        // with clip-state consequences computed.
        if target == "artery.cystic" && !self.clipped.contains(target) {
            self.error(
                t_s,
                "err.divide-unclipped-artery",
                "cystic artery divided before clips were applied".into(),
            );
            let rate = self.params.get("bleed_rate_cystic_artery_ml_s");
            self.start_bleed(
                t_s,
                target,
                rate,
                format!("haemorrhage from the divided, unclipped cystic artery (rate {rate} mL/s — verify-flagged engineering parameter)"),
            );
        }
        if target == "artery.cystic-branch-2" && !self.clipped.contains(target) {
            self.error(
                t_s,
                "err.divide-unclipped-artery",
                "second cystic artery branch divided before it was clipped".into(),
            );
            let rate = self.params.get("bleed_rate_uncontrolled_branch_ml_s");
            self.start_bleed(
                t_s,
                target,
                rate,
                format!("haemorrhage from the divided, unclipped second cystic branch (rate {rate} mL/s — verify-flagged engineering parameter)"),
            );
        }
        if target == "duct.cystic-duct" && !self.clipped.contains(target) {
            self.error(
                t_s,
                "err.divide-unclipped-duct",
                "cystic duct divided before clips were applied".into(),
            );
            self.complications.push(Complication {
                kind: "bile-leak".to_string(),
                t_onset_s: t_s,
                detail: "cystic duct divided unclipped: bile leak from the open duct stump (structural outcome; the physiology engine v0 has no biliary compartment, so no volume effect is computed)".into(),
                resolved_structure: Some("duct.cystic-duct".to_string()),
                stewart_way_class: None,
                recognised: false,
                controlled_s: None,
                loss_ml: None,
            });
        }
        self.divided.insert(target.to_string());
        self.log(t_s, "divide", format!("{} divided with the Critical View demonstrated", m.id));
    }
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

pub fn run_attempt(
    proc: &Procedure,
    tparams: &TheatreParams,
    phys: &PhysParams,
    trace: &Trace,
) -> Result<Debrief, String> {
    // Required set for the attempt's configuration.
    let mut required: HashSet<String> = proc
        .phases
        .iter()
        .flat_map(|p| p.steps.iter())
        .flat_map(|s| s.microsteps.iter())
        .filter(|m| m.required)
        .map(|m| m.id.clone())
        .collect();
    if trace.case.variant.as_deref() == Some("variant.double-cystic") {
        for id in ["m6.7", "m6.8", "m6.9"] {
            required.insert(id.to_string());
        }
    }

    // Physiology: settle and set the reflex setpoint from the
    // baseline window, exactly the Milestone 8 case protocol.
    let mut engine = Engine::new(phys);
    engine.tick_n(4500);
    let b0 = engine.beats.len();
    engine.tick_n(SETTLE_TICKS - 4500);
    let baseline_map = {
        let w = &engine.beats[b0..];
        if w.is_empty() {
            0.0
        } else {
            w.iter().map(|b| b.map).sum::<f64>() / w.len() as f64
        }
    };
    engine.set_reflex_setpoint(baseline_map);
    let beats_at_start = engine.beats.len();
    // Circulating volume is the raw compartment sum: the engine's
    // total_volume_ml() is the *conserved* quantity by construction
    // (compartment sum minus the external-flow integral), so it
    // cannot measure blood loss — volumes() can.
    let volume_at_start: f64 = engine.volumes().iter().sum();

    let mut at = Attempt {
        proc,
        params: tparams,
        engine,
        beats_at_start,
        volume_at_start,
        performed: HashMap::new(),
        criteria: HashMap::new(),
        identified: HashSet::new(),
        clipped: HashSet::new(),
        divided: HashSet::new(),
        misclip_cbd: None,
        required,
        errors: Vec::new(),
        complications: Vec::new(),
        decisions: Vec::new(),
        failed: None,
        prophylaxis_t: None,
        incision_t: None,
        pause_t: None,
        checklist_done: HashSet::new(),
        first_clipdiv_t: None,
        help_calls: Vec::new(),
        recognised_kinds: HashSet::new(),
        drain_placed: false,
        bailout_chosen: false,
        bleeds: Vec::new(),
        flow_sources: Vec::new(),
        pending_infusion_stops: Vec::new(),
        infused_ml: 0.0,
        log: Vec::new(),
        variant: trace.case.variant.clone(),
    };

    let mut last_t = 0.0f64;
    for action in &trace.actions {
        if action.t_s < last_t {
            return Err(format!(
                "trace {}: actions out of order at t={}",
                trace.id, action.t_s
            ));
        }
        last_t = action.t_s;
        at.advance_to(action.t_s);
        apply_action(&mut at, action);
    }
    let end_t = last_t + (TAIL_TICKS as f64) * TICK_SECONDS;
    at.advance_to(end_t);

    Ok(score(proc, tparams, at, trace, baseline_map, end_t))
}

fn apply_action(at: &mut Attempt, a: &Action) {
    let t = a.t_s;
    match a.kind.as_str() {
        "microstep" => {
            if let Some(id) = &a.id {
                at.do_microstep(t, id);
            }
        }
        "drug" => {
            // The prophylaxis microstep, fulfilled by a drug action so
            // its timing against incision can be evaluated.
            at.do_microstep(t, "m0.4");
        }
        "checklist" => {
            let id = match a.phase.as_deref() {
                Some("who.sign-in") => "m0.8",
                Some("who.time-out") => "m0.9",
                Some("who.sign-out") => "m8.7",
                _ => "",
            };
            if !id.is_empty() {
                at.do_microstep(t, id);
            }
        }
        "identify" => {
            if let Some(s) = &a.structure {
                at.identified.insert(s.clone());
                at.log(t, "identify", format!("structure identified: {s}"));
            }
        }
        "decision" => {
            if let (Some(id), Some(choice)) = (&a.id, &a.choice) {
                at.decisions.push(DecisionMade { t_s: t, id: id.clone(), choice: choice.clone() });
                at.log(t, "decision", format!("{id} -> {choice}"));
                match (id.as_str(), choice.as_str()) {
                    ("dp2", "continue-dissection") => {
                        at.error(
                            t,
                            "err.no-bailout",
                            "at dp2 the Critical View was declared unobtainable and dissection continued instead of altering strategy (guideline T3)".into(),
                        );
                    }
                    ("dp2", "ioc") => {
                        for m in ["m5.1", "m5.2", "m5.3", "m5.4", "m5.5", "m5.6", "m5.7", "m5.8", "m5.9", "m5.10"] {
                            at.required.insert(m.to_string());
                        }
                        at.log(t, "config", "IOC group becomes required for this attempt".into());
                    }
                    ("dp2", c) if c.starts_with("subtotal") || c == "convert-open" => {
                        at.bailout_chosen = true;
                        // Unperformed requirements in phases 3-7 are
                        // replaced by the bailout branch set.
                        let phase_of = |mid: &str| at.proc.microstep_phase(mid).unwrap_or("").to_string();
                        let drop: Vec<String> = at
                            .required
                            .iter()
                            .filter(|mid| {
                                !at.performed.contains_key(*mid)
                                    && ["phase.3", "phase.4", "phase.5", "phase.6", "phase.7"]
                                        .contains(&phase_of(mid).as_str())
                            })
                            .cloned()
                            .collect();
                        for mid in drop {
                            at.required.remove(&mid);
                        }
                        for m in ["m6b.1", "m6b.2", "m6b.3", "m6b.4", "m6b.5", "m6b.6"] {
                            at.required.insert(m.to_string());
                        }
                        at.log(t, "config", "bailout branch replaces the division-path requirements".into());
                    }
                    _ => {}
                }
            }
        }
        "recognise" => {
            if let Some(kind) = &a.complication {
                at.recognised_kinds.insert(kind.clone());
                for c in at.complications.iter_mut() {
                    if &c.kind == kind {
                        c.recognised = true;
                    }
                    // Recognising the transection also recognises the
                    // antecedent clip injury — one event chain.
                    if kind == "bile-duct-injury" && c.kind == "clip-on-common-bile-duct" {
                        c.recognised = true;
                    }
                }
                at.log(t, "recognise", format!("complication recognised: {kind}"));
            }
        }
        "control" => {
            if let Some(s) = &a.structure {
                at.stop_bleed(t, s, "control action");
            }
        }
        "clip_remove" => {
            if let Some(s) = &a.structure {
                if s == "duct.cystic-duct" && at.misclip_cbd.is_some() {
                    at.misclip_cbd = None;
                    for c in at.complications.iter_mut() {
                        if c.kind == "clip-on-common-bile-duct" {
                            c.recognised = true;
                            c.controlled_s = Some(t);
                        }
                    }
                    at.recognised_kinds.insert("clip-on-common-bile-duct".to_string());
                    at.log(t, "control", "misplaced clip on the common bile duct recognised and removed — near miss, no division occurred".into());
                }
            }
        }
        "energy" => {
            if let Some(s) = &a.structure {
                let duct = ["duct.cystic-duct", "duct.common-hepatic-duct", "duct.common-bile"].contains(&s.as_str());
                if duct && !at.cvs_at(t) {
                    at.error(
                        t,
                        "err.energy-before-id",
                        format!("electrocautery applied to {s} before the structure was identified (Critical View not demonstrated)"),
                    );
                    if s != "duct.cystic-duct" {
                        at.complications.push(Complication {
                            kind: "thermal-bile-duct-injury".to_string(),
                            t_onset_s: t,
                            detail: "thermal injury to the bile duct from energy applied before identification (Stewart-Way class II mechanism: lateral damage presenting as leak or late stricture)".into(),
                            resolved_structure: Some(s.clone()),
                            stewart_way_class: Some("II (mechanism)".to_string()),
                            recognised: false,
                            controlled_s: None,
                            loss_ml: None,
                        });
                    }
                } else {
                    at.log(t, "note", format!("energy applied to {s} with anatomy identified"));
                }
            }
        }
        "infuse" | "transfuse" => {
            let vol = a.volume_ml.unwrap_or(0.0);
            let rate = a.rate_ml_s.unwrap_or(16.67);
            let label = a.label.clone().unwrap_or_else(|| a.kind.clone());
            if vol > 0.0 && rate > 0.0 {
                at.infused_ml += vol;
                let flow_label = format!("infuse:{label}");
                at.start_flow(&flow_label, rate);
                let dur_ticks = (vol / rate / TICK_SECONDS).round() as u64;
                let stop_tick = at.engine.tick + dur_ticks;
                at.pending_infusion_stops.push((stop_tick, flow_label));
                at.log(t, "infuse", format!("{label}: {vol:.0} mL at {rate:.2} mL/s"));
            }
        }
        "help" => {
            let target = a.label.clone().unwrap_or_else(|| "senior help".to_string());
            at.help_calls.push(target.clone());
            at.log(t, "help", format!("help called: {target}"));
        }
        "note" => {
            at.log(t, "note", a.text.clone().unwrap_or_default());
        }
        other => {
            at.log(t, "warn", format!("unknown action kind '{other}' ignored"));
        }
    }
}

// ---------------------------------------------------------------------------
// Scoring + debrief assembly
// ---------------------------------------------------------------------------

fn score(
    proc: &Procedure,
    tparams: &TheatreParams,
    mut at: Attempt,
    trace: &Trace,
    baseline_map: f64,
    end_t: f64,
) -> Debrief {
    // Close out bleed bookkeeping.
    let mut bleed_integral = 0.0;
    for i in 0..at.bleeds.len() {
        let (t0, rate, tend) = {
            let b = &at.bleeds[i];
            (b.t_start, b.rate_ml_s, b.t_end.unwrap_or(end_t))
        };
        let loss = rate * (tend - t0);
        bleed_integral += loss;
        let ci = at.bleeds[i].complication_idx;
        at.complications[ci].loss_ml = Some(loss);
    }
    let volume_end: f64 = at.engine.volumes().iter().sum();
    // Snap sub-0.01 mL values to zero: the identity carries the
    // engine's conservation noise (~1e-10 mL), which is not blood.
    let loss_engine = {
        let l = (at.volume_at_start + at.infused_ml) - volume_end;
        if l.abs() < 0.01 { 0.0 } else { l }
    };

    // Prophylaxis window (evaluated at scoring so both fulfil paths —
    // microstep and drug action — are judged identically).
    let window_min = tparams.get("cefazolin_window_min");
    let prophylaxis_in_window = match (at.prophylaxis_t, at.incision_t) {
        (Some(p), Some(i)) => p < i && (i - p) <= window_min * 60.0,
        _ => false,
    };
    if let (Some(p), Some(i)) = (at.prophylaxis_t, at.incision_t) {
        if !prophylaxis_in_window {
            at.errors.push(ErrorEvent {
                t_s: p,
                id: "err.prophylaxis-window".to_string(),
                detail: format!(
                    "cefazolin given {}; the cited window is within {:.0} min before incision (T7)",
                    if p >= i { "after incision".to_string() } else { format!("{:.0} min before incision", (i - p) / 60.0) },
                    window_min
                ),
            });
        }
    }

    // Checklist score.
    let missing: Vec<String> = {
        let mut m: Vec<String> = at
            .required
            .iter()
            .filter(|id| !at.performed.contains_key(*id))
            .cloned()
            .collect();
        m.sort();
        m
    };
    let completed = at.required.len() - missing.len();
    let checklist = ChecklistScore {
        completed,
        required: at.required.len(),
        pct: if at.required.is_empty() { 100.0 } else { 100.0 * completed as f64 / at.required.len() as f64 },
        missing,
    };

    // Safety gate score.
    let crit_ref_t = at.first_clipdiv_t.unwrap_or(f64::INFINITY);
    let criteria_before = if at.first_clipdiv_t.is_some() {
        at.crit_count_at(crit_ref_t)
    } else {
        at.criteria.len()
    };
    let pause_before = match (at.pause_t, at.first_clipdiv_t) {
        (Some(p), Some(c)) => p <= c,
        (Some(_), None) => true,
        _ => false,
    };
    let safety = SafetyScore {
        criteria_before_first_clipdiv: criteria_before,
        pause_before_first_clip: pause_before,
        points: criteria_before + pause_before as usize,
        max: 4,
        note: if at.bailout_chosen {
            Some("the Critical View was unobtainable in this scenario and the guideline bailout pathway was taken; gate points measure gate achievement only and are not the bailout's grade".to_string())
        } else {
            None
        },
    };

    // Process score.
    let process = ProcessScore {
        sign_in: at.checklist_done.contains("who.sign-in"),
        time_out: at.checklist_done.contains("who.time-out"),
        sign_out: at.checklist_done.contains("who.sign-out"),
        prophylaxis_in_window,
        planning_complete: at.performed.contains_key("m0.1") && at.performed.contains_key("m0.2"),
        points: 0,
        max: 5,
    };
    let process = ProcessScore {
        points: process.sign_in as usize
            + process.time_out as usize
            + process.sign_out as usize
            + process.prophylaxis_in_window as usize
            + process.planning_complete as usize,
        ..process
    };
    for (done, name) in [
        (process.sign_in, "Sign In"),
        (process.time_out, "Time Out"),
        (process.sign_out, "Sign Out"),
    ] {
        if !done {
            at.errors.push(ErrorEvent {
                t_s: end_t,
                id: "err.checklist-omission".to_string(),
                detail: format!("WHO {name} not performed (T6)"),
            });
        }
    }

    // Physiology score from engine beats after the settle.
    let thr = tparams.get("map_threshold_mmhg");
    let beats = &at.engine.beats[at.beats_at_start..];
    let nadir = beats.iter().map(|b| b.map).fold(f64::INFINITY, f64::min);
    // (== comparison maps a possible -0.0 sum to +0.0 for reporting)
    let below_raw: f64 = beats.iter().filter(|b| b.map < thr).map(|b| b.duration_s).sum();
    let below_s: f64 = if below_raw == 0.0 { 0.0 } else { below_raw };
    let band_full = tparams.get("physio_band_time_below_full_s");
    let band_mid = tparams.get("physio_band_time_below_mid_s");
    let band_low = tparams.get("physio_band_time_below_low_s");
    let time_points = if below_s <= band_full {
        3
    } else if below_s <= band_mid {
        2
    } else if below_s <= band_low {
        1
    } else {
        0
    };
    let nadir_points = if nadir >= thr {
        2
    } else if nadir >= 55.0 {
        1
    } else {
        0
    };
    let loss_full = tparams.get("physio_band_loss_full_ml");
    let loss_mid = tparams.get("physio_band_loss_mid_ml");
    let loss_points = if loss_engine <= loss_full {
        2
    } else if loss_engine <= loss_mid {
        1
    } else {
        0
    };
    let physiology = PhysiologyScore {
        points: time_points + nadir_points + loss_points,
        max: 7,
        time_points,
        nadir_points,
        loss_points,
        map_nadir_mmhg: if nadir.is_finite() { nadir } else { baseline_map },
        map_baseline_mmhg: baseline_map,
        seconds_below_threshold: below_s,
        blood_loss_ml: loss_engine,
        blood_loss_crosscheck_ml: bleed_integral,
        infused_ml: at.infused_ml,
    };

    // Management score (only when a complication was computed).
    let management = if at.complications.is_empty() {
        None
    } else {
        let all_recognised = at.complications.iter().all(|c| {
            c.recognised || at.recognised_kinds.contains(&c.kind)
        });
        let any_recognised = at.complications.iter().any(|c| {
            c.recognised || at.recognised_kinds.contains(&c.kind)
        });
        let recognised_pts = if all_recognised {
            2
        } else if any_recognised {
            1
        } else {
            0
        };
        let all_bleeds_controlled = at.bleeds.iter().all(|b| b.t_end.is_some());
        let has_bdi = at.complications.iter().any(|c| c.kind == "bile-duct-injury");
        let control_pts = if all_bleeds_controlled && (!has_bdi || at.drain_placed) { 1 } else { 0 };
        let escalation_pts = if !at.help_calls.is_empty()
            || at.decisions.iter().any(|d| d.id == "dp3" || d.id == "dp4")
        {
            1
        } else {
            0
        };
        let plan_pts = if has_bdi {
            if at
                .decisions
                .iter()
                .any(|d| d.id == "dp4" && (d.choice == "drain-refer" || d.choice == "convert-repair"))
            {
                1
            } else {
                0
            }
        } else if at.infused_ml > 0.0 || loss_engine <= loss_full {
            1
        } else {
            0
        };
        Some(ManagementScore {
            points: recognised_pts + control_pts + escalation_pts + plan_pts,
            max: 5,
            recognised: recognised_pts,
            control: control_pts,
            escalation: escalation_pts,
            plan: plan_pts,
        })
    };

    let (failed_at_s, fail_reason) = match &at.failed {
        Some((t, r)) => (Some(*t), Some(r.clone())),
        None => (None, None),
    };
    let verdict = if at.failed.is_some() { "FAIL" } else { "PASS" }.to_string();

    let debrief = build_pearls(&at, &checklist, &safety, &process, &physiology, &management, &verdict);

    Debrief {
        trace_id: trace.id.clone(),
        trace_name: trace.name.clone(),
        procedure_id: proc.id.clone(),
        case_variant: trace.case.variant.clone(),
        verdict,
        failed_at_s,
        fail_reason,
        validity_label: "formative-only".to_string(),
        duration_s: end_t,
        checklist,
        safety_gate: safety,
        process,
        physiology,
        management,
        errors: at.errors.clone(),
        complications: at.complications.clone(),
        decisions: at.decisions.clone(),
        engine_trace_hash: format!("{:#018x}", at.engine.hash()),
        engine_beats: at.engine.beats.len(),
        engine_conservation_error_ml: at.engine.volume_conservation_error_ml(),
        debrief,
        event_log: at.log.clone(),
    }
}

fn build_pearls(
    at: &Attempt,
    checklist: &ChecklistScore,
    safety: &SafetyScore,
    process: &ProcessScore,
    physiology: &PhysiologyScore,
    management: &Option<ManagementScore>,
    verdict: &str,
) -> Pearls {
    // Description: the factual event spine (PEARLS phase 3).
    let mut description: Vec<String> = at
        .log
        .iter()
        .filter(|l| ["step", "gate", "error", "complication", "fail", "decision", "control", "recognise", "help"].contains(&l.kind.as_str()))
        .take(40)
        .map(|l| format!("[t={:.0}s] {}", l.t_s, l.text))
        .collect();
    if description.is_empty() {
        description.push("no events recorded".to_string());
    }

    let mut plus: Vec<String> = Vec::new();
    let mut delta: Vec<String> = Vec::new();
    let mut directive: Vec<String> = Vec::new();

    // Plus-delta analysis, generated from state (PEARLS: learner
    // self-assessment prompts in live use; the headless runner emits
    // the state-derived entries a facilitator would work from).
    if safety.criteria_before_first_clipdiv == 3 {
        plus.push("Critical View of Safety achieved and demonstrated before any clip was applied — all three criteria (T2).".to_string());
    }
    if safety.pause_before_first_clip && at.first_clipdiv_t.is_some() {
        plus.push("Pre-clip pause performed and the view confirmed with the team before clipping (T3).".to_string());
    }
    if at.bailout_chosen {
        plus.push("When the Critical View could not be obtained, the operative strategy was altered to a bailout — the guideline-preferred response (T3, T4).".to_string());
    }
    if at.identified.contains("artery.replaced-rha") {
        plus.push("The replaced right hepatic artery was identified in the field and preserved (variant record, prevalence 8.7-11.0%, T12).".to_string());
    }
    if at.complications.iter().any(|c| c.kind == "bile-duct-injury" && c.recognised) {
        plus.push(format!(
            "The bile duct injury was recognised during the index operation; in the reference series only {:.0}% were (T1).",
            25.0
        ));
    }
    if process.sign_in && process.time_out && process.sign_out {
        plus.push("All three WHO checklist phases were completed at their integration points (T6).".to_string());
    }
    if physiology.blood_loss_ml > 0.5 && physiology.seconds_below_threshold == 0.0 {
        plus.push("Haemorrhage was controlled without the mean arterial pressure ever falling below threshold.".to_string());
    }

    let mut seen_delta: HashSet<String> = HashSet::new();
    for e in &at.errors {
        if seen_delta.insert(e.id.clone()) {
            delta.push(format!("{} — {}", e.id, e.detail));
        }
    }
    if !checklist.missing.is_empty() {
        delta.push(format!(
            "required microsteps not performed: {}",
            checklist.missing.join(", ")
        ));
    }

    // Directive feedback, tied to the findings and their sources.
    if at.errors.iter().any(|e| e.id == "err.divide-unidentified") {
        directive.push("Never clip or divide a tubular structure in the hepatocystic triangle until the Critical View is demonstrated — two and only two structures entering the gallbladder (T2). The dominant injury mechanism is perceptual, not technical (97% of the Way series, T1): the defence is the discipline of the view.".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.missed-variant") {
        directive.push("Survey the triangle for variant vessels before any arterial division (microstep m3.12). A replaced right hepatic artery (8.7-11.0% prevalence, T12) courses posterolateral to the common bile duct and can present as the artery in the field.".to_string());
    }
    if at.complications.iter().any(|c| c.kind == "bile-duct-injury") {
        directive.push("Confirmed or suspected bile duct injury is referred to an experienced hepatobiliary team — a strong guideline recommendation (T3). Do not attempt definitive repair without that expertise; drain, document, refer.".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.no-bailout") {
        directive.push("When the Critical View cannot be obtained, alter the strategy: subtotal cholecystectomy is the preferred bailout (T3; fenestrating vs reconstituting subtypes, T4).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.prophylaxis-window") {
        directive.push("Prophylaxis timing is a system step, not a detail: cefazolin 2 g started within 60 minutes before incision (T7).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.uncontrolled-branch") {
        directive.push("A double cystic artery occurs in about 13% of patients (T11): before mobilising the gallbladder, confirm every arterial branch entering it is controlled.".to_string());
    }
    if directive.is_empty() {
        directive.push("Maintain the sequence discipline shown here; the next training increment is speed under the same gate discipline, not a relaxation of it.".to_string());
    }

    let mut summary = vec![
        format!("Verdict: {verdict} (formative only — no construct evidence exists for these scores yet)."),
        format!(
            "Checklist {:.1}% ({}/{}), safety gate {}/{}, process {}/{}, physiology {}/{}{}.",
            checklist.pct,
            checklist.completed,
            checklist.required,
            safety.points,
            safety.max,
            process.points,
            process.max,
            physiology.points,
            physiology.max,
            match management {
                Some(m) => format!(", management {}/{}", m.points, m.max),
                None => ", management n/a (no complication)".to_string(),
            }
        ),
    ];
    if let Some((t, r)) = &at.failed {
        summary.push(format!("Attempt failed at t={t:.0}s: {r}"));
    }
    if let Some(first) = delta.first() {
        summary.push(format!("Next focus: {first}"));
    }

    Pearls { description, plus, delta, directive, summary }
}
