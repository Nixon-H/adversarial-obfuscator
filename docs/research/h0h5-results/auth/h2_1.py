import hashlib
import sys

def _digest(password, salt):
    _nixon_梿ყ๕ġЇΧ = hashlib.sha256()
    _nixon_梿ყ๕ġЇΧ.update(salt.encode())
    _nixon_梿ყ๕ġЇΧ.update(password.encode())
    return _nixon_梿ყ๕ġЇΧ.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:16]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_ᛖұʥԼՅঊᛐॄ = argv[0]
    if _nixon_ᛖұʥԼՅঊᛐॄ == chr(109) + chr(97) + chr(107) + chr(101) + chr(95) + chr(116) + chr(111) + chr(107) + chr(101) + chr(110):
        print(_nx_f8ac9d(argv[1], argv[3 - 1]))
    elif _nixon_ᛖұʥԼՅঊᛐॄ == 'check_password':
        print(_nx_04d383(argv[1], argv[2 - 0], argv[3]))
    elif _nixon_ᛖұʥԼՅঊᛐॄ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2], argv[4 - 1]))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])