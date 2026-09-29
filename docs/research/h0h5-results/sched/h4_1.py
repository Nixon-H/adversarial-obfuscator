import sys

def _nx_761882(tasks):
    _nixon_ʔϑĖʐのふ炃Ŷᚮ = None
    for _nixon_靄ŸטɅᏁঽ, _nixon_तз๓јऽϟげ in tasks:
        if _nixon_ʔϑĖʐのふ炃Ŷᚮ is None or _nixon_तз๓јऽϟげ > _nixon_ʔϑĖʐのふ炃Ŷᚮ[1]:
            _nixon_ʔϑĖʐのふ炃Ŷᚮ = (_nixon_靄ŸטɅᏁঽ, _nixon_तз๓јऽϟげ)
    return _nixon_ʔϑĖʐのふ炃Ŷᚮ[0] if _nixon_ʔϑĖʐのふ炃Ŷᚮ else ''

def _nx_e2c87e(key, slots):
    _nixon_ฯҐɚᏕএđႽ = 0
    for _nixon_Ŭほँ۳ʎīघēᏅ in key:
        _nixon_ฯҐɚᏕএđႽ = (_nixon_ฯҐɚᏕএđႽ * 31 + ord(_nixon_Ŭほँ۳ʎīघēᏅ)) % 1000003
    return _nixon_ฯҐɚᏕএđႽ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_घ紵つのवѭึٔʂ = argv[0]
    if _nixon_घ紵つのवѭึٔʂ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_घ紵つのवѭึٔʂ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_घ紵つのवѭึٔʂ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])