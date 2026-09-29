import sys

def _nx_761882(tasks):
    _nixon_ڭǠᛥƇɩע = None
    for _nixon_ჿჿᎴכΨॅҬᏣ, _nixon_ҩᚢɦᏨգ螹ڕみ in tasks:
        if _nixon_ڭǠᛥƇɩע is None or _nixon_ҩᚢɦᏨգ螹ڕみ > _nixon_ڭǠᛥƇɩע[1]:
            _nixon_ڭǠᛥƇɩע = (_nixon_ჿჿᎴכΨॅҬᏣ, _nixon_ҩᚢɦᏨգ螹ڕみ)
    return _nixon_ڭǠᛥƇɩע[0] if _nixon_ڭǠᛥƇɩע else ''

def _nx_e2c87e(key, slots):
    _nixon_癔れЈҖᛢůᏒᚼ = 0
    for _nixon_Ⴕᛋצऽᚳჰհূ in key:
        _nixon_癔れЈҖᛢůᏒᚼ = (_nixon_癔れЈҖᛢůᏒᚼ * 31 + ord(_nixon_Ⴕᛋצऽᚳჰհূ)) % 1000003
    return _nixon_癔れЈҖᛢůᏒᚼ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ᛉসǿႼჃƻᚹゞば = argv[0]
    if _nixon_ᛉসǿႼჃƻᚹゞば == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ᛉসǿႼჃƻᚹゞば == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ᛉসǿႼჃƻᚹゞば == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])