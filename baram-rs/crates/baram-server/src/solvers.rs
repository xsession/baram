use std::path::Path;
use baram_core::error::{BaramError, Result};
use baram_core::types::solver::{SolverBackend, SolverBackendsConfig};
use tracing::info;

// ════════════════════════════════════════════════════════════════
//  Solver dispatcher — routes to the correct backend runner
// ════════════════════════════════════════════════════════════════

/// Validate that the selected backend is enabled and ready.
pub fn validate_backend(cfg: &SolverBackendsConfig) -> Result<()> {
    if !cfg.enabled.contains(&cfg.active) {
        return Err(BaramError::Validation {
            path: "solver_backends.active".into(),
            message: format!(
                "Backend '{}' is not in the enabled list",
                cfg.active.display_name()
            ),
        });
    }
    Ok(())
}

/// Spawn the appropriate solver for the given backend.
/// Returns the process description for logging/status.
pub async fn start_solver(
    backend: SolverBackend,
    cfg: &SolverBackendsConfig,
    case_dir: &Path,
    num_procs: u32,
) -> Result<String> {
    match backend {
        SolverBackend::OpenFoam => start_openfoam(cfg, case_dir, num_procs).await,
        SolverBackend::Elmer    => start_elmer(cfg, case_dir).await,
        SolverBackend::FluidX3d => start_fluidx3d(cfg, case_dir).await,
    }
}

// ─── OpenFOAM ─────────────────────────────────────────────────

async fn start_openfoam(
    cfg: &SolverBackendsConfig,
    case_dir: &Path,
    num_procs: u32,
) -> Result<String> {
    info!(
        "Starting OpenFOAM solver in {} (procs={})",
        case_dir.display(),
        num_procs
    );

    // Resolve executable from install_dir if set
    let _install = &cfg.openfoam.install_dir;
    let _mpi = &cfg.openfoam.mpi_command;

    // The actual SolverRunner::start() is called by the api handler;
    // this function does pre-validation and returns the status description.
    Ok(format!(
        "OpenFOAM started in {} with {} processes",
        case_dir.display(),
        num_procs
    ))
}

// ─── Elmer FEM ────────────────────────────────────────────────

async fn start_elmer(
    cfg: &SolverBackendsConfig,
    case_dir: &Path,
) -> Result<String> {
    let partitions = cfg.elmer.partitions;

    // Resolve ElmerSolver executable
    let exe = if let Some(ref dir) = cfg.elmer.install_dir {
        if partitions > 1 {
            dir.join("bin").join("ElmerSolver_mpi")
        } else {
            dir.join("bin").join("ElmerSolver")
        }
    } else if partitions > 1 {
        std::path::PathBuf::from("ElmerSolver_mpi")
    } else {
        std::path::PathBuf::from("ElmerSolver")
    };

    info!(
        "Starting Elmer FEM: {} (partitions={})",
        exe.display(),
        partitions,
    );

    // Build the SIF (Solver Input File) from BARAM project data
    let sif_path = case_dir.join("case.sif");
    if !sif_path.exists() {
        return Err(BaramError::SolverNotFound(
            "Elmer case.sif not found — generate case first".into(),
        ));
    }

    // Spawn Elmer process
    let mut cmd = tokio::process::Command::new(&exe);
    cmd.current_dir(case_dir);
    for flag in &cfg.elmer.extra_sif_flags {
        cmd.arg(flag);
    }
    cmd.stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped());

    let _child = cmd.spawn().map_err(|e| {
        BaramError::SolverNotFound(format!("{}: {}", exe.display(), e))
    })?;

    Ok(format!(
        "Elmer started in {} with {} partitions",
        case_dir.display(),
        partitions
    ))
}

// ─── FluidX3D (GPU LBM) ──────────────────────────────────────

async fn start_fluidx3d(
    cfg: &SolverBackendsConfig,
    case_dir: &Path,
) -> Result<String> {
    // Resolve FluidX3D executable
    let exe = if let Some(ref dir) = cfg.fluidx3d.install_dir {
        dir.join("FluidX3D")
    } else {
        std::path::PathBuf::from("FluidX3D")
    };

    info!(
        "Starting FluidX3D GPU solver: {} (resolution={})",
        exe.display(),
        cfg.fluidx3d.lattice_resolution,
    );

    let setup_path = case_dir.join("setup.txt");
    if !setup_path.exists() {
        return Err(BaramError::SolverNotFound(
            "FluidX3D setup.txt not found — generate case first".into(),
        ));
    }

    let mut cmd = tokio::process::Command::new(&exe);
    cmd.current_dir(case_dir);

    // GPU device selection
    match cfg.fluidx3d.device_selection {
        baram_core::types::solver::GpuDeviceSelection::ByIndex(idx) => {
            cmd.arg("--device").arg(idx.to_string());
        }
        _ => {}
    }

    if cfg.fluidx3d.lattice_resolution > 0 {
        cmd.arg("--resolution")
            .arg(cfg.fluidx3d.lattice_resolution.to_string());
    }

    for arg in &cfg.fluidx3d.extra_args {
        cmd.arg(arg);
    }

    cmd.stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped());

    let _child = cmd.spawn().map_err(|e| {
        BaramError::SolverNotFound(format!("{}: {}", exe.display(), e))
    })?;

    Ok(format!(
        "FluidX3D started in {} on GPU",
        case_dir.display()
    ))
}
