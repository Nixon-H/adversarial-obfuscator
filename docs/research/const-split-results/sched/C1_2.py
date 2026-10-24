import sys

def _nx_761882(tasks):
    _nixon_ʟ۟Ⴘצख़şψīڋ = None
    for _nixon_ᛂگॏʕᚡจৱფᛧט, _nixon_ƥڕᏒŁっӯნՖاॏ in tasks:
        if _nixon_ʟ۟Ⴘצख़şψīڋ is None or _nixon_ƥڕᏒŁっӯნՖاॏ > _nixon_ʟ۟Ⴘצख़şψīڋ[1]:
            _nixon_ʟ۟Ⴘצख़şψīڋ = (_nixon_ᛂگॏʕᚡจৱფᛧט, _nixon_ƥڕᏒŁっӯნՖاॏ)
    return _nixon_ʟ۟Ⴘצख़şψīڋ[0] if _nixon_ʟ۟Ⴘצख़şψīڋ else ''

def _nx_e2c87e(key, slots):
    _nixon_Ζʓʒȝぉ验מщすᛂ = 0
    for _nixon_๘ᏀฝדসƋ in key:
        _nixon_Ζʓʒȝぉ验מщすᛂ = (_nixon_Ζʓʒȝぉ验מщすᛂ * 31 + ord(_nixon_๘ᏀฝדসƋ)) % 1000003
    return _nixon_Ζʓʒȝぉ验מщすᛂ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ฮลぅڵॆŝ = argv[0]
    if _nixon_ฮลぅڵॆŝ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ฮลぅڵॆŝ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ฮลぅڵॆŝ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])