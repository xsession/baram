use serde::{Deserialize, Serialize};
use super::mesh::MeshQuality;

// ════════════════════════════════════════════════════════════════
//  Meshing types — complete port of baramMesh schema
//  Covers all 7 steps: Geometry → Export
// ════════════════════════════════════════════════════════════════

/// The wizard step numbers in baramMesh
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[repr(u8)]
pub enum MeshStep {
    Geometry        = 1,
    Region          = 2,
    BaseGrid        = 3,
    Castellation    = 4,
    Snap            = 5,
    BoundaryLayer   = 6,
    Export          = 7,
}

// ─── Geometry ─────────────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum GeometryType {
    #[default]
    Surface,
    Volume,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Shape {
    TriSurfaceMesh,
    Hex,
    Cylinder,
    Sphere,
    Hex6,     // six-face box
    // Boundary sub-faces
    XMin,
    XMax,
    YMin,
    YMax,
    ZMin,
    ZMax,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum CfdType {
    #[default]
    None,
    CellZone,
    Boundary,
    Interface,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeshGeometry {
    pub id: i64,
    pub name: String,
    pub geometry_type: GeometryType,
    pub shape: Shape,
    pub cfd_type: CfdType,
    pub point1: [f64; 3],
    pub point2: [f64; 3],
    pub radius: f64,
    pub stl_file: Option<String>,
}

// ─── Region ───────────────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeshRegion {
    pub id: i64,
    pub name: String,
    pub point: [f64; 3], // seed point inside the region
}

// ─── Base Grid ────────────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BaseGridConfig {
    pub use_hex_6: bool,
    pub num_cells: [u32; 3],
    pub bounding_hex6_id: Option<i64>,
}

impl Default for BaseGridConfig {
    fn default() -> Self {
        Self {
            use_hex_6: false,
            num_cells: [10, 10, 10],
            bounding_hex6_id: None,
        }
    }
}

// ─── Castellation ─────────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CastellationConfig {
    pub number_of_cells_between_levels: u32,
    pub feature_edge_refinement_level: u32,
    pub max_global_cells: u64,
    pub max_local_cells: u64,
    pub min_refinement_cells: u32,
    pub max_load_unbalance: f64,
    pub allow_free_standing_zone_faces: bool,
    pub surface_refinements: Vec<SurfaceRefinement>,
    pub volume_refinements: Vec<VolumeRefinement>,
    pub gap_refinements: Vec<GapRefinement>,
}

impl Default for CastellationConfig {
    fn default() -> Self {
        Self {
            number_of_cells_between_levels: 3,
            feature_edge_refinement_level: 1,
            max_global_cells: 200_000_000,
            max_local_cells: 200_000_000,
            min_refinement_cells: 0,
            max_load_unbalance: 0.0,
            allow_free_standing_zone_faces: false,
            surface_refinements: Vec::new(),
            volume_refinements: Vec::new(),
            gap_refinements: Vec::new(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SurfaceRefinement {
    pub geometry_id: i64,
    pub min_level: u32,
    pub max_level: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VolumeRefinement {
    pub id: i64,
    pub name: String,
    pub geometry_id: i64,
    pub level: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum GapRefinementMode {
    #[default]
    None,
    Inside,
    Outside,
    Mixed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GapRefinement {
    pub geometry_id: i64,
    pub mode: GapRefinementMode,
    pub min_cells: u32,
    pub max_level: u32,
    pub gap_self: bool,
    pub detection_level: u32,
}

// ─── Snap ─────────────────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SnapConfig {
    pub n_smooth_patch: u32,
    pub tolerance: f64,
    pub n_solve_iter: u32,
    pub n_relax_iter: u32,
    pub n_feature_snap_iter: u32,
    pub implicit_feature_snap: bool,
    pub explicit_feature_snap: bool,
    pub multi_region_feature_snap: bool,
}

impl Default for SnapConfig {
    fn default() -> Self {
        Self {
            n_smooth_patch: 3,
            tolerance: 2.0,
            n_solve_iter: 100,
            n_relax_iter: 5,
            n_feature_snap_iter: 10,
            implicit_feature_snap: true,
            explicit_feature_snap: false,
            multi_region_feature_snap: false,
        }
    }
}

// ─── Boundary Layer ───────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum ThicknessModel {
    #[default]
    FirstAndOverall,
    FirstAndExpansionRatio,
    OverallAndExpansionRatio,
    FirstAndRelativeFinal,
    FinalAndOverall,
    FinalAndExpansionRatio,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BoundaryLayerConfig {
    pub n_layers: u32,
    pub thickness_model: ThicknessModel,
    pub first_layer_thickness: f64,
    pub overall_thickness: f64,
    pub expansion_ratio: f64,
    pub relative_final_layer: f64,
    pub final_layer_thickness: f64,
    pub min_thickness: f64,
    pub feature_angle: f64,
    pub merge_angle: f64,
    pub surface_layers: Vec<SurfaceLayer>,
    /// Smoothing parameters
    pub n_smooth_surface_normals: u32,
    pub n_smooth_thickness: u32,
    pub n_smooth_normals: u32,
    pub max_face_thickness_ratio: f64,
    pub max_thickness_to_medial_ratio: f64,
    pub min_medial_axis_angle: f64,
    pub n_buffer_cells: u32,
    pub n_grow: u32,
    pub static_analysis: bool,
}

impl Default for BoundaryLayerConfig {
    fn default() -> Self {
        Self {
            n_layers: 3,
            thickness_model: ThicknessModel::FirstAndOverall,
            first_layer_thickness: 0.01,
            overall_thickness: 0.05,
            expansion_ratio: 1.2,
            relative_final_layer: 0.3,
            final_layer_thickness: 0.01,
            min_thickness: 1e-4,
            feature_angle: 60.0,
            merge_angle: 45.0,
            surface_layers: Vec::new(),
            n_smooth_surface_normals: 1,
            n_smooth_thickness: 10,
            n_smooth_normals: 3,
            max_face_thickness_ratio: 0.5,
            max_thickness_to_medial_ratio: 0.3,
            min_medial_axis_angle: 90.0,
            n_buffer_cells: 0,
            n_grow: 0,
            static_analysis: false,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SurfaceLayer {
    pub geometry_id: i64,
    pub n_layers: u32,
    pub thickness_model: ThicknessModel,
    pub first_layer_thickness: f64,
    pub overall_thickness: f64,
    pub expansion_ratio: f64,
}

// ─── Aggregated meshing config ────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MeshingConfig {
    pub current_step: Option<MeshStep>,
    pub completed_steps: Vec<MeshStep>,
    pub geometries: Vec<MeshGeometry>,
    pub regions: Vec<MeshRegion>,
    pub base_grid: BaseGridConfig,
    pub castellation: CastellationConfig,
    pub snap: SnapConfig,
    pub boundary_layer: BoundaryLayerConfig,
    pub mesh_quality: MeshQuality,
}
