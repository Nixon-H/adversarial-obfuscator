import sys

def _nx_761882(tasks):
    _nixon_զȮկჿʡђどɅলস = None
    for _nixon_ȶȄǢȸڄწ, _nixon_ڗϘႮךลǑфŶႶᎠ in tasks:
        if _nixon_զȮկჿʡђどɅলস is None or _nixon_ڗϘႮךลǑфŶႶᎠ > _nixon_զȮկჿʡђどɅলস[1]:
            _nixon_զȮկჿʡђどɅলস = (_nixon_ȶȄǢȸڄწ, _nixon_ڗϘႮךลǑфŶႶᎠ)
    return _nixon_զȮկჿʡђどɅলস[0] if _nixon_զȮկჿʡђどɅলস else ''

def _nx_e2c87e(key, slots):
    _nixon_ჩʌŘิぼčđুـ = 0
    for _nixon_よגჀЙɯנ in key:
        _nixon_ჩʌŘิぼčđুـ = (_nixon_ჩʌŘิぼčđুـ * 31 + ord(_nixon_よגჀЙɯנ)) % 1000003
    return _nixon_ჩʌŘิぼčđুـ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ᛆתᚳᚴऋڞवا = argv[0]
    if _nixon_ᛆתᚳᚴऋڞवا == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ᛆתᚳᚴऋڞवا == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ᛆתᚳᚴऋڞवا == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])