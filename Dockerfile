# NOTE: base image pinned by digest for release reproducibility
# (resolved 2026-09-23; refresh with: docker pull ubuntu:24.04 &&
# docker inspect --format='{{index .RepoDigests 0}}' ubuntu:24.04).
FROM ubuntu@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    g++ \
    gcc-mingw-w64-x86-64 \
    python3 \
    python3-dev \
    python3-pip \
    llvm-dev \
    clang \
    lld \
    libclang-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Add cross-compilation targets
RUN rustup target add x86_64-pc-windows-gnu aarch64-unknown-linux-gnu

# Copy project
WORKDIR /build
COPY . .

# Install Python dependencies (failures propagate: a tester image must
# never look green while broken).
RUN pip3 install --no-cache-dir -r requirements.txt

# Build
RUN make all

# Testing image
FROM builder AS tester
RUN make test
