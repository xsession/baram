use serde::{Deserialize, Serialize};
use std::path::PathBuf;

// ════════════════════════════════════════════════════════════════
//  Application / project configuration — replaces local.cfg
// ════════════════════════════════════════════════════════════════

/// Per-installation / user configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub openfoam_dir: PathBuf,
    pub paraview_dir: PathBuf,
    pub elmer_dir: PathBuf,
    pub fluidx3d_dir: PathBuf,
    pub recent_projects: Vec<PathBuf>,
    pub max_recent: usize,
    pub num_cores: u32,
    pub language: String,
    pub scale_factor: f64,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            openfoam_dir: PathBuf::new(),
            paraview_dir: PathBuf::new(),
            elmer_dir: PathBuf::new(),
            fluidx3d_dir: PathBuf::new(),
            recent_projects: Vec::new(),
            max_recent: 10,
            num_cores: num_cpus_hint(),
            language: "en".into(),
            scale_factor: 1.0,
        }
    }
}

fn num_cpus_hint() -> u32 {
    std::thread::available_parallelism()
        .map(|n| n.get() as u32)
        .unwrap_or(4)
}

impl AppConfig {
    /// Load from a YAML file; returns default if the file doesn't exist.
    pub fn load(path: &std::path::Path) -> Self {
        match std::fs::read_to_string(path) {
            Ok(text) => serde_yaml::from_str(&text).unwrap_or_default(),
            Err(_) => Self::default(),
        }
    }

    /// Persist to a YAML file.
    pub fn save(&self, path: &std::path::Path) -> crate::error::Result<()> {
        let yaml = serde_yaml::to_string(self)
            .map_err(|e| crate::error::BaramError::Other(e.to_string()))?;
        std::fs::write(path, yaml)?;
        Ok(())
    }

    /// Push a project path to the recent list (dedup + trim).
    pub fn push_recent(&mut self, path: PathBuf) {
        self.recent_projects.retain(|p| p != &path);
        self.recent_projects.insert(0, path);
        self.recent_projects.truncate(self.max_recent);
    }
}
