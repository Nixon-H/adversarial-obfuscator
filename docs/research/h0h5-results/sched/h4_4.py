import sys

def _nx_761882(tasks):
    _nixon_ҶοĿЧᏃנ = None
    for _nixon_ٞٔ飰ĚƶŐ, _nixon_Չยįქէʃƍᛊ in tasks:
        if _nixon_ҶοĿЧᏃנ is None or _nixon_Չยįქէʃƍᛊ > _nixon_ҶοĿЧᏃנ[1]:
            _nixon_ҶοĿЧᏃנ = (_nixon_ٞٔ飰ĚƶŐ, _nixon_Չยįქէʃƍᛊ)
    return _nixon_ҶοĿЧᏃנ[0] if _nixon_ҶοĿЧᏃנ else ''

def _nx_e2c87e(key, slots):
    _nixon_ʛ盉Şלოᛊᚮǋくɒ = 0
    for _nixon_たᎴ欼ᚿǇҥ in key:
        _nixon_ʛ盉Şלოᛊᚮǋくɒ = (_nixon_ʛ盉Şלოᛊᚮǋくɒ * 31 + ord(_nixon_たᎴ欼ᚿǇҥ)) % 1000003
    return _nixon_ʛ盉Şלოᛊᚮǋくɒ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_Ꮐلざげۜॸ = argv[0]
    if _nixon_Ꮐلざげۜॸ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_Ꮐلざげۜॸ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_Ꮐلざげۜॸ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])