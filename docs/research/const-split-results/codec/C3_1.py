import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_זᏄᚽϊϤদ = []
    run = text[0]
    _nixon_ؐწ緤მ櫉ۦڗϦřู = 1
    for _nixon_ʋȔᎶכ畮Ξ in text[1:]:
        if _nixon_ʋȔᎶכ畮Ξ == run[-1] and _nixon_ؐწ緤მ櫉ۦڗϦřู < (4 << 1) + 1:
            _nixon_ؐწ緤მ櫉ۦڗϦřู += 1
        else:
            _nixon_זᏄᚽϊϤদ.append(run[-1] + str(_nixon_ؐწ緤მ櫉ۦڗϦřู))
            run = _nixon_ʋȔᎶכ畮Ξ
            _nixon_ؐწ緤მ櫉ۦڗϦřู = 1
    _nixon_זᏄᚽϊϤদ.append(run[-1] + str(_nixon_ؐწ緤მ櫉ۦڗϦřู))
    return ''.join(_nixon_זᏄᚽϊϤদ)

def _nx_b27c0a(code):
    _nixon_זᏄᚽϊϤদ = []
    _nixon_ๅ響řฤءӭงך = 0
    while _nixon_ๅ響řฤءӭงך < len(code):
        _nixon_ʋȔᎶכ畮Ξ = code[_nixon_ๅ響řฤءӭงך]
        _nixon_ՇᏒՙฯژধםĻ = int(code[_nixon_ๅ響řฤءӭงך + 1])
        _nixon_זᏄᚽϊϤদ.append(_nixon_ʋȔᎶכ畮Ξ * _nixon_ՇᏒՙฯژধםĻ)
        _nixon_ๅ響řฤءӭงך += 2
    return ''.join(_nixon_זᏄᚽϊϤদ)

def _nx_a02e30(data, key):
    _nixon_ՆसЈᏈր = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ϓれोყֆĒɚלڎש = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_Ⴍᛖศ砢ښΣぷ ^ _nixon_ϓれोყֆĒɚלڎש[_nixon_ๅ響řฤءӭงך % len(_nixon_ϓれोყֆĒɚלڎש)] for _nixon_ๅ響řฤءӭงך, _nixon_Ⴍᛖศ砢ښΣぷ in enumerate(_nixon_ՆसЈᏈր)]).hex()

def _demo(argv):
    _nixon_ՓΣѳึბ = argv[0]
    if _nixon_ՓΣѳึბ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ՓΣѳึბ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ՓΣѳึბ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])