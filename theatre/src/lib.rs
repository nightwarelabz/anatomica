//! ANATOMICA theatre (Milestone 17 v1): procedure model, safety-gate
//! evaluation and scored attempt runner.
//!
//! The theatre executes scripted attempt traces against an authored
//! procedure (theatre/procedures/) and the physiology engine
//! (anatomica-physiology). Complications are computed from attempt
//! state — identification state, gate state, clip state — never from
//! the trace script: a trace that divides what it believes is the
//! cystic duct before the Critical View of Safety is demonstrated has
//! the divided structure resolved by the model (the common bile duct,
//! the Stewart-Way class III mechanism), exactly as the cognitive
//! literature describes the real injury (Way et al. 2003).
//!
//! Precision law: every clinical number the module uses is cited,
//! calibrated inside a cited range, or verify-flagged in
//! theatre/parameters.json; the loader enforces the same schema gate
//! as the physiology engine's parameter loader.

pub mod model;
pub mod runner;

pub use model::{
    InstrumentsFile, Procedure, ProcedureFile, TheatreParams, Trace, TraceFile,
};
pub use runner::{run_attempt, Debrief};
