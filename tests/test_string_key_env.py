"""String sealing must not be a self-contained puzzle.

Benchmark 2026-11-17 (DS 4.1 Flash via Mistral, `mistral/deepseek-v4-1-flash-1017`):

The default string-seal mode ships the 32-byte key AND the decoder in the
artefact. The model read the code and said, verbatim:

    "I'll decrypt the embedded constants by extracting the decryption
     routine and running it in a sandboxed way."

...then recovered all 4 secrets. Source-level encryption whose key travels
with the ciphertext only defeats `grep`; it does not defeat an analyst who
can execute code.

`string_key_env` derives the seal key from an environment shard, so the
artefact alone cannot be decrypted. Measured: same payload, same model,
same prompt —

    inline key : runs without shard, 4/4 secrets recovered
    keyless    : refuses to run,       0/4 secrets recovered
"""
import os
import subprocess
import sys

import pytest

from obfuscator.core.pipeline import ObfuscationTransformer

SHARD_VAR = "NX_TEST_SEAL_SHARD"
# Synthetic fixture values for the payload UNDER TEST, not credentials for
# anything. They are spelled "fixture_..." so neither a scanner nor a reader
# can mistake them for live keys -- the earlier "wt_live_"/"pg_prod_" shapes
# were realistic on purpose and tripped the hardcoded-credential rule, which
# is exactly what a real leak would look like.
SECRETS = ["fixture_api_token_8f3a91c2d7e04b56",
           "fixture_db_password_9911", "fixture-salt-2026-11"]

SOURCE = (
    'API_TOKEN = "fixture_api_token_8f3a91c2d7e04b56"\n'
    'DB_PASSWORD = "fixture_db_password_9911"\n'
    'SALT = b"fixture-salt-2026-11"\n'
    '\n'
    'def main():\n'
    '    print("OK", len(API_TOKEN), len(DB_PASSWORD), len(SALT))\n'
    '\n'
    'if __name__ == "__main__":\n'
    '    main()\n'
)

_ON = ["cfg_flatten", "opaque_predicates", "bogus_exceptions", "mba_subs",
       "fragment_strings", "unicode_ids", "symbol_rename", "strip_meta",
       "split_vars", "unfold_constants", "enhanced_junk", "break_decompiler",
       "code_checksums", "obf_calls", "exception_flow", "residue_random"]


def _build(keyless: bool) -> str:
    o = {k: True for k in _ON}
    if keyless:
        os.environ[SHARD_VAR] = "c" * 64
        o["string_key_env"] = SHARD_VAR
    out = ObfuscationTransformer(seed=4242).transform(SOURCE, options=o)
    if isinstance(out, tuple):
        out = out[0]
    return out


def _run(src_text, env=None):
    p = subprocess.run([sys.executable, "-c", src_text], capture_output=True,
                       text=True, timeout=180, env=env or dict(os.environ))
    return p


def test_inline_key_mode_ships_no_plaintext_secrets():
    """Even the default hides the literals from grep (that part works)."""
    out = _build(keyless=False)
    for s in SECRETS:
        assert s not in out


def test_keyless_mode_is_undecryptable_without_the_shard():
    out = _build(keyless=True)
    env = dict(os.environ)
    env.pop(SHARD_VAR, None)
    p = _run(out, env)
    assert p.returncode != 0, "the keyless artefact ran without its shard"
    assert "OK" not in p.stdout
    # the failure names the reason rather than dying silently
    assert "KEK" in (p.stdout + p.stderr) or "shard" in (p.stdout + p.stderr).lower()


def test_keyless_mode_runs_with_the_shard():
    out = _build(keyless=True)
    env = dict(os.environ, **{SHARD_VAR: "c" * 64})
    p = _run(out, env)
    assert p.returncode == 0, p.stderr[-500:]
    assert "OK" in p.stdout


def test_keyless_mode_references_the_env_var():
    out = _build(keyless=True)
    assert SHARD_VAR in out, (
        "the keyless build must read the shard at run time")


def test_build_cli_exposes_string_key_env_via_transforms():
    """The flag lives in --transforms, per the CLI consolidation rule.

    A standalone `--string-key-env` on `build` is REJECTED by design
    (tests/test_unified_flags.py asserts per-knob spellings stay removed),
    so the keyless mode is reached as `--transforms string-key-env=NAME`.
    """
    from obfuscator.core.pipeline import apply_unified_specs, build_parser
    parser, _ = build_parser()
    a = apply_unified_specs(parser.parse_args(["build", "x.py"]))
    assert a.tx_string_key_env is None, "keyless mode must be opt-in"
    a2 = apply_unified_specs(parser.parse_args(
        ["build", "x.py", "--transforms", "string-key-env=NX_SHARD"]))
    assert a2.tx_string_key_env == "NX_SHARD"
    # the standalone spelling must stay rejected
    with pytest.raises(SystemExit):
        parser.parse_args(["build", "x.py", "--string-key-env", "X"])


# --- the BUILD path must honour it (audit 2026-11-17) -----------------------

def test_fallback_opts_carry_the_shard():
    """The dict that compiles the SHIPPED payload must carry string_key_env.

    `fallback_opts` is what builds the sectioned artefact's payload. It had
    fragment_strings=True but no string_key_env, so --transforms
    string-key-env=... was accepted, validated, and then ignored: the
    artefact ran without the shard because the seals used the inline key.
    """
    import inspect
    import obfuscator.core.pipeline as pl
    src = inspect.getsource(pl.build_project)
    i = src.find("fallback_opts = {")
    j = src.find("}", i)
    block = src[i:j]
    assert "string_key_env" in block, (
        "fallback_opts lost string_key_env: the sectioned build's payload "
        "would be sealed with the inline key and ignore the shard")
    assert "fragment_strings" in block


def test_native_path_applies_the_ast_layer():
    """build_local_cython must take ast_opts and apply them.

    It compiled RAW source with no options at all, so the native module --
    the artefact that ships -- ignored every --transforms pass.
    """
    import inspect
    import obfuscator.core.pipeline as pl
    sig = inspect.signature(pl.build_local_cython)
    assert "ast_opts" in sig.parameters, (
        "build_local_cython lost its ast_opts parameter: the native module "
        "would be compiled from raw source")
    body = inspect.getsource(pl.build_local_cython)
    assert "apply_ast_mutation" in body, (
        "build_local_cython no longer applies the AST layer")
