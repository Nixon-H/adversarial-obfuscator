import hashlib
import sys

def _digest(password, salt):
    _nixon_ϡūҶΎȰת蟈 = hashlib.sha256()
    _nixon_ϡūҶΎȰת蟈.update(salt.encode())
    _nixon_ϡūҶΎȰת蟈.update(password.encode())
    return _nixon_ϡūҶΎȰת蟈.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:16]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_ᏄᚺʚϖظωŜᚰȋ = argv[0]
    if _nixon_ᏄᚺʚϖظωŜᚰȋ == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[2]))
    elif _nixon_ᏄᚺʚϖظωŜᚰȋ == 'check_password':
        print(_nx_04d383(argv[1], argv[2], argv[3]))
    elif _nixon_ᏄᚺʚϖظωŜᚰȋ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2], argv[3]))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])