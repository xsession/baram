use serde::{Deserialize, Serialize};

// ════════════════════════════════════════════════════════════════
//  Solver — status, selection logic, solver config
// ════════════════════════════════════════════════════════════════

/// Runtime status of the solver process
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum SolverStatus {
    #[default]
    None,
    Waiting,
    Running,
    Ended,
    Error,
}

/// Known OpenFOAM solver executables (from findSolver logic)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SolverName {
    // ── Density-based aero ──
    UTSLAeroFoam,      // Unsteady, transonic/supersonic, laminar
    TSLAeroFoam,        // Steady, transonic/supersonic

    // ── DPM ──
    ThermoParcelBuoyantPimpleNFoam,
    ThermoParcelBuoyantSimpleNFoam,
    ReactingParcelFoam,

    // ── Multiphase ──
    MultiphaseInterFoam,
    InterPhaseChangeDyMFoam,
    InterPhaseChangeFoam,
    InterFoam,

    // ── CHT multi-region ──
    ChtMultiRegionPimpleNFoam,
    ChtMultiRegionSimpleNFoam,

    // ── Buoyant thermal ──
    BuoyantPimpleNFoam,
    BuoyantSimpleNFoam,
}

impl SolverName {
    /// OpenFOAM executable name
    pub fn executable(&self) -> &'static str {
        match self {
            Self::UTSLAeroFoam                    => "UTSLAeroFoam",
            Self::TSLAeroFoam                     => "TSLAeroFoam",
            Self::ThermoParcelBuoyantPimpleNFoam  => "thermoParcelBuoyantPimpleNFoam",
            Self::ThermoParcelBuoyantSimpleNFoam  => "thermoParcelBuoyantSimpleNFoam",
            Self::ReactingParcelFoam              => "reactingParcelFoam",
            Self::MultiphaseInterFoam             => "multiphaseInterFoam",
            Self::InterPhaseChangeDyMFoam         => "interPhaseChangeDyMFoam",
            Self::InterPhaseChangeFoam            => "interPhaseChangeFoam",
            Self::InterFoam                       => "interFoam",
            Self::ChtMultiRegionPimpleNFoam       => "chtMultiRegionPimpleNFoam",
            Self::ChtMultiRegionSimpleNFoam       => "chtMultiRegionSimpleNFoam",
            Self::BuoyantPimpleNFoam              => "buoyantPimpleNFoam",
            Self::BuoyantSimpleNFoam              => "buoyantSimpleNFoam",
        }
    }

    /// Whether this solver is transient
    pub fn is_transient(&self) -> bool {
        matches!(
            self,
            Self::UTSLAeroFoam
                | Self::ThermoParcelBuoyantPimpleNFoam
                | Self::MultiphaseInterFoam
                | Self::InterPhaseChangeDyMFoam
                | Self::InterPhaseChangeFoam
                | Self::InterFoam
                | Self::ChtMultiRegionPimpleNFoam
                | Self::BuoyantPimpleNFoam
        )
    }
}

/// Solver-process parameters
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SolverConfig {
    pub num_cores: u32,
    pub batch_mode: bool,
    pub status: SolverStatus,
    pub current_iteration: u64,
    pub last_error: Option<String>,
}

impl Default for SolverConfig {
    fn default() -> Self {
        Self {
            num_cores: 1,
            batch_mode: false,
            status: SolverStatus::None,
            current_iteration: 0,
            last_error: None,
        }
    }
}

/// Residual data point (for live plotting)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResidualPoint {
    pub iteration: u64,
    pub field: String,
    pub value: f64,
}
