import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_েᏠԴᎵჅɒ = []
    run = text[0]
    _nixon_цЧɡैύŔבƨ = 1
    for _nixon_Ͷ簆勼ט·ᚽ in text[1:]:
        if _nixon_Ͷ簆勼ט·ᚽ == run[-1] and _nixon_цЧɡैύŔבƨ < 9:
            _nixon_цЧɡैύŔבƨ += 1
        else:
            _nixon_েᏠԴᎵჅɒ.append(run[-1] + str(_nixon_цЧɡैύŔבƨ))
            run = _nixon_Ͷ簆勼ט·ᚽ
            _nixon_цЧɡैύŔבƨ = 1
    _nixon_েᏠԴᎵჅɒ.append(run[-1] + str(_nixon_цЧɡैύŔבƨ))
    return ''.join(_nixon_েᏠԴᎵჅɒ)

def _nx_b27c0a(code):
    _nixon_েᏠԴᎵჅɒ = []
    _nixon_শᏈЖɲŇ氈ᛅ摌Ы = 0
    while _nixon_শᏈЖɲŇ氈ᛅ摌Ы < len(code):
        _nixon_Ͷ簆勼ט·ᚽ = code[_nixon_শᏈЖɲŇ氈ᛅ摌Ы]
        _nixon_傅Ǝ鉲ƏもฒҒƯᛎ = int(code[_nixon_শᏈЖɲŇ氈ᛅ摌Ы + 1])
        _nixon_েᏠԴᎵჅɒ.append(_nixon_Ͷ簆勼ט·ᚽ * _nixon_傅Ǝ鉲ƏもฒҒƯᛎ)
        _nixon_শᏈЖɲŇ氈ᛅ摌Ы += 2
    return ''.join(_nixon_েᏠԴᎵჅɒ)

def _nx_a02e30(data, key):
    _nixon_ҞՠĬיȲڠɵᎠ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_גĚৎᏩΨ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ঀȈِīᎻ趺ۄʬへま ^ _nixon_גĚৎᏩΨ[_nixon_শᏈЖɲŇ氈ᛅ摌Ы % len(_nixon_גĚৎᏩΨ)] for _nixon_শᏈЖɲŇ氈ᛅ摌Ы, _nixon_ঀȈِīᎻ趺ۄʬへま in enumerate(_nixon_ҞՠĬיȲڠɵᎠ)]).hex()

def _demo(argv):
    _nixon_み朌ӓɑᛜ朱か = argv[0]
    if _nixon_み朌ӓɑᛜ朱か == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_み朌ӓɑᛜ朱か == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_み朌ӓɑᛜ朱か == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])