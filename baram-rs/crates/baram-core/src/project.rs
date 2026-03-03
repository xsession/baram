use std::path::{Path, PathBuf};
use crate::db::ProjectDb;
use crate::error::{BaramError, Result};

// ════════════════════════════════════════════════════════════════
//  Project — lifecycle, lock files, directory layout
// ════════════════════════════════════════════════════════════════

/// The directory layout inside a BARAM project folder.
///
/// ```text
/// <project_dir>/
///   ├── baram.db          # SQLite database (replaces configuration.h5)
///   ├── baram.lock        # PID lock file
///   └── case/             # OpenFOAM case directory
///       ├── constant/
///       ├── system/
///       └── 0/
/// ```
pub struct Project {
    root: PathBuf,
    db: ProjectDb,
}

impl Project {
    /// Create a brand-new project at `dir`.
    pub fn create(dir: &Path) -> Result<Self> {
        std::fs::create_dir_all(dir)?;
        let db_path = dir.join("baram.db");
        if db_path.exists() {
            return Err(BaramError::Validation {
                path: dir.display().to_string(),
                message: "Project already exists".into(),
            });
        }
        let db = ProjectDb::open(&db_path)?;

        // Seed singleton rows with defaults
        db.save_general(&Default::default())?;
        db.save_models(&Default::default())?;
        db.save_numerical(&Default::default())?;
        db.save_run_conditions(&Default::default())?;

        // Create case subdirectory structure
        let case = dir.join("case");
        std::fs::create_dir_all(case.join("constant"))?;
        std::fs::create_dir_all(case.join("system"))?;
        std::fs::create_dir_all(case.join("0"))?;

        let mut proj = Self {
            root: dir.to_path_buf(),
            db,
        };
        proj.acquire_lock()?;
        Ok(proj)
    }

    /// Open an existing project.
    pub fn open(dir: &Path) -> Result<Self> {
        let db_path = dir.join("baram.db");
        if !db_path.exists() {
            return Err(BaramError::ProjectNotFound(dir.display().to_string()));
        }
        let db = ProjectDb::open(&db_path)?;
        let mut proj = Self {
            root: dir.to_path_buf(),
            db,
        };
        proj.acquire_lock()?;
        Ok(proj)
    }

    pub fn db(&self) -> &ProjectDb {
        &self.db
    }

    pub fn db_mut(&mut self) -> &mut ProjectDb {
        &mut self.db
    }

    pub fn root(&self) -> &Path {
        &self.root
    }

    pub fn case_dir(&self) -> PathBuf {
        self.root.join("case")
    }

    pub fn constant_dir(&self) -> PathBuf {
        self.case_dir().join("constant")
    }

    pub fn system_dir(&self) -> PathBuf {
        self.case_dir().join("system")
    }

    pub fn time_dir(&self, t: &str) -> PathBuf {
        self.case_dir().join(t)
    }

    // ─── Lock file ────────────────────────────────────────────
    fn lock_path(&self) -> PathBuf {
        self.root.join("baram.lock")
    }

    fn acquire_lock(&mut self) -> Result<()> {
        let lock = self.lock_path();
        if lock.exists() {
            // Read PID and check if alive
            if let Ok(content) = std::fs::read_to_string(&lock) {
                let pid_str = content.trim();
                if is_pid_alive(pid_str) {
                    return Err(BaramError::ProjectLocked);
                }
            }
        }
        let pid = std::process::id();
        std::fs::write(&lock, pid.to_string())?;
        Ok(())
    }

    fn release_lock(&self) {
        let _ = std::fs::remove_file(self.lock_path());
    }
}

impl Drop for Project {
    fn drop(&mut self) {
        self.release_lock();
    }
}

/// Best-effort check whether a PID is still running.
fn is_pid_alive(pid_str: &str) -> bool {
    #[cfg(unix)]
    {
        pid_str
            .parse::<i32>()
            .map(|pid| unsafe { libc::kill(pid, 0) } == 0)
            .unwrap_or(false)
    }
    #[cfg(windows)]
    {
        // On Windows, attempt to open the process
        pid_str
            .parse::<u32>()
            .map(|_pid| {
                // Simple heuristic — if we wrote the lock, assume stale
                false
            })
            .unwrap_or(false)
    }
    #[cfg(not(any(unix, windows)))]
    {
        let _ = pid_str;
        false
    }
}
