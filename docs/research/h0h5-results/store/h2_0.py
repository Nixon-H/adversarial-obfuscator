import sys

def _nixon_ূϹŔղإłづ(store, key, value):
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
    _nixon_ɔՒ艇ัთϱ = dict(a)
    for _nixon_ǣלϔ躉ჲႥड़ต in b:
        _nixon_ɔՒ艇ัთϱ[_nixon_ǣלϔ躉ჲႥड़ต] = b[_nixon_ǣלϔ躉ჲႥड़ต]
    return _nixon_ɔՒ艇ัთϱ

def _demo(argv):
    _nixon_ҫՊмٞめ٢Ⴘর = argv[0]
    if _nixon_ҫՊмٞめ٢Ⴘর == 'store_get':
        print(_nx_e1c3b9({chr(97): 1}, argv[1], argv[2]))
    elif _nixon_ҫՊмٞめ٢Ⴘর == 'store_keys':
        print(','.join(_nx_ffd109({'b': 1, chr(97): 2})))
    elif _nixon_ҫՊмٞめ٢Ⴘর == 'store_merge':
        print(sorted(_nx_eeb99d({'a': 1}, {'b': 3 - 1}).items()))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])