import sys

def _nx_761882(tasks):
    _nixon_ॐǷՆูǟĒᏊ = None
    for _nixon_Ϙ悬ՇหᛚฺᏧ, _nixon_ᛢɈѩऎʒ in tasks:
        if _nixon_ॐǷՆูǟĒᏊ is None or _nixon_ᛢɈѩऎʒ > _nixon_ॐǷՆูǟĒᏊ[1]:
            _nixon_ॐǷՆูǟĒᏊ = (_nixon_Ϙ悬ՇหᛚฺᏧ, _nixon_ᛢɈѩऎʒ)
    return _nixon_ॐǷՆูǟĒᏊ[0] if _nixon_ॐǷՆูǟĒᏊ else ''

def _nx_e2c87e(key, slots):
    _nixon_ŢדᏜჿ矫ɴլᛨล = 0
    for _nixon_ȴɔัťٳŷŏᛊҽ in key:
        _nixon_ŢדᏜჿ矫ɴլᛨล = (_nixon_ŢדᏜჿ矫ɴլᛨล * 31 + ord(_nixon_ȴɔัťٳŷŏᛊҽ)) % 1000003
    return _nixon_ŢדᏜჿ矫ɴլᛨล % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ŧႤᏯבग़ = argv[0]
    if _nixon_ŧႤᏯבग़ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ŧႤᏯבग़ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ŧႤᏯבग़ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])