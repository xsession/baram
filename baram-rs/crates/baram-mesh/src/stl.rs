use std::path::Path;
use baram_core::error::{BaramError, Result};
use rayon::prelude::*;

// ════════════════════════════════════════════════════════════════
//  STL Import — binary + ASCII, parallelized
// ════════════════════════════════════════════════════════════════

/// A single triangle from an STL file.
#[derive(Debug, Clone, Copy)]
pub struct StlTriangle {
    pub normal: [f32; 3],
    pub vertices: [[f32; 3]; 3],
}

/// A named solid from an STL file.
#[derive(Debug, Clone)]
pub struct StlSolid {
    pub name: String,
    pub triangles: Vec<StlTriangle>,
}

/// Parse an STL file (auto-detects binary vs ASCII).
pub fn load_stl(path: &Path) -> Result<Vec<StlSolid>> {
    let data = std::fs::read(path)?;
    if is_binary_stl(&data) {
        parse_binary_stl(&data)
    } else {
        let text = String::from_utf8_lossy(&data);
        parse_ascii_stl(&text)
    }
}

fn is_binary_stl(data: &[u8]) -> bool {
    if data.len() < 84 {
        return false;
    }
    // ASCII STL starts with "solid "
    let header = &data[..6];
    if header == b"solid " {
        // Heuristic: check if the 80-byte header + 4-byte count makes sense
        let n_triangles = u32::from_le_bytes([data[80], data[81], data[82], data[83]]);
        let expected_size = 84 + n_triangles as usize * 50;
        // If the size matches, it's likely binary despite starting with "solid"
        if expected_size == data.len() {
            return true;
        }
        return false;
    }
    true
}

/// Parse binary STL (80-byte header + u32 count + 50 bytes per triangle).
fn parse_binary_stl(data: &[u8]) -> Result<Vec<StlSolid>> {
    if data.len() < 84 {
        return Err(BaramError::InvalidMeshFormat("STL file too small".into()));
    }
    let header = String::from_utf8_lossy(&data[..80])
        .trim_end_matches('\0')
        .trim()
        .to_string();
    let name = if header.is_empty() {
        "solid".to_string()
    } else {
        header
    };

    let n_triangles = u32::from_le_bytes([data[80], data[81], data[82], data[83]]) as usize;
    let expected = 84 + n_triangles * 50;
    if data.len() < expected {
        return Err(BaramError::InvalidMeshFormat(format!(
            "Binary STL claims {n_triangles} triangles but file is too small"
        )));
    }

    // Parallel triangle parsing (chunk the triangle data)
    let tri_data = &data[84..84 + n_triangles * 50];
    let triangles: Vec<StlTriangle> = tri_data
        .par_chunks(50)
        .map(|chunk| {
            let f = |off: usize| -> f32 {
                f32::from_le_bytes([chunk[off], chunk[off + 1], chunk[off + 2], chunk[off + 3]])
            };
            StlTriangle {
                normal: [f(0), f(4), f(8)],
                vertices: [
                    [f(12), f(16), f(20)],
                    [f(24), f(28), f(32)],
                    [f(36), f(40), f(44)],
                ],
            }
        })
        .collect();

    Ok(vec![StlSolid { name, triangles }])
}

/// Parse ASCII STL.
fn parse_ascii_stl(text: &str) -> Result<Vec<StlSolid>> {
    let mut solids = Vec::new();
    let mut current_name = String::new();
    let mut triangles: Vec<StlTriangle> = Vec::new();
    let mut current_normal = [0f32; 3];
    let mut current_verts: Vec<[f32; 3]> = Vec::with_capacity(3);

    for line in text.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("solid ") {
            current_name = trimmed[6..].trim().to_string();
            triangles.clear();
        } else if trimmed.starts_with("endsolid") {
            solids.push(StlSolid {
                name: std::mem::take(&mut current_name),
                triangles: std::mem::take(&mut triangles),
            });
        } else if trimmed.starts_with("facet normal") {
            let parts: Vec<f32> = trimmed[12..]
                .split_whitespace()
                .filter_map(|s| s.parse().ok())
                .collect();
            if parts.len() >= 3 {
                current_normal = [parts[0], parts[1], parts[2]];
            }
            current_verts.clear();
        } else if trimmed.starts_with("vertex") {
            let parts: Vec<f32> = trimmed[6..]
                .split_whitespace()
                .filter_map(|s| s.parse().ok())
                .collect();
            if parts.len() >= 3 {
                current_verts.push([parts[0], parts[1], parts[2]]);
            }
        } else if trimmed.starts_with("endfacet") {
            if current_verts.len() == 3 {
                triangles.push(StlTriangle {
                    normal: current_normal,
                    vertices: [current_verts[0], current_verts[1], current_verts[2]],
                });
            }
        }
    }

    if solids.is_empty() && !triangles.is_empty() {
        solids.push(StlSolid {
            name: current_name,
            triangles,
        });
    }

    Ok(solids)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_simple_ascii() {
        let stl = r#"solid test
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 0 1 0
    endloop
  endfacet
endsolid test
"#;
        let solids = parse_ascii_stl(stl).unwrap();
        assert_eq!(solids.len(), 1);
        assert_eq!(solids[0].triangles.len(), 1);
        assert_eq!(solids[0].name, "test");
    }
}
