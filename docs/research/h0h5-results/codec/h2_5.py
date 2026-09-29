import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ॗٴ隄҅鞐圢ė = []
    run = text[0]
    _nixon_औҢᏙस臈Ʃ = 1
    for _nixon_ӵۨɲฺᚯ進 in text[1:]:
        if _nixon_ӵۨɲฺᚯ進 == run[-1] and _nixon_औҢᏙस臈Ʃ < 9:
            _nixon_औҢᏙस臈Ʃ += 1
        else:
            _nixon_ॗٴ隄҅鞐圢ė.append(run[-1] + str(_nixon_औҢᏙस臈Ʃ))
            run = _nixon_ӵۨɲฺᚯ進
            _nixon_औҢᏙस臈Ʃ = 1
    _nixon_ॗٴ隄҅鞐圢ė.append(run[-1] + str(_nixon_औҢᏙस臈Ʃ))
    return ''.join(_nixon_ॗٴ隄҅鞐圢ė)

def _nx_b27c0a(code):
    _nixon_ॗٴ隄҅鞐圢ė = []
    _nixon_ʋᏛ祜ᚵघъ๊Ꮄųև = 0
    while len(code) > _nixon_ʋᏛ祜ᚵघъ๊Ꮄųև:
        _nixon_ӵۨɲฺᚯ進 = code[_nixon_ʋᏛ祜ᚵघъ๊Ꮄųև]
        _nixon_けΑɬ貏ƌᛙע = int(code[_nixon_ʋᏛ祜ᚵघъ๊Ꮄųև + 1])
        _nixon_ॗٴ隄҅鞐圢ė.append(_nixon_ӵۨɲฺᚯ進 * _nixon_けΑɬ貏ƌᛙע)
        _nixon_ʋᏛ祜ᚵघъ๊Ꮄųև += 2
    return ''.join(_nixon_ॗٴ隄҅鞐圢ė)

def _nx_a02e30(data, key):
    _nixon_ᚯҡלŵطᛚǱแႮȒ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ןچפॾч = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ᏑΙɉけםČĪなךぜ ^ _nixon_ןچפॾч[_nixon_ʋᏛ祜ᚵघъ๊Ꮄųև % len(_nixon_ןچפॾч)] for _nixon_ʋᏛ祜ᚵघъ๊Ꮄųև, _nixon_ᏑΙɉけםČĪなךぜ in enumerate(_nixon_ᚯҡלŵطᛚǱแႮȒ)]).hex()

def _demo(argv):
    _nixon_Њĥ๎疖垨ցწה = argv[0]
    if _nixon_Њĥ๎疖垨ցწה == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_Њĥ๎疖垨ցწה == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_Њĥ๎疖垨ցწה == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])