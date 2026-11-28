"""Regression tests for the precision-first benchmark-harness audit (shard D2)."""
import base64
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def valid_answer():
    return {k: None for k in {
        'artifact_type', 'execution_path', 'loader_sequence', 'native_blob',
        'key_derivation', 'protection_mechanisms', 'licence_chain', 'provenance',
        'recovered_secret', 'recovered_names', 'algorithm', 'hidden_vector_ready',
        'evidence', 'uncertainty', 'claims'}}


def scored_workspace(tmp_path):
    ws = tmp_path / 'ws'
    ws.mkdir()
    (ws / 'answer.json').write_text(json.dumps(valid_answer()))
    (ws / 'artifact.py').write_text('# attacker-visible placeholder\n')
    return ws


def score_record(ws, **extra):
    rec = {
        'variant': 'absolute-native-only', 'scenario': 'static-analysis-only',
        'model': 'tokenharbor/deepseek-v4.1-flash:free', 'attempt': 1,
        'workspace': str(ws), 'returncode': 0, 'timeout': False,
        'tool_event_count': 0, 'workspace_violations': [],
        'validation': {'answer_json_exists': True, 'host_credential_leak_detected': []},
    }
    rec.update(extra)
    return rec


def test_scorer_rejects_provider_retry_and_harness_error_records(tmp_path):
    scorer = load_module('audit_d2_scorer', 're-bench/tools/score_ai_benchmark.py')
    ws = scored_workspace(tmp_path)
    assert scorer.score_result(score_record(ws))['structurally_valid'] is True
    for marker in (
        {'provider_error': {'type': 'provider.quota'}},
        {'provider_retry_errors': [{'type': 'provider.transient'}]},
        {'harness_error': 'sandbox-bridge-syntax-error-before-model-invocation'},
    ):
        assert scorer.score_result(score_record(ws, **marker))['structurally_valid'] is False


def test_final_answer_materialization_rejects_json_embedded_in_prose(tmp_path):
    bench = load_module('audit_d2_ai_bench', 're-bench/tools/ai_bench.py')
    obj = json.dumps(valid_answer())
    prose = 'Here is the answer. ' + obj + ' trailing explanation'
    assert not bench.materialize_final_answer_json(tmp_path, {'text': prose})['materialized']
    assert not (tmp_path / 'answer.json').exists()
    assert bench.materialize_final_answer_json(tmp_path, {'text': obj})['materialized']
    assert json.loads((tmp_path / 'answer.json').read_text()) == valid_answer()


def test_profile_findings_use_canonical_structural_validity(tmp_path, monkeypatch):
    mod = load_module('audit_d2_profile_findings', 're-bench/tools/analyze_profile_findings.py')
    matrix = tmp_path / 'matrix'
    (matrix / 'results').mkdir(parents=True)
    rec = {'variant': 'absolute', 'scenario': 'static-analysis-only', 'model': 'm', 'attempt': 1,
           'returncode': 0, 'timeout': False, 'validation': {'answer_json_valid': True}}
    (matrix / 'results' / 'r.json').write_text(json.dumps(rec))
    monkeypatch.setattr(mod, 'ROOT', tmp_path)
    monkeypatch.setattr(mod.scorer, 'score_result', lambda _d: {'structurally_valid': False})
    out = mod.analyze_root(matrix)
    assert out['counts'].get('valid', 0) == 0
    assert out['counts']['invalid_or_unscored'] == 1


def test_precision_analysis_excludes_supplied_native_in_source_assisted_runtime(tmp_path, monkeypatch):
    mod = load_module('audit_d2_precision', 're-bench/tools/analyze_benchmark_precision.py')
    ai = tmp_path / 'ai'
    ws = ai / 'workspaces' / 'absolute' / 'source-assisted-runtime-secrets' / 'm' / 'attempt1'
    ws.mkdir(parents=True)
    elf = b'\x7fELF' + b'A' * 16 + b'PyInit_payload' + b'B' * 16 + b'nx_apply_protections'
    (ws / 'extracted_linux.so').write_bytes(elf)
    (ws / 'answer.json').write_text('{}')
    (ai / 'results').mkdir(parents=True)
    rec = {'variant': 'absolute', 'scenario': 'source-assisted-runtime-secrets', 'model': 'm',
           'attempt': 1, 'artifact_sha256': 'x', 'validation': {}}
    (ai / 'results' / 'r.json').write_text(json.dumps(rec))
    monkeypatch.setattr(mod, 'ROOT', tmp_path)
    monkeypatch.setattr(mod, 'RAW', tmp_path / 'raw')
    monkeypatch.setattr(mod, 'AI', ai)
    monkeypatch.setattr(mod, 'OUT', ai / 'benchmark_precision_analysis.json')
    mod.main()
    row = json.loads((ai / 'benchmark_precision_analysis.json').read_text())['attempts'][0]
    assert row['raw_payload_elf_hits_including_supplied']
    assert row['payload_elf_hits'] == []
    assert row['payload_elf_recovered_in_workspace'] is False


def test_prefix_comparator_model_path_matches_harness_colon_encoding():
    mod = load_module('audit_d2_compare', 're-bench/tools/compare_prefix_postfix_crypto.py')
    assert mod.model_safe('tokenharbor/deepseek-v4.1-flash:free') == 'tokenharbor_deepseek-v4.1-flash_free'


def test_secret_scan_covers_all_license_values_and_deepseek_roots(monkeypatch):
    scan = load_module('audit_d2_secret_scan', 're-bench/tools/scan_secret_redaction.py')
    monkeypatch.setattr(scan.rbc, 'collect_license_derived_secrets', lambda: [
        ('cloud-key-material-value', 'licence-key_material'),
        ('cloud-runtime-token-value', 'licence-runtime-token'),
        ('derived-mask-value', 'licence-customer-mask'),
    ])
    assert scan.license_secret_scan_values() == [
        ('licence-key_material', 'cloud-key-material-value'),
        ('licence-runtime-token', 'cloud-runtime-token-value'),
        ('licence-customer-mask', 'derived-mask-value'),
    ]
    roots = {str(p) for p in scan.EXTRA_EVIDENCE_ROOTS}
    assert '/home/nixon/absmax-ai-workspaces-profile-matrix-deepseek-local-v12' in roots
    assert '/home/nixon/absmax-opencode-state-profile-matrix-deepseek-cloud-v13' in roots
    assert '/home/nixon/absmax-ai-workspaces-deepseek-smoke-v4' in roots


def test_endpoint_verification_includes_opencode_go_family():
    final_src = (ROOT / 're-bench/tools/final_verification_summary.py').read_text()
    smoke_src = (ROOT / 're-bench/tools/validate_minimal_endpoint_runtime.py').read_text()
    assert "'opencode-go':['evm.sock','opencode-go.sock']" in final_src
    assert "'opencode-go':{'opencode-mitm.sock','opencode-connect.sock','tokenharbor.sock','kern.sock'}" in final_src
    assert "['opencode','opencode-go','tokenharbor','kern']" in smoke_src


def test_ai_probe_extract_json_handles_multiple_objects_and_prose_boundaries():
    probe = load_module('audit_d2_ai_probe', 'pydeobsbench/ai_probe.py')
    text = 'noise {"names": ["sign"], "algorithm": "x", "secrets": [], "refused": false} middle {"nested": {"x": 1}} end'
    assert probe.extract_json(text)['names'] == ['sign']
    assert probe.extract_json('{"outer":{"inner":1}} trailing') == {'outer': {'inner': 1}}


def test_native_blob_probe_reports_licence_bound_before_derivation(tmp_path):
    import pydeobsbench.static_probes as static
    blob = base64.b64encode(b'not-a-plain-elf').decode()
    artifact = tmp_path / 'artifact.py'
    artifact.write_text('\n'.join([
        'NATIVE_BLOBS = {"linux": %r}' % blob,
        '_BLOB_S0 = "AA=="',
        '_BLOB_S1 = "AA=="',
        '_NX_BUILD_ID = "build"',
        '_NX_LICENCE_BOUND = True',
    ]))
    row = static.probe_native_blob(str(artifact), {'names': []})
    assert row['found'] is True
    assert row['derived'] is False
    assert 'licence-bound' in row['reason']


def test_cloud_negative_control_drops_inherited_runtime_secret_env(tmp_path, monkeypatch):
    mod = load_module('audit_d2_cloud_validate', 're-bench/tools/validate_cloud_profile_build.py')
    secrets = tmp_path / 'secrets'
    secrets.mkdir()
    for name in ('nx_seal_shard.hex', 'provenance.public.hex', 'runtime.licence'):
        (secrets / name).write_text('x')
    artifact = tmp_path / 'artifact.py'
    artifact.write_text('# x')
    monkeypatch.setenv('NX_SEAL_SHARD', 'inherited-shard')
    monkeypatch.setenv('NX_TABLE_SHARD', 'inherited-table')
    monkeypatch.setenv('NIXON_LICENCE', '/inherited/licence')
    monkeypatch.setenv('NIXON_PROVENANCE_PUBKEY', 'inherited-pub')
    captured = []

    class Proc:
        returncode = 1
        stdout = ''
        stderr = ''

    def fake_run(cmd, **kwargs):
        captured.append(kwargs['env'])
        return Proc()

    monkeypatch.setattr(mod.subprocess, 'run', fake_run)
    mod.runtime_control(artifact, secrets)
    assert len(captured) == 2
    assert captured[0]['NX_SEAL_SHARD'] == 'x'
    for key in ('NX_SEAL_SHARD', 'NX_TABLE_SHARD', 'NIXON_LICENCE', 'NIXON_PROVENANCE_PUBKEY'):
        assert key not in captured[1]


def test_upstream_http_error_bodies_are_redacted_before_returning_to_sandbox():
    for rel in ('re-bench/tools/tokenharbor_unix_proxy.py',
                're-bench/tools/opencode_go_unix_proxy.py',
                're-bench/tools/kern_unix_proxy.py'):
        src = (ROOT / rel).read_text()
        assert 'errbody,error_redactions' in src
        assert 'response_redactions+=error_redactions' in src
        assert src.index('errbody,error_redactions') < src.index('self.wfile.write(errbody)')


def test_native_blob_probe_decodes_current_nxs1_counter_mode(tmp_path):
    import hashlib
    import pydeobsbench.static_probes as static
    key = b'K' * 32
    build = 'build'
    mask = hashlib.sha256(build.encode()).digest()
    raw_share = bytes(b ^ mask[i % len(mask)] for i, b in enumerate(key))
    nonce = b'N' * 16
    plain = b'\x7fELF' + bytes(range(32))
    stream = bytearray()
    counter = 0
    while len(stream) < len(plain):
        stream.extend(hashlib.sha256(key + nonce + counter.to_bytes(8, 'big')).digest())
        counter += 1
    ciphertext = bytes(c ^ k for c, k in zip(plain, stream[:len(plain)]))
    packed = b'NXS1' + nonce + ciphertext
    artifact = tmp_path / 'artifact.py'
    artifact.write_text('\n'.join([
        'NATIVE_BLOBS = {"linux": %r}' % base64.b64encode(packed).decode(),
        '_BLOB_S0 = %s' % json.dumps(base64.b64encode(raw_share).decode()),
        '_BLOB_S1 = %s' % json.dumps(base64.b64encode(bytes(32)).decode()),
        '_NX_BUILD_ID = "build"',
        '_NX_LICENCE_BOUND = False',
    ]))
    row = static.probe_native_blob(str(artifact), {'names': []})
    assert row['derived'] is True
    assert row['valid_object'] is True
    assert row['elf_bytes'] == len(plain)


def test_runtime_probe_redacts_exact_runtime_secret_values():
    mod = load_module('audit_d2_runtime_probe', 're-bench/tools/runtime_probe.py')
    assert mod.redact_sensitive_text('abc shard123456 abc', ['shard123456']) == 'abc <redacted-runtime-secret> abc'


def test_configured_solution_output_scrubber_detects_and_redacts_secret():
    mod = load_module('audit_d2_configured_solution', 're-bench/tools/validate_configured_solution.py')
    secret = b'unit-test-secret'
    text, disclosed = mod.scrub_validation_output('raw unit-test-secret hex ' + secret.hex(), secret)
    assert disclosed is True
    assert 'unit-test-secret' not in text
    assert secret.hex() not in text
    assert '<redacted-configured-validation-secret>' in text
