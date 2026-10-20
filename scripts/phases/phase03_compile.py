"""
phase03_compile.py

Purpose:
Compilation phases for the orbital-relay Rust binary and IR/LLVM code
generation.  Provides three entry points: native relay compilation,
cross-compilation for multiple targets, IR generation from Python,
and LLVM codegen with OLLVM passes.

Architectural Role:
Runs after obfuscation.  Produces the native orbital-relay binary and
compiled IR/object files used by encryption and packaging phases.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
os, shutil, subprocess, sys, ..common

Security Relevance:
Compilation with OLLVM passes (BCF, FLA, SUB) adds a second layer of
obfuscation at the IR/LLVM level.
"""

import os
import shutil
import subprocess
import sys

from ..common import log, run, BUILD_DIR, ROOT, RELAY_DIR


def phase_compile_relay():
    """
    Compile the orbital-relay native binary via make relay.

    The resulting binary is placed in BUILD_DIR.

    Raises:
        RuntimeError: if the binary is not produced.
    """
    log("RELAY", "Compiling orbital-relay (Rust)...")
    run(['make', 'relay'], timeout=1800)
    binary = os.path.join(BUILD_DIR, "orbital-relay")
    if not os.path.exists(binary):
        log("ERROR", "Rust build failed — binary not found")
        raise RuntimeError("Rust build failed — binary not found")
    size = os.path.getsize(binary)
    log("RELAY", f"Done: {binary} ({size/1024:.1f}KB, stripped)")


def phase_cross_compile(targets_str):
    """
    Cross-compile the orbital-relay binary for multiple targets.

    Args:
        targets_str: comma-separated target aliases (win, linux, macos, etc.)

    Returns:
        list of (target, ok, message) per-target results. Does not abort
        the loop on a single failure; the caller decides the exit status.
    """
    targets = [t.strip() for t in targets_str.split(",") if t.strip()]
    target_map = {
        "win": "x86_64-pc-windows-gnu",
        "win-arm": "aarch64-pc-windows-msvc",
        "linux": "x86_64-unknown-linux-gnu",
        "linux-arm": "aarch64-unknown-linux-gnu",
        "macos": "x86_64-apple-darwin",
        "macos-arm": "aarch64-apple-darwin",
    }

    results = []
    for t in targets:
        triple = target_map.get(t, t)
        log("CROSS", f"Building for {triple}...")
        try:
            run(['cargo', 'build', '--release', '--target', triple], cwd=RELAY_DIR, timeout=1800)
            src = os.path.join(RELAY_DIR, "target", triple, "release", "orbital-relay")
            if os.path.exists(src):
                ext = ".exe" if "windows" in triple else ""
                dst = os.path.join(BUILD_DIR, f"orbital-relay-{t}{ext}")
                shutil.copy2(src, dst)
                log("CROSS", f"  → {dst} ({os.path.getsize(dst)/1024:.1f}KB)")
                results.append((t, True, dst))
            else:
                log("WARN", f"  Binary not found at {src}")
                results.append((t, False, f"binary not found at {src}"))
        except subprocess.CalledProcessError as e:
            err = getattr(e, "stderr", "") or ""
            log("ERROR", f"  Cross-compile for {triple} failed: {err[-200:]}")
            results.append((t, False, f"build failed: {err[-200:]}"))
        except FileNotFoundError:
            log("ERROR", f"  Cross-compile toolchain for {triple} not installed")
            results.append((t, False, "toolchain not installed"))
    failed = [t for t, ok, _ in results if not ok]
    if failed:
        log("ERROR", f"Cross-compile failures: {', '.join(failed)}")
    return results


def phase_ir_compile(input_py, output_ir):
    """
    Generate IR from a Python source file via the irgen module.

    Args:
        input_py: path to the .py source
        output_ir: path for the generated .ir output
    """
    log("IRGEN", f"{input_py} → {output_ir}")
    run([sys.executable, "-m", "irgen", input_py, "-o", output_ir], cwd=ROOT)


def phase_llvm_codegen(input_ir, output_o):
    """
    Generate LLVM object code from IR with OLLVM obfuscation passes.

    Applies bogus control flow (BCF), control-flow flattening (FLA),
    and instruction substitution (SUB) passes.

    Args:
        input_ir: path to the .ir file
        output_o: path for the .o object file
    """
    log("LLVMGEN", f"{input_ir} → {output_o}")
    run([sys.executable, "-m", "llvmgen", input_ir, "-o", output_o,
         "--ollvm-passes", "bcf", "fla", "sub"], cwd=ROOT)
