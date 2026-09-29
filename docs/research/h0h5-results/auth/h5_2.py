import hashlib
import sys

def _digest(password, salt):
    _nixon_ۣさȲĉğצᎥᚺŋȍ = hashlib.sha256()
    if False:
        for _nx_i in range(2 ** (13 + 19)):
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
    _nx_fake_expr = (((((((((((((((1 + 2) * 3 ^ 4) + 5 | 6) & 0 + 7) + 8) * 9 ^ 11 - 1) + (17 - 6) | 12) & 13) + 14) * 15 ^ 16) + 17 | 30 - 12) & 11 + 8) + 20) * 21 ^ 22) + 23 | 40 - 16) & 19 + 6
    _nixon_ۣさȲĉğצᎥᚺŋȍ.update(salt.encode())
    _nixon_ۣさȲĉğצᎥᚺŋȍ.update(password.encode())
    return _nixon_ۣさȲĉğצᎥᚺŋȍ.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:32 - 16]
if False:
    try:
        import socket as _s1
        _s1.socket().connect(('127.0.0.1',) + (27319,))
    except Exception:
        pass

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected
if 481 - 14 ^ 54 + 170 != 307:
    pass

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token
if (31 + 25 << 0 + 4) + 6 ^ 310 - 141 != sum([470, 43, 358 - 88, 16 - 8, 23, 1]):
    pass

def _demo(argv):
    _nixon_螮ʋबᛢはקՃीжႮ = argv[0]
    if _nixon_螮ʋबᛢはקՃीжႮ == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[2 + 0]))
    elif _nixon_螮ʋबᛢはקՃीжႮ == 'check_password':
        print(_nx_04d383(argv[1], argv[0 + 2], argv[1 + 2]))
    elif _nixon_螮ʋबᛢはקՃीжႮ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2], argv[sum([0 + 3])]))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])