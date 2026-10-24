import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_Րぴᚺųх = []
    run = text[0]
    _nixon_ԲაᎿจზԼ = 1
    for _nixon_ᚻǳᎯٚ٥ in text[1:]:
        if _nixon_ᚻǳᎯٚ٥ == run[-1] and _nixon_ԲაᎿจზԼ < 9:
            _nixon_ԲაᎿจზԼ += 1
        else:
            _nixon_Րぴᚺųх.append(run[-1] + str(_nixon_ԲაᎿจზԼ))
            run = _nixon_ᚻǳᎯٚ٥
            _nixon_ԲაᎿจზԼ = 1
    _nixon_Րぴᚺųх.append(run[-1] + str(_nixon_ԲაᎿจზԼ))
    return ''.join(_nixon_Րぴᚺųх)

def _nx_b27c0a(code):
    _nixon_Րぴᚺųх = []
    _nixon_ɠŎ๒י১ۍ = 0
    while _nixon_ɠŎ๒י১ۍ < len(code):
        _nixon_ᚻǳᎯٚ٥ = code[_nixon_ɠŎ๒י১ۍ]
        _nixon_კՇת躮ՋᏊႺჷथᛐ = int(code[_nixon_ɠŎ๒י১ۍ + 1])
        _nixon_Րぴᚺųх.append(_nixon_ᚻǳᎯٚ٥ * _nixon_კՇת躮ՋᏊႺჷथᛐ)
        _nixon_ɠŎ๒י১ۍ += 2
    return ''.join(_nixon_Րぴᚺųх)

def _nx_a02e30(data, key):
    _nixon_ねɆჲϢʝが磤ҟ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ŹɯŸϊᚠँข = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_īǹ९ھᚴせ ^ _nixon_ŹɯŸϊᚠँข[_nixon_ɠŎ๒י১ۍ % len(_nixon_ŹɯŸϊᚠँข)] for _nixon_ɠŎ๒י১ۍ, _nixon_īǹ९ھᚴせ in enumerate(_nixon_ねɆჲϢʝが磤ҟ)]).hex()

def _demo(argv):
    _nixon_翹िۭႣԻबѲɑო = argv[0]
    if _nixon_翹िۭႣԻबѲɑო == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_翹िۭႣԻबѲɑო == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_翹िۭႣԻबѲɑო == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])