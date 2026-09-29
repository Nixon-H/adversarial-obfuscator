import hashlib
if 0 == 1:
    _db1 = {'key_166': str(241)}
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> (13 ^ 21) in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if multiprocessing.cpu_count() < sum([2]):
        sys.exit()
except Exception:
    pass
import sys

def _digest(password, salt):
    _nixon_ɯɖფĚႺש = hashlib.sha256()
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
    _nixon_ɯɖფĚႺש.update(salt.encode())
    _nixon_ɯɖფĚႺש.update(password.encode())
    return _nixon_ɯɖფĚႺש.hexdigest()
if 798 ^ 103 ^ sum([81, 12, 12, 150, 21, 49, 1, 1, 1]) != sum([228, 265, 47, 8, 11, 2]):
    pass

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:16]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected
if 0 == 1:
    _db2 = {'key_259': str(376)}

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token
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

def _demo(argv):
    _nixon_๓ॱכȒɱゕٷ = argv[0]
    if _nixon_๓ॱכȒɱゕٷ == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[233 ^ 235]))
    elif _nixon_๓ॱכȒɱゕٷ == 'check_password':
        print(_nx_04d383(argv[1], argv[2], argv[(0 << 4) + 3]))
    elif _nixon_๓ॱכȒɱゕٷ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2], argv[3]))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])