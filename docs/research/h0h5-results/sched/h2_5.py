import sys

def _nx_761882(tasks):
    _nixon_垧ᛁひģ孜Ⴙĥןষ = None
    for _nixon_ৰज़Ꮖ秢ᛚѡვѣ, _nixon_ᎻॄすʆॗȦয়ʫ in tasks:
        if _nixon_垧ᛁひģ孜Ⴙĥןষ is None or _nixon_垧ᛁひģ孜Ⴙĥןষ[1] < _nixon_ᎻॄすʆॗȦয়ʫ:
            _nixon_垧ᛁひģ孜Ⴙĥןষ = (_nixon_ৰज़Ꮖ秢ᛚѡვѣ, _nixon_ᎻॄすʆॗȦয়ʫ)
    return _nixon_垧ᛁひģ孜Ⴙĥןষ[0] if _nixon_垧ᛁひģ孜Ⴙĥןষ else ''

def _nx_e2c87e(key, slots):
    _nixon_ףূɾ閊פژ庼ǵড়顊 = 0
    for _nixon_覙鄜Ůぷ惗ञ in key:
        _nixon_ףূɾ閊פژ庼ǵড়顊 = (_nixon_ףূɾ閊פژ庼ǵড়顊 * (32 - 1) + ord(_nixon_覙鄜Ůぷ惗ञ)) % (1870550 - 870547)
    return _nixon_ףূɾ閊פژ庼ǵড়顊 % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_くぁᚴղ६ฦ = argv[0]
    if _nixon_くぁᚴղ६ฦ == 'priority_pick':
        print(_nx_761882([(chr(97),) + (1,), ('b', 6 - 1)] + [('c', 3)]))
    elif _nixon_くぁᚴղ६ฦ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_くぁᚴղ६ฦ == chr(114) + chr(111) + chr(116) + chr(97) + chr(116) + chr(101) + chr(95) + chr(108) + chr(105) + chr(115) + chr(116):
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[1 + 1]))))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])