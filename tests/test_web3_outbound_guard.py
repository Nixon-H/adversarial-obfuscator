"""Web3 JSON-RPC must use the same pinned SSRF guard as other outbound calls."""
import sys
import types

import pytest

from obfuscator.core import pipeline


def _install_web3_stub_when_optional_dependency_is_absent(monkeypatch):
    try:
        import web3.providers.rpc  # noqa: F401
        return
    except ModuleNotFoundError as exc:
        if exc.name != "web3":
            raise

    web3_mod = types.ModuleType("web3")
    providers_mod = types.ModuleType("web3.providers")
    rpc_mod = types.ModuleType("web3.providers.rpc")

    class HTTPProvider:
        def __init__(self, endpoint_uri):
            self.endpoint_uri = endpoint_uri

        def get_request_headers(self):
            return {}

        def make_request(self, method, params):
            return self._make_request(method, b"{}")

    rpc_mod.HTTPProvider = HTTPProvider
    providers_mod.rpc = rpc_mod
    web3_mod.providers = providers_mod
    monkeypatch.setitem(sys.modules, "web3", web3_mod)
    monkeypatch.setitem(sys.modules, "web3.providers", providers_mod)
    monkeypatch.setitem(sys.modules, "web3.providers.rpc", rpc_mod)


def test_web3_provider_rejects_reserved_endpoint_before_network(monkeypatch):
    _install_web3_stub_when_optional_dependency_is_absent(monkeypatch)
    provider = pipeline._pinned_web3_provider("https://127.0.0.1:8545")
    calls = []

    def guarded(url, **kwargs):
        calls.append(url)
        raise ValueError("reserved address")

    monkeypatch.setattr(pipeline, "checked_urlopen", guarded)
    with pytest.raises(ValueError, match="reserved"):
        provider.make_request("web3_clientVersion", [])
    assert calls == ["https://127.0.0.1:8545"]
