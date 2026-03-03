//! BARAM — unified CFD desktop application.
//!
//! Single executable that integrates:
//!   Landing → Geometry Editor → Mesh → Flow Setup → Run
//!
//! Architecture (Fyrox‑inspired):
//!   eframe (egui + wgpu + winit)
//!     ↓
//!   Custom tab plugins
//!     ↓
//!   Hedron geometry backend
//!     ↓
//!   wgpu compute pipelines

fn main() -> eframe::Result<()> {
    // Logging
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .init();

    let native_options = eframe::NativeOptions {
        renderer: eframe::Renderer::Wgpu,
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1600.0, 900.0])
            .with_title("BARAM — CFD Suite"),
        ..Default::default()
    };

    eframe::run_native(
        "BARAM",
        native_options,
        Box::new(|cc| Ok(Box::new(baram_app::editor::BaramApp::new(cc)))),
    )
}
