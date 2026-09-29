import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ᛏדĵჽ゚יՖりϟᚫ = []
    run = text[0]
    _nixon_ѭᏰれॹᏏ = 1
    for _nixon_ێε矒ǍȔɗ in text[1:]:
        if _nixon_ێε矒ǍȔɗ == run[-1] and _nixon_ѭᏰれॹᏏ < 9:
            _nixon_ѭᏰれॹᏏ += 1
        else:
            _nixon_ᛏדĵჽ゚יՖりϟᚫ.append(run[-1] + str(_nixon_ѭᏰれॹᏏ))
            run = _nixon_ێε矒ǍȔɗ
            _nixon_ѭᏰれॹᏏ = 1
    _nixon_ᛏדĵჽ゚יՖりϟᚫ.append(run[-1] + str(_nixon_ѭᏰれॹᏏ))
    return ''.join(_nixon_ᛏדĵჽ゚יՖりϟᚫ)

def _nx_b27c0a(code):
    _nixon_ᛏדĵჽ゚יՖりϟᚫ = []
    _nixon_ওृןځ猨Թ = 0
    while _nixon_ওृןځ猨Թ < len(code):
        _nixon_ێε矒ǍȔɗ = code[_nixon_ওृןځ猨Թ]
        _nixon_ͽइʒŀᛊڮৃぃ磦 = int(code[_nixon_ওृןځ猨Թ + 1])
        _nixon_ᛏדĵჽ゚יՖりϟᚫ.append(_nixon_ێε矒ǍȔɗ * _nixon_ͽइʒŀᛊڮৃぃ磦)
        _nixon_ওृןځ猨Թ += 2
    return ''.join(_nixon_ᛏדĵჽ゚יՖりϟᚫ)

def _nx_a02e30(data, key):
    _nixon_ʖঃの裢ն = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ӱۤԵӠדİᚿ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ৡϨђৡॱऊɵօお ^ _nixon_ӱۤԵӠדİᚿ[_nixon_ওृןځ猨Թ % len(_nixon_ӱۤԵӠדİᚿ)] for _nixon_ওृןځ猨Թ, _nixon_ৡϨђৡॱऊɵօお in enumerate(_nixon_ʖঃの裢ն)]).hex()

def _demo(argv):
    _nixon_棬טϸמ゙ᚿלჰ = argv[0]
    if _nixon_棬טϸמ゙ᚿלჰ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_棬טϸמ゙ᚿלჰ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_棬טϸמ゙ᚿלჰ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])