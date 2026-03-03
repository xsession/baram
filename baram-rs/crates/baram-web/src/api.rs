use serde::{de::DeserializeOwned, Serialize};
use gloo_net::http::Request;

// ════════════════════════════════════════════════════════════════
//  API client — talks to baram-server REST endpoints
// ════════════════════════════════════════════════════════════════

const BASE_URL: &str = "http://localhost:8730/api";

pub async fn get_json<T: DeserializeOwned>(path: &str) -> Result<T, String> {
    let url = format!("{BASE_URL}{path}");
    let resp = Request::get(&url)
        .send()
        .await
        .map_err(|e| format!("GET {url} failed: {e}"))?;
    if !resp.ok() {
        return Err(format!("GET {url} returned {}", resp.status()));
    }
    resp.json::<T>()
        .await
        .map_err(|e| format!("JSON parse error: {e}"))
}

pub async fn put_json<T: Serialize>(path: &str, body: &T) -> Result<(), String> {
    let url = format!("{BASE_URL}{path}");
    let json = serde_json::to_string(body).map_err(|e| e.to_string())?;
    let resp = Request::put(&url)
        .header("Content-Type", "application/json")
        .body(json)
        .map_err(|e| format!("Failed to build request: {e}"))?
        .send()
        .await
        .map_err(|e| format!("PUT {url} failed: {e}"))?;
    if !resp.ok() {
        return Err(format!("PUT {url} returned {}", resp.status()));
    }
    Ok(())
}

pub async fn post_json<T: Serialize, R: DeserializeOwned>(
    path: &str,
    body: &T,
) -> Result<R, String> {
    let url = format!("{BASE_URL}{path}");
    let json = serde_json::to_string(body).map_err(|e| e.to_string())?;
    let resp = Request::post(&url)
        .header("Content-Type", "application/json")
        .body(json)
        .map_err(|e| format!("Failed to build request: {e}"))?
        .send()
        .await
        .map_err(|e| format!("POST {url} failed: {e}"))?;
    if !resp.ok() {
        return Err(format!("POST {url} returned {}", resp.status()));
    }
    resp.json::<R>()
        .await
        .map_err(|e| format!("JSON parse error: {e}"))
}

pub async fn post_empty(path: &str) -> Result<(), String> {
    let url = format!("{BASE_URL}{path}");
    let resp = Request::post(&url)
        .send()
        .await
        .map_err(|e| format!("POST {url} failed: {e}"))?;
    if !resp.ok() {
        return Err(format!("POST {url} returned {}", resp.status()));
    }
    Ok(())
}
