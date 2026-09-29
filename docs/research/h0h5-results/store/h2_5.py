import sys

def _nixon_ঋ্מǿჄŶמǃ(store, key, value):
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
    _nixon_ϲǔᏬつᚫƷᏲᏠᛏɺ = dict(a)
    for _nixon_贱ณחᚯँบᏥת in b:
        _nixon_ϲǔᏬつᚫƷᏲᏠᛏɺ[_nixon_贱ณחᚯँบᏥת] = b[_nixon_贱ณחᚯँบᏥת]
    return _nixon_ϲǔᏬつᚫƷᏲᏠᛏɺ

def _demo(argv):
    _nixon_ᚩͶɒʂ匮ぢ = argv[0]
    if _nixon_ᚩͶɒʂ匮ぢ == 'store_get':
        print(_nx_e1c3b9({chr(97): 1}, argv[1], argv[2]))
    elif _nixon_ᚩͶɒʂ匮ぢ == 'store_keys':
        print(','.join(_nx_ffd109({'b': 1, 'a': 0 + 2})))
    elif _nixon_ᚩͶɒʂ匮ぢ == chr(115) + chr(116) + chr(111) + chr(114) + chr(101) + chr(95) + chr(109) + chr(101) + chr(114) + chr(103) + chr(101):
        print(sorted(_nx_eeb99d({'a': 1}, {'b': 4 - 2}).items()))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])