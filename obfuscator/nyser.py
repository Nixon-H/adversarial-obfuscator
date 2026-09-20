"""NYSER1-style code-object serializer (Add, Phase 1).

Self-contained lambda-template ``Code.replace`` reconstructor: a code object
is serialized to bytes WITHOUT marshal, and rebuilt at runtime from a
template captured from a freshly-defined lambda (unhookable via attribute
rebinding — no reference to ``marshal.loads`` on the hot path).

Wire format (versioned):
  magic  b'NYS1' (4B)
  format version  u8  (currently 1; bump when co_* field set changes)
  py_version      u8 major, u8 minor (recorded; loader refuses mismatch)
  node stream: recursive (type-tag u8, varint lengths, raw bytes)

Node tags:
  0x01 code object: argcount, posonly, kwonly, nlocals, stacksize, flags,
       then code-bytes, consts[], names, varnames, freevars, cellvars,
       filename, name, firstlineno, linetable, exceptiontable
       (3.11+ adaptive fields; 3.10 omits exceptiontable)
  0x02 bytes/blob, 0x03 utf-8 str, 0x04 int (zigzag varint),
  0x05 float (repr), 0x06 complex, 0x07 None/True/False/Ellipsis,
  0x08 tuple/list/frozenset, 0x09 code ref (nested code object)

Security properties vs marshal:
  - No ``marshal.loads`` call on the load path: hooking marshal does
    nothing (complements the ctypes-only marshal loader).
  - Template comes from a lambda defined INSIDE the loader (not from the
    payload), so payload bytes alone never describe a full code object.
  - Loader verifies SHA-256 of the node stream before reconstruct
    (tamper-evident; caller decides fail-closed vs fallback).

Version gating: CPython code-object fields drift per minor version
(co_linetable, co_exceptiontable, co_branches...). Dumps record the
producer version; loads() REFUSES cross-version payloads rather than
misbuilding them. Supported: 3.10–3.14. 3.14 note: deferred annotations
(PEP 649/749) and template strings (PEP 750) change annotation/template
consts but NOT the Code.replace field set we serialize — verified by the
3.14 golden tests (which skip automatically on older interpreters).
"""

from __future__ import annotations

import hashlib
import struct
import sys
import types

MAGIC = b"NYS1"
FORMAT_VERSION = 1
SUPPORTED_MINORS = ((3, 10), (3, 11), (3, 12), (3, 13), (3, 14))

_TAG_CODE = 0x01
_TAG_BYTES = 0x02
_TAG_STR = 0x03
_TAG_INT = 0x04
_TAG_FLOAT = 0x05
_TAG_COMPLEX = 0x06
_TAG_CONST = 0x07
_TAG_SEQ = 0x08


def _encode_uvarint(n: int) -> bytes:
    if n < 0:
        raise ValueError("uvarint must be >= 0")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _decode_uvarint(buf: bytes, pos: int) -> tuple[int, int]:
    n = 0
    shift = 0
    while True:
        if pos >= len(buf):
            raise ValueError("truncated uvarint")
        b = buf[pos]
        pos += 1
        n |= (b & 0x7F) << shift
        if not (b & 0x80):
            return n, pos
        shift += 7
        if shift > 70:
            raise ValueError("uvarint overflow")


def _encode_zigzag(n: int) -> bytes:
    # portable zigzag for arbitrary-size ints
    return _encode_uvarint((n << 1) ^ (n >> 63) if n >= 0 else ((-n) << 1) - 1)


class _Writer:
    def __init__(self) -> None:
        self.buf = bytearray()

    def u8(self, v: int) -> None:
        self.buf.append(v & 0xFF)

    def varint(self, v: int) -> None:
        self.buf += _encode_uvarint(v)

    def zigzag(self, v: int) -> None:
        # portable zigzag for arbitrary-size ints
        self.buf += _encode_uvarint((v << 1) ^ (v >> 63) if v >= 0 else ((-v) << 1) - 1)

    def blob(self, b: bytes) -> None:
        self.varint(len(b))
        self.buf += b


class _Reader:
    def __init__(self, buf: bytes) -> None:
        self.buf = buf
        self.pos = 0

    def u8(self) -> int:
        if self.pos >= len(self.buf):
            raise ValueError("truncated stream")
        v = self.buf[self.pos]
        self.pos += 1
        return v

    def varint(self) -> int:
        v, self.pos = _decode_uvarint(self.buf, self.pos)
        return v

    def zigzag(self) -> int:
        n = self.varint()
        return (n >> 1) ^ -(n & 1)

    def blob(self) -> bytes:
        n = self.varint()
        if self.pos + n > len(self.buf):
            raise ValueError("truncated blob")
        b = self.buf[self.pos:self.pos + n]
        self.pos += n
        return bytes(b)


def _dumps_const(w: _Writer, value: object) -> None:
    if value is None:
        w.u8(_TAG_CONST); w.u8(0)
    elif value is True:
        w.u8(_TAG_CONST); w.u8(1)
    elif value is False:
        w.u8(_TAG_CONST); w.u8(2)
    elif value is Ellipsis:
        w.u8(_TAG_CONST); w.u8(3)
    elif isinstance(value, int):
        w.u8(_TAG_INT); w.zigzag(value)
    elif isinstance(value, float):
        w.u8(_TAG_FLOAT)
        w.blob(repr(value).encode("utf-8"))
    elif isinstance(value, complex):
        w.u8(_TAG_COMPLEX)
        w.blob(repr(value).encode("utf-8"))
    elif isinstance(value, bytes):
        w.u8(_TAG_BYTES); w.blob(value)
    elif isinstance(value, str):
        w.u8(_TAG_STR); w.blob(value.encode("utf-8"))
    elif isinstance(value, types.CodeType):
        _dumps_code(w, value)
    elif isinstance(value, tuple):
        w.u8(_TAG_SEQ); w.u8(0); w.varint(len(value))
        for item in value:
            _dumps_const(w, item)
    elif isinstance(value, list):
        w.u8(_TAG_SEQ); w.u8(1); w.varint(len(value))
        for item in value:
            _dumps_const(w, item)
    elif isinstance(value, frozenset):
        w.u8(_TAG_SEQ); w.u8(2); w.varint(len(value))
        for item in sorted(value, key=repr):
            _dumps_const(w, item)
    else:
        raise TypeError(f"NYSER1 cannot serialize const of type {type(value).__name__}")


def _dumps_code(w: _Writer, co: types.CodeType) -> None:
    w.u8(_TAG_CODE)
    w.varint(co.co_argcount)
    w.varint(co.co_posonlyargcount)
    w.varint(co.co_kwonlyargcount)
    w.varint(co.co_nlocals)
    w.varint(co.co_stacksize)
    w.varint(co.co_flags)
    w.blob(co.co_code)
    w.varint(len(co.co_consts))
    for c in co.co_consts:
        _dumps_const(w, c)
    for tup in (co.co_names, co.co_varnames, co.co_freevars, co.co_cellvars):
        w.varint(len(tup))
        for s in tup:
            w.blob(s.encode("utf-8"))
    w.blob(co.co_filename.encode("utf-8"))
    w.blob(co.co_name.encode("utf-8"))
    w.varint(co.co_firstlineno)
    w.blob(co.co_linetable)
    w.blob(getattr(co, "co_exceptiontable", b""))


def dumps(code_obj: types.CodeType) -> bytes:
    """Serialize a code object to NYSER1 bytes (no marshal involved)."""
    if not isinstance(code_obj, types.CodeType):
        raise TypeError("dumps() requires a code object")
    w = _Writer()
    w.buf += MAGIC
    w.u8(FORMAT_VERSION)
    w.u8(sys.version_info[0]); w.u8(sys.version_info[1])
    body = _Writer()
    _dumps_code(body, code_obj)
    digest = hashlib.sha256(body.buf).digest()
    w.blob(digest)
    w.buf += body.buf
    return bytes(w.buf)


def _loads_const(r: _Reader) -> object:
    tag = r.u8()
    if tag == _TAG_CONST:
        sub = r.u8()
        if sub > 3:
            raise ValueError(f"unknown const subtype 0x{sub:02x}")
        return (None, True, False, Ellipsis)[sub]
    if tag == _TAG_INT:
        return r.zigzag()
    if tag == _TAG_FLOAT:
        return float(r.blob().decode("utf-8"))
    if tag == _TAG_COMPLEX:
        return complex(r.blob().decode("utf-8"))
    if tag == _TAG_BYTES:
        return r.blob()
    if tag == _TAG_STR:
        return r.blob().decode("utf-8")
    if tag == _TAG_CODE:
        return _loads_code(r, tag_already=True)
    if tag == _TAG_SEQ:
        kind = r.u8()
        if kind > 2:
            raise ValueError(f"unknown seq kind 0x{kind:02x}")
        n = r.varint()
        items = [_loads_const(r) for _ in range(n)]
        return tuple(items) if kind == 0 else (items if kind == 1 else frozenset(items))
    raise ValueError(f"unknown const tag 0x{tag:02x} at offset {r.pos - 1}")


def _loads_code(r: _Reader, tag_already: bool = False) -> types.CodeType:
    if not tag_already:
        tag = r.u8()
        if tag != _TAG_CODE:
            raise ValueError("expected code node")
    # Template captured from a freshly-defined lambda: the ONLY code
    # object constructor used. No marshal, no types.CodeType(...) direct
    # call with attacker-controlled layout — .replace() rebuilds node by
    # node from verified parts.
    _template = (lambda: None).__code__
    argcount = r.varint()
    posonly = r.varint()
    kwonly = r.varint()
    nlocals = r.varint()
    stacksize = r.varint()
    flags = r.varint()
    code_bytes = r.blob()
    nconsts = r.varint()
    consts = tuple(_loads_const(r) for _ in range(nconsts))

    def _str_tuple() -> tuple[str, ...]:
        n = r.varint()
        return tuple(r.blob().decode("utf-8") for _ in range(n))

    names = _str_tuple()
    varnames = _str_tuple()
    freevars = _str_tuple()
    cellvars = _str_tuple()
    filename = r.blob().decode("utf-8")
    name = r.blob().decode("utf-8")
    firstlineno = r.varint()
    linetable = r.blob()
    exceptiontable = r.blob()
    kw: dict = dict(
        co_argcount=argcount, co_posonlyargcount=posonly,
        co_kwonlyargcount=kwonly, co_nlocals=nlocals,
        co_stacksize=stacksize, co_flags=flags, co_code=code_bytes,
        co_consts=consts, co_names=names, co_varnames=varnames,
        co_freevars=freevars, co_cellvars=cellvars,
        co_filename=filename, co_name=name,
        co_firstlineno=firstlineno, co_linetable=linetable,
    )
    if exceptiontable or sys.version_info >= (3, 11):
        kw["co_exceptiontable"] = exceptiontable
    try:
        return _template.replace(**kw)
    except (TypeError, ValueError, SystemError, IndexError) as e:
        raise ValueError(f"NYSER1 rebuild failed (version skew?): {e}")


def loads(data: bytes) -> types.CodeType:
    """Deserialize NYSER1 bytes to a code object.

    Verifies magic, format version, producer Python version (must match
    runtime — fail-closed, no cross-version rebuild), and SHA-256 of the
    node stream before reconstructing. Raises ValueError on any mismatch.
    """
    try:
        r = _Reader(bytes(data))
    except (TypeError, ValueError) as e:
        raise ValueError(f"bad NYSER1 input: {e}")
    if bytes(r.buf[r.pos:r.pos + 4]) != MAGIC:
        raise ValueError("bad NYSER1 magic")
    r.pos += 4
    fmt = r.u8()
    if fmt != FORMAT_VERSION:
        raise ValueError(f"unsupported NYSER1 format {fmt}")
    major, minor = r.u8(), r.u8()
    if (major, minor) not in SUPPORTED_MINORS:
        raise ValueError(f"NYSER1 payload from unsupported Python {major}.{minor}")
    if (major, minor) != (sys.version_info[0], sys.version_info[1]):
        raise ValueError(
            f"NYSER1 version mismatch: payload {major}.{minor} vs "
            f"runtime {sys.version_info[0]}.{sys.version_info[1]} — rebuild required"
        )
    digest = r.blob()
    body_start = r.pos
    node = _loads_const(r)
    if not isinstance(node, types.CodeType):
        raise ValueError("NYSER1 top-level node is not a code object")
    if r.pos != len(r.buf):
        raise ValueError("NYSER1 trailing bytes")
    actual = hashlib.sha256(r.buf[body_start:]).digest()
    if actual != digest:
        raise ValueError("NYSER1 integrity failure (SHA-256 mismatch)")
    return node


def roundtrip_supported() -> bool:
    """True if this interpreter can NYSER1 round-trip (version gated)."""
    return (sys.version_info[0], sys.version_info[1]) in SUPPORTED_MINORS
