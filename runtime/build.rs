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

    let cc = std::env::var("CC").unwrap_or_else(|_| "gcc".to_string());
    let status = Command::new(&cc)
        .args(&[
            "-c",
            "-O2",
            "-msse4.1",
            "-fPIC",
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
    let ar_status = Command::new("ar")
        .args(&["rcs", &lib_path.to_string_lossy(), &obj_path.to_string_lossy()])
        .status()
        .expect("failed to create static lib");

    if !ar_status.success() {
        panic!("ar failed");
    }

    println!("cargo:rustc-link-search=native={}", out_dir);
    println!("cargo:rustc-link-lib=static=simd_vm");
}
