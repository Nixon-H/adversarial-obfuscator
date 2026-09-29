import sys

def _nx_761882(tasks):
    _nixon_ตむდჿڍΐБᏧɭ = None
    for _nixon_ᚢ衤כᏙृじѿ, _nixon_әႠᏯşŘϗᚬ in tasks:
        if _nixon_ตむდჿڍΐБᏧɭ is None or _nixon_әႠᏯşŘϗᚬ > _nixon_ตむდჿڍΐБᏧɭ[1]:
            _nixon_ตむდჿڍΐБᏧɭ = (_nixon_ᚢ衤כᏙृじѿ, _nixon_әႠᏯşŘϗᚬ)
    return _nixon_ตむდჿڍΐБᏧɭ[0] if _nixon_ตむდჿڍΐБᏧɭ else ''

def _nx_e2c87e(key, slots):
    _nixon_լĨჵʮᛙॶٚ = 0
    for _nixon_ϏɒϳȦ賰Ѱև襧ջ鏌 in key:
        _nixon_լĨჵʮᛙॶٚ = (_nixon_լĨჵʮᛙॶٚ * 31 + ord(_nixon_ϏɒϳȦ賰Ѱև襧ջ鏌)) % 1000003
    return _nixon_լĨჵʮᛙॶٚ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_тृᏅיᛓपむ = argv[0]
    if _nixon_тृᏅיᛓपむ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_тृᏅיᛓपむ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_тृᏅיᛓपむ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])