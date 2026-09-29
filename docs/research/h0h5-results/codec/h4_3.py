import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ঢϒॵぶЬž = []
    run = text[0]
    _nixon_ԶתńτשϜ = 1
    for _nixon_ʢじɩ曽๓შः in text[1:]:
        if _nixon_ʢじɩ曽๓შः == run[-1] and _nixon_ԶתńτשϜ < 9:
            _nixon_ԶתńτשϜ += 1
        else:
            _nixon_ঢϒॵぶЬž.append(run[-1] + str(_nixon_ԶתńτשϜ))
            run = _nixon_ʢじɩ曽๓შः
            _nixon_ԶתńτשϜ = 1
    _nixon_ঢϒॵぶЬž.append(run[-1] + str(_nixon_ԶתńτשϜ))
    return ''.join(_nixon_ঢϒॵぶЬž)

def _nx_b27c0a(code):
    _nixon_ঢϒॵぶЬž = []
    _nixon_θबĉᚴย屮嶝 = 0
    while _nixon_θबĉᚴย屮嶝 < len(code):
        _nixon_ʢじɩ曽๓შः = code[_nixon_θबĉᚴย屮嶝]
        _nixon_პႵŨფճ蚃Ơ҃ = int(code[_nixon_θबĉᚴย屮嶝 + 1])
        _nixon_ঢϒॵぶЬž.append(_nixon_ʢじɩ曽๓შः * _nixon_პႵŨფճ蚃Ơ҃)
        _nixon_θबĉᚴย屮嶝 += 2
    return ''.join(_nixon_ঢϒॵぶЬž)

def _nx_a02e30(data, key):
    _nixon_Źᚬӥॸքᛛίъআ์ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ڙᚸѲक़ั = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ႴたӪเב ^ _nixon_ڙᚸѲक़ั[_nixon_θबĉᚴย屮嶝 % len(_nixon_ڙᚸѲक़ั)] for _nixon_θबĉᚴย屮嶝, _nixon_ႴたӪเב in enumerate(_nixon_Źᚬӥॸքᛛίъআ์)]).hex()

def _demo(argv):
    _nixon_ͿॏלᏧどծど = argv[0]
    if _nixon_ͿॏלᏧどծど == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ͿॏלᏧどծど == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ͿॏלᏧどծど == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])