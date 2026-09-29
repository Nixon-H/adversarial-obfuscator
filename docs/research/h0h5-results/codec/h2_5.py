import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_עđᎲԴ६ = []
    run = text[0]
    _nixon_صะূےɢחĪώ = 1
    for _nixon_ᎺǔՐۃξ臡ȽטᏭ in text[1:]:
        if _nixon_ᎺǔՐۃξ臡ȽטᏭ == run[-1] and 9 > _nixon_صะূےɢחĪώ:
            _nixon_صะূےɢחĪώ += 1
        else:
            _nixon_עđᎲԴ६.append(run[-1] + str(_nixon_صะূےɢחĪώ))
            run = _nixon_ᎺǔՐۃξ臡ȽטᏭ
            _nixon_صะূےɢחĪώ = 1
    _nixon_עđᎲԴ६.append(run[-1] + str(_nixon_صะূےɢחĪώ))
    return ''.join(_nixon_עđᎲԴ६)

def _nx_b27c0a(code):
    _nixon_עđᎲԴ६ = []
    _nixon_ǚそ囪ᛞᛅΩ萱 = 0
    while _nixon_ǚそ囪ᛞᛅΩ萱 < len(code):
        _nixon_ᎺǔՐۃξ臡ȽטᏭ = code[_nixon_ǚそ囪ᛞᛅΩ萱]
        _nixon_ϫͽฉכɲğ = int(code[_nixon_ǚそ囪ᛞᛅΩ萱 + 1])
        _nixon_עđᎲԴ६.append(_nixon_ᎺǔՐۃξ臡ȽטᏭ * _nixon_ϫͽฉכɲğ)
        _nixon_ǚそ囪ᛞᛅΩ萱 += 2 - 0
    return ''.join(_nixon_עđᎲԴ६)

def _nx_a02e30(data, key):
    _nixon_ই櫆ҧĂך = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ᏔЙĜᚸხᚤϰĞŪ璁 = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_תʖᎷঢ๔ ^ _nixon_ᏔЙĜᚸხᚤϰĞŪ璁[_nixon_ǚそ囪ᛞᛅΩ萱 % len(_nixon_ᏔЙĜᚸხᚤϰĞŪ璁)] for _nixon_ǚそ囪ᛞᛅΩ萱, _nixon_תʖᎷঢ๔ in enumerate(_nixon_ই櫆ҧĂך)]).hex()

def _demo(argv):
    _nixon_ॴͰᎮघǟ髮ǪႸΑȧ = argv[0]
    if _nixon_ॴͰᎮघǟ髮ǪႸΑȧ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ॴͰᎮघǟ髮ǪႸΑȧ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ॴͰᎮघǟ髮ǪႸΑȧ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print(chr(117) + chr(110) + chr(107) + chr(110) + chr(111) + chr(119) + chr(110) + chr(32) + chr(111) + chr(112))
if __name__ == '__main__':
    _demo(sys.argv[1:])