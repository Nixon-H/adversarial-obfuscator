import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ढʦᚰՙฌう = []
    run = text[0]
    _nixon_ॻתრႱאɢڍڟНლ = 1
    for _nixon_ჱ鯪сりדᚧ in text[1:]:
        if _nixon_ჱ鯪сりדᚧ == run[-1] and _nixon_ॻתრႱאɢڍڟНლ < 9:
            _nixon_ॻתრႱאɢڍڟНლ += 1
        else:
            _nixon_ढʦᚰՙฌう.append(run[-1] + str(_nixon_ॻתრႱאɢڍڟНლ))
            run = _nixon_ჱ鯪сりדᚧ
            _nixon_ॻתრႱאɢڍڟНლ = 1
    _nixon_ढʦᚰՙฌう.append(run[-1] + str(_nixon_ॻתრႱאɢڍڟНლ))
    return ''.join(_nixon_ढʦᚰՙฌう)

def _nx_b27c0a(code):
    _nixon_ढʦᚰՙฌう = []
    _nixon_Ꭾग़एยႵჳל = 0
    while _nixon_Ꭾग़एยႵჳל < len(code):
        _nixon_ჱ鯪сりדᚧ = code[_nixon_Ꭾग़एยႵჳל]
        _nixon_ぜשৡזฐ๋ʦᛜᏝɺ = int(code[_nixon_Ꭾग़एยႵჳל + 1])
        _nixon_ढʦᚰՙฌう.append(_nixon_ჱ鯪сりדᚧ * _nixon_ぜשৡזฐ๋ʦᛜᏝɺ)
        _nixon_Ꭾग़एยႵჳל += 2
    return ''.join(_nixon_ढʦᚰՙฌう)

def _nx_a02e30(data, key):
    _nixon_ԵŁňΙᎲҴڛ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_Ѭᛟǜʋ鰻Ⴙהჭ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ႼႪღʤɠר ^ _nixon_Ѭᛟǜʋ鰻Ⴙהჭ[_nixon_Ꭾग़एยႵჳל % len(_nixon_Ѭᛟǜʋ鰻Ⴙהჭ)] for _nixon_Ꭾग़एยႵჳל, _nixon_ႼႪღʤɠר in enumerate(_nixon_ԵŁňΙᎲҴڛ)]).hex()

def _demo(argv):
    _nixon_Ӊডǣჿǃ = argv[0]
    if _nixon_Ӊডǣჿǃ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_Ӊডǣჿǃ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_Ӊডǣჿǃ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])