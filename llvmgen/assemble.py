import os
import shutil
import subprocess
import sys
import tempfile


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
        # On failure the .ll is the only thing that says WHICH construct llc
        # rejected -- and it used to be deleted, so the error named a file
        # that no longer existed.  Keep it (and the .s) for any non-zero
        # exit, and say where it went.
        _failed = sys.exc_info()[0] is not None
        _kept = []
        if _failed:
            try:
                for _p in (ir_path, ir_path.replace(".ll", ".s")):
                    if os.path.exists(_p):
                        _dest = os.path.join(tempfile.gettempdir(),
                                             "nixon_failed_" + os.path.basename(_p))
                        shutil.copyfile(_p, _dest)
                        _kept.append(_dest)
            except OSError:
                pass
            if _kept:
                sys.stderr.write("preserved IR: %s\n" % ", ".join(_kept))
        for p in [ir_path, ir_path.replace(".ll", ".s")]:
            try:
                if os.path.exists(p):
                    os.unlink(p)
            except OSError:
                pass
