"""Unified --web3 / --licence flags.

One flag per subsystem.  Each sub-option writes the destination the
consumers read.  The former per-knob spellings (--contract, --rpc,
--shards, --auto-deploy, --deploy-rpc, --explorer, --licence-token,
--licence-env-only, --licence-bootstrap-encrypted, --licence-chain) were
removed on 2026-11-12: this flag is the only interface, and the removed
spellings must be rejected, not silently accepted.
"""

import pytest

from obfuscator.core.pipeline import apply_unified_specs, build_parser


def _parse(argv):
    parser, _subparsers = build_parser()
    args = parser.parse_args(argv)
    return apply_unified_specs(args)


def test_web3_suboptions_reach_the_flag_destinations():
    args = _parse([
        "build", "src.py",
        "--web3", "rpc=https://rpc.example/v1", "contract=0x" + "a" * 40,
        "shards=https://s1,https://s2", "deploy", "deploy-rpc=https://d",
        "explorer=https://blocks.example",
    ])
    assert args.rpc == "https://rpc.example/v1"
    assert args.contract == "0x" + "a" * 40
    assert args.shards == "https://s1,https://s2"
    assert args.auto_deploy is True
    assert args.deploy_rpc == "https://d"
    assert args.explorer == "https://blocks.example"


def test_licence_suboptions_reach_the_flag_destinations():
    args = _parse([
        "build", "src.py",
        "--licence", "token=acme.licence", "env-only", "bootstrap-encrypted",
        "chain",
    ])
    assert args.licence_token == "acme.licence"
    assert args.licence_env_only is True
    assert args.licence_bootstrap_encrypted is True
    assert args.licence_chain is True


def test_licence_defaults_when_the_flag_is_absent():
    # No --licence: the dests must be ABSENT, not falsy-but-set, so the
    # build-time getattr defaults apply and no gate is armed.
    args = _parse(["build", "src.py"])
    assert not hasattr(args, "licence_token")
    assert not hasattr(args, "licence_chain")


def test_boolean_spelling_variants():
    for raw, expected in (("deploy", True), ("deploy=false", False),
                          ("deploy=on", True), ("deploy=0", False)):
        args = _parse(["build", "src.py", "--web3", raw])
        assert args.auto_deploy is expected


def test_underscores_normalise_to_dashes():
    args = _parse(["build", "src.py", "--licence", "bootstrap_encrypted"])
    assert args.licence_bootstrap_encrypted is True


def test_unknown_suboption_is_refused():
    with pytest.raises(SystemExit, match="unknown sub-option"):
        _parse(["build", "src.py", "--web3", "rpcx=https://x"])
    with pytest.raises(SystemExit, match="unknown sub-option"):
        _parse(["build", "src.py", "--licence", "chains"])


def test_duplicate_suboption_is_refused():
    with pytest.raises(SystemExit, match="given twice"):
        _parse(["build", "src.py", "--web3", "rpc=a", "rpc=b"])


def test_value_suboption_requires_a_value():
    with pytest.raises(SystemExit, match="expected key=value"):
        _parse(["build", "src.py", "--web3", "rpc"])


def test_removed_legacy_spellings_are_rejected():
    # The per-knob spellings were removed with the unified flags. Argparse
    # rejects unknown options with exit 2; the point of this test is that
    # they cannot come back silently.
    for argv in (
        ["build", "src.py", "--contract", "0xabc"],
        ["build", "src.py", "--rpc", "https://x"],
        ["build", "src.py", "--shards", "a,b"],
        ["build", "src.py", "--auto-deploy"],
        ["build", "src.py", "--deploy-rpc", "https://x"],
        ["build", "src.py", "--explorer", "https://x"],
        ["build", "src.py", "--licence-token", "acme.licence"],
        ["build", "src.py", "--licence-env-only"],
        ["build", "src.py", "--licence-bootstrap-encrypted"],
        ["build", "src.py", "--licence-chain"],
    ):
        with pytest.raises(SystemExit):
            _parse(argv)


def test_removed_alias_spellings_are_rejected():
    for argv in (
        ["build", "src.py", "--poison-all"],      # alias of --provenance-poison
        ["build", "src.py", "--gpu"],             # alias of --gpu-execution
        ["build", "src.py", "--cpu-gpu-hybrid"],  # alias of --gpu-hybrid
        ["build", "src.py", "--advanced-protection"],  # alias of --phase2
    ):
        with pytest.raises(SystemExit):
            _parse(argv)


def test_access_suboptions_reach_the_flag_destinations():
    args = _parse([
        "build", "src.py", "--access",
        "hwid=ABC123", "hwid-lock", "lock-hwid=H9", "trial=7d",
        "expire=2027-01-01", "bind-mac", "one-shot", "kod", "hostguard",
        "driver-check", "name-gate", "rename-internal",
        "allow-countries=US,DE", "block-countries=RU",
        "allow-regions=R1", "block-regions=R2",
        "webhook=https://alert.example", "net-url=https://auth.example",
    ])
    assert args.hwid == "ABC123"
    assert args.hwid_lock is True
    assert args.lock_hwid == "H9"
    assert args.trial == "7d"
    assert args.expire == "2027-01-01"
    assert args.bind_mac is True
    assert args.one_shot is True
    assert args.kod is True
    assert args.hostguard is True
    assert args.driver_check is True
    assert args.name_gate is True
    assert args.rename_internal is True
    assert args.allow_countries == "US,DE"
    assert args.block_countries == "RU"
    assert args.allow_regions == "R1"
    assert args.block_regions == "R2"
    assert args.webhook == "https://alert.example"
    assert args.net_url == "https://auth.example"


def test_access_defaults_are_filled_when_absent():
    # Direct readers (args.bind_mac, args.expire, ...) must find the dests.
    args = _parse(["build", "src.py"])
    assert args.hwid == ""
    assert args.hwid_lock is False
    assert args.bind_mac is False
    assert args.expire == ""
    assert args.one_shot is False


def test_split_bootstrap_is_on_by_default_with_an_optout():
    # Default-on since 2026-11-12; the enable flag was removed, the
    # --no- split-bootstrap opt-out remains (section-split precedent).
    args = _parse(["build", "src.py"])
    assert args.split_bootstrap is True
    args = _parse(["build", "src.py", "--no-split-bootstrap"])
    assert args.split_bootstrap is False


def test_removed_access_spellings_are_rejected():
    for flag in (
        "--hwid", "--trial", "--expire", "--kod", "--hostguard",
        "--hwid-lock", "--driver-check", "--name-gate", "--rename-internal",
        "--lock-hwid", "--bind-mac", "--one-shot", "--allow-countries",
        "--block-countries", "--allow-regions", "--block-regions",
        "--webhook", "--net-url",
    ):
        with pytest.raises(SystemExit):
            _parse(["build", "src.py", flag])


def test_other_commands_pass_through():
    args = _parse(["version"])
    assert apply_unified_specs(args) is args


def test_package_all_means_package_with_everything_else():
    # "all"/"everything" = maximum recursive packaging on top of the
    # default-on protections (anti-REA maximum, sectioned sealing, ...).
    for word in ("all", "everything"):
        args = _parse(["build", "src.py", "--package", word])
        assert args.layers == 25
        assert args.zips == 3
        assert args.stego is True
    # Explicit options still combine with it, and typos are refused.
    args = _parse(["build", "src.py", "--package", "all", "layers=10"])
    assert args.layers == 10
    assert args.stego is True
    with pytest.raises(SystemExit, match="unknown option"):
        _parse(["build", "src.py", "--package", "everything-else"])
