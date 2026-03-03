use std::io::{BufRead, BufReader};
use std::path::Path;
use baram_core::error::{BaramError, Result};

// ════════════════════════════════════════════════════════════════
//  OpenFOAM polyMesh reader — reads boundary/faces/owner/points
// ════════════════════════════════════════════════════════════════

/// A boundary patch as read from `constant/polyMesh/boundary`.
#[derive(Debug, Clone)]
pub struct BoundaryPatch {
    pub name: String,
    pub n_faces: usize,
    pub start_face: usize,
    pub patch_type: String, // e.g. "patch", "wall", "symmetry"
}

/// Minimal polyMesh data needed for visualization & BC assignment.
#[derive(Debug, Clone)]
pub struct PolyMesh {
    pub points: Vec<[f64; 3]>,
    pub faces: Vec<Vec<usize>>,   // each face is a list of point indices
    pub owner: Vec<usize>,
    pub neighbour: Vec<usize>,
    pub boundaries: Vec<BoundaryPatch>,
}

impl PolyMesh {
    /// Load a polyMesh from the standard OpenFOAM directory.
    pub fn load(polymesh_dir: &Path) -> Result<Self> {
        let points = read_points(&polymesh_dir.join("points"))?;
        let faces = read_faces(&polymesh_dir.join("faces"))?;
        let owner = read_label_list(&polymesh_dir.join("owner"))?;
        let neighbour = read_label_list(&polymesh_dir.join("neighbour"))?;
        let boundaries = read_boundary(&polymesh_dir.join("boundary"))?;
        Ok(Self {
            points,
            faces,
            owner,
            neighbour,
            boundaries,
        })
    }

    pub fn n_cells(&self) -> usize {
        self.owner.iter().copied().max().map(|m| m + 1).unwrap_or(0)
    }

    pub fn n_internal_faces(&self) -> usize {
        self.neighbour.len()
    }
}

// ─── File parsers ─────────────────────────────────────────────

#[allow(dead_code)]
fn skip_foam_header(reader: &mut impl BufRead) -> Result<()> {
    let mut line = String::new();
    loop {
        line.clear();
        reader.read_line(&mut line)?;
        let trimmed = line.trim();
        if trimmed == "(" || trimmed.ends_with('(') || trimmed.parse::<usize>().is_ok() {
            break;
        }
    }
    Ok(())
}

fn read_points(path: &Path) -> Result<Vec<[f64; 3]>> {
    let file = std::fs::File::open(path)?;
    let mut reader = BufReader::new(file);
    let mut line = String::new();

    // Skip header
    loop {
        line.clear();
        reader.read_line(&mut line)?;
        if line.trim().parse::<usize>().is_ok() {
            break;
        }
    }
    let n: usize = line.trim().parse().map_err(|_| {
        BaramError::InvalidMeshFormat("Cannot parse point count".into())
    })?;

    // Skip opening (
    line.clear();
    reader.read_line(&mut line)?;

    let mut points = Vec::with_capacity(n);
    for _ in 0..n {
        line.clear();
        reader.read_line(&mut line)?;
        let trimmed = line.trim().trim_start_matches('(').trim_end_matches(')');
        let coords: Vec<f64> = trimmed
            .split_whitespace()
            .filter_map(|s| s.parse().ok())
            .collect();
        if coords.len() >= 3 {
            points.push([coords[0], coords[1], coords[2]]);
        }
    }
    Ok(points)
}

fn read_faces(path: &Path) -> Result<Vec<Vec<usize>>> {
    let file = std::fs::File::open(path)?;
    let mut reader = BufReader::new(file);
    let mut line = String::new();

    // Find count
    loop {
        line.clear();
        reader.read_line(&mut line)?;
        if line.trim().parse::<usize>().is_ok() {
            break;
        }
    }
    let n: usize = line.trim().parse().map_err(|_| {
        BaramError::InvalidMeshFormat("Cannot parse face count".into())
    })?;

    line.clear();
    reader.read_line(&mut line)?; // (

    let mut faces = Vec::with_capacity(n);
    for _ in 0..n {
        line.clear();
        reader.read_line(&mut line)?;
        let trimmed = line.trim();
        // Format: 4(0 1 5 4)  or  3(0 1 2)
        if let Some(paren_pos) = trimmed.find('(') {
            let inside = &trimmed[paren_pos + 1..trimmed.len() - 1];
            let indices: Vec<usize> = inside
                .split_whitespace()
                .filter_map(|s| s.parse().ok())
                .collect();
            faces.push(indices);
        }
    }
    Ok(faces)
}

fn read_label_list(path: &Path) -> Result<Vec<usize>> {
    let file = std::fs::File::open(path)?;
    let mut reader = BufReader::new(file);
    let mut line = String::new();

    loop {
        line.clear();
        reader.read_line(&mut line)?;
        if line.trim().parse::<usize>().is_ok() {
            break;
        }
    }
    let n: usize = line.trim().parse().map_err(|_| {
        BaramError::InvalidMeshFormat("Cannot parse label count".into())
    })?;

    line.clear();
    reader.read_line(&mut line)?; // (

    let mut labels = Vec::with_capacity(n);
    for _ in 0..n {
        line.clear();
        reader.read_line(&mut line)?;
        if let Ok(v) = line.trim().parse::<usize>() {
            labels.push(v);
        }
    }
    Ok(labels)
}

fn read_boundary(path: &Path) -> Result<Vec<BoundaryPatch>> {
    let text = std::fs::read_to_string(path)?;
    let mut patches = Vec::new();

    // Simple state-machine parser for the boundary file
    let mut in_patch = false;
    let mut current_name = String::new();
    let mut n_faces = 0usize;
    let mut start_face = 0usize;
    let mut patch_type = String::new();
    let mut brace_depth = 0i32;

    // Find the start of the list (after the count and opening paren)
    let mut started = false;

    for line in text.lines() {
        let t = line.trim();

        if !started {
            if t == "(" {
                started = true;
            }
            continue;
        }

        if t == ")" && brace_depth == 0 {
            break;
        }

        if !in_patch && !t.is_empty() && !t.starts_with("//") && t != "(" && t != ")" {
            // This should be a patch name
            current_name = t.to_string();
        }

        if t == "{" {
            brace_depth += 1;
            if brace_depth == 1 {
                in_patch = true;
            }
        } else if t == "}" {
            brace_depth -= 1;
            if brace_depth == 0 && in_patch {
                patches.push(BoundaryPatch {
                    name: std::mem::take(&mut current_name),
                    n_faces,
                    start_face,
                    patch_type: std::mem::take(&mut patch_type),
                });
                in_patch = false;
                n_faces = 0;
                start_face = 0;
            }
        } else if in_patch {
            if let Some(rest) = t.strip_prefix("nFaces") {
                let val = rest.trim().trim_end_matches(';').trim();
                n_faces = val.parse().unwrap_or(0);
            } else if let Some(rest) = t.strip_prefix("startFace") {
                let val = rest.trim().trim_end_matches(';').trim();
                start_face = val.parse().unwrap_or(0);
            } else if let Some(rest) = t.strip_prefix("type") {
                patch_type = rest.trim().trim_end_matches(';').trim().to_string();
            }
        }
    }

    Ok(patches)
}
