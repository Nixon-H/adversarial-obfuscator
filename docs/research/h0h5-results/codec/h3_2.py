import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_כբվǠɩ勖ٵ = []
    run = text[0]
    _nixon_Ⴋᚲטۤᛊ峵ᛋႪ = 1
    for _nixon_ϳ勒ՙמॕإᏟᏗ in text[1:]:
        if _nixon_ϳ勒ՙמॕإᏟᏗ == run[-1] and _nixon_Ⴋᚲטۤᛊ峵ᛋႪ < 9:
            _nixon_Ⴋᚲטۤᛊ峵ᛋႪ += 1
        else:
            _nixon_כբվǠɩ勖ٵ.append(run[-1] + str(_nixon_Ⴋᚲטۤᛊ峵ᛋႪ))
            run = _nixon_ϳ勒ՙמॕإᏟᏗ
            _nixon_Ⴋᚲטۤᛊ峵ᛋႪ = 1
    _nixon_כբվǠɩ勖ٵ.append(run[-1] + str(_nixon_Ⴋᚲטۤᛊ峵ᛋႪ))
    return ''.join(_nixon_כբվǠɩ勖ٵ)

def _nx_b27c0a(code):
    _nixon_כբվǠɩ勖ٵ = []
    _nixon_ზᛏ幀ɾびႸᎰ刳ɺ = 0
    while _nixon_ზᛏ幀ɾびႸᎰ刳ɺ < len(code):
        _nixon_ϳ勒ՙמॕإᏟᏗ = code[_nixon_ზᛏ幀ɾびႸᎰ刳ɺ]
        _nixon_ұղעʢᎵԽƵΑᏠぅ = int(code[_nixon_ზᛏ幀ɾびႸᎰ刳ɺ + 1])
        _nixon_כբվǠɩ勖ٵ.append(_nixon_ϳ勒ՙמॕإᏟᏗ * _nixon_ұղעʢᎵԽƵΑᏠぅ)
        _nixon_ზᛏ幀ɾびႸᎰ刳ɺ += 2
    return ''.join(_nixon_כբվǠɩ勖ٵ)

def _nx_a02e30(data, key):
    _nixon_ƼŝȎᏠทの = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ȩʠปտᛖŋۊञ鵣 = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_鈋ƃʘʎēᛀɀᏕᏲゅ ^ _nixon_ȩʠปտᛖŋۊञ鵣[_nixon_ზᛏ幀ɾびႸᎰ刳ɺ % len(_nixon_ȩʠปտᛖŋۊञ鵣)] for _nixon_ზᛏ幀ɾびႸᎰ刳ɺ, _nixon_鈋ƃʘʎēᛀɀᏕᏲゅ in enumerate(_nixon_ƼŝȎᏠทの)]).hex()

def _demo(argv):
    _nixon_ํ駖Ͳզל = argv[0]
    if _nixon_ํ駖Ͳզל == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ํ駖Ͳզל == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ํ駖Ͳզל == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])