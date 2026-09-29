import sys

def _nx_385816(text):
    _nixon_Ꮺ腗Şɹখ = []
    for _nixon_נıʌᎬċ in text.lower():
        if _nixon_נıʌᎬċ.isalnum():
            _nixon_Ꮺ腗Şɹখ.append(_nixon_נıʌᎬċ)
        elif _nixon_Ꮺ腗Şɹখ and _nixon_Ꮺ腗Şɹখ[-1] != '-':
            _nixon_Ꮺ腗Şɹখ.append('-')
    return ''.join(_nixon_Ꮺ腗Şɹখ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_ᏖղǕげŴլąჯड़ٖ = argv[0]
    _nixon_सʃრԷؐةȿᏯা৾ = ' '.join(argv[1:])
    if _nixon_ᏖղǕげŴլąჯड़ٖ == 'slugify':
        print(_nx_385816(_nixon_सʃრԷؐةȿᏯা৾))
    elif _nixon_ᏖղǕげŴլąჯड़ٖ == 'count_words':
        print(_nx_385101(_nixon_सʃრԷؐةȿᏯা৾))
    elif _nixon_ᏖղǕげŴլąჯड़ٖ == 'reverse_words':
        print(_nx_31b169(_nixon_सʃრԷؐةȿᏯা৾))
    elif _nixon_ᏖղǕげŴլąჯड़ٖ == 'shout':
        print(_nx_8ca8c6(_nixon_सʃრԷؐةȿᏯা৾))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])