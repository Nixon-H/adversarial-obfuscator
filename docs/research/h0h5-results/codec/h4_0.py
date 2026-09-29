import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ქॅნՈᚵへबকঐ = []
    run = text[0]
    _nixon_Ёแᛘąؕ = 1
    for _nixon_Ⴑ梵よ๙ضƐब in text[1:]:
        if _nixon_Ⴑ梵よ๙ضƐब == run[-1] and _nixon_Ёแᛘąؕ < 9:
            _nixon_Ёแᛘąؕ += 1
        else:
            _nixon_ქॅნՈᚵへबকঐ.append(run[-1] + str(_nixon_Ёแᛘąؕ))
            run = _nixon_Ⴑ梵よ๙ضƐब
            _nixon_Ёแᛘąؕ = 1
    _nixon_ქॅნՈᚵへबকঐ.append(run[-1] + str(_nixon_Ёแᛘąؕ))
    return ''.join(_nixon_ქॅნՈᚵへबকঐ)

def _nx_b27c0a(code):
    _nixon_ქॅნՈᚵへबকঐ = []
    _nixon_ڸתخωᛌȻॶ = 0
    while _nixon_ڸתخωᛌȻॶ < len(code):
        _nixon_Ⴑ梵よ๙ضƐब = code[_nixon_ڸתخωᛌȻॶ]
        _nixon_Ѿڍ棾ƫҹণ鷣 = int(code[_nixon_ڸתخωᛌȻॶ + 1])
        _nixon_ქॅნՈᚵへबকঐ.append(_nixon_Ⴑ梵よ๙ضƐब * _nixon_Ѿڍ棾ƫҹণ鷣)
        _nixon_ڸתخωᛌȻॶ += 2
    return ''.join(_nixon_ქॅნՈᚵへबকঐ)

def _nx_a02e30(data, key):
    _nixon_قۘᛏᚿҗᚦ儠ϩำस = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ᛟխՀٝاহ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ՙҕ۸ǓภხĞҴՄ ^ _nixon_ᛟխՀٝاহ[_nixon_ڸתخωᛌȻॶ % len(_nixon_ᛟխՀٝاহ)] for _nixon_ڸתخωᛌȻॶ, _nixon_ՙҕ۸ǓภხĞҴՄ in enumerate(_nixon_قۘᛏᚿҗᚦ儠ϩำस)]).hex()

def _demo(argv):
    _nixon_ろӼ牼ĳᛙևᛉ = argv[0]
    if _nixon_ろӼ牼ĳᛙևᛉ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ろӼ牼ĳᛙևᛉ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ろӼ牼ĳᛙևᛉ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])