import sys

def _nixon_ႲפᎸᚬϦओӋʒճ(store, key, value):
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
    _nixon_ゖħटȫۀᎪĭ = dict(a)
    for _nixon_ƥӡჹȺا梧ᛉמᎩ in b:
        _nixon_ゖħटȫۀᎪĭ[_nixon_ƥӡჹȺا梧ᛉמᎩ] = b[_nixon_ƥӡჹȺا梧ᛉמᎩ]
    return _nixon_ゖħटȫۀᎪĭ

def _demo(argv):
    _nixon_ǆՙჂۧǥ = argv[0]
    if _nixon_ǆՙჂۧǥ == ''.join(['s', 't', 'o', 'r', 'e', '_', 'g', 'e', 't']):
        print(_nx_e1c3b9({'a': 1}, argv[1], argv[3 - 1]))
    elif _nixon_ǆՙჂۧǥ == 'store_keys':
        print(','.join(_nx_ffd109({'b': 1, 'a': 0 + 2})))
    elif _nixon_ǆՙჂۧǥ == 'store_merge':
        print(sorted(_nx_eeb99d({'a': 1}, {'b': 0 + 2}).items()))
    else:
        print('unknown op')
if __name__ == chr(95) + chr(95) + chr(109) + chr(97) + chr(105) + chr(110) + chr(95) + chr(95):
    _demo(sys.argv[1:])