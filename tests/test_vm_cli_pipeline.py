"""Regression tests for the `python -m vm` CLI pipeline (HIGH finding:
`vm run` used to execute the container's ciphertext without ever
decrypting it, so compile output could never run).

Covers:
- compile writes an ENCRYPTED container and never persists the seed
- run decrypts with an out-of-band key and executes
- run fails closed when no key is available
- mutate operates on plaintext (decrypt -> mutate -> re-encrypt) and the
  result is still runnable
- the register allocator never returns a reserved register (FLAGS/PC/SP)
"""
import json

import pytest

from vm.__main__ import main as vm_main
from vm.bytecode_compiler import compile_to_bytecode, encrypt_bytecode, decrypt_bytecode, _value_to_reg
from vm.interpreter import VMInterpreter

SEED = "00" * 16


def _compile(tmp_path, name="bc.json"):
    source = tmp_path / "input.py"
    source.write_text("def main():\n    return 42\n")
    out = str(tmp_path / name)
    key_out = str(tmp_path / (name + ".key"))
    rc = vm_main(["compile", str(source), "-o", out,
                  "--functions", "main", "--seed", SEED, "--key-out", key_out])
    assert rc == 0
    return out, key_out


def test_compile_writes_encrypted_container_and_no_seed(tmp_path):
    out, key_out = _compile(tmp_path)
    with open(out) as f:
        container = json.load(f)
    assert container["encrypted"] is True
    # The ciphertext must not equal the plaintext bytecode.
    assert len(container["bytecode"]) > 0
    with open(key_out) as f:
        sidecar = f.read()
    assert "key=" in sidecar
    assert "seed=" not in sidecar, "seed must never be persisted (seed -> key = self-contained break)"


def test_run_decrypts_and_executes(tmp_path):
    out, key_out = _compile(tmp_path)
    rc = vm_main(["run", out, "--key-file", key_out])
    assert rc == 0


def test_run_fails_closed_without_key(tmp_path):
    out, _key_out = _compile(tmp_path)
    with pytest.raises(SystemExit):
        vm_main(["run", out, "--key-file", str(tmp_path / "missing.key")])


def test_compile_requires_seed_or_key_out(tmp_path):
    out = str(tmp_path / "unrecoverable.json")
    with pytest.raises(SystemExit, match="--seed or --key-out"):
        vm_main(["compile", "examples/hello.py", "-o", out,
                 "--functions", "main"])
    assert not __import__("os").path.exists(out)


def test_compile_with_key_out_only_is_recoverable(tmp_path):
    out = str(tmp_path / "random-key.json")
    key_out = str(tmp_path / "random-key.key")
    source = tmp_path / "input.py"
    source.write_text("def main():\n    return 42\n")
    assert vm_main(["compile", str(source), "-o", out,
                    "--functions", "main", "--key-out", key_out]) == 0
    assert vm_main(["run", out, "--key-file", key_out]) == 0


def test_run_wrong_key_returns_clear_authentication_error(tmp_path, capsys):
    out, _key_out = _compile(tmp_path)
    assert vm_main(["run", out, "--key", "ff" * 32]) == 1
    assert "authentication failed" in capsys.readouterr().err.lower()


def test_run_tampered_container_returns_clear_authentication_error(tmp_path, capsys):
    out, key_out = _compile(tmp_path)
    with open(out) as f:
        container = json.load(f)
    ciphertext = bytearray.fromhex(container["bytecode"])
    ciphertext[17] ^= 1
    container["bytecode"] = ciphertext.hex()
    with open(out, "w") as f:
        json.dump(container, f)
    assert vm_main(["run", out, "--key-file", key_out]) == 1
    assert "authentication failed" in capsys.readouterr().err.lower()


def test_compile_rejects_missing_target_without_writing_container(tmp_path):
    out = str(tmp_path / "missing-target.json")
    with pytest.raises(SystemExit):
        vm_main(["compile", "examples/hello.py", "-o", out,
                 "--functions", "does_not_exist", "--seed", SEED])
    assert not __import__("os").path.exists(out)


def test_compile_and_run_multiple_functions(tmp_path, capsys):
    src = tmp_path / "multi.py"
    src.write_text("def one():\n    return 11\ndef two():\n    return 22\n")
    out = str(tmp_path / "multi.json")
    key_out = str(tmp_path / "multi.key")
    assert vm_main(["compile", str(src), "-o", out, "--functions", "one,two",
                    "--seed", SEED, "--key-out", key_out]) == 0
    with open(out) as f:
        container = json.load(f)
    assert container["num_functions"] == 2
    assert set(container["function_offsets"]) == {"one", "two"}
    assert container["function_offsets"]["one"] == 0
    assert container["function_offsets"]["two"] > 0
    capsys.readouterr()
    assert vm_main(["run", out, "--key-file", key_out, "--trace"]) == 0
    output = capsys.readouterr().out
    assert "Function one: result=11" in output
    assert "Function two: result=22" in output


def test_mutate_roundtrip_stays_runnable(tmp_path):
    out, key_out = _compile(tmp_path)
    mutated = str(tmp_path / "bc2.json")
    rc = vm_main(["mutate", out, "-o", mutated, "--seed", SEED, "--key-file", key_out])
    assert rc == 0
    with open(mutated) as f:
        container = json.load(f)
    assert container["encrypted"] is True
    rc = vm_main(["run", mutated, "--key-file", key_out])
    assert rc == 0


def test_mutate_roundtrip_preserves_execution_result(tmp_path, capsys):
    import ast

    src = tmp_path / "input.py"
    src.write_text("def f():\n    return 150 + 150\n")
    out = str(tmp_path / "bc.json")
    key_out = str(tmp_path / "key")
    assert vm_main(["compile", str(src), "-o", out, "--functions", "f",
                    "--seed", SEED, "--key-out", key_out]) == 0
    mutated = str(tmp_path / "mutated.json")
    assert vm_main(["mutate", out, "-o", mutated, "--seed", SEED,
                    "--key-file", key_out]) == 0
    capsys.readouterr()
    assert vm_main(["run", mutated, "--key-file", key_out, "--trace"]) == 0
    output = capsys.readouterr().out
    line = next(line for line in output.splitlines()
                if line.startswith("Final registers:"))
    regs = ast.literal_eval(line.split(":", 1)[1].strip())
    assert regs[1] == 300


def test_encrypt_decrypt_roundtrip_is_exact():
    bc = bytes(range(256)) * 2
    key = bytes(range(32))
    enc = encrypt_bytecode(bytearray(bc), key)
    assert bytes(enc) != bc
    dec = decrypt_bytecode(enc, key)
    assert bytes(dec) == bc


def test_register_allocator_never_uses_reserved_registers():
    class _Rng:
        def __init__(self):
            self.state = 0
        def next(self):
            self.state = (self.state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
            return self.state >> 33
        def randint(self, a, b):
            return a + self.next() % (b - a + 1)

    class _V:
        def __init__(self, i):
            self.id = i

    rng = _Rng()
    seen = {_value_to_reg(_V(i), rng) for i in range(500)}
    seen |= {rng.randint(1, 12) for _ in range(500)}
    # Reserved: FLAGS=13, PC=14, SP=15 (interpreter.py). Allocatable: 1..12.
    assert seen <= set(range(1, 13)), f"allocator produced reserved register: {seen - set(range(1, 13))}"
    assert 14 not in seen and 15 not in seen and 13 not in seen


def test_compiled_bytecode_runs_to_halt():
    import irgen.compile as ir_compile
    module = ir_compile.compile_py_to_ir("def main():\n    return 42\n")
    func = next(f for f in module.functions if f.name == "main")
    bc = compile_to_bytecode(func, None, bytes.fromhex(SEED))
    key = bytes(range(32))
    enc = encrypt_bytecode(bytearray(bc), key)
    dec = decrypt_bytecode(enc, key)
    vm = VMInterpreter(bytes(dec))
    result = vm.run(max_steps=100000)
    assert result.get("halted", False)
