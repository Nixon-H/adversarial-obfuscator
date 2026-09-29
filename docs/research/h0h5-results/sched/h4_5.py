import sys

def _nx_761882(tasks):
    _nixon_ɖहৣՙ๊ʠۂ刮țを = None
    for _nixon_ৱᎸΛ৭ॱ, _nixon_めৰӍǙყस๖ばᎼ in tasks:
        if _nixon_ɖहৣՙ๊ʠۂ刮țを is None or _nixon_めৰӍǙყस๖ばᎼ > _nixon_ɖहৣՙ๊ʠۂ刮țを[1]:
            _nixon_ɖहৣՙ๊ʠۂ刮țを = (_nixon_ৱᎸΛ৭ॱ, _nixon_めৰӍǙყस๖ばᎼ)
    return _nixon_ɖहৣՙ๊ʠۂ刮țを[0] if _nixon_ɖहৣՙ๊ʠۂ刮țを else ''

def _nx_e2c87e(key, slots):
    _nixon_けॊঋϧへ = 0
    for _nixon_媐邯禨も軁ͷᏞঠǰ in key:
        _nixon_けॊঋϧへ = (_nixon_けॊঋϧへ * 31 + ord(_nixon_媐邯禨も軁ͷᏞঠǰ)) % 1000003
    return _nixon_けॊঋϧへ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_Мぞえ鞺ฮᛡๆ = argv[0]
    if _nixon_Мぞえ鞺ฮᛡๆ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_Мぞえ鞺ฮᛡๆ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_Мぞえ鞺ฮᛡๆ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])