import sys

def _nixon_ĿᏧぞ๎ăαफゔʏᏖ(store, key, value):
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
    _nixon_輍ぷ৮ყםתո = dict(a)
    for _nixon_թᏭāڶוงĠোɈ in b:
        _nixon_輍ぷ৮ყםתո[_nixon_թᏭāڶוงĠোɈ] = b[_nixon_թᏭāڶוงĠোɈ]
    return _nixon_輍ぷ৮ყםתո

def _demo(argv):
    _nixon_๙ٛǠקיღǍ = argv[0]
    if _nixon_๙ٛǠקיღǍ == 'store_get':
        print(_nx_e1c3b9({'a': 1}, argv[1], argv[2]))
    elif _nixon_๙ٛǠקיღǍ == ''.join(['s', 't', 'o', 'r', 'e', '_', 'k', 'e', 'y', 's']):
        print(chr(44).join(_nx_ffd109({'b': 1, 'a': 4 - 2})))
    elif _nixon_๙ٛǠקיღǍ == 'store_merge':
        print(sorted(_nx_eeb99d({chr(97): 1}, {'b': 2}).items()))
    else:
        print(''.join(['u', 'n', 'k', 'n', 'o', 'w', 'n', ' ', 'o', 'p']))
if __name__ == '__main__':
    _demo(sys.argv[1:])