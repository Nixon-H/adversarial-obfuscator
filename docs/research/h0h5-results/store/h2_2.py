import sys

def _nixon_顲৾Ⴛ३ส(store, key, value):
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
    _nixon_ƥրႮڢȯॺͿהᎸᏓ = dict(a)
    for _nixon_נȈ๖穢いʐণטॊᚴ in b:
        _nixon_ƥրႮڢȯॺͿהᎸᏓ[_nixon_נȈ๖穢いʐণטॊᚴ] = b[_nixon_נȈ๖穢いʐণטॊᚴ]
    return _nixon_ƥրႮڢȯॺͿהᎸᏓ

def _demo(argv):
    _nixon_σքűิႷ = argv[0]
    if _nixon_σքűิႷ == 'store_get':
        print(_nx_e1c3b9({chr(97): 1}, argv[1], argv[2]))
    elif _nixon_σքűิႷ == 'store_keys':
        print(chr(44).join(_nx_ffd109({'b': 1, chr(97): 2})))
    elif _nixon_σքűิႷ == 'store_merge':
        print(sorted(_nx_eeb99d({'a': 1}, {chr(98): 2}).items()))
    else:
        print('unknown op')
if __name__ == chr(95) + chr(95) + chr(109) + chr(97) + chr(105) + chr(110) + chr(95) + chr(95):
    _demo(sys.argv[1:])