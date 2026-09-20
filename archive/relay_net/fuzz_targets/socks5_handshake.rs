#![no_main]

use std::pin::Pin;
use std::task::{Context, Poll};
use libfuzzer_sys::fuzz_target;
use tokio::io::{AsyncRead, AsyncWrite, ReadBuf};

struct FuzzStream<'a> {
    data: &'a [u8],
    pos: usize,
}

impl AsyncRead for FuzzStream<'_> {
    fn poll_read(
        mut self: Pin<&mut Self>,
        _cx: &mut Context<'_>,
        buf: &mut ReadBuf<'_>,
    ) -> Poll<std::io::Result<()>> {
        let available = &self.data[self.pos..];
        let len = std::cmp::min(available.len(), buf.remaining());
        buf.put_slice(&available[..len]);
        self.pos += len;
        Poll::Ready(Ok(()))
    }
}

impl AsyncWrite for FuzzStream<'_> {
    fn poll_write(
        self: Pin<&mut Self>,
        _cx: &mut Context<'_>,
        buf: &[u8],
    ) -> Poll<Result<usize, std::io::Error>> {
        Poll::Ready(Ok(buf.len()))
    }
    fn poll_flush(
        self: Pin<&mut Self>,
        _cx: &mut Context<'_>,
    ) -> Poll<Result<(), std::io::Error>> {
        Poll::Ready(Ok(()))
    }
    fn poll_shutdown(
        self: Pin<&mut Self>,
        _cx: &mut Context<'_>,
    ) -> Poll<Result<(), std::io::Error>> {
        Poll::Ready(Ok(()))
    }
}

impl Unpin for FuzzStream<'_> {}

fuzz_target!(|data: &[u8]| {
    if data.is_empty() {
        return;
    }
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        let mut stream = FuzzStream { data, pos: 0 };
        let _ = orbital_relay::socks5::socks5_handshake(&mut stream).await;
    });
});
