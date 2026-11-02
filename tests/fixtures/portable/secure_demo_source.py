"""Secure demo payload: exercises functions, classes, strings, loops, exceptions."""
import hashlib
import json
import zlib


class Vault:
    def __init__(self, name):
        self.name = name
        self.items = {}

    def put(self, key, value):
        self.items[key] = value
        return self

    def digest(self):
        blob = json.dumps(self.items, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:16]


def pack(text):
    return zlib.compress(text.encode()).hex()[:24]


def score(values):
    return sum(v * (i + 1) for i, v in enumerate(values))


def main():
    vault = Vault("demo").put("alpha", 1).put("beta", 2)
    print("vault:", vault.name, "digest:", vault.digest())
    print("packed:", pack("adversarial-obfuscator"))
    print("score:", score([3, 1, 4, 1, 5, 9, 2, 6]))
    total = 0
    for i in range(5):
        try:
            total += 10 // (2 - i) if i != 2 else (_ for _ in ()).throw(ZeroDivisionError())
        except ZeroDivisionError:
            total += 1
    print("total:", total)
    print("OK")


if __name__ == "__main__":
    main()
