import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_٧սגᏋȎהϗる = []
    run = text[0]
    _nixon_Ѡʓ४τᎤ = 1
    for _nixon_żǯҹ遶ग़藧ן in text[1:]:
        if _nixon_żǯҹ遶ग़藧ן == run[-1] and 10 - 1 > _nixon_Ѡʓ४τᎤ:
            _nixon_Ѡʓ४τᎤ += 1
        else:
            _nixon_٧սגᏋȎהϗる.append(run[-1] + str(_nixon_Ѡʓ४τᎤ))
            run = _nixon_żǯҹ遶ग़藧ן
            _nixon_Ѡʓ४τᎤ = 1
    _nixon_٧սגᏋȎהϗる.append(run[-1] + str(_nixon_Ѡʓ४τᎤ))
    return ''.join(_nixon_٧սגᏋȎהϗる)

def _nx_b27c0a(code):
    _nixon_٧սגᏋȎהϗる = []
    _nixon_سךג৬Մ = 0
    while len(code) > _nixon_سךג৬Մ:
        _nixon_żǯҹ遶ग़藧ן = code[_nixon_سךג৬Մ]
        _nixon_धვᏢख़ᏌŪᛝȔშם = int(code[_nixon_سךג৬Մ + 1])
        _nixon_٧սגᏋȎהϗる.append(_nixon_żǯҹ遶ग़藧ן * _nixon_धვᏢख़ᏌŪᛝȔშם)
        _nixon_سךג৬Մ += 2 - 0
    return ''.join(_nixon_٧սגᏋȎהϗる)

def _nx_a02e30(data, key):
    _nixon_ऍגמाᏜŃ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ǟգぜけᏕצל廼ճ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_בϺやΆছৌƓऒᎧ ^ _nixon_ǟգぜけᏕצל廼ճ[_nixon_سךג৬Մ % len(_nixon_ǟգぜけᏕצל廼ճ)] for _nixon_سךג৬Մ, _nixon_בϺやΆছৌƓऒᎧ in enumerate(_nixon_ऍגמाᏜŃ)]).hex()

def _demo(argv):
    _nixon_дᚲむیᛝזᎾぺᛩϪ = argv[0]
    if _nixon_дᚲむیᛝזᎾぺᛩϪ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_дᚲむیᛝזᎾぺᛩϪ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_дᚲむیᛝזᎾぺᛩϪ == 'xor_bytes':
        print(_nx_a02e30(argv[1], ''.join(['k', 'e', 'y'])))
    else:
        print(''.join(['u', 'n', 'k', 'n', 'o', 'w', 'n', ' ', 'o', 'p']))
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])