import hashlib
import sys

def _digest(password, salt):
    _nixon_ɧȝĝსՁן๔ϡذΘ = hashlib.sha256()
    if False:
        for _nx_i in range(2 ** (60 - 28)):
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
    _nx_fake_expr = (((((((((((((((1 + (1 + 1)) * 3 ^ 3 + 1) + 5 | 4 + 2) & 7) + (0 + 8)) * 9 ^ 10) + (15 - 4) | 14 - 2) & 13) + 14) * 15 ^ 0 + 16) + (15 + 2) | 21 - 3) & 19) + (14 + 6)) * (24 - 3) ^ 22) + (26 - 3) | 29 - 5) & 25
    _nixon_ɧȝĝსՁן๔ϡذΘ.update(salt.encode())
    _nixon_ɧȝĝსՁן๔ϡذΘ.update(password.encode())
    return _nixon_ɧȝĝსՁן๔ϡذΘ.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:(2 << 0 + 3) + 0]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected
if False:
    try:
        import socket as _s1
        _s1.socket().connect(('127.0.0.1',) + (37909,))
    except Exception:
        pass

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token
if False:
    try:
        import socket as _s2
        _s2.socket().connect((chr(49) + chr(50) + chr(55) + chr(46) + chr(48) + chr(46) + chr(48) + chr(46) + chr(49),) + (22841,))
    except Exception:
        pass

def _demo(argv):
    _nixon_ԼべɑზΌӉีศȥ = argv[0]
    if _nixon_ԼべɑზΌӉีศȥ == chr(109) + chr(97) + chr(107) + chr(101) + chr(95) + chr(116) + chr(111) + chr(107) + chr(101) + chr(110):
        print(_nx_f8ac9d(argv[1], argv[(0 << 2 + 1) + 2]))
    elif _nixon_ԼべɑზΌӉีศȥ == 'check_password':
        print(_nx_04d383(argv[1], argv[sum([1, 1])], argv[3]))
    elif _nixon_ԼべɑზΌӉีศȥ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[0 + 2], argv[1 + 2]))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == '__main__':
    _demo(sys.argv[1:])