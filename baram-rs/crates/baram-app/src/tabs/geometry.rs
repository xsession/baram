// ════════════════════════════════════════════════════════════════
//  Geometry Tab — 3‑D CAD / CSG editor (Fyrox‑style)
//
//  Left: scene tree (shown by editor shell)
//  Centre: 3‑D viewport with the model
//  Right: inspector (shown by editor shell)
//  Toolbar: Add primitives · Import · Boolean ops
// ════════════════════════════════════════════════════════════════

use eframe::egui;
use baram_renderer::hedron::CsgPrimitive;
use baram_renderer::scene::{NodeComponent, SceneNode};
use glam::Vec3;

use crate::editor::BaramApp;

const PRIMITIVES: &[&str] = &["Box", "Cylinder", "Sphere", "Cone", "Torus"];

pub fn show(app: &mut BaramApp, ui: &mut egui::Ui, ctx: &egui::Context) {
    // ── Local toolbar ──────────────────────────────────────────
    ui.horizontal(|ui| {
        ui.label(egui::RichText::new("Geometry").strong());
        ui.separator();

        // Primitive selector
        egui::ComboBox::from_label("Primitive")
            .selected_text(PRIMITIVES[app.hedron_primitive])
            .show_ui(ui, |ui| {
                for (i, name) in PRIMITIVES.iter().enumerate() {
                    ui.selectable_value(&mut app.hedron_primitive, i, *name);
                }
            });

        if ui.button("➕ Add").clicked() {
            let color = [0.7, 0.7, 0.7, 1.0];
            let prim = match app.hedron_primitive {
                0 => CsgPrimitive::Box { half_extents: Vec3::splat(0.5) },
                1 => CsgPrimitive::Cylinder { radius: 0.5, height: 1.0, segments: 32 },
                2 => CsgPrimitive::Sphere { radius: 0.5, rings: 24, sectors: 32 },
                3 => CsgPrimitive::Cone { radius: 0.5, height: 1.0, segments: 32 },
                4 => CsgPrimitive::Torus {
                    major_radius: 0.5,
                    minor_radius: 0.15,
                    major_seg: 32,
                    minor_seg: 16,
                },
                _ => CsgPrimitive::Box { half_extents: Vec3::splat(0.5) },
            };

            let name = format!("{} {}", PRIMITIVES[app.hedron_primitive], app.scene.nodes.len());
            let mut node = SceneNode::new(name.clone());
            node.component = NodeComponent::CsgPrimitive(prim.clone());
            let handle = app.scene.add_root_node(node);
            app.scene.selected = handle;

            // Tessellate and upload to viewport
            let mesh = prim.tessellate(color);
            {
                let device = &*app.device;
                if let Some(vp) = &mut app.viewport {
                    vp.upload_mesh(device, &mesh);
                }
            }
            app.log(format!("Added CSG primitive: {name}"));
        }

        ui.separator();

        if ui.button("📁 Import STL").clicked() {
            if let Some(path) = rfd::FileDialog::new()
                .add_filter("STL", &["stl"])
                .set_title("Import STL mesh")
                .pick_file()
            {
                match baram_mesh::stl::load_stl(&path) {
                    Ok(solids) => {
                        let all_tris: Vec<_> = solids.iter().flat_map(|s| s.triangles.iter()).cloned().collect();
                        let tri_mesh = baram_mesh::polydata::TriMesh::from_stl_triangles(&all_tris);
                        let name = path
                            .file_stem()
                            .map(|s| s.to_string_lossy().to_string())
                            .unwrap_or_else(|| "imported".into());
                        let mut node = SceneNode::new(name.clone());
                        node.component = NodeComponent::Mesh {
                            mesh_index: 0,
                            visible: true,
                        };
                        let h = app.scene.add_root_node(node);
                        app.scene.selected = h;
                        {
                            let device = &*app.device;
                            if let Some(vp) = &mut app.viewport {
                                vp.upload_mesh(device, &tri_mesh);
                            }
                        }
                        app.log(format!(
                            "Imported STL '{name}': {} triangles",
                            tri_mesh.num_triangles()
                        ));
                    }
                    Err(e) => {
                        app.log(format!("STL import error: {e}"));
                    }
                }
            }
        }

        if ui.button("📐 Import STEP").clicked() {
            if let Some(path) = rfd::FileDialog::new()
                .add_filter("STEP / STP", &["step", "stp", "STEP", "STP"])
                .set_title("Import STEP CAD model")
                .pick_file()
            {
                app.log(format!("Loading STEP file: {} …", path.display()));
                match baram_mesh::step::load_step(&path, 0.01) {
                    Ok(step_solids) => {
                        let mut total_tris = 0usize;
                        for solid in &step_solids {
                            let mut node = SceneNode::new(solid.name.clone());
                            node.component = NodeComponent::Mesh {
                                mesh_index: 0,
                                visible: true,
                            };
                            let h = app.scene.add_root_node(node);
                            app.scene.selected = h;
                            {
                                let device = &*app.device;
                                if let Some(vp) = &mut app.viewport {
                                    vp.upload_mesh(device, &solid.mesh);
                                }
                            }
                            total_tris += solid.mesh.num_triangles();
                        }
                        app.log(format!(
                            "Imported STEP: {} shell(s), {} total triangles",
                            step_solids.len(),
                            total_tris
                        ));
                    }
                    Err(e) => {
                        app.log(format!("STEP import error: {e}"));
                    }
                }
            }
        }

        if ui.button("🗑 Delete selected").clicked() {
            let sel = app.scene.selected;
            if sel.is_some() {
                app.scene.remove_node(sel);
                app.scene.selected = Default::default();
                app.log("Deleted selected node.");
            }
        }
    });

    ui.separator();

    // ── 3‑D Viewport ──────────────────────────────────────────
    show_viewport(app, ui, ctx);
}

/// Draw the 3‑D viewport inside the available area.
pub fn show_viewport(app: &mut BaramApp, ui: &mut egui::Ui, _ctx: &egui::Context) {
    let avail = ui.available_size();
    let (rect, response) = ui.allocate_exact_size(avail, egui::Sense::click_and_drag());

    // Camera interaction
    if response.dragged_by(egui::PointerButton::Primary) {
        let d = response.drag_delta();
        app.camera.orbit(-d.x * 0.005, -d.y * 0.005);
    }
    if response.dragged_by(egui::PointerButton::Middle)
        || response.dragged_by(egui::PointerButton::Secondary)
    {
        let d = response.drag_delta();
        app.camera.pan(d.x, d.y);
    }
    let scroll = ui.input(|i| i.smooth_scroll_delta.y);
    if scroll.abs() > 0.1 {
        app.camera.zoom(1.0 - scroll * 0.002);
    }

    // Update aspect ratio
    if avail.x > 1.0 && avail.y > 1.0 {
        app.camera.aspect = avail.x / avail.y;
    }

    // Render & display
    if app.viewport.is_some() {
        let w = avail.x as u32;
        let h = avail.y as u32;
        let device = &*app.device;
        let queue = &*app.queue;
        let format = app.target_format;
        let camera_uni = app.camera.uniform();
        let vp = app.viewport.as_mut().unwrap();
        vp.resize(device, format, w, h);
        vp.render_frame(device, queue, &camera_uni);

        // Draw a dark rectangle as background
        ui.painter()
            .rect_filled(rect, 0.0, egui::Color32::from_rgb(30, 33, 38));

        // Overlay text (until egui texture registration is wired)
        ui.painter().text(
            rect.center(),
            egui::Align2::CENTER_CENTER,
            format!("3D Viewport  {}×{}\nDrag to orbit · Scroll to zoom", w, h),
            egui::FontId::proportional(14.0),
            egui::Color32::from_white_alpha(120),
        );
    } else {
        ui.painter()
            .rect_filled(rect, 0.0, egui::Color32::from_rgb(30, 33, 38));
        ui.painter().text(
            rect.center(),
            egui::Align2::CENTER_CENTER,
            "No viewport",
            egui::FontId::proportional(14.0),
            egui::Color32::GRAY,
        );
    }
}
