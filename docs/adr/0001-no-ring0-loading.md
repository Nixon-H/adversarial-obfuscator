# ADR 0001 — No Ring-0 Loading

## Context

A kernel-driver gate was requested ("V10 kernel-driver gate") to blunt
BYOVD attacks, where an attacker brings a known-vulnerable signed driver
and uses it for privilege escalation. The naive implementation loads a
driver or opens IOCTL channels to inspect kernel state — which would
make the *defensive* tool itself a ring-0 loader with all the attendant
signing, stability, and supply-chain risk.

## Decision

Detection is **read-only enumeration plus blocklist comparison**. No
driver loading, no ring-0 code, no IOCTLs, no service/driver
installation, no writes of any kind — in both the Python gate
(`obfuscator/driver_blocklist.py:1`) and the native gate
(`native/stub_win.cpp:643`). When armed, a blocklist hit fails closed
through the existing kill ladder (`_nx_kill("driver-blocked")`, exit
137) instead of attempting any remediation that would need privilege.

## Alternatives considered

- **Load a helper driver for ground-truth enumeration.** Rejected: turns
  the protector into a BYOVD candidate itself; needs EV signing,
  per-OS-version maintenance, and blows up the trust story.
- **IOCTL-based driver interrogation.** Rejected: same privilege
  escalation as loading, plus IOCTL parsing is a classic bug farm.
- **No driver gate at all.** Rejected: BYOVD is a real commodity attack
  path and a read-only blocklist is cheap (~20 stems, one `/proc`
  read or one `EnumDeviceDrivers` call).

## Consequences

- The gate cannot see hidden (unlinked) drivers — enumeration only sees
  what the OS lists. Documented limitation, not a silent gap.
- The gate is opt-in (build `--driver-check` or runtime
  `NIXON_DRIVER_CHECK=1`); default disarmed, so protection requires
  operator action.
- Positive: zero new privileges, zero new attack surface in the loader.

## Evidence

- Scope contract: `obfuscator/driver_blocklist.py:1`, native contract
  `native/stub_win.cpp:643`; blocklist `native/stub_win.cpp:681`,
  enumeration `native/stub_win.cpp:719`.
- Absence proof: `NtLoadDriver`, `CreateService`, `DeviceIoControl`
  return zero hits across all non-test Python/C/C++/Rust sources
  (enforced by `tests/test_security_invariants.py::test_no_driver_loading_ioctl`,
  `grep -rn` verified 2026-09-28).
