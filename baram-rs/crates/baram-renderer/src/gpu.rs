// ════════════════════════════════════════════════════════════════
//  GPU context — wgpu device + surface initialisation
//  Works on both native (Vulkan/DX12/Metal) and WASM (WebGPU)
// ════════════════════════════════════════════════════════════════

pub struct GpuContext {
    pub device: wgpu::Device,
    pub queue: wgpu::Queue,
    pub surface: Option<wgpu::Surface<'static>>,
    pub surface_config: Option<wgpu::SurfaceConfiguration>,
    pub adapter: wgpu::Adapter,
}

impl GpuContext {
    /// Create a new GPU context.
    /// On native: pass a window handle (winit etc.).
    /// On WASM: pass an `HtmlCanvasElement` target.
    pub async fn new(
        instance: &wgpu::Instance,
        surface: Option<wgpu::Surface<'static>>,
        width: u32,
        height: u32,
    ) -> Result<Self, String> {
        let adapter = instance
            .request_adapter(&wgpu::RequestAdapterOptions {
                power_preference: wgpu::PowerPreference::HighPerformance,
                compatible_surface: surface.as_ref(),
                force_fallback_adapter: false,
            })
            .await
            .ok_or("No suitable GPU adapter found")?;

        let (device, queue) = adapter
            .request_device(
                &wgpu::DeviceDescriptor {
                    label: Some("BARAM GPU Device"),
                    required_features: wgpu::Features::empty(),
                    required_limits: wgpu::Limits::downlevel_webgl2_defaults()
                        .using_resolution(adapter.limits()),
                },
                None,
            )
            .await
            .map_err(|e| format!("Failed to create device: {e}"))?;

        let surface_config = surface.as_ref().map(|s| {
            let caps = s.get_capabilities(&adapter);
            let format = caps
                .formats
                .iter()
                .find(|f| f.is_srgb())
                .copied()
                .unwrap_or(caps.formats[0]);
            let config = wgpu::SurfaceConfiguration {
                usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
                format,
                width,
                height,
                present_mode: wgpu::PresentMode::AutoVsync,
                alpha_mode: caps.alpha_modes[0],
                view_formats: vec![],
                desired_maximum_frame_latency: 2,
            };
            s.configure(&device, &config);
            config
        });

        Ok(Self {
            device,
            queue,
            surface,
            surface_config,
            adapter,
        })
    }

    pub fn resize(&mut self, width: u32, height: u32) {
        if let (Some(surface), Some(config)) =
            (self.surface.as_ref(), self.surface_config.as_mut())
        {
            config.width = width.max(1);
            config.height = height.max(1);
            surface.configure(&self.device, config);
        }
    }

    pub fn surface_format(&self) -> wgpu::TextureFormat {
        self.surface_config
            .as_ref()
            .map(|c| c.format)
            .unwrap_or(wgpu::TextureFormat::Bgra8UnormSrgb)
    }
}
