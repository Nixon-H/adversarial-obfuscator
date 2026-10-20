# ADR 0004 — Callee-Speed Floor (Timing Never Kills by Default)

## Context

Execution-speed checks ("kill if this callee runs slower/faster than X")
are tempting as anti-instrumentation signals, but speed is the least
trustworthy signal available: hypervisors, power management, CPU
throttling, noisy neighbours, and debuggers all move it by orders of
magnitude. A speed floor in the default path would turn every slow CI
runner, laptop on battery, and oversubscribed VM into a kill — an
availability bug dressed as security.

## Decision

Loader gates **never enforce on callee execution speed by default**.
Timing-derived signals (VM `timing` steal check, `clock_bias`
side-channel) feed the weighted VM *score* (`obfuscator/vm_score.py:61`,
`SIGNALS` weights), which is report-only unless the operator arms
kill-on-detect (`NIXON_KOD`, `obfuscator/vm_score.py:417`, default
`"0"`). The audit-hook timing-kill is likewise opt-in
(`NIXON_AUDIT_TIMING`, `obfuscator/audit_hook.py:77`,
default `"0"` = off, `obfuscator/audit_hook.py:361`). Speed can inform;
only explicit operator arming lets it kill.

## Alternatives considered

- **Default-on timing kill.** Rejected: false-positive rate is
  environment-dominated, not attacker-dominated; first-strike exit on a
  noisy signal bricks legitimate deployments.
- **No timing signals at all.** Rejected: steal-time and clock-bias are
  genuinely informative VM indicators when weighted with 11 other
  signals; dropping them weakens the score for zero availability gain
  (they cost nothing while report-only).
- **Adaptive per-host calibration.** Rejected for now: calibration
  storage is itself attacker-writable state (see THREAT_MODEL
  corrupted-state row); static weights + operator arming is the honest
  trade until calibration can be sealed like trial state.

## Consequences

- Default artifacts cannot be killed by slow hardware — availability
  preserved; VM detection still reports through the score.
- Operators who arm `NIXON_KOD` / `NIXON_AUDIT_TIMING` accept the
  false-positive trade explicitly.
- Known non-ladder exits stay documented variance, not precedent:
  timing-traps `hard_exit` (`sys.exit(1)`) and `py_matrix` version-gate
  (`sys.exit(1)`) are caller-visible failures, not tamper kills
  (`obfuscator/kill_ladder.py` docstring (d)).

## Evidence

- Scoring weights: `obfuscator/vm_score.py:20` (`SIGNALS`, 14 signals,
  timing 10 / total 235); KOD default-off `obfuscator/vm_score.py:417`; timing arm
  default-off `obfuscator/audit_hook.py:116`, `obfuscator/audit_hook.py:361`.
- Kill ladder choke point `obfuscator/kill_ladder.py:44` (`KILL_CODE =
  137`); silent-kill parity `native/crash_suppress.h:46`.
- No measured speed-floor numbers exist in-tree (no such gate ships) —
  nothing to cite; the lowering overhead tables
  (`obfuscator/lowering_DESIGN.md`, per-family geomeans 1.46x–3.84x)
  describe obfuscation cost, not enforcement thresholds, and must not
  be repurposed as such.
