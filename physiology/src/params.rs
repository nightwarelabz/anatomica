//! Parameter-set loading and provenance checks.
//!
//! The parameter set lives in `parameters.json` (crate root) and is the
//! single source of every number the engine uses. Each entry carries its
//! unit, a citation or an explicit `verify` status — the loader refuses a
//! parameter that has neither, so an unsourced, unflagged value cannot
//! enter the model silently (ANATOMICA precision law).

use serde::Deserialize;
use std::collections::BTreeMap;

pub const PARAMETERS_JSON: &str = include_str!("../parameters.json");

#[derive(Debug, Clone, Deserialize)]
pub struct Source {
    pub id: String,
    pub citation: String,
    pub locator: String,
    pub accessed: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Parameter {
    pub name: String,
    /// A number, or a two-element array for bound pairs (reflex clamps).
    pub value: serde_json::Value,
    pub unit: String,
    pub cited_range: Option<[f64; 2]>,
    pub source: Option<String>,
    pub status: String, // "cited" | "calibrated" | "verify"
    pub note: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ValidationRange {
    pub output: String,
    pub unit: String,
    pub low: f64,
    pub high: Option<f64>,
    pub source: String,
    pub note: String,
    pub gated: bool,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Expectation {
    pub output: String,
    pub direction: String, // "rises" | "falls" | "narrows"
    pub source: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct PerturbationCase {
    pub id: String,
    pub description: String,
    pub expectations: Vec<Expectation>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ParameterFile {
    pub schema: String,
    pub about: String,
    pub sources: Vec<Source>,
    pub parameters: Vec<Parameter>,
    pub validation_ranges: Vec<ValidationRange>,
    pub perturbation_cases: Vec<PerturbationCase>,
}

#[derive(Debug, Clone)]
pub struct Params {
    pub file: ParameterFile,
    index: BTreeMap<String, usize>,
}

impl Params {
    pub fn load() -> Result<Params, String> {
        let file: ParameterFile = serde_json::from_str(PARAMETERS_JSON)
            .map_err(|e| format!("parameters.json does not parse: {e}"))?;
        let mut index = BTreeMap::new();
        for (i, p) in file.parameters.iter().enumerate() {
            // Precision-law schema gate: every parameter must be cited,
            // calibrated within a cited range, or explicitly verify-flagged.
            match p.status.as_str() {
                "cited" => {
                    if p.source.is_none() {
                        return Err(format!("parameter {} is 'cited' but names no source", p.name));
                    }
                }
                "calibrated" => {
                    if p.source.is_none() || p.cited_range.is_none() {
                        return Err(format!(
                            "parameter {} is 'calibrated' but lacks a source or cited range",
                            p.name
                        ));
                    }
                    let v = p
                        .value
                        .as_f64()
                        .ok_or_else(|| format!("calibrated parameter {} is not a number", p.name))?;
                    let [lo, hi] = p.cited_range.unwrap();
                    if v < lo || v > hi {
                        return Err(format!(
                            "calibrated parameter {} = {v} lies outside its cited range [{lo}, {hi}]",
                            p.name
                        ));
                    }
                }
                "verify" => {}
                other => return Err(format!("parameter {} has unknown status '{other}'", p.name)),
            }
            if index.insert(p.name.clone(), i).is_some() {
                return Err(format!("duplicate parameter name {}", p.name));
            }
        }
        // Every cited source id must exist.
        let known: std::collections::BTreeSet<&str> =
            file.sources.iter().map(|s| s.id.as_str()).collect();
        for p in &file.parameters {
            if let Some(s) = &p.source {
                if !known.contains(s.as_str()) {
                    return Err(format!("parameter {} cites unknown source {s}", p.name));
                }
            }
        }
        for v in &file.validation_ranges {
            if !known.contains(v.source.as_str()) {
                return Err(format!("validation range {} cites unknown source {}", v.output, v.source));
            }
        }
        Ok(Params { file, index })
    }

    pub fn parameter(&self, name: &str) -> &Parameter {
        let i = *self
            .index
            .get(name)
            .unwrap_or_else(|| panic!("parameter '{name}' missing from parameters.json"));
        &self.file.parameters[i]
    }

    pub fn f64(&self, name: &str) -> f64 {
        self.parameter(name)
            .value
            .as_f64()
            .unwrap_or_else(|| panic!("parameter '{name}' is not a number"))
    }

    pub fn bounds(&self, name: &str) -> [f64; 2] {
        let v = &self.parameter(name).value;
        let a = v.as_array().unwrap_or_else(|| panic!("parameter '{name}' is not a bound pair"));
        assert!(a.len() == 2, "bound pair '{name}' must have exactly 2 elements");
        [a[0].as_f64().unwrap(), a[1].as_f64().unwrap()]
    }

    pub fn validation_range(&self, output: &str) -> Option<&ValidationRange> {
        self.file.validation_ranges.iter().find(|v| v.output == output)
    }

    pub fn perturbation_case(&self, id: &str) -> Option<&PerturbationCase> {
        self.file.perturbation_cases.iter().find(|c| c.id == id)
    }
}
