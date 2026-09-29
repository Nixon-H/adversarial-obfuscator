import sys

def _nx_761882(tasks):
    _nixon_ᛩৈաטǣӛ = None
    for _nixon_धでʉϐ蔖ႰՠᏤ, _nixon_Ϣڈή۵ʡҩहტঀ in tasks:
        if _nixon_ᛩৈաטǣӛ is None or _nixon_Ϣڈή۵ʡҩहტঀ > _nixon_ᛩৈաטǣӛ[1]:
            _nixon_ᛩৈաטǣӛ = (_nixon_धでʉϐ蔖ႰՠᏤ, _nixon_Ϣڈή۵ʡҩहტঀ)
    return _nixon_ᛩৈաטǣӛ[0] if _nixon_ᛩৈաטǣӛ else ''

def _nx_e2c87e(key, slots):
    _nixon_゙ᛨてڥ३Ꭺ = 0
    for _nixon_ᏧᏟӎᚤᏔέʤႳժǀ in key:
        _nixon_゙ᛨてڥ३Ꭺ = (_nixon_゙ᛨてڥ३Ꭺ * 31 + ord(_nixon_ᏧᏟӎᚤᏔέʤႳժǀ)) % 1000003
    return _nixon_゙ᛨてڥ३Ꭺ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_כᚱᏰชɒڸぅᛜľब = argv[0]
    if _nixon_כᚱᏰชɒڸぅᛜľब == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_כᚱᏰชɒڸぅᛜľब == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_כᚱᏰชɒڸぅᛜľब == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])