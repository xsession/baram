use serde::{Deserialize, Serialize};

// ─── Flow type ────────────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub enum FlowType {
    #[default]
    Incompressible,
    Compressible,
}

// ─── Solver type ──────────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub enum SolverType {
    #[default]
    PressureBased,
    DensityBased,
}

// ─── Time ─────────────────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum TimeMode {
    #[default]
    Steady,
    Transient,
}

// ─── Gravity ──────────────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Gravity {
    pub enabled: bool,
    pub direction: [f64; 3],
    pub magnitude: f64,
}

impl Default for Gravity {
    fn default() -> Self {
        Self {
            enabled: false,
            direction: [0.0, -1.0, 0.0],
            magnitude: 9.81,
        }
    }
}

// ─── Operating conditions ─────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OperatingConditions {
    pub gravity: Gravity,
    pub pressure: f64,
}

impl Default for OperatingConditions {
    fn default() -> Self {
        Self {
            gravity: Gravity::default(),
            pressure: 101325.0,
        }
    }
}

// ─── ABL (Atmospheric Boundary Layer) ─────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PasquillStability {
    A,
    B,
    C,
    D,
    E,
    F,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AtmosphericBoundaryLayer {
    pub flow_direction: [f64; 3],
    pub ground_normal: [f64; 3],
    pub reference_flow_speed: f64,
    pub reference_height: f64,
    pub surface_roughness_length: f64,
    pub minimum_z_coordinate: f64,
    pub pasquill_stability: PasquillStability,
}

// ─── Reference values ─────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReferenceValues {
    pub area: f64,
    pub density: f64,
    pub length: f64,
    pub pressure: f64,
    pub velocity: f64,
    pub reference_pressure_location: [f64; 3],
}

impl Default for ReferenceValues {
    fn default() -> Self {
        Self {
            area: 1.0,
            density: 1.225,
            length: 1.0,
            pressure: 0.0,
            velocity: 1.0,
            reference_pressure_location: [0.0; 3],
        }
    }
}

// ─── General configuration ────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeneralConfig {
    pub flow_type: FlowType,
    pub solver_type: SolverType,
    pub time_mode: TimeMode,
    pub operating_conditions: OperatingConditions,
    pub reference_values: ReferenceValues,
    pub abl: Option<AtmosphericBoundaryLayer>,
}

impl Default for GeneralConfig {
    fn default() -> Self {
        Self {
            flow_type: FlowType::Incompressible,
            solver_type: SolverType::PressureBased,
            time_mode: TimeMode::Steady,
            operating_conditions: OperatingConditions::default(),
            reference_values: ReferenceValues::default(),
            abl: None,
        }
    }
}
