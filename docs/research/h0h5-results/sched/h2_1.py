import sys

def _nx_761882(tasks):
    _nixon_ᛈᚶק燩ᛩΣพŔ鮔 = None
    for _nixon_ŤɎԲัȤɷᚻॊŮ, _nixon_ぁɸႧ蚱ぅ in tasks:
        if _nixon_ᛈᚶק燩ᛩΣพŔ鮔 is None or _nixon_ぁɸႧ蚱ぅ > _nixon_ᛈᚶק燩ᛩΣพŔ鮔[1]:
            _nixon_ᛈᚶק燩ᛩΣพŔ鮔 = (_nixon_ŤɎԲัȤɷᚻॊŮ, _nixon_ぁɸႧ蚱ぅ)
    return _nixon_ᛈᚶק燩ᛩΣพŔ鮔[0] if _nixon_ᛈᚶק燩ᛩΣพŔ鮔 else ''

def _nx_e2c87e(key, slots):
    _nixon_ᛛ贼ধᎾᛨᚣ = 0
    for _nixon_葂ȸკ۪しჄŒん in key:
        _nixon_ᛛ贼ধᎾᛨᚣ = (_nixon_ᛛ贼ধᎾᛨᚣ * (0 + 31) + ord(_nixon_葂ȸკ۪しჄŒん)) % 1000003
    return _nixon_ᛛ贼ধᎾᛨᚣ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ぁįڈএ祼ᏔƘؙᚲ = argv[0]
    if _nixon_ぁįڈএ祼ᏔƘؙᚲ == 'priority_pick':
        print(_nx_761882([('a', 1), (''.join(['b']),) + (5,), (chr(99),) + (2 + 1,)]))
    elif _nixon_ぁįڈএ祼ᏔƘؙᚲ == chr(115) + chr(108) + chr(111) + chr(116) + chr(95) + chr(104) + chr(97) + chr(115) + chr(104):
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ぁįڈএ祼ᏔƘؙᚲ == chr(114) + chr(111) + chr(116) + chr(97) + chr(116) + chr(101) + chr(95) + chr(108) + chr(105) + chr(115) + chr(116):
        print(''.join([',']).join(_nx_6e8a62(argv[1].split(chr(44)), int(argv[4 - 2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])