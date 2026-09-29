import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_みԺ谊矔Յॲ۲ৄěᛤ = []
    run = text[0]
    _nixon_კʊএᚧɺЯŁ = 1
    for _nixon_ょ毸ج鑽҅ᛇ in text[1:]:
        if _nixon_ょ毸ج鑽҅ᛇ == run[-1] and _nixon_კʊএᚧɺЯŁ < 9:
            _nixon_კʊএᚧɺЯŁ += 1
        else:
            _nixon_みԺ谊矔Յॲ۲ৄěᛤ.append(run[-1] + str(_nixon_კʊএᚧɺЯŁ))
            run = _nixon_ょ毸ج鑽҅ᛇ
            _nixon_კʊএᚧɺЯŁ = 1
    _nixon_みԺ谊矔Յॲ۲ৄěᛤ.append(run[-1] + str(_nixon_კʊএᚧɺЯŁ))
    return ''.join(_nixon_みԺ谊矔Յॲ۲ৄěᛤ)

def _nx_b27c0a(code):
    _nixon_みԺ谊矔Յॲ۲ৄěᛤ = []
    _nixon_だ馭ӥڝლႱ = 0
    while _nixon_だ馭ӥڝლႱ < len(code):
        _nixon_ょ毸ج鑽҅ᛇ = code[_nixon_だ馭ӥڝლႱ]
        _nixon_骸ʡুρᏋ = int(code[_nixon_だ馭ӥڝლႱ + 1])
        _nixon_みԺ谊矔Յॲ۲ৄěᛤ.append(_nixon_ょ毸ج鑽҅ᛇ * _nixon_骸ʡুρᏋ)
        _nixon_だ馭ӥڝლႱ += 2
    return ''.join(_nixon_みԺ谊矔Յॲ۲ৄěᛤ)

def _nx_a02e30(data, key):
    _nixon_ҹշɕנᚯৠ酙Ⴍӣɺ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_Ժ॒ȉᛋႿせᛏ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ぃčʏճʙ ^ _nixon_Ժ॒ȉᛋႿせᛏ[_nixon_だ馭ӥڝლႱ % len(_nixon_Ժ॒ȉᛋႿせᛏ)] for _nixon_だ馭ӥڝლႱ, _nixon_ぃčʏճʙ in enumerate(_nixon_ҹշɕנᚯৠ酙Ⴍӣɺ)]).hex()

def _demo(argv):
    _nixon_Բংてőかᚳƹ = argv[0]
    if _nixon_Բংてőかᚳƹ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_Բংてőかᚳƹ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_Բংてőかᚳƹ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])