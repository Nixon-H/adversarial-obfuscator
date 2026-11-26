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
//! * **HMAC over the canonical request** -- protocol version, function name,
//!   typed canonical args/kwargs, nonce and binary64 timestamp. A tampered
//!   argument or keyword invalidates the signature.
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
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};

/// Requests older than this are rejected (seconds).
pub const MAX_SKEW_SECS: f64 = 300.0;
/// Versioned, language-neutral remote signing protocol.
pub const REMOTE_PROTOCOL_VERSION: u16 = 1;

/// A registered implementation.
pub type Handler =
    Arc<dyn Fn(&[serde_json::Value]) -> Result<serde_json::Value, String> + Send + Sync>;

/// One request as it arrives on the wire.
#[derive(Debug, Deserialize, Serialize)]
pub struct RemoteRequest {
    pub version: u16,
    pub function: String,
    #[serde(default)]
    pub args: Vec<serde_json::Value>,
    #[serde(default)]
    pub kwargs: serde_json::Map<String, serde_json::Value>,
    pub nonce: String,
    pub timestamp: f64,
    pub signature: String,
}

/// One response.
#[derive(Debug, Serialize, Deserialize)]
pub struct RemoteResponse {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

impl RemoteResponse {
    pub fn ok(value: serde_json::Value) -> Self {
        Self {
            result: Some(value),
            error: None,
        }
    }

    pub fn err(message: impl Into<String>) -> Self {
        Self {
            result: None,
            error: Some(message.into()),
        }
    }
}

fn utf8_hex(value: &str) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(value.len() * 2);
    for byte in value.as_bytes() {
        out.push(DIGITS[(byte >> 4) as usize] as char);
        out.push(DIGITS[(byte & 0x0f) as usize] as char);
    }
    out
}

/// Language-neutral v1 canonical form. The typed representation avoids
/// Python/Rust differences in JSON escaping and shortest-float formatting.
fn canonical(value: &serde_json::Value) -> String {
    match value {
        serde_json::Value::Null => "[\"n\"]".to_string(),
        serde_json::Value::Bool(value) => {
            format!("[\"b\",\"{}\"]", if *value { "1" } else { "0" })
        }
        serde_json::Value::Number(number) => {
            if number.is_i64() || number.is_u64() {
                format!("[\"i\",\"{}\"]", number)
            } else {
                let bits = number.as_f64().unwrap_or(0.0).to_bits();
                format!("[\"f\",\"{bits:016x}\"]")
            }
        }
        serde_json::Value::String(value) => {
            format!("[\"s\",\"{}\"]", utf8_hex(value))
        }
        serde_json::Value::Array(items) => {
            let parts: Vec<String> = items.iter().map(canonical).collect();
            format!("[\"a\",[{}]]", parts.join(","))
        }
        serde_json::Value::Object(map) => {
            let mut keys: Vec<&String> = map.keys().collect();
            keys.sort_by(|a, b| a.as_bytes().cmp(b.as_bytes()));
            let parts: Vec<String> = keys
                .into_iter()
                .map(|key| {
                    format!(
                        "[{},{}]",
                        canonical(&serde_json::Value::String(key.clone())),
                        canonical(&map[key])
                    )
                })
                .collect();
            format!("[\"o\",[{}]]", parts.join(","))
        }
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
    kwargs: &serde_json::Map<String, serde_json::Value>,
    nonce: &str,
    timestamp: f64,
) -> String {
    let canonical_timestamp = format!("[\"f\",\"{:016x}\"]", timestamp.to_bits());
    let material = format!(
        "nixon-remote-v1\n{}\n{}\n{}\n{}\n{}",
        canonical(&serde_json::Value::String(function.to_string())),
        canonical(&serde_json::Value::Array(args.to_vec())),
        canonical(&serde_json::Value::Object(kwargs.clone())),
        canonical(&serde_json::Value::String(nonce.to_string())),
        canonical_timestamp,
    );
    hex(&hmac_sha256(secret, material.as_bytes()))
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
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
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
    /// Operator-side Python bundle.  A request for a function the Rust side
    /// does not register is forwarded there: the bundle holds the real
    /// implementations that never ship to the client.
    worker_bundle: Option<String>,
}

impl RemoteService {
    pub fn new(secret: Vec<u8>) -> Self {
        Self {
            secret,
            handlers: HashMap::new(),
            seen: Mutex::new(HashMap::new()),
            worker_bundle: None,
        }
    }

    /// Point the service at an operator bundle (see
    /// `obfuscator.remote_exec.write_remote_bundle`).  Requests for unknown
    /// functions are forwarded to it via a Python subprocess.
    pub fn with_worker_bundle(mut self, path: impl Into<String>) -> Self {
        self.worker_bundle = Some(path.into());
        self
    }

    /// How many implementations this service holds.
    pub fn handler_count(&self) -> usize {
        self.handlers.len()
    }

    pub fn register<F>(&mut self, name: &str, handler: F)
    where
        F: Fn(&[serde_json::Value]) -> Result<serde_json::Value, String> + Send + Sync + 'static,
    {
        self.handlers.insert(name.to_string(), Arc::new(handler));
    }

    /// Verify and dispatch one request.  Never panics; every failure is an
    /// error response.
    pub fn handle(&self, request: &RemoteRequest, now: f64) -> RemoteResponse {
        if request.version != REMOTE_PROTOCOL_VERSION {
            return RemoteResponse::err("unsupported remote protocol version");
        }
        if !now.is_finite()
            || !request.timestamp.is_finite()
            || (now - request.timestamp).abs() > MAX_SKEW_SECS
        {
            return RemoteResponse::err("remote request expired");
        }
        let expected = sign_request(
            &self.secret,
            &request.function,
            &request.args,
            &request.kwargs,
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
            // No Rust handler: forward to the operator's Python bundle if
            // one is configured.  That bundle holds the implementations
            // that never ship, so this IS the Level-5 path -- the algorithm
            // exists only on the service side.
            None => match &self.worker_bundle {
                Some(bundle) => self.forward_to_worker(bundle, request),
                None => {
                    RemoteResponse::err(format!("unknown remote function '{}'", request.function))
                }
            },
        }
    }

    /// Forward a verified request to the operator's Python bundle.
    ///
    /// The bundle is executed as `python3 <bundle> --call <function>` with
    /// the request on stdin; it writes a JSON response to stdout.  A
    /// non-zero exit or invalid JSON is an error response, never a panic.
    fn forward_to_worker(&self, bundle: &str, request: &RemoteRequest) -> RemoteResponse {
        let payload = serde_json::to_string(request).unwrap_or_default();
        let python = std::env::var("NIXON_REMOTE_PYTHON").unwrap_or_else(|_| "python3".to_string());
        let output = match run_worker(
            &python,
            &[bundle, "--call", &request.function],
            payload.as_bytes(),
            WORKER_DEADLINE,
            MAX_WORKER_STDOUT,
            MAX_WORKER_STDERR,
        ) {
            Ok(output) => output,
            Err(message) => return RemoteResponse::err(message),
        };
        if !output.status.success() {
            return RemoteResponse::err(format!(
                "worker exited with {}: {}",
                output.status,
                String::from_utf8_lossy(&output.stderr)
                    .chars()
                    .take(200)
                    .collect::<String>()
            ));
        }
        match serde_json::from_slice::<RemoteResponse>(&output.stdout) {
            Ok(response) => response,
            Err(err) => RemoteResponse::err(format!("worker response was not JSON: {}", err)),
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

const WORKER_DEADLINE: Duration = Duration::from_secs(10);
const MAX_WORKER_STDOUT: usize = 1 << 20;
const MAX_WORKER_STDERR: usize = 64 << 10;

#[derive(Debug)]
struct WorkerOutput {
    stdout: Vec<u8>,
    stderr: Vec<u8>,
    status: std::process::ExitStatus,
}

fn read_worker_pipe(mut pipe: impl Read, limit: usize) -> std::io::Result<(Vec<u8>, bool)> {
    let mut output = Vec::new();
    let mut buffer = [0u8; 8192];
    let mut overflow = false;
    loop {
        match pipe.read(&mut buffer) {
            Ok(0) => break,
            Ok(count) => {
                let room = limit.saturating_sub(output.len());
                let keep = room.min(count);
                output.extend_from_slice(&buffer[..keep]);
                if keep < count {
                    overflow = true;
                }
            }
            Err(error) if error.kind() == std::io::ErrorKind::Interrupted => continue,
            Err(error) => return Err(error),
        }
    }
    Ok((output, overflow))
}

/// Run a worker with concurrent stdin/stdout/stderr I/O, a hard deadline and
/// bounded captured output. On timeout the direct child is killed and reaped.
fn run_worker(
    program: &str,
    args: &[&str],
    payload: &[u8],
    deadline: Duration,
    stdout_limit: usize,
    stderr_limit: usize,
) -> Result<WorkerOutput, String> {
    use std::process::{Command, Stdio};
    let mut child = Command::new(program)
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("worker spawn failed: {error}"))?;
    let stdin = child.stdin.take().ok_or("worker stdin unavailable")?;
    let stdout = child.stdout.take().ok_or("worker stdout unavailable")?;
    let stderr = child.stderr.take().ok_or("worker stderr unavailable")?;

    let writer_payload = payload.to_vec();
    let writer = std::thread::spawn(move || -> std::io::Result<()> {
        let mut stdin = stdin;
        std::io::Write::write_all(&mut stdin, &writer_payload)
    });
    let stdout_reader = std::thread::spawn(move || read_worker_pipe(stdout, stdout_limit));
    let stderr_reader = std::thread::spawn(move || read_worker_pipe(stderr, stderr_limit));

    let started = Instant::now();
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) => {
                if started.elapsed() >= deadline {
                    let _ = child.kill();
                    match child.wait() {
                        Ok(_) => {}
                        Err(error) => return Err(format!("worker reap failed: {error}")),
                    }
                    let _ = writer.join();
                    let _ = stdout_reader.join();
                    let _ = stderr_reader.join();
                    return Err("worker deadline exceeded".to_string());
                }
                std::thread::sleep(Duration::from_millis(10));
            }
            Err(error) => {
                let _ = child.kill();
                let _ = child.wait();
                return Err(format!("worker wait failed: {error}"));
            }
        }
    };

    let writer_result = writer
        .join()
        .map_err(|_| "worker writer thread failed".to_string())?;
    writer_result.map_err(|error| format!("worker stdin failed: {error}"))?;
    let (stdout, stdout_overflow) = stdout_reader
        .join()
        .map_err(|_| "worker stdout thread failed".to_string())?
        .map_err(|error| format!("worker stdout failed: {error}"))?;
    let (stderr, _) = stderr_reader
        .join()
        .map_err(|_| "worker stderr thread failed".to_string())?
        .map_err(|error| format!("worker stderr failed: {error}"))?;
    if stdout_overflow {
        return Err(format!(
            "worker stdout limit exceeded ({stdout_limit} bytes)"
        ));
    }
    Ok(WorkerOutput {
        stdout,
        stderr,
        status,
    })
}

/// Read the shared secret from the environment.  Never from a file in the
/// repo and never from argv: the same rule the Python side follows.
pub fn secret_from_env() -> Result<Vec<u8>, String> {
    let raw = std::env::var("NIXON_REMOTE_SECRET")
        .map_err(|_| "NIXON_REMOTE_SECRET is not set".to_string())?;
    let raw = raw.trim();
    let bytes = raw.as_bytes();
    if bytes.len() != 64 || !bytes.iter().all(u8::is_ascii_hexdigit) {
        return Err("NIXON_REMOTE_SECRET must be 64 ASCII hex characters".to_string());
    }
    let mut out = Vec::with_capacity(32);
    for pair in bytes.chunks_exact(2) {
        let high = hex_nibble(pair[0]).ok_or("NIXON_REMOTE_SECRET must be hex")?;
        let low = hex_nibble(pair[1]).ok_or("NIXON_REMOTE_SECRET must be hex")?;
        out.push((high << 4) | low);
    }
    Ok(out)
}

fn hex_nibble(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        b'A'..=b'F' => Some(byte - b'A' + 10),
        _ => None,
    }
}

/// Max bytes accepted for the request line or any single header line.
const MAX_LINE: usize = 8 * 1024;
/// Max aggregate request-line + header bytes.
const MAX_HEADER_BYTES: usize = 16 * 1024;
/// Max number of header fields.
const MAX_HEADERS: usize = 64;
/// Max accepted Content-Length (1 MiB).
const MAX_BODY: usize = 1 << 20;
/// Absolute time allowed to receive one request, including a dribbling body.
const REQUEST_DEADLINE: Duration = Duration::from_secs(30);
/// Maximum time a response write may block.
const WRITE_TIMEOUT: Duration = Duration::from_secs(10);

#[derive(Debug)]
enum RequestError {
    Http(u16, &'static str),
    Io(std::io::Error),
}

impl From<std::io::Error> for RequestError {
    fn from(error: std::io::Error) -> Self {
        Self::Io(error)
    }
}

fn remaining(deadline: Instant) -> Result<Duration, RequestError> {
    let now = Instant::now();
    if now >= deadline {
        Err(RequestError::Http(408, "request deadline exceeded"))
    } else {
        Ok(deadline.saturating_duration_since(now))
    }
}

fn read_http_line(
    reader: &mut BufReader<TcpStream>,
    buffer: &mut Vec<u8>,
    deadline: Instant,
    total: &mut usize,
) -> Result<Option<usize>, RequestError> {
    reader
        .get_mut()
        .set_read_timeout(Some(remaining(deadline)?))
        .map_err(RequestError::Io)?;
    buffer.clear();
    let count = reader
        .by_ref()
        .take(MAX_LINE as u64 + 1)
        .read_until(b'\n', buffer)
        .map_err(|error| {
            if matches!(
                error.kind(),
                std::io::ErrorKind::TimedOut | std::io::ErrorKind::WouldBlock
            ) {
                RequestError::Http(408, "request deadline exceeded")
            } else {
                RequestError::Io(error)
            }
        })?;
    if count == 0 {
        return Ok(None);
    }
    *total = total.saturating_add(count);
    if count > MAX_LINE || *total > MAX_HEADER_BYTES {
        return Err(RequestError::Http(431, "request headers too large"));
    }
    if !buffer.ends_with(b"\r\n") {
        return Err(RequestError::Http(400, "malformed HTTP line"));
    }
    Ok(Some(count))
}

fn valid_header_name(name: &[u8]) -> bool {
    !name.is_empty()
        && name.iter().all(|byte| {
            byte.is_ascii_alphanumeric()
                || matches!(
                    byte,
                    b'!' | b'#'
                        | b'$'
                        | b'%'
                        | b'&'
                        | b'\''
                        | b'*'
                        | b'+'
                        | b'-'
                        | b'.'
                        | b'^'
                        | b'_'
                        | b'`'
                        | b'|'
                        | b'~'
                )
        })
}

fn parse_request_line(line: &[u8]) -> Result<(), RequestError> {
    let text =
        std::str::from_utf8(line).map_err(|_| RequestError::Http(400, "invalid request line"))?;
    let mut parts = text[..text.len() - 2].split(' ');
    let method = parts.next().unwrap_or("");
    let target = parts.next().unwrap_or("");
    let version = parts.next().unwrap_or("");
    if method.is_empty()
        || target.is_empty()
        || version != "HTTP/1.1"
        || parts.next().is_some()
        || !text.is_ascii()
    {
        return Err(RequestError::Http(400, "invalid request line"));
    }
    if method != "POST" {
        return Err(RequestError::Http(405, "method not allowed"));
    }
    Ok(())
}

fn serve_one_inner(
    service: &RemoteService,
    mut stream: TcpStream,
    deadline: Instant,
) -> Result<(), RequestError> {
    stream
        .set_write_timeout(Some(WRITE_TIMEOUT))
        .map_err(RequestError::Io)?;
    let mut reader = BufReader::new(stream.try_clone()?);
    let mut total = 0usize;
    let mut line = Vec::new();
    if read_http_line(&mut reader, &mut line, deadline, &mut total)?.is_none() {
        return Ok(());
    }
    parse_request_line(&line)?;

    let mut content_length = None;
    let mut header_count = 0usize;
    loop {
        if read_http_line(&mut reader, &mut line, deadline, &mut total)?.is_none() {
            return Err(RequestError::Http(400, "truncated headers"));
        }
        if line == b"\r\n" {
            break;
        }
        header_count += 1;
        if header_count > MAX_HEADERS {
            return Err(RequestError::Http(431, "too many headers"));
        }
        let text = std::str::from_utf8(&line[..line.len() - 2])
            .map_err(|_| RequestError::Http(400, "invalid header"))?;
        let (name, value) = text
            .split_once(':')
            .ok_or(RequestError::Http(400, "malformed header"))?;
        if !valid_header_name(name.as_bytes())
            || value
                .bytes()
                .any(|byte| byte < 0x20 && byte != b'\t' || byte == 0x7f)
        {
            return Err(RequestError::Http(400, "malformed header"));
        }
        let value = value.trim_matches(|ch| ch == ' ' || ch == '\t');
        if name.eq_ignore_ascii_case("transfer-encoding") {
            return Err(RequestError::Http(
                400,
                "transfer-encoding is not supported",
            ));
        }
        if name.eq_ignore_ascii_case("content-length") {
            if content_length.is_some() {
                return Err(RequestError::Http(400, "duplicate content-length"));
            }
            if value.is_empty() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
                return Err(RequestError::Http(400, "invalid content-length"));
            }
            let parsed = value
                .parse::<usize>()
                .map_err(|_| RequestError::Http(400, "invalid content-length"))?;
            if parsed > MAX_BODY {
                return Err(RequestError::Http(413, "content length too large"));
            }
            content_length = Some(parsed);
        }
    }
    let content_length =
        content_length.ok_or(RequestError::Http(411, "content-length required"))?;
    reader
        .get_mut()
        .set_read_timeout(Some(remaining(deadline)?))
        .map_err(RequestError::Io)?;
    let mut body = vec![0u8; content_length];
    reader
        .read_exact(&mut body)
        .map_err(|error| match error.kind() {
            std::io::ErrorKind::TimedOut | std::io::ErrorKind::WouldBlock => {
                RequestError::Http(408, "request deadline exceeded")
            }
            std::io::ErrorKind::UnexpectedEof => RequestError::Http(400, "truncated body"),
            _ => RequestError::Io(error),
        })?;
    remaining(deadline)?;
    let response = service.handle_body(&body, now_secs());
    let payload = serde_json::to_vec(&response).unwrap_or_else(|_| b"{}".to_vec());
    write_response(&mut stream, 200, &payload)?;
    Ok(())
}

/// Serve one HTTP/1.1 request from `stream` and write the response.
pub fn serve_one(service: &RemoteService, stream: TcpStream) -> std::io::Result<()> {
    serve_one_with_deadline(service, stream, REQUEST_DEADLINE)
}

fn serve_one_with_deadline(
    service: &RemoteService,
    stream: TcpStream,
    duration: Duration,
) -> std::io::Result<()> {
    let mut stream = stream;
    match serve_one_inner(service, stream.try_clone()?, Instant::now() + duration) {
        Ok(()) => Ok(()),
        Err(RequestError::Http(status, message)) => {
            // A timed read leaves the duplicated socket nonblocking on Unix.
            // Restore blocking mode before the bounded response write.
            stream.set_nonblocking(false)?;
            write_response(
                &mut stream,
                status,
                format!("{{\"error\":\"{message}\"}}").as_bytes(),
            )
        }
        Err(RequestError::Io(error)) => Err(error),
    }
}

fn write_response(stream: &mut TcpStream, status: u16, body: &[u8]) -> std::io::Result<()> {
    stream
        .set_write_timeout(Some(WRITE_TIMEOUT))
        .map_err(|error| {
            std::io::Error::new(error.kind(), format!("set write timeout: {error}"))
        })?;
    let reason = match status {
        200 => "OK",
        400 => "Bad Request",
        405 => "Method Not Allowed",
        408 => "Request Timeout",
        411 => "Length Required",
        413 => "Content Too Large",
        431 => "Request Header Fields Too Large",
        503 => "Service Unavailable",
        _ => "Error",
    };
    let head = format!(
        "HTTP/1.1 {} {}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
        status,
        reason,
        body.len()
    );
    stream.write_all(head.as_bytes()).map_err(|error| {
        std::io::Error::new(error.kind(), format!("write response head: {error}"))
    })?;
    stream.write_all(body).map_err(|error| {
        std::io::Error::new(error.kind(), format!("write response body: {error}"))
    })?;
    stream
        .flush()
        .map_err(|error| std::io::Error::new(error.kind(), format!("flush response: {error}")))
}

/// Bind and serve until the process is stopped.
///
/// Refuses a non-loopback address unless `allow_remote` is set: the endpoint
/// speaks plain HTTP, so exposing it on a network would leak the arguments.
pub fn serve(service: Arc<RemoteService>, addr: &str, allow_remote: bool) -> Result<(), String> {
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
    // Bound the number of concurrent connection threads: an unbounded
    // thread-per-connection accept loop is a trivial resource-exhaustion
    // vector. At the cap, answer 503 immediately instead of spawning.
    const MAX_CONNECTIONS: usize = 64;
    let live = Arc::new(std::sync::atomic::AtomicUsize::new(0));
    for incoming in listener.incoming() {
        match incoming {
            Ok(mut stream) => {
                let svc = Arc::clone(&service);
                let live = Arc::clone(&live);
                if live.fetch_add(1, std::sync::atomic::Ordering::AcqRel) >= MAX_CONNECTIONS {
                    live.fetch_sub(1, std::sync::atomic::Ordering::AcqRel);
                    let mut s = stream;
                    let _ = write_response(&mut s, 503, b"{\"error\":\"too many connections\"}");
                    continue;
                }
                let worker_stream = match stream.try_clone() {
                    Ok(worker_stream) => worker_stream,
                    Err(_) => {
                        live.fetch_sub(1, std::sync::atomic::Ordering::AcqRel);
                        continue;
                    }
                };
                let connection_live = Arc::clone(&live);
                let spawned = std::thread::Builder::new()
                    .name("remote-http".to_string())
                    .spawn(move || {
                        let _ = serve_one(&svc, worker_stream);
                        connection_live.fetch_sub(1, std::sync::atomic::Ordering::AcqRel);
                    });
                if spawned.is_err() {
                    live.fetch_sub(1, std::sync::atomic::Ordering::AcqRel);
                    eprintln!("remote: failed to spawn connection thread");
                    let _ =
                        write_response(&mut stream, 503, b"{\"error\":\"too many connections\"}");
                }
            }
            Err(_) => {
                // Don't busy-spin on a persistent accept error.
                std::thread::sleep(std::time::Duration::from_millis(50));
            }
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

    fn signed(
        svc: &RemoteService,
        function: &str,
        args: Vec<serde_json::Value>,
        nonce: &str,
        ts: f64,
    ) -> RemoteRequest {
        RemoteRequest {
            version: REMOTE_PROTOCOL_VERSION,
            function: function.to_string(),
            args: args.clone(),
            kwargs: serde_json::Map::new(),
            nonce: nonce.to_string(),
            timestamp: ts,
            signature: sign_request(
                &svc.secret,
                function,
                &args,
                &serde_json::Map::new(),
                nonce,
                ts,
            ),
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

    #[test]
    fn protocol_v1_cross_language_vectors() {
        // Fixed vectors also appear in tests/test_remote_exec.py.
        let vectors = [
            (
                json!([1, -0.0, "é", true, null, {"b": 2, "a": 1.5}]),
                json!({"rate": 0.5, "label": "x"}),
                "nonce",
                1000.0,
                "b2adc43bf63eb2bfeb87e9b5b509f636b2de11ea36189d23893c7a1be44c030f",
            ),
            (
                json!([]),
                json!({}),
                "n",
                0.0,
                "382e67120a57399c948f27624de9082070d2b80b3e847fcfa421b5b26fb2a396",
            ),
            (
                json!([-9223372036854775808i64, 18446744073709551615u64]),
                json!({"z": 1}),
                "abc",
                1.25,
                "0297cce9a44e6d8da81abbed561dc5ae941c1da98a6b0148df740ec2aa2d59fe",
            ),
        ];
        let mut svc = RemoteService::new(vec![0x11; 32]);
        svc.register("f", |args| Ok(json!(args)));
        for (args, kwargs, nonce, timestamp, signature) in vectors {
            let body = json!({
                "version": 1,
                "function": "f",
                "args": args,
                "kwargs": kwargs,
                "nonce": nonce,
                "timestamp": timestamp,
                "signature": signature,
            });
            let response = svc.handle_body(&serde_json::to_vec(&body).unwrap(), timestamp);
            assert_eq!(response.result, Some(args), "{:?}", response.error);
        }
    }

    #[test]
    fn unsupported_protocol_version_is_rejected() {
        let svc = service();
        let body = json!({
            "version": 2,
            "function": "add",
            "args": [1, 2],
            "kwargs": {},
            "nonce": "version-nonce",
            "timestamp": 1000.0,
            "signature": "00",
        });
        let response = svc.handle_body(&serde_json::to_vec(&body).unwrap(), 1000.0);
        assert!(response.error.unwrap().contains("version"));
    }

    #[test]
    fn non_ascii_remote_secret_is_an_error_not_a_panic() {
        const KEY: &str = "NIXON_REMOTE_SECRET";
        let old = std::env::var_os(KEY);
        std::env::set_var(KEY, "é".repeat(64));
        let result = std::panic::catch_unwind(secret_from_env);
        match old {
            Some(value) => std::env::set_var(KEY, value),
            None => std::env::remove_var(KEY),
        }
        assert!(result.is_ok(), "secret parsing panicked");
        assert!(result.unwrap().is_err());
    }

    fn serve_one_pair(request: &[u8]) -> Vec<u8> {
        use std::io::{Read, Write};
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        let req = request.to_vec();
        let client = std::thread::spawn(move || {
            let mut s = std::net::TcpStream::connect(addr).unwrap();
            let _ = s.write_all(&req);
            let mut buf = Vec::new();
            let mut chunk = [0u8; 4096];
            loop {
                match s.read(&mut chunk) {
                    Ok(0) => break,
                    Ok(count) => buf.extend_from_slice(&chunk[..count]),
                    Err(_) => break,
                }
            }
            buf
        });
        let (stream, _) = listener.accept().unwrap();
        let svc = service();
        serve_one(&svc, stream).unwrap();
        client.join().unwrap()
    }

    #[test]
    fn oversize_header_is_rejected_with_431() {
        let mut req = b"POST / HTTP/1.1\r\nX-Big: ".to_vec();
        req.extend(std::iter::repeat_n(b'A', 9 * 1024));
        req.extend_from_slice(b"\r\n\r\n");
        let resp = serve_one_pair(&req);
        let head = String::from_utf8_lossy(&resp);
        assert!(head.starts_with("HTTP/1.1 431"), "{}", &head[..60]);
    }

    #[test]
    fn oversize_content_length_is_rejected_with_413() {
        let req = b"POST / HTTP/1.1\r\nContent-Length: 99999999\r\n\r\n";
        let resp = serve_one_pair(req);
        let head = String::from_utf8_lossy(&resp);
        assert!(head.starts_with("HTTP/1.1 413"), "{}", &head[..60]);
    }

    #[test]
    fn response_writes_have_a_timeout() {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        let client = std::net::TcpStream::connect(addr).unwrap();
        let (mut server, _) = listener.accept().unwrap();
        write_response(&mut server, 200, b"{}").unwrap();
        assert_eq!(server.write_timeout().unwrap(), Some(WRITE_TIMEOUT));
        drop(client);
    }

    #[test]
    fn duplicate_content_length_is_rejected() {
        let req = b"POST / HTTP/1.1\r\nContent-Length: 0\r\nContent-Length: 0\r\n\r\n";
        let resp = serve_one_pair(req);
        assert!(String::from_utf8_lossy(&resp).starts_with("HTTP/1.1 400"));
    }

    #[test]
    fn transfer_encoding_is_rejected() {
        let req = b"POST / HTTP/1.1\r\nContent-Length: 0\r\nTransfer-Encoding: chunked\r\n\r\n";
        let resp = serve_one_pair(req);
        assert!(String::from_utf8_lossy(&resp).starts_with("HTTP/1.1 400"));
    }

    #[test]
    fn aggregate_header_cap_is_enforced() {
        let mut req = b"POST / HTTP/1.1\r\n".to_vec();
        for i in 0..100 {
            req.extend_from_slice(format!("X-{i}: {}\r\n", "a".repeat(200)).as_bytes());
        }
        req.extend_from_slice(b"Content-Length: 0\r\n\r\n");
        let resp = serve_one_pair(&req);
        assert!(String::from_utf8_lossy(&resp).starts_with("HTTP/1.1 431"));
    }

    #[test]
    fn worker_drains_stdout_while_stdin_is_being_written() {
        let script = "import sys; sys.stdout.buffer.write(b'x' * 262144); sys.stdout.flush(); sys.stdin.buffer.read(); sys.stdout.buffer.write(b'ok')";
        let output = run_worker(
            "python3",
            &["-c", script],
            &vec![b'y'; 262144],
            std::time::Duration::from_secs(3),
            1024 * 1024,
            64 * 1024,
        );
        assert!(output.is_ok());
        assert_eq!(
            output.unwrap().stdout,
            b"x".repeat(262144)
                .into_iter()
                .chain(b"ok".iter().copied())
                .collect::<Vec<_>>()
        );
    }

    #[test]
    fn worker_forwarding_preserves_kwargs_and_rechecks_signature() {
        use std::path::PathBuf;

        struct Scratch(PathBuf);
        impl Drop for Scratch {
            fn drop(&mut self) {
                let _ = std::fs::remove_file(&self.0);
            }
        }
        let base = if std::path::Path::new("/tmp/opencode").is_dir() {
            PathBuf::from("/tmp/opencode")
        } else {
            std::env::temp_dir()
        };
        let path = base.join(format!("hungerg-worker-kwargs-{}.py", std::process::id()));
        let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .expect("repository root");
        let script = format!(
            r#"
import sys
sys.path.insert(0, {root:?})
from obfuscator.remote_exec import RemoteRegistry
registry = RemoteRegistry(bytes.fromhex("11" * 32))
def add_tax(amount, rate=0.2):
    return amount * (1 + rate)
registry.register("add_tax", add_tax)
sys.stdout.buffer.write(registry.handle(sys.stdin.buffer.read()))
"#,
            root = root
        );
        std::fs::write(&path, script).unwrap();
        let _scratch = Scratch(path.clone());
        let secret = vec![0x11; 32];
        let svc = RemoteService::new(secret.clone())
            .with_worker_bundle(path.to_string_lossy().into_owned());
        let args = vec![json!(100)];
        let kwargs = serde_json::Map::from_iter([("rate".to_string(), json!(0.5))]);
        let timestamp = now_secs();
        let request = RemoteRequest {
            version: REMOTE_PROTOCOL_VERSION,
            function: "add_tax".to_string(),
            args,
            kwargs,
            nonce: "worker-kwargs-nonce".to_string(),
            timestamp,
            signature: String::new(),
        };
        let request = RemoteRequest {
            signature: sign_request(
                &secret,
                &request.function,
                &request.args,
                &request.kwargs,
                &request.nonce,
                request.timestamp,
            ),
            ..request
        };
        let response = svc.handle(&request, timestamp);
        assert_eq!(response.result, Some(json!(150.0)), "{:?}", response.error);
    }

    #[test]
    fn worker_deadline_kills_and_reaps_child() {
        let script = "import time; time.sleep(10)";
        let start = std::time::Instant::now();
        let result = run_worker(
            "python3",
            &["-c", script],
            b"",
            std::time::Duration::from_millis(150),
            1024,
            1024,
        );
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("deadline"));
        assert!(start.elapsed() < std::time::Duration::from_secs(2));
    }

    #[test]
    fn worker_output_is_capped() {
        let script = "import sys; sys.stdout.buffer.write(b'x' * 4096)";
        let result = run_worker(
            "python3",
            &["-c", script],
            b"",
            std::time::Duration::from_secs(2),
            1024,
            1024,
        );
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("stdout limit"));
    }

    #[test]
    fn slow_peer_does_not_hold_thread_forever() {
        use std::io::Write;
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        let client = std::thread::spawn(move || {
            let mut s = std::net::TcpStream::connect(addr).unwrap();
            s.write_all(b"POST / HTTP/1.1\r\n").unwrap(); // then stall
            std::thread::sleep(std::time::Duration::from_secs(2));
            drop(s);
        });
        let (stream, _) = listener.accept().unwrap();
        let svc = service();
        let start = std::time::Instant::now();
        // read timeout is 30s; we only assert serve_one returns *eventually*
        // on EOF, not that it hangs. Use a short manual check instead:
        let _ = serve_one(&svc, stream);
        assert!(start.elapsed() < std::time::Duration::from_secs(35));
        client.join().unwrap();
    }

    #[test]
    fn absolute_deadline_rejects_a_dribbling_peer() {
        use std::io::Write;
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        let client = std::thread::spawn(move || {
            let mut s = std::net::TcpStream::connect(addr).unwrap();
            let _ = s.write_all(b"POST / HTTP/1.1\r\n");
            std::thread::sleep(std::time::Duration::from_millis(300));
            let _ = s.write_all(b"Content-Length: 0\r\n\r\n");
            let mut response = Vec::new();
            let _ = s.read_to_end(&mut response);
            response
        });
        let (stream, _) = listener.accept().unwrap();
        let start = std::time::Instant::now();
        serve_one_with_deadline(&service(), stream, std::time::Duration::from_millis(100)).unwrap();
        assert!(start.elapsed() < std::time::Duration::from_secs(2));
        let response = client.join().unwrap();
        assert!(String::from_utf8_lossy(&response).starts_with("HTTP/1.1 408"));
    }
}
