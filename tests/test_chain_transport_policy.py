"""Licence-chain transport policy: local simulation allowed, production HTTPS.

The on-chain licence check needs a node. Production must speak HTTPS, because a
plaintext RPC endpoint would let a network attacker rewrite the `eth_call`
result and the ownership check would mean nothing.

But a local chain speaks PLAIN HTTP (Anvil: http://127.0.0.1:8545), and the
previous rule was literally `rpc_url.startswith("https://")`. That made the
entire on-chain path untestable without spending real gas -- so it went
unbenchmarked, and the benchmark requirement ("simulate the chain locally")
could not be met at all.

The fix admits plain HTTP ONLY for a loopback LITERAL. These tests pin both
directions, because a policy that only gets tested in the permissive direction
is how an SSRF-shaped hole gets introduced.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from obfuscator.licensing import chain_owner_of  # noqa: E402

ADDR = "0x" + "ab" * 20


# ── the loopback policy, tested through the real entry point ──────────────

@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8545",
    "http://127.0.0.5:8545",
    "http://127.1.2.3:8545",
    "http://[::1]:8545",
])
def test_loopback_http_is_accepted_for_simulation(url):
    """Loopback literals must reach the RPC layer, not be refused on scheme.

    The assertion is about the TRANSPORT POLICY, not about whether a node
    happens to be listening. The gate must pass both ways:

      * no node running -> the call fails with a connection error, which
        proves the policy admitted it (a policy refusal raises ValueError with
        a different message);
      * a node running (a developer's local chain, or the benchmark stub) ->
        the call succeeds or fails on the node's answer, which also proves the
        policy admitted it.

    An earlier version asserted the call must FAIL, and broke the moment a
    local stub was running -- an assumption about the environment dressed up as
    a policy test.
    """
    try:
        chain_owner_of(url, ADDR, 1)
    except ValueError as exc:
        assert "must use HTTPS" not in str(exc), (
            "loopback %r was refused by the transport policy; a local chain "
            "speaks plain HTTP and must be simulatable" % (url,))
    except Exception:                   # noqa: BLE001
        pass                            # connection refused etc. -- admitted
    # Falling through without raising is also a pass: the policy admitted the
    # URL and a local node answered.


@pytest.mark.parametrize("url", [
    "http://ethereum-rpc.publicnode.com",
    "http://10.0.0.1:8545",
    "http://192.168.1.1:8545",
    "http://172.16.0.1:8545",
    "http://localhost:8545",
    "http://127.evil.com",
    "http://127.0.0.1.example.com",
    "http://evil.com/127.0.0.1",
    "http://[::1].evil.com:8545",
    "ftp://example.com",
    "file:///etc/passwd",
])
def test_non_loopback_plain_http_is_refused(url):
    """Everything that is not a loopback literal must still be refused.

    `localhost` is included deliberately: it resolves through the resolver and
    can point anywhere, whereas 127.0.0.0/8 and ::1 are checked as literals.
    `127.evil.com` and `127.0.0.1.example.com` are included because a
    string-prefix test would pass them.
    """
    with pytest.raises(ValueError) as exc:
        chain_owner_of(url, ADDR, 1)
    assert "must use HTTPS" in str(exc.value), (
        "%r was refused for the wrong reason: %s" % (url, exc.value))


def test_https_is_always_accepted():
    """HTTPS must never be refused on transport grounds."""
    try:
        chain_owner_of("https://ethereum-rpc.publicnode.com", ADDR, 1)
    except ValueError as exc:
        assert "must use HTTPS" not in str(exc), (
            "an https endpoint was refused on transport grounds")
    except Exception:                   # noqa: BLE001
        pass                            # no network in the gate -- fine


def test_a_bad_contract_address_is_still_refused():
    with pytest.raises(ValueError) as exc:
        chain_owner_of("http://127.0.0.1:8545", "0xdeadbeef", 1)
    assert "20-byte hex address" in str(exc.value)
