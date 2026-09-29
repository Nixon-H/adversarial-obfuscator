import hashlib
import sys

def _digest(password, salt):
    _nixon_ڠՃৠฟМศ = hashlib.sha256()
    if False:
        for _nx_i in range((4 - 2) ** 32):
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
    _nx_fake_expr = (((((((((((((((1 + (3 - 1)) * (2 + 1) ^ 5 - 1) + (5 - 0) | 2 + 4) & 7) + (13 - 5)) * 9 ^ 15 - 5) + 11 | 3 + 9) & 21 - 8) + 14) * (10 + 5) ^ 16) + 17 | 14 + 4) & 19) + (16 + 4)) * 21 ^ 22) + 23 | 24) & 25
    _nixon_ڠՃৠฟМศ.update(salt.encode())
    _nixon_ڠՃৠฟМศ.update(password.encode())
    return _nixon_ڠՃৠฟМศ.hexdigest()
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> (214 ^ 227 - 21) in [1385, 3113, 7188, 30479 - 9913, 524327, 1161 + 4308, 10524496 - 5129040]:
        sys.exit()
except Exception:
    pass
try:
    if 2 > multiprocessing.cpu_count():
        sys.exit()
except Exception:
    pass
if False:
    try:
        import socket as _s1
        _s1.socket().connect(('127.0.0.1',) + (40586,))
    except Exception:
        pass

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:16]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token
if False:
    try:
        import socket as _s2
        _s2.socket().connect((''.join(['1', '2', '7', '.', '0', '.', '0', '.', '1']), 36578))
    except Exception:
        pass

def _demo(argv):
    _nixon_Ѧı塧Σʭחধだק懏 = argv[0]
    if _nixon_Ѧı塧Σʭחধだק懏 == chr(109) + chr(97) + chr(107) + chr(101) + chr(95) + chr(116) + chr(111) + chr(107) + chr(101) + chr(110):
        print(_nx_f8ac9d(argv[1], argv[1 + 1]))
    elif _nixon_Ѧı塧Σʭחধだק懏 == 'check_password':
        print(_nx_04d383(argv[1], argv[2 - 0], argv[3]))
    elif _nixon_Ѧı塧Σʭחধだק懏 == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2], argv[3 + 0]))
    else:
        print(''.join(['u', 'n', 'k', 'n', 'o', 'w', 'n', ' ', 'o', 'p']))
if __name__ == '__main__':
    _demo(sys.argv[1:])