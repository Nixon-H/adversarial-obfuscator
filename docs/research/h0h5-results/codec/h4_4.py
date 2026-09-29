import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ॄǤლЄᚡढᏎ = []
    run = text[0]
    _nixon_Ū沖մҢٽᚢ = 1
    for _nixon_уいʩוნみฮᏤǰ in text[1:]:
        if _nixon_уいʩוნみฮᏤǰ == run[-1] and _nixon_Ū沖մҢٽᚢ < 9:
            _nixon_Ū沖մҢٽᚢ += 1
        else:
            _nixon_ॄǤლЄᚡढᏎ.append(run[-1] + str(_nixon_Ū沖մҢٽᚢ))
            run = _nixon_уいʩוნみฮᏤǰ
            _nixon_Ū沖մҢٽᚢ = 1
    _nixon_ॄǤლЄᚡढᏎ.append(run[-1] + str(_nixon_Ū沖մҢٽᚢ))
    return ''.join(_nixon_ॄǤლЄᚡढᏎ)

def _nx_b27c0a(code):
    _nixon_ॄǤლЄᚡढᏎ = []
    _nixon_Ūǩ痔ČϏजʀᛏᚻɳ = 0
    while _nixon_Ūǩ痔ČϏजʀᛏᚻɳ < len(code):
        _nixon_уいʩוნみฮᏤǰ = code[_nixon_Ūǩ痔ČϏजʀᛏᚻɳ]
        _nixon_ՋすᛤɡᛓՂՊՀ = int(code[_nixon_Ūǩ痔ČϏजʀᛏᚻɳ + 1])
        _nixon_ॄǤლЄᚡढᏎ.append(_nixon_уいʩוნみฮᏤǰ * _nixon_ՋすᛤɡᛓՂՊՀ)
        _nixon_Ūǩ痔ČϏजʀᛏᚻɳ += 2
    return ''.join(_nixon_ॄǤლЄᚡढᏎ)

def _nx_a02e30(data, key):
    _nixon_ᏀגԾǕดȦ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_やᚦѻ়Ӳɷʜᛀʨ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_टĔᎸؚٟפ ^ _nixon_やᚦѻ়Ӳɷʜᛀʨ[_nixon_Ūǩ痔ČϏजʀᛏᚻɳ % len(_nixon_やᚦѻ়Ӳɷʜᛀʨ)] for _nixon_Ūǩ痔ČϏजʀᛏᚻɳ, _nixon_टĔᎸؚٟפ in enumerate(_nixon_ᏀגԾǕดȦ)]).hex()

def _demo(argv):
    _nixon_חɫϒνचც嫴ה = argv[0]
    if _nixon_חɫϒνचც嫴ה == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_חɫϒνचც嫴ה == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_חɫϒνचც嫴ה == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])