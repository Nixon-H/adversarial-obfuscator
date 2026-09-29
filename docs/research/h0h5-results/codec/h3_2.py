import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ᚷ嚥צכԾ = []
    run = text[0]
    _nixon_פِᛅშგჭᚾᚥऋჿ = 1
    for _nixon_ɞযგŘঽЛѧ in text[1:]:
        if _nixon_ɞযგŘঽЛѧ == run[-1] and _nixon_פِᛅშგჭᚾᚥऋჿ < 9:
            _nixon_פِᛅშგჭᚾᚥऋჿ += 1
        else:
            _nixon_ᚷ嚥צכԾ.append(run[-1] + str(_nixon_פِᛅშგჭᚾᚥऋჿ))
            run = _nixon_ɞযგŘঽЛѧ
            _nixon_פِᛅშგჭᚾᚥऋჿ = 1
    _nixon_ᚷ嚥צכԾ.append(run[-1] + str(_nixon_פِᛅშგჭᚾᚥऋჿ))
    return ''.join(_nixon_ᚷ嚥צכԾ)

def _nx_b27c0a(code):
    _nixon_ᚷ嚥צכԾ = []
    _nixon_ᛜ็ΆՌড簗Ǳƭڧڰ = 0
    while _nixon_ᛜ็ΆՌড簗Ǳƭڧڰ < len(code):
        _nixon_ɞযგŘঽЛѧ = code[_nixon_ᛜ็ΆՌড簗Ǳƭڧڰ]
        _nixon_ৌ喺烞ฅᏛჽשЬ = int(code[_nixon_ᛜ็ΆՌড簗Ǳƭڧڰ + 1])
        _nixon_ᚷ嚥צכԾ.append(_nixon_ɞযგŘঽЛѧ * _nixon_ৌ喺烞ฅᏛჽשЬ)
        _nixon_ᛜ็ΆՌড簗Ǳƭڧڰ += 2
    return ''.join(_nixon_ᚷ嚥צכԾ)

def _nx_a02e30(data, key):
    _nixon_瓒Ꮅゖあɜদぶ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ȧฒѷƩφᏊӔিごअ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_दȞՆՆϢもが ^ _nixon_ȧฒѷƩφᏊӔিごअ[_nixon_ᛜ็ΆՌড簗Ǳƭڧڰ % len(_nixon_ȧฒѷƩφᏊӔিごअ)] for _nixon_ᛜ็ΆՌড簗Ǳƭڧڰ, _nixon_दȞՆՆϢもが in enumerate(_nixon_瓒Ꮅゖあɜদぶ)]).hex()

def _demo(argv):
    _nixon_য়ᚬւչАを = argv[0]
    if _nixon_য়ᚬւչАを == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_য়ᚬւչАを == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_য়ᚬւչАを == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])