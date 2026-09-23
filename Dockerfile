# NOTE: ubuntu:24.04 is an LTS tag (moves with point releases). For
# release builds pin a digest (docker inspect --format='{{.RepoDigests}}').
FROM ubuntu:24.04 AS builder

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
