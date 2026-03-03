use bytemuck::{Pod, Zeroable};

// ════════════════════════════════════════════════════════════════
//  PolyData — Vertex/face data structures for rendering & meshing
//  Replaces VTK vtkPolyData in the new stack.
// ════════════════════════════════════════════════════════════════

/// A GPU-friendly vertex with position, normal, and optional color.
#[repr(C)]
#[derive(Debug, Clone, Copy, Pod, Zeroable)]
pub struct Vertex {
    pub position: [f32; 3],
    pub normal: [f32; 3],
    pub color: [f32; 4],  // RGBA, default white
}

/// A mesh surface consisting of indexed triangles.
#[derive(Debug, Clone)]
pub struct TriMesh {
    pub vertices: Vec<Vertex>,
    pub indices: Vec<u32>,
}

impl TriMesh {
    pub fn new() -> Self {
        Self {
            vertices: Vec::new(),
            indices: Vec::new(),
        }
    }

    pub fn num_triangles(&self) -> usize {
        self.indices.len() / 3
    }

    pub fn num_vertices(&self) -> usize {
        self.vertices.len()
    }

    /// Compute flat normals from triangle indices and write them
    /// back into each vertex.
    pub fn compute_flat_normals(&mut self) {
        for chunk in self.indices.chunks(3) {
            if chunk.len() < 3 {
                continue;
            }
            let (i0, i1, i2) = (chunk[0] as usize, chunk[1] as usize, chunk[2] as usize);
            let p0 = self.vertices[i0].position;
            let p1 = self.vertices[i1].position;
            let p2 = self.vertices[i2].position;

            let u = [p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]];
            let v = [p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]];
            let mut n = [
                u[1] * v[2] - u[2] * v[1],
                u[2] * v[0] - u[0] * v[2],
                u[0] * v[1] - u[1] * v[0],
            ];
            let len = (n[0] * n[0] + n[1] * n[1] + n[2] * n[2]).sqrt();
            if len > 1e-12 {
                n[0] /= len;
                n[1] /= len;
                n[2] /= len;
            }
            self.vertices[i0].normal = n;
            self.vertices[i1].normal = n;
            self.vertices[i2].normal = n;
        }
    }

    /// Build a TriMesh from STL triangles (no vertex sharing — flat shaded).
    pub fn from_stl_triangles(tris: &[crate::stl::StlTriangle]) -> Self {
        let mut vertices = Vec::with_capacity(tris.len() * 3);
        let mut indices = Vec::with_capacity(tris.len() * 3);
        let white = [1.0f32, 1.0, 1.0, 1.0];
        for (i, tri) in tris.iter().enumerate() {
            let base = (i * 3) as u32;
            for v in &tri.vertices {
                vertices.push(Vertex {
                    position: *v,
                    normal: tri.normal,
                    color: white,
                });
            }
            indices.push(base);
            indices.push(base + 1);
            indices.push(base + 2);
        }
        Self { vertices, indices }
    }
}

/// Edge data for wireframe rendering.
#[derive(Debug, Clone, Copy)]
pub struct Edge {
    pub v0: u32,
    pub v1: u32,
}

/// Extract unique edges from triangle indices.
pub fn extract_edges(indices: &[u32]) -> Vec<Edge> {
    use std::collections::HashSet;
    let mut seen = HashSet::new();
    let mut edges = Vec::new();
    for chunk in indices.chunks(3) {
        if chunk.len() < 3 {
            continue;
        }
        for &(a, b) in &[(chunk[0], chunk[1]), (chunk[1], chunk[2]), (chunk[2], chunk[0])] {
            let key = if a < b { (a, b) } else { (b, a) };
            if seen.insert(key) {
                edges.push(Edge { v0: key.0, v1: key.1 });
            }
        }
    }
    edges
}
