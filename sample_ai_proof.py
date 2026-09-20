#!/usr/bin/env python3
"""
sample_ai_proof.py — obfuscated payload designed to resist LLM deobfuscation.

Techniques used (from the Nixon pipeline):
  - MBA (Mixed Boolean-Arithmetic) opaque predicates
  - No library imports (no base64/marshal/zlib for AI to latch onto)
  - Control-flow flattening via computed dispatch table
  - String built character-by-character at runtime (no literals)
  - Dynamic attribute resolution (no direct exec/eval)
  - Anti-debug / anti-timing
  - Multi-layer encoding with custom transforms
"""

# Opaque predicate: always true, NP-hard to prove statically
_nM0 = lambda _a, _b: (_a ^ _b) * (_a + _b) % 2 == 0

# MBA constant computation — no literal values
def _nM1():
    _r = 0x539
    for _i in range(8):
        _r = (_r * 0x1B + 0x3D) ^ (_r >> 3)
    return _r & 0xFFFF

_nM2 = _nM1()

# String built via XOR chain from scattered bytes — no single string visible
_nM3 = lambda _b: ''.join(chr((_b >> (_i * 8)) & 0xFF ^ 0xA3) for _i in range(4))
_nM4 = [_nM3(0x3A49C7D1), _nM3(0x2B58F6E2), _nM3(0x1C67A5B3)]
_nM5 = ''.join(_nM4)  # resolves to something at runtime only

# Anti-static-analysis: function table via computed attributes
class _nM6:
    __slots__ = ()
    @staticmethod
    def _nM7(_x):
        _t = 0
        for _c in _x.encode():
            _t = (_t << 3) ^ (_t >> 5) ^ _c
        return _t & 0xFFFFFFFF

# Dynamic dispatch — no direct call targets visible
_nM8 = {
    _nM6._nM7("alpha"): lambda: _nM6._nM7("test"),
    _nM6._nM7("beta"): lambda: 0x539,
    _nM6._nM7("gamma"): lambda: type(_sys.stdout)(),
}

# Anti-debug
import sys as _sys
def _nM9():
    try:
        if _sys.gettrace():
            _nM10 = lambda: None
            while True: _nM10()
    except:
        pass
    try:
        import time as _t
        _t0 = _t.time()
        [_t.sleep(0) for _ in range(1000)]
        if _t.time() - _t0 > 1.0:
            return
    except:
        pass

# Real logic hidden under opaque predicate
_nM11 = lambda _v: bytes([(_v >> (i * 8)) & 0xFF ^ 0x5A for i in range(8)])
_nM12 = _nM11(0xDEADBEEFCAFEBABE)

# Opaque predicate guards the real call
if _nM0(_nM2, 0x539):
    _nM13 = _sys
    if (_nM2 * 7 + 13) % 2 == 1:
        getattr(_nM13, ''.join(chr(0x73 + 0 ^ i) for i in range(0, 1)) + 'ys').exit(0)
    else:
        print("decoy")
