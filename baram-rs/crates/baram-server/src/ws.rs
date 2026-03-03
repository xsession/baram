use axum::{
    Router,
    extract::{
        Path, State,
        ws::{Message, WebSocket, WebSocketUpgrade},
    },
    response::IntoResponse,
    routing::get,
};
use crate::state::AppState;

// ════════════════════════════════════════════════════════════════
//  WebSocket routes — real-time event streaming per project
// ════════════════════════════════════════════════════════════════

pub fn routes() -> Router<AppState> {
    Router::new().route("/events/:project_id", get(ws_handler))
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    Path(project_id): Path<String>,
    State(state): State<AppState>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, project_id, state))
}

async fn handle_socket(mut socket: WebSocket, project_id: String, state: AppState) {
    // Subscribe to broadcast channel for this project
    let rx = if let Some(tx) = state.inner.event_senders.get(&project_id) {
        tx.subscribe()
    } else {
        let _ = socket
            .send(Message::Text(
                r#"{"error":"Project not found"}"#.into(),
            ))
            .await;
        return;
    };

    let mut rx = rx;

    loop {
        tokio::select! {
            // Broadcast server events to the client
            Ok(msg) = rx.recv() => {
                if socket.send(Message::Text(msg.into())).await.is_err() {
                    break; // Client disconnected
                }
            }
            // Process incoming messages from the client (e.g., ping)
            Some(Ok(msg)) = socket.recv() => {
                match msg {
                    Message::Close(_) => break,
                    Message::Ping(data) => {
                        if socket.send(Message::Pong(data)).await.is_err() {
                            break;
                        }
                    }
                    _ => {} // Ignore other inbound messages for now
                }
            }
            else => break,
        }
    }

    tracing::debug!("WebSocket closed for project {project_id}");
}
