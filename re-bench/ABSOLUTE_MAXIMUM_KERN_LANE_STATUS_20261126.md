# ABSOLUTE MAXIMUM Kern lane status — 2026-11-26

## Configuration completed

The Hy4 lane was replaced for new benchmark work by the operator-authorised Kern model:

- benchmark lane: `kern/inkling-2-mini`
- upstream model: `thinkingmachines/inkling-2-mini`
- upstream endpoint: `https://api.kern-llm.org/v1`
- credential-holding host proxy: `re-bench/tools/kern_unix_proxy.py`
- sandbox endpoint socket: `kern.sock`
- sandbox OpenCode model name: `inkling-2-mini`

The real Kern API key is not stored in the benchmark workspace, OpenCode configuration, command lines, or evidence files. The sandboxed OpenCode configuration contains only the non-credential placeholder `credential-isolated-local-proxy`; the host-side Unix proxy injects authorization outside the network-isolated sandbox.

## Security validation completed

- Direct Kern connectivity was operator-demonstrated with HTTP 200 before integration.
- The Unix proxy returned HTTP 200 for sandboxed chat-completion traffic.
- The sandbox still uses `bwrap` with network and PID namespaces disabled for direct egress.
- The Kern endpoint directory is separate from TokenHarbor and OpenCode endpoint directories.
- Runtime-secret redaction was strengthened beyond the TokenHarbor baseline: exact, JSON-escaped, hex, base64, base64url, Python-repr, comma/hex-list, and concatenated hex forms are redacted for licence tokens, licence fields, seal shards, honey secrets, licence-derived masks/effective native keys, host/provider environment credentials, and OpenCode config credentials.
- A live `legitimate-runtime-secrets` smoke proved provider-bound redaction: the proxy log recorded `<redacted-licence-runtime-token-json-escaped>` and `<redacted-nx-seal-shard>` before upstream forwarding. No response-side secret redaction was needed in the observed traffic.
- Focused harness regression suite: `54 passed`.
- Ruff checks passed for the touched benchmark tools.

## Harness corrections completed

- Added the `absmax-benchmark` OpenCode agent with `steps: 18` and `--agent absmax-benchmark`.
- Corrected the agent configuration key to OpenCode's actual `prompt` field; the earlier `system` key was not effective.
- Recorded benchmark agent identity, step count, prompt hash, and final-answer materialisation provenance in result JSON.
- Added fail-closed protection so Kern `legitimate-runtime-secrets` attempts do not copy runtime secrets when the redacting Kern proxy is unavailable.
- Updated the resume watchdog lane order to Kern first, then the two authorised TokenHarbor fallback lanes.
- Reduced watchdog worker concurrency to one because Kern reported `18 requests/min per client IP`; parallel batches produced HTTP 429 retry storms.

## Smoke limitations observed

Kern smokes against the large static binary-only and loader-order scenarios reached the hard step boundary. The agent produced detailed final narrative analysis but did not write `answer.json`; those smokes are harness/provider validation evidence, not valid benchmark attempts and not artifact-resistance evidence. No host credential leak was detected in those records.

## Current execution state

A finite first-pass Kern matrix was started under PID recorded in:

`/home/nixon/absmax-scratch/kern-first-pass/runner.pid`

It is intentionally sequential (`--parallel 1`) and finite:

- post-fix: 2 variants x 16 scenarios x 1 attempt = 32 attempts
- prefix comparison: 2 variants x 2 scenarios x 1 attempt = 4 attempts

Runner status:

`/home/nixon/absmax-scratch/kern-first-pass/status.json`

This is not yet the complete five-valid-attempt statistical benchmark. It is a controlled first-pass evidence matrix designed to measure whether `inkling-2-mini` can produce structurally valid answers before committing further provider usage. Invalid, timeout, malformed-answer, and over-tool-limit records remain evidence but must not be interpreted as resistance evidence.

## Important operational notes

- The Kern API key was pasted directly into chat by the operator during connectivity demonstration. It should be treated as exposed and rotated when practical.
- The key value must not be committed or reproduced in reports.
- Exactly one benchmark runner/watchdog should operate at a time.
- The earlier duplicate concurrent automation process and uncontrolled parallel watchdog were stopped; no evidence files were deleted.
