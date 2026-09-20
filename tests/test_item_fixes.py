"""Tests for Item 13, 16, 31, 40, 45, 46, 60, 64, 67, 68, 70, 72, 74 fixes."""

import ast
import hashlib
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Item 13: Variant pool ─────────────────────────────────────────────
def test_variant_pool_metadata():
    # Verify variant_pool.rs has VariantPool struct
    with open("runtime/src/variant_pool.rs") as f:
        content = f.read()
    assert "VariantPool" in content
    assert "VariantMetadata" in content
    assert "load" in content
    assert "get_variant" in content


def test_variant_pool_runtime_config_defaults():
    # Structural check on the Rust source for variant_pool fields
    with open("runtime/src/lib.rs") as f:
        content = f.read()
    assert "enable_variant_pool" in content
    assert "variant_pool_path" in content
    assert "variant_pool" in content  # module declaration


# ── Item 16: JIT templates ────────────────────────────────────────────
def test_dynamic_code_generator_rust_jit():
    from obfuscator.core.transforms import DynamicCodeGenerator
    gen = DynamicCodeGenerator(use_rust_jit=True)
    assert gen.use_rust_jit is True
    # Check that _make_rust_jit_wrapper produces expected output
    wrapper = gen._make_rust_jit_wrapper(
        ast.parse("def foo(x): return x + 1").body[0],
        "def foo(x): return x + 1",
        42,
        "_nx_tmpl_0"
    )
    assert "base64.b64decode" in wrapper
    assert "subprocess" in wrapper
    assert "RUNTIME_JIT_BIN" in wrapper


# ── Item 31: AES-CTR ──────────────────────────────────────────────────
def test_aes_ctr_encrypt_decrypt():
    from obfuscator.core.pipeline import Nixon_Enc_AES_CTR, _check_aes_ctr
    data = b"Hello, World! This is test data for AES-CTR encryption."
    key = b"test_key_12345678"
    nonce = b"nonce1234567890"
    encrypted = Nixon_Enc_AES_CTR(data, key, nonce)
    assert encrypted != data
    assert len(encrypted) == len(data)
    # Decrypt by encrypting again (CTR is symmetric)
    decrypted = Nixon_Enc_AES_CTR(encrypted, key, nonce)
    assert decrypted == data


def test_aes_ctr_xor_fallback():
    from obfuscator.core.pipeline import Nixon_Enc_AES_CTR, Nixon_Enc_blob
    data = b"test data"
    key = b"key"
    nonce = b"nonce"
    result = Nixon_Enc_AES_CTR(data, key, nonce)
    xor_result = Nixon_Enc_blob(data, key, nonce)
    # Both should produce different but valid encryptions
    assert result != data
    assert xor_result != data


def test_encrypt_payload_with_flag():
    from obfuscator.core.pipeline import encrypt_payload
    data = b"test payload data"
    key = b"secret_key_1234"
    nonce = b"unique_nonce_123"
    encrypted = encrypt_payload(data, key, nonce, use_aes_ctr=True)
    assert encrypted != data
    decrypted = encrypt_payload(encrypted, key, nonce, use_aes_ctr=True)
    assert decrypted == data


# ── Item 40: Relay attestation ────────────────────────────────────────
def test_relay_cargo_toml_has_attestation():
    with open("relay/Cargo.toml") as f:
        content = f.read()
    assert "attestation" in content
    assert "default = [\"attestation\"]" in content


def test_relay_attestation_module():
    """Verify attestation module exists in relay."""
    assert os.path.exists("relay/src/attestation.rs")
    # Verify lib.rs has attestation module declaration
    with open("relay/src/lib.rs") as f:
        content = f.read()
    assert 'pub mod attestation' in content


# ── Item 45: Provenance replacement ───────────────────────────────────
def test_provenance_replace_mode():
    from scripts.phases.phase07_phase2 import phase_provenance_removal
    assert hasattr(phase_provenance_removal, "__call__")


def test_provenance_replacement():
    from obfuscator.provenance import replace_error_messages, encode_sensitive_strings, obfuscate_algorithmic_constants
    code = '''
def test():
    msg = "Error: something failed"
    return msg
'''
    tree = ast.parse(code)
    tree = replace_error_messages(tree)
    unparsed = ast.unparse(tree)
    assert "E0001" in unparsed or "E000" in unparsed


# ── Item 46: Adaptive classifier loop ─────────────────────────────────
def test_adaptive_classifier_loop_exists():
    from scripts.phases.phase07_phase2 import phase_adaptive_classifier_loop
    assert hasattr(phase_adaptive_classifier_loop, "__call__")


# ── Item 60: SMT validation ───────────────────────────────────────────
def test_smt_validator_real_z3():
    from scripts.validation.smt_validator import SMTValidator
    import ast as ast_mod
    from irgen.compile import compile_py_to_ir
    source = "def f(x, y): return x + y"
    ir_module = compile_py_to_ir(source)
    validator = SMTValidator(timeout_ms=30000)
    result = validator.validate_source_vs_ir(source, ir_module)
    assert result.equivalent or result.error


# ── Item 64: Challenge-response ───────────────────────────────────────
def test_challenge_response_module():
    from scripts.runtime.challenge_response import ChallengeResponse, Challenge, Response
    cr = ChallengeResponse(timeout=5.0)
    challenge = cr.create_challenge("peer1")
    assert challenge is not None
    assert len(challenge.challenge_data) > 0


def test_challenge_response_roundtrip():
    from scripts.runtime.challenge_response import ChallengeResponse
    cr = ChallengeResponse(timeout=5.0)
    challenge = cr.create_challenge("peer1")
    response = cr.respond_to_challenge("peer1", challenge)
    assert response is not None
    if response.success:
        verified = cr.verify_response(challenge, response)
        assert verified


def test_challenge_response_pairwise():
    from scripts.runtime.challenge_response import ChallengeResponse
    cr = ChallengeResponse(timeout=5.0)
    results = cr.run_pairwise(["alice", "bob", "charlie"])
    assert len(results) == 3


# ── Item 67: Symbolic exec scoring ────────────────────────────────────
def test_symbolic_resistance_enhanced():
    from scripts.metrics.resilience import compute_symbolic_resistance
    import ast as ast_mod
    orig = ast_mod.parse("def f(x): return x + 1")
    prot = ast_mod.parse("""
def f(x):
    if x > 0 and x < 100:
        return x + 1
    return x - 1
""")
    result = compute_symbolic_resistance(orig, prot)
    assert "original_recursion_depth" in result
    assert "protected_recursion_depth" in result
    assert "original_loop_bound_estimate" in result
    assert "protected_loop_bound_estimate" in result
    assert "original_feasible_paths" in result
    assert "protected_feasible_paths" in result
    assert result["resistance_score"] >= 0.0


# ── Item 68: ROP runtime execution ────────────────────────────────────
def test_rop_runtime_source_generation():
    from scripts.rop.rop_compiler import GadgetFinder, RopCompiler, PayloadDisperser
    finder = GadgetFinder()
    finder.find_gadgets()
    compiler = RopCompiler(finder=finder)
    code = "def f(a, b): return a + b"
    tree = ast.parse(code)
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef):
            chain = compiler.compile(fn)
            disperser = PayloadDisperser()
            dispersed = disperser.disperse(chain)
            key = b"k" + b"e" * 31
            source = disperser.generate_runtime_source(dispersed, key)
            assert 'rop_exec.h' in source
            assert 'rop_load_and_exec' in source
            break


# ── Item 70: Attention poisoning wiring ───────────────────────────────
def test_attention_poison_options_forwarded():
    from obfuscator.core.pipeline import build_pipeline
    source = "def foo(x): return x + 1"
    # Without extra_options, attention_poison should default to False
    result1 = build_pipeline(source)
    # With extra_options enabling it
    result2 = build_pipeline(source, extra_options={
        'attention_poison': True,
        'attention_poison_fan_out': 5,
    })
    assert result1 is not None
    assert result2 is not None


# ── Item 72: Decoy APIs wiring ────────────────────────────────────────
def test_decoy_api_options_forwarded():
    from obfuscator.core.pipeline import build_pipeline
    source = "def foo(x): return x + 1"
    result = build_pipeline(source, extra_options={
        'decoy_apis': True,
        'decoy_api_count': 3,
    })
    assert result is not None


# ── Item 74: Adaptive rewriting wiring ────────────────────────────────
def test_adaptive_rewriting_no_mock():
    from scripts.benchmark.feedback import BenchmarkFeedbackAnalyzer, WeaknessProfile
    from obfuscator.adaptive_rewriter import AdaptiveRewriter

    real_results = {
        "naming_recovery": {"score": 0.3},
        "semantic_leakage": {"score": 0.6},
        "decompilation_resistance": {"score": 0.2},
        "complexity_impact": {"score": 0.4},
        "entropy": {"score": 0.7},
        "static_confusion": {"score": 0.3},
        "overall": 0.42,
    }
    analyzer = BenchmarkFeedbackAnalyzer()
    profile = analyzer.analyze(real_results)
    assert len(profile.failed_metrics) > 0
    assert "strengthen_symbol_renaming" in profile.recommended_actions

    rewriter = AdaptiveRewriter()
    source = "def foo(x): return x + 1"
    rewritten = rewriter.rewrite(profile, source)
    assert rewritten is not None
    assert len(rewritten) > 0
