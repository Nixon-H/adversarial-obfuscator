"""No-third-implementation lint: each subsystem family has EXACTLY its known
members. A new file matching a family glob (a third poly engine, a second
challenge-response, ...) fails this test until docs/contracts.md is updated
to own the newcomer.

Scope is deliberately narrow: only basenames that denote the family core
are matched, and phases/tests/support files are excluded by directory so
the allowlist stays exact.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# basename-substring -> exact set of repo-relative paths allowed to match.
# basenames that match by substring but are NOT family implementations
# (pipeline stage wrappers, proof scripts, other-language layers).
# `scripts/phases/` is excluded wholesale: phase31_poly_engine etc. are
# thin pipeline stages, not competing implementations. `ledger` needs an
# exact-basename match so scripts/ledger_proof.py (a proof script) and
# runtime/src/ledger.rs (the Rust artifact-side ledger, a different layer)
# do not trip the lint.
EXCLUDE_DIRNAMES = {"__pycache__", "target", ".git", "phases"}
EXACT_BASENAME = {"ledger": {"ledger.py"}}
ALLOWLIST = {
    "poly_engine": {
        "scripts/poly/poly_engine.py",
        "scripts/environment/poly_engine.py",
    },
    "dispersal": {
        "scripts/payload/dispersal.py",
        "scripts/dispersal/payload_dispersal.py",
    },
    "fragment_compiler": {
        "scripts/fragment/fragment_compiler.py",
    },
    "micro_fragment": {
        "scripts/fragment/micro_fragment.py",
    },
    "dist_attestation": {
        "scripts/distributed/dist_attestation.py",
    },
    "challenge_response": {
        "scripts/runtime/challenge_response.py",
    },
    "sw_attestation": {
        "runtime/src/sw_attestation.rs",
    },
    "ledger": {
        "scripts/evidence/ledger.py",
    },
    "certificate": {
        "scripts/certificates/certificate.py",
    },
    "bundler": {
        "scripts/verification_bundle/bundler.py",
        "scripts/artifacts/bundler.py",
    },
    "auditor": {
        "scripts/self_audit/auditor.py",
        "scripts/independent_audit/auditor.py",
        "scripts/claim_auditor/auditor.py",
        "scripts/false_confidence/auditor.py",
    },
    "string_crypto": {
        "obfuscator/string_crypto.py",
    },
    "chacha20": {
        "obfuscator/chacha20.py",
    },
}

SCAN_DIRS = ("scripts", "obfuscator", "runtime/src")


def _scan():
    hits = {}
    for top in SCAN_DIRS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, top)):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRNAMES]
            for fn in filenames:
                for key in ALLOWLIST:
                    if key in fn and fn.endswith((".py", ".rs")):
                        if key in EXACT_BASENAME and \
                                fn not in EXACT_BASENAME[key]:
                            continue
                        rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
                        hits.setdefault(key, set()).add(rel)
    return hits


def test_no_third_implementation():
    hits = _scan()
    problems = []
    for key, allowed in ALLOWLIST.items():
        found = hits.get(key, set())
        if found != allowed:
            problems.append("%s: found=%s allowed=%s"
                            % (key, sorted(found), sorted(allowed)))
    assert not problems, (
        "unexpected subsystem family members (new impl or rename — "
        "update docs/contracts.md and this allowlist): %s" % problems)
