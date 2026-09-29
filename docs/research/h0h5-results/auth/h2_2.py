import hashlib
import sys

def _digest(password, salt):
    _nixon_ɵჲᏯᚺіۋ椮 = hashlib.sha256()
    _nixon_ɵჲᏯᚺіۋ椮.update(salt.encode())
    _nixon_ɵჲᏯᚺіۋ椮.update(password.encode())
    return _nixon_ɵჲᏯᚺіۋ椮.hexdigest()

def _nx_f8ac9d(username, secret):
    return _digest(username, secret)[:16]

def _nx_04d383(password, salt, expected):
    return _digest(password, salt) == expected

def _nx_e820b6(username, secret, token):
    return _nx_f8ac9d(username, secret) == token

def _demo(argv):
    _nixon_ぅڸᎡৢᚮ擀蚄ᚵֆ = argv[0]
    if _nixon_ぅڸᎡৢᚮ擀蚄ᚵֆ == 'make_token':
        print(_nx_f8ac9d(argv[1], argv[3 - 1]))
    elif _nixon_ぅڸᎡৢᚮ擀蚄ᚵֆ == chr(99) + chr(104) + chr(101) + chr(99) + chr(107) + chr(95) + chr(112) + chr(97) + chr(115) + chr(115) + chr(119) + chr(111) + chr(114) + chr(100):
        print(_nx_04d383(argv[1], argv[2 + 0], argv[3]))
    elif _nixon_ぅڸᎡৢᚮ擀蚄ᚵֆ == 'verify_token':
        print(_nx_e820b6(argv[1], argv[2], argv[0 + 3]))
    else:
        print('unknown op')
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])