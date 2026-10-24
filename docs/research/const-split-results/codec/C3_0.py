import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ȳჍʅƑĨᏚろএᏠऍ = []
    run = text[0]
    _nixon_ɇჃそƐĎᏐ = 1
    for _nixon_Ꮖרๆє৭มႴัᏍॏ in text[1:]:
        if _nixon_Ꮖרๆє৭มႴัᏍॏ == run[-1] and _nixon_ɇჃそƐĎᏐ < 9:
            _nixon_ɇჃそƐĎᏐ += 1
        else:
            _nixon_ȳჍʅƑĨᏚろএᏠऍ.append(run[-1] + str(_nixon_ɇჃそƐĎᏐ))
            run = _nixon_Ꮖרๆє৭มႴัᏍॏ
            _nixon_ɇჃそƐĎᏐ = 1
    _nixon_ȳჍʅƑĨᏚろএᏠऍ.append(run[-1] + str(_nixon_ɇჃそƐĎᏐ))
    return ''.join(_nixon_ȳჍʅƑĨᏚろএᏠऍ)

def _nx_b27c0a(code):
    _nixon_ȳჍʅƑĨᏚろএᏠऍ = []
    _nixon_٥γצ裍ϋ = 0
    while _nixon_٥γצ裍ϋ < len(code):
        _nixon_Ꮖרๆє৭มႴัᏍॏ = code[_nixon_٥γצ裍ϋ]
        _nixon_ᚨᏂՔӂぞԷƳڟᎬ = int(code[_nixon_٥γצ裍ϋ + 1])
        _nixon_ȳჍʅƑĨᏚろএᏠऍ.append(_nixon_Ꮖרๆє৭มႴัᏍॏ * _nixon_ᚨᏂՔӂぞԷƳڟᎬ)
        _nixon_٥γצ裍ϋ += 2
    return ''.join(_nixon_ȳჍʅƑĨᏚろএᏠऍ)

def _nx_a02e30(data, key):
    _nixon_ᏏႻᏙʉぴ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ႥᎩȫिՔɺ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ԵなĕʓᎤĜӠΗ ^ _nixon_ႥᎩȫिՔɺ[_nixon_٥γצ裍ϋ % len(_nixon_ႥᎩȫिՔɺ)] for _nixon_٥γצ裍ϋ, _nixon_ԵなĕʓᎤĜӠΗ in enumerate(_nixon_ᏏႻᏙʉぴ)]).hex()

def _demo(argv):
    _nixon_रゃǁעჺėᏀ = argv[0]
    if _nixon_रゃǁעჺėᏀ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_रゃǁעჺėᏀ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_रゃǁעჺėᏀ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])