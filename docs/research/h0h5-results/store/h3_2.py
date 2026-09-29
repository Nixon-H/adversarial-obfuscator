import sys

def _nixon_ჿᏬкѪҫƼ(store, key, value):
    store = dict(store)
    store[key] = value
    return store

def _nx_e1c3b9(store, key, default):
    if key in store:
        return store[key]
    return default

def _nx_ffd109(store):
    return sorted(store.keys())

def _nx_eeb99d(a, b):
    _nixon_αঋڶंخԻɦ = dict(a)
    for _nixon_ĸゕじłञきƽӔѳă in b:
        _nixon_αঋڶंخԻɦ[_nixon_ĸゕじłञきƽӔѳă] = b[_nixon_ĸゕじłञきƽӔѳă]
    return _nixon_αঋڶंخԻɦ

def _demo(argv):
    _nixon_ו灬ᎬᎻᛒ闐 = argv[0]
    if _nixon_ו灬ᎬᎻᛒ闐 == 'store_get':
        print(_nx_e1c3b9({'a': 1}, argv[1], argv[2]))
    elif _nixon_ו灬ᎬᎻᛒ闐 == 'store_keys':
        print(','.join(_nx_ffd109({'b': 1, 'a': 2})))
    elif _nixon_ו灬ᎬᎻᛒ闐 == 'store_merge':
        print(sorted(_nx_eeb99d({'a': 1}, {'b': 2}).items()))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])