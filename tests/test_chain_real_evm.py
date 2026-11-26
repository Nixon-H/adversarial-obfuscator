"""Real local-EVM licence-chain tests.

These tests execute the repository's Solidity licence contract in py-evm via
eth-tester. The HTTP server below is only a JSON-RPC transport adapter: every
``eth_call`` is executed against real deployed contract bytecode, not a mocked
owner table. The loader helper under test is the exact source emitted by
``_licence_runtime_helpers``.

The dependencies are intentionally optional because py-evm is a large beta
dependency set. Install ``requirements-evm.txt`` to make the tests mandatory in
a development environment; otherwise pytest skips this module.
"""
import hashlib
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

eth_tester_mod = pytest.importorskip("eth_tester", reason="install requirements-evm.txt")
solcx = pytest.importorskip("solcx", reason="install requirements-evm.txt")
from eth_utils import keccak  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from obfuscator.core.pipeline import _licence_runtime_helpers  # noqa: E402
from obfuscator.licensing import canonical, chain_owner_of  # noqa: E402
from scripts.deploy_erc721_licence import ERC721_SOURCE  # noqa: E402


def _hx(data):
    if isinstance(data, str):
        return data if data.startswith("0x") else "0x" + data
    return "0x" + bytes(data).hex()


def _strip0x(value):
    value = str(value)
    return value[2:] if value.startswith("0x") else value


def _encode_call(signature, *values):
    selector = keccak(text=signature)[:4].hex()
    words = []
    for value in values:
        if isinstance(value, str) and value.startswith("0x"):
            words.append(_strip0x(value).lower().rjust(64, "0"))
        else:
            words.append(int(value).to_bytes(32, "big").hex())
    return "0x" + selector + "".join(words)


def _send(tester, sender, to, data, gas=250_000):
    tx_hash = tester.send_transaction({
        "from": sender, "to": to, "data": data, "gas": gas,
        "gas_price": 2_000_000_000, "value": 0,
    })
    return tester.get_transaction_receipt(tx_hash)


def _decode_address_word(raw):
    raw = _hx(raw)
    return "0x" + raw[-40:]


class _EVMRPCHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_POST(self):
        server = self.server
        request_id = None
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length).decode("utf-8"))
            request_id = request.get("id")
            method = request.get("method")
            if method == "eth_chainId":
                result = hex(server.chain_id)
            elif method == "eth_call":
                tx = dict((request.get("params") or [{}])[0])
                tx.setdefault("from", server.deployer)
                result = _hx(server.tester.call(tx))
                if server.sabotage == "short-owner-word":
                    result = "0x" + "00" * 20
                elif server.sabotage == "noncanonical-owner-word":
                    result = "0x" + "11" * 12 + "00" * 20
            else:
                raise ValueError("unsupported test method: " + str(method))
            response = {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
            if server.sabotage == "wrong-id":
                response["id"] = 999
            elif server.sabotage == "wrong-version":
                response["jsonrpc"] = "1.0"
            body = json.dumps(response, separators=(",", ":"))
        except Exception as exc:
            body = json.dumps({"jsonrpc": "2.0", "id": request_id,
                               "error": {"code": -32000, "message": str(exc)}},
                              separators=(",", ":"))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))


@pytest.fixture(scope="module")
def local_evm():
    versions = solcx.get_installed_solc_versions()
    if not any(str(v) == "0.8.20" for v in versions):
        pytest.skip("solc 0.8.20 is not installed; install it with py-solc-x")
    compiled = solcx.compile_source(
        ERC721_SOURCE, output_values=["abi", "bin"], solc_version="0.8.20")
    key = "<stdin>:LicenceERC721"
    if key not in compiled:
        key = next(iter(compiled))
    tester = eth_tester_mod.EthereumTester(
        backend=eth_tester_mod.PyEVMBackend())
    accounts = tester.get_accounts()
    deployer, customer, attacker, receiver = accounts[:4]
    deploy_tx = tester.send_transaction({
        "from": deployer, "data": _hx(compiled[key]["bin"]),
        "gas": 3_500_000, "gas_price": 2_000_000_000, "value": 0,
    })
    deploy_receipt = tester.get_transaction_receipt(deploy_tx)
    assert int(deploy_receipt.get("status", 0)) == 1
    contract = deploy_receipt["contract_address"]
    mint = _encode_call("mint(address,uint256)", customer, 1)
    mint_receipt = _send(tester, deployer, contract, mint)
    assert int(mint_receipt.get("status", 0)) == 1
    mint2 = _encode_call("mint(address,uint256)", customer, 2)
    mint2_receipt = _send(tester, deployer, contract, mint2)
    assert int(mint2_receipt.get("status", 0)) == 1
    mint3 = _encode_call("mint(address,uint256)", customer, 3)
    mint3_receipt = _send(tester, deployer, contract, mint3)
    assert int(mint3_receipt.get("status", 0)) == 1

    server = ThreadingHTTPServer(("127.0.0.1", 0), _EVMRPCHandler)
    server.tester = tester
    server.deployer = deployer
    server.chain_id = int(tester.backend.chain.chain_id)
    server.sabotage = None
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    rpc_url = "http://127.0.0.1:%d" % server.server_address[1]
    state = {
        "tester": tester, "server": server, "rpc_url": rpc_url,
        "chain_id": server.chain_id, "contract": contract,
        "deployer": deployer, "customer": customer,
        "attacker": attacker, "receiver": receiver,
        "token_id": 1, "manipulation_token_id": 2,
        "artifact_token_id": 3,
        "bytecode_sha256": hashlib.sha256(
            bytes.fromhex(compiled[key]["bin"])).hexdigest(),
    }
    yield state
    server.shutdown()
    server.server_close()


def _payload(state, *, owner=None, expires_at=None):
    return {
        "schema": 1,
        "licence_id": "L-real-evm",
        "customer": "local-evm-test",
        "issued_at": int(time.time()) - 10,
        "expires_at": int(expires_at if expires_at is not None
                         else time.time() + 3600),
        "features": [],
        "key_material": "ab" * 32,
        "chain": {
            "rpc": state["rpc_url"],
            "contract": state["contract"],
            "token_id": str(state["token_id"]),
            "owner": str(owner or state["customer"]),
            "chain_id": str(state["chain_id"]),
        },
    }


def _loader_namespace(payload):
    token_hash = hashlib.sha256(canonical(payload)).hexdigest()
    src = _licence_runtime_helpers(token_hash, True, True)
    ns = {"_nixon_ハッシュ해시": hashlib}
    exec(compile(src, "<real-evm-loader>", "exec"), ns)
    return ns


def _write_token(tmp_path, payload):
    path = tmp_path / ("licence-%d.json" % time.time_ns())
    path.write_text(json.dumps({"payload": payload, "sig": "00"}),
                    encoding="utf-8")
    return path


def _run_loader(tmp_path, monkeypatch, payload):
    ns = _loader_namespace(payload)
    monkeypatch.setenv("NIXON_LICENCE", str(_write_token(tmp_path, payload)))
    return ns["_nx_licence_payload"]()


def test_real_evm_contract_owner_accepted_by_emitted_loader(local_evm, tmp_path,
                                                            monkeypatch):
    payload = _payload(local_evm)
    owner = chain_owner_of(local_evm["rpc_url"], local_evm["contract"],
                           local_evm["manipulation_token_id"], local_evm["chain_id"])
    assert owner.lower() == str(local_evm["customer"]).lower()
    assert _run_loader(tmp_path, monkeypatch, payload) == payload


def test_real_evm_transfer_invalidates_original_owner(local_evm, tmp_path,
                                                      monkeypatch, capsys):
    state = local_evm
    transfer = _encode_call("transferFrom(address,address,uint256)",
                            state["customer"], state["receiver"],
                            state["token_id"])
    receipt = _send(state["tester"], state["customer"], state["contract"],
                    transfer)
    assert int(receipt.get("status", 0)) == 1
    owner = chain_owner_of(state["rpc_url"], state["contract"],
                           state["token_id"], state["chain_id"])
    assert owner.lower() == str(state["receiver"]).lower()

    payload = _payload(state, owner=state["customer"])
    with pytest.raises(SystemExit):
        _run_loader(tmp_path, monkeypatch, payload)
    assert "licence chain owner mismatch" in capsys.readouterr().err

    burn = _encode_call("burn(uint256)", state["token_id"])
    burn_receipt = _send(state["tester"], state["receiver"], state["contract"],
                         burn)
    assert int(burn_receipt.get("status", 0)) == 1
    with pytest.raises(RuntimeError):
        chain_owner_of(state["rpc_url"], state["contract"], state["token_id"],
                       state["chain_id"])
    with pytest.raises(SystemExit):
        _run_loader(tmp_path, monkeypatch, payload)
    assert "licence chain verification failed" in capsys.readouterr().err


def test_real_evm_wrong_chain_and_expiry_fail_closed(local_evm, tmp_path,
                                                     monkeypatch, capsys):
    wrong_chain_payload = _payload(local_evm)
    wrong_chain_payload["chain"]["chain_id"] = str(local_evm["chain_id"] + 1)
    with pytest.raises(SystemExit):
        _run_loader(tmp_path, monkeypatch, wrong_chain_payload)
    assert "licence chain verification failed" in capsys.readouterr().err

    expired_payload = _payload(local_evm, expires_at=int(time.time()) - 1)
    with pytest.raises(SystemExit):
        _run_loader(tmp_path, monkeypatch, expired_payload)
    assert "licence expired" in capsys.readouterr().err


@pytest.mark.nixon_timeout(1900)
def test_real_evm_full_artifact_loader_transfer_enforcement(local_evm, tmp_path):
    """Build and run the real emitted artifact against the real local EVM.

    This is intentionally slower than the helper-level tests: it proves the
    complete path from contract state through the produced loader process.
    """
    import subprocess
    import sys

    from obfuscator.licensing import (
        Licence, issue, private_key_from_hex, public_key_hex)

    state = local_evm
    seed = "33" * 32
    issuer_key = private_key_from_hex(seed)
    public_key = public_key_hex(issuer_key)
    now = time.time()
    licence = Licence(
        licence_id="L-real-evm-artifact",
        customer="local-evm-test",
        issued_at=now - 10,
        expires_at=now + 3600,
        features=("pro",),
        key_material="cd" * 32,
        chain={
            "rpc": state["rpc_url"],
            "contract": state["contract"],
            "token_id": str(state["artifact_token_id"]),
            "owner": str(state["customer"]),
            "chain_id": str(state["chain_id"]),
        },
        key_version=1,
        nonce="artifact-real-evm-nonce",
    )
    token_path = tmp_path / "artifact.licence"
    token_path.write_text(issue(licence, issuer_key), encoding="utf-8")
    payload_path = tmp_path / "payload.py"
    payload_path.write_text('print("REAL_EVM_ARTIFACT_RAN")\n', encoding="utf-8")

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build_env = dict(os.environ)
    build_env.update({
        "PYTHONPATH": repo,
        "NIXON_LOG_REDIRECT": "0",
        "NIXON_LICENCE_PUBLIC_KEY": public_key,
    })
    build = subprocess.run(
        [sys.executable, "-m", "obfuscator.core.pipeline", "build",
         str(payload_path), "--skip-cloud", "--licence",
         "token=" + str(token_path), "env-only", "chain"],
        cwd=tmp_path, env=build_env, capture_output=True, text=True,
        timeout=1800)
    assert build.returncode == 0, build.stderr[-1200:] + build.stdout[-1200:]

    artifact = None
    for root, _dirs, files in os.walk(tmp_path):
        for name in files:
            if name.endswith("_protected.py"):
                artifact = os.path.join(root, name)
                break
        if artifact:
            break
    assert artifact, "no protected artifact produced"

    run_env = dict(os.environ)
    run_env.update({
        "NIXON_LOG_REDIRECT": "0",
        "NIXON_TRACEBACKS": "1",
        "NIXON_LICENCE": str(token_path),
    })
    first = subprocess.run([sys.executable, artifact], cwd=tmp_path,
                           env=run_env, capture_output=True, text=True,
                           timeout=120)
    assert first.returncode == 0, first.stderr[-1200:]
    assert "REAL_EVM_ARTIFACT_RAN" in first.stdout

    transfer = _encode_call("transferFrom(address,address,uint256)",
                            state["customer"], state["receiver"],
                            state["artifact_token_id"])
    receipt = _send(state["tester"], state["customer"], state["contract"],
                    transfer)
    assert int(receipt.get("status", 0)) == 1

    second = subprocess.run([sys.executable, artifact], cwd=tmp_path,
                            env=run_env, capture_output=True, text=True,
                            timeout=120)
    assert second.returncode != 0
    assert "licence chain owner mismatch" in (second.stdout + second.stderr)


def test_real_evm_rpc_response_manipulation_fails_closed(local_evm):
    server = local_evm["server"]
    try:
        server.sabotage = "wrong-id"
        with pytest.raises(RuntimeError, match="mismatched JSON-RPC envelope"):
            chain_owner_of(local_evm["rpc_url"], local_evm["contract"],
                           local_evm["manipulation_token_id"], local_evm["chain_id"])
        server.sabotage = "wrong-version"
        with pytest.raises(RuntimeError, match="mismatched JSON-RPC envelope"):
            chain_owner_of(local_evm["rpc_url"], local_evm["contract"],
                           local_evm["manipulation_token_id"], local_evm["chain_id"])
        server.sabotage = "short-owner-word"
        with pytest.raises(RuntimeError, match="malformed ABI address word"):
            chain_owner_of(local_evm["rpc_url"], local_evm["contract"],
                           local_evm["manipulation_token_id"], local_evm["chain_id"])
        server.sabotage = "noncanonical-owner-word"
        with pytest.raises(RuntimeError, match="non-canonical ABI address word"):
            chain_owner_of(local_evm["rpc_url"], local_evm["contract"],
                           local_evm["manipulation_token_id"], local_evm["chain_id"])
    finally:
        server.sabotage = None
