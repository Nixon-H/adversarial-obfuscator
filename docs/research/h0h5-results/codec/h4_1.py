import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ॵ蠧ᏉᏇवіএ = []
    run = text[0]
    _nixon_ज椖ॴ綢ӥᏤŵŗף = 1
    for _nixon_նᛋฺैط in text[1:]:
        if _nixon_նᛋฺैط == run[-1] and _nixon_ज椖ॴ綢ӥᏤŵŗף < 9:
            _nixon_ज椖ॴ綢ӥᏤŵŗף += 1
        else:
            _nixon_ॵ蠧ᏉᏇवіএ.append(run[-1] + str(_nixon_ज椖ॴ綢ӥᏤŵŗף))
            run = _nixon_նᛋฺैط
            _nixon_ज椖ॴ綢ӥᏤŵŗף = 1
    _nixon_ॵ蠧ᏉᏇवіএ.append(run[-1] + str(_nixon_ज椖ॴ綢ӥᏤŵŗף))
    return ''.join(_nixon_ॵ蠧ᏉᏇवіএ)

def _nx_b27c0a(code):
    _nixon_ॵ蠧ᏉᏇवіএ = []
    _nixon_ঋӨฝՉɟɸხऺΰᚥ = 0
    while _nixon_ঋӨฝՉɟɸხऺΰᚥ < len(code):
        _nixon_նᛋฺैط = code[_nixon_ঋӨฝՉɟɸხऺΰᚥ]
        _nixon_აʟჵǕᚥőռȭ = int(code[_nixon_ঋӨฝՉɟɸხऺΰᚥ + 1])
        _nixon_ॵ蠧ᏉᏇवіএ.append(_nixon_նᛋฺैط * _nixon_აʟჵǕᚥőռȭ)
        _nixon_ঋӨฝՉɟɸხऺΰᚥ += 2
    return ''.join(_nixon_ॵ蠧ᏉᏇवіএ)

def _nx_a02e30(data, key):
    _nixon_סէτღᏩᚾゔɛיづ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ĳᛡטɡვ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_โәくր欜ᚷ娆גᏧ ^ _nixon_ĳᛡטɡვ[_nixon_ঋӨฝՉɟɸხऺΰᚥ % len(_nixon_ĳᛡטɡვ)] for _nixon_ঋӨฝՉɟɸხऺΰᚥ, _nixon_โәくր欜ᚷ娆גᏧ in enumerate(_nixon_סէτღᏩᚾゔɛיづ)]).hex()

def _demo(argv):
    _nixon_ՙʜゎぺɎが = argv[0]
    if _nixon_ՙʜゎぺɎが == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ՙʜゎぺɎが == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ՙʜゎぺɎが == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])