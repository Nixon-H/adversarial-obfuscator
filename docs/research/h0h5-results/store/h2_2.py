import sys

def _nixon_Ůᛎিब煣৾(store, key, value):
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
    _nixon_ČٵתţՄळכՐ = dict(a)
    for _nixon_ϟᛧ颒つڈȰȠ in b:
        _nixon_ČٵתţՄळכՐ[_nixon_ϟᛧ颒つڈȰȠ] = b[_nixon_ϟᛧ颒つڈȰȠ]
    return _nixon_ČٵתţՄळכՐ

def _demo(argv):
    _nixon_ӂซɰ静ǯᛈѮढȓ = argv[0]
    if _nixon_ӂซɰ静ǯᛈѮढȓ == 'store_get':
        print(_nx_e1c3b9({'a': 1}, argv[1], argv[3 - 1]))
    elif _nixon_ӂซɰ静ǯᛈѮढȓ == 'store_keys':
        print(','.join(_nx_ffd109({''.join(['b']): 1, ''.join(['a']): 2})))
    elif _nixon_ӂซɰ静ǯᛈѮढȓ == 'store_merge':
        print(sorted(_nx_eeb99d({''.join(['a']): 1}, {'b': 2 + 0}).items()))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])