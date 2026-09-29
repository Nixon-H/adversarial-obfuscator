import sys

def _nx_761882(tasks):
    _nixon_قĉぽٍ६ = None
    for _nixon_зᏛかॏȒ, _nixon_יঞՓϿʛढ़ע in tasks:
        if _nixon_قĉぽٍ६ is None or _nixon_יঞՓϿʛढ़ע > _nixon_قĉぽٍ६[1]:
            _nixon_قĉぽٍ६ = (_nixon_зᏛかॏȒ, _nixon_יঞՓϿʛढ़ע)
    return _nixon_قĉぽٍ६[0] if _nixon_قĉぽٍ६ else ''

def _nx_e2c87e(key, slots):
    _nixon_ᏍᎼ殳ᛃתᎳȽซ帣Ѯ = 0
    for _nixon_ćʋəĐษɬ in key:
        _nixon_ᏍᎼ殳ᛃתᎳȽซ帣Ѯ = (_nixon_ᏍᎼ殳ᛃתᎳȽซ帣Ѯ * 31 + ord(_nixon_ćʋəĐษɬ)) % 1000003
    return _nixon_ᏍᎼ殳ᛃתᎳȽซ帣Ѯ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ϟػשच่ৡҔをᛚخ = argv[0]
    if _nixon_ϟػשच่ৡҔをᛚخ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ϟػשच่ৡҔをᛚخ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ϟػשच่ৡҔをᛚخ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])