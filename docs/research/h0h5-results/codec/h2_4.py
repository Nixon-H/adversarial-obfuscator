import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ডᛣʤҦևॽय़ΟƁ = []
    run = text[0]
    _nixon_ɑूלřן = 1
    for _nixon_ćპ棗ծΦ in text[1:]:
        if _nixon_ćპ棗ծΦ == run[-1] and 9 > _nixon_ɑूלřן:
            _nixon_ɑूלřן += 1
        else:
            _nixon_ডᛣʤҦևॽय़ΟƁ.append(run[-1] + str(_nixon_ɑूלřן))
            run = _nixon_ćპ棗ծΦ
            _nixon_ɑूלřן = 1
    _nixon_ডᛣʤҦևॽय़ΟƁ.append(run[-1] + str(_nixon_ɑूלřן))
    return ''.join(_nixon_ডᛣʤҦևॽय़ΟƁ)

def _nx_b27c0a(code):
    _nixon_ডᛣʤҦևॽय़ΟƁ = []
    _nixon_ह嗿ʣϋȘ = 0
    while _nixon_ह嗿ʣϋȘ < len(code):
        _nixon_ćპ棗ծΦ = code[_nixon_ह嗿ʣϋȘ]
        _nixon_Ⴔᚺڍঁი = int(code[_nixon_ह嗿ʣϋȘ + 1])
        _nixon_ডᛣʤҦևॽय़ΟƁ.append(_nixon_ćპ棗ծΦ * _nixon_Ⴔᚺڍঁი)
        _nixon_ह嗿ʣϋȘ += 2
    return ''.join(_nixon_ডᛣʤҦևॽय़ΟƁ)

def _nx_a02e30(data, key):
    _nixon_ीぁȩৃՏცŞȱуת = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ƌƨᚫॷᚠιʃɐת = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_پғϊҠႡ ^ _nixon_ƌƨᚫॷᚠιʃɐת[_nixon_ह嗿ʣϋȘ % len(_nixon_ƌƨᚫॷᚠιʃɐת)] for _nixon_ह嗿ʣϋȘ, _nixon_پғϊҠႡ in enumerate(_nixon_ीぁȩৃՏცŞȱуת)]).hex()

def _demo(argv):
    _nixon_תᚦ己ǫ僵ԾϮ = argv[0]
    if _nixon_תᚦ己ǫ僵ԾϮ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_תᚦ己ǫ僵ԾϮ == chr(114) + chr(108) + chr(101) + chr(95) + chr(100) + chr(101) + chr(99) + chr(111) + chr(100) + chr(101):
        print(_nx_b27c0a(argv[1]))
    elif _nixon_תᚦ己ǫ僵ԾϮ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == chr(95) + chr(95) + chr(109) + chr(97) + chr(105) + chr(110) + chr(95) + chr(95):
    _demo(sys.argv[1:])