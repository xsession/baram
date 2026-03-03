// ════════════════════════════════════════════════════════════════
//  Hedron — CSG geometry backend inspired by Fyrox
//
//  Provides parametric primitives, tessellation, and boolean‑op
//  data structures.  The name "Hedron" is a nod to polyhedra —
//  the atomic building blocks of CFD meshes.
// ════════════════════════════════════════════════════════════════

use baram_mesh::polydata::{TriMesh, Vertex};
use glam::{Mat4, Vec3};
use std::f32::consts::PI;

// ── CSG primitives ─────────────────────────────────────────────

/// Parametric CSG primitive.
#[derive(Debug, Clone)]
pub enum CsgPrimitive {
    Box { half_extents: Vec3 },
    Cylinder { radius: f32, height: f32, segments: u32 },
    Sphere { radius: f32, rings: u32, sectors: u32 },
    Cone { radius: f32, height: f32, segments: u32 },
    Torus { major_radius: f32, minor_radius: f32, major_seg: u32, minor_seg: u32 },
}

/// Boolean operation type.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CsgOp {
    Union,
    Subtract,
    Intersect,
}

/// CSG expression‑tree node.
#[derive(Debug, Clone)]
pub enum CsgTree {
    Leaf { primitive: CsgPrimitive, transform: Mat4, color: [f32; 4] },
    Operation { op: CsgOp, left: Box<CsgTree>, right: Box<CsgTree> },
}

// ── Tessellation ───────────────────────────────────────────────

impl CsgPrimitive {
    /// Tessellate this primitive into a `TriMesh` with the given colour.
    pub fn tessellate(&self, color: [f32; 4]) -> TriMesh {
        match self {
            Self::Box { half_extents } => tessellate_box(*half_extents, color),
            Self::Cylinder { radius, height, segments } => {
                tessellate_cylinder(*radius, *height, *segments, color)
            }
            Self::Sphere { radius, rings, sectors } => {
                tessellate_sphere(*radius, *rings, *sectors, color)
            }
            Self::Cone { radius, height, segments } => {
                tessellate_cone(*radius, *height, *segments, color)
            }
            Self::Torus { major_radius, minor_radius, major_seg, minor_seg } => {
                tessellate_torus(*major_radius, *minor_radius, *major_seg, *minor_seg, color)
            }
        }
    }
}

fn v(pos: [f32; 3], n: [f32; 3], c: [f32; 4]) -> Vertex {
    Vertex { position: pos, normal: n, color: c }
}

// ── Box ────────────────────────────────────────────────────────

pub fn tessellate_box(h: Vec3, color: [f32; 4]) -> TriMesh {
    let faces: [([f32; 3], [[f32; 3]; 4]); 6] = [
        ([0., 0., 1.], [[-h.x,-h.y, h.z],[ h.x,-h.y, h.z],[ h.x, h.y, h.z],[-h.x, h.y, h.z]]),
        ([0., 0.,-1.], [[ h.x,-h.y,-h.z],[-h.x,-h.y,-h.z],[-h.x, h.y,-h.z],[ h.x, h.y,-h.z]]),
        ([1., 0., 0.], [[ h.x,-h.y, h.z],[ h.x,-h.y,-h.z],[ h.x, h.y,-h.z],[ h.x, h.y, h.z]]),
        ([-1.,0., 0.], [[-h.x,-h.y,-h.z],[-h.x,-h.y, h.z],[-h.x, h.y, h.z],[-h.x, h.y,-h.z]]),
        ([0., 1., 0.], [[-h.x, h.y, h.z],[ h.x, h.y, h.z],[ h.x, h.y,-h.z],[-h.x, h.y,-h.z]]),
        ([0.,-1., 0.], [[-h.x,-h.y,-h.z],[ h.x,-h.y,-h.z],[ h.x,-h.y, h.z],[-h.x,-h.y, h.z]]),
    ];
    let mut verts = Vec::with_capacity(24);
    let mut idxs = Vec::with_capacity(36);
    for (n, corners) in &faces {
        let base = verts.len() as u32;
        for p in corners {
            verts.push(v(*p, *n, color));
        }
        idxs.extend_from_slice(&[base, base+1, base+2, base, base+2, base+3]);
    }
    TriMesh { vertices: verts, indices: idxs }
}

// ── Sphere (UV) ────────────────────────────────────────────────

pub fn tessellate_sphere(radius: f32, rings: u32, sectors: u32, color: [f32; 4]) -> TriMesh {
    let rings = rings.max(3);
    let sectors = sectors.max(3);
    let mut verts = Vec::with_capacity(((rings + 1) * (sectors + 1)) as usize);
    for r in 0..=rings {
        let phi = PI * r as f32 / rings as f32;
        let sp = phi.sin();
        let cp = phi.cos();
        for s in 0..=sectors {
            let theta = 2.0 * PI * s as f32 / sectors as f32;
            let st = theta.sin();
            let ct = theta.cos();
            let nx = sp * ct;
            let ny = cp;
            let nz = sp * st;
            verts.push(v(
                [radius * nx, radius * ny, radius * nz],
                [nx, ny, nz],
                color,
            ));
        }
    }
    let mut idxs = Vec::with_capacity((rings * sectors * 6) as usize);
    for r in 0..rings {
        for s in 0..sectors {
            let a = r * (sectors + 1) + s;
            let b = a + sectors + 1;
            idxs.extend_from_slice(&[a, b, a + 1, a + 1, b, b + 1]);
        }
    }
    TriMesh { vertices: verts, indices: idxs }
}

// ── Cylinder ───────────────────────────────────────────────────

pub fn tessellate_cylinder(radius: f32, height: f32, seg: u32, color: [f32; 4]) -> TriMesh {
    let seg = seg.max(3);
    let half = height * 0.5;
    let mut verts = Vec::new();
    let mut idxs = Vec::new();

    // Side
    for i in 0..=seg {
        let theta = 2.0 * PI * i as f32 / seg as f32;
        let (st, ct) = (theta.sin(), theta.cos());
        let nx = ct;
        let nz = st;
        verts.push(v([radius * ct, -half, radius * st], [nx, 0., nz], color));
        verts.push(v([radius * ct,  half, radius * st], [nx, 0., nz], color));
    }
    for i in 0..seg {
        let b = i * 2;
        idxs.extend_from_slice(&[b, b+1, b+2, b+2, b+1, b+3]);
    }

    // Top cap
    let top_center = verts.len() as u32;
    verts.push(v([0., half, 0.], [0., 1., 0.], color));
    for i in 0..seg {
        let theta = 2.0 * PI * i as f32 / seg as f32;
        verts.push(v([radius * theta.cos(), half, radius * theta.sin()], [0., 1., 0.], color));
    }
    for i in 0..seg {
        let next = if i + 1 < seg { top_center + 1 + i + 1 } else { top_center + 1 };
        idxs.extend_from_slice(&[top_center, top_center + 1 + i, next]);
    }

    // Bottom cap
    let bot_center = verts.len() as u32;
    verts.push(v([0., -half, 0.], [0., -1., 0.], color));
    for i in 0..seg {
        let theta = 2.0 * PI * i as f32 / seg as f32;
        verts.push(v([radius * theta.cos(), -half, radius * theta.sin()], [0., -1., 0.], color));
    }
    for i in 0..seg {
        let next = if i + 1 < seg { bot_center + 1 + i + 1 } else { bot_center + 1 };
        idxs.extend_from_slice(&[bot_center, next, bot_center + 1 + i]);
    }

    TriMesh { vertices: verts, indices: idxs }
}

// ── Cone ───────────────────────────────────────────────────────

pub fn tessellate_cone(radius: f32, height: f32, seg: u32, color: [f32; 4]) -> TriMesh {
    let seg = seg.max(3);
    let half = height * 0.5;
    let slope = radius / height;
    let mut verts = Vec::new();
    let mut idxs = Vec::new();

    // Tip
    let tip = verts.len() as u32;
    verts.push(v([0., half, 0.], [0., 1., 0.], color));

    // Base ring (side normals)
    for i in 0..=seg {
        let theta = 2.0 * PI * i as f32 / seg as f32;
        let (st, ct) = (theta.sin(), theta.cos());
        // Outward normal for a cone
        let ny = slope;
        let len = (1.0 + ny * ny).sqrt();
        verts.push(v(
            [radius * ct, -half, radius * st],
            [ct / len, ny / len, st / len],
            color,
        ));
    }
    for i in 0..seg {
        idxs.extend_from_slice(&[tip, 1 + i, 2 + i]);
    }

    // Bottom cap
    let bot_center = verts.len() as u32;
    verts.push(v([0., -half, 0.], [0., -1., 0.], color));
    for i in 0..seg {
        let theta = 2.0 * PI * i as f32 / seg as f32;
        verts.push(v([radius * theta.cos(), -half, radius * theta.sin()], [0., -1., 0.], color));
    }
    for i in 0..seg {
        let next = if i + 1 < seg { bot_center + 1 + i + 1 } else { bot_center + 1 };
        idxs.extend_from_slice(&[bot_center, next, bot_center + 1 + i]);
    }

    TriMesh { vertices: verts, indices: idxs }
}

// ── Torus ──────────────────────────────────────────────────────

pub fn tessellate_torus(
    major_r: f32,
    minor_r: f32,
    maj_seg: u32,
    min_seg: u32,
    color: [f32; 4],
) -> TriMesh {
    let maj_seg = maj_seg.max(3);
    let min_seg = min_seg.max(3);
    let mut verts = Vec::with_capacity(((maj_seg + 1) * (min_seg + 1)) as usize);
    for j in 0..=maj_seg {
        let phi = 2.0 * PI * j as f32 / maj_seg as f32;
        let (sp, cp) = (phi.sin(), phi.cos());
        for i in 0..=min_seg {
            let theta = 2.0 * PI * i as f32 / min_seg as f32;
            let (st, ct) = (theta.sin(), theta.cos());
            let px = (major_r + minor_r * ct) * cp;
            let py = minor_r * st;
            let pz = (major_r + minor_r * ct) * sp;
            let nx = ct * cp;
            let ny = st;
            let nz = ct * sp;
            verts.push(v([px, py, pz], [nx, ny, nz], color));
        }
    }
    let mut idxs = Vec::with_capacity((maj_seg * min_seg * 6) as usize);
    for j in 0..maj_seg {
        for i in 0..min_seg {
            let a = j * (min_seg + 1) + i;
            let b = a + min_seg + 1;
            idxs.extend_from_slice(&[a, b, a + 1, a + 1, b, b + 1]);
        }
    }
    TriMesh { vertices: verts, indices: idxs }
}

// ── CSG evaluation (mesh union — trivial concat for now) ───────

/// Evaluate a CSG tree into a single `TriMesh`.
///
/// Full boolean operations (BSP‑tree clipping) are a TODO;
/// the current implementation concatenates leaves, applying
/// transforms, which is sufficient for visualisation.
pub fn evaluate_csg(tree: &CsgTree) -> TriMesh {
    match tree {
        CsgTree::Leaf { primitive, transform, color } => {
            let mut mesh = primitive.tessellate(*color);
            apply_transform(&mut mesh, transform);
            mesh
        }
        CsgTree::Operation { op: _, left, right } => {
            let mut a = evaluate_csg(left);
            let b = evaluate_csg(right);
            merge_into(&mut a, &b);
            a
        }
    }
}

fn apply_transform(mesh: &mut TriMesh, mat: &Mat4) {
    let normal_mat = mat.inverse().transpose();
    for vert in &mut mesh.vertices {
        let p = *mat * glam::Vec4::new(vert.position[0], vert.position[1], vert.position[2], 1.0);
        vert.position = [p.x, p.y, p.z];
        let n = normal_mat * glam::Vec4::new(vert.normal[0], vert.normal[1], vert.normal[2], 0.0);
        let len = (n.x * n.x + n.y * n.y + n.z * n.z).sqrt().max(1e-12);
        vert.normal = [n.x / len, n.y / len, n.z / len];
    }
}

fn merge_into(dst: &mut TriMesh, src: &TriMesh) {
    let offset = dst.vertices.len() as u32;
    dst.vertices.extend_from_slice(&src.vertices);
    dst.indices.extend(src.indices.iter().map(|i| i + offset));
}
