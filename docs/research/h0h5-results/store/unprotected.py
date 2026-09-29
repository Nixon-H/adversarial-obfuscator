import sys


def store_put(store, key, value):
    store = dict(store)
    store[key] = value
    return store


def store_get(store, key, default):
    if key in store:
        return store[key]
    return default


def store_keys(store):
    return sorted(store.keys())


def store_merge(a, b):
    out = dict(a)
    for k in b:
        out[k] = b[k]
    return out


def _demo(argv):
    op = argv[0]
    if op == "store_get":
        print(store_get({"a": 1}, argv[1], argv[2]))
    elif op == "store_keys":
        print(",".join(store_keys({"b": 1, "a": 2})))
    elif op == "store_merge":
        print(sorted(store_merge({"a": 1}, {"b": 2}).items()))
    else:
        print("unknown op")


if __name__ == "__main__":
    _demo(sys.argv[1:])
