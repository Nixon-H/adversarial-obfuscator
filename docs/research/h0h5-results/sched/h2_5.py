import sys

def _nx_761882(tasks):
    _nixon_Ꮓ़ȗɴぬĄۏ屻Ţ = None
    for _nixon_Ěॿწयɘบ, _nixon_ʂע柴ᛋᏀٿɰႥᏔ in tasks:
        if _nixon_Ꮓ़ȗɴぬĄۏ屻Ţ is None or _nixon_Ꮓ़ȗɴぬĄۏ屻Ţ[1] < _nixon_ʂע柴ᛋᏀٿɰႥᏔ:
            _nixon_Ꮓ़ȗɴぬĄۏ屻Ţ = (_nixon_Ěॿწयɘบ, _nixon_ʂע柴ᛋᏀٿɰႥᏔ)
    return _nixon_Ꮓ़ȗɴぬĄۏ屻Ţ[0] if _nixon_Ꮓ़ȗɴぬĄۏ屻Ţ else ''

def _nx_e2c87e(key, slots):
    _nixon_ǒѽҵȩՓȥђ่Ꮋ = 0
    for _nixon_ϵϰۑ砓ᚳैƸ in key:
        _nixon_ǒѽҵȩՓȥђ่Ꮋ = (_nixon_ǒѽҵȩՓȥђ่Ꮋ * (46 - 15) + ord(_nixon_ϵϰۑ砓ᚳैƸ)) % (379002 + 621001)
    return _nixon_ǒѽҵȩՓȥђ่Ꮋ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_悢բՈʊჯにם = argv[0]
    if _nixon_悢բՈʊჯにם == 'priority_pick':
        print(_nx_761882([(''.join(['a']),) + (1,), ('b', 4 + 1)] + [('c',) + (3,)]))
    elif _nixon_悢բՈʊჯにם == ''.join(['s', 'l', 'o', 't', '_', 'h', 'a', 's', 'h']):
        print(_nx_e2c87e(argv[1], int(argv[2 + 0])))
    elif _nixon_悢բՈʊჯにם == 'rotate_list':
        print(chr(44).join(_nx_6e8a62(argv[1].split(','), int(argv[2 + 0]))))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == chr(95) + chr(95) + chr(109) + chr(97) + chr(105) + chr(110) + chr(95) + chr(95):
    _demo(sys.argv[1:])