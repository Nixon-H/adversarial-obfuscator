import sys

def _nx_761882(tasks):
    _nixon_ͰҘՏ莁ɪ९ぅμ = None
    for _nixon_ჷᚭĠᏨɾせϪख, _nixon_ʃАӝʒঽᛃɺすᏞ in tasks:
        if _nixon_ͰҘՏ莁ɪ९ぅμ is None or _nixon_ʃАӝʒঽᛃɺすᏞ > _nixon_ͰҘՏ莁ɪ९ぅμ[1]:
            _nixon_ͰҘՏ莁ɪ९ぅμ = (_nixon_ჷᚭĠᏨɾせϪख, _nixon_ʃАӝʒঽᛃɺすᏞ)
    return _nixon_ͰҘՏ莁ɪ९ぅμ[0] if _nixon_ͰҘՏ莁ɪ९ぅμ else ''

def _nx_e2c87e(key, slots):
    _nixon_ᛤॸるぽږƶงჀۅ = 0
    for _nixon_づŘᛟŗċᚪۦ in key:
        _nixon_ᛤॸるぽږƶงჀۅ = (_nixon_ᛤॸるぽږƶงჀۅ * 31 + ord(_nixon_づŘᛟŗċᚪۦ)) % 1000003
    return _nixon_ᛤॸるぽږƶงჀۅ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ՓՒᏁןגऍƓてƧ = argv[0]
    if _nixon_ՓՒᏁןגऍƓてƧ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ՓՒᏁןגऍƓてƧ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ՓՒᏁןגऍƓてƧ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])