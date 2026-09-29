import sys

def _nx_761882(tasks):
    _nixon_Ȝϙځĝת萇Զضბ = None
    for _nixon_ӓȡΫךऀ, _nixon_Ƀฤʉ苿ɢせ in tasks:
        if _nixon_Ȝϙځĝת萇Զضბ is None or _nixon_Ƀฤʉ苿ɢせ > _nixon_Ȝϙځĝת萇Զضბ[1]:
            _nixon_Ȝϙځĝת萇Զضბ = (_nixon_ӓȡΫךऀ, _nixon_Ƀฤʉ苿ɢせ)
    return _nixon_Ȝϙځĝת萇Զضბ[0] if _nixon_Ȝϙځĝת萇Զضბ else ''

def _nx_e2c87e(key, slots):
    _nixon_璚च徭ڜ१ = 0
    for _nixon_ҠƎցϯ۵۲ in key:
        _nixon_璚च徭ڜ१ = (_nixon_璚च徭ڜ१ * 31 + ord(_nixon_ҠƎցϯ۵۲)) % 1000003
    return _nixon_璚च徭ڜ१ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_מضऒჿভמ = argv[0]
    if _nixon_מضऒჿভמ == ''.join(['p', 'r', 'i', 'o', 'r', 'i', 't', 'y', '_', 'p', 'i', 'c', 'k']):
        print(_nx_761882([('a', 1)] + [('b',) + (5,), ('c',) + (6 - 3,)]))
    elif _nixon_מضऒჿভמ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_מضऒჿভמ == 'rotate_list':
        print(''.join([',']).join(_nx_6e8a62(argv[1].split(','), int(argv[2 + 0]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])