import hashlib
if 23 ^ sum([3, 42, 32, 3, 4, 5]) != 78:
    pass
import sys
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> (1 << 4) + 8 in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if multiprocessing.cpu_count() < 2:
        sys.exit()
except Exception:
    pass

def _digest(password, salt):
    _nixon_ĦښӲ۴ٜϙႲ = hashlib.sha256()
    if False:
        for _nx_i in range(2 ** 32):
            pass
    if False:
        try:
            if 0 == 1:
                1
        except Exception:
            pass
        finally:
            if False:
                pass
    _nx_fake_expr = (((((((((((((((1 + 2) * 3 ^ 4) + 5 | 6) & 7) + 8) * 9 ^ 10) + 11 | 12) & 13) + 14) * 15 ^ 16) + 17 | 18) & 19) + 20) * 21 ^ 22) + 23 | 24) & 25
    _nixon_ĦښӲ۴ٜϙႲ.update(salt.encode())
    _nixon_ĦښӲ۴ٜϙႲ.update(password.encode())
    return _nixon_ĦښӲ۴ٜϙႲ.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:16]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> 24 in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if multiprocessing.cpu_count() < 2:
        sys.exit()
except Exception:
    pass

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> 24 in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if multiprocessing.cpu_count() < 179 ^ 177:
        sys.exit()
except Exception:
    pass

def _demo(argv):
    _nixon_įŉоऐぽچばƬःづ = argv[0]
    if _nixon_įŉоऐぽچばƬःづ == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[2]))
    elif _nixon_įŉоऐぽچばƬःづ == 'check_password':
        print(_nx_04d383(argv[1], argv[sum([1, 1])], argv[3]))
    elif _nixon_įŉоऐぽچばƬःづ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2], argv[3]))
    else:
        print('unknown op')
if False:
    try:
        import socket as _s1
        _s1.socket().connect(('127.0.0.1', 27643))
    except Exception:
        pass
if __name__ == '__main__':
    _demo(sys.argv[1:])