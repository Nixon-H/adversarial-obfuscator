import sys

def _nx_761882(tasks):
    _nixon_ϯऽĤᛙפぞŵղขŵ = None
    for _nixon_ןď๗ʄʧᎤȍיŸ饕, _nixon_ॖฉ্ѬᛓบٱЉؠჃ in tasks:
        if _nixon_ϯऽĤᛙפぞŵղขŵ is None or _nixon_ॖฉ্ѬᛓบٱЉؠჃ > _nixon_ϯऽĤᛙפぞŵղขŵ[1]:
            _nixon_ϯऽĤᛙפぞŵղขŵ = (_nixon_ןď๗ʄʧᎤȍיŸ饕, _nixon_ॖฉ্ѬᛓบٱЉؠჃ)
    return _nixon_ϯऽĤᛙפぞŵղขŵ[0] if _nixon_ϯऽĤᛙפぞŵղขŵ else ''

def _nx_e2c87e(key, slots):
    _nixon_śŊวभɯƍიᚵ = 0
    for _nixon_ุԼいᛥᚹᛊჵ狋づ৯ in key:
        _nixon_śŊวभɯƍიᚵ = (_nixon_śŊวभɯƍიᚵ * 31 + ord(_nixon_ุԼいᛥᚹᛊჵ狋づ৯)) % 1000003
    return _nixon_śŊวभɯƍიᚵ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ʆփѨӖƾᏴʁכᏑ = argv[0]
    if _nixon_ʆփѨӖƾᏴʁכᏑ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ʆփѨӖƾᏴʁכᏑ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ʆփѨӖƾᏴʁכᏑ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])