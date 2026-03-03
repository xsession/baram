use serde::{Deserialize, Serialize};

// ════════════════════════════════════════════════════════════════
//  Physics Models — complete port of models_db.py
// ════════════════════════════════════════════════════════════════

// ─── Multiphase ───────────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum MultiphaseModel {
    #[default]
    Off,
    VolumeOfFluid,
}

// ─── Turbulence ───────────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum TurbulenceModel {
    Inviscid,
    Laminar,
    SpalartAllmaras,
    #[default]
    KEpsilon,
    KOmega,
    Des,
    Les,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum KEpsilonModel {
    Standard,
    Rng,
    #[default]
    Realizable,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum KOmegaModel {
    #[default]
    Sst,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum NearWallTreatment {
    #[default]
    StandardWallFunctions,
    EnhancedWallTreatment,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum RansModel {
    SpalartAllmaras,
    #[default]
    KOmegaSst,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum ShieldingFunctions {
    #[default]
    Ddes,
    Iddes,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum SubgridScaleModel {
    #[default]
    Smagorinsky,
    Wale,
    DynamicKEqn,
    KEqn,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TurbulenceConfig {
    pub model: TurbulenceModel,
    pub k_epsilon_model: KEpsilonModel,
    pub k_omega_model: KOmegaModel,
    pub near_wall_treatment: NearWallTreatment,
    pub rans_model: RansModel,
    pub shielding_functions: ShieldingFunctions,
    pub subgrid_scale_model: SubgridScaleModel,
}

impl Default for TurbulenceConfig {
    fn default() -> Self {
        Self {
            model: TurbulenceModel::KEpsilon,
            k_epsilon_model: KEpsilonModel::Realizable,
            k_omega_model: KOmegaModel::Sst,
            near_wall_treatment: NearWallTreatment::StandardWallFunctions,
            rans_model: RansModel::KOmegaSst,
            shielding_functions: ShieldingFunctions::Ddes,
            subgrid_scale_model: SubgridScaleModel::Smagorinsky,
        }
    }
}

// ─── Species ──────────────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum SpeciesModel {
    #[default]
    Off,
    On,
}

// ─── DPM ──────────────────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum DpmParticleType {
    #[default]
    None,
    Inert,
    Droplet,
}

// ─── User Defined Scalars ─────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserDefinedScalar {
    pub id: i64,
    pub field_name: String,
    pub region: String,
    pub material_id: i64,
    pub diffusivity: f64,
}

// ─── Aggregated models configuration ──────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ModelsConfig {
    pub multiphase: MultiphaseModel,
    pub energy_enabled: bool,
    pub turbulence: TurbulenceConfig,
    pub species: SpeciesModel,
    pub dpm_particle_type: DpmParticleType,
    pub user_defined_scalars: Vec<UserDefinedScalar>,
}

// ─── Cavitation ───────────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum CavitationModel {
    #[default]
    None,
    SchnerrSauer,
    Kunz,
    Merkle,
    ZwartGerberBelamri,
}
