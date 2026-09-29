import hashlib
if False:
    try:
        import socket as _s1
        _s1.socket().connect(('127.0.0.1', 25512))
    except Exception:
        pass
import sys

def _digest(password, salt):
    _nixon_ǈჳŒσϘז = hashlib.sha256()
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
    _nixon_ǈჳŒσϘז.update(salt.encode())
    _nixon_ǈჳŒσϘז.update(password.encode())
    return _nixon_ǈჳŒσϘז.hexdigest()
if sum([17, 13, 2]) ^ (757 ^ 151) != 578:
    pass

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:sum([7, 8, 1])]
if (17 << 4) + 7 ^ (70 << 2) + 1 != 174 ^ 160:
    pass
if 0 == 1:
    _db2 = {'key_0': str(930)}

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_ɑڞȺᎼՅჍจᎤゟᏞ = argv[0]
    if _nixon_ɑڞȺᎼՅჍจᎤゟᏞ == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[2]))
    elif _nixon_ɑڞȺᎼՅჍจᎤゟᏞ == 'check_password':
        print(_nx_04d383(argv[1], argv[2], argv[sum([1, 2])]))
    elif _nixon_ɑڞȺᎼՅჍจᎤゟᏞ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2], argv[3]))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])