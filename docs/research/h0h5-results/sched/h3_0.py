import sys

def _nx_761882(tasks):
    _nixon_ღۜฌȡᛆᚹ = None
    for _nixon_ɲべॐƳৈぽפ, _nixon_ふიᏜบं in tasks:
        if _nixon_ღۜฌȡᛆᚹ is None or _nixon_ふიᏜบं > _nixon_ღۜฌȡᛆᚹ[1]:
            _nixon_ღۜฌȡᛆᚹ = (_nixon_ɲべॐƳৈぽפ, _nixon_ふიᏜบं)
    return _nixon_ღۜฌȡᛆᚹ[0] if _nixon_ღۜฌȡᛆᚹ else ''

def _nx_e2c87e(key, slots):
    _nixon_凋ʒϛшშᎨבӱჴᛨ = 0
    for _nixon_աᚠɵॵΌ in key:
        _nixon_凋ʒϛшშᎨבӱჴᛨ = (_nixon_凋ʒϛшშᎨבӱჴᛨ * 31 + ord(_nixon_աᚠɵॵΌ)) % 1000003
    return _nixon_凋ʒϛшშᎨבӱჴᛨ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ӦᏒ์դؕ = argv[0]
    if _nixon_ӦᏒ์դؕ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ӦᏒ์դؕ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ӦᏒ์դؕ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])