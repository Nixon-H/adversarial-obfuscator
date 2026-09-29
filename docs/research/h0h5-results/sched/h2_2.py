import sys

def _nx_761882(tasks):
    _nixon_もĄխՀみ = None
    for _nixon_ჸɣ২ɴझ, _nixon_のՒנЦᚭიぶԲঝॏ in tasks:
        if _nixon_もĄխՀみ is None or _nixon_もĄխՀみ[1] < _nixon_のՒנЦᚭიぶԲঝॏ:
            _nixon_もĄխՀみ = (_nixon_ჸɣ২ɴझ,) + (_nixon_のՒנЦᚭიぶԲঝॏ,)
    return _nixon_もĄխՀみ[0] if _nixon_もĄխՀみ else ''

def _nx_e2c87e(key, slots):
    _nixon_িΖᏁぅűかԴड़ŲЪ = 0
    for _nixon_ƃᛪɡƆჹჅҖゖて in key:
        _nixon_িΖᏁぅűかԴड़ŲЪ = (_nixon_িΖᏁぅűかԴड़ŲЪ * (61 - 30) + ord(_nixon_ƃᛪɡƆჹჅҖゖて)) % (834052 + 165951)
    return _nixon_িΖᏁぅűかԴड़ŲЪ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ৄこঝႫฮέͶ沯 = argv[0]
    if _nixon_ৄこঝႫฮέͶ沯 == 'priority_pick':
        print(_nx_761882([('a',) + (1,), (''.join(['b']), 3 + 2), ('c', 3)]))
    elif _nixon_ৄこঝႫฮέͶ沯 == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ৄこঝႫฮέͶ沯 == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])