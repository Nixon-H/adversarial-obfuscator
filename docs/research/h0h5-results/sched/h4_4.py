import sys

def _nx_761882(tasks):
    _nixon_ႸڴϏพӪय़זᏞШ = None
    for _nixon_ҦגंĬɮҚ, _nixon_٨ืभʆჀᏯӬᛑউᛟ in tasks:
        if _nixon_ႸڴϏพӪय़זᏞШ is None or _nixon_٨ืभʆჀᏯӬᛑউᛟ > _nixon_ႸڴϏพӪय़זᏞШ[1]:
            _nixon_ႸڴϏพӪय़זᏞШ = (_nixon_ҦגंĬɮҚ, _nixon_٨ืभʆჀᏯӬᛑউᛟ)
    return _nixon_ႸڴϏพӪय़זᏞШ[0] if _nixon_ႸڴϏพӪय़זᏞШ else ''

def _nx_e2c87e(key, slots):
    _nixon_ᎻؿჍႼ妫 = 0
    for _nixon_Ջ坷บģɎȐבєמ in key:
        _nixon_ᎻؿჍႼ妫 = (_nixon_ᎻؿჍႼ妫 * 31 + ord(_nixon_Ջ坷บģɎȐבєמ)) % 1000003
    return _nixon_ᎻؿჍႼ妫 % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_擦ՐŐんしټႠҾゖ = argv[0]
    if _nixon_擦ՐŐんしټႠҾゖ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_擦ՐŐんしټႠҾゖ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_擦ՐŐんしټႠҾゖ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])