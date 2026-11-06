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
use anatomica_native::model::{LayerKind, RecordRange, RecordsFile};
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
    packs: HashMap<LayerKind, Pack>,
    ranges: HashMap<LayerKind, Vec<RecordRange>>,
}

/// Load manifest + records + packs and run the startup assertions.
/// Returns Err only when a file cannot be read/parsed at all;
/// assertion failures are reported in the returned lines and the
/// caller decides (verify exits non-zero; view refuses to start).
fn load_body(data_dir: &PathBuf) -> Result<(BodyData, Vec<(bool, String)>), String> {
    let manifest = model::load_manifest(&data_dir.join("manifest.json"))?;
    let records = model::load_records(&data_dir.join("records.json"))?;
    let mut packs = HashMap::new();
    let mut ranges = HashMap::new();
    let mut report = Vec::new();
    for kind in LayerKind::ALL {
        let layer = manifest
            .layers
            .get(kind.manifest_key())
            .ok_or_else(|| format!("manifest missing layer {}", kind.manifest_key()))?;
        let pack = Pack::load(&data_dir.join(&layer.file))
            .map_err(|e| format!("load {}: {e}", layer.file))?;
        report.extend(pack_manifest_report(kind, &pack, layer));
        ranges.insert(kind, layer.ranges.clone());
        packs.insert(kind, pack);
    }
    Ok((
        BodyData {
            manifest,
            records,
            packs,
            ranges,
        },
        report,
    ))
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
    let layers: Vec<LayerGpu> = LayerKind::ALL
        .iter()
        .map(|&kind| {
            anatomica_native::render::upload_layer(
                &renderer.gpu.device,
                kind,
                &body.packs[&kind],
            )
        })
        .collect();
    println!(
        "GPU upload: {:.1} ms ({} layers)",
        t0.elapsed().as_secs_f64() * 1000.0,
        layers.len()
    );

    // Framing targets from records.json bboxes (canonical cm).
    let combined = body
        .records
        .union_bbox(&[LayerKind::Skeleton, LayerKind::Muscle])
        .expect("combined union bbox");
    let skel_union = body
        .records
        .union_bbox(&[LayerKind::Skeleton])
        .expect("skeletal union bbox");
    let span = skel_union.span();
    println!(
        "skeletal union: min [{:.3}, {:.3}, {:.3}] max [{:.3}, {:.3}, {:.3}] span {:.3} x {:.3} x {:.3} cm",
        skel_union.min[0], skel_union.min[1], skel_union.min[2],
        skel_union.max[0], skel_union.max[1], skel_union.max[2],
        span[0], span[1], span[2]
    );
    let target = Vec3::from_array(combined.centre().map(|v| v as f32));
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
    let frontal = body.records.by_id("frontal").expect("frontal record");
    let frontal_centre = Vec3::from_array(frontal.bbox().unwrap().centre().map(|v| v as f32));
    let close = cam(0.35, 1.15, 42.0, frontal_centre);

    let skel_only = SceneState {
        show_muscles: false,
        ..Default::default()
    };
    let femur_range = body.ranges[&LayerKind::Skeleton]
        .iter()
        .find(|r| r.record_id == "femur_right")
        .expect("femur_right range")
        .clone();
    let selection_state = SceneState {
        show_muscles: false,
        selected: Some((LayerKind::Skeleton, femur_range.slot)),
        ..Default::default()
    };

    std::fs::create_dir_all(&out_dir).ok();
    println!("\n== frames ==");
    let mut hard_fail = false;
    let both_state = SceneState::default();
    let jobs: Vec<(&str, OrbitCamera, Option<Vec3>, &SceneState, bool)> = vec![
        ("front_skeleton", front, None, &skel_only, true),
        ("side_skeleton", side, None, &skel_only, true),
        ("top_skeleton", top, Some(Vec3::new(0.0, 0.0, -1.0)), &skel_only, true),
        ("close_skull", close, None, &skel_only, false),
        ("front_combined", front, None, &both_state, false),
        ("front_selection", front, None, &selection_state, false),
    ];
    for (name, camera, up, state, check) in &jobs {
        let (mvp, mv) = match up {
            Some(u) => (
                camera.mvp_with_up(aspect, *u),
                camera.view_with_up(*u),
            ),
            None => (camera.mvp(aspect), camera.view()),
        };
        let frame = renderer.render_offscreen(&layers, size, size, &mvp, &mv, state);
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
        if *check {
            let gpu_box = silhouette_bbox(&frame.rgba, size, size);
            let vtx = cpu_projected_extent(&body.packs[&LayerKind::Skeleton], &mvp, size, size);
            let ubox = cpu_box_extent(skel_union.min, skel_union.max, &mvp, size, size);
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

    println!("\n== picking (front view, both layers) ==");
    let mvp = front.mvp(aspect);
    let state = SceneState::default();
    let probe = |renderer: &mut Renderer,
                 label: &str,
                 centre: Vec3,
                 expect_none: bool|
     -> Option<(LayerKind, u32)> {
        let (px, py) = project(&mvp, centre, size, size)
            .map(|(x, y)| (x as u32, y as u32))
            .unwrap_or((4, 4));
        let hit = renderer.pick(&layers, &body.ranges, size, size, &mvp, &state, None, px, py);
        match hit {
            Some((kind, slot)) => {
                let rec = body.records.by_slot(kind, slot);
                println!(
                    "{label} @({px},{py}): {} slot {slot} — {}",
                    kind.manifest_key(),
                    rec.map(|r| r.name()).unwrap_or("<unresolved>")
                );
            }
            None => println!("{label} @({px},{py}): no hit"),
        }
        if expect_none && hit.is_some() {
            println!("  [FAIL] expected no hit at background probe");
        }
        hit
    };
    let forehead = probe(&mut renderer, "forehead probe (frontal bbox centre)", frontal_centre, false);
    let femur = body.records.by_id("femur_right").unwrap();
    let femur_centre = Vec3::from_array(femur.bbox().unwrap().centre().map(|v| v as f32));
    let _thigh = probe(&mut renderer, "thigh probe (femur_right bbox centre)", femur_centre, false);
    let bg = renderer.pick(&layers, &body.ranges, size, size, &mvp, &state, None, 4, 4);
    println!("corner probe @(4,4): {:?}", bg.map(|(k, s)| (k.manifest_key(), s)));
    if bg.is_some() {
        println!("  [FAIL] corner probe should be background");
        hard_fail = true;
    }
    // Self-consistency: re-render the id pass with only the picked
    // record's range; the same pixel must return the same id.
    if let Some((kind, slot)) = forehead {
        let range = body.ranges[&kind]
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
            &state,
            Some((kind, &range)),
            px,
            py,
        );
        let pass = again == Some((kind, slot));
        hard_fail |= !pass;
        println!(
            "pick self-consistency ({} slot {slot}, range-restricted re-render): {:?} [{}]",
            kind.manifest_key(),
            again.map(|(k, s)| (k.manifest_key(), s)),
            if pass { "PASS" } else { "FAIL" }
        );
        if let Some(rec) = body.records.by_slot(kind, slot) {
            println!("\n-- record panel (picked) --");
            print!("{}", model::panel_text(&body.records, rec));
        }
    }
    if let Some(rec) = body.records.by_id("femur_right") {
        println!("\n-- record panel (selection frame subject) --");
        print!("{}", model::panel_text(&body.records, rec));
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
// wheel zoom / right-drag pan; S muscles... keys: S skeleton, M
// muscles, W wireframe, R reset view; left click picks (panel text to
// console, record highlighted). Not runnable on a headless machine.
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
        .union_bbox(&[LayerKind::Skeleton, LayerKind::Muscle])
        .expect("combined union bbox");
    let home_target = Vec3::from_array(combined.centre().map(|v| v as f32));

    struct App {
        body: BodyData,
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
            let layers: Vec<LayerGpu> = LayerKind::ALL
                .iter()
                .map(|&kind| {
                    anatomica_native::render::upload_layer(&gpu.device, kind, &self.body.packs[&kind])
                })
                .collect();
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
                                "s" => self.state.show_skeleton = !self.state.show_skeleton,
                                "m" => self.state.show_muscles = !self.state.show_muscles,
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
                Some((kind, slot)) => {
                    self.state.selected = Some((kind, slot));
                    if let Some(rec) = self.body.records.by_slot(kind, slot) {
                        print!("{}", model::panel_text(&self.body.records, rec));
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

    let mut app = App {
        body,
        home_target,
        cam: OrbitCamera::new(home_target),
        state: SceneState::default(),
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
