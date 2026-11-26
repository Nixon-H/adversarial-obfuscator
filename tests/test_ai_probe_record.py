"""The AI probe's record must be reproducible, not just scored.

Reviewer (2026-11-20): "preserve every raw model response, prompt, artifact
hash, scorer version and per-marker decision alongside the summary metrics."
Earlier runs stored a 600-character head and a 1,200-character algorithm
excerpt, which made a surprising score impossible to re-examine afterwards.

These tests monkeypatch the model call, so they are offline and deterministic:
no network, no CLI, no artefact build.
"""
import json


from pydeobsbench import ai_probe


TARGET = {
    "names": ["reconcile", "compute_audit_signature"],
    "secrets": ["fixture_api_token"],
    "algorithms": ("reconcile: delta = counted - ledger_count; "
                   "ok = (delta == 0)"),
}


def _fake_call(payload, status=0):
    def _call(prompt, timeout=0):
        _call.last_prompt = prompt
        if status:
            return {"error": "exhausted", "detail": "boom"}
        return {"content": json.dumps(payload)}
    _call.last_prompt = ""
    return _call


def test_the_record_carries_the_raw_response_and_hashes(monkeypatch):
    answer = {
        "names": ["reconcile"],
        "algorithm": "it reconciles stock counts against a ledger",
        "secrets": [],
    }
    fake = _fake_call(answer)
    monkeypatch.setattr(ai_probe, "call", fake)
    record = ai_probe.probe_ai(TARGET, "artefact text " * 100)

    assert record["measurement_failed"] is False
    # the full response, not a truncated head
    assert json.loads(record["raw_response"]) == answer
    # hashes that let a rerun prove it saw the same inputs
    assert len(record["prompt_sha256"]) == 64
    assert len(record["artefact_sha256"]) == 64
    assert record["artefact_chars_sent"] == len("artefact text " * 100)
    # the scorer identifies itself, so a metric change is not a model change
    assert record["scorer"].startswith("pydeobsbench.ai_probe/")
    # per-marker decisions, not just totals
    assert record["per_marker"]["names_hit"] == ["reconcile"]
    assert isinstance(record["per_marker"]["loader_terms_matched"], list)


def test_the_prompt_hash_covers_what_was_actually_sent(monkeypatch):
    fake = _fake_call({"names": [], "algorithm": "", "secrets": []})
    monkeypatch.setattr(ai_probe, "call", fake)
    record = ai_probe.probe_ai(TARGET, "abcd" * 10)
    import hashlib
    expected = hashlib.sha256(
        fake.last_prompt.encode("utf-8", "replace")).hexdigest()
    assert record["prompt_sha256"] == expected, (
        "the recorded hash must be over the prompt the model received")


def test_truncation_is_recorded_and_hashed_over_the_truncated_surface(
        monkeypatch):
    fake = _fake_call({"names": [], "algorithm": "", "secrets": []})
    monkeypatch.setattr(ai_probe, "call", fake)
    record = ai_probe.probe_ai(TARGET, "x" * 5000, max_chars=100)
    assert record["truncated"] is True
    assert record["artefact_chars_sent"] == 100
    import hashlib
    assert record["artefact_sha256"] == hashlib.sha256(
        ("x" * 5000).encode()).hexdigest(), (
        "the artefact hash must describe the whole artefact, so a rerun can "
        "tell 'same input' from 'same truncated window'")


def test_a_failed_call_is_reported_not_scored(monkeypatch):
    monkeypatch.setattr(ai_probe, "call", _fake_call({}, status=1))
    record = ai_probe.probe_ai(TARGET, "text")
    assert record["measurement_failed"] is True
    assert "error" in record


def test_no_credentials_appear_in_the_record(monkeypatch):
    """The record must never carry a real credential, only fixture values."""
    fake = _fake_call({"names": [], "algorithm": "", "secrets": []})
    monkeypatch.setattr(ai_probe, "call", fake)
    record = ai_probe.probe_ai(TARGET, "text")
    blob = json.dumps(record)
    for shape in ("sk_live_", "pg_prod_", "wt_live_"):
        assert shape not in blob, (
            "the probe record carries a credential-shaped literal (%r); "
            "fixtures must use fixture_* names" % shape)
