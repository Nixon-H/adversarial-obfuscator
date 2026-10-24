import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_эثऎڨせ = []
    run = text[0]
    _nixon_ᏄᚽϊϤদؐ = 1
    for _nixon_წ緤მ櫉ۦڗϦřูЫ in text[1:]:
        if _nixon_წ緤მ櫉ۦڗϦřูЫ == run[-1] and _nixon_ᏄᚽϊϤদؐ < 9:
            _nixon_ᏄᚽϊϤদؐ += 1
        else:
            _nixon_эثऎڨせ.append(run[-1] + str(_nixon_ᏄᚽϊϤদؐ))
            run = _nixon_წ緤მ櫉ۦڗϦřูЫ
            _nixon_ᏄᚽϊϤদؐ = 1
    _nixon_эثऎڨせ.append(run[-1] + str(_nixon_ᏄᚽϊϤদؐ))
    return ''.join(_nixon_эثऎڨせ)

def _nx_b27c0a(code):
    _nixon_эثऎڨせ = []
    _nixon_ȔᎶכ畮ΞᎾ霃ๅ = 0
    while _nixon_ȔᎶכ畮ΞᎾ霃ๅ < len(code):
        _nixon_წ緤მ櫉ۦڗϦřูЫ = code[_nixon_ȔᎶכ畮ΞᎾ霃ๅ]
        _nixon_響řฤءӭงךᛧՇ = int(code[_nixon_ȔᎶכ畮ΞᎾ霃ๅ + 1])
        _nixon_эثऎڨせ.append(_nixon_წ緤მ櫉ۦڗϦřูЫ * _nixon_響řฤءӭงךᛧՇ)
        _nixon_ȔᎶכ畮ΞᎾ霃ๅ += 2
    return ''.join(_nixon_эثऎڨせ)

def _nx_a02e30(data, key):
    _nixon_ᏒՙฯژধםĻĭՑي = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_Ꮘրϓれो = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ყֆĒɚלڎשϝᛉ ^ _nixon_Ꮘրϓれो[_nixon_ȔᎶכ畮ΞᎾ霃ๅ % len(_nixon_Ꮘրϓれो)] for _nixon_ȔᎶכ畮ΞᎾ霃ๅ, _nixon_ყֆĒɚלڎשϝᛉ in enumerate(_nixon_ᏒՙฯژধםĻĭՑي)]).hex()

def _demo(argv):
    _nixon_砢ښΣぷĮႵ = argv[0]
    if _nixon_砢ښΣぷĮႵ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_砢ښΣぷĮႵ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_砢ښΣぷĮႵ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])