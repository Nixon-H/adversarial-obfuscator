# Nixon Project Makefile
# Version: 0.1.0

CXX      := g++
CXXFLAGS := -O2 -fPIC -shared -std=c++17
PYINCLUDES := $(shell python3-config --includes)
PYLDFLAGS  := $(shell python3-config --ldflags --embed 2>/dev/null || python3-config --ldflags)
NPROC      := $(shell nproc 2>/dev/null || echo 1)
MAKEFLAGS  += -j$(NPROC)

SRC := nixon_core.cpp
BUILD_DIR := build

CORES_O    := $(BUILD_DIR)/nixon_core.so
WB_O       := $(BUILD_DIR)/wb.so
PY_COMPILE := $(BUILD_DIR)/py_compile.so

.PHONY: all core wb py_compile clean strip install-deps lint test

all: core wb py_compile

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

clean:
	rm -rf $(BUILD_DIR)

strip:
	-strip $(BUILD_DIR)/*.so 2>/dev/null

install-deps:
	pip3 install -r requirements.txt

lint:
	-pylint *.py 2>/dev/null || pyflakes *.py 2>/dev/null || true

test:
	python3 -m pytest tests/ -v
