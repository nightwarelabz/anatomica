//! ANATOMICA physiology engine — deterministic cardiovascular core.
//!
//! See design/04-physiology-engine.md for the governing architecture,
//! MILESTONE-8.md for the v0 dossier (parameter provenance, validation
//! results, simplifications) and MILESTONE-18.md for v1: baroreflex
//! venomotor recruitment and transcapillary refill, with the
//! haemorrhage magnitude gates they make possible.

pub mod cases;
pub mod engine;
pub mod params;
