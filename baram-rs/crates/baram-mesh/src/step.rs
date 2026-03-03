use std::path::Path;
use baram_core::error::{BaramError, Result};
use tracing::{info, warn};

// ════════════════════════════════════════════════════════════════
//  STEP Import — reads STEP AP203/AP214 B‑rep and tessellates
//  to polygon mesh using the `truck` CAD kernel.
// ════════════════════════════════════════════════════════════════

use truck_stepio::r#in::{alias::*, Table};
use truck_meshalgo::tessellation::{MeshableShape, MeshedShape};

/// Result of importing a STEP file: one or more named triangle meshes.
#[derive(Debug, Clone)]
pub struct StepSolid {
    pub name: String,
    pub mesh: crate::polydata::TriMesh,
}

/// Load a STEP file (.step / .stp) and tessellate all shells.
///
/// `tolerance` controls tessellation resolution (smaller = finer mesh).
/// A typical value is `0.01` for metre‑scale models.
pub fn load_step(path: &Path, tolerance: f64) -> Result<Vec<StepSolid>> {
    let step_string = std::fs::read_to_string(path).map_err(|e| {
        BaramError::InvalidMeshFormat(format!("Cannot read STEP file: {e}"))
    })?;

    info!("Parsing STEP file: {}", path.display());

    let table = Table::from_step(&step_string).ok_or_else(|| {
        BaramError::InvalidMeshFormat("Failed to parse STEP file (invalid format)".into())
    })?;

    let tol = if tolerance <= 1e-12 { 0.01 } else { tolerance };

    let mut solids = Vec::new();

    // Iterate all shells defined in the STEP file.
    let shell_ids: Vec<u64> = table.shell.keys().copied().collect();
    info!("Found {} shell(s) in STEP file", shell_ids.len());

    for (idx, shell_id) in shell_ids.iter().enumerate() {
        let shell_holder = match table.shell.get(shell_id) {
            Some(h) => h,
            None => continue,
        };

        let name = if shell_holder.label.is_empty() {
            format!("Shell_{idx}")
        } else {
            shell_holder.label.clone()
        };

        info!("Processing shell #{shell_id} '{name}'...");

        // Convert STEP shell → truck CompressedShell (B‑rep)
        let compressed = match table.to_compressed_shell(shell_holder) {
            Ok(cs) => cs,
            Err(e) => {
                warn!("Skipping shell #{shell_id}: {e}");
                continue;
            }
        };

        // Tessellate the B‑rep into polygon mesh
        let tessellated = compressed.triangulation(tol);
        let polygon = tessellated.to_polygon();

        let positions = polygon.positions();
        let normals = polygon.normals();
        let tri_faces = polygon.tri_faces();

        if positions.is_empty() || tri_faces.is_empty() {
            warn!("Shell #{shell_id} produced empty tessellation, skipping");
            continue;
        }

        info!(
            "Shell '{name}': {} vertices, {} normals, {} triangles",
            positions.len(),
            normals.len(),
            tri_faces.len()
        );

        // Convert truck PolygonMesh → our TriMesh
        let tri_mesh = polygon_to_trimesh(&polygon);
        solids.push(StepSolid { name, mesh: tri_mesh });
    }

    if solids.is_empty() {
        return Err(BaramError::InvalidMeshFormat(
            "No valid shells found in STEP file".into(),
        ));
    }

    Ok(solids)
}

/// Convert a truck `PolygonMesh` to our `TriMesh`.
///
/// truck stores positions, normals, and face indices separately (like OBJ).
/// We flatten to per-vertex data for GPU rendering.
fn polygon_to_trimesh(polygon: &PolygonMesh) -> crate::polydata::TriMesh {
    use crate::polydata::Vertex;

    let positions = polygon.positions();
    let normals = polygon.normals();
    let tri_faces = polygon.tri_faces();

    let default_color = [0.75_f32, 0.75, 0.78, 1.0]; // light grey

    let mut vertices = Vec::with_capacity(tri_faces.len() * 3);
    let mut indices = Vec::with_capacity(tri_faces.len() * 3);

    for tri in tri_faces {
        let base = vertices.len() as u32;
        for sv in tri {
            let pos = positions[sv.pos];
            let nor = sv.nor.and_then(|i| normals.get(i));

            let position = [pos.x as f32, pos.y as f32, pos.z as f32];
            let normal = match nor {
                Some(n) => [n.x as f32, n.y as f32, n.z as f32],
                None => [0.0, 1.0, 0.0], // placeholder; will recompute below
            };

            vertices.push(Vertex {
                position,
                normal,
                color: default_color,
            });
        }
        indices.push(base);
        indices.push(base + 1);
        indices.push(base + 2);
    }

    let mut mesh = crate::polydata::TriMesh { vertices, indices };

    // If normals were missing, recompute flat normals
    if normals.is_empty() {
        mesh.compute_flat_normals();
    }

    mesh
}
