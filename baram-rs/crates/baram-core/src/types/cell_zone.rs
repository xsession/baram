use serde::{Deserialize, Serialize};

// ════════════════════════════════════════════════════════════════
//  Cell-Zone Configuration — port of cell_zone_db.py
// ════════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum ZoneType {
    #[default]
    None,
    MRF,
    Porous,
    SlidingMesh,
    ActuatorDisk,
}

// ─── MRF ──────────────────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MrfConfig {
    pub rotating_speed: f64,        // rad/s
    pub rotation_axis_origin: [f64; 3],
    pub rotation_axis_direction: [f64; 3],
    pub static_boundary_ids: Vec<i64>,
}

impl Default for MrfConfig {
    fn default() -> Self {
        Self {
            rotating_speed: 0.0,
            rotation_axis_origin: [0.0; 3],
            rotation_axis_direction: [0.0, 0.0, 1.0],
            static_boundary_ids: Vec::new(),
        }
    }
}

// ─── Porous Zone ──────────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum PorousZoneModel {
    #[default]
    DarcyForchheimer,
    PowerLaw,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DarcyForchheimerCoeffs {
    pub direction1: [f64; 3],
    pub direction2: [f64; 3],
    /// Permeability per axis [d1, d2, d3]
    pub inertial_resistance: [f64; 3],
    pub viscous_resistance: [f64; 3],
}

impl Default for DarcyForchheimerCoeffs {
    fn default() -> Self {
        Self {
            direction1: [1.0, 0.0, 0.0],
            direction2: [0.0, 1.0, 0.0],
            inertial_resistance: [0.0; 3],
            viscous_resistance: [0.0; 3],
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PowerLawCoeffs {
    pub c0: f64,
    pub c1: f64,
}

impl Default for PowerLawCoeffs {
    fn default() -> Self {
        Self { c0: 0.0, c1: 0.0 }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PorousZoneConfig {
    pub model: PorousZoneModel,
    pub darcy_forchheimer: DarcyForchheimerCoeffs,
    pub power_law: PowerLawCoeffs,
}

// ─── Sliding Mesh ─────────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SlidingMeshConfig {
    pub rotating_speed: f64,
    pub rotation_axis_origin: [f64; 3],
    pub rotation_axis_direction: [f64; 3],
}

impl Default for SlidingMeshConfig {
    fn default() -> Self {
        Self {
            rotating_speed: 0.0,
            rotation_axis_origin: [0.0; 3],
            rotation_axis_direction: [0.0, 0.0, 1.0],
        }
    }
}

// ─── Actuator Disk ────────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum ActuatorDiskForceComputation {
    #[default]
    FroudeMethod,
    ForcesAndTorques,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActuatorDiskConfig {
    pub disk_direction: [f64; 3],
    pub power_coefficient: f64,
    pub thrust_coefficient: f64,
    pub disk_area: f64,
    pub upstream_point: [f64; 3],
    pub force_computation: ActuatorDiskForceComputation,
    pub force: [f64; 3],
    pub torque: [f64; 3],
}

impl Default for ActuatorDiskConfig {
    fn default() -> Self {
        Self {
            disk_direction: [1.0, 0.0, 0.0],
            power_coefficient: 0.0,
            thrust_coefficient: 0.0,
            disk_area: 0.0,
            upstream_point: [0.0; 3],
            force_computation: ActuatorDiskForceComputation::FroudeMethod,
            force: [0.0; 3],
            torque: [0.0; 3],
        }
    }
}

// ─── Source Terms ─────────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SourceTerm {
    pub field: String,
    pub value: f64,
    pub unit: String,
}

// ─── Fixed Values ─────────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FixedValue {
    pub field: String,
    pub value: f64,
    pub enabled: bool,
}

// ─── Cell Zone ────────────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CellZoneConfig {
    pub id: i64,
    pub name: String,
    pub region_id: i64,
    pub zone_type: ZoneType,
    pub mrf: MrfConfig,
    pub porous: PorousZoneConfig,
    pub sliding_mesh: SlidingMeshConfig,
    pub actuator_disk: ActuatorDiskConfig,
    pub source_terms: Vec<SourceTerm>,
    pub fixed_values: Vec<FixedValue>,
}
