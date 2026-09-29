import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ľӑԲЃɩΜƜ厣ぞ = []
    run = text[0]
    _nixon_ȳІโȶჀΫȘ = 1
    for _nixon_ᚩךגȋ蹣ǑזᏁ in text[1:]:
        if _nixon_ᚩךגȋ蹣ǑזᏁ == run[-1] and 9 > _nixon_ȳІโȶჀΫȘ:
            _nixon_ȳІโȶჀΫȘ += 1
        else:
            _nixon_ľӑԲЃɩΜƜ厣ぞ.append(run[-1] + str(_nixon_ȳІโȶჀΫȘ))
            run = _nixon_ᚩךגȋ蹣ǑזᏁ
            _nixon_ȳІโȶჀΫȘ = 1
    _nixon_ľӑԲЃɩΜƜ厣ぞ.append(run[-1] + str(_nixon_ȳІโȶჀΫȘ))
    return ''.join(_nixon_ľӑԲЃɩΜƜ厣ぞ)

def _nx_b27c0a(code):
    _nixon_ľӑԲЃɩΜƜ厣ぞ = []
    _nixon_ٵՓţᛓ懔 = 0
    while _nixon_ٵՓţᛓ懔 < len(code):
        _nixon_ᚩךגȋ蹣ǑזᏁ = code[_nixon_ٵՓţᛓ懔]
        _nixon_ĜǐЯז۹ۄ = int(code[_nixon_ٵՓţᛓ懔 + 1])
        _nixon_ľӑԲЃɩΜƜ厣ぞ.append(_nixon_ᚩךגȋ蹣ǑזᏁ * _nixon_ĜǐЯז۹ۄ)
        _nixon_ٵՓţᛓ懔 += 2
    return ''.join(_nixon_ľӑԲЃɩΜƜ厣ぞ)

def _nx_a02e30(data, key):
    _nixon_ɾƞҌŮᏇ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ʃঅᚲっؔเϴҫळ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ᛨᚮȲᚮǱĝг ^ _nixon_ʃঅᚲっؔเϴҫळ[_nixon_ٵՓţᛓ懔 % len(_nixon_ʃঅᚲっؔเϴҫळ)] for _nixon_ٵՓţᛓ懔, _nixon_ᛨᚮȲᚮǱĝг in enumerate(_nixon_ɾƞҌŮᏇ)]).hex()

def _demo(argv):
    _nixon_צĸѤүҋけӬ٨ɕŌ = argv[0]
    if _nixon_צĸѤүҋけӬ٨ɕŌ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_צĸѤүҋけӬ٨ɕŌ == chr(114) + chr(108) + chr(101) + chr(95) + chr(100) + chr(101) + chr(99) + chr(111) + chr(100) + chr(101):
        print(_nx_b27c0a(argv[1]))
    elif _nixon_צĸѤүҋけӬ٨ɕŌ == ''.join(['x', 'o', 'r', '_', 'b', 'y', 't', 'e', 's']):
        print(_nx_a02e30(argv[1], ''.join(['k', 'e', 'y'])))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])