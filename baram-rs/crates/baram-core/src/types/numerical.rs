use serde::{Deserialize, Serialize};

// ════════════════════════════════════════════════════════════════
//  Numerical Conditions — port of numerical_db.py
// ════════════════════════════════════════════════════════════════

// ─── Pressure-velocity coupling ───────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum PressureVelocityCouplingScheme {
    #[default]
    Simple,
    Simplec,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum Formulation {
    #[default]
    Implicit,
    Explicit,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum FluxType {
    #[default]
    RoeFds,
    Ausm,
    AusmUp,
}

// ─── Discretization schemes ──────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum DiscretizationScheme {
    FirstOrderUpwind,
    #[default]
    SecondOrderUpwind,
    LinearUpwind,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum PressureInterpolationScheme {
    Linear,
    Momentum,
    #[default]
    SecondOrderCentral,
    Presto,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum VofScheme {
    #[default]
    Cicsam,
    Mules,
}

// ─── Under-relaxation factors ─────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UnderRelaxationFactors {
    pub pressure: f64,
    pub pressure_final: f64,
    pub momentum: f64,
    pub momentum_final: f64,
    pub energy: f64,
    pub energy_final: f64,
    pub turbulence: f64,
    pub turbulence_final: f64,
    pub density: f64,
    pub density_final: f64,
    pub volume_fraction: f64,
    pub volume_fraction_final: f64,
}

impl Default for UnderRelaxationFactors {
    fn default() -> Self {
        Self {
            pressure: 0.3,
            pressure_final: 1.0,
            momentum: 0.7,
            momentum_final: 1.0,
            energy: 1.0,
            energy_final: 1.0,
            turbulence: 0.7,
            turbulence_final: 1.0,
            density: 1.0,
            density_final: 1.0,
            volume_fraction: 0.7,
            volume_fraction_final: 1.0,
        }
    }
}

// ─── Max iterations per time step ─────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MaxIterationsPerTimeStep {
    pub n_correctors: u32,
    pub n_non_orthogonal_correctors: u32,
}

impl Default for MaxIterationsPerTimeStep {
    fn default() -> Self {
        Self {
            n_correctors: 2,
            n_non_orthogonal_correctors: 1,
        }
    }
}

// ─── Linear solver / convergence ──────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum LinearSolverType {
    #[default]
    Gamg,
    PBiCGStab,
    Smooth,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConvergenceCriteria {
    pub absolute_tolerance: f64,
    pub relative_tolerance: f64,
}

impl Default for ConvergenceCriteria {
    fn default() -> Self {
        Self {
            absolute_tolerance: 1e-6,
            relative_tolerance: 0.1,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EquationConfig {
    pub enabled: bool,
    pub discretization: DiscretizationScheme,
    pub convergence: ConvergenceCriteria,
}

impl Default for EquationConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            discretization: DiscretizationScheme::SecondOrderUpwind,
            convergence: ConvergenceCriteria::default(),
        }
    }
}

// ─── Equations block ──────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Equations {
    pub flow: EquationConfig,
    pub energy: EquationConfig,
    pub turbulence: EquationConfig,
    pub volume_fraction: EquationConfig,
    pub species: EquationConfig,
    pub user_defined_scalars: Vec<EquationConfig>,
}

// ─── Aggregated numerical config ──────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct NumericalConfig {
    pub pressure_velocity_coupling: PressureVelocityCouplingScheme,
    pub formulation: Formulation,
    pub flux_type: FluxType,
    pub use_momentum_predictor: bool,
    pub pressure_interpolation: PressureInterpolationScheme,
    pub vof_scheme: VofScheme,
    pub under_relaxation: UnderRelaxationFactors,
    pub max_iterations: MaxIterationsPerTimeStep,
    pub equations: Equations,
    pub multiphase_max_courant_number: f64,
}
