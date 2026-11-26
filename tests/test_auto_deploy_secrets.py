"""Generated deployment keys must not be printed or left world-readable."""
import os
import re
import stat

from obfuscator.core import pipeline


def test_generated_private_key_is_written_0600_not_printed(monkeypatch, capsys):
    monkeypatch.setattr(pipeline, "compile_solidity", lambda *a, **k: {
        "abi": [], "bytecode": "00", "compiler_version": "test",
    })
    monkeypatch.setattr(pipeline, "deploy_contract", lambda *a, **k: "0xcontract")
    address, rpc = pipeline.auto_deploy_contract("https://rpc.example?token=secret")
    output = capsys.readouterr().out
    assert address == "0xcontract"
    assert rpc.startswith("https://")
    assert not re.search(r"0x[0-9a-fA-F]{64}", output)
    assert "token=secret" not in output
    match = re.search(r"Deployment key written to: (.+)", output)
    assert match, output
    key_path = match.group(1).strip().removesuffix(" (0600)")
    try:
        assert stat.S_IMODE(os.stat(key_path).st_mode) == 0o600
        assert re.fullmatch(r"0x[0-9a-fA-F]{64}", open(key_path).read().strip())
    finally:
        os.unlink(key_path)
