import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ᛟฐКՆăदԱ = []
    run = text[0]
    _nixon_य़ᚱतشঌ = 1
    for _nixon_ึऍբณᛉূω০९ʹ in text[1:]:
        if _nixon_ึऍբณᛉূω০९ʹ == run[-1] and _nixon_य़ᚱतشঌ < 9:
            _nixon_य़ᚱतشঌ += 1
        else:
            _nixon_ᛟฐКՆăदԱ.append(run[-1] + str(_nixon_य़ᚱतشঌ))
            run = _nixon_ึऍբณᛉূω০९ʹ
            _nixon_य़ᚱतشঌ = 1
    _nixon_ᛟฐКՆăदԱ.append(run[-1] + str(_nixon_य़ᚱतشঌ))
    return ''.join(_nixon_ᛟฐКՆăदԱ)

def _nx_b27c0a(code):
    _nixon_ᛟฐКՆăदԱ = []
    _nixon_ঙৎقʐʩգყձ = 0
    while _nixon_ঙৎقʐʩգყձ < len(code):
        _nixon_ึऍբณᛉূω০९ʹ = code[_nixon_ঙৎقʐʩգყձ]
        _nixon_ইたよՠյ吾 = int(code[_nixon_ঙৎقʐʩգყձ + 1])
        _nixon_ᛟฐКՆăदԱ.append(_nixon_ึऍբณᛉূω০९ʹ * _nixon_ইたよՠյ吾)
        _nixon_ঙৎقʐʩգყձ += 2
    return ''.join(_nixon_ᛟฐКՆăदԱ)

def _nx_a02e30(data, key):
    _nixon_棩Ĳͽよ๗Ć = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_Ȍ憌דჟٷঃג = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ɞჵůѦŃึֆիɾध ^ _nixon_Ȍ憌דჟٷঃג[_nixon_ঙৎقʐʩգყձ % len(_nixon_Ȍ憌דჟٷঃג)] for _nixon_ঙৎقʐʩգყձ, _nixon_ɞჵůѦŃึֆիɾध in enumerate(_nixon_棩Ĳͽよ๗Ć)]).hex()

def _demo(argv):
    _nixon_ՐᏑでٻʃᏎۻᛇี = argv[0]
    if _nixon_ՐᏑでٻʃᏎۻᛇี == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ՐᏑでٻʃᏎۻᛇี == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ՐᏑでٻʃᏎۻᛇี == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])