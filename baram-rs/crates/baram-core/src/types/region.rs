use serde::{Deserialize, Serialize};
use super::models::CavitationModel;

// ════════════════════════════════════════════════════════════════
//  Region — port of region_db.py
// ════════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum RegionType {
    #[default]
    Fluid,
    Solid,
}

/// Secondary phase in VOF
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecondaryPhase {
    pub material_id: i64,
    pub surface_tension: f64,
    pub cavitation_model: CavitationModel,
}

/// Overview of a single region in the project
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Region {
    pub id: i64,
    pub name: String,
    pub region_type: RegionType,
    pub material_id: i64,
    pub secondary_phases: Vec<SecondaryPhase>,
}

impl Default for Region {
    fn default() -> Self {
        Self {
            id: 0,
            name: String::new(),
            region_type: RegionType::Fluid,
            material_id: 0,
            secondary_phases: Vec::new(),
        }
    }
}

// ─── Initialization ───────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum InitializationMethod {
    #[default]
    SetValues,
    PotentialFlow,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InitializationValues {
    pub velocity: [f64; 3],
    pub pressure: f64,
    pub temperature: f64,
    pub scale_of_velocity: f64,
    pub turbulent_intensity: f64,
    pub turbulent_viscosity_ratio: f64,
    pub volume_fractions: Vec<(i64, f64)>, // (material_id, fraction)
}

impl Default for InitializationValues {
    fn default() -> Self {
        Self {
            velocity: [0.0; 3],
            pressure: 0.0,
            temperature: 300.0,
            scale_of_velocity: 1.0,
            turbulent_intensity: 0.01,
            turbulent_viscosity_ratio: 10.0,
            volume_fractions: Vec::new(),
        }
    }
}

/// Section initialization (setFieldsDict equivalent)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SectionInitialization {
    pub id: i64,
    pub name: String,
    pub region_id: i64,
    pub override_values: InitializationValues,
    /// Geometry definition for the section (hex, cylinder, sphere)
    pub section_type: SectionType,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SectionType {
    Hex {
        min: [f64; 3],
        max: [f64; 3],
    },
    Cylinder {
        axis1: [f64; 3],
        axis2: [f64; 3],
        radius: f64,
    },
    Sphere {
        center: [f64; 3],
        radius: f64,
    },
}

/// Aggregated region initialization
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RegionInitialization {
    pub method: InitializationMethod,
    pub default_values: InitializationValues,
    pub sections: Vec<SectionInitialization>,
}
