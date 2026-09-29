import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ȥჩᚼᚸךϝᛇᚥ = []
    run = text[0]
    _nixon_Ǝめ١ӌᛜьᏝぺŋ鋶 = 1
    for _nixon_Ꮞॿᛥٚɚ萎ӊलႿข in text[1:]:
        if _nixon_Ꮞॿᛥٚɚ萎ӊलႿข == run[-1] and _nixon_Ǝめ١ӌᛜьᏝぺŋ鋶 < 1 + 8:
            _nixon_Ǝめ١ӌᛜьᏝぺŋ鋶 += 1
        else:
            _nixon_ȥჩᚼᚸךϝᛇᚥ.append(run[-1] + str(_nixon_Ǝめ١ӌᛜьᏝぺŋ鋶))
            run = _nixon_Ꮞॿᛥٚɚ萎ӊलႿข
            _nixon_Ǝめ١ӌᛜьᏝぺŋ鋶 = 1
    _nixon_ȥჩᚼᚸךϝᛇᚥ.append(run[-1] + str(_nixon_Ǝめ١ӌᛜьᏝぺŋ鋶))
    return ''.join(_nixon_ȥჩᚼᚸךϝᛇᚥ)

def _nx_b27c0a(code):
    _nixon_ȥჩᚼᚸךϝᛇᚥ = []
    _nixon_३ĐʭĚふฌӐせŏ = 0
    while _nixon_३ĐʭĚふฌӐせŏ < len(code):
        _nixon_Ꮞॿᛥٚɚ萎ӊलႿข = code[_nixon_३ĐʭĚふฌӐせŏ]
        _nixon_琍ڴँʄᛝۃȮ = int(code[_nixon_३ĐʭĚふฌӐせŏ + 1])
        _nixon_ȥჩᚼᚸךϝᛇᚥ.append(_nixon_Ꮞॿᛥٚɚ萎ӊलႿข * _nixon_琍ڴँʄᛝۃȮ)
        _nixon_३ĐʭĚふฌӐせŏ += 2
    return ''.join(_nixon_ȥჩᚼᚸךϝᛇᚥ)

def _nx_a02e30(data, key):
    _nixon_০ॺდӖᚷʪৱȖ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ᏠקよจჍ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ć刿ϜבۣɳĉႠ ^ _nixon_ᏠקよจჍ[_nixon_३ĐʭĚふฌӐせŏ % len(_nixon_ᏠקよจჍ)] for _nixon_३ĐʭĚふฌӐせŏ, _nixon_ć刿ϜבۣɳĉႠ in enumerate(_nixon_০ॺდӖᚷʪৱȖ)]).hex()

def _demo(argv):
    _nixon_Ƹבłɮט栃ज = argv[0]
    if _nixon_Ƹבłɮט栃ज == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_Ƹבłɮט栃ज == ''.join(['r', 'l', 'e', '_', 'd', 'e', 'c', 'o', 'd', 'e']):
        print(_nx_b27c0a(argv[1]))
    elif _nixon_Ƹבłɮט栃ज == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])