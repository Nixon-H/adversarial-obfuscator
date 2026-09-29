import sys

def _nixon_ᏮᛧՐتλჴট(store, key, value):
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
    _nixon_ŘιμʣΣびউ = dict(a)
    for _nixon_ᎡӒՀʫĬĮķ҇է in b:
        _nixon_ŘιμʣΣびউ[_nixon_ᎡӒՀʫĬĮķ҇է] = b[_nixon_ᎡӒՀʫĬĮķ҇է]
    return _nixon_ŘιμʣΣびউ

def _demo(argv):
    _nixon_ჍゑץǴᛗ = argv[0]
    if _nixon_ჍゑץǴᛗ == chr(115) + chr(116) + chr(111) + chr(114) + chr(101) + chr(95) + chr(103) + chr(101) + chr(116):
        print(_nx_e1c3b9({'a': 1}, argv[1], argv[2]))
    elif _nixon_ჍゑץǴᛗ == 'store_keys':
        print(','.join(_nx_ffd109({'b': 1, chr(97): 0 + 2})))
    elif _nixon_ჍゑץǴᛗ == 'store_merge':
        print(sorted(_nx_eeb99d({'a': 1}, {'b': 2}).items()))
    else:
        print('unknown op')
if __name__ == chr(95) + chr(95) + chr(109) + chr(97) + chr(105) + chr(110) + chr(95) + chr(95):
    _demo(sys.argv[1:])