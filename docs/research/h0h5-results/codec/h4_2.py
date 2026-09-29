import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ƲŒϭ癛ոᛗ = []
    run = text[0]
    _nixon_ʞᏇॆƏ肂חჴ = 1
    for _nixon_ᚼᏲŰ胲შ in text[1:]:
        if _nixon_ᚼᏲŰ胲შ == run[-1] and _nixon_ʞᏇॆƏ肂חჴ < 9:
            _nixon_ʞᏇॆƏ肂חჴ += 1
        else:
            _nixon_ƲŒϭ癛ոᛗ.append(run[-1] + str(_nixon_ʞᏇॆƏ肂חჴ))
            run = _nixon_ᚼᏲŰ胲შ
            _nixon_ʞᏇॆƏ肂חჴ = 1
    _nixon_ƲŒϭ癛ոᛗ.append(run[-1] + str(_nixon_ʞᏇॆƏ肂חჴ))
    return ''.join(_nixon_ƲŒϭ癛ոᛗ)

def _nx_b27c0a(code):
    _nixon_ƲŒϭ癛ոᛗ = []
    _nixon_ʜॕႨअॅ = 0
    while _nixon_ʜॕႨअॅ < len(code):
        _nixon_ᚼᏲŰ胲შ = code[_nixon_ʜॕႨअॅ]
        _nixon_ᚫेҞぺɴŘ๖ปҍʖ = int(code[_nixon_ʜॕႨअॅ + 1])
        _nixon_ƲŒϭ癛ոᛗ.append(_nixon_ᚼᏲŰ胲შ * _nixon_ᚫेҞぺɴŘ๖ปҍʖ)
        _nixon_ʜॕႨअॅ += 2
    return ''.join(_nixon_ƲŒϭ癛ոᛗ)

def _nx_a02e30(data, key):
    _nixon_ęΩぁʠवضժǬঀ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ıץӴᎳしত = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_৬ӷহᏌᛃ ^ _nixon_ıץӴᎳしত[_nixon_ʜॕႨअॅ % len(_nixon_ıץӴᎳしত)] for _nixon_ʜॕႨअॅ, _nixon_৬ӷহᏌᛃ in enumerate(_nixon_ęΩぁʠवضժǬঀ)]).hex()

def _demo(argv):
    _nixon_ᚦวა祳ᚭᛔᏠ = argv[0]
    if _nixon_ᚦวა祳ᚭᛔᏠ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ᚦวა祳ᚭᛔᏠ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ᚦวა祳ᚭᛔᏠ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])