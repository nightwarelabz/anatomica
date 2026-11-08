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
    /// Blood-product volume given (mL, Milestone 26 physiology):
    /// transfuse actions naming a known product composition, routed
    /// through the engine's product channel and reported separately
    /// from crystalloid (infused_ml).
    pub transfused_ml: f64,
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
    /// Engine net transcapillary refill at attempt start (Milestone
    /// 18 physiology): refill during the attempt is a real inflow, so
    /// the volume identity must add it back to keep measuring gross
    /// blood loss — the same accounting the infused volume already
    /// gets. Zero with the v0 engine semantics.
    refill_at_start: f64,
    /// Engine cumulative urine output and fluid intake at attempt
    /// start (Milestone 25 physiology): the renal/intake boundary
    /// fluxes run throughout the attempt, so the loss identity must
    /// carry them too — intake is an inflow (added back like
    /// refill), urine an outflow (subtracted), or a quiet attempt
    /// would report the patient's net boundary flux as blood loss.
    urine_at_start: f64,
    intake_at_start: f64,
    /// Engine cumulative product volume at attempt start (Milestone
    /// 26 physiology): blood products given during the attempt are
    /// an inflow like infused crystalloid, so the loss identity
    /// adds them back through the engine's own product integral —
    /// the Milestone 25 pattern, one channel further.
    product_at_start: f64,
    // procedure state
    performed: HashMap<String, f64>,
    criteria: HashMap<String, f64>,
    identified: HashSet<String>,
    clipped: HashSet<String>,
    divided: HashSet<String>,
    misclip_cbd: Option<f64>,
    required: HashSet<String>,
    /// Milestone 28 (appendicectomy): scenario severity and base
    /// condition from the trace's case spec — the stump-closure and
    /// contamination rules key on them.
    severity: Option<String>,
    base_condition: Option<String>,
    /// Inguinal hernia repair (Milestone 49): defect characterisation
    /// from the trace's case spec — the fixation rules key on it.
    defect: Option<String>,
    /// Total thyroidectomy (Milestone 56): the side whose
    /// parathyroid gland the scenario declares devascularised
    /// ("right" | "left") — the autotransplant rules key on it.
    parathyroid_devascularized: Option<String>,
    /// Upper GI endoscopy (Milestone 62): the scenario's bleeding
    /// lesion ("<kind>:<class>") — the therapy rules score what
    /// was delivered against this truth.
    lesion: Option<String>,
    /// Upper GI endoscopy (Milestone 62): the Forrest class the
    /// attempt declared at dp3 — the record the therapy was keyed
    /// on, held separately from the scenario truth it is scored
    /// against.
    declared_class: Option<String>,
    /// Upper GI endoscopy (Milestone 62): the therapy modalities
    /// actually delivered ("clot-removal" | "epinephrine" |
    /// "mechanical" | "thermal"), recorded by the treat handler.
    endo_modalities: HashSet<String>,
    /// Appendicectomy: the closure method applied at the base
    /// ("endoloop" | "stapler" | "polymeric-clips"), once applied.
    closure_method: Option<String>,
    /// Appendicectomy, retrocecal configuration: gate criteria
    /// demonstrated before the cecum was mobilized, held until the
    /// mobilization microstep registers them.
    deferred_criteria: Vec<String>,
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
    /// Carpal tunnel release (Milestone 42): the epineurial repair
    /// microstep was performed — the definitive control the
    /// management score credits after a computed nerve injury, the
    /// parallel of drain_placed for the biliary/caecal injuries.
    repair_done: bool,
    bailout_chosen: bool,
    // flows
    bleeds: Vec<Bleed>,
    flow_sources: Vec<(String, f64)>, // (label, rate) — engine has ONE ext-flow channel; we net
    pending_infusion_stops: Vec<(u64, String)>,
    infused_ml: f64,
    /// Blood-product volume given during the attempt (mL, Milestone
    /// 26): the nominal volumes of transfuse actions routed through
    /// the engine's product channel (the loss identity itself reads
    /// the engine's product integral, not this tally).
    transfused_ml: f64,
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

    /// The scored safety gate is the procedure's first safety_gate
    /// (the Critical View of Safety; the appendiceal base
    /// identification). Its criteria ids come from the procedure
    /// file, not from a hardcoded list.
    fn gate_criteria(&self) -> Vec<String> {
        self.proc
            .safety_gates
            .iter()
            .find(|g| g.kind == "safety_gate")
            .map(|g| g.criteria.iter().map(|c| c.id.clone()).collect())
            .unwrap_or_default()
    }

    fn gate_at(&self, t_s: f64) -> bool {
        let crit = self.gate_criteria();
        !crit.is_empty()
            && crit
                .iter()
                .all(|c| self.criteria.get(c).map(|t| *t <= t_s).unwrap_or(false))
    }

    fn crit_count_at(&self, t_s: f64) -> usize {
        self.gate_criteria()
            .iter()
            .filter(|c| self.criteria.get(*c).map(|t| *t <= t_s).unwrap_or(false))
            .count()
    }

    fn log_gate_achieved(&mut self, t_s: f64) {
        if let Some(g) = self.proc.safety_gates.iter().find(|g| g.kind == "safety_gate") {
            let n = g.criteria.len();
            let nword = if n == 3 { "three".to_string() } else { n.to_string() };
            let name = g.name.clone();
            self.log(t_s, "gate", format!("{name} achieved: all {nword} criteria demonstrated"));
        }
    }

    /// Appendicectomy: the scenario's severity is a complicated
    /// grade (gangrenous or perforated).
    fn complicated(&self) -> bool {
        matches!(self.severity.as_deref(), Some("gangrenous") | Some("perforated"))
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
            Some("preclip-pause") | Some("pre-division-pause") => {
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
            // Milestone 28 (retrocecal appendicectomy): the taeniae
            // convergence cannot be confirmed while the appendix
            // lies behind an unmobilized cecum, so crit1 demonstrated
            // before the cecum is mobilized (m3.5) is deferred and
            // registers only once mobilization happens.
            // Milestone 42 (transligamentous carpal release): the
            // recurrent branch's course cannot be accounted for
            // while the branch lies inside the unopened ligament, so
            // crit2 demonstrated before the branch is identified
            // where it pierces the retinaculum (m5.5) is deferred the
            // same way.
            let defer = (self.proc.id == "proc.appy.lap"
                && c == "crit1"
                && self.variant_active("variant.retrocecal")
                && !self.performed.contains_key("m3.5"))
                || (self.proc.id == "proc.carpal-release"
                    && c == "crit2"
                    && self.variant_active("variant.transligamentous-recurrent-branch")
                    && !self.performed.contains_key("m5.5"));
            if defer {
                if !self.deferred_criteria.iter().any(|x| x == c) {
                    self.deferred_criteria.push(c.clone());
                }
                let why = if self.proc.id == "proc.carpal-release" {
                    "criterion deferred: the recurrent branch's course cannot be accounted for while the branch lies inside the unopened ligament"
                } else {
                    "criterion deferred: the taeniae convergence cannot be confirmed while the appendix lies behind the unmobilized cecum"
                };
                self.log(t_s, "note", why.into());
            } else {
                // First demonstration wins (Milestone 56): a
                // criterion demonstrated on both sides of a
                // bilateral procedure keeps its FIRST time, so the
                // end-of-run safety scoring measures the criteria
                // against the first gated division rather than
                // against the second side's later demonstration.
                // Every earlier procedure demonstrates each
                // criterion exactly once, so this changes nothing
                // there — the 25 prior debriefs stay byte-identical.
                self.criteria.entry(c.clone()).or_insert(t_s);
                if self.gate_at(t_s) {
                    self.log_gate_achieved(t_s);
                }
            }
        }
        if self.proc.id == "proc.appy.lap" && id == "m3.5" {
            let deferred = std::mem::take(&mut self.deferred_criteria);
            for c in deferred {
                self.criteria.insert(c, t_s);
                self.log(t_s, "note", "deferred base-identification criterion registers now that the cecum is mobilized".into());
            }
            if !self.criteria.is_empty() && self.gate_at(t_s) {
                self.log_gate_achieved(t_s);
            }
        }
        if self.proc.id == "proc.carpal-release" && id == "m5.5" {
            let deferred = std::mem::take(&mut self.deferred_criteria);
            for c in deferred {
                self.criteria.insert(c, t_s);
                self.log(t_s, "note", "deferred recurrent-branch criterion registers now that the branch is identified where it pierces the retinaculum".into());
            }
            if !self.criteria.is_empty() && self.gate_at(t_s) {
                self.log_gate_achieved(t_s);
            }
        }
        if id == "m7.6" || id == "m6b.6" {
            self.drain_placed = true;
        }

        let target = m.targets.first().cloned().unwrap_or_default();
        // The critical-structure set is per procedure: the
        // cholecystectomy's lives in CRITICAL (Milestone 17); the
        // appendicectomy's is the appendix and its artery; the
        // carpal tunnel release's is the transverse carpal ligament
        // (Milestone 42); the ulnar decompression's is the fascial
        // set of the release (Milestone 44); total thyroidectomy's
        // is the six gated pedicle/Berry targets (Milestone 56).
        let appy = self.proc.id == "proc.appy.lap";
        let carpal = self.proc.id == "proc.carpal-release";
        let ulnar = self.proc.id == "proc.ulnar-decompression";
        let hernia = self.proc.id == "proc.lap-inguinal-hernia";
        let thyroid = self.proc.id == "proc.thyroidectomy.total";
        let endo = self.proc.id == "proc.upper-gi-endoscopy";
        let critical: &[&str] = if appy {
            &["canal.appendix", "artery.appendicular-artery"]
        } else if carpal {
            &["ligament.transverse-carpal"]
        } else if hernia {
            &["sac.inguinal-hernia", "fascia.transversalis"]
        } else if thyroid {
            &[
                "artery.right-superior-thyroid-artery",
                "artery.left-superior-thyroid-artery",
                "artery.right-inferior-thyroid-artery",
                "artery.left-inferior-thyroid-artery",
                "ligament.right-ligament-of-berry",
                "ligament.left-ligament-of-berry",
            ]
        } else if ulnar {
            &[
                "fascia.arcade-of-struthers",
                "ligament.cubital-tunnel-retinaculum",
                "fascia.fcu-aponeurosis",
                "fascia.deep-flexor-pronator-aponeurosis",
                "ligament.medial-intermuscular-septum",
            ]
        } else {
            &CRITICAL
        };
        match m.verb.as_str() {
            "clip" if critical.contains(&target.as_str()) => {
                if appy {
                    self.on_clip_appy(t_s, &m, &target);
                } else {
                    self.on_clip(t_s, &m, &target);
                }
            }
            "divide" if critical.contains(&target.as_str()) => {
                if appy {
                    self.on_divide_appy(t_s, &m, &target);
                } else if carpal {
                    self.on_divide_carpal(t_s, &m, &target);
                } else if ulnar {
                    self.on_divide_ulnar(t_s, &m, &target);
                } else if hernia {
                    self.on_divide_hernia(t_s, &m, &target);
                } else if thyroid {
                    self.on_divide_thyroid(t_s, &m, &target);
                } else {
                    self.on_divide(t_s, &m, &target);
                }
            }
            // Milestone 49: fixation is this operation's second
            // gated verb — a tack placed before the danger anatomy
            // is accounted for resolves exactly as a division does.
            "fixate" if hernia => {
                self.on_fixate_hernia(t_s, &m, &target);
            }
            // Milestone 62: therapy is this procedure's gated
            // verb — an endotherapy act taken before the lesion is
            // identified and classified resolves exactly as a
            // division before identification does.
            "treat" if endo => {
                self.on_treat_endoscopy(t_s, &m);
            }
            "close" if appy && target == "canal.appendix" => {
                let method = match id {
                    "m6.2" => "endoloop",
                    "m6.3" => "stapler",
                    _ => "closure",
                };
                self.closure_applied(t_s, method);
            }
            _ => {}
        }

        if appy {
            self.appy_microstep_rules(t_s, &m);
        }
        if carpal {
            self.carpal_microstep_rules(t_s, &m);
        }
        if ulnar {
            self.ulnar_microstep_rules(t_s, &m);
        }
        if hernia {
            self.hernia_microstep_rules(t_s, &m);
        }
        if thyroid {
            self.thyroid_microstep_rules(t_s, &m);
        }
        if endo {
            self.endoscopy_microstep_rules(t_s, &m);
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
        if !self.gate_at(t_s) {
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

        if !self.gate_at(t_s) {
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

    // -- appendicectomy rules (Milestone 28) ------------------------------
    //
    // The parallel of the cholecystectomy handlers above, under the
    // same master rule with the anatomy of this operation: what is
    // divided as "appendix" before the base gate is the cecum.

    /// A stump closure was applied; score the method against the
    /// scenario's base condition (dp3's rule, from T14/T18).
    fn closure_applied(&mut self, t_s: f64, method: &str) {
        self.closure_method = Some(method.to_string());
        self.log(t_s, "close", format!("appendiceal base closed ({method})"));
        if method != "stapler" && self.base_condition.as_deref() == Some("necrotic") {
            self.error(
                t_s,
                "err.closure-mismatch",
                format!("{method} closure applied to a necrotic appendiceal base: the closure cannot seal non-viable tissue (the stapler, fired across healthy tissue, is the scored choice here - T18)"),
            );
            self.complications.push(Complication {
                kind: "stump-leak".to_string(),
                t_onset_s: t_s,
                detail: "stump leak: the closure was placed on a necrotic base and cannot hold; the leak declares as a postoperative consequence (faecal contamination, peritonitis) rather than an intraoperative event - structural outcome; the physiology engine has no peritoneal compartment, so no volume effect is computed".into(),
                resolved_structure: Some("canal.appendix".to_string()),
                stewart_way_class: None,
                recognised: false,
                controlled_s: None,
                loss_ml: None,
            });
            self.log(t_s, "complication", "stump leak computed from the closure/base-condition mismatch (postoperative consequence)".into());
        }
    }

    fn on_clip_appy(&mut self, t_s: f64, m: &crate::model::Microstep, target: &str) {
        if self.first_clipdiv_t.is_none() {
            self.first_clipdiv_t = Some(t_s);
        }
        if !self.gate_at(t_s) {
            self.error(
                t_s,
                "err.clip-unidentified",
                format!(
                    "clip applied to presumed {} before the appendiceal base was positively identified ({} of 3 criteria met)",
                    target,
                    self.crit_count_at(t_s)
                ),
            );
            if target == "canal.appendix" && self.misclip_cbd.is_none() {
                self.misclip_cbd = Some(t_s);
                self.complications.push(Complication {
                    kind: "clip-on-cecum".to_string(),
                    t_onset_s: t_s,
                    detail: "clip placed across the cecal wall at the unidentified appendiceal base".into(),
                    resolved_structure: Some("canal.cecum".to_string()),
                    stewart_way_class: None,
                    recognised: false,
                    controlled_s: None,
                    loss_ml: None,
                });
                self.log(t_s, "complication", "the clipped structure is the cecal wall at the unidentified base".into());
            }
        } else {
            self.clipped.insert(target.to_string());
            self.log(t_s, "clip", format!("{} clipped with the base positively identified", m.id));
            if m.id == "m6.4" {
                // Polymeric clips are a closure method, not just a clip.
                self.closure_applied(t_s, "polymeric-clips");
            }
        }
    }

    fn on_divide_appy(&mut self, t_s: f64, m: &crate::model::Microstep, target: &str) {
        if self.first_clipdiv_t.is_none() {
            self.first_clipdiv_t = Some(t_s);
        }
        if !self.gate_at(t_s) {
            // The master rule, with this operation's anatomy.
            self.error(
                t_s,
                "err.divide-unidentified",
                format!(
                    "{} divided before the appendiceal base was positively identified ({} of 3 criteria met)",
                    target,
                    self.crit_count_at(t_s)
                ),
            );
            if target == "canal.appendix" {
                self.complications.push(Complication {
                    kind: "cecal-injury".to_string(),
                    t_onset_s: t_s,
                    detail: "the structure divided as the appendix is the cecum at its pole - the base was never identified, so the taeniae convergence was never demonstrated; full-thickness cecal injury with faecal contamination".into(),
                    resolved_structure: Some("canal.cecum".to_string()),
                    stewart_way_class: None,
                    recognised: false,
                    controlled_s: None,
                    loss_ml: None,
                });
                self.log(t_s, "complication", "cecal injury: the cecal wall was divided at the unidentified base".into());
            } else {
                let rate = self.params.get("bleed_rate_appendiceal_artery_ml_s");
                self.start_bleed(
                    t_s,
                    target,
                    rate,
                    format!("unidentified vessel in the mesoappendix divided (rate {rate} mL/s - verify-flagged engineering parameter)"),
                );
            }
            self.divided.insert(target.to_string());
            self.fail(
                t_s,
                format!("an unidentified critical structure ({target}) was divided before the appendiceal base was positively identified (err.divide-unidentified)"),
            );
            return;
        }

        // Base identified: division resolves as intended, with the
        // closure-state consequence computed.
        if target == "canal.appendix" && self.closure_method.is_none() {
            self.error(
                t_s,
                "err.divide-unclosed-base",
                "appendix divided with no stump closure (endoloop, clips or stapler) applied".into(),
            );
            self.complications.push(Complication {
                kind: "stump-leak".to_string(),
                t_onset_s: t_s,
                detail: "stump leak: the appendix was divided with its stump left open; the leak declares as a postoperative consequence (faecal contamination, peritonitis) - structural outcome; the physiology engine has no peritoneal compartment, so no volume effect is computed".into(),
                resolved_structure: Some("canal.appendix".to_string()),
                stewart_way_class: None,
                recognised: false,
                controlled_s: None,
                loss_ml: None,
            });
            self.log(t_s, "complication", "stump leak computed from division without closure (postoperative consequence)".into());
        }
        self.divided.insert(target.to_string());
        self.log(t_s, "divide", format!("{} divided with the base positively identified", m.id));
    }

    /// Appendicectomy microstep rules that are not clip/divide
    /// resolution: the requires_controlled haemorrhage and the
    /// guideline-discordance errors (lavage, drain, antibiotics).
    fn appy_microstep_rules(&mut self, t_s: f64, m: &crate::model::Microstep) {
        // Dividing a structure whose feeding artery is uncontrolled
        // computes haemorrhage from that artery — once, however many
        // division microsteps follow.
        if m.verb == "divide" {
            for s in &m.requires_controlled {
                let already = self.bleeds.iter().any(|b| &b.source == s);
                // A division that resolved onto the cecum (base gate
                // unachieved) is the cecal injury, not also an
                // arterial bleed.
                let resolved_elsewhere = m.targets.first().map(|t| t == "canal.appendix").unwrap_or(false)
                    && !self.gate_at(t_s);
                if !self.clipped.contains(s) && !already && !resolved_elsewhere {
                    self.error(
                        t_s,
                        "err.divide-unclipped-artery",
                        format!("{} divided while the appendiceal artery was uncontrolled (gate.artery-control)", m.id),
                    );
                    let rate = self.params.get("bleed_rate_appendiceal_artery_ml_s");
                    self.start_bleed(
                        t_s,
                        s,
                        rate,
                        format!("haemorrhage from the uncontrolled appendiceal artery (rate {rate} mL/s - verify-flagged engineering parameter)"),
                    );
                }
            }
        }
        match m.id.as_str() {
            "m7.3" => {
                self.error(
                    t_s,
                    "err.unnecessary-lavage",
                    "peritoneal lavage performed; the guideline recommendation in complicated appendicitis is suction alone (T14), and the meta-analysis finds no outcome advantage for irrigation (T15)".into(),
                );
            }
            "m7.5" => {
                self.drain_placed = true;
                if !self.complications.iter().any(|c| c.kind == "cecal-injury") {
                    self.error(
                        t_s,
                        "err.unnecessary-drain",
                        "abdominal drain placed after appendicectomy; WSES recommends against drains in adults - no benefit in preventing intra-abdominal abscess, longer hospitalisation (T14)".into(),
                    );
                }
            }
            "m8.4" => {
                if !self.complicated() {
                    self.error(
                        t_s,
                        "err.unnecessary-antibiotics",
                        "postoperative antibiotic course prescribed for uncomplicated appendicitis; WSES recommends against postoperative antibiotics there (T14)".into(),
                    );
                }
            }
            _ => {}
        }
    }

    // -- carpal tunnel release rules (Milestone 42) --------------------
    //
    // The parallel of the handlers above, under the same master rule
    // with the anatomy of this operation: what is divided before the
    // nerve gate is the median nerve, which lies immediately deep to
    // the ligament along the whole tunnel.

    fn on_divide_carpal(&mut self, t_s: f64, m: &crate::model::Microstep, target: &str) {
        if self.first_clipdiv_t.is_none() {
            self.first_clipdiv_t = Some(t_s);
        }
        if !self.gate_at(t_s) {
            // Variant resolution inside the master rule: in the
            // transligamentous field, if the ONLY undemonstrated
            // criterion is the branch account (crit2), the division
            // resolves onto the branch where it pierces the
            // ligament — the structure the variant puts inside the
            // structure being divided.
            let missing: Vec<String> = self
                .gate_criteria()
                .into_iter()
                .filter(|c| !self.criteria.contains_key(c))
                .collect();
            if self.variant_active("variant.transligamentous-recurrent-branch")
                && missing.len() == 1
                && missing[0] == "crit2"
            {
                self.error(
                    t_s,
                    "err.missed-variant",
                    "transverse carpal ligament divided with the transligamentous recurrent motor branch unaccounted for (crit2 undemonstrated: microstep m5.5 not performed)".into(),
                );
                self.complications.push(Complication {
                    kind: "recurrent-branch-injury".to_string(),
                    t_onset_s: t_s,
                    detail: "the division crosses the recurrent motor branch where it pierces the ligament: the branch was inside the structure being divided, and its course had never been accounted for - thenar motor loss is the computed consequence (Lanz group I variant, T23; pooled transligamentous prevalence 11.3%, T24)".into(),
                    resolved_structure: Some("nerve.recurrent-branch-median".to_string()),
                    stewart_way_class: None,
                    recognised: false,
                    controlled_s: None,
                    loss_ml: None,
                });
                self.log(t_s, "complication", "recurrent motor branch injury: the branch was divided within the ligament".into());
                self.divided.insert(target.to_string());
                self.fail(
                    t_s,
                    "an unaccounted critical structure — the transligamentous recurrent motor branch — was divided within the ligament (err.missed-variant)".into(),
                );
                return;
            }
            // The master rule, with this operation's anatomy.
            self.error(
                t_s,
                "err.divide-unidentified",
                format!(
                    "{} divided before the structures at risk were identified and protected ({} of 3 criteria met)",
                    target,
                    self.crit_count_at(t_s)
                ),
            );
            self.complications.push(Complication {
                kind: "median-nerve-injury".to_string(),
                t_onset_s: t_s,
                detail: "the division passes through the unvisualised tunnel and divides the median nerve, which lies immediately deep to the ligament along its whole length - the catastrophic iatrogenic injury of this operation (the median nerve is among the structures the revision literature lists as injured at release, T27)".into(),
                resolved_structure: Some("major.median".to_string()),
                stewart_way_class: None,
                recognised: false,
                controlled_s: None,
                loss_ml: None,
            });
            self.log(t_s, "complication", "median nerve injury: the nerve was divided beneath the unopened ligament".into());
            self.divided.insert(target.to_string());
            self.fail(
                t_s,
                format!("an unidentified critical structure ({target}) was divided before the structures at risk were identified and protected (err.divide-unidentified)"),
            );
            return;
        }

        // Gate demonstrated: division resolves as intended, with
        // the variant-vessel consequence computed — in the
        // persistent-median-artery field, dividing with the artery
        // unprotected bleeds from the artery until it is controlled.
        // The attempt does not fail: the divided structure is the
        // intended one; the injury is collateral.
        if self.variant_active("variant.persistent-median-artery")
            && !self.performed.contains_key("m5.6")
        {
            self.error(
                t_s,
                "err.unprotected-variant-vessel",
                "ligament divided in a persistent-median-artery field without identifying and protecting the artery (Lanz group III; microstep m5.6 not performed)".into(),
            );
            let rate = self.params.get("bleed_rate_persistent_median_artery_ml_s");
            self.start_bleed(
                t_s,
                "artery.persistent-median",
                rate,
                format!("haemorrhage from the divided persistent median artery (rate {rate} mL/s — verify-flagged engineering parameter)"),
            );
        }
        self.divided.insert(target.to_string());
        self.log(t_s, "divide", format!("{} divided with the structures at risk identified and protected", m.id));
    }

    /// Carpal microstep rules that are not division resolution: the
    /// scored departures (radial dissection across the palmar
    /// cutaneous branch; routine neurolysis) and the repair state.
    fn carpal_microstep_rules(&mut self, t_s: f64, m: &crate::model::Microstep) {
        match m.id.as_str() {
            "m6.4" => {
                self.error(
                    t_s,
                    "err.palmar-cutaneous-injury",
                    "dissection extended radially across the palmar cutaneous branch's territory; the approach stays ulnar precisely to avoid this branch (T21, T22)".into(),
                );
                self.complications.push(Complication {
                    kind: "palmar-cutaneous-branch-injury".to_string(),
                    t_onset_s: t_s,
                    detail: "palmar cutaneous branch injury: the revision literature's named iatrogenic injury of this approach (T27) - its presentation is a painful neuroma and new palmar sensory symptoms, declared as a postoperative structural consequence; no volume effect is computed".into(),
                    resolved_structure: Some("nerve.palmar-cutaneous-branch".to_string()),
                    stewart_way_class: None,
                    recognised: false,
                    controlled_s: None,
                    loss_ml: None,
                });
                self.log(t_s, "complication", "palmar cutaneous branch injury computed from the radial dissection (postoperative consequence)".into());
            }
            "m6.5" => {
                self.error(
                    t_s,
                    "err.unnecessary-neurolysis",
                    "internal neurolysis / epineurotomy performed as part of a primary release; such additional procedures are rarely indicated and are not routine in primary carpal tunnel release (T21)".into(),
                );
            }
            "m7.3" => {
                self.repair_done = true;
                self.log(t_s, "control", "epineurial repair of the divided nerve performed under magnification".into());
            }
            _ => {}
        }
    }

    /// Division resolution for the ulnar decompression (Milestone
    /// 44): the divided structures are the fascial structures of
    /// the release, and the gate is the identification-and-
    /// protection gate (gate.nerve-protection). The resolution
    /// follows the gate's own anatomy, exactly as the carpal
    /// release's variant resolution did: which structure the
    /// division resolves onto depends on which criterion is unmet.
    /// With the nerve itself unaccounted for, the division passes
    /// through the nerve in the tunnel. With the nerve protected
    /// and only the cutaneous-branch account missing, the division
    /// and its dissection cross the medial antebrachial cutaneous
    /// branches that were never accounted for — the operation's
    /// named iatrogenic injury, and a gate failure in its own
    /// right (the specialty's failure taxonomy names injury to the
    /// cutaneous nerves among the technical causes of a failed
    /// release, T34). Both fail the attempt.
    fn on_divide_ulnar(&mut self, t_s: f64, m: &crate::model::Microstep, target: &str) {
        if self.first_clipdiv_t.is_none() {
            self.first_clipdiv_t = Some(t_s);
        }
        if !self.gate_at(t_s) {
            let missing: Vec<String> = self
                .gate_criteria()
                .into_iter()
                .filter(|c| !self.criteria.contains_key(c))
                .collect();
            if missing.len() == 1 && missing[0] == "crit2" {
                self.error(
                    t_s,
                    "err.mabc-unaccounted",
                    format!(
                        "{} divided with the medial antebrachial cutaneous nerve unaccounted for (crit2 undemonstrated: microstep m1.3 not performed)",
                        target
                    ),
                );
                self.complications.push(Complication {
                    kind: "mabc-injury".to_string(),
                    t_onset_s: t_s,
                    detail: "the dissection and division cross the medial antebrachial cutaneous branches that were never identified or protected in the subcutaneous plane: numbness in the nerve's distribution and, where a neuroma forms, causalgia-type pain at the elbow is the computed consequence (among the most frequent complications of open decompression, T29; a named technical cause of a failed release, T34)".into(),
                    resolved_structure: Some("nerve.medial-cutaneous-nerve-of-forearm".to_string()),
                    stewart_way_class: None,
                    recognised: false,
                    controlled_s: None,
                    loss_ml: None,
                });
                self.log(t_s, "complication", "medial antebrachial cutaneous nerve injury: the unaccounted branches were divided in the field".into());
                self.divided.insert(target.to_string());
                self.fail(
                    t_s,
                    "a critical structure the gate protects by name — the medial antebrachial cutaneous nerve — was injured with its branches unaccounted for (err.mabc-unaccounted)".into(),
                );
                return;
            }
            // The master rule, with this operation's anatomy.
            self.error(
                t_s,
                "err.divide-unidentified",
                format!(
                    "{} divided before the nerves at risk were identified and protected ({} of 3 criteria met)",
                    target,
                    self.crit_count_at(t_s)
                ),
            );
            self.complications.push(Complication {
                kind: "ulnar-nerve-injury".to_string(),
                t_onset_s: t_s,
                detail: "the division passes through the unvisualised fascia and divides the ulnar nerve, which lies in and beyond the tunnel along the whole release length - the catastrophic iatrogenic injury of this operation (the ulnar nerve is among the structures the failed-release literature lists as injured at this operation, T34)".into(),
                resolved_structure: Some("major.ulnar".to_string()),
                stewart_way_class: None,
                recognised: false,
                controlled_s: None,
                loss_ml: None,
            });
            self.log(t_s, "complication", "ulnar nerve injury: the nerve was divided within the unopened fascia".into());
            self.divided.insert(target.to_string());
            self.fail(
                t_s,
                format!("an unidentified critical structure ({target}) was divided before the nerves at risk were identified and protected (err.divide-unidentified)"),
            );
            return;
        }

        self.divided.insert(target.to_string());
        self.log(t_s, "divide", format!("{} divided with the nerves at risk identified and protected", m.id));
    }

    /// Ulnar decompression microstep rules that are not division
    /// resolution (Milestone 44): the repair state. The operation's
    /// configuration and completeness consequences are decision and
    /// scoring rules, not microstep rules — they live in the dp5
    /// decision arm and in score(), beside the carpal tunnel
    /// release's incomplete-release rule.
    fn ulnar_microstep_rules(&mut self, t_s: f64, m: &crate::model::Microstep) {
        if m.id == "m7.3" {
            self.repair_done = true;
            self.log(t_s, "control", "epineurial repair of the injured nerve performed under magnification".into());
        }
    }

    // -- inguinal hernia repair rules (Milestone 49) ------------------
    //
    // The parallel of the handlers above, under the same master rule
    // with the anatomy of this operation: the gated acts are division
    // of the sac / transversalis fascia and placement of mesh
    // fixation, and the gate is the danger-anatomy account (the
    // critical view of the myopectineal orifice). Which structure an
    // unaccounted act resolves onto follows the gate's stated
    // priority: crit1 (the doom account) protects the external iliac
    // vessels; with crit1 met, crit2 (the pain account) protects the
    // lateral nerves; with both met, crit3 (the cord account)
    // protects the deferent duct. The total order is stated in the
    // procedure file's gate enforcement text and in MILESTONE-49.

    /// The gate-resolution shared by division and fixation: returns
    /// true when the act was resolved as a gate failure (the caller
    /// must not proceed with its normal path).
    fn hernia_gate_resolution(&mut self, t_s: f64, m: &crate::model::Microstep, target: &str) -> bool {
        if self.gate_at(t_s) {
            return false;
        }
        let missing: Vec<String> = self
            .gate_criteria()
            .into_iter()
            .filter(|c| !self.criteria.contains_key(c))
            .collect();
        if missing.iter().any(|c| c == "crit1") {
            self.error(
                t_s,
                "err.divide-unidentified",
                format!(
                    "{} acted on ({} {}) before the triangle of doom was delimited and the external iliac vessels identified ({} of 3 criteria met)",
                    target,
                    m.verb,
                    m.id,
                    self.crit_count_at(t_s)
                ),
            );
            self.complications.push(Complication {
                kind: "vascular-injury".to_string(),
                t_onset_s: t_s,
                detail: "the act crosses the external iliac vessels inside the unaccounted triangle of doom — the preperitoneal vascular injury HerniaSurge names for dissection and mesh fixation in this space (T36); the vessels lie within the triangle bounded by the vas deferens, the testicular vessels and the peritoneal fold (T39)".into(),
                resolved_structure: Some("artery.right-external-iliac-artery".to_string()),
                stewart_way_class: None,
                recognised: false,
                controlled_s: None,
                loss_ml: None,
            });
            let rate = self.params.get("bleed_rate_external_iliac_ml_s");
            self.start_bleed(
                t_s,
                "artery.right-external-iliac-artery",
                rate,
                format!("haemorrhage from the injured external iliac artery (rate {rate} mL/s — verify-flagged engineering parameter)"),
            );
            self.log(t_s, "complication", "vascular injury: the external iliac artery was injured inside the unaccounted triangle of doom".into());
            self.fail(
                t_s,
                "an unaccounted critical structure — the external iliac artery, inside the undelimited triangle of doom — was injured (err.divide-unidentified)".into(),
            );
        } else if missing.iter().any(|c| c == "crit2") {
            self.error(
                t_s,
                "err.pain-triangle-injury",
                format!(
                    "{} acted on ({} {}) with the triangle of pain undelimited (crit2 undemonstrated: microstep m4.2 not performed)",
                    target, m.verb, m.id
                ),
            );
            self.complications.push(Complication {
                kind: "nerve-injury".to_string(),
                t_onset_s: t_s,
                detail: "the act crosses the lateral nerves of the undelimited triangle of pain — the femoral branch of the genitofemoral nerve and its neighbours, damaged at separation or fixation in this territory, with chronic neuropathic pain as the named consequence (T39)".into(),
                resolved_structure: Some("nerve.genitofemoral".to_string()),
                stewart_way_class: None,
                recognised: false,
                controlled_s: None,
                loss_ml: None,
            });
            self.log(t_s, "complication", "nerve injury: the pain-triangle nerves were injured with their territory undelimited".into());
            self.fail(
                t_s,
                "a critical territory the gate protects by name — the triangle of pain — was acted on undelimited, injuring its nerves (err.pain-triangle-injury)".into(),
            );
        } else {
            self.error(
                t_s,
                "err.vas-injury",
                format!(
                    "{} acted on ({} {}) with the cord structures unaccounted for (crit3 undemonstrated: microstep m4.3 not performed)",
                    target, m.verb, m.id
                ),
            );
            self.complications.push(Complication {
                kind: "vas-deferens-injury".to_string(),
                t_onset_s: t_s,
                detail: "the act divides the unparietalized deferent duct where it lies against the sac — the cord injury the parietalization discipline (T38, Rules 5-6) exists to prevent".into(),
                resolved_structure: Some("repro.right-deferent-duct".to_string()),
                stewart_way_class: None,
                recognised: false,
                controlled_s: None,
                loss_ml: None,
            });
            self.log(t_s, "complication", "vas deferens injury: the unaccounted duct was divided against the sac".into());
            self.fail(
                t_s,
                "an unaccounted critical structure — the deferent duct — was divided (err.vas-injury)".into(),
            );
        }
        true
    }

    fn on_divide_hernia(&mut self, t_s: f64, m: &crate::model::Microstep, target: &str) {
        if self.first_clipdiv_t.is_none() {
            self.first_clipdiv_t = Some(t_s);
        }
        if self.hernia_gate_resolution(t_s, m, target) {
            self.divided.insert(target.to_string());
            return;
        }
        // Gate achieved: the sliding configuration's own rule — the
        // sac wall is partly a viscus, and dividing it without the
        // survey is the variant's master-rule failure (the
        // replaced-RHA identify-before-divide pattern).
        if self.variant_active("variant.sliding-hernia") && !self.performed.contains_key("m4.5") {
            self.error(
                t_s,
                "err.missed-variant",
                "sac divided in a sliding-hernia field without the sliding survey (microstep m4.5 not performed): part of the sac wall is formed by a viscus (T41)".into(),
            );
            self.complications.push(Complication {
                kind: "visceral-injury".to_string(),
                t_onset_s: t_s,
                detail: "the division cuts the viscus forming part of the sac wall — on this right side the cecum — the defining hazard of the sliding hernia, present in 2-5% of indirect inguinal hernias (T41)".into(),
                resolved_structure: Some("canal.cecum".to_string()),
                stewart_way_class: None,
                recognised: false,
                controlled_s: None,
                loss_ml: None,
            });
            self.log(t_s, "complication", "visceral injury: the viscus forming the sliding sac wall was divided".into());
            self.divided.insert(target.to_string());
            self.fail(
                t_s,
                "the sliding sac wall — a viscus — was divided without the sliding survey (err.missed-variant)".into(),
            );
            return;
        }
        self.divided.insert(target.to_string());
        self.log(t_s, "divide", format!("{} divided with the danger anatomy accounted for", m.id));
    }

    fn on_fixate_hernia(&mut self, t_s: f64, m: &crate::model::Microstep, target: &str) {
        if self.first_clipdiv_t.is_none() {
            self.first_clipdiv_t = Some(t_s);
        }
        // The two authored prohibited placements are departures of a
        // gated act, handled by hernia_microstep_rules when the gate
        // is achieved; before the gate they are gate failures like
        // any other fixation, so they fall through to the resolution.
        let departure = (m.id == "m6.7" || m.id == "m6.8") && self.gate_at(t_s);
        if departure {
            return;
        }
        if self.hernia_gate_resolution(t_s, m, target) {
            return;
        }
        // Gate achieved: the corona configuration's collateral rule —
        // medial fixation into Cooper's ligament without protecting
        // the anastomotic vessel bleeds from it (the carpal
        // persistent-median-artery pattern: major, not a fail).
        if m.id == "m6.4"
            && self.variant_active("variant.corona-mortis")
            && !self.performed.contains_key("m4.4")
        {
            self.error(
                t_s,
                "err.corona-unprotected",
                "medial fixation placed into Cooper's ligament in a corona mortis field without protecting the anastomotic vessel (microstep m4.4 not performed)".into(),
            );
            let rate = self.params.get("bleed_rate_corona_mortis_ml_s");
            self.start_bleed(
                t_s,
                "artery.corona-mortis",
                rate,
                format!("haemorrhage from the unprotected corona mortis (rate {rate} mL/s — verify-flagged engineering parameter)"),
            );
            self.log(t_s, "complication", "corona mortis haemorrhage: the unprotected anastomotic vessel was struck by the medial fixation".into());
            return;
        }
        self.log(t_s, "fixate", format!("{} fixation placed with the danger anatomy accounted for", m.id));
    }

    /// Hernia microstep rules that are not gate resolution: the two
    /// authored prohibited placements, performed WITH the gate
    /// achieved — the account was made and then violated, so each is
    /// a scored major departure with a computed injury and
    /// management, not a failed attempt (the carpal release's
    /// radial-dissection pattern, Milestone 42).
    fn hernia_microstep_rules(&mut self, t_s: f64, m: &crate::model::Microstep) {
        match m.id.as_str() {
            "m6.7" if self.gate_at(t_s) => {
                self.error(
                    t_s,
                    "err.fixation-in-pain-triangle",
                    "traumatic fixation placed below the iliopubic tract inside the triangle of pain; traumatic fixation should not be placed below the iliopubic tract, and 2 cm above it is the extra-safety line (T38)".into(),
                );
                self.complications.push(Complication {
                    kind: "nerve-injury".to_string(),
                    t_onset_s: t_s,
                    detail: "the fixation entraps the lateral nerves of the triangle of pain — the chronic-neuropathic-pain mechanism named for fixation in this territory (T39)".into(),
                    resolved_structure: Some("nerve.genitofemoral".to_string()),
                    stewart_way_class: None,
                    recognised: false,
                    controlled_s: None,
                    loss_ml: None,
                });
                self.log(t_s, "complication", "nerve injury computed from fixation inside the triangle of pain (postoperative consequence)".into());
            }
            "m6.8" if self.gate_at(t_s) => {
                self.error(
                    t_s,
                    "err.fixation-in-doom-triangle",
                    "traumatic fixation placed inside the triangle of doom; the vessels of the preperitoneal space are the fixation injuries of this operation (T36, T39)".into(),
                );
                self.complications.push(Complication {
                    kind: "vascular-injury".to_string(),
                    t_onset_s: t_s,
                    detail: "the fixation strikes the external iliac vessels inside the triangle of doom (T39)".into(),
                    resolved_structure: Some("artery.right-external-iliac-artery".to_string()),
                    stewart_way_class: None,
                    recognised: false,
                    controlled_s: None,
                    loss_ml: None,
                });
                let rate = self.params.get("bleed_rate_external_iliac_ml_s");
                self.start_bleed(
                    t_s,
                    "artery.right-external-iliac-artery",
                    rate,
                    format!("haemorrhage from the external iliac artery struck by fixation (rate {rate} mL/s — verify-flagged engineering parameter)"),
                );
                self.log(t_s, "complication", "vascular injury computed from fixation inside the triangle of doom".into());
            }
            _ => {}
        }
    }

    // -- Total thyroidectomy (Milestone 56) -------------------------------
    //
    // The gate is demonstrated and enforced PER SIDE: the criteria
    // register records the demonstrations generically, but the
    // divide handler checks the performed set for the side being
    // divided (right accounts m3.1-m3.3, left accounts m5.2-m5.4) —
    // neither side's account is inherited from the other, because
    // the catastrophe the gate exists to prevent is a second-side
    // injury added to a first (T42; T44).

    /// Push this side's recurrent laryngeal nerve injury (once per
    /// side), and compute the bilateral injury when the second
    /// side's nerve falls after the first.
    fn thyroid_rln_injury(&mut self, t_s: f64, side: &str, mechanism: &str) {
        let rln = format!("nerve.{side}-recurrent-laryngeal-nerve");
        if self
            .complications
            .iter()
            .any(|c| c.kind == "recurrent-laryngeal-nerve-injury" && c.resolved_structure.as_deref() == Some(rln.as_str()))
        {
            return;
        }
        self.complications.push(Complication {
            kind: "recurrent-laryngeal-nerve-injury".to_string(),
            t_onset_s: t_s,
            detail: format!(
                "{mechanism} — the {side} recurrent laryngeal nerve, whose injury produces vocal fold dysfunction on that side (temporary in 0.5-10% and permanent in 0-5% of thyroidectomies in most series, T44)"
            ),
            resolved_structure: Some(rln.clone()),
            stewart_way_class: None,
            recognised: false,
            controlled_s: None,
            loss_ml: None,
        });
        self.log(t_s, "complication", format!("recurrent laryngeal nerve injury: the {side} nerve was divided unaccounted"));
        let other = if side == "right" { "left" } else { "right" };
        let other_rln = format!("nerve.{other}-recurrent-laryngeal-nerve");
        let other_injured = self.complications.iter().any(|c| {
            c.kind == "recurrent-laryngeal-nerve-injury" && c.resolved_structure.as_deref() == Some(other_rln.as_str())
        });
        let bilateral_already = self
            .complications
            .iter()
            .any(|c| c.kind == "bilateral-recurrent-laryngeal-nerve-injury");
        if other_injured && !bilateral_already {
            self.complications.push(Complication {
                kind: "bilateral-recurrent-laryngeal-nerve-injury".to_string(),
                t_onset_s: t_s,
                detail: "bilateral recurrent laryngeal nerve injury computed: both vocal folds dysfunctional — bilateral vocal fold dysfunction is a life-threatening condition in the immediate postoperative period, a rare event reported in 0.1-0.4% of cases, with reintubation and/or tracheostomy the prepared contingency (T44; the preoperative warning of the same progression, T42)".to_string(),
                resolved_structure: Some(rln),
                stewart_way_class: None,
                recognised: false,
                controlled_s: None,
                loss_ml: None,
            });
            self.log(t_s, "complication", "bilateral recurrent laryngeal nerve injury computed: the second side's nerve has fallen after the first".into());
        }
    }

    fn on_divide_thyroid(&mut self, t_s: f64, m: &crate::model::Microstep, target: &str) {
        if self.first_clipdiv_t.is_none() {
            self.first_clipdiv_t = Some(t_s);
        }
        let side = if target.contains(".right-") { "right" } else { "left" };
        let crit1_demo = if side == "right" { "m3.1" } else { "m5.2" };
        let crit3_demo = if side == "right" { "m3.3" } else { "m5.4" };

        // The superior pedicle is crit3-gated only: the divided
        // structure is the intended pedicle, and the injury the
        // unaccounted division computes is collateral — the
        // external branch, taken by a pedicle line that was never
        // established on the capsule (the carpal
        // persistent-median-artery pattern: major, not a fail).
        if target.contains("superior-thyroid") {
            if !self.performed.contains_key(crit3_demo) {
                self.error(
                    t_s,
                    "err.ebsln-unaccounted",
                    format!(
                        "superior thyroid pedicle divided ({}) with the external branch of the superior laryngeal nerve unaccounted on the {side} side (crit3 undemonstrated: microstep {crit3_demo} not performed); the superior pole vessels should be ligated close to the thyroid capsule to avoid potential EBSLN injury (T44)",
                        m.id
                    ),
                );
                self.complications.push(Complication {
                    kind: "external-laryngeal-nerve-injury".to_string(),
                    t_onset_s: t_s,
                    detail: "the pedicle line crosses the external branch's course on the inferior constrictor: cricothyroid paralysis degrading voice pitch and projection without vocal fold paralysis — the branch most surgeons avoid rather than expose, which is why its account here is the capsular line itself (T48; T44)".to_string(),
                    resolved_structure: Some(format!("nerve.{side}-external-laryngeal-branch")),
                    stewart_way_class: None,
                    recognised: false,
                    controlled_s: None,
                    loss_ml: None,
                });
                self.log(t_s, "complication", format!("external laryngeal nerve injury: the {side} superior pedicle was divided with the branch unaccounted"));
            } else {
                self.log(t_s, "divide", format!("{} divided on the capsule with the external branch accounted for", m.id));
            }
            self.divided.insert(target.to_string());
            return;
        }

        // Inferior pedicle and ligament of Berry. Variant
        // resolution first (the replaced-RHA pattern): in the
        // branching configuration the account the division needed
        // is the branch survey, and its absence resolves onto the
        // unaccounted anterior motor branch.
        if side == "right"
            && self.variant_active("variant.rln-extralaryngeal-branching")
            && !self.performed.contains_key("m3.5")
        {
            self.error(
                t_s,
                "err.missed-variant",
                format!(
                    "{} divided ({}) in an extralaryngeal-branching field without the branch survey (microstep m3.5 not performed): the nerve's branches were never all accounted for to the laryngeal entry (T45)",
                    target, m.id
                ),
            );
            self.thyroid_rln_injury(t_s, side, "the division takes the unaccounted anterior motor branch of the branched right recurrent laryngeal nerve — the branch carrying the motor fibres (T45)");
            self.divided.insert(target.to_string());
            self.fail(
                t_s,
                "an unaccounted critical structure — the anterior motor branch of the branched recurrent laryngeal nerve — was divided (err.missed-variant)".into(),
            );
            return;
        }
        if !self.performed.contains_key(crit1_demo) {
            self.error(
                t_s,
                "err.divide-unidentified",
                format!(
                    "{} divided ({}) before the {side} recurrent laryngeal nerve was identified and traced (crit1 undemonstrated on this side: microstep {crit1_demo} not performed); visual identification of the RLN is required in all cases (T42)",
                    target, m.id
                ),
            );
            self.thyroid_rln_injury(t_s, side, "the division takes the unidentified recurrent laryngeal nerve where it lies against the pedicle and the ligament of Berry — the ligament is the most common site of RLN injury in this operation (T44)");
            self.divided.insert(target.to_string());
            self.fail(
                t_s,
                format!("an unaccounted critical structure — the {side} recurrent laryngeal nerve — was divided (err.divide-unidentified)"),
            );
            return;
        }
        self.divided.insert(target.to_string());
        self.log(t_s, "divide", format!("{} divided with the {side} nerve and parathyroid account demonstrated", m.id));
    }

    /// Thyroid microstep rules that are not gate resolution: the
    /// magnified repair of a transected recurrent laryngeal nerve
    /// (m7.3) is the definitive control the management score
    /// credits after a computed nerve injury — the carpal/ulnar
    /// repair rule (Milestones 42/44), on this operation's repair
    /// microstep.
    fn thyroid_microstep_rules(&mut self, t_s: f64, m: &crate::model::Microstep) {
        if m.id == "m7.3" && !self.repair_done {
            self.repair_done = true;
            self.log(t_s, "control", "recurrent laryngeal nerve repair performed under magnification (m7.3)".into());
        }
    }

    /// Upper GI endoscopy (Milestone 62): the scenario's lesion
    /// truth, parsed from the case field — (kind, class), e.g.
    /// ("duodenal-ulcer", "iia") or ("dieulafoy", "gastric").
    fn endo_truth(&self) -> Option<(String, String)> {
        let l = self.lesion.as_deref()?;
        let (kind, cls) = l.split_once(':')?;
        Some((kind.to_string(), cls.to_string()))
    }

    /// The treatment-relevant group of a Forrest class: the
    /// guidelines' own partition — high-risk stigmata that receive
    /// therapy (Ia/Ib/IIa), the adherent clot (IIb), and the
    /// low-risk stigmata that receive none (IIc/III) (T49; T50).
    fn endo_forrest_group(class: &str) -> &'static str {
        match class {
            "ia" | "ib" | "iia" => "high",
            "iib" => "clot",
            _ => "low",
        }
    }

    /// Upper GI endoscopy (Milestone 62): the gate resolution for
    /// this procedure's gated verb. Therapy applied before the
    /// lesion is identified (crit1) and classified (crit2), or
    /// with no classification declared at dp3, is therapy applied
    /// blind — the classification exists to decide the therapy
    /// (T49) — and resolves exactly as a division before
    /// identification does in the house's other procedures: a
    /// perforation computed onto the treated segment (T52) and
    /// the attempt FAILS at the act. A gated act that passes the
    /// gate is recorded by modality; what the delivered modalities
    /// are worth is judged at scoring, against the scenario truth.
    fn on_treat_endoscopy(&mut self, t_s: f64, m: &crate::model::Microstep) {
        if self.first_clipdiv_t.is_none() {
            self.first_clipdiv_t = Some(t_s);
        }
        let modality = match m.id.as_str() {
            "m5.1" => "clot-removal",
            "m5.2" => "epinephrine",
            "m5.3" => "mechanical",
            "m5.4" => "thermal",
            _ => "other",
        };
        self.endo_modalities.insert(modality.to_string());

        let identified = self.criteria.contains_key("crit1");
        let classified = self.criteria.contains_key("crit2");
        let declared = self
            .declared_class
            .as_deref()
            .filter(|c| *c != "abort-terminate-procedure");
        if identified && classified && declared.is_some() {
            self.log(
                t_s,
                "treat",
                format!(
                    "{} applied to the identified, classified lesion (declared {})",
                    m.id,
                    declared.unwrap_or_default()
                ),
            );
            return;
        }
        let missing = [
            (!identified).then_some("the bleeding source was not identified and localised (crit1 undemonstrated: microstep m3.1 not performed)"),
            (!classified).then_some("the lesion was not classified by its Forrest stigmata (crit2 undemonstrated: microstep m3.2 not performed)"),
            (declared.is_none()).then_some("no classification was declared at dp3 for the record the therapy keys on"),
        ]
        .into_iter()
        .flatten()
        .collect::<Vec<_>>()
        .join("; ");
        self.error(
            t_s,
            "err.treat-before-classification",
            format!(
                "endoscopic therapy applied ({}) before identification and classification: {}; the Forrest classification is to be used in all patients with peptic ulcer hemorrhage because therapy keys on it (T49)",
                m.id, missing
            ),
        );
        let segment = match self.endo_truth().map(|(k, _)| k).as_deref() {
            Some("gastric-ulcer") | Some("dieulafoy") => "dig.stomach",
            _ => "canal.duodenum",
        };
        self.complications.push(Complication {
            kind: "perforation".to_string(),
            t_onset_s: t_s,
            detail: format!(
                "perforation of the treated segment computed: therapy was applied to a lesion whose class was never established — the adverse event the ASGE guideline records at ≤ 0.03% for diagnostic EGD, its risk rising with therapeutic intervention (T52), taken here blind"
            ),
            resolved_structure: Some(segment.to_string()),
            stewart_way_class: None,
            recognised: false,
            controlled_s: None,
            loss_ml: None,
        });
        self.log(t_s, "complication", "perforation computed: therapy applied before identification and classification".into());
        self.fail(
            t_s,
            "endoscopic therapy was applied to a lesion before it was identified and classified (err.treat-before-classification)".into(),
        );
    }

    /// Upper GI endoscopy (Milestone 62) microstep rules that are
    /// not gate resolution: the two scenario computations.
    /// (a) Sedation administered in the ongoing-hematemesis
    /// configuration before the airway is protected computes
    /// aspiration at the sedation act (T52; T53) — performed late,
    /// the protection does not un-compute it. (b) Completing the
    /// survey in the Dieulafoy configuration without the
    /// caliber-persistent artery search lets the unaccounted
    /// lesion declare itself as a haemorrhage, on the hernia
    /// pattern: the variant's identification act is what the
    /// completion needed (T54).
    fn endoscopy_microstep_rules(&mut self, t_s: f64, m: &crate::model::Microstep) {
        if m.id == "m1.2"
            && self.severity.as_deref() == Some("ongoing-hematemesis")
            && !self.performed.contains_key("m1.3")
        {
            self.error(
                t_s,
                "err.unprotected-airway",
                "sedation administered (m1.2) in ongoing hematemesis before the airway was protected (microstep m1.3 not performed): sedation suppresses the protective airway reflexes over a stomach full of blood, and the sedation standard's rescue and anesthesia-assistance provisions exist for exactly this configuration (T53)".into(),
            );
            self.complications.push(Complication {
                kind: "aspiration".to_string(),
                t_onset_s: t_s,
                detail: "aspiration of gastric blood computed at the sedation act: a named sedation-related cardiopulmonary adverse event (T52), in the event class that forms the largest share of this procedure's adverse events (structural outcome; no gas-exchange trajectory is computed)".into(),
                resolved_structure: Some("airway.trachea".to_string()),
                stewart_way_class: None,
                recognised: false,
                controlled_s: None,
                loss_ml: None,
            });
            self.log(t_s, "complication", "aspiration computed: sedation over an unprotected airway in ongoing hematemesis".into());
        }
        if m.id == "m6.2"
            && self.failed.is_none()
            && self.variant_active("variant.dieulafoy-lesion")
            && !self.performed.contains_key("m3.3")
        {
            self.error(
                t_s,
                "err.missed-variant",
                "completion survey performed (m6.2) in a Dieulafoy field without the caliber-persistent artery search (microstep m3.3 not performed): the lesion was present in the proximal stomach and findable by its own search, and was never accounted for (T54)".into(),
            );
            let rate = self.params.get("bleed_rate_dieulafoy_ml_s");
            self.start_bleed(
                t_s,
                "lesion.dieulafoy",
                rate,
                format!("haemorrhage from the unaccounted Dieulafoy lesion — the caliber-persistent artery declares itself (rate {rate} mL/s — verify-flagged engineering parameter)"),
            );
            self.fail(
                t_s,
                "an unaccounted bleeding lesion — the Dieulafoy caliber-persistent artery — declared itself at the completion survey (err.missed-variant)".into(),
            );
        }
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
    // Variant configurations add their microsteps from the variant
    // definition's required_additions (data-driven since Milestone
    // 28; the cholecystectomy's double-cystic variant carries the
    // same three ids the Milestone 17 runner hardcoded).
    if let Some(vid) = trace.case.variant.as_deref() {
        if let Some(v) = proc.variants.iter().find(|v| v.id == vid) {
            for id in &v.required_additions {
                required.insert(id.clone());
            }
        }
    }
    // Appendicectomy severity configurations: a complicated grade
    // requires the postoperative antibiotic course; a perforated
    // appendix additionally requires suction of the contamination.
    if proc.id == "proc.appy.lap" {
        match trace.case.severity.as_deref() {
            Some("gangrenous") => {
                required.insert("m8.4".to_string());
            }
            Some("perforated") => {
                required.insert("m7.2".to_string());
                required.insert("m8.4".to_string());
            }
            _ => {}
        }
    }
    // Total thyroidectomy (Milestone 56): a scenario-declared
    // devascularised parathyroid gland makes that side's
    // autotransplant microstep required for the attempt — the
    // appendicectomy severity mechanism applied to the
    // parathyroid pathway (the consulted standard for a gland
    // that cannot be preserved is autotransplantation, T44
    // Recommendation 27b; T42 Recommendation 43).
    if proc.id == "proc.thyroidectomy.total" {
        match trace.case.parathyroid_devascularized.as_deref() {
            Some("right") => {
                required.insert("m7.1".to_string());
            }
            Some("left") => {
                required.insert("m7.2".to_string());
            }
            _ => {}
        }
    }
    // Upper GI endoscopy (Milestone 62): a scenario of ongoing
    // hematemesis makes the airway-protection microstep required
    // for the attempt — the appendicectomy severity mechanism
    // applied to the airway pathway (sedation over an unprotected
    // airway in that configuration computes aspiration, T52/T53).
    if proc.id == "proc.upper-gi-endoscopy"
        && trace.case.severity.as_deref() == Some("ongoing-hematemesis")
    {
        required.insert("m1.3".to_string());
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
    let refill_at_start: f64 = engine.net_refill_ml();
    let urine_at_start: f64 = engine.cumulative_urine_ml();
    let intake_at_start: f64 = engine.cumulative_intake_ml();
    let product_at_start: f64 = engine.cumulative_product_ml();

    let mut at = Attempt {
        proc,
        params: tparams,
        engine,
        beats_at_start,
        volume_at_start,
        refill_at_start,
        urine_at_start,
        intake_at_start,
        product_at_start,
        performed: HashMap::new(),
        criteria: HashMap::new(),
        identified: HashSet::new(),
        clipped: HashSet::new(),
        divided: HashSet::new(),
        misclip_cbd: None,
        required,
        severity: trace.case.severity.clone(),
        base_condition: trace.case.base_condition.clone(),
        defect: trace.case.defect.clone(),
        parathyroid_devascularized: trace.case.parathyroid_devascularized.clone(),
        lesion: trace.case.lesion.clone(),
        declared_class: None,
        endo_modalities: HashSet::new(),
        closure_method: None,
        deferred_criteria: Vec::new(),
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
        repair_done: false,
        bailout_chosen: false,
        bleeds: Vec::new(),
        flow_sources: Vec::new(),
        pending_infusion_stops: Vec::new(),
        infused_ml: 0.0,
        transfused_ml: 0.0,
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
            // its timing against incision can be evaluated. Resolved
            // by its fulfills marker, not by id (Milestone 28: the two
            // procedures' prophylaxis microsteps share the marker).
            let id = at
                .proc
                .phases
                .iter()
                .flat_map(|p| p.steps.iter())
                .flat_map(|s| s.microsteps.iter())
                .find(|m| m.fulfills.as_deref() == Some("prophylaxis"))
                .map(|m| m.id.clone());
            if let Some(id) = id {
                at.do_microstep(t, &id);
            }
        }
        "checklist" => {
            // WHO phases resolve by their fulfills marker (Milestone
            // 28 generalization; the cholecystectomy's m0.8/m0.9/m8.7
            // are found by the same markers they always carried).
            if let Some(phase) = &a.phase {
                let id = at
                    .proc
                    .phases
                    .iter()
                    .flat_map(|p| p.steps.iter())
                    .flat_map(|s| s.microsteps.iter())
                    .find(|m| m.fulfills.as_deref() == Some(phase.as_str()))
                    .map(|m| m.id.clone());
                if let Some(id) = id {
                    at.do_microstep(t, &id);
                }
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
                    ("dp2", "continue-dissection") if at.proc.id == "proc.carpal-release" => {
                        at.error(
                            t,
                            "err.no-bailout",
                            "at dp2 the structures at risk were declared unidentifiable and division continued instead of altering strategy (design/05)".into(),
                        );
                    }
                    ("dp2", "continue-dissection") if at.proc.id == "proc.appy.lap" => {
                        at.error(
                            t,
                            "err.no-bailout",
                            "at dp2 the appendiceal base was declared unidentifiable and dissection continued instead of altering strategy (design/05)".into(),
                        );
                    }
                    ("dp2", "continue-dissection") if at.proc.id == "proc.ulnar-decompression" => {
                        at.error(
                            t,
                            "err.no-bailout",
                            "at dp2 the nerves at risk were declared unidentifiable and division continued instead of altering strategy (design/05)".into(),
                        );
                    }
                    ("dp2", "continue-dissection") if at.proc.id == "proc.lap-inguinal-hernia" => {
                        at.error(
                            t,
                            "err.no-bailout",
                            "at dp2 the danger anatomy was declared unaccountable and division/fixation continued instead of altering strategy (design/05)".into(),
                        );
                    }
                    ("dp2", "continue-dissection") if at.proc.id == "proc.thyroidectomy.total" => {
                        at.error(
                            t,
                            "err.no-bailout",
                            "at dp2 the second look found a nerve or parathyroid account incomplete and dissection continued toward division instead of altering strategy (design/05)".into(),
                        );
                    }
                    ("dp5", "fixation") if at.proc.id == "proc.lap-inguinal-hernia" => {
                        // The fixation decision makes the zonal
                        // fixation microsteps required for this
                        // attempt — the ulnar transposition
                        // mechanism (Milestone 44) applied to a
                        // fixation configuration (Milestone 49).
                        for m in ["m6.4", "m6.5", "m6.6"] {
                            at.required.insert(m.to_string());
                        }
                        at.log(t, "config", "fixation configuration: zonal fixation microsteps m6.4-m6.6 become required".into());
                    }
                    ("dp5", "anterior-transposition") if at.proc.id == "proc.ulnar-decompression" => {
                        // The configuration decision makes the
                        // transposition microsteps required for this
                        // attempt and drops the in-situ completion —
                        // the appendicectomy closure mechanism
                        // (Milestone 28) generalised to a whole
                        // configuration (Milestone 44).
                        if !at.performed.contains_key("m6.2") {
                            at.required.remove("m6.2");
                        }
                        for m in ["m6.3", "m6.4", "m6.5", "m6.6"] {
                            at.required.insert(m.to_string());
                        }
                        at.log(t, "config", "anterior transposition configuration: transposition microsteps m6.3-m6.6 become required, in-situ completion m6.2 dropped".into());
                    }
                    ("dp2", "continue-dissection") => {
                        at.error(
                            t,
                            "err.no-bailout",
                            "at dp2 the Critical View was declared unobtainable and dissection continued instead of altering strategy (guideline T3)".into(),
                        );
                    }
                    ("dp3", c) if at.proc.id == "proc.appy.lap" => {
                        // The closure decision makes the chosen closure
                        // microstep required for this attempt.
                        let mid = match c {
                            "endoloop" => Some("m6.2"),
                            "stapler" => Some("m6.3"),
                            "polymeric-clips" => Some("m6.4"),
                            _ => None,
                        };
                        if let Some(mid) = mid {
                            at.required.insert(mid.to_string());
                            at.log(t, "config", format!("closure method {c} becomes required for this attempt"));
                        }
                    }
                    ("dp3", c) if at.proc.id == "proc.upper-gi-endoscopy" => {
                        // The classification declaration: the record
                        // the therapy keys on, held separately from
                        // the scenario truth the scoring rules judge
                        // it against (Milestone 62).
                        at.declared_class = Some(c.to_string());
                        at.log(t, "config", format!("classification declared for the record the therapy keys on: {c}"));
                    }
                    ("dp2", "ioc") => {
                        for m in ["m5.1", "m5.2", "m5.3", "m5.4", "m5.5", "m5.6", "m5.7", "m5.8", "m5.9", "m5.10"] {
                            at.required.insert(m.to_string());
                        }
                        at.log(t, "config", "IOC group becomes required for this attempt".into());
                    }
                    ("dp2", c) if at.proc.id == "proc.chole.lap" && (c.starts_with("subtotal") || c == "convert-open") => {
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
                    // The appendicectomy's parallel chain (Milestone 28).
                    if kind == "cecal-injury" && c.kind == "clip-on-cecum" {
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
                if s == "canal.appendix" && at.proc.id == "proc.appy.lap" && at.misclip_cbd.is_some() {
                    at.misclip_cbd = None;
                    for c in at.complications.iter_mut() {
                        if c.kind == "clip-on-cecum" {
                            c.recognised = true;
                            c.controlled_s = Some(t);
                        }
                    }
                    at.recognised_kinds.insert("clip-on-cecum".to_string());
                    at.log(t, "control", "misplaced clip on the cecal wall recognised and removed — near miss, no division occurred".into());
                }
            }
        }
        "energy" => {
            if let Some(s) = &a.structure {
                if at.proc.id == "proc.appy.lap" {
                    // Appendicectomy: energy on the appendix or cecum
                    // before the base is identified (Milestone 28).
                    let bowel = ["canal.appendix", "canal.cecum"].contains(&s.as_str());
                    if bowel && !at.gate_at(t) {
                        at.error(
                            t,
                            "err.energy-before-id",
                            format!("electrocautery applied to {s} before the appendiceal base was identified"),
                        );
                        if s == "canal.cecum" {
                            at.complications.push(Complication {
                                kind: "thermal-cecal-injury".to_string(),
                                t_onset_s: t,
                                detail: "thermal injury to the cecal wall from energy applied before the base was identified (its clinical presentation is delayed perforation - recorded structurally; no thermal model exists in the physiology engine)".into(),
                                resolved_structure: Some(s.clone()),
                                stewart_way_class: None,
                                recognised: false,
                                controlled_s: None,
                                loss_ml: None,
                            });
                        }
                    } else {
                        at.log(t, "note", format!("energy applied to {s} with the base identified"));
                    }
                } else {
                    let duct = ["duct.cystic-duct", "duct.common-hepatic-duct", "duct.common-bile"].contains(&s.as_str());
                    if duct && !at.gate_at(t) {
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
        }
        "infuse" => {
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
        "transfuse" => {
            // Milestone 26: a transfuse naming a known product
            // composition routes through the engine's product
            // channel (red cells + protein at the product's own
            // concentrations) and is tallied separately from
            // crystalloid. Without a known product it routes as
            // volume only through the event channel, as before
            // Milestone 26, and the log says so — the fluid is
            // accounted, its composition is not modelled.
            let label = a.label.clone().unwrap_or_else(|| a.kind.clone());
            let spec = a
                .product
                .as_deref()
                .and_then(|k| at.engine.model.product_spec(k));
            match spec {
                Some((unit_vol, hct, prot)) => {
                    let vol = a.volume_ml.unwrap_or(unit_vol);
                    let rate = a.rate_ml_s.unwrap_or(16.67);
                    if vol > 0.0 && rate > 0.0 {
                        at.transfused_ml += vol;
                        let tick = at.engine.tick;
                        let key = a.product.clone().unwrap_or_default();
                        at.engine.apply(
                            tick,
                            Event::SetProductFlow {
                                rate_ml_s: rate,
                                hematocrit: hct,
                                protein_g_per_ml: prot,
                                label: format!("theatre transfuse: {label}"),
                            },
                        );
                        let dur_ticks = (vol / rate / TICK_SECONDS).round() as u64;
                        at.engine.apply(
                            tick + dur_ticks,
                            Event::SetProductFlow {
                                rate_ml_s: 0.0,
                                hematocrit: hct,
                                protein_g_per_ml: prot,
                                label: format!("theatre transfuse ends: {label}"),
                            },
                        );
                        at.log(
                            t,
                            "infuse",
                            format!("{label}: {vol:.0} mL {key} at {rate:.2} mL/s (product channel)"),
                        );
                    }
                }
                None => {
                    let vol = a.volume_ml.unwrap_or(0.0);
                    let rate = a.rate_ml_s.unwrap_or(16.67);
                    if vol > 0.0 && rate > 0.0 {
                        at.infused_ml += vol;
                        let flow_label = format!("infuse:{label}");
                        at.start_flow(&flow_label, rate);
                        let dur_ticks = (vol / rate / TICK_SECONDS).round() as u64;
                        let stop_tick = at.engine.tick + dur_ticks;
                        at.pending_infusion_stops.push((stop_tick, flow_label));
                        at.log(
                            t,
                            "infuse",
                            format!("{label}: {vol:.0} mL at {rate:.2} mL/s (no product composition named; volume only)"),
                        );
                    }
                }
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
    // Milestone 18: transcapillary refill during the attempt is a
    // real inflow into the compartments (interstitium -> plasma), so
    // it is added back exactly as infused volume is — the identity
    // then measures gross blood loss, and refill is reported by the
    // engine's own state, not hidden inside the loss figure.
    // Milestone 25: the same accounting extends to the renal/intake
    // boundary — intake during the attempt is an inflow (added
    // back), urine an outflow (subtracted) — so the identity still
    // measures gross blood loss alone now that the engine excretes.
    // Milestone 26: the same accounting extends once more, to the
    // product channel — blood products given during the attempt are
    // an inflow measured by the engine's own product integral
    // (added back), so the identity still measures gross blood
    // loss alone now that the engine transfuses.
    let refill_during_attempt = at.engine.net_refill_ml() - at.refill_at_start;
    let urine_during_attempt = at.engine.cumulative_urine_ml() - at.urine_at_start;
    let intake_during_attempt = at.engine.cumulative_intake_ml() - at.intake_at_start;
    let product_during_attempt = at.engine.cumulative_product_ml() - at.product_at_start;
    let loss_engine = {
        let l = (at.volume_at_start + at.infused_ml + product_during_attempt
            + refill_during_attempt
            + intake_during_attempt
            - urine_during_attempt)
            - volume_end;
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
            let drug_label = if proc.id == "proc.appy.lap" {
                "antibiotic prophylaxis"
            } else {
                "cefazolin"
            };
            at.errors.push(ErrorEvent {
                t_s: p,
                id: "err.prophylaxis-window".to_string(),
                detail: format!(
                    "{} given {}; the cited window is within {:.0} min before incision (T7)",
                    drug_label,
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
        transfused_ml: at.transfused_ml,
    };

    // Appendicectomy (Milestone 28): a perforated appendix completed
    // without suctioning the contamination computes its postoperative
    // consequence here, at scoring — residual contamination declares
    // as an intra-abdominal abscess, the same "postoperative
    // consequence in the debrief" treatment as the stump leak.
    if proc.id == "proc.appy.lap"
        && trace.case.severity.as_deref() == Some("perforated")
        && !at.performed.contains_key("m7.2")
    {
        at.errors.push(ErrorEvent {
            t_s: end_t,
            id: "err.contamination-uncontrolled".to_string(),
            detail: "perforated appendicitis completed without suctioning the contamination (m7.2 not performed); WSES recommends suction of intra-abdominal collections in complicated appendicitis (T14)".to_string(),
        });
        at.complications.push(Complication {
            kind: "intra-abdominal-abscess".to_string(),
            t_onset_s: end_t,
            detail: "intra-abdominal abscess declared as a postoperative consequence of residual contamination (structural outcome; the physiology engine has no peritoneal compartment, so no volume effect is computed)".into(),
            resolved_structure: None,
            stewart_way_class: None,
            recognised: false,
            controlled_s: None,
            loss_ml: None,
        });
    }

    // Carpal tunnel release (Milestone 42): a ligament divided
    // without the completeness confirmation computes its
    // postoperative consequence here, at scoring — an unconfirmed
    // release declares as persistent symptoms, the same
    // "postoperative consequence in the debrief" treatment as the
    // stump leak and the abscess. The revision literature is
    // explicit that incomplete release is the most common reason
    // for persistent symptoms after this operation (T27). A failed
    // attempt is excluded: its division resolved onto the nerve,
    // and its declared outcome is the injury, not the release's
    // completeness.
    if proc.id == "proc.carpal-release"
        && at.failed.is_none()
        && at.divided.contains("ligament.transverse-carpal")
        && !at.performed.contains_key("m6.2")
    {
        at.errors.push(ErrorEvent {
            t_s: end_t,
            id: "err.incomplete-release".to_string(),
            detail: "release completed without confirming its completeness (m6.2 not performed); the most common reason for persistent symptoms after carpal tunnel release is incomplete release of the transverse carpal ligament, distally at the palmar arch or proximally at the antebrachial fascia (T27)".to_string(),
        });
        at.complications.push(Complication {
            kind: "incomplete-release".to_string(),
            t_onset_s: end_t,
            detail: "persistent symptoms declared as a postoperative consequence of the unconfirmed (incomplete) release (structural outcome; no physiology representation of entrapment exists in the engine, so no volume effect is computed)".into(),
            resolved_structure: Some("ligament.transverse-carpal".to_string()),
            stewart_way_class: None,
            recognised: false,
            controlled_s: None,
            loss_ml: None,
        });
    }

    // Ulnar nerve decompression (Milestone 44): the same
    // scoring-time treatment for this operation's three computed
    // postoperative consequences. Each is a named technical
    // failure in the specialty's own failure taxonomy (T34), and
    // each is declared here, at scoring — none fails the attempt;
    // all are managed at dp4 by return to theatre.
    //
    // (a) An unconfirmed release: the retinaculum was divided but
    // the completeness confirmation (m5.4) was omitted. The
    // revision series quantifies what an unconfirmed release
    // leaves behind (arcade of Struthers 71.4%, deep
    // flexor-pronator aponeurosis 38%, T35).
    if proc.id == "proc.ulnar-decompression"
        && at.failed.is_none()
        && at.divided.contains("ligament.cubital-tunnel-retinaculum")
        && !at.performed.contains_key("m5.4")
    {
        at.errors.push(ErrorEvent {
            t_s: end_t,
            id: "err.incomplete-release".to_string(),
            detail: "release completed without confirming its completeness along the full length (m5.4 not performed); incomplete decompression is a named technical cause of failure after this operation (T34), and the sites an unconfirmed release leaves behind are the revision series' findings — arcade of Struthers 71.4%, deep flexor-pronator aponeurosis 38% (T35)".to_string(),
        });
        at.complications.push(Complication {
            kind: "incomplete-release".to_string(),
            t_onset_s: end_t,
            detail: "persistent symptoms declared as a postoperative consequence of the unconfirmed (incomplete) release (structural outcome; no physiology representation of entrapment exists in the engine, so no volume effect is computed)".into(),
            resolved_structure: Some("ligament.cubital-tunnel-retinaculum".to_string()),
            stewart_way_class: None,
            recognised: false,
            controlled_s: None,
            loss_ml: None,
        });
    }

    // (b) An unstable nerve completed in situ: the subluxating
    // variant's nerve was assessed at m6.1 and the attempt did
    // not take the transposition branch at dp5. The specialty
    // consensus routes instability to transposition (T29, T31);
    // leaving the nerve unstable is the taxonomy's "persistent or
    // new subluxation/instability" technical failure (T34).
    if proc.id == "proc.ulnar-decompression"
        && at.failed.is_none()
        && at.variant.as_deref() == Some("variant.subluxating-nerve")
        && !at
            .decisions
            .iter()
            .any(|d| d.id == "dp5" && d.choice == "anterior-transposition")
    {
        at.errors.push(ErrorEvent {
            t_s: end_t,
            id: "err.subluxation-unaddressed".to_string(),
            detail: "the released nerve was unstable at the stability assessment and the operation was completed in situ (no anterior-transposition decision at dp5); persistent subluxation/instability is a named technical cause of failure after this operation (T34), and transposition is the consensus configuration for the unstable nerve (T29, T31)".to_string(),
        });
        at.complications.push(Complication {
            kind: "nerve-instability".to_string(),
            t_onset_s: end_t,
            detail: "postoperative nerve instability declared as a consequence of completing the decompression in situ over an unstable nerve: the nerve continues to subluxate over the medial epicondyle with flexion, the chronic irritation the transposition configuration exists to relieve (T29) (structural outcome; no volume effect is computed)".into(),
            resolved_structure: Some("major.ulnar".to_string()),
            stewart_way_class: None,
            recognised: false,
            controlled_s: None,
            loss_ml: None,
        });
    }

    // (c) A transposition performed over an intact medial
    // intermuscular septum: the transposed nerve (m6.5) kinks
    // over the septum's edge — the creation of a new compression
    // site (T34), and the single commonest residual finding at
    // revision of failed transposition (intact septum 76.2%, T35).
    if proc.id == "proc.ulnar-decompression"
        && at.failed.is_none()
        && at.performed.contains_key("m6.5")
        && !at.performed.contains_key("m6.4")
    {
        at.errors.push(ErrorEvent {
            t_s: end_t,
            id: "err.new-compression-site".to_string(),
            detail: "anterior transposition performed without releasing the medial intermuscular septum (m6.4 not performed); an intact septum was found in 76.2% of revisions of failed transposition (T35), and creating a new area of compression is a named technical cause of failure (T34)".to_string(),
        });
        at.complications.push(Complication {
            kind: "new-compression".to_string(),
            t_onset_s: end_t,
            detail: "a new compression site at the intact medial intermuscular septum declared as a postoperative consequence of the transposition (structural outcome; no volume effect is computed)".into(),
            resolved_structure: Some("ligament.medial-intermuscular-septum".to_string()),
            stewart_way_class: None,
            recognised: false,
            controlled_s: None,
            loss_ml: None,
        });
    }

    // Inguinal hernia repair (Milestone 49): this operation's
    // scoring-time rules, on the same treatment as the earlier
    // procedures' postoperative consequences. A failed attempt is
    // excluded from both: its declared outcome is the injury.
    //
    // (a) The fixation judgment pair, keyed on the scenario's defect
    // characterisation: fixation of a defect that is not a large
    // medial (M3) defect is a judgment error (non-fixation is the
    // guideline default, T36/T38); a large medial defect completed
    // WITHOUT fixation computes the recurrence consequence (T36;
    // T37's reported recurrence signal runs the same way).
    if proc.id == "proc.lap-inguinal-hernia" && at.failed.is_none() {
        let fixation_performed = ["m6.4", "m6.5", "m6.6"]
            .iter()
            .any(|m| at.performed.contains_key(*m));
        let large_medial = at.defect.as_deref() == Some("large-medial-m3");
        if fixation_performed && !large_medial {
            at.errors.push(ErrorEvent {
                t_s: end_t,
                id: "err.unnecessary-fixation".to_string(),
                detail: "mesh fixated for a defect that is not a large medial (M3) defect; non-fixation is recommended in almost all hernia types except large medial defects (T36), and fixation is unnecessary in most minimally invasive repairs (T38)".to_string(),
            });
        }
        if large_medial && !fixation_performed && at.performed.contains_key("m6.2") {
            at.errors.push(ErrorEvent {
                t_s: end_t,
                id: "err.no-fixation-large-defect".to_string(),
                detail: "large medial (M3 EHS) defect completed without mesh fixation; fixation of large medial defects in TEP/TAPP is the HerniaSurge recommendation (T36) and the golden rules recommend fixation in large, especially direct, hernias (T38)".to_string(),
            });
            at.complications.push(Complication {
                kind: "recurrence".to_string(),
                t_onset_s: end_t,
                detail: "recurrence declared as a postoperative consequence of the unfixed large medial defect: the mesh over a dilated direct floor without fixation is the configuration the fixation recommendation exists for (T36; recurrence after non-fixated mesh in direct repairs markedly increased in the meta-analysis the 2023 update reports, T37) (structural outcome; no volume effect is computed)".into(),
                resolved_structure: Some("sac.inguinal-hernia".to_string()),
                stewart_way_class: None,
                recognised: false,
                controlled_s: None,
                loss_ml: None,
            });
        }
        // (b) An unconfirmed peritoneal closure: the flap was closed
        // (m7.1) but its completeness was never confirmed (m7.2) —
        // exposed mesh is the adhesion/obstruction mechanism (T36,
        // T38 Rule 10).
        if at.performed.contains_key("m7.1") && !at.performed.contains_key("m7.2") {
            at.errors.push(ErrorEvent {
                t_s: end_t,
                id: "err.incomplete-peritoneal-closure".to_string(),
                detail: "peritoneal closure completed without confirming its completeness (m7.2 not performed); gaps, holes or tears of the peritoneum should be closed to reduce the risk of early bowel obstruction or mesh exposure (T38), and exposed mesh may cause bowel adhesions resulting in obstruction (T36)".to_string(),
            });
            at.complications.push(Complication {
                kind: "bowel-adhesion".to_string(),
                t_onset_s: end_t,
                detail: "bowel adhesion to exposed mesh declared as a postoperative consequence of the unconfirmed peritoneal closure (structural outcome; the physiology engine has no peritoneal compartment, so no volume effect is computed)".into(),
                resolved_structure: Some("peritoneum.peritoneum".to_string()),
                stewart_way_class: None,
                recognised: false,
                controlled_s: None,
                loss_ml: None,
            });
        }
    }

    // Total thyroidectomy (Milestone 56): this operation's
    // scoring-time consequences, on the same treatment. A failed
    // attempt is excluded throughout: its declared outcome is the
    // nerve injury, not the parathyroid or field consequences.
    if proc.id == "proc.thyroidectomy.total" && at.failed.is_none() {
        let mut hypocalcemia = false;
        // (a) The per-side parathyroid account: a side whose gated
        // work was completed with crit2 undemonstrated on that side
        // never had its glands under the operation's control.
        for (side, demo, divs) in [
            ("right", "m3.2", ["artery.right-inferior-thyroid-artery", "ligament.right-ligament-of-berry"]),
            ("left", "m5.3", ["artery.left-inferior-thyroid-artery", "ligament.left-ligament-of-berry"]),
        ] {
            let divided_side = divs.iter().any(|d| at.divided.contains(*d));
            if divided_side && !at.performed.contains_key(demo) {
                at.errors.push(ErrorEvent {
                    t_s: end_t,
                    id: "err.parathyroid-unaccounted".to_string(),
                    detail: format!("the {side} side's pedicle and Berry work was completed with its parathyroid account undemonstrated (microstep {demo} not performed); the parathyroid glands and their blood supply should be preserved during thyroid surgery (T42), and identification of fewer than two parathyroid glands at surgery is an independent predictor of permanent hypocalcemia (T47)"),
                });
                hypocalcemia = true;
            }
        }
        // (b) A scenario-declared devascularised gland completed
        // without its autotransplant: the gland's function is lost
        // either way; the transplant is what gives the tissue a
        // second blood supply (T44, Recommendation 27b).
        if let Some(side) = at.parathyroid_devascularized.as_deref() {
            let auto = if side == "right" { "m7.1" } else { "m7.2" };
            if !at.performed.contains_key(auto) {
                at.errors.push(ErrorEvent {
                    t_s: end_t,
                    id: "err.devascularized-gland-not-autotransplanted".to_string(),
                    detail: format!("the scenario's devascularised {side} parathyroid gland was completed without autotransplantation (microstep {auto} not performed); if a parathyroid gland cannot be preserved, parathyroid autotransplantation should be performed (T44)"),
                });
                hypocalcemia = true;
            }
        }
        if hypocalcemia {
            at.complications.push(Complication {
                kind: "hypocalcemia".to_string(),
                t_onset_s: end_t,
                detail: "postoperative hypocalcemia declared as a consequence of parathyroid failure: transient hypocalcemia is the commonest complication of total thyroidectomy (median incidence 27%, range 19-38%, across 115 studies; permanent hypoparathyroidism median 1%, range 0-3%) (T47), treated by oral calcium first-line, calcitriol as necessary, intravenous calcium if severe or refractory (T44) (structural outcome; the physiology engine has no calcium axis, so no biochemical trajectory is computed)".into(),
                resolved_structure: Some("gland.parathyroid-glands".to_string()),
                stewart_way_class: None,
                recognised: false,
                controlled_s: None,
                loss_ml: None,
            });
        }
        // (c) An unconfirmed haemostasis after Berry work: the
        // closed neck collects blood against the trachea.
        let berry_divided = at.divided.contains("ligament.right-ligament-of-berry")
            || at.divided.contains("ligament.left-ligament-of-berry");
        if berry_divided && !at.performed.contains_key("m7.4") {
            at.errors.push(ErrorEvent {
                t_s: end_t,
                id: "err.unconfirmed-haemostasis".to_string(),
                detail: "neck closed without the haemostasis confirmation (m7.4 not performed); prior to closure a dry, bloodless field should be verified, with positive-pressure ventilation to assess for venous bleeding (T44)".to_string(),
            });
            at.complications.push(Complication {
                kind: "neck-hematoma".to_string(),
                t_onset_s: end_t,
                detail: "postoperative neck hematoma declared as a consequence of the unconfirmed field: collected blood in the closed neck compresses the cervical trachea and impairs laryngeal venous return, with rapid airway edema and stridor; nonoperative management is not recommended and untreated hematoma is life-threatening — the standard is immediate bedside evaluation and a low threshold for cervical exploration (T44) (structural outcome; no bleed volume is computed, because no consulted rate exists for this field and none is invented)".into(),
                resolved_structure: Some("airway.trachea".to_string()),
                stewart_way_class: None,
                recognised: false,
                controlled_s: None,
                loss_ml: None,
            });
        }
    }

    // Upper GI endoscopy (Milestone 62): this procedure's
    // scoring-time rules — the therapy actually delivered, judged
    // against the scenario truth. A failed attempt is excluded:
    // its declared outcome is the perforation, not the therapy
    // judgment. The declaration is judged first (a wrong class is
    // a departure in itself), then the delivery is judged as the
    // truth required — the thyroidectomy's "judged at scoring"
    // treatment, on the Forrest partition both guidelines use.
    if proc.id == "proc.upper-gi-endoscopy" && at.failed.is_none() {
        if let Some((kind, class)) = at.endo_truth() {
            let truth_group = if kind == "dieulafoy" {
                "dieulafoy"
            } else {
                Attempt::endo_forrest_group(&class)
            };
            let declared_group = at.declared_class.as_deref().map(|c| {
                if c == "dieulafoy-lesion" {
                    "dieulafoy"
                } else {
                    Attempt::endo_forrest_group(c.strip_prefix("forrest-").unwrap_or(c))
                }
            });
            if let Some(dg) = declared_group {
                if dg != truth_group {
                    at.errors.push(ErrorEvent {
                        t_s: end_t,
                        id: "err.misclassification".to_string(),
                        detail: format!(
                            "the classification declared at dp3 ({}) differs from the lesion's true stigmata ({}) in treatment-relevant group: therapy was keyed to a class the lesion does not carry — the Forrest classification is to be used in all peptic ulcer hemorrhage precisely because therapy keys on it (T49)",
                            at.declared_class.as_deref().unwrap_or_default(),
                            at.lesion.as_deref().unwrap_or_default()
                        ),
                    });
                }
            }
            // The therapy delivered, clot removal aside (it is a
            // diagnostic exposure act, not a hemostasis modality).
            let therapy: Vec<&str> = ["epinephrine", "mechanical", "thermal"]
                .into_iter()
                .filter(|m| at.endo_modalities.contains(*m))
                .collect();
            let lesion_structure = if kind == "dieulafoy" {
                "lesion.dieulafoy"
            } else {
                "lesion.peptic-ulcer"
            };
            let rebleed = |at: &mut Attempt, detail: String| {
                at.complications.push(Complication {
                    kind: "rebleeding".to_string(),
                    t_onset_s: end_t,
                    detail,
                    resolved_structure: Some(lesion_structure.to_string()),
                    stewart_way_class: None,
                    recognised: false,
                    controlled_s: None,
                    loss_ml: None,
                });
            };
            match truth_group {
                "high" => {
                    if therapy.is_empty() {
                        at.errors.push(ErrorEvent {
                            t_s: end_t,
                            id: "err.high-risk-untreated".to_string(),
                            detail: format!(
                                "the lesion's true stigmata are high-risk ({}) and no endoscopic therapy was delivered: endoscopic therapy is recommended for active spurting, active oozing and nonbleeding visible vessels (T49; T50)",
                                at.lesion.as_deref().unwrap_or_default()
                            ),
                        });
                        let rate = match class.as_str() {
                            "iia" => "43%",
                            _ => "55%",
                        };
                        rebleed(
                            &mut at,
                            format!(
                                "rebleeding declared as a post-procedure consequence of the untreated high-risk lesion: further bleeding without endoscopic therapy runs at {rate} for this class in the consulted tabulation (T51) (structural outcome; the rate is a proportion of patients, not a flow, so no volume is computed)"
                            ),
                        );
                    } else if therapy == ["epinephrine"] {
                        at.errors.push(ErrorEvent {
                            t_s: end_t,
                            id: "err.epinephrine-monotherapy".to_string(),
                            detail: "the high-risk lesion was treated with epinephrine injection alone: epinephrine is not to be used as endoscopic monotherapy — if used, it is combined with a second hemostasis modality (T49, strong recommendation, high-quality evidence; T50, statement 10)".to_string(),
                        });
                        rebleed(
                            &mut at,
                            "rebleeding declared as a post-procedure consequence of epinephrine-only therapy: injection temporises and the vessel reopens — the consequence both guidelines' monotherapy prohibition exists to prevent (T49; T50) (structural outcome; no volume is computed)".to_string(),
                        );
                    }
                }
                "dieulafoy" => {
                    if therapy.is_empty() {
                        at.errors.push(ErrorEvent {
                            t_s: end_t,
                            id: "err.high-risk-untreated".to_string(),
                            detail: "the Dieulafoy lesion was identified and no endoscopic therapy was delivered: endoscopic therapy is the first-choice management of this lesion (T54)".to_string(),
                        });
                        rebleed(
                            &mut at,
                            "rebleeding declared as a post-procedure consequence of the untreated Dieulafoy lesion: a caliber-persistent submucosal artery left unoccluded (T54) (structural outcome; no volume is computed)".to_string(),
                        );
                    } else if !therapy.contains(&"mechanical") {
                        at.errors.push(ErrorEvent {
                            t_s: end_t,
                            id: "err.substandard-modality".to_string(),
                            detail: "the Dieulafoy lesion was treated without mechanical therapy: endoscopic band ligation or hemoclipping are the most effective options for this lesion, and epinephrine injection is a suboptimal treatment (T54)".to_string(),
                        });
                        rebleed(
                            &mut at,
                            "rebleeding declared as a post-procedure consequence of non-mechanical therapy of the Dieulafoy lesion: in the consulted series, early recurrence followed in two of three patients treated solely with epinephrine injection or argon plasma coagulation, against permanent hemostasis around 90% for mechanical therapy (T54) (structural outcome; no volume is computed)".to_string(),
                        );
                    }
                }
                "clot" => {
                    if !therapy.is_empty() && !at.endo_modalities.contains("clot-removal") {
                        at.errors.push(ErrorEvent {
                            t_s: end_t,
                            id: "err.clot-not-addressed".to_string(),
                            detail: "therapy was delivered to an adherent-clot (Forrest IIb) lesion without the clot first being addressed by targeted irrigation and removal (m5.1 not performed): the underlying stigmata the therapy was priced on were never exposed (T49)".to_string(),
                        });
                    }
                }
                _ => {
                    // Low-risk stigmata (IIc/III): no therapy is the
                    // specialty's answer; any delivered is scored.
                    if !therapy.is_empty() {
                        at.errors.push(ErrorEvent {
                            t_s: end_t,
                            id: "err.therapy-not-indicated".to_string(),
                            detail: format!(
                                "endoscopic therapy was delivered to a lesion whose true stigmata are low-risk ({}): flat pigmented spots and clean bases receive no endoscopic therapy (T49; T50) — their untreated further-bleeding rates are 10% and 5% (T51)",
                                at.lesion.as_deref().unwrap_or_default()
                            ),
                        });
                    }
                }
            }
        }
    }

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
        let has_cecal = at.complications.iter().any(|c| c.kind == "cecal-injury");
        let has_leak = at.complications.iter().any(|c| c.kind == "stump-leak");
        let has_abscess = at.complications.iter().any(|c| c.kind == "intra-abdominal-abscess");
        // Milestone 42 (carpal tunnel release): a nerve injury's
        // definitive control is the epineurial repair, the parallel
        // of drainage for the biliary and caecal injuries.
        // Milestone 44 adds the ulnar decompression's injury kinds
        // to the same rule (its repair microstep is also m7.3).
        // Milestone 56 adds total thyroidectomy's recurrent
        // laryngeal nerve injury kinds (its repair microstep is
        // also m7.3); the bilateral kind rides with the unilateral
        // one — the repair obligation is the same.
        let has_nerve_injury = at.complications.iter().any(|c| {
            c.kind == "median-nerve-injury"
                || c.kind == "recurrent-branch-injury"
                || c.kind == "ulnar-nerve-injury"
                || c.kind == "mabc-injury"
                || c.kind == "recurrent-laryngeal-nerve-injury"
                || c.kind == "bilateral-recurrent-laryngeal-nerve-injury"
        });
        let has_incomplete = at.complications.iter().any(|c| c.kind == "incomplete-release");
        // Milestone 44: the ulnar decompression's other two
        // postoperative consequences share the incomplete release's
        // definitive plan — return to theatre to complete the
        // correction (T34).
        let has_instability = at.complications.iter().any(|c| c.kind == "nerve-instability");
        let has_new_compression = at.complications.iter().any(|c| c.kind == "new-compression");
        // Milestone 49 (inguinal hernia repair): the structural
        // injuries take their definitive plan at dp4; the
        // postoperative consequences at dp6. The hernia nerve kind
        // ("nerve-injury") is deliberately NOT in has_nerve_injury
        // above: that rule demands the epineurial repair microstep,
        // which this operation does not carry — its injuries are
        // planned at dp4, and a haemorrhage's control is the
        // all-bleeds-controlled condition already in control_pts.
        let has_hernia_injury = at.complications.iter().any(|c| {
            c.kind == "vascular-injury"
                || c.kind == "nerve-injury"
                || c.kind == "vas-deferens-injury"
                || c.kind == "visceral-injury"
        });
        let has_hernia_postop = at.complications.iter().any(|c| {
            c.kind == "recurrence" || c.kind == "bowel-adhesion"
        });
        // Milestone 56 (total thyroidectomy): the external branch
        // injury is deliberately NOT in has_nerve_injury above —
        // this operation carries no repair microstep for that
        // branch, so its definitive plan is the dp3 referral (the
        // hernia nerve-injury precedent). The two postoperative
        // consequences take their plans at dp6, each by its own
        // standard (return to theatre for hematoma, T44
        // Recommendation 58; the calcium replacement protocol for
        // hypocalcemia, T44 Recommendation 61).
        let has_ebsln_injury = at.complications.iter().any(|c| c.kind == "external-laryngeal-nerve-injury");
        let has_hypocalcemia = at.complications.iter().any(|c| c.kind == "hypocalcemia");
        let has_neck_hematoma = at.complications.iter().any(|c| c.kind == "neck-hematoma");
        // Milestone 62 (upper GI endoscopy): a computed rebleeding
        // or the missed lesion's running haemorrhage takes its
        // definitive plan at dp4 — repeat endoscopy first, the
        // sequence both guidelines put first (T49; T50).
        let has_endo_rebleed = proc.id == "proc.upper-gi-endoscopy"
            && at.complications.iter().any(|c| {
                c.kind == "rebleeding" || c.kind == "hemorrhage"
            });
        let control_pts = if all_bleeds_controlled
            && (!has_bdi || at.drain_placed)
            && (!has_cecal || at.drain_placed)
            && (!has_nerve_injury || at.repair_done)
        {
            1
        } else {
            0
        };
        let escalation_pts = if !at.help_calls.is_empty()
            || at.decisions.iter().any(|d| {
                d.id == "dp3" || d.id == "dp4" || (proc.id == "proc.appy.lap" && (d.id == "dp2" || d.id == "dp5"))
                    || (proc.id == "proc.lap-inguinal-hernia" && d.id == "dp6")
                    || (proc.id == "proc.thyroidectomy.total" && d.id == "dp6")
                    || (proc.id == "proc.upper-gi-endoscopy" && d.id == "dp4")
            })
        {
            1
        } else {
            0
        };
        let plan_pts = if has_hernia_injury {
            // Milestone 49: the hernia injuries' definitive plans
            // are taken at dp4 — convert and repair, or immediate
            // referral to the repair service.
            if at
                .decisions
                .iter()
                .any(|d| d.id == "dp4" && (d.choice == "convert-to-repair" || d.choice == "repair-refer"))
            {
                1
            } else {
                0
            }
        } else if has_hernia_postop {
            // Milestone 49: recurrence and bowel adhesion are
            // definitively treated by return to theatre (dp6).
            if at
                .decisions
                .iter()
                .any(|d| d.id == "dp6" && d.choice == "return-theatre")
            {
                1
            } else {
                0
            }
        } else if has_bdi {
            if at
                .decisions
                .iter()
                .any(|d| d.id == "dp4" && (d.choice == "drain-refer" || d.choice == "convert-repair"))
            {
                1
            } else {
                0
            }
        } else if has_cecal {
            if at
                .decisions
                .iter()
                .any(|d| d.id == "dp4" && (d.choice == "convert-repair" || d.choice == "stapler-repair"))
            {
                1
            } else {
                0
            }
        } else if has_leak || has_abscess {
            if at
                .decisions
                .iter()
                .any(|d| d.id == "dp5" && (d.choice == "return-theatre" || d.choice == "image-guided-drain"))
            {
                1
            } else {
                0
            }
        } else if has_nerve_injury {
            // Milestone 42: the injury decision point is dp3, and
            // the definitive plans are immediate magnified repair or
            // immediate referral to the repair service.
            if at
                .decisions
                .iter()
                .any(|d| d.id == "dp3" && (d.choice == "convert-microscope-repair" || d.choice == "repair-refer"))
            {
                1
            } else {
                0
            }
        } else if has_ebsln_injury {
            // Milestone 56: the external branch's injury has no
            // repair microstep in this operation; its definitive
            // plan is the dp3 referral to the repair / laryngology
            // service.
            if at
                .decisions
                .iter()
                .any(|d| d.id == "dp3" && d.choice == "repair-refer")
            {
                1
            } else {
                0
            }
        } else if has_hypocalcemia || has_neck_hematoma {
            // Milestone 56: the postoperative consequences are
            // planned at dp6, each by its own standard — return to
            // theatre for the hematoma, the calcium replacement
            // protocol for the hypocalcemia.
            if (has_neck_hematoma
                && at
                    .decisions
                    .iter()
                    .any(|d| d.id == "dp6" && d.choice == "return-theatre"))
                || (has_hypocalcemia
                    && at
                        .decisions
                        .iter()
                        .any(|d| d.id == "dp6" && d.choice == "calcium-replacement-protocol"))
            {
                1
            } else {
                0
            }
        } else if has_incomplete || has_instability || has_new_compression {
            // Milestone 42: persistent symptoms from an incomplete
            // release are definitively treated by completing the
            // release at re-operation (dp4). Milestone 44: the
            // ulnar consequences take the same definitive plan —
            // complete the release, transpose the unstable nerve,
            // or release the septum, at re-operation (T34).
            if at
                .decisions
                .iter()
                .any(|d| d.id == "dp4" && d.choice == "return-theatre")
            {
                1
            } else {
                0
            }
        } else if has_endo_rebleed {
            // Milestone 62: the rebleeding pathway's definitive
            // plan is taken at dp4 — repeat endoscopy with therapy
            // first (T49; T50). TAE-first, surgery-first and
            // supportive-only take later steps of the sequence
            // first and earn no plan point.
            if at
                .decisions
                .iter()
                .any(|d| d.id == "dp4" && d.choice == "repeat-endoscopy")
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

    let debrief = if proc.id == "proc.appy.lap" {
        build_pearls_appy(&at, &checklist, &safety, &process, &physiology, &management, &verdict)
    } else if proc.id == "proc.carpal-release" {
        build_pearls_carpal(&at, &checklist, &safety, &process, &physiology, &management, &verdict)
    } else if proc.id == "proc.ulnar-decompression" {
        build_pearls_ulnar(&at, &checklist, &safety, &process, &physiology, &management, &verdict)
    } else if proc.id == "proc.lap-inguinal-hernia" {
        build_pearls_hernia(&at, &checklist, &safety, &process, &physiology, &management, &verdict)
    } else if proc.id == "proc.thyroidectomy.total" {
        build_pearls_thyroid(&at, &checklist, &safety, &process, &physiology, &management, &verdict)
    } else if proc.id == "proc.upper-gi-endoscopy" {
        build_pearls_endoscopy(&at, &checklist, &safety, &process, &physiology, &management, &verdict)
    } else {
        build_pearls(&at, &checklist, &safety, &process, &physiology, &management, &verdict)
    };

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

/// PEARLS debrief for upper GI endoscopy (Milestone 62): same
/// structure and state-derived discipline as the other builders,
/// with this procedure's gate (identification and Forrest
/// classification before therapy), its variant and its guideline
/// points.
fn build_pearls_endoscopy(
    at: &Attempt,
    checklist: &ChecklistScore,
    safety: &SafetyScore,
    process: &ProcessScore,
    physiology: &PhysiologyScore,
    management: &Option<ManagementScore>,
    verdict: &str,
) -> Pearls {
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

    if safety.criteria_before_first_clipdiv == 3 && at.first_clipdiv_t.is_some() {
        plus.push("The gate was demonstrated before the first therapy act — source identified and localised, lesion Forrest-classified and declared, airway–sedation account made: the classification is to be used in all peptic ulcer hemorrhage because therapy keys on it (T49).".to_string());
    }
    if safety.pause_before_first_clip && at.first_clipdiv_t.is_some() {
        plus.push("Pre-therapy pause performed: the declared classification was restated and the modality set matched to it with the team before the first therapy act (T49; T50).".to_string());
    }
    if at.performed.contains_key("m3.3") && at.variant_active("variant.dieulafoy-lesion") {
        plus.push("The Dieulafoy lesion — 1–6.5% of acute nonvariceal upper GI bleeding (T54) — was found by its own discipline: the proximal stomach and lesser curvature searched vessel by vessel for the caliber-persistent artery in near-normal mucosa.".to_string());
    }
    if at.endo_modalities.contains("mechanical")
        && at.variant_active("variant.dieulafoy-lesion")
        && !at.errors.iter().any(|e| e.id == "err.substandard-modality")
    {
        plus.push("The Dieulafoy lesion was treated mechanically — hemoclipping, the modality the consulted review records as most effective for this lesion, with permanent hemostasis around 90% (T54).".to_string());
    }
    if at.complications.iter().any(|c| c.kind == "rebleeding" && c.recognised) {
        plus.push("The rebleeding was recognised and met with the specialty's first move: repeat endoscopy with therapy, ahead of embolization and surgery in the sequence (T49; T50).".to_string());
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

    if at.errors.iter().any(|e| e.id == "err.treat-before-classification") {
        directive.push("Never treat a lesion you have not classified: identify the source, wash the base, read the stigmata and declare the Forrest class before the first therapy act — the class is the therapy decision (Ia/Ib combination therapy; IIa a definitive modality; IIb uncover, then treat what is exposed; IIc/III none) (T49; T50; T51).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.misclassification") {
        directive.push("When the washed base disagrees with the first read, re-declare before therapy, not after it: the second look (m4.2) exists because a clot can lift to show a vessel and a spot can wash clean — the declaration the therapy keys on must be the lesion's true class (T49; T51).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.epinephrine-monotherapy") {
        directive.push("Epinephrine buys the field; it does not close the vessel. If you inject, combine — clip or thermal in the same session: epinephrine monotherapy is the one configuration both guidelines prohibit by name (T49; T50, statement 10).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.high-risk-untreated") {
        directive.push("A spurting, oozing or visible-vessel lesion left untreated keeps its natural history — 55% (Ia/Ib) and 43% (IIa) further bleeding without therapy (T51). If it cannot be treated, that is a dp1 bailout to a centre with cover, not a quiet completion.".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.substandard-modality") {
        directive.push("For a Dieulafoy lesion, occlude the artery mechanically — clip or band. Injection and thermal alone are the suboptimal modalities for a caliber-persistent vessel, with early recurrence the recorded pattern (T54).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.therapy-not-indicated") {
        directive.push("A flat spot (10%) or a clean base (5%) is a discharge-pathway lesion, not a therapy target (T51): treating it buys only the therapeutic risk (T52). The discipline of the gate runs both ways — classify first, then let the class decide, including when the decision is to do nothing.".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.unprotected-airway") {
        directive.push("In ongoing hematemesis the airway is the first procedure: protect it before sedation depth, because sedation removes the reflexes that are keeping blood out of the trachea, and aspiration is among this procedure's commonest serious adverse events (T52; T53).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.missed-variant") {
        directive.push("A survey that found an incidental ulcer has not finished: when the bleeding is unexplained by what you found, search the proximal stomach and lesser curvature for the caliber-persistent artery — the first endoscopy misses this diagnosis in about 15% of cases (T54).".to_string());
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

/// PEARLS debrief for the appendicectomy (Milestone 28): same
/// structure and state-derived discipline as build_pearls, with this
/// procedure's gates, variants and guideline points.
fn build_pearls_appy(
    at: &Attempt,
    checklist: &ChecklistScore,
    safety: &SafetyScore,
    process: &ProcessScore,
    physiology: &PhysiologyScore,
    management: &Option<ManagementScore>,
    verdict: &str,
) -> Pearls {
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

    if safety.criteria_before_first_clipdiv == 3 {
        plus.push("Appendiceal base positively identified and demonstrated before any clip or division — taeniae traced to their convergence, appendix seen arising from it, base condition stated (T19, T14).".to_string());
    }
    if safety.pause_before_first_clip && at.first_clipdiv_t.is_some() {
        plus.push("Pre-division pause performed and the identification confirmed with the team before clipping (module safety culture, T20).".to_string());
    }
    if at.performed.contains_key("m3.5") && at.variant_active("variant.retrocecal") {
        plus.push("The retrocecal appendix — the most common position, 43.5% in the consulted cadaver series (T16) — was managed by mobilizing the cecum before identification, the adaptation the variant demands.".to_string());
    }
    if at.closure_method.as_deref() == Some("stapler") && at.base_condition.as_deref() == Some("necrotic") {
        plus.push("The stapler was chosen because the base was necrotic — sealing healthy tissue rather than cinching a ligature on non-viable tissue (T18).".to_string());
    }
    if at.complications.iter().any(|c| c.kind == "cecal-injury" && c.recognised) {
        plus.push("The cecal injury was recognised during the index operation and a definitive repair plan was made.".to_string());
    }
    if at.severity.as_deref() == Some("perforated")
        && at.performed.contains_key("m7.2")
        && !at.errors.iter().any(|e| e.id == "err.unnecessary-lavage")
    {
        plus.push("Contamination was managed by suction alone, as the guideline recommends (T14); no lavage was performed.".to_string());
    }
    if at.complicated()
        && at.performed.contains_key("m7.2")
        && !at.performed.contains_key("m7.5")
    {
        plus.push("No drain was placed: in adults, drains after appendicectomy do not prevent intra-abdominal abscess and prolong hospitalisation (T14).".to_string());
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

    if at.errors.iter().any(|e| e.id == "err.divide-unidentified") {
        directive.push("Never clip, close or divide at the appendiceal base until the base is positively identified: follow the taeniae coli to their convergence and see the appendix arise from it (T19). What is divided as 'appendix' before that demonstration is cecal wall.".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.closure-mismatch") {
        directive.push("Match the closure to the base condition stated at the gate: a ligature or clips cannot seal a necrotic base — fire the stapler across healthy tissue, or convert (T14, T18).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.divide-unclipped-artery") {
        directive.push("Control the appendiceal artery before dividing the mesoappendix: identify it in the fold and occlude it first (T19; mesoappendix technique per T14).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.contamination-uncontrolled") {
        directive.push("In perforated appendicitis, suction every collection — right iliac fossa, paracolic gutter, pelvis — before closing: residual contamination declares itself as an abscess (T14).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.unnecessary-drain") {
        directive.push("Do not drain an appendicectomy in an adult without a repair to drain: drains do not prevent intra-abdominal abscess and are associated with longer hospitalisation (T14); the meta-analysis found no adult outcome benefit (T15).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.unnecessary-lavage") {
        directive.push("Suction alone for contamination: irrigation has no advantage over suction alone (T14, strong recommendation 1B; T15).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.unnecessary-antibiotics") {
        directive.push("Uncomplicated appendicitis needs the single preoperative dose and no postoperative course (T14).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.no-bailout") {
        directive.push("When the base cannot be identified, alter the strategy: mobilize further, call for senior help, or convert — never divide on presumption (design/05).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.prophylaxis-window") {
        directive.push("Prophylaxis timing is a system step, not a detail: the single broad-spectrum dose inside the window before incision (T14; window per T7).".to_string());
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

/// PEARLS debrief for the carpal tunnel release (Milestone 42):
/// same structure and state-derived discipline as build_pearls,
/// with this procedure's gate, variants and literature points.
fn build_pearls_carpal(
    at: &Attempt,
    checklist: &ChecklistScore,
    safety: &SafetyScore,
    process: &ProcessScore,
    physiology: &PhysiologyScore,
    management: &Option<ManagementScore>,
    verdict: &str,
) -> Pearls {
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

    if safety.criteria_before_first_clipdiv == 3 {
        plus.push("The structures at risk were identified and protected before the ligament was divided — median nerve demonstrated and protected, recurrent branch accounted for, division limits established (T21, T22).".to_string());
    }
    if safety.pause_before_first_clip && at.first_clipdiv_t.is_some() {
        plus.push("Pre-division pause performed and the identification confirmed with the team before division (module safety culture, T20).".to_string());
    }
    if at.performed.contains_key("m5.5") && at.variant_active("variant.transligamentous-recurrent-branch") {
        plus.push("The transligamentous recurrent branch — 11.3% pooled prevalence (T24) — was identified where it pierces the retinaculum and carefully released from the ligament before division (T21).".to_string());
    }
    if at.performed.contains_key("m5.6") && at.variant_active("variant.persistent-median-artery") {
        plus.push("The persistent median artery (7.5% of wrists, T25) was identified between the trunks of the high-division nerve and protected before division.".to_string());
    }
    if at.complications.iter().any(|c| (c.kind == "median-nerve-injury" || c.kind == "recurrent-branch-injury") && c.recognised) {
        plus.push("The nerve injury was recognised during the index operation and a definitive plan was made.".to_string());
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

    if at.errors.iter().any(|e| e.id == "err.divide-unidentified") {
        directive.push("Never divide the transverse carpal ligament until the nerve is seen and protected: the ligament must be clearly visible and exposed, and the nerve identified at the proximal edge of the retinaculum, before any division (T21). The injury this gate prevents is the operation's catastrophic one (T27).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.missed-variant") {
        directive.push("In the transligamentous configuration the branch is inside the ligament being divided: identify it where it pierces the retinaculum and free it from the ligament before division (T21; Lanz group I, T23).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.unprotected-variant-vessel") {
        directive.push("A persistent median artery (7.5% of wrists, T25) runs between the trunks of a high-division nerve: find it and protect it before division — that is the Lanz group III field (T23).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.palmar-cutaneous-injury") {
        directive.push("Keep the dissection on the ulnar side of the field: the palmar cutaneous branch is injured by radial dissection, and its painful neuroma is the approach's named complication (T27; its course and protection, T22).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.incomplete-release") {
        directive.push("Confirm the release before closing: the elevator must pass freely on both sides of the nerve and the fascia release must be confirmed — an unconfirmed release is the most common cause of persistent symptoms after this operation (T27; the completeness check, T21).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.unnecessary-neurolysis") {
        directive.push("Neurolysis is not part of a primary release: internal neurolysis, epineurotomy and tenosynovectomy are rarely indicated here (T21).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.no-bailout") {
        directive.push("When the structures at risk cannot be identified, alter the strategy: extend the exposure, call for senior help, or abort and refer — never divide on presumption (design/05).".to_string());
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

fn build_pearls_ulnar(
    at: &Attempt,
    checklist: &ChecklistScore,
    safety: &SafetyScore,
    process: &ProcessScore,
    physiology: &PhysiologyScore,
    management: &Option<ManagementScore>,
    verdict: &str,
) -> Pearls {
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

    if safety.criteria_before_first_clipdiv == 3 {
        plus.push("The nerves at risk were identified and protected before any fascia was divided — ulnar nerve demonstrated and protected, medial antebrachial cutaneous branches accounted for, full release extent established (T29, T31, T34).".to_string());
    }
    if safety.pause_before_first_clip && at.first_clipdiv_t.is_some() {
        plus.push("Pre-division pause performed and the identification confirmed with the team before division (module safety culture, T20).".to_string());
    }
    if at.performed.contains_key("m6.5") {
        plus.push("The unstable nerve was transposed anteriorly with its perineural vessels preserved and its gliding re-confirmed through the full range (T31) — the configuration the specialty consensus assigns to the subluxating nerve (T29).".to_string());
    }
    if at.complications.iter().any(|c| (c.kind == "ulnar-nerve-injury" || c.kind == "mabc-injury") && c.recognised) {
        plus.push("The nerve injury was recognised during the index operation and a definitive plan was made.".to_string());
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

    if at.errors.iter().any(|e| e.id == "err.divide-unidentified") {
        directive.push("Never divide the fascia of this release until the ulnar nerve is seen and protected: identify it proximal to the tunnel, in undisected tissue, and keep it under vision along the whole length to be released (T31). The injury this gate prevents is the operation's catastrophic one (T34).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.mabc-unaccounted") {
        directive.push("Account for the medial antebrachial cutaneous nerve before dividing anything: its branches cross the incision in the subcutaneous plane, numbness in its distribution is among the most frequent complications of this operation, and its neuroma is the painful one (T29; the injury, T34).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.incomplete-release") {
        directive.push("Confirm the release before closing: the elevator must pass freely and the nerve must glide from the arcade of Struthers to the flexor-pronator aponeurosis — incomplete decompression is a named technical cause of failure, and the revision series finds the missed sites in most failed cases (T34; T35).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.subluxation-unaddressed") {
        directive.push("An unstable nerve does not stay treated in its sulcus: when the stability assessment finds subluxation, transpose — the specialty's one consensus in this operation (T29), implemented as protocol in the consulted cohort (T31); persistent instability is a named technical failure (T34).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.new-compression-site") {
        directive.push("A transposition that leaves the medial intermuscular septum intact trades one compression for another: the septum was intact in 76.2% of revised failed transpositions (T35). Release it, and re-range the elbow before closing (T31).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.no-bailout") {
        directive.push("When the nerves at risk cannot be identified, alter the strategy: extend the exposure, call for senior help, or abort and refer — never divide on presumption (design/05).".to_string());
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

/// PEARLS debrief for the inguinal hernia repair (Milestone 49):
/// same structure and state-derived discipline as build_pearls,
/// with this procedure's gate, variants and guideline points.
fn build_pearls_hernia(
    at: &Attempt,
    checklist: &ChecklistScore,
    safety: &SafetyScore,
    process: &ProcessScore,
    physiology: &PhysiologyScore,
    management: &Option<ManagementScore>,
    verdict: &str,
) -> Pearls {
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

    if safety.criteria_before_first_clipdiv == 3 {
        plus.push("The danger anatomy was accounted for before any division or fixation — triangle of doom delimited with the external iliac vessels identified, triangle of pain delimited, cord parietalized: the critical view of the myopectineal orifice (T38, T39).".to_string());
    }
    if safety.pause_before_first_clip && at.first_clipdiv_t.is_some() {
        plus.push("Pre-division pause performed and the account confirmed with the team before dividing or fixating (module safety culture, T20).".to_string());
    }
    if at.performed.contains_key("m4.4") && at.variant_active("variant.corona-mortis") {
        plus.push("The corona mortis — present in 49.3% of the population (T40) — was found on the survey and protected before medial fixation (T39).".to_string());
    }
    if at.performed.contains_key("m4.5") && at.variant_active("variant.sliding-hernia") {
        plus.push("The sliding configuration (2-5% of indirect hernias, T41) was surveyed before any sac division, and the visceral sac wall was not divided.".to_string());
    }
    if at.complications.iter().any(|c| (c.kind == "vascular-injury" || c.kind == "nerve-injury" || c.kind == "vas-deferens-injury" || c.kind == "visceral-injury") && c.recognised) {
        plus.push("The structural injury was recognised during the index operation and a definitive plan was made.".to_string());
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

    if at.errors.iter().any(|e| e.id == "err.divide-unidentified") {
        directive.push("Never divide or fixate in the preperitoneal space until the triangle of doom is delimited and the external iliac vessels are seen inside it: only when all anatomical elements have been recognized, the dissection completed and haemostasis achieved should mesh placement proceed (T38; the triangle's definition, T39).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.pain-triangle-injury" || e.id == "err.fixation-in-pain-triangle") {
        directive.push("The triangle of pain is protected territorially, not by dissection: the nerves are not systematically exposed in this approach (T38, Rule 2) — establish the iliopubic tract line and keep every fixation point at least 2 cm above it (T38, Rule 9; the nerves and their chronic-pain consequence, T39).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.vas-injury") {
        directive.push("Parietalize before dividing: the duct and gonadal vessels are completely exposed only when the internal spermatic fascia is incised and the sac separated cephalad, and parietalization is sufficient when the vas crosses the external iliac vein (T39; T38, Rule 5).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.missed-variant") {
        directive.push("Survey the sac wall before dividing it: in 2-5% of indirect hernias part of the wall is a viscus (T41), and a sliding sac is reduced, not divided.".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.corona-unprotected") {
        directive.push("Survey Cooper's ligament before fixating into it: the corona mortis arches over it in about half the population (T40), and a cut corona retracts into the obturator canal, where haemostasis is difficult (T39).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.unnecessary-fixation") {
        directive.push("Non-fixation is the default: fixation is recommended only for large medial (M3) defects (T36), and is unnecessary in most minimally invasive repairs (T38, Rule 9).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.no-fixation-large-defect") {
        directive.push("A large medial (M3) defect is the exception that takes fixation: the HerniaSurge recommendation (T36), with adequate mesh size, overlap and dead-space reduction — the recurrence evidence runs against the unfixed direct repair (T37).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.incomplete-peritoneal-closure") {
        directive.push("Confirm the flap closure before deflating: every gap leaves mesh exposed, and exposed mesh is the adhesion and obstruction mechanism (T36; T38, Rule 10).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.no-bailout") {
        directive.push("When the danger anatomy cannot be accounted for, alter the strategy: extend the dissection, call for senior help, or abort and refer — never divide or fixate on presumption (design/05).".to_string());
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

fn build_pearls_thyroid(
    at: &Attempt,
    checklist: &ChecklistScore,
    safety: &SafetyScore,
    process: &ProcessScore,
    physiology: &PhysiologyScore,
    management: &Option<ManagementScore>,
    verdict: &str,
) -> Pearls {
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

    if safety.criteria_before_first_clipdiv == 3 {
        plus.push("The nerve and parathyroid account was demonstrated before the first gated division — nerve identified and traced, parathyroids accounted on the capsule, external branch accounted at the pole: visual identification required in all cases (T42, Recommendation 42A), the parathyroids and their blood supply preserved (T42, Recommendation 43), the superior pole taken on the capsule (T44, Recommendation 25).".to_string());
    }
    if safety.pause_before_first_clip && at.first_clipdiv_t.is_some() {
        plus.push("Pre-division pause performed and the accounts confirmed with the team before the pedicle and Berry divisions (module safety culture, T20).".to_string());
    }
    if at.performed.contains_key("m3.5") && at.variant_active("variant.rln-extralaryngeal-branching") {
        plus.push("The branched nerve — extralaryngeal branching in 39.2% of nerves intraoperatively (T45) — was surveyed branch by branch to the laryngeal entry before division, the anterior motor branch accounted by name.".to_string());
    }
    if at.parathyroid_devascularized.is_some()
        && (at.performed.contains_key("m7.1") || at.performed.contains_key("m7.2"))
    {
        plus.push("The devascularised parathyroid gland was autotransplanted into a marked intramuscular pocket — the consulted standard for a gland that cannot be preserved (T44, Recommendation 27b; T42).".to_string());
    }
    if at.complications.iter().any(|c| (c.kind == "recurrent-laryngeal-nerve-injury" || c.kind == "external-laryngeal-nerve-injury") && c.recognised) {
        plus.push("The nerve injury was recognised during the index operation and a definitive plan was made.".to_string());
    }
    if process.sign_in && process.time_out && process.sign_out {
        plus.push("All three WHO checklist phases were completed at their integration points (T6).".to_string());
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

    if at.errors.iter().any(|e| e.id == "err.divide-unidentified") {
        directive.push("Never divide the inferior pedicle or the ligament of Berry on a side whose nerve you have not seen traced to its laryngeal entry: visual identification is required in all cases (T42, Recommendation 42A), the nerve's course should be visualised through the entire operative field (T44), and the Berry ligament — divided as close to the trachea as possible — is the commonest injury site (T44). Monitoring confirms an identified nerve; it does not identify one (T42, Recommendation 42B; T43).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.missed-variant") {
        directive.push("In a branched nerve, account for every branch to the entry point: the motor fibres run in the anterior branch and posterior branches can carry motor fibres too, so no branch is expendable — and branched nerves are the higher-risk configuration (T45).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.ebsln-unaccounted") {
        directive.push("Take the superior pole on the capsule, vessel by vessel: ligating close to the capsule is the external branch's protection (T44, Recommendation 25), and where the branch cannot be seen, the capsular line is its account (T42; T48).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.parathyroid-unaccounted") {
        directive.push("Account for the glands on the capsule before the pedicle work, and take the inferior pedicle at the capsule — the glands are supplied from that artery (T42, Recommendation 43; T44, Recommendation 27a). Fewer than two glands identified at surgery predicts permanent hypocalcemia (T47).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.devascularized-gland-not-autotransplanted") {
        directive.push("A gland that cannot be preserved is transplanted, not watched: mince it into a marked sternocleidomastoid or strap-muscle pocket (T44, Recommendation 27b; T42) — monitoring calcium detects the hypocalcemia the transplant exists to prevent.".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.unconfirmed-haemostasis") {
        directive.push("Verify a dry, bloodless field before closure, with positive-pressure ventilation to unmask venous bleeding (T44): a hematoma in the closed neck compresses the trachea, and the standard is immediate evaluation with a low threshold for exploration (T44, Recommendation 58).".to_string());
    }
    if at.errors.iter().any(|e| e.id == "err.no-bailout") {
        directive.push("When the second look finds an account incomplete, alter the strategy: extend the exposure, call for senior help, or abort and refer — never divide on presumption (design/05).".to_string());
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
