//! wgpu renderer for the ANW1 packs.
//!
//! Parity with the web shell (`web/viewer.js`): merged static buffers
//! per layer, one draw call per layer, the same two-light diffuse +
//! specular shading, the same selection highlight, the same pick-id
//! scheme ((layer_bit << 24) | slot in an RGBA8 id pass), face culling
//! off (source meshes are double-sided after the frame conversion).
//!
//! Headless-first: everything renders into offscreen targets and is
//! read back; the windowed `view` mode reuses the same draw code with
//! a surface target.

use crate::model::{LayerInfo, RecordRange};
use crate::pack::Pack;
use std::collections::BTreeSet;
use bytemuck::{Pod, Zeroable};
use glam::Mat4;
use std::time::Instant;

/// Clear colour of the web shell.
pub const BACKGROUND: wgpu::Color = wgpu::Color {
    r: 0.043,
    g: 0.055,
    b: 0.075,
    a: 1.0,
};
/// BACKGROUND as readback bytes (what "not background" is measured
/// against). GPU float→unorm conversion rounds to nearest:
/// 0.043→11, 0.055→14, 0.075→19 (measured in the first frames).
pub const BACKGROUND_BYTES: [u8; 3] = [11, 14, 19];

pub struct Gpu {
    pub instance: wgpu::Instance,
    pub adapter: wgpu::Adapter,
    pub device: wgpu::Device,
    pub queue: wgpu::Queue,
    pub info: wgpu::AdapterInfo,
}

impl Gpu {
    /// Initialise wgpu with no surface. Backend fallback chain:
    /// PRIMARY (Vulkan/Metal/DX12) → GL (llvmpipe on this VM) → all.
    /// `force_fallback_adapter` stays false: a software GL adapter is
    /// still enumerated as a normal adapter when it is the only one.
    pub async fn init() -> Result<Gpu, String> {
        let mut errors: Vec<String> = Vec::new();
        for backends in [
            wgpu::Backends::PRIMARY,
            wgpu::Backends::GL,
            wgpu::Backends::all(),
        ] {
            let instance = wgpu::Instance::new(&wgpu::InstanceDescriptor {
                backends,
                ..Default::default()
            });
            let adapter = match instance
                .request_adapter(&wgpu::RequestAdapterOptions {
                    power_preference: wgpu::PowerPreference::None,
                    compatible_surface: None,
                    force_fallback_adapter: false,
                })
                .await
            {
                Ok(a) => a,
                Err(e) => {
                    errors.push(format!("{backends:?}: request_adapter: {e}"));
                    continue;
                }
            };
            let info = adapter.get_info();
            let (device, queue) = match adapter
                .request_device(&wgpu::DeviceDescriptor {
                    label: Some("anatomica device"),
                    required_features: wgpu::Features::empty(),
                    required_limits: wgpu::Limits::default(),
                    memory_hints: wgpu::MemoryHints::Performance,
                    trace: wgpu::Trace::Off,
                    experimental_features: wgpu::ExperimentalFeatures::disabled(),
                })
                .await
            {
                Ok(dq) => dq,
                Err(e) => {
                    errors.push(format!("{backends:?}: request_device: {e}"));
                    continue;
                }
            };
            return Ok(Gpu {
                instance,
                adapter,
                device,
                queue,
                info,
            });
        }
        Err(format!(
            "no wgpu adapter on any backend chain: {}",
            errors.join(" | ")
        ))
    }

    pub fn info_string(&self) -> String {
        format!(
            "{} (backend {:?}, device type {:?}, driver {})",
            self.info.name, self.info.backend, self.info.device_type, self.info.driver
        )
    }

    pub fn wait(&self) {
        let _ = self.device.poll(wgpu::PollType::wait_indefinitely());
    }
}

#[repr(C)]
#[derive(Copy, Clone, Pod, Zeroable)]
struct ShadeUniforms {
    mvp: [[f32; 4]; 4],
    mv: [[f32; 4]; 4],
    color: [f32; 3],
    dim: f32,
    sel_slot: u32,
    sel_active: i32,
    wire: i32,
    _pad: i32,
}

#[repr(C)]
#[derive(Copy, Clone, Pod, Zeroable)]
struct PickUniforms {
    mvp: [[f32; 4]; 4],
    layer_bit: u32,
    _pad: [u32; 3],
}

const SHADE_WGSL: &str = r#"
struct Uniforms {
  mvp: mat4x4<f32>,
  mv: mat4x4<f32>,
  color: vec3<f32>,
  dim: f32,
  sel_slot: u32,
  sel_active: i32,
  wire: i32,
  pad: i32,
};
@group(0) @binding(0) var<uniform> u: Uniforms;

struct VsOut {
  @builtin(position) pos: vec4<f32>,
  @location(0) n: vec3<f32>,
  @location(1) vp: vec3<f32>,
  @location(2) @interpolate(flat) slot: u32,
};

@vertex
fn vs_main(@location(0) p: vec3<f32>, @location(1) nrm: vec4<f32>, @location(2) slot: u32) -> VsOut {
  var o: VsOut;
  let vp4 = u.mv * vec4<f32>(p, 1.0);
  o.vp = vp4.xyz;
  o.n = (u.mv * vec4<f32>(nrm.xyz, 0.0)).xyz;
  o.slot = slot;
  o.pos = u.mvp * vec4<f32>(p, 1.0);
  return o;
}

@fragment
fn fs_main(in: VsOut) -> @location(0) vec4<f32> {
  if (u.wire == 1) {
    return vec4<f32>(0.05, 0.05, 0.06, 1.0);
  }
  let n = normalize(in.n);
  let v = normalize(-in.vp);
  let l1 = normalize(vec3<f32>(0.45, 0.75, 0.65));
  let l2 = normalize(vec3<f32>(-0.55, -0.25, 0.45));
  var d = 0.34 + 0.78 * max(dot(n, l1), 0.0) + 0.26 * max(dot(n, l2), 0.0);
  let h = normalize(l1 + v);
  d += 0.18 * pow(max(dot(n, h), 0.0), 42.0);
  var col = u.color * d;
  let is_sel = u.sel_active == 1 && in.slot == u.sel_slot;
  if (is_sel) {
    col = mix(col, vec3<f32>(1.0, 0.62, 0.18), 0.55) + vec3<f32>(0.10, 0.05, 0.0);
  } else if (u.sel_active == 1 && u.dim > 0.0) {
    col *= (1.0 - u.dim);
  }
  return vec4<f32>(col, 1.0);
}
"#;

const PICK_WGSL: &str = r#"
struct PickUniforms {
  mvp: mat4x4<f32>,
  layer_bit: u32,
  pad0: u32,
  pad1: u32,
  pad2: u32,
};
@group(0) @binding(0) var<uniform> u: PickUniforms;

struct VsOut {
  @builtin(position) pos: vec4<f32>,
  @location(0) @interpolate(flat) slot: u32,
};

@vertex
fn vs_main(@location(0) p: vec3<f32>, @location(2) slot: u32) -> VsOut {
  var o: VsOut;
  o.slot = slot;
  o.pos = u.mvp * vec4<f32>(p, 1.0);
  return o;
}

@fragment
fn fs_main(in: VsOut) -> @location(0) vec4<f32> {
  let id = (u.layer_bit << 24u) | in.slot;
  // Byte 3 of the id (the layer bit) rides in alpha: RGB only holds
  // 24 bits. Alpha 0 = miss (the clear value); 1..11 = layer bit.
  // The codec is shared with the web shell (model::decode_pick_id).
  return vec4<f32>(
    f32(id & 255u) / 255.0,
    f32((id >> 8u) & 255u) / 255.0,
    f32((id >> 16u) & 255u) / 255.0,
    f32((id >> 24u) & 255u) / 255.0);
}
"#;

pub struct LayerGpu {
    pub info: LayerInfo,
    pub positions: wgpu::Buffer,
    pub normals: wgpu::Buffer,
    pub slots: wgpu::Buffer,
    pub indices: wgpu::Buffer,
    pub edges: wgpu::Buffer,
    pub index_count: u32,
    pub edge_index_count: u32,
}

pub fn upload_layer(device: &wgpu::Device, info: LayerInfo, pack: &Pack) -> LayerGpu {
    use wgpu::util::DeviceExt;
    let mk = |label: &str, bytes: &[u8], usage: wgpu::BufferUsages| {
        device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some(label),
            contents: bytes,
            usage,
        })
    };
    let name = info.key.clone();
    LayerGpu {
        info,
        positions: mk(
            &format!("{name} positions"),
            bytemuck::cast_slice(&pack.positions),
            wgpu::BufferUsages::VERTEX,
        ),
        normals: mk(
            &format!("{name} normals"),
            bytemuck::cast_slice(&pack.normals),
            wgpu::BufferUsages::VERTEX,
        ),
        slots: mk(
            &format!("{name} record ids"),
            bytemuck::cast_slice(&pack.record_ids),
            wgpu::BufferUsages::VERTEX,
        ),
        indices: mk(
            &format!("{name} indices"),
            bytemuck::cast_slice(&pack.indices),
            wgpu::BufferUsages::INDEX,
        ),
        edges: mk(
            &format!("{name} edges"),
            bytemuck::cast_slice(&pack.edges),
            wgpu::BufferUsages::INDEX,
        ),
        index_count: pack.header.index_count,
        edge_index_count: pack.header.edge_index_count,
    }
}

/// What to draw: layer visibility, selection, focus dimming,
/// wireframe — the web shell's display state, minus hover.
#[derive(Debug, Clone)]
pub struct SceneState {
    /// Layer keys currently drawn (and pickable).
    pub visible: BTreeSet<String>,
    pub selected: Option<(String, u32)>,
    /// When set, visible layers outside the focus set are drawn
    /// dimmed (selection machinery with a slot that matches nothing)
    /// — the highlighted-systems view.
    pub focus: Option<BTreeSet<String>>,
    /// Dim factor for non-selected records while a selection is
    /// active (web shell default when its dim option is on: 0.62).
    pub dim: f32,
    pub wireframe: bool,
}

impl SceneState {
    /// All layers visible, nothing selected.
    pub fn all(layers: &[LayerInfo]) -> SceneState {
        SceneState {
            visible: layers.iter().map(|l| l.key.clone()).collect(),
            selected: None,
            focus: None,
            dim: 0.62,
            wireframe: false,
        }
    }

    /// Only the named layers visible.
    pub fn only(keys: &[&str]) -> SceneState {
        SceneState {
            visible: keys.iter().map(|s| s.to_string()).collect(),
            selected: None,
            focus: None,
            dim: 0.62,
            wireframe: false,
        }
    }

    pub fn visible(&self, info: &LayerInfo) -> bool {
        self.visible.contains(&info.key)
    }
}

struct UniformPool {
    buffer: wgpu::Buffer,
    stride: u64,
    /// Size of one uniform struct — the bind group must bind exactly
    /// one element, or wgpu rejects any non-zero dynamic offset as
    /// overrunning the binding.
    element_size: u64,
    capacity: u32,
    next: u32,
}

impl UniformPool {
    fn new(
        device: &wgpu::Device,
        label: &str,
        stride: u64,
        element_size: u64,
        capacity: u32,
    ) -> UniformPool {
        let buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some(label),
            size: stride * capacity as u64,
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        UniformPool {
            buffer,
            stride,
            element_size,
            capacity,
            next: 0,
        }
    }
    fn reset(&mut self) {
        self.next = 0;
    }
    fn write<T: Pod>(&mut self, queue: &wgpu::Queue, data: &T) -> u32 {
        assert!(self.next < self.capacity, "uniform pool exhausted");
        let offset = self.next as u64 * self.stride;
        queue.write_buffer(&self.buffer, offset, bytemuck::bytes_of(data));
        self.next += 1;
        offset as u32
    }
}

pub struct Renderer {
    pub gpu: Gpu,
    shade_pipeline: wgpu::RenderPipeline,
    wire_pipeline: wgpu::RenderPipeline,
    pick_pipeline: wgpu::RenderPipeline,
    shade_bg_layout: wgpu::BindGroupLayout,
    pick_bg_layout: wgpu::BindGroupLayout,
    shade_pool: UniformPool,
    pick_pool: UniformPool,
}

pub const DEPTH_FORMAT: wgpu::TextureFormat = wgpu::TextureFormat::Depth32Float;

impl Renderer {
    pub fn new(gpu: Gpu, color_format: wgpu::TextureFormat) -> Renderer {
        let device = &gpu.device;
        let shade_module = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("anatomica shade"),
            source: wgpu::ShaderSource::Wgsl(SHADE_WGSL.into()),
        });
        let pos_attrs = wgpu::vertex_attr_array![0 => Float32x3];
        let nrm_attrs = wgpu::vertex_attr_array![1 => Snorm8x4];
        let slot_attrs = wgpu::vertex_attr_array![2 => Uint32];
        let vertex_buffers = [
            wgpu::VertexBufferLayout {
                array_stride: 12,
                step_mode: wgpu::VertexStepMode::Vertex,
                attributes: &pos_attrs,
            },
            wgpu::VertexBufferLayout {
                array_stride: 4,
                step_mode: wgpu::VertexStepMode::Vertex,
                attributes: &nrm_attrs,
            },
            wgpu::VertexBufferLayout {
                array_stride: 4,
                step_mode: wgpu::VertexStepMode::Vertex,
                attributes: &slot_attrs,
            },
        ];
        let uniform_layout = |label: &str| {
            device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
                label: Some(label),
                entries: &[wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::VERTEX_FRAGMENT,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Uniform,
                        has_dynamic_offset: true,
                        min_binding_size: None,
                    },
                    count: None,
                }],
            })
        };
        let shade_bg_layout = uniform_layout("shade uniforms");
        let pick_bg_layout = uniform_layout("pick uniforms");
        let depth_stencil = Some(wgpu::DepthStencilState {
            format: DEPTH_FORMAT,
            depth_write_enabled: true,
            depth_compare: wgpu::CompareFunction::LessEqual,
            stencil: wgpu::StencilState::default(),
            bias: wgpu::DepthBiasState::default(),
        });
        let mk_shade = |topology: wgpu::PrimitiveTopology, depth_write: bool| {
            let mut ds = depth_stencil.clone().unwrap();
            ds.depth_write_enabled = depth_write;
            device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
                label: Some("shade pipeline"),
                layout: Some(
                    &device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                        label: Some("shade layout"),
                        bind_group_layouts: &[&shade_bg_layout],
                        push_constant_ranges: &[],
                    }),
                ),
                vertex: wgpu::VertexState {
                    module: &shade_module,
                    entry_point: Some("vs_main"),
                    compilation_options: Default::default(),
                    buffers: &vertex_buffers,
                },
                fragment: Some(wgpu::FragmentState {
                    module: &shade_module,
                    entry_point: Some("fs_main"),
                    compilation_options: Default::default(),
                    targets: &[Some(wgpu::ColorTargetState {
                        format: color_format,
                        blend: None,
                        write_mask: wgpu::ColorWrites::ALL,
                    })],
                }),
                primitive: wgpu::PrimitiveState {
                    topology,
                    strip_index_format: None,
                    front_face: wgpu::FrontFace::Ccw,
                    cull_mode: None,
                    unclipped_depth: false,
                    polygon_mode: wgpu::PolygonMode::Fill,
                    conservative: false,
                },
                depth_stencil: Some(ds),
                multisample: wgpu::MultisampleState::default(),
                multiview: None,
                cache: None,
            })
        };
        let shade_pipeline = mk_shade(wgpu::PrimitiveTopology::TriangleList, true);
        let wire_pipeline = mk_shade(wgpu::PrimitiveTopology::LineList, false);

        let pick_module = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("anatomica pick"),
            source: wgpu::ShaderSource::Wgsl(PICK_WGSL.into()),
        });
        let pick_vertex_buffers = [
            vertex_buffers[0].clone(),
            wgpu::VertexBufferLayout {
                array_stride: 4,
                step_mode: wgpu::VertexStepMode::Vertex,
                attributes: &slot_attrs,
            },
        ];
        let pick_pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("pick pipeline"),
            layout: Some(
                &device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                    label: Some("pick layout"),
                    bind_group_layouts: &[&pick_bg_layout],
                    push_constant_ranges: &[],
                }),
            ),
            vertex: wgpu::VertexState {
                module: &pick_module,
                entry_point: Some("vs_main"),
                compilation_options: Default::default(),
                buffers: &pick_vertex_buffers,
            },
            fragment: Some(wgpu::FragmentState {
                module: &pick_module,
                entry_point: Some("fs_main"),
                compilation_options: Default::default(),
                targets: &[Some(wgpu::ColorTargetState {
                    format: wgpu::TextureFormat::Rgba8Unorm,
                    blend: None,
                    write_mask: wgpu::ColorWrites::ALL,
                })],
            }),
            primitive: wgpu::PrimitiveState {
                topology: wgpu::PrimitiveTopology::TriangleList,
                strip_index_format: None,
                front_face: wgpu::FrontFace::Ccw,
                cull_mode: None,
                unclipped_depth: false,
                polygon_mode: wgpu::PolygonMode::Fill,
                conservative: false,
            },
            depth_stencil,
            multisample: wgpu::MultisampleState::default(),
            multiview: None,
            cache: None,
        });

        let align = gpu
            .adapter
            .limits()
            .min_uniform_buffer_offset_alignment as u64;
        let stride = align.max(256);
        let shade_pool = UniformPool::new(
            device,
            "shade uniform pool",
            stride,
            std::mem::size_of::<ShadeUniforms>() as u64,
            64,
        );
        let pick_pool = UniformPool::new(
            device,
            "pick uniform pool",
            stride,
            std::mem::size_of::<PickUniforms>() as u64,
            64,
        );
        Renderer {
            gpu,
            shade_pipeline,
            wire_pipeline,
            pick_pipeline,
            shade_bg_layout,
            pick_bg_layout,
            shade_pool,
            pick_pool,
        }
    }

    fn bind_group(&self, layout: &wgpu::BindGroupLayout, pool: &UniformPool) -> wgpu::BindGroup {
        self.gpu.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: None,
            layout,
            entries: &[wgpu::BindGroupEntry {
                binding: 0,
                resource: wgpu::BindingResource::Buffer(wgpu::BufferBinding {
                    buffer: &pool.buffer,
                    offset: 0,
                    size: std::num::NonZeroU64::new(pool.element_size),
                }),
            }],
        })
    }

    /// Record the shaded draws for `layers` into an open render pass.
    /// The caller owns the pass (target + clears).
    pub fn draw_shaded(
        &mut self,
        pass: &mut wgpu::RenderPass<'_>,
        layers: &[LayerGpu],
        mvp: &Mat4,
        mv: &Mat4,
        state: &SceneState,
    ) {
        self.shade_pool.reset();
        for layer in layers {
            if !state.visible(&layer.info) {
                continue;
            }
            // Focus dimming reuses the selection path: a layer
            // outside the focus set is drawn with selection active
            // on a slot that matches nothing, so every fragment dims.
            let in_focus = state
                .focus
                .as_ref()
                .map(|f| f.contains(&layer.info.key))
                .unwrap_or(true);
            let (sel_active, sel_slot) = if !in_focus {
                (1, u32::MAX)
            } else {
                match &state.selected {
                    Some((key, slot)) if *key == layer.info.key => (1, *slot),
                    _ => (0, 0),
                }
            };
            let uniforms = ShadeUniforms {
                mvp: mvp.to_cols_array_2d(),
                mv: mv.to_cols_array_2d(),
                color: layer.info.color,
                dim: if sel_active == 1 { state.dim } else { 0.0 },
                sel_slot,
                sel_active,
                wire: 0,
                _pad: 0,
            };
            let offset = self.shade_pool.write(&self.gpu.queue, &uniforms);
            let bg = self.bind_group(&self.shade_bg_layout, &self.shade_pool);
            pass.set_pipeline(&self.shade_pipeline);
            pass.set_bind_group(0, &bg, &[offset]);
            pass.set_vertex_buffer(0, layer.positions.slice(..));
            pass.set_vertex_buffer(1, layer.normals.slice(..));
            pass.set_vertex_buffer(2, layer.slots.slice(..));
            pass.set_index_buffer(layer.indices.slice(..), wgpu::IndexFormat::Uint32);
            pass.draw_indexed(0..layer.index_count, 0, 0..1);
            if state.wireframe {
                let wire_uniforms = ShadeUniforms { wire: 1, ..uniforms };
                let woffset = self.shade_pool.write(&self.gpu.queue, &wire_uniforms);
                let wbg = self.bind_group(&self.shade_bg_layout, &self.shade_pool);
                pass.set_pipeline(&self.wire_pipeline);
                pass.set_bind_group(0, &wbg, &[woffset]);
                pass.set_index_buffer(layer.edges.slice(..), wgpu::IndexFormat::Uint32);
                pass.draw_indexed(0..layer.edge_index_count, 0, 0..1);
            }
        }
    }

    /// Record the id-pass draws. `restrict` limits drawing to one
    /// record's index range (the pick self-consistency check).
    fn draw_ids(
        &mut self,
        pass: &mut wgpu::RenderPass<'_>,
        layers: &[LayerGpu],
        ranges: &std::collections::HashMap<String, Vec<RecordRange>>,
        mvp: &Mat4,
        state: &SceneState,
        restrict: Option<(&str, &RecordRange)>,
    ) {
        self.pick_pool.reset();
        for layer in layers {
            if !state.visible(&layer.info) {
                continue;
            }
            if let Some((key, _)) = restrict {
                if key != layer.info.key {
                    continue;
                }
            }
            let uniforms = PickUniforms {
                mvp: mvp.to_cols_array_2d(),
                layer_bit: layer.info.pick_bit,
                _pad: [0; 3],
            };
            let offset = self.pick_pool.write(&self.gpu.queue, &uniforms);
            let bg = self.bind_group(&self.pick_bg_layout, &self.pick_pool);
            pass.set_pipeline(&self.pick_pipeline);
            pass.set_bind_group(0, &bg, &[offset]);
            pass.set_vertex_buffer(0, layer.positions.slice(..));
            // pick pipeline buffer slot 1 carries the record-id buffer
            pass.set_vertex_buffer(1, layer.slots.slice(..));
            pass.set_index_buffer(layer.indices.slice(..), wgpu::IndexFormat::Uint32);
            match restrict {
                Some((_, range)) => {
                    pass.draw_indexed(
                        range.index_start..range.index_start + range.index_count,
                        0,
                        0..1,
                    );
                }
                None => {
                    let _ = ranges;
                    pass.draw_indexed(0..layer.index_count, 0, 0..1);
                }
            }
        }
    }
}

pub struct OffscreenTarget {
    pub color: wgpu::Texture,
    pub color_view: wgpu::TextureView,
    pub depth: wgpu::Texture,
    pub depth_view: wgpu::TextureView,
    pub width: u32,
    pub height: u32,
}

pub fn make_target(
    device: &wgpu::Device,
    width: u32,
    height: u32,
    format: wgpu::TextureFormat,
    label: &str,
) -> OffscreenTarget {
    let size = wgpu::Extent3d {
        width,
        height,
        depth_or_array_layers: 1,
    };
    let color = device.create_texture(&wgpu::TextureDescriptor {
        label: Some(label),
        size,
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format,
        usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::COPY_SRC,
        view_formats: &[],
    });
    let depth = device.create_texture(&wgpu::TextureDescriptor {
        label: Some("depth"),
        size,
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format: DEPTH_FORMAT,
        usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
        view_formats: &[],
    });
    let color_view = color.create_view(&Default::default());
    let depth_view = depth.create_view(&Default::default());
    OffscreenTarget {
        color,
        color_view,
        depth,
        depth_view,
        width,
        height,
    }
}

pub struct FrameResult {
    /// RGBA8, rows top-to-bottom (framebuffer row 0 first).
    pub rgba: Vec<u8>,
    pub width: u32,
    pub height: u32,
    /// Wall time: encode + submit + wait for the render pass.
    pub render_ms: f64,
    /// Wall time: texture→buffer copy + map + unpad.
    pub readback_ms: f64,
}

impl Renderer {
    /// Render the shaded scene into a fresh offscreen target and read
    /// it back.
    pub fn render_offscreen(
        &mut self,
        layers: &[LayerGpu],
        width: u32,
        height: u32,
        mvp: &Mat4,
        mv: &Mat4,
        state: &SceneState,
    ) -> FrameResult {
        let target = make_target(
            &self.gpu.device,
            width,
            height,
            wgpu::TextureFormat::Rgba8Unorm,
            "offscreen colour",
        );
        let t0 = Instant::now();
        let mut encoder = self
            .gpu
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("frame"),
            });
        {
            let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("shaded pass"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &target.color_view,
                    depth_slice: None,
                    resolve_target: None,
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Clear(BACKGROUND),
                        store: wgpu::StoreOp::Store,
                    },
                })],
                depth_stencil_attachment: Some(wgpu::RenderPassDepthStencilAttachment {
                    view: &target.depth_view,
                    depth_ops: Some(wgpu::Operations {
                        load: wgpu::LoadOp::Clear(1.0),
                        store: wgpu::StoreOp::Store,
                    }),
                    stencil_ops: None,
                }),
                timestamp_writes: None,
                occlusion_query_set: None,
            });
            self.draw_shaded(&mut pass, layers, mvp, mv, state);
        }
        self.gpu.queue.submit([encoder.finish()]);
        self.gpu.wait();
        let render_ms = t0.elapsed().as_secs_f64() * 1000.0;
        let t1 = Instant::now();
        let rgba = read_texture(&self.gpu, &target.color, width, height);
        let readback_ms = t1.elapsed().as_secs_f64() * 1000.0;
        FrameResult {
            rgba,
            width,
            height,
            render_ms,
            readback_ms,
        }
    }

    /// Render the id pass at (width, height) and decode the pixel at
    /// (px, py). With `restrict`, only that record's range is drawn.
    pub fn pick(
        &mut self,
        layers: &[LayerGpu],
        ranges: &std::collections::HashMap<String, Vec<RecordRange>>,
        width: u32,
        height: u32,
        mvp: &Mat4,
        state: &SceneState,
        restrict: Option<(&str, &RecordRange)>,
        px: u32,
        py: u32,
    ) -> Option<(String, u32)> {
        let target = make_target(
            &self.gpu.device,
            width,
            height,
            wgpu::TextureFormat::Rgba8Unorm,
            "pick target",
        );
        let mut encoder = self
            .gpu
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor { label: Some("pick") });
        {
            let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("pick pass"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &target.color_view,
                    depth_slice: None,
                    resolve_target: None,
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Clear(wgpu::Color::TRANSPARENT),
                        store: wgpu::StoreOp::Store,
                    },
                })],
                depth_stencil_attachment: Some(wgpu::RenderPassDepthStencilAttachment {
                    view: &target.depth_view,
                    depth_ops: Some(wgpu::Operations {
                        load: wgpu::LoadOp::Clear(1.0),
                        store: wgpu::StoreOp::Store,
                    }),
                    stencil_ops: None,
                }),
                timestamp_writes: None,
                occlusion_query_set: None,
            });
            self.draw_ids(&mut pass, layers, ranges, mvp, state, restrict);
        }
        self.gpu.queue.submit([encoder.finish()]);
        self.gpu.wait();
        let px_bytes = read_pixel(&self.gpu, &target.color, px, py);
        let infos: Vec<LayerInfo> = layers.iter().map(|l| l.info.clone()).collect();
        crate::model::decode_pick_id(px_bytes, &infos)
    }
}

fn read_texture(gpu: &Gpu, texture: &wgpu::Texture, width: u32, height: u32) -> Vec<u8> {
    let row_bytes = width * 4;
    let padded = row_bytes.div_ceil(256) * 256;
    let buffer = gpu.device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("readback"),
        size: (padded * height) as u64,
        usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
        mapped_at_creation: false,
    });
    let mut encoder = gpu
        .device
        .create_command_encoder(&wgpu::CommandEncoderDescriptor {
            label: Some("readback copy"),
        });
    encoder.copy_texture_to_buffer(
        wgpu::TexelCopyTextureInfo {
            texture,
            mip_level: 0,
            origin: wgpu::Origin3d::ZERO,
            aspect: wgpu::TextureAspect::All,
        },
        wgpu::TexelCopyBufferInfo {
            buffer: &buffer,
            layout: wgpu::TexelCopyBufferLayout {
                offset: 0,
                bytes_per_row: Some(padded),
                rows_per_image: Some(height),
            },
        },
        wgpu::Extent3d {
            width,
            height,
            depth_or_array_layers: 1,
        },
    );
    gpu.queue.submit([encoder.finish()]);
    let slice = buffer.slice(..);
    let (tx, rx) = std::sync::mpsc::channel();
    slice.map_async(wgpu::MapMode::Read, move |r| {
        let _ = tx.send(r);
    });
    gpu.wait();
    rx.recv().expect("map callback").expect("map read");
    let data = slice.get_mapped_range();
    let mut out = Vec::with_capacity((row_bytes * height) as usize);
    for row in 0..height {
        let start = (row * padded) as usize;
        out.extend_from_slice(&data[start..start + row_bytes as usize]);
    }
    drop(data);
    buffer.unmap();
    out
}

fn read_pixel(gpu: &Gpu, texture: &wgpu::Texture, x: u32, y: u32) -> [u8; 4] {
    let buffer = gpu.device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("pick readback"),
        size: 256,
        usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
        mapped_at_creation: false,
    });
    let mut encoder = gpu
        .device
        .create_command_encoder(&wgpu::CommandEncoderDescriptor {
            label: Some("pick copy"),
        });
    encoder.copy_texture_to_buffer(
        wgpu::TexelCopyTextureInfo {
            texture,
            mip_level: 0,
            origin: wgpu::Origin3d { x, y, z: 0 },
            aspect: wgpu::TextureAspect::All,
        },
        wgpu::TexelCopyBufferInfo {
            buffer: &buffer,
            layout: wgpu::TexelCopyBufferLayout {
                offset: 0,
                bytes_per_row: Some(256),
                rows_per_image: Some(1),
            },
        },
        wgpu::Extent3d {
            width: 1,
            height: 1,
            depth_or_array_layers: 1,
        },
    );
    gpu.queue.submit([encoder.finish()]);
    let slice = buffer.slice(..);
    let (tx, rx) = std::sync::mpsc::channel();
    slice.map_async(wgpu::MapMode::Read, move |r| {
        let _ = tx.send(r);
    });
    gpu.wait();
    rx.recv().expect("map callback").expect("map read");
    let data = slice.get_mapped_range();
    let px = [data[0], data[1], data[2], data[3]];
    drop(data);
    buffer.unmap();
    px
}

/// Fraction of pixels that differ from the background colour.
pub fn non_background_fraction(rgba: &[u8]) -> f64 {
    let total = rgba.len() / 4;
    if total == 0 {
        return 0.0;
    }
    let mut drawn = 0usize;
    for px in rgba.chunks_exact(4) {
        if px[0] != BACKGROUND_BYTES[0] || px[1] != BACKGROUND_BYTES[1] || px[2] != BACKGROUND_BYTES[2]
        {
            drawn += 1;
        }
    }
    drawn as f64 / total as f64
}

/// Pixel-space bounding box of the non-background pixels:
/// (min_x, min_y, max_x, max_y), inclusive.
pub fn silhouette_bbox(rgba: &[u8], width: u32, height: u32) -> Option<(u32, u32, u32, u32)> {
    let (mut mnx, mut mny) = (u32::MAX, u32::MAX);
    let (mut mxx, mut mxy) = (0u32, 0u32);
    let mut any = false;
    for y in 0..height {
        for x in 0..width {
            let i = ((y * width + x) * 4) as usize;
            let px = &rgba[i..i + 4];
            if px[0] != BACKGROUND_BYTES[0]
                || px[1] != BACKGROUND_BYTES[1]
                || px[2] != BACKGROUND_BYTES[2]
            {
                any = true;
                mnx = mnx.min(x);
                mxx = mxx.max(x);
                mny = mny.min(y);
                mxy = mxy.max(y);
            }
        }
    }
    if any {
        Some((mnx, mny, mxx, mxy))
    } else {
        None
    }
}
