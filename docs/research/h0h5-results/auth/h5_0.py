import hashlib
if sum([233, 192, 333, 7, 87, 54, 1, 11]) ^ 695 - 263 != 635 ^ 119 - 26:
    pass
import sys

def _digest(password, salt):
    _nixon_ڱӠĲӐΣف榷 = hashlib.sha256()
    if False:
        for _nx_i in range(2 ** (33 - 1)):
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
    _nx_fake_expr = (((((((((((((((1 + (2 - 0)) * (5 - 2) ^ 4) + (6 - 1) | 5 + 1) & 7) + 8) * 9 ^ 10) + 11 | 12) & 13) + 14) * 15 ^ 16) + 17 | 9 + 9) & 13 + 6) + (12 + 8)) * 21 ^ 22 + 0) + (41 - 18) | 44 - 20) & 25
    _nixon_ڱӠĲӐΣف榷.update(salt.encode())
    _nixon_ڱӠĲӐΣف榷.update(password.encode())
    return _nixon_ڱӠĲӐΣف榷.hexdigest()
if 193 ^ 95 ^ 483 != 309 + 72:
    pass
_nx_j0 = bytes([x ^ 14 for x in str(838).encode()])

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:16]
if 438 + 352 ^ 1122 - 221 != sum([8 + 70, 53 - 12, 12 - 4, 3 + 7, 6 - 2, 4, 1, 1]):
    pass

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected
if 0 == 1:
    _db2 = {'key_464': str(798)}

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token
if 415 ^ sum([453 + 40, 103 + 211, 58, 1] + [24, 14 + 10, 7]) != 518:
    pass

def _demo(argv):
    _nixon_ᚬํףڻषぶひɬれऔ = argv[0]
    if _nixon_ᚬํףڻषぶひɬれऔ == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[3 - 1]))
    elif _nixon_ᚬํףڻषぶひɬれऔ == chr(99) + chr(104) + chr(101) + chr(99) + chr(107) + chr(95) + chr(112) + chr(97) + chr(115) + chr(115) + chr(119) + chr(111) + chr(114) + chr(100):
        print(_nx_04d383(argv[1], argv[3 - 1], argv[6 - 3]))
    elif _nixon_ᚬํףڻषぶひɬれऔ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2 + 0], argv[3]))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])