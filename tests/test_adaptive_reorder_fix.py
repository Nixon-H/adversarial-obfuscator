"""Tests for adaptive_rewriter exec/eval + reorder >256 fixes (items 6-8)."""
import ast

from obfuscator.adaptive_rewriter import AdaptiveRewriter
from obfuscator.reorder_pack import _SeededRng, pack_container, unpack_container


def _make_rewriter(tmp_path):
    return AdaptiveRewriter(history_path=str(tmp_path / "hist.json"))


def test_exec_eval_emits_str_and_runs(tmp_path):
    rw = _make_rewriter(tmp_path)
    tree = ast.parse("def f():\n    x = 1\n    return x\n")
    out = rw._inject_exec_eval(tree)
    out = ast.fix_missing_locations(out)
    ns = {}
    exec(compile(out, "<test>", "exec"), ns)
    assert ns["f"]() == 1
    dumped = ast.dump(out)
    assert "decode" in dumped  # .decode() present on b64decode result


def test_duplicate_dispatch_skips_impure(tmp_path):
    rw = _make_rewriter(tmp_path)
    src = "def f():\n    x.append(1)\n    return x\n"
    tree = ast.parse(src)
    before = len(tree.body[0].body)
    out = rw._duplicate_dispatch(tree)
    assert len(out.body[0].body) == before  # unchanged: impure body


def test_duplicate_dispatch_pure_ok(tmp_path):
    rw = _make_rewriter(tmp_path)
    tree = ast.parse("def f():\n    pass\n    'doc'\n")
    out = rw._duplicate_dispatch(tree)
    assert len(out.body[0].body) == 4  # pure body duplicated harmlessly


def test_randbelow_large_n_terminates():
    rng = _SeededRng(b"seed")
    for _ in range(300):
        v = rng.randbelow(300)
        assert 0 <= v < 300
    rng2 = _SeededRng(b"seed2")
    vals = {rng2.randbelow(1000) for _ in range(200)}
    assert len(vals) > 50  # spread, not stuck


def test_pack_roundtrip_many_chunks():
    blobs = [bytes(300 * 8)]
    pack = pack_container(blobs, b"seed", chunk_size=8)
    assert len(pack["order"]) == 300  # > 256 chunks exercises 2-byte path
    assert unpack_container(pack) == blobs
