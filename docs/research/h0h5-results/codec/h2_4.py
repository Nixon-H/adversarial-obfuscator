import sys

def _nx_049ebf(text):
    if not text:
        return ''
    _nixon_ฃᏛۿᚼჇւתঔӵ = []
    run = text[0]
    _nixon_ণצϤŭנ = 1
    for _nixon_ᚳᛌऀďท০ in text[1:]:
        if _nixon_ᚳᛌऀďท০ == run[-1] and 9 > _nixon_ণצϤŭנ:
            _nixon_ণצϤŭנ += 1
        else:
            _nixon_ฃᏛۿᚼჇւתঔӵ.append(run[-1] + str(_nixon_ণצϤŭנ))
            run = _nixon_ᚳᛌऀďท০
            _nixon_ণצϤŭנ = 1
    _nixon_ฃᏛۿᚼჇւתঔӵ.append(run[-1] + str(_nixon_ণצϤŭנ))
    return ''.join(_nixon_ฃᏛۿᚼჇւתঔӵ)

def _nx_b27c0a(code):
    _nixon_ฃᏛۿᚼჇւתঔӵ = []
    _nixon_ᛄูӥȧפՃŢ = 0
    while len(code) > _nixon_ᛄูӥȧפՃŢ:
        _nixon_ᚳᛌऀďท০ = code[_nixon_ᛄูӥȧפՃŢ]
        _nixon_כজźմƍููŕ = int(code[_nixon_ᛄูӥȧפՃŢ + 1])
        _nixon_ฃᏛۿᚼჇւתঔӵ.append(_nixon_ᚳᛌऀďท০ * _nixon_כজźմƍููŕ)
        _nixon_ᛄูӥȧפՃŢ += 1 + 1
    return ''.join(_nixon_ฃᏛۿᚼჇւתঔӵ)

def _nx_a02e30(data, key):
    _nixon_ॽǆৌʠעϹけ鞆ϴ = data.encode() if isinstance(data, str) else bytes(data)
    _nixon_Ⴊסय़ȖႭ胎ƚα = key.encode() if isinstance(key, str) else bytes(key)
    return bytes([_nixon_ऎڽɗɭ५ᛦぱৼจ ^ _nixon_Ⴊסय़ȖႭ胎ƚα[_nixon_ᛄูӥȧפՃŢ % len(_nixon_Ⴊסय़ȖႭ胎ƚα)] for _nixon_ᛄูӥȧפՃŢ, _nixon_ऎڽɗɭ५ᛦぱৼจ in enumerate(_nixon_ॽǆৌʠעϹけ鞆ϴ)]).hex()

def _demo(argv):
    _nixon_ιɄבυᎦ๔ = argv[0]
    if _nixon_ιɄבυᎦ๔ == 'rle_encode':
        print(_nx_049ebf(argv[1]))
    elif _nixon_ιɄבυᎦ๔ == ''.join(['r', 'l', 'e', '_', 'd', 'e', 'c', 'o', 'd', 'e']):
        print(_nx_b27c0a(argv[1]))
    elif _nixon_ιɄבυᎦ๔ == chr(120) + chr(111) + chr(114) + chr(95) + chr(98) + chr(121) + chr(116) + chr(101) + chr(115):
        print(_nx_a02e30(argv[1], 'key'))
    else:
        print('unknown op')
if __name__ == ''.join(['_', '_', 'm', 'a', 'i', 'n', '_', '_']):
    _demo(sys.argv[1:])