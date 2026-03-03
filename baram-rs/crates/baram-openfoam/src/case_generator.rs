use std::path::Path;
use baram_core::db::ProjectDb;
use baram_core::error::Result;
use baram_core::types::general::TimeMode;
use baram_core::types::solver::SolverName;

use crate::dictionary;

// ════════════════════════════════════════════════════════════════
//  Case Generator — creates the full OpenFOAM case from the DB
// ════════════════════════════════════════════════════════════════

/// Generate all OpenFOAM dictionary files for a project.
pub fn generate_case(db: &ProjectDb, case_dir: &Path) -> Result<()> {
    let general = db.load_general()?;
    let models = db.load_models()?;
    let numerical = db.load_numerical()?;
    let run_conds = db.load_run_conditions()?;

    let solver_name = select_solver(&general, &models);

    // Ensure directories exist
    let constant = case_dir.join("constant");
    let system = case_dir.join("system");
    let zero = case_dir.join("0");
    std::fs::create_dir_all(&constant)?;
    std::fs::create_dir_all(&system)?;
    std::fs::create_dir_all(&zero)?;

    // ─── system/ ──────────────────────────────────────────────
    std::fs::write(
        system.join("controlDict"),
        dictionary::control_dict(&general, &run_conds, solver_name.executable()),
    )?;
    std::fs::write(
        system.join("fvSchemes"),
        dictionary::fv_schemes(&general, &numerical),
    )?;
    std::fs::write(
        system.join("fvSolution"),
        dictionary::fv_solution(&numerical),
    )?;

    // ─── constant/ ────────────────────────────────────────────
    std::fs::write(
        constant.join("turbulenceProperties"),
        dictionary::turbulence_properties(&models),
    )?;
    std::fs::write(
        constant.join("g"),
        dictionary::gravity_file(
            general.operating_conditions.gravity.direction[0] * general.operating_conditions.gravity.magnitude,
            general.operating_conditions.gravity.direction[1] * general.operating_conditions.gravity.magnitude,
            general.operating_conditions.gravity.direction[2] * general.operating_conditions.gravity.magnitude,
        ),
    )?;

    tracing::info!("Case generated at {}", case_dir.display());
    Ok(())
}

/// Select the appropriate solver based on the configuration.
/// Mirrors `findSolver()` from the Python codebase.
pub fn select_solver(
    general: &baram_core::types::general::GeneralConfig,
    models: &baram_core::types::models::ModelsConfig,
) -> SolverName {
    let is_transient = general.time_mode == TimeMode::Transient;
    let is_density_based = general.solver_type == baram_core::types::general::SolverType::DensityBased;

    // Density-based → aero solvers
    if is_density_based {
        return if is_transient {
            SolverName::UTSLAeroFoam
        } else {
            SolverName::TSLAeroFoam
        };
    }

    // DPM
    if models.dpm_particle_type != baram_core::types::models::DpmParticleType::None {
        return if is_transient {
            SolverName::ThermoParcelBuoyantPimpleNFoam
        } else {
            SolverName::ThermoParcelBuoyantSimpleNFoam
        };
    }

    // Multiphase VOF
    if models.multiphase != baram_core::types::models::MultiphaseModel::Off {
        return SolverName::InterFoam;
    }

    // Default: buoyant solvers
    if is_transient {
        SolverName::BuoyantPimpleNFoam
    } else {
        SolverName::BuoyantSimpleNFoam
    }
}
