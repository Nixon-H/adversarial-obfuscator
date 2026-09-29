import sys

def _nx_761882(tasks):
    _nixon_שわეঌڜᎣ = None
    for _nixon_ҵᛝמ゙ɒΝ, _nixon_ųҺউϑנ৩Կڍճ in tasks:
        if _nixon_שわეঌڜᎣ is None or _nixon_ųҺউϑנ৩Կڍճ > _nixon_שわეঌڜᎣ[1]:
            _nixon_שわეঌڜᎣ = (_nixon_ҵᛝמ゙ɒΝ, _nixon_ųҺউϑנ৩Կڍճ)
    return _nixon_שわეঌڜᎣ[0] if _nixon_שわეঌڜᎣ else ''

def _nx_e2c87e(key, slots):
    _nixon_ᛧऴᛚħᎷ۶هภղ = 0
    for _nixon_ΕЉϊڊɎゕ in key:
        _nixon_ᛧऴᛚħᎷ۶هภղ = (_nixon_ᛧऴᛚħᎷ۶هภղ * (53 - 22) + ord(_nixon_ΕЉϊڊɎゕ)) % 1000003
    return _nixon_ᛧऴᛚħᎷ۶هภղ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ᛠסמƖȍ = argv[0]
    if _nixon_ᛠסמƖȍ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 4 + 1), ('c', 4 - 1)]))
    elif _nixon_ᛠסמƖȍ == ''.join(['s', 'l', 'o', 't', '_', 'h', 'a', 's', 'h']):
        print(_nx_e2c87e(argv[1], int(argv[4 - 2])))
    elif _nixon_ᛠסמƖȍ == chr(114) + chr(111) + chr(116) + chr(97) + chr(116) + chr(101) + chr(95) + chr(108) + chr(105) + chr(115) + chr(116):
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])