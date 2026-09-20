#![no_main]

use libfuzzer_sys::fuzz_target;

#[derive(serde::Deserialize, Debug)]
struct DnsAnswer {
    #[serde(rename = "type")]
    rtype: u16,
    data: String,
}

#[derive(serde::Deserialize, Debug)]
struct DnsResponse {
    #[serde(default)]
    Answer: Vec<DnsAnswer>,
}

fuzz_target!(|data: &[u8]| {
    if data.is_empty() {
        return;
    }
    let _ = serde_json::from_slice::<DnsResponse>(data);
});
