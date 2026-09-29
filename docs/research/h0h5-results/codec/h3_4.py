import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ৈแɳᚷᎠǴ = []
    run = text[0]
    _nixon_すюքपᎶהও秵ӆӁ = 1
    for _nixon_জの৮だūրへӉ in text[1:]:
        if _nixon_জの৮だūրへӉ == run[-1] and _nixon_すюքपᎶהও秵ӆӁ < 9:
            _nixon_すюքपᎶהও秵ӆӁ += 1
        else:
            _nixon_ৈแɳᚷᎠǴ.append(run[-1] + str(_nixon_すюքपᎶהও秵ӆӁ))
            run = _nixon_জの৮だūրへӉ
            _nixon_すюքपᎶהও秵ӆӁ = 1
    _nixon_ৈแɳᚷᎠǴ.append(run[-1] + str(_nixon_すюքपᎶהও秵ӆӁ))
    return ''.join(_nixon_ৈแɳᚷᎠǴ)

def _nx_b27c0a(code):
    _nixon_ৈแɳᚷᎠǴ = []
    _nixon_םմุо३ѢぱᏘჍƵ = 0
    while _nixon_םմุо३ѢぱᏘჍƵ < len(code):
        _nixon_জの৮だūրへӉ = code[_nixon_םմุо३ѢぱᏘჍƵ]
        _nixon_Ǘɣ痺ƨけ = int(code[_nixon_םմุо३ѢぱᏘჍƵ + 1])
        _nixon_ৈแɳᚷᎠǴ.append(_nixon_জの৮だūրへӉ * _nixon_Ǘɣ痺ƨけ)
        _nixon_םմุо३ѢぱᏘჍƵ += 2
    return ''.join(_nixon_ৈแɳᚷᎠǴ)

def _nx_a02e30(data, key):
    _nixon_ȴСᛂち皸ב鰰ธג = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ऀ鬂ᏩųڟᎱξ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_য়พぼႯ柛Ꭵᚵ ^ _nixon_ऀ鬂ᏩųڟᎱξ[_nixon_םմุо३ѢぱᏘჍƵ % len(_nixon_ऀ鬂ᏩųڟᎱξ)] for _nixon_םմุо३ѢぱᏘჍƵ, _nixon_য়พぼႯ柛Ꭵᚵ in enumerate(_nixon_ȴСᛂち皸ב鰰ธג)]).hex()

def _demo(argv):
    _nixon_טѮႰႻᎳך = argv[0]
    if _nixon_טѮႰႻᎳך == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_טѮႰႻᎳך == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_טѮႰႻᎳך == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])