import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ŀ庁עېآᎢᏈǟՈ = []
    run = text[0]
    _nixon_Ꮀזʌזᚷ阍ॎőϝ = 1
    for _nixon_ʟѳぺॉǤǬג in text[1:]:
        if _nixon_ʟѳぺॉǤǬג == run[-1] and _nixon_Ꮀזʌזᚷ阍ॎőϝ < 9:
            _nixon_Ꮀזʌזᚷ阍ॎőϝ += 1
        else:
            _nixon_ŀ庁עېآᎢᏈǟՈ.append(run[-1] + str(_nixon_Ꮀזʌזᚷ阍ॎőϝ))
            run = _nixon_ʟѳぺॉǤǬג
            _nixon_Ꮀזʌזᚷ阍ॎőϝ = 1
    _nixon_ŀ庁עېآᎢᏈǟՈ.append(run[-1] + str(_nixon_Ꮀזʌזᚷ阍ॎőϝ))
    return ''.join(_nixon_ŀ庁עېآᎢᏈǟՈ)

def _nx_b27c0a(code):
    _nixon_ŀ庁עېآᎢᏈǟՈ = []
    _nixon_ɤדეぱɩႿᏍ郙 = 0
    while len(code) > _nixon_ɤדეぱɩႿᏍ郙:
        _nixon_ʟѳぺॉǤǬג = code[_nixon_ɤדეぱɩႿᏍ郙]
        _nixon_とǗॹ騼հ = int(code[_nixon_ɤדეぱɩႿᏍ郙 + 1])
        _nixon_ŀ庁עېآᎢᏈǟՈ.append(_nixon_ʟѳぺॉǤǬג * _nixon_とǗॹ騼հ)
        _nixon_ɤדეぱɩႿᏍ郙 += 2 + 0
    return ''.join(_nixon_ŀ庁עېآᎢᏈǟՈ)

def _nx_a02e30(data, key):
    _nixon_ᏳשᏟႤչცʦʍ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ูくᚱჶגᛘუや俩ฏ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ბᛐᛑेゆᏍʚ ^ _nixon_ูくᚱჶגᛘუや俩ฏ[_nixon_ɤדეぱɩႿᏍ郙 % len(_nixon_ูくᚱჶגᛘუや俩ฏ)] for _nixon_ɤדეぱɩႿᏍ郙, _nixon_ბᛐᛑेゆᏍʚ in enumerate(_nixon_ᏳשᏟႤչცʦʍ)]).hex()

def _demo(argv):
    _nixon_Ո্脶ঔΐ = argv[0]
    if _nixon_Ո্脶ঔΐ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_Ո্脶ঔΐ == ''.join(['r', 'l', 'e', '_', 'd', 'e', 'c', 'o', 'd', 'e']):
        print(_nx_b27c0a(argv[1]))
    elif _nixon_Ո্脶ঔΐ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])