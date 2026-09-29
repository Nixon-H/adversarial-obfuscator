import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ᚴくऐขئべшᏱ = []
    run = text[0]
    _nixon_ίᛢɯφԵǅ৫Өᛛҽ = 1
    for _nixon_忲ʮᎩცᏎקᏂढΌŀ in text[1:]:
        if _nixon_忲ʮᎩცᏎקᏂढΌŀ == run[-1] and _nixon_ίᛢɯφԵǅ৫Өᛛҽ < 9:
            _nixon_ίᛢɯφԵǅ৫Өᛛҽ += 1
        else:
            _nixon_ᚴくऐขئべшᏱ.append(run[-1] + str(_nixon_ίᛢɯφԵǅ৫Өᛛҽ))
            run = _nixon_忲ʮᎩცᏎקᏂढΌŀ
            _nixon_ίᛢɯφԵǅ৫Өᛛҽ = 1
    _nixon_ᚴくऐขئべшᏱ.append(run[-1] + str(_nixon_ίᛢɯφԵǅ৫Өᛛҽ))
    return ''.join(_nixon_ᚴくऐขئべшᏱ)

def _nx_b27c0a(code):
    _nixon_ᚴくऐขئべшᏱ = []
    _nixon_է釓ƛۺᛩ輺є = 0
    while _nixon_է釓ƛۺᛩ輺є < len(code):
        _nixon_忲ʮᎩცᏎקᏂढΌŀ = code[_nixon_է釓ƛۺᛩ輺є]
        _nixon_ᛥ齎辬ǉธŵᚯऴᏉו = int(code[_nixon_է釓ƛۺᛩ輺є + 1])
        _nixon_ᚴくऐขئべшᏱ.append(_nixon_忲ʮᎩცᏎקᏂढΌŀ * _nixon_ᛥ齎辬ǉธŵᚯऴᏉו)
        _nixon_է釓ƛۺᛩ輺є += 2
    return ''.join(_nixon_ᚴくऐขئべшᏱ)

def _nx_a02e30(data, key):
    _nixon_Ⴕטǅųűɣჵぇɢ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ちႢ璻ѷȐ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ʒɀɸԿĪל ^ _nixon_ちႢ璻ѷȐ[_nixon_է釓ƛۺᛩ輺є % len(_nixon_ちႢ璻ѷȐ)] for _nixon_է釓ƛۺᛩ輺є, _nixon_ʒɀɸԿĪל in enumerate(_nixon_Ⴕטǅųűɣჵぇɢ)]).hex()

def _demo(argv):
    _nixon_ա帿ҎۑۢΔゅٗᛂ = argv[0]
    if _nixon_ա帿ҎۑۢΔゅٗᛂ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ա帿ҎۑۢΔゅٗᛂ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ա帿ҎۑۢΔゅٗᛂ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])