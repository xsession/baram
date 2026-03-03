use std::path::Path;
use rusqlite::{params, Connection, OptionalExtension};
use crate::error::{BaramError, Result};
use crate::types::boundary::BoundaryCondition;
use crate::types::general::GeneralConfig;
use crate::types::models::ModelsConfig;
use crate::types::numerical::NumericalConfig;
use crate::types::run::RunConditions;
use crate::types::solver::SolverBackendsConfig;

use super::schema::SCHEMA_SQL;

/// Core project database backed by SQLite.
///
/// Replaces the old CoreDB (XML + HDF5) with a single `.db` file.
pub struct ProjectDb {
    conn: Connection,
}

impl ProjectDb {
    // ─── Lifecycle ────────────────────────────────────────────
    /// Open (or create) a project database.
    pub fn open(path: &Path) -> Result<Self> {
        let conn = Connection::open(path)?;
        conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;")?;
        conn.execute_batch(SCHEMA_SQL)?;
        Ok(Self { conn })
    }

    /// Open an in-memory database (for tests or ephemeral work).
    pub fn open_memory() -> Result<Self> {
        let conn = Connection::open_in_memory()?;
        conn.execute_batch("PRAGMA foreign_keys=ON;")?;
        conn.execute_batch(SCHEMA_SQL)?;
        Ok(Self { conn })
    }

    pub fn conn(&self) -> &Connection {
        &self.conn
    }

    // ─── Project metadata (key-value) ─────────────────────────
    pub fn set_meta(&self, key: &str, value: &str) -> Result<()> {
        self.conn.execute(
            "INSERT OR REPLACE INTO project(key, value) VALUES (?1, ?2)",
            params![key, value],
        )?;
        Ok(())
    }

    pub fn get_meta(&self, key: &str) -> Result<Option<String>> {
        let v = self
            .conn
            .query_row(
                "SELECT value FROM project WHERE key = ?1",
                params![key],
                |row| row.get(0),
            )
            .optional()?;
        Ok(v)
    }

    // ─── Singleton-row helpers ────────────────────────────────
    fn upsert_singleton(&self, table: &str, json: &str) -> Result<()> {
        let sql = format!(
            "INSERT OR REPLACE INTO {table}(id, config_json) VALUES (1, ?1)"
        );
        self.conn.execute(&sql, params![json])?;
        Ok(())
    }

    fn get_singleton(&self, table: &str) -> Result<Option<String>> {
        let sql = format!("SELECT config_json FROM {table} WHERE id = 1");
        let v = self
            .conn
            .query_row(&sql, [], |row| row.get(0))
            .optional()?;
        Ok(v)
    }

    // ─── General config ───────────────────────────────────────
    pub fn save_general(&self, cfg: &GeneralConfig) -> Result<()> {
        let json = serde_json::to_string(cfg)?;
        self.upsert_singleton("general", &json)
    }

    pub fn load_general(&self) -> Result<GeneralConfig> {
        match self.get_singleton("general")? {
            Some(json) => Ok(serde_json::from_str(&json)?),
            None => {
                let cfg = GeneralConfig::default();
                self.save_general(&cfg)?;
                Ok(cfg)
            }
        }
    }

    // ─── Models config ────────────────────────────────────────
    pub fn save_models(&self, cfg: &ModelsConfig) -> Result<()> {
        let json = serde_json::to_string(cfg)?;
        self.upsert_singleton("models", &json)
    }

    pub fn load_models(&self) -> Result<ModelsConfig> {
        match self.get_singleton("models")? {
            Some(json) => Ok(serde_json::from_str(&json)?),
            None => {
                let cfg = ModelsConfig::default();
                self.save_models(&cfg)?;
                Ok(cfg)
            }
        }
    }

    // ─── Numerical config ─────────────────────────────────────
    pub fn save_numerical(&self, cfg: &NumericalConfig) -> Result<()> {
        let json = serde_json::to_string(cfg)?;
        self.upsert_singleton("numerical", &json)
    }

    pub fn load_numerical(&self) -> Result<NumericalConfig> {
        match self.get_singleton("numerical")? {
            Some(json) => Ok(serde_json::from_str(&json)?),
            None => {
                let cfg = NumericalConfig::default();
                self.save_numerical(&cfg)?;
                Ok(cfg)
            }
        }
    }

    // ─── Run conditions ───────────────────────────────────────
    pub fn save_run_conditions(&self, cfg: &RunConditions) -> Result<()> {
        let json = serde_json::to_string(cfg)?;
        self.upsert_singleton("run_conditions", &json)
    }

    pub fn load_run_conditions(&self) -> Result<RunConditions> {
        match self.get_singleton("run_conditions")? {
            Some(json) => Ok(serde_json::from_str(&json)?),
            None => {
                let cfg = RunConditions::default();
                self.save_run_conditions(&cfg)?;
                Ok(cfg)
            }
        }
    }

    // ─── Solver backends config ───────────────────────────────
    pub fn save_solver_backends(&self, cfg: &SolverBackendsConfig) -> Result<()> {
        let json = serde_json::to_string(cfg)?;
        self.upsert_singleton("solver_backends", &json)
    }

    pub fn load_solver_backends(&self) -> Result<SolverBackendsConfig> {
        match self.get_singleton("solver_backends")? {
            Some(json) => Ok(serde_json::from_str(&json)?),
            None => {
                let cfg = SolverBackendsConfig::default();
                self.save_solver_backends(&cfg)?;
                Ok(cfg)
            }
        }
    }

    // ─── Boundary conditions (CRUD) ───────────────────────────
    pub fn insert_bc(&self, region_id: i64, bc: &BoundaryCondition) -> Result<i64> {
        let json = serde_json::to_string(bc)?;
        let bc_type = format!("{:?}", bc.bc_type);
        self.conn.execute(
            "INSERT INTO boundary_conditions(name, region_id, bc_type, config_json) VALUES (?1, ?2, ?3, ?4)",
            params![bc.name, region_id, bc_type, json],
        )?;
        Ok(self.conn.last_insert_rowid())
    }

    pub fn update_bc(&self, id: i64, bc: &BoundaryCondition) -> Result<()> {
        let json = serde_json::to_string(bc)?;
        let bc_type = format!("{:?}", bc.bc_type);
        self.conn.execute(
            "UPDATE boundary_conditions SET name=?1, bc_type=?2, config_json=?3 WHERE id=?4",
            params![bc.name, bc_type, json, id],
        )?;
        Ok(())
    }

    pub fn delete_bc(&self, id: i64) -> Result<()> {
        self.conn.execute("DELETE FROM boundary_conditions WHERE id=?1", params![id])?;
        Ok(())
    }

    pub fn list_bcs(&self, region_id: i64) -> Result<Vec<(i64, BoundaryCondition)>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, config_json FROM boundary_conditions WHERE region_id=?1 ORDER BY id"
        )?;
        let rows = stmt.query_map(params![region_id], |row| {
            let id: i64 = row.get(0)?;
            let json_str: String = row.get(1)?;
            Ok((id, json_str))
        })?;
        let mut results = Vec::new();
        for row in rows {
            let (id, json_str) = row?;
            let bc: BoundaryCondition = serde_json::from_str(&json_str)
                .map_err(|e| rusqlite::Error::ToSqlConversionFailure(Box::new(e)))?;
            results.push((id, bc));
        }
        Ok(results)
    }

    // ─── Residuals (append-only time series) ──────────────────
    pub fn append_residual(&self, iteration: u64, field: &str, value: f64) -> Result<()> {
        self.conn.execute(
            "INSERT INTO residuals(iteration, field, value) VALUES (?1, ?2, ?3)",
            params![iteration as i64, field, value],
        )?;
        Ok(())
    }

    pub fn get_residuals(&self, field: &str, from_iter: u64) -> Result<Vec<(u64, f64)>> {
        let mut stmt = self.conn.prepare(
            "SELECT iteration, value FROM residuals WHERE field=?1 AND iteration>=?2 ORDER BY iteration"
        )?;
        let rows = stmt.query_map(params![field, from_iter as i64], |row| {
            Ok((row.get::<_, i64>(0)? as u64, row.get(1)?))
        })?;
        rows.collect::<std::result::Result<Vec<_>, _>>()
            .map_err(BaramError::from)
    }

    pub fn clear_residuals(&self) -> Result<()> {
        self.conn.execute("DELETE FROM residuals", [])?;
        Ok(())
    }

    // ─── Transactions ─────────────────────────────────────────
    pub fn transaction<F, T>(&mut self, f: F) -> Result<T>
    where
        F: FnOnce(&Connection) -> Result<T>,
    {
        let tx = self.conn.transaction()?;
        let result = f(&tx)?;
        tx.commit()?;
        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::boundary::BoundaryType;

    #[test]
    fn round_trip_general() {
        let db = ProjectDb::open_memory().unwrap();
        let cfg = GeneralConfig::default();
        db.save_general(&cfg).unwrap();
        let loaded = db.load_general().unwrap();
        assert_eq!(loaded.flow_type, cfg.flow_type);
    }

    #[test]
    fn crud_bc() {
        let db = ProjectDb::open_memory().unwrap();
        // Need a region first
        db.conn().execute(
            "INSERT INTO regions(name, region_type, config_json) VALUES ('default', 'Fluid', '{}')",
            [],
        ).unwrap();
        let region_id = db.conn().last_insert_rowid();

        let mut bc = BoundaryCondition::default();
        bc.name = "inlet".into();
        bc.bc_type = BoundaryType::VelocityInlet;

        let bc_id = db.insert_bc(region_id, &bc).unwrap();
        assert!(bc_id > 0);

        let list = db.list_bcs(region_id).unwrap();
        assert_eq!(list.len(), 1);
        assert_eq!(list[0].1.name, "inlet");

        bc.name = "inlet-updated".into();
        db.update_bc(bc_id, &bc).unwrap();
        let list = db.list_bcs(region_id).unwrap();
        assert_eq!(list[0].1.name, "inlet-updated");

        db.delete_bc(bc_id).unwrap();
        let list = db.list_bcs(region_id).unwrap();
        assert!(list.is_empty());
    }

    #[test]
    fn residual_timeseries() {
        let db = ProjectDb::open_memory().unwrap();
        db.append_residual(1, "p", 0.5).unwrap();
        db.append_residual(2, "p", 0.3).unwrap();
        db.append_residual(3, "p", 0.1).unwrap();
        let res = db.get_residuals("p", 2).unwrap();
        assert_eq!(res.len(), 2);
        assert_eq!(res[0], (2, 0.3));
    }
}
