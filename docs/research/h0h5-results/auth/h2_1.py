import hashlib
import sys

def _digest(password, salt):
    _nixon_ᛘ鲛ɴƏᚸٖ = hashlib.sha256()
    _nixon_ᛘ鲛ɴƏᚸٖ.update(salt.encode())
    _nixon_ᛘ鲛ɴƏᚸٖ.update(password.encode())
    return _nixon_ᛘ鲛ɴƏᚸٖ.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:3 + 13]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_ٹҘҊغđႩՙᚮը = argv[0]
    if _nixon_ٹҘҊغđႩՙᚮը == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[0 + 2]))
    elif _nixon_ٹҘҊغđႩՙᚮը == chr(99) + chr(104) + chr(101) + chr(99) + chr(107) + chr(95) + chr(112) + chr(97) + chr(115) + chr(115) + chr(119) + chr(111) + chr(114) + chr(100):
        print(_nx_04d383(argv[1], argv[2], argv[3]))
    elif _nixon_ٹҘҊغđႩՙᚮը == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2], argv[1 + 2]))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == '__main__':
    _demo(sys.argv[1:])