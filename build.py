#!/usr/bin/env python3
"""
Nixon Build Pipeline — Obfuscate → Config → Compile → Package

Usage:
    python3 build.py --payload myscript.py [options]

    python3 build.py --payload myscript.py --cf-token X --cf-account Y
    python3 build.py --payload myscript.py --skip-obfuscate --skip-relay
    python3 build.py --payload myscript.py --cross win,linux
"""

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(ROOT, "build")
RELAY_DIR = os.path.join(ROOT, "orbital-relay")
OBFUSCATOR = os.path.join(ROOT, "15(14).py")
ORBITAL_RELAY_PY = os.path.join(ROOT, "orbital-relay.py")
CONFIG_FILE = os.path.join(ROOT, "orbital-relay.json")


def log(phase, msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{phase:>12}] {msg}")


def run(cmd, cwd=None, check=True):
    log("CMD", " ".join(cmd) if isinstance(cmd, list) else cmd)
    return subprocess.run(cmd, cwd=cwd or ROOT, check=check, capture_output=True, text=True)


def phase_obfuscate(payload, output, opts):
    log("OBFUSCATE", f"{payload} → {output}")
    cmd = [sys.executable, OBFUSCATOR, "obfuscate", payload, "-o", output]
    if opts.cfg_flatten: cmd.append("--cfg-flatten")
    if opts.opaque_predicates: cmd.append("--opaque-predicates")
    if opts.bogus_exceptions: cmd.append("--bogus-exceptions")
    if opts.mba_subs: cmd.append("--mba-subs")
    if opts.fragment_strings: cmd.append("--fragment-strings")
    if opts.unicode_ids: cmd.append("--unicode-ids")
    result = run(cmd)
    if not os.path.exists(output):
        log("ERROR", "Obfuscation produced no output — check 15(14).py")
        sys.exit(1)
    size = os.path.getsize(output)
    log("OBFUSCATE", f"Done: {size/1024:.1f}KB (was {os.path.getsize(payload)/1024:.1f}KB)")


def phase_generate_config(opts):
    log("CONFIG", "Generating orbital-relay.json")
    cfg = {
        "cloudflare": {
            "api_token": opts.cf_token or "",
            "account_id": opts.cf_account or "",
        },
        "worker": {
            "mode": opts.mode or "socks",
            "auth_token": secrets.token_hex(16),
            "socks_password": secrets.token_urlsafe(24),
            "compatibility_date": "2023-09-04",
            "compatibility_flags": ["nodejs_compat"],
        },
        "client": {
            "bind_host": "127.0.0.1",
            "base_port": 1080,
            "auto_random_ports": True,
            "cf_override_ip": "",
            "cf_hostnames": [],
            "handshake_timeout": 5.0,
            "use_doh": True,
            "doh_timeout": 5.0,
            "relay": {
                "enabled": False,
                "url": "",
                "auth_token": "",
                "socks_password": "",
            },
        },
        "cached_services": [],
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    log("CONFIG", f"Written to {CONFIG_FILE}")

    # Update Makefile config if needed (future: template-based)
    return cfg


def phase_compile_relay():
    log("RELAY", "Compiling orbital-relay (Rust)...")
    result = run(["make", "relay"])
    binary = os.path.join(BUILD_DIR, "orbital-relay")
    if not os.path.exists(binary):
        log("ERROR", "Rust build failed — binary not found")
        sys.exit(1)
    size = os.path.getsize(binary)
    log("RELAY", f"Done: {binary} ({size/1024:.1f}KB, stripped)")


def phase_cross_compile(targets_str):
    targets = [t.strip() for t in targets_str.split(",") if t.strip()]
    target_map = {
        "win": "x86_64-pc-windows-gnu",
        "win-arm": "aarch64-pc-windows-msvc",
        "linux": "x86_64-unknown-linux-gnu",
        "linux-arm": "aarch64-unknown-linux-gnu",
        "macos": "x86_64-apple-darwin",
        "macos-arm": "aarch64-apple-darwin",
    }

    for t in targets:
        triple = target_map.get(t, t)
        log("CROSS", f"Building for {triple}...")
        try:
            result = run(["cargo", "build", "--release", "--target", triple], cwd=RELAY_DIR)
            src = os.path.join(RELAY_DIR, "target", triple, "release", "orbital-relay")
            if os.path.exists(src):
                ext = ".exe" if "windows" in triple else ""
                dst = os.path.join(BUILD_DIR, f"orbital-relay-{t}{ext}")
                shutil.copy2(src, dst)
                log("CROSS", f"  → {dst} ({os.path.getsize(dst)/1024:.1f}KB)")
            else:
                log("WARN", f"  Binary not found at {src}")
        except subprocess.CalledProcessError as e:
            log("WARN", f"  Cross-compile for {triple} failed: {e.stderr[-200:]}")
        except FileNotFoundError:
            log("WARN", f"  Cross-compile toolchain for {triple} not installed")


def phase_package(payload, obfuscated_output, obfuscated_name, opts):
    log("PACKAGE", "Packaging build artifacts...")
    os.makedirs(BUILD_DIR, exist_ok=True)

    # Copy obfuscated payload
    if os.path.exists(obfuscated_output):
        dst = os.path.join(BUILD_DIR, obfuscated_name)
        shutil.copy2(obfuscated_output, dst)
        log("PACKAGE", f"  Payload: {dst}")
        os.remove(obfuscated_output)

    # Copy original (for reference)
    if opts.include_original:
        dst = os.path.join(BUILD_DIR, f"original_{os.path.basename(payload)}")
        shutil.copy2(payload, dst)
        log("PACKAGE", f"  Original: {dst}")

    # Copy config
    if os.path.exists(CONFIG_FILE):
        dst = os.path.join(BUILD_DIR, "orbital-relay.json")
        shutil.copy2(CONFIG_FILE, dst)
        log("PACKAGE", f"  Config: {dst}")

    log("PACKAGE", f"  Build dir: {BUILD_DIR}")
    for f in sorted(os.listdir(BUILD_DIR)):
        fp = os.path.join(BUILD_DIR, f)
        if os.path.isfile(fp) and not f.endswith(".so"):
            log("PACKAGE", f"    {f:40s} {os.path.getsize(fp)/1024:.1f}KB")


def main():
    parser = argparse.ArgumentParser(
        description="Nixon Build Pipeline — Obfuscate → Config → Compile → Package",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 build.py --payload myscript.py
  python3 build.py --payload myscript.py --cf-token X --cf-account Y
  python3 build.py --payload myscript.py --skip-obfuscate --skip-relay
  python3 build.py --payload myscript.py --cross win,linux,linux-arm
        """,
    )
    parser.add_argument("--payload", required=True, help="Python script to obfuscate")
    parser.add_argument("-o", "--output", help="Output path for obfuscated script")
    parser.add_argument("--cf-token", help="Cloudflare API token")
    parser.add_argument("--cf-account", help="Cloudflare Account ID")
    parser.add_argument("--mode", choices=["socks", "http"], default="socks", help="Relay mode")
    parser.add_argument("--cross", help="Cross-compile targets: win,linux,macos,linux-arm")
    parser.add_argument("--skip-obfuscate", action="store_true", help="Skip AST obfuscation")
    parser.add_argument("--skip-relay", action="store_true", help="Skip Rust relay build")
    parser.add_argument("--include-original", action="store_true", help="Include original payload in build/")
    parser.add_argument("--cfg-flatten", action="store_true", default=True, help=argparse.SUPPRESS)
    parser.add_argument("--no-cfg-flatten", action="store_false", dest="cfg_flatten")
    parser.add_argument("--opaque-predicates", action="store_true", default=True, help=argparse.SUPPRESS)
    parser.add_argument("--no-opaque-predicates", action="store_false", dest="opaque_predicates")
    parser.add_argument("--bogus-exceptions", action="store_true", default=True, help=argparse.SUPPRESS)
    parser.add_argument("--no-bogus-exceptions", action="store_false", dest="bogus_exceptions")
    parser.add_argument("--mba-subs", action="store_true", default=True, help=argparse.SUPPRESS)
    parser.add_argument("--no-mba-subs", action="store_false", dest="mba_subs")
    parser.add_argument("--fragment-strings", action="store_true", default=True, help=argparse.SUPPRESS)
    parser.add_argument("--no-fragment-strings", action="store_false", dest="fragment_strings")
    parser.add_argument("--unicode-ids", action="store_true", default=True, help=argparse.SUPPRESS)
    parser.add_argument("--no-unicode-ids", action="store_false", dest="unicode_ids")

    opts = parser.parse_args()

    if not os.path.exists(opts.payload):
        log("ERROR", f"Payload not found: {opts.payload}")
        sys.exit(1)

    os.makedirs(BUILD_DIR, exist_ok=True)

    base = os.path.splitext(os.path.basename(opts.payload))[0]
    obfuscated_name = f"{base}_obfuscated.py"
    obfuscated_output = opts.output or os.path.join(ROOT, f".build_tmp_{obfuscated_name}")
    obfuscated_output = os.path.abspath(obfuscated_output)

    # Phase 1: Obfuscate
    if not opts.skip_obfuscate:
        phase_obfuscate(opts.payload, obfuscated_output, opts)
    else:
        log("SKIP", "Obfuscation skipped")
        shutil.copy2(opts.payload, obfuscated_output)

    # Phase 2: Generate config
    phase_generate_config(opts)

    # Phase 3: Compile Rust relay
    if not opts.skip_relay:
        phase_compile_relay()
    else:
        log("SKIP", "Rust relay build skipped")

    # Phase 4: Cross-compile
    if opts.cross:
        phase_cross_compile(opts.cross)

    # Phase 5: Package
    phase_package(opts.payload, obfuscated_output, obfuscated_name, opts)

    log("DONE", "Pipeline complete")
    print(f"\n  {'='*50}")
    print(f"  Build artifacts: {BUILD_DIR}/")
    print(f"  Run: build/orbital-relay --help")
    print(f"  {'='*50}\n")


if __name__ == "__main__":
    main()
