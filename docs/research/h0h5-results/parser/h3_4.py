import sys

def _nx_385816(text):
    _nixon_ƴЏॾくňϹჿŮ = []
    for _nixon_๔მপזゔցႠ in text.lower():
        if _nixon_๔მপזゔցႠ.isalnum():
            _nixon_ƴЏॾくňϹჿŮ.append(_nixon_๔მপזゔցႠ)
        elif _nixon_ƴЏॾくňϹჿŮ and _nixon_ƴЏॾくňϹჿŮ[-1] != '-':
            _nixon_ƴЏॾくňϹჿŮ.append('-')
    return ''.join(_nixon_ƴЏॾくňϹჿŮ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ॊאԻխձᛕ๓Ҋ = argv[0]
    _nixon_ჶӭɯᏄๆ = ' '.join(argv[1:])
    if _nixon_ॊאԻխձᛕ๓Ҋ == 'slugify':
        print(_nx_385816(_nixon_ჶӭɯᏄๆ))
    elif _nixon_ॊאԻխձᛕ๓Ҋ == 'count_words':
        print(_nx_385101(_nixon_ჶӭɯᏄๆ))
    elif _nixon_ॊאԻխձᛕ๓Ҋ == 'reverse_words':
        print(_nx_31b169(_nixon_ჶӭɯᏄๆ))
    elif _nixon_ॊאԻխձᛕ๓Ҋ == 'shout':
        print(_nx_8ca8c6(_nixon_ჶӭɯᏄๆ))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])