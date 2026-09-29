import sys

def _nixon_ᏨԵᏖ溽ᛔƴΘჅথ(store, key, value):
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
    _nixon_ĚڋӏŌょךՀᛤ代 = dict(a)
    for _nixon_ᛜȣӴঢɛʣᛉē in b:
        _nixon_ĚڋӏŌょךՀᛤ代[_nixon_ᛜȣӴঢɛʣᛉē] = b[_nixon_ᛜȣӴঢɛʣᛉē]
    return _nixon_ĚڋӏŌょךՀᛤ代

def _demo(argv):
    _nixon_ՊĎǓƭה = argv[0]
    if _nixon_ՊĎǓƭה == chr(115) + chr(116) + chr(111) + chr(114) + chr(101) + chr(95) + chr(103) + chr(101) + chr(116):
        print(_nx_e1c3b9({'a': 1}, argv[1], argv[2]))
    elif _nixon_ՊĎǓƭה == 'store_keys':
        print(','.join(_nx_ffd109({'b': 1, 'a': 2})))
    elif _nixon_ՊĎǓƭה == 'store_merge':
        print(sorted(_nx_eeb99d({chr(97): 1}, {'b': 0 + 2}).items()))
    else:
        print('unknown op')
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])