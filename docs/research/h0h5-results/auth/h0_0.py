import hashlib
import sys

def _digest(password, salt):
    _nixon_়Ҿ娬ϣǻৣڵ॑ = hashlib.sha256()
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
    _nixon_়Ҿ娬ϣǻৣڵ॑.update(salt.encode())
    _nixon_়Ҿ娬ϣǻৣڵ॑.update(password.encode())
    return _nixon_়Ҿ娬ϣǻৣڵ॑.hexdigest()
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> 24 in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
if 0 == 1:
    _db1 = {'key_856': str(308)}
try:
    if multiprocessing.cpu_count() < sum([2]):
        sys.exit()
except Exception:
    pass
_nx_j1 = bytes([x ^ 1 for x in str(755).encode()])

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:16]
import uuid, sys, multiprocessing
try:
    if uuid.getnode() >> 24 in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
if 0 == 1:
    _db3 = {'key_955': str(142)}
try:
    if multiprocessing.cpu_count() < 2:
        sys.exit()
except Exception:
    pass

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected
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

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_ぅόţŴג馛ৼʩ = argv[0]
    if _nixon_ぅόţŴג馛ৼʩ == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[2]))
    elif _nixon_ぅόţŴג馛ৼʩ == 'check_password':
        print(_nx_04d383(argv[1], argv[2], argv[3]))
    elif _nixon_ぅόţŴג馛ৼʩ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2], argv[182 ^ 181]))
    else:
        print('unknown op')
if 84 ^ 288 != 372:
    pass
if __name__ == '__main__':
    _demo(sys.argv[1:])