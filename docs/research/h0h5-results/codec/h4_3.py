import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ॣǯēטखϯ鰹ش = []
    run = text[0]
    _nixon_იĸɇʦבँű = 1
    for _nixon_ɔॆʹৣӫٽटべ in text[1:]:
        if _nixon_ɔॆʹৣӫٽटべ == run[-1] and _nixon_იĸɇʦבँű < 9:
            _nixon_იĸɇʦבँű += 1
        else:
            _nixon_ॣǯēטखϯ鰹ش.append(run[-1] + str(_nixon_იĸɇʦבँű))
            run = _nixon_ɔॆʹৣӫٽटべ
            _nixon_იĸɇʦבँű = 1
    _nixon_ॣǯēטखϯ鰹ش.append(run[-1] + str(_nixon_იĸɇʦבँű))
    return ''.join(_nixon_ॣǯēטखϯ鰹ش)

def _nx_b27c0a(code):
    _nixon_ॣǯēטखϯ鰹ش = []
    _nixon_ךęᛅႿʆҘח্क़ॼ = 0
    while _nixon_ךęᛅႿʆҘח্क़ॼ < len(code):
        _nixon_ɔॆʹৣӫٽटべ = code[_nixon_ךęᛅႿʆҘח্क़ॼ]
        _nixon_Ζ爧ƥũ๓ = int(code[_nixon_ךęᛅႿʆҘח্क़ॼ + 1])
        _nixon_ॣǯēטखϯ鰹ش.append(_nixon_ɔॆʹৣӫٽटべ * _nixon_Ζ爧ƥũ๓)
        _nixon_ךęᛅႿʆҘח্क़ॼ += 2
    return ''.join(_nixon_ॣǯēטखϯ鰹ش)

def _nx_a02e30(data, key):
    _nixon_ჶखᚱᏊա = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ЁশυぽӱƻĢญ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_Ꮖհुףͼฺ็ ^ _nixon_ЁশυぽӱƻĢญ[_nixon_ךęᛅႿʆҘח্क़ॼ % len(_nixon_ЁশυぽӱƻĢญ)] for _nixon_ךęᛅႿʆҘח্क़ॼ, _nixon_Ꮖհुףͼฺ็ in enumerate(_nixon_ჶखᚱᏊա)]).hex()

def _demo(argv):
    _nixon_ᏆᚱũסিϺրϯȥ = argv[0]
    if _nixon_ᏆᚱũסিϺրϯȥ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ᏆᚱũסিϺրϯȥ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ᏆᚱũסিϺրϯȥ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])