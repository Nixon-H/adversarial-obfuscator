import sys

def _nx_761882(tasks):
    _nixon_փᏛ६๙鿙 = None
    for _nixon_ีᏍᛃযӤѯȞЉ, _nixon_麨თբ錒գ嘡 in tasks:
        if _nixon_փᏛ६๙鿙 is None or _nixon_麨თբ錒գ嘡 > _nixon_փᏛ६๙鿙[1]:
            _nixon_փᏛ६๙鿙 = (_nixon_ีᏍᛃযӤѯȞЉ, _nixon_麨თբ錒գ嘡)
    return _nixon_փᏛ६๙鿙[0] if _nixon_փᏛ६๙鿙 else ''

def _nx_e2c87e(key, slots):
    _nixon_ᚥһϻɪ碓ǯڤƺϭՀ = 0
    for _nixon_פघčɄǭᚻぉᎤѱ in key:
        _nixon_ᚥһϻɪ碓ǯڤƺϭՀ = (_nixon_ᚥһϻɪ碓ǯڤƺϭՀ * 31 + ord(_nixon_פघčɄǭᚻぉᎤѱ)) % 1000003
    return _nixon_ᚥһϻɪ碓ǯڤƺϭՀ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_匬॑ᏧগՍǁנՆן = argv[0]
    if _nixon_匬॑ᏧগՍǁנՆן == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_匬॑ᏧগՍǁנՆן == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_匬॑ᏧগՍǁנՆן == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])