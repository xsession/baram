use thiserror::Error;

#[derive(Error, Debug)]
pub enum BaramError {
    // ── Database ──
    #[error("Database error: {0}")]
    Database(#[from] rusqlite::Error),

    #[error("Value not found at path: {0}")]
    PathNotFound(String),

    #[error("Validation error at '{path}': {message}")]
    Validation { path: String, message: String },

    // ── Serialization ──
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),

    #[error("YAML error: {0}")]
    Yaml(#[from] serde_yaml::Error),

    // ── IO ──
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    // ── Project ──
    #[error("Project is locked by another process")]
    ProjectLocked,

    #[error("Project not found: {0}")]
    ProjectNotFound(String),

    #[error("Invalid project format: {0}")]
    InvalidProject(String),

    // ── Mesh ──
    #[error("Mesh error: {0}")]
    Mesh(String),

    #[error("Invalid mesh format: {0}")]
    InvalidMeshFormat(String),

    // ── OpenFOAM ──
    #[error("OpenFOAM error: {0}")]
    OpenFOAM(String),

    #[error("Solver not found: {0}")]
    SolverNotFound(String),

    #[error("Solver execution failed: {0}")]
    SolverFailed(String),

    // ── General ──
    #[error("Cancelled")]
    Cancelled,

    #[error("{0}")]
    Other(String),
}

pub type Result<T> = std::result::Result<T, BaramError>;
