import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_הऌؙǇֈϜでた = []
    run = text[0]
    _nixon_ϰ॑ӦϐǮצȿ = 1
    for _nixon_ΐᏘりঊٱᏗひ in text[1:]:
        if _nixon_ΐᏘりঊٱᏗひ == run[-1] and _nixon_ϰ॑ӦϐǮצȿ < 9:
            _nixon_ϰ॑ӦϐǮצȿ += 1
        else:
            _nixon_הऌؙǇֈϜでた.append(run[-1] + str(_nixon_ϰ॑ӦϐǮצȿ))
            run = _nixon_ΐᏘりঊٱᏗひ
            _nixon_ϰ॑ӦϐǮצȿ = 1
    _nixon_הऌؙǇֈϜでた.append(run[-1] + str(_nixon_ϰ॑ӦϐǮצȿ))
    return ''.join(_nixon_הऌؙǇֈϜでた)

def _nx_b27c0a(code):
    _nixon_הऌؙǇֈϜでた = []
    _nixon_ʕĄϛےूႯґᛥく = 0
    while _nixon_ʕĄϛےूႯґᛥく < len(code):
        _nixon_ΐᏘりঊٱᏗひ = code[_nixon_ʕĄϛےूႯґᛥく]
        _nixon_Ꮮե朅ɒוΝѱ = int(code[_nixon_ʕĄϛےूႯґᛥく + 1])
        _nixon_הऌؙǇֈϜでた.append(_nixon_ΐᏘりঊٱᏗひ * _nixon_Ꮮե朅ɒוΝѱ)
        _nixon_ʕĄϛےूႯґᛥく += 2
    return ''.join(_nixon_הऌؙǇֈϜでた)

def _nx_a02e30(data, key):
    _nixon_ऊפৗᏏ৩ξ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ΤᏎ১ęᚦ柁 = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ƨהʂڞปॐ ^ _nixon_ΤᏎ১ęᚦ柁[_nixon_ʕĄϛےूႯґᛥく % len(_nixon_ΤᏎ১ęᚦ柁)] for _nixon_ʕĄϛےूႯґᛥく, _nixon_ƨהʂڞปॐ in enumerate(_nixon_ऊפৗᏏ৩ξ)]).hex()

def _demo(argv):
    _nixon_Šჺᛙᚾหխѥʬɳچ = argv[0]
    if _nixon_Šჺᛙᚾหխѥʬɳچ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_Šჺᛙᚾหխѥʬɳچ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_Šჺᛙᚾหխѥʬɳچ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])