import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ᚲ۵蔶শĬึᏧい = []
    run = text[0]
    _nixon_ղňᛧᛙるΥ = 1
    for _nixon_ԺϳႬᎪᏎĘϻƾ in text[1:]:
        if _nixon_ԺϳႬᎪᏎĘϻƾ == run[-1] and _nixon_ղňᛧᛙるΥ < 9:
            _nixon_ղňᛧᛙるΥ += 1
        else:
            _nixon_ᚲ۵蔶শĬึᏧい.append(run[-1] + str(_nixon_ղňᛧᛙるΥ))
            run = _nixon_ԺϳႬᎪᏎĘϻƾ
            _nixon_ղňᛧᛙるΥ = 1
    _nixon_ᚲ۵蔶শĬึᏧい.append(run[-1] + str(_nixon_ղňᛧᛙるΥ))
    return ''.join(_nixon_ᚲ۵蔶শĬึᏧい)

def _nx_b27c0a(code):
    _nixon_ᚲ۵蔶শĬึᏧい = []
    _nixon_ჷ氿उۤטჸ = 0
    while _nixon_ჷ氿उۤטჸ < len(code):
        _nixon_ԺϳႬᎪᏎĘϻƾ = code[_nixon_ჷ氿उۤטჸ]
        _nixon_Ⴚ८ᛇΩĎĲϰ = int(code[_nixon_ჷ氿उۤטჸ + 1])
        _nixon_ᚲ۵蔶শĬึᏧい.append(_nixon_ԺϳႬᎪᏎĘϻƾ * _nixon_Ⴚ८ᛇΩĎĲϰ)
        _nixon_ჷ氿उۤטჸ += 2
    return ''.join(_nixon_ᚲ۵蔶শĬึᏧい)

def _nx_a02e30(data, key):
    _nixon_ঐॡϧŧٌτՁ๑Խ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_৾ざףᛌʚछȻᏈۭ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ΦႯӳגႫ ^ _nixon_৾ざףᛌʚछȻᏈۭ[_nixon_ჷ氿उۤטჸ % len(_nixon_৾ざףᛌʚछȻᏈۭ)] for _nixon_ჷ氿उۤטჸ, _nixon_ΦႯӳגႫ in enumerate(_nixon_ঐॡϧŧٌτՁ๑Խ)]).hex()

def _demo(argv):
    _nixon_Ũᚱט۶խĘᛙĒ猑戄 = argv[0]
    if _nixon_Ũᚱט۶խĘᛙĒ猑戄 == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_Ũᚱט۶խĘᛙĒ猑戄 == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_Ũᚱט۶խĘᛙĒ猑戄 == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])