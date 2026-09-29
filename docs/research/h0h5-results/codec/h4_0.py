import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ჴɰζืՄȄ = []
    run = text[0]
    _nixon_ĉॖĒɽʀত榧ĄӢ = 1
    for _nixon_でչํჳđעᛞฤ in text[1:]:
        if _nixon_でչํჳđעᛞฤ == run[-1] and _nixon_ĉॖĒɽʀত榧ĄӢ < 9:
            _nixon_ĉॖĒɽʀত榧ĄӢ += 1
        else:
            _nixon_ჴɰζืՄȄ.append(run[-1] + str(_nixon_ĉॖĒɽʀত榧ĄӢ))
            run = _nixon_でչํჳđעᛞฤ
            _nixon_ĉॖĒɽʀত榧ĄӢ = 1
    _nixon_ჴɰζืՄȄ.append(run[-1] + str(_nixon_ĉॖĒɽʀত榧ĄӢ))
    return ''.join(_nixon_ჴɰζืՄȄ)

def _nx_b27c0a(code):
    _nixon_ჴɰζืՄȄ = []
    _nixon_ऱᛥყᚶ羄ȏشʢ = 0
    while _nixon_ऱᛥყᚶ羄ȏشʢ < len(code):
        _nixon_でչํჳđעᛞฤ = code[_nixon_ऱᛥყᚶ羄ȏشʢ]
        _nixon_ʅᚳʟႫӥぞĉ๓ぬภ = int(code[_nixon_ऱᛥყᚶ羄ȏشʢ + 1])
        _nixon_ჴɰζืՄȄ.append(_nixon_でչํჳđעᛞฤ * _nixon_ʅᚳʟႫӥぞĉ๓ぬภ)
        _nixon_ऱᛥყᚶ羄ȏشʢ += 2
    return ''.join(_nixon_ჴɰζืՄȄ)

def _nx_a02e30(data, key):
    _nixon_খ७す椮ϱ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_דুひৗ१のᎬ҅ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_恶ԻƕᏛʄॗᚭ ^ _nixon_דুひৗ१のᎬ҅[_nixon_ऱᛥყᚶ羄ȏشʢ % len(_nixon_דুひৗ१のᎬ҅)] for _nixon_ऱᛥყᚶ羄ȏشʢ, _nixon_恶ԻƕᏛʄॗᚭ in enumerate(_nixon_খ७す椮ϱ)]).hex()

def _demo(argv):
    _nixon_ڎǸᏏწڕ٧ = argv[0]
    if _nixon_ڎǸᏏწڕ٧ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ڎǸᏏწڕ٧ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ڎǸᏏწڕ٧ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])