mod state;
mod api;
mod ws;
mod solvers;

use std::net::SocketAddr;
use axum::Router;
use tower_http::cors::CorsLayer;
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() {
    // Initialise structured logging
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive("baram=debug".parse().unwrap()))
        .init();

    let app_state = state::AppState::new();

    let app = Router::new()
        .nest("/api", api::routes())
        .nest("/ws", ws::routes())
        .layer(CorsLayer::permissive())
        .with_state(app_state);

    let addr = SocketAddr::from(([0, 0, 0, 0], 8730));
    tracing::info!("BARAM server listening on {addr}");

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
