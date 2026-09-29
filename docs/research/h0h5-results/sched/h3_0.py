import sys

def _nx_761882(tasks):
    _nixon_剽şᏑջή = None
    for _nixon_ᛝষおลे, _nixon_ᎷゕĢぎყ in tasks:
        if _nixon_剽şᏑջή is None or _nixon_ᎷゕĢぎყ > _nixon_剽şᏑջή[1]:
            _nixon_剽şᏑջή = (_nixon_ᛝষおลे, _nixon_ᎷゕĢぎყ)
    return _nixon_剽şᏑջή[0] if _nixon_剽şᏑջή else ''

def _nx_e2c87e(key, slots):
    _nixon_ืɵٰえᏬেσ゚ѭด = 0
    for _nixon_るΠŅ๕ċঈ in key:
        _nixon_ืɵٰえᏬেσ゚ѭด = (_nixon_ืɵٰえᏬেσ゚ѭด * 31 + ord(_nixon_るΠŅ๕ċঈ)) % 1000003
    return _nixon_ืɵٰえᏬেσ゚ѭด % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_Ⴑʠʥबฌご仂žোλ = argv[0]
    if _nixon_Ⴑʠʥबฌご仂žোλ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_Ⴑʠʥबฌご仂žোλ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_Ⴑʠʥबฌご仂žোλ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])