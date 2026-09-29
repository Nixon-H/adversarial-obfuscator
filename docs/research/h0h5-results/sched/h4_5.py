import sys

def _nx_761882(tasks):
    _nixon_גืҺנɂգ = None
    for _nixon_ĺば菇Ժհढ, _nixon_っĮٹवսᏰჍ٤গȆ in tasks:
        if _nixon_גืҺנɂգ is None or _nixon_っĮٹवսᏰჍ٤গȆ > _nixon_גืҺנɂգ[1]:
            _nixon_גืҺנɂգ = (_nixon_ĺば菇Ժհढ, _nixon_っĮٹवսᏰჍ٤গȆ)
    return _nixon_גืҺנɂգ[0] if _nixon_גืҺנɂգ else ''

def _nx_e2c87e(key, slots):
    _nixon_ăय़क़菄॑ҹჳεม = 0
    for _nixon_Ʀҿะ倨ᛎƙႻ in key:
        _nixon_ăय़क़菄॑ҹჳεม = (_nixon_ăय़क़菄॑ҹჳεม * 31 + ord(_nixon_Ʀҿะ倨ᛎƙႻ)) % 1000003
    return _nixon_ăय़क़菄॑ҹჳεม % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ऊ़ᚹᎷჸ = argv[0]
    if _nixon_ऊ़ᚹᎷჸ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ऊ़ᚹᎷჸ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ऊ़ᚹᎷჸ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])