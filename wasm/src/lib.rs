//! ANATOMICA wasm wrapper.
//!
//! Exposes the physiology engine (`physio`) and the theatre runner
//! (`theatre_run` / `theatre_validate`) to the browser build. Every
//! exported function takes JSON text in and returns JSON text out;
//! on any error the return value is `{"error": "<msg>"}`.
//!
//! The theatre parameters and instrument catalogue are embedded at
//! compile time from the theatre crate's data files; the physiology
//! parameters are embedded inside the physiology crate itself
//! (`Params::load`), so this wrapper carries no filesystem access.

use anatomica_physiology::cases::{
    evaluate_course, evaluate_hormones, evaluate_respiratory, evaluate_resting, run_case,
    run_course_arm, run_hormone_set, run_respiratory_case, CaseKind, CourseArm, CourseSet,
    RespCaseKind,
};
use anatomica_physiology::params::Params;
use anatomica_theatre::model::{InstrumentsFile, ProcedureFile, TheatreParams, TraceFile};
use anatomica_theatre::runner;
use wasm_bindgen::prelude::*;

const THEATRE_PARAMETERS_JSON: &str = include_str!("../../theatre/parameters.json");
const THEATRE_INSTRUMENTS_JSON: &str = include_str!("../../theatre/instruments.json");

fn error_json(msg: impl std::fmt::Display) -> String {
    serde_json::json!({ "error": msg.to_string() }).to_string()
}

fn to_json(value: &serde_json::Value) -> Result<String, String> {
    serde_json::to_string(value).map_err(|e| e.to_string())
}

// ---------------------------------------------------------------------------
// Physiology
// ---------------------------------------------------------------------------

fn physio_inner(request_json: &str) -> Result<String, String> {
    let request: serde_json::Value =
        serde_json::from_str(request_json).map_err(|e| format!("request does not parse: {e}"))?;
    let kind = request
        .get("kind")
        .and_then(|k| k.as_str())
        .ok_or_else(|| "request has no string field 'kind'".to_string())?;
    let params = Params::load()?;
    match kind {
        "resting" => {
            let outcome = run_case(&params, CaseKind::Resting);
            let lines = evaluate_resting(&params, &outcome);
            to_json(&serde_json::json!({
                "kind": kind,
                "outcome": outcome,
                "lines": lines,
            }))
        }
        "course" => {
            let set = CourseSet {
                untreated: run_course_arm(&params, CourseArm::Untreated),
                crystalloid: run_course_arm(&params, CourseArm::Crystalloid),
                whole_blood: run_course_arm(&params, CourseArm::WholeBlood),
                components: run_course_arm(&params, CourseArm::Components),
            };
            let lines = evaluate_course(&params, &set);
            to_json(&serde_json::json!({
                "kind": kind,
                "set": set,
                "lines": lines,
            }))
        }
        "hormones" => {
            let set = run_hormone_set(&params);
            let lines = evaluate_hormones(&params, &set);
            to_json(&serde_json::json!({
                "kind": kind,
                "set": set,
                "lines": lines,
            }))
        }
        "respiratory" => {
            // The resting respiratory readout comes from the resting
            // case's post readout, as in the native CLI.
            let resting = run_case(&params, CaseKind::Resting);
            let resting_resp = resting.resp_post.clone();
            // Every RespCaseKind, each with the evaluation case ids
            // the native CLI applies to it in its validate / run
            // sections.
            let arms_spec: [(RespCaseKind, &[&str]); 13] = [
                (
                    RespCaseKind::Hypoventilation,
                    &["hypoventilation_halved", "hypoventilation_bohr"],
                ),
                (
                    RespCaseKind::Shunt,
                    &["shunt_20pct", "shunt_hypoxic_coupled"],
                ),
                (RespCaseKind::Metabolic, &["metabolic_doubled"]),
                (
                    RespCaseKind::HemorrhageResp,
                    &["hemorrhage_750_respiratory"],
                ),
                (RespCaseKind::ShuntPure, &["shunt_20pct"]),
                (
                    RespCaseKind::HemorrhageFeedback,
                    &["hemorrhage_750_metabolic_feedback"],
                ),
                (
                    RespCaseKind::HypoventilationPure,
                    &["hypoventilation_bohr_pure", "hypoventilation_halved"],
                ),
                (
                    RespCaseKind::Hyperventilation,
                    &["hyperventilation_alkalosis"],
                ),
                (
                    RespCaseKind::HyperventilationPure,
                    &["hyperventilation_bohr_pure"],
                ),
                (
                    RespCaseKind::ChronicHypoventilation,
                    &["chronic_hypoventilation_compensated"],
                ),
                (
                    RespCaseKind::ChronicHypoventilationPure,
                    &["chronic_hypoventilation_uncompensated"],
                ),
                (
                    RespCaseKind::ChronicHyperventilation,
                    &["chronic_hyperventilation_compensated"],
                ),
                (
                    RespCaseKind::ChronicHyperventilationPure,
                    &["chronic_hyperventilation_uncompensated"],
                ),
            ];
            let mut arms = Vec::new();
            for (arm_kind, case_ids) in arms_spec {
                let outcome = run_respiratory_case(&params, arm_kind);
                let evaluations: Vec<serde_json::Value> = case_ids
                    .iter()
                    .map(|case_id| {
                        serde_json::json!({
                            "case_id": case_id,
                            "lines": evaluate_respiratory(&params, case_id, &outcome),
                        })
                    })
                    .collect();
                arms.push(serde_json::json!({
                    "kind": format!("{arm_kind:?}"),
                    "outcome": outcome,
                    "evaluations": evaluations,
                }));
            }
            to_json(&serde_json::json!({
                "kind": kind,
                "resting_resp": resting_resp,
                "arms": arms,
            }))
        }
        other => Err(format!(
            "unknown physio kind '{other}' (expected resting|course|hormones|respiratory)"
        )),
    }
}

#[wasm_bindgen(js_name = physio)]
pub fn physio(request_json: &str) -> String {
    match physio_inner(request_json) {
        Ok(s) => s,
        Err(e) => error_json(e),
    }
}

// ---------------------------------------------------------------------------
// Theatre
// ---------------------------------------------------------------------------

fn theatre_run_inner(procedure_json: &str, trace_json: &str) -> Result<String, String> {
    let proc_file: ProcedureFile =
        serde_json::from_str(procedure_json).map_err(|e| format!("procedure does not parse: {e}"))?;
    let trace_file: TraceFile =
        serde_json::from_str(trace_json).map_err(|e| format!("trace does not parse: {e}"))?;
    let tparams = TheatreParams::from_str(THEATRE_PARAMETERS_JSON)?;
    // The embedded instrument catalogue is parsed as part of the
    // run's data load (mirrors the native CLI's load_all), even
    // though the runner itself does not consult it.
    let _instruments: InstrumentsFile = serde_json::from_str(THEATRE_INSTRUMENTS_JSON)
        .map_err(|e| format!("instruments do not parse: {e}"))?;
    let phys = Params::load()?;
    let debrief = runner::run_attempt(&proc_file.procedure, &tparams, &phys, &trace_file.trace)?;
    serde_json::to_string(&debrief).map_err(|e| e.to_string())
}

#[wasm_bindgen(js_name = theatre_run)]
pub fn theatre_run(procedure_json: &str, trace_json: &str) -> String {
    match theatre_run_inner(procedure_json, trace_json) {
        Ok(s) => s,
        Err(e) => error_json(e),
    }
}

fn theatre_validate_inner(procedure_json: &str) -> Result<String, String> {
    let proc_file: ProcedureFile =
        serde_json::from_str(procedure_json).map_err(|e| format!("procedure does not parse: {e}"))?;
    let instruments: InstrumentsFile = serde_json::from_str(THEATRE_INSTRUMENTS_JSON)
        .map_err(|e| format!("instruments do not parse: {e}"))?;
    let problems = proc_file.procedure.validate(&instruments.ids());
    to_json(&serde_json::json!({ "problems": problems }))
}

#[wasm_bindgen(js_name = theatre_validate)]
pub fn theatre_validate(procedure_json: &str) -> String {
    match theatre_validate_inner(procedure_json) {
        Ok(s) => s,
        Err(e) => error_json(e),
    }
}
