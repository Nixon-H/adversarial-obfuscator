use std::path::Path;
use std::process::Command;

fn main() {
    let native_dir = match Path::new("../native").canonicalize() {
        Ok(p) => p,
        Err(_) => return,
    };
    let simd_src = native_dir.join("simd_vm.c");
    if !simd_src.exists() {
        return;
    }

    println!("cargo:rerun-if-changed={}", simd_src.display());

    let out_dir = std::env::var("OUT_DIR").unwrap();
    let obj_path = Path::new(&out_dir).join("simd_vm.o");

    let target = std::env::var("TARGET").unwrap_or_default();
    let (default_cc, default_ar, x86_sse) = if target.starts_with("x86_64-pc-windows-gnu") {
        ("x86_64-w64-mingw32-gcc", "x86_64-w64-mingw32-ar", true)
    } else if target.starts_with("aarch64-unknown-linux-gnu") {
        ("aarch64-linux-gnu-gcc", "aarch64-linux-gnu-ar", false)
    } else if target.contains("musl") {
        ("musl-gcc", "ar", target.starts_with("x86_64"))
    } else {
        ("gcc", "ar", target.starts_with("x86_64"))
    };
    let cc = std::env::var("CC").unwrap_or_else(|_| default_cc.to_string());
    let ar = std::env::var("AR").unwrap_or_else(|_| default_ar.to_string());
    let mut compile = Command::new(&cc);
    compile.args(["-c", "-O2", "-fPIC"]);
    if x86_sse {
        compile.arg("-msse4.1");
    }
    let status = compile
        .args([
            "-o",
            &obj_path.to_string_lossy(),
            &simd_src.to_string_lossy(),
        ])
        .status()
        .expect("failed to compile simd_vm.c");

    if !status.success() {
        panic!("simd_vm.c compilation failed");
    }

    let lib_path = Path::new(&out_dir).join("libsimd_vm.a");
    let ar_status = Command::new(&ar)
        .args(["rcs", &lib_path.to_string_lossy(), &obj_path.to_string_lossy()])
        .status()
        .expect("failed to create static lib");

    if !ar_status.success() {
        panic!("ar failed");
    }

    println!("cargo:rustc-link-search=native={}", out_dir);
    println!("cargo:rustc-link-lib=static=simd_vm");
    println!("cargo:archive={}", lib_path.display());
}
