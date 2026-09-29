import sys

def _nx_761882(tasks):
    _nixon_ȋპॎڠӤŗ = None
    for _nixon_ȷᛁऩȓǢ, _nixon_ՃĂǠםӺͶᛩш in tasks:
        if _nixon_ȋპॎڠӤŗ is None or _nixon_ՃĂǠםӺͶᛩш > _nixon_ȋპॎڠӤŗ[1]:
            _nixon_ȋპॎڠӤŗ = (_nixon_ȷᛁऩȓǢ, _nixon_ՃĂǠםӺͶᛩш)
    return _nixon_ȋპॎڠӤŗ[0] if _nixon_ȋპॎڠӤŗ else ''

def _nx_e2c87e(key, slots):
    _nixon_جכΧҷѧůʔႤۭ = 0
    for _nixon_仟้ङҜάᏨᛨ魎ם in key:
        _nixon_جכΧҷѧůʔႤۭ = (_nixon_جכΧҷѧůʔႤۭ * 31 + ord(_nixon_仟้ङҜάᏨᛨ魎ם)) % 1000003
    return _nixon_جכΧҷѧůʔႤۭ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ŇɠŧᎮŲɆρ = argv[0]
    if _nixon_ŇɠŧᎮŲɆρ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ŇɠŧᎮŲɆρ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ŇɠŧᎮŲɆρ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])