import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ᚲڿȻךƫᚹʢҷҸף = []
    run = text[0]
    _nixon_ʔںӃ樽どŚႳ = 1
    for _nixon_螓যॖΡᎶゖᚥႢ۶ in text[1:]:
        if _nixon_螓যॖΡᎶゖᚥႢ۶ == run[-1] and _nixon_ʔںӃ樽どŚႳ < 9:
            _nixon_ʔںӃ樽どŚႳ += 1
        else:
            _nixon_ᚲڿȻךƫᚹʢҷҸף.append(run[-1] + str(_nixon_ʔںӃ樽どŚႳ))
            run = _nixon_螓যॖΡᎶゖᚥႢ۶
            _nixon_ʔںӃ樽どŚႳ = 1
    _nixon_ᚲڿȻךƫᚹʢҷҸף.append(run[-1] + str(_nixon_ʔںӃ樽どŚႳ))
    return ''.join(_nixon_ᚲڿȻךƫᚹʢҷҸף)

def _nx_b27c0a(code):
    _nixon_ᚲڿȻךƫᚹʢҷҸף = []
    _nixon_ইᛑŝתぉԴ = 0
    while _nixon_ইᛑŝתぉԴ < len(code):
        _nixon_螓যॖΡᎶゖᚥႢ۶ = code[_nixon_ইᛑŝתぉԴ]
        _nixon_Ꮏڻȡরゕか = int(code[_nixon_ইᛑŝתぉԴ + 1])
        _nixon_ᚲڿȻךƫᚹʢҷҸף.append(_nixon_螓যॖΡᎶゖᚥႢ۶ * _nixon_Ꮏڻȡরゕか)
        _nixon_ইᛑŝתぉԴ += 2
    return ''.join(_nixon_ᚲڿȻךƫᚹʢҷҸף)

def _nx_a02e30(data, key):
    _nixon_եטჟբ氐ჿվա = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ɖๅطᎤႬקЩڶğ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_قこȈ凟ずռ ^ _nixon_ɖๅطᎤႬקЩڶğ[_nixon_ইᛑŝתぉԴ % len(_nixon_ɖๅطᎤႬקЩڶğ)] for _nixon_ইᛑŝתぉԴ, _nixon_قこȈ凟ずռ in enumerate(_nixon_եטჟբ氐ჿվա)]).hex()

def _demo(argv):
    _nixon_ॖΗПʐॸ算Ⴆ = argv[0]
    if _nixon_ॖΗПʐॸ算Ⴆ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ॖΗПʐॸ算Ⴆ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ॖΗПʐॸ算Ⴆ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])