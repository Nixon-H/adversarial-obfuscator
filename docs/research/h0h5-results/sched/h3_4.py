import sys

def _nx_761882(tasks):
    _nixon_ხЫғ๊ĵ = None
    for _nixon_ŨȴǠᛕǼϵʏҔռ, _nixon_۴ǞসՏせŐɮ in tasks:
        if _nixon_ხЫғ๊ĵ is None or _nixon_۴ǞসՏせŐɮ > _nixon_ხЫғ๊ĵ[1]:
            _nixon_ხЫғ๊ĵ = (_nixon_ŨȴǠᛕǼϵʏҔռ, _nixon_۴ǞসՏせŐɮ)
    return _nixon_ხЫғ๊ĵ[0] if _nixon_ხЫғ๊ĵ else ''

def _nx_e2c87e(key, slots):
    _nixon_ぱƿᎫק礗كᏄϝ = 0
    for _nixon_ᛪ綊Ώɪɢ in key:
        _nixon_ぱƿᎫק礗كᏄϝ = (_nixon_ぱƿᎫק礗كᏄϝ * 31 + ord(_nixon_ᛪ綊Ώɪɢ)) % 1000003
    return _nixon_ぱƿᎫק礗كᏄϝ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ტǂसʂ٢مƅ = argv[0]
    if _nixon_ტǂसʂ٢مƅ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ტǂसʂ٢مƅ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ტǂसʂ٢مƅ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])