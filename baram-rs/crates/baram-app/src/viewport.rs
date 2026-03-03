// ════════════════════════════════════════════════════════════════
//  Viewport Renderer — off‑screen 3‑D rendering with egui integration
//
//  Renders the scene to an off‑screen wgpu texture, then registers
//  that texture with egui so it can be displayed as `ui.image()`.
// ════════════════════════════════════════════════════════════════

use baram_mesh::polydata::{TriMesh, Vertex};
use baram_renderer::camera::CameraUniform;
use wgpu::util::DeviceExt;

// ── GPU mesh buffer ────────────────────────────────────────────

struct MeshGpuBuffer {
    vertex_buffer: wgpu::Buffer,
    index_buffer: wgpu::Buffer,
    num_indices: u32,
}

// ── Viewport renderer ──────────────────────────────────────────

pub struct ViewportRenderer {
    // Render pipeline (same Blinn‑Phong shader as baram-renderer)
    pipeline: wgpu::RenderPipeline,
    camera_buffer: wgpu::Buffer,
    camera_bind_group: wgpu::BindGroup,

    // Off‑screen render targets
    color_texture: wgpu::Texture,
    color_view: wgpu::TextureView,
    depth_view: wgpu::TextureView,
    pub width: u32,
    pub height: u32,

    // Meshes
    mesh_buffers: Vec<MeshGpuBuffer>,

    // egui texture handle (lazy‑registered)
    pub egui_texture_id: Option<egui::TextureId>,
}

/// WGSL: same Blinn‑Phong mesh shader.
const VIEWPORT_SHADER: &str = r#"
struct Camera { view_proj: mat4x4<f32>, eye: vec4<f32> };
@group(0) @binding(0) var<uniform> camera: Camera;

struct VIn {
    @location(0) position: vec3<f32>,
    @location(1) normal:   vec3<f32>,
    @location(2) color:    vec4<f32>,
};
struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) world_normal: vec3<f32>,
    @location(1) color:        vec4<f32>,
    @location(2) world_pos:    vec3<f32>,
};

@vertex fn vs_main(v: VIn) -> VOut {
    var o: VOut;
    o.clip         = camera.view_proj * vec4(v.position, 1.0);
    o.world_normal = v.normal;
    o.color        = v.color;
    o.world_pos    = v.position;
    return o;
}

@fragment fn fs_main(f: VOut) -> @location(0) vec4<f32> {
    let light = normalize(vec3(0.5, 1.0, 0.3));
    let n = normalize(f.world_normal);
    let ambient  = 0.15;
    let diffuse  = max(dot(n, light), 0.0) * 0.7;
    let view_dir = normalize(camera.eye.xyz - f.world_pos);
    let half_dir = normalize(light + view_dir);
    let specular = pow(max(dot(n, half_dir), 0.0), 32.0) * 0.3;
    let lum = ambient + diffuse + specular;
    return vec4(f.color.rgb * lum, f.color.a);
}
"#;

impl ViewportRenderer {
    pub fn new(
        device: &wgpu::Device,
        target_format: wgpu::TextureFormat,
        width: u32,
        height: u32,
    ) -> Self {
        let w = width.max(1);
        let h = height.max(1);

        // Shader
        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("Viewport Shader"),
            source: wgpu::ShaderSource::Wgsl(VIEWPORT_SHADER.into()),
        });

        // Camera uniform
        let camera_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("VP Camera"),
            size: std::mem::size_of::<CameraUniform>() as u64,
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });

        let bgl = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("VP BGL"),
            entries: &[wgpu::BindGroupLayoutEntry {
                binding: 0,
                visibility: wgpu::ShaderStages::VERTEX | wgpu::ShaderStages::FRAGMENT,
                ty: wgpu::BindingType::Buffer {
                    ty: wgpu::BufferBindingType::Uniform,
                    has_dynamic_offset: false,
                    min_binding_size: None,
                },
                count: None,
            }],
        });

        let camera_bind_group = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("VP BG"),
            layout: &bgl,
            entries: &[wgpu::BindGroupEntry {
                binding: 0,
                resource: camera_buffer.as_entire_binding(),
            }],
        });

        let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: Some("VP PL"),
            bind_group_layouts: &[&bgl],
            push_constant_ranges: &[],
        });

        let pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("Viewport Pipeline"),
            layout: Some(&pipeline_layout),
            vertex: wgpu::VertexState {
                module: &shader,
                entry_point: "vs_main",
                buffers: &[wgpu::VertexBufferLayout {
                    array_stride: std::mem::size_of::<Vertex>() as u64,
                    step_mode: wgpu::VertexStepMode::Vertex,
                    attributes: &[
                        wgpu::VertexAttribute { offset: 0,  shader_location: 0, format: wgpu::VertexFormat::Float32x3 },
                        wgpu::VertexAttribute { offset: 12, shader_location: 1, format: wgpu::VertexFormat::Float32x3 },
                        wgpu::VertexAttribute { offset: 24, shader_location: 2, format: wgpu::VertexFormat::Float32x4 },
                    ],
                }],
                compilation_options: Default::default(),
            },
            fragment: Some(wgpu::FragmentState {
                module: &shader,
                entry_point: "fs_main",
                targets: &[Some(wgpu::ColorTargetState {
                    format: target_format,
                    blend: Some(wgpu::BlendState::REPLACE),
                    write_mask: wgpu::ColorWrites::ALL,
                })],
                compilation_options: Default::default(),
            }),
            primitive: wgpu::PrimitiveState {
                topology: wgpu::PrimitiveTopology::TriangleList,
                front_face: wgpu::FrontFace::Ccw,
                cull_mode: Some(wgpu::Face::Back),
                ..Default::default()
            },
            depth_stencil: Some(wgpu::DepthStencilState {
                format: wgpu::TextureFormat::Depth32Float,
                depth_write_enabled: true,
                depth_compare: wgpu::CompareFunction::Less,
                stencil: Default::default(),
                bias: Default::default(),
            }),
            multisample: wgpu::MultisampleState::default(),
            multiview: None,
        });

        // Off‑screen textures
        let (color_texture, color_view) = create_color_texture(device, target_format, w, h);
        let depth_view = create_depth_view(device, w, h);

        Self {
            pipeline,
            camera_buffer,
            camera_bind_group,
            color_texture,
            color_view,
            depth_view,
            width: w,
            height: h,
            mesh_buffers: Vec::new(),
            egui_texture_id: None,
        }
    }

    /// Ensure the render targets match the given size.
    pub fn resize(&mut self, device: &wgpu::Device, format: wgpu::TextureFormat, w: u32, h: u32) {
        let w = w.max(1);
        let h = h.max(1);
        if w == self.width && h == self.height {
            return;
        }
        let (ct, cv) = create_color_texture(device, format, w, h);
        self.color_texture = ct;
        self.color_view = cv;
        self.depth_view = create_depth_view(device, w, h);
        self.width = w;
        self.height = h;
        // The registered egui texture id must be updated
        self.egui_texture_id = None;
    }

    /// Upload a TriMesh to the GPU (appends to the buffer list).
    pub fn upload_mesh(&mut self, device: &wgpu::Device, mesh: &TriMesh) {
        if mesh.vertices.is_empty() || mesh.indices.is_empty() { return; }
        let vb = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("VP VB"),
            contents: bytemuck::cast_slice(&mesh.vertices),
            usage: wgpu::BufferUsages::VERTEX,
        });
        let ib = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("VP IB"),
            contents: bytemuck::cast_slice(&mesh.indices),
            usage: wgpu::BufferUsages::INDEX,
        });
        self.mesh_buffers.push(MeshGpuBuffer {
            vertex_buffer: vb,
            index_buffer: ib,
            num_indices: mesh.indices.len() as u32,
        });
    }

    /// Clear all uploaded meshes.
    pub fn clear_meshes(&mut self) {
        self.mesh_buffers.clear();
    }

    /// Render the scene to the off‑screen colour texture.
    pub fn render_frame(
        &self,
        device: &wgpu::Device,
        queue: &wgpu::Queue,
        camera: &CameraUniform,
    ) {
        queue.write_buffer(&self.camera_buffer, 0, bytemuck::bytes_of(camera));

        let mut encoder = device.create_command_encoder(&wgpu::CommandEncoderDescriptor {
            label: Some("VP Encoder"),
        });
        {
            let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("VP Pass"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &self.color_view,
                    resolve_target: None,
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Clear(wgpu::Color {
                            r: 0.12, g: 0.13, b: 0.15, a: 1.0,
                        }),
                        store: wgpu::StoreOp::Store,
                    },
                })],
                depth_stencil_attachment: Some(wgpu::RenderPassDepthStencilAttachment {
                    view: &self.depth_view,
                    depth_ops: Some(wgpu::Operations {
                        load: wgpu::LoadOp::Clear(1.0),
                        store: wgpu::StoreOp::Store,
                    }),
                    stencil_ops: None,
                }),
                ..Default::default()
            });

            pass.set_pipeline(&self.pipeline);
            pass.set_bind_group(0, &self.camera_bind_group, &[]);
            for buf in &self.mesh_buffers {
                pass.set_vertex_buffer(0, buf.vertex_buffer.slice(..));
                pass.set_index_buffer(buf.index_buffer.slice(..), wgpu::IndexFormat::Uint32);
                pass.draw_indexed(0..buf.num_indices, 0, 0..1);
            }
        }
        queue.submit(std::iter::once(encoder.finish()));
    }

    /// Get (or create) the egui `TextureId` for the viewport colour texture.
    pub fn ensure_egui_texture(
        &mut self,
        device: &wgpu::Device,
        egui_renderer: &mut eframe::egui_wgpu::Renderer,
    ) -> egui::TextureId {
        if let Some(id) = self.egui_texture_id {
            egui_renderer.update_egui_texture_from_wgpu_texture(
                device,
                &self.color_view,
                wgpu::FilterMode::Linear,
                id,
            );
            id
        } else {
            let id = egui_renderer.register_native_texture(
                device,
                &self.color_view,
                wgpu::FilterMode::Linear,
            );
            self.egui_texture_id = Some(id);
            id
        }
    }
}

// ── Helpers ────────────────────────────────────────────────────

fn create_color_texture(
    device: &wgpu::Device,
    format: wgpu::TextureFormat,
    w: u32,
    h: u32,
) -> (wgpu::Texture, wgpu::TextureView) {
    let tex = device.create_texture(&wgpu::TextureDescriptor {
        label: Some("VP Color"),
        size: wgpu::Extent3d { width: w, height: h, depth_or_array_layers: 1 },
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format,
        usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::TEXTURE_BINDING,
        view_formats: &[],
    });
    let view = tex.create_view(&Default::default());
    (tex, view)
}

fn create_depth_view(device: &wgpu::Device, w: u32, h: u32) -> wgpu::TextureView {
    let tex = device.create_texture(&wgpu::TextureDescriptor {
        label: Some("VP Depth"),
        size: wgpu::Extent3d { width: w, height: h, depth_or_array_layers: 1 },
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format: wgpu::TextureFormat::Depth32Float,
        usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::TEXTURE_BINDING,
        view_formats: &[],
    });
    tex.create_view(&Default::default())
}
