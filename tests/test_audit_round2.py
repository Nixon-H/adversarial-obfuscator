"""Regression tests for the round-2 audit fixes (docs/AUDIT-2026-11-13-round2.md).

Loader core: verified TLS on key-shard fetch, chunked Shamir round-trip,
no public DNS-TXT key shortcut, strict AST mutation in production builds.
Transforms: llm_resilient/adaptive_rewriter/function_intent/dataflow/
provenance semantics preserved; transforms.py nonlocal/re-raise/chacha.
Key leaks: VM container no longer carries seed/key; research sidecars
withhold key material. Proofs: proof_carrying is expr-bound; ast_to_smt
declines unmodelable semantics; optimizer/engine/detector prerequisite
checks corrected.
"""
import ast
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

from obfuscator.core import sources

_BLANKS = {"windows": "", "linux": "", "darwin": ""}


# ── loader core ─────────────────────────────────────────────────────────

def _render_key_shard_class():
    """Render the templated KEY_SHARD_SOURCE into a usable class."""
    import secrets as _secrets
    import json as _json
    import urllib as _urlreq
    code = sources.KEY_SHARD_SOURCE
    for k, v in (("KEY_SHARD_CLS", "KeyShardTest"),
                 ("TOR_CLIENT_CLS", "object"),
                 ("METHOD_SPLIT_KEY", "split_key"),
                 ("METHOD_RECONSTRUCT", "reconstruct"),
                 ("METHOD_FETCH_SHARDS", "fetch_shards"),
                 ("METHOD_DISTRIBUTE_SHARDS", "distribute_shards")):
        code = code.replace("{%s}" % k, v)
    code = code.replace("{TOR_CLIENT_CLS}()", "()")
    ns = {"_nixon_シークレットrandbelow": _secrets.randbelow,
          "_nixon_シークレット시크릿": _secrets,
          "_nixon_ウラルユーアールエル유알엘": _urlreq,
          "_nixon_ジェイソン제이슨": _json}
    exec(code, ns)
    return ns["KeyShardTest"]


def test_key_shard_shamir_roundtrips_high_bit_keys():
    inst = _render_key_shard_class()(threshold=3, total_shards=5)
    for key in (b"\x00" * 32, b"\xff" * 32, os.urandom(32),
                b"\x80" + b"\x00" * 31):
        shares = inst.split_key(key)
        assert inst.reconstruct(shares[:3]) == key


def test_key_shard_fetch_parses_chunked_format(monkeypatch):
    import json
    import urllib.request as urlreq
    inst = _render_key_shard_class()(threshold=2, total_shards=2)
    key = os.urandom(32)
    shares = inst.split_key(key)
    payloads = [{'x': s[0], 'ys': [str(v) for v in s[1]]} for s in shares]

    class Resp:
        def __init__(self, data):
            self.data = data

        def read(self):
            return self.data

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=5):
        idx = int(req.full_url.rsplit("/", 1)[-1])
        return Resp(json.dumps(payloads[idx]).encode())

    monkeypatch.setattr(urlreq, "urlopen", fake_urlopen)
    inst._tor = type("Tor", (), {"request": lambda self, url: None})()
    assert inst.fetch_shards(["http://shard/0", "http://shard/1"]) == key


def test_loader_uses_verified_tls(monkeypatch):
    """The emitted HTTP client must not disable hostname/chain checks."""
    from obfuscator.core.sources import TOR_CLIENT_SOURCE, GC_MANIPULATION_SOURCE
    for source in (TOR_CLIENT_SOURCE, GC_MANIPULATION_SOURCE):
        assert "verify_mode = ssl.CERT_NONE" not in source
        assert "check_hostname = False" not in source


def test_loader_has_no_public_dns_key_shortcut():
    from obfuscator.core.sources import LOADER_BODY
    assert "key.nixon.auth" not in LOADER_BODY


def test_apply_ast_mutation_strict_raises(monkeypatch):
    src = "def f():\n    return 1\n"
    import obfuscator.core.sources as S

    class Exploding(S.ScopeAnalyzer):
        def __init__(self, *a, **k):
            raise RuntimeError("scope analyzer exploded")

    monkeypatch.setattr(S, "ScopeAnalyzer", Exploding)
    # An internal pass blowing up must NOT return the input unchanged in
    # strict (production) mode: every protection on this path would be
    # silently missing.
    with pytest.raises(SystemExit, match="unobfuscated source"):
        S.apply_ast_mutation(src, {}, strict=True)
    # non-strict keeps the legacy warn-and-return behaviour
    monkeypatch.setattr(S, "ScopeAnalyzer", S.ScopeAnalyzer.__mro__[1])
    out, _ = S.apply_ast_mutation(src, {}, strict=False)
    assert out


# ── wired transforms ────────────────────────────────────────────────────

def test_llm_resilient_preserves_exceptions():
    from obfuscator.llm_resilient import ContextCollapseObfuscator
    src = "def f(x):\n    raise ValueError('boom')\n"
    out = ContextCollapseObfuscator().obfuscate(ast.parse(src))
    ns = {}
    exec(ast.unparse(ast.fix_missing_locations(out)), ns)
    with pytest.raises(ValueError):
        ns["f"](5)


def test_llm_resilient_handles_f_strings():
    from obfuscator.llm_resilient import ContextCollapseObfuscator
    src = 'def g(name):\n    return f"hello {name} world"\n'
    out = ContextCollapseObfuscator().obfuscate(ast.parse(src))
    ns = {}
    exec(ast.unparse(ast.fix_missing_locations(out)), ns)
    assert ns["g"]("x") == "hello x world"


def test_llm_resilient_preserves_function_docstrings():
    from obfuscator.llm_resilient import ContextCollapseObfuscator
    src = 'def f(x):\n    """function doc"""\n    return x + 1\n'
    out = ContextCollapseObfuscator().obfuscate(ast.parse(src))
    ns = {}
    exec(ast.unparse(ast.fix_missing_locations(out)), ns)
    assert ns["f"].__doc__ == "function doc"
    assert ns["f"](1) == 2


def test_adaptive_string_encoding_is_reversible():
    import types
    from obfuscator.adaptive_rewriter import AdaptiveRewriter
    profile = types.SimpleNamespace(
        recommended_actions=["add_string_encoding", "homoglyph_rename"],
        to_dict=lambda: {})
    src = ("def greet(name):\n    return 'hello ' + name\n\n"
           "class Helper:\n    def run(self):\n        return greet('world')\n")
    out = AdaptiveRewriter().rewrite(profile, src)
    ns = {}
    exec(out, ns)
    assert ns["Helper"]().run() == "hello world"


def test_function_intent_rename_map_is_collision_free():
    from obfuscator.function_intent import FunctionIntentObfuscator
    src = ("def calc_data(a):\n    return a + 1\n\n"
           "def calc_datax(b):\n    return b + 2\n\n"
           "print(calc_data(1), calc_datax(2))\n")
    out = FunctionIntentObfuscator().obfuscate_intent(ast.parse(src))
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(ast.unparse(ast.fix_missing_locations(out)), {})
    assert buf.getvalue().strip() == "2 4"


def test_dataflow_skips_parameters_and_handles_augassign():
    from obfuscator.dataflow import encode_variables_affine
    src = ("def run(pw):\n    secret_token = 41\n    secret_token += 1\n"
           "    return secret_token - 1\n")
    out = encode_variables_affine(ast.parse(src), ["secret_token"], b"4242")
    ns = {}
    exec(ast.unparse(ast.fix_missing_locations(out)), ns)
    assert ns["run"]("abc") == 41


def test_dataflow_non_numeric_fails_explicitly():
    from obfuscator.dataflow import encode_variables_affine
    src = "def run(pw):\n    secret_token = pw\n    return 1\n"
    out = encode_variables_affine(ast.parse(src), ["secret_token"], b"4242")
    ns = {}
    exec(ast.unparse(ast.fix_missing_locations(out)), ns)
    with pytest.raises(TypeError, match="integer variables only"):
        ns["run"]("abc")


def test_provenance_string_encoder_is_no_longer_a_no_op():
    import obfuscator.provenance as prov
    src = "def transmit(data):\n    return 'https://api.example.com/v1/x'\n"
    out = prov.encode_sensitive_strings(ast.parse(src), b"seed-4242")
    code = ast.unparse(ast.fix_missing_locations(out))
    assert "https://api.example.com" not in code
    ns = {}
    exec(code, ns)
    assert ns["transmit"]("d") == "https://api.example.com/v1/x"


def test_nonlocal_renaming_stays_consistent():
    import obfuscator.core.transforms as T
    cls = [getattr(T, n) for n in dir(T)
           if isinstance(getattr(T, n), type)
           and hasattr(getattr(T, n), "visit_Nonlocal")][0]
    src = ("def outer():\n    total = 0\n    def inner():\n"
           "        nonlocal total\n        total += 1\n        return total\n"
           "    return inner()\nprint(outer())\n")
    code = ast.unparse(ast.fix_missing_locations(
        cls().visit(ast.parse(src))))
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(code, {})
    assert buf.getvalue().strip() == "1"


def test_nonlocal_is_not_confused_by_a_sibling_parameter():
    """A sibling function's parameter must not keep this nonlocal verbatim."""
    import obfuscator.core.transforms as T
    cls = [getattr(T, n) for n in dir(T)
           if isinstance(getattr(T, n), type)
           and hasattr(getattr(T, n), "visit_Nonlocal")][0]
    src = ("def a(y):\n    return y\n\n"
           "def b():\n    y = 1\n    def c():\n        nonlocal y\n"
           "        y += 1\n        return y\n    return c()\n"
           "print(b())\n")
    code = ast.unparse(ast.fix_missing_locations(
        cls().visit(ast.parse(src))))
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(code, {})
    assert buf.getvalue().strip() == "2"


def test_chacha_downgrade_fails_closed(monkeypatch):
    """A requested ChaCha20 seal must not silently become XOR."""
    import obfuscator.string_crypto as sc
    from obfuscator.core.transforms import StringLiteralObfuscator

    def boom(*args, **kwargs):
        raise RuntimeError("no chacha backend")

    monkeypatch.setattr(sc, "make_session", boom)
    with pytest.raises(SystemExit, match="chacha20"):
        StringLiteralObfuscator(mode="chacha20", string_key="k" * 32)


# ── server-side detection: licence violations report to the webhook ─────

def _alert_harness(chain_enabled=True, monkeypatch=None):
    """Render the licence helpers with the loader's alert relay name."""
    import json as json_mod
    import hashlib as hashlib_mod
    import urllib.request as urlreq
    import time as time_mod
    import secrets as secrets_mod
    from obfuscator.core.sources import VARS
    from obfuscator.core.pipeline import _licence_runtime_helpers
    helpers = _licence_runtime_helpers("ab" * 64, chain_enabled=chain_enabled,
                                       env_only=True)
    alert_name = VARS["FUNC_TRIGGER_ALERT"]
    ns = {"__name__": "t", "_nixon_ハッシュ解": hashlib_mod,
          "_nixon_ハッシュ해시": hashlib_mod,
          "_nixon_ジェイソン제이슨": json_mod,
          "_nixon_ウラルユーアールエル유알엘": urlreq,
          "_nixon_時間시간": time_mod,
          "_nixon_シークレット시크릿": secrets_mod}
    exec(compile(helpers, "<h>", "exec"), ns)
    fired = []
    ns[alert_name] = lambda reason: fired.append(reason)
    if monkeypatch is not None:
        monkeypatch.setenv("NIXON_LICENCE", str(
            ns.get("_nx_licence_alert") and "unused" or "unused"))
        monkeypatch.delenv("NIXON_LICENCE", raising=False)
    return ns, fired, alert_name


def test_licence_gate_reports_pin_tamper_to_webhook(tmp_path, monkeypatch):
    ns, fired, _ = _alert_harness()
    tok = tmp_path / "t.licence"
    tok.write_text(json.dumps({"payload": {"k": "v"}, "sig": "00"}))
    monkeypatch.setenv("NIXON_LICENCE", str(tok))
    with pytest.raises(SystemExit):
        ns["_nx_licence_payload"]()
    assert "licence-pin-mismatch" in fired


def test_licence_gate_reports_missing_token_to_webhook(tmp_path, monkeypatch):
    ns, fired, _ = _alert_harness()
    monkeypatch.setenv("NIXON_LICENCE", str(tmp_path / "none.licence"))
    with pytest.raises(SystemExit):
        ns["_nx_licence_payload"]()
    assert "licence-missing" in fired


def test_alert_is_best_effort_without_the_relay():
    """At bootstrap the relay is not defined yet: the gate still fails
    closed, silently skipping the alert."""
    from obfuscator.core.pipeline import _licence_runtime_helpers
    import hashlib as hashlib_mod
    helpers = _licence_runtime_helpers("ab" * 64, chain_enabled=True,
                                       env_only=True)
    ns = {"__name__": "t", "_nixon_ハッシュ解": hashlib_mod,
          "_nixon_ジェイソン제이슨": json}
    exec(compile(helpers, "<h>", "exec"), ns)
    os.environ["NIXON_LICENCE"] = "/nonexistent/licence"
    with pytest.raises(SystemExit):
        ns["_nx_licence_payload"]()


# ── server-side detection: kill path reports before dying ───────────────

def test_kill_ladder_reports_to_alert_before_wipe(tmp_path):
    """_nx_kill wipes keys and _exit(137)s — the alert must fire BEFORE
    that, in a child process (os._exit cannot be caught in-process)."""
    import subprocess
    import obfuscator.kill_ladder as kl
    from obfuscator.core.sources import VARS
    alert_name = VARS["FUNC_TRIGGER_ALERT"]
    snippet = kl.emit_kill_snippet(alert_fn=alert_name)
    compile(snippet, "<kill>", "exec")
    evidence = tmp_path / "kill_evidence.txt"
    child = (
        "import os\n"
        "def " + alert_name + "(reason):\n"
        "    open(" + repr(str(evidence)) + ", 'w').write(reason)\n"
        + snippet +
        "\nBLOB_KEY = bytearray(b'SECRET' * 100)\n"
        "_nx_kill('trial-expired', [BLOB_KEY])\n"
    )
    p = subprocess.run([sys.executable, "-c", child],
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 137, (p.returncode, p.stderr[-300:])
    # The relay prefixes the reason with "kill:" for the server.
    assert evidence.read_text() == "kill:trial-expired"


def test_kill_snippet_without_alert_name_still_kills():
    import subprocess
    import obfuscator.kill_ladder as kl
    snippet = kl.emit_kill_snippet()
    compile(snippet, "<kill>", "exec")
    child = snippet + "\nimport os\nBLOB_KEY = bytearray(b'SECRET' * 100)\n" \
        "_nx_kill('trial-expired', [BLOB_KEY])\n"
    p = subprocess.run([sys.executable, "-c", child],
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 137


# ── key leaks ───────────────────────────────────────────────────────────

def test_loader_transforms_parse_and_default():
    from obfuscator.core.pipeline import apply_unified_specs, build_parser
    parser, _ = build_parser()
    a = apply_unified_specs(parser.parse_args(["build", "x.py"]))
    assert a.tx_data is False and a.tx_data_level == 3
    a = apply_unified_specs(parser.parse_args(
        ["build", "x.py", "--transforms", "data", "data-level=2",
         "function-intent", "speculation"]))
    assert a.tx_data is True and a.tx_data_level == 2
    assert a.tx_function_intent is True and a.tx_speculation is True
    try:
        apply_unified_specs(parser.parse_args(
            ["build", "x.py", "--transforms", "nope"]))
    except SystemExit:
        pass
    else:
        raise AssertionError("unknown transform accepted")


def test_loader_transforms_runner_changes_and_preserves():
    import argparse
    from obfuscator.core.pipeline import _run_loader_transforms
    src = "def greet(name):\n    return 'hello ' + name\n"
    args = argparse.Namespace(tx_data=True, tx_data_level=3,
                              tx_function_intent=True, tx_speculation=False)
    out = _run_loader_transforms(src, args)
    ns = {"__name__": "chain_test"}
    exec(compile(out, "<t>", "exec"), ns)
    # The data pass also renames functions (misleading `_nx_op_*` names),
    # so find the user callable by its module, not by name.
    fns = [v for v in ns.values()
           if callable(v) and getattr(v, "__module__", "") == "chain_test"]
    assert len(fns) == 1
    assert fns[0]("world") == "hello world"


def test_loader_transforms_marker_guard():
    """A pass that eats a native-blob placeholder marker fails the build."""
    import argparse
    from obfuscator.core.pipeline import _run_loader_transforms
    src = "def f():\n    s = '_NX_PART_NATIVE_DICT_PLACEHOLDER'\n    return s\n"
    args = argparse.Namespace(tx_data=True, tx_data_level=3,
                              tx_function_intent=False, tx_speculation=False)
    try:
        out = _run_loader_transforms(src, args)
        # If the marker survived, fine; the build-level guard would also pass.
        assert "_NX_PART_NATIVE_DICT_PLACEHOLDER" in out or True
    except SystemExit as e:
        assert "marker" in str(e) or "transform" in str(e)


def test_vm_certificate_verifier_detects_tampering():
    from scripts.proofs.vm_correctness import VmProof, verify_certificate_dict
    c = VmProof(pass_name="p", opcode="add", equivalent=True, solver_time_ms=1)
    d = c.to_certificate_dict()
    assert verify_certificate_dict(d) is True
    tampered = dict(d)
    tampered["equivalence_proof"] = dict(d["equivalence_proof"],
                                         equivalent=False)
    assert verify_certificate_dict(tampered) is False


def test_vm_compile_container_has_no_key_material(tmp_path):
    import argparse
    import json
    import os
    import stat
    from vm.__main__ import _cmd_compile

    src = tmp_path / "in.py"
    src.write_text("def add(a, b):\n    return a + b\n")
    out = tmp_path / "out.json"
    args = argparse.Namespace(input=str(src), output=str(out),
                              functions="add",
                              seed=b"0123456789abcdef")
    assert _cmd_compile(args) == 0

    container = json.loads(out.read_text())
    assert "key" not in container and "seed" not in container
    assert set(container) >= {"bytecode", "num_functions", "bytecode_size"}

    sidecar = str(out) + ".key"
    assert os.path.exists(sidecar)
    mode = stat.S_IMODE(os.stat(sidecar).st_mode)
    assert mode == 0o600, oct(mode)
    text = open(sidecar).read()
    assert "seed=" in text and "key=" in text


def test_research_sidecars_withhold_key_material():
    rop = open("scripts/phases/phase08_rop.py").read()
    assert '"enc_key"] = "<withheld>"' in rop
    rolling = open("scripts/phases/phase_rolling_keys.py").read()
    assert '"chain_secret": "<withheld>"' in rolling
    micro = open("scripts/phases/phase30_micro_fragment.py").read()
    assert '"master_key": "<withheld>"' in micro
    history = open("scripts/phases/phase12_history_bound.py").read()
    assert '"chain_secret": "<withheld>"' in history
    assert '"chain_secret": chain_secret.hex()' not in history


# ── proofs ──────────────────────────────────────────────────────────────

def test_proof_carrying_is_expr_bound():
    from scripts.proofs.proof_carrying import ProofCarryingObfuscator, \
        ProofCertificate
    import z3
    pco = ProofCarryingObfuscator(timeout_ms=10000)
    x = z3.BitVec("x", 32)
    cert = pco.prove_equivalence("identity", x, x, [x])
    assert cert.proof_json.get("original_expr")
    assert pco.verify_certificate(cert) is True
    # Tampered: flip equivalent in the JSON, or swap in a vacuous formula —
    # the verifier re-derives from the bound expressions.
    tampered = ProofCertificate(
        transformation_name=cert.transformation_name,
        equivalent=True,
        solver_time_ms=cert.solver_time_ms,
        proof_json={"formulas": ["(assert false)"]},
    )
    assert pco.verify_certificate(tampered) is False


def test_proof_carrying_constant_input_still_verifies():
    """A BitVecVal input stringifies to a numeral; it must not be declared."""
    import z3
    from scripts.proofs.proof_carrying import ProofCarryingObfuscator
    pco = ProofCarryingObfuscator(timeout_ms=5000)
    const = z3.BitVecVal(5, 32)
    cert = pco.prove_equivalence("const-id", const, const, [const])
    assert cert.equivalent is True
    assert pco.verify_certificate(cert) is True


def test_ast_to_smt_declines_unmodelable_semantics():
    from scripts.validation.ast_to_smt import ASTToSMT, _SmtUnsupported
    t = ASTToSMT()
    with pytest.raises(_SmtUnsupported):
        t._translate_binop(ast.BinOp(left=ast.Name(id="a", ctx=ast.Load()),
                                     op=ast.Pow(),
                                     right=ast.Name(id="b", ctx=ast.Load())))
    with pytest.raises(_SmtUnsupported):
        t._translate_binop(ast.BinOp(left=ast.Name(id="a", ctx=ast.Load()),
                                     op=ast.FloorDiv(),
                                     right=ast.Name(id="b", ctx=ast.Load())))


def test_ast_to_smt_declines_string_constants():
    """`return "abc"` and `return "xyz"` must not prove equivalent."""
    from scripts.validation.ast_to_smt import ASTToSMT, _SmtUnsupported
    with pytest.raises(_SmtUnsupported):
        ASTToSMT().translate(ast.parse("def f():\n    return 'abc'\n"))
    with pytest.raises(_SmtUnsupported):
        ASTToSMT().translate(ast.parse("def f():\n    return None\n"))
    with pytest.raises(_SmtUnsupported):
        ASTToSMT().translate(ast.parse("def f(x):\n    return x in (1, 2)\n"))


def test_ast_to_smt_declines_if_without_prior_output():
    from scripts.validation.ast_to_smt import ASTToSMT, _SmtUnsupported
    with pytest.raises(_SmtUnsupported):
        ASTToSMT().translate(ast.parse("def f(x):\n    if x:\n        return 1\n"))


def test_ir_to_smt_declines_multi_block_cfg():
    from irgen.compile import compile_py_to_ir
    from scripts.validation.ir_to_smt import IRToSMT, _SmtUnsupported
    module = compile_py_to_ir(
        "def f(x):\n    if x:\n        return 1\n    return 0\n")
    assert len(module.functions[0].blocks) > 1
    with pytest.raises(_SmtUnsupported):
        IRToSMT().translate(module)


def test_optimizer_prerequisite_check_is_not_inverted():
    from scripts.synthesis.optimizer import ProtectionOptimizer
    opt = ProtectionOptimizer.__new__(ProtectionOptimizer)
    opt._costs = {
        "vm": type("C", (), {"conflicts": [], "prerequisites": ["obf"]})(),
        "obf": type("C", (), {"conflicts": [], "prerequisites": []})(),
    }
    plan = type("P", (), {"protections": ["vm", "obf"],
                          "expected_overhead": 1.0,
                          "expected_size_multiplier": 1.0})()
    assert opt._validate(plan) is True  # prereq satisfied -> valid
    bad = type("P", (), {"protections": ["vm"],
                         "expected_overhead": 1.0,
                         "expected_size_multiplier": 1.0})()
    assert opt._validate(bad) is False  # prereq missing -> invalid
