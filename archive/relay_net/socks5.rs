use std::net::{Ipv4Addr, Ipv6Addr};
use tokio::io::{AsyncRead, AsyncReadExt, AsyncWrite, AsyncWriteExt};
use anyhow::{Context, Result};

#[derive(Debug, Clone)]
pub struct Socks5Request {
    pub version: u8,
    pub command: u8,
    pub addr_type: u8,
    pub host: String,
    pub port: u16,
    pub raw: Vec<u8>,
}

pub const SOCKS5_SUCCESS: u8 = 0x00;
pub const SOCKS5_GENERAL_FAILURE: u8 = 0x01;
pub const SOCKS5_CONN_NOT_ALLOWED: u8 = 0x02;
pub const SOCKS5_NET_UNREACHABLE: u8 = 0x03;
pub const SOCKS5_HOST_UNREACHABLE: u8 = 0x04;
pub const SOCKS5_CONN_REFUSED: u8 = 0x05;
pub const SOCKS5_TTL_EXPIRED: u8 = 0x06;
pub const SOCKS5_CMD_NOT_SUPPORTED: u8 = 0x07;
pub const SOCKS5_ADDR_NOT_SUPPORTED: u8 = 0x08;

pub async fn socks5_handshake(
    stream: &mut (impl AsyncRead + AsyncWrite + Unpin),
) -> Result<Socks5Request> {
    let mut buf = [0u8; 2];
    stream
        .read_exact(&mut buf)
        .await
        .context("failed to read SOCKS5 version and auth method count")?;

    let socks_version = buf[0];
    let auth_method_count = buf[1] as usize;

    if socks_version != 5 {
        anyhow::bail!("invalid SOCKS version: {}", socks_version);
    }

    if auth_method_count > 0 {
        let mut auth_methods = vec![0u8; auth_method_count];
        stream
            .read_exact(&mut auth_methods)
            .await
            .context("failed to read auth methods")?;
    }

    stream
        .write_all(&[0x05, 0x00])
        .await
        .context("failed to write SOCKS5 no-auth response")?;
    stream.flush().await.ok();

    let mut header = [0u8; 4];
    stream
        .read_exact(&mut header)
        .await
        .context("failed to read SOCKS5 request header")?;

    let req_version = header[0];
    let req_command = header[1];
    let req_addr_type = header[3];

    if req_version != 5 {
        anyhow::bail!("invalid request version: {}", req_version);
    }

    if req_command != 1 {
        stream
            .write_all(&socks5_failure_response(SOCKS5_CMD_NOT_SUPPORTED))
            .await
            .ok();
        anyhow::bail!("unsupported SOCKS5 command: {}", req_command);
    }

    let mut raw = Vec::with_capacity(256);
    raw.extend_from_slice(&header);

    let host = match req_addr_type {
        1 => {
            let mut addr = [0u8; 4];
            stream
                .read_exact(&mut addr)
                .await
                .context("failed to read IPv4 address")?;
            raw.extend_from_slice(&addr);
            Ipv4Addr::from(addr).to_string()
        }
        3 => {
            let mut len_byte = [0u8; 1];
            stream
                .read_exact(&mut len_byte)
                .await
                .context("failed to read domain name length")?;
            let domain_len = len_byte[0] as usize;
            raw.push(len_byte[0]);

            let mut domain = vec![0u8; domain_len];
            stream
                .read_exact(&mut domain)
                .await
                .context("failed to read domain name")?;
            raw.extend_from_slice(&domain);

            String::from_utf8(domain).context("domain name is not valid UTF-8")?
        }
        4 => {
            let mut addr = [0u8; 16];
            stream
                .read_exact(&mut addr)
                .await
                .context("failed to read IPv6 address")?;
            raw.extend_from_slice(&addr);
            Ipv6Addr::from(addr).to_string()
        }
        _ => {
            stream
                .write_all(&socks5_failure_response(SOCKS5_ADDR_NOT_SUPPORTED))
                .await
                .ok();
            anyhow::bail!("unsupported address type: {}", req_addr_type);
        }
    };

    let mut port_buf = [0u8; 2];
    stream
        .read_exact(&mut port_buf)
        .await
        .context("failed to read port")?;
    raw.extend_from_slice(&port_buf);
    let port = u16::from_be_bytes(port_buf);

    if port == 0 {
        stream
            .write_all(&socks5_failure_response(SOCKS5_GENERAL_FAILURE))
            .await
            .ok();
        anyhow::bail!("invalid port 0");
    }

    Ok(Socks5Request {
        version: req_version,
        command: req_command,
        addr_type: req_addr_type,
        host,
        port,
        raw,
    })
}

pub fn socks5_success_response(_request: &Socks5Request) -> Vec<u8> {
    vec![0x05, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
}

pub fn socks5_failure_response(error_code: u8) -> Vec<u8> {
    vec![0x05, error_code, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
}
