import sys

def _nx_761882(tasks):
    _nixon_ΒᚼשӸـќ袋Ǩ = None
    for _nixon_בϹēङ如ゃᛧᏙϔФ, _nixon_ざͶพぽŞɠにƓϺķ in tasks:
        if _nixon_ΒᚼשӸـќ袋Ǩ is None or _nixon_ざͶพぽŞɠにƓϺķ > _nixon_ΒᚼשӸـќ袋Ǩ[1]:
            _nixon_ΒᚼשӸـќ袋Ǩ = (_nixon_בϹēङ如ゃᛧᏙϔФ,) + (_nixon_ざͶพぽŞɠにƓϺķ,)
    return _nixon_ΒᚼשӸـќ袋Ǩ[0] if _nixon_ΒᚼשӸـќ袋Ǩ else ''

def _nx_e2c87e(key, slots):
    _nixon_תۼΝ০ʗูϜ戎 = 0
    for _nixon_ঊלסĐʖ in key:
        _nixon_תۼΝ০ʗูϜ戎 = (_nixon_תۼΝ০ʗูϜ戎 * 31 + ord(_nixon_ঊלסĐʖ)) % (1206052 - 206049)
    return _nixon_תۼΝ০ʗูϜ戎 % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_のѻᛟמגআしよჴ = argv[0]
    if _nixon_のѻᛟמגআしよჴ == ''.join(['p', 'r', 'i', 'o', 'r', 'i', 't', 'y', '_', 'p', 'i', 'c', 'k']):
        print(_nx_761882([('a', 1), ('b', 5), (''.join(['c']), 4 - 1)]))
    elif _nixon_のѻᛟמגআしよჴ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_のѻᛟמגআしよჴ == chr(114) + chr(111) + chr(116) + chr(97) + chr(116) + chr(101) + chr(95) + chr(108) + chr(105) + chr(115) + chr(116):
        print(','.join(_nx_6e8a62(argv[1].split(''.join([','])), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])