//! Milestone 24 diagnostic, retained: prints the Guyton snapshot
//! (stressed volume, MSFP, MCFP, RAP proxy, empirical and formula
//! resistance to venous return) at the end of each standard case,
//! using only the shipped engine/case API so it cannot drift from
//! the validated code paths.
//!
//! Run: cargo run --release --example guyton_probe

use anatomica_physiology::cases::{run_case, CaseKind};
use anatomica_physiology::params::Params;

fn main() {
    let p = Params::load().expect("parameters.json must load");
    for kind in [
        CaseKind::Resting,
        CaseKind::Hemorrhage750,
        CaseKind::Infusion1000,
        CaseKind::Hemorrhage1500,
    ] {
        let o = run_case(&p, kind);
        println!(
            "{kind:?}: post HR {:.1} MAP {:.1} CO {:.2} CVP {:.2} RAP {:.2} | stressed {:.1} mL MSFP {:.2} MCFP {:.2} | RVR emp {:.4} formula {:.4} (rel. diff {:.1}%) | hash {:#018x}",
            o.post.hr,
            o.post.map,
            o.post.co,
            o.post.cvp,
            o.post.rap,
            o.stressed_sys_ml,
            o.msfp_mmhg,
            o.mcfp_mmhg,
            o.rvr_empirical,
            o.rvr_formula,
            (o.rvr_empirical - o.rvr_formula).abs() / o.rvr_formula * 100.0,
            o.trace_hash
        );
    }
}
