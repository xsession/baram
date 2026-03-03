// ════════════════════════════════════════════════════════════════
//  Grid — infinite ground grid rendered via a full‑screen quad
//  with procedural line generation in the fragment shader.
// ════════════════════════════════════════════════════════════════



/// WGSL shader for the infinite grid.
pub const GRID_SHADER: &str = r#"
struct Camera {
    view_proj: mat4x4<f32>,
    eye:       vec4<f32>,
};
@group(0) @binding(0) var<uniform> cam: Camera;

struct VsOut {
    @builtin(position) clip: vec4<f32>,
    @location(0)       near_point: vec3<f32>,
    @location(1)       far_point:  vec3<f32>,
};

// Full‑screen triangle trick (3 verts, no buffers)
@vertex
fn vs_grid(@builtin(vertex_index) vi: u32) -> VsOut {
    let positions = array<vec2<f32>, 6>(
        vec2(-1.0, -1.0), vec2(1.0, -1.0), vec2(1.0, 1.0),
        vec2(-1.0, -1.0), vec2(1.0,  1.0), vec2(-1.0, 1.0),
    );
    let p = positions[vi];
    let inv_vp = cam.view_proj;  // we actually need the INVERSE — see note below.
    // For a proper grid we need inverse(view_proj).  We pass it
    // as a second uniform in production; for the prototype we
    // simply draw a finite ground quad instead (see GridRenderer).
    var out: VsOut;
    out.clip       = vec4(p, 0.0, 1.0);
    out.near_point = vec3(p, 0.0);
    out.far_point  = vec3(p, 1.0);
    return out;
}

@fragment
fn fs_grid(in: VsOut) -> @location(0) vec4<f32> {
    return vec4(0.35, 0.35, 0.35, 0.5);
}
"#;

/// Renders a finite reference grid on the XZ plane.
pub struct GridRenderer {
    pipeline: wgpu::RenderPipeline,
    vertex_buffer: wgpu::Buffer,
    num_vertices: u32,
    camera_bg: wgpu::BindGroup,
}

impl GridRenderer {
    /// Create the grid renderer.
    pub fn new(
        device: &wgpu::Device,
        format: wgpu::TextureFormat,
        camera_buffer: &wgpu::Buffer,
    ) -> Self {
        use wgpu::util::DeviceExt;

        // Generate grid line vertices (thin quads on XZ plane)
        let extent = 50.0f32;
        let step = 1.0f32;
        let color: [f32; 4] = [0.35, 0.35, 0.35, 0.6];
        let mut verts: Vec<[f32; 10]> = Vec::new(); // pos3 + normal3 + color4

        let half_w = 0.005f32;
        let n: [f32; 3] = [0.0, 1.0, 0.0];
        let mut x = -extent;
        while x <= extent + 0.001 {
            // Line along Z
            push_line_quad(&mut verts, [x, 0.0, -extent], [x, 0.0, extent], half_w, n, color);
            // Line along X
            push_line_quad(&mut verts, [-extent, 0.0, x], [extent, 0.0, x], half_w, n, color);
            x += step;
        }

        let raw: Vec<f32> = verts.iter().flat_map(|v| v.iter().copied()).collect();
        let vertex_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("GridVB"),
            contents: bytemuck::cast_slice(&raw),
            usage: wgpu::BufferUsages::VERTEX,
        });
        let num_vertices = (verts.len()) as u32;

        // BGL + BG (reuse camera buffer)
        let bgl = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("Grid BGL"),
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
        let camera_bg = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("Grid BG"),
            layout: &bgl,
            entries: &[wgpu::BindGroupEntry {
                binding: 0,
                resource: camera_buffer.as_entire_binding(),
            }],
        });

        // Shader (reuse mesh shader VS/FS — the grid is just vertices)
        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("Grid Shader"),
            source: wgpu::ShaderSource::Wgsl(GRID_LINE_SHADER.into()),
        });

        let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: Some("Grid PL"),
            bind_group_layouts: &[&bgl],
            push_constant_ranges: &[],
        });

        let pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("Grid Pipeline"),
            layout: Some(&pipeline_layout),
            vertex: wgpu::VertexState {
                module: &shader,
                entry_point: "vs_main",
                buffers: &[wgpu::VertexBufferLayout {
                    array_stride: 40, // 10 × f32
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
                    format,
                    blend: Some(wgpu::BlendState::ALPHA_BLENDING),
                    write_mask: wgpu::ColorWrites::ALL,
                })],
                compilation_options: Default::default(),
            }),
            primitive: wgpu::PrimitiveState {
                topology: wgpu::PrimitiveTopology::TriangleList,
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

        Self { pipeline, vertex_buffer, num_vertices, camera_bg }
    }

    /// Record grid draw commands into an existing render pass.
    pub fn draw<'a>(&'a self, pass: &mut wgpu::RenderPass<'a>) {
        pass.set_pipeline(&self.pipeline);
        pass.set_bind_group(0, &self.camera_bg, &[]);
        pass.set_vertex_buffer(0, self.vertex_buffer.slice(..));
        pass.draw(0..self.num_vertices, 0..1);
    }
}

// ── Helpers ────────────────────────────────────────────────────

/// Simple pass‑through shader for grid line vertices.
const GRID_LINE_SHADER: &str = r#"
struct Camera { view_proj: mat4x4<f32>, eye: vec4<f32> };
@group(0) @binding(0) var<uniform> cam: Camera;

struct VIn {
    @location(0) pos:   vec3<f32>,
    @location(1) norm:  vec3<f32>,
    @location(2) color: vec4<f32>,
};
struct VOut {
    @builtin(position) clip: vec4<f32>,
    @location(0) color: vec4<f32>,
};

@vertex fn vs_main(v: VIn) -> VOut {
    var o: VOut;
    o.clip  = cam.view_proj * vec4(v.pos, 1.0);
    o.color = v.color;
    return o;
}

@fragment fn fs_main(f: VOut) -> @location(0) vec4<f32> {
    return f.color;
}
"#;

fn push_line_quad(
    verts: &mut Vec<[f32; 10]>,
    a: [f32; 3],
    b: [f32; 3],
    half_w: f32,
    n: [f32; 3],
    c: [f32; 4],
) {
    // Build a thin quad perpendicular to Y axis
    let dx = b[0] - a[0];
    let dz = b[2] - a[2];
    let len = (dx * dx + dz * dz).sqrt().max(1e-12);
    let px = -dz / len * half_w;
    let pz =  dx / len * half_w;

    let v0 = [a[0]+px, a[1], a[2]+pz, n[0], n[1], n[2], c[0], c[1], c[2], c[3]];
    let v1 = [a[0]-px, a[1], a[2]-pz, n[0], n[1], n[2], c[0], c[1], c[2], c[3]];
    let v2 = [b[0]+px, b[1], b[2]+pz, n[0], n[1], n[2], c[0], c[1], c[2], c[3]];
    let v3 = [b[0]-px, b[1], b[2]-pz, n[0], n[1], n[2], c[0], c[1], c[2], c[3]];

    verts.push(v0);
    verts.push(v1);
    verts.push(v2);
    verts.push(v2);
    verts.push(v1);
    verts.push(v3);
}
