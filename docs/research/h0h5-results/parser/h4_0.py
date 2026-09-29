import sys

def _nx_385816(text):
    _nixon_ŤᚶИՖゞ = []
    for _nixon_ᛗѐৎञฝ in text.lower():
        if _nixon_ᛗѐৎञฝ.isalnum():
            _nixon_ŤᚶИՖゞ.append(_nixon_ᛗѐৎञฝ)
        elif _nixon_ŤᚶИՖゞ and _nixon_ŤᚶИՖゞ[-1] != '-':
            _nixon_ŤᚶИՖゞ.append('-')
    return ''.join(_nixon_ŤᚶИՖゞ).strip('-')

def _nx_385101(text):
    return len(text.split())

def _nx_31b169(text):
    return ' '.join(text.split()[::-1])

def _nx_8ca8c6(text):
    return text.upper() + '!'

def _demo(argv):
    _nixon_渏ĳฎɣՄט = argv[0]
    _nixon_淸ϖū砿ॴᏖ咐 = ' '.join(argv[1:])
    if _nixon_渏ĳฎɣՄט == 'slugify':
        print(_nx_385816(_nixon_淸ϖū砿ॴᏖ咐))
    elif _nixon_渏ĳฎɣՄט == 'count_words':
        print(_nx_385101(_nixon_淸ϖū砿ॴᏖ咐))
    elif _nixon_渏ĳฎɣՄט == 'reverse_words':
        print(_nx_31b169(_nixon_淸ϖū砿ॴᏖ咐))
    elif _nixon_渏ĳฎɣՄט == 'shout':
        print(_nx_8ca8c6(_nixon_淸ϖū砿ॴᏖ咐))
    else:
        print('unknown op')
if __name__ == '__main__':
    _demo(sys.argv[1:])