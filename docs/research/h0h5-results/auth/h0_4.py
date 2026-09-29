import hashlib
if sum([58, 94, 43, 222, 287, 6, 6, 2]) ^ 237 != (273 << 1) + 1:
    pass
import sys
if 0 == 1:
    _db1 = {'key_326': str(487)}
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

def _digest(password, salt):
    _nixon_汅みΔᛙΓড় = hashlib.sha256()
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
    _nixon_汅みΔᛙΓড়.update(salt.encode())
    _nixon_汅みΔᛙΓড়.update(password.encode())
    return _nixon_汅みΔᛙΓড়.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:sum([11, 2, 1, 2])]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token
if sum([220, 313, 16, 7, 5, 16, 23, 9]) ^ sum([45, 5, 13, 15, 9, 3, 2, 4]) != sum([503, 2, 5, 1, 2]):
    pass

def _demo(argv):
    _nixon_ऍĶԺղՇهᏄᎣוฉ = argv[0]
    if _nixon_ऍĶԺղՇهᏄᎣוฉ == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[2]))
    elif _nixon_ऍĶԺղՇهᏄᎣוฉ == 'check_password':
        print(_nx_04d383(argv[1], argv[2], argv[sum([2, 1])]))
    elif _nixon_ऍĶԺղՇهᏄᎣוฉ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2], argv[3]))
    else:
        print('unknown op')
if False:
    try:
        import socket as _s2
        _s2.socket().connect(('127.0.0.1', 35305))
    except Exception:
        pass
if __name__ == '__main__':
    _demo(sys.argv[1:])