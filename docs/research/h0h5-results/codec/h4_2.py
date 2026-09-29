import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ʥٙǐӼᚹ = []
    run = text[0]
    _nixon_ɺრĳԳӠהȘᚺ = 1
    for _nixon_לɹৎฆ殄ゑ納ڄ in text[1:]:
        if _nixon_לɹৎฆ殄ゑ納ڄ == run[-1] and _nixon_ɺრĳԳӠהȘᚺ < 9:
            _nixon_ɺრĳԳӠהȘᚺ += 1
        else:
            _nixon_ʥٙǐӼᚹ.append(run[-1] + str(_nixon_ɺრĳԳӠהȘᚺ))
            run = _nixon_לɹৎฆ殄ゑ納ڄ
            _nixon_ɺრĳԳӠהȘᚺ = 1
    _nixon_ʥٙǐӼᚹ.append(run[-1] + str(_nixon_ɺრĳԳӠהȘᚺ))
    return ''.join(_nixon_ʥٙǐӼᚹ)

def _nx_b27c0a(code):
    _nixon_ʥٙǐӼᚹ = []
    _nixon_ҙरףՓ伇 = 0
    while _nixon_ҙरףՓ伇 < len(code):
        _nixon_לɹৎฆ殄ゑ納ڄ = code[_nixon_ҙरףՓ伇]
        _nixon_৩ฌΘभتŔǟथ = int(code[_nixon_ҙरףՓ伇 + 1])
        _nixon_ʥٙǐӼᚹ.append(_nixon_לɹৎฆ殄ゑ納ڄ * _nixon_৩ฌΘभتŔǟथ)
        _nixon_ҙरףՓ伇 += 2
    return ''.join(_nixon_ʥٙǐӼᚹ)

def _nx_a02e30(data, key):
    _nixon_ſחʭऩᛜתņ涶ᛗᎺ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ċᏳԱᏍॲぶ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_や১Ⴇӵᛂ煚ĪᎰอ鹤 ^ _nixon_ċᏳԱᏍॲぶ[_nixon_ҙरףՓ伇 % len(_nixon_ċᏳԱᏍॲぶ)] for _nixon_ҙरףՓ伇, _nixon_や১Ⴇӵᛂ煚ĪᎰอ鹤 in enumerate(_nixon_ſחʭऩᛜתņ涶ᛗᎺ)]).hex()

def _demo(argv):
    _nixon_ġᛞ籮ᏔБहɚ = argv[0]
    if _nixon_ġᛞ籮ᏔБहɚ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ġᛞ籮ᏔБहɚ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ġᛞ籮ᏔБहɚ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])