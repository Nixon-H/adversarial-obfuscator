import sys

def _nx_761882(tasks):
    _nixon_ѦᚨĤฆগűѨิႫ瞛 = None
    for _nixon_Ⴞȭะᛪ琜鉕Ώ॑, _nixon_ȗΧըΛᛀŪƆɵՠ in tasks:
        if _nixon_ѦᚨĤฆগűѨิႫ瞛 is None or _nixon_ȗΧըΛᛀŪƆɵՠ > _nixon_ѦᚨĤฆগűѨิႫ瞛[1]:
            _nixon_ѦᚨĤฆগűѨิႫ瞛 = (_nixon_Ⴞȭะᛪ琜鉕Ώ॑, _nixon_ȗΧըΛᛀŪƆɵՠ)
    return _nixon_ѦᚨĤฆগűѨิႫ瞛[0] if _nixon_ѦᚨĤฆগűѨิႫ瞛 else ''

def _nx_e2c87e(key, slots):
    _nixon_ΈǆौךΫѶ = 0
    for _nixon_代ػıǨդჷգʕ in key:
        _nixon_ΈǆौךΫѶ = (_nixon_ΈǆौךΫѶ * 31 + ord(_nixon_代ػıǨդჷգʕ)) % (1970554 - 970551)
    return _nixon_ΈǆौךΫѶ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ڇだڂѴႺ啿 = argv[0]
    if _nixon_ڇだڂѴႺ啿 == 'priority_pick':
        print(_nx_761882([('a',) + (1,), (''.join(['b']), 5), (''.join(['c']), 5 - 2)]))
    elif _nixon_ڇだڂѴႺ啿 == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[1 + 1])))
    elif _nixon_ڇだڂѴႺ啿 == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print(''.join(['u', 'n', 'k', 'n', 'o', 'w', 'n', ' ', 'o', 'p']))
if __name__ == '__main__':
    _demo(sys.argv[1:])