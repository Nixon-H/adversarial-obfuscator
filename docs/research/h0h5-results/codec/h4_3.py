import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_゙ᏭϝɵᎵʊȒぴ = []
    run = text[0]
    _nixon_邬ƘႫᚩগばΗ = 1
    for _nixon_בסงȬにওբҏग़ȿ in text[1:]:
        if _nixon_בסงȬにওբҏग़ȿ == run[-1] and _nixon_邬ƘႫᚩগばΗ < 9:
            _nixon_邬ƘႫᚩগばΗ += 1
        else:
            _nixon_゙ᏭϝɵᎵʊȒぴ.append(run[-1] + str(_nixon_邬ƘႫᚩগばΗ))
            run = _nixon_בסงȬにওբҏग़ȿ
            _nixon_邬ƘႫᚩগばΗ = 1
    _nixon_゙ᏭϝɵᎵʊȒぴ.append(run[-1] + str(_nixon_邬ƘႫᚩগばΗ))
    return ''.join(_nixon_゙ᏭϝɵᎵʊȒぴ)

def _nx_b27c0a(code):
    _nixon_゙ᏭϝɵᎵʊȒぴ = []
    _nixon_ŨסᛚלļҰյ = 0
    while _nixon_ŨסᛚלļҰյ < len(code):
        _nixon_בסงȬにওբҏग़ȿ = code[_nixon_ŨסᛚלļҰյ]
        _nixon_ᚫᛉēთȾ纀Čѿई傞 = int(code[_nixon_ŨסᛚלļҰյ + 1])
        _nixon_゙ᏭϝɵᎵʊȒぴ.append(_nixon_בסงȬにওբҏग़ȿ * _nixon_ᚫᛉēთȾ纀Čѿई傞)
        _nixon_ŨסᛚלļҰյ += 2
    return ''.join(_nixon_゙ᏭϝɵᎵʊȒぴ)

def _nx_a02e30(data, key):
    _nixon_禘ᏢρŻพžᏚ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_մすĂؑǷʞքאᛊЪ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ปנᚥᚰןγ ^ _nixon_մすĂؑǷʞքאᛊЪ[_nixon_ŨסᛚלļҰյ % len(_nixon_մすĂؑǷʞքאᛊЪ)] for _nixon_ŨסᛚלļҰյ, _nixon_ปנᚥᚰןγ in enumerate(_nixon_禘ᏢρŻพžᏚ)]).hex()

def _demo(argv):
    _nixon_มƐॉᛓɦոŅאკ = argv[0]
    if _nixon_มƐॉᛓɦոŅאკ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_มƐॉᛓɦոŅאკ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_มƐॉᛓɦոŅאკ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])