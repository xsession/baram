use std::fmt::Write;
use crate::file_header::FoamFileHeader;
use baram_core::types::general::GeneralConfig;
use baram_core::types::models::{ModelsConfig, TurbulenceModel};
use baram_core::types::numerical::NumericalConfig;
use baram_core::types::run::RunConditions;

// ════════════════════════════════════════════════════════════════
//  OpenFOAM Dictionary Generation — replaces Python dict writers
// ════════════════════════════════════════════════════════════════

/// Generate `controlDict` content.
pub fn control_dict(
    general: &GeneralConfig,
    run: &RunConditions,
    solver_name: &str,
) -> String {
    let header = FoamFileHeader::new("dictionary", "controlDict").render();
    let is_transient = general.time_mode == baram_core::types::general::TimeMode::Transient;

    let mut s = String::new();
    let _ = write!(s, "{header}\n");
    let _ = writeln!(s, "application     {solver_name};");
    let _ = writeln!(s, "startFrom       latestTime;");
    let _ = writeln!(s, "startTime       0;");

    if is_transient {
        let _ = writeln!(s, "stopAt          endTime;");
        let _ = writeln!(s, "endTime         {};", run.end_time);
        let _ = writeln!(s, "deltaT          {};", run.time_stepping.time_step_size);
    } else {
        let _ = writeln!(s, "stopAt          endTime;");
        let _ = writeln!(s, "endTime         {};", run.number_of_iterations);
        let _ = writeln!(s, "deltaT          1;");
    }

    let write_format = match run.data_write_format {
        baram_core::types::run::DataWriteFormat::Binary => "binary",
        baram_core::types::run::DataWriteFormat::Ascii => "ascii",
    };

    let _ = writeln!(s, "writeControl    timeStep;");
    let _ = writeln!(s, "writeInterval   {};", run.report_interval_steps);
    let _ = writeln!(s, "purgeWrite      {};", run.retain_only_last_n.unwrap_or(0));
    let _ = writeln!(s, "writeFormat     {write_format};");
    let _ = writeln!(s, "writePrecision  6;");
    let _ = writeln!(s, "writeCompression uncompressed;");
    let _ = writeln!(s, "timeFormat      general;");
    let _ = writeln!(s, "timePrecision   6;");
    let _ = writeln!(s, "runTimeModifiable yes;");

    s
}

/// Generate `fvSchemes` content.
pub fn fv_schemes(general: &GeneralConfig, _numerical: &NumericalConfig) -> String {
    let header = FoamFileHeader::new("dictionary", "fvSchemes").render();
    let is_transient = general.time_mode == baram_core::types::general::TimeMode::Transient;

    let mut s = String::new();
    let _ = write!(s, "{header}\n");

    // ddtSchemes
    let _ = writeln!(s, "ddtSchemes\n{{");
    if is_transient {
        let _ = writeln!(s, "    default         Euler;");
    } else {
        let _ = writeln!(s, "    default         steadyState;");
    }
    let _ = writeln!(s, "}}\n");

    // gradSchemes
    let _ = writeln!(s, "gradSchemes\n{{");
    let _ = writeln!(s, "    default         Gauss linear;");
    let _ = writeln!(s, "}}\n");

    // divSchemes
    let _ = writeln!(s, "divSchemes\n{{");
    let _ = writeln!(s, "    default         none;");
    let _ = writeln!(s, "    div(phi,U)      bounded Gauss linearUpwind grad(U);");
    let _ = writeln!(s, "    div(phi,k)      bounded Gauss upwind;");
    let _ = writeln!(s, "    div(phi,epsilon) bounded Gauss upwind;");
    let _ = writeln!(s, "    div(phi,omega)  bounded Gauss upwind;");
    let _ = writeln!(s, "    div((nuEff*dev2(T(grad(U))))) Gauss linear;");
    let _ = writeln!(s, "}}\n");

    // laplacianSchemes
    let _ = writeln!(s, "laplacianSchemes\n{{");
    let _ = writeln!(s, "    default         Gauss linear corrected;");
    let _ = writeln!(s, "}}\n");

    // interpolationSchemes
    let _ = writeln!(s, "interpolationSchemes\n{{");
    let _ = writeln!(s, "    default         linear;");
    let _ = writeln!(s, "}}\n");

    // snGradSchemes
    let _ = writeln!(s, "snGradSchemes\n{{");
    let _ = writeln!(s, "    default         corrected;");
    let _ = writeln!(s, "}}");

    s
}

/// Generate `fvSolution` content.
pub fn fv_solution(numerical: &NumericalConfig) -> String {
    let header = FoamFileHeader::new("dictionary", "fvSolution").render();
    let urf = &numerical.under_relaxation;

    let mut s = String::new();
    let _ = write!(s, "{header}\n");

    // Solvers block
    let _ = writeln!(s, "solvers\n{{");
    let _ = writeln!(s, "    p\n    {{");
    let _ = writeln!(s, "        solver          GAMG;");
    let _ = writeln!(s, "        smoother        GaussSeidel;");
    let _ = writeln!(s, "        tolerance       1e-06;");
    let _ = writeln!(s, "        relTol          0.1;");
    let _ = writeln!(s, "    }}");
    let _ = writeln!(s, "    \"(U|k|epsilon|omega|nuTilda)\"\n    {{");
    let _ = writeln!(s, "        solver          PBiCGStab;");
    let _ = writeln!(s, "        preconditioner  DILU;");
    let _ = writeln!(s, "        tolerance       1e-06;");
    let _ = writeln!(s, "        relTol          0.1;");
    let _ = writeln!(s, "    }}");
    let _ = writeln!(s, "}}\n");

    // SIMPLE / PIMPLE block
    let method = match numerical.pressure_velocity_coupling {
        baram_core::types::numerical::PressureVelocityCouplingScheme::Simple => "SIMPLE",
        baram_core::types::numerical::PressureVelocityCouplingScheme::Simplec => "SIMPLE",
    };
    let _ = writeln!(s, "{method}\n{{");
    let _ = writeln!(s, "    nNonOrthogonalCorrectors {};", numerical.max_iterations.n_non_orthogonal_correctors);
    let _ = writeln!(s, "    consistent      yes;");
    let _ = writeln!(s, "}}\n");

    // relaxationFactors
    let _ = writeln!(s, "relaxationFactors\n{{");
    let _ = writeln!(s, "    fields\n    {{");
    let _ = writeln!(s, "        p               {};", urf.pressure);
    let _ = writeln!(s, "    }}");
    let _ = writeln!(s, "    equations\n    {{");
    let _ = writeln!(s, "        U               {};", urf.momentum);
    let _ = writeln!(s, "        k               {};", urf.turbulence);
    let _ = writeln!(s, "        epsilon         {};", urf.turbulence);
    let _ = writeln!(s, "        omega           {};", urf.turbulence);
    let _ = writeln!(s, "    }}");
    let _ = writeln!(s, "}}");

    s
}

/// Generate `turbulenceProperties` content.
pub fn turbulence_properties(models: &ModelsConfig) -> String {
    let header = FoamFileHeader::new("dictionary", "turbulenceProperties").render();
    let mut s = String::new();
    let _ = write!(s, "{header}\n");

    match models.turbulence.model {
        TurbulenceModel::Inviscid | TurbulenceModel::Laminar => {
            let _ = writeln!(s, "simulationType  laminar;");
        }
        TurbulenceModel::KEpsilon | TurbulenceModel::KOmega | TurbulenceModel::SpalartAllmaras => {
            let _ = writeln!(s, "simulationType  RAS;");
            let _ = writeln!(s, "RAS\n{{");
            match models.turbulence.model {
                TurbulenceModel::KEpsilon => {
                    let model_name = match models.turbulence.k_epsilon_model {
                        baram_core::types::models::KEpsilonModel::Standard => "kEpsilon",
                        baram_core::types::models::KEpsilonModel::Rng => "RNGkEpsilon",
                        baram_core::types::models::KEpsilonModel::Realizable => "realizableKE",
                    };
                    let _ = writeln!(s, "    RASModel        {model_name};");
                }
                TurbulenceModel::KOmega => {
                    let _ = writeln!(s, "    RASModel        kOmegaSST;");
                }
                TurbulenceModel::SpalartAllmaras => {
                    let _ = writeln!(s, "    RASModel        SpalartAllmaras;");
                }
                _ => {}
            }
            let _ = writeln!(s, "    turbulence      on;");
            let _ = writeln!(s, "    printCoeffs     on;");
            let _ = writeln!(s, "}}");
        }
        TurbulenceModel::Des => {
            let _ = writeln!(s, "simulationType  LES;");
            let _ = writeln!(s, "LES\n{{");
            let _ = writeln!(s, "    LESModel        SpalartAllmarasDES;");
            let _ = writeln!(s, "    turbulence      on;");
            let _ = writeln!(s, "    printCoeffs     on;");
            let _ = writeln!(s, "}}");
        }
        TurbulenceModel::Les => {
            let _ = writeln!(s, "simulationType  LES;");
            let _ = writeln!(s, "LES\n{{");
            let model_name = match models.turbulence.subgrid_scale_model {
                baram_core::types::models::SubgridScaleModel::Smagorinsky => "Smagorinsky",
                baram_core::types::models::SubgridScaleModel::Wale => "WALE",
                baram_core::types::models::SubgridScaleModel::DynamicKEqn => "dynamicKEqn",
                baram_core::types::models::SubgridScaleModel::KEqn => "kEqn",
            };
            let _ = writeln!(s, "    LESModel        {model_name};");
            let _ = writeln!(s, "    turbulence      on;");
            let _ = writeln!(s, "    printCoeffs     on;");
            let _ = writeln!(s, "}}");
        }
    }

    s
}

/// Generate `transportProperties` content (simplified for constant viscosity).
pub fn transport_properties(kinematic_viscosity: f64) -> String {
    let header = FoamFileHeader::new("dictionary", "transportProperties").render();
    let mut s = String::new();
    let _ = write!(s, "{header}\n");
    let _ = writeln!(s, "transportModel  Newtonian;");
    let _ = writeln!(s, "nu              [0 2 -1 0 0 0 0] {kinematic_viscosity};");
    s
}

/// Generate gravity vector file `g`.
pub fn gravity_file(gx: f64, gy: f64, gz: f64) -> String {
    let header = FoamFileHeader::new("uniformDimensionedVectorField", "g").render();
    let mut s = String::new();
    let _ = write!(s, "{header}\n");
    let _ = writeln!(s, "dimensions      [0 1 -2 0 0 0 0];");
    let _ = writeln!(s, "value           ({gx} {gy} {gz});");
    s
}

/// Generate `decomposeParDict` for parallel runs.
pub fn decompose_par_dict(n_procs: u32) -> String {
    let header = FoamFileHeader::new("dictionary", "decomposeParDict").render();
    let mut s = String::new();
    let _ = write!(s, "{header}\n");
    let _ = writeln!(s, "numberOfSubdomains  {n_procs};");
    let _ = writeln!(s, "method          scotch;");
    s
}
