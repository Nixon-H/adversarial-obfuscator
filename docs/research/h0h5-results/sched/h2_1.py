import sys

def _nx_761882(tasks):
    _nixon_ᚲɖᚧʎǕǅʟठ常 = None
    for _nixon_Ꮀ山ġৃᛐغʊњ, _nixon_קʓωᏮΣ in tasks:
        if _nixon_ᚲɖᚧʎǕǅʟठ常 is None or _nixon_קʓωᏮΣ > _nixon_ᚲɖᚧʎǕǅʟठ常[1]:
            _nixon_ᚲɖᚧʎǕǅʟठ常 = (_nixon_Ꮀ山ġৃᛐغʊњ, _nixon_קʓωᏮΣ)
    return _nixon_ᚲɖᚧʎǕǅʟठ常[0] if _nixon_ᚲɖᚧʎǕǅʟठ常 else ''

def _nx_e2c87e(key, slots):
    _nixon_ঝᏪๅ۸Ơ = 0
    for _nixon_ნņΰᛙȭᎬき๐ЂᏴ in key:
        _nixon_ঝᏪๅ۸Ơ = (_nixon_ঝᏪๅ۸Ơ * 31 + ord(_nixon_ნņΰᛙȭᎬき๐ЂᏴ)) % 1000003
    return _nixon_ঝᏪๅ۸Ơ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_伭ŶाǀᛀᏪĿ = argv[0]
    if _nixon_伭ŶाǀᛀᏪĿ == chr(112) + chr(114) + chr(105) + chr(111) + chr(114) + chr(105) + chr(116) + chr(121) + chr(95) + chr(112) + chr(105) + chr(99) + chr(107):
        print(_nx_761882([('a',) + (1,), (chr(98), 5), ('c', 0 + 3)]))
    elif _nixon_伭ŶाǀᛀᏪĿ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_伭ŶाǀᛀᏪĿ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(''.join([','])), int(argv[1 + 1]))))
    else:
        print(''.join(['u', 'n', 'k', 'n', 'o', 'w', 'n', ' ', 'o', 'p']))
if __name__ == '__main__':
    _demo(sys.argv[1:])