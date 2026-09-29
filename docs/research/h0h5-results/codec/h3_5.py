import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_Ꮩǫϲءęふौᚻ = []
    run = text[0]
    _nixon_५सӛᎻʝſǶןす = 1
    for _nixon_ɐऀკʤძŁषۆѬȊ in text[1:]:
        if _nixon_ɐऀკʤძŁषۆѬȊ == run[-1] and _nixon_५सӛᎻʝſǶןす < 9:
            _nixon_५सӛᎻʝſǶןす += 1
        else:
            _nixon_Ꮩǫϲءęふौᚻ.append(run[-1] + str(_nixon_५सӛᎻʝſǶןす))
            run = _nixon_ɐऀკʤძŁषۆѬȊ
            _nixon_५सӛᎻʝſǶןす = 1
    _nixon_Ꮩǫϲءęふौᚻ.append(run[-1] + str(_nixon_५सӛᎻʝſǶןす))
    return ''.join(_nixon_Ꮩǫϲءęふौᚻ)

def _nx_b27c0a(code):
    _nixon_Ꮩǫϲءęふौᚻ = []
    _nixon_Ĝএ佢่२и = 0
    while _nixon_Ĝএ佢่२и < len(code):
        _nixon_ɐऀკʤძŁषۆѬȊ = code[_nixon_Ĝএ佢่२и]
        _nixon_סऋॲΆȊُ梈ירा = int(code[_nixon_Ĝএ佢่२и + 1])
        _nixon_Ꮩǫϲءęふौᚻ.append(_nixon_ɐऀკʤძŁषۆѬȊ * _nixon_סऋॲΆȊُ梈ירा)
        _nixon_Ĝএ佢่२и += 2
    return ''.join(_nixon_Ꮩǫϲءęふौᚻ)

def _nx_a02e30(data, key):
    _nixon_ЯġӓĢ枊Ĵ擁πבѷ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ন玉黑թȗסǕՐ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ᛂɾѼᛈѬר ^ _nixon_ন玉黑թȗסǕՐ[_nixon_Ĝএ佢่२и % len(_nixon_ন玉黑թȗסǕՐ)] for _nixon_Ĝএ佢่२и, _nixon_ᛂɾѼᛈѬר in enumerate(_nixon_ЯġӓĢ枊Ĵ擁πבѷ)]).hex()

def _demo(argv):
    _nixon_朊עȨՎᚪჽक़ = argv[0]
    if _nixon_朊עȨՎᚪჽक़ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_朊עȨՎᚪჽक़ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_朊עȨՎᚪჽक़ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])