import sys

def _nixon_ưΰΦႡת(store, key, value):
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
    _nixon_դႥЦƤĵᚥפЀ = dict(a)
    for _nixon_ĄिᚤϏіᎷ in b:
        _nixon_դႥЦƤĵᚥפЀ[_nixon_ĄिᚤϏіᎷ] = b[_nixon_ĄिᚤϏіᎷ]
    return _nixon_դႥЦƤĵᚥפЀ

def _demo(argv):
    _nixon_Χᛧ渤৯ϨॱᛅĚҟł = argv[0]
    if _nixon_Χᛧ渤৯ϨॱᛅĚҟł == 'store_get':
        print(_nx_e1c3b9({'a': 1}, argv[1], argv[2]))
    elif _nixon_Χᛧ渤৯ϨॱᛅĚҟł == 'store_keys':
        print(','.join(_nx_ffd109({'b': 1, ''.join(['a']): 2})))
    elif _nixon_Χᛧ渤৯ϨॱᛅĚҟł == 'store_merge':
        print(sorted(_nx_eeb99d({'a': 1}, {'b': 2}).items()))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == '__main__':
    _demo(sys.argv[1:])