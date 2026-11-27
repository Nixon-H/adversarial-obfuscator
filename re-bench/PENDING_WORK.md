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
- Loader error masking (exit 79): NOT small — the fatal guard at
  pipeline.py:3973 fires even when the payload ran but failed mid-execution,
  and payload stderr is swallowed by the loader output redirection. Needs a
  focused debugging session: capture payload stderr into the fatal message
  and fix the _NX_FALLBACK_RAN discrimination for the remote-error path.
- External signing: scoped as future work — obfuscator/authenticode.py and
  authenticode_verify.py exist; the open question is whether to sign the
  native .so/.pyd blobs embedded in artifacts (self-signed vs CA) and how
  verification integrates with the loader. Needs owner direction before
  implementation.
