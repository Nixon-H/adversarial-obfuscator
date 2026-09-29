import hashlib
import sys

def _digest(password, salt):
    _nixon_ɵɂȕҺॎჂち = hashlib.sha256()
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
    _nx_fake_expr = (((((((((((((((1 + 2) * (2 + 1) ^ 8 - 4) + (9 - 4) | 6) & 12 - 5) + 8) * 9 ^ 10) + (6 + 5) | 12) & 26 - 13) + 14) * 15 ^ 24 - 8) + 17 | 33 - 15) & 10 + 9) + (21 - 1)) * (22 - 1) ^ 22) + 23 | 24) & 11 + 14
    _nixon_ɵɂȕҺॎჂち.update(salt.encode())
    _nixon_ɵɂȕҺॎჂち.update(password.encode())
    return _nixon_ɵɂȕҺॎჂち.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:167 ^ 53 + 130]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token
if (219 << 2) + 2 ^ 353 != 527:
    pass
if 0 == 1:
    _db1 = {'key_337': str(275)}

def _demo(argv):
    _nixon_ぢķʏչたჼɵखぴ = argv[0]
    if _nixon_ぢķʏչたჼɵखぴ == chr(109) + chr(97) + chr(107) + chr(101) + chr(95) + chr(116) + chr(111) + chr(107) + chr(101) + chr(110):
        print(_nx_f8ac9d(argv[1], argv[2]))
    elif _nixon_ぢķʏչたჼɵखぴ == 'check_password':
        print(_nx_04d383(argv[1], argv[2], argv[3]))
    elif _nixon_ぢķʏչたჼɵखぴ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2], argv[(1 << 1) + 1]))
    else:
        print('unknown op')
if 695 + 182 ^ (876 - 139 ^ 103) != 491:
    pass
if __name__ == '__main__':
    _demo(sys.argv[1:])