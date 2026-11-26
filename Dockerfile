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

# Copy project. SOURCE_COMMIT is supplied by the outer build command because
# .git is deliberately excluded from the context; the tester-stage manifest
# acceptance test can then bind the exact source revision honestly.
ARG SOURCE_COMMIT=""
ENV NIXON_SOURCE_COMMIT=${SOURCE_COMMIT}
WORKDIR /build
COPY . .

# Install Python dependencies (failures propagate: a tester image must
# never look green while broken). ubuntu:24.04 ships the PEP 668
# EXTERNALLY-MANAGED marker, so a bare `pip3 install` into the system
# environment is refused; --break-system-packages is required in this
# disposable build image.
# --ignore-installed avoids trying to uninstall distro-managed packages whose
# RECORD files are absent (notably wheel on Ubuntu 24.04).
RUN pip3 install --no-cache-dir --break-system-packages --ignore-installed -r requirements.txt

# Build
RUN make all

# Testing image. The suite's compatibility/lint gates call ruff directly, so
# install the same pinned version as requirements-dev.lock in the image too.
FROM builder AS tester
# Node is a test-time dependency of the Cloudflare-worker and JS-digest
# compatibility tests. Install it only in the tester stage so the builder
# toolchain layer remains reusable.
RUN apt-get update && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir --break-system-packages --ignore-installed ruff==0.16.1
# The in-container filesystem is slower than the developer host; keep the
# per-test safety net but allow enough headroom for build-heavy tests.
ENV NIXON_TEST_TIMEOUT=180
RUN make test
