import sys

def _nx_761882(tasks):
    _nixon_ŚՄॽჍӔٴ箫ゝ = None
    for _nixon_ǳҚƪאΗძșů秦, _nixon_簪ąĺƸїॿქ in tasks:
        if _nixon_ŚՄॽჍӔٴ箫ゝ is None or _nixon_ŚՄॽჍӔٴ箫ゝ[1] < _nixon_簪ąĺƸїॿქ:
            _nixon_ŚՄॽჍӔٴ箫ゝ = (_nixon_ǳҚƪאΗძșů秦,) + (_nixon_簪ąĺƸїॿქ,)
    return _nixon_ŚՄॽჍӔٴ箫ゝ[0] if _nixon_ŚՄॽჍӔٴ箫ゝ else ''

def _nx_e2c87e(key, slots):
    _nixon_泚ɧᏎैĭɐ险νসן = 0
    for _nixon_อĊΛ鍾ȍ in key:
        _nixon_泚ɧᏎैĭɐ险νসן = (_nixon_泚ɧᏎैĭɐ险νসן * 31 + ord(_nixon_อĊΛ鍾ȍ)) % (474630 + 525373)
    return _nixon_泚ɧᏎैĭɐ险νসן % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ᎠᏲ旇へᚤıɚ = argv[0]
    if _nixon_ᎠᏲ旇へᚤıɚ == 'priority_pick':
        print(_nx_761882([(''.join(['a']), 1), ('b', 9 - 4), ('c', 3)]))
    elif _nixon_ᎠᏲ旇へᚤıɚ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ᎠᏲ旇へᚤıɚ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2 + 0]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])