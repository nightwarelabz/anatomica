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

fn load_appy() -> (Procedure, TheatreParams, PhysParams) {
    let r = root();
    let proc = Procedure::load(&r.join("procedures/proc.lap-appendectomy.json")).unwrap();
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
        procedure: None,
        case: CaseSpec { variant: variant.map(|s| s.to_string()), ..Default::default() },
        expect_verdict: String::new(),
        actions,
    }
}

fn appy_trace(
    id: &str,
    variant: Option<&str>,
    severity: Option<&str>,
    base: Option<&str>,
    actions: Vec<Action>,
) -> Trace {
    Trace {
        id: id.into(),
        name: id.into(),
        procedure: Some("proc.appy.lap".into()),
        case: CaseSpec {
            variant: variant.map(|s| s.to_string()),
            severity: severity.map(|s| s.to_string()),
            base_condition: base.map(|s| s.to_string()),
            ..Default::default()
        },
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
    let (chole, tp, phys) = load();
    let (appy, _, _) = load_appy();
    let (carpal, _, _) = load_carpal();
    let (ulnar, _, _) = load_ulnar();
    let (hernia, _, _) = load_hernia();
    let dir = root().join("traces");
    let mut paths: Vec<PathBuf> = std::fs::read_dir(&dir)
        .unwrap()
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().map(|x| x == "json").unwrap_or(false))
        .collect();
    paths.sort();
    assert_eq!(paths.len(), 25, "twenty-five shipped traces (five per procedure)");
    for p in &paths {
        let tr = Trace::load(p).unwrap();
        let proc = match tr.procedure.as_deref() {
            Some("proc.appy.lap") => &appy,
            Some("proc.carpal-release") => &carpal,
            Some("proc.ulnar-decompression") => &ulnar,
            Some("proc.lap-inguinal-hernia") => &hernia,
            _ => &chole,
        };
        let d = run_attempt(proc, &tp, &phys, &tr).unwrap();
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
        // Milestone 28: appendicectomy traces.
        if tr.id == "trace-06-appy-clean" {
            assert_eq!(d.checklist.pct, 100.0);
            assert_eq!(d.checklist.required, 37); // 36 standard + chosen closure
            assert_eq!(d.safety_gate.points, 4);
            assert!(d.errors.is_empty(), "clean appy trace carries no errors: {:?}", d.errors);
        }
        if tr.id == "trace-07-appy-variant-retrocecal" {
            assert_eq!(d.checklist.required, 39); // + retrocecal mobilization pair
            assert_eq!(d.checklist.pct, 100.0);
        }
        if tr.id == "trace-08-appy-divide-unidentified" {
            let ci = d
                .complications
                .iter()
                .find(|c| c.kind == "cecal-injury")
                .expect("trace-08 computes the cecal injury");
            assert_eq!(ci.resolved_structure.as_deref(), Some("canal.cecum"));
            assert_eq!(d.failed_at_s, Some(1740.0));
            assert_eq!(d.management.as_ref().unwrap().points, 5);
        }
        if tr.id == "trace-09-appy-perforated" {
            assert_eq!(d.checklist.required, 39); // + suction + antibiotic course
            assert_eq!(d.checklist.pct, 100.0);
            assert!(d.errors.is_empty(), "perforated reference trace carries no errors: {:?}", d.errors);
        }
        if tr.id == "trace-10-appy-variant-pelvic" {
            assert_eq!(d.checklist.required, 38); // + pelvic delivery
            assert_eq!(d.checklist.pct, 100.0);
        }
        // Milestone 42: carpal tunnel release traces.
        if tr.id == "trace-11-carpal-clean" {
            assert_eq!(d.checklist.pct, 100.0);
            assert_eq!(d.checklist.required, 29);
            assert_eq!(d.safety_gate.points, 4);
            // No prophylaxis exists for this operation (T26, T28):
            // the process ceiling is 4 of 5 by design.
            assert_eq!(d.process.points, 4);
            assert!(d.errors.is_empty(), "clean carpal trace carries no errors: {:?}", d.errors);
        }
        if tr.id == "trace-12-carpal-divide-before-id" {
            let inj = d
                .complications
                .iter()
                .find(|c| c.kind == "median-nerve-injury")
                .expect("trace-12 computes the median nerve injury");
            assert_eq!(inj.resolved_structure.as_deref(), Some("major.median"));
            assert_eq!(d.failed_at_s, Some(1020.0));
            assert_eq!(d.management.as_ref().unwrap().points, 5);
            assert_eq!(d.complications.len(), 1, "the failed attempt declares the injury only");
        }
        if tr.id == "trace-13-carpal-variant-transligamentous" {
            assert_eq!(d.checklist.required, 30); // + branch identification
            assert_eq!(d.checklist.pct, 100.0);
            assert_eq!(d.safety_gate.points, 4);
        }
        if tr.id == "trace-14-carpal-variant-persistent-median-artery" {
            assert_eq!(d.checklist.required, 30); // + artery protection
            assert_eq!(d.checklist.pct, 100.0);
        }
        if tr.id == "trace-15-carpal-incomplete-release" {
            assert_eq!(d.checklist.required, 29);
            assert_eq!(d.checklist.missing, vec!["m6.2".to_string()]);
            assert!(d.errors.iter().any(|e| e.id == "err.incomplete-release"));
            let inc = d
                .complications
                .iter()
                .find(|c| c.kind == "incomplete-release")
                .expect("trace-15 computes the incomplete release consequence");
            assert_eq!(inc.resolved_structure.as_deref(), Some("ligament.transverse-carpal"));
            assert_eq!(d.management.as_ref().unwrap().points, 5);
        }
        // Milestone 44: ulnar nerve decompression traces.
        if tr.id == "trace-16-ulnar-clean" {
            assert_eq!(d.checklist.pct, 100.0);
            assert_eq!(d.checklist.required, 30);
            assert_eq!(d.safety_gate.points, 4);
            // No prophylaxis exists for this operation (T33):
            // the process ceiling is 4 of 5 by design.
            assert_eq!(d.process.points, 4);
            assert!(d.errors.is_empty(), "clean ulnar trace carries no errors: {:?}", d.errors);
        }
        if tr.id == "trace-17-ulnar-divide-before-id" {
            let inj = d
                .complications
                .iter()
                .find(|c| c.kind == "ulnar-nerve-injury")
                .expect("trace-17 computes the ulnar nerve injury");
            assert_eq!(inj.resolved_structure.as_deref(), Some("major.ulnar"));
            assert_eq!(d.failed_at_s, Some(1140.0));
            assert_eq!(d.management.as_ref().unwrap().points, 5);
            assert_eq!(d.complications.len(), 1, "the failed attempt declares the injury only");
        }
        if tr.id == "trace-18-ulnar-variant-subluxating" {
            // The dp5 decision drops m6.2 and inserts m6.3-m6.6:
            // 30 - 1 + 4 = 33 required, all performed.
            assert_eq!(d.checklist.required, 33);
            assert_eq!(d.checklist.pct, 100.0);
            assert_eq!(d.safety_gate.points, 4);
            assert!(d.errors.is_empty(), "transposition trace carries no errors: {:?}", d.errors);
            assert!(d.complications.is_empty(), "a transposed unstable nerve computes no instability consequence");
        }
        if tr.id == "trace-19-ulnar-subluxation-unaddressed" {
            assert_eq!(d.checklist.required, 30);
            assert_eq!(d.checklist.pct, 100.0);
            assert!(d.errors.iter().any(|e| e.id == "err.subluxation-unaddressed"));
            let inst = d
                .complications
                .iter()
                .find(|c| c.kind == "nerve-instability")
                .expect("trace-19 computes the instability consequence");
            assert_eq!(inst.resolved_structure.as_deref(), Some("major.ulnar"));
            assert_eq!(d.management.as_ref().unwrap().points, 5);
        }
        if tr.id == "trace-20-ulnar-incomplete-release" {
            assert_eq!(d.checklist.required, 30);
            assert_eq!(d.checklist.missing, vec!["m5.4".to_string()]);
            assert!(d.errors.iter().any(|e| e.id == "err.incomplete-release"));
            let inc = d
                .complications
                .iter()
                .find(|c| c.kind == "incomplete-release")
                .expect("trace-20 computes the incomplete release consequence");
            assert_eq!(inc.resolved_structure.as_deref(), Some("ligament.cubital-tunnel-retinaculum"));
            assert_eq!(d.management.as_ref().unwrap().points, 5);
        }
        // Milestone 49: inguinal hernia repair traces.
        if tr.id == "trace-21-hernia-clean" {
            assert_eq!(d.checklist.pct, 100.0);
            assert_eq!(d.checklist.required, 33);
            assert_eq!(d.safety_gate.points, 4);
            // No prophylaxis exists for this operation (T36, T37):
            // the process ceiling is 4 of 5 by design.
            assert_eq!(d.process.points, 4);
            assert!(d.errors.is_empty(), "clean hernia trace carries no errors: {:?}", d.errors);
        }
        if tr.id == "trace-22-hernia-fixate-before-account" {
            let inj = d
                .complications
                .iter()
                .find(|c| c.kind == "vascular-injury")
                .expect("trace-22 computes the vascular injury");
            assert_eq!(inj.resolved_structure.as_deref(), Some("artery.right-external-iliac-artery"));
            assert_eq!(d.failed_at_s, Some(1200.0));
            assert_eq!(d.management.as_ref().unwrap().points, 5);
            let h = d.complications.iter().find(|c| c.kind == "hemorrhage").expect("haemorrhage computed");
            // 300 s at the 5.0 mL/s placeholder rate = 1500 mL.
            assert!((h.loss_ml.unwrap() - 1500.0).abs() < 5.0);
        }
        if tr.id == "trace-23-hernia-variant-corona-mortis" {
            assert_eq!(d.checklist.required, 34); // + corona protection
            assert_eq!(d.checklist.pct, 100.0);
            assert!(d.errors.is_empty(), "corona trace carries no errors: {:?}", d.errors);
        }
        if tr.id == "trace-24-hernia-variant-sliding" {
            assert_eq!(d.checklist.required, 34); // + sliding survey
            assert_eq!(d.checklist.pct, 100.0);
            assert!(d.errors.is_empty(), "sliding trace carries no errors: {:?}", d.errors);
        }
        if tr.id == "trace-25-hernia-incomplete-closure" {
            assert_eq!(d.checklist.required, 33);
            assert_eq!(d.checklist.missing, vec!["m7.2".to_string()]);
            assert!(d.errors.iter().any(|e| e.id == "err.incomplete-peritoneal-closure"));
            let ad = d
                .complications
                .iter()
                .find(|c| c.kind == "bowel-adhesion")
                .expect("trace-25 computes the bowel adhesion consequence");
            assert_eq!(ad.resolved_structure.as_deref(), Some("peritoneum.peritoneum"));
            assert_eq!(d.management.as_ref().unwrap().points, 5);
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
    let appy = Procedure::load(&r.join("procedures/proc.lap-appendectomy.json")).unwrap();
    let problems = appy.validate(&instruments.ids());
    assert!(problems.is_empty(), "appendicectomy validation problems: {problems:?}");
    let carpal = Procedure::load(&r.join("procedures/proc.carpal-release.json")).unwrap();
    let problems = carpal.validate(&instruments.ids());
    assert!(problems.is_empty(), "carpal tunnel release validation problems: {problems:?}");
    let ulnar = Procedure::load(&r.join("procedures/proc.ulnar-decompression.json")).unwrap();
    let problems = ulnar.validate(&instruments.ids());
    assert!(problems.is_empty(), "ulnar decompression validation problems: {problems:?}");
    let hernia = Procedure::load(&r.join("procedures/proc.lap-inguinal-hernia.json")).unwrap();
    let problems = hernia.validate(&instruments.ids());
    assert!(problems.is_empty(), "inguinal hernia repair validation problems: {problems:?}");
}

// ---------------------------------------------------------------------------
// Milestone 28: appendicectomy probes — the computation rules the five
// shipped appy traces do not exercise.
// ---------------------------------------------------------------------------

/// Drug at 0, incision at 120, base-gate criteria at 180/240/300,
/// pause at 360, artery identified at 420.
fn appy_gate_prefix() -> Vec<Action> {
    vec![
        Action { drug: Some("broad-spectrum-prophylaxis".into()), ..act(0.0, "drug") },
        ms(120.0, "m1.1"),
        ms(180.0, "m3.1"),
        ms(240.0, "m3.2"),
        ms(300.0, "m3.3"),
        ms(360.0, "m4.2"),
        ms(420.0, "m3.4"),
    ]
}

fn run_appy(tr: &Trace) -> Debrief {
    let (proc, tp, phys) = load_appy();
    run_attempt(&proc, &tp, &phys, tr).unwrap()
}

#[test]
fn appy_uncontrolled_artery_bleeds_engine_computed_volume() {
    let mut a = appy_gate_prefix();
    a.push(ms(480.0, "m5.1"));
    a.push(ms(540.0, "m5.3")); // divide mesoappendix, artery never clipped
    a.push(Action { structure: Some("artery.appendicular-artery".into()), ..act(840.0, "control") });
    let d = run_appy(&appy_trace("probe-appy-artery", None, Some("uncomplicated"), Some("healthy"), a));
    assert_eq!(d.verdict, "PASS");
    assert!(d.errors.iter().any(|e| e.id == "err.divide-unclipped-artery"));
    let h = d.complications.iter().find(|c| c.kind == "hemorrhage").expect("haemorrhage computed");
    // 300 s at the 1.5 mL/s placeholder rate = 450 mL, two ways.
    assert!((h.loss_ml.unwrap() - 450.0).abs() < 5.0, "event-integral loss {:?}", h.loss_ml);
    assert!((d.physiology.blood_loss_ml - 450.0).abs() < 5.0, "engine identity loss {}", d.physiology.blood_loss_ml);
}

#[test]
fn appy_endoloop_on_necrotic_base_computes_stump_leak() {
    let mut a = appy_gate_prefix();
    a.push(ms(480.0, "m5.1"));
    a.push(ms(540.0, "m5.2"));
    a.push(ms(600.0, "m5.3"));
    a.push(Action { id: Some("dp3".into()), choice: Some("endoloop".into()), ..act(660.0, "decision") });
    a.push(ms(720.0, "m6.2")); // endoloop on a necrotic base
    a.push(ms(780.0, "m6.5"));
    a.push(Action { complication: Some("stump-leak".into()), ..act(840.0, "recognise") });
    a.push(Action { id: Some("dp5".into()), choice: Some("return-theatre".into()), ..act(900.0, "decision") });
    let d = run_appy(&appy_trace("probe-appy-leak", None, Some("uncomplicated"), Some("necrotic"), a));
    assert_eq!(d.verdict, "PASS"); // a scored major error, not the master-rule fail
    assert!(d.errors.iter().any(|e| e.id == "err.closure-mismatch"));
    let leak = d.complications.iter().find(|c| c.kind == "stump-leak").expect("stump leak computed");
    assert!(leak.recognised);
    assert_eq!(d.management.as_ref().unwrap().points, 5);
}

#[test]
fn appy_stapler_on_necrotic_base_is_the_scored_correct_choice() {
    let mut a = appy_gate_prefix();
    a.push(ms(480.0, "m5.1"));
    a.push(ms(540.0, "m5.2"));
    a.push(ms(600.0, "m5.3"));
    a.push(Action { id: Some("dp3".into()), choice: Some("stapler".into()), ..act(660.0, "decision") });
    a.push(ms(720.0, "m6.3"));
    a.push(ms(780.0, "m6.5"));
    let d = run_appy(&appy_trace("probe-appy-stapler", None, Some("uncomplicated"), Some("necrotic"), a));
    assert_eq!(d.verdict, "PASS");
    assert!(!d.errors.iter().any(|e| e.id == "err.closure-mismatch"));
    assert!(d.complications.is_empty());
}

#[test]
fn appy_retrocecal_identification_before_mobilization_does_not_open_the_gate() {
    let a = vec![
        Action { drug: Some("broad-spectrum-prophylaxis".into()), ..act(0.0, "drug") },
        ms(120.0, "m1.1"),
        ms(180.0, "m3.1"), // traced — but the cecum is unmobilized: crit1 deferred
        ms(240.0, "m3.2"),
        ms(300.0, "m3.3"),
        ms(360.0, "m6.5"), // divide on a gate that never opened
    ];
    let d = run_appy(&appy_trace("probe-appy-retro", Some("variant.retrocecal"), Some("uncomplicated"), Some("healthy"), a));
    assert_eq!(d.verdict, "FAIL");
    assert!(d.complications.iter().any(|c| c.kind == "cecal-injury"));
    assert_eq!(d.safety_gate.criteria_before_first_clipdiv, 2);
}

#[test]
fn appy_misclip_on_cecum_recognised_and_removed_is_a_near_miss() {
    let mut a = vec![
        Action { drug: Some("broad-spectrum-prophylaxis".into()), ..act(0.0, "drug") },
        ms(120.0, "m1.1"),
        ms(180.0, "m6.4"), // closure clip across the presumed base -> on the cecum
        Action { structure: Some("canal.appendix".into()), ..act(240.0, "clip_remove") },
        ms(300.0, "m3.1"),
        ms(360.0, "m3.2"),
        ms(420.0, "m3.3"),
        ms(480.0, "m4.2"),
        ms(540.0, "m3.4"),
        ms(600.0, "m5.1"),
        ms(660.0, "m5.2"),
        ms(720.0, "m5.3"),
    ];
    a.push(Action { id: Some("dp3".into()), choice: Some("endoloop".into()), ..act(780.0, "decision") });
    a.push(ms(840.0, "m6.2"));
    a.push(ms(900.0, "m6.5"));
    let d = run_appy(&appy_trace("probe-appy-near-miss", None, Some("uncomplicated"), Some("healthy"), a));
    assert_eq!(d.verdict, "PASS");
    assert!(d.errors.iter().any(|e| e.id == "err.clip-unidentified"));
    let clip = d.complications.iter().find(|c| c.kind == "clip-on-cecum").expect("clip-on-cecum recorded");
    assert!(clip.recognised);
    assert!(!d.complications.iter().any(|c| c.kind == "cecal-injury"));
}

#[test]
fn appy_drain_and_lavage_are_scored_against_the_guideline() {
    let mut a = appy_gate_prefix();
    a.push(ms(480.0, "m5.1"));
    a.push(ms(540.0, "m5.2"));
    a.push(ms(600.0, "m5.3"));
    a.push(Action { id: Some("dp3".into()), choice: Some("endoloop".into()), ..act(660.0, "decision") });
    a.push(ms(720.0, "m6.2"));
    a.push(ms(780.0, "m6.5"));
    a.push(ms(840.0, "m7.3")); // lavage
    a.push(ms(900.0, "m7.5")); // drain
    let d = run_appy(&appy_trace("probe-appy-drain", None, Some("perforated"), Some("inflamed"), a));
    assert_eq!(d.verdict, "PASS");
    assert!(d.errors.iter().any(|e| e.id == "err.unnecessary-lavage"));
    assert!(d.errors.iter().any(|e| e.id == "err.unnecessary-drain"));
}

#[test]
fn appy_perforated_without_suction_computes_abscess() {
    let mut a = appy_gate_prefix();
    a.push(ms(480.0, "m5.1"));
    a.push(ms(540.0, "m5.2"));
    a.push(ms(600.0, "m5.3"));
    a.push(Action { id: Some("dp3".into()), choice: Some("stapler".into()), ..act(660.0, "decision") });
    a.push(ms(720.0, "m6.3"));
    a.push(ms(780.0, "m6.5"));
    // no m7.2 suction despite the perforated scenario
    let d = run_appy(&appy_trace("probe-appy-abscess", None, Some("perforated"), Some("inflamed"), a));
    assert_eq!(d.verdict, "PASS");
    assert!(d.errors.iter().any(|e| e.id == "err.contamination-uncontrolled"));
    assert!(d.complications.iter().any(|c| c.kind == "intra-abdominal-abscess"));
}

#[test]
fn appy_division_without_closure_computes_stump_leak() {
    let mut a = appy_gate_prefix();
    a.push(ms(480.0, "m5.1"));
    a.push(ms(540.0, "m5.2"));
    a.push(ms(600.0, "m5.3"));
    a.push(ms(660.0, "m6.5")); // divided with no closure applied
    let d = run_appy(&appy_trace("probe-appy-unclosed", None, Some("uncomplicated"), Some("healthy"), a));
    assert_eq!(d.verdict, "PASS");
    assert!(d.errors.iter().any(|e| e.id == "err.divide-unclosed-base"));
    assert!(d.complications.iter().any(|c| c.kind == "stump-leak"));
}

// ---------------------------------------------------------------------------
// Milestone 42: carpal tunnel release probes — the computation rules
// the five shipped carpal traces do not exercise.
// ---------------------------------------------------------------------------

fn load_carpal() -> (Procedure, TheatreParams, PhysParams) {
    let r = root();
    let proc = Procedure::load(&r.join("procedures/proc.carpal-release.json")).unwrap();
    let tp = TheatreParams::load(&r.join("parameters.json")).unwrap();
    let phys = PhysParams::load().unwrap();
    (proc, tp, phys)
}

fn carpal_trace(id: &str, variant: Option<&str>, actions: Vec<Action>) -> Trace {
    Trace {
        id: id.into(),
        name: id.into(),
        procedure: Some("proc.carpal-release".into()),
        case: CaseSpec { variant: variant.map(|s| s.to_string()), ..Default::default() },
        expect_verdict: String::new(),
        actions,
    }
}

/// Planning, incision, then the three gate criteria and the pause.
fn carpal_gate_prefix() -> Vec<Action> {
    vec![
        ms(60.0, "m0.1"),
        ms(120.0, "m0.2"),
        ms(180.0, "m1.1"),
        ms(240.0, "m4.1"),
        ms(300.0, "m4.2"),
        ms(360.0, "m5.1"),
        ms(420.0, "m5.4"),
    ]
}

fn run_carpal(tr: &Trace) -> Debrief {
    let (proc, tp, phys) = load_carpal();
    run_attempt(&proc, &tp, &phys, tr).unwrap()
}

#[test]
fn carpal_unprotected_persistent_median_artery_bleeds_engine_computed_volume() {
    let mut a = carpal_gate_prefix();
    a.push(ms(480.0, "m6.1")); // divide with the variant artery unprotected
    a.push(Action { structure: Some("artery.persistent-median".into()), ..act(780.0, "control") });
    let d = run_carpal(&carpal_trace("probe-carpal-pma", Some("variant.persistent-median-artery"), a));
    assert_eq!(d.verdict, "PASS"); // collateral injury, not the master-rule fail
    assert!(d.errors.iter().any(|e| e.id == "err.unprotected-variant-vessel"));
    let h = d.complications.iter().find(|c| c.kind == "hemorrhage").expect("haemorrhage computed");
    assert_eq!(h.resolved_structure.as_deref(), Some("artery.persistent-median"));
    // 300 s at the 1.0 mL/s placeholder rate = 300 mL, two ways.
    assert!((h.loss_ml.unwrap() - 300.0).abs() < 5.0, "event-integral loss {:?}", h.loss_ml);
    assert!((d.physiology.blood_loss_ml - 300.0).abs() < 5.0, "engine identity loss {}", d.physiology.blood_loss_ml);
}

#[test]
fn carpal_transligamentous_branch_unaccounted_fails_on_the_branch() {
    let a = vec![
        ms(60.0, "m0.1"),
        ms(120.0, "m0.2"),
        ms(180.0, "m1.1"),
        ms(240.0, "m4.1"), // crit1
        ms(300.0, "m4.2"), // crit3
        ms(360.0, "m5.1"), // crit2 stated — deferred: branch inside the ligament
        ms(420.0, "m5.2"),
        ms(480.0, "m5.4"), // pause
        ms(540.0, "m6.1"), // divide: crit2 is the only missing criterion
    ];
    let d = run_carpal(&carpal_trace("probe-carpal-translig", Some("variant.transligamentous-recurrent-branch"), a));
    assert_eq!(d.verdict, "FAIL");
    assert_eq!(d.failed_at_s, Some(540.0));
    assert!(d.errors.iter().any(|e| e.id == "err.missed-variant"));
    let inj = d
        .complications
        .iter()
        .find(|c| c.kind == "recurrent-branch-injury")
        .expect("recurrent branch injury computed");
    assert_eq!(inj.resolved_structure.as_deref(), Some("nerve.recurrent-branch-median"));
    assert!(
        !d.complications.iter().any(|c| c.kind == "median-nerve-injury"),
        "the variant resolution replaces, not adds to, the master-rule injury"
    );
    assert_eq!(d.safety_gate.criteria_before_first_clipdiv, 2);
}

#[test]
fn carpal_transligamentous_with_nerve_also_unidentified_is_the_master_rule() {
    let a = vec![
        ms(60.0, "m0.1"),
        ms(120.0, "m0.2"),
        ms(180.0, "m1.1"),
        ms(240.0, "m4.2"), // crit3 only; crit1 never demonstrated either
        ms(300.0, "m5.1"), // crit2 deferred
        ms(360.0, "m6.1"), // divide with two criteria missing
    ];
    let d = run_carpal(&carpal_trace("probe-carpal-translig-master", Some("variant.transligamentous-recurrent-branch"), a));
    assert_eq!(d.verdict, "FAIL");
    assert!(d.errors.iter().any(|e| e.id == "err.divide-unidentified"));
    assert!(d.complications.iter().any(|c| c.kind == "median-nerve-injury"));
    assert!(!d.complications.iter().any(|c| c.kind == "recurrent-branch-injury"));
}

#[test]
fn carpal_radial_dissection_computes_palmar_cutaneous_injury() {
    let mut a = carpal_gate_prefix();
    a.push(ms(480.0, "m6.1"));
    a.push(ms(540.0, "m6.2"));
    a.push(ms(600.0, "m6.4")); // radial dissection across the branch's territory
    let d = run_carpal(&carpal_trace("probe-carpal-pcb", None, a));
    assert_eq!(d.verdict, "PASS");
    assert!(d.errors.iter().any(|e| e.id == "err.palmar-cutaneous-injury"));
    let inj = d
        .complications
        .iter()
        .find(|c| c.kind == "palmar-cutaneous-branch-injury")
        .expect("palmar cutaneous injury computed");
    assert_eq!(inj.resolved_structure.as_deref(), Some("nerve.palmar-cutaneous-branch"));
}

#[test]
fn carpal_routine_neurolysis_is_scored_against_the_technique_literature() {
    let mut a = carpal_gate_prefix();
    a.push(ms(480.0, "m6.1"));
    a.push(ms(540.0, "m6.2"));
    a.push(ms(600.0, "m6.5")); // internal neurolysis in a primary release
    let d = run_carpal(&carpal_trace("probe-carpal-neurolysis", None, a));
    assert_eq!(d.verdict, "PASS");
    assert!(d.errors.iter().any(|e| e.id == "err.unnecessary-neurolysis"));
    assert!(d.complications.is_empty());
}

#[test]
fn carpal_nerve_injury_without_repair_scores_no_control_point() {
    let a = vec![
        ms(60.0, "m0.1"),
        ms(120.0, "m0.2"),
        ms(180.0, "m1.1"),
        ms(240.0, "m6.1"), // divide before identification: the nerve is divided
        Action { complication: Some("median-nerve-injury".into()), ..act(300.0, "recognise") },
        Action { id: Some("dp3".into()), choice: Some("repair-refer".into()), ..act(360.0, "decision") },
        // no m7.3 repair microstep: the plan is referral, control stays unearned
    ];
    let d = run_carpal(&carpal_trace("probe-carpal-norepair", None, a));
    assert_eq!(d.verdict, "FAIL");
    let mg = d.management.as_ref().expect("management scored");
    assert_eq!(mg.recognised, 2);
    assert_eq!(mg.control, 0, "no repair performed, no control point");
    assert_eq!(mg.plan, 1, "immediate referral is a definitive plan");
    assert_eq!(mg.points, 4);
}

// ---------------------------------------------------------------------------
// Milestone 44: ulnar nerve decompression probes — the computation
// rules the five shipped ulnar traces do not exercise: the gate's
// second resolution (the cutaneous nerve), the boundary of that
// resolution, the configuration decision's required-set mechanics,
// the transposition's own completeness rule, and the repair /
// referral control asymmetry for a nerve injury.
// ---------------------------------------------------------------------------

fn load_ulnar() -> (Procedure, TheatreParams, PhysParams) {
    let r = root();
    let proc = Procedure::load(&r.join("procedures/proc.ulnar-decompression.json")).unwrap();
    let tp = TheatreParams::load(&r.join("parameters.json")).unwrap();
    let phys = PhysParams::load().unwrap();
    (proc, tp, phys)
}

fn ulnar_trace(id: &str, variant: Option<&str>, actions: Vec<Action>) -> Trace {
    Trace {
        id: id.into(),
        name: id.into(),
        procedure: Some("proc.ulnar-decompression".into()),
        case: CaseSpec { variant: variant.map(|s| s.to_string()), ..Default::default() },
        expect_verdict: String::new(),
        actions,
    }
}

/// Planning, incision, then the three gate criteria and the pause:
/// m1.3 demonstrates crit2, m2.1 crit1, m2.3 crit3, m3.3 the pause.
fn ulnar_gate_prefix() -> Vec<Action> {
    vec![
        ms(60.0, "m0.1"),
        ms(120.0, "m0.2"),
        ms(180.0, "m1.1"),
        ms(240.0, "m1.3"),
        ms(300.0, "m2.1"),
        ms(360.0, "m2.3"),
        ms(420.0, "m3.3"),
    ]
}

fn run_ulnar(tr: &Trace) -> Debrief {
    let (proc, tp, phys) = load_ulnar();
    run_attempt(&proc, &tp, &phys, tr).unwrap()
}

#[test]
fn ulnar_divide_with_only_the_cutaneous_account_missing_fails_on_the_mabc() {
    let a = vec![
        ms(60.0, "m0.1"),
        ms(120.0, "m0.2"),
        ms(180.0, "m1.1"),
        // no m1.3: crit2 (the MABC account) never demonstrated
        ms(240.0, "m2.1"), // crit1
        ms(300.0, "m2.3"), // crit3
        ms(360.0, "m3.3"), // pause
        ms(420.0, "m5.1"), // divide Osborne's ligament
    ];
    let d = run_ulnar(&ulnar_trace("probe-ulnar-mabc", None, a));
    assert_eq!(d.verdict, "FAIL");
    assert!(d.errors.iter().any(|e| e.id == "err.mabc-unaccounted"));
    let inj = d
        .complications
        .iter()
        .find(|c| c.kind == "mabc-injury")
        .expect("the division resolves onto the unaccounted cutaneous nerve");
    assert_eq!(inj.resolved_structure.as_deref(), Some("nerve.medial-cutaneous-nerve-of-forearm"));
    assert_eq!(d.failed_at_s, Some(420.0));
}

#[test]
fn ulnar_divide_with_the_extent_unestablished_is_the_master_rule_not_the_mabc() {
    // crit1 and crit2 demonstrated, crit3 missing: the MABC
    // resolution requires crit2 to be the ONLY missing criterion,
    // so this division resolves onto the ulnar nerve itself.
    let a = vec![
        ms(60.0, "m0.1"),
        ms(120.0, "m0.2"),
        ms(180.0, "m1.1"),
        ms(240.0, "m1.3"), // crit2
        ms(300.0, "m2.1"), // crit1
        // no m2.3: crit3 (release extent) never established
        ms(360.0, "m3.3"),
        ms(420.0, "m4.1"), // divide the arcade of Struthers fascia
    ];
    let d = run_ulnar(&ulnar_trace("probe-ulnar-extent", None, a));
    assert_eq!(d.verdict, "FAIL");
    assert!(d.errors.iter().any(|e| e.id == "err.divide-unidentified"));
    assert!(!d.errors.iter().any(|e| e.id == "err.mabc-unaccounted"));
    let inj = d
        .complications
        .iter()
        .find(|c| c.kind == "ulnar-nerve-injury")
        .expect("the division resolves onto the ulnar nerve");
    assert_eq!(inj.resolved_structure.as_deref(), Some("major.ulnar"));
}

#[test]
fn ulnar_dp2_continue_dissection_scores_the_no_bailout_error() {
    let mut a = ulnar_gate_prefix();
    a.push(Action { id: Some("dp2".into()), choice: Some("continue-dissection".into()), ..act(480.0, "decision") });
    // Remove the gate's protection for the division that follows:
    // rebuild without crit1 so the division itself also fires.
    let mut b = vec![
        ms(60.0, "m0.1"),
        ms(120.0, "m0.2"),
        ms(180.0, "m1.1"),
        ms(240.0, "m1.3"),
        ms(300.0, "m2.3"),
        ms(360.0, "m3.3"),
    ];
    b.push(Action { id: Some("dp2".into()), choice: Some("continue-dissection".into()), ..act(420.0, "decision") });
    b.push(ms(480.0, "m5.1"));
    let _ = a;
    let d = run_ulnar(&ulnar_trace("probe-ulnar-nobailout", None, b));
    assert_eq!(d.verdict, "FAIL");
    assert!(d.errors.iter().any(|e| e.id == "err.no-bailout"), "dp2 arm fires: {:?}", d.errors);
    assert!(d.errors.iter().any(|e| e.id == "err.divide-unidentified"));
}

#[test]
fn ulnar_transposition_without_septum_release_computes_a_new_compression_site() {
    let mut a = ulnar_gate_prefix();
    a.push(ms(480.0, "m4.1"));
    a.push(ms(540.0, "m5.1"));
    a.push(ms(600.0, "m5.2"));
    a.push(ms(660.0, "m5.3"));
    a.push(ms(720.0, "m5.4"));
    a.push(ms(780.0, "m6.1"));
    a.push(Action { id: Some("dp5".into()), choice: Some("anterior-transposition".into()), ..act(840.0, "decision") });
    a.push(ms(900.0, "m6.3"));
    // no m6.4: the septum is left intact
    a.push(ms(960.0, "m6.5"));
    a.push(ms(1020.0, "m6.6"));
    let d = run_ulnar(&ulnar_trace("probe-ulnar-septum", Some("variant.subluxating-nerve"), a));
    assert_eq!(d.verdict, "PASS"); // a postoperative consequence, not a failed attempt
    assert!(d.errors.iter().any(|e| e.id == "err.new-compression-site"));
    let nc = d
        .complications
        .iter()
        .find(|c| c.kind == "new-compression")
        .expect("the intact septum computes the new compression site");
    assert_eq!(nc.resolved_structure.as_deref(), Some("ligament.medial-intermuscular-septum"));
    assert_eq!(d.checklist.required, 33, "the dp5 decision reconfigured the required set");
    assert!(d.checklist.missing.contains(&"m6.4".to_string()));
}

#[test]
fn ulnar_subluxating_nerve_without_a_dp5_decision_is_still_unaddressed() {
    // The instability rule keys on the absence of a transposition
    // decision, not on an explicit in-situ choice: a trace that
    // never takes dp5 at all leaves the unstable nerve in situ.
    let mut a = ulnar_gate_prefix();
    a.push(ms(480.0, "m4.1"));
    a.push(ms(540.0, "m5.1"));
    a.push(ms(600.0, "m5.2"));
    a.push(ms(660.0, "m5.3"));
    a.push(ms(720.0, "m5.4"));
    a.push(ms(780.0, "m6.1"));
    a.push(ms(840.0, "m6.2"));
    let d = run_ulnar(&ulnar_trace("probe-ulnar-nodecision", Some("variant.subluxating-nerve"), a));
    assert_eq!(d.verdict, "PASS");
    assert!(d.errors.iter().any(|e| e.id == "err.subluxation-unaddressed"));
    assert!(d.complications.iter().any(|c| c.kind == "nerve-instability"));
}

#[test]
fn ulnar_nerve_injury_managed_by_referral_without_repair_scores_no_control_point() {
    let a = vec![
        ms(60.0, "m0.1"),
        ms(120.0, "m0.2"),
        ms(180.0, "m1.1"),
        ms(240.0, "m5.1"), // divide before identification: the nerve is divided
        Action { complication: Some("ulnar-nerve-injury".into()), ..act(300.0, "recognise") },
        Action { id: Some("dp3".into()), choice: Some("repair-refer".into()), ..act(360.0, "decision") },
        // no m7.3 repair microstep: the plan is referral, control stays unearned
    ];
    let d = run_ulnar(&ulnar_trace("probe-ulnar-norepair", None, a));
    assert_eq!(d.verdict, "FAIL");
    let mg = d.management.as_ref().expect("management scored");
    assert_eq!(mg.recognised, 2);
    assert_eq!(mg.control, 0, "no repair performed, no control point");
    assert_eq!(mg.plan, 1, "immediate referral is a definitive plan");
    assert_eq!(mg.points, 4);
}

// ---------------------------------------------------------------------------
// Milestone 49: inguinal hernia repair probes — the computation
// rules the five shipped hernia traces do not exercise: the gate's
// three-way resolution and its priority order, the corona
// collateral bleed, the two gated-act departures inside the named
// triangles, the fixation judgment pair, the sliding variant's
// master-rule failure, and the dp2 no-bailout arm.
// ---------------------------------------------------------------------------

fn load_hernia() -> (Procedure, TheatreParams, PhysParams) {
    let r = root();
    let proc = Procedure::load(&r.join("procedures/proc.lap-inguinal-hernia.json")).unwrap();
    let tp = TheatreParams::load(&r.join("parameters.json")).unwrap();
    let phys = PhysParams::load().unwrap();
    (proc, tp, phys)
}

fn hernia_trace(id: &str, variant: Option<&str>, defect: Option<&str>, actions: Vec<Action>) -> Trace {
    Trace {
        id: id.into(),
        name: id.into(),
        procedure: Some("proc.lap-inguinal-hernia".into()),
        case: CaseSpec {
            variant: variant.map(|s| s.to_string()),
            defect: defect.map(|s| s.to_string()),
            ..Default::default()
        },
        expect_verdict: String::new(),
        actions,
    }
}

/// Planning, incision, then the three gate criteria and the pause:
/// m4.1 demonstrates crit1, m4.2 crit2, m4.3 crit3, m5.3 the pause.
fn hernia_gate_prefix() -> Vec<Action> {
    vec![
        ms(60.0, "m0.1"),
        ms(120.0, "m0.2"),
        ms(180.0, "m1.1"),
        ms(240.0, "m4.1"),
        ms(300.0, "m4.2"),
        ms(360.0, "m4.3"),
        ms(420.0, "m5.3"),
    ]
}

fn run_hernia(tr: &Trace) -> Debrief {
    let (proc, tp, phys) = load_hernia();
    run_attempt(&proc, &tp, &phys, tr).unwrap()
}

#[test]
fn hernia_divide_with_only_the_pain_account_missing_fails_on_the_nerves() {
    let a = vec![
        ms(60.0, "m0.1"),
        ms(120.0, "m0.2"),
        ms(180.0, "m1.1"),
        ms(240.0, "m4.1"), // crit1
        // no m4.2: crit2 (the pain account) never demonstrated
        ms(300.0, "m4.3"), // crit3
        ms(360.0, "m5.3"), // pause
        ms(420.0, "m6.1"), // divide the sac
    ];
    let d = run_hernia(&hernia_trace("probe-hernia-pain", None, None, a));
    assert_eq!(d.verdict, "FAIL");
    assert!(d.errors.iter().any(|e| e.id == "err.pain-triangle-injury"));
    let inj = d
        .complications
        .iter()
        .find(|c| c.kind == "nerve-injury")
        .expect("the division resolves onto the pain-triangle nerves");
    assert_eq!(inj.resolved_structure.as_deref(), Some("nerve.genitofemoral"));
    assert_eq!(d.failed_at_s, Some(420.0));
}

#[test]
fn hernia_divide_with_only_the_cord_account_missing_fails_on_the_vas() {
    let a = vec![
        ms(60.0, "m0.1"),
        ms(120.0, "m0.2"),
        ms(180.0, "m1.1"),
        ms(240.0, "m4.1"), // crit1
        ms(300.0, "m4.2"), // crit2
        // no m4.3: crit3 (the cord account) never demonstrated
        ms(360.0, "m5.3"),
        ms(420.0, "m6.1"),
    ];
    let d = run_hernia(&hernia_trace("probe-hernia-vas", None, None, a));
    assert_eq!(d.verdict, "FAIL");
    assert!(d.errors.iter().any(|e| e.id == "err.vas-injury"));
    let inj = d
        .complications
        .iter()
        .find(|c| c.kind == "vas-deferens-injury")
        .expect("the division resolves onto the deferent duct");
    assert_eq!(inj.resolved_structure.as_deref(), Some("repro.right-deferent-duct"));
}

#[test]
fn hernia_divide_with_doom_and_pain_missing_resolves_vascular_first() {
    // The gate's stated priority: crit1 unmet dominates — with the
    // doom and pain accounts both missing, the resolution is the
    // vascular injury, not the nerve injury.
    let a = vec![
        ms(60.0, "m0.1"),
        ms(120.0, "m0.2"),
        ms(180.0, "m1.1"),
        ms(240.0, "m4.3"), // crit3 only
        ms(300.0, "m5.3"),
        ms(360.0, "m6.1"),
    ];
    let d = run_hernia(&hernia_trace("probe-hernia-priority", None, None, a));
    assert_eq!(d.verdict, "FAIL");
    assert!(d.errors.iter().any(|e| e.id == "err.divide-unidentified"));
    assert!(!d.errors.iter().any(|e| e.id == "err.pain-triangle-injury"));
    assert!(d.complications.iter().any(|c| c.kind == "vascular-injury"));
    assert!(!d.complications.iter().any(|c| c.kind == "nerve-injury"));
}

#[test]
fn hernia_unprotected_corona_fixation_bleeds_engine_computed_volume() {
    let mut a = hernia_gate_prefix();
    a.push(ms(480.0, "m6.4")); // medial fixation, corona unprotected
    a.push(Action { structure: Some("artery.corona-mortis".into()), ..act(780.0, "control") });
    let d = run_hernia(&hernia_trace("probe-hernia-corona", Some("variant.corona-mortis"), None, a));
    assert_eq!(d.verdict, "PASS"); // collateral injury, not the master-rule fail
    assert!(d.errors.iter().any(|e| e.id == "err.corona-unprotected"));
    let h = d.complications.iter().find(|c| c.kind == "hemorrhage").expect("haemorrhage computed");
    assert_eq!(h.resolved_structure.as_deref(), Some("artery.corona-mortis"));
    // 300 s at the 1.2 mL/s placeholder rate = 360 mL, two ways.
    assert!((h.loss_ml.unwrap() - 360.0).abs() < 5.0, "event-integral loss {:?}", h.loss_ml);
    assert!((d.physiology.blood_loss_ml - 360.0).abs() < 5.0, "engine identity loss {}", d.physiology.blood_loss_ml);
}

#[test]
fn hernia_pain_zone_fixation_with_gate_met_is_a_major_departure_not_a_fail() {
    let mut a = hernia_gate_prefix();
    a.push(ms(480.0, "m6.7")); // prohibited placement, gate achieved
    let d = run_hernia(&hernia_trace("probe-hernia-painzone", None, None, a));
    assert_eq!(d.verdict, "PASS");
    assert!(d.errors.iter().any(|e| e.id == "err.fixation-in-pain-triangle"));
    let inj = d
        .complications
        .iter()
        .find(|c| c.kind == "nerve-injury")
        .expect("the placement computes the nerve injury");
    assert_eq!(inj.resolved_structure.as_deref(), Some("nerve.genitofemoral"));
}

#[test]
fn hernia_doom_zone_fixation_with_gate_met_bleeds_but_does_not_fail() {
    let mut a = hernia_gate_prefix();
    a.push(ms(480.0, "m6.8")); // prohibited placement, gate achieved
    a.push(Action { structure: Some("artery.right-external-iliac-artery".into()), ..act(780.0, "control") });
    let d = run_hernia(&hernia_trace("probe-hernia-doomzone", None, None, a));
    assert_eq!(d.verdict, "PASS");
    assert!(d.errors.iter().any(|e| e.id == "err.fixation-in-doom-triangle"));
    let h = d.complications.iter().find(|c| c.kind == "hemorrhage").expect("haemorrhage computed");
    assert_eq!(h.resolved_structure.as_deref(), Some("artery.right-external-iliac-artery"));
    // 300 s at the 5.0 mL/s placeholder rate = 1500 mL.
    assert!((h.loss_ml.unwrap() - 1500.0).abs() < 5.0);
}

#[test]
fn hernia_large_medial_defect_without_fixation_computes_recurrence() {
    let mut a = hernia_gate_prefix();
    a.push(ms(480.0, "m6.1"));
    a.push(ms(540.0, "m6.2"));
    a.push(ms(600.0, "m6.3"));
    a.push(Action { id: Some("dp5".into()), choice: Some("non-fixation".into()), ..act(660.0, "decision") });
    let d = run_hernia(&hernia_trace("probe-hernia-recurrence", None, Some("large-medial-m3"), a));
    assert_eq!(d.verdict, "PASS"); // a postoperative consequence, not a failed attempt
    assert!(d.errors.iter().any(|e| e.id == "err.no-fixation-large-defect"));
    let rec = d
        .complications
        .iter()
        .find(|c| c.kind == "recurrence")
        .expect("the unfixed large medial defect computes recurrence");
    assert_eq!(rec.resolved_structure.as_deref(), Some("sac.inguinal-hernia"));
}

#[test]
fn hernia_fixation_of_a_small_defect_is_scored_unnecessary() {
    let mut a = hernia_gate_prefix();
    a.push(ms(480.0, "m6.1"));
    a.push(ms(540.0, "m6.2"));
    a.push(ms(600.0, "m6.3"));
    a.push(Action { id: Some("dp5".into()), choice: Some("fixation".into()), ..act(660.0, "decision") });
    a.push(ms(720.0, "m6.4"));
    a.push(ms(780.0, "m6.5"));
    a.push(ms(840.0, "m6.6"));
    let d = run_hernia(&hernia_trace("probe-hernia-unnecessary", None, None, a));
    assert_eq!(d.verdict, "PASS");
    assert!(d.errors.iter().any(|e| e.id == "err.unnecessary-fixation"));
    assert!(d.complications.is_empty(), "a judgment error computes no complication");
    assert_eq!(d.checklist.required, 36, "the dp5 decision reconfigured the required set (33 + 3 fixation)");
}

#[test]
fn hernia_sliding_sac_divided_without_survey_fails_on_the_cecum() {
    let mut a = hernia_gate_prefix();
    a.push(ms(480.0, "m6.1")); // divide with no sliding survey (no m4.5)
    let d = run_hernia(&hernia_trace("probe-hernia-sliding", Some("variant.sliding-hernia"), None, a));
    assert_eq!(d.verdict, "FAIL");
    assert!(d.errors.iter().any(|e| e.id == "err.missed-variant"));
    let inj = d
        .complications
        .iter()
        .find(|c| c.kind == "visceral-injury")
        .expect("the division resolves onto the viscus forming the sac wall");
    assert_eq!(inj.resolved_structure.as_deref(), Some("canal.cecum"));
    assert_eq!(d.failed_at_s, Some(480.0));
}

#[test]
fn hernia_dp2_continue_dissection_scores_the_no_bailout_error() {
    let a = vec![
        ms(60.0, "m0.1"),
        ms(120.0, "m0.2"),
        ms(180.0, "m1.1"),
        ms(240.0, "m4.2"),
        ms(300.0, "m4.3"),
        ms(360.0, "m5.3"),
        Action { id: Some("dp2".into()), choice: Some("continue-dissection".into()), ..act(420.0, "decision") },
        ms(480.0, "m6.1"), // divide with crit1 still undemonstrated
    ];
    let d = run_hernia(&hernia_trace("probe-hernia-nobailout", None, None, a));
    assert_eq!(d.verdict, "FAIL");
    assert!(d.errors.iter().any(|e| e.id == "err.no-bailout"), "dp2 arm fires: {:?}", d.errors);
    assert!(d.errors.iter().any(|e| e.id == "err.divide-unidentified"));
}
