import hashlib
import sys

def _digest(password, salt):
    _nixon_Փᛁ娣Ɗずᛘთॵᛕɾ = hashlib.sha256()
    _nixon_Փᛁ娣Ɗずᛘთॵᛕɾ.update(salt.encode())
    _nixon_Փᛁ娣Ɗずᛘთॵᛕɾ.update(password.encode())
    return _nixon_Փᛁ娣Ɗずᛘთॵᛕɾ.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:11 + 5]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_ǼɏɥώЗŝϢᎮϱঌ = argv[0]
    if _nixon_ǼɏɥώЗŝϢᎮϱঌ == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[2]))
    elif _nixon_ǼɏɥώЗŝϢᎮϱঌ == 'check_password':
        print(_nx_04d383(argv[1], argv[2], argv[0 + 3]))
    elif _nixon_ǼɏɥώЗŝϢᎮϱঌ == chr(118) + chr(101) + chr(114) + chr(105) + chr(102) + chr(121) + chr(95) + chr(116) + chr(111) + chr(107) + chr(101) + chr(110):
        print(_nx_e820b6(argv[1], argv[2], argv[3]))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])