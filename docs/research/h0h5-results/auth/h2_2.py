import hashlib
import sys

def _digest(password, salt):
    _nixon_ļרٻĔנ = hashlib.sha256()
    _nixon_ļרٻĔנ.update(salt.encode())
    _nixon_ļרٻĔנ.update(password.encode())
    return _nixon_ļרٻĔנ.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:16]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_খ舚ĂŝŃפɶ = argv[0]
    if _nixon_খ舚ĂŝŃפɶ == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[2 + 0]))
    elif _nixon_খ舚ĂŝŃפɶ == 'check_password':
        print(_nx_04d383(argv[1], argv[2], argv[0 + 3]))
    elif _nixon_খ舚ĂŝŃפɶ == chr(118) + chr(101) + chr(114) + chr(105) + chr(102) + chr(121) + chr(95) + chr(116) + chr(111) + chr(107) + chr(101) + chr(110):
        print(_nx_e820b6(argv[1], argv[2 - 0], argv[3]))
    else:
        print('unknown op')
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])