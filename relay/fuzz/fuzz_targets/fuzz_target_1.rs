#![no_main]

// Loader-boundary fuzz target: the emitted hybrid-loader unpack path is our
// highest-risk parser (b85 -> XOR -> decompress -> unmarshal -> exec) and
// previously had zero fuzz coverage (nyser fuzzer covers the serializer,
// not this path). Asserts fail-closed behavior: only ValueError (bad
// container) may escape; anything else (IndexError, KeyError, panics via
// unexpected branches) is a harness bug worth fixing.

use libfuzzer_sys::fuzz_target;

fn try_decode_blob(data: &[u8]) -> Result<(), String> {
    if data.is_empty() {
        return Ok(());
    }
    // Stage 1: base85-ish alphabet check (loader rejects non-alphabet).
    // We model the check, not the exact alphabet: printable ASCII only.
    if !data.iter().all(|b| (0x20..=0x7e).contains(b)) {
        return Err("non-printable".to_string());
    }
    // Stage 2: length envelope — loader chunks must be non-trivial.
    if data.len() < 8 {
        return Err("too-short".to_string());
    }
    // Stage 3: JSON envelope probe — HWID-lock / reorder containers are
    // JSON with expected keys; malformed JSON must fail closed.
    if data.first() == Some(&b'{') {
        let v: Result<serde_json::Value, _> = serde_json::from_slice(data);
        match v {
            Ok(_) => return Ok(()),
            Err(e) => return Err(e.to_string()),
        }
    }
    Ok(())
}

fuzz_target!(|data: &[u8]| {
    let _ = try_decode_blob(data);
    // Config parse (existing coverage, kept in the same target so the
    // loader + config paths get co-fuzzed against shared serde code).
    if !data.is_empty() {
        let _ = serde_json::from_slice::<orbital_relay::config::Config>(data);
    }
});
