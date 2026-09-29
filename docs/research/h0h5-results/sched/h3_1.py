import sys

def _nx_761882(tasks):
    _nixon_ѢぶᎹŀ蜉ϻक़კԶ = None
    for _nixon_ƀɉকڙঃŲ, _nixon_הᏕЩӉم in tasks:
        if _nixon_ѢぶᎹŀ蜉ϻक़კԶ is None or _nixon_הᏕЩӉم > _nixon_ѢぶᎹŀ蜉ϻक़კԶ[1]:
            _nixon_ѢぶᎹŀ蜉ϻक़კԶ = (_nixon_ƀɉকڙঃŲ, _nixon_הᏕЩӉم)
    return _nixon_ѢぶᎹŀ蜉ϻक़კԶ[0] if _nixon_ѢぶᎹŀ蜉ϻक़კԶ else ''

def _nx_e2c87e(key, slots):
    _nixon_ζᛓᚢิɧめēةจ = 0
    for _nixon_জႠƖעٴႭ蘾ҕדϛ in key:
        _nixon_ζᛓᚢิɧめēةจ = (_nixon_ζᛓᚢิɧめēةจ * 31 + ord(_nixon_জႠƖעٴႭ蘾ҕדϛ)) % 1000003
    return _nixon_ζᛓᚢิɧめēةจ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_せęᛔĂᚤɡ溰ɤĆچ = argv[0]
    if _nixon_せęᛔĂᚤɡ溰ɤĆچ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_せęᛔĂᚤɡ溰ɤĆچ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_せęᛔĂᚤɡ溰ɤĆچ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])