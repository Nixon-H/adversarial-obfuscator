import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ȃڨせל৭طႭ = []
    run = text[0]
    _nixon_দؐწ緤მ櫉ۦڗ = 1
    for _nixon_შูЫいᎶ in text[1:]:
        if _nixon_შูЫいᎶ == run[-1] and _nixon_দؐწ緤მ櫉ۦڗ < 9:
            _nixon_দؐწ緤მ櫉ۦڗ += 1
        else:
            _nixon_ȃڨせל৭طႭ.append(run[-1] + str(_nixon_দؐწ緤მ櫉ۦڗ))
            run = _nixon_შูЫいᎶ
            _nixon_দؐწ緤მ櫉ۦڗ = 1
    _nixon_ȃڨせל৭طႭ.append(run[-1] + str(_nixon_দؐწ緤მ櫉ۦڗ))
    return ''.join(_nixon_ȃڨせל৭طႭ)

def _nx_b27c0a(code):
    _nixon_ȃڨせל৭طႭ = []
    _nixon_პঝգๅ響ř = 0
    while _nixon_პঝգๅ響ř < len(code):
        _nixon_შูЫいᎶ = code[_nixon_პঝգๅ響ř]
        _nixon_ฤءӭงךᛧՇᏒՙฯ = int(code[_nixon_პঝգๅ響ř + 1])
        _nixon_ȃڨせל৭طႭ.append(_nixon_შูЫいᎶ * _nixon_ฤءӭงךᛧՇᏒՙฯ)
        _nixon_პঝգๅ響ř += sum([1, 1])
    return ''.join(_nixon_ȃڨせל৭طႭ)

def _nx_a02e30(data, key):
    _nixon_ᛇѪᛧĻĭՑ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ЈᏈրϓれो = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ყֆĒɚלڎשϝᛉ ^ _nixon_ЈᏈրϓれो[_nixon_პঝգๅ響ř % len(_nixon_ЈᏈրϓれो)] for _nixon_პঝգๅ響ř, _nixon_ყֆĒɚלڎשϝᛉ in enumerate(_nixon_ᛇѪᛧĻĭՑ)]).hex()

def _demo(argv):
    _nixon_砢ښΣぷĮႵ = argv[0]
    if _nixon_砢ښΣぷĮႵ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_砢ښΣぷĮႵ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_砢ښΣぷĮႵ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])