//! Data model for the theatre: procedure files, theatre parameters
//! (with the precision-law schema gate), instruments and attempt
//! traces. Serde types mirror the JSON files under theatre/.

use serde::Deserialize;
use std::collections::{HashMap, HashSet};

// ---------------------------------------------------------------------------
// Procedure
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Deserialize)]
pub struct ProcedureFile {
    pub procedure: Procedure,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Procedure {
    pub id: String,
    pub name: String,
    pub authority_basis: String,
    pub validity: serde_json::Value,
    pub review: serde_json::Value,
    pub structures: Vec<StructureRef>,
    pub safety_gates: Vec<Gate>,
    pub decision_points: Vec<DecisionPoint>,
    pub errors: Vec<ErrorDef>,
    pub phases: Vec<Phase>,
    pub variants: Vec<VariantDef>,
    pub scoring: serde_json::Value,
}

#[derive(Debug, Clone, Deserialize)]
pub struct StructureRef {
    pub id: String,
    /// "record" (resolves to a Body Model record) or "absence"
    /// (carries an explicit absence note; resolves_to may still name
    /// the file that documents the absence or the resolution target).
    pub kind: String,
    pub resolves_to: Option<String>,
    pub note: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Gate {
    pub id: String,
    pub kind: String,
    pub name: String,
    pub criteria: Vec<Criterion>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Criterion {
    pub id: String,
    pub name: String,
    pub definition: String,
    pub source: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct DecisionPoint {
    pub id: String,
    pub question: String,
    pub choices: Vec<Choice>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Choice {
    pub id: String,
    pub label: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ErrorDef {
    pub id: String,
    pub severity: String,
    pub definition: String,
    pub consequence: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Phase {
    pub id: String,
    pub name: String,
    #[serde(default)]
    pub group: Option<String>,
    pub steps: Vec<Step>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Step {
    pub id: String,
    pub name: String,
    #[serde(default)]
    pub group: Option<String>,
    pub microsteps: Vec<Microstep>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Microstep {
    pub id: String,
    pub label: String,
    pub verb: String,
    #[serde(default)]
    pub targets: Vec<String>,
    #[serde(default)]
    pub instruments: Vec<String>,
    pub required: bool,
    #[serde(default)]
    pub demonstrates: Option<String>,
    #[serde(default)]
    pub fulfills: Option<String>,
    #[serde(default)]
    pub critical: bool,
    #[serde(default)]
    pub anchors_decision: Option<String>,
    #[serde(default)]
    pub sources: Vec<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct VariantDef {
    pub id: String,
    pub name: String,
    #[serde(default)]
    pub structure_additions: Vec<String>,
}

impl Procedure {
    pub fn load(path: &std::path::Path) -> Result<Procedure, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
        let file: ProcedureFile =
            serde_json::from_str(&text).map_err(|e| format!("procedure does not parse: {e}"))?;
        Ok(file.procedure)
    }

    pub fn microstep(&self, id: &str) -> Option<&Microstep> {
        self.phases
            .iter()
            .flat_map(|p| p.steps.iter())
            .flat_map(|s| s.microsteps.iter())
            .find(|m| m.id == id)
    }

    pub fn microstep_phase(&self, id: &str) -> Option<&str> {
        for p in &self.phases {
            for s in &p.steps {
                if s.microsteps.iter().any(|m| m.id == id) {
                    return Some(p.id.as_str());
                }
            }
        }
        None
    }

    pub fn census(&self) -> (usize, usize, usize, usize) {
        let steps: usize = self.phases.iter().map(|p| p.steps.len()).sum();
        let micro: Vec<&Microstep> = self
            .phases
            .iter()
            .flat_map(|p| p.steps.iter())
            .flat_map(|s| s.microsteps.iter())
            .collect();
        let required = micro.iter().filter(|m| m.required).count();
        (self.phases.len(), steps, micro.len(), required)
    }

    /// Internal consistency validation (reference resolution against
    /// the Body Model data files is the independent checker's job —
    /// tools/theatre_check.py — this validates the file against
    /// itself and the instrument catalogue).
    pub fn validate(&self, instrument_ids: &HashSet<String>) -> Vec<String> {
        let mut problems = Vec::new();
        let register: HashSet<&str> = self.structures.iter().map(|s| s.id.as_str()).collect();
        let mut seen: HashSet<&str> = HashSet::new();
        let mut demonstrated: HashSet<&str> = HashSet::new();
        for p in &self.phases {
            for s in &p.steps {
                for m in &s.microsteps {
                    if !seen.insert(m.id.as_str()) {
                        problems.push(format!("duplicate microstep id {}", m.id));
                    }
                    for t in &m.targets {
                        if !register.contains(t.as_str()) {
                            problems.push(format!("microstep {} targets unregistered structure {t}", m.id));
                        }
                    }
                    for i in &m.instruments {
                        if !instrument_ids.contains(i.as_str()) {
                            problems.push(format!("microstep {} uses unknown instrument {i}", m.id));
                        }
                    }
                    if let Some(c) = &m.demonstrates {
                        demonstrated.insert(c.as_str());
                    }
                    if m.sources.is_empty() {
                        problems.push(format!("microstep {} carries no source", m.id));
                    }
                }
            }
        }
        for g in &self.safety_gates {
            for c in &g.criteria {
                if g.kind == "safety_gate" && !demonstrated.contains(c.id.as_str()) {
                    problems.push(format!(
                        "gate {} criterion {} is demonstrated by no microstep — gate unreachable",
                        g.id, c.id
                    ));
                }
            }
        }
        for v in &self.variants {
            for s in &v.structure_additions {
                if !register.contains(s.as_str()) {
                    problems.push(format!("variant {} adds unregistered structure {s}", v.id));
                }
            }
        }
        for dp in &self.decision_points {
            let has_bailout = dp
                .choices
                .iter()
                .any(|c| c.id.contains("subtotal") || c.id.contains("convert") || c.id.contains("abort"));
            if !has_bailout {
                problems.push(format!(
                    "decision point {} offers no bailout choice (design/05 requires one)",
                    dp.id
                ));
            }
        }
        problems
    }
}

// ---------------------------------------------------------------------------
// Instruments
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Deserialize)]
pub struct InstrumentsFile {
    pub instruments: Vec<Instrument>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Instrument {
    pub id: String,
    pub name: String,
}

impl InstrumentsFile {
    pub fn load(path: &std::path::Path) -> Result<InstrumentsFile, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
        serde_json::from_str(&text).map_err(|e| format!("instruments do not parse: {e}"))
    }

    pub fn ids(&self) -> HashSet<String> {
        self.instruments.iter().map(|i| i.id.clone()).collect()
    }
}

// ---------------------------------------------------------------------------
// Theatre parameters — same precision-law gate as physiology::Params.
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Deserialize)]
pub struct TheatreParameterFile {
    pub parameters: Vec<TheatreParameter>,
    pub sources: Vec<TheatreSource>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct TheatreParameter {
    pub key: String,
    pub value: f64,
    pub unit: String,
    pub status: String,
    pub source: Option<String>,
    pub note: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct TheatreSource {
    pub id: String,
    pub cite: String,
    pub carries: String,
}

#[derive(Debug, Clone)]
pub struct TheatreParams {
    pub file: TheatreParameterFile,
    index: HashMap<String, usize>,
}

impl TheatreParams {
    pub fn load(path: &std::path::Path) -> Result<TheatreParams, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
        let file: TheatreParameterFile =
            serde_json::from_str(&text).map_err(|e| format!("theatre parameters do not parse: {e}"))?;
        let source_ids: HashSet<&str> = file.sources.iter().map(|s| s.id.as_str()).collect();
        let mut index = HashMap::new();
        for (i, p) in file.parameters.iter().enumerate() {
            match p.status.as_str() {
                "cited" | "calibrated" => {
                    let s = p.source.as_deref().ok_or_else(|| {
                        format!("parameter {} is '{}' but names no source", p.key, p.status)
                    })?;
                    if !source_ids.contains(s) {
                        return Err(format!(
                            "parameter {} names unknown source {s}",
                            p.key
                        ));
                    }
                }
                "verify" => {}
                other => {
                    return Err(format!(
                        "parameter {} has unrecognised status '{other}' (precision law: cited, calibrated or verify)",
                        p.key
                    ))
                }
            }
            index.insert(p.key.clone(), i);
        }
        Ok(TheatreParams { file, index })
    }

    pub fn get(&self, key: &str) -> f64 {
        let i = *self.index.get(key).unwrap_or_else(|| panic!("no theatre parameter {key}"));
        self.file.parameters[i].value
    }
}

// ---------------------------------------------------------------------------
// Attempt traces
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Deserialize)]
pub struct TraceFile {
    pub trace: Trace,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Trace {
    pub id: String,
    pub name: String,
    #[serde(default)]
    pub case: CaseSpec,
    pub expect_verdict: String,
    pub actions: Vec<Action>,
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct CaseSpec {
    #[serde(default)]
    pub variant: Option<String>,
    #[serde(default)]
    pub note: Option<String>,
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct Action {
    pub t_s: f64,
    #[serde(rename = "do")]
    pub kind: String,
    #[serde(default)]
    pub id: Option<String>,
    #[serde(default)]
    pub structure: Option<String>,
    #[serde(default)]
    pub drug: Option<String>,
    #[serde(default)]
    pub phase: Option<String>,
    #[serde(default)]
    pub choice: Option<String>,
    #[serde(default)]
    pub complication: Option<String>,
    #[serde(default)]
    pub volume_ml: Option<f64>,
    #[serde(default)]
    pub rate_ml_s: Option<f64>,
    #[serde(default)]
    pub label: Option<String>,
    #[serde(default)]
    pub text: Option<String>,
}

impl Trace {
    pub fn load(path: &std::path::Path) -> Result<Trace, String> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| format!("cannot read {}: {e}", path.display()))?;
        let file: TraceFile =
            serde_json::from_str(&text).map_err(|e| format!("trace does not parse: {e}"))?;
        Ok(file.trace)
    }
}
