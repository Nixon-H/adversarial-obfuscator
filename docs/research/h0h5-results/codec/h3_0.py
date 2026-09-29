import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ผżαᎨぇড = []
    run = text[0]
    _nixon_ᚨडЖまעĐͿխș佄 = 1
    for _nixon_גӖϖᏊדぼτᎦԻᏝ in text[1:]:
        if _nixon_גӖϖᏊדぼτᎦԻᏝ == run[-1] and _nixon_ᚨडЖまעĐͿխș佄 < 9:
            _nixon_ᚨडЖまעĐͿխș佄 += 1
        else:
            _nixon_ผżαᎨぇড.append(run[-1] + str(_nixon_ᚨडЖまעĐͿխș佄))
            run = _nixon_גӖϖᏊדぼτᎦԻᏝ
            _nixon_ᚨडЖまעĐͿխș佄 = 1
    _nixon_ผżαᎨぇড.append(run[-1] + str(_nixon_ᚨडЖまעĐͿխș佄))
    return ''.join(_nixon_ผżαᎨぇড)

def _nx_b27c0a(code):
    _nixon_ผżαᎨぇড = []
    _nixon_փĤᛍᎼĢלѻԺևᛔ = 0
    while _nixon_փĤᛍᎼĢלѻԺևᛔ < len(code):
        _nixon_גӖϖᏊדぼτᎦԻᏝ = code[_nixon_փĤᛍᎼĢלѻԺևᛔ]
        _nixon_ɨԲΓקԼɽĨͻ = int(code[_nixon_փĤᛍᎼĢלѻԺևᛔ + 1])
        _nixon_ผżαᎨぇড.append(_nixon_גӖϖᏊדぼτᎦԻᏝ * _nixon_ɨԲΓקԼɽĨͻ)
        _nixon_փĤᛍᎼĢלѻԺևᛔ += 2
    return ''.join(_nixon_ผżαᎨぇড)

def _nx_a02e30(data, key):
    _nixon_իڱĥǭᛅɄ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ႻȾוᛡϧᚫغ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_լטჟᚼմ ^ _nixon_ႻȾוᛡϧᚫغ[_nixon_փĤᛍᎼĢלѻԺևᛔ % len(_nixon_ႻȾוᛡϧᚫغ)] for _nixon_փĤᛍᎼĢלѻԺևᛔ, _nixon_լטჟᚼմ in enumerate(_nixon_իڱĥǭᛅɄ)]).hex()

def _demo(argv):
    _nixon_৫ɼჴנほᏕѻ = argv[0]
    if _nixon_৫ɼჴנほᏕѻ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_৫ɼჴנほᏕѻ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_৫ɼჴנほᏕѻ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])