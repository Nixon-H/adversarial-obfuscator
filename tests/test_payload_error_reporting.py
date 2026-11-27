"""Regression: payload mid-run failure inside the native module must surface
the real error, not the false 'ran no payload' fatal."""
import re

def test_exec_module_records_payload_error():
    src = open("obfuscator/core/pipeline.py").read()
    # the non-ImportError branch must exist directly after exec_module handling
    assert "_NX_PAYLOAD_ERROR" in src
    i = src.find("spec.loader.exec_module(module)")
    seg = src[i:i+1400]
    assert "except ImportError" in seg
    assert "_nx_payload_err" in seg
    # it must not fall through to trying other module names after a payload
    # mid-run failure (would duplicate remote side effects)
    assert "return None" in seg
    # and it must not mark success
    j = seg.find("_nx_payload_err")
    assert "_nx_ok = True" not in seg[j:j+800]

def test_fatal_message_discriminates():
    src = open("obfuscator/core/pipeline.py").read()
    assert "payload started but failed inside the" in src
    # original no-payload message retained for genuine nothing-ran cases
    assert "artefact ran no payload" in src
