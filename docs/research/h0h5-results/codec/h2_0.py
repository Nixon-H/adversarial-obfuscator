import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ねӗсٕȺোႦॗԵѕ = []
    run = text[0]
    _nixon_Ǘ濤ǿαटำзʀᚻႰ = 1
    for _nixon_ᏑᏲᛙȔسΘঋФǖɫ in text[1:]:
        if _nixon_ᏑᏲᛙȔسΘঋФǖɫ == run[-1] and _nixon_Ǘ濤ǿαटำзʀᚻႰ < 15 - 6:
            _nixon_Ǘ濤ǿαटำзʀᚻႰ += 1
        else:
            _nixon_ねӗсٕȺোႦॗԵѕ.append(run[-1] + str(_nixon_Ǘ濤ǿαटำзʀᚻႰ))
            run = _nixon_ᏑᏲᛙȔسΘঋФǖɫ
            _nixon_Ǘ濤ǿαटำзʀᚻႰ = 1
    _nixon_ねӗсٕȺোႦॗԵѕ.append(run[-1] + str(_nixon_Ǘ濤ǿαटำзʀᚻႰ))
    return ''.join(_nixon_ねӗсٕȺোႦॗԵѕ)

def _nx_b27c0a(code):
    _nixon_ねӗсٕȺোႦॗԵѕ = []
    _nixon_ᛣŲɳႨॆו = 0
    while _nixon_ᛣŲɳႨॆו < len(code):
        _nixon_ᏑᏲᛙȔسΘঋФǖɫ = code[_nixon_ᛣŲɳႨॆו]
        _nixon_ჯՅএごם = int(code[_nixon_ᛣŲɳႨॆו + 1])
        _nixon_ねӗсٕȺোႦॗԵѕ.append(_nixon_ᏑᏲᛙȔسΘঋФǖɫ * _nixon_ჯՅএごם)
        _nixon_ᛣŲɳႨॆו += 2
    return ''.join(_nixon_ねӗсٕȺোႦॗԵѕ)

def _nx_a02e30(data, key):
    _nixon_ƣͽᏀונь = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_Ꮌてה๓զ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_תთƠみל ^ _nixon_Ꮌてה๓զ[_nixon_ᛣŲɳႨॆו % len(_nixon_Ꮌてה๓զ)] for _nixon_ᛣŲɳႨॆו, _nixon_תთƠみל in enumerate(_nixon_ƣͽᏀונь)]).hex()

def _demo(argv):
    _nixon_ȧেოфţふƞ = argv[0]
    if _nixon_ȧেოфţふƞ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ȧেოфţふƞ == chr(114) + chr(108) + chr(101) + chr(95) + chr(100) + chr(101) + chr(99) + chr(111) + chr(100) + chr(101):
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ȧেოфţふƞ == 'xor_bytes':
        print(_nx_a02e30(argv[1], chr(107) + chr(101) + chr(121)))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == '__main__':
    _demo(sys.argv[1:])