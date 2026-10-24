import sys

def _nx_761882(tasks):
    _nixon_ई১Γऍգ = None
    for _nixon_ड़ڥ侑น姎くৱ, _nixon_ɿռȧǆѿᚶźۺǂ in tasks:
        if _nixon_ई১Γऍգ is None or _nixon_ɿռȧǆѿᚶźۺǂ > _nixon_ई১Γऍգ[1]:
            _nixon_ई১Γऍգ = (_nixon_ड़ڥ侑น姎くৱ, _nixon_ɿռȧǆѿᚶźۺǂ)
    return _nixon_ई১Γऍգ[0] if _nixon_ई১Γऍգ else ''

def _nx_e2c87e(key, slots):
    _nixon_ڲ蔗পিŜөღᛅ = 0
    for _nixon_ᛥႴ椹אբķᛔ in key:
        _nixon_ڲ蔗পিŜөღᛅ = (_nixon_ڲ蔗পিŜөღᛅ * 31 + ord(_nixon_ᛥႴ椹אբķᛔ)) % 1000003
    return _nixon_ڲ蔗পিŜөღᛅ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ڣӎѸ茰պǔʪ嶷 = argv[0]
    if _nixon_ڣӎѸ茰պǔʪ嶷 == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', sum([1, 1, 1]))]))
    elif _nixon_ڣӎѸ茰պǔʪ嶷 == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ڣӎѸ茰պǔʪ嶷 == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])