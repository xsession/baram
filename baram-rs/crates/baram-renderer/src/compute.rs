// ════════════════════════════════════════════════════════════════
//  wgpu Compute Pipelines — GPU‑accelerated mesh operations
//
//  Part of the Fyrox‑inspired stack:
//    Fyrox Editor → Custom plugins → Hedron geometry → **wgpu compute**
// ════════════════════════════════════════════════════════════════

/// WGSL compute shader that recalculates flat normals per triangle.
const NORMALS_SHADER: &str = r#"
struct Vertex {
    position: vec3<f32>,
    normal:   vec3<f32>,
    color:    vec4<f32>,
};

@group(0) @binding(0) var<storage, read_write> vertices: array<Vertex>;
@group(0) @binding(1) var<storage, read>        indices:  array<u32>;

@compute @workgroup_size(64)
fn recalc_normals(@builtin(global_invocation_id) gid: vec3<u32>) {
    let tri = gid.x;
    let i0 = indices[tri * 3u];
    let i1 = indices[tri * 3u + 1u];
    let i2 = indices[tri * 3u + 2u];

    let p0 = vertices[i0].position;
    let p1 = vertices[i1].position;
    let p2 = vertices[i2].position;

    let n = normalize(cross(p1 - p0, p2 - p0));

    vertices[i0].normal = n;
    vertices[i1].normal = n;
    vertices[i2].normal = n;
}
"#;

/// WGSL compute shader that applies a 4×4 transform to every vertex.
const TRANSFORM_SHADER: &str = r#"
struct Vertex {
    position: vec3<f32>,
    normal:   vec3<f32>,
    color:    vec4<f32>,
};

struct Params {
    model:      mat4x4<f32>,
    normal_mat: mat4x4<f32>,
};

@group(0) @binding(0) var<storage, read_write> vertices: array<Vertex>;
@group(0) @binding(1) var<uniform>              params:   Params;

@compute @workgroup_size(64)
fn apply_transform(@builtin(global_invocation_id) gid: vec3<u32>) {
    let idx = gid.x;
    let p = vertices[idx].position;
    let n = vertices[idx].normal;

    let tp = params.model * vec4<f32>(p, 1.0);
    vertices[idx].position = tp.xyz;

    let tn = normalize((params.normal_mat * vec4<f32>(n, 0.0)).xyz);
    vertices[idx].normal = tn;
}
"#;

/// Holds compiled wgpu compute pipelines for mesh processing.
pub struct ComputePipelines {
    normals_pipeline: wgpu::ComputePipeline,
    normals_bgl: wgpu::BindGroupLayout,
    transform_pipeline: wgpu::ComputePipeline,
    transform_bgl: wgpu::BindGroupLayout,
}

impl ComputePipelines {
    pub fn new(device: &wgpu::Device) -> Self {
        // ── Normals pipeline ───────────────────────────────────
        let normals_module = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("Compute: normals"),
            source: wgpu::ShaderSource::Wgsl(NORMALS_SHADER.into()),
        });
        let normals_bgl = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("Normals BGL"),
            entries: &[
                wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: false },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 1,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: true },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
            ],
        });
        let normals_pipeline = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("Compute: normals"),
            layout: Some(&device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                label: None,
                bind_group_layouts: &[&normals_bgl],
                push_constant_ranges: &[],
            })),
            module: &normals_module,
            entry_point: "recalc_normals",
            compilation_options: Default::default(),
        });

        // ── Transform pipeline ─────────────────────────────────
        let xform_module = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("Compute: transform"),
            source: wgpu::ShaderSource::Wgsl(TRANSFORM_SHADER.into()),
        });
        let transform_bgl = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("Transform BGL"),
            entries: &[
                wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: false },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 1,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Uniform,
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
            ],
        });
        let transform_pipeline =
            device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
                label: Some("Compute: transform"),
                layout: Some(&device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                    label: None,
                    bind_group_layouts: &[&transform_bgl],
                    push_constant_ranges: &[],
                })),
                module: &xform_module,
                entry_point: "apply_transform",
                compilation_options: Default::default(),
            });

        Self {
            normals_pipeline,
            normals_bgl,
            transform_pipeline,
            transform_bgl,
        }
    }

    /// Dispatch a GPU compute pass to recalculate flat normals.
    ///
    /// `vertex_buf` must be created with `STORAGE` usage and contain
    /// `Vertex` structs.  `index_buf` likewise.
    pub fn recalculate_normals(
        &self,
        device: &wgpu::Device,
        queue: &wgpu::Queue,
        vertex_buf: &wgpu::Buffer,
        index_buf: &wgpu::Buffer,
        num_triangles: u32,
    ) {
        let bg = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("Normals BG"),
            layout: &self.normals_bgl,
            entries: &[
                wgpu::BindGroupEntry { binding: 0, resource: vertex_buf.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 1, resource: index_buf.as_entire_binding() },
            ],
        });
        let mut encoder =
            device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: Some("Normals") });
        {
            let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
                label: Some("Normals"),
                timestamp_writes: None,
            });
            pass.set_pipeline(&self.normals_pipeline);
            pass.set_bind_group(0, &bg, &[]);
            pass.dispatch_workgroups((num_triangles + 63) / 64, 1, 1);
        }
        queue.submit(std::iter::once(encoder.finish()));
    }

    /// Dispatch a GPU compute pass to apply a 4×4 transform to
    /// every vertex in the buffer.
    pub fn apply_transform(
        &self,
        device: &wgpu::Device,
        queue: &wgpu::Queue,
        vertex_buf: &wgpu::Buffer,
        model: &glam::Mat4,
        num_vertices: u32,
    ) {
        let normal_mat = model.inverse().transpose();

        #[repr(C)]
        #[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
        struct Params {
            model: [[f32; 4]; 4],
            normal_mat: [[f32; 4]; 4],
        }

        let params = Params {
            model: model.to_cols_array_2d(),
            normal_mat: normal_mat.to_cols_array_2d(),
        };

        let param_buf = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Transform params"),
            size: std::mem::size_of::<Params>() as u64,
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        queue.write_buffer(&param_buf, 0, bytemuck::bytes_of(&params));

        let bg = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("Transform BG"),
            layout: &self.transform_bgl,
            entries: &[
                wgpu::BindGroupEntry { binding: 0, resource: vertex_buf.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 1, resource: param_buf.as_entire_binding() },
            ],
        });
        let mut encoder =
            device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: Some("Transform") });
        {
            let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
                label: Some("Transform"),
                timestamp_writes: None,
            });
            pass.set_pipeline(&self.transform_pipeline);
            pass.set_bind_group(0, &bg, &[]);
            pass.dispatch_workgroups((num_vertices + 63) / 64, 1, 1);
        }
        queue.submit(std::iter::once(encoder.finish()));
    }
}
