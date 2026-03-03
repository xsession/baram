use serde::{Deserialize, Serialize};

// ════════════════════════════════════════════════════════════════
//  Mesh types — display, bounds, quality, actor info
// ════════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum DisplayMode {
    Feature,
    Points,
    #[default]
    Surface,
    SurfaceEdge,
    Wireframe,
}

/// Axis-aligned bounding box
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct Bounds {
    pub min: [f64; 3],
    pub max: [f64; 3],
}

impl Default for Bounds {
    fn default() -> Self {
        Self {
            min: [f64::MAX; 3],
            max: [f64::MIN; 3],
        }
    }
}

impl Bounds {
    pub fn center(&self) -> [f64; 3] {
        [
            (self.min[0] + self.max[0]) * 0.5,
            (self.min[1] + self.max[1]) * 0.5,
            (self.min[2] + self.max[2]) * 0.5,
        ]
    }

    pub fn size(&self) -> [f64; 3] {
        [
            self.max[0] - self.min[0],
            self.max[1] - self.min[1],
            self.max[2] - self.min[2],
        ]
    }

    pub fn diagonal(&self) -> f64 {
        let s = self.size();
        (s[0] * s[0] + s[1] * s[1] + s[2] * s[2]).sqrt()
    }

    pub fn expand(&mut self, point: &[f64; 3]) {
        for i in 0..3 {
            if point[i] < self.min[i] {
                self.min[i] = point[i];
            }
            if point[i] > self.max[i] {
                self.max[i] = point[i];
            }
        }
    }

    pub fn union(&self, other: &Bounds) -> Bounds {
        Bounds {
            min: [
                self.min[0].min(other.min[0]),
                self.min[1].min(other.min[1]),
                self.min[2].min(other.min[2]),
            ],
            max: [
                self.max[0].max(other.max[0]),
                self.max[1].max(other.max[1]),
                self.max[2].max(other.max[2]),
            ],
        }
    }
}

/// Mesh quality metrics (used in baramMesh quality check)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeshQuality {
    pub max_non_orthogonality: f64,
    pub max_boundary_skewness: f64,
    pub max_internal_skewness: f64,
    pub max_aspect_ratio: f64,
    pub min_volume_ratio: f64,
    pub min_tetrahedral_quality: f64,
    pub min_face_flatness: f64,
    pub min_face_interpolation_weight: f64,
    pub min_face_area: f64,
    pub min_cell_volume: f64,
}

impl Default for MeshQuality {
    fn default() -> Self {
        Self {
            max_non_orthogonality: 65.0,
            max_boundary_skewness: 20.0,
            max_internal_skewness: 4.0,
            max_aspect_ratio: 1000.0,
            min_volume_ratio: 0.01,
            min_tetrahedral_quality: 1e-30,
            min_face_flatness: 0.5,
            min_face_interpolation_weight: 0.02,
            min_face_area: -1.0, // negative = disabled
            min_cell_volume: -1.0,
        }
    }
}

/// Information about a renderable mesh actor
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActorInfo {
    pub id: i64,
    pub name: String,
    pub visible: bool,
    pub display_mode: DisplayMode,
    pub opacity: f32,
    pub color: [f32; 3],
    pub bounds: Bounds,
    pub num_faces: u32,
    pub num_vertices: u32,
}

/// Result of a face selection (picking)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FaceSelection {
    pub actor_id: i64,
    pub face_index: u32,
    pub hit_point: [f64; 3],
    pub normal: [f64; 3],
}
