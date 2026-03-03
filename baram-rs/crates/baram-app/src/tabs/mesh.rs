// ════════════════════════════════════════════════════════════════
//  Mesh Tab — mesh generation settings
// ════════════════════════════════════════════════════════════════

use eframe::egui;
use crate::editor::BaramApp;

pub fn show(app: &mut BaramApp, ui: &mut egui::Ui, ctx: &egui::Context) {
    ui.horizontal(|ui| {
        ui.label(egui::RichText::new("Mesh").strong());
        ui.separator();

        if ui.button("▶ Generate Mesh").clicked() {
            app.mesh_generated = true;
            app.log("Mesh generation started (placeholder).");
        }
        if ui.button("🔍 Check Quality").clicked() {
            app.log("Mesh quality check: OK (placeholder).");
        }
    });

    ui.separator();

    // ── Settings ───────────────────────────────────────────────
    egui::SidePanel::left("mesh_settings")
        .default_width(280.0)
        .resizable(true)
        .show_inside(ui, |ui| {
            ui.heading("Base Grid");
            ui.horizontal(|ui| {
                ui.label("Cell size:");
                ui.add(
                    egui::DragValue::new(&mut app.base_cell_size)
                        .speed(0.001)
                        .range(0.0001..=10.0)
                        .suffix(" m"),
                );
            });

            ui.separator();
            ui.heading("Castellated Mesh");
            ui.label("• Surface refinement levels: 2–4");
            ui.label("• Feature edge angle: 150°");

            ui.separator();
            ui.heading("Snap");
            ui.label("• Iterations: 5");
            ui.label("• Relaxation: 0.5");

            ui.separator();
            ui.heading("Boundary Layers");
            ui.label("• Layers: 3");
            ui.label("• Expansion ratio: 1.2");
            ui.label("• Final thickness: 0.001 m");

            ui.separator();
            if app.mesh_generated {
                ui.label(
                    egui::RichText::new("✔ Mesh generated")
                        .color(egui::Color32::GREEN),
                );
            }
        });

    // ── Viewport ───────────────────────────────────────────────
    crate::tabs::geometry::show_viewport(app, ui, ctx);
}
