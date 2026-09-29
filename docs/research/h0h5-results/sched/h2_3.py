import sys

def _nx_761882(tasks):
    _nixon_Ŀ噵րაをᚷɞち泀 = None
    for _nixon_ऴƴউ始ʫさʅԶใぼ, _nixon_Сϩ丯ͶۈႩ in tasks:
        if _nixon_Ŀ噵րაをᚷɞち泀 is None or _nixon_Ŀ噵րაをᚷɞち泀[1] < _nixon_Сϩ丯ͶۈႩ:
            _nixon_Ŀ噵րაをᚷɞち泀 = (_nixon_ऴƴউ始ʫさʅԶใぼ, _nixon_Сϩ丯ͶۈႩ)
    return _nixon_Ŀ噵րაをᚷɞち泀[0] if _nixon_Ŀ噵րაをᚷɞち泀 else ''

def _nx_e2c87e(key, slots):
    _nixon_ڒɿחیᚴɟ = 0
    for _nixon_ҷ゙őचᏥƜʊՄ in key:
        _nixon_ڒɿחیᚴɟ = (_nixon_ڒɿחیᚴɟ * 31 + ord(_nixon_ҷ゙őचᏥƜʊՄ)) % 1000003
    return _nixon_ڒɿחیᚴɟ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_Φᛔדڪ۰ϻךข = argv[0]
    if _nixon_Φᛔדڪ۰ϻךข == 'priority_pick':
        print(_nx_761882([(chr(97), 1)] + [('b', 5), ('c', 6 - 3)]))
    elif _nixon_Φᛔדڪ۰ϻךข == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_Φᛔדڪ۰ϻךข == ''.join(['r', 'o', 't', 'a', 't', 'e', '_', 'l', 'i', 's', 't']):
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])