import sys

def _nx_761882(tasks):
    _nixon_ঢȐᏚӣ०翿 = None
    for _nixon_ᛑϝみ妧ᛞ, _nixon_ռڀΒŵכ in tasks:
        if _nixon_ঢȐᏚӣ०翿 is None or _nixon_ռڀΒŵכ > _nixon_ঢȐᏚӣ०翿[1]:
            _nixon_ঢȐᏚӣ०翿 = (_nixon_ᛑϝみ妧ᛞ, _nixon_ռڀΒŵכ)
    return _nixon_ঢȐᏚӣ०翿[0] if _nixon_ঢȐᏚӣ०翿 else ''

def _nx_e2c87e(key, slots):
    _nixon_օႡᚲぐը = 0
    for _nixon_ƛᛜႨɱاךʀᎧϨ in key:
        _nixon_օႡᚲぐը = (_nixon_օႡᚲぐը * 31 + ord(_nixon_ƛᛜႨɱاךʀᎧϨ)) % 1000003
    return _nixon_օႡᚲぐը % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ცৼ้ᎾฒɻՎټॠᚼ = argv[0]
    if _nixon_ცৼ้ᎾฒɻՎټॠᚼ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ცৼ้ᎾฒɻՎټॠᚼ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ცৼ้ᎾฒɻՎټॠᚼ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])