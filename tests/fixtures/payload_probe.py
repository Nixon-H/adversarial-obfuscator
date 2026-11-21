"""Release-candidate probe payload: prints a marker then holds memory.

Built by tests/test_release_acceptance.py so the memory-dump probe has a
window in which the payload plaintext is resident. The marker string is what
the dump scan searches for.
"""
import time

print("RC-ACCEPT-MARKER-7f3a")
time.sleep(6)
