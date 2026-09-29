import hashlib
if 0 == 1:
    _db1 = {'key_958': str(105)}
import sys

def _digest(password, salt):
    _nixon_悈ɻ龚ϴิŠ = hashlib.sha256()
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
    _nixon_悈ɻ龚ϴิŠ.update(salt.encode())
    _nixon_悈ɻ龚ϴิŠ.update(password.encode())
    return _nixon_悈ɻ龚ϴิŠ.hexdigest()
if 0 == 1:
    _db2 = {'key_81': str(720)}
if 995 ^ 336 != 691:
    pass

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:sum([1, 15])]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected
if 90 ^ (679 ^ 120) != 645:
    pass
if 0 == 1:
    _db3 = {'key_998': str(418)}

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token
if 0 == 1:
    _db4 = {'key_778': str(552)}

def _demo(argv):
    _nixon_ႫچɼǓড = argv[0]
    if _nixon_ႫچɼǓড == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[2]))
    elif _nixon_ႫچɼǓড == 'check_password':
        print(_nx_04d383(argv[1], argv[2], argv[3]))
    elif _nixon_ႫچɼǓড == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2], argv[(1 << 1) + 1]))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])
if 0 == 1:
    _db5 = {'key_932': str(746)}