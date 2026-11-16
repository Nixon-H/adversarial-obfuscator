//! Remote-function service (Tier 4 #8, Level-5 split execution).
//!
//! The client artefact carries a stub for every `@remote` function; the
//! implementation lives here and never ships.  This module is the server
//! half: a minimal HTTP/1.1 endpoint that verifies an HMAC-signed request
//! and dispatches it to a registered handler.
//!
//! Deliberately stdlib-only (`TcpListener` + `serde_json`, both already
//! dependencies) so adding this does not change the crate's dependency
//! graph or its `panic = "abort"` / `lto` release profile.
//!
//! Security properties, each mirrored by a test:
//!
//! * **HMAC over the canonical request** -- function name, canonical args,
//!   nonce and timestamp.  A tampered argument invalidates the signature.
//! * **Freshness** -- a request older than `MAX_SKEW_SECS` is rejected.
//! * **Replay rejection** -- a nonce is accepted once and remembered for
//!   twice the skew window.
//! * **HTTPS or loopback only** -- the server refuses to bind a
//!   non-loopback address without `--allow-remote`, because plain HTTP over
//!   a network would expose the arguments.
//! * **Fail closed** -- every error path returns a JSON error; the handler
//!   is never called with an unverified request.

use std::collections::HashMap;
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{IpAddr, SocketAddr, TcpListener, TcpStream};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};

/// Requests older than this are rejected (seconds).
pub const MAX_SKEW_SECS: f64 = 300.0;

/// A registered implementation.
pub type Handler = Arc<dyn Fn(&[serde_json::Value]) -> Result<serde_json::Value, String>
    + Send
    + Sync>;

/// One request as it arrives on the wire.
#[derive(Debug, Deserialize)]
pub struct RemoteRequest {
    pub function: String,
    #[serde(default)]
    pub args: Vec<serde_json::Value>,
    pub nonce: String,
    pub timestamp: f64,
    pub signature: String,
}

/// One response.
#[derive(Debug, Serialize)]
pub struct RemoteResponse {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

impl RemoteResponse {
    pub fn ok(value: serde_json::Value) -> Self {
        Self { result: Some(value), error: None }
    }

    pub fn err(message: impl Into<String>) -> Self {
        Self { result: None, error: Some(message.into()) }
    }
}

/// Canonical JSON: sorted keys, no whitespace.  Must match the Python side
/// (`obfuscator.remote_exec._canonical`) byte for byte.
fn canonical(value: &serde_json::Value) -> String {
    match value {
        serde_json::Value::Object(map) => {
            let mut keys: Vec<&String> = map.keys().collect();
            keys.sort();
            let parts: Vec<String> = keys
                .into_iter()
                .map(|k| {
                    format!(
                        "{}:{}",
                        serde_json::to_string(k).unwrap_or_default(),
                        canonical(&map[k])
                    )
                })
                .collect();
            format!("{{{}}}", parts.join(","))
        }
        serde_json::Value::Array(items) => {
            let parts: Vec<String> = items.iter().map(canonical).collect();
            format!("[{}]", parts.join(","))
        }
        other => serde_json::to_string(other).unwrap_or_default(),
    }
}

/// HMAC-SHA256 over the canonical request.
///
/// Implemented here rather than pulling in a crate: the crate's dependency
/// graph is frozen by the release profile, and this is a small, well-defined
/// construction (RFC 2104) over SHA-256 (FIPS 180-4).
pub fn sign_request(
    secret: &[u8],
    function: &str,
    args: &[serde_json::Value],
    nonce: &str,
    timestamp: f64,
) -> String {
    let material = format!(
        "{}\n{}\n{}\n{}",
        function,
        canonical(&serde_json::Value::Array(args.to_vec())),
        nonce,
        format_f64(timestamp)
    );
    hex(&hmac_sha256(secret, material.as_bytes()))
}

/// Format a float the way Python's `repr(float)` does for our values.
fn format_f64(value: f64) -> String {
    if value.fract() == 0.0 && value.abs() < 1e16 {
        format!("{:.1}", value)
    } else {
        format!("{}", value)
    }
}

fn hex(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        out.push_str(&format!("{:02x}", b));
    }
    out
}

// ── SHA-256 (FIPS 180-4) ────────────────────────────────────────────────

const K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
    0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
    0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
    0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
    0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
    0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
    0xc67178f2,
];

pub fn sha256(data: &[u8]) -> [u8; 32] {
    let mut h: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab,
        0x5be0cd19,
    ];
    let mut message = data.to_vec();
    let bit_len = (data.len() as u64) * 8;
    message.push(0x80);
    while message.len() % 64 != 56 {
        message.push(0);
    }
    message.extend_from_slice(&bit_len.to_be_bytes());

    for chunk in message.chunks(64) {
        let mut w = [0u32; 64];
        for (i, word) in chunk.chunks(4).enumerate() {
            w[i] = u32::from_be_bytes([word[0], word[1], word[2], word[3]]);
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }
        let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut hh) =
            (h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7]);
        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let t1 = hh
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(K[i])
                .wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let t2 = s0.wrapping_add(maj);
            hh = g;
            g = f;
            f = e;
            e = d.wrapping_add(t1);
            d = c;
            c = b;
            b = a;
            a = t1.wrapping_add(t2);
        }
        h[0] = h[0].wrapping_add(a);
        h[1] = h[1].wrapping_add(b);
        h[2] = h[2].wrapping_add(c);
        h[3] = h[3].wrapping_add(d);
        h[4] = h[4].wrapping_add(e);
        h[5] = h[5].wrapping_add(f);
        h[6] = h[6].wrapping_add(g);
        h[7] = h[7].wrapping_add(hh);
    }

    let mut out = [0u8; 32];
    for (i, word) in h.iter().enumerate() {
        out[i * 4..i * 4 + 4].copy_from_slice(&word.to_be_bytes());
    }
    out
}

pub fn hmac_sha256(key: &[u8], message: &[u8]) -> [u8; 32] {
    const BLOCK: usize = 64;
    let mut k = [0u8; BLOCK];
    if key.len() > BLOCK {
        k[..32].copy_from_slice(&sha256(key));
    } else {
        k[..key.len()].copy_from_slice(key);
    }
    let mut inner = Vec::with_capacity(BLOCK + message.len());
    let mut outer = Vec::with_capacity(BLOCK + 32);
    for b in k.iter() {
        inner.push(b ^ 0x36);
        outer.push(b ^ 0x5c);
    }
    inner.extend_from_slice(message);
    let inner_hash = sha256(&inner);
    outer.extend_from_slice(&inner_hash);
    sha256(&outer)
}

// ── verification ────────────────────────────────────────────────────────

/// Constant-time comparison.
fn ct_eq(a: &str, b: &str) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let mut diff = 0u8;
    for (x, y) in a.bytes().zip(b.bytes()) {
        diff |= x ^ y;
    }
    diff == 0
}

fn now_secs() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

/// The service: a secret, a handler table, and the seen-nonce set.
pub struct RemoteService {
    secret: Vec<u8>,
    handlers: HashMap<String, Handler>,
    seen: Mutex<HashMap<String, f64>>,
}

impl RemoteService {
    pub fn new(secret: Vec<u8>) -> Self {
        Self { secret, handlers: HashMap::new(), seen: Mutex::new(HashMap::new()) }
    }

    /// How many implementations this service holds.
    pub fn handler_count(&self) -> usize {
        self.handlers.len()
    }

    pub fn register<F>(&mut self, name: &str, handler: F)
    where
        F: Fn(&[serde_json::Value]) -> Result<serde_json::Value, String>
            + Send
            + Sync
            + 'static,
    {
        self.handlers.insert(name.to_string(), Arc::new(handler));
    }

    /// Verify and dispatch one request.  Never panics; every failure is an
    /// error response.
    pub fn handle(&self, request: &RemoteRequest, now: f64) -> RemoteResponse {
        if (now - request.timestamp).abs() > MAX_SKEW_SECS {
            return RemoteResponse::err("remote request expired");
        }
        let expected = sign_request(
            &self.secret,
            &request.function,
            &request.args,
            &request.nonce,
            request.timestamp,
        );
        if !ct_eq(&expected, &request.signature) {
            return RemoteResponse::err("remote request signature mismatch");
        }
        {
            let mut seen = match self.seen.lock() {
                Ok(guard) => guard,
                Err(_) => return RemoteResponse::err("service unavailable"),
            };
            // Prune, then reject a reuse.
            let cutoff = now - MAX_SKEW_SECS * 2.0;
            seen.retain(|_, stamp| *stamp >= cutoff);
            if seen.contains_key(&request.nonce) {
                return RemoteResponse::err("remote request replayed");
            }
            seen.insert(request.nonce.clone(), now);
        }
        match self.handlers.get(&request.function) {
            Some(handler) => match handler(&request.args) {
                Ok(value) => RemoteResponse::ok(value),
                Err(message) => RemoteResponse::err(message),
            },
            None => RemoteResponse::err(format!(
                "unknown remote function '{}'",
                request.function
            )),
        }
    }

    /// Handle a raw JSON body (what the HTTP layer calls).
    pub fn handle_body(&self, body: &[u8], now: f64) -> RemoteResponse {
        match serde_json::from_slice::<RemoteRequest>(body) {
            Ok(request) => self.handle(&request, now),
            Err(err) => RemoteResponse::err(format!("bad request: {}", err)),
        }
    }
}

/// Read the shared secret from the environment.  Never from a file in the
/// repo and never from argv: the same rule the Python side follows.
pub fn secret_from_env() -> Result<Vec<u8>, String> {
    let raw = std::env::var("NIXON_REMOTE_SECRET")
        .map_err(|_| "NIXON_REMOTE_SECRET is not set".to_string())?;
    let raw = raw.trim();
    if raw.len() != 64 {
        return Err("NIXON_REMOTE_SECRET must be 64 hex characters".to_string());
    }
    let mut out = Vec::with_capacity(32);
    for i in (0..raw.len()).step_by(2) {
        let byte = u8::from_str_radix(&raw[i..i + 2], 16)
            .map_err(|_| "NIXON_REMOTE_SECRET must be hex".to_string())?;
        out.push(byte);
    }
    Ok(out)
}

/// Serve one HTTP/1.1 request from `stream` and write the response.
pub fn serve_one(service: &RemoteService, mut stream: TcpStream) -> std::io::Result<()> {
    let mut reader = BufReader::new(stream.try_clone()?);
    let mut request_line = String::new();
    reader.read_line(&mut request_line)?;
    let mut content_length = 0usize;
    loop {
        let mut header = String::new();
        if reader.read_line(&mut header)? == 0 {
            break;
        }
        let trimmed = header.trim_end();
        if trimmed.is_empty() {
            break;
        }
        if let Some(value) = trimmed
            .to_ascii_lowercase()
            .strip_prefix("content-length:")
            .map(|v| v.trim().to_string())
        {
            content_length = value.parse().unwrap_or(0);
        }
    }
    if !request_line.starts_with("POST ") {
        let body = b"{\"error\":\"method not allowed\"}";
        write_response(&mut stream, 405, body)?;
        return Ok(());
    }
    let mut body = vec![0u8; content_length.min(1 << 20)];
    reader.read_exact(&mut body)?;
    let response = service.handle_body(&body, now_secs());
    let payload = serde_json::to_vec(&response).unwrap_or_else(|_| b"{}".to_vec());
    write_response(&mut stream, 200, &payload)
}

fn write_response(stream: &mut TcpStream, status: u16, body: &[u8]) -> std::io::Result<()> {
    let reason = if status == 200 { "OK" } else { "Method Not Allowed" };
    let head = format!(
        "HTTP/1.1 {} {}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
        status,
        reason,
        body.len()
    );
    stream.write_all(head.as_bytes())?;
    stream.write_all(body)?;
    stream.flush()
}

/// Bind and serve until the process is stopped.
///
/// Refuses a non-loopback address unless `allow_remote` is set: the endpoint
/// speaks plain HTTP, so exposing it on a network would leak the arguments.
pub fn serve(
    service: Arc<RemoteService>,
    addr: &str,
    allow_remote: bool,
) -> Result<(), String> {
    let socket: SocketAddr = addr
        .parse()
        .map_err(|_| format!("invalid bind address '{}'", addr))?;
    let loopback = matches!(socket.ip(), IpAddr::V4(ip) if ip.is_loopback())
        || matches!(socket.ip(), IpAddr::V6(ip) if ip.is_loopback());
    if !loopback && !allow_remote {
        return Err(
            "refusing to bind a non-loopback address without --allow-remote \
             (the endpoint speaks plain HTTP)"
                .to_string(),
        );
    }
    let listener = TcpListener::bind(socket).map_err(|e| format!("bind failed: {}", e))?;
    for incoming in listener.incoming() {
        match incoming {
            Ok(stream) => {
                let svc = Arc::clone(&service);
                std::thread::spawn(move || {
                    let _ = serve_one(&svc, stream);
                });
            }
            Err(_) => continue,
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn service() -> RemoteService {
        let mut svc = RemoteService::new(b"secret-key".to_vec());
        svc.register("add", |args| {
            let a = args.first().and_then(|v| v.as_i64()).unwrap_or(0);
            let b = args.get(1).and_then(|v| v.as_i64()).unwrap_or(0);
            Ok(json!(a + b))
        });
        svc
    }

    fn signed(svc: &RemoteService, function: &str, args: Vec<serde_json::Value>,
              nonce: &str, ts: f64) -> RemoteRequest {
        RemoteRequest {
            function: function.to_string(),
            args: args.clone(),
            nonce: nonce.to_string(),
            timestamp: ts,
            signature: sign_request(&svc.secret, function, &args, nonce, ts),
        }
    }

    #[test]
    fn sha256_matches_known_vector() {
        // FIPS 180-4 test vector for "abc".
        assert_eq!(
            hex(&sha256(b"abc")),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[test]
    fn hmac_matches_rfc4231_case_2() {
        // RFC 4231 test case 2: key "Jefe", data "what do ya want for nothing?"
        assert_eq!(
            hex(&hmac_sha256(b"Jefe", b"what do ya want for nothing?")),
            "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"
        );
    }

    #[test]
    fn valid_request_is_dispatched() {
        let svc = service();
        let req = signed(&svc, "add", vec![json!(2), json!(3)], "n1", 1000.0);
        let response = svc.handle(&req, 1000.0);
        assert_eq!(response.result, Some(json!(5)));
        assert!(response.error.is_none());
    }

    #[test]
    fn tampered_args_are_rejected() {
        let svc = service();
        let mut req = signed(&svc, "add", vec![json!(2), json!(3)], "n2", 1000.0);
        req.args = vec![json!(9), json!(9)];
        let response = svc.handle(&req, 1000.0);
        assert!(response.result.is_none());
        assert!(response.error.unwrap().contains("signature"));
    }

    #[test]
    fn stale_request_is_rejected() {
        let svc = service();
        let req = signed(&svc, "add", vec![json!(1)], "n3", 1000.0);
        let response = svc.handle(&req, 1000.0 + MAX_SKEW_SECS + 1.0);
        assert!(response.error.unwrap().contains("expired"));
    }

    #[test]
    fn replay_is_rejected() {
        let svc = service();
        let req = signed(&svc, "add", vec![json!(1)], "n4", 1000.0);
        assert!(svc.handle(&req, 1000.0).result.is_some());
        let second = svc.handle(&req, 1000.0);
        assert!(second.error.unwrap().contains("replayed"));
    }

    #[test]
    fn unknown_function_is_rejected() {
        let svc = service();
        let req = signed(&svc, "nope", vec![], "n5", 1000.0);
        let response = svc.handle(&req, 1000.0);
        assert!(response.error.unwrap().contains("unknown remote function"));
    }

    #[test]
    fn handler_error_is_reported() {
        let mut svc = RemoteService::new(b"k".to_vec());
        svc.register("boom", |_args| Err("handler failed".to_string()));
        let req = signed(&svc, "boom", vec![], "n6", 1000.0);
        let response = svc.handle(&req, 1000.0);
        assert!(response.error.unwrap().contains("handler failed"));
    }

    #[test]
    fn bad_json_is_an_error_not_a_panic() {
        let svc = service();
        let response = svc.handle_body(b"not json", 1000.0);
        assert!(response.error.unwrap().contains("bad request"));
    }

    #[test]
    fn non_loopback_bind_is_refused_without_opt_in() {
        let svc = Arc::new(service());
        let err = serve(svc, "0.0.0.0:0", false).unwrap_err();
        assert!(err.contains("non-loopback"));
    }

    #[test]
    fn canonical_form_is_stable() {
        let a = json!({"b": 1, "a": [2, 3]});
        let b = json!({"a": [2, 3], "b": 1});
        assert_eq!(canonical(&a), canonical(&b));
    }
}
