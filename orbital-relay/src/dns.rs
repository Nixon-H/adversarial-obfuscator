use std::net::IpAddr;
use std::str::FromStr;
use std::time::Duration;

use anyhow::{Context, Result};
use ipnetwork::IpNetwork;
use reqwest::Client;
use serde::Deserialize;
use tokio::time::timeout as tokio_timeout;

const DOH_URL: &str = "https://dns.google/dns-query";

const CF_IPV4_RANGES: &[&str] = &[
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22",
    "103.31.4.0/22", "141.101.64.0/18", "108.162.192.0/18",
    "190.93.240.0/20", "188.114.96.0/20", "197.234.240.0/22",
    "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
];

const CF_IPV6_RANGES: &[&str] = &[
    "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32",
    "2405:b500::/32", "2405:8100::/32", "2a06:98c0::/29",
    "2c0f:f248::/32",
];

#[derive(Debug, Deserialize)]
struct DnsAnswer {
    #[serde(rename = "type")]
    rtype: u16,
    data: String,
}

#[derive(Debug, Deserialize)]
struct DnsResponse {
    #[serde(default)]
    Answer: Vec<DnsAnswer>,
}

pub async fn resolve_doh(host: &str, timeout: Duration) -> Result<Vec<IpAddr>> {
    let client = Client::builder()
        .timeout(timeout)
        .build()?;

    let url = format!("{DOH_URL}?name={host}&type=A");
    let resp = client
        .get(&url)
        .header("Accept", "application/dns-json")
        .send()
        .await?;

    let dns_resp: DnsResponse = resp.json().await?;

    let mut ips = Vec::new();
    for answer in dns_resp.Answer {
        if answer.rtype == 1 || answer.rtype == 28 {
            if let Ok(ip) = IpAddr::from_str(&answer.data) {
                ips.push(ip);
            }
        }
    }
    Ok(ips)
}

pub fn is_cloudflare_ip(ip: &IpAddr) -> bool {
    let ranges = match ip {
        IpAddr::V4(_) => CF_IPV4_RANGES,
        IpAddr::V6(_) => CF_IPV6_RANGES,
    };

    ranges.iter().any(|cidr| {
        IpNetwork::from_str(cidr)
            .is_ok_and(|network| network.contains(*ip))
    })
}

async fn system_resolve(host: &str, timeout: Duration) -> Result<Vec<IpAddr>> {
    let addrs = tokio_timeout(timeout, tokio::net::lookup_host((host, 0)))
        .await
        .context("system resolver timed out")?
        .context("system resolver lookup failed")?;

    Ok(addrs.map(|sa| sa.ip()).collect())
}

pub async fn resolve_with_fallback(
    host: &str,
    use_doh: bool,
    timeout: Duration,
) -> Result<Vec<IpAddr>> {
    if use_doh {
        match resolve_doh(host, timeout).await {
            Ok(ips) if !ips.is_empty() => return Ok(ips),
            _ => {}
        }
    }

    system_resolve(host, timeout).await
}

pub async fn determine_if_service_ip(
    host: &str,
    use_doh: bool,
    timeout: Duration,
) -> Result<bool> {
    let ips = resolve_with_fallback(host, use_doh, timeout).await?;
    Ok(ips.iter().any(is_cloudflare_ip))
}
