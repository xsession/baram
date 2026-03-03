use serde::{Deserialize, Serialize};

// ════════════════════════════════════════════════════════════════
//  Run / calculation conditions — port of run_calculation_db.py
// ════════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum TimeSteppingMethod {
    #[default]
    Fixed,
    Adaptive,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum DataWriteFormat {
    #[default]
    Binary,
    Ascii,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum DataWritePrecision {
    #[default]
    Float32,
    Float64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimeStepping {
    pub method: TimeSteppingMethod,
    pub time_step_size: f64,
    pub max_courant_number: f64,
    pub max_courant_number_vof: f64,
}

impl Default for TimeStepping {
    fn default() -> Self {
        Self {
            method: TimeSteppingMethod::Fixed,
            time_step_size: 0.001,
            max_courant_number: 1.0,
            max_courant_number_vof: 1.0,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunConditions {
    pub number_of_iterations: u64,       // steady
    pub end_time: f64,                    // transient
    pub report_interval_steps: u32,
    pub report_interval_seconds: f64,
    pub retain_only_last_n: Option<u32>,
    pub time_stepping: TimeStepping,
    pub data_write_format: DataWriteFormat,
    pub data_write_precision: DataWritePrecision,
}

impl Default for RunConditions {
    fn default() -> Self {
        Self {
            number_of_iterations: 1000,
            end_time: 1.0,
            report_interval_steps: 100,
            report_interval_seconds: 0.0,
            retain_only_last_n: None,
            time_stepping: TimeStepping::default(),
            data_write_format: DataWriteFormat::Binary,
            data_write_precision: DataWritePrecision::Float32,
        }
    }
}

// ─── Batch run ────────────────────────────────────────────────
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BatchCase {
    pub id: i64,
    pub name: String,
    pub global_parameters: Vec<(String, f64)>,
    pub enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct BatchRunConfig {
    pub cases: Vec<BatchCase>,
    pub current_case: Option<i64>,
}
