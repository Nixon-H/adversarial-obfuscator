import sys

def _nx_761882(tasks):
    _nixon_Ꮂをმᛛᛃ = None
    for _nixon_łჴพĝđנϏَōι, _nixon_ɬᏄჁԴג in tasks:
        if _nixon_Ꮂをმᛛᛃ is None or _nixon_ɬᏄჁԴג > _nixon_Ꮂをმᛛᛃ[1]:
            _nixon_Ꮂをმᛛᛃ = (_nixon_łჴพĝđנϏَōι, _nixon_ɬᏄჁԴג)
    return _nixon_Ꮂをმᛛᛃ[0] if _nixon_Ꮂをმᛛᛃ else ''

def _nx_e2c87e(key, slots):
    _nixon_Ϫ鹷Љภοく怟ȣՓ = 0
    for _nixon_ȏӂךץᏜᚠดפʡ in key:
        _nixon_Ϫ鹷Љภοく怟ȣՓ = (_nixon_Ϫ鹷Љภοく怟ȣՓ * 31 + ord(_nixon_ȏӂךץᏜᚠดפʡ)) % 1000003
    return _nixon_Ϫ鹷Љภοく怟ȣՓ % slots

def _nx_6e8a62(items, n):
    if not items:
        return []
    n = n % len(items)
    return items[n:] + items[:n]

def _demo(argv):
    _nixon_ᚺএҠظႱ = argv[0]
    if _nixon_ᚺএҠظႱ == 'priority_pick':
        print(_nx_761882([('a', 1), ('b', 5), ('c', 3)]))
    elif _nixon_ᚺএҠظႱ == 'slot_hash':
        print(_nx_e2c87e(argv[1], int(argv[2])))
    elif _nixon_ᚺএҠظႱ == 'rotate_list':
        print(','.join(_nx_6e8a62(argv[1].split(','), int(argv[2]))))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])