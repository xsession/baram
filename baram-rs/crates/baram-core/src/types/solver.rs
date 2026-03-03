use serde::{Deserialize, Serialize};
use std::path::PathBuf;

// ════════════════════════════════════════════════════════════════
//  Solver Backends — OpenFOAM, Elmer, FluidX3D
// ════════════════════════════════════════════════════════════════

/// Available solver backend engines.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum SolverBackend {
    #[default]
    OpenFoam,
    Elmer,
    FluidX3d,
}

impl SolverBackend {
    pub fn display_name(&self) -> &'static str {
        match self {
            Self::OpenFoam => "OpenFOAM",
            Self::Elmer    => "Elmer FEM",
            Self::FluidX3d => "FluidX3D (LBM/GPU)",
        }
    }

    pub fn all() -> &'static [SolverBackend] {
        &[Self::OpenFoam, Self::Elmer, Self::FluidX3d]
    }
}

impl std::fmt::Display for SolverBackend {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.display_name())
    }
}

// ─── Per-backend configuration ────────────────────────────────

/// OpenFOAM-specific settings.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpenFoamSettings {
    pub install_dir: Option<PathBuf>,
    pub mpi_command: String,
    pub extra_args: Vec<String>,
}

impl Default for OpenFoamSettings {
    fn default() -> Self {
        Self {
            install_dir: None,
            mpi_command: "mpirun".into(),
            extra_args: Vec::new(),
        }
    }
}

/// Elmer FEM settings.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ElmerSettings {
    pub install_dir: Option<PathBuf>,
    /// Number of mesh partitions for parallel ElmerSolver_mpi.
    pub partitions: u32,
    /// Additional .sif flags.
    pub extra_sif_flags: Vec<String>,
}

impl Default for ElmerSettings {
    fn default() -> Self {
        Self {
            install_dir: None,
            partitions: 1,
            extra_sif_flags: Vec::new(),
        }
    }
}

/// GPU device selection strategy for FluidX3D.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum GpuDeviceSelection {
    #[default]
    Auto,
    ByIndex(u32),
}

/// FluidX3D LBM/GPU settings.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FluidX3dSettings {
    pub install_dir: Option<PathBuf>,
    /// Which GPU device to use.
    pub device_selection: GpuDeviceSelection,
    /// LBM lattice resolution override (0 = auto from mesh).
    pub lattice_resolution: u32,
    /// Extra CLI arguments.
    pub extra_args: Vec<String>,
}

impl Default for FluidX3dSettings {
    fn default() -> Self {
        Self {
            install_dir: None,
            device_selection: GpuDeviceSelection::Auto,
            lattice_resolution: 0,
            extra_args: Vec::new(),
        }
    }
}

/// Project-level solver backend configuration.
/// Stores which backends are enabled and their per-backend settings.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SolverBackendsConfig {
    /// The currently-active backend for this project.
    pub active: SolverBackend,
    /// Which backends the user has enabled (can run any of these).
    pub enabled: Vec<SolverBackend>,
    pub openfoam: OpenFoamSettings,
    pub elmer: ElmerSettings,
    pub fluidx3d: FluidX3dSettings,
}

impl Default for SolverBackendsConfig {
    fn default() -> Self {
        Self {
            active: SolverBackend::OpenFoam,
            enabled: vec![SolverBackend::OpenFoam],
            openfoam: OpenFoamSettings::default(),
            elmer: ElmerSettings::default(),
            fluidx3d: FluidX3dSettings::default(),
        }
    }
}

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
    /// Which backend to use when starting.
    pub backend: SolverBackend,
}

impl Default for SolverConfig {
    fn default() -> Self {
        Self {
            num_cores: 1,
            batch_mode: false,
            status: SolverStatus::None,
            current_iteration: 0,
            last_error: None,
            backend: SolverBackend::OpenFoam,
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
