import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_গ師άŨჀדʜ = []
    run = text[0]
    _nixon_ѤᎼʨՀऋえɎ = 1
    for _nixon_עʢӷႥ檑狺ᛅ in text[1:]:
        if _nixon_עʢӷႥ檑狺ᛅ == run[-1] and _nixon_ѤᎼʨՀऋえɎ < 9:
            _nixon_ѤᎼʨՀऋえɎ += 1
        else:
            _nixon_গ師άŨჀדʜ.append(run[-1] + str(_nixon_ѤᎼʨՀऋえɎ))
            run = _nixon_עʢӷႥ檑狺ᛅ
            _nixon_ѤᎼʨՀऋえɎ = 1
    _nixon_গ師άŨჀדʜ.append(run[-1] + str(_nixon_ѤᎼʨՀऋえɎ))
    return ''.join(_nixon_গ師άŨჀדʜ)

def _nx_b27c0a(code):
    _nixon_গ師άŨჀדʜ = []
    _nixon_যႰďƱȞր = 0
    while _nixon_যႰďƱȞր < len(code):
        _nixon_עʢӷႥ檑狺ᛅ = code[_nixon_যႰďƱȞր]
        _nixon_ϒ睐Ꮺগॸ = int(code[_nixon_যႰďƱȞր + 1])
        _nixon_গ師άŨჀדʜ.append(_nixon_עʢӷႥ檑狺ᛅ * _nixon_ϒ睐Ꮺগॸ)
        _nixon_যႰďƱȞր += 2
    return ''.join(_nixon_গ師άŨჀדʜ)

def _nx_a02e30(data, key):
    _nixon_ゆũחᛇऱԽɸぁ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ϠΨჟɚλぞǨ瞛 = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_स从ǕĖも ^ _nixon_ϠΨჟɚλぞǨ瞛[_nixon_যႰďƱȞր % len(_nixon_ϠΨჟɚλぞǨ瞛)] for _nixon_যႰďƱȞր, _nixon_स从ǕĖも in enumerate(_nixon_ゆũחᛇऱԽɸぁ)]).hex()

def _demo(argv):
    _nixon_նڴีՑぇϝʅ = argv[0]
    if _nixon_նڴีՑぇϝʅ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_նڴีՑぇϝʅ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_նڴีՑぇϝʅ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])