import sys

def _nx_761882(tasks):
    _nixon_τňঌҐʅճุؑ = None
    for _nixon_žѐʆŏႴưᏌζ, _nixon_ᛆנΑᛝƒقۦȺɪᏴ in tasks:
        if _nixon_τňঌҐʅճุؑ is None or _nixon_ᛆנΑᛝƒقۦȺɪᏴ > _nixon_τňঌҐʅճุؑ[1]:
            _nixon_τňঌҐʅճุؑ = (_nixon_žѐʆŏႴưᏌζ, _nixon_ᛆנΑᛝƒقۦȺɪᏴ)
    return _nixon_τňঌҐʅճุؑ[0] if _nixon_τňঌҐʅճุؑ else ''

def _nx_e2c87e(key, slots):
    _nixon_ոغב麫ृᛂזᛕт = 0
    for _nixon_ᎲȨגĿ緼狔พ in key:
        _nixon_ոغב麫ृᛂזᛕт = (_nixon_ոغב麫ृᛂזᛕт * 31 + ord(_nixon_ᎲȨגĿ緼狔พ)) % 1000003
    return _nixon_ոغב麫ृᛂזᛕт % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_そळᏃქॸ = argv[0]
    if _nixon_そळᏃქॸ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_そळᏃქॸ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_そळᏃქॸ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])