# Nixon Project Makefile
# Version: 0.1.0

CXX      := g++
CXXFLAGS := -O2 -fPIC -shared -std=c++17
PYINCLUDES := $(shell python3-config --includes)
PYLDFLAGS  := $(shell python3-config --ldflags --embed 2>/dev/null || python3-config --ldflags)
CARGO     := cargo
NPROC      := $(shell nproc 2>/dev/null || echo 1)
MAKEFLAGS  += -j$(NPROC)

SRC       := native/core.cpp
WB_SRC    := native/whitebox_feistel.cpp
BUILD_DIR := build
RELAY_DIR := relay

CORES_O    := $(BUILD_DIR)/nixon_core.so
WB_O       := $(BUILD_DIR)/wb.so
PY_COMPILE := $(BUILD_DIR)/py_compile.so
RELAY_BIN  := $(BUILD_DIR)/orbital-relay

.PHONY: all core wb py_compile relay relay-win relay-linux-arm relay-all relay-cross relay-cross-prereqs clean strip install-deps lint test irgen llvmgen encrypt all-shadow stub stub-check vm-stub-so vm-stub-win

all: core wb py_compile relay

all-shadow: core wb py_compile irgen llvmgen encrypt relay

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

core: $(BUILD_DIR) $(CORES_O)

$(CORES_O): $(SRC) $(WB_SRC)
	$(CXX) $(CXXFLAGS) -DCORE_HAVE_PYTHON_H -o $@ $(SRC) $(WB_SRC) $(PYINCLUDES) $(PYLDFLAGS)
	-strip $@

wb: $(BUILD_DIR) $(WB_O)

$(WB_O): $(SRC) $(WB_SRC)
	$(CXX) $(CXXFLAGS) -DWHITEBOX_ONLY -o $@ $(SRC) $(WB_SRC) $(PYINCLUDES) $(PYLDFLAGS)
	-strip $@

py_compile: $(BUILD_DIR) $(PY_COMPILE)

$(PY_COMPILE): $(SRC) $(WB_SRC)
	$(CXX) $(CXXFLAGS) -DCORE_HAVE_PYTHON_H -DCOMPILE_ONLY -o $@ $(SRC) $(WB_SRC) $(PYINCLUDES) $(PYLDFLAGS)
	-strip $@

irgen: $(BUILD_DIR) core
	python3 -m irgen build/obfuscated.py -o build/program.ir

llvmgen: $(BUILD_DIR) irgen
	python3 -m llvmgen build/program.ir -o build/program.o -O bcf fla sub

encrypt: $(BUILD_DIR) llvmgen
	python3 -m encrypt encrypt build/program.o -o build/encrypted.o

relay: $(BUILD_DIR) $(RELAY_BIN)

$(RELAY_BIN): $(wildcard $(RELAY_DIR)/src/*.rs) $(RELAY_DIR)/Cargo.toml $(RELAY_DIR)/build.rs
	cd $(RELAY_DIR) && $(CARGO) build --release
	cp $(RELAY_DIR)/target/release/orbital-relay $@
	-strip $@

relay-cross-prereqs:
	@echo "[*] Checking cross-compilation prerequisites..."
	@echo -n "  x86_64-w64-mingw32-gcc (Windows): "; \
	if command -v x86_64-w64-mingw32-gcc >/dev/null 2>&1; then \
		echo "FOUND"; \
	else \
		echo "MISSING (sudo apt install gcc-mingw-w64-x86-64)"; \
	fi
	@echo -n "  aarch64-linux-gnu-gcc (Linux ARM64): "; \
	if command -v aarch64-linux-gnu-gcc >/dev/null 2>&1; then \
		echo "FOUND"; \
	else \
		echo "MISSING (sudo apt install gcc-aarch64-linux-gnu)"; \
	fi
	@echo "[*] Checking Rust cross targets..."
	@rustup target list --installed 2>/dev/null | awk '{print "  - " $$0}'; \
	if [ $$? -ne 0 ]; then \
		echo "  rustup not found — install from https://rustup.rs"; \
	fi

relay-win: $(BUILD_DIR)
	@echo "[*] Cross-compiling relay for Windows x86_64..."
	cd $(RELAY_DIR) && rustup target add x86_64-pc-windows-gnu 2>/dev/null || true
	cd $(RELAY_DIR) && cargo build --release --target x86_64-pc-windows-gnu
	cp $(RELAY_DIR)/target/x86_64-pc-windows-gnu/release/orbital-relay.exe $(BUILD_DIR)/orbital-relay-win.exe
	-strip $(BUILD_DIR)/orbital-relay-win.exe
	@echo "[+] relay-win done: $(BUILD_DIR)/orbital-relay-win.exe"

relay-linux-arm: $(BUILD_DIR)
	@echo "[*] Cross-compiling relay for Linux ARM64..."
	cd $(RELAY_DIR) && rustup target add aarch64-unknown-linux-gnu 2>/dev/null || true
	if ! command -v aarch64-linux-gnu-gcc >/dev/null 2>&1; then \
		echo "[!] WARNING: aarch64-linux-gnu-gcc not found — link may fail"; \
	fi
	cd $(RELAY_DIR) && cargo build --release --target aarch64-unknown-linux-gnu
	cp $(RELAY_DIR)/target/aarch64-unknown-linux-gnu/release/orbital-relay $(BUILD_DIR)/orbital-relay-linux-arm
	-strip $(BUILD_DIR)/orbital-relay-linux-arm
	@echo "[+] relay-linux-arm done: $(BUILD_DIR)/orbital-relay-linux-arm"

relay-all: relay relay-win relay-linux-arm

relay-cross: relay-win relay-linux-arm

# Windows stub — requires MinGW cross-compiler
STUB_SRC = native/stub_win.cpp
STUB_OUT = build/stub.exe
PAYLOAD_H = native/payload.h

$(STUB_OUT): $(STUB_SRC) $(PAYLOAD_H)
	@echo "  CXX     $<"
	$(QUIET)$(CXX) $(CXXFLAGS) -o $@ $< -lz -static -static-libgcc -static-libstdc++

stub: $(STUB_OUT)

stub-check:
	@echo "Checking MinGW availability..."
	@x86_64-w64-mingw32-g++ --version >/dev/null 2>&1 && echo "MinGW OK" || echo "MinGW not installed; run: apt install gcc-mingw-w64-x86-64"

stub-linux:
	@echo "  CC      native/stub_linux.cpp"
	gcc -o native/stub_linux_test native/stub_linux.cpp -lpthread

stub-win:
	@echo "  WIN32CC native/stub_win.cpp"
	@if command -v x86_64-w64-mingw32-gcc >/dev/null 2>&1; then \
		if echo '#include <Python.h>' | x86_64-w64-mingw32-gcc -E -x c - >/dev/null 2>&1; then \
			x86_64-w64-mingw32-gcc -o native/stub_win_test.exe native/stub_win.cpp -lz; \
		else \
			echo "  SKIP: Python.h not found for mingw cross-compiler"; \
		fi \
	else \
		echo "  SKIP: x86_64-w64-mingw32-gcc not found"; \
	fi

vm-stub:
	@echo "  CC      native/vm_stub.c"
	gcc -c native/vm_stub.c -o native/vm_stub_test.o

crypto-chain:
	@echo "  CC      native/crypto_chain.c"
	gcc -c native/crypto_chain.c -o native/crypto_chain_test.o -I native
	@echo "  CC      native/key_evolution.c"
	gcc -c native/key_evolution.c -o native/key_evolution_test.o -I native
	@echo "  CC      native/vm_stub.c (with crypto_chain)"
	gcc -c native/vm_stub.c -o native/vm_stub_crypto_test.o -I native
	@echo "  LD      crypto_chain.so"
	gcc -shared -fPIC native/vm_stub_crypto_test.o native/crypto_chain_test.o native/key_evolution_test.o -o native/crypto_chain.so -lc
	@echo "  [OK]    native/crypto_chain.so"

vm-stub-so:
	@echo "  CC      native/vm_stub.c (shared object)"
	gcc -shared -fPIC native/vm_stub.c -o native/vm_stub_test.so -lc

vm-stub-win:
	@echo "  WIN32CC native/vm_stub.c"
	@if command -v x86_64-w64-mingw32-gcc >/dev/null 2>&1; then \
		x86_64-w64-mingw32-gcc -c native/vm_stub.c -o native/vm_stub_win_test.o; \
		echo "  [OK] native/vm_stub_win_test.o"; \
	else \
		echo "  SKIP: x86_64-w64-mingw32-gcc not found"; \
	fi

core-cpp:
	@echo "  CXX     native/core.cpp"
	PYINCLUDES=$$(python3-config --includes 2>/dev/null); \
	if echo '#include <Python.h>' | g++ -E -x c++ $$PYINCLUDES - >/dev/null 2>&1; then \
		g++ -c native/core.cpp -o native/core_test.o -fPIC -DCORE_HAVE_PYTHON_H $$PYINCLUDES; \
	else \
		g++ -c native/core.cpp -o native/core_test.o -fPIC; \
		echo "  [INFO] Compiled without Python.h (core only)"; \
	fi

# NOTE: native/attestation.c was DELETED (unwired experimental sim with
# known defects). Canonical attestation is runtime/src/sw_attestation.rs
# (see docs/ATTESTATION.md; exercised by `cargo test` in runtime/).
# The `attestation` target is kept as a no-op so existing callers
# (native-test, CI) don't break.
attestation:
	@echo "  CC      native/attestation.c (deleted; canonical: runtime/src/sw_attestation.rs)"

native-test: stub-linux stub-win vm-stub core-cpp attestation microjit-c simd-vm-c gpu-stub-c self-healing-c struct-random-c

.PHONY: microjit-c
microjit-c:
	@echo "  CC      native/microjit.c"
	gcc -c native/microjit.c -o native/microjit_test.o -Wall -Werror

.PHONY: simd-vm-c
simd-vm-c:
	@echo "  CC      native/simd_vm.c"
	gcc -c native/simd_vm.c -o native/simd_vm_test.o -Wall -Werror -msse4.1

.PHONY: gpu-stub-c
gpu-stub-c:
	@echo "  CC      native/gpu_stub.c"
	# gpu_stub.c is an unwired experimental sim: explicitly opt in here only.
	gcc -DNIXON_EXPERIMENTAL -c native/gpu_stub.c -o native/gpu_stub_test.o -Wall -Werror

.PHONY: self-healing-c
self-healing-c:
	@echo "  CC      native/self_healing.c"
	gcc -c native/self_healing.c -o native/self_healing_test.o -Wall -Werror

.PHONY: struct-random-c
struct-random-c:
	@echo "  CC      native/struct_random.c"
	gcc -c native/struct_random.c -o native/struct_random_test.o -Wall -Werror

.PHONY: microjit-so
microjit-so:
	@echo "  CC      native/microjit.c (shared object)"
	gcc -shared -fPIC native/microjit.c native/key_evolution.c native/vm_stub.c -o /tmp/libmicrojit.so -lc

clean:
	rm -rf $(BUILD_DIR)
	cd $(RELAY_DIR) && $(CARGO) clean 2>/dev/null || true

strip:
	-strip $(BUILD_DIR)/*.so 2>/dev/null

install-deps:
	pip3 install -r requirements.txt

lint:
	-pylint obfuscator/ native/ scripts/ 2>/dev/null || pyflakes obfuscator/ native/ scripts/ 2>/dev/null || true

test:
	python3 -m pytest tests/ -v
	cd runtime && cargo test
	cd relay && cargo test
