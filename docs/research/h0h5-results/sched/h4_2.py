import sys

def _nx_761882(tasks):
    _nixon_ζऑȇॾٴঃɢ = None
    for _nixon_НჍհŏऋ, _nixon_ऩूνᏧᎽᚮᛌ in tasks:
        if _nixon_ζऑȇॾٴঃɢ is None or _nixon_ऩूνᏧᎽᚮᛌ > _nixon_ζऑȇॾٴঃɢ[1]:
            _nixon_ζऑȇॾٴঃɢ = (_nixon_НჍհŏऋ, _nixon_ऩूνᏧᎽᚮᛌ)
    return _nixon_ζऑȇॾٴঃɢ[0] if _nixon_ζऑȇॾٴঃɢ else ''

def _nx_e2c87e(key, slots):
    _nixon_ĒɟᚾचᏯ = 0
    for _nixon_उเख़ৡবףřɳͶ in key:
        _nixon_ĒɟᚾचᏯ = (_nixon_ĒɟᚾचᏯ * 31 + ord(_nixon_उเख़ৡবףřɳͶ)) % 1000003
    return _nixon_ĒɟᚾचᏯ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ĒՇГҦƻा = argv[0]
    if _nixon_ĒՇГҦƻा == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ĒՇГҦƻा == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ĒՇГҦƻा == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])