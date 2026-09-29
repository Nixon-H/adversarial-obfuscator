import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_嫈Ⴤ茽ᎤǏᏍʑᛦॻ蒧 = []
    run = text[0]
    _nixon_ͼほैӟȦᛤ = 1
    for _nixon_ѮҌŀɡԳथϨ霴Υ in text[1:]:
        if _nixon_ѮҌŀɡԳथϨ霴Υ == run[-1] and 4 + 5 > _nixon_ͼほैӟȦᛤ:
            _nixon_ͼほैӟȦᛤ += 1
        else:
            _nixon_嫈Ⴤ茽ᎤǏᏍʑᛦॻ蒧.append(run[-1] + str(_nixon_ͼほैӟȦᛤ))
            run = _nixon_ѮҌŀɡԳथϨ霴Υ
            _nixon_ͼほैӟȦᛤ = 1
    _nixon_嫈Ⴤ茽ᎤǏᏍʑᛦॻ蒧.append(run[-1] + str(_nixon_ͼほैӟȦᛤ))
    return ''.join(_nixon_嫈Ⴤ茽ᎤǏᏍʑᛦॻ蒧)

def _nx_b27c0a(code):
    _nixon_嫈Ⴤ茽ᎤǏᏍʑᛦॻ蒧 = []
    _nixon_ऌƕƹᎿĄরぬśอख = 0
    while len(code) > _nixon_ऌƕƹᎿĄরぬśอख:
        _nixon_ѮҌŀɡԳथϨ霴Υ = code[_nixon_ऌƕƹᎿĄরぬśอख]
        _nixon_پՏɼॶหϺখɜĺ = int(code[_nixon_ऌƕƹᎿĄরぬśอख + 1])
        _nixon_嫈Ⴤ茽ᎤǏᏍʑᛦॻ蒧.append(_nixon_ѮҌŀɡԳथϨ霴Υ * _nixon_پՏɼॶหϺখɜĺ)
        _nixon_ऌƕƹᎿĄরぬśอख += 2
    return ''.join(_nixon_嫈Ⴤ茽ᎤǏᏍʑᛦॻ蒧)

def _nx_a02e30(data, key):
    _nixon_șפűհৃᛞわお२ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_ϼƉᎪᛊやמϢᎿџ = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_吀แՏ๊ѳкᚯফ ^ _nixon_ϼƉᎪᛊやמϢᎿџ[_nixon_ऌƕƹᎿĄরぬśอख % len(_nixon_ϼƉᎪᛊやמϢᎿџ)] for _nixon_ऌƕƹᎿĄরぬśอख, _nixon_吀แՏ๊ѳкᚯফ in enumerate(_nixon_șפűհৃᛞわお२)]).hex()

def _demo(argv):
    _nixon_ʙらᚵᚥţƧ鈘 = argv[0]
    if _nixon_ʙらᚵᚥţƧ鈘 == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ʙらᚵᚥţƧ鈘 == 'rle_decode':
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ʙらᚵᚥţƧ鈘 == 'xor_bytes':
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print(''.join(['u', 'n', 'k', 'n', 'o', 'w', 'n', ' ', 'o', 'p']))
if __name__ == '__main__':
    _demo(sys.argv[1:])