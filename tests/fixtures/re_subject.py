"""Reverse-engineering evaluation subject — obfuscated arm.

This is the payload an independent analyst receives as a BUILT ARTEFACT.
The source is not given to them; it exists here so the evaluation can be
scored objectively rather than by impression.

The semantics are deliberately finite and checkable: four objectives the
register names, each with a definite answer an analyst either recovers or
does not. Nothing here is a trick — the point of the evaluation is to measure
what obfuscation does to recovery cost, not to construct an unfair puzzle.

Objectives (see docs/security/RE_EVALUATION_PROTOCOL.md):

  O1 ENTRY        the entry function is `settle_account`.
  O2 ALGORITHM    `settle_account` computes a weighted running balance where
                  each entry is scaled by a decay applied in integer math.
                  Precisely: balance = sum(amount_i * weight_i) // 1000,
                  with weight_i = 1000 - 7*i, and a final adjustment that
                  subtracts `penalty` once if the balance exceeds THRESHOLD.
  O3 STRINGS      three observable string constants: "settled", "rejected",
                  "audit" — plus the marker the driver prints.
  O4 INTEGRITY    the artefact refuses to run when its own bytes change
                  (the loader's provenance/integrity check), and the failure
                  is silent (exit 137) rather than diagnostic.

A control arm is built from the SAME semantics with obfuscation disabled, so
the analyst's cost on the control is the baseline the obfuscated cost is
measured against.
"""
import sys

THRESHOLD = 50000
DECAY = 7


def settle_account(entries, penalty):
    """Return (balance, verdict). This is objective O1/O2."""
    balance = 0
    for index, amount in enumerate(entries):
        weight = 1000 - DECAY * index
        if weight < 1:
            weight = 1
        balance += amount * weight
    balance //= 1000
    if balance > THRESHOLD:
        balance -= penalty
        verdict = "settled"
    else:
        verdict = "rejected"
    return balance, verdict


def emit_audit(verdict):
    """Produces the third string constant, "audit"."""
    return "audit:" + verdict


def main():
    entries = [12000, 9000, 15000, 3000]
    penalty = 250
    balance, verdict = settle_account(entries, penalty)
    print("RE-SUBJECT-OUTCOME", balance, verdict)
    print(emit_audit(verdict))
    return 0


if __name__ == "__main__":
    sys.exit(main())
