// ════════════════════════════════════════════════════════════════
//  Run Tab — solver control + residual monitoring
// ════════════════════════════════════════════════════════════════

use eframe::egui;
use crate::editor::BaramApp;

const SOLVERS: &[&str] = &["OpenFOAM", "Elmer", "FluidX3D"];

pub fn show(app: &mut BaramApp, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        ui.label(egui::RichText::new("Run").strong());
        ui.separator();

        egui::ComboBox::from_label("Solver Backend")
            .selected_text(SOLVERS[app.solver_idx])
            .show_ui(ui, |ui| {
                for (i, name) in SOLVERS.iter().enumerate() {
                    ui.selectable_value(&mut app.solver_idx, i, *name);
                }
            });

        if !app.solver_running {
            if ui
                .add(egui::Button::new("▶ Start").fill(egui::Color32::from_rgb(40, 130, 60)))
                .clicked()
            {
                app.solver_running = true;
                app.residuals.clear();
                app.log(format!("Solver started: {}", SOLVERS[app.solver_idx]));
            }
        } else if ui
            .add(egui::Button::new("■ Stop").fill(egui::Color32::from_rgb(180, 50, 50)))
            .clicked()
        {
            app.solver_running = false;
            app.log("Solver stopped.");
        }
    });

    ui.separator();

    // ── Two‑column layout: settings + chart ────────────────────
    ui.columns(2, |cols| {
        // Left: run settings
        cols[0].heading("Run Settings");
        cols[0].horizontal(|ui| {
            ui.label("Iterations:");
            ui.add(
                egui::DragValue::new(&mut app.iterations)
                    .speed(10)
                    .range(1..=1_000_000),
            );
        });
        cols[0].separator();
        cols[0].heading("Monitors");
        cols[0].label("• Force: inlet (drag / lift)");
        cols[0].label("• Point: probe (0.1, 0.05, 0)");

        cols[0].separator();
        cols[0].heading("Status");
        if app.solver_running {
            // Fake residual data
            if app.residuals.len() < app.iterations as usize {
                let n = app.residuals.len() as f32;
                let val = (-n * 0.005).exp() * 0.5 + 0.0001;
                app.residuals.push(val);
            }
            cols[0].label(
                egui::RichText::new(format!(
                    "Iteration {} / {}",
                    app.residuals.len(),
                    app.iterations
                ))
                .strong(),
            );
        } else {
            cols[0].label("Idle");
        }

        // Right: residual chart (simple painter-based)
        cols[1].heading("Residuals");
        if app.residuals.is_empty() {
            cols[1].label("No data yet.");
        } else {
            let chart_h = 300.0_f32;
            let (chart_rect, _chart_resp) =
                cols[1].allocate_exact_size(egui::vec2(cols[1].available_width(), chart_h), egui::Sense::hover());
            let painter = cols[1].painter_at(chart_rect);
            painter.rect_filled(chart_rect, 4.0, egui::Color32::from_rgb(25, 28, 32));

            // Scale: x = iteration index, y = log10(residual) range [-6, 0]
            let n = app.residuals.len();
            let x_scale = chart_rect.width() / n.max(1) as f32;
            let y_min = -6.0_f32;
            let y_max = 0.0_f32;
            let y_range = y_max - y_min;

            let points: Vec<egui::Pos2> = app.residuals.iter().enumerate().map(|(i, &v)| {
                let x = chart_rect.left() + i as f32 * x_scale;
                let y_val = (v as f32).log10().clamp(y_min, y_max);
                let y = chart_rect.bottom() - ((y_val - y_min) / y_range) * chart_rect.height();
                egui::pos2(x, y)
            }).collect();

            // Draw grid lines
            for &tick in &[-5.0_f32, -4.0, -3.0, -2.0, -1.0] {
                let y = chart_rect.bottom() - ((tick - y_min) / y_range) * chart_rect.height();
                painter.line_segment(
                    [egui::pos2(chart_rect.left(), y), egui::pos2(chart_rect.right(), y)],
                    egui::Stroke::new(0.5, egui::Color32::from_white_alpha(30)),
                );
                painter.text(
                    egui::pos2(chart_rect.left() + 2.0, y - 8.0),
                    egui::Align2::LEFT_BOTTOM,
                    format!("{tick}"),
                    egui::FontId::monospace(9.0),
                    egui::Color32::from_white_alpha(80),
                );
            }

            // Draw line
            if points.len() >= 2 {
                let stroke = egui::Stroke::new(1.5, egui::Color32::from_rgb(100, 200, 255));
                for pair in points.windows(2) {
                    painter.line_segment([pair[0], pair[1]], stroke);
                }
            }

            // Axis labels
            painter.text(
                egui::pos2(chart_rect.center().x, chart_rect.bottom() - 2.0),
                egui::Align2::CENTER_BOTTOM,
                "Iteration",
                egui::FontId::monospace(10.0),
                egui::Color32::from_white_alpha(100),
            );
        }
    });
}
