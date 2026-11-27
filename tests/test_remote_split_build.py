"""Build-pipeline wiring for server-side split execution."""
import argparse
import os
import stat
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from obfuscator.core.pipeline import (  # noqa: E402
    _prepare_remote_split_source, apply_unified_specs, build_parser,
)


SOURCE = '''\
from obfuscator.remote_exec import remote


@remote
def pricing_engine(units, tier):
    SECRET_COEFFICIENT = 0x5EC12E7
    base = units * SECRET_COEFFICIENT
    if tier == "gold":
        return base * 87 // 100
    return base


def main():
    print(pricing_engine(10, "gold"))


if __name__ == "__main__":
    main()
'''


def _write_source(tmp_path):
    path = tmp_path / "payload.py"
    path.write_text(SOURCE, encoding="utf-8")
    return str(path)


def _cleanup(args):
    path = getattr(args, "_tmp_remote_client", None)
    if path and os.path.exists(path):
        os.unlink(path)


def test_transforms_parser_accepts_remote_and_remote_bundle():
    parser, _subparsers = build_parser()
    args = parser.parse_args([
        "build", "payload.py", "--transforms", "remote",
        "remote-bundle=operator_bundle.py",
    ])
    args = apply_unified_specs(args)
    assert args.tx_remote is True
    assert args.tx_remote_bundle == "operator_bundle.py"


def test_remote_split_requires_an_operator_bundle(tmp_path):
    source = _write_source(tmp_path)
    args = argparse.Namespace(tx_remote=True, tx_remote_bundle="")
    args._input_source = source
    with pytest.raises(SystemExit, match="remote-bundle"):
        _prepare_remote_split_source(args, source)


def test_remote_split_happens_before_any_payload_consumer(tmp_path):
    source = _write_source(tmp_path)
    bundle = str(tmp_path / "operator_bundle.py")
    args = argparse.Namespace(tx_remote=True, tx_remote_bundle=bundle)
    args._input_source = source
    try:
        client_path = _prepare_remote_split_source(args, source)
    finally:
        pass
    try:
        assert client_path != source
        client = open(client_path, encoding="utf-8").read()
        assert "SECRET_COEFFICIENT" not in client
        assert "0x5EC12E7" not in client
        assert "base * 87" not in client
        assert "obfuscator" not in client
        assert "@remote" not in client
        assert "_nx_call_remote" in client
        compile(client, "<client>", "exec")

        original = open(source, encoding="utf-8").read()
        assert "SECRET_COEFFICIENT" in original, (
            "the input payload must remain untouched; split output goes to a temp file")

        operator = open(bundle, encoding="utf-8").read()
        assert "SECRET_COEFFICIENT" in operator
        assert stat.S_IMODE(os.stat(bundle).st_mode) & 0o077 == 0
        assert args._original_source == source
        assert args._remote_function_count == 1
    finally:
        _cleanup(args)


def test_remote_transform_without_markers_fails_closed(tmp_path):
    # An operator who explicitly passes --transforms remote for a payload
    # with no @remote function has misconfigured the build. Shipping the
    # unsplit source would produce a fully local artefact that looks
    # remote-protected, so the pipeline must refuse rather than warn.
    path = tmp_path / "plain.py"
    path.write_text("print('plain')\n", encoding="utf-8")
    args = argparse.Namespace(
        tx_remote=True, tx_remote_bundle=str(tmp_path / "bundle.py"))
    args._input_source = str(path)
    with pytest.raises(SystemExit, match="no @remote"):
        _prepare_remote_split_source(args, str(path))
    assert not os.path.exists(args.tx_remote_bundle)


def test_marked_payload_is_refused_when_remote_transform_is_not_enabled(tmp_path):
    source = _write_source(tmp_path)
    args = argparse.Namespace(tx_remote=False, tx_remote_bundle="")
    args._input_source = source
    with pytest.raises(SystemExit, match="--transforms remote"):
        _prepare_remote_split_source(args, source)


def test_unmarked_payload_is_allowed_when_remote_transform_is_not_enabled(tmp_path):
    path = tmp_path / "plain.py"
    path.write_text("print('plain')\n", encoding="utf-8")
    args = argparse.Namespace(tx_remote=False, tx_remote_bundle="")
    args._input_source = str(path)
    assert _prepare_remote_split_source(args, str(path)) == str(path)


def test_transforms_parser_accepts_cloudflare_worker_output():
    parser, _subparsers = build_parser()
    args = parser.parse_args([
        "build", "payload.py", "--transforms", "remote",
        "remote-bundle=operator_bundle.py",
        "remote-cloudflare=cloudflare-worker",
        "remote-cloudflare-name=my-remote-worker",
    ])
    args = apply_unified_specs(args)
    assert args.tx_remote is True
    assert args.tx_remote_cloudflare == "cloudflare-worker"
    assert args.tx_remote_cloudflare_name == "my-remote-worker"


def test_remote_split_writes_cloudflare_worker_project(tmp_path):
    source = _write_source(tmp_path)
    bundle = str(tmp_path / "operator_bundle.py")
    worker_dir = str(tmp_path / "cloudflare-worker")
    args = argparse.Namespace(
        tx_remote=True,
        tx_remote_bundle=bundle,
        tx_remote_cloudflare=worker_dir,
        tx_remote_cloudflare_name="test-remote-worker",
    )
    args._input_source = source
    try:
        client_path = _prepare_remote_split_source(args, source)
        assert client_path != source
        assert args._remote_cloudflare_worker == os.path.abspath(worker_dir)
        entry = open(os.path.join(worker_dir, "src", "entry.py"),
                     encoding="utf-8").read()
        implementation = open(os.path.join(worker_dir, "src", "remote_impl.py"),
                              encoding="utf-8").read()
        assert "SECRET_COEFFICIENT" not in entry
        assert "SECRET_COEFFICIENT" in implementation
        assert "class SecurityRegistry" in entry
        assert "NIXON_REMOTE_MASTER_SECRET" in entry
        assert "NIXON_REMOTE_RATE_LIMIT_PER_MINUTE" in entry
        assert stat.S_IMODE(os.stat(os.path.join(
            worker_dir, "src", "entry.py")).st_mode) & 0o077 == 0
        assert stat.S_IMODE(os.stat(os.path.join(
            worker_dir, "src", "remote_impl.py")).st_mode) & 0o077 == 0
        client = open(client_path, encoding="utf-8").read()
        assert "SECRET_COEFFICIENT" not in client
    finally:
        _cleanup(args)


def test_remote_split_fails_closed_when_cloudflare_output_exists(tmp_path):
    source = _write_source(tmp_path)
    worker_dir = tmp_path / "cloudflare-worker"
    worker_dir.mkdir()
    args = argparse.Namespace(
        tx_remote=True,
        tx_remote_bundle=str(tmp_path / "operator_bundle.py"),
        tx_remote_cloudflare=str(worker_dir),
        tx_remote_cloudflare_name="test-remote-worker",
    )
    args._input_source = source
    with pytest.raises(SystemExit, match="Cloudflare worker"):
        _prepare_remote_split_source(args, source)


def test_remote_transform_without_marked_functions_fails_closed(tmp_path):
    """--transforms remote on a payload with no @remote function must not
    silently ship a fully local artefact: the operator asked for split
    execution, so a no-op split is a build error, not a warning."""
    path = tmp_path / "payload.py"
    path.write_text(
        "def main():\n    print('no remote markers here')\n\n"
        "if __name__ == '__main__':\n    main()\n",
        encoding="utf-8")
    parser, _subparsers = build_parser()
    args = parser.parse_args([
        "build", str(path), "--transforms", "remote",
        "remote-bundle=%s" % (tmp_path / "operator_bundle.py"),
    ])
    args = apply_unified_specs(args)
    try:
        with pytest.raises(SystemExit) as excinfo:
            _prepare_remote_split_source(args, str(path))
        assert "no @remote" in str(excinfo.value)
    finally:
        _cleanup(args)
