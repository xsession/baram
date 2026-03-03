// ════════════════════════════════════════════════════════════════
//  3‑D Gizmos — translate / rotate / scale handles
//  Inspired by Fyrox's gizmo system.
// ════════════════════════════════════════════════════════════════

use baram_mesh::polydata::{TriMesh, Vertex};
use glam::Vec3;
use std::f32::consts::PI;

// ── Types ──────────────────────────────────────────────────────

/// Active gizmo manipulation mode.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GizmoMode {
    Translate,
    Rotate,
    Scale,
}

/// Which axis is being manipulated.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GizmoAxis {
    None,
    X,
    Y,
    Z,
}

/// State of the gizmo for the current frame.
pub struct Gizmo {
    pub mode: GizmoMode,
    pub active_axis: GizmoAxis,
    pub position: Vec3,
    pub size: f32,
}

impl Default for Gizmo {
    fn default() -> Self {
        Self {
            mode: GizmoMode::Translate,
            active_axis: GizmoAxis::None,
            position: Vec3::ZERO,
            size: 0.15,
        }
    }
}

// ── Mesh generation ────────────────────────────────────────────

/// Colours for the three axes.
const RED:   [f32; 4] = [0.95, 0.20, 0.20, 1.0];
const GREEN: [f32; 4] = [0.20, 0.85, 0.20, 1.0];
const BLUE:  [f32; 4] = [0.20, 0.40, 0.95, 1.0];

impl Gizmo {
    /// Build the gizmo tri‑mesh for the current mode and position.
    pub fn build_mesh(&self) -> TriMesh {
        match self.mode {
            GizmoMode::Translate => build_translate_gizmo(self.position, self.size),
            GizmoMode::Rotate    => build_rotate_gizmo(self.position, self.size),
            GizmoMode::Scale     => build_scale_gizmo(self.position, self.size),
        }
    }

    /// Crude screen‑space hit test: return the axis whose arrow
    /// centre is closest to the given world‑space ray direction.
    pub fn hit_test(&self, _ray_origin: Vec3, _ray_dir: Vec3) -> GizmoAxis {
        // Full implementation would do ray–cylinder / ray–torus
        // intersection.  For now return None.
        GizmoAxis::None
    }
}

// ── Translate gizmo (three arrows) ─────────────────────────────

fn build_translate_gizmo(origin: Vec3, size: f32) -> TriMesh {
    let mut mesh = TriMesh::new();
    append_arrow(&mut mesh, origin, Vec3::X, size, RED);
    append_arrow(&mut mesh, origin, Vec3::Y, size, GREEN);
    append_arrow(&mut mesh, origin, Vec3::Z, size, BLUE);
    mesh
}

/// A single arrow: thin cylinder shaft + cone head.
fn append_arrow(mesh: &mut TriMesh, origin: Vec3, dir: Vec3, length: f32, color: [f32; 4]) {
    let shaft_r = length * 0.03;
    let head_r  = length * 0.08;
    let head_len = length * 0.2;
    let shaft_len = length - head_len;
    let seg = 8u32;

    // We'll build the arrow along +Y then rotate to `dir`.
    let up = Vec3::Y;
    let rotation = glam::Quat::from_rotation_arc(up, dir.normalize());

    let base_offset = mesh.vertices.len() as u32;

    // Shaft (cylinder)
    for i in 0..=seg {
        let theta = 2.0 * PI * i as f32 / seg as f32;
        let (s, c) = (theta.sin(), theta.cos());
        let nx = c;
        let nz = s;
        let p_low  = rotation * Vec3::new(shaft_r * c, 0.0,       shaft_r * s) + origin;
        let p_high = rotation * Vec3::new(shaft_r * c, shaft_len, shaft_r * s) + origin;
        let n = rotation * Vec3::new(nx, 0.0, nz);
        mesh.vertices.push(Vertex {
            position: p_low.into(),
            normal: n.into(),
            color,
        });
        mesh.vertices.push(Vertex {
            position: p_high.into(),
            normal: n.into(),
            color,
        });
    }
    for i in 0..seg {
        let b = base_offset + i * 2;
        mesh.indices.extend_from_slice(&[b, b+1, b+2, b+2, b+1, b+3]);
    }

    // Head (cone)
    let tip_offset = mesh.vertices.len() as u32;
    let tip = rotation * Vec3::new(0.0, length, 0.0) + origin;
    mesh.vertices.push(Vertex {
        position: tip.into(),
        normal: (rotation * Vec3::Y).into(),
        color,
    });
    for i in 0..=seg {
        let theta = 2.0 * PI * i as f32 / seg as f32;
        let (s, c) = (theta.sin(), theta.cos());
        let p = rotation * Vec3::new(head_r * c, shaft_len, head_r * s) + origin;
        let n = rotation * Vec3::new(c, 0.3, s).normalize();
        mesh.vertices.push(Vertex {
            position: p.into(),
            normal: n.into(),
            color,
        });
    }
    for i in 0..seg {
        mesh.indices.extend_from_slice(&[tip_offset, tip_offset + 1 + i, tip_offset + 2 + i]);
    }
}

// ── Rotate gizmo (three rings) ─────────────────────────────────

fn build_rotate_gizmo(origin: Vec3, size: f32) -> TriMesh {
    let mut mesh = TriMesh::new();
    append_ring(&mut mesh, origin, Vec3::X, size, RED);
    append_ring(&mut mesh, origin, Vec3::Y, size, GREEN);
    append_ring(&mut mesh, origin, Vec3::Z, size, BLUE);
    mesh
}

fn append_ring(mesh: &mut TriMesh, origin: Vec3, axis: Vec3, radius: f32, color: [f32; 4]) {
    let seg = 48u32;
    let tube_r = radius * 0.02;
    let rot = glam::Quat::from_rotation_arc(Vec3::Y, axis.normalize());

    let base = mesh.vertices.len() as u32;
    let ring_seg = 6u32;
    for i in 0..=seg {
        let theta = 2.0 * PI * i as f32 / seg as f32;
        let center = Vec3::new(radius * theta.cos(), 0.0, radius * theta.sin());
        let _tangent = Vec3::new(-theta.sin(), 0.0, theta.cos());
        let normal_base = center.normalize();
        for j in 0..=ring_seg {
            let phi = 2.0 * PI * j as f32 / ring_seg as f32;
            let local_n = normal_base * phi.cos() + Vec3::Y * phi.sin();
            let p = rot * (center + local_n * tube_r) + origin;
            let n = rot * local_n;
            mesh.vertices.push(Vertex {
                position: p.into(),
                normal: n.into(),
                color,
            });
        }
    }
    let stride = ring_seg + 1;
    for i in 0..seg {
        for j in 0..ring_seg {
            let a = base + i * stride + j;
            let b = a + stride;
            mesh.indices.extend_from_slice(&[a, b, a + 1, a + 1, b, b + 1]);
        }
    }
}

// ── Scale gizmo (three axes with cubes) ────────────────────────

fn build_scale_gizmo(origin: Vec3, size: f32) -> TriMesh {
    // Re‑use translate gizmo for now (cubes at tips are a TODO).
    build_translate_gizmo(origin, size)
}
