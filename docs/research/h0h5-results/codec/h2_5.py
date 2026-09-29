import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_āŵմΠזġΜᎳษʦ = []
    run = text[0]
    _nixon_ΰ惙ぴよΆזӘঔЕ০ = 1
    for _nixon_ǮѼঽ犁ƯŽɹըŢ in text[1:]:
        if _nixon_ǮѼঽ犁ƯŽɹըŢ == run[-1] and 11 - 2 > _nixon_ΰ惙ぴよΆזӘঔЕ০:
            _nixon_ΰ惙ぴよΆזӘঔЕ০ += 1
        else:
            _nixon_āŵմΠזġΜᎳษʦ.append(run[-1] + str(_nixon_ΰ惙ぴよΆזӘঔЕ০))
            run = _nixon_ǮѼঽ犁ƯŽɹըŢ
            _nixon_ΰ惙ぴよΆזӘঔЕ০ = 1
    _nixon_āŵմΠזġΜᎳษʦ.append(run[-1] + str(_nixon_ΰ惙ぴよΆזӘঔЕ০))
    return ''.join(_nixon_āŵմΠזġΜᎳษʦ)

def _nx_b27c0a(code):
    _nixon_āŵմΠזġΜᎳษʦ = []
    _nixon_žŻʑӻোᚤ閕Ᏹप = 0
    while _nixon_žŻʑӻোᚤ閕Ᏹप < len(code):
        _nixon_ǮѼঽ犁ƯŽɹըŢ = code[_nixon_žŻʑӻোᚤ閕Ᏹप]
        _nixon_ƱɪӑিŅבոऺჽ = int(code[_nixon_žŻʑӻোᚤ閕Ᏹप + 1])
        _nixon_āŵմΠזġΜᎳษʦ.append(_nixon_ǮѼঽ犁ƯŽɹըŢ * _nixon_ƱɪӑিŅבոऺჽ)
        _nixon_žŻʑӻোᚤ閕Ᏹप += 0 + 2
    return ''.join(_nixon_āŵմΠזġΜᎳษʦ)

def _nx_a02e30(data, key):
    _nixon_ɕᛡฉƜ擎ט = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ग़คႢرใ҃ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ʩึǂ鹞Ꭺώ ^ _nixon_ग़คႢرใ҃[_nixon_žŻʑӻোᚤ閕Ᏹप % len(_nixon_ग़คႢرใ҃)] for _nixon_žŻʑӻোᚤ閕Ᏹप, _nixon_ʩึǂ鹞Ꭺώ in enumerate(_nixon_ɕᛡฉƜ擎ט)]).hex()

def _demo(argv):
    _nixon_ผשą叭չĔѤ = argv[0]
    if _nixon_ผשą叭չĔѤ == chr(114) + chr(108) + chr(101) + chr(95) + chr(101) + chr(110) + chr(99) + chr(111) + chr(100) + chr(101):
        print(_nx_049ebf(argv[1]))
    elif _nixon_ผשą叭չĔѤ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ผשą叭չĔѤ == chr(120) + chr(111) + chr(114) + chr(95) + chr(98) + chr(121) + chr(116) + chr(101) + chr(115):
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])