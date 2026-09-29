import sys

def _nx_761882(tasks):
    _nixon_ʠӜげღœւĞ = None
    for _nixon_ฟͼძぺがƐٱ, _nixon_ᏳӲכפᏏ醵ۡゆ in tasks:
        if _nixon_ʠӜげღœւĞ is None or _nixon_ʠӜげღœւĞ[1] < _nixon_ᏳӲכפᏏ醵ۡゆ:
            _nixon_ʠӜげღœւĞ = (_nixon_ฟͼძぺがƐٱ,) + (_nixon_ᏳӲכפᏏ醵ۡゆ,)
    return _nixon_ʠӜげღœւĞ[0] if _nixon_ʠӜげღœւĞ else ''

def _nx_e2c87e(key, slots):
    _nixon_にǶმςƌ = 0
    for _nixon_Āিڲᚷ窜ģ榩Řȝӿ in key:
        _nixon_にǶმςƌ = (_nixon_にǶმςƌ * 31 + ord(_nixon_Āিڲᚷ窜ģ榩Řȝӿ)) % 1000003
    return _nixon_にǶმςƌ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_থҵみᚫēՉۃ = argv[0]
    if _nixon_থҵみᚫēՉۃ == 'priority_pick':
        print(_nx_761882([('a',) + (1,)] + [('b', 5 - 0), ('c', 3)]))
    elif _nixon_থҵみᚫēՉۃ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[4 - 2])))
    elif _nixon_থҵみᚫēՉۃ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print(''.join(['u', 'n', 'k', 'n', 'o', 'w', 'n', ' ', 'o', 'p']))
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])