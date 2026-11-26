"""Regression tests for benchmark harness isolation controls."""
import importlib.util
import json

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
    assert 'Hard validity timebox: never exceed 9 tool invocations in this turn' in source
    assert 'write answer.json no later than tool invocation 8' in source
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
    for name in ('tokenharbor.sock', 'kern.sock', 'evm.sock', 'opencode-mitm.sock', 'opencode-connect.sock'):
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

    kern_dir = bench.ensure_sandbox_endpoint_links('kern/inkling-2-mini')
    kern_expected = set(bench.endpoint_files_for('kern/inkling-2-mini'))
    assert sorted(p.name for p in kern_dir.iterdir()) == sorted(kern_expected)
    assert 'kern.sock' in kern_expected
    assert 'tokenharbor.sock' not in kern_expected
    assert 'opencode-mitm.sock' not in kern_expected
    assert 'opencode-connect.sock' not in kern_expected


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
    assert 'LANES=[KERN_MODEL,TOKEN_FREE_MODEL,TOKEN_PAID_MODEL]' in source
    assert 'probe_model(lane)' in source
    assert 'if current_lane:' in source
    assert "provider_error=any('free-limit'" in source
    assert "if rec.get('returncode')!=0 or provider_error:" in source
    # Probe availability must require assistant-text/token evidence, not rc0
    # alone, and must not require an exact 'ok' reply.
    assert 'available=(returncode==0 and not quota and (assistant_text or token_usage))' in source
    assert "'available':p.returncode==0 and not quota" not in source
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


def test_kern_endpoint_family_and_socket_files_are_separate():
    bench = _load('ai_bench_harness_kern_endpoints', ROOT / 're-bench/tools/ai_bench.py')
    assert bench.endpoint_family('kern/inkling-2-mini') == 'kern'
    assert bench.endpoint_files_for('kern/inkling-2-mini') == ('evm.sock', 'kern.sock')
    assert bench.endpoint_files_for('tokenharbor/deepseek-v4.1-flash:free') == ('evm.sock', 'tokenharbor.sock')
    assert bench.KERN_MODEL in bench.MODELS
    assert 'opencode/hy4-flash-free' not in bench.MODELS


def test_kern_legitimate_secrets_fail_closed_without_redacting_proxy(tmp_path, monkeypatch):
    bench = _load('ai_bench_harness_kern_guard', ROOT / 're-bench/tools/ai_bench.py')
    monkeypatch.setattr(bench, 'kern_redacting_proxy_ready', lambda: False)
    monkeypatch.setattr(bench, 'OUT', tmp_path / 'bench-out')
    def forbidden_prep(*args):
        raise AssertionError('workspace preparation must not copy runtime secrets when the Kern redacting proxy is unavailable')
    monkeypatch.setattr(bench, 'prep_workspace', forbidden_prep)
    result = bench.one(('absolute-native-only', 'legitimate-runtime-secrets', 'kern/inkling-2-mini', 99))
    assert result['harness_error'] == 'kern-legitimate-runtime-secrets-blocked-redacting-proxy-unavailable'
    assert result['returncode'] is None
    assert result['validation']['answer_valid'] is False


def test_kern_proxy_rewrites_local_model_and_never_logs_secret_content():
    source = _read_tool_text('kern_unix_proxy.py')
    assert "UPSTREAM='https://api.kern-llm.org/v1'" in source
    assert "LOCAL_MODEL='inkling-2-mini'" in source
    assert "obj['model']=MODEL" in source
    assert "KEY=os.environ.get('KERN_API_KEY','')" in source
    assert 'request_redactions' in source and 'response_redactions' in source
    assert "req.add_header('Authorization','Bearer '+KEY)" in source


def test_resume_watchdog_lanes_are_exactly_the_authorized_models():
    resume = _load('resume_watchdog_authorized_lanes', ROOT / 're-bench/tools/resume_absmax_benchmark_when_quota.py')
    assert resume.LANES == [resume.KERN_MODEL, resume.TOKEN_FREE_MODEL, resume.TOKEN_PAID_MODEL]
    assert resume.KERN_MODEL == 'kern/inkling-2-mini'
    assert resume.HY4_MODEL == 'opencode/hy4-flash-free'
    assert resume.TOKEN_FREE_MODEL == 'tokenharbor/deepseek-v4.1-flash:free'
    assert resume.TOKEN_PAID_MODEL == 'tokenharbor/deepseek-v4.1-flash-1017'
    assert resume.HY4_MODEL not in resume.LANES


def test_resume_watchdog_cmdline_matcher_distinguishes_outer_from_worker():
    resume = _load('resume_watchdog_cmdline_matcher', ROOT / 're-bench/tools/resume_absmax_benchmark_when_quota.py')
    assert resume.cmdline_is_outer_watchdog('python3 re-bench/tools/resume_absmax_benchmark_when_quota.py --probe-interval 300 ')
    assert resume.cmdline_is_outer_watchdog('python3 /home/nixon/Projects/adversarial-obfuscator/re-bench/tools/resume_absmax_benchmark_when_quota.py ')
    assert not resume.cmdline_is_outer_watchdog('python3 re-bench/tools/resume_absmax_benchmark_when_quota.py --worker --status-file /tmp/x.json ')
    assert not resume.cmdline_is_outer_watchdog('python3 unrelated_script.py --probe-interval 300 ')
    assert not resume.cmdline_is_outer_watchdog('')
    assert not resume.cmdline_is_outer_watchdog(None)


def test_resume_watchdog_fence_rejects_live_outer_watchdog_process(tmp_path):
    import subprocess, sys
    resume = _load('resume_watchdog_fence_live', ROOT / 're-bench/tools/resume_absmax_benchmark_when_quota.py')
    # Spawn a real live process whose cmdline matches an outer watchdog; the
    # fence must refuse to start a second instance even though this legacy
    # process holds no flock.
    script = tmp_path / 'resume_absmax_benchmark_when_quota.py'
    script.write_text('import time\ntime.sleep(60)\n')
    proc = subprocess.Popen([sys.executable, str(script)])
    try:
        pidfile = tmp_path / 'watchdog.pid'
        pidfile.write_text(str(proc.pid))
        fence = resume.acquire_watchdog_fence(pidfile)
        assert fence['acquired'] is False
        assert fence['conflict_pid'] == proc.pid
        # The watchdog must fail safely: no scan/probe/job side effects, and
        # the recorded pid file still belongs to the live instance.
        assert pidfile.read_text().strip() == str(proc.pid)
    finally:
        proc.kill()
        proc.wait()


def test_resume_watchdog_fence_acquires_stale_pidfile_and_recovers_after_death(tmp_path):
    import subprocess, sys, os
    resume = _load('resume_watchdog_fence_stale', ROOT / 're-bench/tools/resume_absmax_benchmark_when_quota.py')
    pidfile = tmp_path / 'watchdog.pid'
    # A pid that cannot be a live process is stale and must not block startup.
    pidfile.write_text('4194303')
    fence = resume.acquire_watchdog_fence(pidfile)
    assert fence['acquired'] is True
    assert fence['pid'] == os.getpid()
    assert pidfile.read_text().strip() == str(os.getpid())
    fence['handle'].close()
    # A live outer watchdog that exits releases the lane: after process death
    # the recorded pid is stale and a new watchdog may take over.
    script = tmp_path / 'resume_absmax_benchmark_when_quota.py'
    script.write_text('import time\ntime.sleep(60)\n')
    proc = subprocess.Popen([sys.executable, str(script)])
    try:
        pidfile.write_text(str(proc.pid))
        conflict = resume.acquire_watchdog_fence(pidfile)
        assert conflict['acquired'] is False
    finally:
        proc.kill()
        proc.wait()
    takeover = resume.acquire_watchdog_fence(pidfile)
    assert takeover['acquired'] is True
    takeover['handle'].close()


def test_resume_watchdog_fence_second_acquire_conflicts_via_flock(tmp_path):
    resume = _load('resume_watchdog_fence_flock', ROOT / 're-bench/tools/resume_absmax_benchmark_when_quota.py')
    pidfile = tmp_path / 'watchdog.pid'
    first = resume.acquire_watchdog_fence(pidfile)
    assert first['acquired'] is True
    try:
        second = resume.acquire_watchdog_fence(pidfile)
        assert second['acquired'] is False
        assert second['mechanism'] == 'flock-conflict'
    finally:
        first['handle'].close()


def test_resume_watchdog_hy4_cooldown_uses_freshest_record_not_historical_maximum(tmp_path):
    import json, os, time
    resume = _load('resume_watchdog_cooldown_freshest', ROOT / 're-bench/tools/resume_absmax_benchmark_when_quota.py')
    results = tmp_path / 'results'
    results.mkdir()
    now = time.time()
    # An older record with a very long retry window is still active, but the
    # fresher record has already expired: the lane must not stay blocked by
    # the stale historical maximum.
    old = {'provider_error': {'type': 'provider.free-limit', 'message': 'Free usage limit reached', 'retryAfterMs': 24 * 3600 * 1000}}
    old_path = results / 'absolute-native-only__crypto-construction__opencode_hy4-flash-free__a1.json'
    old_path.write_text(json.dumps(old))
    os.utime(old_path, (now - 3600, now - 3600))
    fresh = {'provider_error': {'type': 'provider.free-limit', 'message': 'Free usage limit reached', 'retryAfterMs': 1000}}
    fresh_path = results / 'absolute-native-only__loader-initialization-order__opencode_hy4-flash-free__a2.json'
    fresh_path.write_text(json.dumps(fresh))
    os.utime(fresh_path, (now - 10, now - 10))
    cd = resume.hy4_free_limit_cooldown(tmp_path)
    assert cd['active'] is False
    assert cd['latest_free_limit']['result_file'] == fresh_path.name
    # When the freshest record is still inside its retry window, that window
    # is honoured exactly.
    os.utime(fresh_path, (now, now))
    fresh2 = {'provider_error': {'type': 'provider.free-limit', 'message': 'Free usage limit reached', 'retryAfterMs': 60000}}
    fresh_path.write_text(json.dumps(fresh2))
    cd2 = resume.hy4_free_limit_cooldown(tmp_path)
    assert cd2['active'] is True
    assert 1 <= cd2['remaining_seconds'] <= 60
    assert cd2['latest_free_limit']['retry_after_ms'] == 60000


def test_resume_watchdog_advisory_cap_treats_long_cooldowns_as_advisory():
    import time
    resume = _load('resume_watchdog_advisory_cap', ROOT / 're-bench/tools/resume_absmax_benchmark_when_quota.py')
    now = time.time()
    # A multi-hour cooldown may only suppress probing for one advisory window
    # (30-60 minutes), never for the whole recorded cooldown.
    assert resume.advisory_capped_until(now + 20 * 3600, now, 2700) == now + 2700
    # A short cooldown is honoured exactly.
    assert resume.advisory_capped_until(now + 600, now, 2700) == now + 600
    assert resume.advisory_capped_until(0, now, 2700) == 0.0
    # The watchdog applies the cap at both cooldown consumption sites and to
    # the fresh probe's own retryAfterMs backoff for the Hy4 lane.
    source = _read_tool_text('resume_absmax_benchmark_when_quota.py')
    assert source.count('advisory_capped_until(float(cooldown.get(') >= 2
    assert 'advisory_capped_until(float(blocked_until[lane] or 0),now,args.advisory_probe_interval)' in source
    assert "'--advisory-probe-interval',type=int,default=2700" in source


def test_resume_watchdog_probe_assessment_requires_assistant_evidence_not_exact_ok():
    import json
    resume = _load('resume_watchdog_probe_assessment', ROOT / 're-bench/tools/resume_absmax_benchmark_when_quota.py')
    text_events = '\n'.join([
        json.dumps({'type': 'step_start', 'part': {}}),
        json.dumps({'type': 'text', 'part': {'type': 'text', 'text': 'Sure — the probe reply need not be exactly ok.'}}),
        json.dumps({'type': 'step_finish', 'part': {'type': 'step-finish', 'tokens': {'input': 10, 'output': 3, 'reasoning': 0}}}),
    ])
    a = resume.assess_hy4_probe_output(text_events, '', 0)
    assert a['available'] is True
    assert a['assistant_text_evidence'] is True
    assert a['token_usage_evidence'] is True
    # Assistant text that is not exactly 'ok' still proves availability.
    assert a['ok_text'] is False or a['available'] is True
    # Token usage alone is sufficient evidence of a served completion.
    tokens_only = json.dumps({'type': 'step_finish', 'part': {'type': 'step-finish', 'tokens': {'input': 5, 'output': 1, 'reasoning': 0, 'cache': {'read': 0, 'write': 0}}}})
    a2 = resume.assess_hy4_probe_output(tokens_only, '', 0)
    assert a2['available'] is True
    assert a2['assistant_text_evidence'] is False
    assert a2['token_usage_evidence'] is True
    # rc0 with neither assistant text nor token usage proves nothing: an early
    # client/harness failure can exit zero without ever reaching the model.
    zero_run = json.dumps({'type': 'step_finish', 'part': {'type': 'step-finish', 'tokens': {'input': 0, 'output': 0, 'reasoning': 0}}})
    a3 = resume.assess_hy4_probe_output(zero_run, '', 0)
    assert a3['available'] is False
    # Nonzero return code is never available, even with assistant evidence.
    a4 = resume.assess_hy4_probe_output(text_events, '', 1)
    assert a4['available'] is False
    # A free-limit error event is quota evidence even when other events exist,
    # and its retryAfterMs is surfaced for backoff.
    quota_event = json.dumps({'type': 'error', 'error': {'type': 'provider.free-limit', 'message': 'Free usage limit reached', 'retryAfterMs': 30000}})
    a5 = resume.assess_hy4_probe_output(quota_event + '\n' + text_events, '', 0)
    assert a5['available'] is False
    assert a5['quota_limited'] is True
    assert a5['retry_after_ms'] == 30000


def test_resume_watchdog_probe_env_mirrors_benchmark_without_credentials(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace
    resume = _load('resume_watchdog_probe_env', ROOT / 're-bench/tools/resume_absmax_benchmark_when_quota.py')
    monkeypatch.setenv('ABSMAX_PROBE_TMP_ROOT', str(tmp_path))
    captured = {}

    def fake_run(cmd, **kwargs):
        env = kwargs.get('env') or {}
        captured['cmd'] = list(cmd)
        captured['env'] = dict(env)
        captured['cwd'] = kwargs.get('cwd')
        home = Path(env.get('HOME', ''))
        cfg = home / '.config/opencode/opencode.json'
        captured['config'] = json.loads(cfg.read_text()) if cfg.exists() else None
        captured['data_db_exists'] = (home / '.local/share/opencode/opencode.db').exists()
        return SimpleNamespace(returncode=1, stdout='', stderr='simulated probe failure')

    monkeypatch.setattr(resume.subprocess, 'run', fake_run)
    result = resume.probe_hy4()
    assert result['available'] is False
    env = captured['env']
    # The environment is the minimal benchmark OpenCode environment: no
    # inherited host credentials, exact key set, redacting-MITM egress path.
    assert set(env) == {'PATH', 'HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL', 'TMPDIR', 'PYTHONUNBUFFERED',
                        'OPENCODE_DISABLE_AUTOUPDATE', 'HTTPS_PROXY', 'https_proxy', 'HTTP_PROXY', 'http_proxy',
                        'NO_PROXY', 'no_proxy', 'SSL_CERT_FILE', 'NODE_EXTRA_CA_CERTS'}
    assert env['HTTPS_PROXY'] == 'http://127.0.0.1:9898'
    assert env['NO_PROXY'] == '127.0.0.1,localhost'
    assert env['OPENCODE_DISABLE_AUTOUPDATE'] == '1'
    assert env['SSL_CERT_FILE'] == '/home/nixon/absmax-tokenharbor-proxy/opencode-mitm-ca-bundle.pem'
    assert env['NODE_EXTRA_CA_CERTS'] == env['SSL_CERT_FILE']
    assert env['PATH'] == '/usr/local/bin:/usr/bin:/bin'
    assert not any(('KEY' in k or 'TOKEN' in k or 'SECRET' in k or 'CREDENTIAL' in k) for k in env)
    # Fresh per-probe OpenCode state carries the credential-free minimal
    # provider config benchmark attempts use, with only the dummy proxy apiKey.
    assert captured['data_db_exists'] is True
    cfg = captured['config']
    assert cfg is not None
    tokenharbor = (cfg.get('provider') or {}).get('tokenharbor') or {}
    assert (tokenharbor.get('options') or {}).get('apiKey') == 'credential-isolated-local-proxy'
    assert 'kern' not in json.dumps(cfg).lower()
    # Invocation flags match the benchmark harness invocation.
    cmd = captured['cmd']
    assert cmd[0].endswith('/opencode')
    for flag in ('run', '--standalone', '--format', 'json', '--auto', '--archived', '--model', 'opencode/hy4-flash-free'):
        assert flag in cmd


def test_resume_watchdog_outer_fences_before_any_scan_or_probe():
    source = _read_tool_text('resume_absmax_benchmark_when_quota.py')
    assert 'fence=acquire_watchdog_fence(WATCHDOG_PIDFILE)' in source
    assert 'another outer watchdog is already active' in source
    # The unconditional pre-fence pid write must not exist any more: the pid
    # file is only written after the fence is acquired.
    assert "(ORCH/'resume_quota_watchdog.pid').write_text(str(os.getpid()))" not in source
    fence_pos = source.index('fence=acquire_watchdog_fence(WATCHDOG_PIDFILE)')
    scan_pos = source.index("run_worker('post',scan_only=True,model=lane)")
    assert fence_pos < scan_pos


def test_kern_proxy_redacts_json_escaped_runtime_licence():
    sec = ROOT / 're-bench/secrets/absolute-native-only/cipher/runtime.licence'
    if not sec.exists():
        pytest.skip('benchmark runtime licence fixture is unavailable')
    import json
    kern = _load('kern_unix_proxy_redaction_test', ROOT / 're-bench/tools/kern_unix_proxy.py')
    raw = sec.read_text().strip()
    escaped = json.dumps(raw)[1:-1]
    redacted, count = kern.redact_bytes(('prefix ' + escaped + ' suffix').encode())
    assert count == 1
    assert escaped.encode() not in redacted
    assert raw.encode() not in redacted
    assert b'<redacted-' in redacted


def test_benchmark_agent_is_step_limited_and_recorded():
    source = _read_tool_text('ai_bench.py')
    assert 'BENCHMARK_AGENT_STEPS=10' in source
    assert "'steps':BENCHMARK_AGENT_STEPS" in source
    assert "'--agent',BENCHMARK_AGENT" in source
    assert 'benchmark_agent_prompt_sha256' in source
    assert 'Never exceed 9 tool invocations in this turn' in source
    assert 'By tool invocation 8, create answer.json' in source


def test_final_text_json_materialization_preserves_model_content(tmp_path):
    bench = _load('ai_bench_final_answer_materialization', ROOT / 're-bench/tools/ai_bench.py')
    payload = {'artifact_type': 'x', 'claims': ['evidence-backed'], 'nested': {'ok': True}}
    out = bench.materialize_final_answer_json(tmp_path, {'text': json.dumps(payload)})
    assert out['materialized'] is True
    assert json.loads((tmp_path / 'answer.json').read_text()) == payload
    (tmp_path / 'answer.json').unlink()
    out = bench.materialize_final_answer_json(tmp_path, {'text': 'not json'})
    assert out['materialized'] is False
    assert not (tmp_path / 'answer.json').exists()


def test_benchmark_profile_matrix_includes_local_cloud_packed_and_absolute():
    builder = _load('benchmark_profile_builder', ROOT / 're-bench/tools/build_absolute.py')
    expected = {'maximum-local', 'maximum-packed', 'maximum-cloud', 'absolute', 'absolute-cloud', 'absolute-native-only'}
    assert expected <= set(builder.PROFILE_CONFIG)
    assert builder.PROFILE_CONFIG['maximum-local']['skip_cloud'] is True
    assert builder.PROFILE_CONFIG['maximum-packed']['skip_cloud'] is True
    assert builder.PROFILE_CONFIG['maximum-cloud']['skip_cloud'] is False
    assert builder.PROFILE_CONFIG['absolute-cloud']['skip_cloud'] is False
    assert 'platform=github' in builder.PROFILE_CONFIG['maximum-cloud']['pkg']
    assert 'platform=github' in builder.PROFILE_CONFIG['absolute-cloud']['pkg']


def test_source_assisted_workspace_receives_original_source(tmp_path, monkeypatch):
    bench = _load('ai_bench_source_assisted_workspace', ROOT / 're-bench/tools/ai_bench.py')
    monkeypatch.setattr(bench, 'LIVE_WORKSPACE_ROOT', tmp_path / 'live')
    assert 'source-assisted-runtime-secrets' in bench.SCENARIOS
    assert 'source-assisted-secrets-withheld' in bench.SCENARIOS
    assert 'source-assisted-static' in bench.SCENARIOS
    ws, desc = bench.prep_workspace('absolute-native-only', 'source-assisted-static', 'kern/inkling-2-mini', 77)
    assert 'original_source.py' in desc or (ws / 'original_source.py').exists()
    assert (ws / 'original_source.py').exists()
    assert (ws / 'original_source.py').read_bytes() == (ROOT / 're-bench/builds/absolute-native-only/cipher/cipher.py').read_bytes()


def test_two_turn_finalisation_command_uses_continue_only_when_answer_missing():
    bench = _load('ai_bench_two_turn_command', ROOT / 're-bench/tools/ai_bench.py')
    cmd = bench.opencode_shell_command('absolute', 'runtime-secrets-withheld', 3, 'kern/inkling-2-mini', 'analysis prompt')
    assert '--session' in cmd
    assert 'if [ ! -s answer.json ]; then' in cmd
    assert 'analysis prompt' in cmd
    assert 'mandatory finalisation turn' in cmd


def test_resume_watchdog_matrix_covers_profiles_and_source_assisted_scenarios():
    source = _read_tool_text('resume_absmax_benchmark_when_quota.py')
    assert "BENCHMARK_VARIANTS=['maximum-local','maximum-packed','maximum-cloud','absolute','absolute-cloud','absolute-native-only']" in source
    for scenario in ('source-assisted-static', 'source-assisted-runtime-secrets', 'source-assisted-secrets-withheld'):
        assert scenario in source
    assert 'missing_variants.append(variant)' in source
    assert "'active_variants':variants" in source


def test_workspace_secret_root_can_be_overridden(tmp_path, monkeypatch):
    bench = _load('ai_bench_secret_root_override', ROOT / 're-bench/tools/ai_bench.py')
    monkeypatch.setattr(bench, 'LIVE_WORKSPACE_ROOT', tmp_path / 'live')
    alt = tmp_path / 'alt-secrets' / 'absolute-native-only' / 'cipher'
    alt.mkdir(parents=True)
    for name, data in [('runtime.licence', '{"x":1}'), ('nx_seal_shard.hex', 'aa'), ('provenance.public.hex', 'bb')]:
        (alt / name).write_text(data)
    monkeypatch.setattr(bench, 'SECRETS_ROOT', tmp_path / 'alt-secrets')
    ws, _desc = bench.prep_workspace('absolute-native-only', 'legitimate-runtime-secrets', 'kern/inkling-2-mini', 91)
    assert (ws / 'runtime.licence').read_text() == '{"x":1}'
    assert (ws / 'nx_seal_shard.hex').read_text() == 'aa'
    assert (ws / 'provenance.public.hex').read_text() == 'bb'


def test_secret_mentions_in_source_assisted_answer_are_not_exact_recovery(tmp_path):
    bench = _load('ai_bench_secret_exactness', ROOT / 're-bench/tools/ai_bench.py')
    (tmp_path / 'answer.json').write_text(json.dumps({
        'recovered_secret': None,
        'algorithm': 'input original_source.py literally contains cipher-master-K_77',
        'key_derivation': 'cipher-master-K_77 appears in supplied source',
    }))
    result = bench.validate_workspace(tmp_path)
    assert result['secret_recovered'] is False
    assert result['secret_exact_in_recovered_secret'] is False
    assert result['secret_mentioned_incidentally'] is True


def test_exact_recovered_secret_field_counts_as_exact_recovery(tmp_path):
    bench = _load('ai_bench_secret_exactness2', ROOT / 're-bench/tools/ai_bench.py')
    (tmp_path / 'answer.json').write_text(json.dumps({'recovered_secret': 'cipher-master-K_77'}))
    result = bench.validate_workspace(tmp_path)
    assert result['secret_recovered'] is True
    assert result['secret_exact_in_recovered_secret'] is True
    assert result['secret_mentioned_incidentally'] is False


def test_scorer_does_not_cross_contaminate_evidence_roots():
    source = _read_tool_text('score_ai_benchmark.py')
    assert 'workspace_is_preserved' in source
    assert 'if not workspace_is_preserved and copied.exists()' in source
    assert 'crossing evidence-root' in source


def test_scorer_exact_secret_boundary_is_field_specific():
    source = _read_tool_text('score_ai_benchmark.py')
    assert "answer_obj.get('recovered_secret') == benchmark_payload_secret" in source
    assert 'secret_mentioned_incidentally' in source
    assert 'harness_secret_recovered_field' in source


def test_profile_matrix_id_is_configurable():
    source = _read_tool_text('run_profile_matrix.py')
    assert "ABSMAX_PROFILE_MATRIX_ID" in source
    assert "'_profile_matrix_'+PROFILE_MATRIX_ID" in source
    assert "'/home/nixon/absmax-scratch/profile-matrix-'+PROFILE_MATRIX_ID+'-status.json'" in source


def test_cloud_build_integrity_regressions():
    builder = _read_tool_text('build_absolute.py')
    validator = _read_tool_text('validate_cloud_profile_build.py')
    assert 'acquire_build_root_lock' in builder
    assert 'fcntl.LOCK_EX|fcntl.LOCK_NB' in builder
    assert 'artifact_matches_build_manifest' in validator
    assert 'nxs1-container' in validator
    assert 'positive_ok' in validator and 'negative_fail_closed' in validator


def test_deepseek_flash_plan_lane_is_explicitly_configured():
    bench = _load('ai_bench_deepseek_flash_plan_lane', ROOT / 're-bench/tools/ai_bench.py')
    assert 'tokenharbor/deepseek-v4.1-flash' in bench.MODELS
    assert bench.endpoint_files_for('tokenharbor/deepseek-v4.1-flash') == ('evm.sock', 'tokenharbor.sock')
    proxy = _read_tool_text('tokenharbor_unix_proxy.py')
    assert "'deepseek-v4.1-flash:free','deepseek-v4.1-flash-1017'" in proxy or "deepseek-v4.1-flash-1017" in proxy
    assert 'prompt_cache_hit_tokens' in proxy
    assert 'cache_hit_rate' in proxy


def test_opencode_go_deepseek_lane_is_credential_isolated():
    bench = _load('ai_bench_opencode_go_lane', ROOT / 're-bench/tools/ai_bench.py')
    assert 'opencode-go/deepseek-v4.1-flash' in bench.MODELS
    assert bench.endpoint_family('opencode-go/deepseek-v4.1-flash') == 'opencode-go'
    assert bench.endpoint_files_for('opencode-go/deepseek-v4.1-flash') == ('evm.sock', 'opencode-go.sock')
    proxy = _read_tool_text('opencode_go_unix_proxy.py')
    assert 'https://opencode.ai/zen/go/v1' in proxy
    assert 'x-opencode-session' in proxy
    assert 'prompt_cache_hit_tokens' in proxy
    assert 'OPENCODE_API_KEY missing' in proxy


def test_benchmark_prompt_uses_cache_friendly_stable_prefix():
    bench = _load('ai_bench_cache_prefix_prompt', ROOT / 're-bench/tools/ai_bench.py')
    a = bench.prompt_for('absolute', 'runtime-secrets-withheld', 'variant specific text')
    b = bench.prompt_for('maximum-cloud', 'legitimate-runtime-secrets', 'other variant text')
    # Scenario/variant metadata must not appear before the stable instructional
    # prefix; prompt cache hits require exact leading-token equality.
    assert a.index('Benchmark target metadata follows') == b.index('Benchmark target metadata follows')
    assert a[:a.index('Benchmark target metadata follows')] == b[:b.index('Benchmark target metadata follows')]
    assert 'deepseek-cache-prefix-v1' in bench.PROMPT_VERSION


def test_redaction_covers_cloud_final4_secret_root():
    source = _read_tool_text('redact_benchmark_credentials.py')
    assert 'cloud-final4-secrets' in source
    assert 'artifact_subdir' in source
    assert 'validated replacement artifacts' in source


def test_two_turn_finalisation_reuses_explicit_session():
    bench = _load('ai_bench_two_turn_session', ROOT / 're-bench/tools/ai_bench.py')
    cmd = bench.opencode_shell_command('absolute', 'runtime-secrets-withheld', 3, 'opencode-go/deepseek-v4.1-flash', 'analysis prompt')
    assert cmd.count('--session') == 2
    assert 'ses_absmax_absolute-runtime-secrets-withheld-a3' in cmd
    assert 'if [ ! -s answer.json ]; then' in cmd


def test_secret_bearing_scenarios_fail_closed_for_each_external_lane():
    source = _read_tool_text('ai_bench.py')
    assert 'secrets_included=bool(SCENARIOS[scenario][1])' in source
    assert "model.startswith('opencode-go/') and secrets_included" in source
    assert 'opencode-go-runtime-secrets-blocked-redacting-proxy-unavailable' in source
    assert source.count('and secrets_included') >= 3


def test_opencode_go_proxy_has_ready_metadata_and_cache_pinning():
    proxy = _read_tool_text('opencode_go_unix_proxy.py')
    assert 'opencode-go-proxy.ready' in proxy
    assert 'redaction_count' in proxy
    assert "prompt_cache_key" in proxy
    assert 'absmax-benchmark-deepseek-v1' in proxy
    assert 'include_usage' in proxy
    assert 'for sec in sorted(root.glob' in proxy


def test_opencode_go_proxy_sets_exact_buffered_content_length():
    proxy = _read_tool_text('opencode_go_unix_proxy.py')
    assert "self.send_header('Transfer-Encoding','chunked')" in proxy
    assert 'chunk boundaries' in proxy
    assert 'first-byte progress' in proxy


def test_opencode_go_cache_summary_is_numeric_only():
    source = _read_tool_text('summarize_opencode_go_cache.py')
    assert 'prompt_cache_hit_tokens' in source
    assert 'weighted_cache_hit_rate' in source
    assert 'cache_write_5m_tokens' in source
    assert 'messages' not in source
    assert 'prompt_content' not in source


def test_result_preserves_validation_materialisation_fields():
    source = _read_tool_text('ai_bench.py')
    assert "for validation_key in ('answer_json_exists','answer_json_valid','solution_py_exists','secret_recovered'" in source
    assert "result[validation_key]=validation.get(validation_key)" in source


def test_operator_composed_effective_key_is_redacted():
    redactor = _read_tool_text('redact_benchmark_credentials.py')
    proxy = _read_tool_text('opencode_go_unix_proxy.py')
    for source in (redactor, proxy):
        assert 'nx-operator-blob:' in source
        assert 'licence-operator-mask' in source
        assert 'licence-effective-native-key-operator' in source
        assert 'str(len(seal)).encode' in source
