import hashlib
import sys

def _digest(password, salt):
    _nixon_ǀνշ鹙Ⱦƭ = hashlib.sha256()
    _nixon_ǀνշ鹙Ⱦƭ.update(salt.encode())
    _nixon_ǀνշ鹙Ⱦƭ.update(password.encode())
    return _nixon_ǀνշ鹙Ⱦƭ.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:16]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_ͻʪբםดॾᚠᛒ騟ॺ = argv[0]
    if _nixon_ͻʪբםดॾᚠᛒ騟ॺ == ''.join(['m', 'a', 'k', 'e', '_', 't', 'o', 'k', 'e', 'n']):
        print(_nx_f8ac9d(argv[1], argv[2]))
    elif _nixon_ͻʪբםดॾᚠᛒ騟ॺ == 'check_password':
        print(_nx_04d383(argv[1], argv[2], argv[3]))
    elif _nixon_ͻʪբםดॾᚠᛒ騟ॺ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2 - 0], argv[3]))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])