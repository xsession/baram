// ════════════════════════════════════════════════════════════════
//  Editor — main application shell (Fyrox Editor‑style)
//
//  Tabs:  Landing │ Geometry │ Mesh │ Flow │ Run
//  Dock:  Scene tree │ 3‑D Viewport │ Inspector │ Console
// ════════════════════════════════════════════════════════════════

use std::sync::Arc;

use eframe::egui;
use baram_renderer::camera::OrbitCamera;
use baram_renderer::scene::{Handle, NodeComponent, Scene, SceneNode};
use glam::Vec3;

use crate::tabs;
use crate::viewport::ViewportRenderer;

// ── Workflow tab ───────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Tab {
    Landing,
    Geometry,
    Mesh,
    Flow,
    Run,
}

// ── Application state ──────────────────────────────────────────

pub struct BaramApp {
    // GPU state (from eframe's wgpu backend)
    pub(crate) device: Arc<wgpu::Device>,
    pub(crate) queue: Arc<wgpu::Queue>,
    pub(crate) target_format: wgpu::TextureFormat,

    // Scene graph
    pub scene: Scene,

    // Camera
    pub camera: OrbitCamera,

    // Viewport renderer (off‑screen → egui texture)
    pub(crate) viewport: Option<ViewportRenderer>,

    // UI state
    pub active_tab: Tab,
    pub scene_tree_open: bool,
    pub inspector_open: bool,
    pub console_open: bool,
    pub console_log: Vec<String>,

    // Project
    pub project_name: String,
    pub project_path: String,

    // Landing
    pub recent_projects: Vec<(String, String)>, // (name, path)

    // Geometry tab
    pub hedron_primitive: usize, // index into PRIMITIVES list

    // Mesh tab state
    pub base_cell_size: f32,
    pub mesh_generated: bool,

    // Flow tab state
    pub flow_type_idx: usize,
    pub turbulence_idx: usize,

    // Run tab state
    pub solver_idx: usize,
    pub iterations: u32,
    pub solver_running: bool,
    pub residuals: Vec<f32>,
}

impl BaramApp {
    pub fn new(cc: &eframe::CreationContext<'_>) -> Self {
        let wgpu_state = cc.wgpu_render_state.as_ref().expect("wgpu backend required");
        let device = wgpu_state.device.clone();
        let queue = wgpu_state.queue.clone();
        let format = wgpu_state.target_format;

        // Default scene with a light
        let mut scene = Scene::new();
        let mut light_node = SceneNode::new("Directional Light");
        light_node.component = NodeComponent::Light {
            direction: Vec3::new(0.5, -1.0, 0.3).normalize(),
            color: Vec3::ONE,
            intensity: 1.0,
        };
        scene.add_root_node(light_node);

        let mut camera = OrbitCamera::default();
        camera.distance = 5.0;
        camera.fit_to_bounds(Vec3::ZERO, 3.0);

        Self {
            device,
            queue,
            target_format: format,
            scene,
            camera,
            viewport: None,
            active_tab: Tab::Landing,
            scene_tree_open: true,
            inspector_open: true,
            console_open: true,
            console_log: vec!["BARAM initialised.".into()],
            project_name: String::new(),
            project_path: String::new(),
            recent_projects: vec![
                ("Tutorial — Backward Facing Step".into(), "~/baram-projects/bfs".into()),
                ("Ahmed Body".into(), "~/baram-projects/ahmed".into()),
            ],
            hedron_primitive: 0,
            base_cell_size: 0.01,
            mesh_generated: false,
            flow_type_idx: 0,
            turbulence_idx: 0,
            solver_idx: 0,
            iterations: 1000,
            solver_running: false,
            residuals: Vec::new(),
        }
    }

    pub(crate) fn log(&mut self, msg: impl Into<String>) {
        self.console_log.push(msg.into());
    }
}

// ── eframe::App ────────────────────────────────────────────────

impl eframe::App for BaramApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // ── Render 3‑D viewport to off‑screen texture ──────────
        // (only when a viewport‑bearing tab is active)
        let needs_viewport = matches!(
            self.active_tab,
            Tab::Geometry | Tab::Mesh | Tab::Flow
        );
        if needs_viewport {
            // Ensure viewport renderer exists
            if self.viewport.is_none() {
                self.viewport = Some(ViewportRenderer::new(
                    &self.device,
                    self.target_format,
                    800,
                    600,
                ));
            }
        }

        // ── Top toolbar ────────────────────────────────────────
        egui::TopBottomPanel::top("toolbar").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.heading("BARAM");
                ui.separator();

                // Tab bar
                for (tab, label) in [
                    (Tab::Landing,  "  Landing  "),
                    (Tab::Geometry, "  Geometry  "),
                    (Tab::Mesh,     "  Mesh  "),
                    (Tab::Flow,     "  Flow  "),
                    (Tab::Run,      "  Run  "),
                ] {
                    if ui.selectable_label(self.active_tab == tab, label).clicked() {
                        self.active_tab = tab;
                    }
                }

                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if !self.project_name.is_empty() {
                        ui.label(
                            egui::RichText::new(format!("Project: {}", self.project_name))
                                .small()
                                .color(egui::Color32::LIGHT_GRAY),
                        );
                    }
                });
            });
        });

        // ── Status bar ─────────────────────────────────────────
        egui::TopBottomPanel::bottom("statusbar").show(ctx, |ui| {
            ui.horizontal(|ui| {
                if self.solver_running {
                    ui.label(egui::RichText::new("● Solver running").color(egui::Color32::GREEN));
                } else {
                    ui.label(egui::RichText::new("○ Idle").color(egui::Color32::GRAY));
                }
                ui.separator();
                ui.label(format!("Scene nodes: {}", self.scene.nodes.len()));
            });
        });

        // ── Console panel (bottom) ─────────────────────────────
        if self.console_open && !matches!(self.active_tab, Tab::Landing) {
            egui::TopBottomPanel::bottom("console")
                .resizable(true)
                .default_height(120.0)
                .show(ctx, |ui| {
                    ui.horizontal(|ui| {
                        ui.heading("Console");
                        if ui.small_button("Clear").clicked() {
                            self.console_log.clear();
                        }
                    });
                    egui::ScrollArea::vertical()
                        .auto_shrink([false, false])
                        .stick_to_bottom(true)
                        .show(ui, |ui| {
                            for line in &self.console_log {
                                ui.label(egui::RichText::new(line).monospace().size(11.0));
                            }
                        });
                });
        }

        // ── Scene tree (left panel) ────────────────────────────
        if self.scene_tree_open && !matches!(self.active_tab, Tab::Landing | Tab::Run) {
            egui::SidePanel::left("scene_tree")
                .default_width(200.0)
                .resizable(true)
                .show(ctx, |ui| {
                    ui.heading("Scene");
                    ui.separator();
                    let roots: Vec<_> = self.scene.root_nodes.clone();
                    for handle in &roots {
                        draw_scene_tree(ui, &mut self.scene, *handle);
                    }
                });
        }

        // ── Inspector (right panel) ────────────────────────────
        if self.inspector_open && !matches!(self.active_tab, Tab::Landing | Tab::Run) {
            egui::SidePanel::right("inspector")
                .default_width(260.0)
                .resizable(true)
                .show(ctx, |ui| {
                    ui.heading("Inspector");
                    ui.separator();
                    let sel = self.scene.selected;
                    if let Some(node) = self.scene.nodes.get_mut(sel) {
                        ui.label(egui::RichText::new(&node.name).strong());
                        ui.separator();

                        // Transform
                        ui.label("Transform");
                        ui.horizontal(|ui| {
                            ui.label("Pos");
                            ui.add(egui::DragValue::new(&mut node.transform.position.x).speed(0.01).prefix("X:"));
                            ui.add(egui::DragValue::new(&mut node.transform.position.y).speed(0.01).prefix("Y:"));
                            ui.add(egui::DragValue::new(&mut node.transform.position.z).speed(0.01).prefix("Z:"));
                        });
                        ui.horizontal(|ui| {
                            ui.label("Scl");
                            ui.add(egui::DragValue::new(&mut node.transform.scale.x).speed(0.01).prefix("X:"));
                            ui.add(egui::DragValue::new(&mut node.transform.scale.y).speed(0.01).prefix("Y:"));
                            ui.add(egui::DragValue::new(&mut node.transform.scale.z).speed(0.01).prefix("Z:"));
                        });

                        ui.separator();
                        // Component‑specific
                        match &node.component {
                            NodeComponent::Mesh { mesh_index, .. } => {
                                ui.label(format!("Mesh index: {mesh_index}"));
                            }
                            NodeComponent::Boundary { boundary_name, .. } => {
                                ui.label(format!("Boundary: {boundary_name}"));
                            }
                            NodeComponent::CsgPrimitive(prim) => {
                                ui.label(format!("CSG: {:?}", std::mem::discriminant(prim)));
                            }
                            NodeComponent::Light { intensity, .. } => {
                                ui.label(format!("Light intensity: {intensity:.2}"));
                            }
                            _ => {
                                ui.label("(empty node)");
                            }
                        }
                    } else {
                        ui.label("No selection");
                    }
                });
        }

        // ── Central area (tab content + viewport) ──────────────
        egui::CentralPanel::default().show(ctx, |ui| {
            match self.active_tab {
                Tab::Landing  => tabs::landing::show(self, ui),
                Tab::Geometry => tabs::geometry::show(self, ui, ctx),
                Tab::Mesh     => tabs::mesh::show(self, ui, ctx),
                Tab::Flow     => tabs::flow::show(self, ui, ctx),
                Tab::Run      => tabs::run::show(self, ui),
            }
        });
    }
}

// ── Scene tree recursive drawer ────────────────────────────────

fn draw_scene_tree(
    ui: &mut egui::Ui,
    scene: &mut Scene,
    handle: Handle<SceneNode>,
) {
    let (name, children, component_tag) = {
        let Some(node) = scene.nodes.get(handle) else { return };
        let tag = match &node.component {
            NodeComponent::Empty => "",
            NodeComponent::Mesh { .. } => " 🔲",
            NodeComponent::Boundary { .. } => " 🏷",
            NodeComponent::CellZone { .. } => " ⬡",
            NodeComponent::CsgPrimitive(_) => " ◆",
            NodeComponent::Light { .. } => " 💡",
        };
        (node.name.clone(), node.children.clone(), tag)
    };

    let is_selected = scene.selected == handle;
    let label = format!("{name}{component_tag}");

    if children.is_empty() {
        let resp = ui.selectable_label(is_selected, &label);
        if resp.clicked() {
            scene.selected = handle;
        }
    } else {
        let id = ui.make_persistent_id(handle.index());
        egui::CollapsingHeader::new(&label)
            .id_source(id)
            .default_open(true)
            .show(ui, |ui: &mut egui::Ui| {
                if ui.selectable_label(is_selected, "(select)").clicked() {
                    scene.selected = handle;
                }
                for child in &children {
                    draw_scene_tree(ui, scene, *child);
                }
            });
    }
}
