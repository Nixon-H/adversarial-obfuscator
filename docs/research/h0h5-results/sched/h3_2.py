import sys

def _nx_761882(tasks):
    _nixon_ȟȅᏢӇת灞 = None
    for _nixon_ळᚧՋՏΘঠᎱ, _nixon_ৃȜĠႤƘϬϜ in tasks:
        if _nixon_ȟȅᏢӇת灞 is None or _nixon_ৃȜĠႤƘϬϜ > _nixon_ȟȅᏢӇת灞[1]:
            _nixon_ȟȅᏢӇת灞 = (_nixon_ळᚧՋՏΘঠᎱ, _nixon_ৃȜĠႤƘϬϜ)
    return _nixon_ȟȅᏢӇת灞[0] if _nixon_ȟȅᏢӇת灞 else ''

def _nx_e2c87e(key, slots):
    _nixon_拀ɧষᏫͷΛᎷがӌ = 0
    for _nixon_ăᚩņ১šט in key:
        _nixon_拀ɧষᏫͷΛᎷがӌ = (_nixon_拀ɧষᏫͷΛᎷがӌ * 31 + ord(_nixon_ăᚩņ১šט)) % 1000003
    return _nixon_拀ɧষᏫͷΛᎷがӌ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ぱɁǐრჶ = argv[0]
    if _nixon_ぱɁǐრჶ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ぱɁǐრჶ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ぱɁǐრჶ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])