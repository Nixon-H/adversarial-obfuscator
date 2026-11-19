"""§4 kernel-state probe for nx_apply_protections (run in a subprocess).

Loads the blob given in NX_ENF_SO with ctypes, calls the enforcement entry,
and prints the resulting kernel state so a test can assert the policy was
actually applied rather than assumed. Kept as a committed fixture file so
no test has to generate code at runtime.

The probe process itself ends up non-dumpable with an empty core limit --
that is the POINT, and it exits immediately after printing.
"""
import ctypes
import os

lib = ctypes.CDLL(os.environ["NX_ENF_SO"])
mask = int(lib.nx_apply_protections() or 0)

fields = {}
for line in open("/proc/self/status"):
    if ":" in line:
        key, value = line.split(":", 1)
        fields[key] = value.strip()

print("mask=%d core=%s" % (mask, fields.get("CoreDumping")))
