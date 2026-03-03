use serde::{Deserialize, Serialize};

// ════════════════════════════════════════════════════════════════
//  Materials — complete port of material_db.py / materials schema
// ════════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum MaterialPhase {
    #[default]
    Gas,
    Liquid,
    Solid,
}

// ─── Density specification ────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum DensitySpecification {
    #[default]
    Constant,
    PerfectGas,
    Polynomial,
    IncompressiblePerfectGas,
    PengRobinsonGas,
    Boussinesq,
    PerfectFluid,
    RealGasPengRobinson,
}

// ─── Viscosity model ──────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum ViscosityModel {
    #[default]
    Constant,
    Sutherland,
    Polynomial,
    CrossPowerLaw,
    HerschelBulkley,
    BirdCarreau,
    NonNewtonianPowerLaw,
}

// ─── Specific heat model ──────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum SpecificHeatModel {
    #[default]
    Constant,
    Polynomial,
}

// ─── Thermal conductivity model ───────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum ThermalConductivityModel {
    #[default]
    Constant,
    Polynomial,
}

// ─── Absorption coefficient model ─────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum AbsorptionCoefficientModel {
    #[default]
    Constant,
    WsggmSmith,
}

// ─── Surface tension model ────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum SurfaceTensionModel {
    #[default]
    Constant,
}

// ─── Polynomial coefficients ──────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolynomialCoeffs {
    pub coefficients: Vec<f64>, // up to 8th order
}

impl Default for PolynomialCoeffs {
    fn default() -> Self {
        Self {
            coefficients: vec![0.0],
        }
    }
}

// ─── Sutherland parameters ────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SutherlandParameters {
    pub coefficient: f64,
    pub temperature: f64,
}

impl Default for SutherlandParameters {
    fn default() -> Self {
        Self {
            coefficient: 1.458e-6,
            temperature: 110.4,
        }
    }
}

// ─── Non-Newtonian parameters ─────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CrossPowerLawParams {
    pub zero_shear_viscosity: f64,
    pub infinite_shear_viscosity: f64,
    pub natural_time: f64,
    pub power_law_index: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HerschelBulkleyParams {
    pub zero_shear_viscosity: f64,
    pub yield_stress: f64,
    pub consistency_index: f64,
    pub power_law_index: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BirdCarreauParams {
    pub zero_shear_viscosity: f64,
    pub infinite_shear_viscosity: f64,
    pub relaxation_time: f64,
    pub power_law_index: f64,
    pub linearity_deviation: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NonNewtonianPowerLawParams {
    pub max_viscosity: f64,
    pub min_viscosity: f64,
    pub consistency_index: f64,
    pub power_law_index: f64,
}

// ─── Density parameters ───────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerfectFluidParams {
    pub p0: f64,
    pub rho0: f64,
}

impl Default for PerfectFluidParams {
    fn default() -> Self {
        Self {
            p0: 101325.0,
            rho0: 1.225,
        }
    }
}

// ─── Material Property Struct ─────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Material {
    pub id: i64,
    pub name: String,
    pub formula: String,
    pub phase: MaterialPhase,
    pub molecular_weight: f64,
    pub absorptivity: f64,
    pub emissivity: f64,

    // Density
    pub density_spec: DensitySpecification,
    pub density_constant: f64,
    pub density_polynomial: PolynomialCoeffs,
    pub boussinesq_reference_temperature: f64,
    pub perfect_fluid: PerfectFluidParams,

    // Specific heat
    pub specific_heat_model: SpecificHeatModel,
    pub specific_heat_constant: f64,
    pub specific_heat_polynomial: PolynomialCoeffs,

    // Viscosity
    pub viscosity_model: ViscosityModel,
    pub viscosity_constant: f64,
    pub viscosity_polynomial: PolynomialCoeffs,
    pub sutherland: SutherlandParameters,
    pub cross_power_law: Option<CrossPowerLawParams>,
    pub herschel_bulkley: Option<HerschelBulkleyParams>,
    pub bird_carreau: Option<BirdCarreauParams>,
    pub non_newtonian_power_law: Option<NonNewtonianPowerLawParams>,

    // Thermal conductivity
    pub thermal_conductivity_model: ThermalConductivityModel,
    pub thermal_conductivity_constant: f64,
    pub thermal_conductivity_polynomial: PolynomialCoeffs,

    // Radiation
    pub absorption_coefficient_model: AbsorptionCoefficientModel,
    pub absorption_coefficient_constant: f64,

    // Surface tension
    pub surface_tension_model: SurfaceTensionModel,
    pub surface_tension_constant: f64,

    // Saturation properties (VOF)
    pub saturation_pressure: f64,
    pub saturation_temperature: f64,
}

impl Default for Material {
    fn default() -> Self {
        Self {
            id: 0,
            name: "air".into(),
            formula: String::new(),
            phase: MaterialPhase::Gas,
            molecular_weight: 28.966,
            absorptivity: 0.0,
            emissivity: 0.0,
            density_spec: DensitySpecification::Constant,
            density_constant: 1.225,
            density_polynomial: PolynomialCoeffs::default(),
            boussinesq_reference_temperature: 300.0,
            perfect_fluid: PerfectFluidParams::default(),
            specific_heat_model: SpecificHeatModel::Constant,
            specific_heat_constant: 1006.0,
            specific_heat_polynomial: PolynomialCoeffs::default(),
            viscosity_model: ViscosityModel::Constant,
            viscosity_constant: 1.79e-5,
            viscosity_polynomial: PolynomialCoeffs::default(),
            sutherland: SutherlandParameters::default(),
            cross_power_law: None,
            herschel_bulkley: None,
            bird_carreau: None,
            non_newtonian_power_law: None,
            thermal_conductivity_model: ThermalConductivityModel::Constant,
            thermal_conductivity_constant: 0.0245,
            thermal_conductivity_polynomial: PolynomialCoeffs::default(),
            absorption_coefficient_model: AbsorptionCoefficientModel::Constant,
            absorption_coefficient_constant: 0.0,
            surface_tension_model: SurfaceTensionModel::Constant,
            surface_tension_constant: 0.0,
            saturation_pressure: 0.0,
            saturation_temperature: 0.0,
        }
    }
}

/// Mixture material (for species transport)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MixtureMaterial {
    pub primary_specie: i64,
    pub species: Vec<i64>,
}

/// Region material assignment
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegionMaterialAssignment {
    pub region_id: i64,
    pub material_id: i64,
    pub secondary_material_ids: Vec<i64>, // for VOF
}
