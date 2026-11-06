//! anatomica — native shell entry point.
//!
//!   anatomica verify [--data DIR] [--out DIR] [--size N]
//!       Headless: load + assert the packs, initialise wgpu on
//!       whatever adapter exists (software included), render the
//!       verification frames offscreen, check the silhouettes against
//!       CPU projections of the same data, exercise the pick path,
//!       and print the full report.
//!   anatomica view [--data DIR]
//!       Windowed orbit viewer (winit + wgpu surface). Needs a
//!       display; on a headless machine use `verify`.

use anatomica_native::camera::{project, OrbitCamera};
use anatomica_native::model::{LayerInfo, RecordRange, RecordsFile};
use anatomica_native::pack::Pack;
use anatomica_native::render::{
    non_background_fraction, silhouette_bbox, Gpu, LayerGpu, Renderer, SceneState,
};
use anatomica_native::{model, pack_manifest_report};
use glam::Vec3;
use std::collections::HashMap;
use std::path::PathBuf;
use std::process::ExitCode;

fn default_data_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../web/data")
}

fn arg_value(args: &[String], flag: &str) -> Option<String> {
    args.windows(2)
        .find(|w| w[0] == flag)
        .map(|w| w[1].clone())
}

struct BodyData {
    #[allow(dead_code)] // kept loaded for the shells that grow on this
    manifest: model::Manifest,
    records: RecordsFile,
    /// Layer descriptors in manifest order (all 11 systems).
    infos: Vec<LayerInfo>,
    ranges: HashMap<String, Vec<RecordRange>>,
}

/// Load manifest + records + packs and run the startup assertions
/// for every layer in the manifest. Returns Err only when a file
/// cannot be read/parsed at all; assertion failures are reported in
/// the returned lines and the caller decides (verify exits non-zero;
/// view refuses to start).
fn load_body(data_dir: &PathBuf) -> Result<(BodyData, Vec<(bool, String)>), String> {
    let manifest = model::load_manifest(&data_dir.join("manifest.json"))?;
    let records = model::load_records(&data_dir.join("records.json"))?;
    let infos = LayerInfo::from_manifest(&manifest);
    let mut ranges = HashMap::new();
    let mut report = Vec::new();
    // Packs are decoded one at a time for the startup assertions and
    // dropped — decoded packs are re-read on demand (GPU upload, CPU
    // reference projections) so resident memory stays bounded.
    for info in &infos {
        let layer = manifest
            .layers
            .get(&info.key)
            .ok_or_else(|| format!("manifest missing layer {}", info.key))?;
        let pack = Pack::load(&data_dir.join(&layer.file))
            .map_err(|e| format!("load {}: {e}", layer.file))?;
        report.extend(pack_manifest_report(&info.key, &pack, layer));
        ranges.insert(info.key.clone(), layer.ranges.clone());
    }
    Ok((
        BodyData {
            manifest,
            records,
            infos,
            ranges,
        },
        report,
    ))
}

/// Re-load one layer's pack from disk (GPU upload / CPU reference).
fn load_pack(data_dir: &PathBuf, body: &BodyData, key: &str) -> Result<Pack, String> {
    let layer = body
        .manifest
        .layers
        .get(key)
        .ok_or_else(|| format!("manifest missing layer {key}"))?;
    Pack::load(&data_dir.join(&layer.file)).map_err(|e| format!("load {}: {e}", layer.file))
}

fn print_report(report: &[(bool, String)]) -> bool {
    let mut all = true;
    for (ok, line) in report {
        println!("  [{}] {line}", if *ok { "PASS" } else { "FAIL" });
        all &= *ok;
    }
    all
}

/// CPU reference: project every vertex of `pack` with `mvp` and
/// return the pixel-space extent (min_x, min_y, max_x, max_y).
fn cpu_projected_extent(
    pack: &Pack,
    mvp: &glam::Mat4,
    width: u32,
    height: u32,
) -> (f32, f32, f32, f32) {
    let (mut mnx, mut mny) = (f32::INFINITY, f32::INFINITY);
    let (mut mxx, mut mxy) = (f32::NEG_INFINITY, f32::NEG_INFINITY);
    for p in &pack.positions {
        if let Some((x, y)) = project(mvp, Vec3::from_array(*p), width, height) {
            mnx = mnx.min(x);
            mxx = mxx.max(x);
            mny = mny.min(y);
            mxy = mxy.max(y);
        }
    }
    (mnx, mny, mxx, mxy)
}

/// Project the 8 corners of a bbox — the "assembled union bounds"
/// reference extent for a view.
fn cpu_box_extent(
    min: [f64; 3],
    max: [f64; 3],
    mvp: &glam::Mat4,
    width: u32,
    height: u32,
) -> (f32, f32, f32, f32) {
    let (mut mnx, mut mny) = (f32::INFINITY, f32::INFINITY);
    let (mut mxx, mut mxy) = (f32::NEG_INFINITY, f32::NEG_INFINITY);
    for &x in &[min[0], max[0]] {
        for &y in &[min[1], max[1]] {
            for &z in &[min[2], max[2]] {
                let p = Vec3::new(x as f32, y as f32, z as f32);
                if let Some((px, py)) = project(mvp, p, width, height) {
                    mnx = mnx.min(px);
                    mxx = mxx.max(px);
                    mny = mny.min(py);
                    mxy = mxy.max(py);
                }
            }
        }
    }
    (mnx, mny, mxx, mxy)
}

fn save_png(frame: &anatomica_native::render::FrameResult, path: &PathBuf) -> Result<(), String> {
    let img = image::RgbaImage::from_raw(frame.width, frame.height, frame.rgba.clone())
        .ok_or("frame buffer size mismatch")?;
    img.save(path).map_err(|e| format!("save {}: {e}", path.display()))
}

fn verify(args: &[String]) -> ExitCode {
    let data_dir = arg_value(args, "--data")
        .map(PathBuf::from)
        .unwrap_or_else(default_data_dir);
    let out_dir = arg_value(args, "--out")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("frames"));
    let size: u32 = arg_value(args, "--size")
        .and_then(|s| s.parse().ok())
        .unwrap_or(1024);
    println!("ANATOMICA native shell — headless verification");
    println!("data dir: {}", data_dir.display());
    println!("frame size: {size}x{size}");

    let (body, report) = match load_body(&data_dir) {
        Ok(v) => v,
        Err(e) => {
            println!("FATAL: {e}");
            return ExitCode::from(2);
        }
    };
    println!("\n== pack/manifest assertions ==");
    let packs_ok = print_report(&report);
    if !packs_ok {
        println!("pack assertions FAILED — refusing to render");
        return ExitCode::from(1);
    }

    let gpu = match pollster::block_on(Gpu::init()) {
        Ok(g) => g,
        Err(e) => {
            println!("\nGPU INITIALISATION FAILED: {e}");
            return ExitCode::from(2);
        }
    };
    println!("\nadapter: {}", gpu.info_string());

    let mut renderer = Renderer::new(gpu, wgpu::TextureFormat::Rgba8Unorm);
    let t0 = std::time::Instant::now();
    let mut layers: Vec<LayerGpu> = Vec::new();
    for info in &body.infos {
        let pack = load_pack(&data_dir, &body, &info.key).expect("pack reload for upload");
        layers.push(anatomica_native::render::upload_layer(
            &renderer.gpu.device,
            info.clone(),
            &pack,
        ));
    }
    println!(
        "GPU upload: {:.1} ms ({} layers)",
        t0.elapsed().as_secs_f64() * 1000.0,
        layers.len()
    );

    // Framing targets from records.json bboxes (canonical cm).
    let all_keys: Vec<&str> = body.infos.iter().map(|i| i.key.as_str()).collect();
    let combined = body
        .records
        .union_bbox(&["skeletal", "muscular"])
        .expect("combined union bbox");
    let skel_union = body
        .records
        .union_bbox(&["skeletal"])
        .expect("skeletal union bbox");
    let all_union = body
        .records
        .union_bbox(&all_keys)
        .expect("all-layers union bbox");
    let span = skel_union.span();
    println!(
        "skeletal union: min [{:.3}, {:.3}, {:.3}] max [{:.3}, {:.3}, {:.3}] span {:.3} x {:.3} x {:.3} cm",
        skel_union.min[0], skel_union.min[1], skel_union.min[2],
        skel_union.max[0], skel_union.max[1], skel_union.max[2],
        span[0], span[1], span[2]
    );
    let aspan = all_union.span();
    println!(
        "all-layers union: span {:.3} x {:.3} x {:.3} cm (the integumentary shell is the outermost layer)",
        aspan[0], aspan[1], aspan[2]
    );
    let target = Vec3::from_array(combined.centre().map(|v| v as f32));
    let target_all = Vec3::from_array(all_union.centre().map(|v| v as f32));
    let aspect = 1.0f32;

    let cam = |az: f32, pol: f32, radius: f32, tgt: Vec3| OrbitCamera {
        az,
        pol,
        radius,
        target: tgt,
    };
    let front = cam(0.0, std::f32::consts::FRAC_PI_2, 300.0, target);
    let side = cam(std::f32::consts::FRAC_PI_2, std::f32::consts::FRAC_PI_2, 300.0, target);
    let top = cam(0.0, 0.0, 300.0, target);
    let front_all = cam(0.0, std::f32::consts::FRAC_PI_2, 310.0, target_all);
    let frontal = body.records.by_id("frontal").expect("frontal record");
    let frontal_centre = Vec3::from_array(frontal.bbox().unwrap().centre().map(|v| v as f32));
    let close = cam(0.35, 1.15, 42.0, frontal_centre);

    let skel_only = SceneState::only(&["skeletal"]);
    let both_state = SceneState::only(&["skeletal", "muscular"]);
    let all_state = SceneState::all(&body.infos);
    let skin_state = SceneState::only(&["integumentary"]);
    let mut focus_state = SceneState::all(&body.infos);
    focus_state.focus = Some(["cardiovascular", "nervous"].iter().map(|s| s.to_string()).collect());
    focus_state.dim = 0.78;
    // Milestone 21: the same focus view with the integumentary
    // shell genuinely translucent (per-layer opacity) instead of
    // merely dimmed — the Milestone-16 defect-1 comparison frame.
    let mut glass_state = focus_state.clone();
    glass_state.opacity.insert("integumentary".to_string(), 0.15);
    let cvn_only_state = SceneState::only(&["cardiovascular", "nervous"]);
    let femur_range = body.ranges["skeletal"]
        .iter()
        .find(|r| r.record_id == "femur_right")
        .expect("femur_right range")
        .clone();
    let mut selection_state = SceneState::only(&["skeletal"]);
    selection_state.selected = Some(("skeletal".to_string(), femur_range.slot));

    std::fs::create_dir_all(&out_dir).ok();
    println!("\n== frames ==");
    let mut hard_fail = false;
    // Framebuffers kept for the Milestone-21 translucency proof.
    let mut captured: HashMap<&str, Vec<u8>> = HashMap::new();
    // (name, camera, up, state, silhouette-check layer keys)
    let jobs: Vec<(&str, OrbitCamera, Option<Vec3>, SceneState, Option<Vec<&str>>)> = vec![
        ("front_skeleton", front, None, skel_only.clone(), Some(vec!["skeletal"])),
        ("side_skeleton", side, None, skel_only.clone(), Some(vec!["skeletal"])),
        ("top_skeleton", top, Some(Vec3::new(0.0, 0.0, -1.0)), skel_only.clone(), Some(vec!["skeletal"])),
        ("close_skull", close, None, skel_only.clone(), None),
        ("front_combined", front, None, both_state.clone(), None),
        ("front_selection", front, None, selection_state.clone(), None),
        ("front_all_layers", front_all, None, all_state.clone(), Some(all_keys.clone())),
        ("front_cv_nervous_focus", front_all, None, focus_state.clone(), None),
        ("front_cv_nervous_glass", front_all, None, glass_state.clone(), None),
        ("front_cv_nervous", front_all, None, cvn_only_state.clone(), None),
        ("front_skin", front_all, None, skin_state.clone(), Some(vec!["integumentary"])),
    ];
    for (name, camera, up, state, check_keys) in &jobs {
        let (mvp, mv) = match up {
            Some(u) => (
                camera.mvp_with_up(aspect, *u),
                camera.view_with_up(*u),
            ),
            None => (camera.mvp(aspect), camera.view()),
        };
        let frame = renderer.render_offscreen(&layers, size, size, &mvp, &mv, state);
        if *name == "front_cv_nervous_focus" || *name == "front_cv_nervous_glass" {
            captured.insert(name, frame.rgba.clone());
        }
        let path = out_dir.join(format!("{name}.png"));
        if let Err(e) = save_png(&frame, &path) {
            println!("{name}: PNG save failed: {e}");
            hard_fail = true;
            continue;
        }
        let frac = non_background_fraction(&frame.rgba);
        println!(
            "{name}: render {:.1} ms, readback {:.1} ms, non-background {:.4} -> {}",
            frame.render_ms,
            frame.readback_ms,
            frac,
            path.display()
        );
        if let Some(keys) = check_keys {
            let gpu_box = silhouette_bbox(&frame.rgba, size, size);
            // CPU reference: project every vertex of every checked
            // layer's pack (packs loaded one at a time).
            let (mut mnx, mut mny) = (f32::INFINITY, f32::INFINITY);
            let (mut mxx, mut mxy) = (f32::NEG_INFINITY, f32::NEG_INFINITY);
            for key in keys {
                let pack = load_pack(&data_dir, &body, key).expect("pack reload for CPU reference");
                let e = cpu_projected_extent(&pack, &mvp, size, size);
                mnx = mnx.min(e.0); mny = mny.min(e.1);
                mxx = mxx.max(e.2); mxy = mxy.max(e.3);
            }
            let vtx = (mnx, mny, mxx, mxy);
            let ub = body.records.union_bbox(keys).expect("union bbox for check");
            let ubox = cpu_box_extent(ub.min, ub.max, &mvp, size, size);
            match gpu_box {
                Some((gx0, gy0, gx1, gy1)) => {
                    let diffs = [
                        (gx0 as f32 - vtx.0).abs(),
                        (gy0 as f32 - vtx.1).abs(),
                        (gx1 as f32 - vtx.2).abs(),
                        (gy1 as f32 - vtx.3).abs(),
                    ];
                    let worst = diffs.iter().cloned().fold(0.0f32, f32::max);
                    let pass = worst <= 2.0;
                    hard_fail |= !pass;
                    println!(
                        "  silhouette gpu x[{gx0}..{gx1}] y[{gy0}..{gy1}]; cpu-vertices x[{:.1}..{:.1}] y[{:.1}..{:.1}]; union-box x[{:.1}..{:.1}] y[{:.1}..{:.1}]; worst |gpu-cpu| {worst:.2} px [{}]",
                        vtx.0, vtx.2, vtx.1, vtx.3, ubox.0, ubox.2, ubox.1, ubox.3,
                        if pass { "PASS" } else { "FAIL" }
                    );
                }
                None => {
                    println!("  silhouette: EMPTY FRAME [FAIL]");
                    hard_fail = true;
                }
            }
        }
    }

    // Milestone 21 translucency proof: in the opaque focus frame
    // (Milestone 16) the heart's and brain's projected regions show
    // only the opaque dimmed skin shell — every lit pixel there has
    // the skin family's channel ratios (g/r 0.70, b/r 0.51, from the
    // manifest colour 0.88/0.62/0.45; dimming scales all channels
    // together, so ratios survive it). Two measurements:
    //  (a) skin-dominated fraction of the heart's region: a pixel is
    //      skin-dominated when both ratios sit within +/-0.06 of
    //      the skin family's. Through a translucent shell the
    //      interior (muscle g/r 0.40, cardiovascular 0.20) pulls the
    //      composite ratios measurably off the skin point, so the
    //      fraction must fall.
    //  (b) nervous-ratio pixels in the brain's region (yellow
    //      family: g > 0.70 r and b < 0.48 r — skin fails on b/r,
    //      bone on b/r 0.77): the count must rise.
    println!("\n== translucency proof (Milestone 21) ==");
    {
        let focus_rgba = &captured["front_cv_nervous_focus"];
        let glass_rgba = &captured["front_cv_nervous_glass"];
        let mvp_fa = front_all.mvp(aspect);
        // (skin-dominated fraction, nervous-ratio count, lit pixels)
        let region_stats = |rgba: &[u8], min: [f64; 3], max: [f64; 3]| -> (f64, usize, usize) {
            let (x0, y0, x1, y1) = cpu_box_extent(min, max, &mvp_fa, size, size);
            let xa = (x0.max(0.0) as u32).min(size - 1);
            let xb = (x1.max(0.0) as u32).min(size - 1);
            let ya = (y0.max(0.0) as u32).min(size - 1);
            let yb = (y1.max(0.0) as u32).min(size - 1);
            let (mut skin, mut nerv, mut lit) = (0usize, 0usize, 0usize);
            for y in ya..=yb {
                for x in xa..=xb {
                    let i = ((y * size + x) * 4) as usize;
                    let (r, g, b) = (rgba[i] as f32, rgba[i + 1] as f32, rgba[i + 2] as f32);
                    if r <= 25.0 {
                        continue; // background / near-black: no family signal
                    }
                    lit += 1;
                    if (g / r - 0.7045).abs() < 0.06 && (b / r - 0.5114).abs() < 0.06 {
                        skin += 1;
                    }
                    if g > 0.70 * r && b < 0.48 * r {
                        nerv += 1;
                    }
                }
            }
            (
                if lit > 0 { skin as f64 / lit as f64 } else { 0.0 },
                nerv,
                lit,
            )
        };
        let heart_rec = body.records.by_id("heart").expect("heart record");
        let hb = heart_rec.bbox().unwrap();
        let brain_rec = body.records.by_id("brain").expect("brain record");
        let bb = brain_rec.bbox().unwrap();
        let (hf_skin, _, hf_lit) = region_stats(focus_rgba, hb.min, hb.max);
        let (hg_skin, _, hg_lit) = region_stats(glass_rgba, hb.min, hb.max);
        let (_, bf_nerv, _) = region_stats(focus_rgba, bb.min, bb.max);
        let (_, bg_nerv, _) = region_stats(glass_rgba, bb.min, bb.max);
        println!(
            "heart region: skin-dominated fraction of {hf_lit}/{hg_lit} lit px: opaque focus {hf_skin:.3} -> glass shell {hg_skin:.3}"
        );
        println!("brain region, nervous-ratio pixels: opaque focus {bf_nerv} -> glass shell {bg_nerv}");
        let heart_pass = hg_skin < hf_skin - 0.10;
        let brain_pass = bg_nerv > bf_nerv;
        hard_fail |= !heart_pass || !brain_pass;
        println!(
            "[{}] interior reads through the translucent shell (heart skin-dominated fraction falls > 0.10; brain nervous pixels increase)",
            if heart_pass && brain_pass { "PASS" } else { "FAIL" }
        );
    }

    println!("\n== picking ==");
    let mvp = front.mvp(aspect);
    let mvp_all = front_all.mvp(aspect);
    let probe = |renderer: &mut Renderer,
                 label: &str,
                 mvp: &glam::Mat4,
                 state: &SceneState,
                 centre: Vec3|
     -> Option<(String, u32)> {
        let (px, py) = project(mvp, centre, size, size)
            .map(|(x, y)| (x as u32, y as u32))
            .unwrap_or((4, 4));
        let hit = renderer.pick(&layers, &body.ranges, size, size, mvp, state, None, px, py);
        match &hit {
            Some((key, slot)) => {
                let rec = body.records.by_slot(key, *slot);
                println!(
                    "{label} @({px},{py}): {key} slot {slot} — {}",
                    rec.map(|r| r.name()).unwrap_or("<unresolved>")
                );
            }
            None => println!("{label} @({px},{py}): no hit"),
        }
        hit
    };
    // Skeletal + muscular visible (the Milestone-7 probe setup).
    let forehead = probe(&mut renderer, "forehead probe, skeletal+muscular (frontal bbox centre)", &mvp, &both_state, frontal_centre);
    let femur = body.records.by_id("femur_right").unwrap();
    let femur_centre = Vec3::from_array(femur.bbox().unwrap().centre().map(|v| v as f32));
    let _thigh = probe(&mut renderer, "thigh probe, skeletal+muscular (femur_right bbox centre)", &mvp, &both_state, femur_centre);
    // All layers visible: the integumentary shell covers the forehead.
    let skin_probe = probe(&mut renderer, "forehead probe, all layers", &mvp_all, &all_state, frontal_centre);
    // Cardiovascular + nervous only: the heart's own centre.
    let heart = body.records.by_id("heart").expect("heart record");
    let heart_centre = Vec3::from_array(heart.bbox().unwrap().centre().map(|v| v as f32));
    let cvn_state = SceneState::only(&["cardiovascular", "nervous"]);
    let _heart = probe(&mut renderer, "heart probe, cardiovascular+nervous (heart bbox centre)", &mvp_all, &cvn_state, heart_centre);
    // Milestone 21: opacity must not corrupt picking. The pick pass
    // renders ids, not colours, and never reads the opacity map —
    // the same pixels probed through the translucent shell must
    // return the same records as through the opaque shell.
    let forehead_glass = probe(&mut renderer, "forehead probe, glass focus state (shell translucent)", &mvp_all, &glass_state, frontal_centre);
    let heart_all = probe(&mut renderer, "heart-centre probe, all layers", &mvp_all, &all_state, heart_centre);
    let heart_glass = probe(&mut renderer, "heart-centre probe, glass focus state (shell translucent)", &mvp_all, &glass_state, heart_centre);
    let pick_opacity_ok = forehead_glass == skin_probe
        && skin_probe == Some(("integumentary".to_string(), 0))
        && heart_glass == heart_all;
    hard_fail |= !pick_opacity_ok;
    println!(
        "[{}] pick invariance under opacity: glass-shell probes == opaque-shell probes at the same pixels (forehead {:?}, heart-centre {:?})",
        if pick_opacity_ok { "PASS" } else { "FAIL" },
        forehead_glass, heart_glass
    );
    let bg = renderer.pick(&layers, &body.ranges, size, size, &mvp, &both_state, None, 4, 4);
    println!("corner probe @(4,4): {:?}", bg);
    if bg.is_some() {
        println!("  [FAIL] corner probe should be background");
        hard_fail = true;
    }
    // Self-consistency: re-render the id pass with only the picked
    // record's range; the same pixel must return the same id.
    if let Some((key, slot)) = forehead {
        let range = body.ranges[&key]
            .iter()
            .find(|r| r.slot == slot)
            .cloned()
            .expect("picked slot has a range");
        let (px, py) = project(&mvp, frontal_centre, size, size)
            .map(|(x, y)| (x as u32, y as u32))
            .unwrap();
        let again = renderer.pick(
            &layers,
            &body.ranges,
            size,
            size,
            &mvp,
            &both_state,
            Some((key.as_str(), &range)),
            px,
            py,
        );
        let pass = again == Some((key.clone(), slot));
        hard_fail |= !pass;
        println!(
            "pick self-consistency ({key} slot {slot}, range-restricted re-render): {:?} [{}]",
            again,
            if pass { "PASS" } else { "FAIL" }
        );
        if let Some(rec) = body.records.by_slot(&key, slot) {
            println!("\n-- record panel (picked) --");
            print!("{}", model::panel_text(&body.records, &body.infos, rec));
        }
    }
    if let Some(rec) = body.records.by_id("femur_right") {
        println!("\n-- record panel (selection frame subject) --");
        print!("{}", model::panel_text(&body.records, &body.infos, rec));
    }
    if let Some(rec) = body.records.by_id("heart") {
        println!("\n-- record panel (heart) --");
        print!("{}", model::panel_text(&body.records, &body.infos, rec));
    }

    println!(
        "\nverify: {}",
        if hard_fail { "FAILURES PRESENT" } else { "ALL HARD CHECKS PASS" }
    );
    if hard_fail {
        ExitCode::from(1)
    } else {
        ExitCode::SUCCESS
    }
}

fn main() -> ExitCode {
    env_logger::init();
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.first().map(|s| s.as_str()) {
        Some("view") => view(&args[1..]),
        Some("verify") => verify(&args[1..]),
        _ => verify(&args),
    }
}

// ---------------------------------------------------------------------------
// Windowed viewer: same draw code, surface target. Mouse orbit /
// wheel zoom / right-drag pan; keys: S skeletal, M muscular,
// 1..9/0 toggle layers 1..10 in manifest order, I integumentary,
// A all layers on, G glass shell (integumentary opacity 0.15,
// Milestone 21), W wireframe, R reset view; left click picks
// (panel text to console, record highlighted). Not runnable on a
// headless machine.
// ---------------------------------------------------------------------------

#[cfg(not(target_arch = "wasm32"))]
fn view(args: &[String]) -> ExitCode {
    use std::sync::Arc;
    use winit::application::ApplicationHandler;
    use winit::event::{ElementState, MouseButton, WindowEvent};
    use winit::event_loop::{ActiveEventLoop, EventLoop};
    use winit::keyboard::{Key, NamedKey};
    use winit::window::{Window, WindowId};

    let data_dir = arg_value(args, "--data")
        .map(PathBuf::from)
        .unwrap_or_else(default_data_dir);
    let (body, report) = match load_body(&data_dir) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("FATAL: {e}");
            return ExitCode::from(2);
        }
    };
    if !print_report(&report) {
        eprintln!("pack assertions FAILED — refusing to start");
        return ExitCode::from(1);
    }
    let combined = body
        .records
        .union_bbox(&["skeletal", "muscular"])
        .expect("combined union bbox");
    let home_target = Vec3::from_array(combined.centre().map(|v| v as f32));

    struct App {
        body: BodyData,
        data_dir: PathBuf,
        home_target: Vec3,
        cam: OrbitCamera,
        state: SceneState,
        window: Option<Arc<Window>>,
        surface: Option<wgpu::Surface<'static>>,
        surface_format: wgpu::TextureFormat,
        renderer: Option<Renderer>,
        layers: Vec<LayerGpu>,
        depth: Option<anatomica_native::render::OffscreenTarget>,
        size: (u32, u32),
        left_down: bool,
        right_down: bool,
        last: (f64, f64),
        press: (f64, f64),
        dragged: bool,
    }

    impl ApplicationHandler for App {
        fn resumed(&mut self, event_loop: &ActiveEventLoop) {
            if self.window.is_some() {
                return;
            }
            let window = Arc::new(
                event_loop
                    .create_window(
                        Window::default_attributes()
                            .with_title("ANATOMICA — native shell")
                            .with_inner_size(winit::dpi::LogicalSize::new(1280.0, 900.0)),
                    )
                    .expect("create window"),
            );
            let gpu = pollster::block_on(Gpu::init()).expect("gpu init");
            let surface = gpu
                .instance
                .create_surface(window.clone())
                .expect("create surface");
            let size = window.inner_size();
            let caps = surface.get_capabilities(&gpu.adapter);
            // Prefer a non-sRGB format so the surface shows the same
            // raw shading values as the offscreen path (as the web
            // shell's canvas does); fall back to the first offered.
            let format = caps
                .formats
                .iter()
                .copied()
                .find(|f| !f.is_srgb())
                .unwrap_or(caps.formats[0]);
            let config = wgpu::SurfaceConfiguration {
                usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
                format,
                width: size.width.max(1),
                height: size.height.max(1),
                present_mode: wgpu::PresentMode::Fifo,
                desired_maximum_frame_latency: 2,
                alpha_mode: caps.alpha_modes[0],
                view_formats: vec![],
            };
            surface.configure(&gpu.device, &config);
            self.surface_format = format;
            let mut layers: Vec<LayerGpu> = Vec::new();
            for info in &self.body.infos {
                let pack = load_pack(&self.data_dir, &self.body, &info.key)
                    .expect("pack reload for upload");
                layers.push(anatomica_native::render::upload_layer(
                    &gpu.device,
                    info.clone(),
                    &pack,
                ));
            }
            self.renderer = Some(Renderer::new(gpu, format));
            self.layers = layers;
            // Only the depth view of this target is used; its colour
            // texture is a placeholder in a neutral format.
            self.depth = Some(anatomica_native::render::make_target(
                &self.renderer.as_ref().unwrap().gpu.device,
                config.width,
                config.height,
                wgpu::TextureFormat::Rgba8Unorm,
                "view depth-holder",
            ));
            self.surface = Some(surface);
            self.window = Some(window);
            self.size = (config.width, config.height);
        }

        fn window_event(
            &mut self,
            event_loop: &ActiveEventLoop,
            _id: WindowId,
            event: WindowEvent,
        ) {
            let window = match &self.window {
                Some(w) => w.clone(),
                None => return,
            };
            match event {
                WindowEvent::CloseRequested => event_loop.exit(),
                WindowEvent::Resized(new_size) => {
                    let (w, h) = (new_size.width.max(1), new_size.height.max(1));
                    self.size = (w, h);
                    if let (Some(surface), Some(renderer)) = (&self.surface, &self.renderer) {
                        let caps = surface.get_capabilities(&renderer.gpu.adapter);
                        surface.configure(
                            &renderer.gpu.device,
                            &wgpu::SurfaceConfiguration {
                                usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
                                format: self.surface_format,
                                width: w,
                                height: h,
                                present_mode: wgpu::PresentMode::Fifo,
                                desired_maximum_frame_latency: 2,
                                alpha_mode: caps.alpha_modes[0],
                                view_formats: vec![],
                            },
                        );
                        self.depth = Some(anatomica_native::render::make_target(
                            &renderer.gpu.device,
                            w,
                            h,
                            wgpu::TextureFormat::Rgba8Unorm,
                            "view depth-holder",
                        ));
                    }
                    window.request_redraw();
                }
                WindowEvent::MouseInput { state, button, .. } => {
                    let pressed = state == ElementState::Pressed;
                    match button {
                        MouseButton::Left => {
                            if pressed {
                                self.left_down = true;
                                self.press = self.last;
                                self.dragged = false;
                            } else {
                                self.left_down = false;
                                if !self.dragged {
                                    self.click_pick();
                                }
                            }
                        }
                        MouseButton::Right => self.right_down = pressed,
                        _ => {}
                    }
                    window.request_redraw();
                }
                WindowEvent::CursorMoved { position, .. } => {
                    let (x, y) = (position.x, position.y);
                    let (dx, dy) = (x - self.last.0, y - self.last.1);
                    self.last = (x, y);
                    if self.left_down {
                        if (x - self.press.0).abs() + (y - self.press.1).abs() > 4.0 {
                            self.dragged = true;
                        }
                        self.cam.az -= (dx * 0.005) as f32;
                        self.cam.pol = (self.cam.pol - (dy * 0.005) as f32)
                            .clamp(0.05, std::f32::consts::PI - 0.05);
                        window.request_redraw();
                    } else if self.right_down {
                        let eye = self.cam.eye();
                        let fwd = (self.cam.target - eye).normalize();
                        let right = fwd.cross(Vec3::Y).normalize_or_zero();
                        let up = right.cross(fwd);
                        let s = self.cam.radius * 0.0016;
                        self.cam.target += (-(dx as f32) * right + (dy as f32) * up) * s;
                        window.request_redraw();
                    }
                }
                WindowEvent::MouseWheel { delta, .. } => {
                    let lines = match delta {
                        winit::event::MouseScrollDelta::LineDelta(_, y) => y,
                        winit::event::MouseScrollDelta::PixelDelta(p) => (p.y / 40.0) as f32,
                    };
                    self.cam.radius =
                        (self.cam.radius * (-lines * 0.12).exp()).clamp(12.0, 900.0);
                    window.request_redraw();
                }
                WindowEvent::KeyboardInput { event: key, .. } => {
                    if key.state == ElementState::Pressed {
                        match &key.logical_key {
                            Key::Named(NamedKey::Escape) => event_loop.exit(),
                            Key::Character(c) => match c.to_lowercase().as_str() {
                                "s" => self.toggle_layer("skeletal"),
                                "m" => self.toggle_layer("muscular"),
                                "i" => self.toggle_layer("integumentary"),
                                "a" => {
                                    self.state.visible =
                                        self.body.infos.iter().map(|l| l.key.clone()).collect();
                                }
                                "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "0" => {
                                    let n: usize = c.parse().unwrap();
                                    let idx = if n == 0 { 9 } else { n - 1 };
                                    if let Some(info) = self.body.infos.get(idx) {
                                        let key = info.key.clone();
                                        self.toggle_layer(&key);
                                    }
                                }
                                "g" => {
                                    // Glass shell: toggle the
                                    // integumentary layer between
                                    // opaque and translucent.
                                    if self.state.opacity.remove("integumentary").is_none() {
                                        self.state
                                            .opacity
                                            .insert("integumentary".to_string(), 0.15);
                                    }
                                }
                                "w" => self.state.wireframe = !self.state.wireframe,
                                "r" => {
                                    self.cam = OrbitCamera::new(self.home_target);
                                    self.state.selected = None;
                                }
                                _ => {}
                            },
                            _ => {}
                        }
                    }
                    window.request_redraw();
                }
                WindowEvent::RedrawRequested => self.draw(),
                _ => {}
            }
        }
    }

    impl App {
        fn toggle_layer(&mut self, key: &str) {
            if !self.state.visible.remove(key) {
                self.state.visible.insert(key.to_string());
            }
        }

        fn click_pick(&mut self) {
            let renderer = match &mut self.renderer {
                Some(r) => r,
                None => return,
            };
            let (w, h) = self.size;
            let aspect = w as f32 / h as f32;
            let mvp = self.cam.mvp(aspect);
            let hit = renderer.pick(
                &self.layers,
                &self.body.ranges,
                w,
                h,
                &mvp,
                &self.state,
                None,
                self.last.0 as u32,
                self.last.1 as u32,
            );
            match hit {
                Some((key, slot)) => {
                    self.state.selected = Some((key.clone(), slot));
                    if let Some(rec) = self.body.records.by_slot(&key, slot) {
                        print!("{}", model::panel_text(&self.body.records, &self.body.infos, rec));
                    }
                }
                None => self.state.selected = None,
            }
        }

        fn draw(&mut self) {
            let (surface, renderer) = match (&self.surface, &mut self.renderer) {
                (Some(s), Some(r)) => (s, r),
                _ => return,
            };
            let frame = match surface.get_current_texture() {
                Ok(f) => f,
                Err(_) => return,
            };
            let view = frame
                .texture
                .create_view(&wgpu::TextureViewDescriptor::default());
            let (w, h) = self.size;
            let aspect = w as f32 / h as f32;
            let mvp = self.cam.mvp(aspect);
            let mv = self.cam.view();
            let depth = self.depth.as_ref().unwrap();
            let mut encoder =
                renderer
                    .gpu
                    .device
                    .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                        label: Some("view frame"),
                    });
            {
                let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                    label: Some("view pass"),
                    color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                        view: &view,
                        depth_slice: None,
                        resolve_target: None,
                        ops: wgpu::Operations {
                            load: wgpu::LoadOp::Clear(anatomica_native::render::BACKGROUND),
                            store: wgpu::StoreOp::Store,
                        },
                    })],
                    depth_stencil_attachment: Some(
                        wgpu::RenderPassDepthStencilAttachment {
                            view: &depth.depth_view,
                            depth_ops: Some(wgpu::Operations {
                                load: wgpu::LoadOp::Clear(1.0),
                                store: wgpu::StoreOp::Store,
                            }),
                            stencil_ops: None,
                        },
                    ),
                    timestamp_writes: None,
                    occlusion_query_set: None,
                });
                renderer.draw_shaded(&mut pass, &self.layers, &mvp, &mv, &self.state);
            }
            renderer.gpu.queue.submit([encoder.finish()]);
            frame.present();
        }
    }

    let initial_state = SceneState::all(&body.infos);
    let mut app = App {
        body,
        data_dir,
        home_target,
        cam: OrbitCamera::new(home_target),
        state: initial_state,
        window: None,
        surface: None,
        surface_format: wgpu::TextureFormat::Rgba8Unorm,
        renderer: None,
        layers: Vec::new(),
        depth: None,
        size: (1, 1),
        left_down: false,
        right_down: false,
        last: (0.0, 0.0),
        press: (0.0, 0.0),
        dragged: false,
    };
    let event_loop = EventLoop::new().expect("event loop");
    event_loop.run_app(&mut app).expect("run app");
    ExitCode::SUCCESS
}
