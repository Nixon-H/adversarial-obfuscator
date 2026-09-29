import sys

def _nx_761882(tasks):
    _nixon_ۙושрღ = None
    for _nixon_МϵĴļɛ葖ϗ๐๕, _nixon_梨ऊႤȗॼᏒ枝Ȭ in tasks:
        if _nixon_ۙושрღ is None or _nixon_梨ऊႤȗॼᏒ枝Ȭ > _nixon_ۙושрღ[1]:
            _nixon_ۙושрღ = (_nixon_МϵĴļɛ葖ϗ๐๕, _nixon_梨ऊႤȗॼᏒ枝Ȭ)
    return _nixon_ۙושрღ[0] if _nixon_ۙושрღ else ''

def _nx_e2c87e(key, slots):
    _nixon_ĪにҸȔᏨֆჷճ = 0
    for _nixon_囹Ǟऽआฉぺ隹ᛢʑ in key:
        _nixon_ĪにҸȔᏨֆჷճ = (_nixon_ĪにҸȔᏨֆჷճ * 31 + ord(_nixon_囹Ǟऽआฉぺ隹ᛢʑ)) % 1000003
    return _nixon_ĪにҸȔᏨֆჷճ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_েᎬמざΤ = argv[0]
    if _nixon_েᎬמざΤ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_েᎬמざΤ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_েᎬמざΤ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])