import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ऩओᎦɯי = []
    run = text[0]
    _nixon_ᏗきでҰ৪ɐ俚ť = 1
    for _nixon_ȶחکᏧǘ磳Ꮳד骻雥 in text[1:]:
        if _nixon_ȶחکᏧǘ磳Ꮳד骻雥 == run[-1] and _nixon_ᏗきでҰ৪ɐ俚ť < 9:
            _nixon_ᏗきでҰ৪ɐ俚ť += 1
        else:
            _nixon_ऩओᎦɯי.append(run[-1] + str(_nixon_ᏗきでҰ৪ɐ俚ť))
            run = _nixon_ȶחکᏧǘ磳Ꮳד骻雥
            _nixon_ᏗきでҰ৪ɐ俚ť = 1
    _nixon_ऩओᎦɯי.append(run[-1] + str(_nixon_ᏗきでҰ৪ɐ俚ť))
    return ''.join(_nixon_ऩओᎦɯי)

def _nx_b27c0a(code):
    _nixon_ऩओᎦɯי = []
    _nixon_থםᛞᚦจよडǼж = 0
    while _nixon_থםᛞᚦจよडǼж < len(code):
        _nixon_ȶחکᏧǘ磳Ꮳד骻雥 = code[_nixon_থםᛞᚦจよडǼж]
        _nixon_ᛘն๊Ꭺऑᚻ = int(code[_nixon_থםᛞᚦจよडǼж + 1])
        _nixon_ऩओᎦɯי.append(_nixon_ȶחکᏧǘ磳Ꮳד骻雥 * _nixon_ᛘն๊Ꭺऑᚻ)
        _nixon_থםᛞᚦจよडǼж += 2
    return ''.join(_nixon_ऩओᎦɯי)

def _nx_a02e30(data, key):
    _nixon_丶ᛑҰՅჁہॉฟ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ŊগצĢŀʕӒϖۓদ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ऽϳɘႭבȤ ^ _nixon_ŊগצĢŀʕӒϖۓদ[_nixon_থםᛞᚦจよडǼж % len(_nixon_ŊগצĢŀʕӒϖۓদ)] for _nixon_থםᛞᚦจよडǼж, _nixon_ऽϳɘႭבȤ in enumerate(_nixon_丶ᛑҰՅჁہॉฟ)]).hex()

def _demo(argv):
    _nixon_Ź捴隥खճȆ = argv[0]
    if _nixon_Ź捴隥खճȆ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_Ź捴隥खճȆ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_Ź捴隥खճȆ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])