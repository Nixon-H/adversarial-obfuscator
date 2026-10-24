import sys

def _nx_761882(tasks):
    _nixon_זख़şψīڋᛂ = None
    for _nixon_گॏʕᚡจৱფᛧטƥ, _nixon_০ᎣॎǷणნ in tasks:
        if _nixon_זख़şψīڋᛂ is None or _nixon_০ᎣॎǷणნ > _nixon_זख़şψīڋᛂ[1]:
            _nixon_זख़şψīڋᛂ = (_nixon_گॏʕᚡจৱფᛧטƥ, _nixon_০ᎣॎǷणნ)
    return _nixon_זख़şψīڋᛂ[0] if _nixon_זख़şψīڋᛂ else ''

def _nx_e2c87e(key, slots):
    _nixon_সɰটУʒȝ = 0
    for _nixon_ʠ验מщすᛂנ๘ in key:
        _nixon_সɰটУʒȝ = (_nixon_সɰটУʒȝ * 31 + ord(_nixon_ʠ验מщすᛂנ๘)) % 1000003
    return _nixon_সɰটУʒȝ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_॔Χλɇךհลぅ = argv[0]
    if _nixon_॔Χλɇךհลぅ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_॔Χλɇךհลぅ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_॔Χλɇךհลぅ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])