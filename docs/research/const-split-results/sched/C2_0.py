import sys

def _nx_761882(tasks):
    _nixon_ƘุĉこᏠᎴგǌ = None
    for _nixon_דڊৱすბ, _nixon_驶ৣɦ觇ΑĤᏳ in tasks:
        if _nixon_ƘุĉこᏠᎴგǌ is None or _nixon_驶ৣɦ觇ΑĤᏳ > _nixon_ƘุĉこᏠᎴგǌ[1]:
            _nixon_ƘุĉこᏠᎴგǌ = (_nixon_דڊৱすბ, _nixon_驶ৣɦ觇ΑĤᏳ)
    return _nixon_ƘุĉこᏠᎴგǌ[0] if _nixon_ƘุĉこᏠᎴგǌ else ''

def _nx_e2c87e(key, slots):
    _nixon_זწحעשตӀ = 0
    for _nixon_ƤՂכɂϼ in key:
        _nixon_זწحעשตӀ = (_nixon_זწحעשตӀ * 31 + ord(_nixon_ƤՂכɂϼ)) % 1000003
    return _nixon_זწحעשตӀ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ᎮǪゖϐēՌႽႮڝ = argv[0]
    if _nixon_ᎮǪゖϐēՌႽႮڝ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ᎮǪゖϐēՌႽႮڝ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[165 ^ 167])))
    elif _nixon_ᎮǪゖϐēՌႽႮڝ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[105 ^ 107]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])