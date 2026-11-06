//! Runner probes: synthetic traces that exercise the computation
//! rules the five shipped traces do not — haemorrhage from an
//! unclipped division (engine-computed loss), the recognised-and-
//! removed misclip (near miss, no fail), the unrecognised replaced
//! RHA division (fail + larger bleed), thermal injury from energy on
//! an unidentified duct, and the uncontrolled second branch.
//! Plus: shipped-trace expectations and determinism.

use anatomica_physiology::params::Params as PhysParams;
use anatomica_theatre::model::{Action, CaseSpec, InstrumentsFile, Procedure, TheatreParams, Trace};
use anatomica_theatre::runner::{run_attempt, Debrief};
use std::path::PathBuf;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn load() -> (Procedure, TheatreParams, PhysParams) {
    let r = root();
    let proc = Procedure::load(&r.join("procedures/proc.lap-cholecystectomy.json")).unwrap();
    let tp = TheatreParams::load(&r.join("parameters.json")).unwrap();
    let phys = PhysParams::load().unwrap();
    (proc, tp, phys)
}

fn ms(t: f64, id: &str) -> Action {
    Action { t_s: t, kind: "microstep".into(), id: Some(id.into()), ..Default::default() }
}
fn act(t: f64, kind: &str) -> Action {
    Action { t_s: t, kind: kind.into(), ..Default::default() }
}
fn trace(id: &str, variant: Option<&str>, actions: Vec<Action>) -> Trace {
    Trace {
        id: id.into(),
        name: id.into(),
        case: CaseSpec { variant: variant.map(|s| s.to_string()), note: None },
        expect_verdict: String::new(),
        actions,
    }
}
/// Drug at 0, incision at 120, CVS criteria at 180/240/300.
fn cvs_prefix() -> Vec<Action> {
    vec![
        Action { drug: Some("cefazolin".into()), ..act(0.0, "drug") },
        ms(120.0, "m1.1"),
        ms(180.0, "m3.11"),
        ms(240.0, "m4.2"),
        ms(300.0, "m4.5"),
    ]
}
fn run(tr: &Trace) -> Debrief {
    let (proc, tp, phys) = load();
    run_attempt(&proc, &tp, &phys, tr).unwrap()
}

#[test]
fn unclipped_artery_division_bleeds_engine_computed_volume() {
    let mut a = cvs_prefix();
    a.push(ms(360.0, "m6.3")); // divide cystic artery, never clipped
    a.push(Action { structure: Some("artery.cystic".into()), ..act(660.0, "control") });
    let d = run(&trace("probe-unclipped", None, a));
    assert_eq!(d.verdict, "PASS");
    assert!(d.errors.iter().any(|e| e.id == "err.divide-unclipped-artery"));
    let h = d.complications.iter().find(|c| c.kind == "hemorrhage").expect("haemorrhage computed");
    let loss = h.loss_ml.unwrap();
    // 300 s at the 2.5 mL/s placeholder rate = 750 mL, computed two
    // independent ways (event integral vs engine volume identity).
    assert!((loss - 750.0).abs() < 5.0, "event-integral loss {loss}");
    assert!((d.physiology.blood_loss_ml - loss).abs() < 1.0, "engine identity loss {}", d.physiology.blood_loss_ml);
    assert!(d.physiology.map_nadir_mmhg < d.physiology.map_baseline_mmhg);
}

#[test]
fn misclip_recognised_and_removed_is_a_near_miss_not_a_fail() {
    let a = vec![
        Action { drug: Some("cefazolin".into()), ..act(0.0, "drug") },
        ms(120.0, "m1.1"),
        ms(180.0, "m6.4"), // clip presumed cystic duct pre-CVS -> on the CBD
        Action { structure: Some("duct.cystic-duct".into()), ..act(240.0, "clip_remove") },
        ms(300.0, "m3.11"),
        ms(360.0, "m4.2"),
        ms(420.0, "m4.5"),
        ms(480.0, "m4.6"),
        ms(540.0, "m6.4"),
        ms(600.0, "m6.5"),
        ms(660.0, "m6.6"),
    ];
    let d = run(&trace("probe-near-miss", None, a));
    assert_eq!(d.verdict, "PASS");
    assert!(d.errors.iter().any(|e| e.id == "err.clip-unidentified"));
    let clip = d
        .complications
        .iter()
        .find(|c| c.kind == "clip-on-common-bile-duct")
        .expect("clip-on-CBD complication recorded");
    assert!(clip.recognised, "near miss must be marked recognised after removal");
    assert!(!d.complications.iter().any(|c| c.kind == "bile-duct-injury"));
}

#[test]
fn unrecognised_replaced_rha_division_fails_with_the_larger_bleed() {
    let mut a = cvs_prefix();
    a.push(ms(360.0, "m6.1"));
    a.push(ms(420.0, "m6.3")); // divide "cystic artery" — actually the replaced RHA
    a.push(Action { structure: Some("artery.replaced-rha".into()), ..act(720.0, "control") });
    let d = run(&trace("probe-rha", Some("variant.replaced-rha"), a));
    assert_eq!(d.verdict, "FAIL");
    assert!(d.fail_reason.as_deref().unwrap_or("").contains("err.missed-variant"));
    let h = d.complications.iter().find(|c| c.kind == "hemorrhage").expect("haemorrhage computed");
    assert_eq!(h.resolved_structure.as_deref(), Some("artery.replaced-rha"));
    // 300 s at the 5.0 mL/s placeholder rate = 1500 mL.
    assert!((h.loss_ml.unwrap() - 1500.0).abs() < 5.0);
}

#[test]
fn energy_on_unidentified_duct_is_a_class_ii_mechanism_injury() {
    let a = vec![
        Action { drug: Some("cefazolin".into()), ..act(0.0, "drug") },
        ms(120.0, "m1.1"),
        Action { structure: Some("duct.common-hepatic-duct".into()), ..act(180.0, "energy") },
    ];
    let d = run(&trace("probe-energy", None, a));
    assert_eq!(d.verdict, "PASS"); // scored injury, not an automatic fail
    assert!(d.errors.iter().any(|e| e.id == "err.energy-before-id"));
    let th = d
        .complications
        .iter()
        .find(|c| c.kind == "thermal-bile-duct-injury")
        .expect("thermal injury recorded");
    assert!(th.stewart_way_class.as_deref().unwrap_or("").contains("II"));
}

#[test]
fn uncontrolled_second_branch_bleeds_at_mobilisation() {
    let mut a = cvs_prefix();
    a.push(ms(360.0, "m6.1"));
    a.push(ms(390.0, "m6.2"));
    a.push(ms(420.0, "m6.3"));
    a.push(ms(480.0, "m6.4"));
    a.push(ms(540.0, "m6.5"));
    a.push(ms(600.0, "m6.6"));
    a.push(ms(660.0, "m7.1")); // mobilisation with branch 2 uncontrolled
    a.push(ms(960.0, "m6.8")); // clip the branch: stops the bleed
    let d = run(&trace("probe-branch", Some("variant.double-cystic"), a));
    assert_eq!(d.verdict, "PASS");
    assert!(d.errors.iter().any(|e| e.id == "err.uncontrolled-branch"));
    let h = d.complications.iter().find(|c| c.kind == "hemorrhage").expect("branch haemorrhage computed");
    // 300 s at the 1.2 mL/s placeholder rate = 360 mL.
    assert!((h.loss_ml.unwrap() - 360.0).abs() < 5.0);
}

#[test]
fn shipped_traces_meet_their_expectations() {
    let (proc, tp, phys) = load();
    let dir = root().join("traces");
    let mut paths: Vec<PathBuf> = std::fs::read_dir(&dir)
        .unwrap()
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().map(|x| x == "json").unwrap_or(false))
        .collect();
    paths.sort();
    assert_eq!(paths.len(), 5, "five shipped traces");
    for p in &paths {
        let tr = Trace::load(p).unwrap();
        let d = run_attempt(&proc, &tp, &phys, &tr).unwrap();
        assert_eq!(
            d.verdict.to_lowercase(),
            tr.expect_verdict.to_lowercase(),
            "trace {} verdict",
            tr.id
        );
        if tr.id == "trace-02-divide-before-cvs" {
            let bdi = d
                .complications
                .iter()
                .find(|c| c.kind == "bile-duct-injury")
                .expect("trace-02 computes the bile duct injury");
            assert_eq!(bdi.stewart_way_class.as_deref(), Some("III"));
            assert_eq!(bdi.resolved_structure.as_deref(), Some("duct.common-bile"));
            assert_eq!(d.failed_at_s, Some(1920.0));
            assert_eq!(d.management.as_ref().unwrap().points, 5);
        }
        if tr.id == "trace-01-clean" {
            assert_eq!(d.checklist.pct, 100.0);
            assert_eq!(d.safety_gate.points, 4);
            assert_eq!(d.process.points, 5);
        }
        if tr.id == "trace-04-variant-double-cystic" {
            assert_eq!(d.checklist.required, 67);
        }
        if tr.id == "trace-05-bailout-subtotal" {
            assert!(d.decisions.iter().any(|x| x.id == "dp2" && x.choice == "subtotal-fenestrating"));
            assert_eq!(d.checklist.pct, 100.0);
        }
    }
}

#[test]
fn runs_are_deterministic() {
    let (proc, tp, phys) = load();
    let tr = Trace::load(&root().join("traces/trace-01-clean.json")).unwrap();
    let d1 = run_attempt(&proc, &tp, &phys, &tr).unwrap();
    let d2 = run_attempt(&proc, &tp, &phys, &tr).unwrap();
    assert_eq!(d1.engine_trace_hash, d2.engine_trace_hash);
    assert_eq!(d1.physiology.blood_loss_ml, d2.physiology.blood_loss_ml);
}

#[test]
fn procedure_validates_clean() {
    let r = root();
    let proc = Procedure::load(&r.join("procedures/proc.lap-cholecystectomy.json")).unwrap();
    let instruments = InstrumentsFile::load(&r.join("instruments.json")).unwrap();
    let problems = proc.validate(&instruments.ids());
    assert!(problems.is_empty(), "validation problems: {problems:?}");
}
