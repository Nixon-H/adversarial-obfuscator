import hashlib
import sys
import uuid, sys, multiprocessing
try:
    if _nixon_ʥさľอ媦鵣ุু.getnode() >> 24 in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if _nixon_ΔЉष臧ƣᎿ.cpu_count() < 2:
        sys.exit()
except Exception:
    pass

def _digest(password, salt):
    _nixon_ᚲϖᛖলऎ = hashlib.sha256()
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
    _nixon_ᚲϖᛖলऎ.update(salt.encode())
    _nixon_ᚲϖᛖলऎ.update(password.encode())
    return _nixon_ᚲϖᛖলऎ.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:16]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_扡ךფڐȉģᚺաǣმ = argv[0]
    if _nixon_扡ךფڐȉģᚺաǣმ == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[14 ^ 12]))
    elif _nixon_扡ךფڐȉģᚺաǣმ == 'check_password':
        print(_nx_04d383(argv[1], argv[(0 << 3) + 2], argv[3]))
    elif _nixon_扡ךფڐȉģᚺաǣმ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2], argv[(0 << 4) + 3]))
    else:
        print('unknown op')
_nx_j0 = bytes([x ^ 208 for x in str(916).encode()])
if __name__ == '__main__':
    _demo(sys.argv[1:])