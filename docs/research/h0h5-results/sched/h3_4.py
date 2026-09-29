import sys

def _nx_761882(tasks):
    _nixon_ϯᛑǷŉふゅǉ楼 = None
    for _nixon_Ֆᚾद剣Պ, _nixon_এᛖ摛ʈ窲Թƥぼɐͼ in tasks:
        if _nixon_ϯᛑǷŉふゅǉ楼 is None or _nixon_এᛖ摛ʈ窲Թƥぼɐͼ > _nixon_ϯᛑǷŉふゅǉ楼[1]:
            _nixon_ϯᛑǷŉふゅǉ楼 = (_nixon_Ֆᚾद剣Պ, _nixon_এᛖ摛ʈ窲Թƥぼɐͼ)
    return _nixon_ϯᛑǷŉふゅǉ楼[0] if _nixon_ϯᛑǷŉふゅǉ楼 else ''

def _nx_e2c87e(key, slots):
    _nixon_ᏙתǣđऋǼ = 0
    for _nixon_չʦ在عǃƐդΐৠĴ in key:
        _nixon_ᏙתǣđऋǼ = (_nixon_ᏙתǣđऋǼ * 31 + ord(_nixon_չʦ在عǃƐդΐৠĴ)) % 1000003
    return _nixon_ᏙתǣđऋǼ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ᛋॖǚĽᛚოנႡ = argv[0]
    if _nixon_ᛋॖǚĽᛚოנႡ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ᛋॖǚĽᛚოנႡ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ᛋॖǚĽᛚოנႡ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])