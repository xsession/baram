// ════════════════════════════════════════════════════════════════
//  Landing Tab — project overview + recent projects
// ════════════════════════════════════════════════════════════════

use eframe::egui;
use crate::editor::{BaramApp, Tab};

pub fn show(app: &mut BaramApp, ui: &mut egui::Ui) {
    ui.vertical_centered(|ui| {
        ui.add_space(40.0);
        ui.heading(
            egui::RichText::new("BARAM — CFD Suite")
                .size(32.0)
                .strong(),
        );
        ui.add_space(8.0);
        ui.label(
            egui::RichText::new(
                "Unified workflow:  Geometry → Mesh → Flow → Run",
            )
            .size(14.0)
            .color(egui::Color32::LIGHT_GRAY),
        );
        ui.add_space(24.0);

        // ── Action buttons ─────────────────────────────────────
        ui.horizontal(|ui| {
            ui.add_space(ui.available_width() * 0.25);
            if ui
                .add_sized([160.0, 36.0], egui::Button::new("📁  New Project"))
                .clicked()
            {
                app.project_name = "Untitled".into();
                app.project_path = String::new();
                app.active_tab = Tab::Geometry;
                app.log("Created new project.");
            }
            ui.add_space(12.0);
            if ui
                .add_sized([160.0, 36.0], egui::Button::new("📂  Open Project"))
                .clicked()
            {
                if let Some(path) = rfd::FileDialog::new()
                    .set_title("Open BARAM project")
                    .pick_folder()
                {
                    app.project_name = path
                        .file_name()
                        .map(|s| s.to_string_lossy().to_string())
                        .unwrap_or_default();
                    app.project_path = path.display().to_string();
                    app.active_tab = Tab::Geometry;
                    app.log(format!("Opened project: {}", app.project_path));
                }
            }
        });
        ui.add_space(32.0);

        // ── Recent projects ────────────────────────────────────
        ui.heading("Recent Projects");
        ui.add_space(8.0);
        egui::Grid::new("recent_projects")
            .num_columns(3)
            .spacing([20.0, 6.0])
            .striped(true)
            .show(ui, |ui| {
                ui.label(egui::RichText::new("Name").strong());
                ui.label(egui::RichText::new("Path").strong());
                ui.label("");
                ui.end_row();
                let projects = app.recent_projects.clone();
                for (name, path) in &projects {
                    ui.label(name);
                    ui.label(
                        egui::RichText::new(path)
                            .monospace()
                            .color(egui::Color32::LIGHT_GRAY),
                    );
                    if ui.small_button("Open").clicked() {
                        app.project_name = name.clone();
                        app.project_path = path.clone();
                        app.active_tab = Tab::Geometry;
                        app.log(format!("Opened project: {path}"));
                    }
                    ui.end_row();
                }
            });

        ui.add_space(32.0);

        // ── Quick‑start cards ──────────────────────────────────
        ui.heading("Quick Start");
        ui.add_space(8.0);
        ui.horizontal_wrapped(|ui| {
            for (title, desc) in [
                ("Import STL", "Load an STL surface mesh"),
                ("Import STEP", "Load a CAD model (STEP/IGES)"),
                ("Parametric Box", "Create a box with Hedron CSG"),
                ("Tutorial: BFS", "Backward‑facing step tutorial"),
            ] {
                ui.group(|ui| {
                    ui.set_min_size(egui::vec2(180.0, 80.0));
                    ui.vertical(|ui| {
                        ui.label(egui::RichText::new(title).strong());
                        ui.label(
                            egui::RichText::new(desc)
                                .small()
                                .color(egui::Color32::GRAY),
                        );
                    });
                });
            }
        });
    });
}
