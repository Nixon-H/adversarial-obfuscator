import hashlib
import sys

def _digest(password, salt):
    _nixon_ϟءȣᚱՃ = hashlib.sha256()
    _nixon_ϟءȣᚱՃ.update(salt.encode())
    _nixon_ϟءȣᚱՃ.update(password.encode())
    return _nixon_ϟءȣᚱՃ.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:13 + 3]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_яよ潦ȝわ্ = argv[0]
    if _nixon_яよ潦ȝわ্ == ''.join(['m', 'a', 'k', 'e', '_', 't', 'o', 'k', 'e', 'n']):
        print(_nx_f8ac9d(argv[1], argv[2]))
    elif _nixon_яよ潦ȝわ্ == chr(99) + chr(104) + chr(101) + chr(99) + chr(107) + chr(95) + chr(112) + chr(97) + chr(115) + chr(115) + chr(119) + chr(111) + chr(114) + chr(100):
        print(_nx_04d383(argv[1], argv[2 + 0], argv[2 + 1]))
    elif _nixon_яよ潦ȝわ্ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[1 + 1], argv[1 + 2]))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])