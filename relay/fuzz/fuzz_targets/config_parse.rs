#![no_main]

use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    if data.is_empty() {
        return;
    }
    let _ = serde_json::from_slice::<orbital_relay::config::Config>(data);
});
