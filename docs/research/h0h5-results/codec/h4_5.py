import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_๎լॱऩҋ = []
    run = text[0]
    _nixon_Ꮓ茮ゆऩč绵 = 1
    for _nixon_৾ɷحぁ郡ॹר塴Ⴊ in text[1:]:
        if _nixon_৾ɷحぁ郡ॹר塴Ⴊ == run[-1] and _nixon_Ꮓ茮ゆऩč绵 < 9:
            _nixon_Ꮓ茮ゆऩč绵 += 1
        else:
            _nixon_๎լॱऩҋ.append(run[-1] + str(_nixon_Ꮓ茮ゆऩč绵))
            run = _nixon_৾ɷحぁ郡ॹר塴Ⴊ
            _nixon_Ꮓ茮ゆऩč绵 = 1
    _nixon_๎լॱऩҋ.append(run[-1] + str(_nixon_Ꮓ茮ゆऩč绵))
    return ''.join(_nixon_๎լॱऩҋ)

def _nx_b27c0a(code):
    _nixon_๎լॱऩҋ = []
    _nixon_Ƒ矮ϩʌ゚ = 0
    while _nixon_Ƒ矮ϩʌ゚ < len(code):
        _nixon_৾ɷحぁ郡ॹר塴Ⴊ = code[_nixon_Ƒ矮ϩʌ゚]
        _nixon_ᏈᛁסǹႮƶګΦ = int(code[_nixon_Ƒ矮ϩʌ゚ + 1])
        _nixon_๎լॱऩҋ.append(_nixon_৾ɷحぁ郡ॹר塴Ⴊ * _nixon_ᏈᛁסǹႮƶګΦ)
        _nixon_Ƒ矮ϩʌ゚ += 2
    return ''.join(_nixon_๎լॱऩҋ)

def _nx_a02e30(data, key):
    _nixon_حპϹু҇ʛႢ酷Ꮯჵ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ᏫζᛡɄᎯ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ۑήตᏍɷჟτ ^ _nixon_ᏫζᛡɄᎯ[_nixon_Ƒ矮ϩʌ゚ % len(_nixon_ᏫζᛡɄᎯ)] for _nixon_Ƒ矮ϩʌ゚, _nixon_ۑήตᏍɷჟτ in enumerate(_nixon_حპϹু҇ʛႢ酷Ꮯჵ)]).hex()

def _demo(argv):
    _nixon_ם睃ՋŦऩ = argv[0]
    if _nixon_ם睃ՋŦऩ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ם睃ՋŦऩ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ם睃ՋŦऩ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])