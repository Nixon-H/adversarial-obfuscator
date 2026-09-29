import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ןवʑᎩ霨 = []
    run = text[0]
    _nixon_վזᎣस্ںǌझ = 1
    for _nixon_ᛄוק़κ๖েᛃ绖 in text[1:]:
        if _nixon_ᛄוק़κ๖েᛃ绖 == run[-1] and _nixon_վזᎣस্ںǌझ < 9:
            _nixon_վזᎣस্ںǌझ += 1
        else:
            _nixon_ןवʑᎩ霨.append(run[-1] + str(_nixon_վזᎣस্ںǌझ))
            run = _nixon_ᛄוק़κ๖েᛃ绖
            _nixon_վזᎣस্ںǌझ = 1
    _nixon_ןवʑᎩ霨.append(run[-1] + str(_nixon_վזᎣस্ںǌझ))
    return ''.join(_nixon_ןवʑᎩ霨)

def _nx_b27c0a(code):
    _nixon_ןवʑᎩ霨 = []
    _nixon_ठТᚻūむךՏր这Ȭ = 0
    while _nixon_ठТᚻūむךՏր这Ȭ < len(code):
        _nixon_ᛄוק़κ๖েᛃ绖 = code[_nixon_ठТᚻūむךՏր这Ȭ]
        _nixon_εᛥǰχ蕃はჿ = int(code[_nixon_ठТᚻūむךՏր这Ȭ + 1])
        _nixon_ןवʑᎩ霨.append(_nixon_ᛄוק़κ๖েᛃ绖 * _nixon_εᛥǰχ蕃はჿ)
        _nixon_ठТᚻūむךՏր这Ȭ += 2
    return ''.join(_nixon_ןवʑᎩ霨)

def _nx_a02e30(data, key):
    _nixon_ןᏊƭฝؐ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ᛏႮѣीৌ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ᛝɒञȸ櫖 ^ _nixon_ᛏႮѣीৌ[_nixon_ठТᚻūむךՏր这Ȭ % len(_nixon_ᛏႮѣीৌ)] for _nixon_ठТᚻūむךՏր这Ȭ, _nixon_ᛝɒञȸ櫖 in enumerate(_nixon_ןᏊƭฝؐ)]).hex()

def _demo(argv):
    _nixon_҄こᎵןճب餮 = argv[0]
    if _nixon_҄こᎵןճب餮 == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_҄こᎵןճب餮 == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_҄こᎵןճب餮 == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])