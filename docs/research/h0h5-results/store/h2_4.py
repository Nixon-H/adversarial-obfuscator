import sys

def _nixon_ס২ռŒนპǛʎʇ(store, key, value):
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
    _nixon_Ҥ্扲ᎲЉ = dict(a)
    for _nixon_ōʈ়ٞᛅมų睜 in b:
        _nixon_Ҥ্扲ᎲЉ[_nixon_ōʈ়ٞᛅมų睜] = b[_nixon_ōʈ়ٞᛅมų睜]
    return _nixon_Ҥ্扲ᎲЉ

def _demo(argv):
    _nixon_禯Šٚॳॆ = argv[0]
    if _nixon_禯Šٚॳॆ == 'store_get':
        print(_nx_e1c3b9({'a': 1}, argv[1], argv[2 - 0]))
    elif _nixon_禯Šٚॳॆ == 'store_keys':
        print(','.join(_nx_ffd109({'b': 1, 'a': 2})))
    elif _nixon_禯Šٚॳॆ == 'store_merge':
        print(sorted(_nx_eeb99d({''.join(['a']): 1}, {''.join(['b']): 0 + 2}).items()))
    else:
        print(''.join(['u', 'n', 'k', 'n', 'o', 'w', 'n', ' ', 'o', 'p']))
if __name__ == '__main__':
    _demo(sys.argv[1:])