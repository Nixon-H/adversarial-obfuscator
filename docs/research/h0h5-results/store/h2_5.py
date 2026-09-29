import sys

def _nixon_ղѐ৫ЉŅɧᚺЇѪ(store, key, value):
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
    _nixon_ʇփใϧ妵๖褛ư = dict(a)
    for _nixon_ძקᛍᛧᚺ in b:
        _nixon_ʇփใϧ妵๖褛ư[_nixon_ძקᛍᛧᚺ] = b[_nixon_ძקᛍᛧᚺ]
    return _nixon_ʇփใϧ妵๖褛ư

def _demo(argv):
    _nixon_ӯঝᚤכᚲĈΌɩğ = argv[0]
    if _nixon_ӯঝᚤכᚲĈΌɩğ == 'store_get':
        print(_nx_e1c3b9({'a': 1}, argv[1], argv[2]))
    elif _nixon_ӯঝᚤכᚲĈΌɩğ == chr(115) + chr(116) + chr(111) + chr(114) + chr(101) + chr(95) + chr(107) + chr(101) + chr(121) + chr(115):
        print(chr(44).join(_nx_ffd109({chr(98): 1, 'a': 2})))
    elif _nixon_ӯঝᚤכᚲĈΌɩğ == ''.join(['s', 't', 'o', 'r', 'e', '_', 'm', 'e', 'r', 'g', 'e']):
        print(sorted(_nx_eeb99d({''.join(['a']): 1}, {'b': 0 + 2}).items()))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])