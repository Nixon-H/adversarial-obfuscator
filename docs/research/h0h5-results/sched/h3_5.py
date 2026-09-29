import sys

def _nx_761882(tasks):
    _nixon_ʧᛛڸかΪᏁ५ = None
    for _nixon_וҶΙᛅᏟՈʜאぎ, _nixon_篓ȍचॎɲᛠӔМჂ in tasks:
        if _nixon_ʧᛛڸかΪᏁ५ is None or _nixon_篓ȍचॎɲᛠӔМჂ > _nixon_ʧᛛڸかΪᏁ५[1]:
            _nixon_ʧᛛڸかΪᏁ५ = (_nixon_וҶΙᛅᏟՈʜאぎ, _nixon_篓ȍचॎɲᛠӔМჂ)
    return _nixon_ʧᛛڸかΪᏁ५[0] if _nixon_ʧᛛڸかΪᏁ५ else ''

def _nx_e2c87e(key, slots):
    _nixon_ᛚᏓǽღʠժז鶼゚ぶ = 0
    for _nixon_鸏ᛚ醕غСɟয in key:
        _nixon_ᛚᏓǽღʠժז鶼゚ぶ = (_nixon_ᛚᏓǽღʠժז鶼゚ぶ * 31 + ord(_nixon_鸏ᛚ醕غСɟয)) % 1000003
    return _nixon_ᛚᏓǽღʠժז鶼゚ぶ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ȬᎢʩʒŌɡᎳ = argv[0]
    if _nixon_ȬᎢʩʒŌɡᎳ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ȬᎢʩʒŌɡᎳ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ȬᎢʩʒŌɡᎳ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])