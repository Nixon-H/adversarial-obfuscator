import sys

def _nx_761882(tasks):
    _nixon_ڇעГԱᚭɷ = None
    for _nixon_ほҒতĽՌฺ, _nixon_ᏉגȠთᛉאڗ麱Ꮯ in tasks:
        if _nixon_ڇעГԱᚭɷ is None or _nixon_ᏉגȠთᛉאڗ麱Ꮯ > _nixon_ڇעГԱᚭɷ[1]:
            _nixon_ڇעГԱᚭɷ = (_nixon_ほҒতĽՌฺ, _nixon_ᏉגȠთᛉאڗ麱Ꮯ)
    return _nixon_ڇעГԱᚭɷ[0] if _nixon_ڇעГԱᚭɷ else ''

def _nx_e2c87e(key, slots):
    _nixon_רぽฮ蓒ᛈ = 0
    for _nixon_ᎥʅॳןႭʕ揠ऀ৩ in key:
        _nixon_רぽฮ蓒ᛈ = (_nixon_רぽฮ蓒ᛈ * 31 + ord(_nixon_ᎥʅॳןႭʕ揠ऀ৩)) % 1000003
    return _nixon_רぽฮ蓒ᛈ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ŊՆҡЧᚻぅᛁႻᎱ = argv[0]
    if _nixon_ŊՆҡЧᚻぅᛁႻᎱ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ŊՆҡЧᚻぅᛁႻᎱ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ŊՆҡЧᚻぅᛁႻᎱ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])