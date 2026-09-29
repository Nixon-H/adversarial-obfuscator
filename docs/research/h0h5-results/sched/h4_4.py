import sys

def _nx_761882(tasks):
    _nixon_țɛɨڣōΓふЫ = None
    for _nixon_ɐίらϳႨझ, _nixon_ჾႻলঝᛗश in tasks:
        if _nixon_țɛɨڣōΓふЫ is None or _nixon_ჾႻলঝᛗश > _nixon_țɛɨڣōΓふЫ[1]:
            _nixon_țɛɨڣōΓふЫ = (_nixon_ɐίらϳႨझ, _nixon_ჾႻলঝᛗश)
    return _nixon_țɛɨڣōΓふЫ[0] if _nixon_țɛɨڣōΓふЫ else ''

def _nx_e2c87e(key, slots):
    _nixon_ॡķʯร毹餄Ӝ = 0
    for _nixon_貲ŅآؼՊɡᎵᛥѮ in key:
        _nixon_ॡķʯร毹餄Ӝ = (_nixon_ॡķʯร毹餄Ӝ * 31 + ord(_nixon_貲ŅآؼՊɡᎵᛥѮ)) % 1000003
    return _nixon_ॡķʯร毹餄Ӝ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ռওפばᏠႸ = argv[0]
    if _nixon_ռওפばᏠႸ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ռওפばᏠႸ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ռওפばᏠႸ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])