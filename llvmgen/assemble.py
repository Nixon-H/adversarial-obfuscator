import subprocess
import tempfile
import os


def assemble(llvm_ir: str, output_path: str) -> str:
    llc_cmd = os.environ.get("LLC", "llc")
    as_cmd = os.environ.get("AS", "as")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ll", delete=False, prefix="nixon_"
    ) as f:
        ir_path = f.name
        f.write(llvm_ir)

    try:
        asm_path = ir_path.replace(".ll", ".s")

        llc_result = subprocess.run(
            [llc_cmd, ir_path, "-o", asm_path],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if llc_result.returncode != 0:
            error_msg = llc_result.stderr.strip()
            raise RuntimeError(
                f"LLVM assembly failed (llc):\n{error_msg}"
            )

        as_result = subprocess.run(
            [as_cmd, asm_path, "-o", output_path],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if as_result.returncode != 0:
            error_msg = as_result.stderr.strip()
            raise RuntimeError(
                f"Assembly failed (as):\n{error_msg}"
            )

        return output_path

    except FileNotFoundError as e:
        missing = llc_cmd if "llc" in str(e) else as_cmd
        raise RuntimeError(
            f"Required tool not found: {missing}. "
            f"Install LLVM toolchain: apt install llvm-dev"
        ) from e

    except subprocess.TimeoutExpired:
        raise RuntimeError("Compilation timed out (120s)")

    finally:
        for p in [ir_path, ir_path.replace(".ll", ".s")]:
            try:
                if os.path.exists(p):
                    os.unlink(p)
            except OSError:
                pass
