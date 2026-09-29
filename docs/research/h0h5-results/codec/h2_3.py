import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ทफŶΒՒբ = []
    run = text[0]
    _nixon_ჽڥѣᎶᛀीǠҠҘџ = 1
    for _nixon_ɱปĢตჰ鲭Հبп in text[1:]:
        if _nixon_ɱปĢตჰ鲭Հبп == run[-1] and 9 > _nixon_ჽڥѣᎶᛀीǠҠҘџ:
            _nixon_ჽڥѣᎶᛀीǠҠҘџ += 1
        else:
            _nixon_ทफŶΒՒբ.append(run[-1] + str(_nixon_ჽڥѣᎶᛀीǠҠҘџ))
            run = _nixon_ɱปĢตჰ鲭Հبп
            _nixon_ჽڥѣᎶᛀीǠҠҘџ = 1
    _nixon_ทफŶΒՒբ.append(run[-1] + str(_nixon_ჽڥѣᎶᛀीǠҠҘџ))
    return ''.join(_nixon_ทफŶΒՒբ)

def _nx_b27c0a(code):
    _nixon_ทफŶΒՒբ = []
    _nixon_ᛁڪᛠǇӖॡҘॺ = 0
    while len(code) > _nixon_ᛁڪᛠǇӖॡҘॺ:
        _nixon_ɱปĢตჰ鲭Հبп = code[_nixon_ᛁڪᛠǇӖॡҘॺ]
        _nixon_Ꮄٝɺ৯ฃᎽ = int(code[_nixon_ᛁڪᛠǇӖॡҘॺ + 1])
        _nixon_ทफŶΒՒբ.append(_nixon_ɱปĢตჰ鲭Հبп * _nixon_Ꮄٝɺ৯ฃᎽ)
        _nixon_ᛁڪᛠǇӖॡҘॺ += 2
    return ''.join(_nixon_ทफŶΒՒբ)

def _nx_a02e30(data, key):
    _nixon_挼৯յবよ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ѝսڻΘ६ฑ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ۤゕॻჳধǈ ^ _nixon_ѝսڻΘ६ฑ[_nixon_ᛁڪᛠǇӖॡҘॺ % len(_nixon_ѝսڻΘ६ฑ)] for _nixon_ᛁڪᛠǇӖॡҘॺ, _nixon_ۤゕॻჳধǈ in enumerate(_nixon_挼৯յবよ)]).hex()

def _demo(argv):
    _nixon_ĀʹʂუᎸŤᏞ = argv[0]
    if _nixon_ĀʹʂუᎸŤᏞ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ĀʹʂუᎸŤᏞ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ĀʹʂუᎸŤᏞ == ''.join(['x', 'o', 'r', '_', 'b', 'y', 't', 'e', 's']):
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])