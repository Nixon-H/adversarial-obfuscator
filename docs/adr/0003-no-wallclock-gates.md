# ADR 0003 — No Bare Wall-Clock Gates

## Context

Trial expiry (`--trial 7d`) is inherently time-based, but the wall
clock is attacker-controlled (`date -s`, VM clock games, NTP spoofing).
A bare `now > deadline` gate is defeated by turning the clock back, and
a bare `now < last_seen` check false-fires on legitimate NTP corrections
and dual-boot clock skew.

## Decision

No gate reads the wall clock bare. Every `time.time()` read in
enforcement is paired with an **HMAC-sealed monotonic last-seen stamp**:
on each `ok` run the stamp advances (`seal_last_seen`,
`obfuscator/trial_bind.py:222`); each run rejects seals that fail
`unseal_last_seen` (`obfuscator/trial_bind.py:235`,
`ValueError` → `tampered`) and rejects `now < last_seen - tolerance`
(`obfuscator/trial_bind.py:370`) with a `rollback` verdict. Binding is
checked before expiry (`check_trial`, `obfuscator/trial_bind.py:254`),
and the full gate is binding + deadline + rollback
(`check_and_update`, `obfuscator/trial_bind.py:314`).

## Alternatives considered

- **Bare `now > deadline`.** Rejected: one `date -s` defeats it.
- **Zero-tolerance rollback (`now < last_seen` ⇒ kill).** Rejected:
  legitimate skew (NTP step, dual-boot) would brick paying artifacts.
  The 300 s `ROLLBACK_TOLERANCE_S` allowance trades a small replay
  window for availability.
- **Monotonic-only clock (`CLOCK_MONOTONIC`).** Rejected as sole
  source: monotonic clocks reset on reboot and cannot express an
  absolute trial deadline; used implicitly nowhere, absolute deadline
  always bounds the window.

## Consequences

- Deleting the state dotfile restarts `last_seen` at now (documented at
  `obfuscator/trial_bind.py:44`) — bounded by the absolute deadline, so
  the exposure is a window extension, not a bypass.
- Clock jumps inside the 300 s tolerance are undetectable by design;
  the sealed stamp still prevents large rollbacks.
- The emitted runtime snippet takes no `flock`
  (`obfuscator/trial_bind.py:467`); concurrent same-artifact runs risk
  one stale window at most (monotonic HMAC writes), never a pass-from-
  corrupt-state.

## Evidence

- Seal/unseal: `obfuscator/trial_bind.py:222`,
  `obfuscator/trial_bind.py:235`; tamper fail-closed
  `obfuscator/trial_bind.py:364`; rollback verdict
  `obfuscator/trial_bind.py:370`; build-time lock
  `obfuscator/trial_bind.py:97`; snippet `O_NOFOLLOW`
  `obfuscator/trial_bind.py:382`, `obfuscator/trial_bind.py:620`.
- Measured numbers: tolerance 300 s (`ROLLBACK_TOLERANCE_S`); trial
  format/parity suite `tests/test_trial_bind.py`, `tests/test_macros.py`
  (no wall-clock mock escapes: tests inject `now=` explicitly).
