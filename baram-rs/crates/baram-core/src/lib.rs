// baram-core: Core types, database, configuration, and project management
//
// This crate replaces:
//   - baramFlow/coredb/ (CoreDB, BoundaryDB, GeneralDB, ModelsDB, RegionDB, etc.)
//   - baramMesh/db/     (SimpleDB, configurations_schema)
//   - libbaram/simple_db/
//   - baramFlow/coredb/project.py

pub mod types;
pub mod db;
pub mod config;
pub mod project;
pub mod error;
pub mod units;

pub use error::{BaramError, Result};
