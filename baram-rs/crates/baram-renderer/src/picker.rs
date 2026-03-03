use bytemuck;
use std::sync::mpsc;

// ════════════════════════════════════════════════════════════════
//  GPU-accelerated face picking — render triangle IDs to a texture
//  then read back the pixel under the cursor.
// ════════════════════════════════════════════════════════════════

/// WGSL shader that outputs triangle ID as color.
#[allow(dead_code)]
const PICK_SHADER: &str = r#"
struct CameraUniform {
    view_proj: mat4x4<f32>,
    eye: vec4<f32>,
};
@group(0) @binding(0) var<uniform> camera: CameraUniform;

struct PickInput {
    @location(0) position: vec3<f32>,
    @location(1) normal: vec3<f32>,
    @location(2) color: vec4<f32>,
};

struct PickOutput {
    @builtin(position) clip_position: vec4<f32>,
};

@vertex
fn vs_pick(in: PickInput) -> PickOutput {
    var out: PickOutput;
    out.clip_position = camera.view_proj * vec4<f32>(in.position, 1.0);
    return out;
}

// Each triangle gets a unique ID encoded in @builtin(primitive_index) — not
// available in all backends. Fallback: encode the ID in vertex color during
// upload, then just output that.
@fragment
fn fs_pick(in: PickOutput) -> @location(0) vec4<u32> {
    // Placeholder: use screen coords for now; actual implementation
    // encodes triangle ID via vertex attribute in the pick upload pass.
    return vec4<u32>(0u, 0u, 0u, 1u);
}
"#;

/// Result of a pick query.
#[derive(Debug, Clone, Copy)]
pub struct PickResult {
    pub mesh_id: u32,
    pub triangle_id: u32,
}

/// Face picker that renders mesh IDs to an off-screen texture
/// and reads back the pixel under the cursor.
pub struct FacePicker {
    pick_texture: wgpu::Texture,
    pick_view: wgpu::TextureView,
    readback_buffer: wgpu::Buffer,
    width: u32,
    height: u32,
}

impl FacePicker {
    pub fn new(device: &wgpu::Device, width: u32, height: u32) -> Self {
        let (texture, view) = create_pick_texture(device, width, height);
        let readback_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Pick Readback"),
            size: 16, // 4 × u32
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        Self {
            pick_texture: texture,
            pick_view: view,
            readback_buffer,
            width,
            height,
        }
    }

    pub fn resize(&mut self, device: &wgpu::Device, width: u32, height: u32) {
        let (texture, view) = create_pick_texture(device, width, height);
        self.pick_texture = texture;
        self.pick_view = view;
        self.width = width;
        self.height = height;
    }

    /// Schedule a readback of the pixel at (x, y) from the pick texture.
    /// Returns the command encoder; caller submits and then calls `read_result`.
    pub fn copy_pixel(
        &self,
        device: &wgpu::Device,
        x: u32,
        y: u32,
    ) -> wgpu::CommandEncoder {
        let mut encoder =
            device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: Some("Pick Copy") });
        encoder.copy_texture_to_buffer(
            wgpu::ImageCopyTexture {
                texture: &self.pick_texture,
                mip_level: 0,
                origin: wgpu::Origin3d {
                    x: x.min(self.width.saturating_sub(1)),
                    y: y.min(self.height.saturating_sub(1)),
                    z: 0,
                },
                aspect: wgpu::TextureAspect::All,
            },
            wgpu::ImageCopyBuffer {
                buffer: &self.readback_buffer,
                layout: wgpu::ImageDataLayout {
                    offset: 0,
                    bytes_per_row: Some(16),
                    rows_per_image: Some(1),
                },
            },
            wgpu::Extent3d {
                width: 1,
                height: 1,
                depth_or_array_layers: 1,
            },
        );
        encoder
    }

    /// Read the result after the GPU has finished (synchronous).
    pub fn read_result(&self, device: &wgpu::Device) -> Option<PickResult> {
        let slice = self.readback_buffer.slice(..);
        let (tx, rx) = mpsc::channel();
        slice.map_async(wgpu::MapMode::Read, move |result| {
            let _ = tx.send(result);
        });
        device.poll(wgpu::Maintain::Wait);
        rx.recv().ok()?.ok()?;

        let data = slice.get_mapped_range();
        let ids: &[u32] = bytemuck::cast_slice(&data);
        let mesh_id = ids[0];
        let triangle_id = ids[1];
        drop(data);
        self.readback_buffer.unmap();

        if mesh_id == 0 && triangle_id == 0 {
            None // background
        } else {
            Some(PickResult {
                mesh_id,
                triangle_id,
            })
        }
    }

    pub fn texture_view(&self) -> &wgpu::TextureView {
        &self.pick_view
    }
}

fn create_pick_texture(
    device: &wgpu::Device,
    width: u32,
    height: u32,
) -> (wgpu::Texture, wgpu::TextureView) {
    let texture = device.create_texture(&wgpu::TextureDescriptor {
        label: Some("Pick Texture"),
        size: wgpu::Extent3d {
            width: width.max(1),
            height: height.max(1),
            depth_or_array_layers: 1,
        },
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format: wgpu::TextureFormat::Rgba32Uint,
        usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::COPY_SRC,
        view_formats: &[],
    });
    let view = texture.create_view(&Default::default());
    (texture, view)
}
