use std::path::{Path, PathBuf};
use std::process::Stdio;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};
use tokio::sync::mpsc;
use baram_core::error::{BaramError, Result};
use baram_core::types::solver::{ResidualPoint, SolverStatus};

// ════════════════════════════════════════════════════════════════
//  Solver Runner — spawns OpenFOAM solver as a child process
//  and streams residual data via channel
// ════════════════════════════════════════════════════════════════

pub struct SolverRunner {
    solver_exe: String,
    case_dir: PathBuf,
    num_procs: u32,
    child: Option<Child>,
}

impl SolverRunner {
    pub fn new(solver_exe: &str, case_dir: &Path, num_procs: u32) -> Self {
        Self {
            solver_exe: solver_exe.to_string(),
            case_dir: case_dir.to_path_buf(),
            num_procs,
            child: None,
        }
    }

    /// Start the solver and return a channel that receives residual data.
    pub async fn start(&mut self) -> Result<mpsc::Receiver<SolverEvent>> {
        let (tx, rx) = mpsc::channel(1024);

        let mut cmd = if self.num_procs > 1 {
            let mut c = Command::new("mpirun");
            c.args(["-np", &self.num_procs.to_string()])
                .arg(&self.solver_exe)
                .arg("-parallel")
                .arg("-case")
                .arg(&self.case_dir);
            c
        } else {
            let mut c = Command::new(&self.solver_exe);
            c.arg("-case").arg(&self.case_dir);
            c
        };

        cmd.stdout(Stdio::piped()).stderr(Stdio::piped());

        let mut child = cmd.spawn().map_err(|e| {
            BaramError::SolverNotFound(format!("{}: {}", self.solver_exe, e))
        })?;

        let stdout = child.stdout.take().unwrap();
        let tx_clone = tx.clone();

        // Spawn a task to parse solver output
        tokio::spawn(async move {
            let reader = BufReader::new(stdout);
            let mut lines = reader.lines();
            let mut iteration: u64 = 0;

            while let Ok(Some(line)) = lines.next_line().await {
                // Parse residual lines from OpenFOAM output
                // Typical format: "smoothSolver:  Solving for Ux, ..."
                // or "GAMG:  Solving for p, Initial residual = 0.123, Final residual = 0.001, ..."
                if let Some(point) = parse_residual_line(&line, &mut iteration) {
                    let _ = tx_clone.send(SolverEvent::Residual(point)).await;
                }
                let _ = tx_clone.send(SolverEvent::LogLine(line)).await;
            }
            let _ = tx_clone.send(SolverEvent::StatusChange(SolverStatus::Ended)).await;
        });

        self.child = Some(child);
        let _ = tx.send(SolverEvent::StatusChange(SolverStatus::Running)).await;
        Ok(rx)
    }

    /// Stop the solver.
    pub async fn stop(&mut self) -> Result<()> {
        if let Some(ref mut child) = self.child {
            child.kill().await.map_err(|e| {
                BaramError::SolverFailed(format!("Failed to kill solver: {}", e))
            })?;
        }
        self.child = None;
        Ok(())
    }

    pub fn is_running(&self) -> bool {
        self.child.is_some()
    }
}

#[derive(Debug, Clone)]
pub enum SolverEvent {
    StatusChange(SolverStatus),
    Residual(ResidualPoint),
    LogLine(String),
}

/// Parse a residual from OpenFOAM solver output.
fn parse_residual_line(line: &str, iteration: &mut u64) -> Option<ResidualPoint> {
    // Detect iteration number from "Time = X"
    if line.starts_with("Time = ") {
        if let Ok(t) = line[7..].trim().parse::<u64>() {
            *iteration = t;
        }
    }

    // Parse "Solving for <field>, Initial residual = <val>, ..."
    if line.contains("Solving for") && line.contains("Initial residual") {
        let field = line
            .split("Solving for ")
            .nth(1)?
            .split(',')
            .next()?
            .trim()
            .to_string();
        let value_str = line
            .split("Initial residual = ")
            .nth(1)?
            .split(',')
            .next()?
            .trim();
        let value: f64 = value_str.parse().ok()?;
        return Some(ResidualPoint {
            iteration: *iteration,
            field,
            value,
        });
    }
    None
}
