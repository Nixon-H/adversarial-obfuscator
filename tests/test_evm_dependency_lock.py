"""Optional local-EVM dependencies must be exact and hash-locked."""
from pathlib import Path


def test_requirements_evm_exact_pins_and_hash_lock():
    req = Path("requirements-evm.txt").read_text(encoding="utf-8")
    lock = Path("requirements-evm.lock").read_text(encoding="utf-8")
    direct = [line.strip() for line in req.splitlines()
              if line.strip() and not line.lstrip().startswith("#")]
    assert direct == [
        "eth-tester==0.14.0b1",
        "py-evm==0.12.1b1",
        "py-solc-x==2.0.5",
    ]
    for package in direct:
        name, version = package.split("==", 1)
        assert f"{name}=={version}" in lock
    assert "--generate-hashes" in lock
    assert lock.count("--hash=sha256:") >= 100
    records = []
    current = ""
    for line in lock.splitlines():
        if not line or line.startswith("#"):
            continue
        if not line.startswith(" "):
            if current:
                records.append(current)
            current = line.strip()
        else:
            current += " " + line.strip()
    if current:
        records.append(current)
    bad = [line for line in records if "==" in line and "--hash=sha256:" not in line]
    assert bad == []


def test_real_evm_tests_are_dependency_gated():
    src = Path("tests/test_chain_real_evm.py").read_text(encoding="utf-8")
    assert 'pytest.importorskip("eth_tester"' in src
    assert 'pytest.importorskip("solcx"' in src
    assert "ERC721_SOURCE" in src
    assert "transferFrom(address,address,uint256)" in src
    assert "licence chain owner mismatch" in src
    assert "non-canonical ABI address word" in src
