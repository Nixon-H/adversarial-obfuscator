import sys

def _nx_761882(tasks):
    _nixon_υНॱרざღस = None
    for _nixon_ɼקごՏड़ცѓ, _nixon_垺ȳȝҝ临ſɺ in tasks:
        if _nixon_υНॱרざღस is None or _nixon_υНॱרざღस[1] < _nixon_垺ȳȝҝ临ſɺ:
            _nixon_υНॱרざღस = (_nixon_ɼקごՏड़ცѓ, _nixon_垺ȳȝҝ临ſɺ)
    return _nixon_υНॱרざღस[0] if _nixon_υНॱרざღस else ''

def _nx_e2c87e(key, slots):
    _nixon_רएƶƼזҰᚺȖ = 0
    for _nixon_户իॽႿճ in key:
        _nixon_רएƶƼזҰᚺȖ = (_nixon_רएƶƼזҰᚺȖ * (15 + 16) + ord(_nixon_户իॽႿճ)) % 1000003
    return _nixon_רएƶƼזҰᚺȖ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_゙ぉϯႭჺ呠ŻᛂĔ = argv[0]
    if _nixon_゙ぉϯႭჺ呠ŻᛂĔ == chr(112) + chr(114) + chr(105) + chr(111) + chr(114) + chr(105) + chr(116) + chr(121) + chr(95) + chr(112) + chr(105) + chr(99) + chr(107):
        print(_nx_761882([('a', 1)] + [(chr(98),) + (7 - 2,), ('c',) + (3,)]))
    elif _nixon_゙ぉϯႭჺ呠ŻᛂĔ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[1 + 1])))
    elif _nixon_゙ぉϯႭჺ呠ŻᛂĔ == ''.join(['r', 'o', 't', 'a', 't', 'e', '_', 'l', 'i', 's', 't']):
        print(chr(44).join(_nx_6e8a62(argv[1].split(chr(44)), int(argv[3 - 1]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])