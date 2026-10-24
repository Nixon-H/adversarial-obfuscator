import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ŢԲՐぴᚺųхוŚ = []
    run = text[0]
    _nixon_ᎿจზԼʅבに腓 = 1
    for _nixon_ٚ٥ؠЇื in text[1:]:
        if _nixon_ٚ٥ؠЇื == run[-1] and _nixon_ᎿจზԼʅבに腓 < 9:
            _nixon_ᎿจზԼʅבに腓 += 1
        else:
            _nixon_ŢԲՐぴᚺųхוŚ.append(run[-1] + str(_nixon_ᎿจზԼʅבに腓))
            run = _nixon_ٚ٥ؠЇื
            _nixon_ᎿจზԼʅבに腓 = 1
    _nixon_ŢԲՐぴᚺųхוŚ.append(run[-1] + str(_nixon_ᎿจზԼʅבに腓))
    return ''.join(_nixon_ŢԲՐぴᚺųхוŚ)

def _nx_b27c0a(code):
    _nixon_ŢԲՐぴᚺųхוŚ = []
    _nixon_১ۍკՇת躮Ջ = 0
    while _nixon_১ۍკՇת躮Ջ < len(code):
        _nixon_ٚ٥ؠЇื = code[_nixon_১ۍკՇת躮Ջ]
        _nixon_רჷथᛐ゙ねɆჲ = int(code[_nixon_১ۍკՇת躮Ջ + 1])
        _nixon_ŢԲՐぴᚺųхוŚ.append(_nixon_ٚ٥ؠЇื * _nixon_רჷथᛐ゙ねɆჲ)
        _nixon_১ۍკՇת躮Ջ += 2
    return ''.join(_nixon_ŢԲՐぴᚺųхוŚ)

def _nx_a02e30(data, key):
    _nixon_ぉが磤ҟअ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ɯŸϊᚠँขԴ鄹 = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ᚼზնせ翹िۭ ^ _nixon_ɯŸϊᚠँขԴ鄹[_nixon_১ۍკՇת躮Ջ % len(_nixon_ɯŸϊᚠँขԴ鄹)] for _nixon_১ۍკՇת躮Ջ, _nixon_ᚼზնせ翹िۭ in enumerate(_nixon_ぉが磤ҟअ)]).hex()

def _demo(argv):
    _nixon_īɰՀؤŚ嘨ภ = argv[0]
    if _nixon_īɰՀؤŚ嘨ภ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_īɰՀؤŚ嘨ภ == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_īɰՀؤŚ嘨ภ == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])