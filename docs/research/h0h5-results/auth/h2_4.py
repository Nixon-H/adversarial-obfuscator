import hashlib
import sys

def _digest(password, salt):
    _nixon_םჩᛞʚɿ = hashlib.sha256()
    _nixon_םჩᛞʚɿ.update(salt.encode())
    _nixon_םჩᛞʚɿ.update(password.encode())
    return _nixon_םჩᛞʚɿ.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:16]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_ΣŔつᎯג = argv[0]
    if _nixon_ΣŔつᎯג == ''.join(['m', 'a', 'k', 'e', '_', 't', 'o', 'k', 'e', 'n']):
        print(_nx_f8ac9d(argv[1], argv[3 - 1]))
    elif _nixon_ΣŔつᎯג == 'check_password':
        print(_nx_04d383(argv[1], argv[1 + 1], argv[3 - 0]))
    elif _nixon_ΣŔつᎯג == 'verify_token':
        print(_nx_e820b6(argv[1], argv[1 + 1], argv[3 + 0]))
    else:
        print(''.join(['u', 'n', 'k', 'n', 'o', 'w', 'n', ' ', 'o', 'p']))
if __name__ == '__main__':
    _demo(sys.argv[1:])