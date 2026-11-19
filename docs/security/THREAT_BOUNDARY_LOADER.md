# Threat boundary: what the loader can and cannot hide

**Status: accepted.** This file records a limit that was *measured*, not
assumed, and the decision that follows from it. It exists so the next person to
open "the loader is readable" does not spend a week renaming symbols.

## What was measured

PyDeObsBench §5l gave DeepSeek V4.1 Flash the text of a real `max`-profile
artefact (280 KB, built in 14.5 s). The model reconstructed the enforcement
layer completely, with no debugger and no execution:

* `prctl(PR_SET_DUMPABLE=0)` and `RLIMIT_CORE=(0,-1)`
* the identity gate and its exit path
* `constant_time_compare`'s OR-accumulate-of-XOR construction
* `_nx_self_fail` → `os._exit(137)` and its message format
* `_nx_mlock`'s `addressof` / page-alignment construction

Then the obvious remedy was tested rather than assumed. The loader's **187
symbols** were renamed to opaque identifiers — the strongest symbol-level
obfuscation available. Afterwards, every behaviour-bearing constant was still
present:

| marker | survives total symbol renaming |
|---|---|
| `prctl` | yes |
| `137` | yes |
| `RLIMIT_CORE` | yes |
| `mlock` | yes |
| `0o600` | yes |
| the `self-check error:` string | yes |

**Renaming symbols does not hide behaviour.** The model did not recover
`_nx_self_fail` — it recovered *"writes to stderr and calls `os._exit(137)`"*.
Those are syscall numbers and constants, and they are what the code must do to
work. An obfuscation pass that changes only names cannot touch them.

## The decision

The protection is therefore split into two claims, and they are graded
separately:

| layer | measured outcome | stands or falls |
|---|---|---|
| **Payload** (what the customer ships: source, algorithms, secrets) | 0/4 names, 0/2 secrets static; 0/2 secrets and 0/4 names in memory across 14 samples; semantic equivalent matches at 0.00 identifier overlap | **holds** |
| **Wrapper** (how integrity, licensing and anti-dump are enforced) | fully reconstructed from artefact text | **does not hold — accepted** |

This is the "payload-vs-wrapper boundary" as the target threat model. It is a
deliberate scope statement, not a workaround:

* Hiding the *payload* is achievable, because the payload is data and data can
  be sealed under keys the attacker does not have.
* Hiding the *enforcement mechanism* is not achievable in client-side Python.
  The mechanism must execute on the attacker's machine, so its behaviour is
  necessarily observable; and because the artefact is text they can read, its
  structure is necessarily readable. This is the same class of limit the review
  itself names — *"absolute irreversibility isn't a realistic guarantee for
  client-side software"*.

## What this costs, concretely

An attacker who reads the wrapper learns:

* exactly which guards run, and in what order,
* that the integrity check is a Merkle root plus an HMAC over the artefact,
* where the anti-dump calls are, and therefore how to avoid them (`mlock` a
  buffer instead, or patch `prctl` before the loader runs).

An attacker who reads the wrapper does **not** learn:

* the payload's identifiers, literals or algorithm,
* the sealing key material (the loader derives it; the shares in the artefact
  reconstruct it only with the customer mask),
* anything that makes 0/4 and 0/2 become non-zero.

§1's five measured attack routes all still end at `rc 137` **after** the loader
was fully read — including tamper + re-stamp, which the second HMAC layer
caught. Reading the mechanism is not the same as defeating it, and the
difference is why this boundary is acceptable rather than fatal.

## What would change the answer

Not more symbol obfuscation. The only approaches that could hide the *mechanism*
are ones where the mechanism is not in the artefact at all:

1. **Move enforcement into the native blob.** The C transform already emits C;
   the guards could be C functions rather than Python. That raises the cost from
   "read the file" to "reverse the .so" — a real increase, though the blob is
   itself extractable (the loader carries its key).
2. **Move enforcement off-device.** A licensing/attestation service that the
   artefact must reach; the mechanism then lives on infrastructure the attacker
   does not control. This changes the deployment model, not just the code.
3. **Accept and price it.** Which is what this document does: the payload holds,
   the wrapper is transparent, and both are measured.

Options 1 and 2 are recorded as future work because neither is a tuning change
and both have costs the current design deliberately avoids (option 2 requires
network availability at runtime; option 1 requires the guards to be reimplemented
in C, including the Cython boundary).
