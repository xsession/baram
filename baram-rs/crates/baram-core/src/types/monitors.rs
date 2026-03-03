use serde::{Deserialize, Serialize};

// ════════════════════════════════════════════════════════════════
//  Monitors — port of monitors_db.py
// ════════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum MonitorWriteInterval {
    #[default]
    EveryTimeStep,
    SpecifiedWriteInterval,
}

// ─── Force Monitor ────────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum ForceReportType {
    #[default]
    LiftAndDrag,
    ForceAndMoment,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ForceMonitor {
    pub id: i64,
    pub name: String,
    pub enabled: bool,
    pub report_type: ForceReportType,
    pub write_interval: MonitorWriteInterval,
    pub interval: u32,
    pub boundary_ids: Vec<i64>,
    pub lift_direction: [f64; 3],
    pub drag_direction: [f64; 3],
    pub center_of_rotation: [f64; 3],
}

impl Default for ForceMonitor {
    fn default() -> Self {
        Self {
            id: 0,
            name: "Force Monitor".into(),
            enabled: true,
            report_type: ForceReportType::LiftAndDrag,
            write_interval: MonitorWriteInterval::EveryTimeStep,
            interval: 1,
            boundary_ids: Vec::new(),
            lift_direction: [0.0, 0.0, 1.0],
            drag_direction: [1.0, 0.0, 0.0],
            center_of_rotation: [0.0; 3],
        }
    }
}

// ─── Point Monitor ────────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PointMonitor {
    pub id: i64,
    pub name: String,
    pub enabled: bool,
    pub write_interval: MonitorWriteInterval,
    pub interval: u32,
    pub field: String,
    pub coordinate: [f64; 3],
    pub snap_to_boundary: bool,
    pub region_id: i64,
}

impl Default for PointMonitor {
    fn default() -> Self {
        Self {
            id: 0,
            name: "Point Monitor".into(),
            enabled: true,
            write_interval: MonitorWriteInterval::EveryTimeStep,
            interval: 1,
            field: "p".into(),
            coordinate: [0.0; 3],
            snap_to_boundary: false,
            region_id: 0,
        }
    }
}

// ─── Surface Monitor ──────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum SurfaceReportType {
    #[default]
    AreaWeightedAverage,
    MassWeightedAverage,
    Integral,
    MassFlowRate,
    VolumeFlowRate,
    Minimum,
    Maximum,
    CoefficientOfVariation,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SurfaceMonitor {
    pub id: i64,
    pub name: String,
    pub enabled: bool,
    pub report_type: SurfaceReportType,
    pub write_interval: MonitorWriteInterval,
    pub interval: u32,
    pub field: String,
    pub boundary_ids: Vec<i64>,
    pub region_id: i64,
}

impl Default for SurfaceMonitor {
    fn default() -> Self {
        Self {
            id: 0,
            name: "Surface Monitor".into(),
            enabled: true,
            report_type: SurfaceReportType::AreaWeightedAverage,
            write_interval: MonitorWriteInterval::EveryTimeStep,
            interval: 1,
            field: "p".into(),
            boundary_ids: Vec::new(),
            region_id: 0,
        }
    }
}

// ─── Volume Monitor ───────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum VolumeReportType {
    #[default]
    VolumeAverage,
    VolumeIntegral,
    Minimum,
    Maximum,
    CoefficientOfVariation,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VolumeMonitor {
    pub id: i64,
    pub name: String,
    pub enabled: bool,
    pub report_type: VolumeReportType,
    pub write_interval: MonitorWriteInterval,
    pub interval: u32,
    pub field: String,
    pub region_id: i64,
}

impl Default for VolumeMonitor {
    fn default() -> Self {
        Self {
            id: 0,
            name: "Volume Monitor".into(),
            enabled: true,
            report_type: VolumeReportType::VolumeAverage,
            write_interval: MonitorWriteInterval::EveryTimeStep,
            interval: 1,
            field: "p".into(),
            region_id: 0,
        }
    }
}

// ─── Residual Monitor config ──────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResidualMonitor {
    pub absolute_tolerance: f64,
    pub relative_tolerance: f64,
}

impl Default for ResidualMonitor {
    fn default() -> Self {
        Self {
            absolute_tolerance: 1e-6,
            relative_tolerance: 0.0,
        }
    }
}
