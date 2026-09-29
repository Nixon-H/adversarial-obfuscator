import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ᛤめѿҠĜॄিصɠ = []
    run = text[0]
    _nixon_ӴეᏫըƠĚ鄢ճ = 1
    for _nixon_きᎨֆФ瞎 in text[1:]:
        if _nixon_きᎨֆФ瞎 == run[-1] and 1 + 8 > _nixon_ӴეᏫըƠĚ鄢ճ:
            _nixon_ӴეᏫըƠĚ鄢ճ += 1
        else:
            _nixon_ᛤめѿҠĜॄিصɠ.append(run[-1] + str(_nixon_ӴეᏫըƠĚ鄢ճ))
            run = _nixon_きᎨֆФ瞎
            _nixon_ӴეᏫըƠĚ鄢ճ = 1
    _nixon_ᛤめѿҠĜॄিصɠ.append(run[-1] + str(_nixon_ӴეᏫըƠĚ鄢ճ))
    return ''.join(_nixon_ᛤめѿҠĜॄিصɠ)

def _nx_b27c0a(code):
    _nixon_ᛤめѿҠĜॄিصɠ = []
    _nixon_۴ʡĢՄᏉᚩȩʮ畣Ŭ = 0
    while len(code) > _nixon_۴ʡĢՄᏉᚩȩʮ畣Ŭ:
        _nixon_きᎨֆФ瞎 = code[_nixon_۴ʡĢՄᏉᚩȩʮ畣Ŭ]
        _nixon_ৢॆƢזउҊϵ = int(code[_nixon_۴ʡĢՄᏉᚩȩʮ畣Ŭ + 1])
        _nixon_ᛤめѿҠĜॄিصɠ.append(_nixon_きᎨֆФ瞎 * _nixon_ৢॆƢזउҊϵ)
        _nixon_۴ʡĢՄᏉᚩȩʮ畣Ŭ += 2
    return ''.join(_nixon_ᛤめѿҠĜॄিصɠ)

def _nx_a02e30(data, key):
    _nixon_ৣᛜӭᛋϹȅу = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ʏႯրङėזŦפ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_րᛤႲংყᏅჄۢิ ^ _nixon_ʏႯրङėזŦפ[_nixon_۴ʡĢՄᏉᚩȩʮ畣Ŭ % len(_nixon_ʏႯրङėזŦפ)] for _nixon_۴ʡĢՄᏉᚩȩʮ畣Ŭ, _nixon_րᛤႲংყᏅჄۢิ in enumerate(_nixon_ৣᛜӭᛋϹȅу)]).hex()

def _demo(argv):
    _nixon_ʠڂɫ艣ᛗ = argv[0]
    if _nixon_ʠڂɫ艣ᛗ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ʠڂɫ艣ᛗ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ʠڂɫ艣ᛗ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == chr(95) + chr(95) + chr(109) + chr(97) + chr(105) + chr(110) + chr(95) + chr(95):
    _demo(sys.argv[1:])