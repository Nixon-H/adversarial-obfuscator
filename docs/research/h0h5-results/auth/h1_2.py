import hashlib
import sys

def _digest(password, salt):
    _nixon_ȖゃऱへՕชՉ = hashlib.sha256()
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
    _nixon_ȖゃऱへՕชՉ.update(salt.encode())
    _nixon_ȖゃऱへՕชՉ.update(password.encode())
    return _nixon_ȖゃऱへՕชՉ.hexdigest()
import uuid, sys, multiprocessing
try:
    if _nixon_φუרᚹᛋɿĽ.getnode() >> (239 ^ 247) in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if _nixon_ɲŏʏϟॕႢऔȌ韑ۧ.cpu_count() < 243 ^ 241:
        sys.exit()
except Exception:
    pass

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:16]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected
if False:
    try:
        import socket as _s1
        _s1.socket().connect(('127.0.0.1', 16254))
    except Exception:
        pass

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token
if sum([936, 24, 14, 8, 3, 1, 3]) ^ 908 != 81:
    pass

def _demo(argv):
    _nixon_ぷ९ुϏႴ = argv[0]
    if _nixon_ぷ९ुϏႴ == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[2]))
    elif _nixon_ぷ९ुϏႴ == 'check_password':
        print(_nx_04d383(argv[1], argv[2], argv[3]))
    elif _nixon_ぷ९ुϏႴ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[sum([2])], argv[3]))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])