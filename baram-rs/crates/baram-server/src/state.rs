use std::path::PathBuf;
use std::sync::Arc;
use dashmap::DashMap;
use baram_core::config::AppConfig;
use baram_core::project::Project;
use tokio::sync::{Mutex, RwLock};

// ════════════════════════════════════════════════════════════════
//  Application State — shared across all Axum handlers
// ════════════════════════════════════════════════════════════════

/// Global server state, cheaply cloneable via Arc.
#[derive(Clone)]
pub struct AppState {
    pub inner: Arc<AppStateInner>,
}

pub struct AppStateInner {
    /// Currently open projects (id → Project).
    /// Uses Mutex instead of RwLock because rusqlite::Connection is Send but not Sync.
    pub projects: DashMap<String, Mutex<Project>>,
    /// Application configuration (will be used for settings endpoints).
    #[allow(dead_code)]
    pub config: RwLock<AppConfig>,
    /// WebSocket event broadcast channels (per project).
    pub event_senders: DashMap<String, tokio::sync::broadcast::Sender<String>>,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            inner: Arc::new(AppStateInner {
                projects: DashMap::new(),
                config: RwLock::new(AppConfig::default()),
                event_senders: DashMap::new(),
            }),
        }
    }

    /// Open or create a project and register it.
    pub async fn open_project(&self, id: &str, path: PathBuf) -> baram_core::error::Result<()> {
        let project = if path.join("baram.db").exists() {
            Project::open(&path)?
        } else {
            Project::create(&path)?
        };
        self.inner.projects.insert(id.to_string(), Mutex::new(project));

        // Create a broadcast channel for real-time events
        let (tx, _) = tokio::sync::broadcast::channel(256);
        self.inner.event_senders.insert(id.to_string(), tx);

        Ok(())
    }

    pub fn broadcast(&self, project_id: &str, msg: &str) {
        if let Some(tx) = self.inner.event_senders.get(project_id) {
            let _ = tx.send(msg.to_string());
        }
    }
}
