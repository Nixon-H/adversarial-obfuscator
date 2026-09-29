import sys

def _nx_761882(tasks):
    _nixon_譬פȃीखʇνრᏀल = None
    for _nixon_৮ļŷႵՕ५, _nixon_ゎĮšڎӳתʨ゚ in tasks:
        if _nixon_譬פȃीखʇνრᏀल is None or _nixon_ゎĮšڎӳתʨ゚ > _nixon_譬פȃीखʇνრᏀल[1]:
            _nixon_譬פȃीखʇνრᏀल = (_nixon_৮ļŷႵՕ५, _nixon_ゎĮšڎӳתʨ゚)
    return _nixon_譬פȃीखʇνრᏀल[0] if _nixon_譬פȃीखʇνრᏀल else ''

def _nx_e2c87e(key, slots):
    _nixon_ɯᏡҒ৩ΊᏰぅঊۘ = 0
    for _nixon_ǣة粽ǹฉטᎰֈ in key:
        _nixon_ɯᏡҒ৩ΊᏰぅঊۘ = (_nixon_ɯᏡҒ৩ΊᏰぅঊۘ * (48 - 17) + ord(_nixon_ǣة粽ǹฉטᎰֈ)) % 1000003
    return _nixon_ɯᏡҒ৩ΊᏰぅঊۘ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ϞƘᚠ嬱Ӳҏॣ = argv[0]
    if _nixon_ϞƘᚠ嬱Ӳҏॣ == 'priority_pick':
        print(_nx_761882([('a',) + (1,), ('b', 5), ('c',) + (3,)]))
    elif _nixon_ϞƘᚠ嬱Ӳҏॣ == ''.join(['s', 'l', 'o', 't', '_', 'h', 'a', 's', 'h']):
        print(_nx_e2c87e(argv[1], int(argv[2 - 0])))
    elif _nixon_ϞƘᚠ嬱Ӳҏॣ == 'rotate_list':
        print(''.join([',']).join(_nx_6e8a62(argv[1].split(','), int(argv[4 - 2]))))
    else:
        print(''.join(['u', 'n', 'k', 'n', 'o', 'w', 'n', ' ', 'o', 'p']))
if __name__ == chr(95) + chr(95) + chr(109) + chr(97) + chr(105) + chr(110) + chr(95) + chr(95):
    _demo(sys.argv[1:])