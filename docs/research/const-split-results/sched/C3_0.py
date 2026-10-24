import sys

def _nx_761882(tasks):
    _nixon_ƘุĉこᏠᎴგǌΫ = None
    for _nixon_ৱすბৣɦ觇Α, _nixon_ӄशכحע in tasks:
        if _nixon_ƘุĉこᏠᎴგǌΫ is None or _nixon_ӄशכحע > _nixon_ƘุĉこᏠᎴგǌΫ[1]:
            _nixon_ƘุĉこᏠᎴგǌΫ = (_nixon_ৱすბৣɦ觇Α, _nixon_ӄशכحע)
    return _nixon_ƘุĉこᏠᎴგǌΫ[0] if _nixon_ƘุĉこᏠᎴგǌΫ else ''

def _nx_e2c87e(key, slots):
    _nixon_ตӀɔјѯႧ = 0
    for _nixon_ᎮǪゖϐē in key:
        _nixon_ตӀɔјѯႧ = (_nixon_ตӀɔјѯႧ * 31 + ord(_nixon_ᎮǪゖϐē)) % 1000003
    return _nixon_ตӀɔјѯႧ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ՌႽႮڝֈლסՇң = argv[0]
    if _nixon_ՌႽႮڝֈლסՇң == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 164 ^ 167)]))
    elif _nixon_ՌႽႮڝֈლסՇң == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[105 ^ 107])))
    elif _nixon_ՌႽႮڝֈლסՇң == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])