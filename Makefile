# Nixon Project Makefile
# Version: 0.1.0

CXX      := g++
CXXFLAGS := -O2 -fPIC -shared -std=c++17
PYINCLUDES := $(shell python3-config --includes)
PYLDFLAGS  := $(shell python3-config --ldflags --embed 2>/dev/null || python3-config --ldflags)
CARGO     := cargo
NPROC      := $(shell nproc 2>/dev/null || echo 1)
MAKEFLAGS  += -j$(NPROC)

SRC := nixon_core.cpp
BUILD_DIR := build
RELAY_DIR := orbital-relay

CORES_O    := $(BUILD_DIR)/nixon_core.so
WB_O       := $(BUILD_DIR)/wb.so
PY_COMPILE := $(BUILD_DIR)/py_compile.so
RELAY_BIN  := $(BUILD_DIR)/orbital-relay

.PHONY: all core wb py_compile relay clean strip install-deps lint test

all: core wb py_compile relay

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

core: $(BUILD_DIR) $(CORES_O)

$(CORES_O): $(SRC)
	$(CXX) $(CXXFLAGS) -o $@ $< $(PYINCLUDES) $(PYLDFLAGS)
	-strip $@

wb: $(BUILD_DIR) $(WB_O)

$(WB_O): $(SRC)
	$(CXX) $(CXXFLAGS) -DWHITEBOX_ONLY -o $@ $< $(PYINCLUDES) $(PYLDFLAGS)
	-strip $@

py_compile: $(BUILD_DIR) $(PY_COMPILE)

$(PY_COMPILE): $(SRC)
	$(CXX) $(CXXFLAGS) -DCOMPILE_ONLY -o $@ $< $(PYINCLUDES) $(PYLDFLAGS)
	-strip $@

relay: $(BUILD_DIR) $(RELAY_BIN)

$(RELAY_BIN): $(wildcard $(RELAY_DIR)/src/*.rs) $(RELAY_DIR)/Cargo.toml
	cd $(RELAY_DIR) && $(CARGO) build --release
	cp $(RELAY_DIR)/target/release/orbital-relay $@
	-strip $@

clean:
	rm -rf $(BUILD_DIR)
	cd $(RELAY_DIR) && $(CARGO) clean 2>/dev/null || true

strip:
	-strip $(BUILD_DIR)/*.so 2>/dev/null

install-deps:
	pip3 install -r requirements.txt

lint:
	-pylint *.py 2>/dev/null || pyflakes *.py 2>/dev/null || true

test:
	python3 -m pytest tests/ -v
