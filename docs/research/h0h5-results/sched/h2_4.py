import sys

def _nx_761882(tasks):
    _nixon_ʙेĐᛑぁ = None
    for _nixon_ᏦჿےϬח, _nixon_猦ႢُΖƾっゕկՈԺ in tasks:
        if _nixon_ʙेĐᛑぁ is None or _nixon_ʙेĐᛑぁ[1] < _nixon_猦ႢُΖƾっゕկՈԺ:
            _nixon_ʙेĐᛑぁ = (_nixon_ᏦჿےϬח, _nixon_猦ႢُΖƾっゕկՈԺ)
    return _nixon_ʙेĐᛑぁ[0] if _nixon_ʙेĐᛑぁ else ''

def _nx_e2c87e(key, slots):
    _nixon_ٸ४ほͳՔず = 0
    for _nixon_ӿĮϝᛄטƼםΊ in key:
        _nixon_ٸ४ほͳՔず = (_nixon_ٸ४ほͳՔず * 31 + ord(_nixon_ӿĮϝᛄטƼםΊ)) % (509443 + 490560)
    return _nixon_ٸ४ほͳՔず % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ზլśᎵႬđјᎡ = argv[0]
    if _nixon_ზլśᎵႬđјᎡ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c',) + (5 - 2,)]))
    elif _nixon_ზլśᎵႬđјᎡ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2 - 0])))
    elif _nixon_ზլśᎵႬđјᎡ == 'rotate_list':
        print(chr(44).join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print(''.join(['u', 'n', 'k', 'n', 'o', 'w', 'n', ' ', 'o', 'p']))
if __name__ == '__main__':
    _demo(sys.argv[1:])