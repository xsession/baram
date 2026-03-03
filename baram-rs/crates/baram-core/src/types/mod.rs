// Types module — all domain enums and data structures
//
// Replaces every Python enum across baramFlow/coredb and baramMesh/db

pub mod boundary;
pub mod general;
pub mod models;
pub mod cell_zone;
pub mod materials;
pub mod numerical;
pub mod mesh;
pub mod monitors;
pub mod solver;
pub mod region;
pub mod run;
pub mod meshing;  // baramMesh step/geometry schema

pub use boundary::*;
pub use general::*;
pub use models::*;
pub use cell_zone::*;
pub use numerical::*;
pub use mesh::*;
pub use solver::*;
