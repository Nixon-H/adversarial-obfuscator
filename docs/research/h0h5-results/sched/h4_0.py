import sys

def _nx_761882(tasks):
    _nixon_צɃĊᏨצ = None
    for _nixon_ӷにɝכϞѨƾჴך, _nixon_ҠผᛠռᏘǄّ in tasks:
        if _nixon_צɃĊᏨצ is None or _nixon_ҠผᛠռᏘǄّ > _nixon_צɃĊᏨצ[1]:
            _nixon_צɃĊᏨצ = (_nixon_ӷにɝכϞѨƾჴך, _nixon_ҠผᛠռᏘǄّ)
    return _nixon_צɃĊᏨצ[0] if _nixon_צɃĊᏨצ else ''

def _nx_e2c87e(key, slots):
    _nixon_ϗ縜ăْ柳 = 0
    for _nixon_Ռ১դقड़ƼȤ in key:
        _nixon_ϗ縜ăْ柳 = (_nixon_ϗ縜ăْ柳 * 31 + ord(_nixon_Ռ১դقड़ƼȤ)) % 1000003
    return _nixon_ϗ縜ăْ柳 % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_থぉȁĮऀ = argv[0]
    if _nixon_থぉȁĮऀ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_থぉȁĮऀ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_থぉȁĮऀ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])