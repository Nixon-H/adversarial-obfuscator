import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ȳჍʅƑĨ = []
    run = text[0]
    _nixon_つএᏠऍבჃそƐ = 1
    for _nixon_ǧᏓরๆє in text[1:]:
        if _nixon_ǧᏓরๆє == run[-1] and _nixon_つএᏠऍבჃそƐ < 9:
            _nixon_つএᏠऍבჃそƐ += 1
        else:
            _nixon_ȳჍʅƑĨ.append(run[-1] + str(_nixon_つএᏠऍבჃそƐ))
            run = _nixon_ǧᏓরๆє
            _nixon_つএᏠऍבჃそƐ = 1
    _nixon_ȳჍʅƑĨ.append(run[-1] + str(_nixon_つএᏠऍבჃそƐ))
    return ''.join(_nixon_ȳჍʅƑĨ)

def _nx_b27c0a(code):
    _nixon_ȳჍʅƑĨ = []
    _nixon_৭มႴัᏍॏȫ٥γ = 0
    while _nixon_৭มႴัᏍॏȫ٥γ < len(code):
        _nixon_ǧᏓরๆє = code[_nixon_৭มႴัᏍॏȫ٥γ]
        _nixon_裍ϋᚨᏂՔӂ = int(code[_nixon_৭มႴัᏍॏȫ٥γ + 1])
        _nixon_ȳჍʅƑĨ.append(_nixon_ǧᏓরๆє * _nixon_裍ϋᚨᏂՔӂ)
        _nixon_৭มႴัᏍॏȫ٥γ += sum([2])
    return ''.join(_nixon_ȳჍʅƑĨ)

def _nx_a02e30(data, key):
    _nixon_ڝさƊצڟᎬȬᏏ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_לぉんぴւႥᎩ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_いिՔɺᛧԵ ^ _nixon_לぉんぴւႥᎩ[_nixon_৭มႴัᏍॏȫ٥γ % len(_nixon_לぉんぴւႥᎩ)] for _nixon_৭มႴัᏍॏȫ٥γ, _nixon_いिՔɺᛧԵ in enumerate(_nixon_ڝさƊצڟᎬȬᏏ)]).hex()

def _demo(argv):
    _nixon_คɚᎤĜӠΗסゃ = argv[0]
    if _nixon_คɚᎤĜӠΗסゃ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_คɚᎤĜӠΗסゃ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_คɚᎤĜӠΗסゃ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])