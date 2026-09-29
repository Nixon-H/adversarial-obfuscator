import sys

def _nx_761882(tasks):
    _nixon_ؾӒฌ鈤ばᚻ = None
    for _nixon_ϩӢŪՇডחɘȁᚧ, _nixon_ᚡგণʚᏛ廳כ३ᚬʁ in tasks:
        if _nixon_ؾӒฌ鈤ばᚻ is None or _nixon_ᚡგণʚᏛ廳כ३ᚬʁ > _nixon_ؾӒฌ鈤ばᚻ[1]:
            _nixon_ؾӒฌ鈤ばᚻ = (_nixon_ϩӢŪՇডחɘȁᚧ, _nixon_ᚡგণʚᏛ廳כ३ᚬʁ)
    return _nixon_ؾӒฌ鈤ばᚻ[0] if _nixon_ؾӒฌ鈤ばᚻ else ''

def _nx_e2c87e(key, slots):
    _nixon_ๅ啸რƧᛦ = 0
    for _nixon_ख़ღฆפʃƎᎸვ in key:
        _nixon_ๅ啸რƧᛦ = (_nixon_ๅ啸რƧᛦ * 31 + ord(_nixon_ख़ღฆפʃƎᎸვ)) % 1000003
    return _nixon_ๅ啸რƧᛦ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ᎣჀীλᏨ诤า = argv[0]
    if _nixon_ᎣჀীλᏨ诤า == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ᎣჀীλᏨ诤า == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ᎣჀীλᏨ诤า == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])