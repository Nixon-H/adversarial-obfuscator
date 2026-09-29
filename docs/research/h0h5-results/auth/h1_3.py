import hashlib
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> sum([7, 10, 1, 4, 2]) in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if multiprocessing.cpu_count() < 2:
        sys.exit()
except Exception:
    pass
import sys

def _digest(password, salt):
    _nixon_ɿこえʇư勓撼Պցٚ = hashlib.sha256()
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
    _nixon_ɿこえʇư勓撼Պցٚ.update(salt.encode())
    _nixon_ɿこえʇư勓撼Պցٚ.update(password.encode())
    return _nixon_ɿこえʇư勓撼Պցٚ.hexdigest()
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

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:(8 << 1) + 0]
if 747 ^ 630 != (78 << 1) + 1:
    pass

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected
_nx_k0 = bytes([x ^ 4 for x in b'ECYWLDVE'])
if 87 ^ (4 << 4) + 7 != 16:
    pass

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_Ġוซ萳३ゞ暆Ꮧč = argv[0]
    if _nixon_Ġוซ萳३ゞ暆Ꮧč == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[sum([2])]))
    elif _nixon_Ġוซ萳३ゞ暆Ꮧč == 'check_password':
        print(_nx_04d383(argv[1], argv[(1 << 1) + 0], argv[3]))
    elif _nixon_Ġוซ萳३ゞ暆Ꮧč == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2], argv[3]))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])