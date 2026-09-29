import sys

def _nixon_ŜŬङƯƠӬʔɢᛌٻ(store, key, value):
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
    _nixon_ᎬȢोΛɫƝぅ৭ϝ = dict(a)
    for _nixon_ᛟ鋧े०ٷस๎ᛢȤ in b:
        _nixon_ᎬȢोΛɫƝぅ৭ϝ[_nixon_ᛟ鋧े०ٷस๎ᛢȤ] = b[_nixon_ᛟ鋧े०ٷस๎ᛢȤ]
    return _nixon_ᎬȢोΛɫƝぅ৭ϝ

def _demo(argv):
    _nixon_ǐ衿תএ举ۺᛏЊ = argv[0]
    if _nixon_ǐ衿תএ举ۺᛏЊ == 'store_get':
        print(_nx_e1c3b9({chr(97): 1}, argv[1], argv[3 - 1]))
    elif _nixon_ǐ衿תএ举ۺᛏЊ == ''.join(['s', 't', 'o', 'r', 'e', '_', 'k', 'e', 'y', 's']):
        print(','.join(_nx_ffd109({chr(98): 1, 'a': 2})))
    elif _nixon_ǐ衿תএ举ۺᛏЊ == ''.join(['s', 't', 'o', 'r', 'e', '_', 'm', 'e', 'r', 'g', 'e']):
        print(sorted(_nx_eeb99d({'a': 1}, {'b': 0 + 2}).items()))
    else:
        print('unknown op')
if __name__ == chr(95) + chr(95) + chr(109) + chr(97) + chr(105) + chr(110) + chr(95) + chr(95):
    _demo(sys.argv[1:])