import hashlib
import sys


def _digest(password, salt):
    h = hashlib.sha256()
    h.update(salt.encode())
    h.update(password.encode())
    return h.hexdigest()


def make_token(username, secret):
    return _digest(username, secret)[:16]


def check_password(password, salt, expected):
    return _digest(password, salt) == expected


def verify_token(username, secret, token):
    return make_token(username, secret) == token


def _demo(argv):
    op = argv[0]
    if op == "make_token":
        print(make_token(argv[1], argv[2]))
    elif op == "check_password":
        print(check_password(argv[1], argv[2], argv[3]))
    elif op == "verify_token":
        print(verify_token(argv[1], argv[2], argv[3]))
    else:
        print("unknown op")


if __name__ == "__main__":
    _demo(sys.argv[1:])
