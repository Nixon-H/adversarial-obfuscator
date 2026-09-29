import sys

def _nx_761882(tasks):
    _nixon_ほ٧螓ずᏟ = None
    for _nixon_טϺ҇戂κטᏴᚺ, _nixon_ʊ襶კなᏛ in tasks:
        if _nixon_ほ٧螓ずᏟ is None or _nixon_ʊ襶კなᏛ > _nixon_ほ٧螓ずᏟ[1]:
            _nixon_ほ٧螓ずᏟ = (_nixon_טϺ҇戂κטᏴᚺ, _nixon_ʊ襶კなᏛ)
    return _nixon_ほ٧螓ずᏟ[0] if _nixon_ほ٧螓ずᏟ else ''

def _nx_e2c87e(key, slots):
    _nixon_Ƀēɑ鑃ढϲऊᏕСპ = 0
    for _nixon_їʜŐΈႺϗլნ in key:
        _nixon_Ƀēɑ鑃ढϲऊᏕСპ = (_nixon_Ƀēɑ鑃ढϲऊᏕСპ * 31 + ord(_nixon_їʜŐΈႺϗլნ)) % 1000003
    return _nixon_Ƀēɑ鑃ढϲऊᏕСპ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_Ꮰघɹ訤料顥Ռษϱ = argv[0]
    if _nixon_Ꮰघɹ訤料顥Ռษϱ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_Ꮰघɹ訤料顥Ռษϱ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_Ꮰघɹ訤料顥Ռษϱ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])