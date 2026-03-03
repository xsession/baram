use axum::{
    Router,
    extract::{Path, State},
    http::StatusCode,
    Json,
    routing::{get, post, put},
};
use serde::{Deserialize, Serialize};
use crate::state::AppState;

// ════════════════════════════════════════════════════════════════
//  REST API routes for BARAM
// ════════════════════════════════════════════════════════════════

pub fn routes() -> Router<AppState> {
    Router::new()
        // Project
        .route("/project/create", post(create_project))
        .route("/project/open", post(open_project))
        .route("/project/:id/close", post(close_project))
        // General
        .route("/project/:id/general", get(get_general).put(put_general))
        // Models
        .route("/project/:id/models", get(get_models).put(put_models))
        // Boundary Conditions
        .route("/project/:id/regions/:rid/bcs", get(list_bcs).post(create_bc))
        .route("/project/:id/regions/:rid/bcs/:bcid", put(update_bc).delete(delete_bc))
        // Numerical
        .route("/project/:id/numerical", get(get_numerical).put(put_numerical))
        // Run
        .route("/project/:id/run", get(get_run_conditions).put(put_run_conditions))
        // Solver backends
        .route("/project/:id/solver-backends", get(get_solver_backends).put(put_solver_backends))
        // Solver
        .route("/project/:id/solver/start", post(start_solver))
        .route("/project/:id/solver/stop", post(stop_solver))
        // Case generation
        .route("/project/:id/case/generate", post(generate_case))
        // Residuals
        .route("/project/:id/residuals/:field", get(get_residuals))
        // Mesh import
        .route("/project/:id/mesh/import-stl", post(import_stl))
}

// ─── Request / Response types ─────────────────────────────────

#[derive(Deserialize)]
struct ProjectRequest {
    path: String,
    id: Option<String>,
}

#[derive(Serialize)]
struct ProjectResponse {
    id: String,
    message: String,
}

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
}

fn internal_error(msg: impl ToString) -> (StatusCode, Json<ErrorResponse>) {
    (
        StatusCode::INTERNAL_SERVER_ERROR,
        Json(ErrorResponse { error: msg.to_string() }),
    )
}

#[derive(Serialize)]
struct SolverStartResponse {
    backend: String,
    message: String,
}

// ─── Project endpoints ────────────────────────────────────────

async fn create_project(
    State(state): State<AppState>,
    Json(req): Json<ProjectRequest>,
) -> Result<Json<ProjectResponse>, (StatusCode, Json<ErrorResponse>)> {
    let id = req.id.unwrap_or_else(|| uuid::Uuid::new_v4().to_string());
    state
        .open_project(&id, std::path::PathBuf::from(&req.path))
        .await
        .map_err(|e| internal_error(e))?;
    Ok(Json(ProjectResponse {
        id,
        message: "Project created".into(),
    }))
}

async fn open_project(
    State(state): State<AppState>,
    Json(req): Json<ProjectRequest>,
) -> Result<Json<ProjectResponse>, (StatusCode, Json<ErrorResponse>)> {
    let id = req.id.unwrap_or_else(|| uuid::Uuid::new_v4().to_string());
    state
        .open_project(&id, std::path::PathBuf::from(&req.path))
        .await
        .map_err(|e| internal_error(e))?;
    Ok(Json(ProjectResponse {
        id,
        message: "Project opened".into(),
    }))
}

async fn close_project(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> StatusCode {
    state.inner.projects.remove(&id);
    state.inner.event_senders.remove(&id);
    StatusCode::OK
}

// ─── General ──────────────────────────────────────────────────

async fn get_general(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<baram_core::types::general::GeneralConfig>, (StatusCode, Json<ErrorResponse>)> {
    let projects = &state.inner.projects;
    let project = projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    let cfg = proj.db().load_general().map_err(|e| internal_error(e))?;
    Ok(Json(cfg))
}

async fn put_general(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(cfg): Json<baram_core::types::general::GeneralConfig>,
) -> Result<StatusCode, (StatusCode, Json<ErrorResponse>)> {
    let projects = &state.inner.projects;
    let project = projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    proj.db().save_general(&cfg).map_err(|e| internal_error(e))?;
    state.broadcast(&id, r#"{"type":"general_updated"}"#);
    Ok(StatusCode::OK)
}

// ─── Models ───────────────────────────────────────────────────

async fn get_models(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<baram_core::types::models::ModelsConfig>, (StatusCode, Json<ErrorResponse>)> {
    let project = state.inner.projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    let cfg = proj.db().load_models().map_err(|e| internal_error(e))?;
    Ok(Json(cfg))
}

async fn put_models(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(cfg): Json<baram_core::types::models::ModelsConfig>,
) -> Result<StatusCode, (StatusCode, Json<ErrorResponse>)> {
    let project = state.inner.projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    proj.db().save_models(&cfg).map_err(|e| internal_error(e))?;
    state.broadcast(&id, r#"{"type":"models_updated"}"#);
    Ok(StatusCode::OK)
}

// ─── Boundary Conditions ──────────────────────────────────────

async fn list_bcs(
    State(state): State<AppState>,
    Path((id, rid)): Path<(String, i64)>,
) -> Result<Json<Vec<(i64, baram_core::types::boundary::BoundaryCondition)>>, (StatusCode, Json<ErrorResponse>)> {
    let project = state.inner.projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    let bcs = proj.db().list_bcs(rid).map_err(|e| internal_error(e))?;
    Ok(Json(bcs))
}

async fn create_bc(
    State(state): State<AppState>,
    Path((id, rid)): Path<(String, i64)>,
    Json(bc): Json<baram_core::types::boundary::BoundaryCondition>,
) -> Result<Json<i64>, (StatusCode, Json<ErrorResponse>)> {
    let project = state.inner.projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    let bc_id = proj.db().insert_bc(rid, &bc).map_err(|e| internal_error(e))?;
    state.broadcast(&id, r#"{"type":"bc_created"}"#);
    Ok(Json(bc_id))
}

async fn update_bc(
    State(state): State<AppState>,
    Path((id, _rid, bcid)): Path<(String, i64, i64)>,
    Json(bc): Json<baram_core::types::boundary::BoundaryCondition>,
) -> Result<StatusCode, (StatusCode, Json<ErrorResponse>)> {
    let project = state.inner.projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    proj.db().update_bc(bcid, &bc).map_err(|e| internal_error(e))?;
    state.broadcast(&id, r#"{"type":"bc_updated"}"#);
    Ok(StatusCode::OK)
}

async fn delete_bc(
    State(state): State<AppState>,
    Path((id, _rid, bcid)): Path<(String, i64, i64)>,
) -> Result<StatusCode, (StatusCode, Json<ErrorResponse>)> {
    let project = state.inner.projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    proj.db().delete_bc(bcid).map_err(|e| internal_error(e))?;
    state.broadcast(&id, r#"{"type":"bc_deleted"}"#);
    Ok(StatusCode::OK)
}

// ─── Numerical ────────────────────────────────────────────────

async fn get_numerical(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<baram_core::types::numerical::NumericalConfig>, (StatusCode, Json<ErrorResponse>)> {
    let project = state.inner.projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    let cfg = proj.db().load_numerical().map_err(|e| internal_error(e))?;
    Ok(Json(cfg))
}

async fn put_numerical(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(cfg): Json<baram_core::types::numerical::NumericalConfig>,
) -> Result<StatusCode, (StatusCode, Json<ErrorResponse>)> {
    let project = state.inner.projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    proj.db().save_numerical(&cfg).map_err(|e| internal_error(e))?;
    state.broadcast(&id, r#"{"type":"numerical_updated"}"#);
    Ok(StatusCode::OK)
}

// ─── Run Conditions ───────────────────────────────────────────

async fn get_run_conditions(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<baram_core::types::run::RunConditions>, (StatusCode, Json<ErrorResponse>)> {
    let project = state.inner.projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    let cfg = proj.db().load_run_conditions().map_err(|e| internal_error(e))?;
    Ok(Json(cfg))
}

async fn put_run_conditions(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(cfg): Json<baram_core::types::run::RunConditions>,
) -> Result<StatusCode, (StatusCode, Json<ErrorResponse>)> {
    let project = state.inner.projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    proj.db().save_run_conditions(&cfg).map_err(|e| internal_error(e))?;
    state.broadcast(&id, r#"{"type":"run_conditions_updated"}"#);
    Ok(StatusCode::OK)
}

// ─── Solver control ───────────────────────────────────────────

// ─── Solver backends CRUD ─────────────────────────────────────

async fn get_solver_backends(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<baram_core::types::solver::SolverBackendsConfig>, (StatusCode, Json<ErrorResponse>)> {
    let project = state.inner.projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    let cfg = proj.db().load_solver_backends().map_err(|e| internal_error(e))?;
    Ok(Json(cfg))
}

async fn put_solver_backends(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(cfg): Json<baram_core::types::solver::SolverBackendsConfig>,
) -> Result<StatusCode, (StatusCode, Json<ErrorResponse>)> {
    let project = state.inner.projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    proj.db().save_solver_backends(&cfg).map_err(|e| internal_error(e))?;
    state.broadcast(&id, r#"{"type":"solver_backends_updated"}"#);
    Ok(StatusCode::OK)
}

async fn start_solver(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Json<SolverStartResponse>, (StatusCode, Json<ErrorResponse>)> {
    let project = state.inner.projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    let case_dir = proj.case_dir();

    // Load solver backend config
    let backends_cfg = proj.db().load_solver_backends().map_err(|e| internal_error(e))?;
    crate::solvers::validate_backend(&backends_cfg).map_err(|e| internal_error(e))?;

    let active = backends_cfg.active;

    // For OpenFOAM, generate case files first
    if active == baram_core::types::solver::SolverBackend::OpenFoam {
        baram_openfoam::case_generator::generate_case(proj.db(), &case_dir)
            .map_err(|e| internal_error(e))?;
    }

    // Dispatch to the correct backend
    let msg = crate::solvers::start_solver(active, &backends_cfg, &case_dir, 1)
        .await
        .map_err(|e| internal_error(e))?;

    state.broadcast(&id, &format!(r#"{{"type":"solver_started","backend":"{:?}"}}"#, active));
    Ok(Json(SolverStartResponse { backend: format!("{:?}", active), message: msg }))
}

async fn stop_solver(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> StatusCode {
    state.broadcast(&id, r#"{"type":"solver_stopped"}"#);
    StatusCode::OK
}

// ─── Case generation ──────────────────────────────────────────

async fn generate_case(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<StatusCode, (StatusCode, Json<ErrorResponse>)> {
    let project = state.inner.projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    baram_openfoam::case_generator::generate_case(proj.db(), &proj.case_dir())
        .map_err(|e| internal_error(e))?;
    state.broadcast(&id, r#"{"type":"case_generated"}"#);
    Ok(StatusCode::OK)
}

// ─── Residuals ────────────────────────────────────────────────

#[derive(Deserialize)]
struct ResidualQuery {
    from_iter: Option<u64>,
}

async fn get_residuals(
    State(state): State<AppState>,
    Path((id, field)): Path<(String, String)>,
    axum::extract::Query(query): axum::extract::Query<ResidualQuery>,
) -> Result<Json<Vec<(u64, f64)>>, (StatusCode, Json<ErrorResponse>)> {
    let project = state.inner.projects.get(&id).ok_or_else(|| internal_error("Project not found"))?;
    let proj = project.lock().await;
    let from = query.from_iter.unwrap_or(0);
    let data = proj.db().get_residuals(&field, from).map_err(|e| internal_error(e))?;
    Ok(Json(data))
}

// ─── Mesh import ──────────────────────────────────────────────

#[derive(Deserialize)]
struct ImportStlRequest {
    file_path: String,
}

#[derive(Serialize)]
struct ImportStlResponse {
    solids: usize,
    total_triangles: usize,
}

async fn import_stl(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(req): Json<ImportStlRequest>,
) -> Result<Json<ImportStlResponse>, (StatusCode, Json<ErrorResponse>)> {
    let path = std::path::PathBuf::from(&req.file_path);
    let solids = baram_mesh::stl::load_stl(&path).map_err(|e| internal_error(e))?;
    let total_triangles: usize = solids.iter().map(|s| s.triangles.len()).sum();
    state.broadcast(&id, r#"{"type":"stl_imported"}"#);
    Ok(Json(ImportStlResponse {
        solids: solids.len(),
        total_triangles,
    }))
}
