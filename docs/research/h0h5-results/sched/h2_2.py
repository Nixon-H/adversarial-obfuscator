import sys

def _nx_761882(tasks):
    _nixon_説びɯیטή傏ҢҊ = None
    for _nixon_ҼʥךতᚻᚤĶ炋๓, _nixon_फ़ח稁בჵ in tasks:
        if _nixon_説びɯیטή傏ҢҊ is None or _nixon_説びɯیטή傏ҢҊ[1] < _nixon_फ़ח稁בჵ:
            _nixon_説びɯیטή傏ҢҊ = (_nixon_ҼʥךতᚻᚤĶ炋๓, _nixon_फ़ח稁בჵ)
    return _nixon_説びɯیטή傏ҢҊ[0] if _nixon_説びɯیטή傏ҢҊ else ''

def _nx_e2c87e(key, slots):
    _nixon_ǌलצॅで = 0
    for _nixon_Զҷϩ瑱ո๘ in key:
        _nixon_ǌलצॅで = (_nixon_ǌलצॅで * 31 + ord(_nixon_Զҷϩ瑱ո๘)) % 1000003
    return _nixon_ǌलצॅで % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ϒฌႰ饎ЦႸůȤᚨल = argv[0]
    if _nixon_ϒฌႰ饎ЦႸůȤᚨल == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5)] + [('c',) + (3,)]))
    elif _nixon_ϒฌႰ饎ЦႸůȤᚨल == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2 + 0])))
    elif _nixon_ϒฌႰ饎ЦႸůȤᚨल == chr(114) + chr(111) + chr(116) + chr(97) + chr(116) + chr(101) + chr(95) + chr(108) + chr(105) + chr(115) + chr(116):
        print(''.join([',']).join(_nx_6e8a62(argv[1].split(''.join([','])), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])