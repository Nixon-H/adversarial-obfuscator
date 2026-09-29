import hashlib
import sys
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> 24 in [1279 + 106, 3113, 4567 + 2621, 18660 + 1906, 524327, 7946 - 2477, 3506515 + 1888941]:
        sys.exit()
except Exception:
    pass
try:
    if 2 > multiprocessing.cpu_count():
        sys.exit()
except Exception:
    pass

def _digest(password, salt):
    _nixon_ゑɅƤऺŨɞ = hashlib.sha256()
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
    _nx_fake_expr = (((((((((((((((1 + (4 - 2)) * (5 - 2) ^ 4) + (10 - 5) | 6) & 7) + (1 + 7)) * 9 ^ 10) + 11 | 12) & 13) + 14) * 15 ^ 16) + 17 | 18) & 19) + (24 - 4)) * (34 - 13) ^ 18 + 4) + (14 + 9) | 11 + 13) & 25
    _nixon_ゑɅƤऺŨɞ.update(salt.encode())
    _nixon_ゑɅƤऺŨɞ.update(password.encode())
    return _nixon_ゑɅƤऺŨɞ.hexdigest()
if False:
    try:
        import socket as _s1
        _s1.socket().connect(('127.0.0.1', 55837))
    except Exception:
        pass

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:90 ^ 74]
if 39 + 626 ^ (466 ^ 122) != 1621 - 804:
    pass

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected
if False:
    try:
        import socket as _s2
        _s2.socket().connect(('127.0.0.1', 24893))
    except Exception:
        pass

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_шᛩӵह蕕ɯҷᏌჇ = argv[0]
    if _nixon_шᛩӵह蕕ɯҷᏌჇ == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[1 + 1]))
    elif _nixon_шᛩӵह蕕ɯҷᏌჇ == 'check_password':
        print(_nx_04d383(argv[1], argv[1 + 1], argv[3]))
    elif _nixon_шᛩӵह蕕ɯҷᏌჇ == ''.join(['v', 'e', 'r', 'i', 'f', 'y', '_', 't', 'o', 'k', 'e', 'n']):
        print(_nx_e820b6(argv[1], argv[2], argv[3]))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])
if 0 == 1:
    _db3 = {'key_508': str(152 + 78)}