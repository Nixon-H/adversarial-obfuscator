import sys

def _nixon_ΑӥᏆǴ濙ᛌঌ(store, key, value):
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
    _nixon_ᛧ錙ɷえ๓დϽ = dict(a)
    for _nixon_仑ϖυɕ弇ǭᏍঈ in b:
        _nixon_ᛧ錙ɷえ๓დϽ[_nixon_仑ϖυɕ弇ǭᏍঈ] = b[_nixon_仑ϖυɕ弇ǭᏍঈ]
    return _nixon_ᛧ錙ɷえ๓დϽ

def _demo(argv):
    _nixon_ʏӸびҳैႸগ = argv[0]
    if _nixon_ʏӸびҳैႸগ == 'store_get':
        print(_nx_e1c3b9({'a': 1}, argv[1], argv[2]))
    elif _nixon_ʏӸびҳैႸগ == 'store_keys':
        print(','.join(_nx_ffd109({'b': 1, 'a': 2})))
    elif _nixon_ʏӸびҳैႸগ == 'store_merge':
        print(sorted(_nx_eeb99d({'a': 1}, {'b': 2}).items()))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])