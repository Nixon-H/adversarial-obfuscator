import sys

def _nx_761882(tasks):
    _nixon_にŃ゚ᛐƘุĉこ = None
    for _nixon_ᎴგǌΫटתৱす, _nixon_ბৣɦ觇ΑĤᏳशכ in tasks:
        if _nixon_にŃ゚ᛐƘุĉこ is None or _nixon_ბৣɦ觇ΑĤᏳशכ > _nixon_にŃ゚ᛐƘุĉこ[1]:
            _nixon_にŃ゚ᛐƘุĉこ = (_nixon_ᎴგǌΫटתৱす, _nixon_ბৣɦ觇ΑĤᏳशכ)
    return _nixon_にŃ゚ᛐƘุĉこ[0] if _nixon_にŃ゚ᛐƘุĉこ else ''

def _nx_e2c87e(key, slots):
    _nixon_حעשตӀɔјѯႧ = 0
    for _nixon_ᎮǪゖϐē in key:
        _nixon_حעשตӀɔјѯႧ = (_nixon_حעשตӀɔјѯႧ * 31 + ord(_nixon_ᎮǪゖϐē)) % 1000003
    return _nixon_حעשตӀɔјѯႧ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ՌႽႮڝֈლסՇң = argv[0]
    if _nixon_ՌႽႮڝֈლסՇң == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ՌႽႮڝֈლסՇң == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ՌႽႮڝֈლסՇң == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])