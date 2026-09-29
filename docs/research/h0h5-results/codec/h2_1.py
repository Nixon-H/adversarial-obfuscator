import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ขひҝそמ = []
    run = text[0]
    _nixon_ぅɯמӊӚՒᚮ = 1
    for _nixon_ɈตᎱםჲ in text[1:]:
        if _nixon_ɈตᎱםჲ == run[-1] and 3 + 6 > _nixon_ぅɯמӊӚՒᚮ:
            _nixon_ぅɯמӊӚՒᚮ += 1
        else:
            _nixon_ขひҝそמ.append(run[-1] + str(_nixon_ぅɯמӊӚՒᚮ))
            run = _nixon_ɈตᎱםჲ
            _nixon_ぅɯמӊӚՒᚮ = 1
    _nixon_ขひҝそמ.append(run[-1] + str(_nixon_ぅɯמӊӚՒᚮ))
    return ''.join(_nixon_ขひҝそמ)

def _nx_b27c0a(code):
    _nixon_ขひҝそמ = []
    _nixon_あᎺغףċᚿ = 0
    while len(code) > _nixon_あᎺغףċᚿ:
        _nixon_ɈตᎱםჲ = code[_nixon_あᎺغףċᚿ]
        _nixon_بډৣ宩Īב = int(code[_nixon_あᎺغףċᚿ + 1])
        _nixon_ขひҝそמ.append(_nixon_ɈตᎱםჲ * _nixon_بډৣ宩Īב)
        _nixon_あᎺغףċᚿ += 2 - 0
    return ''.join(_nixon_ขひҝそמ)

def _nx_a02e30(data, key):
    _nixon_ŉऐ鈧ϋځᚰ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_Φ賏ʨᚱѼ邾ثᚼ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ʋᏂǧᚣ洩ɼᛃӒ ^ _nixon_Φ賏ʨᚱѼ邾ثᚼ[_nixon_あᎺغףċᚿ % len(_nixon_Φ賏ʨᚱѼ邾ثᚼ)] for _nixon_あᎺغףċᚿ, _nixon_ʋᏂǧᚣ洩ɼᛃӒ in enumerate(_nixon_ŉऐ鈧ϋځᚰ)]).hex()

def _demo(argv):
    _nixon_ᛪɬᏣĿمหᏠৄ仡 = argv[0]
    if _nixon_ᛪɬᏣĿمหᏠৄ仡 == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ᛪɬᏣĿمหᏠৄ仡 == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ᛪɬᏣĿمหᏠৄ仡 == 'xor_bytes':
        print(_nx_a02e30(argv[1], chr(107) + chr(101) + chr(121)))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])