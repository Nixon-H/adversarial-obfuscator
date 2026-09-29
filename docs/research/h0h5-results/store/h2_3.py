import sys

def _nixon_秜งᚽէڴ(store, key, value):
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
    _nixon_ƛŰϸۥमΗСゝΰჲ = dict(a)
    for _nixon_ৡป晓昿ʟȋ৩ɷუ in b:
        _nixon_ƛŰϸۥमΗСゝΰჲ[_nixon_ৡป晓昿ʟȋ৩ɷუ] = b[_nixon_ৡป晓昿ʟȋ৩ɷუ]
    return _nixon_ƛŰϸۥमΗСゝΰჲ

def _demo(argv):
    _nixon_ธƨყӆۓউ = argv[0]
    if _nixon_ธƨყӆۓউ == chr(115) + chr(116) + chr(111) + chr(114) + chr(101) + chr(95) + chr(103) + chr(101) + chr(116):
        print(_nx_e1c3b9({''.join(['a']): 1}, argv[1], argv[2]))
    elif _nixon_ธƨყӆۓউ == 'store_keys':
        print(','.join(_nx_ffd109({''.join(['b']): 1, 'a': 3 - 1})))
    elif _nixon_ธƨყӆۓউ == 'store_merge':
        print(sorted(_nx_eeb99d({'a': 1}, {'b': 2}).items()))
    else:
        print('unknown op')
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])