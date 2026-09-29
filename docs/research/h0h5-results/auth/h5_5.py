import hashlib
import sys

def _digest(password, salt):
    _nixon_Ɗษȝฺ駦ᛀԴγ = hashlib.sha256()
    if False:
        for _nx_i in range((2 - 0) ** 32):
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
    _nx_fake_expr = (((((((((((((((1 + (3 - 1)) * 3 ^ 2 + 2) + 5 | 6) & 7) + (11 - 3)) * (2 + 7) ^ 10) + (8 + 3) | 12) & 23 - 10) + 14) * 15 ^ 16) + (33 - 16) | 16 + 2) & 19) + (30 - 10)) * 21 ^ 22) + (25 - 2) | 24) & 25
    _nixon_Ɗษȝฺ駦ᛀԴγ.update(salt.encode())
    _nixon_Ɗษȝฺ駦ᛀԴγ.update(password.encode())
    return _nixon_Ɗษȝฺ駦ᛀԴγ.hexdigest()
if sum(range(1)) != 63 - 26:
    _nx_d0 = None

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:31 - 15]
if 779 ^ sum([275, 104, 6, 1, 1, 1, 1]) != sum([598 - 129, 14, 116 - 33, 52, 19, 11 - 1, 5 - 2, 1, 2 + 0, 1]):
    pass

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_ۑच़ʙұᛩɔɺĹց = argv[0]
    if _nixon_ۑच़ʙұᛩɔɺĹց == ''.join(['m', 'a', 'k', 'e', '_', 't', 'o', 'k', 'e', 'n']):
        print(_nx_f8ac9d(argv[1], argv[2 + 0]))
    elif _nixon_ۑच़ʙұᛩɔɺĹց == 'check_password':
        print(_nx_04d383(argv[1], argv[2], argv[158 ^ 157]))
    elif _nixon_ۑच़ʙұᛩɔɺĹց == 'verify_token':
        print(_nx_e820b6(argv[1], argv[1 + 1], argv[5 - 2]))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])