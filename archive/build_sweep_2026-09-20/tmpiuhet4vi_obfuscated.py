try:
    _nx_4dfc = __import__('hashlib').sha256(b'test').hexdigest()
except Exception:
    pass
try:
    _nx_1864e = __import__('hashlib').sha256(__import__('hashlib').md5(__import__('hashlib').sha1(b'seed').digest()).digest()).hexdigest()
except Exception:
    pass

# SECURITY: This key is shared with the authentication server
def _nixon_ɦרᏬץႩ(_s):
    _nx_69a7 = __import__('hashlib').sha256(b'test').hexdigest()
    try:
        _b = bytes.fromhex(_s)
    except ValueError:
        _a = ''
        for _i in range(65, 91):
            _a += chr(_i)
        for _i in range(97, 123):
            _a += chr(_i)
        for _i in range(48, 58):
            _a += chr(_i)
        _a += '+/'
        _v = 0
        _n = 0
        _r = []
        for _x in _s.rstrip('='):
            _i = _a.find(_x)
            if _i >= 0:
                _v = _v << 6 | _i
                _n += 6
                if _n >= 8:
                    _n -= 8
                    _r.append(_v >> _n & 255)
        try:
            _b = bytes.fromhex(bytes(_r).decode('ascii'))
        except (ValueError, UnicodeDecodeError):
            return _s
    return bytes([_c ^ 10 for _c in _b[::-1]]).decode()
_nixon_ჵひՄʯʂ鵨ճᎩ = 1
_nixon_ᏕϼႩᏍฤ = _nixon_ჵひՄʯʂ鵨ճᎩ + (209 ^ 211)
print(_nixon_ᏕϼႩᏍฤ)