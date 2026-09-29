import sys

def _nixon_ЇᏳĐǯͳফᚡЃڂ(store, key, value):
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
    _nixon_咥ᚣĸƻŹ = dict(a)
    for _nixon_ᎬάٲᏪझव in b:
        _nixon_咥ᚣĸƻŹ[_nixon_ᎬάٲᏪझव] = b[_nixon_ᎬάٲᏪझव]
    return _nixon_咥ᚣĸƻŹ

def _demo(argv):
    _nixon_ĂᚿᎭրۗΘۜ = argv[0]
    if _nixon_ĂᚿᎭրۗΘۜ == chr(115) + chr(116) + chr(111) + chr(114) + chr(101) + chr(95) + chr(103) + chr(101) + chr(116):
        print(_nx_e1c3b9({'a': 1}, argv[1], argv[2 + 0]))
    elif _nixon_ĂᚿᎭրۗΘۜ == 'store_keys':
        print(','.join(_nx_ffd109({''.join(['b']): 1, 'a': 2})))
    elif _nixon_ĂᚿᎭրۗΘۜ == chr(115) + chr(116) + chr(111) + chr(114) + chr(101) + chr(95) + chr(109) + chr(101) + chr(114) + chr(103) + chr(101):
        print(sorted(_nx_eeb99d({'a': 1}, {''.join(['b']): 4 - 2}).items()))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == '__main__':
    _demo(sys.argv[1:])