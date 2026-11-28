import ast
import inspect
import re

import pytest

from obfuscator.core import pipeline


_KEY_HEX = "00" * 32


def _hybrid_loader(**overrides):
    kwargs = dict(
        native_blobs={},
        bytecode_fallback=b"",
        key_hex=_KEY_HEX,
        native_only=False,
        identity_gate=False,
        split_bootstrap=False,
        snapshot_off=True,
        stdlib_audit_off=True,
    )
    kwargs.update(overrides)
    return pipeline.generate_hybrid_loader_script(**kwargs)[0]


def test_hybrid_placeholders_are_single_pass_and_string_escaped():
    build_id = 'id-{customer_salt}";injected()#'
    customer_salt = "customer-{share0}"
    src = _hybrid_loader(build_id=build_id, customer_salt=customer_salt)

    # The hostile values are data, not template code.  In particular the
    # later ``{customer_salt}``/``{share0}`` tokens must not be substituted
    # inside values inserted by earlier replacements.
    compile(src, "<hybrid>", "exec")
    tree = ast.parse(src)
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                values[target.id] = node.value.value
    assert values["_NX_BUILD_ID"] == build_id
    assert values["_NX_CUSTOMER_SALT"] == customer_salt


def _selfcheck_namespace(src, artefact_path):
    tree = ast.parse(src)
    wanted = {"constant_time_compare", "_nx_self_fail", "_nx_self_check"}
    parts = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted:
            parts.append(ast.get_source_segment(src, node))
    assert len(parts) == 3
    ns = {"__file__": str(artefact_path)}
    exec("\n\n".join(parts), ns)
    for name in ("_NX_SELF_CK", "_NX_SELF_HM", "_NX_SELF_HK", "_NX_SELF_TOK"):
        match = re.search(rf'^{name} = "([0-9a-f]*)"', src, re.M)
        assert match, name
        ns[name] = match.group(1)

    class SelfCheckFailed(Exception):
        pass

    def fail(reason):
        raise SelfCheckFailed(str(reason))

    ns["_nx_self_fail"] = fail
    ns["SelfCheckFailed"] = SelfCheckFailed
    return ns


def test_selfcheck_token_pin_cannot_mark_injected_lines_unhashed(tmp_path):
    token_hash = "ab" * 32
    src = _hybrid_loader(
        self_check=True, licence_bound=True, licence_token_hash=token_hash)
    stamped = pipeline._stamp_hybrid_selfcheck(
        src, "cd" * 32, token_hash=token_hash)
    artefact = tmp_path / "artefact.py"
    artefact.write_text(stamped, encoding="utf-8")

    ns = _selfcheck_namespace(stamped, artefact)
    assert ns["_nx_self_check"]()

    token_line = next(
        line for line in stamped.splitlines()
        if line.startswith('_NX_SELF_TOK = '))
    injected = (
        token_line
        + "\nINJECTED_BEFORE_CHECK = 1  # " + token_hash
    )
    tampered = stamped.replace(token_line, injected, 1)
    artefact.write_text(tampered, encoding="utf-8")
    with pytest.raises(ns["SelfCheckFailed"]):
        ns["_nx_self_check"]()


def test_hybrid_loader_error_path_wipes_live_buffers_and_preserves_interrupts():
    src = _hybrid_loader(self_check=False)
    assert "_nx_wipe(bytearray(encrypted))" not in src
    assert "_nx_wipe(bytearray(compressed))" not in src
    assert "_nx_wipe(bytearray(raw))" not in src
    assert "isinstance(e, (SystemExit, KeyboardInterrupt))" in src


def test_hybrid_loader_has_no_unsafe_object_address_mprotect():
    src = _hybrid_loader(self_check=False)
    assert "id(compressed)" not in src
    assert "_nx_ro_" not in src
    assert 'globals()["_NX_PAYLOAD_RO"] = False' in src


def test_kill_ladder_is_defined_before_expiry_gate_executes():
    src = _hybrid_loader(self_check=False, expire_ts=4_102_444_800)
    kill_at = src.find("def _nx_kill(")
    expiry_at = src.find("_NX_EXP_DATE =")
    assert kill_at != -1 and expiry_at != -1
    assert kill_at < expiry_at


def test_selfcheck_uses_constant_time_hmac_verification():
    src = _hybrid_loader(self_check=True)
    assert "compare_digest(sig, _NX_SELF_HM)" in src
    assert "if sig != _NX_SELF_HM:" not in src


class _FakeResponse:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None


def test_cloudflare_licence_write_requires_success_status(monkeypatch):
    deployer = pipeline.CloudflareDeployer("token", "account")
    monkeypatch.setattr(deployer, "get_kv_id", lambda: "kv")
    monkeypatch.setattr(
        pipeline, "checked_urlopen", lambda *a, **k: _FakeResponse(500))
    assert deployer.add_license("a" * 64, "payload") is False


def test_cloudflare_worker_deploy_requires_success_status(monkeypatch):
    deployer = pipeline.CloudflareDeployer("token", "account")
    monkeypatch.setattr(deployer, "get_kv_id", lambda: "kv")
    monkeypatch.setattr(
        deployer, "_req", lambda *a, **k: {"result": {"subdomain": "example"}})
    monkeypatch.setattr(
        pipeline, "checked_urlopen", lambda *a, **k: _FakeResponse(403))
    assert deployer.deploy_master("hmac") is None


def test_hwid_lock_and_region_gates_fail_closed_in_build_logic():
    build_src = inspect.getsource(pipeline.build_project)
    assert "hwid-lock requires" in build_src
    assert "continuing unlocked" not in build_src
    assert "payload obfuscation failed" in build_src
    assert "ast_options['allowed_regions']" in build_src
    assert "ast_options['blocked_regions']" in build_src
    assert "ast_options.get('allowed_regions')" in build_src
    assert "ast_options.get('blocked_regions')" in build_src


def test_process_file_safe_does_not_ship_untransformed_source_on_mutation_error(tmp_path, monkeypatch):
    src_dir = tmp_path / "src"
    build_dir = tmp_path / "build"
    src_dir.mkdir()
    build_dir.mkdir()
    src = src_dir / "payload.py"
    src.write_text("print('secret')\n", encoding="utf-8")

    def boom(*args, **kwargs):
        raise RuntimeError("mutation exploded")

    monkeypatch.setattr(pipeline, "apply_ast_mutation", boom)
    result = pipeline.process_file_safe(
        (str(src), str(build_dir), list(b"k" * 16), "output.py",
         str(src_dir), {}, {}))
    assert result[0] == "error"
    assert "AST mutation failed" in result[2]
    assert not (build_dir / "payload.py").exists()
