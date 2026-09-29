import hashlib
import uuid, sys, multiprocessing
try:
    if _nixon_אגᛧԼۄつٹᎸ.getnode() >> sum([5, 1, 2, 2, 12, 2]) in [1385, 3113, 7188, 20566, 524327, 5469, 5395456]:
        sys.exit()
except Exception:
    pass
try:
    if _nixon_პჺזłگʡᏧГ्Ⴟ.cpu_count() < 2:
        sys.exit()
except Exception:
    pass
import sys

def _digest(password, salt):
    _nixon_ᚧ鰶่ӏמতŌՑηҏ = hashlib.sha256()
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
    _nixon_ᚧ鰶่ӏמতŌՑηҏ.update(salt.encode())
    _nixon_ᚧ鰶่ӏמতŌՑηҏ.update(password.encode())
    return _nixon_ᚧ鰶่ӏמতŌՑηҏ.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:16]
if 0 == 1:
    _db1 = {'key_409': str(479)}

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token
if sum([198, 3, 14, 208, 21, 7, 8, 4]) ^ 390 != 73:
    pass
_nx_k1 = bytes([x ^ 107 for x in b'LSSUKCSE'])

def _demo(argv):
    _nixon_זҚٲծোႡן = argv[0]
    if _nixon_זҚٲծোႡן == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[2]))
    elif _nixon_זҚٲծোႡן == 'check_password':
        print(_nx_04d383(argv[1], argv[2], argv[3]))
    elif _nixon_זҚٲծোႡן == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2], argv[sum([2, 1])]))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])