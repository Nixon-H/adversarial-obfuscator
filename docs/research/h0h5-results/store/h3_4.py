import sys

def _nixon_ᛗねĊйՐॲۼ(store, key, value):
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
    _nixon_้घŵᏦমჶʨმŽ = dict(a)
    for _nixon_ıႠȶƳᎶהףרঅ卻 in b:
        _nixon_้घŵᏦমჶʨმŽ[_nixon_ıႠȶƳᎶהףרঅ卻] = b[_nixon_ıႠȶƳᎶהףרঅ卻]
    return _nixon_้घŵᏦমჶʨმŽ

def _demo(argv):
    _nixon_なႤٹざช゚օ = argv[0]
    if _nixon_なႤٹざช゚օ == 'store_get':
        print(_nx_e1c3b9({'a': 1}, argv[1], argv[2]))
    elif _nixon_なႤٹざช゚օ == 'store_keys':
        print(','.join(_nx_ffd109({'b': 1, 'a': 2})))
    elif _nixon_なႤٹざช゚օ == 'store_merge':
        print(sorted(_nx_eeb99d({'a': 1}, {'b': 2}).items()))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])