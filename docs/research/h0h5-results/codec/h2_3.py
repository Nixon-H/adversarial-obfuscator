import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ΪᚩჩדᏢ嘶ןঘᏎհ = []
    run = text[0]
    _nixon_ขᏰŘᏆᚾय़づ = 1
    for _nixon_ĮŞƷゝკ in text[1:]:
        if _nixon_ĮŞƷゝკ == run[-1] and _nixon_ขᏰŘᏆᚾय़づ < 9:
            _nixon_ขᏰŘᏆᚾय़づ += 1
        else:
            _nixon_ΪᚩჩדᏢ嘶ןঘᏎհ.append(run[-1] + str(_nixon_ขᏰŘᏆᚾय़づ))
            run = _nixon_ĮŞƷゝკ
            _nixon_ขᏰŘᏆᚾय़づ = 1
    _nixon_ΪᚩჩדᏢ嘶ןঘᏎհ.append(run[-1] + str(_nixon_ขᏰŘᏆᚾय़づ))
    return ''.join(_nixon_ΪᚩჩדᏢ嘶ןঘᏎհ)

def _nx_b27c0a(code):
    _nixon_ΪᚩჩדᏢ嘶ןঘᏎհ = []
    _nixon_Ǻ阓ॏוᏳר = 0
    while _nixon_Ǻ阓ॏוᏳר < len(code):
        _nixon_ĮŞƷゝკ = code[_nixon_Ǻ阓ॏוᏳר]
        _nixon_ऺ๔ぬɔᏞ = int(code[_nixon_Ǻ阓ॏוᏳר + 1])
        _nixon_ΪᚩჩדᏢ嘶ןঘᏎհ.append(_nixon_ĮŞƷゝკ * _nixon_ऺ๔ぬɔᏞ)
        _nixon_Ǻ阓ॏוᏳר += 2
    return ''.join(_nixon_ΪᚩჩדᏢ嘶ןঘᏎհ)

def _nx_a02e30(data, key):
    _nixon_ほʠาɷゐїȚᏀঁ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_غץՠႨϼっ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ʦϞ๑偡Ǜ ^ _nixon_غץՠႨϼっ[_nixon_Ǻ阓ॏוᏳר % len(_nixon_غץՠႨϼっ)] for _nixon_Ǻ阓ॏוᏳר, _nixon_ʦϞ๑偡Ǜ in enumerate(_nixon_ほʠาɷゐїȚᏀঁ)]).hex()

def _demo(argv):
    _nixon_ҫᏥɱゐ籖კᏑ = argv[0]
    if _nixon_ҫᏥɱゐ籖კᏑ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ҫᏥɱゐ籖კᏑ == chr(114) + chr(108) + chr(101) + chr(95) + chr(100) + chr(101) + chr(99) + chr(111) + chr(100) + chr(101):
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ҫᏥɱゐ籖კᏑ == chr(120) + chr(111) + chr(114) + chr(95) + chr(98) + chr(121) + chr(116) + chr(101) + chr(115):
        print(_nx_a02e30(argv[1], ''.join(['k', 'e', 'y'])))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])