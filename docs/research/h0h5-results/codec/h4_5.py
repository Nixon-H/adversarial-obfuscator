import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_くᎸɮϩऍϱत = []
    run = text[0]
    _nixon_ĺוǦƜԷʬ = 1
    for _nixon_ᛌқჼձৃমħᛘฃ in text[1:]:
        if _nixon_ᛌқჼձৃমħᛘฃ == run[-1] and _nixon_ĺוǦƜԷʬ < 9:
            _nixon_ĺוǦƜԷʬ += 1
        else:
            _nixon_くᎸɮϩऍϱत.append(run[-1] + str(_nixon_ĺוǦƜԷʬ))
            run = _nixon_ᛌқჼձৃমħᛘฃ
            _nixon_ĺוǦƜԷʬ = 1
    _nixon_くᎸɮϩऍϱत.append(run[-1] + str(_nixon_ĺוǦƜԷʬ))
    return ''.join(_nixon_くᎸɮϩऍϱत)

def _nx_b27c0a(code):
    _nixon_くᎸɮϩऍϱत = []
    _nixon_ȃকȬศʙ = 0
    while _nixon_ȃকȬศʙ < len(code):
        _nixon_ᛌқჼձৃমħᛘฃ = code[_nixon_ȃকȬศʙ]
        _nixon_ीᛅӎړᛌীєრƶ = int(code[_nixon_ȃকȬศʙ + 1])
        _nixon_くᎸɮϩऍϱत.append(_nixon_ᛌқჼձৃমħᛘฃ * _nixon_ीᛅӎړᛌীєრƶ)
        _nixon_ȃকȬศʙ += 2
    return ''.join(_nixon_くᎸɮϩऍϱत)

def _nx_a02e30(data, key):
    _nixon_ज़ढ़ֆนढ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ŉฝȝΟ๋ʢƲᏆ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ᏝᏭᛑ栣ՈईԳ ^ _nixon_ŉฝȝΟ๋ʢƲᏆ[_nixon_ȃকȬศʙ % len(_nixon_ŉฝȝΟ๋ʢƲᏆ)] for _nixon_ȃকȬศʙ, _nixon_ᏝᏭᛑ栣ՈईԳ in enumerate(_nixon_ज़ढ़ֆนढ)]).hex()

def _demo(argv):
    _nixon_҆ګどȥড়Լ勘ƸわႦ = argv[0]
    if _nixon_҆ګどȥড়Լ勘ƸわႦ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_҆ګどȥড়Լ勘ƸわႦ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_҆ګどȥড়Լ勘ƸわႦ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])