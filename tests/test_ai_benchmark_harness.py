"""Regression tests for benchmark harness isolation controls."""
import importlib.util

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    if not path.exists():
        pytest.skip(f"benchmark harness tool is outside the Docker build context: {path.name}")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_tool_text(filename):
    path = ROOT / 're-bench/tools' / filename
    if not path.exists():
        pytest.skip(f"benchmark harness tool is outside the Docker build context: {filename}")
    return path.read_text()


def test_bridge_snapshot_is_per_attempt_copy(tmp_path):
    bench = _load('ai_bench_harness', ROOT / 're-bench/tools/ai_bench.py')
    state = tmp_path / 'attempt-state'
    state.mkdir()
    copied = bench.snapshot_bridge(state)
    assert copied == state / 'sandbox_tokenharbor_bridge.py'
    assert copied.read_bytes() == (ROOT / 're-bench/tools/sandbox_tokenharbor_bridge.py').read_bytes()
    assert copied != ROOT / 're-bench/tools/sandbox_tokenharbor_bridge.py'


def test_agent_chain_bridge_is_read_only():
    bridge = _load('sandbox_bridge', ROOT / 're-bench/tools/sandbox_tokenharbor_bridge.py')
    assert 'eth_call' in bridge.EVM_READ_ONLY_METHODS
    assert 'eth_chainId' in bridge.EVM_READ_ONLY_METHODS
    assert 'eth_sendTransaction' not in bridge.EVM_READ_ONLY_METHODS
    assert 'eth_sendRawTransaction' not in bridge.EVM_READ_ONLY_METHODS


def test_resume_watchdog_uses_unused_attempt_numbers_and_prioritises_zero_valid():
    resume = _load('resume_watchdog', ROOT / 're-bench/tools/resume_absmax_benchmark_when_quota.py')
    groups = {
        ('absolute-native-only', 'binary-only-external'): {
            'valid': 4, 'needed': 1, 'used_attempts': set(range(1, 11)), 'records': 10},
        ('absolute-native-only', 'legitimate-runtime-secrets'): {
            'valid': 0, 'needed': 5, 'used_attempts': set(range(1, 11)), 'records': 10},
        ('absolute', 'runtime-secrets-withheld'): {
            'valid': 0, 'needed': 5, 'used_attempts': {1, 2, 4}, 'records': 3},
    }
    scenarios = ['binary-only-external', 'legitimate-runtime-secrets', 'runtime-secrets-withheld']
    jobs = resume.choose_jobs(groups, ['absolute-native-only', 'absolute'], scenarios, 6, 5)
    assert jobs
    assert jobs[0][1] == 'legitimate-runtime-secrets'
    for _variant, _scenario, _model, attempt in jobs:
        assert attempt not in set(range(1, 11)) or attempt in {3, 5}
    assert all(attempt >= 11 for _v, scenario, _m, attempt in jobs if scenario == 'legitimate-runtime-secrets')
    assert any(attempt == 3 for _v, scenario, _m, attempt in jobs if scenario == 'runtime-secrets-withheld')


def test_resume_watchdog_next_attempt_never_reuses_existing_evidence_label():
    resume = _load('resume_watchdog_next', ROOT / 're-bench/tools/resume_absmax_benchmark_when_quota.py')
    assert resume.next_attempt(set()) == 1
    assert resume.next_attempt({1, 2, 4}) == 3
    assert resume.next_attempt(set(range(1, 11))) == 11


def test_hy4_legitimate_secrets_fail_closed_without_redacting_lane(tmp_path, monkeypatch):
    bench = _load('ai_bench_harness_hy4_guard', ROOT / 're-bench/tools/ai_bench.py')
    monkeypatch.setattr(bench, 'hy4_redacting_lane_ready', lambda: False)
    monkeypatch.setattr(bench, 'OUT', tmp_path / 'bench-out')
    def forbidden_prep(*args):
        raise AssertionError('workspace preparation must not copy runtime secrets when the redacting lane is unavailable')
    monkeypatch.setattr(bench, 'prep_workspace', forbidden_prep)
    result = bench.one(('absolute-native-only', 'legitimate-runtime-secrets', 'opencode/hy4-flash-free', 99))
    assert result['harness_error'] == 'hy4-legitimate-runtime-secrets-blocked-unredacted-tls'
    assert result['returncode'] is None
    assert result['validation']['answer_valid'] is False


def test_opencode_mitm_addon_exact_redaction():
    pytest.importorskip('mitmproxy')
    addon = _load('opencode_mitm_addon_test', ROOT / 're-bench/tools/opencode_mitm_addon.py')
    secret = b'abc123secret456789'
    redacted, counts = addon.redact_bytes(b'prefix abc123secret456789 suffix', [('unit-test-secret', secret)])
    assert redacted == b'prefix <redacted-absmax-runtime-secret> suffix'
    assert counts == {'unit-test-secret': 1}


def test_secret_candidate_prefilter_supports_multiline_values(tmp_path):
    rbc = _load('redact_benchmark_credentials_multiline', ROOT / 're-bench/tools/redact_benchmark_credentials.py')
    secret = '-----BEGIN TEST KEY-----\nabcdefgh12345678\n-----END TEST KEY-----'
    evidence = tmp_path / 'evidence.txt'
    evidence.write_text('prefix\n' + secret + '\nsuffix\n')
    found = rbc.secret_candidate_files(tmp_path, [('dummy-test', secret)])
    rx, _mapping = rbc.compile_secret_matcher([('dummy-test', secret)])
    assert found == {str(evidence.resolve())}
    assert rx is not None and rx.findall(evidence.read_bytes())


def test_extra_evidence_redaction_preserves_public_hwid_but_redacts_secret(tmp_path):
    rbc = _load('redact_benchmark_credentials_skip_hwid', ROOT / 're-bench/tools/redact_benchmark_credentials.py')
    evidence = tmp_path / 'evidence.txt'
    evidence.write_text('hwid12345678plusSECRETXYZ123')
    stats = rbc.redact_tree(
        tmp_path,
        [('licence-hwid', 'hwid12345678'), ('unit-secret', 'SECRETXYZ123')],
        skip_labels={'licence-hwid'},
    )
    sanitised = evidence.read_text()
    assert 'hwid12345678' in sanitised
    assert 'SECRETXYZ123' not in sanitised
    assert stats['files_changed'] == 1
    assert stats['skipped_replacements']['licence-hwid'] == 1


def test_opencode_config_secret_field_audit_classifies_dummy_and_literal():
    audit = _load('opencode_config_secret_field_audit_test', ROOT / 're-bench/tools/audit_opencode_config_secret_fields.py')
    rows = audit.walk({
        'provider': {'tokenharbor': {'options': {'apiKey': 'credential-isolated-local-proxy'}}},
        'providers': {
            'example': {'settings': {'apiKey': 'literal-secret-value-123'}},
            'env': {'settings': {'apiKey': '{env:EXAMPLE_API_KEY}'}},
            'redacted': {'settings': {'apiKey': '<redacted-example>'}},
        },
    })
    states = {row['field_path']: row['state'] for row in rows}
    assert states['provider.tokenharbor.options.apiKey'] == 'intentional-local-proxy-dummy'
    assert states['providers.example.settings.apiKey'] == 'literal-sensitive-value'
    assert states['providers.env.settings.apiKey'] == 'environment-reference'
    assert states['providers.redacted.settings.apiKey'] == 'redacted-placeholder'


def test_opencode_connect_compatibility_relay_uses_redacting_mitm_backend():
    source = _read_tool_text('opencode_connect_relay.py')
    assert "('127.0.0.1',9898)" in source
    assert 'connected-via-redacting-mitm' in source
    assert 'CONNECT {host}:{port} HTTP/1.1' in source


def test_sandbox_bridge_prefers_redacting_mitm_socket_for_connect():
    source = _read_tool_text('sandbox_tokenharbor_bridge.py')
    assert 'opencode-mitm.sock' in source
    assert 'pipe_unix_client(conn,mitm_sock)' in source


def test_copied_workspace_sanitizes_license_derived_keys(tmp_path):
    bench = _load('ai_bench_harness_sanitize', ROOT / 're-bench/tools/ai_bench.py')
    rbc = _load('redact_benchmark_credentials_test', ROOT / 're-bench/tools/redact_benchmark_credentials.py')
    derived = [(val, label) for val, label in rbc.collect_license_derived_secrets()
               if label == 'licence-effective-native-key' and val]
    if not derived:
        pytest.skip('benchmark licence-derived secret fixtures are unavailable')
    val, _label = derived[0]
    raw = tmp_path / 'raw-workspace'
    raw.mkdir()
    (raw / 'opencode.events.jsonl').write_text('prefix ' + val + ' suffix')
    bench.sanitize_copied_workspace(raw, 'absolute-native-only')
    sanitised = (raw / 'opencode.events.jsonl').read_text()
    assert val not in sanitised
    assert '<redacted-licence-effective-native-key>' in sanitised


def test_opencode_binary_mount_does_not_expose_full_opencode_home():
    source = _read_tool_text('ai_bench.py')
    assert "'--ro-bind','/home/nixon/.opencode','/home/nixon/.opencode'" not in source
    assert "'--ro-bind','/home/nixon/.opencode/bin','/home/nixon/.opencode/bin'" in source


def test_scorer_handles_fail_closed_no_workspace_records():
    scorer = _load('score_ai_benchmark_test', ROOT / 're-bench/tools/score_ai_benchmark.py')
    out = scorer.score_result({'workspace': None, 'returncode': None, 'timeout': False, 'validation': {}, 'harness_error': 'hy4-legitimate-runtime-secrets-blocked-unredacted-tls'})
    assert out['structurally_valid'] is False
    assert out['failure_category'] == 'harness-blocked-before-workspace'


def test_payload_elf_scan_detects_python_base64_embedding(tmp_path):
    import base64
    scorer = _load('score_ai_benchmark_encoded_scan', ROOT / 're-bench/tools/score_ai_benchmark.py')
    payload = b'\x7fELF' + b'A' * 32 + b'PyInit_payload' + b'B' * 32 + b'nx_apply_protections'
    encoded = base64.b64encode(payload).decode()
    # Repeat a valid base64 unit enough times to cross the large-literal threshold;
    # concatenated repetitions still begin with the same marker-bearing ELF prefix.
    encoded *= 20
    (tmp_path / 'solution.py').write_text('_BLOB_B64 = "' + encoded + '"\n')
    hits = scorer.scan_payload_elfs(tmp_path)
    assert any(h.get('encoding') == 'python-base64-string' and h.get('path') == 'solution.py' for h in hits)


def test_prefix_postfix_comparator_uses_model_specific_workspace_paths():
    source = _read_tool_text('compare_prefix_postfix_crypto.py')
    assert 'model_safe(d.get(\'model\'))' in source
    assert "MODEL_SAFE='tokenharbor_deepseek-v4.1-flash-1017'" not in source


def test_prefix_postfix_comparator_detects_python_base64_embedding(tmp_path):
    import base64
    cmpmod = _load('compare_prefix_postfix_crypto_test', ROOT / 're-bench/tools/compare_prefix_postfix_crypto.py')
    payload = b'\x7fELF' + b'A' * 32 + b'PyInit_payload' + b'B' * 32 + b'nx_apply_protections'
    encoded = base64.b64encode(payload).decode() * 20
    (tmp_path / 'solution.py').write_text('_BLOB_B64 = "' + encoded + '"\n')
    hits = cmpmod.scan_payload_elfs(tmp_path)['payload_elf_hits']
    assert any(h.get('encoding') == 'python-base64-string' and h.get('path') == 'solution.py' for h in hits)


def test_copied_workspace_redacts_json_escaped_licence_and_signature(tmp_path):
    import json
    bench = _load('ai_bench_harness_licence_redaction', ROOT / 're-bench/tools/ai_bench.py')
    sec = ROOT / 're-bench/secrets/absolute-native-only/cipher/runtime.licence'
    if not sec.exists():
        pytest.skip('benchmark runtime licence fixture is unavailable')
    raw = sec.read_text().strip()
    lic = json.loads(raw)
    sig = lic.get('sig')
    if not sig:
        pytest.skip('benchmark runtime licence fixture has no signature')
    raw_ws = tmp_path / 'raw-workspace'
    raw_ws.mkdir()
    (raw_ws / 'opencode.events.jsonl').write_text(json.dumps({'tool_output': raw}) + '\n')
    bench.sanitize_copied_workspace(raw_ws, 'absolute-native-only')
    sanitised = (raw_ws / 'opencode.events.jsonl').read_text()
    assert sig not in sanitised
    assert json.dumps(raw)[1:-1] not in sanitised
    assert '<redacted-runtime-licence>' in sanitised


def test_resume_watchdog_hy4_free_limit_cooldown_uses_retry_after(tmp_path):
    import json, time
    resume = _load('resume_watchdog_cooldown', ROOT / 're-bench/tools/resume_absmax_benchmark_when_quota.py')
    results = tmp_path / 'results'
    results.mkdir()
    rec = {'provider_error': {'type': 'provider.free-limit', 'message': 'Free usage limit reached', 'retryAfterMs': 60000}}
    path = results / 'absolute-native-only__crypto-construction__opencode_hy4-flash-free__a1.json'
    path.write_text(json.dumps(rec))
    now = time.time()
    # Make the record look recent regardless of filesystem timestamp granularity.
    import os
    os.utime(path, (now, now))
    cd = resume.hy4_free_limit_cooldown(tmp_path)
    assert cd['active'] is True
    assert 1 <= cd['remaining_seconds'] <= 60
    assert cd['latest_free_limit']['retry_after_ms'] == 60000


def test_scorer_classifies_hy4_free_limit_as_provider_limit(tmp_path):
    scorer = _load('score_ai_benchmark_free_limit', ROOT / 're-bench/tools/score_ai_benchmark.py')
    out = scorer.score_result({'workspace': str(tmp_path), 'returncode': 1, 'timeout': False, 'validation': {}, 'provider_error': {'type': 'provider.free-limit'}})
    assert out['failure_category'] == 'provider-free-usage-limit'


def test_scorer_prefers_preserved_copied_workspace(tmp_path, monkeypatch):
    import json
    scorer = _load('score_ai_benchmark_copied_precedence', ROOT / 're-bench/tools/score_ai_benchmark.py')
    model = 'opencode/hy4-flash-free'
    safe = model.replace('/', '_').replace(':', '_')
    outroot = tmp_path / 'out'
    copied = outroot / 'workspaces/absolute-native-only/binary-only-external' / safe / 'attempt1'
    copied.mkdir(parents=True)
    keys = ['artifact_type', 'execution_path', 'loader_sequence', 'native_blob', 'key_derivation', 'protection_mechanisms', 'licence_chain', 'provenance', 'recovered_secret', 'recovered_names', 'algorithm', 'hidden_vector_ready', 'evidence', 'uncertainty', 'claims']
    (copied / 'answer.json').write_text(json.dumps({k: '' for k in keys}))
    live = tmp_path / 'live'
    live.mkdir()
    monkeypatch.setattr(scorer, 'OUT', outroot)
    rec = {'workspace': str(live), 'variant': 'absolute-native-only', 'scenario': 'binary-only-external', 'model': model, 'attempt': 1, 'returncode': 0, 'timeout': False, 'validation': {'answer_json_exists': True}}
    assert scorer.score_result(rec)['structurally_valid'] is True


def test_scorer_rejects_attempts_over_twenty_tool_calls(tmp_path):
    import json
    scorer = _load('score_ai_benchmark_tool_limit', ROOT / 're-bench/tools/score_ai_benchmark.py')
    keys = ['artifact_type', 'execution_path', 'loader_sequence', 'native_blob', 'key_derivation', 'protection_mechanisms', 'licence_chain', 'provenance', 'recovered_secret', 'recovered_names', 'algorithm', 'hidden_vector_ready', 'evidence', 'uncertainty', 'claims']
    (tmp_path / 'answer.json').write_text(json.dumps({k: '' for k in keys}))
    out = scorer.score_result({'workspace': str(tmp_path), 'returncode': 0, 'timeout': False, 'tool_event_count': 21, 'validation': {'answer_json_exists': True}, 'variant': 'absolute-native-only', 'scenario': 'binary-only-external', 'model': 'opencode/hy4-flash-free', 'attempt': 99})
    assert out['structurally_valid'] is False
    assert out['failure_category'] == 'tool-call-limit-exceeded'


def test_benchmark_prompt_states_hard_twenty_tool_validity_limit():
    source = _read_tool_text('ai_bench.py')
    assert 'Hard validity timebox: use at most 20 tool invocations' in source
    assert 'more than 20 tool invocations is structurally invalid' in source


def test_repair_skips_fail_closed_records_without_workspace(tmp_path):
    import hashlib, json
    repair = _load('repair_copied_artifacts_test', ROOT / 're-bench/tools/repair_copied_artifacts.py')
    artifact = ROOT / 're-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/builds/absolute-native-only/cipher/artifact.py'
    if not artifact.exists():
        pytest.skip('authoritative artifact fixture is unavailable')
    root = tmp_path / 'bench'
    (root / 'results').mkdir(parents=True)
    rec = {
        'variant': 'absolute-native-only',
        'scenario': 'legitimate-runtime-secrets',
        'model': 'opencode/hy4-flash-free',
        'attempt': 1,
        'artifact_sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
        'workspace': None,
        'harness_error': 'hy4-legitimate-runtime-secrets-blocked-unredacted-tls',
    }
    (root / 'results/a1.json').write_text(json.dumps(rec))
    out = repair.repair_root(root)
    assert out['errors'] == []
    assert len(out['skipped_no_workspace']) == 1
    assert out['copies'] == 0


def test_scorer_counts_unique_tool_invocations_from_preserved_events(tmp_path):
    import json
    scorer = _load('score_ai_benchmark_event_tool_count', ROOT / 're-bench/tools/score_ai_benchmark.py')
    keys = ['artifact_type', 'execution_path', 'loader_sequence', 'native_blob', 'key_derivation', 'protection_mechanisms', 'licence_chain', 'provenance', 'recovered_secret', 'recovered_names', 'algorithm', 'hidden_vector_ready', 'evidence', 'uncertainty', 'claims']
    (tmp_path / 'answer.json').write_text(json.dumps({k: '' for k in keys}))
    events = []
    for i in range(21):
        events.append({'type': 'tool_use', 'part': {'partID': f'prt-{i}', 'type': 'tool', 'tool': 'shell', 'state': {'input': {'command': 'true'}, 'status': 'completed'}}})
    # A repeated update for the same part must not be double-counted, but the
    # 21 unique invocations above still exceed the hard validity limit.
    events.append(events[-1])
    (tmp_path / 'opencode.events.jsonl').write_text('\n'.join(json.dumps(x) for x in events) + '\n')
    out = scorer.score_result({'workspace': str(tmp_path), 'returncode': 0, 'timeout': False, 'tool_event_count': 0, 'validation': {'answer_json_exists': True}, 'variant': 'absolute-native-only', 'scenario': 'binary-only-external', 'model': 'opencode/hy4-flash-free', 'attempt': 99})
    assert out['structurally_valid'] is False
    assert out['failure_category'] == 'tool-call-limit-exceeded'
    assert out['tool_invocations'] == 21
    assert out['tool_invocation_source'] == 'opencode.events.jsonl'


def test_renderer_reports_overlimit_and_elf_precision_boundaries():
    source = _read_tool_text('render_benchmark_report.py')
    assert 'Security-relevant over-limit evidence (unscored)' in source
    assert 'payload_elf_recovered_in_workspace' in source
    assert 'raw_payload_elf_hits_including_supplied' in source
    assert 'Payload plaintext/semantic recovery' in source
    assert 'Payload ELF recovery excluding scenario-supplied native evidence' in source


def test_renderer_lists_zero_record_authorised_free_lane():
    source = _read_tool_text('render_benchmark_report.py')
    assert "authorised_models={" in source
    assert "'tokenharbor/deepseek-v4.1-flash:free'" in source
    assert '| authorised_models' in source
    assert 'zero records is still listed' in source


def test_host_evm_unix_proxy_enforces_read_only_at_socket(monkeypatch):
    import json, socket, threading
    proxy = _load('evm_readonly_unix_proxy_test', ROOT / 're-bench/tools/evm_readonly_unix_proxy.py')

    class FakeUpstream:
        def __init__(self):
            self.sent = b''
            body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'result': '0x1'}).encode()
            self.response = (b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: '
                             + str(len(body)).encode() + b'\r\nConnection: close\r\n\r\n' + body)
        def sendall(self, data):
            self.sent += data
        def recv(self, n):
            if not self.response:
                return b''
            out, self.response = self.response[:n], self.response[n:]
            return out
        def close(self):
            pass

    upstreams = []
    def fake_create_connection(*args, **kwargs):
        upstream = FakeUpstream()
        upstreams.append(upstream)
        return upstream
    monkeypatch.setattr(proxy.socket, 'create_connection', fake_create_connection)

    def roundtrip(method):
        client, server = socket.socketpair()
        thread = threading.Thread(target=proxy.handle, args=(server,), daemon=True)
        thread.start()
        body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': []}).encode()
        request = (b'POST / HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: '
                   + str(len(body)).encode() + b'\r\nConnection: close\r\n\r\n' + body)
        client.sendall(request)
        data = b''
        while True:
            chunk = client.recv(65536)
            if not chunk:
                break
            data += chunk
        thread.join(2)
        client.close()
        return data

    blocked = roundtrip('eth_sendTransaction')
    assert b' 403 ' in blocked.split(b'\r\n', 1)[0]
    assert upstreams == []

    allowed = roundtrip('eth_chainId')
    assert b' 200 ' in allowed.split(b'\r\n', 1)[0]
    assert b'"result": "0x1"' in allowed or b'"result":"0x1"' in allowed
    assert len(upstreams) == 1
    assert b'eth_chainId' in upstreams[0].sent


def test_sandbox_endpoint_exposure_contains_only_model_required_socket_links(tmp_path, monkeypatch):
    bench = _load('ai_bench_endpoint_links', ROOT / 're-bench/tools/ai_bench.py')
    source = tmp_path / 'proxy-source'
    exposed_root = tmp_path / 'exposed-root'
    source.mkdir()
    for name in ('tokenharbor.sock', 'evm.sock', 'opencode-mitm.sock', 'opencode-connect.sock'):
        (source / name).write_text('endpoint-placeholder')
    (source / 'proxy.log').write_text('metadata must not be exposed')
    monkeypatch.setattr(bench, 'ENDPOINT_SOURCE', source)
    monkeypatch.setattr(bench, 'ENDPOINT_ROOT', exposed_root)

    hy4_dir = bench.ensure_sandbox_endpoint_links('opencode/hy4-flash-free')
    hy4_expected = set(bench.endpoint_files_for('opencode/hy4-flash-free'))
    assert sorted(p.name for p in hy4_dir.iterdir()) == sorted(hy4_expected)
    assert 'tokenharbor.sock' not in hy4_expected
    assert 'opencode-mitm.sock' in hy4_expected
    assert not (hy4_dir / 'proxy.log').exists()
    for name in hy4_expected:
        assert (hy4_dir / name).stat().st_ino == (source / name).stat().st_ino

    th_dir = bench.ensure_sandbox_endpoint_links('tokenharbor/deepseek-v4.1-flash-1017')
    th_expected = set(bench.endpoint_files_for('tokenharbor/deepseek-v4.1-flash-1017'))
    assert sorted(p.name for p in th_dir.iterdir()) == sorted(th_expected)
    assert 'tokenharbor.sock' in th_expected
    assert 'opencode-mitm.sock' not in th_expected
    assert 'opencode-connect.sock' not in th_expected


def test_benchmark_binds_per_model_endpoint_directory_not_proxy_log_directory():
    source = _read_tool_text('ai_bench.py')
    assert "'--ro-bind',str(endpoint_dir),'/run/absmax-tokenharbor'" in source
    assert 'endpoint_dir=ensure_sandbox_endpoint_links(model)' in source
    assert "'--ro-bind','/home/nixon/absmax-tokenharbor-proxy','/run/absmax-tokenharbor'" not in source


def test_hy4_redacting_lane_ready_requires_metadata_and_liveness(tmp_path, monkeypatch):
    import json
    bench = _load('ai_bench_hy4_lane_liveness', ROOT / 're-bench/tools/ai_bench.py')
    ready = {'expanded_secret_representation_count': 139}
    (tmp_path / 'opencode-mitm.ready').write_text(json.dumps(ready))
    monkeypatch.setattr(bench, '_pid_cmdline_matches', lambda *args: True)
    monkeypatch.setattr(bench, '_connect_ok', lambda *args, **kwargs: True)
    assert bench.hy4_redacting_lane_ready(tmp_path) is True
    monkeypatch.setattr(bench, '_connect_ok', lambda *args, **kwargs: False)
    assert bench.hy4_redacting_lane_ready(tmp_path) is False
    monkeypatch.setattr(bench, '_connect_ok', lambda *args, **kwargs: True)
    (tmp_path / 'opencode-mitm.ready').write_text(json.dumps({'expanded_secret_representation_count': 0}))
    assert bench.hy4_redacting_lane_ready(tmp_path) is False
    (tmp_path / 'opencode-mitm.ready').unlink()
    assert bench.hy4_redacting_lane_ready(tmp_path) is False


def test_solution_validation_runs_inside_isolated_bwrap_workspace(tmp_path, monkeypatch):
    bench = _load('ai_bench_solution_validation_isolation', ROOT / 're-bench/tools/ai_bench.py')
    if not Path('/usr/bin/bwrap').exists():
        pytest.skip('bubblewrap is unavailable')
    monkeypatch.setenv('ABSMAX_VALIDATION_TMP_ROOT', str(tmp_path / 'validation-tmp'))
    (tmp_path / 'solution.py').write_text(
        'import os\n'
        'assert not os.path.exists("/home/nixon/Projects/adversarial-obfuscator/re-bench/secrets")\n'
        'def keystream(seed, n): return bytes(n)\n'
        'def seal(data, nonce): return data\n'
    )
    result = bench.validate_workspace(tmp_path)
    validation = result['independent_solution_validation']
    assert validation['execution_isolation'] == 'bubblewrap-unshare-net-pid-readonly-workspace'
    assert validation['validator_returncode'] == 0
    assert validation['loads'] is True


def test_solution_validation_source_does_not_execute_candidate_on_host():
    source = _read_tool_text('ai_bench.py')
    assert 'run_solution_validation_isolated(ws,code)' in source
    assert "subprocess.run([sys.executable,'-c',code],cwd=ws" not in source
    assert 'PROMPT_VERSION' in source
    assert 'prompt_sha256' in source
    assert 'prompt_execution_policy' in source


def test_static_scenario_prompt_explicitly_forbids_execution():
    bench = _load('ai_bench_static_prompt_boundary', ROOT / 're-bench/tools/ai_bench.py')
    static_prompt = bench.prompt_for('absolute-native-only', 'crypto-construction', 'static test instruction')
    dynamic_prompt = bench.prompt_for('absolute-native-only', 'runtime-secrets-withheld', 'dynamic test instruction')
    assert 'static-analysis scenario' in static_prompt
    assert 'do not execute, import, trace, debug, or invoke artifact.py' in static_prompt
    assert 'Execution is permitted only within this scenario boundary' in dynamic_prompt
    assert 'static-analysis scenario' not in dynamic_prompt


def test_resume_watchdog_multilane_uses_authorized_models_and_avoids_success_batch_probes():
    source = _read_tool_text('resume_absmax_benchmark_when_quota.py')
    assert 'LANES=[HY4_MODEL,TOKEN_FREE_MODEL,TOKEN_PAID_MODEL]' in source
    assert 'probe_model(lane)' in source
    assert 'if current_lane:' in source
    assert "provider_error=any('free-limit'" in source
    assert "if rec.get('returncode')!=0 or provider_error:" in source
    assert "'available':p.returncode==0 and not quota" in source
    assert "'available':p.returncode==0 and not quota and ok_text" not in source
    assert 'probe_needed' not in source


def test_resume_watchdog_lane_status_paths_are_model_specific():
    resume = _load('resume_watchdog_lane_paths', ROOT / 're-bench/tools/resume_absmax_benchmark_when_quota.py')
    paid_post, paid_prefix = resume.status_paths(resume.TOKEN_PAID_MODEL)
    free_post, free_prefix = resume.status_paths(resume.TOKEN_FREE_MODEL)
    hy4_post, hy4_prefix = resume.status_paths(resume.HY4_MODEL)
    assert paid_post.name == 'resume_post_status.json'
    assert paid_prefix.name == 'resume_prefix_status.json'
    assert 'tokenharbor_deepseek-v4.1-flash_free' in free_post.name
    assert 'tokenharbor_deepseek-v4.1-flash_free' in free_prefix.name
    assert 'opencode_hy4-flash-free' in hy4_post.name
    assert 'opencode_hy4-flash-free' in hy4_prefix.name


def test_resume_watchdog_parses_provider_free_reset_timestamp():
    resume = _load('resume_watchdog_reset_parse', ROOT / 're-bench/tools/resume_absmax_benchmark_when_quota.py')
    msg = "Your free allowance for ':free' models is used up. It comes back on 2 Dec 2026 at 15:07 UTC."
    assert resume.provider_reset_epoch(msg) == 1796224020.0
    assert resume.provider_reset_epoch('pass allowance exhausted without a timestamp') == 0.0


def test_tokenharbor_proxy_authorizes_only_free_and_1017_models():
    source = _read_tool_text('tokenharbor_unix_proxy.py')
    assert "deepseek-v4.1-flash:free" in source
    assert "deepseek-v4.1-flash-1017" in source
    assert 'model not in AUTHORIZED_MODELS' in source
    assert 'allowed_models' in source
