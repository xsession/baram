//! BARAM Renderer — standalone demo window
//!
//! Renders a coloured demo cube with orbit/pan/zoom camera.
//! Left-drag = orbit, middle/right-drag = pan, scroll = zoom.

use std::sync::Arc;

use baram_mesh::polydata::{TriMesh, Vertex};
use baram_renderer::camera::OrbitCamera;
use baram_renderer::gpu::GpuContext;
use baram_renderer::mesh_renderer::MeshRenderer;
use winit::dpi::PhysicalSize;
use winit::event::{ElementState, Event, MouseButton, MouseScrollDelta, WindowEvent};
use winit::event_loop::EventLoop;
use winit::window::WindowBuilder;

// ────────────────────────────────────────────────────────────────
//  Demo mesh — colourful unit cube (24 verts, 36 indices)
// ────────────────────────────────────────────────────────────────

fn demo_cube() -> TriMesh {
    // (normal, colour RGBA, 4 CCW corners viewed from outside)
    let faces: [([f32; 3], [f32; 4], [[f32; 3]; 4]); 6] = [
        // Front  Z+  red
        (
            [0.0, 0.0, 1.0],
            [0.90, 0.30, 0.30, 1.0],
            [
                [-0.5, -0.5, 0.5],
                [0.5, -0.5, 0.5],
                [0.5, 0.5, 0.5],
                [-0.5, 0.5, 0.5],
            ],
        ),
        // Back   Z-  green
        (
            [0.0, 0.0, -1.0],
            [0.30, 0.85, 0.30, 1.0],
            [
                [0.5, -0.5, -0.5],
                [-0.5, -0.5, -0.5],
                [-0.5, 0.5, -0.5],
                [0.5, 0.5, -0.5],
            ],
        ),
        // Right  X+  blue
        (
            [1.0, 0.0, 0.0],
            [0.30, 0.50, 0.95, 1.0],
            [
                [0.5, -0.5, 0.5],
                [0.5, -0.5, -0.5],
                [0.5, 0.5, -0.5],
                [0.5, 0.5, 0.5],
            ],
        ),
        // Left   X-  yellow
        (
            [-1.0, 0.0, 0.0],
            [0.95, 0.90, 0.25, 1.0],
            [
                [-0.5, -0.5, -0.5],
                [-0.5, -0.5, 0.5],
                [-0.5, 0.5, 0.5],
                [-0.5, 0.5, -0.5],
            ],
        ),
        // Top    Y+  cyan
        (
            [0.0, 1.0, 0.0],
            [0.25, 0.90, 0.90, 1.0],
            [
                [-0.5, 0.5, 0.5],
                [0.5, 0.5, 0.5],
                [0.5, 0.5, -0.5],
                [-0.5, 0.5, -0.5],
            ],
        ),
        // Bottom Y-  magenta
        (
            [0.0, -1.0, 0.0],
            [0.90, 0.30, 0.85, 1.0],
            [
                [-0.5, -0.5, -0.5],
                [0.5, -0.5, -0.5],
                [0.5, -0.5, 0.5],
                [-0.5, -0.5, 0.5],
            ],
        ),
    ];

    let mut vertices = Vec::with_capacity(24);
    let mut indices = Vec::with_capacity(36);

    for (normal, color, corners) in &faces {
        let base = vertices.len() as u32;
        for pos in corners {
            vertices.push(Vertex {
                position: *pos,
                normal: *normal,
                color: *color,
            });
        }
        // Two CCW triangles per quad
        indices.extend_from_slice(&[base, base + 1, base + 2, base, base + 2, base + 3]);
    }

    TriMesh { vertices, indices }
}

// ────────────────────────────────────────────────────────────────
//  Entry point
// ────────────────────────────────────────────────────────────────

fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .init();

    // ── Window ──────────────────────────────────────────────────
    let event_loop = EventLoop::new().unwrap();
    let window = Arc::new(
        WindowBuilder::new()
            .with_title("BARAM Renderer")
            .with_inner_size(PhysicalSize::new(1280u32, 720u32))
            .build(&event_loop)
            .unwrap(),
    );

    // ── GPU ─────────────────────────────────────────────────────
    let instance = wgpu::Instance::new(wgpu::InstanceDescriptor {
        backends: wgpu::Backends::all(),
        ..Default::default()
    });
    let surface = instance.create_surface(window.clone()).unwrap();
    let size = window.inner_size();

    let mut gpu = pollster::block_on(GpuContext::new(
        &instance,
        Some(surface),
        size.width.max(1),
        size.height.max(1),
    ))
    .expect("Failed to create GPU context");

    // ── Renderer + camera ───────────────────────────────────────
    let mut renderer = MeshRenderer::new(&gpu);
    let mut camera = OrbitCamera::default();
    camera.aspect = size.width as f32 / size.height.max(1) as f32;

    let cube = demo_cube();
    renderer.upload_mesh(&gpu, &cube);
    camera.fit_to_bounds(glam::Vec3::ZERO, 1.73); // √3 ≈ unit-cube diagonal

    // ── Input state ─────────────────────────────────────────────
    let mut mouse_btn = [false; 3]; // left, middle, right
    let mut last_pos = [0.0f64; 2];

    // ── Event loop ──────────────────────────────────────────────
    event_loop
        .run(move |event, elwt| match event {
            Event::WindowEvent { event: we, .. } => match we {
                WindowEvent::CloseRequested => elwt.exit(),

                WindowEvent::Resized(new_size) => {
                    if new_size.width > 0 && new_size.height > 0 {
                        gpu.resize(new_size.width, new_size.height);
                        renderer.resize(&gpu, new_size.width, new_size.height);
                        camera.aspect = new_size.width as f32 / new_size.height as f32;
                    }
                }

                WindowEvent::RedrawRequested => {
                    let surface = gpu.surface.as_ref().expect("no surface");
                    let frame = match surface.get_current_texture() {
                        Ok(f) => f,
                        Err(
                            wgpu::SurfaceError::Lost | wgpu::SurfaceError::Outdated,
                        ) => {
                            let s = window.inner_size();
                            gpu.resize(s.width.max(1), s.height.max(1));
                            return;
                        }
                        Err(wgpu::SurfaceError::OutOfMemory) => {
                            eprintln!("GPU out of memory");
                            elwt.exit();
                            return;
                        }
                        Err(e) => {
                            eprintln!("Surface error: {e:?}");
                            return;
                        }
                    };
                    let view = frame.texture.create_view(&Default::default());
                    renderer.render(&gpu, &view, &camera.uniform());
                    frame.present();
                }

                WindowEvent::MouseInput { state, button, .. } => {
                    let idx = match button {
                        MouseButton::Left => 0,
                        MouseButton::Middle => 1,
                        MouseButton::Right => 2,
                        _ => return,
                    };
                    mouse_btn[idx] = state == ElementState::Pressed;
                }

                WindowEvent::CursorMoved { position, .. } => {
                    let dx = position.x - last_pos[0];
                    let dy = position.y - last_pos[1];
                    last_pos = [position.x, position.y];

                    if mouse_btn[0] {
                        // Left drag → orbit
                        camera.orbit(-dx as f32 * 0.005, -dy as f32 * 0.005);
                        window.request_redraw();
                    }
                    if mouse_btn[1] || mouse_btn[2] {
                        // Middle/right drag → pan
                        camera.pan(dx as f32, dy as f32);
                        window.request_redraw();
                    }
                }

                WindowEvent::MouseWheel { delta, .. } => {
                    let scroll = match delta {
                        MouseScrollDelta::LineDelta(_, y) => y,
                        MouseScrollDelta::PixelDelta(p) => p.y as f32 * 0.01,
                    };
                    camera.zoom(1.0 - scroll * 0.1);
                    window.request_redraw();
                }

                _ => {}
            },

            // Continuous rendering — request a new frame after every event batch
            Event::AboutToWait => {
                window.request_redraw();
            }

            _ => {}
        })
        .unwrap();
}
