# Pending work tracker

## Waiting on the phone (plug in vivo V2338 USB when ready)

1. Artifact end-to-end validation ×3 — one biometric approval each:
   - `/home/nixon/absmax-scratch/cloudflare-remote-artifacts/launchers/run-absolute-maximum.sh`
   - `/home/nixon/absmax-scratch/cloudflare-remote-artifacts/launchers/run-local-maximum.sh`
   - `/home/nixon/absmax-scratch/cloudflare-remote-artifacts/launchers/run-cloud-maximum.sh`
   Wait ~20-30 s after launch, tap "Check for pending requests" on the
   matching worker tab, approve `seal_hex`. 15-minute window per request.
2. Push-notification test — reload one worker tab on the phone, ALLOW
   notification permission when Chrome asks, then close Chrome entirely and
   ask for a test probe: the phone should buzz within seconds.

## Closed 2026-11-27/28

- Genuine remote split end-to-end (direct client round trip approved on phone)
- NIXON_REMOTE_APPROVAL_MODE=required on all 3 workers (TOTP cannot bypass)
- Approval expiry 900s live; launcher client timeout aligned (850s)
- Passkeys enrolled ×3 workers; passkey+push+anomaly+security-headers deployed
- Fail-closed pipeline fix; commit-trailer history rewrite; farm repo deleted

## Analysis state (2026-11-28)

- Statistical repeat runner COMPLETED cleanly: 126 jobs, no missing variants
  (status: /home/nixon/absmax-scratch/profile-matrix-go-v12-status.json).
- 486 repeat-trial result files exist across 4 variants x 16 scenarios.
- REMAINING: score them with the harness evaluator (not heuristics):
  the evaluation schema lives in re-bench/tools/ai_bench.py; use the harness's
  own scoring path, then compare exploit rates per variant against the
  original-run verdict in deepseek_benchmark_aggregate.json. Until that runs,
  no statistical claim should be quoted.

## Operational decisions (2026-11-28)

- Cloudflare API token rotation: must be done in the Cloudflare dashboard
  (Tokens -> roll). API tokens cannot rotate themselves. Owner action;
  then replace /home/nixon/.config/cloudflare/api_token (0600).
- Provisioning secrets: KEEP the current arrangement — customer provisioning
  JSONs are mode-0600 owner-only on the operator machine, the launchers read
  them, and moving them into a system keyring adds no real protection on the
  same threat model (same machine compromise). Documented as accepted risk.
  The master provisioning files must never leave this machine.
- Loader error masking (exit 79): FIXED 2026-11-28 (commit: report real
  payload errors). Root cause was different from the note above: non-ImportError
  payload exceptions inside exec_module were swallowed as a None verdict, so
  the fatal misfired on any mid-run payload failure. Now the real exception is
  recorded and surfaced ("payload started but failed inside the native module:
  <error>"), and module-name retry stops after a mid-run failure. Validated
  end-to-end on the v4 absolute artifact. Regression test:
  tests/test_payload_error_reporting.py.
- External signing: scoped as future work — obfuscator/authenticode.py and
  authenticode_verify.py exist; the open question is whether to sign the
  native .so/.pyd blobs embedded in artifacts (self-signed vs CA) and how
  verification integrates with the loader. Needs owner direction before
  implementation.


## Status update 2026-11-28 (this session)

- Benchmark repeat analysis: DONE — see
  re-bench/ABSOLUTE_MAXIMUM_RAW_RESULTS/ai_benchmark_profile_matrix_go-v12/REPEAT_ANALYSIS.md
  Headline: 0/165 valid non-source-assisted exploits across all 6 variants;
  source-assisted-static positives are control positives by design.
  Coverage gap noted: legitimate-runtime-secrets / runtime-secrets-withheld
  not in the repeat matrix — prioritize those in any future round.
- v4 artifact rebuilds (fixed loader + approval progress notice embedded):
  absolute DONE + validated; maximum-local/maximum-cloud rebuilding.
  PHONE validation should use the v4 artifacts once all three are built.
- Loader UX progress notice + approval-page empty-state text: committed.
  NOTE: workers still need a redeploy for the page-text fix to go live;
  the push/anomaly/security-header deployment predates it.
