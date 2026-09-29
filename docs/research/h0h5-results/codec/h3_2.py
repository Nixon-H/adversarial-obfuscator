import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_าᏅգĄ़ؽॹ = []
    run = text[0]
    _nixon_ѪƘӵάぜĥƼᚢ = 1
    for _nixon_ơřᏓ歷აोც in text[1:]:
        if _nixon_ơřᏓ歷აोც == run[-1] and _nixon_ѪƘӵάぜĥƼᚢ < 9:
            _nixon_ѪƘӵάぜĥƼᚢ += 1
        else:
            _nixon_าᏅգĄ़ؽॹ.append(run[-1] + str(_nixon_ѪƘӵάぜĥƼᚢ))
            run = _nixon_ơřᏓ歷აोც
            _nixon_ѪƘӵάぜĥƼᚢ = 1
    _nixon_าᏅգĄ़ؽॹ.append(run[-1] + str(_nixon_ѪƘӵάぜĥƼᚢ))
    return ''.join(_nixon_าᏅգĄ़ؽॹ)

def _nx_b27c0a(code):
    _nixon_าᏅգĄ़ؽॹ = []
    _nixon_ךשՌקͶ蘕 = 0
    while _nixon_ךשՌקͶ蘕 < len(code):
        _nixon_ơřᏓ歷აोც = code[_nixon_ךשՌקͶ蘕]
        _nixon_ᛍ็ᛐśႧկᎣ = int(code[_nixon_ךשՌקͶ蘕 + 1])
        _nixon_าᏅգĄ़ؽॹ.append(_nixon_ơřᏓ歷აोც * _nixon_ᛍ็ᛐśႧկᎣ)
        _nixon_ךשՌקͶ蘕 += 2
    return ''.join(_nixon_าᏅգĄ़ؽॹ)

def _nx_a02e30(data, key):
    _nixon_ٰЈʔľΧ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_Գ睟ঁҳ皲๖כ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ŗʞᏩĤᏈ ^ _nixon_Գ睟ঁҳ皲๖כ[_nixon_ךשՌקͶ蘕 % len(_nixon_Գ睟ঁҳ皲๖כ)] for _nixon_ךשՌקͶ蘕, _nixon_ŗʞᏩĤᏈ in enumerate(_nixon_ٰЈʔľΧ)]).hex()

def _demo(argv):
    _nixon_ぉᚭɨ穜Ѭฐকי = argv[0]
    if _nixon_ぉᚭɨ穜Ѭฐকי == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ぉᚭɨ穜Ѭฐকי == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ぉᚭɨ穜Ѭฐকי == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])