import sys

def _nixon_צǭۛշΗŐᚧゞ(store, key, value):
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
    _nixon_ĭᏲ珩ǭשᎠθҶӓנ = dict(a)
    for _nixon_ԴᚫʁᏍӑच in b:
        _nixon_ĭᏲ珩ǭשᎠθҶӓנ[_nixon_ԴᚫʁᏍӑच] = b[_nixon_ԴᚫʁᏍӑच]
    return _nixon_ĭᏲ珩ǭשᎠθҶӓנ

def _demo(argv):
    _nixon_ゟВひҷɶא = argv[0]
    if _nixon_ゟВひҷɶא == 'store_get':
        print(_nx_e1c3b9({chr(97): 1}, argv[1], argv[2]))
    elif _nixon_ゟВひҷɶא == 'store_keys':
        print(','.join(_nx_ffd109({chr(98): 1, ''.join(['a']): 2})))
    elif _nixon_ゟВひҷɶא == 'store_merge':
        print(sorted(_nx_eeb99d({chr(97): 1}, {'b': 3 - 1}).items()))
    else:
        print(''.join(['u', 'n', 'k', 'n', 'o', 'w', 'n', ' ', 'o', 'p']))
if __name__ == '__main__':
    _demo(sys.argv[1:])