import hashlib
import sys

def _digest(password, salt):
    _nixon_ǃᛦᚦҒʞ蝐Ꮒ = hashlib.sha256()
    _nixon_ǃᛦᚦҒʞ蝐Ꮒ.update(salt.encode())
    _nixon_ǃᛦᚦҒʞ蝐Ꮒ.update(password.encode())
    return _nixon_ǃᛦᚦҒʞ蝐Ꮒ.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:16]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_ৱჰৢႮıᛏพכՃむ = argv[0]
    if _nixon_ৱჰৢႮıᛏพכՃむ == ''.join(['m', 'a', 'k', 'e', '_', 't', 'o', 'k', 'e', 'n']):
        print(_nx_f8ac9d(argv[1], argv[4 - 2]))
    elif _nixon_ৱჰৢႮıᛏพכՃむ == 'check_password':
        print(_nx_04d383(argv[1], argv[2], argv[3 - 0]))
    elif _nixon_ৱჰৢႮıᛏพכՃむ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[1 + 1], argv[5 - 2]))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])