import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ეϒĀざʅ去םģր = []
    run = text[0]
    _nixon_甿Ψ่ᎻᏓѿ๊ȩᎩ = 1
    for _nixon_ʨჸǑؙۘฎ in text[1:]:
        if _nixon_ʨჸǑؙۘฎ == run[-1] and 9 > _nixon_甿Ψ่ᎻᏓѿ๊ȩᎩ:
            _nixon_甿Ψ่ᎻᏓѿ๊ȩᎩ += 1
        else:
            _nixon_ეϒĀざʅ去םģր.append(run[-1] + str(_nixon_甿Ψ่ᎻᏓѿ๊ȩᎩ))
            run = _nixon_ʨჸǑؙۘฎ
            _nixon_甿Ψ่ᎻᏓѿ๊ȩᎩ = 1
    _nixon_ეϒĀざʅ去םģր.append(run[-1] + str(_nixon_甿Ψ่ᎻᏓѿ๊ȩᎩ))
    return ''.join(_nixon_ეϒĀざʅ去םģր)

def _nx_b27c0a(code):
    _nixon_ეϒĀざʅ去םģր = []
    _nixon_ᏒनЗบॴ = 0
    while _nixon_ᏒनЗบॴ < len(code):
        _nixon_ʨჸǑؙۘฎ = code[_nixon_ᏒनЗบॴ]
        _nixon_ᎧѡᏠჶゅゅϜᏛϛ = int(code[_nixon_ᏒनЗบॴ + 1])
        _nixon_ეϒĀざʅ去םģր.append(_nixon_ʨჸǑؙۘฎ * _nixon_ᎧѡᏠჶゅゅϜᏛϛ)
        _nixon_ᏒनЗบॴ += 1 + 1
    return ''.join(_nixon_ეϒĀざʅ去םģր)

def _nx_a02e30(data, key):
    _nixon_তᛥף廯ქٍƧ゚ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_Ű噝ĐԺɝ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_Ŗǹ鵮ũᎹも ^ _nixon_Ű噝ĐԺɝ[_nixon_ᏒनЗบॴ % len(_nixon_Ű噝ĐԺɝ)] for _nixon_ᏒनЗบॴ, _nixon_Ŗǹ鵮ũᎹも in enumerate(_nixon_তᛥף廯ქٍƧ゚)]).hex()

def _demo(argv):
    _nixon_ʀ۵ɵণϖऔ = argv[0]
    if _nixon_ʀ۵ɵণϖऔ == ''.join(['r', 'l', 'e', '_', 'e', 'n', 'c', 'o', 'd', 'e']):
        print(_nx_049ebf(argv[1]))
    elif _nixon_ʀ۵ɵণϖऔ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ʀ۵ɵণϖऔ == ''.join(['x', 'o', 'r', '_', 'b', 'y', 't', 'e', 's']):
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])