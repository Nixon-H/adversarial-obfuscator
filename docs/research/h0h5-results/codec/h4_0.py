import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_าぎҤȇՅゑןপ = []
    run = text[0]
    _nixon_ᛆɧʭႿჇᛖょؔ蟨び = 1
    for _nixon_ʝऻႲɢᎥ in text[1:]:
        if _nixon_ʝऻႲɢᎥ == run[-1] and _nixon_ᛆɧʭႿჇᛖょؔ蟨び < 9:
            _nixon_ᛆɧʭႿჇᛖょؔ蟨び += 1
        else:
            _nixon_าぎҤȇՅゑןপ.append(run[-1] + str(_nixon_ᛆɧʭႿჇᛖょؔ蟨び))
            run = _nixon_ʝऻႲɢᎥ
            _nixon_ᛆɧʭႿჇᛖょؔ蟨び = 1
    _nixon_าぎҤȇՅゑןপ.append(run[-1] + str(_nixon_ᛆɧʭႿჇᛖょؔ蟨び))
    return ''.join(_nixon_าぎҤȇՅゑןপ)

def _nx_b27c0a(code):
    _nixon_าぎҤȇՅゑןপ = []
    _nixon_ქרɼզะふ = 0
    while _nixon_ქרɼզะふ < len(code):
        _nixon_ʝऻႲɢᎥ = code[_nixon_ქרɼզะふ]
        _nixon_ᛢЁᛏѳ১ = int(code[_nixon_ქרɼզะふ + 1])
        _nixon_าぎҤȇՅゑןপ.append(_nixon_ʝऻႲɢᎥ * _nixon_ᛢЁᛏѳ১)
        _nixon_ქרɼզะふ += 2
    return ''.join(_nixon_าぎҤȇՅゑןপ)

def _nx_a02e30(data, key):
    _nixon_ौทৢآ椱 = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ۂႥᛠմ্とת = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_য়讧дԾԳϩע ^ _nixon_ۂႥᛠմ্とת[_nixon_ქרɼզะふ % len(_nixon_ۂႥᛠմ্とת)] for _nixon_ქרɼզะふ, _nixon_য়讧дԾԳϩע in enumerate(_nixon_ौทৢآ椱)]).hex()

def _demo(argv):
    _nixon_はशʂĊץႱٟॎᏍ = argv[0]
    if _nixon_はशʂĊץႱٟॎᏍ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_はशʂĊץႱٟॎᏍ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_はशʂĊץႱٟॎᏍ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])