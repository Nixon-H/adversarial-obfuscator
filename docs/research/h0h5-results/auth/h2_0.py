import hashlib
import sys

def _digest(password, salt):
    _nixon_ϗ๕ըᛈӰȽকւჯअ = hashlib.sha256()
    _nixon_ϗ๕ըᛈӰȽকւჯअ.update(salt.encode())
    _nixon_ϗ๕ըᛈӰȽকւჯअ.update(password.encode())
    return _nixon_ϗ๕ըᛈӰȽকւჯअ.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:4 + 12]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_ᏲჼჇʫぞʚ淗ЌСƴ = argv[0]
    if _nixon_ᏲჼჇʫぞʚ淗ЌСƴ == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[2]))
    elif _nixon_ᏲჼჇʫぞʚ淗ЌСƴ == 'check_password':
        print(_nx_04d383(argv[1], argv[2 - 0], argv[3]))
    elif _nixon_ᏲჼჇʫぞʚ淗ЌСƴ == ''.join(['v', 'e', 'r', 'i', 'f', 'y', '_', 't', 'o', 'k', 'e', 'n']):
        print(_nx_e820b6(argv[1], argv[2], argv[3]))
    else:
        print('unknown op')
if __name__ == chr(95) + chr(95) + chr(109) + chr(97) + chr(105) + chr(110) + chr(95) + chr(95):
    _demo(sys.argv[1:])