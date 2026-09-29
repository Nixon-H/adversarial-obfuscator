import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ϰɪᚪʨŒჾęढॷȔ = []
    run = text[0]
    _nixon_בΤƃւতϭŎȱ = 1
    for _nixon_ҹƫҍϔ丘ĖᏘʞ in text[1:]:
        if _nixon_ҹƫҍϔ丘ĖᏘʞ == run[-1] and _nixon_בΤƃւতϭŎȱ < 9:
            _nixon_בΤƃւতϭŎȱ += 1
        else:
            _nixon_ϰɪᚪʨŒჾęढॷȔ.append(run[-1] + str(_nixon_בΤƃւতϭŎȱ))
            run = _nixon_ҹƫҍϔ丘ĖᏘʞ
            _nixon_בΤƃւতϭŎȱ = 1
    _nixon_ϰɪᚪʨŒჾęढॷȔ.append(run[-1] + str(_nixon_בΤƃւতϭŎȱ))
    return ''.join(_nixon_ϰɪᚪʨŒჾęढॷȔ)

def _nx_b27c0a(code):
    _nixon_ϰɪᚪʨŒჾęढॷȔ = []
    _nixon_١ঌᏅᎳᏗᎯʒᛩᏂ = 0
    while _nixon_١ঌᏅᎳᏗᎯʒᛩᏂ < len(code):
        _nixon_ҹƫҍϔ丘ĖᏘʞ = code[_nixon_١ঌᏅᎳᏗᎯʒᛩᏂ]
        _nixon_ᎶႤəѷᚢǯז = int(code[_nixon_١ঌᏅᎳᏗᎯʒᛩᏂ + 1])
        _nixon_ϰɪᚪʨŒჾęढॷȔ.append(_nixon_ҹƫҍϔ丘ĖᏘʞ * _nixon_ᎶႤəѷᚢǯז)
        _nixon_١ঌᏅᎳᏗᎯʒᛩᏂ += 2
    return ''.join(_nixon_ϰɪᚪʨŒჾęढॷȔ)

def _nx_a02e30(data, key):
    _nixon_٧ʒʇᎦᏉƽはʤ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ᛟΆȼฎभʎ८ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ү๑ოᏈϐۊ ^ _nixon_ᛟΆȼฎभʎ८[_nixon_١ঌᏅᎳᏗᎯʒᛩᏂ % len(_nixon_ᛟΆȼฎभʎ८)] for _nixon_١ঌᏅᎳᏗᎯʒᛩᏂ, _nixon_ү๑ოᏈϐۊ in enumerate(_nixon_٧ʒʇᎦᏉƽはʤ)]).hex()

def _demo(argv):
    _nixon_ŮเՌʬᏴ尬Ե = argv[0]
    if _nixon_ŮเՌʬᏴ尬Ե == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ŮเՌʬᏴ尬Ե == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ŮเՌʬᏴ尬Ե == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])