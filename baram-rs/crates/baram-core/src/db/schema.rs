/// SQLite schema: replaces XML/XSD + HDF5 storage from CoreDB / SimpleDB.
///
/// Every table maps 1 : 1 to a top-level section in the old XML schema.
/// Blob-typed columns store serde_json payloads for flexibility, while
/// the most-queried scalar columns are native SQL types.
pub const SCHEMA_SQL: &str = r#"
-- ─── Project metadata ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS project (
    key      TEXT PRIMARY KEY,
    value    TEXT NOT NULL
);

-- ─── General settings ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS general (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    config_json TEXT NOT NULL  -- serialized GeneralConfig
);

-- ─── Physics models ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS models (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    config_json TEXT NOT NULL  -- serialized ModelsConfig
);

-- ─── Materials ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS materials (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    phase       TEXT NOT NULL,
    config_json TEXT NOT NULL  -- serialized Material
);

-- ─── Regions ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS regions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    region_type TEXT NOT NULL DEFAULT 'Fluid',
    material_id INTEGER REFERENCES materials(id),
    config_json TEXT NOT NULL  -- serialized Region
);

-- ─── Boundary conditions ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS boundary_conditions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    region_id   INTEGER NOT NULL REFERENCES regions(id),
    bc_type     TEXT NOT NULL,
    config_json TEXT NOT NULL  -- serialized BoundaryCondition
);
CREATE INDEX IF NOT EXISTS idx_bc_region ON boundary_conditions(region_id);

-- ─── Cell zones ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cell_zones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    region_id   INTEGER NOT NULL REFERENCES regions(id),
    zone_type   TEXT NOT NULL DEFAULT 'None',
    config_json TEXT NOT NULL  -- serialized CellZoneConfig
);
CREATE INDEX IF NOT EXISTS idx_cz_region ON cell_zones(region_id);

-- ─── Monitors ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS monitors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    monitor_type TEXT NOT NULL, -- 'force','point','surface','volume'
    config_json TEXT NOT NULL
);

-- ─── Numerical conditions ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS numerical (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    config_json TEXT NOT NULL  -- serialized NumericalConfig
);

-- ─── Run conditions ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS run_conditions (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    config_json TEXT NOT NULL  -- serialized RunConditions
);

-- ─── Initialization ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS initialization (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    config_json TEXT NOT NULL  -- serialized RegionInitialization
);

-- ─── Batch parameters ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS batch (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    config_json TEXT NOT NULL  -- serialized BatchRunConfig
);

-- ─── Meshing (baramMesh) ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS meshing (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    config_json TEXT NOT NULL  -- serialized MeshingConfig
);

-- ─── Solver residual history ──────────────────────────────────
CREATE TABLE IF NOT EXISTS residuals (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    iteration INTEGER NOT NULL,
    field     TEXT    NOT NULL,
    value     REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_residual_iter ON residuals(iteration);
"#;
