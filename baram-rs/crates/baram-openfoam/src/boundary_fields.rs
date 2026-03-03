use baram_core::types::boundary::{BoundaryCondition, BoundaryType};
use crate::file_header::FoamFileHeader;
use std::fmt::Write;

// ════════════════════════════════════════════════════════════════
//  Boundary field file writers (U, p, T, k, epsilon, omega, nut)
// ════════════════════════════════════════════════════════════════

/// Write the velocity field `U` boundary file.
pub fn write_velocity_field(
    boundaries: &[(String, BoundaryCondition)],
    internal_field: &[f64; 3],
) -> String {
    let header = FoamFileHeader::new("volVectorField", "U").render();
    let mut s = String::new();
    let _ = write!(s, "{header}\n");
    let _ = writeln!(s, "dimensions      [0 1 -1 0 0 0 0];\n");
    let _ = writeln!(
        s,
        "internalField   uniform ({} {} {});\n",
        internal_field[0], internal_field[1], internal_field[2]
    );
    let _ = writeln!(s, "boundaryField\n{{");

    for (name, bc) in boundaries {
        let _ = writeln!(s, "    {name}\n    {{");
        match bc.bc_type {
            BoundaryType::VelocityInlet => {
                let v = bc.velocity.component;
                let _ = writeln!(s, "        type            fixedValue;");
                let _ = writeln!(s, "        value           uniform ({} {} {});", v[0], v[1], v[2]);
            }
            BoundaryType::PressureInlet | BoundaryType::PressureOutlet => {
                let _ = writeln!(s, "        type            pressureInletOutletVelocity;");
                let _ = writeln!(s, "        value           uniform (0 0 0);");
            }
            BoundaryType::Wall | BoundaryType::ThermoCoupledWall => {
                let _ = writeln!(s, "        type            noSlip;");
            }
            BoundaryType::Symmetry => {
                let _ = writeln!(s, "        type            symmetry;");
            }
            BoundaryType::FreeStream => {
                let dir = bc.free_stream.flow_direction;
                let mag = bc.free_stream.free_stream_velocity;
                let v = [dir[0] * mag, dir[1] * mag, dir[2] * mag];
                let _ = writeln!(s, "        type            freestreamVelocity;");
                let _ = writeln!(s, "        freestreamValue uniform ({} {} {});", v[0], v[1], v[2]);
            }
            BoundaryType::Outflow => {
                let _ = writeln!(s, "        type            zeroGradient;");
            }
            _ => {
                let _ = writeln!(s, "        type            zeroGradient;");
            }
        }
        let _ = writeln!(s, "    }}");
    }

    let _ = writeln!(s, "}}");
    s
}

/// Write the pressure field `p` or `p_rgh` boundary file.
pub fn write_pressure_field(
    field_name: &str,
    boundaries: &[(String, BoundaryCondition)],
    internal_value: f64,
) -> String {
    let header = FoamFileHeader::new("volScalarField", field_name).render();
    let mut s = String::new();
    let _ = write!(s, "{header}\n");
    let _ = writeln!(s, "dimensions      [0 2 -2 0 0 0 0];\n");
    let _ = writeln!(s, "internalField   uniform {internal_value};\n");
    let _ = writeln!(s, "boundaryField\n{{");

    for (name, bc) in boundaries {
        let _ = writeln!(s, "    {name}\n    {{");
        match bc.bc_type {
            BoundaryType::VelocityInlet => {
                let _ = writeln!(s, "        type            zeroGradient;");
            }
            BoundaryType::PressureInlet | BoundaryType::PressureOutlet => {
                let _ = writeln!(s, "        type            fixedValue;");
                let _ = writeln!(s, "        value           uniform {};", bc.pressure.pressure);
            }
            BoundaryType::Wall | BoundaryType::ThermoCoupledWall => {
                let _ = writeln!(s, "        type            zeroGradient;");
            }
            BoundaryType::Symmetry => {
                let _ = writeln!(s, "        type            symmetry;");
            }
            BoundaryType::Outflow => {
                let _ = writeln!(s, "        type            fixedValue;");
                let _ = writeln!(s, "        value           uniform 0;");
            }
            _ => {
                let _ = writeln!(s, "        type            zeroGradient;");
            }
        }
        let _ = writeln!(s, "    }}");
    }

    let _ = writeln!(s, "}}");
    s
}

/// Write a scalar turbulence field (k, epsilon, omega, nut, nuTilda).
pub fn write_turbulence_field(
    field_name: &str,
    dimensions: &str,
    boundaries: &[(String, BoundaryCondition)],
    internal_value: f64,
) -> String {
    let header = FoamFileHeader::new("volScalarField", field_name).render();
    let mut s = String::new();
    let _ = write!(s, "{header}\n");
    let _ = writeln!(s, "dimensions      {dimensions};\n");
    let _ = writeln!(s, "internalField   uniform {internal_value};\n");
    let _ = writeln!(s, "boundaryField\n{{");

    for (name, bc) in boundaries {
        let _ = writeln!(s, "    {name}\n    {{");
        match bc.bc_type {
            BoundaryType::Wall | BoundaryType::ThermoCoupledWall => {
                if field_name == "nut" || field_name == "nuTilda" {
                    let _ = writeln!(s, "        type            nutkWallFunction;");
                    let _ = writeln!(s, "        value           uniform 0;");
                } else if field_name == "k" {
                    let _ = writeln!(s, "        type            kqRWallFunction;");
                    let _ = writeln!(s, "        value           uniform {internal_value};");
                } else if field_name == "epsilon" {
                    let _ = writeln!(s, "        type            epsilonWallFunction;");
                    let _ = writeln!(s, "        value           uniform {internal_value};");
                } else if field_name == "omega" {
                    let _ = writeln!(s, "        type            omegaWallFunction;");
                    let _ = writeln!(s, "        value           uniform {internal_value};");
                }
            }
            BoundaryType::Symmetry => {
                let _ = writeln!(s, "        type            symmetry;");
            }
            _ => {
                let _ = writeln!(s, "        type            fixedValue;");
                let _ = writeln!(s, "        value           uniform {internal_value};");
            }
        }
        let _ = writeln!(s, "    }}");
    }

    let _ = writeln!(s, "}}");
    s
}
