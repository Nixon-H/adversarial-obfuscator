import sys

def _nx_761882(tasks):
    _nixon_ӾʧבעĆշԼԴס = None
    for _nixon_ՉঀסŽोᏅΐিėग़, _nixon_ȃϨ媫ゃŵ in tasks:
        if _nixon_ӾʧבעĆշԼԴס is None or _nixon_ȃϨ媫ゃŵ > _nixon_ӾʧבעĆշԼԴס[1]:
            _nixon_ӾʧבעĆշԼԴס = (_nixon_ՉঀסŽोᏅΐিėग़, _nixon_ȃϨ媫ゃŵ)
    return _nixon_ӾʧבעĆշԼԴס[0] if _nixon_ӾʧבעĆշԼԴס else ''

def _nx_e2c87e(key, slots):
    _nixon_ჼᎩৢᎠןᎿরᏊ = 0
    for _nixon_洿ٵӗոȎπɐ in key:
        _nixon_ჼᎩৢᎠןᎿরᏊ = (_nixon_ჼᎩৢᎠןᎿরᏊ * 31 + ord(_nixon_洿ٵӗոȎπɐ)) % (233935 + 766068)
    return _nixon_ჼᎩৢᎠןᎿরᏊ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_黊ɵץฒゖにΆċמ = argv[0]
    if _nixon_黊ɵץฒゖにΆċמ == ''.join(['p', 'r', 'i', 'o', 'r', 'i', 't', 'y', '_', 'p', 'i', 'c', 'k']):
        print(_nx_761882([('a',) + (1,), ('b', 5), (''.join(['c']),) + (3,)]))
    elif _nixon_黊ɵץฒゖにΆċמ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_黊ɵץฒゖにΆċמ == chr(114) + chr(111) + chr(116) + chr(97) + chr(116) + chr(101) + chr(95) + chr(108) + chr(105) + chr(115) + chr(116):
        print(''.join([',']).join(_nx_6e8a62(argv[1].split(','), int(argv[3 - 1]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])