import sys

def _nx_761882(tasks):
    _nixon_ৄ冎Υϕȭई = None
    for _nixon_ᏎบҋȫգჂჲ, _nixon_ห侑น姎くৱ in tasks:
        if _nixon_ৄ冎Υϕȭई is None or _nixon_ห侑น姎くৱ > _nixon_ৄ冎Υϕȭई[1]:
            _nixon_ৄ冎Υϕȭई = (_nixon_ᏎบҋȫգჂჲ, _nixon_ห侑น姎くৱ)
    return _nixon_ৄ冎Υϕȭई[0] if _nixon_ৄ冎Υϕȭई else ''

def _nx_e2c87e(key, slots):
    _nixon_ɿռȧǆѿᚶźۺǂ = 0
    for _nixon_ڲ蔗পিŜөღᛅ in key:
        _nixon_ɿռȧǆѿᚶźۺǂ = (_nixon_ɿռȧǆѿᚶźۺǂ * 31 + ord(_nixon_ڲ蔗পিŜөღᛅ)) % 1000003
    return _nixon_ɿռȧǆѿᚶźۺǂ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ᛥႴ椹אբķᛔ = argv[0]
    if _nixon_ᛥႴ椹אբķᛔ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ᛥႴ椹אբķᛔ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ᛥႴ椹אբķᛔ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])