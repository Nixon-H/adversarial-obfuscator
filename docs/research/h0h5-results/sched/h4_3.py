import sys

def _nx_761882(tasks):
    _nixon_ぴ斤ɷؐο = None
    for _nixon_ゕそіЌᛅʣঊঔĻ, _nixon_כΈכᚴचǮևɔϻ in tasks:
        if _nixon_ぴ斤ɷؐο is None or _nixon_כΈכᚴचǮևɔϻ > _nixon_ぴ斤ɷؐο[1]:
            _nixon_ぴ斤ɷؐο = (_nixon_ゕそіЌᛅʣঊঔĻ, _nixon_כΈכᚴचǮևɔϻ)
    return _nixon_ぴ斤ɷؐο[0] if _nixon_ぴ斤ɷؐο else ''

def _nx_e2c87e(key, slots):
    _nixon_ɢᛚႩᛘԲ = 0
    for _nixon_ȄǗǱլोႤᏍԽռ in key:
        _nixon_ɢᛚႩᛘԲ = (_nixon_ɢᛚႩᛘԲ * 31 + ord(_nixon_ȄǗǱլोႤᏍԽռ)) % 1000003
    return _nixon_ɢᛚႩᛘԲ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ѱڋƐᚭᛂ = argv[0]
    if _nixon_ѱڋƐᚭᛂ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ѱڋƐᚭᛂ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ѱڋƐᚭᛂ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])