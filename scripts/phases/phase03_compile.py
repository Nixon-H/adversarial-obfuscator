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

    A MISSING TOOLCHAIN is reported as "skipped" (ok=None), not "failed":
    the host simply cannot emit that target, which is an environment
    limitation and must not fail an otherwise good build.  Only a real
    compile error -- the toolchain ran and rejected the code -- is a
    failure (ok=False).
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
            # A toolchain that is simply not installed surfaces as a
            # CalledProcessError whose message says so.  That is a SKIP, not
            # a build failure: the host cannot emit this target, and the
            # host-target artefact is unaffected.  Only a real compile error
            # (the toolchain ran and rejected the code) fails the build.
            _low = err.lower()
            _missing = any(_m in _low for _m in (
                "not found", "no such file", "linker `", "unable to find",
                "cannot find", "command not found", "does not exist",
                "could not find", "is not installed",
                # The Rust target is installed but no cross-linker is: the
                # host `cc` tries to link foreign objects and the linker
                # rejects them.  That is a missing toolchain, not a code
                # error -- the exact failure seen for aarch64/macOS here.
                "incompatible with elf", "linking with `cc` failed",
                "linker command failed", "cannot find -l",
                "undefined reference to `__libc", "unrecognized emulation",
                # A cross-gcc present without its sysroot/libraries, and a
                # macOS target without an SDK, both report this way.
                "libraries to link with cargo", "cannot find library",
                "unable to find library", "sdk", "sysroot",
                "no such file or directory: 'x86_64-w64-mingw32",
                # The Rust target itself is not installed: rustc cannot
                # find the target's core/std crates.
                "can't find crate for `core`", "can't find crate for `std`",
                "target may not be installed", "rustup target add"))
            if _missing:
                log("WARN", f"  Cross-compile for {triple} skipped "
                            f"(toolchain not installed on this host)")
                results.append((t, None, "toolchain not installed (skipped)"))
            else:
                log("ERROR", f"  Cross-compile for {triple} failed: {err[-200:]}")
                results.append((t, False, f"build failed: {err[-200:]}"))
        except FileNotFoundError:
            log("WARN", f"  Cross-compile for {triple} skipped "
                        f"(toolchain not installed on this host)")
            results.append((t, None, "toolchain not installed (skipped)"))
    failed = [t for t, ok, _ in results if ok is False]
    skipped = [t for t, ok, _ in results if ok is None]
    if skipped:
        log("WARN", f"Cross-compile skipped (no toolchain): {', '.join(skipped)}")
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


DEFAULT_OLLVM_PASSES = ("bcf", "fla", "sub", "replay", "speculative")

# Passes whose emitted calls resolve to symbols the runtime does not provide.
# They are valid IR and assemble, but an object built with them cannot link,
# so they are never added implicitly -- only when a config asks for them.
_OLLVM_PASSES_NEEDING_RUNTIME = frozenset({"crypto_cfg", "crypto_checkpoint", "transient"})


def _ollvm_passes_from_config():
    """Read ``shadow_compiler.llvmgen.ollvm_passes`` from the default config.

    The key existed but nothing consumed it, so every build ran the same
    hardcoded three passes.  Falls back to DEFAULT_OLLVM_PASSES when the
    config is missing, unreadable, or names no usable pass.
    """
    try:
        import json

        from ..common import ROOT

        cfg_path = os.path.join(ROOT, "config", "default.json")
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        passes = (
            cfg.get("shadow_compiler", {})
            .get("llvmgen", {})
            .get("ollvm_passes", [])
        )
        cleaned = [str(p).strip().lower() for p in passes if str(p).strip()]
        if cleaned:
            return cleaned
    except Exception as e:  # config is optional; never fail the build over it
        log("LLVMGEN", f"  ollvm_passes config unreadable ({e}); using defaults")
    return list(DEFAULT_OLLVM_PASSES)


def phase_llvm_codegen(input_ir, output_o):
    """
    Generate LLVM object code from IR with OLLVM obfuscation passes.

    Applies bogus control flow (BCF), control-flow flattening (FLA),
    instruction substitution (SUB), replay poisoning and speculative
    traps.  The pass list comes from ``shadow_compiler.llvmgen.ollvm_passes``
    in config/default.json.

    Args:
        input_ir: path to the .ir file
        output_o: path for the .o object file
    """
    passes = _ollvm_passes_from_config()
    log("LLVMGEN", f"{input_ir} → {output_o} (passes: {', '.join(passes)})")
    run([sys.executable, "-m", "llvmgen", input_ir, "-o", output_o,
         "--ollvm-passes", *passes], cwd=ROOT)
