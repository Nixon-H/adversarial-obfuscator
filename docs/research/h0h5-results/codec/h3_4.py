import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ᏣৗᎥภร = []
    run = text[0]
    _nixon_ίᏭБᛓӃŦǷ = 1
    for _nixon_ςՖᎺঈ肀Ᏸ in text[1:]:
        if _nixon_ςՖᎺঈ肀Ᏸ == run[-1] and _nixon_ίᏭБᛓӃŦǷ < 9:
            _nixon_ίᏭБᛓӃŦǷ += 1
        else:
            _nixon_ᏣৗᎥภร.append(run[-1] + str(_nixon_ίᏭБᛓӃŦǷ))
            run = _nixon_ςՖᎺঈ肀Ᏸ
            _nixon_ίᏭБᛓӃŦǷ = 1
    _nixon_ᏣৗᎥภร.append(run[-1] + str(_nixon_ίᏭБᛓӃŦǷ))
    return ''.join(_nixon_ᏣৗᎥภร)

def _nx_b27c0a(code):
    _nixon_ᏣৗᎥภร = []
    _nixon_ᚥᏝٸƅռی = 0
    while _nixon_ᚥᏝٸƅռی < len(code):
        _nixon_ςՖᎺঈ肀Ᏸ = code[_nixon_ᚥᏝٸƅռی]
        _nixon_ᛀᛙႺᏨʫႫ = int(code[_nixon_ᚥᏝٸƅռی + 1])
        _nixon_ᏣৗᎥภร.append(_nixon_ςՖᎺঈ肀Ᏸ * _nixon_ᛀᛙႺᏨʫႫ)
        _nixon_ᚥᏝٸƅռی += 2
    return ''.join(_nixon_ᏣৗᎥภร)

def _nx_a02e30(data, key):
    _nixon_ǫʕոϮѳ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_θცᎸڵЈןჯঔ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ᛅᚣإӿもϛ ^ _nixon_θცᎸڵЈןჯঔ[_nixon_ᚥᏝٸƅռی % len(_nixon_θცᎸڵЈןჯঔ)] for _nixon_ᚥᏝٸƅռی, _nixon_ᛅᚣإӿもϛ in enumerate(_nixon_ǫʕոϮѳ)]).hex()

def _demo(argv):
    _nixon_ٔぴৡғ҄ƀקזؘ = argv[0]
    if _nixon_ٔぴৡғ҄ƀקזؘ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ٔぴৡғ҄ƀקזؘ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ٔぴৡғ҄ƀקזؘ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])