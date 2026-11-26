# Nixon Project Makefile
# Version: 0.1.0

CXX      := g++
# -O3 + LTO + hidden visibility. The three exported entry points
# (CompileToMarshal, FreeMarshalBuffer, the whitebox wrappers) carry an
# explicit __attribute__((visibility("default"))), so hiding everything else
# costs nothing at the ABI and removes the internal symbol table an analyst
# would otherwise read straight out of the .so.
CXXFLAGS := -O3 -fPIC -shared -std=c++17 -flto -fvisibility=hidden -fvisibility-inlines-hidden -fno-semantic-interposition
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

.PHONY: all core wb py_compile relay relay-win relay-linux-arm relay-all relay-cross relay-cross-prereqs clean strip install-deps lint lint-upgrade lock lock-verify e2e audit-commit lint-clean test irgen llvmgen encrypt all-shadow core-cpp native-test simd-vm-c

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

# The IR stage consumes the obfuscated payload produced by scripts/build.py
# (build/<stem>_obfuscated.py). There is no checked-in build/obfuscated.py, so
# produce it here instead of reading a file no rule creates.
OBF_PAYLOAD := $(BUILD_DIR)/hello_obfuscated.py

$(OBF_PAYLOAD): $(BUILD_DIR) scripts/build.py examples/hello.py config/default.json $(wildcard obfuscator/*.py obfuscator/core/*.py)
	python3 scripts/build.py --payload examples/hello.py --skip irgen llvmgen encrypt relay extras

irgen: $(BUILD_DIR) core $(OBF_PAYLOAD)
	python3 -m irgen $(OBF_PAYLOAD) -o build/program.ir

llvmgen: $(BUILD_DIR) irgen
	python3 -m llvmgen build/program.ir -o build/program.o -O bcf fla sub

encrypt: $(BUILD_DIR) llvmgen
	python3 -m encrypt encrypt build/program.o -o build/encrypted.o

relay: $(BUILD_DIR) $(RELAY_BIN)

$(RELAY_BIN): $(wildcard $(RELAY_DIR)/src/*.rs) $(wildcard $(RELAY_DIR)/../runtime/src/*.rs) $(RELAY_DIR)/Cargo.toml $(RELAY_DIR)/build.rs scripts/runtime_config.py
	cd $(RELAY_DIR) && $(CARGO) build --release
	cp $(RELAY_DIR)/target/release/orbital-relay $@
	-strip $@
	# The integrity check verifies this binary's own text, so the
	# expected value has to be produced from the binary that ships --
	# after strip, because strip changes it. Without this file
	# integrity_expected_crc stays None and verify_text_section is
	# never called.
	python3 -m scripts.runtime_config $@

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
	cd $(RELAY_DIR) && CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER=x86_64-w64-mingw32-gcc cargo build --release --target x86_64-pc-windows-gnu
	cp $(RELAY_DIR)/target/x86_64-pc-windows-gnu/release/orbital-relay.exe $(BUILD_DIR)/orbital-relay-win.exe
	-strip $(BUILD_DIR)/orbital-relay-win.exe
	@echo "[+] relay-win done: $(BUILD_DIR)/orbital-relay-win.exe"

relay-linux-arm: $(BUILD_DIR)
	@echo "[*] Cross-compiling relay for Linux ARM64..."
	cd $(RELAY_DIR) && rustup target add aarch64-unknown-linux-gnu 2>/dev/null || true
	if ! command -v aarch64-linux-gnu-gcc >/dev/null 2>&1; then \
		echo "[!] WARNING: aarch64-linux-gnu-gcc not found — link may fail"; \
	fi
	cd $(RELAY_DIR) && CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc cargo build --release --target aarch64-unknown-linux-gnu
	cp $(RELAY_DIR)/target/aarch64-unknown-linux-gnu/release/orbital-relay $(BUILD_DIR)/orbital-relay-linux-arm
	-strip $(BUILD_DIR)/orbital-relay-linux-arm
	@echo "[+] relay-linux-arm done: $(BUILD_DIR)/orbital-relay-linux-arm"

relay-all: relay relay-win relay-linux-arm

relay-cross: relay-win relay-linux-arm

# The Windows/Linux native stubs (native/stub_win.cpp, native/stub_linux.cpp)
# were archived on 2026-10-23 — see archive/native/README.md.  The shipped
# loader is the Python one; the native stub was a compile-test only, and its
# reflective-loading / AMSI / ETW code is out of scope for an IP-protection
# product (it is the "hide from defenders" half, not the "protect the code"
# half).  `make stub` and `make stub-win` no longer exist.
core-cpp:
	@echo "  CXX     native/core.cpp"
	PYINCLUDES=$$(python3-config --includes 2>/dev/null); \
	if echo '#include <Python.h>' | g++ -E -x c++ $$PYINCLUDES - >/dev/null 2>&1; then \
		g++ -c native/core.cpp -o native/core_test.o -fPIC -DCORE_HAVE_PYTHON_H $$PYINCLUDES; \
	else \
		g++ -c native/core.cpp -o native/core_test.o -fPIC; \
		echo "  [INFO] Compiled without Python.h (core only)"; \
	fi

# The native compile-test corpus was archived on 2026-10-23 (see
# archive/native/README.md): stub_win.cpp, stub_linux.cpp, vm_stub.c,
# microjit.c, crypto_chain.c, key_evolution.c, gpu_stub.c,
# self_healing.c, struct_random.c, cross_process.c, distributed_vm.c,
# fragment_migration.c.  None of them was in the shipped artefact; the
# ones with live behaviour have Python or Rust implementations that are
# wired.  native-test now only builds what the product actually uses.
native-test: core-cpp simd-vm-c abi-test

.PHONY: abi-test
abi-test:
	@echo "  CXX+RUN native/core_abi_test.cpp"
	@mkdir -p $(BUILD_DIR)
	g++ -std=c++17 -O1 -g -Wall -Wextra -Werror \
		native/core_abi_test.cpp $(SRC) $(WB_SRC) \
		-o $(BUILD_DIR)/core_abi_test
	$(BUILD_DIR)/core_abi_test

.PHONY: simd-vm-c
simd-vm-c:
	@echo "  CC      native/simd_vm.c"
	gcc -c native/simd_vm.c -o native/simd_vm_test.o -Wall -Werror -msse4.1
	@echo "  CC+RUN  native/simd_vm_test.c"
	@mkdir -p $(BUILD_DIR)
	gcc -I native native/simd_vm_test.c native/simd_vm.c -o $(BUILD_DIR)/simd_vm_test -msse4.1 -Wall -Werror
	$(BUILD_DIR)/simd_vm_test

clean:
	rm -rf $(BUILD_DIR)
	cd $(RELAY_DIR) && $(CARGO) clean 2>/dev/null || true

strip:
	-strip $(BUILD_DIR)/*.so 2>/dev/null

install-deps:
	# PEP 668 (Ubuntu >= 23.04 / Debian >= 12): a plain `pip3 install` into the
	# system environment is refused with EXTERNALLY-MANAGED. Fall back to
	# --break-system-packages only when the plain install fails, so hosts
	# without PEP 668 keep working unchanged. --ignore-installed avoids
	# uninstalling distro-managed packages whose RECORD files are missing.
	pip3 install -r requirements.txt || pip3 install --break-system-packages --ignore-installed -r requirements.txt

lint:
	ruff check --no-cache .
	python3 scripts/lint/check_undefined_globals.py
	python3 scripts/lint/generate_core_facade.py --check

# Bump the pinned linter.  The pin is deliberate -- an unpinned linter
# can turn a green tree red with no change to the code -- but a pin
# that is never reviewed goes stale.  This is the deliberate act.
lint-upgrade:
	@echo "Current pin:"; grep '^ruff==' requirements-dev.txt
	@echo "Latest on PyPI:"; pip index versions ruff 2>/dev/null | head -1
	@echo
	@echo "To bump: edit the ruff== line in requirements-dev.txt, then run"
	@echo "  ruff check --no-cache .   # and fix anything the new version reports"
	@echo "Review the diff before committing: a new ruff may find new"
	@echo "findings, and those are yours to accept or fix."

# Regenerate the hash-pinned dependency lock.  Review the diff: a new
# lock is a change to what CI is allowed to install.
lock:
	uv pip compile requirements.txt --generate-hashes --universal \
		--python-version 3.10 -o requirements.lock
	@echo "Review the diff, then verify: make lock-verify"
lock-verify:
	python3 -m venv /tmp/nixon-lock-venv
	/tmp/nixon-lock-venv/bin/pip install --require-hashes -r requirements.lock
	@echo "the lock installs cleanly with --require-hashes"

# End-to-end: every build must produce an artifact that RUNS.
# A build that produces a file which dies at import is a failure --
# that is the failure mode the seal-corruption bug had.
e2e:
	python3 scripts/lint/e2e_build_check.py 5
	python3 scripts/lint/e2e_build_check.py 3 --section-split

# Audit what a commit removed: the statements it deleted, and the ones
# among them that dropped a call (those are the ones that can change
# behaviour).
audit-commit:
	@python3 scripts/lint/audit_commit_removals.py --calls-only HEAD

# Re-run the deterministic lint cleanups (unused imports / unused locals).
# These are idempotent and only remove code the linter proves unused.
lint-clean:
	python3 scripts/lint/clean_unused_imports.py obfuscator/ scripts/ tests/ irgen/ vm/ llvmgen/ encrypt/ *.py --apply
	python3 scripts/lint/clean_unused_locals.py obfuscator/ scripts/ tests/ irgen/ vm/ llvmgen/ encrypt/ *.py --apply

test:
	PYTHONDONTWRITEBYTECODE=1 NIXON_TEST_TIMEOUT=60 python3 scripts/run_pytest.py tests/ -q -p no:cacheprovider
	cd runtime && cargo test
	cd relay && cargo test
