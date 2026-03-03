// ════════════════════════════════════════════════════════════════
//  Flow Tab — boundary conditions, models, materials
// ════════════════════════════════════════════════════════════════

use eframe::egui;
use crate::editor::BaramApp;

const FLOW_TYPES: &[&str] = &["Incompressible", "Compressible", "Multiphase (VOF)"];
const TURBULENCE: &[&str] = &[
    "Inviscid",
    "Laminar",
    "Spalart–Allmaras",
    "k–ε Standard",
    "k–ε Realizable",
    "k–ω SST",
    "LES (Smagorinsky)",
];

pub fn show(app: &mut BaramApp, ui: &mut egui::Ui, ctx: &egui::Context) {
    ui.horizontal(|ui| {
        ui.label(egui::RichText::new("Flow").strong());
        ui.separator();

        if ui.button("💾 Save Config").clicked() {
            app.log("Flow configuration saved (placeholder).");
        }
        if ui.button("📄 Generate Case").clicked() {
            app.log("OpenFOAM case generated (placeholder).");
        }
    });

    ui.separator();

    // ── Settings panel (left) ──────────────────────────────────
    egui::SidePanel::left("flow_settings")
        .default_width(280.0)
        .resizable(true)
        .show_inside(ui, |ui| {
            // General
            ui.heading("General");
            egui::ComboBox::from_label("Flow type")
                .selected_text(FLOW_TYPES[app.flow_type_idx])
                .show_ui(ui, |ui| {
                    for (i, name) in FLOW_TYPES.iter().enumerate() {
                        ui.selectable_value(&mut app.flow_type_idx, i, *name);
                    }
                });

            ui.separator();

            // Turbulence
            ui.heading("Turbulence");
            egui::ComboBox::from_label("Model")
                .selected_text(TURBULENCE[app.turbulence_idx])
                .show_ui(ui, |ui| {
                    for (i, name) in TURBULENCE.iter().enumerate() {
                        ui.selectable_value(&mut app.turbulence_idx, i, *name);
                    }
                });

            ui.separator();

            // Boundary Conditions (overview)
            ui.heading("Boundary Conditions");
            ui.label("• inlet — Velocity Inlet");
            ui.label("• outlet — Pressure Outlet");
            ui.label("• walls — No‑slip Wall");
            ui.label("• symmetry — Symmetry");

            ui.separator();

            // Materials
            ui.heading("Materials");
            ui.label("Air: ρ = 1.225 kg/m³, μ = 1.789e‑5 Pa·s");
        });

    // ── Viewport ───────────────────────────────────────────────
    crate::tabs::geometry::show_viewport(app, ui, ctx);
}
