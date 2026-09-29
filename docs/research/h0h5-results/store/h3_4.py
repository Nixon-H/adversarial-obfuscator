import sys

def _nixon_НŨᛗওԳৈ(store, key, value):
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
    _nixon_ᚻळॏʚᚩźᚳ = dict(a)
    for _nixon_ყƎǑիՒ in b:
        _nixon_ᚻळॏʚᚩźᚳ[_nixon_ყƎǑիՒ] = b[_nixon_ყƎǑիՒ]
    return _nixon_ᚻळॏʚᚩźᚳ

def _demo(argv):
    _nixon_ؓƥןɜըϓđ = argv[0]
    if _nixon_ؓƥןɜըϓđ == 'store_get':
        print(_nx_e1c3b9({'a': 1}, argv[1], argv[2]))
    elif _nixon_ؓƥןɜըϓđ == 'store_keys':
        print(','.join(_nx_ffd109({'b': 1, 'a': 2})))
    elif _nixon_ؓƥןɜըϓđ == 'store_merge':
        print(sorted(_nx_eeb99d({'a': 1}, {'b': 2}).items()))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])