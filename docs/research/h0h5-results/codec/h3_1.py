import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_הŵփԷȗכ鰸 = []
    run = text[0]
    _nixon_ᛀठ优עႳ = 1
    for _nixon_Ϲ蜽էʏჇَ in text[1:]:
        if _nixon_Ϲ蜽էʏჇَ == run[-1] and _nixon_ᛀठ优עႳ < 9:
            _nixon_ᛀठ优עႳ += 1
        else:
            _nixon_הŵփԷȗכ鰸.append(run[-1] + str(_nixon_ᛀठ优עႳ))
            run = _nixon_Ϲ蜽էʏჇَ
            _nixon_ᛀठ优עႳ = 1
    _nixon_הŵփԷȗכ鰸.append(run[-1] + str(_nixon_ᛀठ优עႳ))
    return ''.join(_nixon_הŵփԷȗכ鰸)

def _nx_b27c0a(code):
    _nixon_הŵփԷȗכ鰸 = []
    _nixon_つ҅ĳįئজЁŦ = 0
    while _nixon_つ҅ĳįئজЁŦ < len(code):
        _nixon_Ϲ蜽էʏჇَ = code[_nixon_つ҅ĳįئজЁŦ]
        _nixon_ב喌ाեǻშʡ = int(code[_nixon_つ҅ĳįئজЁŦ + 1])
        _nixon_הŵփԷȗכ鰸.append(_nixon_Ϲ蜽էʏჇَ * _nixon_ב喌ाեǻშʡ)
        _nixon_つ҅ĳįئজЁŦ += 2
    return ''.join(_nixon_הŵփԷȗכ鰸)

def _nx_a02e30(data, key):
    _nixon_ƙঽʇƖҫႾī = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_შ揑ɄğɕŁկु = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ġҔĿցΔوՁēᛖॕ ^ _nixon_შ揑ɄğɕŁկु[_nixon_つ҅ĳįئজЁŦ % len(_nixon_შ揑ɄğɕŁկु)] for _nixon_つ҅ĳįئজЁŦ, _nixon_ġҔĿցΔوՁēᛖॕ in enumerate(_nixon_ƙঽʇƖҫႾī)]).hex()

def _demo(argv):
    _nixon_ृऎᚵᏄᚽ = argv[0]
    if _nixon_ृऎᚵᏄᚽ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ृऎᚵᏄᚽ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ृऎᚵᏄᚽ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])